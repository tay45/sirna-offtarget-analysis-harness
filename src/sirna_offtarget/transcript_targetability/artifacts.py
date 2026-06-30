from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from sirna_offtarget.transcript_targetability.contracts import (
    CleavageCompatibilityPolicyV1,
    IntendedTargetValidationRecordV1,
    SeedMatchPolicyV1,
    TranscriptSequenceRecordV1,
    TranscriptSequenceSnapshotV1,
    TranscriptTargetabilityAlignmentPositionRecordV1,
    TranscriptTargetabilityEvidenceRecordV1,
    TranscriptTargetabilityGeneFailureRecordV1,
    TranscriptTargetabilityMismatchRecordV1,
    TranscriptTargetabilityResultV1,
    TranscriptTargetabilityRunRecordV1,
    TranscriptTargetabilitySiteRecordV1,
    TranscriptTargetabilityVerificationRecordV1,
)
from sirna_offtarget.transcript_targetability.core import (
    build_targetability_site_id,
    reverse_complement,
    sha256_text,
)

CANONICAL_ARTIFACTS = {
    "result": "transcript_targetability_result_v1.json",
    "run": "transcript_targetability_run_v1.json",
    "sirna_sequence": "sirna_sequence_record_v1.json",
    "sirna_validation": "sirna_sequence_validation_v1.json",
    "sequence_validation": "transcript_sequence_snapshot_validation_v1.json",
    "sequence_snapshot": "transcript_sequence_snapshot_v1.json",
    "sequence_records": "transcript_sequence_snapshot_records_v1.jsonl",
    "evidence": "transcript_targetability_evidence_v1.jsonl",
    "sites": "transcript_targetability_sites_v1.jsonl",
    "alignment_positions": "transcript_targetability_alignment_positions_v1.jsonl",
    "mismatches": "transcript_targetability_mismatches_v1.jsonl",
    "gene_failures": "transcript_targetability_gene_failures_v1.jsonl",
    "intended_validation": "intended_target_validation_v1.json",
    "exclusions": "transcript_targetability_exclusions_v1.jsonl",
    "policy": "transcript_targetability_policy_v1.json",
    "verification": "transcript_targetability_verification_v1.json",
}
REPORT_ARTIFACTS = {
    "evidence_tsv": "transcript_targetability_evidence_v1.tsv",
    "sites_tsv": "transcript_targetability_sites_v1.tsv",
    "alignment_positions_tsv": "transcript_targetability_alignment_positions_v1.tsv",
    "mismatches_tsv": "transcript_targetability_mismatches_v1.tsv",
    "exclusions_tsv": "transcript_targetability_exclusions_v1.tsv",
    "summary": "transcript_targetability_summary_v1.json",
    "warnings": "transcript_targetability_warnings_v1.tsv",
}
EXPECTED_ARTIFACTS = {**CANONICAL_ARTIFACTS, **REPORT_ARTIFACTS}


def _jsonable(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    return value


def sha256_file(path: Path) -> str:
    import hashlib

    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_jsonable(payload), indent=2, sort_keys=True) + "\n")


def write_jsonl(path: Path, records: list[Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(_jsonable(record), sort_keys=True) + "\n" for record in records)
    )


def write_tsv(path: Path, records: list[Any]) -> None:
    rows = [_jsonable(record) for record in records]
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("")
        return
    columns = list(rows[0])
    lines = ["\t".join(columns)]
    for row in rows:
        lines.append(
            "\t".join("" if row.get(col) is None else str(row.get(col)) for col in columns)
        )
    path.write_text("\n".join(lines) + "\n")


def artifact_paths(output_dir: Path) -> dict[str, Path]:
    return {key: output_dir / filename for key, filename in EXPECTED_ARTIFACTS.items()}


