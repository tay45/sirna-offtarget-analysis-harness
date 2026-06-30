from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class NormalizedMechanisticEdge:
    edge_id: str
    source: str
    target: str
    source_identifier: str
    target_identifier: str
    directed: bool
    sign: str
    relation_type: str
    mechanism: str
    provider: str
    original_sources: tuple[str, ...]
    references: tuple[str, ...]
    organism: str
    evidence_level: str
    signed_support_count: int
    unsigned_support_count: int
    source_count: int
    reference_count: int
    predicted_only: bool
    conflict: bool
    database_versions: tuple[str, ...]
    retrieval_snapshots: tuple[str, ...]
    lineage_key: str
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class NormalizedMechanisticPath:
    path_id: str
    intended_target: str
    candidate: str
    ordered_nodes: tuple[str, ...]
    ordered_edge_ids: tuple[str, ...]
    path_length: int
    directed: bool
    fully_signed: bool
    composed_sign: str | None
    expected_candidate_direction_after_target_decrease: str | None
    observed_candidate_direction: str
    direction_consistent: bool | None
    provider_sources: tuple[str, ...]
    references: tuple[str, ...]
    evidence_score: float
    conflicting_with_other_paths: bool
    unsigned_edge_count: int
    conflicting_edge_count: int = 0
    positive_composed_path_count: int = 0
    negative_composed_path_count: int = 0
    warnings: tuple[str, ...] = ()
