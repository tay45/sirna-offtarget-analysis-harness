from __future__ import annotations

from pathlib import Path

from sirna_offtarget.execution.hashing import dump_json
from sirna_offtarget.execution.runner import _verify_mechanistic_v2_payload


def _write_payload(attempt_dir: Path, payload: dict[str, object]) -> None:
    output_dir = attempt_dir / "committed" / "outputs"
    output_dir.mkdir(parents=True)
    dump_json(output_dir / "stage_result.payload.json", {"payload": payload})


def test_verify_mechanistic_v2_payload_accepts_linked_metrics(tmp_path: Path) -> None:
    attempt_dir = tmp_path / "attempt_001"
    payload = {
        "signed_paths": [
            {
                "path_id": "path-1",
                "search_result_id": "search-1",
                "source_entity_id": "gene:A",
                "target_entity_id": "gene:B",
                "graph_layer": "signed_causal",
            }
        ],
        "unsigned_context_paths": [],
        "path_search_results": [
            {
                "search_result_id": "search-1",
                "source_entity_id": "gene:A",
                "target_entity_id": "gene:B",
                "graph_layer": "signed_causal",
                "retained_path_ids": ["path-1"],
            }
        ],
        "consensus_edges": [{"edge_id": "edge-1"}],
        "provider_evidence": [{"evidence_id": "ev-1"}],
        "metrics": {
            "signed_path_count": 1,
            "unsigned_context_path_count": 0,
            "total_canonical_path_count": 1,
            "path_search_result_count": 1,
            "consensus_edge_count": 1,
            "provider_evidence_count": 1,
        },
    }
    _write_payload(attempt_dir, payload)

    assert _verify_mechanistic_v2_payload(attempt_dir) == []


def test_verify_mechanistic_v2_payload_rejects_bad_links_and_metrics(
    tmp_path: Path,
) -> None:
    attempt_dir = tmp_path / "attempt_001"
    payload = {
        "signed_paths": [
            {
                "path_id": "path-1",
                "search_result_id": "missing-search",
                "source_entity_id": "gene:A",
                "target_entity_id": "gene:B",
                "graph_layer": "signed_causal",
                "truncation_status": "complete",
            }
        ],
        "unsigned_context_paths": [],
        "path_search_results": [
            {
                "search_result_id": "search-1",
                "source_entity_id": "gene:A",
                "target_entity_id": "gene:C",
                "graph_layer": "signed_causal",
                "retained_path_ids": ["missing-path"],
            }
        ],
        "consensus_edges": [],
        "provider_evidence": [],
        "metrics": {"total_canonical_path_count": 99},
    }
    _write_payload(attempt_dir, payload)

    errors = _verify_mechanistic_v2_payload(attempt_dir)

    assert any("references missing search result" in error for error in errors)
    assert any("references missing child path" in error for error in errors)
    assert any("metric total_canonical_path_count=99 expected 1" in error for error in errors)
