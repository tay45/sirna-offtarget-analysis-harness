from __future__ import annotations

from sirna_offtarget.secondary_evidence_integration.artifacts import (
    verify_secondary_evidence_integration_outputs,
    write_secondary_evidence_integration_artifacts,
)
from sirna_offtarget.secondary_evidence_integration.contracts import (
    SecondaryEvidenceIntegrationPolicyV1,
    SecondaryEvidenceIntegrationRunRecordV1,
)
from sirna_offtarget.secondary_evidence_integration.core import (
    compute_secondary_evidence_integration,
)
from tests.unit.secondary_evidence_integration.test_secondary_evidence_integration_core import (
    residual_record,
)


def test_secondary_evidence_integration_artifacts_verify(tmp_path) -> None:
    policy = SecondaryEvidenceIntegrationPolicyV1()
    computed = compute_secondary_evidence_integration(
        residual_attribution_records=[residual_record()],
        policy=policy,
        source_residual_attribution_checksum="abc123",
    )
    result = write_secondary_evidence_integration_artifacts(
        output_dir=tmp_path,
        run_record=SecondaryEvidenceIntegrationRunRecordV1(
            run_id="run-1",
            residual_attribution_result_id="residual-result-1",
            residual_attribution_checksum="residual-checksum",
            policy_id=policy.policy_id,
            policy_checksum=policy.fingerprint,
            started_at="2026-01-01T00:00:00+00:00",
            completed_at="2026-01-01T00:00:01+00:00",
            status="completed",
            source_counts={"gene_residual_attribution_evidence_records": 1},
            verification_status="verified",
        ),
        policy=policy,
        gene_evidence=computed.gene_evidence,
        unresolved=computed.unresolved,
        summary=computed.summary,
        warnings=computed.warnings,
    )
    verification = verify_secondary_evidence_integration_outputs(tmp_path)
    assert verification["passed"]
    assert result.counts["genes_with_secondary_evidence_integration"] == 1
    assert (tmp_path / "gene_secondary_evidence_integration_v1.tsv").exists()
    assert (tmp_path / "secondary_evidence_integration_unresolved_v1.tsv").exists()


def test_secondary_evidence_integration_verification_detects_tampering(tmp_path) -> None:
    policy = SecondaryEvidenceIntegrationPolicyV1()
    computed = compute_secondary_evidence_integration(
        residual_attribution_records=[residual_record()],
        policy=policy,
    )
    write_secondary_evidence_integration_artifacts(
        output_dir=tmp_path,
        run_record=SecondaryEvidenceIntegrationRunRecordV1(
            run_id="run-1",
            residual_attribution_result_id="residual-result-1",
            residual_attribution_checksum="residual-checksum",
            policy_id=policy.policy_id,
            policy_checksum=policy.fingerprint,
            started_at="2026-01-01T00:00:00+00:00",
            completed_at="2026-01-01T00:00:01+00:00",
            status="completed",
            verification_status="verified",
        ),
        policy=policy,
        gene_evidence=computed.gene_evidence,
        unresolved=computed.unresolved,
        summary=computed.summary,
        warnings=computed.warnings,
    )
    (tmp_path / "secondary_evidence_integration_summary_v1.json").write_text("{}\n")
    verification = verify_secondary_evidence_integration_outputs(tmp_path)
    assert not verification["passed"]
    assert any("count_reconciliation_checks" in error for error in verification["errors"])
