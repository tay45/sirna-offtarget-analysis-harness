from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from sirna_offtarget.isoform_uncertainty.contracts import (
    IsoformUncertaintyArtifactVerificationRecordV1,
    IsoformUncertaintyRunRecordV1,
)

IMMUTABLE_SCIENTIFIC_ARTIFACTS = {
    "genes": "gene_isoform_uncertainty_v1.jsonl",
    "weights": "transcript_prior_weights_v1.jsonl",
    "exclusions": "transcript_set_exclusions_v1.jsonl",
    "annotation_validation": "transcript_annotation_validation_v1.json",
    "external_validation": "external_transcript_evidence_validation_v1.json",
    "method_selection": "isoform_method_selection_v1.json",
    "input_validation": "isoform_input_validation_v1.json",
}
REPORT_ARTIFACTS = {
    "genes_tsv": "gene_isoform_uncertainty_v1.tsv",
    "weights_tsv": "transcript_prior_weights_v1.tsv",
    "exclusions_tsv": "transcript_set_exclusions_v1.tsv",
    "summary": "isoform_uncertainty_summary_v1.json",
    "warnings": "isoform_warnings_v1.tsv",
}
METADATA_ARTIFACTS = {
    "run": "isoform_uncertainty_run_v1.json",
    "result": "isoform_uncertainty_result_v1.json",
}
EXPECTED_ARTIFACTS = {
    **IMMUTABLE_SCIENTIFIC_ARTIFACTS,
    **REPORT_ARTIFACTS,
    **METADATA_ARTIFACTS,
}
EMPTY_VALID_ARTIFACTS = {
    "genes",
    "genes_tsv",
    "weights",
    "exclusions",
    "weights_tsv",
    "exclusions_tsv",
    "warnings",
}


def _jsonable(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    return value


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, payload: Any) -> None:
    _atomic_write_text(path, json.dumps(_jsonable(payload), indent=2, sort_keys=True) + "\n")


def write_jsonl(path: Path, records: list[Any]) -> None:
    _atomic_write_text(
        path,
        "".join(json.dumps(_jsonable(record), sort_keys=True) + "\n" for record in records),
    )


def write_tsv(path: Path, records: list[Any]) -> None:
    rows = [_jsonable(record) for record in records]
    if not rows:
        _atomic_write_text(path, "")
        return
    columns = list(rows[0])
    lines = ["\t".join(columns)]
    for row in rows:
        values = ["" if row.get(column) is None else str(row.get(column)) for column in columns]
        lines.append("\t".join(values))
    _atomic_write_text(path, "\n".join(lines) + "\n")


def _atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp")
    tmp.write_text(text)
    tmp.replace(path)


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


def artifact_paths(output_dir: Path) -> dict[str, Path]:
    return {name: output_dir / filename for name, filename in EXPECTED_ARTIFACTS.items()}


def write_immutable_isoform_uncertainty_artifacts(
    *,
    output_dir: Path,
    gene_records: list[Any],
    weight_records: list[Any],
    exclusion_records: list[Any],
    annotation_validation: Any,
    method_selection: dict[str, Any],
    input_validation: dict[str, Any],
    summary: dict[str, Any],
    external_validation: dict[str, Any] | None = None,
) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = artifact_paths(output_dir)
    write_jsonl(paths["genes"], gene_records)
    write_jsonl(paths["weights"], weight_records)
    write_jsonl(paths["exclusions"], exclusion_records)
    write_json(paths["annotation_validation"], annotation_validation)
    write_json(paths["external_validation"], external_validation or {"status": "not_applicable"})
    write_json(paths["method_selection"], method_selection)
    write_json(paths["input_validation"], input_validation)
    write_tsv(paths["genes_tsv"], gene_records)
    write_tsv(paths["weights_tsv"], weight_records)
    write_tsv(paths["exclusions_tsv"], exclusion_records)
    write_json(paths["summary"], summary)
    warnings = [
        {"record_id": record.record_id, "warning": warning}
        for record in gene_records
        for warning in getattr(record, "warnings", ())
    ]
    write_tsv(paths["warnings"], warnings)
    return {
        name: sha256_file(paths[name])
        for name in (*IMMUTABLE_SCIENTIFIC_ARTIFACTS, *REPORT_ARTIFACTS)
    }


