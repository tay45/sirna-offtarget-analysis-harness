from __future__ import annotations

import hashlib
import json
import math
from typing import ClassVar, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

IsoformEvidenceMode = Literal[
    "annotation_only_equal_prior",
    "precomputed_transcript_proportions",
    "precomputed_transcript_abundance",
    "unsupported",
    "insufficient_evidence",
]
IsoformResolutionStatus = Literal[
    "single_eligible_transcript",
    "multiple_transcripts_equal_prior",
    "multiple_transcripts_external_proportions",
    "multiple_transcripts_external_abundance",
    "no_eligible_transcripts",
    "annotation_unavailable",
    "identifier_unresolved",
    "annotation_conflict",
    "invalid_external_proportions",
    "insufficient_evidence",
    "unsupported",
]
TranscriptWeightType = Literal[
    "equal_prior",
    "external_proportion",
    "abundance_derived_proportion",
    "unavailable",
]
ExternalProportionPolicy = Literal[
    "fail_gene",
    "fail_stage",
    "preserve_invalid_with_status",
    "renormalize_with_warning",
]
MissingTranscriptBehavior = Literal[
    "require_complete_coverage",
    "missing_as_zero",
    "fallback_to_equal_prior",
]
ExternalRowBehavior = Literal["fail_gene", "fail_stage", "ignore_with_warning"]


def stable_id(prefix: str, *parts: object) -> str:
    payload = json.dumps(parts, sort_keys=True, separators=(",", ":"), default=str)
    return f"{prefix}-{hashlib.sha256(payload.encode()).hexdigest()[:24]}"


class TranscriptSetPolicyV1(BaseModel):
    schema_version: str = "1"
    policy_id: str = "transcript-set-policy-v1-conservative"
    include_protein_coding: bool = True
    include_retained_intron: bool = True
    include_nonsense_mediated_decay: bool = True
    include_processed_transcript: bool = True
    include_noncoding: bool = True
    include_pseudogene: bool = False
    include_readthrough: bool = False
    allow_alternative_contigs: bool = False
    allow_deprecated_transcripts: bool = False
    require_sequence_reference: bool = True
    allow_unresolved_gene_mapping: bool = False
    allowed_transcript_support_levels: tuple[str, ...] | None = None

    @property
    def fingerprint(self) -> str:
        data = self.model_dump(exclude={"policy_id"})
        data["allow_unresolved_gene_mapping"] = False
        return stable_id("tx-policy", data)


class ExternalTranscriptProportionPolicyV1(BaseModel):
    schema_version: str = "1"
    policy_id: str = "external-transcript-proportion-policy-v1-strict"
    invalid_proportion_behavior: ExternalProportionPolicy = "fail_gene"
    missing_transcript_behavior: MissingTranscriptBehavior = "require_complete_coverage"
    duplicate_row_behavior: ExternalRowBehavior = "fail_gene"
    unknown_transcript_behavior: ExternalRowBehavior = "fail_gene"
    wrong_gene_mapping_behavior: ExternalRowBehavior = "fail_gene"
    small_rounding_tolerance: float = 1e-6
    material_sum_tolerance: float = 0.05
    allow_renormalization: bool = False

    @property
    def fingerprint(self) -> str:
        return stable_id("external-tx-proportion-policy", self.model_dump(exclude={"policy_id"}))


class TranscriptAnnotationSnapshotV1(BaseModel):
    schema_version: str = "1"
    provider: str
    release: str
    organism: str
    assembly: str
    transcript_identifier_namespace: str
    gene_identifier_namespace: str
    source_file_checksum: str
    snapshot_id: str
    verification_status: Literal["verified", "unverified"]

    @property
    def fingerprint(self) -> str:
        return stable_id("tx-annotation", self.model_dump())


