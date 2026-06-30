from __future__ import annotations

from sirna_offtarget.contracts.registry import STAGE_CONTRACTS


def test_stage_contract_schemas_generate() -> None:
    for contract in STAGE_CONTRACTS.values():
        schema = contract.model_json_schema()
        assert schema["type"] == "object"