def write_final_isoform_uncertainty_metadata(
    *,
    output_dir: Path,
    run_record: IsoformUncertaintyRunRecordV1,
    result_payload: dict[str, Any],
) -> dict[str, str]:
    paths = artifact_paths(output_dir)
    write_json(paths["run"], run_record)
    run_checksum = sha256_file(paths["run"])
    result_payload = dict(result_payload)
    result_payload.setdefault("run_record_file", paths["run"].name)
    result_payload.setdefault("run_record_file_sha256", run_checksum)
    result_payload.setdefault("self_checksum_status", "recorded_in_outer_manifest")
    write_json(paths["result"], result_payload)
    return {"run": run_checksum, "result": sha256_file(paths["result"])}


def verify_isoform_uncertainty_final_outputs(
    output_dir: Path,
) -> IsoformUncertaintyArtifactVerificationRecordV1:
    paths = artifact_paths(output_dir)
    errors: list[str] = []
    warnings: list[str] = []
    final_checksums: dict[str, str] = {}
    observed = tuple(sorted(path.name for path in output_dir.iterdir() if path.is_file()))
    for name, path in paths.items():
        if not path.exists():
            errors.append(f"missing_artifact:{path.name}")
            continue
        final_checksums[name] = sha256_file(path)
        if path.stat().st_size == 0 and name not in EMPTY_VALID_ARTIFACTS:
            errors.append(f"empty_artifact:{path.name}")
            continue
    run_status_check = False
    result_reference_check = False
    referenced_comparisons: dict[str, bool] = {}
    count_comparisons: dict[str, bool] = {}
    schema_comparisons: dict[str, bool] = {}
    try:
        run = json.loads(paths["run"].read_text())
        run_status_check = run.get("status") == "completed"
        if not run_status_check:
            errors.append("run_record_not_completed")
        if "output_checksums" in run and run.get("output_checksums"):
            errors.append("run_record_contains_deprecated_output_checksums")
        if run.get("self_checksum_status") != "recorded_in_outer_manifest":
            errors.append("run_record_self_checksum_status_not_explicit")
        referenced = run.get("referenced_artifact_checksums", {})
        for key in IMMUTABLE_SCIENTIFIC_ARTIFACTS:
            ok = referenced.get(key) == final_checksums.get(key)
            referenced_comparisons[key] = ok
            if not ok:
                errors.append(f"stale_referenced_checksum:{key}")
        for key, expected in run.get("record_counts", {}).items():
            if key == "gene_isoform_uncertainty_records":
                actual = _jsonl_count(paths["genes"])
            elif key == "transcript_prior_weight_records":
                actual = _jsonl_count(paths["weights"])
            elif key == "transcript_set_exclusion_records":
                actual = _jsonl_count(paths["exclusions"])
            else:
                continue
            ok = actual == expected
            count_comparisons[key] = ok
            if not ok:
                errors.append(f"count_mismatch:{key}")
    except (json.JSONDecodeError, OSError) as exc:
        errors.append(f"run_record_unreadable:{exc}")
    try:
        result = json.loads(paths["result"].read_text())
        result_reference_check = (
            result.get("run_record", {}).get("run_id") == run.get("run_id")
            if "run" in locals()
            else False
        )
        if not result_reference_check:
            errors.append("result_run_reference_mismatch")
        if result.get("self_checksum_status") != "recorded_in_outer_manifest":
            errors.append("result_self_checksum_status_not_explicit")
        for key, expected in result.get("artifacts", {}).items():
            if key in IMMUTABLE_SCIENTIFIC_ARTIFACTS:
                ok = expected == final_checksums.get(key)
                referenced_comparisons[f"result:{key}"] = ok
                if not ok:
                    errors.append(f"result_stale_referenced_checksum:{key}")
    except (json.JSONDecodeError, OSError) as exc:
        errors.append(f"result_record_unreadable:{exc}")
    for name in (
        "annotation_validation",
        "external_validation",
        "method_selection",
        "input_validation",
        "summary",
    ):
        try:
            schema_comparisons[name] = bool(json.loads(paths[name].read_text()))
        except (json.JSONDecodeError, OSError):
            schema_comparisons[name] = False
            errors.append(f"schema_mismatch:{name}")
    verification_hash = hashlib.sha256(
        json.dumps(final_checksums, sort_keys=True).encode()
    ).hexdigest()[:16]
    return IsoformUncertaintyArtifactVerificationRecordV1(
        verification_id=f"isoform-artifact-verification-{verification_hash}",
        expected_artifacts=tuple(path.name for path in paths.values()),
        observed_artifacts=observed,
        final_checksums=final_checksums,
        referenced_checksum_comparisons=referenced_comparisons,
        count_comparisons=count_comparisons,
        schema_comparisons=schema_comparisons,
        run_status_check=run_status_check,
        result_reference_check=result_reference_check,
        passed=not errors,
        errors=tuple(errors),
        warnings=tuple(warnings),
        verified_at=_utc_now(),
    )


