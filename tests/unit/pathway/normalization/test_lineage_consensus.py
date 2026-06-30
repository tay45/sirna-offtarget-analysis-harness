from __future__ import annotations

from sirna_offtarget.pathway.providers.models import ProviderEdgeEvidenceRecord
from sirna_offtarget.pathway.providers.normalization import (
    build_consensus_edges,
    deduplicate_lineage,
    lineage_key,
    normalize_identifier,
)


def evidence(
    provider: str,
    sign: str,
    reference: str,
    *,
    original_source: str = "signor",
) -> ProviderEdgeEvidenceRecord:
    key = lineage_key("A", "B", "interaction", sign, original_source, reference)
    return ProviderEdgeEvidenceRecord(
        evidence_id=f"{provider}:{reference}",
        provider=provider,
        access_route=provider,
        source="A",
        target="B",
        source_identifier="A",
        target_identifier="B",
        directed=True,
        sign=sign,
        relation_type="interaction",
        mechanism="test",
        functional_only=False,
        causal_eligible=sign in {"positive", "negative"},
        original_sources=(original_source,),
        references=(reference,),
        organism="human",
        evidence_level="curated",
        provider_record_id=reference,
        database_version="v",
        retrieval_snapshot="snap",
        predicted_only=False,
        lineage_key=key,
    )


def test_signor_via_omnipath_deduplicates_by_lineage() -> None:
    direct = evidence("signor", "positive", "PMID1")
    via = evidence("omnipath", "positive", "PMID1")
    deduped = deduplicate_lineage([direct, via])
    assert len(deduped) == 1
    assert "lineage duplicate merged" in deduped[0].warnings


def test_independent_pmids_remain_independent_and_conflicts_surface() -> None:
    consensus = build_consensus_edges(
        [
            evidence("signor", "positive", "PMID1"),
            evidence("omnipath", "negative", "PMID2", original_source="omnipath"),
        ]
    )[0]
    assert consensus.consensus_sign == "conflicting"
    assert consensus.independent_source_count == 2


def test_identifier_mapping_keeps_ambiguous_records_auditable() -> None:
    mapping = normalize_identifier(
        "X",
        organism="human",
        mapping_provider="fixture",
        database_version="v",
        snapshot_id="snap",
        aliases={"X": ("A", "B")},
    )
    assert mapping.mapping_status == "ambiguous"
    assert mapping.candidate_mappings == ("A", "B")
