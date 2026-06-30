import json
from pathlib import Path

from sirna_offtarget.transcript_targetability_ratio.artifacts import (
    verify_transcript_targetability_ratio_outputs,
    write_transcript_targetability_ratio_artifacts,
)
from sirna_offtarget.transcript_targetability_ratio.contracts import (
    TargetableTranscriptInclusionPolicyV1,
    TranscriptTargetabilityRatioRunRecordV1,
)
from tests.unit.transcript_targetability_ratio.helpers import compute, evidence, site, weight


def _write_outputs(tmp_path: Path) -> Path:
    computed = compute(
        [weight("G1", "TX1", 2), weight("G1", "TX2", 2)],
        [evidence("G1", "TX1"), evidence("G1", "TX2")],
        [site("G1", "TX1", "s1")],
    )
    write_transcript_targetability_ratio_artifacts(
        output_dir=tmp_path,
        run_record=TranscriptTargetabilityRatioRunRecordV1(
            run_id="run",
            isoform_uncertainty_result_id="iu",
            isoform_uncertainty_checksum="iu-sha",
            transcript_targetability_result_id="tt",
            transcript_targetability_checksum="tt-sha",
            inclusion_policy_id="targetable-transcript-inclusion-v1-cleavage-compatible",
            inclusion_policy_checksum="policy-sha",
            started_at="2026-06-27T00:00:00Z",
            completed_at="2026-06-27T00:00:01Z",
            status="completed",
            verification_status="verified",
        ),
        inclusion_policy=TargetableTranscriptInclusionPolicyV1(),
        gene_ratios=computed.gene_ratios,
        contributions=computed.contributions,
        unresolved=computed.unresolved,
        summary=computed.summary,
        warnings=[],
    )
    return tmp_path


def test_verifier_recomputes_ratio_artifact_counts(tmp_path: Path) -> None:
    output_dir = _write_outputs(tmp_path)
    assert verify_transcript_targetability_ratio_outputs(output_dir)["passed"]


def test_verifier_rejects_seed_only_qualified_corruption(tmp_path: Path) -> None:
    output_dir = _write_outputs(tmp_path)
    path = output_dir / "transcript_m_contributions_v1.jsonl"
    rows = path.read_text().splitlines()
    rows[0] = rows[0].replace(
        '"qualifying_evidence_class": "exact_full_length_complement"',
        '"qualifying_evidence_class": "seed_only_candidate"',
    )
    path.write_text("\n".join(rows) + "\n")
    verification = verify_transcript_targetability_ratio_outputs(output_dir)
    assert not verification["passed"]
    assert any("seed_only_exclusion_checks" in error for error in verification["errors"])


def test_verifier_rejects_count_and_ratio_corruption(tmp_path: Path) -> None:
    output_dir = _write_outputs(tmp_path)
    path = output_dir / "gene_transcript_targetability_ratios_v1.jsonl"
    row = json.loads(path.read_text().splitlines()[0])
    row["m_targetable_transcripts"] = 3
    row["ratio_m_over_n"] = 1.5
    row["qualifying_equal_prior_weight_sum"] = 0.25
    row["unresolved_transcript_ids"] = ["TX2"]
    row["unresolved_transcript_count"] = 1
    path.write_text(json.dumps(row, sort_keys=True) + "\n")
    verification = verify_transcript_targetability_ratio_outputs(output_dir)
    assert not verification["passed"]
    assert any("m_count_checks" in error for error in verification["errors"])
    assert any("ratio_arithmetic_checks" in error for error in verification["errors"])
    assert any("equal_prior_weight_checks" in error for error in verification["errors"])


def test_verifier_rejects_bad_contribution_and_checksum(tmp_path: Path) -> None:
    output_dir = _write_outputs(tmp_path)
    path = output_dir / "transcript_m_contributions_v1.jsonl"
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    rows[0]["contribution_to_n"] = 2
    rows[0]["contribution_to_m"] = 7
    rows.append(rows[0] | {"contribution_record_id": "duplicate"})
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows))
    verification = verify_transcript_targetability_ratio_outputs(output_dir)
    assert not verification["passed"]
    assert any("n_count_checks" in error for error in verification["errors"])
    assert any("unique_transcript_checks" in error for error in verification["errors"])
    assert any("artifact_reference_checks" in error for error in verification["errors"])


