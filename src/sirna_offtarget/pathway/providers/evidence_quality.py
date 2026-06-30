from __future__ import annotations

from dataclasses import dataclass

from sirna_offtarget.pathway.providers.models import ProviderEdgeEvidenceRecord


@dataclass(frozen=True)
class EvidenceQuality:
    explicit_direction: bool
    explicit_sign: bool
    publication_support: int
    independent_original_databases: int
    curated: bool
    predicted_penalty: float
    functional_only_penalty: float
    uncertainty: str
    evidence_level: str
    component_score: float


def evaluate_evidence_quality(record: ProviderEdgeEvidenceRecord) -> EvidenceQuality:
    explicit_sign = record.sign in {"positive", "negative"}
    score = 0.0
    score += 2.0 if record.directed else 0.0
    score += 2.0 if explicit_sign else 0.0
    score += min(len(record.references), 3)
    score += min(len(record.original_sources), 3)
    if record.predicted_only:
        score -= 2.0
    if record.functional_only:
        score -= 2.0
    if record.sign == "conflicting":
        level = "conflicting"
    elif record.functional_only:
        level = "contextual"
    elif score >= 6:
        level = "high"
    elif score >= 4:
        level = "moderate"
    elif score > 0:
        level = "low"
    else:
        level = "insufficient"
    return EvidenceQuality(
        explicit_direction=record.directed,
        explicit_sign=explicit_sign,
        publication_support=len(record.references),
        independent_original_databases=len(record.original_sources),
        curated=record.evidence_level == "curated",
        predicted_penalty=2.0 if record.predicted_only else 0.0,
        functional_only_penalty=2.0 if record.functional_only else 0.0,
        uncertainty="unsigned functional evidence" if record.functional_only else "not calibrated",
        evidence_level=level,
        component_score=max(score, 0.0),
    )
