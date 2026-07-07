from __future__ import annotations

import json
from dataclasses import asdict, dataclass, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol, cast

from sirna_offtarget.contracts.stage_results import (
    ExpectedDirectEffectResultV1,
    ExpressionAnalysisResultV2,
    IsoformUncertaintyResultV1,
    MechanisticNetworkResultV2,
    ResidualAttributionResultV1,
    SecondaryEvidenceIntegrationResultV1,
    SequenceAnalysisResultV1,
    TranscriptTargetabilityRatioResultV1,
    TranscriptTargetabilityResultV1,
    sequence_results_from_contract,
)
from sirna_offtarget.execution.contracts import committed_contract_path, load_dependency_contract
from sirna_offtarget.execution.dag import STAGE_NODES
from sirna_offtarget.execution.hashing import artifact_record, dump_json, hash_data, sha256_file
from sirna_offtarget.execution.state import RunContext, StageExecutionResult
from sirna_offtarget.expected_direct_effect.artifacts import (
    sha256_file as expected_direct_sha256_file,
)
from sirna_offtarget.expected_direct_effect.artifacts import (
    verify_expected_direct_effect_outputs,
    write_expected_direct_effect_artifacts,
)
from sirna_offtarget.expected_direct_effect.contracts import (
    ExpectedDirectEffectPolicyV1,
    ExpectedDirectEffectRunRecordV1,
    GeneExpectedDirectEffectRecordV1,
)
from sirna_offtarget.expected_direct_effect.core import compute_expected_direct_effects
from sirna_offtarget.expression import analyze_expression_with_config
from sirna_offtarget.expression.committed import (
    load_committed_normalized_gene_effects_v2,
    load_isoform_gene_effect_inputs,
    load_network_gene_effect_inputs,
    load_pathway_gene_effect_inputs,
)
from sirna_offtarget.expression.contracts_v2 import (
    build_expression_contrast_record_v2,
    build_expression_normalization_run_record_v2,
    build_legacy_gene_effect_records_v2,
    records_as_dicts_v2,
)
from sirna_offtarget.expression.downstream import (
    DownstreamExpressionViewV1,
    IsoformGeneEffectInputViewV1,
    normalized_gene_effect_v2_to_downstream_view,
)
from sirna_offtarget.expression.importer_v2 import import_precomputed_expression_v2
from sirna_offtarget.expression.support import (
    expression_execution_support,
    support_matrix_as_dict,
)
from sirna_offtarget.final_evidence_classification.artifacts import (
    sha256_file as final_evidence_classification_sha256_file,
)
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
from sirna_offtarget.identifiers.resolver_v2 import IdentifierResolverV2
from sirna_offtarget.identifiers.snapshots import (
    inspect_identifier_cache,
    write_identifier_snapshot,
)
from sirna_offtarget.io import (
    read_counts,
    read_regulons,
    read_sample_metadata,
    read_transcripts,
)
from sirna_offtarget.io.serialization import write_tsv
from sirna_offtarget.isoform import analyze_isoforms_from_gene_effect_inputs
from sirna_offtarget.isoform_uncertainty.artifacts import (
    sha256_file as isoform_uncertainty_sha256_file,
)
from sirna_offtarget.isoform_uncertainty.artifacts import (
    verify_isoform_uncertainty_final_outputs,
    write_final_isoform_uncertainty_metadata,
    write_immutable_isoform_uncertainty_artifacts,
)
from sirna_offtarget.isoform_uncertainty.contracts import (
    ExternalProportionPolicy,
    ExternalRowBehavior,
    ExternalTranscriptProportionPolicyV1,
    ExternalTranscriptProportionRecordV1,
    IsoformEvidenceMode,
    IsoformUncertaintyPayloadV1,
    IsoformUncertaintyRunRecordV1,
    MissingTranscriptBehavior,
    TranscriptAnnotationRecordV1,
    TranscriptAnnotationSnapshotV1,
    TranscriptPriorWeightRecordV1,
    TranscriptSetPolicyV1,
)
from sirna_offtarget.isoform_uncertainty.core import (
    assign_isoform_uncertainty_for_gene,
    validate_annotation_snapshot,
)
from sirna_offtarget.pathway import analyze_pathway_enrichment
from sirna_offtarget.pathway.enrichment import (
    build_background_universe,
    build_gene_sets,
    build_memberships_from_provider_results,
    consensus_by_annotation_lineage,
    run_local_ora,
)
from sirna_offtarget.pathway.evidence import build_mechanistic_network_payload_v2
from sirna_offtarget.pathway.membership import (
    load_verified_memberships,
    to_enrichment_memberships,
)
from sirna_offtarget.pathway.providers.loaders import (
    load_enrichment_records,
    load_provider_edge_evidence,
    provider_mode_requires_cache,
    resolve_provider_snapshots,
    summarize_provider_snapshots,
)
from sirna_offtarget.residual_attribution.artifacts import (
    sha256_file as residual_attribution_sha256_file,
)
from sirna_offtarget.residual_attribution.artifacts import (
    verify_residual_attribution_outputs,
    write_residual_attribution_artifacts,
)
from sirna_offtarget.residual_attribution.contracts import (
    GeneResidualAttributionEvidenceRecordV1,
    ResidualAttributionPolicyV1,
    ResidualAttributionRunRecordV1,
    ResidualAttributionUnresolvedRecordV1,
)
from sirna_offtarget.residual_attribution.core import compute_residual_attribution
from sirna_offtarget.residual_attribution.pathway_support import (
    pathway_support_from_mechanistic_network_v2,
)
from sirna_offtarget.secondary_evidence_integration.artifacts import (
    sha256_file as secondary_evidence_integration_sha256_file,
)
from sirna_offtarget.secondary_evidence_integration.artifacts import (
    verify_secondary_evidence_integration_outputs,
    write_secondary_evidence_integration_artifacts,
)
from sirna_offtarget.secondary_evidence_integration.contracts import (
    GeneSecondaryEvidenceIntegrationRecordV1,
    SecondaryEvidenceIntegrationPolicyV1,
    SecondaryEvidenceIntegrationRunRecordV1,
    SecondaryEvidenceIntegrationUnresolvedRecordV1,
)
from sirna_offtarget.secondary_evidence_integration.core import (
    compute_secondary_evidence_integration,
)
from sirna_offtarget.sequence import map_sequence_hits
from sirna_offtarget.transcript_targetability.artifacts import (
    verify_transcript_targetability_outputs,
    write_transcript_targetability_artifacts,
)
from sirna_offtarget.transcript_targetability.contracts import (
    CleavageCompatibilityPolicyV1,
    IntendedTargetValidationPolicyV1,
    MissingTranscriptSequencePolicyV1,
    SeedMatchPolicyV1,
    TranscriptTargetabilityRunRecordV1,
)
from sirna_offtarget.transcript_targetability.core import (
    build_gene_failure_record,
    find_transcript_targetability,
    gene_failed_evidence,
    load_transcript_sequence_snapshot,
    sha256_text,
    unavailable_sequence_evidence,
    validate_intended_target_actual_site,
    validate_sirna_sequence,
    validate_transcript_sequence_snapshot,
)
from sirna_offtarget.transcript_targetability_ratio.artifacts import (
    sha256_file as ratio_sha256_file,
)
from sirna_offtarget.transcript_targetability_ratio.artifacts import (
    verify_transcript_targetability_ratio_outputs,
    write_transcript_targetability_ratio_artifacts,
)
from sirna_offtarget.transcript_targetability_ratio.contracts import (
    GeneTranscriptTargetabilityRatioRecordV1,
    TargetableTranscriptInclusionPolicyV1,
    TranscriptTargetabilityRatioRunRecordV1,
)
from sirna_offtarget.transcript_targetability_ratio.core import (
    compute_transcript_targetability_ratios,
)


class PipelineStage(Protocol):
    @property
    def name(self) -> str: ...

    @property
    def version(self) -> str: ...

    def data_dependencies(self) -> tuple[str, ...]: ...

    def completion_dependencies(self) -> tuple[str, ...]: ...

    def dependencies(self) -> tuple[str, ...]: ...

    def relevant_config_paths(self) -> tuple[str, ...]: ...

    def required_inputs(self, context: RunContext) -> list[Path]: ...

    def execute(self, context: RunContext, attempt_directory: Path) -> StageExecutionResult: ...


def _mechanistic_identifier_resolver(
    context: RunContext, attempt_directory: Path
) -> IdentifierResolverV2:
    organism = context.config.project.organism
    if context.config.pathway.synthetic_mode:
        snapshot = write_identifier_snapshot(
            attempt_directory / "identifier_snapshot_cache", organism
        )
        return IdentifierResolverV2(snapshot, organism, ambiguity_policy="preserve_unresolved")
    cache_dir = context.config.pathway.cache_dir
    if cache_dir is None:
        msg = "production mechanistic runtime requires a verified identifier snapshot cache"
        raise RuntimeError(msg)
    snapshots = inspect_identifier_cache(cache_dir)
    if not snapshots:
        msg = "production mechanistic runtime requires a verified identifier snapshot"
        raise RuntimeError(msg)
    snapshot_id = str(snapshots[0]["snapshot_id"])
    return IdentifierResolverV2(
        cache_dir / snapshot_id, organism, ambiguity_policy="preserve_unresolved"
    )


def _select_config(data: dict[str, Any], paths: tuple[str, ...]) -> dict[str, Any]:
    selected: dict[str, Any] = {}
    for path in paths:
        current: Any = data
        ok = True
        for part in path.split("."):
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                ok = False
                break
        if ok:
            selected[path] = current
    return selected


def relevant_config_hash(context: RunContext, paths: tuple[str, ...]) -> str:
    return hash_data(_select_config(context.resolved_config, paths))


def _pathway_enrichment_options(resolved_config: dict[str, Any]) -> dict[str, Any]:
    pathway = resolved_config.get("pathway", {})
    if isinstance(pathway, dict):
        enrichment = pathway.get("enrichment", {})
        return enrichment if isinstance(enrichment, dict) else {}
    return {}


def _optional_path(value: object) -> Path | None:
    if isinstance(value, str) and value:
        return Path(value)
    if isinstance(value, Path):
        return value
    return None


def _isoform_uncertainty_config(context: RunContext) -> dict[str, Any]:
    config = context.resolved_config.get("isoform_uncertainty", {})
    return config if isinstance(config, dict) else {}


def _load_transcript_annotation_snapshot(
    *,
    cache_dir: Path,
    snapshot_id: str,
    manifest_name: str,
    records_name: str,
) -> tuple[TranscriptAnnotationSnapshotV1, list[TranscriptAnnotationRecordV1], Path]:
    snapshot_dir = cache_dir / snapshot_id
    manifest_path = snapshot_dir / manifest_name
    records_path = snapshot_dir / records_name
    if not manifest_path.exists():
        raise RuntimeError(f"missing isoform uncertainty annotation manifest: {manifest_path}")
    if not records_path.exists():
        raise RuntimeError(f"missing isoform uncertainty transcript records: {records_path}")
    manifest = json.loads(manifest_path.read_text())
    actual_checksum = isoform_uncertainty_sha256_file(records_path)
    expected_checksum = str(manifest.get("source_file_checksum", ""))
    if expected_checksum.startswith("sha256:"):
        expected_checksum = expected_checksum.removeprefix("sha256:")
    if expected_checksum and expected_checksum != actual_checksum:
        raise RuntimeError("isoform uncertainty annotation transcript checksum mismatch")
    manifest["source_file_checksum"] = actual_checksum
    snapshot = TranscriptAnnotationSnapshotV1.model_validate(manifest)
    records = [
        TranscriptAnnotationRecordV1.model_validate(json.loads(line))
        for line in records_path.read_text().splitlines()
        if line.strip()
    ]
    return snapshot, records, records_path


def _load_external_transcript_proportions(
    path: Path | None,
) -> list[ExternalTranscriptProportionRecordV1]:
    if path is None:
        return []
    if not path.exists():
        raise RuntimeError(f"missing external transcript proportion file: {path}")
    rows: list[dict[str, Any]] = []
    if path.suffix.lower() == ".jsonl":
        rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    else:
        import csv

        with path.open(newline="") as handle:
            delimiter = "\t" if path.suffix.lower() == ".tsv" else ","
            reader = csv.DictReader(handle, delimiter=delimiter)
            rows = [dict(row) for row in reader]
    records: list[ExternalTranscriptProportionRecordV1] = []
    checksum = isoform_uncertainty_sha256_file(path)
    for row in rows:
        row = dict(row)
        row["proportion"] = float(row["proportion"])
        row.setdefault("source_file_checksum", checksum)
        records.append(ExternalTranscriptProportionRecordV1.model_validate(row))
    return records


def write_contract(attempt_directory: Path, name: str, version: str, payload: Any) -> Path:
    path = attempt_directory / "outputs" / "stage_result.payload.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    dump_json(path, {"contract": name, "schema_version": version, "payload": payload})
    return path


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows))
    return path


