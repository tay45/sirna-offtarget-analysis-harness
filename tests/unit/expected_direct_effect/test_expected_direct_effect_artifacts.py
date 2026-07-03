from __future__ import annotations

import json
from math import log2

import pytest

from sirna_offtarget.expected_direct_effect.artifacts import (
    verify_expected_direct_effect_outputs,
    write_expected_direct_effect_artifacts,
)
from sirna_offtarget.expected_direct_effect.contracts import (
    ExpectedDirectEffectPolicyV1,
    ExpectedDirectEffectRunRecordV1,
)
from sirna_offtarget.expected_direct_effect.core import compute_expected_direct_effects
from tests.unit.expected_direct_effect.test_expected_direct_effect_core import expr, ratio


def test_artifact_verification_recomputes_expected_direct_effect(tmp_path) -> None:
    policy = ExpectedDirectEffectPolicyV1()
    computed = compute_expected_direct_effects(
        intended_target_gene_id="TARGET",
        expression_records=[expr("TARGET", log2(0.5)), expr("GENE", -0.5)],
        ratio_records=[ratio("TARGET", 2, 2), ratio("GENE", 2, 1)],
        policy=policy,
    )
    write_expected_direct_effect_artifacts(
        output_dir=tmp_path,
        run_record=ExpectedDirectEffectRunRecordV1(
            run_id="run",
            expression_result_id="expr-run",
            expression_checksum="expr-checksum",
            transcript_targetability_ratio_result_id="ratio-run",
            transcript_targetability_ratio_checksum="ratio-checksum",
            policy_id=policy.policy_id,
            policy_checksum=policy.fingerprint,
            calibration_record_id=computed.calibration.calibration_record_id,
            started_at="2026-01-01T00:00:00+00:00",
            completed_at="2026-01-01T00:00:01+00:00",
            status="completed",
            verification_status="verified",
        ),
        policy=policy,
        calibration=computed.calibration,
        gene_effects=computed.gene_effects,
        unresolved=computed.unresolved,
        summary=computed.summary,
        warnings=computed.warnings,
    )
    verification = verify_expected_direct_effect_outputs(tmp_path)
    assert verification["passed"] is True


def test_artifact_verification_rejects_tampered_arithmetic(tmp_path) -> None:
    policy = ExpectedDirectEffectPolicyV1()
    computed = compute_expected_direct_effects(
        intended_target_gene_id="TARGET",
        expression_records=[expr("TARGET", log2(0.5)), expr("GENE", -0.5)],
        ratio_records=[ratio("TARGET", 2, 2), ratio("GENE", 2, 1)],
        policy=policy,
    )
    write_expected_direct_effect_artifacts(
        output_dir=tmp_path,
        run_record=ExpectedDirectEffectRunRecordV1(
            run_id="run",
            expression_result_id="expr-run",
            expression_checksum="expr-checksum",
            transcript_targetability_ratio_result_id="ratio-run",
            transcript_targetability_ratio_checksum="ratio-checksum",
            policy_id=policy.policy_id,
            policy_checksum=policy.fingerprint,
            calibration_record_id=computed.calibration.calibration_record_id,
            started_at="2026-01-01T00:00:00+00:00",
            completed_at="2026-01-01T00:00:01+00:00",
            status="completed",
            verification_status="verified",
        ),
        policy=policy,
        calibration=computed.calibration,
        gene_effects=computed.gene_effects,
        unresolved=computed.unresolved,
        summary=computed.summary,
        warnings=computed.warnings,
    )
    path = tmp_path / "gene_expected_direct_effects_v1.jsonl"
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    rows[0]["expected_direct_effect_log2fc"] = 0.25
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows))
    verification = verify_expected_direct_effect_outputs(tmp_path)
    assert verification["passed"] is False
    assert any("arithmetic_checks" in error for error in verification["errors"])


def test_policy_guardrails_reject_forbidden_semantics() -> None:
    with pytest.raises(ValueError, match="pathway evidence"):
        ExpectedDirectEffectPolicyV1(pathway_evidence_used=True)
    with pytest.raises(ValueError, match="classification"):
        ExpectedDirectEffectPolicyV1(classification_performed=True)
    with pytest.raises(ValueError, match="seed-only"):
        ExpectedDirectEffectPolicyV1(include_seed_only_as_targetable=True)
    with pytest.raises(ValueError, match="numerical_tolerance"):
        ExpectedDirectEffectPolicyV1(numerical_tolerance=0)


