from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest
from click.testing import CliRunner

from sirna_offtarget.cli import main
from sirna_offtarget.config import ExpressionConfig, ProviderSelectionConfig
from sirna_offtarget.contracts.artifacts import ArtifactReference
from sirna_offtarget.contracts.base import StageContract
from sirna_offtarget.expression.api import analyze_expression_with_config
from sirna_offtarget.expression.backends.precomputed import (
    LegacyExpressionPathNotSupportedError,
    PrecomputedDifferentialExpressionBackend,
)
from sirna_offtarget.identifiers.detect import detect_identifier_type as legacy_detect
from sirna_offtarget.models import Direction
from sirna_offtarget.pathway.directed_paths import build_directed_graph, shortest_directed_path
from sirna_offtarget.pathway.direction_consistency import (
    expected_direction_after_target_decrease,
    is_direction_consistent,
    sign_to_int,
)
from sirna_offtarget.pathway.providers.cache import (
    latest_snapshot_dir,
    read_jsonl,
    require_valid_cache,
    to_jsonable,
    verify_cache,
)
from sirna_offtarget.pathway.providers.evidence_quality import evaluate_evidence_quality
from sirna_offtarget.pathway.providers.exceptions import (
    PathwayProviderError,
    ProviderSnapshotError,
)
from sirna_offtarget.pathway.providers.http import fetch_bytes
from sirna_offtarget.pathway.providers.loaders import (
    provider_mode_requires_cache,
    resolve_provider_snapshots,
    summarize_provider_snapshots,
)
from sirna_offtarget.pathway.providers.models import ProviderEdgeEvidenceRecord
from sirna_offtarget.pathway.providers.normalization import (
    build_consensus_edges,
    deduplicate_lineage,
    infer_identifier_type,
    lineage_key,
    normalize_identifier,
    normalize_sign,
)
from sirna_offtarget.reporting.artifact_catalog import committed_artifact_catalog
from sirna_offtarget.reporting.report_links import relative_link

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "examples/synthetic/config.yaml"


def test_provider_db_cli_verify_inspect_and_renormalize(tmp_path: Path) -> None:
    runner = CliRunner()
    cache_dir = tmp_path / "cache"
    fetch = runner.invoke(
        main,
        [
            "pathway-db",
            "fetch",
            "--config",
            str(CONFIG),
            "--providers",
            "panther",
            "--cache-dir",
            str(cache_dir),
        ],
    )
    assert fetch.exit_code == 0, fetch.output
    inspect = runner.invoke(main, ["pathway-db", "inspect", "--cache-dir", str(cache_dir)])
    assert inspect.exit_code == 0, inspect.output
    verify = runner.invoke(main, ["pathway-db", "verify", "--cache-dir", str(cache_dir)])
    assert verify.exit_code == 0, verify.output
    snapshot = latest_snapshot_dir(cache_dir, "panther")
    assert snapshot is not None
    renorm = runner.invoke(
        main,
        [
            "pathway-db",
            "renormalize",
            "--provider",
            "panther",
            "--snapshot-id",
            snapshot.name,
            "--normalization-schema-version",
            "provider-cache-v2",
            "--cache-dir",
            str(cache_dir),
        ],
    )
    assert renorm.exit_code == 0, renorm.output
    assert "verified" in renorm.output


def test_precomputed_expression_backend_and_error_paths(tmp_path: Path) -> None:
    table = tmp_path / "de.tsv"
    table.write_text(
        "gene\tbaseMean\tlog2FoldChange\tlfcShrink\tlfcSE\tpvalue\tpadj\n"
        "A\t20\t1.5\t1.1\t0.2\t0.01\t0.02\n"
        "B\t2\t-0.8\t\t\t\t0.5\n"
    )
    config = ExpressionConfig(
        backend="precomputed",
        count_matrix=tmp_path / "counts.tsv",
        sample_metadata=tmp_path / "samples.tsv",
        precomputed_table=table,
    )
    with pytest.raises(LegacyExpressionPathNotSupportedError):
        analyze_expression_with_config(pd.DataFrame(), pd.DataFrame(), config)
    backend = PrecomputedDifferentialExpressionBackend.from_config(config)
    with pytest.raises(LegacyExpressionPathNotSupportedError):
        backend.run(pd.DataFrame(), pd.DataFrame())
    with pytest.raises(ValueError):
        analyze_expression_with_config(
            pd.DataFrame(),
            pd.DataFrame(),
            ExpressionConfig(
                backend="precomputed",
                count_matrix=tmp_path / "counts.tsv",
                sample_metadata=tmp_path / "samples.tsv",
            ),
        )
    bad = tmp_path / "bad.tsv"
    bad.write_text("gene\tbaseline_expression\tadjusted_p_value\nA\t1\t0.1\n")
    with pytest.raises(LegacyExpressionPathNotSupportedError):
        PrecomputedDifferentialExpressionBackend(bad).run(pd.DataFrame(), pd.DataFrame())


