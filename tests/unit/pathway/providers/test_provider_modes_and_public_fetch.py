from __future__ import annotations

import json
from pathlib import Path

import pytest

from sirna_offtarget.config import ProviderSelectionConfig, load_config
from sirna_offtarget.pathway.providers.exceptions import ProviderSnapshotError
from sirna_offtarget.pathway.providers.fetch import fetch_pathway_cache
from sirna_offtarget.pathway.providers.loaders import (
    load_enrichment_records,
    load_provider_edge_evidence,
    provider_mode_requires_cache,
    resolve_provider_snapshots,
    summarize_provider_snapshots,
)

ROOT = Path(__file__).resolve().parents[4]
CONFIG = ROOT / "examples/synthetic/config.yaml"


def test_public_fetch_reads_configured_endpoint_without_analysis_network(tmp_path: Path) -> None:
    payload = [
        {
            "gene": "TP53",
            "pathway_id": "P00001",
            "pathway_name": "p53 pathway",
            "matched_genes": "TP53",
            "number_in_list": 1,
            "expected": 0.25,
            "fold_enrichment": 4.0,
            "pValue": 0.01,
            "fdr": 0.02,
            "dataset": "PANTHER_PATHWAY",
        }
    ]
    endpoint = tmp_path / "panther.json"
    endpoint.write_text(json.dumps(payload))
    config = load_config(CONFIG)
    config.providers["panther"] = ProviderSelectionConfig(
        mode="public_fetch",
        endpoint=endpoint.as_uri(),
        expected_content_type=None,
    )
    manifest = fetch_pathway_cache(config, ["panther"], tmp_path / "cache")
    assert manifest["providers"][0]["provider"] == "panther"
    manifest_path = next((tmp_path / "cache").glob("panther/*/provider_manifest.json"))
    assert json.loads(manifest_path.read_text())["endpoint"] == endpoint.as_uri()


def test_public_cache_mode_requires_verified_snapshot(tmp_path: Path) -> None:
    config = {"omnipath": ProviderSelectionConfig(mode="public_cache", required=True)}
    assert provider_mode_requires_cache(config, "local_snapshot")
    with pytest.raises(ProviderSnapshotError):
        resolve_provider_snapshots(tmp_path, config, ["omnipath"])


def test_disabled_provider_is_not_selected(tmp_path: Path) -> None:
    selected, warnings = resolve_provider_snapshots(
        tmp_path,
        {"omnipath": ProviderSelectionConfig(mode="disabled")},
        ["omnipath"],
    )
    assert selected == []
    assert warnings == []


def test_provider_snapshot_resolution_covers_optional_cache_and_defaults(tmp_path: Path) -> None:
    selected, warnings = resolve_provider_snapshots(tmp_path, {}, ["omnipath"])
    assert selected == ["omnipath"]
    assert warnings == []

    selected, warnings = resolve_provider_snapshots(
        tmp_path,
        {"omnipath": ProviderSelectionConfig(mode="public_cache", required=False)},
        ["omnipath"],
    )
    assert selected == []
    assert warnings == ["required provider cache missing or invalid: omnipath"]

    snapshot = tmp_path / "omnipath" / "snapshot-a"
    snapshot.mkdir(parents=True)
    (snapshot / ".verified").write_text("verified\n")
    selected, warnings = resolve_provider_snapshots(
        tmp_path,
        {"omnipath": ProviderSelectionConfig(mode="public_cache", required=False)},
        ["omnipath"],
    )
    assert selected == ["omnipath"]
    assert warnings == []
    assert provider_mode_requires_cache({}, "public_cache")
    assert summarize_provider_snapshots(tmp_path, ["omnipath"])["snapshots"] == [
        {
            "provider": "omnipath",
            "snapshot_path": str(snapshot),
            "verified": True,
        }
    ]


def test_provider_snapshot_resolution_rejects_analysis_time_public_fetch(tmp_path: Path) -> None:
    with pytest.raises(ProviderSnapshotError, match="public_fetch during analysis"):
        resolve_provider_snapshots(
            tmp_path,
            {"omnipath": ProviderSelectionConfig(mode="public_fetch")},
            ["omnipath"],
        )


def test_provider_loaders_skip_missing_snapshots_and_load_current_records(tmp_path: Path) -> None:
    assert load_provider_edge_evidence(tmp_path, ["omnipath"]) == []
    assert load_enrichment_records(tmp_path, ["panther"]) == []

    edge_snapshot = tmp_path / "omnipath" / "snapshot-a" / "normalized"
    edge_snapshot.mkdir(parents=True)
    (edge_snapshot / "records.jsonl").write_text(
        json.dumps(
            {
                "evidence_id": "e1",
                "provider": "omnipath",
                "access_route": "cache",
                "source": "A",
                "target": "B",
                "source_identifier": "A",
                "target_identifier": "B",
                "directed": True,
                "sign": "positive",
                "relation_type": "activation",
                "mechanism": "pathway",
                "functional_only": False,
                "causal_eligible": True,
                "original_sources": ["OmniPath"],
                "references": ["PMID1"],
                "organism": "human",
                "evidence_level": "curated",
                "provider_record_id": "p1",
                "database_version": "v1",
                "retrieval_snapshot": "snapshot-a",
                "predicted_only": False,
                "lineage_key": "A>B",
                "warnings": [],
            },
            sort_keys=True,
        )
        + "\n"
    )
    edges = load_provider_edge_evidence(tmp_path, ["omnipath"])
    assert edges[0].source == "A"
    assert edges[0].target == "B"

    enrichment_snapshot = tmp_path / "panther" / "snapshot-b" / "normalized"
    enrichment_snapshot.mkdir(parents=True)
    (enrichment_snapshot / "records.jsonl").write_text(
        json.dumps(
            {
                "provider": "panther",
                "annotation_source": "PANTHER",
                "term_id": "P1",
                "term_name": "Pathway",
                "gene_set_category": "pathway",
                "expression_direction": "up",
                "observed_count": 1,
                "expected_count": 0.5,
                "fold_enrichment": 2.0,
                "raw_p_value": 0.1,
                "adjusted_p_value": 0.2,
                "matched_genes": ["A"],
                "submitted_gene_count": 1,
                "background_gene_count": 10,
                "tested_gene_universe": ["A", "B"],
                "organism": "human",
                "database_version": "v1",
                "retrieval_snapshot": "snapshot-b",
                "request_checksum": "abc",
                "response_checksum": "def",
                "warnings": [],
            },
            sort_keys=True,
        )
        + "\n"
    )
    records = load_enrichment_records(tmp_path, ["panther"])
    assert records[0].term_id == "P1"
