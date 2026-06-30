from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ProviderManifest:
    provider: str
    snapshot_id: str
    organism: str
    endpoint: str
    request_parameters: dict[str, str]
    retrieval_timestamp: str
    database_version: str
    api_version: str | None
    normalization_schema_version: str
    raw_files: tuple[str, ...]
    normalized_files: tuple[str, ...]
    file_checksums: dict[str, str]
    record_counts: dict[str, int]
    warning_count: int
    license_notes: str
    completeness_status: str


@dataclass(frozen=True)
class IdentifierMappingRecord:
    input_identifier: str
    input_identifier_type: str
    normalized_identifier: str
    output_identifier_type: str
    mapped_identifier: str | None
    organism: str
    mapping_status: str
    ambiguity_status: str
    candidate_mappings: tuple[str, ...]
    mapping_provider: str
    database_version: str
    snapshot_id: str
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class ProviderEdgeEvidenceRecord:
    evidence_id: str
    provider: str
    access_route: str
    source: str
    target: str
    source_identifier: str
    target_identifier: str
    directed: bool
    sign: str
    relation_type: str
    mechanism: str
    functional_only: bool
    causal_eligible: bool
    original_sources: tuple[str, ...]
    references: tuple[str, ...]
    organism: str
    evidence_level: str
    provider_record_id: str
    database_version: str
    retrieval_snapshot: str
    predicted_only: bool
    lineage_key: str
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class ConsensusMechanisticEdgeRecord:
    edge_id: str
    source: str
    target: str
    directed: bool
    consensus_sign: str
    relation_type: str
    mechanism: str
    provider_sources: tuple[str, ...]
    references: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    lineage_groups: tuple[str, ...]
    independent_source_count: int
    reference_count: int
    positive_support: int
    negative_support: int
    unsigned_support: int
    conflicting_support: int
    evidence_level: str
    functional_only: bool
    causal_eligible: bool
    predicted_only: bool
    database_versions: tuple[str, ...]
    retrieval_snapshots: tuple[str, ...]
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class PathwayEnrichmentProviderRecord:
    provider: str
    annotation_source: str
    term_id: str
    term_name: str
    gene_set_category: str
    expression_direction: str
    observed_count: int
    expected_count: float
    fold_enrichment: float
    raw_p_value: float
    adjusted_p_value: float
    matched_genes: tuple[str, ...]
    submitted_gene_count: int
    background_gene_count: int
    tested_gene_universe: tuple[str, ...]
    organism: str
    database_version: str
    retrieval_snapshot: str
    request_checksum: str
    response_checksum: str
    warnings: tuple[str, ...] = ()
