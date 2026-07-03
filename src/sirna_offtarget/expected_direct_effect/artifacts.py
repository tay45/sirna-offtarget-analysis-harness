from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from math import isclose, log2
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel

from sirna_offtarget.expected_direct_effect.contracts import (
    ExpectedDirectEffectPolicyV1,
    ExpectedDirectEffectResultV1,
    ExpectedDirectEffectRunRecordV1,
    ExpectedDirectEffectVerificationRecordV1,
    GeneExpectedDirectEffectRecordV1,
    IntendedTargetKnockdownCalibrationRecordV1,
    UnresolvedExpectedDirectEffectRecordV1,
    stable_id,
)

CANONICAL_ARTIFACTS = {
    "result": "expected_direct_effect_result_v1.json",
    "run": "expected_direct_effect_run_v1.json",
    "policy": "expected_direct_effect_policy_v1.json",
    "calibration": "intended_target_knockdown_calibration_v1.json",
    "gene_effects": "gene_expected_direct_effects_v1.jsonl",
    "gene_effects_tsv": "gene_expected_direct_effects_v1.tsv",
    "unresolved": "expected_direct_effect_unresolved_v1.jsonl",
    "unresolved_tsv": "expected_direct_effect_unresolved_v1.tsv",
    "verification": "expected_direct_effect_verification_v1.json",
    "summary": "expected_direct_effect_summary_v1.json",
    "warnings": "expected_direct_effect_warnings_v1.tsv",
}


def _jsonable(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    return value


def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text)
    tmp.replace(path)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, payload: Any) -> None:
    _atomic_write(path, json.dumps(_jsonable(payload), indent=2, sort_keys=True) + "\n")


def write_jsonl(path: Path, records: list[Any]) -> None:
    _atomic_write(
        path,
        "".join(json.dumps(_jsonable(record), sort_keys=True) + "\n" for record in records),
    )


def _flatten(value: Any) -> str:
    if isinstance(value, (list, tuple)):
        return ";".join(str(item) for item in value)
    if isinstance(value, dict):
        return json.dumps(value, sort_keys=True)
    if value is None:
        return ""
    return str(value)


def write_tsv(path: Path, records: list[Any]) -> None:
    rows = [_jsonable(record) for record in records]
    if not rows:
        _atomic_write(path, "")
        return
    headers = list(rows[0])
    lines = ["\t".join(headers)]
    for row in rows:
        lines.append("\t".join(_flatten(row.get(header)) for header in headers))
    _atomic_write(path, "\n".join(lines) + "\n")


def _jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def artifact_paths(output_dir: Path) -> dict[str, Path]:
    return {key: output_dir / name for key, name in CANONICAL_ARTIFACTS.items()}


def write_expected_direct_effect_artifacts(
    *,
    output_dir: Path,
    run_record: ExpectedDirectEffectRunRecordV1,
    policy: ExpectedDirectEffectPolicyV1,
    calibration: IntendedTargetKnockdownCalibrationRecordV1,
    gene_effects: list[GeneExpectedDirectEffectRecordV1],
    unresolved: list[UnresolvedExpectedDirectEffectRecordV1],
    summary: dict[str, Any],
    warnings: list[str],
) -> ExpectedDirectEffectResultV1:
    paths = artifact_paths(output_dir)
    write_json(paths["policy"], policy)
    write_json(paths["calibration"], calibration)
    write_jsonl(paths["gene_effects"], gene_effects)
    write_tsv(paths["gene_effects_tsv"], gene_effects)
    write_jsonl(paths["unresolved"], unresolved)
    write_tsv(paths["unresolved_tsv"], unresolved)
    write_tsv(paths["warnings"], [{"warning": warning} for warning in warnings])
    write_json(paths["summary"], summary)
    checksums = {
        key: sha256_file(path)
        for key, path in paths.items()
        if key not in {"result", "run", "verification"} and path.exists()
    }
    finalized_run = run_record.model_copy(
        update={
            "calibration_checksum": checksums["calibration"],
            "output_counts": {
                key: value for key, value in summary.items() if isinstance(value, int)
            },
            "output_checksums": checksums,
            "verification_status": "verified",
        }
    )
    write_json(paths["run"], finalized_run)
    checksums["run"] = sha256_file(paths["run"])
    result = ExpectedDirectEffectResultV1(
        run_record=finalized_run,
        policy_artifact=paths["policy"].name,
        calibration_artifact=paths["calibration"].name,
        gene_effect_records_artifact=paths["gene_effects"].name,
        unresolved_records_artifact=paths["unresolved"].name,
        summary_artifact=paths["summary"].name,
        verification_artifact=paths["verification"].name,
        warnings_artifact=paths["warnings"].name,
        canonical_artifact_checksums=checksums,
        counts={key: value for key, value in summary.items() if isinstance(value, int)},
        status="completed",
        warnings=tuple(warnings),
    )
    write_json(paths["result"], result)
    verification = verify_expected_direct_effect_outputs(output_dir)
    write_json(paths["verification"], verification)
    return result


