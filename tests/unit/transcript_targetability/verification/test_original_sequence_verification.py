from __future__ import annotations

import json
from pathlib import Path

from sirna_offtarget.transcript_targetability.artifacts import (
    verify_transcript_targetability_outputs,
)
from tests.unit.transcript_targetability.test_artifacts_and_stage import (
    _read_jsonl,
    _write_jsonl,
    _write_valid_artifact_set,
)


def _rewrite(path: Path, name: str, rows: list[dict[str, object]]) -> None:
    _write_jsonl(path / name, rows)


def test_verifier_loads_original_transcript_snapshot(tmp_path: Path) -> None:
    _write_valid_artifact_set(tmp_path)
    snapshot = json.loads((tmp_path / "transcript_sequence_snapshot_v1.json").read_text())
    snapshot["verification_status"] = "unverified"
    (tmp_path / "transcript_sequence_snapshot_v1.json").write_text(json.dumps(snapshot))

    verification = verify_transcript_targetability_outputs(tmp_path)

    assert "transcript_snapshot_reload_check:unverified" in verification["errors"]


def test_verifier_recomputes_transcript_checksum(tmp_path: Path) -> None:
    _write_valid_artifact_set(tmp_path)
    rows = _read_jsonl(tmp_path / "transcript_sequence_snapshot_records_v1.jsonl")
    rows[0]["sequence_checksum"] = "wrong"
    _rewrite(tmp_path, "transcript_sequence_snapshot_records_v1.jsonl", rows)

    verification = verify_transcript_targetability_outputs(tmp_path)

    assert any(
        error.startswith("transcript_sequence_checksum_mismatch:")
        for error in verification["errors"]
    )


def test_verifier_extracts_site_from_original_sequence(tmp_path: Path) -> None:
    _write_valid_artifact_set(tmp_path)
    rows = _read_jsonl(tmp_path / "transcript_targetability_sites_v1.jsonl")
    rows[0]["transcript_start"] = rows[0]["transcript_start"] + 1
    rows[0]["transcript_end"] = rows[0]["transcript_end"] + 1
    _rewrite(tmp_path, "transcript_targetability_sites_v1.jsonl", rows)

    verification = verify_transcript_targetability_outputs(tmp_path)

    assert any(error.startswith("site_sequence_mismatch:") for error in verification["errors"])


def test_verifier_rejects_coordinated_fake_site_records(tmp_path: Path) -> None:
    _write_valid_artifact_set(tmp_path)
    sites = _read_jsonl(tmp_path / "transcript_targetability_sites_v1.jsonl")
    positions = _read_jsonl(tmp_path / "transcript_targetability_alignment_positions_v1.jsonl")
    fake_sequence = "A" * sites[0]["alignment_length"]
    sites[0]["transcript_site_sequence"] = fake_sequence
    sites[0]["matched_base_count"] = 0
    sites[0]["total_mismatch_count"] = sites[0]["alignment_length"]
    sites[0]["mismatch_positions"] = list(range(1, sites[0]["alignment_length"] + 1))
    sites[0]["evidence_class"] = "unsupported_alignment"
    for row in positions:
        row["target_base"] = "A"
        row["pairing_status"] = "mismatch"
    _rewrite(tmp_path, "transcript_targetability_sites_v1.jsonl", sites)
    _rewrite(tmp_path, "transcript_targetability_alignment_positions_v1.jsonl", positions)

    verification = verify_transcript_targetability_outputs(tmp_path)

    assert any(error.startswith("site_sequence_mismatch:") for error in verification["errors"])


def test_verifier_recomputes_best_site_and_evidence_counts(tmp_path: Path) -> None:
    _write_valid_artifact_set(tmp_path)
    evidence = _read_jsonl(tmp_path / "transcript_targetability_evidence_v1.jsonl")
    evidence[0]["best_site_record_id"] = "fake-best"
    evidence[0]["exact_site_count"] = 99
    _rewrite(tmp_path, "transcript_targetability_evidence_v1.jsonl", evidence)

    verification = verify_transcript_targetability_outputs(tmp_path)

    assert any(error.startswith("best_site_mismatch:") for error in verification["errors"])
    assert any(error.startswith("evidence_count_mismatch:") for error in verification["errors"])