def test_cache_http_reporting_and_path_helpers(tmp_path: Path) -> None:
    source = tmp_path / "payload.json"
    source.write_text(json.dumps({"ok": True}))
    response = fetch_bytes(
        url=source.as_uri(),
        timeout_seconds=1,
        retry_count=0,
        expected_content_type=None,
    )
    assert response.status_code == 200
    assert json.loads(response.body.decode()) == {"ok": True}
    with pytest.raises(PathwayProviderError):
        fetch_bytes(url="", timeout_seconds=1, retry_count=0, expected_content_type=None)
    with pytest.raises(PathwayProviderError):
        fetch_bytes(
            url=(tmp_path / "missing.json").as_uri(),
            timeout_seconds=1,
            retry_count=1,
            expected_content_type=None,
        )
    empty = tmp_path / "empty.json"
    empty.write_text("")
    with pytest.raises(PathwayProviderError):
        fetch_bytes(
            url=empty.as_uri(),
            timeout_seconds=1,
            retry_count=0,
            expected_content_type=None,
        )
    with pytest.raises(PathwayProviderError):
        fetch_bytes(
            url=source.as_uri(),
            timeout_seconds=1,
            retry_count=0,
            expected_content_type="application/xml",
        )
    assert read_jsonl(tmp_path / "missing.jsonl") == []
    assert verify_cache(tmp_path) == []
    require_valid_cache(tmp_path)
    assert to_jsonable({"path": tmp_path}) == {"path": str(tmp_path)}
    graph = build_directed_graph(
        pd.DataFrame(
            [
                {"source": "A", "target": "B", "sign": "positive"},
                {"source": "B", "target": "C", "sign": "negative"},
            ]
        )
    )
    assert shortest_directed_path(graph, "A", "C", 2) == ["A", "B", "C"]
    assert shortest_directed_path(graph, "A", "C", 1) is None
    assert shortest_directed_path(graph, "A", "Z", 2) is None
    assert is_direction_consistent("positive", Direction.DOWN)
    assert is_direction_consistent("negative", Direction.UP)
    assert not is_direction_consistent("positive", Direction.UP)
    assert sign_to_int("negative") == -1
    assert sign_to_int("unknown") is None
    assert expected_direction_after_target_decrease(1).value == "down"
    assert expected_direction_after_target_decrease(-1).value == "up"
    assert expected_direction_after_target_decrease(None) is None