def _write_expression_report_tsv(path: Path, rows: list[dict[str, Any]]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    write_tsv(path, rows)
    return path


def _expression_identifier_resolver(
    context: RunContext, attempt_directory: Path
) -> IdentifierResolverV2:
    organism = context.config.project.organism
    expression_config = context.config.expression
    cache_dir = expression_config.identifier_cache_dir
    backend = (expression_config.backend or "unset").lower().replace("-", "_")
    production_import = (
        backend == "precomputed"
        or expression_config.input_mode == "precomputed_de"
        or expression_config.require_verified_identifier_snapshot
    )
    if cache_dir is None:
        if production_import:
            msg = (
                "production precomputed expression import requires "
                "expression.identifier_cache_dir and expression.identifier_snapshot_id"
            )
            raise RuntimeError(msg)
        snapshot = write_identifier_snapshot(
            attempt_directory / "identifier_snapshot_cache", organism
        )
    else:
        if expression_config.identifier_snapshot_id:
            snapshot = cache_dir / expression_config.identifier_snapshot_id
            if not snapshot.exists():
                msg = f"configured expression identifier snapshot does not exist: {snapshot}"
                raise RuntimeError(msg)
        elif production_import:
            msg = (
                "production precomputed expression import requires "
                "expression.identifier_snapshot_id"
            )
            raise RuntimeError(msg)
        else:
            snapshot = write_identifier_snapshot(cache_dir, organism)
    return IdentifierResolverV2(
        snapshot,
        organism,
        ambiguity_policy=expression_config.identifier_ambiguity_policy,
    )


def _expression_validation_payload(
    context: RunContext,
    support: Any,
    fatal_errors: list[str],
    warnings: list[str],
) -> dict[str, Any]:
    config = context.config.expression
    checksums: dict[str, str] = {}
    for path in (config.count_matrix, config.sample_metadata, config.precomputed_table):
        if path is not None and path.exists():
            checksums[str(path)] = sha256_file(path)
    return {
        "input_mode": support.input_mode,
        "value_scale": config.value_scale,
        "schema_validation": "passed" if not fatal_errors else "failed",
        "sample_validation": "passed",
        "contrast_validation": "passed",
        "numeric_validation": "passed" if not fatal_errors else "failed",
        "duplicate_gene_handling": config.duplicate_gene_policy,
        "missing_value_handling": "row-level nullable fields preserved in V2",
        "p_value_validation": "nonmissing p-values must be within [0,1]",
        "execution_support_level": support.execution_support_level,
        "fatal_errors": fatal_errors,
        "warnings": warnings,
        "source_checksums": checksums,
    }


def _filtering_summary_rows(records: list[Any]) -> list[dict[str, Any]]:
    def count(field: str, values: set[str]) -> int:
        return sum(1 for record in records if getattr(record, field) in values)

    missing_effect = sum(1 for record in records if record.canonical_log2_fold_change is None)
    missing_p = sum(1 for record in records if record.raw_p_value is None)
    missing_padj = sum(1 for record in records if record.adjusted_p_value is None)
    unresolved = sum(1 for record in records if record.canonical_gene_id is None)
    ambiguous = sum(1 for record in records if record.identifier_ambiguity_status == "ambiguous")
    organism_mismatch = sum(1 for record in records if not record.identifier_organism_match)
    return [
        {"category": "total_input_rows", "count": len(records)},
        {"category": "tested", "count": count("tested_status", {"tested"})},
        {"category": "filtered_low_count", "count": count("low_count_status", {"low_count"})},
        {
            "category": "independently_filtered",
            "count": count("filter_status", {"independent_filtered"}),
        },
        {"category": "outlier_filtered", "count": count("filter_status", {"outlier_filtered"})},
        {"category": "missing_effect", "count": missing_effect},
        {"category": "missing_p_value", "count": missing_p},
        {"category": "missing_adjusted_p_value", "count": missing_padj},
        {
            "category": "model_not_estimable",
            "count": count("model_status", {"model_not_estimable"}),
        },
        {"category": "model_failure", "count": count("model_status", {"model_failure"})},
        {"category": "invalid_row", "count": 0},
        {"category": "unresolved_identifier", "count": unresolved},
        {"category": "ambiguous_identifier", "count": ambiguous},
        {"category": "organism_mismatch", "count": organism_mismatch},
        {"category": "retained_canonical_records", "count": len(records)},
    ]


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _identifier_snapshot_checksum(resolver: IdentifierResolverV2) -> str | None:
    records_path = resolver.snapshot_path / "records.jsonl"
    return sha256_file(records_path) if records_path.exists() else None


def _expression_v2_record_counts(
    records: list[Any],
    downstream_view: DownstreamExpressionViewV1,
) -> dict[str, int]:
    return {
        "total_source_rows": len(records),
        "normalized_gene_effects_v2": len(records),
        "records_with_canonical_gene_ids": sum(
            1 for record in records if record.canonical_gene_id is not None
        ),
        "unresolved_identifier_count": sum(
            1 for record in records if record.identifier_ambiguity_status == "unresolved"
        ),
        "ambiguous_identifier_count": sum(
            1 for record in records if record.identifier_ambiguity_status == "ambiguous"
        ),
        "missing_effect_count": sum(
            1 for record in records if record.canonical_log2_fold_change is None
        ),
        "tested_count": sum(1 for record in records if record.tested_status == "tested"),
        "not_tested_count": sum(
            1 for record in records if record.tested_status in {"not_tested", "untested"}
        ),
        "filtered_count": sum(
            1
            for record in records
            if record.filter_status not in {"not_filtered", "imported_missing"}
            or record.low_count_status == "low_count"
        ),
        "model_not_estimable_count": sum(
            1 for record in records if record.model_status == "model_not_estimable"
        ),
        "model_failure_count": sum(
            1 for record in records if record.model_status == "model_failure"
        ),
        "downstream_view_included_count": len(downstream_view.records),
        "downstream_view_excluded_count": len(downstream_view.exclusions),
        "compatibility_warning_count": len(downstream_view.exclusions),
    }


def _downstream_view_payload(view: DownstreamExpressionViewV1) -> dict[str, Any]:
    return {
        "canonical": False,
        "deprecated": True,
        "source_contract": "ExpressionAnalysisResultV2",
        "generated_from_v2": True,
        "downstream_view_name": view.view_name,
        "included_record_count": len(view.records),
        "excluded_record_count": len(view.exclusions),
        "records": [asdict(record) for record in view.records],
        "exclusions": [asdict(exclusion) for exclusion in view.exclusions],
        "warnings": [exclusion.warning for exclusion in view.exclusions],
    }


def _write_isoform_expression_input_artifacts(
    attempt_directory: Path, view: IsoformGeneEffectInputViewV1
) -> list[Path]:
    records = [asdict(record) for record in view.records]
    exclusions = [asdict(exclusion) for exclusion in view.exclusions]
    outputs = attempt_directory / "outputs"
    jsonl_output = outputs / "isoform_expression_input_v1.jsonl"
    tsv_output = outputs / "isoform_expression_input_v1.tsv"
    exclusions_output = outputs / "isoform_expression_input_exclusions.tsv"
    summary_output = outputs / "isoform_expression_input_summary.json"
    write_jsonl(jsonl_output, records)
    _write_expression_report_tsv(tsv_output, records)
    _write_expression_report_tsv(exclusions_output, exclusions)
    dump_json(
        summary_output,
        {
            "view_name": view.view_name,
            "schema_version": view.schema_version,
            **view.summary,
        },
    )
    return [jsonl_output, tsv_output, exclusions_output, summary_output]


def _write_downstream_expression_input_artifacts(
    attempt_directory: Path,
    view: DownstreamExpressionViewV1,
    basename: str,
) -> list[Path]:
    records = [asdict(record) for record in view.records]
    exclusions = [asdict(exclusion) for exclusion in view.exclusions]
    outputs = attempt_directory / "outputs"
    jsonl_output = outputs / f"{basename}.jsonl"
    exclusions_output = outputs / f"{basename}_exclusions.tsv"
    summary_output = outputs / f"{basename}_summary.json"
    write_jsonl(jsonl_output, records)
    _write_expression_report_tsv(exclusions_output, exclusions)
    dump_json(summary_output, _downstream_input_summary(view))
    return [jsonl_output, exclusions_output, summary_output]


def _downstream_input_summary(view: DownstreamExpressionViewV1) -> dict[str, Any]:
    reason_counts: dict[str, int] = {}
    for exclusion in view.exclusions:
        reason_counts[exclusion.exclusion_reason] = (
            reason_counts.get(exclusion.exclusion_reason, 0) + 1
        )
    return {
        "view_name": view.view_name,
        "schema_version": "1",
        "total_v2_records_examined": len(view.records) + len(view.exclusions),
        "included_records": len(view.records),
        "excluded_records": len(view.exclusions),
        "missing_effect_count": reason_counts.get("canonical_effect_unavailable", 0),
        "unresolved_identifier_count": reason_counts.get("canonical_gene_id_unavailable", 0),
        "missing_padj_but_included_count": sum(
            1 for record in view.records if record.adjusted_p_value is None
        ),
        "unavailable_replicate_consistency_but_included_count": len(view.records),
        "shrunken_effect_count": sum(
            1
            for record in view.records
            if record.canonical_effect_source
            in {"imported_shrunken_log2fc", "backend_shrunken_log2fc"}
        ),
        "unshrunken_effect_count": sum(
            1
            for record in view.records
            if record.canonical_effect_source
            not in {"imported_shrunken_log2fc", "backend_shrunken_log2fc"}
        ),
        "exclusion_reason_counts": dict(sorted(reason_counts.items())),
    }


def _provider_coverage_rows(
    provider_evidence_edges: list[Any],
    consensus_edges: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    provider_counts: dict[str, dict[str, Any]] = {}
    for edge in provider_evidence_edges:
        row = edge if isinstance(edge, dict) else edge.model_dump(mode="json")
        provider = str(row.get("provider", "unknown"))
        stats = provider_counts.setdefault(
            provider,
            {
                "provider": provider,
                "evidence_edge_count": 0,
                "signed_evidence_edge_count": 0,
                "unsigned_or_unknown_edge_count": 0,
                "consensus_edge_participation_count": 0,
                "reference_count": 0,
                "snapshot_count": 0,
            },
        )
        stats["evidence_edge_count"] += 1
        if row.get("sign") in {"positive", "negative", "conflicting"}:
            stats["signed_evidence_edge_count"] += 1
        else:
            stats["unsigned_or_unknown_edge_count"] += 1
        stats["reference_count"] += len(row.get("references", ()) or ())
        if row.get("retrieval_snapshot"):
            stats["snapshot_count"] += 1
    for edge in consensus_edges:
        for provider in edge.get("provider_sources", ()) or ():
            stats = provider_counts.setdefault(
                str(provider),
                {
                    "provider": str(provider),
                    "evidence_edge_count": 0,
                    "signed_evidence_edge_count": 0,
                    "unsigned_or_unknown_edge_count": 0,
                    "consensus_edge_participation_count": 0,
                    "reference_count": 0,
                    "snapshot_count": 0,
                },
            )
            stats["consensus_edge_participation_count"] += 1
    return [provider_counts[key] for key in sorted(provider_counts)]


def write_stage_report(
    attempt_directory: Path,
    *,
    stage_name: str,
    status: str,
    purpose: str,
    metrics: dict[str, Any],
    warnings: list[str],
    outputs: list[Path],
    explanation: str = "",
) -> dict[str, str]:
    report_json = attempt_directory / "report.json"
    report_html = attempt_directory / "report.html"
    payload = {
        "stage": stage_name,
        "status": status,
        "purpose": purpose,
        "metrics": metrics,
        "warnings": warnings,
        "generated_outputs": [str(path.relative_to(attempt_directory)) for path in outputs],
        "explanation": explanation,
    }
    dump_json(report_json, payload)
    report_html.write_text(
        "<html><body>"
        f"<h1>{stage_name}</h1><p>Status: {status}</p><p>{purpose}</p>"
        f"<pre>{json.dumps(payload, indent=2, default=str)}</pre>"
        "</body></html>"
    )
    return {"json": str(report_json), "html": str(report_html)}


def _input_files(context: RunContext, names: tuple[str, ...]) -> list[Path]:
    config = context.config
    mapping = {
        "transcripts": config.sequence.transcript_fasta,
        "annotation": config.sequence.annotation_gtf,
        "counts": config.expression.count_matrix,
        "metadata": config.expression.sample_metadata,
        "network": config.pathway.network_file,
        "regulons": config.pathway.regulon_file,
    }
    return [mapping[name] for name in names]


@dataclass(frozen=True)
class FunctionStage:
    name: str
    version: str
    config_paths: tuple[str, ...]
    input_names: tuple[str, ...]
    purpose: str

    def data_dependencies(self) -> tuple[str, ...]:
        return STAGE_NODES[self.name].data_dependencies

    def completion_dependencies(self) -> tuple[str, ...]:
        return STAGE_NODES[self.name].completion_dependencies

    def dependencies(self) -> tuple[str, ...]:
        return STAGE_NODES[self.name].dependencies

    def relevant_config_paths(self) -> tuple[str, ...]:
        return self.config_paths

    def required_inputs(self, context: RunContext) -> list[Path]:
        inputs = _input_files(context, self.input_names)
        if self.name == "isoform_uncertainty" and context.config.isoform_uncertainty.enabled:
            iu_config = context.config.isoform_uncertainty
            if iu_config.annotation_cache_dir and iu_config.annotation_snapshot_id:
                snapshot_dir = iu_config.annotation_cache_dir / iu_config.annotation_snapshot_id
                inputs.extend(
                    [
                        snapshot_dir / iu_config.manifest_artifact,
                        snapshot_dir / iu_config.transcript_records_artifact,
                    ]
                )
            if iu_config.external_proportions_file:
                inputs.append(iu_config.external_proportions_file)
        if (
            self.name == "transcript_targetability"
            and context.config.transcript_targetability.enabled
        ):
            tt_config = context.config.transcript_targetability
            if (
                tt_config.transcript_sequence_cache_dir
                and tt_config.transcript_sequence_snapshot_id
            ):
                snapshot_dir = (
                    tt_config.transcript_sequence_cache_dir
                    / tt_config.transcript_sequence_snapshot_id
                )
                inputs.append(snapshot_dir / tt_config.manifest_artifact)
        return inputs

    def execute(self, context: RunContext, attempt_directory: Path) -> StageExecutionResult:
        context.dependency_consumption.clear()
        method = getattr(self, f"_execute_{self.name}")
        result: StageExecutionResult = method(context, attempt_directory)
        return result

    def _record_consumed(
        self,
        context: RunContext,
        *,
        dependency_stage: str,
        contract: Any,
        artifacts: list[str] | None = None,
        payload_fields: list[str] | None = None,
    ) -> None:
        context.record_dependency_consumption(
            dependency_stage=dependency_stage,
            dependency_type="data"
            if dependency_stage in self.data_dependencies()
            else "completion",
            contract_name=contract.contract_name,
            contract_version=contract.schema_version,
            contract_sha256=sha256_file(committed_contract_path(context.run_dir, dependency_stage)),
            artifacts=artifacts,
            payload_fields=payload_fields,
        )

    def _execute_validate(
        self, context: RunContext, attempt_directory: Path
    ) -> StageExecutionResult:
        missing = [str(path) for path in self.required_inputs(context) if not path.exists()]
        if missing:
            raise FileNotFoundError(f"missing required input files: {missing}")
        output = write_contract(
            attempt_directory,
            "ValidationResultV1",
            "1",
            {
                "yaml_schema_version": context.resolved_config.get("schema_version", "1"),
                "missing_files": missing,
                "dag_stage_count": len(STAGE_NODES),
            },
        )
        return StageExecutionResult(
            [output],
            {"missing_files": len(missing)},
            [],
            "ValidationResultV1",
            payload={
                "yaml_schema_version": context.resolved_config.get("schema_version", "1"),
                "missing_files": missing,
                "dag_stage_count": len(STAGE_NODES),
            },
        )

    def _execute_prepare_inputs(
        self, context: RunContext, attempt_directory: Path
    ) -> StageExecutionResult:
        files = [artifact_record(path) for path in self.required_inputs(context)]
        output = write_contract(
            attempt_directory,
            "PreparedInputsResultV1",
            "1",
            {"inputs": files},
        )
        return StageExecutionResult(
            [output],
            {"input_file_count": len(files)},
            [],
            "PreparedInputsResultV1",
            payload={"inputs": files},
        )

    def _execute_map_identifiers(
        self, context: RunContext, attempt_directory: Path
    ) -> StageExecutionResult:
        transcripts = read_transcripts(context.config.sequence.transcript_fasta)
        genes = sorted({record.gene for record in transcripts})
        output = write_contract(
            attempt_directory,
            "IdentifierMappingResultV1",
            "1",
            {
                "mapped_count": len(genes),
                "unmapped_count": 0,
                "ambiguous_count": 0,
                "genes": genes,
            },
        )
        return StageExecutionResult(
            [output],
            {"mapped_count": len(genes)},
            [],
            "IdentifierMappingResultV1",
            payload={
                "mapped_count": len(genes),
                "unmapped_count": 0,
                "ambiguous_count": 0,
                "genes": genes,
            },
        )

    def _execute_sequence_analysis(
        self, context: RunContext, attempt_directory: Path
    ) -> StageExecutionResult:
        transcripts = read_transcripts(context.config.sequence.transcript_fasta)
        hits = map_sequence_hits(
            context.config.sirna.guide_sequence,
            context.config.sirna.passenger_sequence
            if context.config.sequence.search_passenger_strand
            else None,
            transcripts,
            context.config.sequence.seed_lengths,
            context.config.sequence.allow_gu_wobble,
        )
        payload = {gene: asdict(evidence) for gene, evidence in hits.items()}
        site_count = sum(len(t.binding_sites) for item in hits.values() for t in item.transcripts)
        output = write_contract(attempt_directory, "SequenceAnalysisResultV1", "1", payload)
        return StageExecutionResult(
            [output],
            {
                "gene_count": len(hits),
                "total_sites": site_count,
                "transcript_count": len(transcripts),
            },
            [],
            "SequenceAnalysisResultV1",
            payload={
                "sequence_hits": payload,
                "total_sites": site_count,
                "transcript_count": len(transcripts),
            },
        )

    def _execute_expression_analysis(
        self, context: RunContext, attempt_directory: Path
    ) -> StageExecutionResult:
        started_at = _utc_now()
        expression_config = context.config.expression
        if (
            expression_config.backend
            and expression_config.backend.lower().replace("-", "_") == "precomputed"
            and expression_config.input_mode == "raw_counts"
        ):
            expression_config = expression_config.model_copy(
                update={"input_mode": "precomputed_de"}
            )
        metadata = read_sample_metadata(context.config.expression.sample_metadata)
        support = expression_execution_support(expression_config)
        resolver = _expression_identifier_resolver(context, attempt_directory)
        identifier_checksum = _identifier_snapshot_checksum(resolver)
        if (
            support.input_mode == "precomputed_de"
            and expression_config.precomputed_table is not None
        ):
            imported = import_precomputed_expression_v2(
                config=expression_config,
                organism=context.config.project.organism,
                metadata=metadata,
                resolver=resolver,
                counts_path=expression_config.count_matrix,
                metadata_path=expression_config.sample_metadata,
            )
            contrast_v2 = imported.contrast
            normalization_run_v2 = replace(
                imported.normalization_run,
                started_at=started_at,
                completed_at=None,
                status="pending",
                identifier_snapshot_checksum=identifier_checksum,
                identifier_snapshot_verified=identifier_checksum is not None,
            )
            normalized_effects_v2 = imported.records
            resolutions = {
                resolution.input_identifier: resolution
                for resolution in imported.identifier_resolutions
            }
            validation_payload = imported.validation_payload
            warning_rows = imported.warning_rows
            demonstration_warnings: list[str] = []
        else:
            counts = read_counts(expression_config.count_matrix)
            results = analyze_expression_with_config(counts, metadata, expression_config)
            resolutions = {gene: resolver.resolve_expression_gene(gene) for gene in sorted(results)}
            contrast_v2 = build_expression_contrast_record_v2(expression_config)
            source_result_path = expression_config.precomputed_table
            source_checksum_path = (
                expression_config.precomputed_table
                if expression_config.precomputed_table is not None
                else expression_config.count_matrix
            )
            source_checksum = (
                sha256_file(source_checksum_path) if source_checksum_path.exists() else ""
            )
            normalization_run_v2 = build_expression_normalization_run_record_v2(
                config=expression_config,
                organism=context.config.project.organism,
                support=support,
                counts_path=expression_config.count_matrix,
                metadata_path=expression_config.sample_metadata,
                source_result_path=source_result_path,
                metadata=metadata,
                identifier_snapshot_id=resolver.snapshot_id,
                started_at=started_at,
                completed_at=None,
                warnings=tuple(support.limitations),
                identifier_snapshot_checksum=identifier_checksum,
                identifier_snapshot_verified=identifier_checksum is not None,
            )
            normalization_run_v2 = replace(normalization_run_v2, status="pending")
            normalized_effects_v2 = build_legacy_gene_effect_records_v2(
                results=results,
                config=expression_config,
                organism=context.config.project.organism,
                contrast_id=contrast_v2.contrast_id,
                normalization_run_id=normalization_run_v2.normalization_run_id,
                source_checksum=source_checksum,
                resolutions=resolutions,
            )
            validation_payload = _expression_validation_payload(
                context,
                support,
                fatal_errors=[],
                warnings=list(support.limitations),
            )
            warning_rows = [
                {"record_id": record.record_id, "warning": warning}
                for record in normalized_effects_v2
                for warning in record.warnings
            ]
            demonstration_warnings = (
                ["demonstration-only synthetic expression backend selected explicitly"]
                if any(result.demonstration_only for result in results.values())
                else []
            )
        downstream_view = normalized_gene_effect_v2_to_downstream_view(normalized_effects_v2)
        analysis_output_v2 = attempt_directory / "outputs" / "expression_analysis_result_v2.json"
        compatibility_output = (
            attempt_directory / "outputs" / "expression_downstream_compatibility_view_v1.json"
        )
        normalization_output_v2 = (
            attempt_directory / "outputs" / "expression_normalization_run_v2.json"
        )
        contrast_output_v2 = attempt_directory / "outputs" / "expression_contrasts_v2.json"
        effects_output_v2 = attempt_directory / "outputs" / "normalized_gene_effects_v2.jsonl"
        effects_tsv_v2 = attempt_directory / "outputs" / "normalized_gene_effects_v2.tsv"
        validation_output = attempt_directory / "outputs" / "expression_input_validation.json"
        filtering_summary_output = (
            attempt_directory / "outputs" / "expression_filtering_summary.tsv"
        )
        identifier_output_v2 = (
            attempt_directory / "outputs" / "expression_identifier_resolutions_v2.jsonl"
        )
        warnings_output = attempt_directory / "outputs" / "expression_warnings.tsv"
        support_output = attempt_directory / "outputs" / "expression_execution_support.json"
        effect_dicts_v2 = records_as_dicts_v2(normalized_effects_v2)
        dump_json(contrast_output_v2, {"contrasts": [asdict(contrast_v2)]})
        write_jsonl(effects_output_v2, effect_dicts_v2)
        _write_expression_report_tsv(effects_tsv_v2, effect_dicts_v2)
        _write_expression_report_tsv(
            filtering_summary_output,
            _filtering_summary_rows(normalized_effects_v2),
        )
        write_jsonl(
            identifier_output_v2, [resolution.asdict() for resolution in resolutions.values()]
        )
        warning_rows.extend(
            {"record_id": item.source_expression_v2_record_id, "warning": item.warning}
            for item in downstream_view.exclusions
        )
        _write_expression_report_tsv(warnings_output, warning_rows)
        dump_json(support_output, support_matrix_as_dict(expression_config))
        validation_payload["identifier_snapshot_validation"] = (
            "passed" if identifier_checksum else "failed"
        )
        validation_payload["raw_count_normalization_execution"] = (
            "not_applicable" if support.input_mode == "precomputed_de" else "passed"
        )
        validation_payload["downstream_view_generation"] = {
            "state": "passed",
            "included_count": len(downstream_view.records),
            "excluded_count": len(downstream_view.exclusions),
        }
        dump_json(validation_output, validation_payload)
        dump_json(compatibility_output, _downstream_view_payload(downstream_view))
        output_checksum_targets = [
            contrast_output_v2,
            effects_output_v2,
            effects_tsv_v2,
            validation_output,
            filtering_summary_output,
            identifier_output_v2,
            warnings_output,
            support_output,
            compatibility_output,
        ]
        completed_at = _utc_now()
        normalization_run_v2 = replace(
            normalization_run_v2,
            completed_at=completed_at,
            status="completed",
            output_checksums={
                path.name: sha256_file(path) for path in output_checksum_targets if path.exists()
            },
        )
        normalization_run_payload_v2 = asdict(normalization_run_v2)
        dump_json(normalization_output_v2, normalization_run_payload_v2)
        analysis_artifacts = [
            normalization_output_v2,
            contrast_output_v2,
            effects_output_v2,
            effects_tsv_v2,
            validation_output,
            filtering_summary_output,
            identifier_output_v2,
            warnings_output,
            support_output,
            compatibility_output,
        ]
        record_counts = _expression_v2_record_counts(normalized_effects_v2, downstream_view)
        record_counts["identifier_resolutions_v2"] = len(resolutions)
        artifact_checksums = {
            path.name: sha256_file(path) for path in analysis_artifacts if path.exists()
        }
        analysis_payload = {
            "canonical": True,
            "normalization_run_artifact": normalization_output_v2.name,
            "contrasts_artifact": contrast_output_v2.name,
            "normalized_gene_effects_artifact": effects_output_v2.name,
            "identifier_resolutions_artifact": identifier_output_v2.name,
            "input_validation_artifact": validation_output.name,
            "filtering_summary_artifact": filtering_summary_output.name,
            "warnings_artifact": warnings_output.name,
            "execution_support_artifact": support_output.name,
            "downstream_compatibility_artifact": compatibility_output.name,
            "artifact_checksums": artifact_checksums,
            "record_counts": record_counts,
            "compatibility_metadata": {
                "canonical": False,
                "deprecated": True,
                "generated_from_v2": True,
                "included_record_count": len(downstream_view.records),
                "excluded_record_count": len(downstream_view.exclusions),
            },
        }
        dump_json(analysis_output_v2, {"schema_version": "2", **analysis_payload})
        warnings = demonstration_warnings + [item.warning for item in downstream_view.exclusions]
        output = write_contract(
            attempt_directory, "ExpressionAnalysisResultV2", "2", analysis_payload
        )
        return StageExecutionResult(
            [
                output,
                analysis_output_v2,
                compatibility_output,
                normalization_output_v2,
                contrast_output_v2,
                effects_output_v2,
                effects_tsv_v2,
                validation_output,
                filtering_summary_output,
                identifier_output_v2,
                warnings_output,
                support_output,
            ],
            {"sample_count": len(metadata), **record_counts},
            warnings,
            "ExpressionAnalysisResultV2",
            contract_version="2",
            payload=analysis_payload,
        )

    def _execute_isoform_uncertainty(
        self, context: RunContext, attempt_directory: Path
    ) -> StageExecutionResult:
        started_at = _utc_now()
        config = context.config.isoform_uncertainty
        warnings: list[str] = []
        output_dir = attempt_directory / "outputs"
        if not config.enabled:
            expression_contract = load_dependency_contract(
                context,
                dependency_stage="expression_analysis",
                expected_contract=ExpressionAnalysisResultV2,
            )
            self._record_consumed(
                context,
                dependency_stage="expression_analysis",
                contract=expression_contract,
                artifacts=["normalized_gene_effects_v2.jsonl"],
                payload_fields=["normalized_gene_effects_artifact"],
            )
            counts: dict[str, int] = {
                "expression_records": 0,
                "annotation_records": 0,
                "external_transcript_proportions": 0,
                "gene_isoform_uncertainty_records": 0,
                "transcript_prior_weight_records": 0,
                "transcript_set_exclusion_records": 0,
            }
            artifact_checksums = write_immutable_isoform_uncertainty_artifacts(
                output_dir=output_dir,
                gene_records=[],
                weight_records=[],
                exclusion_records=[],
                annotation_validation={"status": "not_applicable"},
                method_selection={"stage_enabled": False},
                input_validation={"status": "not_applicable"},
                summary={"stage_enabled": False},
            )
            run_record = IsoformUncertaintyRunRecordV1(
                run_id=context.run_id,
                expression_stage_contract=expression_contract.contract_name,
                expression_artifact_checksum="not_applicable",
                annotation_snapshot_id="not_applicable",
                annotation_checksum="not_applicable",
                transcript_set_policy_id="not_applicable",
                isoform_evidence_mode="insufficient_evidence",
                evidence_mode="insufficient_evidence",
                weight_policy="disabled",
                numerical_tolerance=0.0,
                organism=context.config.project.organism,
                assembly=context.config.project.genome_build,
                identifier_snapshot_id=None,
                identifier_snapshot_checksum=None,
                software_version="sirna-offtarget",
                started_at=started_at,
                completed_at=_utc_now(),
                status="completed",
                verification_status="not_applicable",
                record_counts=counts,
                referenced_artifact_checksums=artifact_checksums,
                warnings=("isoform uncertainty stage disabled by configuration",),
            )
            payload = IsoformUncertaintyPayloadV1(
                run_record=run_record, counts=counts, artifacts=artifact_checksums
            )
            metadata_checksums = write_final_isoform_uncertainty_metadata(
                output_dir=output_dir,
                run_record=run_record,
                result_payload=payload.model_dump(mode="json"),
            )
            verification = verify_isoform_uncertainty_final_outputs(output_dir)
            if not verification.passed:
                raise RuntimeError(
                    "isoform uncertainty final artifact verification failed: "
                    + ", ".join(verification.errors)
                )
            payload = IsoformUncertaintyPayloadV1(
                run_record=run_record,
                counts=counts,
                artifacts={**artifact_checksums, **metadata_checksums},
            )
            artifacts = sorted(output_dir.iterdir())
            return StageExecutionResult(
                artifacts,
                {"stage_enabled": False},
                ["isoform uncertainty stage disabled by configuration"],
                "IsoformUncertaintyResultV1",
                payload=payload,
            )

        expression_contract = load_dependency_contract(
            context,
            dependency_stage="expression_analysis",
            expected_contract=ExpressionAnalysisResultV2,
        )
        self._record_consumed(
            context,
            dependency_stage="expression_analysis",
            contract=expression_contract,
            artifacts=["normalized_gene_effects_v2.jsonl"],
            payload_fields=["normalized_gene_effects_artifact"],
        )
        if config.annotation_cache_dir is None or config.annotation_snapshot_id is None:
            raise RuntimeError(
                "isoform uncertainty production execution requires "
                "isoform_uncertainty.annotation_cache_dir and annotation_snapshot_id"
            )
        snapshot, annotation_records, annotation_path = _load_transcript_annotation_snapshot(
            cache_dir=config.annotation_cache_dir,
            snapshot_id=config.annotation_snapshot_id,
            manifest_name=config.manifest_artifact,
            records_name=config.transcript_records_artifact,
        )
        if (
            config.require_verified_annotation_snapshot
            and snapshot.verification_status != "verified"
        ):
            raise RuntimeError(
                "isoform uncertainty production execution requires verified annotation"
            )
        if snapshot.organism != context.config.project.organism:
            raise RuntimeError("isoform uncertainty annotation organism does not match project")
        if snapshot.assembly != context.config.project.genome_build:
            raise RuntimeError("isoform uncertainty annotation assembly does not match project")
        identifier_snapshot_id = (
            config.identifier_snapshot_id or context.config.expression.identifier_snapshot_id
        )
        identifier_snapshot_checksum = config.identifier_snapshot_checksum
        if config.require_verified_identifier_snapshot and (
            not identifier_snapshot_id or not identifier_snapshot_checksum
        ):
            raise RuntimeError(
                "isoform uncertainty production execution requires verified identifier "
                "snapshot id and checksum"
            )
        annotation_validation = validate_annotation_snapshot(
            snapshot,
            annotation_records,
            require_verified=config.require_verified_annotation_snapshot,
        )
        if annotation_validation.fatal_errors:
            raise RuntimeError(
                "isoform uncertainty annotation validation failed: "
                + ", ".join(annotation_validation.fatal_errors)
            )
        transcript_policy = TranscriptSetPolicyV1(
            include_protein_coding=config.include_protein_coding,
            include_retained_intron=config.include_retained_intron,
            include_nonsense_mediated_decay=config.include_nonsense_mediated_decay,
            include_processed_transcript=config.include_processed_transcript,
            include_noncoding=config.include_noncoding,
            include_pseudogene=config.include_pseudogene,
            include_readthrough=config.include_readthrough,
            allow_alternative_contigs=config.allow_alternative_contigs,
            allow_deprecated_transcripts=config.allow_deprecated_transcripts,
            require_sequence_reference=config.require_sequence_reference,
            allow_unresolved_gene_mapping=config.allow_unresolved_gene_mapping,
            allowed_transcript_support_levels=tuple(config.allowed_transcript_support_levels)
            if config.allowed_transcript_support_levels
            else None,
        )
        if config.allow_unresolved_gene_mapping:
            warnings.append(
                "isoform_uncertainty.allow_unresolved_gene_mapping is deprecated and ignored; "
                "unresolved gene mappings are excluded from production eligibility"
            )
        external_policy = ExternalTranscriptProportionPolicyV1(
            invalid_proportion_behavior=cast(
                ExternalProportionPolicy, config.invalid_proportion_behavior
            ),
            missing_transcript_behavior=cast(
                MissingTranscriptBehavior, config.missing_transcript_behavior
            ),
            duplicate_row_behavior=cast(ExternalRowBehavior, config.duplicate_row_behavior),
            unknown_transcript_behavior=cast(
                ExternalRowBehavior, config.unknown_transcript_behavior
            ),
            wrong_gene_mapping_behavior=cast(
                ExternalRowBehavior, config.wrong_gene_mapping_behavior
            ),
            small_rounding_tolerance=config.small_rounding_tolerance,
            material_sum_tolerance=config.material_sum_tolerance,
            allow_renormalization=config.allow_renormalization,
        )
        external_records = _load_external_transcript_proportions(config.external_proportions_file)
        external_by_gene: dict[str, list[ExternalTranscriptProportionRecordV1]] = {}
        for record in external_records:
            external_by_gene.setdefault(record.canonical_gene_id, []).append(record)
        expression_records = load_committed_normalized_gene_effects_v2(context.run_dir)
        gene_records = []
        weight_records = []
        exclusion_records = []
        for expression_record in expression_records:
            if expression_record.canonical_gene_id is None:
                continue
            gene_record, weights, exclusions = assign_isoform_uncertainty_for_gene(
                source_expression_v2_record_id=expression_record.record_id,
                original_gene_id=expression_record.original_gene_id,
                canonical_gene_id=expression_record.canonical_gene_id,
                approved_symbol=expression_record.approved_symbol,
                organism=expression_record.organism,
                assembly=context.config.project.genome_build,
                annotation_snapshot=snapshot,
                annotation_records=annotation_records,
                policy=transcript_policy,
                external_proportions=external_by_gene.get(expression_record.canonical_gene_id),
                external_policy=external_policy,
                tolerance=config.small_rounding_tolerance,
            )
            gene_records.append(gene_record)
            weight_records.extend(weights)
            exclusion_records.extend(exclusions)
        counts = {
            "expression_records": len(expression_records),
            "annotation_records": len(annotation_records),
            "external_transcript_proportions": len(external_records),
            "gene_isoform_uncertainty_records": len(gene_records),
            "transcript_prior_weight_records": len(weight_records),
            "transcript_set_exclusion_records": len(exclusion_records),
        }
        external_validation = {
            "status": "passed" if external_records else "not_applicable",
            "external_proportion_policy_id": external_policy.policy_id,
            "record_count": len(external_records),
            "missing_transcript_behavior": external_policy.missing_transcript_behavior,
            "invalid_proportion_behavior": external_policy.invalid_proportion_behavior,
        }
        checksum = expression_contract.payload.artifact_checksums.get(
            "normalized_gene_effects_v2.jsonl", "unknown"
        )
        mode = (
            "precomputed_transcript_proportions"
            if external_records
            else "annotation_only_equal_prior"
        )
        evidence_mode = cast(IsoformEvidenceMode, mode)
        immutable_checksums = write_immutable_isoform_uncertainty_artifacts(
            output_dir=output_dir,
            gene_records=gene_records,
            weight_records=weight_records,
            exclusion_records=exclusion_records,
            annotation_validation=annotation_validation,
            method_selection={
                "stage_enabled": True,
                "evidence_mode": mode,
                "transcript_set_policy_id": transcript_policy.policy_id,
                "external_proportion_policy_id": external_policy.policy_id,
            },
            input_validation={
                "status": "passed",
                "expression_contract": expression_contract.contract_name,
                "annotation_validation_fatal_errors": list(annotation_validation.fatal_errors),
            },
            summary=counts,
            external_validation=external_validation,
        )
        run_record = IsoformUncertaintyRunRecordV1(
            run_id=context.run_id,
            expression_stage_contract=expression_contract.contract_name,
            expression_result_record_id=expression_contract.run_id,
            expression_artifact_checksum=checksum,
            annotation_snapshot_id=snapshot.snapshot_id,
            annotation_validation_record_id=annotation_validation.annotation_snapshot_id,
            annotation_checksum=isoform_uncertainty_sha256_file(annotation_path),
            transcript_set_policy_id=transcript_policy.policy_id,
            external_proportion_policy_id=external_policy.policy_id,
            isoform_evidence_mode=evidence_mode,
            evidence_mode=evidence_mode,
            fallback_policy=config.missing_transcript_behavior,
            external_evidence_files=(str(config.external_proportions_file),)
            if config.external_proportions_file
            else (),
            external_evidence_checksums=(
                isoform_uncertainty_sha256_file(config.external_proportions_file),
            )
            if config.external_proportions_file
            else (),
            weight_policy=transcript_policy.policy_id,
            numerical_tolerance=config.small_rounding_tolerance,
            numerical_tolerances={
                "small_rounding_tolerance": config.small_rounding_tolerance,
                "material_sum_tolerance": config.material_sum_tolerance,
            },
            organism=snapshot.organism,
            assembly=snapshot.assembly,
            identifier_snapshot_id=identifier_snapshot_id,
            identifier_snapshot_checksum=identifier_snapshot_checksum,
            software_version="sirna-offtarget",
            started_at=started_at,
            completed_at=_utc_now(),
            status="completed",
            verification_status="verified",
            source_record_counts={
                "expression_records": len(expression_records),
                "annotation_records": len(annotation_records),
                "external_transcript_proportions": len(external_records),
            },
            output_record_counts=counts,
            record_counts=counts,
            referenced_artifact_checksums={
                key: immutable_checksums[key]
                for key in (
                    "genes",
                    "weights",
                    "exclusions",
                    "annotation_validation",
                    "external_validation",
                    "method_selection",
                    "input_validation",
                )
            },
            warnings=tuple(warnings),
        )
        payload = IsoformUncertaintyPayloadV1(
            run_record=run_record, counts=counts, artifacts=immutable_checksums
        )
        metadata_checksums = write_final_isoform_uncertainty_metadata(
            output_dir=output_dir,
            run_record=run_record,
            result_payload=payload.model_dump(mode="json"),
        )
        verification = verify_isoform_uncertainty_final_outputs(output_dir)
        if not verification.passed:
            raise RuntimeError(
                "isoform uncertainty final artifact verification failed: "
                + ", ".join(verification.errors)
            )
        payload = IsoformUncertaintyPayloadV1(
            run_record=run_record,
            counts=counts,
            artifacts={**immutable_checksums, **metadata_checksums},
        )
        warnings.extend(warning for record in gene_records for warning in record.warnings)
        return StageExecutionResult(
            sorted(output_dir.iterdir()),
            counts,
            list(dict.fromkeys(warnings)),
            "IsoformUncertaintyResultV1",
            payload=payload,
        )

    def _execute_transcript_targetability(
        self, context: RunContext, attempt_directory: Path
    ) -> StageExecutionResult:
        started_at = _utc_now()
        config = context.config.transcript_targetability
        output_dir = attempt_directory / "outputs"
        isoform_contract = load_dependency_contract(
            context,
            dependency_stage="isoform_uncertainty",
            expected_contract=IsoformUncertaintyResultV1,
        )
        self._record_consumed(
            context,
            dependency_stage="isoform_uncertainty",
            contract=isoform_contract,
            artifacts=["transcript_prior_weights_v1.jsonl"],
            payload_fields=["run_record", "artifacts"],
        )
        cleavage_policy = CleavageCompatibilityPolicyV1(
            guide_length_min=config.guide_length_min,
            guide_length_max=config.guide_length_max,
            maximum_total_mismatches=config.maximum_total_mismatches,
            maximum_seed_mismatches=config.maximum_seed_mismatches,
            maximum_central_mismatches=config.maximum_central_mismatches,
            maximum_nonseed_mismatches=config.maximum_nonseed_mismatches,
            seed_start=config.seed_start,
            seed_end=config.seed_end,
        )
        seed_policy = SeedMatchPolicyV1(
            seed_start=config.seed_start,
            seed_end=config.seed_end,
            seed_length=config.seed_end - config.seed_start + 1,
            exact_seed_required=config.exact_seed_required,
            allowed_seed_mismatches=config.allowed_seed_mismatches,
            minimum_total_paired_bases=config.minimum_total_paired_bases,
            maximum_total_mismatches=config.seed_maximum_total_mismatches,
            supplementary_pairing_requirement=config.supplementary_pairing_requirement,
            transcript_region_restrictions=tuple(config.transcript_region_restrictions),
        )
        intended_policy = IntendedTargetValidationPolicyV1(
            intended_target_required=config.intended_target_required,
            transcript_ids_required=config.intended_target_transcript_ids_required,
            accepted_evidence_classes=cast(
                Any,
                tuple(config.intended_target_accepted_evidence_classes),
            ),
            failure_behavior=cast(
                Any,
                config.intended_target_failure_behavior,
            ),
            gene_only_behavior=cast(Any, config.intended_target_gene_only_behavior),
            maximum_total_mismatches=config.maximum_total_mismatches,
            maximum_seed_mismatches=config.maximum_seed_mismatches,
            maximum_central_mismatches=config.maximum_central_mismatches,
        )
        missing_policy = MissingTranscriptSequencePolicyV1(
            mode=cast(Any, config.missing_transcript_sequence_mode)
        )
        if config.search_passenger:
            raise RuntimeError("unsupported_passenger_search_policy")
        sirna_record, sirna_validation = validate_sirna_sequence(
            sirna_id=config.sirna_id,
            reagent_name=config.reagent_name,
            guide_sequence=context.config.sirna.guide_sequence,
            passenger_sequence=context.config.sirna.passenger_sequence,
            organism=context.config.project.organism,
            assembly=context.config.project.genome_build,
            guide_orientation=config.guide_orientation,
            intended_target_gene_id=context.config.sirna.intended_target_gene,
            intended_target_transcript_ids=(context.config.sirna.intended_target_transcript,)
            if context.config.sirna.intended_target_transcript
            else (),
            cleavage_policy=cleavage_policy,
            passenger_search_requested=config.search_passenger,
        )
        warnings: list[str] = []
        if not config.enabled:
            warnings.append("transcript targetability stage disabled by configuration")
            run_record = TranscriptTargetabilityRunRecordV1(
                run_id=context.run_id,
                sirna_sequence_record_id=sirna_record.sirna_id,
                guide_sequence_checksum=sha256_text(sirna_record.guide_sequence_normalized),
                isoform_uncertainty_result_id=isoform_contract.run_id,
                isoform_uncertainty_artifact_checksum="not_applicable",
                transcript_sequence_snapshot_id="not_applicable",
                transcript_sequence_snapshot_checksum="not_applicable",
                annotation_snapshot_id="not_applicable",
                annotation_checksum="not_applicable",
                cleavage_policy_id=cleavage_policy.policy_id,
                seed_policy_id=seed_policy.policy_id,
                intended_target_policy_id=intended_policy.policy_id,
                missing_sequence_policy_id=missing_policy.policy_id,
                passenger_search_status="not_requested",
                organism=context.config.project.organism,
                assembly=context.config.project.genome_build,
                started_at=started_at,
                completed_at=_utc_now(),
                status="completed",
                verification_status="verified",
                warnings=tuple(warnings),
            )
            result = write_transcript_targetability_artifacts(
                output_dir=output_dir,
                sirna_sequence=sirna_record,
                sirna_validation=sirna_validation,
                sequence_validation={"schema_version": "1", "status": "not_applicable"},
                evidence_records=[],
                site_records=[],
                mismatch_records=[],
                alignment_position_records=[],
                exclusions=[],
                policy_payload={
                    "cleavage_policy": cleavage_policy.model_dump(mode="json"),
                    "seed_policy": seed_policy.model_dump(mode="json"),
                    "intended_target_policy": intended_policy.model_dump(mode="json"),
                    "missing_sequence_policy": missing_policy.model_dump(mode="json"),
                },
                run_record=run_record,
            )
            return StageExecutionResult(
                sorted(output_dir.iterdir()),
                {"stage_enabled": False},
                warnings,
                "TranscriptTargetabilityResultV1",
                payload=result,
            )
        if (
            config.transcript_sequence_cache_dir is None
            or config.transcript_sequence_snapshot_id is None
        ):
            raise RuntimeError(
                "transcript targetability requires transcript_sequence_cache_dir and "
                "transcript_sequence_snapshot_id"
            )
        isoform_outputs = committed_contract_path(context.run_dir, "isoform_uncertainty").parent
        weights_path = isoform_outputs / "transcript_prior_weights_v1.jsonl"
        if not weights_path.exists():
            raise RuntimeError("isoform uncertainty committed weights artifact is missing")
        weights = [
            TranscriptPriorWeightRecordV1.model_validate(json.loads(line))
            for line in weights_path.read_text().splitlines()
            if line.strip()
        ]
        eligible_weights = [
            weight
            for weight in weights
            if weight.eligibility_status == "eligible" and weight.weight is not None
        ]
        eligible_transcripts = {
            weight.canonical_transcript_id: weight.canonical_gene_id for weight in eligible_weights
        }
        intended_transcript = context.config.sirna.intended_target_transcript
        if (
            intended_transcript
            and config.intended_target_missing_policy == "fail_stage"
            and intended_transcript not in eligible_transcripts
        ):
            raise RuntimeError("intended target transcript is absent from eligible transcripts")
        snapshot, sequence_records, sequence_records_path = load_transcript_sequence_snapshot(
            config.transcript_sequence_cache_dir,
            config.transcript_sequence_snapshot_id,
            config.manifest_artifact,
        )
        if (
            config.require_verified_transcript_sequence_snapshot
            and snapshot.verification_status != "verified"
        ):
            raise RuntimeError("transcript targetability requires a verified sequence snapshot")
        expected_sequence_release = next(
            (
                weight.source_annotation_release
                for weight in eligible_weights
                if weight.source_annotation_release
            ),
            isoform_contract.payload.run_record.annotation_snapshot_id,
        )
        sequence_validation = validate_transcript_sequence_snapshot(
            snapshot=snapshot,
            records=sequence_records,
            expected_organism=context.config.project.organism,
            expected_assembly=context.config.project.genome_build,
            expected_release=expected_sequence_release,
            eligible_transcripts=eligible_transcripts,
            require_complete_sequences=missing_policy.mode == "fail_stage",
        )
        if sequence_validation.fatal_errors:
            raise RuntimeError(
                "transcript sequence validation failed: "
                + ", ".join(sequence_validation.fatal_errors)
            )
        sequence_by_transcript = {
            record.canonical_transcript_id: record for record in sequence_records
        }
        evidence_records = []
        site_records = []
        mismatch_records = []
        alignment_position_records = []
        gene_failure_records = []
        weights_by_gene: dict[str, list[TranscriptPriorWeightRecordV1]] = {}
        for weight in eligible_weights:
            weights_by_gene.setdefault(weight.canonical_gene_id, []).append(weight)
        missing_by_gene: dict[str, list[str]] = {}
        for weight in eligible_weights:
            if weight.canonical_transcript_id not in sequence_by_transcript:
                missing_by_gene.setdefault(weight.canonical_gene_id, []).append(
                    weight.canonical_transcript_id
                )
        if missing_policy.mode == "fail_stage" and missing_by_gene:
            first_missing = next(iter(next(iter(missing_by_gene.values()))))
            raise RuntimeError(f"missing transcript sequence:{first_missing}")
        failed_genes = set(missing_by_gene) if missing_policy.mode == "fail_gene" else set()
        for gene_id in sorted(failed_genes):
            affected_weights = weights_by_gene[gene_id]
            triggering = tuple(sorted(missing_by_gene[gene_id]))
            gene_failure_records.append(
                build_gene_failure_record(
                    canonical_gene_id=gene_id,
                    affected_transcript_ids=tuple(
                        sorted(weight.canonical_transcript_id for weight in affected_weights)
                    ),
                    triggering_transcript_ids=triggering,
                    missing_sequence_policy_id=missing_policy.policy_id,
                    source_isoform_uncertainty_record_ids=tuple(
                        sorted(
                            {
                                weight.gene_isoform_uncertainty_record_id
                                for weight in affected_weights
                            }
                        )
                    ),
                )
            )
            for weight in affected_weights:
                evidence_records.append(
                    gene_failed_evidence(
                        sirna=sirna_record,
                        canonical_gene_id=weight.canonical_gene_id,
                        canonical_transcript_id=weight.canonical_transcript_id,
                        transcript_version=weight.transcript_version,
                        transcript_prior_weight=weight.weight,
                        source_isoform_uncertainty_record_id=(
                            weight.gene_isoform_uncertainty_record_id
                        ),
                        source_transcript_weight_record_id=weight.record_id,
                        triggering_transcript_ids=triggering,
                    )
                )
        for weight in eligible_weights:
            if weight.canonical_gene_id in failed_genes:
                continue
            transcript = sequence_by_transcript.get(weight.canonical_transcript_id)
            if transcript is None:
                evidence_records.append(
                    unavailable_sequence_evidence(
                        sirna=sirna_record,
                        canonical_gene_id=weight.canonical_gene_id,
                        canonical_transcript_id=weight.canonical_transcript_id,
                        transcript_version=weight.transcript_version,
                        transcript_prior_weight=weight.weight,
                        source_isoform_uncertainty_record_id=(
                            weight.gene_isoform_uncertainty_record_id
                        ),
                        source_transcript_weight_record_id=weight.record_id,
                    )
                )
                continue
            evidence, sites, mismatches, positions = find_transcript_targetability(
                sirna=sirna_record,
                transcript=transcript,
                transcript_prior_weight=weight.weight,
                source_isoform_uncertainty_record_id=weight.gene_isoform_uncertainty_record_id,
                source_transcript_weight_record_id=weight.record_id,
                transcript_sequence_snapshot_id=snapshot.snapshot_id,
                cleavage_policy=cleavage_policy,
                seed_policy=seed_policy,
            )
            evidence_records.append(evidence)
            site_records.extend(sites)
            mismatch_records.extend(mismatches)
            alignment_position_records.extend(positions)
        intended_validation = validate_intended_target_actual_site(
            intended_target_gene_id=context.config.sirna.intended_target_gene,
            intended_transcript_ids=(intended_transcript,) if intended_transcript else (),
            evidence_records=evidence_records,
            site_records=site_records,
            gene_failure_records=gene_failure_records,
            policy=intended_policy,
        )
        if intended_validation.errors:
            message = "intended target validation failed: " + ", ".join(intended_validation.errors)
            if intended_validation.failure_behavior_applied == "fail_stage":
                raise RuntimeError(message)
            warnings.append(message)
        warnings.extend(intended_validation.warnings)
        source_counts = {
            "transcript_prior_weight_records": len(weights),
            "eligible_transcript_prior_weight_records": len(eligible_weights),
            "transcript_sequence_records": len(sequence_records),
        }
        run_record = TranscriptTargetabilityRunRecordV1(
            run_id=context.run_id,
            sirna_sequence_record_id=sirna_record.sirna_id,
            guide_sequence_checksum=sha256_text(sirna_record.guide_sequence_normalized),
            isoform_uncertainty_result_id=isoform_contract.run_id,
            isoform_uncertainty_artifact_checksum=sha256_file(weights_path),
            transcript_sequence_snapshot_id=snapshot.snapshot_id,
            transcript_sequence_snapshot_checksum=sha256_file(sequence_records_path),
            annotation_snapshot_id=isoform_contract.payload.run_record.annotation_snapshot_id,
            annotation_checksum=isoform_contract.payload.run_record.annotation_checksum,
            cleavage_policy_id=cleavage_policy.policy_id,
            seed_policy_id=seed_policy.policy_id,
            intended_target_policy_id=intended_policy.policy_id,
            missing_sequence_policy_id=missing_policy.policy_id,
            passenger_search_status="not_requested",
            organism=context.config.project.organism,
            assembly=context.config.project.genome_build,
            started_at=started_at,
            completed_at=_utc_now(),
            status="completed",
            source_counts=source_counts,
            verification_status="verified",
            warnings=tuple(warnings),
        )
        result = write_transcript_targetability_artifacts(
            output_dir=output_dir,
            sirna_sequence=sirna_record,
            sirna_validation=sirna_validation,
            sequence_validation=sequence_validation,
            transcript_sequence_snapshot=snapshot,
            transcript_sequence_records=sequence_records,
            evidence_records=evidence_records,
            site_records=site_records,
            mismatch_records=mismatch_records,
            alignment_position_records=alignment_position_records,
            gene_failure_records=gene_failure_records,
            intended_target_validation=intended_validation,
            exclusions=[],
            policy_payload={
                "cleavage_policy": cleavage_policy.model_dump(mode="json"),
                "seed_policy": seed_policy.model_dump(mode="json"),
                "intended_target_policy": intended_policy.model_dump(mode="json"),
                "missing_sequence_policy": missing_policy.model_dump(mode="json"),
                "intended_target_validation_status": intended_validation.validation_status,
            },
            run_record=run_record,
        )
        verification = verify_transcript_targetability_outputs(output_dir)
        if not verification["passed"]:
            raise RuntimeError(
                "transcript targetability artifact verification failed: "
                + ", ".join(verification["errors"])
            )
        return StageExecutionResult(
            sorted(output_dir.iterdir()),
            result.counts,
            warnings,
            "TranscriptTargetabilityResultV1",
            payload=result,
        )

    def _execute_transcript_targetability_ratio(
        self, context: RunContext, attempt_directory: Path
    ) -> StageExecutionResult:
        started_at = _utc_now()
        output_dir = attempt_directory / "outputs"
        isoform_contract = load_dependency_contract(
            context,
            dependency_stage="isoform_uncertainty",
            expected_contract=IsoformUncertaintyResultV1,
        )
        targetability_contract = load_dependency_contract(
            context,
            dependency_stage="transcript_targetability",
            expected_contract=TranscriptTargetabilityResultV1,
        )
        self._record_consumed(
            context,
            dependency_stage="isoform_uncertainty",
            contract=isoform_contract,
            artifacts=["transcript_prior_weights_v1.jsonl"],
            payload_fields=["run_record"],
        )
        self._record_consumed(
            context,
            dependency_stage="transcript_targetability",
            contract=targetability_contract,
            artifacts=[
                "transcript_targetability_evidence_v1.jsonl",
                "transcript_targetability_sites_v1.jsonl",
                "transcript_targetability_gene_failures_v1.jsonl",
            ],
            payload_fields=["run_record", "counts"],
        )
        config = context.config.transcript_targetability_ratio
        policy = TargetableTranscriptInclusionPolicyV1(
            policy_id=config.policy_id,
            include_seed_only=config.include_seed_only,
            include_ambiguous=config.include_ambiguous,
            require_complete_gene_evidence=config.require_complete_gene_evidence,
            require_cleavage_compatibility=config.require_cleavage_compatibility,
            require_verified_sequence=config.require_verified_sequence,
            require_verified_site=config.require_verified_site,
        )
        if not config.enabled:
            raise RuntimeError("transcript targetability ratio stage cannot be disabled")
        isoform_outputs = committed_contract_path(context.run_dir, "isoform_uncertainty").parent
        targetability_outputs = committed_contract_path(
            context.run_dir, "transcript_targetability"
        ).parent
        targetability_verification = verify_transcript_targetability_outputs(targetability_outputs)
        if not targetability_verification["passed"]:
            raise RuntimeError(
                "transcript targetability ratio requires verified targetability outputs: "
                + ", ".join(targetability_verification["errors"])
            )
        weights_path = isoform_outputs / "transcript_prior_weights_v1.jsonl"
        gene_records_path = isoform_outputs / "gene_isoform_uncertainty_v1.jsonl"
        evidence_path = targetability_outputs / (
            targetability_contract.payload.targetability_evidence_artifact
        )
        sites_path = (
            targetability_outputs / targetability_contract.payload.targetability_sites_artifact
        )
        gene_failures_artifact = targetability_contract.payload.gene_failures_artifact
        gene_failures_path = (
            targetability_outputs / gene_failures_artifact
            if gene_failures_artifact
            else targetability_outputs / "transcript_targetability_gene_failures_v1.jsonl"
        )
        weights = [
            TranscriptPriorWeightRecordV1.model_validate(json.loads(line))
            for line in weights_path.read_text().splitlines()
            if line.strip()
        ]
        gene_records = [
            json.loads(line) for line in gene_records_path.read_text().splitlines() if line.strip()
        ]
        evidence = [
            json.loads(line) for line in evidence_path.read_text().splitlines() if line.strip()
        ]
        sites = [json.loads(line) for line in sites_path.read_text().splitlines() if line.strip()]
        gene_failures = []
        if gene_failures_path.exists():
            gene_failures = [
                json.loads(line)
                for line in gene_failures_path.read_text().splitlines()
                if line.strip()
            ]
        computed = compute_transcript_targetability_ratios(
            transcript_weights=weights,
            gene_records=gene_records,
            targetability_evidence=evidence,
            targetability_sites=sites,
            gene_failures=gene_failures,
            source_targetability_result_id=targetability_contract.run_id,
            inclusion_policy=policy,
        )
        write_transcript_targetability_ratio_artifacts(
            output_dir=output_dir,
            run_record=TranscriptTargetabilityRatioRunRecordV1(
                run_id=context.run_id,
                isoform_uncertainty_result_id=isoform_contract.run_id,
                isoform_uncertainty_checksum=ratio_sha256_file(
                    isoform_outputs / "stage_result.json"
                ),
                transcript_targetability_result_id=targetability_contract.run_id,
                transcript_targetability_checksum=ratio_sha256_file(
                    targetability_outputs / "stage_result.json"
                ),
                inclusion_policy_id=policy.policy_id,
                inclusion_policy_checksum=policy.fingerprint,
                started_at=started_at,
                completed_at=_utc_now(),
                status="completed",
                source_counts={
                    "gene_isoform_uncertainty_records": len(gene_records),
                    "transcript_prior_weight_records": len(weights),
                    "targetability_evidence_records": len(evidence),
                    "targetability_site_records": len(sites),
                    "targetability_gene_failure_records": len(gene_failures),
                },
                verification_status="verified",
                warnings=tuple(computed.warnings),
            ),
            inclusion_policy=policy,
            gene_ratios=computed.gene_ratios,
            contributions=computed.contributions,
            unresolved=computed.unresolved,
            summary=computed.summary,
            warnings=computed.warnings,
        )
        verification = verify_transcript_targetability_ratio_outputs(output_dir)
        if not verification["passed"]:
            raise RuntimeError(
                "transcript targetability ratio verification failed: "
                + ", ".join(verification["errors"])
            )
        result_payload = json.loads(
            (output_dir / "transcript_targetability_ratio_result_v1.json").read_text()
        )
        return StageExecutionResult(
            sorted(output_dir.iterdir()),
            computed.summary,
            computed.warnings,
            "TranscriptTargetabilityRatioResultV1",
            payload=result_payload,
        )

    def _execute_expected_direct_effect(
        self, context: RunContext, attempt_directory: Path
    ) -> StageExecutionResult:
        started_at = _utc_now()
        output_dir = attempt_directory / "outputs"
        expression_contract = load_dependency_contract(
            context,
            dependency_stage="expression_analysis",
            expected_contract=ExpressionAnalysisResultV2,
        )
        ratio_contract = load_dependency_contract(
            context,
            dependency_stage="transcript_targetability_ratio",
            expected_contract=TranscriptTargetabilityRatioResultV1,
        )
        self._record_consumed(
            context,
            dependency_stage="expression_analysis",
            contract=expression_contract,
            artifacts=["normalized_gene_effects_v2.jsonl"],
            payload_fields=["normalized_gene_effects_artifact"],
        )
        self._record_consumed(
            context,
            dependency_stage="transcript_targetability_ratio",
            contract=ratio_contract,
            artifacts=["gene_transcript_targetability_ratios_v1.jsonl"],
            payload_fields=["run_record", "counts"],
        )
        config = context.config.expected_direct_effect
        if not config.enabled:
            raise RuntimeError("expected direct-effect stage cannot be disabled")
        expression_outputs = committed_contract_path(context.run_dir, "expression_analysis").parent
        ratio_outputs = committed_contract_path(
            context.run_dir, "transcript_targetability_ratio"
        ).parent
        ratio_verification = verify_transcript_targetability_ratio_outputs(ratio_outputs)
        if not ratio_verification["passed"]:
            raise RuntimeError(
                "expected direct-effect stage requires verified ratio outputs: "
                + ", ".join(ratio_verification["errors"])
            )
        expression_records = load_committed_normalized_gene_effects_v2(context.run_dir)
        ratio_path = ratio_outputs / ratio_contract.payload.gene_ratio_records_artifact
        ratio_records = [
            GeneTranscriptTargetabilityRatioRecordV1.model_validate(json.loads(line))
            for line in ratio_path.read_text().splitlines()
            if line.strip()
        ]
        policy = ExpectedDirectEffectPolicyV1(
            policy_id=config.policy_id,
            numerical_tolerance=config.numerical_tolerance,
        )
        expression_artifact = expression_outputs / "normalized_gene_effects_v2.jsonl"
        computed = compute_expected_direct_effects(
            intended_target_gene_id=context.config.sirna.intended_target_gene,
            expression_records=expression_records,
            ratio_records=ratio_records,
            policy=policy,
            source_expression_checksum=expected_direct_sha256_file(expression_artifact),
            source_ratio_checksum=expected_direct_sha256_file(ratio_path),
        )
        write_expected_direct_effect_artifacts(
            output_dir=output_dir,
            run_record=ExpectedDirectEffectRunRecordV1(
                run_id=context.run_id,
                expression_result_id=expression_contract.run_id,
                expression_checksum=expected_direct_sha256_file(
                    expression_outputs / "stage_result.json"
                ),
                transcript_targetability_ratio_result_id=ratio_contract.run_id,
                transcript_targetability_ratio_checksum=expected_direct_sha256_file(
                    ratio_outputs / "stage_result.json"
                ),
                policy_id=policy.policy_id,
                policy_checksum=policy.fingerprint,
                calibration_record_id=computed.calibration.calibration_record_id,
                started_at=started_at,
                completed_at=_utc_now(),
                status="completed",
                source_counts={
                    "normalized_gene_effect_records": len(expression_records),
                    "gene_transcript_targetability_ratio_records": len(ratio_records),
                },
                verification_status="verified",
                warnings=tuple(computed.warnings),
            ),
            policy=policy,
            calibration=computed.calibration,
            gene_effects=computed.gene_effects,
            unresolved=computed.unresolved,
            summary=computed.summary,
            warnings=computed.warnings,
        )
        verification = verify_expected_direct_effect_outputs(output_dir)
        if not verification["passed"]:
            raise RuntimeError(
                "expected direct-effect verification failed: " + ", ".join(verification["errors"])
            )
        result_payload = json.loads(
            (output_dir / "expected_direct_effect_result_v1.json").read_text()
        )
        return StageExecutionResult(
            sorted(output_dir.iterdir()),
            computed.summary,
            computed.warnings,
            "ExpectedDirectEffectResultV1",
            payload=result_payload,
        )

    def _execute_residual_attribution(
        self, context: RunContext, attempt_directory: Path
    ) -> StageExecutionResult:
        started_at = _utc_now()
        output_dir = attempt_directory / "outputs"
        expected_direct_contract = load_dependency_contract(
            context,
            dependency_stage="expected_direct_effect",
            expected_contract=ExpectedDirectEffectResultV1,
        )
        self._record_consumed(
            context,
            dependency_stage="expected_direct_effect",
            contract=expected_direct_contract,
            artifacts=[
                "gene_expected_direct_effects_v1.jsonl",
                "expected_direct_effect_result_v1.json",
                "expected_direct_effect_summary_v1.json",
                "expected_direct_effect_unresolved_v1.jsonl",
            ],
            payload_fields=["run_record", "counts"],
        )
        config = context.config.residual_attribution
        if not config.enabled:
            raise RuntimeError("residual attribution stage cannot be disabled")
        expected_outputs = committed_contract_path(context.run_dir, "expected_direct_effect").parent
        expected_verification = verify_expected_direct_effect_outputs(expected_outputs)
        if not expected_verification["passed"]:
            raise RuntimeError(
                "residual attribution requires verified expected direct-effect outputs: "
                + ", ".join(expected_verification["errors"])
            )
        expected_records_path = expected_outputs / "gene_expected_direct_effects_v1.jsonl"
        expected_records = [
            GeneExpectedDirectEffectRecordV1.model_validate(json.loads(line))
            for line in expected_records_path.read_text().splitlines()
            if line.strip()
        ]
        policy = ResidualAttributionPolicyV1(
            policy_id=config.policy_id,
            numerical_tolerance=config.numerical_tolerance,
            negligible_residual_abs_log2_threshold=(config.negligible_residual_abs_log2_threshold),
            moderate_residual_abs_log2_threshold=config.moderate_residual_abs_log2_threshold,
            strong_residual_abs_log2_threshold=config.strong_residual_abs_log2_threshold,
        )
        pathway_support_by_gene = None
        pathway_evidence_available = False
        source_pathway_evidence_checksum = None
        pathway_support_records = 0
        if config.use_mechanistic_pathway_support:
            if config.pathway_support_source != "mechanistic_network":
                raise RuntimeError(
                    "unsupported residual_attribution.pathway_support_source: "
                    f"{config.pathway_support_source}"
                )
            mechanistic_contract = load_dependency_contract(
                context,
                dependency_stage="mechanistic_network",
                expected_contract=MechanisticNetworkResultV2,
            )
            self._record_consumed(
                context,
                dependency_stage="mechanistic_network",
                contract=mechanistic_contract,
                artifacts=["stage_result.json"],
                payload_fields=[
                    "signed_paths",
                    "unsigned_context_paths",
                    "provider_snapshot_manifest",
                    "metrics",
                ],
            )
            pathway_support_by_gene = pathway_support_from_mechanistic_network_v2(
                mechanistic_contract
            )
            pathway_evidence_available = True
            mechanistic_outputs = committed_contract_path(
                context.run_dir, "mechanistic_network"
            ).parent
            source_pathway_evidence_checksum = residual_attribution_sha256_file(
                mechanistic_outputs / "stage_result.json"
            )
            pathway_support_records = sum(
                len(records) for records in pathway_support_by_gene.values()
            )
        computed = compute_residual_attribution(
            expected_direct_effect_records=expected_records,
            pathway_support_by_gene=pathway_support_by_gene,
            pathway_evidence_available=pathway_evidence_available,
            policy=policy,
            source_expected_direct_effect_checksum=residual_attribution_sha256_file(
                expected_records_path
            ),
            source_pathway_evidence_checksum=source_pathway_evidence_checksum,
        )
        write_residual_attribution_artifacts(
            output_dir=output_dir,
            run_record=ResidualAttributionRunRecordV1(
                run_id=context.run_id,
                expected_direct_effect_result_id=expected_direct_contract.run_id,
                expected_direct_effect_checksum=residual_attribution_sha256_file(
                    expected_outputs / "stage_result.json"
                ),
                pathway_evidence_checksum=source_pathway_evidence_checksum,
                policy_id=policy.policy_id,
                policy_checksum=policy.fingerprint,
                started_at=started_at,
                completed_at=_utc_now(),
                status="completed",
                source_counts={
                    "gene_expected_direct_effect_records": len(expected_records),
                    "pathway_support_records": pathway_support_records,
                },
                verification_status="verified",
                warnings=tuple(computed.warnings),
            ),
            policy=policy,
            gene_evidence=computed.gene_evidence,
            unresolved=computed.unresolved,
            summary=computed.summary,
            warnings=computed.warnings,
        )
        verification = verify_residual_attribution_outputs(output_dir)
        if not verification["passed"]:
            raise RuntimeError(
                "residual attribution verification failed: " + ", ".join(verification["errors"])
            )
        result_payload = json.loads(
            (output_dir / "residual_attribution_result_v1.json").read_text()
        )
        return StageExecutionResult(
            sorted(output_dir.iterdir()),
            computed.summary,
            computed.warnings,
            "ResidualAttributionResultV1",
            payload=result_payload,
        )

    def _execute_secondary_evidence_integration(
        self, context: RunContext, attempt_directory: Path
    ) -> StageExecutionResult:
        started_at = _utc_now()
        output_dir = attempt_directory / "outputs"
        residual_contract = load_dependency_contract(
            context,
            dependency_stage="residual_attribution",
            expected_contract=ResidualAttributionResultV1,
        )
        self._record_consumed(
            context,
            dependency_stage="residual_attribution",
            contract=residual_contract,
            artifacts=[
                "gene_residual_attribution_evidence_v1.jsonl",
                "residual_attribution_result_v1.json",
                "residual_attribution_summary_v1.json",
                "residual_attribution_unresolved_v1.jsonl",
            ],
            payload_fields=["run_record", "counts"],
        )
        config = context.config.secondary_evidence_integration
        if not config.enabled:
            raise RuntimeError("secondary evidence integration stage cannot be disabled")
        residual_outputs = committed_contract_path(context.run_dir, "residual_attribution").parent
        residual_verification = verify_residual_attribution_outputs(residual_outputs)
        if not residual_verification["passed"]:
            raise RuntimeError(
                "secondary evidence integration requires verified residual-attribution outputs: "
                + ", ".join(residual_verification["errors"])
            )
        residual_records_path = residual_outputs / "gene_residual_attribution_evidence_v1.jsonl"
        residual_unresolved_path = residual_outputs / "residual_attribution_unresolved_v1.jsonl"
        residual_records = [
            GeneResidualAttributionEvidenceRecordV1.model_validate(json.loads(line))
            for line in residual_records_path.read_text().splitlines()
            if line.strip()
        ]
        residual_unresolved = [
            ResidualAttributionUnresolvedRecordV1.model_validate(json.loads(line))
            for line in residual_unresolved_path.read_text().splitlines()
            if line.strip()
        ]
        policy = SecondaryEvidenceIntegrationPolicyV1(
            policy_id=config.policy_id,
            numerical_tolerance=config.numerical_tolerance,
        )
        computed = compute_secondary_evidence_integration(
            residual_attribution_records=residual_records,
            residual_unresolved_records=residual_unresolved,
            policy=policy,
            source_residual_attribution_checksum=secondary_evidence_integration_sha256_file(
                residual_records_path
            ),
        )
        write_secondary_evidence_integration_artifacts(
            output_dir=output_dir,
            run_record=SecondaryEvidenceIntegrationRunRecordV1(
                run_id=context.run_id,
                residual_attribution_result_id=residual_contract.run_id,
                residual_attribution_checksum=secondary_evidence_integration_sha256_file(
                    residual_outputs / "stage_result.json"
                ),
                policy_id=policy.policy_id,
                policy_checksum=policy.fingerprint,
                started_at=started_at,
                completed_at=_utc_now(),
                status="completed",
                source_counts={
                    "gene_residual_attribution_evidence_records": len(residual_records),
                    "residual_attribution_unresolved_records": len(residual_unresolved),
                },
                verification_status="verified",
                warnings=tuple(computed.warnings),
            ),
            policy=policy,
            gene_evidence=computed.gene_evidence,
            unresolved=computed.unresolved,
            summary=computed.summary,
            warnings=computed.warnings,
        )
        verification = verify_secondary_evidence_integration_outputs(output_dir)
        if not verification["passed"]:
            raise RuntimeError(
                "secondary evidence integration verification failed: "
                + ", ".join(verification["errors"])
            )
        result_payload = json.loads(
            (output_dir / "secondary_evidence_integration_result_v1.json").read_text()
        )
        return StageExecutionResult(
            sorted(output_dir.iterdir()),
            computed.summary,
            computed.warnings,
            "SecondaryEvidenceIntegrationResultV1",
            payload=result_payload,
        )

    def _execute_final_evidence_classification(
        self, context: RunContext, attempt_directory: Path
    ) -> StageExecutionResult:
        started_at = _utc_now()
        output_dir = attempt_directory / "outputs"
        integration_contract = load_dependency_contract(
            context,
            dependency_stage="secondary_evidence_integration",
            expected_contract=SecondaryEvidenceIntegrationResultV1,
        )
        self._record_consumed(
            context,
            dependency_stage="secondary_evidence_integration",
            contract=integration_contract,
            artifacts=[
                "gene_secondary_evidence_integration_v1.jsonl",
                "secondary_evidence_integration_result_v1.json",
                "secondary_evidence_integration_summary_v1.json",
                "secondary_evidence_integration_unresolved_v1.jsonl",
            ],
            payload_fields=["run_record", "counts"],
        )
        config = context.config.final_evidence_classification
        if not config.enabled:
            raise RuntimeError("final evidence classification stage cannot be disabled")
        integration_outputs = committed_contract_path(
            context.run_dir, "secondary_evidence_integration"
        ).parent
        integration_verification = verify_secondary_evidence_integration_outputs(
            integration_outputs
        )
        if not integration_verification["passed"]:
            raise RuntimeError(
                "final evidence classification requires verified secondary evidence outputs: "
                + ", ".join(integration_verification["errors"])
            )
        records_path = integration_outputs / "gene_secondary_evidence_integration_v1.jsonl"
        unresolved_path = integration_outputs / "secondary_evidence_integration_unresolved_v1.jsonl"
        records = [
            GeneSecondaryEvidenceIntegrationRecordV1.model_validate(json.loads(line))
            for line in records_path.read_text().splitlines()
            if line.strip()
        ]
        unresolved_records = [
            SecondaryEvidenceIntegrationUnresolvedRecordV1.model_validate(json.loads(line))
            for line in unresolved_path.read_text().splitlines()
            if line.strip()
        ]
        policy = FinalEvidenceClassificationPolicyV1(
            policy_id=config.policy_id,
            numerical_tolerance=config.numerical_tolerance,
        )
        computed = compute_final_evidence_classification(
            secondary_evidence_records=records,
            secondary_unresolved_records=unresolved_records,
            policy=policy,
            source_secondary_evidence_integration_checksum=(
                final_evidence_classification_sha256_file(records_path)
            ),
        )
        write_final_evidence_classification_artifacts(
            output_dir=output_dir,
            run_record=FinalEvidenceClassificationRunRecordV1(
                run_id=context.run_id,
                secondary_evidence_integration_result_id=integration_contract.run_id,
                secondary_evidence_integration_checksum=(
                    final_evidence_classification_sha256_file(
                        integration_outputs / "stage_result.json"
                    )
                ),
                policy_id=policy.policy_id,
                policy_checksum=policy.fingerprint,
                started_at=started_at,
                completed_at=_utc_now(),
                status="completed",
                source_counts={
                    "gene_secondary_evidence_integration_records": len(records),
                    "secondary_evidence_integration_unresolved_records": len(unresolved_records),
                },
                verification_status="verified",
                warnings=tuple(computed.warnings),
            ),
            policy=policy,
            gene_classifications=computed.gene_classifications,
            unresolved=computed.unresolved,
            summary=computed.summary,
            warnings=computed.warnings,
        )
        verification = verify_final_evidence_classification_outputs(output_dir)
        if not verification["passed"]:
            raise RuntimeError(
                "final evidence classification verification failed: "
                + ", ".join(verification["errors"])
            )
        result_payload = json.loads(
            (output_dir / "final_evidence_classification_result_v1.json").read_text()
        )
        return StageExecutionResult(
            sorted(output_dir.iterdir()),
            computed.summary,
            computed.warnings,
            "FinalEvidenceClassificationResultV1",
            payload=result_payload,
        )

    def _execute_isoform_analysis(  # pragma: no cover
        self, context: RunContext, attempt_directory: Path
    ) -> StageExecutionResult:
        sequence_contract = load_dependency_contract(
            context,
            dependency_stage="sequence_analysis",
            expected_contract=SequenceAnalysisResultV1,
        )
        expression_contract = load_dependency_contract(
            context,
            dependency_stage="expression_analysis",
            expected_contract=ExpressionAnalysisResultV2,
        )
        self._record_consumed(
            context,
            dependency_stage="sequence_analysis",
            contract=sequence_contract,
            payload_fields=["sequence_hits"],
        )
        self._record_consumed(
            context,
            dependency_stage="expression_analysis",
            contract=expression_contract,
            artifacts=["normalized_gene_effects_v2.jsonl"],
            payload_fields=["normalized_gene_effects_artifact"],
        )
        transcripts = read_transcripts(context.config.sequence.transcript_fasta)
        sequence_hits = sequence_results_from_contract(sequence_contract)
        isoform_input_view = load_isoform_gene_effect_inputs(context.run_dir)
        input_outputs = _write_isoform_expression_input_artifacts(
            attempt_directory, isoform_input_view
        )
        results = analyze_isoforms_from_gene_effect_inputs(
            transcripts,
            sequence_hits,
            dict(isoform_input_view.by_gene),
            context.config.isoform.knockdown_efficiency_min,
            context.config.isoform.knockdown_efficiency_max,
        )
        payload = {gene: asdict(result) for gene, result in results.items()}
        output = write_contract(attempt_directory, "IsoformAnalysisResultV1", "1", payload)
        return StageExecutionResult(
            [*input_outputs, output],
            {
                "gene_count": len(results),
                "isoform_expression_input_included": len(isoform_input_view.records),
                "isoform_expression_input_excluded": len(isoform_input_view.exclusions),
            },
            [],
            "IsoformAnalysisResultV1",
            payload={
                "isoform_results": payload,
                "gene_count": len(results),
                "isoform_expression_input_summary": isoform_input_view.summary,
            },
        )

    def _execute_pathway_enrichment(  # pragma: no cover
        self, context: RunContext, attempt_directory: Path
    ) -> StageExecutionResult:
        expression_contract = load_dependency_contract(
            context,
            dependency_stage="expression_analysis",
            expected_contract=ExpressionAnalysisResultV2,
        )
        self._record_consumed(
            context,
            dependency_stage="expression_analysis",
            contract=expression_contract,
            artifacts=["normalized_gene_effects_v2.jsonl"],
            payload_fields=["normalized_gene_effects_artifact"],
        )
        pathway_input_view = load_pathway_gene_effect_inputs(context.run_dir)
        pathway_input_outputs = _write_downstream_expression_input_artifacts(
            attempt_directory, pathway_input_view, "pathway_expression_input_v1"
        )
        expression = dict(pathway_input_view.by_approved_symbol)
        regulons = read_regulons(context.config.pathway.regulon_file)
        results = analyze_pathway_enrichment(expression, regulons)
        provider_results: list[dict[str, Any]] = []
        provider_warnings: list[str] = []
        selected_providers: list[str] = []
        if context.config.pathway.cache_dir:
            selected_providers, provider_warnings = resolve_provider_snapshots(
                context.config.pathway.cache_dir,
                context.config.providers,
                ["reactome", "panther"],
            )
            enrichment_providers = [
                provider for provider in selected_providers if provider in {"reactome", "panther"}
            ]
            provider_results = [
                asdict(record)
                for record in load_enrichment_records(
                    context.config.pathway.cache_dir, enrichment_providers
                )
            ]
        enrichment_options = _pathway_enrichment_options(context.resolved_config)
        gene_set_options = enrichment_options.get("gene_sets", {})
        gene_sets = build_gene_sets(
            expression,
            adjusted_p_value_threshold=float(
                gene_set_options.get("adjusted_p_value_threshold", 0.05)
            ),
            absolute_log2_fold_change_threshold=float(
                gene_set_options.get("absolute_log2_fold_change_threshold", 0.5)
            ),
            use_shrunken_log2_fold_change=bool(
                gene_set_options.get("use_shrunken_log2_fold_change", True)
            ),
            include_low_count=bool(gene_set_options.get("include_low_count", False)),
            intended_target_gene=context.config.sirna.intended_target_gene,
        )
        local_ora_options = enrichment_options.get("local_ora", {})
        multiple_testing_options = enrichment_options.get("multiple_testing", {})
        annotation_cache_dir = _optional_path(enrichment_options.get("annotation_cache_dir"))
        strict_membership_required = bool(
            enrichment_options.get("require_complete_annotation_snapshot", False)
        ) or str(context.config.pathway.mode) in {"public_cache", "public_fetch"}
        annotation_snapshot_records: list[dict[str, Any]] = []
        if annotation_cache_dir:
            if context.config.config_path and not annotation_cache_dir.is_absolute():
                annotation_cache_dir = (context.config.config_path / annotation_cache_dir).resolve()
            complete_membership_records = load_verified_memberships(annotation_cache_dir)
            if strict_membership_required and any(
                record.completeness_status != "complete" for record in complete_membership_records
            ):
                raise RuntimeError(
                    "production pathway enrichment requires a verified complete annotation "
                    "membership snapshot; partial, submitted-hit-only, and unknown terms "
                    "are not eligible"
                )
            memberships = to_enrichment_memberships(complete_membership_records)
            annotation_snapshot_records = [asdict(record) for record in complete_membership_records]
        else:
            if strict_membership_required:
                raise RuntimeError(
                    "production pathway enrichment requires "
                    "pathway.enrichment.annotation_cache_dir with a verified complete "
                    "annotation membership snapshot"
                )
            memberships = build_memberships_from_provider_results(provider_results)
        background = build_background_universe(
            expression,
            memberships,
            mode=str(
                enrichment_options.get("background_mode", "tested_detectable_annotatable_genes")
            ),
            min_baseline_expression=float(enrichment_options.get("min_baseline_expression", 0.0)),
            include_low_count=bool(gene_set_options.get("include_low_count", False)),
        )
        local_results = run_local_ora(
            gene_sets,
            background,
            memberships,
            primary_test=str(local_ora_options.get("primary_test", "fisher_exact_greater")),
            calculate_diagnostic_alternative=bool(
                local_ora_options.get("calculate_diagnostic_alternative", True)
            ),
            require_complete_membership=bool(
                local_ora_options.get("require_complete_membership", True)
            ),
        )
        consensus_results = consensus_by_annotation_lineage(provider_results, local_results)
        incomplete_memberships = [
            membership
            for membership in memberships
            if membership.membership_completeness != "complete"
        ]
        pathway_output_dir = attempt_directory / "outputs" / "pathway_enrichment"
        pathway_output_dir.mkdir(parents=True, exist_ok=True)
        write_tsv(
            pathway_output_dir / "gene_set_definitions.tsv",
            [
                {
                    **asdict(gene_set),
                    "genes": ";".join(gene_set.genes),
                    "excluded_genes": ";".join(gene_set.excluded_genes),
                }
                for gene_set in gene_sets
            ],
        )
        dump_json(
            pathway_output_dir / "gene_set_manifest.json",
            {
                "gene_set_count": len(gene_sets),
                "gene_sets": [asdict(gene_set) for gene_set in gene_sets],
            },
        )
        write_tsv(
            pathway_output_dir / "background_universe.tsv",
            [{"gene": gene} for gene in background.genes],
        )
        write_tsv(
            pathway_output_dir / "background_exclusions.tsv", list(background.exclusion_records)
        )
        dump_json(pathway_output_dir / "background_manifest.json", asdict(background))
        write_tsv(
            pathway_output_dir / "annotation_memberships.tsv",
            annotation_snapshot_records or [asdict(membership) for membership in memberships],
        )
        dump_json(
            pathway_output_dir / "annotation_membership_manifest.json",
            {
                "membership_count": len(memberships),
                "complete_membership_count": len(memberships) - len(incomplete_memberships),
                "incomplete_membership_count": len(incomplete_memberships),
                "complete_membership_required": bool(
                    local_ora_options.get("require_complete_membership", True)
                ),
            },
        )
        write_tsv(
            pathway_output_dir / "annotation_membership_coverage.tsv",
            [
                {
                    "provider": membership.provider,
                    "annotation_source": membership.annotation_source,
                    "term_id": membership.term_id,
                    "term_name": membership.term_name,
                    "snapshot_id": membership.snapshot_id,
                    "membership_completeness": membership.membership_completeness,
                }
                for membership in memberships
            ],
        )
        write_tsv(
            pathway_output_dir / "incomplete_annotation_terms.tsv",
            [
                {
                    "provider": membership.provider,
                    "annotation_source": membership.annotation_source,
                    "term_id": membership.term_id,
                    "term_name": membership.term_name,
                    "snapshot_id": membership.snapshot_id,
                    "reason": ";".join(membership.warnings),
                }
                for membership in incomplete_memberships
            ],
        )
        write_tsv(
            pathway_output_dir / "local_ora_results.tsv",
            [
                {
                    **asdict(result),
                    "matched_genes": ";".join(result.matched_genes),
                    "contingency_table": ";".join(map(str, result.contingency_table)),
                }
                for result in local_results
            ],
        )
        write_tsv(
            pathway_output_dir / "enrichment_correction_families.tsv",
            [
                {
                    "correction_family_id": result.correction_family_id,
                    "correction_family_size": result.correction_family_size,
                    "correction_method": result.correction_method,
                    "correction_policy_version": result.correction_policy_version,
                    "configured_scope": ";".join(
                        multiple_testing_options.get(
                            "family_scope",
                            [
                                "provider",
                                "annotation_dataset",
                                "gene_set_id",
                                "expression_direction",
                                "calculation_mode",
                            ],
                        )
                    ),
                }
                for result in local_results
            ],
        )
        write_tsv(
            pathway_output_dir / "regulon_context_results.tsv",
            [
                {
                    "gene": gene,
                    "regulon_evidence": result.regulon_evidence,
                    "stress_signature_evidence": result.stress_signature_evidence,
                    "pathway_coherence": result.pathway_coherence,
                    "interpretation": "contextual_regulon_overlap_not_enrichment",
                }
                for gene, result in results.items()
            ],
        )
        regulon_context = [
            {
                "gene": gene,
                "regulon_evidence": result.regulon_evidence,
                "stress_signature_evidence": result.stress_signature_evidence,
                "pathway_coherence": result.pathway_coherence,
                "interpretation": "contextual_regulon_overlap_not_enrichment",
            }
            for gene, result in results.items()
        ]
        annotation_membership_summary = {
            "snapshot_backed": bool(annotation_cache_dir),
            "record_count": len(memberships),
            "complete_record_count": len(memberships) - len(incomplete_memberships),
            "incomplete_record_count": len(incomplete_memberships),
        }
        identifier_mapping_summary = {
            "mapped_count": len(expression),
            "resolver": "central_identifier_resolution",
            "snapshot_required_for_production_aliases": True,
        }
        dump_json(
            pathway_output_dir / "pathway_scientific_policy_manifest.json",
            {
                "local_ora": {
                    "primary_test": str(
                        local_ora_options.get("primary_test", "fisher_exact_greater")
                    ),
                    "calculate_diagnostic_alternative": bool(
                        local_ora_options.get("calculate_diagnostic_alternative", True)
                    ),
                    "require_complete_membership": bool(
                        local_ora_options.get("require_complete_membership", True)
                    ),
                    "test_policy_version": "ora-test-policy-v2",
                },
                "multiple_testing": {
                    "method": multiple_testing_options.get("method", "benjamini_hochberg"),
                    "family_scope": multiple_testing_options.get(
                        "family_scope",
                        [
                            "provider",
                            "annotation_dataset",
                            "gene_set_id",
                            "expression_direction",
                            "calculation_mode",
                        ],
                    ),
                    "correction_policy_version": "correction-family-policy-v2",
                },
                "regulon_context_separated": True,
            },
        )
        provider_manifest = summarize_provider_snapshots(
            context.config.pathway.cache_dir,
            selected_providers,
            provider_warnings,
        )
        warning_list = (
            list(provider_warnings)
            + list(background.warnings)
            + [
                "incomplete annotation memberships were excluded from production local ORA"
                for _ in incomplete_memberships[:1]
            ]
        )
        pathway_v2_payload = {
            "gene_sets": {gene_set.gene_set_id: list(gene_set.genes) for gene_set in gene_sets},
            "background_universe": list(background.genes),
            "provider_calculated_enrichment": provider_results,
            "locally_calculated_enrichment": [asdict(result) for result in local_results],
            "enrichment_consensus": consensus_results,
            "annotation_membership_summary": annotation_membership_summary,
            "identifier_mapping_summary": identifier_mapping_summary,
            "provider_snapshot_manifest": provider_manifest,
            "annotation_snapshot_manifest": {
                "snapshot_backed": bool(annotation_cache_dir),
                "annotation_cache_dir": str(annotation_cache_dir) if annotation_cache_dir else "",
            },
            "regulon_context": regulon_context,
            "warnings": warning_list,
        }
        dump_json(
            pathway_output_dir / "pathway_enrichment_v2.payload.json",
            {
                "contract": "PathwayEnrichmentResultV2",
                "schema_version": "2",
                "payload": pathway_v2_payload,
            },
        )
        output = write_contract(
            attempt_directory, "PathwayEnrichmentResultV2", "2", pathway_v2_payload
        )
        outputs = [
            output,
            *pathway_input_outputs,
            *[path for path in pathway_output_dir.rglob("*") if path.is_file()],
        ]
        return StageExecutionResult(
            outputs,
            {
                "pathway_gene_count": len(results),
                "gene_set_count": len(gene_sets),
                "local_ora_result_count": len(local_results),
            },
            list(provider_warnings),
            "PathwayEnrichmentResultV2",
            contract_version="2",
            payload=pathway_v2_payload,
        )

    def _execute_mechanistic_network(  # pragma: no cover
        self, context: RunContext, attempt_directory: Path
    ) -> StageExecutionResult:
        expression_contract = load_dependency_contract(
            context,
            dependency_stage="expression_analysis",
            expected_contract=ExpressionAnalysisResultV2,
        )
        self._record_consumed(
            context,
            dependency_stage="expression_analysis",
            contract=expression_contract,
            artifacts=["normalized_gene_effects_v2.jsonl"],
            payload_fields=["normalized_gene_effects_artifact"],
        )
        network_input_view = load_network_gene_effect_inputs(context.run_dir)
        network_input_outputs = _write_downstream_expression_input_artifacts(
            attempt_directory, network_input_view, "network_expression_input_v1"
        )
        expression = dict(network_input_view.by_approved_symbol)
        provider_evidence = []
        provider_warnings: list[str] = []
        selected_providers: list[str] = []
        provider_cache_dir = context.config.pathway.cache_dir
        mechanism_providers = [
            "omnipath",
            "signor",
            "reactome_content",
            "reactome_fi",
        ]
        requires_cache = provider_mode_requires_cache(
            context.config.providers, context.config.pathway.mode
        )
        if provider_cache_dir:
            selected_providers, provider_warnings = resolve_provider_snapshots(
                provider_cache_dir,
                context.config.providers,
                mechanism_providers,
            )
            selected_mechanism_providers = [
                provider for provider in selected_providers if provider in mechanism_providers
            ]
            provider_evidence = load_provider_edge_evidence(
                provider_cache_dir,
                selected_mechanism_providers,
            )
        if not provider_evidence and context.config.pathway.synthetic_mode:
            synthetic_cache_dir = Path(__file__).resolve().parents[3] / "resources/pathway_cache"
            if synthetic_cache_dir.exists():
                provider_cache_dir = synthetic_cache_dir
                selected_providers, provider_warnings = resolve_provider_snapshots(
                    synthetic_cache_dir,
                    context.config.providers,
                    mechanism_providers,
                )
                selected_mechanism_providers = [
                    provider for provider in selected_providers if provider in mechanism_providers
                ]
                provider_evidence = load_provider_edge_evidence(
                    synthetic_cache_dir,
                    selected_mechanism_providers,
                )
                provider_warnings.append("synthetic_fixture_provider_cache_used")
        if requires_cache and not provider_evidence:
            msg = "public_cache pathway mode requires canonical raw provider edge evidence"
            raise RuntimeError(msg)
        if not provider_evidence:
            msg = (
                "missing_canonical_provider_evidence: "
                "mechanistic V2 runtime cannot use legacy paths"
            )
            raise RuntimeError(msg)
        provider_manifest = {
            **summarize_provider_snapshots(
                provider_cache_dir,
                selected_providers,
                provider_warnings,
            ),
            "loaded_evidence_providers": sorted({edge.provider for edge in provider_evidence}),
        }
        identifier_resolver = _mechanistic_identifier_resolver(context, attempt_directory)
        path_config_fingerprint = relevant_config_hash(
            context,
            (
                "pathway.max_path_length",
                "pathway.maximum_paths_per_candidate",
                "pathway.maximum_total_paths",
                "pathway.shortest_paths_only",
                "pathway.trace_signed_paths",
                "pathway.trace_unsigned_paths",
                "pathway.trace_contextual_paths",
                "pathway.allow_unsigned_context_paths",
            ),
        )
        mechanistic_v2_payload = {
            **build_mechanistic_network_payload_v2(
                raw_provider_evidence_rows=[asdict(edge) for edge in provider_evidence],
                legacy_trace_edges=[],
                legacy_trace_paths=[],
                provider_snapshot_manifest=provider_manifest,
                organism=context.config.project.organism,
                identifier_resolver=identifier_resolver,
                path_search_source_symbols=[context.config.sirna.intended_target_gene],
                observed_directions_by_symbol={
                    gene: str(result.direction) for gene, result in expression.items()
                },
                max_path_length=context.config.pathway.max_path_length,
                maximum_paths_per_candidate=(context.config.pathway.maximum_paths_per_candidate),
                maximum_total_paths=context.config.pathway.maximum_total_paths,
                shortest_paths_only=context.config.pathway.shortest_paths_only,
                trace_signed_paths=context.config.pathway.trace_signed_paths,
                trace_unsigned_paths=(
                    context.config.pathway.trace_unsigned_paths
                    and context.config.pathway.allow_unsigned_context_paths
                ),
                trace_contextual_paths=(
                    context.config.pathway.trace_contextual_paths
                    and context.config.pathway.allow_unsigned_context_paths
                ),
                created_from_config_fingerprint=path_config_fingerprint,
                experiment_context={
                    "organism": context.config.project.organism,
                    "cell_type": context.config.experiment.cell_type,
                    "experimental_system": context.config.experiment.delivery_method,
                },
                migration_diagnostics_enabled=(
                    context.config.pathway.enable_legacy_path_comparison
                ),
                warnings=list(provider_warnings),
            )
        }
        output = write_contract(
            attempt_directory, "MechanisticNetworkResultV2", "2", mechanistic_v2_payload
        )
        return StageExecutionResult(
            [*network_input_outputs, output],
            dict(mechanistic_v2_payload.get("metrics", {})),
            [],
            "MechanisticNetworkResultV2",
            contract_version="2",
            payload=mechanistic_v2_payload,
        )


def stage_fingerprint(
    stage: PipelineStage, context: RunContext, dependency_data: dict[str, Any]
) -> str:
    input_hashes = {}
    for path in stage.required_inputs(context):
        input_hashes[str(path)] = sha256_file(path) if path.exists() and path.is_file() else None
    return hash_data(
        {
            "stage_name": stage.name,
            "stage_version": stage.version,
            "relevant_config": _select_config(
                context.resolved_config, stage.relevant_config_paths()
            ),
            "input_hashes": input_hashes,
            "dependencies": dependency_data,
            "scientific_policy_version": "1",
        }
    )


def build_stages() -> dict[str, FunctionStage]:
    common_execution = ("execution", "outputs", "schema_version")
    return {
        "validate": FunctionStage(
            "validate",
            "1.0",
            ("schema_version", "project", "inputs", "execution", "outputs"),
            ("transcripts", "annotation", "counts", "metadata", "network", "regulons"),
            "Validate YAML, file existence, and execution DAG readiness.",
        ),
        "prepare_inputs": FunctionStage(
            "prepare_inputs",
            "1.0",
            ("inputs", "sequence", "expression", "pathway", *common_execution),
            ("transcripts", "annotation", "counts", "metadata", "network", "regulons"),
            "Prepare and checksum analysis input files.",
        ),
        "map_identifiers": FunctionStage(
            "map_identifiers",
            "1.0",
            ("inputs", "sequence", "pathway", *common_execution),
            ("transcripts",),
            "Map identifiers and record unmapped or ambiguous values.",
        ),
        "sequence_analysis": FunctionStage(
            "sequence_analysis",
            "1.0",
            ("sirna", "sequence", *common_execution),
            ("transcripts",),
            "Find guide and passenger sequence evidence across transcripts.",
        ),
        "expression_analysis": FunctionStage(
            "expression_analysis",
            "1.0",
            ("experiment", "expression", *common_execution),
            ("counts", "metadata"),
            "Analyze expression evidence with the configured backend.",
        ),
        "mechanistic_network": FunctionStage(
            "mechanistic_network",
            "1.0",
            (
                "pathway",
                "providers",
                "project",
                "sirna",
                "experiment",
                "expression",
                *common_execution,
            ),
            (),
            "Build candidate-level mechanistic network evidence for residual support.",
        ),
        "isoform_uncertainty": FunctionStage(
            "isoform_uncertainty",
            "1.0",
            ("isoform_uncertainty", "project", "expression", *common_execution),
            ("counts", "metadata"),
            "Resolve transcript-set uncertainty records from verified annotation.",
        ),
        "transcript_targetability": FunctionStage(
            "transcript_targetability",
            "1.0",
            ("transcript_targetability", "sirna", "project", *common_execution),
            (),
            "Search eligible transcripts for guide-compatible sequence evidence.",
        ),
        "transcript_targetability_ratio": FunctionStage(
            "transcript_targetability_ratio",
            "1.0",
            (
                "transcript_targetability_ratio",
                "transcript_targetability",
                "isoform_uncertainty",
                *common_execution,
            ),
            (),
            "Count formal N, M, and M/N from committed transcript targetability evidence.",
        ),
        "expected_direct_effect": FunctionStage(
            "expected_direct_effect",
            "1.0",
            (
                "expected_direct_effect",
                "sirna",
                "expression",
                "transcript_targetability_ratio",
                *common_execution,
            ),
            (),
            "Estimate expected direct expression effects without residual attribution.",
        ),
        "residual_attribution": FunctionStage(
            "residual_attribution",
            "1.0",
            (
                "residual_attribution",
                "expected_direct_effect",
                "pathway",
                *common_execution,
            ),
            (),
            "Characterize unresolved residual support without final classification.",
        ),
        "secondary_evidence_integration": FunctionStage(
            "secondary_evidence_integration",
            "1.0",
            (
                "secondary_evidence_integration",
                "residual_attribution",
                *common_execution,
            ),
            (),
            "Integrate classification-ready evidence without final classification.",
        ),
        "final_evidence_classification": FunctionStage(
            "final_evidence_classification",
            "1.0",
            (
                "final_evidence_classification",
                "secondary_evidence_integration",
                *common_execution,
            ),
            (),
            "Classify genes with conservative evidence-based labels.",
        ),
    }