def test_gene_record_rejects_residual_interpretation() -> None:
    computed = compute_expected_direct_effects(
        intended_target_gene_id="TARGET",
        expression_records=[expr("TARGET", log2(0.5)), expr("GENE", -0.5)],
        ratio_records=[ratio("TARGET", 2, 2), ratio("GENE", 2, 1)],
    )
    payload = computed.gene_effects[0].model_dump(mode="json")
    payload["residual_interpretation"] = "secondary_effect"
    with pytest.raises(ValueError, match="residual"):
        type(computed.gene_effects[0]).model_validate(payload)


def _write_verified_fixture(tmp_path):
    policy = ExpectedDirectEffectPolicyV1()
    computed = compute_expected_direct_effects(
        intended_target_gene_id="TARGET",
        expression_records=[expr("TARGET", log2(0.5)), expr("GENE", -0.5)],
        ratio_records=[ratio("TARGET", 2, 2), ratio("GENE", 2, 1)],
        policy=policy,
    )
    write_expected_direct_effect_artifacts(
        output_dir=tmp_path,
        run_record=ExpectedDirectEffectRunRecordV1(
            run_id="run",
            expression_result_id="expr-run",
            expression_checksum="expr-checksum",
            transcript_targetability_ratio_result_id="ratio-run",
            transcript_targetability_ratio_checksum="ratio-checksum",
            policy_id=policy.policy_id,
            policy_checksum=policy.fingerprint,
            calibration_record_id=computed.calibration.calibration_record_id,
            started_at="2026-01-01T00:00:00+00:00",
            completed_at="2026-01-01T00:00:01+00:00",
            status="completed",
            verification_status="verified",
        ),
        policy=policy,
        calibration=computed.calibration,
        gene_effects=computed.gene_effects,
        unresolved=computed.unresolved,
        summary=computed.summary,
        warnings=computed.warnings,
    )


def _rewrite_json(path, mutate):
    payload = json.loads(path.read_text())
    mutate(payload)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def _rewrite_jsonl(path, mutate):
    rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    mutate(rows)
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows))


@pytest.mark.parametrize(
    ("mutator", "expected_error"),
    [
        (
            lambda root: _rewrite_json(
                root / "intended_target_knockdown_calibration_v1.json",
                lambda payload: payload.update(
                    {
                        "status": "definitive_zero_no_decrease",
                        "accepted_calibration_knockdown_fraction": 0.25,
                    }
                ),
            ),
            "zero_no_decrease",
        ),
        (
            lambda root: _rewrite_json(
                root / "intended_target_knockdown_calibration_v1.json",
                lambda payload: payload.update(
                    {
                        "status": "unavailable_inconsistent_calibration",
                        "accepted_calibration_knockdown_fraction": 0.25,
                    }
                ),
            ),
            "inconsistent_has_accepted_value",
        ),
        (
            lambda root: _rewrite_json(
                root / "expected_direct_effect_run_v1.json",
                lambda payload: payload.update({"verification_status": "failed"}),
            ),
            "run_not_verified",
        ),
        (
            lambda root: _rewrite_json(
                root / "expected_direct_effect_result_v1.json",
                lambda payload: payload["counts"].update({"genes_examined": 999}),
            ),
            "result_counts",
        ),
        (
            lambda root: _rewrite_jsonl(
                root / "gene_expected_direct_effects_v1.jsonl",
                lambda rows: rows[0].update({"evidence_fields_kept_separate": False}),
            ),
            "evidence_not_separate",
        ),
        (
            lambda root: _rewrite_jsonl(
                root / "gene_expected_direct_effects_v1.jsonl",
                lambda rows: rows[0].update(
                    {
                        "status": "unavailable_ratio",
                        "expected_direct_effect_log2fc": -1.0,
                    }
                ),
            ),
            "unavailable_has_expected",
        ),
    ],
)
def test_artifact_verification_rejects_guardrail_tampering(
    tmp_path, mutator, expected_error
) -> None:
    _write_verified_fixture(tmp_path)
    mutator(tmp_path)
    verification = verify_expected_direct_effect_outputs(tmp_path)
    assert verification["passed"] is False
    assert any(expected_error in error for error in verification["errors"])


def test_artifact_verification_reports_missing_files(tmp_path) -> None:
    verification = verify_expected_direct_effect_outputs(tmp_path)
    assert verification["passed"] is False
    assert any(
        "missing:expected_direct_effect_result_v1.json" in error for error in verification["errors"]
    )
