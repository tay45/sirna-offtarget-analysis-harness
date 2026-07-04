from __future__ import annotations

import hashlib
import json
from typing import Literal

from pydantic import BaseModel, Field, model_validator


def stable_id(prefix: str, *parts: object) -> str:
    payload = json.dumps(parts, sort_keys=True, separators=(",", ":"), default=str)
    return f"{prefix}-{hashlib.sha256(payload.encode()).hexdigest()[:24]}"


CLASSIFICATION_INTERPRETATION_BOUNDARY = (
    "This classification is an evidence-based interpretation of the current harness outputs. "
    "It is not a definitive biological, clinical, toxicological, or regulatory conclusion."
)

FinalEvidenceClassification = Literal[
    "direct_compatible",
    "secondary_supported",
    "mixed_supported",
    "no_evidence_for_effect",
    "unresolved",
]

ClassificationConfidence = Literal["low", "moderate", "high", "unresolved"]

FORBIDDEN_CERTAINTY_LABELS = (
    "definitive_direct",
    "definitive_secondary",
    "true_off_target",
    "false_off_target",
    "toxic",
    "safe",
    "causal",
    "confirmed",
    "clinically_validated",
    "regulatory_ready",
    "validated_biological_effect",
)

FORBIDDEN_CLAIM_FIELDS = (
    "clinical_claim",
    "toxicological_claim",
    "regulatory_claim",
    "definitive_biological_claim",
    "causal_claim",
    "truth_status",
    "safety_status",
)


def _contains_forbidden_label(value: object) -> bool:
    if isinstance(value, str):
        return value in FORBIDDEN_CERTAINTY_LABELS
    if isinstance(value, dict):
        return any(_contains_forbidden_label(child) for child in value.values())
    if isinstance(value, (list, tuple, set)):
        return any(_contains_forbidden_label(child) for child in value)
    return False


class FinalEvidenceClassificationPolicyV1(BaseModel):
    schema_version: str = "1"
    policy_id: str = "final-evidence-classification-v1-conservative"
    numerical_tolerance: float = 1e-9
    confidence_policy_id: str = "final-evidence-confidence-v1-conservative"
    missing_evidence_as_negative_allowed: bool = False
    seed_only_upgrade_allowed: bool = False
    definitive_biological_claims_allowed: bool = False
    regulatory_claims_allowed: bool = False

    @model_validator(mode="after")
    def validate_guardrails(self) -> FinalEvidenceClassificationPolicyV1:
        if self.numerical_tolerance <= 0:
            raise ValueError("final_evidence_classification.numerical_tolerance must be positive")
        if self.missing_evidence_as_negative_allowed:
            raise ValueError("missing evidence must not be converted into negative evidence")
        if self.seed_only_upgrade_allowed:
            raise ValueError("seed-only evidence must not be upgraded")
        if self.definitive_biological_claims_allowed:
            raise ValueError("definitive biological claims are not allowed")
        if self.regulatory_claims_allowed:
            raise ValueError("regulatory claims are not allowed")
        return self

    @property
    def fingerprint(self) -> str:
        return stable_id("final-evidence-classification-policy", self.model_dump(mode="json"))


class GeneFinalEvidenceClassificationRecordV1(BaseModel):
    schema_version: str = "1"
    classification_record_id: str
    gene_id: str
    secondary_evidence_integration_record_id: str
    final_evidence_classification: FinalEvidenceClassification
    classification_confidence: ClassificationConfidence
    classification_reason: str
    observed_normalized_log2fc: float
    expected_direct_effect_log2fc: float | None
    observed_vs_expected_log2_difference: float | None
    unresolved_residual_log2fc: float | None
    residual_direction: str | None
    residual_magnitude_status: str | None
    residual_support_status: str
    direct_sequence_evidence_component: str
    expected_direct_effect_component: str
    residual_evidence_component: str
    pathway_support_component: str
    evidence_readiness_status: str
    targetability_fields_preserved: dict[str, object] = Field(default_factory=dict)
    calibration_fields_preserved: dict[str, object] = Field(default_factory=dict)
    pathway_support_summary: dict[str, object] = Field(default_factory=dict)
    upstream_warning_codes: tuple[str, ...] = ()
    classification_warning_codes: tuple[str, ...] = ()
    classification_interpretation_boundary: str = CLASSIFICATION_INTERPRETATION_BOUNDARY
    provenance_record_ids: tuple[str, ...] = ()
    source_secondary_evidence_integration_checksum: str | None = None

    @model_validator(mode="after")
    def validate_guardrails(self) -> GeneFinalEvidenceClassificationRecordV1:
        if self.classification_interpretation_boundary != CLASSIFICATION_INTERPRETATION_BOUNDARY:
            raise ValueError("final classification record must preserve interpretation boundary")
        if _contains_forbidden_label(self.model_dump(mode="json")):
            raise ValueError("forbidden certainty or regulatory label emitted")
        emitted_fields = (
            set(type(self).model_fields)
            | set(self.targetability_fields_preserved)
            | set(self.calibration_fields_preserved)
            | set(self.pathway_support_summary)
        )
        if set(FORBIDDEN_CLAIM_FIELDS).intersection(emitted_fields):
            raise ValueError("forbidden clinical, toxicological, regulatory, or definitive field")
        if (
            self.final_evidence_classification == "unresolved"
            and self.classification_confidence != "unresolved"
        ):
            raise ValueError("unresolved classifications must have unresolved confidence")
        if (
            self.final_evidence_classification == "no_evidence_for_effect"
            and self.classification_confidence == "high"
        ):
            raise ValueError("no_evidence_for_effect cannot have high confidence")
        return self


class FinalEvidenceClassificationUnresolvedRecordV1(BaseModel):
    schema_version: str = "1"
    unresolved_record_id: str
    gene_id: str
    reason: str
    source_secondary_evidence_integration_record_id: str | None = None
    preserved_upstream_status: str | None = None
    warning_codes: tuple[str, ...] = ()


class FinalEvidenceClassificationRunRecordV1(BaseModel):
    schema_version: str = "1"
    run_id: str
    stage_name: Literal["final_evidence_classification"] = "final_evidence_classification"
    stage_version: str = "1.0"
    secondary_evidence_integration_result_id: str
    secondary_evidence_integration_checksum: str
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


class FinalEvidenceClassificationVerificationRecordV1(BaseModel):
    schema_version: str = "1"
    verification_id: str
    secondary_evidence_integration_checks: Literal["passed", "failed"]
    preservation_checks: Literal["passed", "failed"]
    classification_policy_checks: Literal["passed", "failed"]
    confidence_policy_checks: Literal["passed", "failed"]
    interpretation_boundary_checks: Literal["passed", "failed"]
    forbidden_claim_checks: Literal["passed", "failed"]
    artifact_reference_checks: Literal["passed", "failed"]
    count_reconciliation_checks: Literal["passed", "failed"]
    passed: bool
    errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    verified_at: str


class FinalEvidenceClassificationResultV1(BaseModel):
    schema_version: str = "1"
    run_record: FinalEvidenceClassificationRunRecordV1
    policy_artifact: str
    gene_classification_records_artifact: str
    unresolved_records_artifact: str
    summary_artifact: str
    verification_artifact: str
    warnings_artifact: str
    canonical_artifact_checksums: dict[str, str]
    counts: dict[str, int]
    status: Literal["completed", "failed"]
    interpretation_boundary: str = CLASSIFICATION_INTERPRETATION_BOUNDARY
    warnings: tuple[str, ...] = ()