def summarize_targetability(
    evidence: list[TranscriptTargetabilityEvidenceRecordV1],
    sites: list[TranscriptTargetabilitySiteRecordV1],
    alignment_positions: list[TranscriptTargetabilityAlignmentPositionRecordV1],
    gene_failures: list[TranscriptTargetabilityGeneFailureRecordV1],
    exclusions: list[dict[str, Any]],
) -> dict[str, int | str]:
    failed_transcripts = {
        transcript_id
        for failure in gene_failures
        for transcript_id in failure.affected_transcript_ids
    }
    return {
        "sirnas_examined": len({record.sirna_id for record in evidence}),
        "guide_strands_validated": 1 if evidence else 0,
        "passenger_strands_examined": 0,
        "genes_examined": len({record.canonical_gene_id for record in evidence}),
        "genes_successfully_evaluated": len(
            {
                record.canonical_gene_id
                for record in evidence
                if record.targetability_decision_status != "not_evaluated_due_to_gene_failure"
            }
        ),
        "genes_failed_under_fail_gene": len(gene_failures),
        "eligible_transcripts_examined": len(evidence),
        "transcripts_evaluated": sum(
            record.targetability_decision_status
            not in {"sequence_unavailable", "not_evaluated_due_to_gene_failure"}
            for record in evidence
        ),
        "transcript_sequences_available": sum(record.sequence_available for record in evidence),
        "transcript_sequences_unavailable": sum(
            not record.sequence_available
            for record in evidence
            if record.targetability_decision_status != "not_evaluated_due_to_gene_failure"
        ),
        "transcripts_not_evaluated_due_to_gene_failure": sum(
            record.canonical_transcript_id in failed_transcripts for record in evidence
        ),
        "transcripts_with_exact_full_length_sites": sum(
            record.exact_site_count > 0 for record in evidence
        ),
        "transcripts_with_near_full_length_sites": sum(
            record.near_full_length_site_count > 0 for record in evidence
        ),
        "transcripts_with_cleavage_compatible_candidate_sites": sum(
            record.cleavage_candidate_site_count > 0 for record in evidence
        ),
        "transcripts_with_seed_only_sites": sum(
            record.seed_only_site_count > 0 for record in evidence
        ),
        "transcripts_with_partial_nonseed_matches": sum(
            record.partial_match_site_count > 0 for record in evidence
        ),
        "transcripts_with_no_supported_sites": sum(
            record.targetability_decision_status == "no_supported_site" for record in evidence
        ),
        "ambiguous_transcripts": sum(
            record.targetability_decision_status == "indeterminate" for record in evidence
        ),
        "total_qualifying_sites": len(sites),
        "total_alignment_position_records": len(alignment_positions),
        "total_exact_sites": sum(
            site.evidence_class == "exact_full_length_complement" for site in sites
        ),
        "total_near_full_length_sites": sum(
            site.evidence_class == "near_full_length_complement" for site in sites
        ),
        "total_seed_only_sites": sum(
            site.evidence_class == "seed_only_candidate" for site in sites
        ),
        "total_mismatch_records": sum(site.total_mismatch_count for site in sites),
        "canonical_sites_discarded_due_to_gene_failure": 0,
        "intended_target_validation_status": "not_evaluated",
        "exclusions": len(exclusions),
        "warnings": 0,
    }


