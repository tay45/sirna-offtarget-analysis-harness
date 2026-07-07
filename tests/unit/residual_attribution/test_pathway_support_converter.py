from __future__ import annotations

from sirna_offtarget.contracts.stage_results import MechanisticNetworkResultV2
from sirna_offtarget.residual_attribution.pathway_support import (
    SIGNED_PATH_KIND,
    UNSIGNED_CONTEXT_KIND,
    pathway_support_from_mechanistic_network_v2,
)


def _contract(*, signed_paths=None, unsigned_context_paths=None) -> MechanisticNetworkResultV2:
    return MechanisticNetworkResultV2(
        contract_name="MechanisticNetworkResultV2",
        schema_version="2",
        stage_name="mechanistic_network",
        stage_version="1.0",
        run_id="run-1",
        attempt_number=1,
        payload={
            "signed_paths": signed_paths or [],
            "unsigned_context_paths": unsigned_context_paths or [],
            "provider_snapshot_manifest": {
                "providers": [{"provider": "signor", "snapshot_id": "signor-v1"}]
            },
            "metrics": {},
        },
    )


def test_signed_mechanistic_paths_become_candidate_support() -> None:
    contract = _contract(
        signed_paths=[
            {
                "path_id": "path-1",
                "search_result_id": "search-1",
                "candidate": "GENEA",
                "ordered_nodes": ("TARGET", "GENEA"),
                "path_length": 1,
                "fully_signed": True,
                "direction_consistent": True,
                "composed_sign": "positive",
                "provider_sources": ("SIGNOR",),
                "references": ("PMID:1",),
                "database_versions": ("signor-v1",),
            }
        ]
    )

    support = pathway_support_from_mechanistic_network_v2(contract)

    assert list(support) == ["GENEA"]
    record = support["GENEA"][0]
    assert record.record_id == "path-1"
    assert record.evidence_kind == SIGNED_PATH_KIND
    assert record.support_strength == "direction_consistent_signed_path"
    assert record.summary
    assert record.summary["causal_direction_support"] is True
    assert record.summary["provider_sources"] == ("SIGNOR",)
    assert record.summary["references"] == ("PMID:1",)


def test_unsigned_context_paths_are_preserved_without_causal_direction_support() -> None:
    contract = _contract(
        unsigned_context_paths=[
            {
                "path_id": "context-1",
                "candidate": "GENEB",
                "ordered_nodes": ("TARGET", "GENEB"),
                "path_length": 1,
                "fully_signed": False,
                "provider_sources": ("ReactomeFI",),
                "warnings": ("unsigned_context_only",),
            }
        ]
    )

    support = pathway_support_from_mechanistic_network_v2(contract)

    record = support["GENEB"][0]
    assert record.evidence_kind == UNSIGNED_CONTEXT_KIND
    assert record.support_strength == "supporting_context"
    assert record.summary
    assert record.summary["causal_direction_support"] is False
    assert (
        record.summary["interpretation"] == "unsigned_or_context_path_not_causal_direction_support"
    )
