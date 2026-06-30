from __future__ import annotations

from pathlib import Path
from typing import Any

from sirna_offtarget.config import ProviderSelectionConfig
from sirna_offtarget.pathway.providers.cache import is_verified, latest_snapshot_dir, read_jsonl
from sirna_offtarget.pathway.providers.exceptions import ProviderSnapshotError
from sirna_offtarget.pathway.providers.models import (
    ConsensusMechanisticEdgeRecord,
    PathwayEnrichmentProviderRecord,
    ProviderEdgeEvidenceRecord,
)
from sirna_offtarget.pathway.providers.modes import ProviderMode, normalize_provider_name
from sirna_offtarget.pathway.providers.normalization import build_consensus_edges


def load_provider_edge_evidence(
    cache_dir: Path,
    providers: list[str],
) -> list[ProviderEdgeEvidenceRecord]:
    records: list[ProviderEdgeEvidenceRecord] = []
    for provider in providers:
        snapshot = latest_snapshot_dir(cache_dir, provider.replace("-", "_"))
        if snapshot is None:
            continue
        for row in read_jsonl(snapshot / "normalized" / "records.jsonl"):
            if "source" in row and "target" in row and "sign" in row:
                records.append(_provider_edge_from_dict(row))
    return records


def resolve_provider_snapshots(
    cache_dir: Path,
    provider_config: dict[str, ProviderSelectionConfig],
    default_providers: list[str],
) -> tuple[list[str], list[str]]:
    selected: list[str] = []
    warnings: list[str] = []
    if provider_config:
        items = list(provider_config.items())
    else:
        items = [
            (provider, ProviderSelectionConfig(mode="local_snapshot"))
            for provider in default_providers
        ]
    for raw_name, config in items:
        provider = normalize_provider_name(raw_name)
        if config.mode == ProviderMode.DISABLED:
            continue
        if config.mode in {ProviderMode.SYNTHETIC_FIXTURE, ProviderMode.LOCAL_SNAPSHOT}:
            selected.append(provider)
            continue
        if config.mode == ProviderMode.PUBLIC_FETCH:
            raise ProviderSnapshotError(
                f"provider {provider} is configured public_fetch during analysis; "
                "run pathway-db fetch first and use public_cache"
            )
        if config.mode == ProviderMode.PUBLIC_CACHE:
            snapshot = latest_snapshot_dir(cache_dir, provider)
            if snapshot is None or not is_verified(snapshot):
                message = f"required provider cache missing or invalid: {provider}"
                if config.required:
                    raise ProviderSnapshotError(message)
                warnings.append(message)
                continue
            selected.append(provider)
            continue
        raise ProviderSnapshotError(f"unsupported provider mode {config.mode!r} for {provider}")
    return selected, warnings


def provider_mode_requires_cache(
    provider_config: dict[str, ProviderSelectionConfig], pathway_mode: str
) -> bool:
    mode = pathway_mode.lower()
    if mode == ProviderMode.PUBLIC_CACHE:
        return True
    return any(config.mode == ProviderMode.PUBLIC_CACHE for config in provider_config.values())


def summarize_provider_snapshots(
    cache_dir: Path | None,
    providers: list[str],
    warnings: list[str] | None = None,
) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "cache_dir": str(cache_dir) if cache_dir else "",
        "providers": providers,
        "warnings": list(warnings or ()),
    }
    snapshots: list[dict[str, Any]] = []
    if cache_dir:
        for provider in providers:
            snapshot = latest_snapshot_dir(cache_dir, provider)
            snapshots.append(
                {
                    "provider": provider,
                    "snapshot_path": str(snapshot) if snapshot else "",
                    "verified": bool(snapshot and is_verified(snapshot)),
                }
            )
    summary["snapshots"] = snapshots
    return summary


def load_consensus_edges(
    cache_dir: Path, providers: list[str]
) -> list[ConsensusMechanisticEdgeRecord]:
    return build_consensus_edges(load_provider_edge_evidence(cache_dir, providers))


def load_enrichment_records(
    cache_dir: Path,
    providers: list[str],
) -> list[PathwayEnrichmentProviderRecord]:
    records: list[PathwayEnrichmentProviderRecord] = []
    for provider in providers:
        snapshot = latest_snapshot_dir(cache_dir, provider.replace("-", "_"))
        if snapshot is None:
            continue
        for row in read_jsonl(snapshot / "normalized" / "records.jsonl"):
            if "term_id" in row or "pathway_id" in row:
                records.append(_enrichment_from_dict(row))
    return records


def _provider_edge_from_dict(row: dict[str, Any]) -> ProviderEdgeEvidenceRecord:
    return ProviderEdgeEvidenceRecord(
        evidence_id=str(row["evidence_id"]),
        provider=str(row["provider"]),
        access_route=str(row["access_route"]),
        source=str(row["source"]),
        target=str(row["target"]),
        source_identifier=str(row["source_identifier"]),
        target_identifier=str(row["target_identifier"]),
        directed=bool(row["directed"]),
        sign=str(row["sign"]),
        relation_type=str(row["relation_type"]),
        mechanism=str(row["mechanism"]),
        functional_only=bool(row["functional_only"]),
        causal_eligible=bool(row["causal_eligible"]),
        original_sources=tuple(row.get("original_sources", ())),
        references=tuple(row.get("references", ())),
        organism=str(row["organism"]),
        evidence_level=str(row["evidence_level"]),
        provider_record_id=str(row["provider_record_id"]),
        database_version=str(row["database_version"]),
        retrieval_snapshot=str(row["retrieval_snapshot"]),
        predicted_only=bool(row["predicted_only"]),
        lineage_key=str(row["lineage_key"]),
        warnings=tuple(row.get("warnings", ())),
    )


def _enrichment_from_dict(row: dict[str, Any]) -> PathwayEnrichmentProviderRecord:
    return PathwayEnrichmentProviderRecord(
        provider=str(row["provider"]),
        annotation_source=str(row["annotation_source"]),
        term_id=str(row["term_id"]),
        term_name=str(row["term_name"]),
        gene_set_category=str(row["gene_set_category"]),
        expression_direction=str(row["expression_direction"]),
        observed_count=int(row["observed_count"]),
        expected_count=float(row["expected_count"]),
        fold_enrichment=float(row["fold_enrichment"]),
        raw_p_value=float(row["raw_p_value"]),
        adjusted_p_value=float(row["adjusted_p_value"]),
        matched_genes=tuple(row.get("matched_genes", ())),
        submitted_gene_count=int(row["submitted_gene_count"]),
        background_gene_count=int(row["background_gene_count"]),
        tested_gene_universe=tuple(row.get("tested_gene_universe", ())),
        organism=str(row["organism"]),
        database_version=str(row["database_version"]),
        retrieval_snapshot=str(row["retrieval_snapshot"]),
        request_checksum=str(row["request_checksum"]),
        response_checksum=str(row["response_checksum"]),
        warnings=tuple(row.get("warnings", ())),
    )
