from __future__ import annotations

from sirna_offtarget.final_evidence_classification.artifacts import (
    verify_final_evidence_classification_outputs,
    write_final_evidence_classification_artifacts,
)
from sirna_offtarget.final_evidence_classification.contracts import (
    FinalEvidenceClassificationPolicyV1,
    FinalEvidenceClassificationRunRecordV1,
)
from sirna_offtarget.final_evidence_classification.core import (
    compute_final_evidence_classification,
)
from tests.unit.final_evidence_classification.test_final_evidence_classification_core import (
    integrated_record,
)


def test_final_evidence_classification_artifacts_verify(tmp_path) -> None:
    policy = FinalEvidenceClassificationPolicyV1()
    computed = compute_final_evidence_classification(
        secondary_evidence_records=[integrated_record()],
        policy=policy,
        source_secondary_evidence_integration_checksum="abc123",
    )
    result = write_final_evidence_classification_artifacts(
        output_dir=tmp_path,
        run_record=FinalEvidenceClassificationRunRecordV1(
            run_id="run-1",
            secondary_evidence_integration_result_id="secondary-result-1",
            secondary_evidence_integration_checksum="secondary-checksum",
            policy_id=policy.policy_id,
            policy_checksum=policy.fingerprint,
            started_at="2026-01-01T00:00:00+00:00",
            completed_at="2026-01-01T00:00:01+00:00",
            status="completed",
            source_counts={"gene_secondary_evidence_integration_records": 1},
            verification_status="verified",
        ),
        policy=policy,
        gene_classifications=computed.gene_classifications,
        unresolved=computed.unresolved,
        summary=computed.summary,
        warnings=computed.warnings,
    )
    verification = verify_final_evidence_classification_outputs(tmp_path)
    assert verification["passed"]
    assert result.counts["genes_with_final_evidence_classification"] == 1
    assert (tmp_path / "gene_final_evidence_classifications_v1.tsv").exists()
    assert (tmp_path / "final_evidence_classification_unresolved_v1.tsv").exists()


def test_final_evidence_classification_verification_detects_tampering(tmp_path) -> None:
    policy = FinalEvidenceClassificationPolicyV1()
    computed = compute_final_evidence_classification(
        secondary_evidence_records=[integrated_record()],
        policy=policy,
    )
    write_final_evidence_classification_artifacts(
        output_dir=tmp_path,
        run_record=FinalEvidenceClassificationRunRecordV1(
            run_id="run-1",
            secondary_evidence_integration_result_id="secondary-result-1",
            secondary_evidence_integration_checksum="secondary-checksum",
            policy_id=policy.policy_id,
            policy_checksum=policy.fingerprint,
            started_at="2026-01-01T00:00:00+00:00",
            completed_at="2026-01-01T00:00:01+00:00",
            status="completed",
            verification_status="verified",
        ),
        policy=policy,
        gene_classifications=computed.gene_classifications,
        unresolved=computed.unresolved,
        summary=computed.summary,
        warnings=computed.warnings,
    )
    (tmp_path / "final_evidence_classification_summary_v1.json").write_text("{}\n")
    verification = verify_final_evidence_classification_outputs(tmp_path)
    assert not verification["passed"]
    assert any("count_reconciliation_checks" in error for error in verification["errors"])
