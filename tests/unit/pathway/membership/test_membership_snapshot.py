from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from sirna_offtarget.cli import main
from sirna_offtarget.pathway.membership import (
    build_annotation_membership_snapshot,
    inspect_membership_cache,
    load_verified_memberships,
    to_enrichment_memberships,
    verify_membership_cache,
)

ROOT = Path(__file__).resolve().parents[4]
CONFIG = ROOT / "examples/synthetic/config.yaml"
FIXTURE = ROOT / "tests/fixtures/annotation_memberships.tsv"


def test_annotation_membership_snapshot_build_verify_load(tmp_path: Path) -> None:
    snapshot = build_annotation_membership_snapshot(
        cache_dir=tmp_path,
        provider="reactome",
        input_files=[FIXTURE],
        organism="human",
        annotation_source="REACTOME_PATHWAY",
        snapshot_id="reactome-human-test",
        provider_release="release-test",
    )
    assert (snapshot / "annotation_memberships.tsv").exists()
    assert verify_membership_cache(tmp_path) == []
    assert inspect_membership_cache(tmp_path)[0]["membership_record_count"] == 4
    records = load_verified_memberships(tmp_path, provider="reactome")
    assert {record.completeness_status for record in records} == {"complete", "partial"}
    enrichment_records = to_enrichment_memberships(records)
    assert {record.membership_completeness for record in enrichment_records} == {
        "complete",
        "partial",
    }


def test_annotation_db_cli_build_inspect_verify(tmp_path: Path) -> None:
    runner = CliRunner()
    build = runner.invoke(
        main,
        [
            "annotation-db",
            "build",
            "--config",
            str(CONFIG),
            "--provider",
            "reactome",
            "--annotation-source",
            "REACTOME_PATHWAY",
            "--inputs",
            str(FIXTURE),
            "--cache-dir",
            str(tmp_path),
        ],
    )
    assert build.exit_code == 0, build.output
    inspect = runner.invoke(main, ["annotation-db", "inspect", "--cache-dir", str(tmp_path)])
    assert inspect.exit_code == 0, inspect.output
    verify = runner.invoke(main, ["annotation-db", "verify", "--cache-dir", str(tmp_path)])
    assert verify.exit_code == 0, verify.output