def test_identifier_normalization_and_lineage_dedup_branches() -> None:
    assert legacy_detect("ENST00000367770.8") == "ensembl_transcript_id"
    assert legacy_detect("ENSG00000141510.15") == "ensembl_gene_id"
    assert legacy_detect("123") == "entrez_gene_id"
    assert legacy_detect("P04637") == "uniprot_accession"
    assert legacy_detect("TP53") == "hgnc_symbol"
    assert legacy_detect("R-HSA-1234") == "reactome_stable_id"
    assert legacy_detect("SIGNOR-X1") == "signor_entity_id"
    assert legacy_detect("provider:123") == "provider_specific_id"
    assert infer_identifier_type("P04637") == "uniprot_accession"
    invalid = normalize_identifier(
        "",
        organism="human",
        mapping_provider="test",
        database_version="v1",
        snapshot_id="s1",
    )
    assert invalid.mapping_status == "invalid"
    ambiguous = normalize_identifier(
        "OLD",
        organism="human",
        mapping_provider="test",
        database_version="v1",
        snapshot_id="s1",
        aliases={"OLD": ("A", "B")},
    )
    assert ambiguous.mapping_status == "ambiguous"
    assert normalize_sign(True, inhibition=True) == "conflicting"
    assert normalize_sign(True) == "positive"
    assert normalize_sign(False, inhibition=True) == "negative"
    assert normalize_sign(False) == "unknown"
    assert normalize_sign("both") == "conflicting"
    assert normalize_sign("functional") == "unsigned"
    assert normalize_sign("?") == "unknown"
    assert lineage_key("a", "b", "activation", "positive", "db", "pmid")
    edge = _edge(lineage_key="same", access_route="a", references=("PMID1",))
    duplicate = _edge(lineage_key="same", access_route="b", references=("PMID2",))
    merged = deduplicate_lineage([edge, duplicate])
    assert len(merged) == 1
    assert merged[0].references == ("PMID1", "PMID2")
    predicted = evaluate_evidence_quality(
        _edge(sign="unknown", directed=False, predicted_only=True, references=())
    )
    assert predicted.predicted_penalty == 2.0
    consensus = build_consensus_edges(
        [
            _edge(source="A", target="B", sign="positive", lineage_key="p"),
            _edge(source="A", target="B", sign="negative", lineage_key="n"),
            _edge(source="C", target="D", sign="unsigned", lineage_key="u"),
            _edge(source="E", target="F", sign="unknown", lineage_key="x"),
        ]
    )
    assert [edge.consensus_sign for edge in consensus] == [
        "conflicting",
        "unsigned",
        "unknown",
    ]


def test_provider_loader_mode_branches(tmp_path: Path) -> None:
    selected, warnings = resolve_provider_snapshots(tmp_path, {}, ["omnipath"])
    assert selected == ["omnipath"]
    assert warnings == []
    selected, warnings = resolve_provider_snapshots(
        tmp_path,
        {"omnipath": ProviderSelectionConfig(mode="public_cache", required=False)},
        ["omnipath"],
    )
    assert selected == []
    assert warnings
    with pytest.raises(ProviderSnapshotError):
        resolve_provider_snapshots(
            tmp_path,
            {"omnipath": ProviderSelectionConfig(mode="public_fetch")},
            ["omnipath"],
        )
    with pytest.raises(ProviderSnapshotError):
        resolve_provider_snapshots(
            tmp_path,
            {"omnipath": ProviderSelectionConfig(mode="mystery")},
            ["omnipath"],
        )
    assert provider_mode_requires_cache({}, "public_cache")
    summary = summarize_provider_snapshots(tmp_path, ["omnipath"], ["missing"])
    assert summary["warnings"] == ["missing"]


def test_artifact_catalog_and_relative_links(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    output = run_dir / "outputs" / "result.txt"
    output.parent.mkdir(parents=True)
    output.write_text("hello")
    contract = StageContract(
        contract_name="StageContract",
        schema_version="1",
        stage_name="stage",
        stage_version="1",
        run_id="run",
        attempt_number=1,
        artifacts=[
            ArtifactReference(
                logical_name="result",
                relative_path="outputs/result.txt",
                media_type="text/plain",
                schema_name=None,
                schema_version=None,
                sha256="old",
                size_bytes=1,
                created_by_stage="stage",
                created_by_attempt=1,
                required=True,
                description="demo",
            )
        ],
        payload={"ok": True},
    )
    rows = committed_artifact_catalog(run_dir, contract)
    assert rows[0]["size_bytes"] == 5
    assert relative_link(run_dir, output) == "outputs/result.txt"
    assert relative_link(output.parent, tmp_path / "outside.txt").endswith("outside.txt")


def _edge(**overrides: object) -> ProviderEdgeEvidenceRecord:
    values = {
        "evidence_id": "ev1",
        "provider": "signor",
        "access_route": "api",
        "source": "A",
        "target": "B",
        "source_identifier": "A",
        "target_identifier": "B",
        "directed": True,
        "sign": "positive",
        "relation_type": "activation",
        "mechanism": "curated",
        "functional_only": False,
        "causal_eligible": True,
        "original_sources": ("SIGNOR",),
        "references": ("PMID1",),
        "organism": "human",
        "evidence_level": "curated",
        "provider_record_id": "r1",
        "database_version": "v1",
        "retrieval_snapshot": "s1",
        "predicted_only": False,
        "lineage_key": "l1",
        "warnings": (),
    }
    values.update(overrides)
    return ProviderEdgeEvidenceRecord(**values)
