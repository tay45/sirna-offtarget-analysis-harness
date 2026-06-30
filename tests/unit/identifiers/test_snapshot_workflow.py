from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from sirna_offtarget.cli import main
from sirna_offtarget.identifiers.snapshots import (
    inspect_identifier_cache,
    verify_identifier_cache,
    write_identifier_snapshot,
)

ROOT = Path(__file__).resolve().parents[3]
CONFIG = ROOT / "examples/synthetic/config.yaml"


def test_identifier_snapshot_fetch_inspect_verify(tmp_path: Path) -> None:
    snapshot = write_identifier_snapshot(tmp_path, "human")
    assert (snapshot / "records.jsonl").exists()
    assert inspect_identifier_cache(tmp_path)[0]["schema_version"] == "identifier-snapshot-v1"
    assert verify_identifier_cache(tmp_path) == []
    runner = CliRunner()
    fetch = runner.invoke(
        main,
        ["identifier-db", "fetch", "--config", str(CONFIG), "--cache-dir", str(tmp_path / "cli")],
    )
    assert fetch.exit_code == 0, fetch.output
    inspect = runner.invoke(
        main, ["identifier-db", "inspect", "--cache-dir", str(tmp_path / "cli")]
    )
    assert inspect.exit_code == 0, inspect.output
    verify = runner.invoke(main, ["identifier-db", "verify", "--cache-dir", str(tmp_path / "cli")])
    assert verify.exit_code == 0, verify.output
