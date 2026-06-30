from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class IdentifierMappingResult:
    input_identifier: str
    inferred_input_type: str
    normalized_identifier: str
    mapped_identifier: str | None
    organism: str
    mapping_status: str
    ambiguity: bool
    candidate_mappings: tuple[str, ...]
    mapping_provider: str
    mapping_database_version: str
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class MechanisticEdge:
    source_node: str
    target_node: str
    directed: bool
    sign: str
    relation_type: str
    mechanism: str
    original_provider: str
    original_database_source: str
    publication_identifiers: tuple[str, ...]
    organism: str
    confidence_metadata: str
    database_version: str
    retrieval_date: str
    deduplication_key: str


@dataclass(frozen=True)
class FunctionalEdge:
    source_node: str
    target_node: str
    provider: str
    support_type: str = "unsigned functional support only"
    database_version: str = "synthetic_snapshot_v1"


@dataclass(frozen=True)
class PathwayRelation:
    gene: str
    pathway_id: str
    pathway_name: str
    provider: str
    relation_type: str


@dataclass(frozen=True)
class MechanisticPath:
    intended_target: str
    candidate: str
    ordered_nodes: tuple[str, ...]
    ordered_edges: tuple[str, ...]
    relation_types: tuple[str, ...]
    edge_signs: tuple[str, ...]
    composed_path_sign: int | None
    expected_candidate_direction: str | None
    observed_direction: str
    direction_consistency: bool | None
    conflicting_paths: bool
    provider_sources: tuple[str, ...]
    publication_references: tuple[str, ...]
    database_versions: tuple[str, ...]
    evidence_limitations: tuple[str, ...]


@dataclass(frozen=True)
class EnrichmentResult:
    provider: str
    annotation_dataset: str
    pathway_id: str
    pathway_name: str
    gene_set_category: str
    expression_direction: str
    observed_count: int
    expected_count: float
    enrichment_ratio: float
    raw_p_value: float
    fdr: float
    matched_genes: tuple[str, ...]
    background_size: int
    test_list_size: int
    organism: str
    database_release: str
    retrieval_timestamp: str
    request_checksum: str
    response_checksum: str