class TranscriptAnnotationRecordV1(BaseModel):
    schema_version: str = "1"
    original_gene_id: str
    canonical_gene_id: str | None
    original_transcript_id: str
    canonical_transcript_id: str | None
    transcript_version: str | None = None
    transcript_biotype: str
    organism: str
    assembly: str
    annotation_release: str
    sequence_reference: str | None = None
    transcript_support_level: str | None = None
    deprecated: bool = False
    alternative_contig: bool = False
    unresolved_gene_mapping: bool = False
    ambiguous_transcript_mapping: bool = False
    warnings: tuple[str, ...] = ()


class TranscriptAnnotationValidationRecordV1(BaseModel):
    schema_version: str = "1"
    annotation_snapshot_id: str
    total_rows: int
    unique_genes: int
    unique_transcripts: int
    duplicates: int
    invalid_mappings: int
    unresolved_genes: int
    unresolved_transcripts: int
    assembly_conflicts: int
    organism_conflicts: int
    missing_sequence_references: int
    warnings: tuple[str, ...] = ()
    fatal_errors: tuple[str, ...] = ()


class TranscriptSetExclusionRecordV1(BaseModel):
    schema_version: str = "1"
    record_id: str
    canonical_gene_id: str
    transcript_id: str
    policy_id: str
    exclusion_reason: str
    annotation_snapshot_id: str
    warnings: tuple[str, ...] = ()


class TranscriptPriorWeightRecordV1(BaseModel):
    schema_version: str = "1"
    record_id: str
    gene_isoform_uncertainty_record_id: str
    original_gene_id: str
    canonical_gene_id: str
    original_transcript_id: str
    canonical_transcript_id: str
    transcript_version: str | None
    transcript_biotype: str
    annotation_status: str
    eligibility_status: str
    exclusion_reason: str | None
    weight: float | None
    weight_type: TranscriptWeightType
    weight_source: str
    weight_evidence_status: str
    source_method: str | None = None
    source_software: str | None = None
    source_software_version: str | None = None
    source_annotation_release: str | None = None
    warnings: tuple[str, ...] = ()
    provenance_record_ids: tuple[str, ...] = ()

    @field_validator("weight")
    @classmethod
    def validate_weight(cls, value: float | None) -> float | None:
        if value is None:
            return None
        if not math.isfinite(value):
            raise ValueError("transcript weight must be finite")
        if value < 0 or value > 1:
            raise ValueError("transcript weight must be between 0 and 1")
        return value

    @model_validator(mode="after")
    def validate_no_overclaiming(self) -> TranscriptPriorWeightRecordV1:
        forbidden = ("observed_fraction", "true_isoform_fraction", "measured_isoform_fraction")
        text = " ".join(
            str(item)
            for item in (
                self.weight_source,
                self.weight_evidence_status,
                self.source_method,
                self.source_software,
            )
            if item is not None
        )
        if any(term in text for term in forbidden):
            raise ValueError("weight wording must not overclaim biological abundance")
        return self


class GeneIsoformUncertaintyRecordV1(BaseModel):
    schema_version: str = "1"
    record_id: str
    source_expression_v2_record_id: str
    original_gene_id: str
    canonical_gene_id: str
    approved_symbol: str | None
    organism: str
    assembly: str
    annotation_snapshot_id: str
    annotation_checksum: str
    transcript_set_policy_id: str
    annotated_transcript_count: int
    eligible_transcript_count: int
    excluded_transcript_count: int
    isoform_evidence_mode: IsoformEvidenceMode
    isoform_resolution_status: IsoformResolutionStatus
    prior_method: str
    weight_sum: float | None
    transcript_weight_record_ids: tuple[str, ...]
    input_proportion_source: str | None = None
    input_abundance_source: str | None = None
    warnings: tuple[str, ...] = ()
    exclusion_reasons: tuple[str, ...] = ()
    provenance_record_ids: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_counts_and_weights(self) -> GeneIsoformUncertaintyRecordV1:
        if self.eligible_transcript_count == 0 and self.transcript_weight_record_ids:
            raise ValueError("no weights may be generated for zero eligible transcripts")
        if self.eligible_transcript_count == 0 and self.weight_sum not in (None, 0.0):
            raise ValueError("zero eligible transcript genes must not have a positive weight sum")
        if "fold_change" in self.model_dump_json() or "p_value" in self.model_dump_json():
            raise ValueError("isoform uncertainty records must not carry transcript effect fields")
        return self


