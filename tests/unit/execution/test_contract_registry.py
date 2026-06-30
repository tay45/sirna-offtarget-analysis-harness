from __future__ import annotations

from sirna_offtarget.contracts.registry import CONTRACT_REGISTRY, STAGE_CONTRACTS


def test_all_stages_have_registered_contracts() -> None:
    assert STAGE_CONTRACTS["sequence_analysis"].expected_contract_name == "SequenceAnalysisResultV1"
    assert "_".join(("candidate", "scoring")) not in STAGE_CONTRACTS
    assert set(STAGE_CONTRACTS.values()).issubset(set(CONTRACT_REGISTRY.values()))
