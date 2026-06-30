from __future__ import annotations

from dataclasses import dataclass

ENTITY_TYPES = {
    "gene",
    "protein",
    "transcript",
    "complex",
    "protein_family",
    "entity_set",
    "pathway",
    "reaction",
    "small_molecule",
    "phenotype",
    "unknown",
}

EVIDENCE_LEVELS = ("high", "moderate", "low", "contextual", "conflicting", "insufficient")


@dataclass(frozen=True)
class BiologicalEntityRecordV2:
    entity_id: str
    entity_type: str
    display_name: str
    canonical_identifier: str
    organism: str
    source_identifiers: tuple[str, ...]
    canonical_gene_ids: tuple[str, ...]
    member_entity_ids: tuple[str, ...]
    entity_set_semantics: str
    identifier_snapshot_id: str
    mapping_confidence: float
    ambiguity_status: str
    provider_sources: tuple[str, ...]
    provider_record_ids: tuple[str, ...]
    compartments: tuple[str, ...]
    contexts: tuple[str, ...]
    warnings: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.entity_type not in ENTITY_TYPES:
            msg = f"unsupported entity_type: {self.entity_type}"
            raise ValueError(msg)
        if (
            self.entity_type in {"small_molecule", "phenotype", "unknown"}
            and self.canonical_gene_ids
        ):
            msg = f"{self.entity_type} cannot carry canonical_gene_ids"
            raise ValueError(msg)


@dataclass(frozen=True)
class ProviderEdgeEvidenceRecordV2:
    evidence_id: str
    source_entity_id: str
    target_entity_id: str
    source_resolution_id: str
    target_resolution_id: str
    source_entity_type: str
    target_entity_type: str
    directed: bool
    sign: str
    relation_type: str
    mechanism: str
    directness: str
    functional_only: bool
    contextual_only: bool
    causal_eligible: bool
    original_provider: str
    access_provider: str
    original_database: str
    provider_record_id: str
    references: tuple[str, ...]
    organism: str
    cell_type: str | None
    tissue: str | None
    compartment: str | None
    experimental_system: str | None
    disease_state: str | None
    predicted_only: bool
    curated_status: str
    identifier_snapshot_id: str
    provider_snapshot_id: str
    provider_version: str
    normalization_version: str
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class EvidenceQualityComponentsV2:
    directed_support: float
    signed_support: float
    explicit_mechanism_support: float
    direct_interaction_support: float
    curated_support: float
    independent_publication_count: int
    independent_original_database_count: int
    identifier_mapping_confidence: float
    organism_match: bool
    cell_type_match: bool | None
    tissue_match: bool | None
    compartment_match: bool | None
    experimental_system_match: bool | None
    predicted_only_penalty: float
    indirect_relation_penalty: float
    lineage_dependence_penalty: float
    conflict_penalty: float
    missing_context_penalty: float
    unsupported_entity_penalty: float
    component_weights: dict[str, float]
    missing_components: tuple[str, ...]
    raw_score: float
    capped_score: float
    cap_reasons: tuple[str, ...]
    final_level: str
    uncertainty: float
    policy_version: str
    warnings: tuple[str, ...] = ()
    disease_state_match: bool | None = None


