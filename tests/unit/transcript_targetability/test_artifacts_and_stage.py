from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from sirna_offtarget.contracts.registry import CONTRACT_REGISTRY, STAGE_CONTRACTS
from sirna_offtarget.execution.dag import STAGE_NODES, STAGE_ORDER, topological_sort
from sirna_offtarget.execution.stages import build_stages
from sirna_offtarget.transcript_targetability.artifacts import (
    verify_transcript_targetability_outputs,
    write_transcript_targetability_artifacts,
)
from sirna_offtarget.transcript_targetability.contracts import (
    CleavageCompatibilityPolicyV1,
    SeedMatchPolicyV1,
    TranscriptSequenceSnapshotV1,
    TranscriptTargetabilityRunRecordV1,
)
from sirna_offtarget.transcript_targetability.core import (
    find_transcript_targetability,
    sha256_text,
    validate_sirna_sequence,
)
from tests.unit.transcript_targetability.test_core import _transcript


def _records():
    sirna, sirna_validation = validate_sirna_sequence(
        sirna_id="sirna1",
        reagent_name="reagent1",
        guide_sequence="AAAAAAAAAAAAAAAAAAAAA",
        organism="human",
        assembly="GRCh38",
    )
    evidence, sites, mismatches, positions = find_transcript_targetability(
        sirna=sirna,
        transcript=_transcript(),
        transcript_prior_weight=1.0,
        source_isoform_uncertainty_record_id="gene-iu",
        source_transcript_weight_record_id="weight-1",
        transcript_sequence_snapshot_id="seq-snapshot",
    )
    run_record = TranscriptTargetabilityRunRecordV1(
        run_id="run1",
        sirna_sequence_record_id=sirna.sirna_id,
        guide_sequence_checksum=sha256_text(sirna.guide_sequence_normalized),
        isoform_uncertainty_result_id="iu-result",
        isoform_uncertainty_artifact_checksum="weights-checksum",
        transcript_sequence_snapshot_id="seq-snapshot",
        transcript_sequence_snapshot_checksum="seq-checksum",
        annotation_snapshot_id="annotation-snapshot",
        annotation_checksum="annotation-checksum",
        cleavage_policy_id="cleavage-compatibility-v1-conservative-ungapped",
        seed_policy_id="seed-match-v1-exact-seed-separate",
        organism="human",
        assembly="GRCh38",
        started_at="2026-06-27T00:00:00+00:00",
        completed_at="2026-06-27T00:00:01+00:00",
        status="completed",
        verification_status="verified",
    )
    return sirna, sirna_validation, [evidence], sites, mismatches, positions, run_record


def _snapshot() -> TranscriptSequenceSnapshotV1:
    return TranscriptSequenceSnapshotV1(
        snapshot_id="seq-snapshot",
        provider="unit",
        release="annotation-snapshot",
        organism="human",
        assembly="GRCh38",
        transcript_identifier_namespace="canonical_transcript_id",
        transcript_count=1,
        sequence_file_checksum="seq-checksum",
        verification_status="verified",
        generation_method="unit_test",
    )


def _sequence_records():
    return [_transcript()]


def _write_valid_artifact_set(output_dir: Path) -> None:
    sirna, sirna_validation, evidence, sites, mismatches, positions, run_record = _records()
    write_transcript_targetability_artifacts(
        output_dir=output_dir,
        sirna_sequence=sirna,
        sirna_validation=sirna_validation,
        sequence_validation={"schema_version": "1", "verification_status": "verified"},
        transcript_sequence_snapshot=_snapshot(),
        transcript_sequence_records=_sequence_records(),
        evidence_records=evidence,
        site_records=sites,
        mismatch_records=mismatches,
        alignment_position_records=positions,
        exclusions=[],
        policy_payload={
            "cleavage_policy": CleavageCompatibilityPolicyV1().model_dump(mode="json"),
            "seed_policy": SeedMatchPolicyV1().model_dump(mode="json"),
        },
        run_record=run_record,
    )


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows))


