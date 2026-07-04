from __future__ import annotations

import hashlib
import json
from typing import Literal

from pydantic import BaseModel, Field, model_validator


def stable_id(prefix: str, *parts: object) -> str:
    payload = json.dumps(parts, sort_keys=True, separators=(",", ":"), default=str)
    return f"{prefix}-{hashlib.sha256(payload.encode()).hexdigest()[:24]}"


INTERPRETATION_BOUNDARY = (
    "This record integrates evidence for future final classification. It is not a direct, "
    "secondary, mixed, or off-target classification."
)

DirectSequenceEvidenceComponent = Literal[
    "definitive_targetable_fraction_present",
    "no_cleavage_compatible_targetability",
    "unresolved_targetability",
    "unavailable_targetability",
]

ExpectedDirectEffectComponent = Literal[
    "expected_direct_effect_available",
    "expected_direct_effect_unavailable",
    "expected_direct_effect_zero",
    "expected_direct_effect_nonzero",
]

ResidualEvidenceComponent = Literal[
    "no_residual_to_integrate",
    "weak_residual_evidence",
    "moderate_residual_evidence",
    "strong_residual_evidence",
    "unresolved_residual_evidence",
]

PathwaySupportComponent = Literal[
    "no_residual_to_attribute",
    "residual_without_pathway_support",
    "residual_with_weak_pathway_support",
    "residual_with_moderate_pathway_support",
    "residual_with_strong_pathway_support",
    "unresolved_missing_pathway_evidence",
    "unresolved_upstream_expected_effect",
]

EvidenceReadinessStatus = Literal[
    "ready_for_final_classification",
    "ready_with_unresolved_pathway_context",
    "ready_with_unresolved_targetability",
    "insufficient_expected_effect_evidence",
    "insufficient_residual_evidence",
    "unresolved_upstream_residual_attribution",
]

FORBIDDEN_FINAL_CALL_FIELDS = (
    "_".join(("final", "classification")),
    "_".join(("final", "call")),
    "_".join(("gene", "class")),
    "_".join(("off", "target", "call")),
    "_".join(("secondary", "effect", "call")),
    "_".join(("direct", "effect", "call")),
    "_".join(("mixed", "call")),
)


class SecondaryEvidenceIntegrationPolicyV1(BaseModel):
    schema_version: str = "1"
    policy_id: str = "secondary-evidence-integration-v1-classification-ready-evidence"
    numerical_tolerance: float = 1e-9
    readiness_policy_id: str = "evidence-readiness-precedence-v1"
    classification_performed: bool = False
    classification_allowed: bool = False
    seed_only_upgrade_allowed: bool = False
    missing_evidence_as_negative_allowed: bool = False

    @model_validator(mode="after")
    def validate_guardrails(self) -> SecondaryEvidenceIntegrationPolicyV1:
        if self.numerical_tolerance <= 0:
            raise ValueError("secondary_evidence_integration.numerical_tolerance must be positive")
        if self.classification_performed:
            raise ValueError("secondary evidence integration must not perform final classification")
        if self.classification_allowed:
            raise ValueError("classification is not allowed in this stage")
        if self.seed_only_upgrade_allowed:
            raise ValueError("seed-only evidence must not be upgraded")
        if self.missing_evidence_as_negative_allowed:
            raise ValueError("missing evidence must remain unresolved, not negative evidence")
        return self

    @property
    def fingerprint(self) -> str:
        return stable_id("secondary-evidence-integration-policy", self.model_dump(mode="json"))


class GeneSecondaryEvidenceIntegrationRecordV1(BaseModel):
    schema_version: str = "1"
    integration_record_id: str
    gene_id: str
    residual_attribution_record_id: str
    observed_normalized_log2fc: float
    expected_direct_effect_log2fc: float | None
    observed_vs_expected_log2_difference: float | None
    unresolved_residual_log2fc: float | None
    residual_direction: str | None
    residual_magnitude_status: str | None
    residual_support_status: str
    direct_sequence_evidence_component: DirectSequenceEvidenceComponent
    expected_direct_effect_component: ExpectedDirectEffectComponent
    residual_evidence_component: ResidualEvidenceComponent
    pathway_support_component: PathwaySupportComponent
    evidence_readiness_status: EvidenceReadinessStatus
    targetability_fields_preserved: dict[str, object] = Field(default_factory=dict)
    calibration_fields_preserved: dict[str, object] = Field(default_factory=dict)
    pathway_support_summary: dict[str, object] = Field(default_factory=dict)
    interpretation_boundary: str = INTERPRETATION_BOUNDARY
    warning_codes: tuple[str, ...] = ()
    provenance_record_ids: tuple[str, ...] = ()
    source_residual_attribution_checksum: str | None = None

    @model_validator(mode="after")
    def validate_guardrails(self) -> GeneSecondaryEvidenceIntegrationRecordV1:
        if self.interpretation_boundary != INTERPRETATION_BOUNDARY:
            raise ValueError("secondary evidence record must preserve interpretation boundary")
        emitted = (
            set(type(self).model_fields)
            | set(self.pathway_support_summary)
            | set(self.targetability_fields_preserved)
            | set(self.calibration_fields_preserved)
        )
        if set(FORBIDDEN_FINAL_CALL_FIELDS).intersection(emitted):
            raise ValueError("secondary evidence integration must not emit final call fields")
        return self


class SecondaryEvidenceIntegrationUnresolvedRecordV1(BaseModel):
    schema_version: str = "1"
    unresolved_record_id: str
    gene_id: str
    reason: EvidenceReadinessStatus
    source_residual_attribution_record_id: str | None = None
    preserved_upstream_status: str | None = None
    warning_codes: tuple[str, ...] = ()


class SecondaryEvidenceIntegrationRunRecordV1(BaseModel):
    schema_version: str = "1"
    run_id: str
    stage_name: Literal["secondary_evidence_integration"] = "secondary_evidence_integration"
    stage_version: str = "1.0"
    residual_attribution_result_id: str
    residual_attribution_checksum: str
    policy_id: str
    policy_checksum: str
    started_at: str
    completed_at: str
    status: Literal["completed", "failed"]
    source_counts: dict[str, int] = Field(default_factory=dict)
    output_counts: dict[str, int] = Field(default_factory=dict)
    output_checksums: dict[str, str] = Field(default_factory=dict)
    verification_status: Literal["verified", "failed"]
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()


class SecondaryEvidenceIntegrationVerificationRecordV1(BaseModel):
    schema_version: str = "1"
    verification_id: str
    residual_attribution_checks: Literal["passed", "failed"]
    preservation_checks: Literal["passed", "failed"]
    evidence_component_checks: Literal["passed", "failed"]
    interpretation_boundary_checks: Literal["passed", "failed"]
    readiness_precedence_checks: Literal["passed", "failed"]
    artifact_reference_checks: Literal["passed", "failed"]
    count_reconciliation_checks: Literal["passed", "failed"]
    passed: bool
    errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    verified_at: str


class SecondaryEvidenceIntegrationResultV1(BaseModel):
    schema_version: str = "1"
    run_record: SecondaryEvidenceIntegrationRunRecordV1
    policy_artifact: str
    gene_evidence_records_artifact: str
    unresolved_records_artifact: str
    summary_artifact: str
    verification_artifact: str
    warnings_artifact: str
    canonical_artifact_checksums: dict[str, str]
    counts: dict[str, int]
    status: Literal["completed", "failed"]
    interpretation_boundary: str = INTERPRETATION_BOUNDARY
    warnings: tuple[str, ...] = ()