@dataclass(frozen=True)
class PathSearchPolicyV1:
    schema_version: str
    policy_id: str
    max_path_length: int
    maximum_paths_per_candidate: int
    maximum_total_paths: int | None
    shortest_paths_only: bool
    trace_signed_paths: bool
    trace_unsigned_paths: bool
    trace_contextual_paths: bool
    include_conflicting_edges: bool
    deterministic_path_order: tuple[str, ...]
    source_selection_policy_version: str
    candidate_selection_policy_version: str
    source_symbol_scope: tuple[str, ...]
    created_from_config_fingerprint: str
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class PathSearchResultV1:
    schema_version: str
    search_result_id: str
    search_policy_id: str
    graph_layer: str
    source_entity_id: str
    candidate_entity_id: str | None
    target_entity_id: str | None
    candidate: str | None
    candidate_scope: str
    requested_source_identifier: str | None
    requested_candidate_identifier: str | None
    source_resolution_status: str
    candidate_resolution_status: str
    generated_path_count: int
    retained_path_count: int
    discarded_path_count: int
    discarded_by_per_candidate_cap_count: int
    discarded_by_global_cap_count: int
    discarded_duplicate_path_count: int
    discarded_by_graph_layer_policy_count: int
    retained_path_ids: tuple[str, ...]
    maximum_depth_reached: int
    truncation_status: str
    termination_reason: str
    truncated: bool
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class ContextDimensionRecordV1:
    dimension: str
    raw_value: str | None
    normalized_value: str | None
    vocabulary: str
    mapping_confidence: float
    missing_status: str
    unresolved_status: str
    source_record_ids: tuple[str, ...]


@dataclass(frozen=True)
class StructuredContextRecordV1:
    context_id: str
    dimensions: dict[str, ContextDimensionRecordV1]
    completeness_fraction: float
    missing_dimensions: tuple[str, ...]
    unresolved_dimensions: tuple[str, ...]


@dataclass(frozen=True)
class ExperimentalContextV1:
    organism: str
    cell_type: str | None
    tissue: str | None
    compartment: str | None
    experimental_system: str | None
    disease_state: str | None


@dataclass(frozen=True)
class ContextComparisonRecordV1:
    comparison_id: str
    evidence_id: str
    dimension: str
    left_context_role: str
    right_context_role: str
    evidence_value: str | None
    experiment_value: str | None
    match_state: str


@dataclass(frozen=True)
class PathContextSummaryV1:
    context_summary_id: str
    shared_known_context: dict[str, str]
    conflicting_context_dimensions: tuple[str, ...]
    missing_context_dimensions: tuple[str, ...]
    unresolved_context_dimensions: tuple[str, ...]
    context_supporting_evidence_ids: tuple[str, ...]
    dimensions: dict[str, dict[str, object]]
    context_completeness_fraction: float


def calculate_evidence_quality_v2(
    evidence: ProviderEdgeEvidenceRecordV2,
) -> EvidenceQualityComponentsV2:
    weights = {
        "directed": 0.15,
        "signed": 0.15,
        "mechanism": 0.15,
        "direct": 0.15,
        "curated": 0.15,
        "publication": 0.1,
        "database": 0.1,
        "mapping": 0.05,
    }
    directed = 1.0 if evidence.directed else 0.0
    signed = 1.0 if evidence.sign in {"positive", "negative"} else 0.0
    mechanism = 1.0 if evidence.mechanism else 0.0
    direct = 1.0 if evidence.directness == "direct" else 0.0
    curated = 1.0 if evidence.curated_status == "curated" else 0.0
    mapping = 0.5 if evidence.identifier_snapshot_id else 0.0
    raw = (
        directed * weights["directed"]
        + signed * weights["signed"]
        + mechanism * weights["mechanism"]
        + direct * weights["direct"]
        + curated * weights["curated"]
        + min(len(evidence.references), 3) / 3 * weights["publication"]
        + (1.0 if evidence.original_database else 0.0) * weights["database"]
        + mapping * weights["mapping"]
    )
    cap = raw
    cap_reasons: list[str] = []
    if evidence.functional_only and evidence.sign == "unsigned":
        cap = min(cap, 0.55)
        cap_reasons.append("unsigned_functional_only_contextual_cap")
    if not evidence.directed or evidence.sign not in {"positive", "negative"}:
        cap = min(cap, 0.45)
        cap_reasons.append("missing_direction_or_sign_low_cap")
    if evidence.predicted_only:
        cap = min(cap, 0.7)
        cap_reasons.append("predicted_only_not_high_cap")
    if evidence.source_entity_type == "unknown" or evidence.target_entity_type == "unknown":
        cap = min(cap, 0.2)
        cap_reasons.append("unsupported_entity_insufficient_cap")
    level = _level_from_score(cap)
    if evidence.sign == "conflicting":
        level = "conflicting"
    return EvidenceQualityComponentsV2(
        directed_support=directed,
        signed_support=signed,
        explicit_mechanism_support=mechanism,
        direct_interaction_support=direct,
        curated_support=curated,
        independent_publication_count=len(set(evidence.references)),
        independent_original_database_count=1 if evidence.original_database else 0,
        identifier_mapping_confidence=mapping,
        organism_match=True,
        cell_type_match=None,
        tissue_match=None,
        compartment_match=None,
        experimental_system_match=None,
        disease_state_match=None,
        predicted_only_penalty=0.3 if evidence.predicted_only else 0.0,
        indirect_relation_penalty=0.2 if evidence.directness != "direct" else 0.0,
        lineage_dependence_penalty=0.0,
        conflict_penalty=0.4 if evidence.sign == "conflicting" else 0.0,
        missing_context_penalty=0.1
        if evidence.cell_type is None and evidence.tissue is None
        else 0.0,
        unsupported_entity_penalty=0.8
        if "unknown" in {evidence.source_entity_type, evidence.target_entity_type}
        else 0.0,
        component_weights=weights,
        missing_components=(),
        raw_score=round(raw, 6),
        capped_score=round(cap, 6),
        cap_reasons=tuple(cap_reasons),
        final_level=level,
        uncertainty=round(1.0 - cap, 6),
        policy_version="evidence-quality-v2",
    )


