from __future__ import annotations

import json

from sirna_offtarget.residual_attribution.artifacts import (
    verify_residual_attribution_outputs,
    write_residual_attribution_artifacts,
)
from sirna_offtarget.residual_attribution.contracts import (
    ResidualAttributionPolicyV1,
    ResidualAttributionRunRecordV1,
)
from sirna_offtarget.residual_attribution.core import compute_residual_attribution
from tests.unit.residual_attribution.test_residual_attribution_core import expected_record


def test_artifact_verification_recomputes_residual_boundaries(tmp_path) -> None:
    policy = ResidualAttributionPolicyV1()
    computed = compute_residual_attribution(
        expected_direct_effect_records=[expected_record(residual=0.2)],
        pathway_evidence_available=False,
        policy=policy,
    )
    write_residual_attribution_artifacts(
        output_dir=tmp_path,
        run_record=ResidualAttributionRunRecordV1(
            run_id="run-1",
            expected_direct_effect_result_id="ede-run",
            expected_direct_effect_checksum="ede-checksum",
            policy_id=policy.policy_id,
            policy_checksum=policy.fingerprint,
            started_at="2026-01-01T00:00:00Z",
            completed_at="2026-01-01T00:00:01Z",
            status="completed",
            verification_status="verified",
        ),
        policy=policy,
        gene_evidence=computed.gene_evidence,
        unresolved=computed.unresolved,
        summary=computed.summary,
        warnings=computed.warnings,
    )
    verification = verify_residual_attribution_outputs(tmp_path)
    assert verification["passed"]


def test_artifact_verification_detects_residual_mutation(tmp_path) -> None:
    policy = ResidualAttributionPolicyV1()
    computed = compute_residual_attribution(
        expected_direct_effect_records=[expected_record(residual=0.2)],
        pathway_evidence_available=True,
        policy=policy,
    )
    write_residual_attribution_artifacts(
        output_dir=tmp_path,
        run_record=ResidualAttributionRunRecordV1(
            run_id="run-1",
            expected_direct_effect_result_id="ede-run",
            expected_direct_effect_checksum="ede-checksum",
            policy_id=policy.policy_id,
            policy_checksum=policy.fingerprint,
            started_at="2026-01-01T00:00:00Z",
            completed_at="2026-01-01T00:00:01Z",
            status="completed",
            verification_status="verified",
        ),
        policy=policy,
        gene_evidence=computed.gene_evidence,
        unresolved=computed.unresolved,
        summary=computed.summary,
        warnings=computed.warnings,
    )
    path = tmp_path / "gene_residual_attribution_evidence_v1.jsonl"
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    rows[0]["residual_abs_log2"] = 999
    path.write_text("\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n")
    verification = verify_residual_attribution_outputs(tmp_path)
    assert not verification["passed"]
    assert any("residual_preservation_checks:abs" in error for error in verification["errors"])


def test_missing_required_artifact_fails_verification(tmp_path) -> None:
    assert not verify_residual_attribution_outputs(tmp_path)["passed"]
