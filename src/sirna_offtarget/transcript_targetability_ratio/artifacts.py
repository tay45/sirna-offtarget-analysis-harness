from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel

from sirna_offtarget.isoform_uncertainty.contracts import TranscriptPriorWeightRecordV1
from sirna_offtarget.transcript_targetability_ratio.contracts import (
    GeneTranscriptTargetabilityRatioRecordV1,
    TargetableTranscriptInclusionPolicyV1,
    TranscriptMContributionRecordV1,
    TranscriptTargetabilityRatioResultV1,
    TranscriptTargetabilityRatioRunRecordV1,
    TranscriptTargetabilityRatioVerificationRecordV1,
    UnresolvedTargetabilityRatioEvidenceRecordV1,
    stable_id,
)
from sirna_offtarget.transcript_targetability_ratio.core import (
    compute_transcript_targetability_ratios,
)

CANONICAL_ARTIFACTS = {
    "result": "transcript_targetability_ratio_result_v1.json",
    "run": "transcript_targetability_ratio_run_v1.json",
    "policy": "targetable_transcript_inclusion_policy_v1.json",
    "ratios": "gene_transcript_targetability_ratios_v1.jsonl",
    "contributions": "transcript_m_contributions_v1.jsonl",
    "unresolved": "transcript_targetability_ratio_unresolved_v1.jsonl",
    "verification": "transcript_targetability_ratio_verification_v1.json",
    "summary": "transcript_targetability_ratio_summary_v1.json",
    "warnings": "transcript_targetability_ratio_warnings_v1.tsv",
    "ratios_tsv": "gene_transcript_targetability_ratios_v1.tsv",
    "contributions_tsv": "transcript_m_contributions_v1.tsv",
    "unresolved_tsv": "transcript_targetability_ratio_unresolved_v1.tsv",
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


def write_transcript_targetability_ratio_artifacts(
    *,
    output_dir: Path,
    run_record: TranscriptTargetabilityRatioRunRecordV1,
    inclusion_policy: TargetableTranscriptInclusionPolicyV1,
    gene_ratios: list[GeneTranscriptTargetabilityRatioRecordV1],
    contributions: list[TranscriptMContributionRecordV1],
    unresolved: list[UnresolvedTargetabilityRatioEvidenceRecordV1],
    summary: dict[str, Any],
    warnings: list[str],
) -> TranscriptTargetabilityRatioResultV1:
    paths = artifact_paths(output_dir)
    write_json(paths["policy"], inclusion_policy)
    write_jsonl(paths["ratios"], gene_ratios)
    write_jsonl(paths["contributions"], contributions)
    write_jsonl(paths["unresolved"], unresolved)
    write_tsv(paths["ratios_tsv"], gene_ratios)
    write_tsv(paths["contributions_tsv"], contributions)
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
    result = TranscriptTargetabilityRatioResultV1(
        run_record=finalized_run,
        inclusion_policy_artifact=paths["policy"].name,
        gene_ratio_records_artifact=paths["ratios"].name,
        transcript_contribution_records_artifact=paths["contributions"].name,
        unresolved_evidence_records_artifact=paths["unresolved"].name,
        summary_artifact=paths["summary"].name,
        verification_artifact=paths["verification"].name,
        warnings_artifact=paths["warnings"].name,
        canonical_artifact_checksums=checksums,
        counts={key: value for key, value in summary.items() if isinstance(value, int)},
        status="completed",
        warnings=tuple(warnings),
    )
    write_json(paths["result"], result)
    verification = verify_transcript_targetability_ratio_outputs(output_dir)
    write_json(paths["verification"], verification)
    return result


def verify_transcript_targetability_ratio_outputs(output_dir: Path) -> dict[str, Any]:
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
        policy = TargetableTranscriptInclusionPolicyV1.model_validate(
            json.loads(paths["policy"].read_text())
        )
        ratios = [
            GeneTranscriptTargetabilityRatioRecordV1.model_validate(record)
            for record in _jsonl(paths["ratios"])
        ]
        contributions = [
            TranscriptMContributionRecordV1.model_validate(record)
            for record in _jsonl(paths["contributions"])
        ]
        unresolved = [
            UnresolvedTargetabilityRatioEvidenceRecordV1.model_validate(record)
            for record in _jsonl(paths["unresolved"])
        ]
        summary = json.loads(paths["summary"].read_text())

        ratio_by_gene = {record.canonical_gene_id: record for record in ratios}
        if len(ratio_by_gene) != len(ratios):
            errors.append("unique_transcript_checks:duplicate_gene_ratio")
        contrib_by_gene: dict[str, list[TranscriptMContributionRecordV1]] = {}
        seen_tx: set[str] = set()
        for contribution in contributions:
            tx = contribution.canonical_transcript_id
            if tx in seen_tx:
                errors.append(f"unique_transcript_checks:duplicate_contribution:{tx}")
            seen_tx.add(tx)
            contrib_by_gene.setdefault(contribution.canonical_gene_id, []).append(contribution)
            if contribution.contribution_to_n != 1:
                errors.append(f"n_count_checks:bad_contribution:{tx}")
            if (
                contribution.qualifying_for_m
                and contribution.qualifying_evidence_class == "seed_only_candidate"
            ):
                errors.append(f"seed_only_exclusion_checks:seed_only_qualified:{tx}")
            if contribution.contribution_to_m not in {None, 0, 1}:
                errors.append(f"m_count_checks:bad_contribution:{tx}")

        for ratio in ratios:
            items = contrib_by_gene.get(ratio.canonical_gene_id, [])
            eligible = {item.canonical_transcript_id for item in items if item.eligible_for_n}
            qualifying = {item.canonical_transcript_id for item in items if item.qualifying_for_m}
            unresolved_ids = {
                item.canonical_transcript_id for item in items if item.contribution_to_m is None
            }
            seed_only = {
                item.canonical_transcript_id for item in items if item.seed_only_evidence_present
            }
            if eligible != set(ratio.eligible_transcript_ids):
                errors.append(f"transcript_set_checks:{ratio.canonical_gene_id}")
            if len(eligible) != ratio.n_total_eligible_transcripts:
                errors.append(f"n_count_checks:{ratio.canonical_gene_id}")
            if qualifying != set(ratio.qualifying_transcript_ids):
                errors.append(f"m_count_checks:{ratio.canonical_gene_id}")
            if len(qualifying) != ratio.observed_qualifying_transcript_count:
                errors.append(f"m_count_checks:observed:{ratio.canonical_gene_id}")
            if unresolved_ids != set(ratio.unresolved_transcript_ids):
                errors.append(f"unavailable_evidence_checks:{ratio.canonical_gene_id}")
            if seed_only != set(ratio.seed_only_transcript_ids):
                errors.append(f"seed_only_exclusion_checks:{ratio.canonical_gene_id}")
            if ratio.gene_failure_record_id and ratio.ratio_status != "unavailable_gene_failure":
                errors.append(f"failed_gene_checks:{ratio.canonical_gene_id}")
            if ratio.n_total_eligible_transcripts == 0 and ratio.ratio_m_over_n is not None:
                errors.append(f"zero_denominator_checks:{ratio.canonical_gene_id}")
            if ratio.m_targetable_transcripts is not None:
                if ratio.m_targetable_transcripts != len(qualifying):
                    errors.append(f"m_count_checks:definitive:{ratio.canonical_gene_id}")
                if ratio.m_targetable_transcripts > ratio.n_total_eligible_transcripts:
                    errors.append(f"m_count_checks:m_gt_n:{ratio.canonical_gene_id}")
            if ratio.ratio_m_over_n is not None:
                expected = len(qualifying) / ratio.n_total_eligible_transcripts
                if abs(ratio.ratio_m_over_n - expected) > 1e-12:
                    errors.append(f"ratio_arithmetic_checks:{ratio.canonical_gene_id}")
                if not 0 <= ratio.ratio_m_over_n <= 1:
                    errors.append(f"ratio_arithmetic_checks:range:{ratio.canonical_gene_id}")
                if (
                    ratio.qualifying_equal_prior_weight_sum is None
                    or abs(ratio.ratio_m_over_n - ratio.qualifying_equal_prior_weight_sum) > 1e-12
                ):
                    errors.append(f"equal_prior_weight_checks:{ratio.canonical_gene_id}")
            elif ratio.ratio_status == "definitive":
                errors.append(f"ratio_arithmetic_checks:missing_ratio:{ratio.canonical_gene_id}")
            if (
                ratio.ratio_status == "definitive"
                and ratio.unresolved_transcript_count
                and policy.require_complete_gene_evidence
            ):
                errors.append(
                    f"unavailable_evidence_checks:definitive_with_unresolved:{ratio.canonical_gene_id}"
                )

        summary_counts = {
            "genes_examined": len(ratios),
            "total_eligible_transcripts": sum(
                record.n_total_eligible_transcripts for record in ratios
            ),
            "total_qualifying_transcripts": sum(
                record.observed_qualifying_transcript_count for record in ratios
            ),
            "total_unresolved_transcripts": sum(
                record.unresolved_transcript_count for record in ratios
            ),
        }
        for field, expected in summary_counts.items():
            if summary.get(field) != expected:
                errors.append(f"count_reconciliation_checks:{field}")
        if result.get("counts", {}).get("genes_examined") != len(ratios):
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
        if len(unresolved) != summary.get("total_unresolved_transcripts"):
            errors.append("count_reconciliation_checks:unresolved_records")
    except (OSError, json.JSONDecodeError, KeyError, ValueError) as exc:
        errors.append(f"unreadable:{exc}")
    status: Literal["passed", "failed"] = "passed" if not errors else "failed"
    verification = TranscriptTargetabilityRatioVerificationRecordV1(
        verification_id=stable_id("ratio-verification", str(output_dir)),
        transcript_set_checks=status,
        n_count_checks=status,
        m_count_checks=status,
        unique_transcript_checks=status,
        inclusion_policy_checks=status,
        seed_only_exclusion_checks=status,
        unavailable_evidence_checks=status,
        failed_gene_checks=status,
        zero_denominator_checks=status,
        equal_prior_weight_checks=status,
        ratio_arithmetic_checks=status,
        artifact_reference_checks=status,
        count_reconciliation_checks=status,
        passed=not errors,
        errors=tuple(errors),
        verified_at=datetime.now(UTC).isoformat(),
    )
    return verification.model_dump(mode="json")


def recompute_from_artifacts(
    *,
    transcript_weights_path: Path,
    evidence_path: Path,
    sites_path: Path,
    gene_failures_path: Path,
    source_targetability_result_id: str,
    inclusion_policy: TargetableTranscriptInclusionPolicyV1,
) -> tuple[list[GeneTranscriptTargetabilityRatioRecordV1], list[TranscriptMContributionRecordV1]]:
    weights = [
        TranscriptPriorWeightRecordV1.model_validate(json.loads(line))
        for line in transcript_weights_path.read_text().splitlines()
        if line.strip()
    ]
    computed = compute_transcript_targetability_ratios(
        transcript_weights=weights,
        gene_records=None,
        targetability_evidence=_jsonl(evidence_path),
        targetability_sites=_jsonl(sites_path),
        gene_failures=_jsonl(gene_failures_path) if gene_failures_path.exists() else [],
        source_targetability_result_id=source_targetability_result_id,
        inclusion_policy=inclusion_policy,
    )
    return computed.gene_ratios, computed.contributions
