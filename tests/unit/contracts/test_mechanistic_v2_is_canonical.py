from __future__ import annotations

from sirna_offtarget.contracts.stage_results import MechanisticNetworkResultV2


def test_mechanistic_v2_required_sections_validate() -> None:
    contract = MechanisticNetworkResultV2(
        contract_name="MechanisticNetworkResultV2",
        schema_version="2",
        stage_name="mechanistic_network",
        stage_version="1.0",
        run_id="run",
        attempt_number=1,
        payload={
            "biological_entities": [{"entity_id": "gene:TP53"}],
            "identifier_resolution_records": [],
            "provider_evidence": [],
            "lineage_groups": [],
            "consensus_edges": [],
            "graph_layer_summary": {},
            "signed_paths": [],
            "unsigned_context_paths": [],
            "path_confidence_records": [],
            "contextual_conflicts": [],
            "unsupported_entities": [],
            "provider_snapshot_manifest": {},
            "identifier_snapshot_manifest": {},
            "warnings": [],
            "coverage_summary": {},
            "scientific_policy_manifest": {},
        },
    )
    assert contract.schema_version == "2"
    assert contract.payload.biological_entities[0]["entity_id"] == "gene:TP53"