def test_verifier_handles_unreadable_artifact(tmp_path: Path) -> None:
    output_dir = _write_outputs(tmp_path)
    (output_dir / "transcript_targetability_ratio_summary_v1.json").write_text("{")
    verification = verify_transcript_targetability_ratio_outputs(output_dir)
    assert not verification["passed"]
    assert any(error.startswith("unreadable:") for error in verification["errors"])


def test_verifier_rejects_missing_required_artifact(tmp_path: Path) -> None:
    output_dir = _write_outputs(tmp_path)
    (output_dir / "transcript_targetability_ratio_unresolved_v1.jsonl").unlink()
    verification = verify_transcript_targetability_ratio_outputs(output_dir)
    assert not verification["passed"]
    assert any(
        error == "missing:transcript_targetability_ratio_unresolved_v1.jsonl"
        for error in verification["errors"]
    )
    assert any(error.startswith("unreadable:") for error in verification["errors"])


def test_verifier_rejects_duplicate_gene_ratio_records(tmp_path: Path) -> None:
    output_dir = _write_outputs(tmp_path)
    path = output_dir / "gene_transcript_targetability_ratios_v1.jsonl"
    row = path.read_text().splitlines()[0]
    path.write_text(f"{row}\n{row}\n")
    verification = verify_transcript_targetability_ratio_outputs(output_dir)
    assert not verification["passed"]
    assert any("duplicate_gene_ratio" in error for error in verification["errors"])
    assert any(
        "count_reconciliation_checks:genes_examined" in error for error in verification["errors"]
    )


def test_verifier_rejects_transcript_set_and_result_count_corruption(tmp_path: Path) -> None:
    output_dir = _write_outputs(tmp_path)
    ratio_path = output_dir / "gene_transcript_targetability_ratios_v1.jsonl"
    ratio = json.loads(ratio_path.read_text().splitlines()[0])
    ratio["eligible_transcript_ids"] = ["TX1"]
    ratio["n_total_eligible_transcripts"] = 9
    ratio["qualifying_transcript_ids"] = ["TX2"]
    ratio["observed_qualifying_transcript_count"] = 2
    ratio["seed_only_transcript_ids"] = ["TX2"]
    ratio["m_targetable_transcripts"] = 10
    ratio_path.write_text(json.dumps(ratio, sort_keys=True) + "\n")

    result_path = output_dir / "transcript_targetability_ratio_result_v1.json"
    result = json.loads(result_path.read_text())
    result["counts"]["genes_examined"] = 99
    result_path.write_text(json.dumps(result, sort_keys=True) + "\n")

    verification = verify_transcript_targetability_ratio_outputs(output_dir)
    assert not verification["passed"]
    assert any("transcript_set_checks" in error for error in verification["errors"])
    assert any("n_count_checks" in error for error in verification["errors"])
    assert any("m_count_checks" in error for error in verification["errors"])
    assert any("seed_only_exclusion_checks" in error for error in verification["errors"])
    assert any(
        error == "count_reconciliation_checks:result_counts" for error in verification["errors"]
    )


def test_verifier_rejects_unverified_run_and_unresolved_record_mismatch(tmp_path: Path) -> None:
    output_dir = _write_outputs(tmp_path)
    run_path = output_dir / "transcript_targetability_ratio_run_v1.json"
    run = json.loads(run_path.read_text())
    run["verification_status"] = "pending"
    run_path.write_text(json.dumps(run, sort_keys=True) + "\n")

    summary_path = output_dir / "transcript_targetability_ratio_summary_v1.json"
    summary = json.loads(summary_path.read_text())
    summary["total_unresolved_transcripts"] = 1
    summary_path.write_text(json.dumps(summary, sort_keys=True) + "\n")

    verification = verify_transcript_targetability_ratio_outputs(output_dir)
    assert not verification["passed"]
    assert any(
        error == "artifact_reference_checks:run_not_verified" for error in verification["errors"]
    )
    assert any(
        error == "count_reconciliation_checks:unresolved_records"
        for error in verification["errors"]
    )
