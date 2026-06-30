from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

import pytest

from sirna_offtarget.contracts.stage_results import (
    MechanisticNetworkResultV2,
    _coerce_value,
    _dataclass_from_dict,
    pathway_results_from_contract,
)
from sirna_offtarget.expression.backends.deseq2_r import (
    Deseq2RBackend,
    DESeq2RBackendUnavailable,
)
from sirna_offtarget.expression.backends.pydeseq2 import (
    PyDeseq2Backend,
    PyDESeq2BackendUnavailable,
)
from sirna_offtarget.io.serialization import to_jsonable, write_json, write_tsv
from sirna_offtarget.pathway.fetch.transport import FetchResponse, fetch_bytes
from sirna_offtarget.pathway.providers.cache import (
    is_verified,
    latest_snapshot_dir,
    mark_verified,
    read_jsonl,
    require_valid_cache,
    write_jsonl,
)
from sirna_offtarget.pathway.providers.exceptions import ProviderSnapshotError
from sirna_offtarget.pathway.providers.registry import get_provider


class ExampleEnum(Enum):
    ACTIVE = "active"


@dataclass(frozen=True)
class ExampleRecord:
    path: Path
    status: ExampleEnum


def test_serialization_helpers_cover_dataclasses_enums_paths_and_tables(tmp_path: Path) -> None:
    payload = {
        "record": ExampleRecord(tmp_path / "input.tsv", ExampleEnum.ACTIVE),
        "items": (ExampleEnum.ACTIVE, tmp_path / "nested"),
    }

    assert to_jsonable(payload) == {
        "items": ["active", str(tmp_path / "nested")],
        "record": {"path": str(tmp_path / "input.tsv"), "status": "active"},
    }

    json_path = tmp_path / "payload.json"
    write_json(json_path, payload)
    assert json.loads(json_path.read_text())["record"]["status"] == "active"

    tsv_path = tmp_path / "rows.tsv"
    write_tsv(tsv_path, [{"gene": "A", "value": 1}])
    assert tsv_path.read_text().splitlines() == ["gene\tvalue", "A\t1"]


def test_stage_contract_coercion_handles_current_contract_shapes(tmp_path: Path) -> None:
    raw = {"path": str(tmp_path / "input.tsv"), "status": "active"}

    assert _coerce_value(str | None, None) is None
    assert _coerce_value(tuple[ExampleEnum, ...], ["active"]) == (ExampleEnum.ACTIVE,)
    assert _coerce_value(list[ExampleEnum], ["active"]) == (ExampleEnum.ACTIVE,)
    assert _coerce_value(dict[str, str], {"a": "b"}) == {"a": "b"}
    assert _coerce_value(ExampleEnum | None, "active") == ExampleEnum.ACTIVE
    assert _coerce_value(ExampleRecord, raw) == ExampleRecord(
        path=str(tmp_path / "input.tsv"),
        status=ExampleEnum.ACTIVE,
    )
    assert _dataclass_from_dict(ExampleRecord, raw) == ExampleRecord(
        path=str(tmp_path / "input.tsv"),
        status=ExampleEnum.ACTIVE,
    )


def test_mechanistic_network_v2_contract_converts_to_pathway_results() -> None:
    contract = MechanisticNetworkResultV2(
        contract_name="MechanisticNetworkResultV2",
        schema_version="2",
        stage_name="pathway_analysis",
        stage_version="1",
        run_id="run-1",
        attempt_number=1,
        payload={
            "signed_paths": [
                {
                    "candidate": "GENE1",
                    "path_length": 2,
                    "expected_candidate_direction_after_target_decrease": "down",
                    "direction_consistent": True,
                    "ordered_nodes": ["TARGET", "GENE1"],
                    "fully_signed": True,
                    "composed_sign": "positive",
                    "conflicting_with_other_paths": False,
                    "provider_sources": ["reactome"],
                    "warnings": ["low_support"],
                },
                {
                    "candidate": "GENE1",
                    "path_length": 3,
                    "direction_consistent": False,
                    "ordered_nodes": ["TARGET", "X", "GENE1"],
                    "fully_signed": False,
                    "composed_sign": "negative",
                    "conflicting_with_other_paths": True,
                    "provider_sources": ["signor"],
                    "warnings": [],
                },
            ],
            "unsigned_context_paths": [
                {
                    "candidate": "",
                    "path_length": 1,
                    "direction_consistent": None,
                }
            ],
        },
    )

    results = pathway_results_from_contract(contract)

    assert set(results) == {"GENE1"}
    assert results["GENE1"].target_pathway_distance == 2
    assert results["GENE1"].shortest_signed_path == ("TARGET", "GENE1")
    assert results["GENE1"].composed_path_sign == 1
    assert results["GENE1"].supporting_path_count == 1
    assert results["GENE1"].contradictory_path_count == 1
    assert results["GENE1"].conflicting_paths is True
    assert results["GENE1"].provider_sources == ("reactome", "signor")
    assert results["GENE1"].evidence_limitations == ("low_support",)


def test_optional_expression_backends_fail_explicitly() -> None:
    with pytest.raises(RuntimeError, match="DESeq2"):
        Deseq2RBackend(None)
    with pytest.raises(RuntimeError, match="not initialized"):
        Deseq2RBackend.run(object.__new__(Deseq2RBackend), None, None)
    with pytest.raises(RuntimeError, match="unavailable"):
        DESeq2RBackendUnavailable().run()
    with pytest.raises(RuntimeError, match="PyDESeq2"):
        PyDeseq2Backend(None)
    with pytest.raises(RuntimeError, match="not bundled"):
        PyDeseq2Backend.run(object.__new__(PyDeseq2Backend), None, None)
    with pytest.raises(RuntimeError, match="unavailable"):
        PyDESeq2BackendUnavailable().run()


def test_provider_cache_helpers_handle_missing_empty_and_marked_snapshots(tmp_path: Path) -> None:
    assert latest_snapshot_dir(tmp_path, "reactome") is None
    assert read_jsonl(tmp_path / "missing.jsonl") == []

    snapshot = tmp_path / "reactome" / "snap-a"
    snapshot.mkdir(parents=True)
    write_jsonl(snapshot / "records.jsonl", [{"a": 1}, {"b": Path("x")}])
    assert read_jsonl(snapshot / "records.jsonl") == [{"a": 1}, {"b": "x"}]
    assert latest_snapshot_dir(tmp_path, "reactome") == snapshot

    stale = snapshot / "leftover.tmp"
    stale.write_text("temporary\n")
    with pytest.raises(ProviderSnapshotError, match="stale temporary"):
        require_valid_cache(tmp_path)
    stale.unlink()

    assert not is_verified(snapshot)
    mark_verified(snapshot)
    assert is_verified(snapshot)


def test_provider_registry_and_transport_exports_are_current() -> None:
    assert get_provider("reactome_fi").__class__.__name__ == "ReactomeFIProvider"
    assert get_provider("reactome-fi").__class__.__name__ == "ReactomeFIProvider"
    assert get_provider("reactome_content").__class__.__name__ == "ReactomeContentProvider"
    with pytest.raises(KeyError, match="unknown pathway provider"):
        get_provider("missing")

    assert FetchResponse.__name__ == "FetchResponse"
    assert callable(fetch_bytes)
