from __future__ import annotations

from pathlib import Path

from sirna_offtarget.execution.api import run_staged_analysis
from sirna_offtarget.execution.hashing import load_json


def test_declared_data_dependencies_have_consumption_records(tmp_path: Path) -> None:
    out = tmp_path / "run"
    run_staged_analysis(config_path=Path("examples/synthetic/config.yaml"), output_dir=out)
    for manifest_path in out.glob("stages/*/attempts/attempt_001/stage_manifest.json"):
        manifest = load_json(manifest_path)
        declared = set(manifest.get("data_dependencies", []))
        consumed = {
            item["dependency_stage"]
            for item in manifest.get("consumed_dependencies", [])
            if item["dependency_type"] == "data"
        }
        assert declared <= consumed