def test_targetability_artifacts_verify_and_do_not_include_forbidden_scope(tmp_path: Path) -> None:
    sirna, sirna_validation, evidence, sites, mismatches, positions, run_record = _records()
    result = write_transcript_targetability_artifacts(
        output_dir=tmp_path,
        sirna_sequence=sirna,
        sirna_validation=sirna_validation,
        sequence_validation={"schema_version": "1", "verification_status": "verified"},
        transcript_sequence_snapshot=_snapshot(),
        transcript_sequence_records=_sequence_records(),
        evidence_records=evidence,
        site_records=sites,
        mismatch_records=mismatches,
        alignment_position_records=positions,
        exclusions=[],
        policy_payload={
            "cleavage_policy": CleavageCompatibilityPolicyV1().model_dump(mode="json"),
            "seed_policy": SeedMatchPolicyV1().model_dump(mode="json"),
        },
        run_record=run_record,
    )
    verification = verify_transcript_targetability_outputs(tmp_path)
    assert verification["passed"]
    assert result.counts["eligible_transcripts_examined"] == 1
    assert "result" not in result.output_checksums
    result_json = json.loads((tmp_path / "transcript_targetability_result_v1.json").read_text())
    assert "expected direct decrease" not in json.dumps(result_json).lower()


def test_targetability_verifier_rejects_missing_and_count_mismatch(tmp_path: Path) -> None:
    sirna, sirna_validation, evidence, sites, mismatches, positions, run_record = _records()
    write_transcript_targetability_artifacts(
        output_dir=tmp_path,
        sirna_sequence=sirna,
        sirna_validation=sirna_validation,
        sequence_validation={"schema_version": "1", "verification_status": "verified"},
        transcript_sequence_snapshot=_snapshot(),
        transcript_sequence_records=_sequence_records(),
        evidence_records=evidence,
        site_records=sites,
        mismatch_records=mismatches,
        alignment_position_records=positions,
        exclusions=[],
        policy_payload={
            "cleavage_policy": CleavageCompatibilityPolicyV1().model_dump(mode="json"),
            "seed_policy": SeedMatchPolicyV1().model_dump(mode="json"),
        },
        run_record=run_record,
    )
    result_path = tmp_path / "transcript_targetability_result_v1.json"
    result_payload = json.loads(result_path.read_text())
    result_payload["counts"]["eligible_transcripts_examined"] = 99
    result_path.write_text(json.dumps(result_payload))
    verification = verify_transcript_targetability_outputs(tmp_path)
    assert "count_mismatch:eligible_transcripts_examined" in verification["errors"]

    result_payload["counts"]["eligible_transcripts_examined"] = 1
    result_payload["counts"]["total_qualifying_sites"] = 999
    result_path.write_text(json.dumps(result_payload))
    verification = verify_transcript_targetability_outputs(tmp_path)
    assert "count_mismatch:total_qualifying_sites" in verification["errors"]

    (tmp_path / "transcript_targetability_sites_v1.jsonl").unlink()
    verification = verify_transcript_targetability_outputs(tmp_path)
    assert "missing:transcript_targetability_sites_v1.jsonl" in verification["errors"]


def test_targetability_verifier_rejects_unreadable_result(tmp_path: Path) -> None:
    sirna, sirna_validation, evidence, sites, mismatches, positions, run_record = _records()
    write_transcript_targetability_artifacts(
        output_dir=tmp_path,
        sirna_sequence=sirna,
        sirna_validation=sirna_validation,
        sequence_validation={"schema_version": "1", "verification_status": "verified"},
        transcript_sequence_snapshot=_snapshot(),
        transcript_sequence_records=_sequence_records(),
        evidence_records=evidence,
        site_records=sites,
        mismatch_records=mismatches,
        alignment_position_records=positions,
        exclusions=[],
        policy_payload={
            "cleavage_policy": CleavageCompatibilityPolicyV1().model_dump(mode="json"),
            "seed_policy": SeedMatchPolicyV1().model_dump(mode="json"),
        },
        run_record=run_record,
    )
    (tmp_path / "transcript_targetability_result_v1.json").write_text("{")
    verification = verify_transcript_targetability_outputs(tmp_path)
    assert any(error.startswith("unreadable:") for error in verification["errors"])


