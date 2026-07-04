from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel

from sirna_offtarget.final_evidence_classification.contracts import (
    CLASSIFICATION_INTERPRETATION_BOUNDARY,
    FinalEvidenceClassificationPolicyV1,
    FinalEvidenceClassificationResultV1,
    FinalEvidenceClassificationRunRecordV1,
    FinalEvidenceClassificationUnresolvedRecordV1,
    FinalEvidenceClassificationVerificationRecordV1,
    GeneFinalEvidenceClassificationRecordV1,
    _contains_forbidden_label,
    stable_id,
)

CANONICAL_ARTIFACTS = {
    "result": "final_evidence_classification_result_v1.json",
    "run": "final_evidence_classification_run_v1.json",
    "policy": "final_evidence_classification_policy_v1.json",
    "gene_classifications": "gene_final_evidence_classifications_v1.jsonl",
    "gene_classifications_tsv": "gene_final_evidence_classifications_v1.tsv",
    "unresolved": "final_evidence_classification_unresolved_v1.jsonl",
    "unresolved_tsv": "final_evidence_classification_unresolved_v1.tsv",
    "summary": "final_evidence_classification_summary_v1.json",
    "verification": "final_evidence_classification_verification_v1.json",
    "warnings": "final_evidence_classification_warnings_v1.tsv",
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


def write_final_evidence_classification_artifacts(
    *,
    output_dir: Path,
    run_record: FinalEvidenceClassificationRunRecordV1,
    policy: FinalEvidenceClassificationPolicyV1,
    gene_classifications: list[GeneFinalEvidenceClassificationRecordV1],
    unresolved: list[FinalEvidenceClassificationUnresolvedRecordV1],
    summary: dict[str, Any],
    warnings: list[str],
) -> FinalEvidenceClassificationResultV1:
    paths = artifact_paths(output_dir)
    write_json(paths["policy"], policy)
    write_jsonl(paths["gene_classifications"], gene_classifications)
    write_tsv(paths["gene_classifications_tsv"], gene_classifications)
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
            "output_counts": {
                key: value for key, value in summary.items() if isinstance(value, int)
            },
            "output_checksums": checksums,
            "verification_status": "verified",
        }
    )
    write_json(paths["run"], finalized_run)
    checksums["run"] = sha256_file(paths["run"])
    result = FinalEvidenceClassificationResultV1(
        run_record=finalized_run,
        policy_artifact=paths["policy"].name,
        gene_classification_records_artifact=paths["gene_classifications"].name,
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
    verification = verify_final_evidence_classification_outputs(output_dir)
    write_json(paths["verification"], verification)
    return result


def verify_final_evidence_classification_outputs(output_dir: Path) -> dict[str, Any]:
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
        policy = FinalEvidenceClassificationPolicyV1.model_validate(
            json.loads(paths["policy"].read_text())
        )
        classifications = [
            GeneFinalEvidenceClassificationRecordV1.model_validate(record)
            for record in _jsonl(paths["gene_classifications"])
        ]
        unresolved = [
            FinalEvidenceClassificationUnresolvedRecordV1.model_validate(record)
            for record in _jsonl(paths["unresolved"])
        ]
        summary = json.loads(paths["summary"].read_text())
        if (
            policy.missing_evidence_as_negative_allowed
            or policy.seed_only_upgrade_allowed
            or policy.definitive_biological_claims_allowed
            or policy.regulatory_claims_allowed
        ):
            errors.append("classification_policy_checks:unsafe_policy")
        for record in classifications:
            if (
                record.classification_interpretation_boundary
                != CLASSIFICATION_INTERPRETATION_BOUNDARY
            ):
                errors.append(f"interpretation_boundary_checks:{record.gene_id}")
            if record.final_evidence_classification == "unresolved" and (
                record.classification_confidence != "unresolved"
            ):
                errors.append(f"confidence_policy_checks:unresolved:{record.gene_id}")
            if record.final_evidence_classification == "no_evidence_for_effect" and (
                record.classification_confidence == "high"
            ):
                errors.append(f"confidence_policy_checks:no_effect_high:{record.gene_id}")
            if record.classification_confidence == "high" and (
                "unresolved" in record.direct_sequence_evidence_component
                or "unavailable" in record.direct_sequence_evidence_component
                or record.expected_direct_effect_component == "expected_direct_effect_unavailable"
                or record.residual_evidence_component == "unresolved_residual_evidence"
                or record.pathway_support_component
                in {"unresolved_missing_pathway_evidence", "unresolved_upstream_expected_effect"}
            ):
                errors.append(f"confidence_policy_checks:high_with_unresolved:{record.gene_id}")
            if _contains_forbidden_label(record.model_dump(mode="json")):
                errors.append(f"forbidden_claim_checks:{record.gene_id}")
            if (
                record.unresolved_residual_log2fc is not None
                and record.observed_vs_expected_log2_difference is not None
                and record.unresolved_residual_log2fc != record.observed_vs_expected_log2_difference
            ):
                errors.append(f"preservation_checks:residual:{record.gene_id}")
        if summary.get("genes_with_final_evidence_classification") != len(classifications):
            errors.append("count_reconciliation_checks:gene_classifications")
        if summary.get("unresolved_records") != len(unresolved):
            errors.append("count_reconciliation_checks:unresolved_records")
        if result.get("counts", {}).get("genes_examined") != summary.get("genes_examined"):
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
    verification = FinalEvidenceClassificationVerificationRecordV1(
        verification_id=stable_id("final-evidence-classification-verification", str(output_dir)),
        secondary_evidence_integration_checks=status,
        preservation_checks=status,
        classification_policy_checks=status,
        confidence_policy_checks=status,
        interpretation_boundary_checks=status,
        forbidden_claim_checks=status,
        artifact_reference_checks=status,
        count_reconciliation_checks=status,
        passed=not errors,
        errors=tuple(errors),
        verified_at=datetime.now(UTC).isoformat(),
    )
    return verification.model_dump(mode="json")
