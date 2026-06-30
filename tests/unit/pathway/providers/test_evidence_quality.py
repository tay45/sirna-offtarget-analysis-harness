from __future__ import annotations

from sirna_offtarget.pathway.providers.evidence_quality import evaluate_evidence_quality
from sirna_offtarget.pathway.providers.models import ProviderEdgeEvidenceRecord


def _edge(**overrides: object) -> ProviderEdgeEvidenceRecord:
    values = {
        "evidence_id": "ev1",
        "provider": "signor",
        "access_route": "api",
        "source": "A",
        "target": "B",
        "source_identifier": "A",
        "target_identifier": "B",
        "directed": True,
        "sign": "positive",
        "relation_type": "activation",
        "mechanism": "curated",
        "functional_only": False,
        "causal_eligible": True,
        "original_sources": ("SIGNOR", "Reactome"),
        "references": ("PMID1", "PMID2"),
        "organism": "human",
        "evidence_level": "curated",
        "provider_record_id": "r1",
        "database_version": "v1",
        "retrieval_snapshot": "s1",
        "predicted_only": False,
        "lineage_key": "l1",
        "warnings": (),
    }
    values.update(overrides)
    return ProviderEdgeEvidenceRecord(**values)


def test_evidence_quality_scores_curated_signed_edges_highly() -> None:
    quality = evaluate_evidence_quality(_edge())
    assert quality.explicit_direction
    assert quality.explicit_sign
    assert quality.evidence_level == "high"


def test_evidence_quality_marks_functional_unsigned_contextual() -> None:
    quality = evaluate_evidence_quality(
        _edge(sign="unsigned", functional_only=True, references=(), original_sources=())
    )
    assert quality.evidence_level == "contextual"
    assert quality.functional_only_penalty == 2.0


def test_evidence_quality_marks_conflicts_explicitly() -> None:
    quality = evaluate_evidence_quality(_edge(sign="conflicting"))
    assert quality.evidence_level == "conflicting"
