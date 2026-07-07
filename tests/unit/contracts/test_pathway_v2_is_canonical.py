from __future__ import annotations

import json
import warnings
from pathlib import Path

import pytest

from sirna_offtarget.contracts.adapters.pathway_v2_to_v1 import pathway_v2_to_v1_payload
from sirna_offtarget.contracts.exceptions import ContractCompatibilityError
from sirna_offtarget.contracts.registry import CONTRACT_REGISTRY, STAGE_CONTRACTS
from sirna_offtarget.contracts.stage_results import (
    MechanisticNetworkResultV2,
    PathwayEnrichmentResultV2,
)
from sirna_offtarget.contracts.validation import validate_contract_file


def test_pathway_v2_is_available_and_mechanistic_v2_is_current_stage_contract() -> None:
    assert "pathway_enrichment" not in STAGE_CONTRACTS
    assert STAGE_CONTRACTS["mechanistic_network"] is MechanisticNetworkResultV2
    assert CONTRACT_REGISTRY["PathwayEnrichmentResultV2"] is PathwayEnrichmentResultV2
    assert CONTRACT_REGISTRY["MechanisticNetworkResultV2"] is MechanisticNetworkResultV2
    assert PathwayEnrichmentResultV2.expected_schema_version == "2"
    assert MechanisticNetworkResultV2.expected_schema_version == "2"


def test_v1_pathway_artifact_rejected_by_v2_contract(tmp_path: Path) -> None:
    path = tmp_path / "stage_result.json"
    path.write_text(
        json.dumps(
            {
                "contract_name": "PathwayEnrichmentResultV1",
                "schema_version": "1",
                "stage_name": "pathway_enrichment",
                "stage_version": "1.0",
                "run_id": "run",
                "attempt_number": 1,
                "payload": {"pathway_results": {"TP53": {}}, "pathway_gene_count": 1},
            }
        )
    )
    with pytest.raises(ContractCompatibilityError):
        validate_contract_file(path, PathwayEnrichmentResultV2)


def test_v2_to_v1_adapter_is_explicit_and_deprecated() -> None:
    contract = PathwayEnrichmentResultV2(
        contract_name="PathwayEnrichmentResultV2",
        schema_version="2",
        stage_name="pathway_enrichment",
        stage_version="1.0",
        run_id="run",
        attempt_number=1,
        payload={
            "gene_sets": {"down": ["TP53"]},
            "background_universe": ["TP53"],
            "provider_calculated_enrichment": [],
            "locally_calculated_enrichment": [],
            "enrichment_consensus": [],
            "annotation_membership_summary": {"completeness_status": "complete"},
            "identifier_mapping_summary": {},
            "provider_snapshot_manifest": {},
            "annotation_snapshot_manifest": {},
            "regulon_context": [{"gene": "TP53"}],
            "warnings": [],
        },
    )
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        payload = pathway_v2_to_v1_payload(contract)
    assert payload["deprecated_compatibility_payload"] is True
    assert "regulon_context_results" in payload
    assert any(item.category is DeprecationWarning for item in caught)