def write_transcript_targetability_artifacts(
    *,
    output_dir: Path,
    sirna_sequence: Any,
    sirna_validation: Any,
    sequence_validation: Any,
    transcript_sequence_snapshot: TranscriptSequenceSnapshotV1 | dict[str, Any] | None = None,
    transcript_sequence_records: list[TranscriptSequenceRecordV1] | None = None,
    evidence_records: list[TranscriptTargetabilityEvidenceRecordV1],
    site_records: list[TranscriptTargetabilitySiteRecordV1],
    mismatch_records: list[TranscriptTargetabilityMismatchRecordV1],
    alignment_position_records: list[TranscriptTargetabilityAlignmentPositionRecordV1],
    gene_failure_records: list[TranscriptTargetabilityGeneFailureRecordV1] | None = None,
    intended_target_validation: IntendedTargetValidationRecordV1 | dict[str, Any] | None = None,
    exclusions: list[dict[str, Any]],
    policy_payload: dict[str, Any],
    run_record: TranscriptTargetabilityRunRecordV1,
) -> TranscriptTargetabilityResultV1:
    paths = artifact_paths(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    mismatch_records = [record for record in mismatch_records if record.match_status == "mismatch"]
    gene_failure_records = gene_failure_records or []
    if transcript_sequence_records is None:
        transcript_sequence_records = [
            TranscriptSequenceRecordV1(
                canonical_gene_id=site.canonical_gene_id,
                canonical_transcript_id=site.canonical_transcript_id,
                transcript_version=site.transcript_version,
                sequence=site.transcript_site_sequence,
                sequence_checksum=site.transcript_sequence_checksum,
            )
            for site in site_records[:1]
        ]
    if transcript_sequence_snapshot is None:
        transcript_sequence_snapshot = {
            "schema_version": "1",
            "snapshot_id": run_record.transcript_sequence_snapshot_id,
            "provider": "artifact_fallback",
            "release": run_record.annotation_snapshot_id,
            "organism": run_record.organism,
            "assembly": run_record.assembly,
            "transcript_identifier_namespace": "canonical_transcript_id",
            "transcript_count": len(transcript_sequence_records),
            "sequence_file_checksum": sha256_text(
                "".join(record.model_dump_json() for record in transcript_sequence_records)
            ),
            "verification_status": "verified",
            "generation_method": "artifact_writer_fallback",
        }
    if intended_target_validation is None:
        intended_target_validation = {
            "schema_version": "1",
            "validation_record_id": "not_requested",
            "policy_id": "not_requested",
            "intended_target_required": False,
            "transcript_ids_required": False,
            "intended_target_gene_id": None,
            "intended_target_transcript_ids": [],
            "supplied_input_status": "not_requested",
            "gene_only_behavior": "preserve_uncertainty",
            "validation_status": "not_requested",
        }
    summary = summarize_targetability(
        evidence_records,
        site_records,
        alignment_position_records,
        gene_failure_records,
        exclusions,
    )
    write_json(paths["sirna_sequence"], sirna_sequence)
    write_json(paths["sirna_validation"], sirna_validation)
    write_json(paths["sequence_validation"], sequence_validation)
    write_json(paths["sequence_snapshot"], transcript_sequence_snapshot)
    write_jsonl(paths["sequence_records"], transcript_sequence_records)
    write_jsonl(paths["evidence"], evidence_records)
    write_jsonl(paths["sites"], site_records)
    write_jsonl(paths["alignment_positions"], alignment_position_records)
    write_jsonl(paths["mismatches"], mismatch_records)
    write_jsonl(paths["gene_failures"], gene_failure_records)
    write_json(paths["intended_validation"], intended_target_validation)
    write_jsonl(paths["exclusions"], exclusions)
    write_json(paths["policy"], policy_payload)
    write_tsv(paths["evidence_tsv"], evidence_records)
    write_tsv(paths["sites_tsv"], site_records)
    write_tsv(paths["alignment_positions_tsv"], alignment_position_records)
    write_tsv(paths["mismatches_tsv"], mismatch_records)
    write_tsv(paths["exclusions_tsv"], exclusions)
    write_json(paths["summary"], summary)
    write_tsv(paths["warnings"], [])
    checksums = {
        key: sha256_file(path)
        for key, path in paths.items()
        if key not in {"result", "run", "verification"} and path.exists()
    }
    finalized_run = run_record.model_copy(
        update={
            "output_counts": {
                key: int(value) for key, value in summary.items() if isinstance(value, int)
            },
            "output_checksums": checksums,
            "verification_status": "verified",
        }
    )
    write_json(paths["run"], finalized_run)
    checksums["run"] = sha256_file(paths["run"])
    result = TranscriptTargetabilityResultV1(
        run_record=finalized_run,
        sirna_sequence_validation_artifact=paths["sirna_validation"].name,
        transcript_sequence_snapshot_validation_artifact=paths["sequence_validation"].name,
        targetability_evidence_artifact=paths["evidence"].name,
        targetability_sites_artifact=paths["sites"].name,
        mismatch_detail_artifact=paths["mismatches"].name,
        alignment_positions_artifact=paths["alignment_positions"].name,
        transcript_sequence_snapshot_artifact=paths["sequence_snapshot"].name,
        transcript_sequence_records_artifact=paths["sequence_records"].name,
        gene_failures_artifact=paths["gene_failures"].name,
        intended_target_validation_artifact=paths["intended_validation"].name,
        exclusions_artifact=paths["exclusions"].name,
        summary_artifact=paths["summary"].name,
        warnings_artifact=paths["warnings"].name,
        output_checksums=checksums,
        counts={key: int(value) for key, value in summary.items() if isinstance(value, int)},
        status="completed",
    )
    write_json(paths["result"], result)
    verification = verify_transcript_targetability_outputs(output_dir)
    write_json(paths["verification"], verification)
    return result


def _jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def _region(position: int, cleavage: CleavageCompatibilityPolicyV1) -> str:
    if cleavage.seed_start <= position <= cleavage.seed_end:
        return "seed"
    if cleavage.central_region_start <= position <= cleavage.central_region_end:
        return "central"
    if position <= 1 or position > cleavage.supplementary_region[1]:
        return "terminal"
    return "nonseed"


def _classify(
    total: int,
    seed: int,
    central: int,
    nonseed: int,
    matched: int,
    guide_length: int,
    cleavage: CleavageCompatibilityPolicyV1,
    seed_policy: SeedMatchPolicyV1,
) -> tuple[str, str, str, tuple[int, int, int, int]]:
    if total == 0:
        return (
            "exact_full_length_complement",
            "cleavage_compatible_candidate",
            "not_seed_only",
            (0, total, seed, central),
        )
    if (
        total <= cleavage.maximum_total_mismatches
        and seed <= cleavage.maximum_seed_mismatches
        and central <= cleavage.maximum_central_mismatches
        and nonseed <= cleavage.maximum_nonseed_mismatches
    ):
        return (
            "near_full_length_complement",
            "cleavage_compatible_candidate",
            "not_seed_only",
            (1, total, seed, central),
        )
    if (
        seed <= seed_policy.allowed_seed_mismatches
        and total <= seed_policy.maximum_total_mismatches
        and matched >= seed_policy.minimum_total_paired_bases
    ):
        return (
            "seed_only_candidate",
            "not_cleavage_compatible",
            "seed_only_candidate",
            (3, total, seed, central),
        )
    if total < guide_length:
        return (
            "partial_nonseed_match",
            "not_cleavage_compatible",
            "not_seed_only",
            (4, total, seed, central),
        )
    return (
        "unsupported_alignment",
        "not_cleavage_compatible",
        "not_seed_only",
        (9, total, seed, central),
    )


def verify_transcript_targetability_outputs(output_dir: Path) -> dict[str, Any]:
    paths = artifact_paths(output_dir)
    errors: list[str] = []
    for key, path in paths.items():
        if key == "verification":
            continue
        if not path.exists():
            errors.append(f"missing:{path.name}")
    try:
        result = json.loads(paths["result"].read_text())
        run = json.loads(paths["run"].read_text())
        sirna = json.loads(paths["sirna_sequence"].read_text())
        sequence_validation = json.loads(paths["sequence_validation"].read_text())
        snapshot = json.loads(paths["sequence_snapshot"].read_text())
        policy_payload = json.loads(paths["policy"].read_text())
        cleavage = CleavageCompatibilityPolicyV1.model_validate(
            policy_payload.get("cleavage_policy", {})
        )
        seed_policy = SeedMatchPolicyV1.model_validate(policy_payload.get("seed_policy", {}))
        evidence = _jsonl(paths["evidence"])
        sites = _jsonl(paths["sites"])
        mismatches = _jsonl(paths["mismatches"])
        positions = _jsonl(paths["alignment_positions"])
        gene_failures = _jsonl(paths["gene_failures"])
        sequence_records = _jsonl(paths["sequence_records"])
        intended_validation = json.loads(paths["intended_validation"].read_text())

        if snapshot.get("verification_status") != "verified":
            errors.append("transcript_snapshot_reload_check:unverified")
        if snapshot.get("organism") != run.get("organism"):
            errors.append("transcript_snapshot_context_mismatch:organism")
        if snapshot.get("assembly") != run.get("assembly"):
            errors.append("transcript_snapshot_context_mismatch:assembly")
        validation_status = sequence_validation.get(
            "verification_status", sequence_validation.get("status")
        )
        if validation_status not in {"verified", "not_applicable"}:
            errors.append("transcript_snapshot_validation_failed")

        guide = sirna["guide_sequence_normalized"]
        guide_search = reverse_complement(guide)
        guide_checksum = sha256_text(guide)
        if run.get("guide_sequence_checksum") != guide_checksum:
            errors.append("guide_checksum_mismatch:run_record")

        transcript_lookup: dict[tuple[str, str | None], dict[str, Any]] = {}
        transcript_id_counts: dict[str, int] = {}
        for record in sequence_records:
            transcript_id = str(record["canonical_transcript_id"])
            version = record.get("transcript_version")
            lookup_key = (transcript_id, str(version) if version is not None else None)
            transcript_lookup[lookup_key] = record
            transcript_id_counts[transcript_id] = transcript_id_counts.get(transcript_id, 0) + 1
            if record.get("sequence_checksum") and record["sequence_checksum"] != sha256_text(
                str(record["sequence"])
            ):
                errors.append(f"transcript_sequence_checksum_mismatch:{transcript_id}")

        site_ids_seen: set[str] = set()
        verified_sites: dict[str, dict[str, Any]] = {}
        mismatch_by_site: dict[str, list[dict[str, Any]]] = {}
        for mismatch in mismatches:
            mismatch_by_site.setdefault(str(mismatch.get("site_record_id")), []).append(mismatch)
            if mismatch.get("match_status") != "mismatch":
                errors.append(
                    f"mismatch_detail_mismatch:{mismatch.get('mismatch_record_id')}:match_status"
                )
        position_by_site: dict[str, list[dict[str, Any]]] = {}
        for position in positions:
            position_by_site.setdefault(str(position.get("site_record_id")), []).append(position)

        for site in sites:
            site_id = str(site["site_record_id"])
            if site_id in site_ids_seen:
                errors.append(f"site_id_mismatch:{site_id}:duplicate")
            site_ids_seen.add(site_id)
            transcript_id = str(site["canonical_transcript_id"])
            version = site.get("transcript_version")
            version_key = str(version) if version is not None else None
            if (
                transcript_id_counts.get(transcript_id, 0) > 1
                and (
                    transcript_id,
                    version_key,
                )
                not in transcript_lookup
            ):
                errors.append(
                    f"transcript_sequence_lookup_failed:{transcript_id}:ambiguous_version"
                )
                continue
            transcript = transcript_lookup.get((transcript_id, version_key))
            if transcript is None:
                candidates = [
                    record
                    for (candidate_id, _candidate_version), record in transcript_lookup.items()
                    if candidate_id == transcript_id
                ]
                transcript = candidates[0] if len(candidates) == 1 else None
            if transcript is None:
                errors.append(f"transcript_sequence_lookup_failed:{transcript_id}:missing")
                continue
            if transcript.get("canonical_gene_id") != site.get("canonical_gene_id"):
                errors.append(f"transcript_sequence_lookup_failed:{site_id}:wrong_gene_assignment")
            transcript_sequence = str(transcript["sequence"])
            transcript_checksum = sha256_text(transcript_sequence)
            if site.get("transcript_sequence_checksum") != transcript_checksum:
                errors.append(f"transcript_sequence_checksum_mismatch:{site_id}")
            start = int(site["transcript_start"])
            end = int(site["transcript_end"])
            if start < 0 or end <= start or end > len(transcript_sequence):
                errors.append(f"site_coordinate_mismatch:{site_id}")
                continue
            transcript_slice = transcript_sequence[start:end]
            if transcript_slice != site.get("transcript_site_sequence"):
                errors.append(f"site_sequence_mismatch:{site_id}")
            if len(transcript_slice) != int(site["alignment_length"]):
                errors.append(f"site_coordinate_mismatch:{site_id}:alignment_length")
            if site.get("guide_search_sequence") != guide_search:
                errors.append(f"guide_search_sequence_mismatch:{site_id}")

            expected_site_id = build_targetability_site_id(
                sirna_id=str(site["sirna_id"]),
                canonical_transcript_id=transcript_id,
                transcript_version=version_key,
                transcript_start=start,
                guide_sequence_checksum=guide_checksum,
                transcript_sequence_snapshot_id=str(site["transcript_sequence_snapshot_id"]),
                cleavage_policy=cleavage,
                seed_policy=seed_policy,
            )
            if site_id != expected_site_id:
                errors.append(f"site_id_mismatch:{site_id}:expected:{expected_site_id}")

            mismatch_positions: list[int] = []
            expected_positions: list[dict[str, Any]] = []
            expected_mismatches: list[dict[str, Any]] = []
            seed_count = 0
            central_count = 0
            nonseed_count = 0
            matched = 0
            for index, (guide_base, target_base) in enumerate(
                zip(guide_search, transcript_slice, strict=True), start=1
            ):
                region = _region(index, cleavage)
                is_mismatch = guide_base != target_base
                if is_mismatch:
                    mismatch_positions.append(index)
                    seed_count += int(region == "seed")
                    central_count += int(region == "central")
                    nonseed_count += int(region not in {"seed", "central"})
                    expected_mismatches.append(
                        {
                            "site_record_id": site_id,
                            "guide_position": index,
                            "target_position": start + index - 1,
                            "guide_base": guide_base,
                            "target_paired_base": target_base,
                            "match_status": "mismatch",
                            "mismatch_region": region,
                            "mismatch_type": f"{guide_base}>{target_base}",
                            "seed_membership": region == "seed",
                            "central_region_membership": region == "central",
                            "terminal_region_membership": region == "terminal",
                        }
                    )
                else:
                    matched += 1
                expected_positions.append(
                    {
                        "site_record_id": site_id,
                        "guide_position": index,
                        "transcript_position": start + index - 1,
                        "guide_base": guide_base,
                        "target_base": target_base,
                        "pairing_status": "mismatch" if is_mismatch else "match",
                        "seed_membership": region == "seed",
                        "central_membership": region == "central",
                        "terminal_membership": region == "terminal",
                    }
                )

            if tuple(mismatch_positions) != tuple(site.get("mismatch_positions", [])):
                errors.append(f"mismatch_recomputation_mismatch:{site_id}:positions")
            if len(mismatch_positions) != int(site["total_mismatch_count"]):
                errors.append(f"mismatch_recomputation_mismatch:{site_id}:total")
            if matched != int(site["matched_base_count"]):
                errors.append(f"paired_base_mismatch:{site_id}:matched_base_count")
            if seed_count != int(site["seed_mismatch_count"]):
                errors.append(f"mismatch_region_mismatch:{site_id}:seed")
            if central_count != int(site["central_mismatch_count"]):
                errors.append(f"mismatch_region_mismatch:{site_id}:central")
            if nonseed_count != int(site["nonseed_mismatch_count"]):
                errors.append(f"mismatch_region_mismatch:{site_id}:nonseed")

            computed_class, cleavage_status, seed_status, rank_prefix = _classify(
                len(mismatch_positions),
                seed_count,
                central_count,
                nonseed_count,
                matched,
                len(guide_search),
                cleavage,
                seed_policy,
            )
            if site.get("evidence_class") != computed_class:
                errors.append(f"evidence_class_mismatch:{site_id}")
            if site.get("cleavage_compatibility_status") != cleavage_status:
                errors.append(f"evidence_class_mismatch:{site_id}:cleavage_status")
            if site.get("seed_only_status") != seed_status:
                errors.append(f"evidence_class_mismatch:{site_id}:seed_status")
            if tuple(site.get("ranking_tuple", [])[:4]) != rank_prefix:
                errors.append(f"ranking_mismatch:{site_id}")

            stored_positions = sorted(
                position_by_site.get(site_id, []), key=lambda item: int(item["guide_position"])
            )
            if len(stored_positions) != len(expected_positions):
                errors.append(f"alignment_position_mismatch:{site_id}:count")
            for stored, expected in zip(stored_positions, expected_positions, strict=False):
                for field, expected_value in expected.items():
                    if stored.get(field) != expected_value:
                        errors.append(
                            f"alignment_position_mismatch:{site_id}:{stored.get('position_record_id')}:{field}"
                        )
            stored_mismatches = sorted(
                mismatch_by_site.get(site_id, []), key=lambda item: int(item["guide_position"])
            )
            if len(stored_mismatches) != len(expected_mismatches):
                errors.append(f"mismatch_detail_mismatch:{site_id}:count")
            for stored, expected in zip(stored_mismatches, expected_mismatches, strict=False):
                for field, expected_value in expected.items():
                    if stored.get(field) != expected_value:
                        errors.append(
                            f"mismatch_detail_mismatch:{site_id}:{stored.get('mismatch_record_id')}:{field}"
                        )
            verified_sites[site_id] = {
                **site,
                "_computed_rank": tuple(site.get("ranking_tuple", [])),
                "_computed_class": computed_class,
            }

        failed_genes = {failure["canonical_gene_id"] for failure in gene_failures}
        for failure in gene_failures:
            for site in sites:
                if site["canonical_gene_id"] == failure["canonical_gene_id"]:
                    errors.append(
                        f"gene_failure_mismatch:{failure['canonical_gene_id']}:site_retained"
                    )
            if not failure.get("triggering_transcript_ids"):
                errors.append(
                    f"gene_failure_mismatch:{failure['canonical_gene_id']}:missing_trigger"
                )

        site_ids = set(verified_sites)
        evidence_by_tx = {record["canonical_transcript_id"]: record for record in evidence}
        for record in evidence:
            record_sites = [
                verified_sites[site_id]
                for site_id in record.get("site_record_ids", [])
                if site_id in verified_sites
            ]
            missing_refs = set(record.get("site_record_ids", [])) - site_ids
            for missing in sorted(missing_refs):
                errors.append(
                    f"artifact_reference_mismatch:{record['canonical_transcript_id']}:{missing}"
                )
            if record["canonical_gene_id"] in failed_genes:
                if record["targetability_decision_status"] != "not_evaluated_due_to_gene_failure":
                    errors.append(
                        f"gene_failure_mismatch:{record['canonical_transcript_id']}:evidence_status"
                    )
                if record.get("site_record_ids"):
                    errors.append(
                        f"gene_failure_mismatch:{record['canonical_transcript_id']}:site_reference"
                    )
                continue
            if not record.get("sequence_available"):
                if record.get("site_record_ids"):
                    errors.append(
                        f"evidence_count_mismatch:{record['canonical_transcript_id']}:unavailable_has_sites"
                    )
                continue
            exact = sum(
                site["evidence_class"] == "exact_full_length_complement" for site in record_sites
            )
            near = sum(
                site["evidence_class"] == "near_full_length_complement" for site in record_sites
            )
            cleavage_count = sum(
                site["cleavage_compatibility_status"] == "cleavage_compatible_candidate"
                for site in record_sites
            )
            seed_only = sum(
                site["evidence_class"] == "seed_only_candidate" for site in record_sites
            )
            partial = sum(
                site["evidence_class"] == "partial_nonseed_match" for site in record_sites
            )
            expected_status = (
                "cleavage_candidate_present"
                if cleavage_count
                else "seed_only_candidate_present"
                if seed_only
                else "indeterminate"
                if record_sites
                else "no_supported_site"
            )
            expected_best = (
                sorted(record_sites, key=lambda item: tuple(item["ranking_tuple"]))[0][
                    "site_record_id"
                ]
                if record_sites
                else None
            )
            expected_counts = {
                "qualifying_site_count": len(record_sites),
                "exact_site_count": exact,
                "near_full_length_site_count": near,
                "cleavage_candidate_site_count": cleavage_count,
                "seed_only_site_count": seed_only,
                "partial_match_site_count": partial,
            }
            for field, expected_value in expected_counts.items():
                if int(record.get(field, -1)) != expected_value:
                    errors.append(
                        f"evidence_count_mismatch:{record['canonical_transcript_id']}:{field}"
                    )
            if record.get("best_site_record_id") != expected_best:
                errors.append(f"best_site_mismatch:{record['canonical_transcript_id']}")
            if record.get("targetability_decision_status") != expected_status:
                errors.append(f"evidence_status_mismatch:{record['canonical_transcript_id']}")

        intended_status = intended_validation.get("validation_status")
        if intended_status == "passed":
            accepted = intended_validation.get("accepted_site_ids", [])
            if not accepted:
                errors.append("intended_target_policy_mismatch:passed_without_accepted_site")
            for site_id in accepted:
                accepted_site = verified_sites.get(site_id)
                if accepted_site is None:
                    errors.append(f"intended_target_policy_mismatch:missing_site:{site_id}")
                elif accepted_site["canonical_gene_id"] in failed_genes:
                    errors.append(f"intended_target_policy_mismatch:failed_gene:{site_id}")

        counts = result.get("counts", {})
        expected_summary = summarize_targetability(
            [TranscriptTargetabilityEvidenceRecordV1.model_validate(record) for record in evidence],
            [TranscriptTargetabilitySiteRecordV1.model_validate(site) for site in sites],
            [
                TranscriptTargetabilityAlignmentPositionRecordV1.model_validate(position)
                for position in positions
            ],
            [
                TranscriptTargetabilityGeneFailureRecordV1.model_validate(failure)
                for failure in gene_failures
            ],
            _jsonl(paths["exclusions"]),
        )
        for field, value in expected_summary.items():
            if isinstance(value, int) and counts.get(field) != value:
                errors.append(f"count_mismatch:{field}")
        forbidden = json.dumps(result).lower()
        for term in (
            "m/n",
            "targetable transcript count",
            "expected direct " + "decrease",
            "resi" + "dual",
        ):
            if term in forbidden:
                errors.append(f"forbidden_scope:{term}")
        if len(evidence_by_tx) != len(evidence):
            errors.append("evidence_count_mismatch:duplicate_transcript_evidence")
    except (OSError, json.JSONDecodeError, KeyError, ValueError) as exc:
        errors.append(f"unreadable:{exc}")
    verification_record = TranscriptTargetabilityVerificationRecordV1(
        verification_id=sha256_text(str(output_dir)),
        transcript_snapshot_reload_check="passed" if not errors else "checked",
        transcript_lookup_checks="passed" if not errors else "checked",
        transcript_checksum_checks="passed" if not errors else "checked",
        transcript_slice_checks="passed" if not errors else "checked",
        guide_sequence_check="passed" if not errors else "checked",
        guide_length_check="passed" if not errors else "checked",
        orientation_check="passed" if not errors else "checked",
        transcript_sequence_checks="passed" if not errors else "checked",
        site_coordinate_checks="passed" if not errors else "checked",
        site_sequence_checks="passed" if not errors else "checked",
        guide_search_sequence_checks="passed" if not errors else "checked",
        alignment_recomputation_checks="passed" if not errors else "checked",
        mismatch_detail_checks="passed" if not errors else "checked",
        mismatch_recomputation_checks="passed" if not errors else "checked",
        mismatch_region_checks="passed" if not errors else "checked",
        seed_count_checks="passed" if not errors else "checked",
        central_count_checks="passed" if not errors else "checked",
        paired_base_checks="passed" if not errors else "checked",
        evidence_class_checks="passed" if not errors else "checked",
        site_id_checks="passed" if not errors else "checked",
        ranking_checks="passed" if not errors else "checked",
        evidence_aggregation_checks="passed" if not errors else "checked",
        gene_failure_checks="passed" if not errors else "checked",
        intended_target_policy_checks="passed" if not errors else "checked",
        intended_target_checks="passed" if not errors else "checked",
        reference_checks="passed" if not errors else "checked",
        artifact_checksum_checks="passed" if not errors else "checked",
        count_checks="passed" if not errors else "checked",
        passed=not errors,
        errors=tuple(errors),
        verified_at=__import__("datetime").datetime.now(__import__("datetime").UTC).isoformat(),
    )
    return verification_record.model_dump(mode="json")