def test_targetability_verifier_rejects_missing_site_reference_and_forbidden_scope(
    tmp_path: Path,
) -> None:
    sirna, sirna_validation, evidence, sites, mismatches, positions, run_record = _records()
    write_transcript_targetability_artifacts(
        output_dir=tmp_path,
        sirna_sequence=sirna,
        sirna_validation=sirna_validation,
        sequence_validation={"schema_version": "1", "verification_status": "verified"},
        transcript_sequence_snapshot=_snapshot(),
        transcript_sequence_records=_sequence_records(),
        evidence_records=[evidence[0].model_copy(update={"site_record_ids": ("missing-site",)})],
        site_records=sites,
        mismatch_records=mismatches,
        alignment_position_records=positions,
        exclusions=[],
        policy_payload={
            "cleavage_policy": CleavageCompatibilityPolicyV1().model_dump(mode="json"),
            "seed_policy": SeedMatchPolicyV1().model_dump(mode="json"),
        },
        run_record=run_record,
    )
    verification = verify_transcript_targetability_outputs(tmp_path)
    assert "artifact_reference_mismatch:TX1:missing-site" in verification["errors"]

    result_path = tmp_path / "transcript_targetability_result_v1.json"
    result_payload = json.loads(result_path.read_text())
    result_payload["targetable transcript count"] = "out of scope"
    result_path.write_text(json.dumps(result_payload))
    verification = verify_transcript_targetability_outputs(tmp_path)
    assert "forbidden_scope:targetable transcript count" in verification["errors"]


def test_targetability_verifier_rejects_corrupt_alignment_position(tmp_path: Path) -> None:
    _write_valid_artifact_set(tmp_path)
    positions_path = tmp_path / "transcript_targetability_alignment_positions_v1.jsonl"
    rows = _read_jsonl(positions_path)
    rows[0]["target_base"] = "C" if rows[0]["target_base"] != "C" else "A"
    _write_jsonl(positions_path, rows)

    verification = verify_transcript_targetability_outputs(tmp_path)
    assert any(error.startswith("alignment_position_mismatch:") for error in verification["errors"])


def test_targetability_verifier_rejects_corrupt_site_fields(tmp_path: Path) -> None:
    cases: list[tuple[str, str, Any]] = [
        ("site_coordinate_mismatch", "transcript_start", -1),
        ("site_coordinate_mismatch", "transcript_end", 999),
        ("guide_search_sequence_mismatch", "guide_search_sequence", "A" * 21),
        ("site_sequence_mismatch", "transcript_site_sequence", "T" * 20),
        ("mismatch_recomputation_mismatch", "mismatch_positions", [1]),
        ("mismatch_recomputation_mismatch", "total_mismatch_count", 1),
        ("paired_base_mismatch", "matched_base_count", 0),
        ("mismatch_region_mismatch", "seed_mismatch_count", 1),
        ("mismatch_region_mismatch", "central_mismatch_count", 1),
        ("mismatch_region_mismatch", "nonseed_mismatch_count", 1),
        ("evidence_class_mismatch", "evidence_class", "seed_only_candidate"),
        ("evidence_class_mismatch", "cleavage_compatibility_status", "not_cleavage_compatible"),
        ("evidence_class_mismatch", "seed_only_status", "seed_only_candidate"),
        ("ranking_mismatch", "ranking_tuple", [9, 9, 9, 9, 9]),
    ]
    for index, (expected_prefix, field, value) in enumerate(cases):
        case_dir = tmp_path / f"case-{index}"
        _write_valid_artifact_set(case_dir)
        sites_path = case_dir / "transcript_targetability_sites_v1.jsonl"
        rows = _read_jsonl(sites_path)
        rows[0][field] = value
        _write_jsonl(sites_path, rows)

        verification = verify_transcript_targetability_outputs(case_dir)
        assert any(error.startswith(f"{expected_prefix}:") for error in verification["errors"]), (
            expected_prefix
        )