def verify_expected_direct_effect_outputs(output_dir: Path) -> dict[str, Any]:
    paths = artifact_paths(output_dir)
    errors: list[str] = []
    for key, path in paths.items():
        if key.endswith("_tsv"):
            continue
        if not path.exists():
            errors.append(f"missing:{path.name}")
    try:
        result = json.loads(paths["result"].read_text())
        run = json.loads(paths["run"].read_text())
        policy = ExpectedDirectEffectPolicyV1.model_validate(
            json.loads(paths["policy"].read_text())
        )
        calibration = IntendedTargetKnockdownCalibrationRecordV1.model_validate(
            json.loads(paths["calibration"].read_text())
        )
        gene_effects = [
            GeneExpectedDirectEffectRecordV1.model_validate(record)
            for record in _jsonl(paths["gene_effects"])
        ]
        unresolved = [
            UnresolvedExpectedDirectEffectRecordV1.model_validate(record)
            for record in _jsonl(paths["unresolved"])
        ]
        summary = json.loads(paths["summary"].read_text())
        if policy.classification_performed:
            errors.append("residual_guardrail_checks:classification_performed")
        if policy.pathway_evidence_used:
            errors.append("residual_guardrail_checks:pathway_evidence_used")
        if calibration.accepted_calibration_knockdown_fraction is not None:
            accepted = calibration.accepted_calibration_knockdown_fraction
            if not 0 <= accepted <= 1:
                errors.append("calibration_checks:accepted_calibration_out_of_bounds")
        if (
            calibration.status == "definitive_zero_no_decrease"
            and calibration.accepted_calibration_knockdown_fraction != 0
        ):
            errors.append("calibration_checks:zero_no_decrease_not_zero")
        if (
            calibration.status == "unavailable_inconsistent_calibration"
            and calibration.accepted_calibration_knockdown_fraction is not None
        ):
            errors.append("calibration_checks:inconsistent_has_accepted_value")
        definitive = 0
        for record in gene_effects:
            if not record.evidence_fields_kept_separate:
                errors.append(
                    f"residual_guardrail_checks:evidence_not_separate:{record.canonical_gene_id}"
                )
            if record.residual_interpretation != "unresolved_residual_only":
                errors.append(
                    f"residual_guardrail_checks:bad_residual_interpretation:{record.canonical_gene_id}"
                )
            if record.status == "definitive":
                definitive += 1
                if record.observed_normalized_log2fc is None:
                    errors.append(f"expression_checks:missing_observed:{record.canonical_gene_id}")
                    continue
                if record.targetable_fraction_m_over_n is None:
                    errors.append(f"ratio_checks:missing_ratio:{record.canonical_gene_id}")
                    continue
                accepted_calibration = calibration.accepted_calibration_knockdown_fraction
                if accepted_calibration is None:
                    errors.append(f"calibration_checks:missing_accepted:{record.canonical_gene_id}")
                    continue
                remaining = 1.0 - accepted_calibration * record.targetable_fraction_m_over_n
                if remaining < -policy.numerical_tolerance:
                    errors.append(
                        f"arithmetic_checks:remaining_below_zero:{record.canonical_gene_id}"
                    )
                    continue
                remaining = max(remaining, 0.0)
                expected = float("-inf") if remaining == 0 else log2(remaining)
                if record.expected_direct_effect_log2fc is None or not isclose(
                    record.expected_direct_effect_log2fc,
                    expected,
                    rel_tol=0.0,
                    abs_tol=policy.numerical_tolerance,
                ):
                    errors.append(f"arithmetic_checks:expected:{record.canonical_gene_id}")
                difference = record.observed_normalized_log2fc - expected
                if record.observed_vs_expected_log2_difference is None or not isclose(
                    record.observed_vs_expected_log2_difference,
                    difference,
                    rel_tol=0.0,
                    abs_tol=policy.numerical_tolerance,
                ):
                    errors.append(f"arithmetic_checks:difference:{record.canonical_gene_id}")
                if record.unresolved_residual_log2fc != record.observed_vs_expected_log2_difference:
                    errors.append(f"arithmetic_checks:residual:{record.canonical_gene_id}")
            elif record.expected_direct_effect_log2fc is not None:
                errors.append(
                    f"arithmetic_checks:unavailable_has_expected:{record.canonical_gene_id}"
                )
        if len(unresolved) != sum(record.status != "definitive" for record in gene_effects):
            errors.append("count_reconciliation_checks:unresolved_records")
        if summary.get("genes_examined") != len(gene_effects):
            errors.append("count_reconciliation_checks:genes_examined")
        if summary.get("genes_with_definitive_expected_direct_effect") != definitive:
            errors.append("count_reconciliation_checks:definitive")
        if result.get("counts", {}).get("genes_examined") != len(gene_effects):
            errors.append("count_reconciliation_checks:result_counts")
        for key, checksum in result.get("canonical_artifact_checksums", {}).items():
            if (
                key in paths
                and key not in {"result", "verification"}
                and paths[key].exists()
                and sha256_file(paths[key]) != checksum
            ):
                errors.append(f"artifact_reference_checks:checksum:{key}")
        if run.get("verification_status") != "verified":
            errors.append("artifact_reference_checks:run_not_verified")
    except (OSError, json.JSONDecodeError, KeyError, ValueError) as exc:
        errors.append(f"unreadable:{exc}")
    status: Literal["passed", "failed"] = "passed" if not errors else "failed"
    verification = ExpectedDirectEffectVerificationRecordV1(
        verification_id=stable_id("expected-direct-verification", str(output_dir)),
        calibration_checks=status,
        expression_checks=status,
        ratio_checks=status,
        arithmetic_checks=status,
        residual_guardrail_checks=status,
        artifact_reference_checks=status,
        count_reconciliation_checks=status,
        passed=not errors,
        errors=tuple(errors),
        verified_at=datetime.now(UTC).isoformat(),
    )
    return verification.model_dump(mode="json")