@dataclass(frozen=True)
class LineageGroupRecordV2:
    lineage_group_id: str
    relationship_class: str
    member_evidence_ids: tuple[str, ...]
    normalized_source_entity_id: str
    normalized_target_entity_id: str
    signs: tuple[str, ...]
    mechanisms: tuple[str, ...]
    original_databases: tuple[str, ...]
    access_providers: tuple[str, ...]
    provider_record_ids: tuple[str, ...]
    publication_ids: tuple[str, ...]
    contexts: tuple[str, ...]
    deduplication_rule: str
    confidence: float
    independent_support_count: int
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class ConsensusMechanisticEdgeRecordV2:
    consensus_edge_id: str
    source_entity_id: str
    target_entity_id: str
    graph_layers: tuple[str, ...]
    positive_signed_support: int
    negative_signed_support: int
    unsigned_functional_support: int
    contextual_support: int
    exact_duplicate_count: int
    likely_duplicate_count: int
    independent_lineage_count: int
    independent_publication_count: int
    original_database_count: int
    access_provider_count: int
    consensus_sign: str
    conflict_status: str
    causal_eligible: bool
    evidence_quality: float
    component_evidence_ids: tuple[str, ...]
    lineage_group_ids: tuple[str, ...]
    context_summary: dict[str, str]
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class PathConfidenceRecordV2:
    path_id: str
    path_type: str
    edge_ids: tuple[str, ...]
    path_length: int
    minimum_edge_quality_score: float
    average_edge_quality_score: float
    bottleneck_edge_id: str
    bottleneck_cap: float
    fully_directed: bool
    fully_signed: bool
    independent_lineage_count: int
    independent_publication_count: int
    minimum_identifier_mapping_confidence: float
    predicted_edge_fraction: float
    indirect_edge_fraction: float
    context_match_fraction: float
    missing_context_fraction: float
    conflicting_edge_count: int
    unsupported_entity_count: int
    truncation_status: str
    component_weights: dict[str, float]
    raw_score: float
    capped_score: float
    confidence_level: str
    uncertainty: float
    policy_version: str
    warnings: tuple[str, ...] = ()