def test_targetability_verifier_rejects_corrupt_mismatch_and_position_fields(
    tmp_path: Path,
) -> None:
    cases: list[tuple[str, str, str, Any]] = [
        (
            "alignment_position_mismatch",
            "transcript_targetability_alignment_positions_v1.jsonl",
            "guide_position",
            999,
        ),
        (
            "alignment_position_mismatch",
            "transcript_targetability_alignment_positions_v1.jsonl",
            "transcript_position",
            999,
        ),
        (
            "alignment_position_mismatch",
            "transcript_targetability_alignment_positions_v1.jsonl",
            "guide_base",
            "C",
        ),
        (
            "alignment_position_mismatch",
            "transcript_targetability_alignment_positions_v1.jsonl",
            "pairing_status",
            "mismatch",
        ),
        (
            "mismatch_detail_mismatch",
            "transcript_targetability_mismatches_v1.jsonl",
            "guide_position",
            10,
        ),
        (
            "mismatch_detail_mismatch",
            "transcript_targetability_mismatches_v1.jsonl",
            "guide_base",
            "C",
        ),
        (
            "mismatch_detail_mismatch",
            "transcript_targetability_mismatches_v1.jsonl",
            "target_paired_base",
            "C",
        ),
    ]
    for index, (expected_prefix, artifact_name, field, value) in enumerate(cases):
        case_dir = tmp_path / f"case-{index}"
        _write_valid_artifact_set(case_dir)
        path = case_dir / artifact_name
        rows = _read_jsonl(path)
        if not rows and artifact_name.endswith("mismatches_v1.jsonl"):
            if expected_prefix != "extra_mismatch_detail":
                sites_path = case_dir / "transcript_targetability_sites_v1.jsonl"
                sites = _read_jsonl(sites_path)
                sites[0]["transcript_site_sequence"] = "TATTTTTTTTTTTTTTTTTTT"
                sites[0]["matched_base_count"] = 20
                sites[0]["total_mismatch_count"] = 1
                sites[0]["seed_mismatch_count"] = 1
                sites[0]["mismatch_positions"] = [2]
                sites[0]["evidence_class"] = "partial_nonseed_match"
                sites[0]["cleavage_compatibility_status"] = "not_cleavage_compatible"
                sites[0]["ranking_tuple"] = [4, 1, 1, 0, sites[0]["transcript_start"]]
                _write_jsonl(sites_path, sites)
            positions = _read_jsonl(
                case_dir / "transcript_targetability_alignment_positions_v1.jsonl"
            )
            rows = [
                {
                    "schema_version": "1",
                    "mismatch_record_id": "synthetic-corrupt-mismatch",
                    "site_record_id": positions[0]["site_record_id"],
                    "guide_position": 2,
                    "target_position": 1,
                    "guide_base": "T",
                    "target_paired_base": "A",
                    "match_status": "mismatch",
                    "mismatch_region": "seed",
                    "mismatch_type": "T>A",
                    "seed_membership": True,
                    "central_region_membership": False,
                    "terminal_region_membership": False,
                }
            ]
        row_index = 0
        if field == "pairing_status":
            row_index = next(
                position for position, row in enumerate(rows) if row["pairing_status"] == "match"
            )
        rows[row_index][field] = value
        _write_jsonl(path, rows)

        verification = verify_transcript_targetability_outputs(case_dir)
        assert any(error.startswith(f"{expected_prefix}:") for error in verification["errors"]), (
            expected_prefix
        )


def test_transcript_targetability_stage_is_registered_after_isoform_uncertainty() -> None:
    ordered = topological_sort()
    assert STAGE_ORDER.index("isoform_uncertainty") < STAGE_ORDER.index("transcript_targetability")
    assert ordered.index("isoform_uncertainty") < ordered.index("transcript_targetability")
    assert STAGE_NODES["transcript_targetability"].data_dependencies == ("isoform_uncertainty",)
    assert "transcript_targetability" in build_stages()
    assert STAGE_CONTRACTS["transcript_targetability"].expected_contract_name == (
        "TranscriptTargetabilityResultV1"
    )
    assert "TranscriptTargetabilityResultV1" in CONTRACT_REGISTRY
