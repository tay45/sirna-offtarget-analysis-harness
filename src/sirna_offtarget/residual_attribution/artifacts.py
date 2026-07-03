from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel

from sirna_offtarget.residual_attribution.contracts import (
    INTERPRETATION_BOUNDARY,
    GeneResidualAttributionEvidenceRecordV1,
    ResidualAttributionPolicyV1,
    ResidualAttributionResultV1,
    ResidualAttributionRunRecordV1,
    ResidualAttributionUnresolvedRecordV1,
    ResidualAttributionVerificationRecordV1,
    stable_id,
)

CANONICAL_ARTIFACTS = {
    "result": "residual_attribution_result_v1.json",
    "run": "residual_attribution_run_v1.json",
    "policy": "residual_attribution_policy_v1.json",
    "gene_evidence": "gene_residual_attribution_evidence_v1.jsonl",
    "gene_evidence_tsv": "gene_residual_attribution_evidence_v1.tsv",
    "unresolved": "residual_attribution_unresolved_v1.jsonl",
    "unresolved_tsv": "residual_attribution_unresolved_v1.tsv",
    "summary": "residual_attribution_summary_v1.json",
    "verification": "residual_attribution_verification_v1.json",
    "warnings": "residual_attribution_warnings_v1.tsv",
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


def write_residual_attribution_artifacts(
    *,
    output_dir: Path,
    run_record: ResidualAttributionRunRecordV1,
    policy: ResidualAttributionPolicyV1,
    gene_evidence: list[GeneResidualAttributionEvidenceRecordV1],
    unresolved: list[ResidualAttributionUnresolvedRecordV1],
    summary: dict[str, Any],
    warnings: list[str],
) -> ResidualAttributionResultV1:
    paths = artifact_paths(output_dir)
    write_json(paths["policy"], policy)
    write_jsonl(paths["gene_evidence"], gene_evidence)
    write_tsv(paths["gene_evidence_tsv"], gene_evidence)
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
    result = ResidualAttributionResultV1(
        run_record=finalized_run,
        policy_artifact=paths["policy"].name,
        gene_evidence_records_artifact=paths["gene_evidence"].name,
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
    verification = verify_residual_attribution_outputs(output_dir)
    write_json(paths["verification"], verification)
    return result


def verify_residual_attribution_outputs(output_dir: Path) -> dict[str, Any]:
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
        policy = ResidualAttributionPolicyV1.model_validate(json.loads(paths["policy"].read_text()))
        gene_evidence = [
            GeneResidualAttributionEvidenceRecordV1.model_validate(record)
            for record in _jsonl(paths["gene_evidence"])
        ]
        unresolved = [
            ResidualAttributionUnresolvedRecordV1.model_validate(record)
            for record in _jsonl(paths["unresolved"])
        ]
        summary = json.loads(paths["summary"].read_text())
        if policy.classification_performed:
            errors.append("interpretation_boundary_checks:classification_performed")
        if policy.sequence_targetability_override:
            errors.append("interpretation_boundary_checks:sequence_targetability_override")
        for record in gene_evidence:
            if record.interpretation_boundary != INTERPRETATION_BOUNDARY:
                errors.append(f"interpretation_boundary_checks:{record.gene_id}")
            if record.unresolved_residual_log2fc != record.observed_vs_expected_log2_difference:
                errors.append(f"residual_preservation_checks:{record.gene_id}")
            if record.residual_abs_log2 != abs(record.unresolved_residual_log2fc):
                errors.append(f"residual_preservation_checks:abs:{record.gene_id}")
            if (
                record.residual_magnitude_status == "negligible_residual"
                and record.residual_support_status != "no_residual_to_attribute"
            ):
                errors.append(f"support_precedence_checks:negligible:{record.gene_id}")
            if (
                record.residual_magnitude_status != "negligible_residual"
                and not record.pathway_support_summary.get("pathway_evidence_available")
                and record.residual_support_status != "unresolved_missing_pathway_evidence"
            ):
                errors.append(f"support_precedence_checks:missing_pathway:{record.gene_id}")
            if not record.pathway_support_summary.get("supporting_context_only"):
                errors.append(f"interpretation_boundary_checks:support_context:{record.gene_id}")
        unresolved_upstream = sum(
            item.reason == "unresolved_upstream_expected_effect" for item in unresolved
        )
        if summary.get("genes_with_unresolved_upstream_expected_effect") != unresolved_upstream:
            errors.append("count_reconciliation_checks:unresolved_upstream")
        if summary.get("genes_with_residual_attribution_evidence") != len(gene_evidence):
            errors.append("count_reconciliation_checks:gene_evidence")
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
    verification = ResidualAttributionVerificationRecordV1(
        verification_id=stable_id("residual-attribution-verification", str(output_dir)),
        expected_direct_effect_checks=status,
        residual_preservation_checks=status,
        interpretation_boundary_checks=status,
        support_precedence_checks=status,
        artifact_reference_checks=status,
        count_reconciliation_checks=status,
        passed=not errors,
        errors=tuple(errors),
        verified_at=datetime.now(UTC).isoformat(),
    )
    return verification.model_dump(mode="json")