class ExternalTranscriptProportionRecordV1(BaseModel):
    schema_version: str = "1"
    original_gene_id: str
    original_transcript_id: str
    canonical_gene_id: str
    canonical_transcript_id: str
    proportion: float
    sample_or_contrast_scope: str
    source_method: str
    source_software: str
    source_software_version: str
    annotation_release: str
    organism: str
    assembly: str
    source_file_checksum: str

    @field_validator("proportion")
    @classmethod
    def validate_proportion(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("proportion must be finite")
        if value < 0:
            raise ValueError("proportion must be nonnegative")
        if value > 1:
            raise ValueError("proportion must not exceed 1")
        return value


class IsoformUncertaintyRunRecordV1(BaseModel):
    schema_version: str = "1"
    run_id: str
    stage_name: str = "isoform_uncertainty"
    expression_stage_contract: str
    expression_result_record_id: str | None = None
    expression_artifact_checksum: str
    annotation_snapshot_id: str
    annotation_validation_record_id: str | None = None
    annotation_checksum: str
    transcript_set_policy_id: str
    external_proportion_policy_id: str | None = None
    isoform_evidence_mode: IsoformEvidenceMode
    evidence_mode: IsoformEvidenceMode | None = None
    fallback_policy: str | None = None
    external_evidence_files: tuple[str, ...] = ()
    external_evidence_checksums: tuple[str, ...] = ()
    weight_policy: str
    numerical_tolerance: float
    numerical_tolerances: dict[str, float] = Field(default_factory=dict)
    organism: str
    assembly: str
    identifier_snapshot_id: str | None
    identifier_snapshot_checksum: str | None
    software_version: str
    adapter_versions: dict[str, str] = Field(default_factory=dict)
    started_at: str
    completed_at: str
    status: Literal["completed", "failed"]
    verification_status: Literal["verified", "failed", "not_applicable"] = "verified"
    source_record_counts: dict[str, int] = Field(default_factory=dict)
    output_record_counts: dict[str, int] = Field(default_factory=dict)
    record_counts: dict[str, int]
    referenced_artifact_checksums: dict[str, str] = Field(default_factory=dict)
    self_checksum_status: Literal["recorded_in_outer_manifest"] = "recorded_in_outer_manifest"
    output_checksums: dict[str, str] = Field(
        default_factory=dict,
        exclude=True,
        description="Deprecated compatibility alias; do not use for isoform metadata checksums.",
    )
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_completed_run(self) -> IsoformUncertaintyRunRecordV1:
        if self.status == "completed":
            if not self.started_at or not self.completed_at:
                raise ValueError("completed run requires timestamps")
            if not self.referenced_artifact_checksums and not self.output_checksums:
                raise ValueError("completed run requires referenced artifact checksums")
            if not self.annotation_checksum:
                raise ValueError("completed run requires annotation checksum")
        return self


class IsoformUncertaintyPayloadV1(BaseModel):
    run_record: IsoformUncertaintyRunRecordV1
    counts: dict[str, int]
    artifacts: dict[str, str]


class IsoformUncertaintyArtifactVerificationRecordV1(BaseModel):
    schema_version: str = "1"
    verification_id: str
    stage_name: str = "isoform_uncertainty"
    expected_artifacts: tuple[str, ...]
    observed_artifacts: tuple[str, ...]
    final_checksums: dict[str, str]
    referenced_checksum_comparisons: dict[str, bool]
    count_comparisons: dict[str, bool]
    schema_comparisons: dict[str, bool]
    run_status_check: bool
    result_reference_check: bool
    passed: bool
    errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    verified_at: str


class IsoformUncertaintyResultContractNames:
    contract_name: ClassVar[str] = "IsoformUncertaintyResultV1"
    schema_version: ClassVar[str] = "1"