def calculate_path_confidence_v2(
    path_id: str,
    edge_scores: dict[str, float],
    *,
    fully_directed: bool = True,
    fully_signed: bool = True,
) -> PathConfidenceRecordV2:
    if not edge_scores:
        msg = "path confidence requires at least one edge"
        raise ValueError(msg)
    bottleneck_edge_id, minimum = min(edge_scores.items(), key=lambda item: item[1])
    average = sum(edge_scores.values()) / len(edge_scores)
    raw = average
    capped = min(raw, minimum)
    return PathConfidenceRecordV2(
        path_id=path_id,
        path_type="signed_causal" if fully_directed and fully_signed else "contextual",
        edge_ids=tuple(edge_scores),
        path_length=len(edge_scores),
        minimum_edge_quality_score=round(minimum, 6),
        average_edge_quality_score=round(average, 6),
        bottleneck_edge_id=bottleneck_edge_id,
        bottleneck_cap=round(minimum, 6),
        fully_directed=fully_directed,
        fully_signed=fully_signed,
        independent_lineage_count=0,
        independent_publication_count=0,
        minimum_identifier_mapping_confidence=1.0,
        predicted_edge_fraction=0.0,
        indirect_edge_fraction=0.0,
        context_match_fraction=0.0,
        missing_context_fraction=1.0,
        conflicting_edge_count=0,
        unsupported_entity_count=0,
        truncation_status="not_truncated",
        component_weights={"average_edge_quality": 1.0},
        raw_score=round(raw, 6),
        capped_score=round(capped, 6),
        confidence_level=_level_from_score(capped),
        uncertainty=round(1.0 - capped, 6),
        policy_version="path-confidence-v2",
    )


@dataclass(frozen=True)
class ContextualConflictSummaryV1:
    conflict_id: str
    candidate_entity_id: str
    positive_path_ids: tuple[str, ...]
    negative_path_ids: tuple[str, ...]
    positive_contexts: tuple[str, ...]
    negative_contexts: tuple[str, ...]
    context_overlap: bool
    organism_overlap: bool
    cell_type_overlap: bool | None
    tissue_overlap: bool | None
    compartment_overlap: bool | None
    experimental_system_overlap: bool | None
    independent_positive_lineages: int
    independent_negative_lineages: int
    strongest_positive_path: str | None
    strongest_negative_path: str | None
    conflict_class: str
    confidence: float
    unresolved_context_fields: tuple[str, ...]
    warnings: tuple[str, ...] = ()


def classify_contextual_conflict(
    conflict_id: str,
    candidate_entity_id: str,
    positive_path_ids: tuple[str, ...],
    negative_path_ids: tuple[str, ...],
    positive_contexts: tuple[str, ...],
    negative_contexts: tuple[str, ...],
) -> ContextualConflictSummaryV1:
    unresolved: tuple[str, ...]
    if not positive_contexts or not negative_contexts:
        conflict_class = "unresolved_context_conflict"
        overlap = False
        unresolved = ("context",)
    else:
        overlap = bool(set(positive_contexts) & set(negative_contexts))
        conflict_class = "global_sign_conflict" if overlap else "context_specific_conflict"
        unresolved = ()
    return ContextualConflictSummaryV1(
        conflict_id=conflict_id,
        candidate_entity_id=candidate_entity_id,
        positive_path_ids=positive_path_ids,
        negative_path_ids=negative_path_ids,
        positive_contexts=positive_contexts,
        negative_contexts=negative_contexts,
        context_overlap=overlap,
        organism_overlap=True,
        cell_type_overlap=overlap,
        tissue_overlap=None,
        compartment_overlap=None,
        experimental_system_overlap=None,
        independent_positive_lineages=len(positive_path_ids),
        independent_negative_lineages=len(negative_path_ids),
        strongest_positive_path=positive_path_ids[0] if positive_path_ids else None,
        strongest_negative_path=negative_path_ids[0] if negative_path_ids else None,
        conflict_class=conflict_class,
        confidence=0.8 if overlap else 0.5,
        unresolved_context_fields=unresolved,
    )


def _level_from_score(score: float) -> str:
    if score >= 0.8:
        return "high"
    if score >= 0.6:
        return "moderate"
    if score >= 0.4:
        return "low"
    if score >= 0.25:
        return "contextual"
    return "insufficient"
