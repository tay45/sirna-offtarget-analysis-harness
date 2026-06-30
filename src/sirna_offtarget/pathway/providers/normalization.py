from __future__ import annotations

import hashlib

from sirna_offtarget.identifiers import detect_identifier_type, normalize_identifier_value
from sirna_offtarget.identifiers.api import resolve_identifier
from sirna_offtarget.pathway.providers.models import (
    ConsensusMechanisticEdgeRecord,
    IdentifierMappingRecord,
    ProviderEdgeEvidenceRecord,
)


def infer_identifier_type(identifier: str) -> str:
    return detect_identifier_type(identifier)


def normalize_identifier(
    identifier: str,
    *,
    organism: str,
    mapping_provider: str,
    database_version: str,
    snapshot_id: str,
    aliases: dict[str, tuple[str, ...]] | None = None,
) -> IdentifierMappingRecord:
    resolution = resolve_identifier(identifier, aliases=aliases)
    if resolution.status == "invalid":
        return IdentifierMappingRecord(
            identifier,
            "invalid",
            "",
            "hgnc_symbol",
            None,
            organism,
            "invalid",
            "none",
            (),
            mapping_provider,
            database_version,
            snapshot_id,
            ("empty identifier",),
        )
    if resolution.status == "ambiguous":
        return IdentifierMappingRecord(
            resolution.input_identifier,
            resolution.input_identifier_type,
            resolution.normalized_identifier,
            "hgnc_symbol",
            None,
            organism,
            "ambiguous",
            "ambiguous",
            resolution.candidate_mappings,
            mapping_provider,
            database_version,
            snapshot_id,
            resolution.warnings,
        )
    mapped = resolution.mapped_identifier or normalize_identifier_value(identifier)
    return IdentifierMappingRecord(
        resolution.input_identifier,
        resolution.input_identifier_type,
        resolution.normalized_identifier,
        resolution.output_identifier_type,
        mapped,
        organism,
        "mapped",
        "unambiguous",
        resolution.candidate_mappings,
        mapping_provider,
        database_version,
        snapshot_id,
    )


def normalize_sign(value: str | bool | None, inhibition: bool | None = None) -> str:
    if isinstance(value, bool):
        stimulation = value
        if stimulation and inhibition:
            return "conflicting"
        if stimulation:
            return "positive"
        if inhibition:
            return "negative"
        return "unknown"
    normalized = str(value or "").strip().lower()
    if normalized in {"1", "+", "+1", "positive", "activation", "activates", "stimulation"}:
        return "positive"
    if normalized in {"-1", "-", "negative", "inhibition", "inhibits"}:
        return "negative"
    if normalized in {"conflict", "conflicting", "both"}:
        return "conflicting"
    if normalized in {"unsigned", "functional", "association"}:
        return "unsigned"
    return "unknown"


def lineage_key(
    source: str,
    target: str,
    relation_type: str,
    sign: str,
    original_source: str,
    primary_reference_or_record: str,
) -> str:
    parts = (
        source.upper(),
        target.upper(),
        relation_type.lower(),
        sign.lower(),
        original_source.lower(),
        primary_reference_or_record.lower(),
    )
    return hashlib.sha256("|".join(parts).encode()).hexdigest()[:24]


def deduplicate_lineage(
    records: list[ProviderEdgeEvidenceRecord],
) -> list[ProviderEdgeEvidenceRecord]:
    grouped: dict[str, ProviderEdgeEvidenceRecord] = {}
    for record in records:
        if record.lineage_key not in grouped:
            grouped[record.lineage_key] = record
            continue
        current = grouped[record.lineage_key]
        grouped[record.lineage_key] = ProviderEdgeEvidenceRecord(
            **{
                **current.__dict__,
                "access_route": ",".join(sorted({current.access_route, record.access_route})),
                "references": tuple(sorted(set(current.references) | set(record.references))),
                "warnings": tuple(
                    sorted(
                        set(current.warnings) | set(record.warnings) | {"lineage duplicate merged"}
                    )
                ),
            }
        )
    return sorted(grouped.values(), key=lambda item: item.evidence_id)


def build_consensus_edges(
    records: list[ProviderEdgeEvidenceRecord],
) -> list[ConsensusMechanisticEdgeRecord]:
    deduped = deduplicate_lineage(records)
    grouped: dict[tuple[str, str], list[ProviderEdgeEvidenceRecord]] = {}
    for record in deduped:
        grouped.setdefault((record.source, record.target), []).append(record)
    consensus: list[ConsensusMechanisticEdgeRecord] = []
    for index, ((source, target), items) in enumerate(sorted(grouped.items()), start=1):
        positive = [item for item in items if item.sign == "positive"]
        negative = [item for item in items if item.sign == "negative"]
        unsigned = [item for item in items if item.sign == "unsigned"]
        conflicting = [item for item in items if item.sign == "conflicting"]
        if positive and negative or conflicting:
            sign = "conflicting"
        elif positive:
            sign = "positive"
        elif negative:
            sign = "negative"
        elif unsigned:
            sign = "unsigned"
        else:
            sign = "unknown"
        causal = sign in {"positive", "negative"} and any(item.causal_eligible for item in items)
        functional_only = all(item.functional_only for item in items)
        consensus.append(
            ConsensusMechanisticEdgeRecord(
                edge_id=f"consensus_edge_{index:05d}",
                source=source,
                target=target,
                directed=any(item.directed for item in items),
                consensus_sign=sign,
                relation_type="consensus_mechanistic_relation",
                mechanism="lineage_deduplicated_consensus",
                provider_sources=tuple(sorted({item.provider for item in items})),
                references=tuple(sorted({ref for item in items for ref in item.references})),
                evidence_ids=tuple(item.evidence_id for item in items),
                lineage_groups=tuple(sorted({item.lineage_key for item in items})),
                independent_source_count=len({item.lineage_key for item in items}),
                reference_count=len({ref for item in items for ref in item.references}),
                positive_support=len(positive),
                negative_support=len(negative),
                unsigned_support=len(unsigned),
                conflicting_support=len(conflicting),
                evidence_level="curated" if any(item.references for item in items) else "provider",
                functional_only=functional_only,
                causal_eligible=causal,
                predicted_only=all(item.predicted_only for item in items),
                database_versions=tuple(sorted({item.database_version for item in items})),
                retrieval_snapshots=tuple(sorted({item.retrieval_snapshot for item in items})),
                warnings=(("conflicting signed support",) if sign == "conflicting" else ())
                + (("functional-only unsigned edge",) if functional_only else ()),
            )
        )
    return consensus
