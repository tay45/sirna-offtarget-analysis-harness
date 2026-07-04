from __future__ import annotations

import importlib.util
from pathlib import Path

from sirna_offtarget.contracts.registry import CONTRACT_REGISTRY, STAGE_CONTRACTS
from sirna_offtarget.execution.dag import STAGE_NODES, STAGE_ORDER

ROOT = Path(__file__).resolve().parents[2]


def _snake(*parts: str) -> str:
    return "_".join(parts)


def _package(*parts: str) -> str:
    return ".".join(parts)


def test_removed_package_is_not_importable() -> None:
    removed = _package("sirna_offtarget", "scoring")
    assert importlib.util.find_spec(removed) is None
    try:
        found = importlib.util.find_spec(_package(removed, "api"))
    except ModuleNotFoundError:
        found = None
    assert found is None


def test_removed_stage_names_are_not_registered() -> None:
    removed_stage = _snake("candidate", "scoring")
    assert removed_stage not in STAGE_ORDER
    assert removed_stage not in STAGE_NODES
    assert removed_stage not in STAGE_CONTRACTS
    assert "classification" not in STAGE_ORDER
    assert "classification" not in STAGE_NODES
    assert "classification" not in STAGE_CONTRACTS
    assert list(STAGE_ORDER)[-1] == _snake("secondary", "evidence", "integration")


def test_removed_contracts_configs_and_schemas_are_absent() -> None:
    removed_contracts = {
        "".join(("Candidate", "Scoring", "ResultV1")),
        "".join(("Classification", "ResultV1")),
        "".join(("Final", "Reporting", "ResultV1")),
    }
    assert not removed_contracts.intersection(CONTRACT_REGISTRY)
    assert not (ROOT / "config").exists() or not any((ROOT / "config").iterdir())
    schema_names = {path.name for path in (ROOT / "schemas" / "stages").glob("*.json")}
    assert not {f"{name}.schema.json" for name in removed_contracts}.intersection(schema_names)


def test_current_source_contains_no_removed_execution_surface() -> None:
    source_root = ROOT / "src" / "sirna_offtarget"
    source = "\n".join(path.read_text() for path in source_root.rglob("*.py"))
    removed_tokens = {
        _snake("candidate", "scoring"),
        _snake("direct", "effect", "score"),
        _snake("secondary", "effect", "score"),
        _snake("final", "call"),
        _snake("off", "target", "call"),
        _snake("mechanism", "classification"),
        _snake("risk", "score"),
        _snake("risk", "tier"),
    }
    assert not {token for token in removed_tokens if token in source}


def test_coverage_config_has_no_removed_module_omit() -> None:
    text = (ROOT / "pyproject.toml").read_text()
    assert _package("src/sirna_offtarget", "scoring", "*") not in text
    assert _snake("final", "assembly") not in text