def verify_committed_isoform_uncertainty_result(
    attempt_dir: Path,
) -> IsoformUncertaintyArtifactVerificationRecordV1:
    output_dir = attempt_dir / "committed" / "outputs"
    verification = verify_isoform_uncertainty_final_outputs(output_dir)
    manifest_path = attempt_dir / "stage_manifest.json"
    errors = list(verification.errors)
    if not manifest_path.exists():
        errors.append("missing_stage_manifest")
    else:
        manifest = json.loads(manifest_path.read_text())
        manifest_checksums = manifest.get("output_sha256_checksums", {})
        for _name, path in artifact_paths(output_dir).items():
            relative = str(path.relative_to(attempt_dir))
            if relative not in manifest_checksums:
                errors.append(f"missing_manifest_entry:{path.name}")
                continue
            if manifest_checksums[relative] != sha256_file(path):
                errors.append(f"stale_manifest_checksum:{path.name}")
        expected = {path.name for path in artifact_paths(output_dir).values()}
        expected.add("stage_result.json")
        unexpected = {
            path.name
            for path in output_dir.iterdir()
            if path.is_file() and path.name not in expected
        }
        if unexpected:
            errors.append("unexpected_artifact:" + ",".join(sorted(unexpected)))
    if errors == list(verification.errors):
        return verification
    return verification.model_copy(update={"passed": False, "errors": tuple(errors)})


def _jsonl_count(path: Path) -> int:
    return sum(1 for line in path.read_text().splitlines() if line.strip())


def write_isoform_uncertainty_artifacts(
    *,
    output_dir: Path,
    run_record: Any,
    gene_records: list[Any],
    weight_records: list[Any],
    exclusion_records: list[Any],
    annotation_validation: Any,
    method_selection: dict[str, Any],
    input_validation: dict[str, Any],
    summary: dict[str, Any],
    external_validation: dict[str, Any] | None = None,
    result_payload: dict[str, Any] | None = None,
) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "run": output_dir / "isoform_uncertainty_run_v1.json",
        "genes": output_dir / "gene_isoform_uncertainty_v1.jsonl",
        "weights": output_dir / "transcript_prior_weights_v1.jsonl",
        "exclusions": output_dir / "transcript_set_exclusions_v1.jsonl",
        "annotation_validation": output_dir / "transcript_annotation_validation_v1.json",
        "external_validation": output_dir / "external_transcript_evidence_validation_v1.json",
        "method_selection": output_dir / "isoform_method_selection_v1.json",
        "input_validation": output_dir / "isoform_input_validation_v1.json",
        "result": output_dir / "isoform_uncertainty_result_v1.json",
        "genes_tsv": output_dir / "gene_isoform_uncertainty_v1.tsv",
        "weights_tsv": output_dir / "transcript_prior_weights_v1.tsv",
        "exclusions_tsv": output_dir / "transcript_set_exclusions_v1.tsv",
        "summary": output_dir / "isoform_uncertainty_summary_v1.json",
        "warnings": output_dir / "isoform_warnings_v1.tsv",
    }
    write_json(paths["run"], run_record)
    write_jsonl(paths["genes"], gene_records)
    write_jsonl(paths["weights"], weight_records)
    write_jsonl(paths["exclusions"], exclusion_records)
    write_json(paths["annotation_validation"], annotation_validation)
    write_json(paths["external_validation"], external_validation or {"status": "not_applicable"})
    write_json(paths["method_selection"], method_selection)
    write_json(paths["input_validation"], input_validation)
    write_json(paths["result"], result_payload or {})
    write_tsv(paths["genes_tsv"], gene_records)
    write_tsv(paths["weights_tsv"], weight_records)
    write_tsv(paths["exclusions_tsv"], exclusion_records)
    write_json(paths["summary"], summary)
    warnings = [
        {"record_id": record.record_id, "warning": warning}
        for record in gene_records
        for warning in getattr(record, "warnings", ())
    ]
    write_tsv(paths["warnings"], warnings)
    return {name: sha256_file(path) for name, path in paths.items()}
