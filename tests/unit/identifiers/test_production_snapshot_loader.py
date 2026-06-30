from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from sirna_offtarget.cli import main
from sirna_offtarget.identifiers.snapshots import (
    build_identifier_snapshot_from_resources,
    verify_identifier_cache,
)

ROOT = Path(__file__).resolve().parents[3]
CONFIG = ROOT / "examples/synthetic/config.yaml"


def test_build_identifier_snapshot_from_user_resources(tmp_path: Path) -> None:
    resource = tmp_path / "identifiers.tsv"
    resource.write_text(
        "\t".join(
            [
                "input_identifier",
                "identifier_type",
                "canonical_gene_id",
                "canonical_symbol",
                "aliases",
                "previous_symbols",
                "ambiguous",
                "candidate_mappings",
            ]
        )
        + "\n"
        + "P53\thgnc_alias\tHGNC:11998\tTP53\tP53\tBCC7\tfalse\t\n"
        + "OLD1\thgnc_symbol\t\t\t\tOLD1\ttrue\tGENEA;GENEB\n"
    )
    snapshot = build_identifier_snapshot_from_resources(tmp_path / "cache", "human", [resource])
    assert (snapshot / "identifier_entities.tsv").exists()
    assert (snapshot / "identifier_aliases.tsv").read_text().count("P53") >= 1
    assert "OLD1" in (snapshot / "identifier_deprecated.tsv").read_text()
    assert "GENEA;GENEB" in (snapshot / "identifier_ambiguities.tsv").read_text()
    manifest = json.loads((snapshot / "identifier_snapshot_manifest.json").read_text())
    assert manifest["record_count"] == 2
    assert manifest["ambiguity_count"] == 1
    assert verify_identifier_cache(tmp_path / "cache") == []


def test_identifier_db_build_cli(tmp_path: Path) -> None:
    resource = tmp_path / "identifiers.tsv"
    resource.write_text(
        "input_identifier\tidentifier_type\tcanonical_gene_id\tcanonical_symbol\n"
        "ENSG00000141510\tensembl_gene_id\tHGNC:11998\tTP53\n"
    )
    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "identifier-db",
            "build",
            "--config",
            str(CONFIG),
            "--inputs",
            str(resource),
            "--cache-dir",
            str(tmp_path / "cache"),
        ],
    )
    assert result.exit_code == 0, result.output
    assert "snapshot_dir" in result.output
