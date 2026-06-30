from __future__ import annotations

from dataclasses import fields, is_dataclass
from enum import Enum
from types import UnionType
from typing import Any, ClassVar, Union, get_args, get_origin, get_type_hints

from pydantic import BaseModel, Field

from sirna_offtarget.contracts.base import StageContract
from sirna_offtarget.isoform_uncertainty.contracts import IsoformUncertaintyPayloadV1
from sirna_offtarget.models import (
    Direction,
    ExpressionResult,
    GeneSequenceEvidence,
    IsoformResult,
    PathwayResult,
)
from sirna_offtarget.transcript_targetability.contracts import (
    TranscriptTargetabilityResultV1 as TranscriptTargetabilityPayloadV1,
)
from sirna_offtarget.transcript_targetability_ratio.contracts import (
    TranscriptTargetabilityRatioResultV1 as TranscriptTargetabilityRatioPayloadV1,
)

JsonScalar = str | int | float | bool | None
JsonValue = JsonScalar | list[JsonScalar] | dict[str, JsonScalar]


class EvidenceMetricRecordV1(BaseModel):
    value: float | None
    backend: str
    backend_version: str
    calculation_status: str
    is_heuristic: bool
    missing_value_reason: str | None = None


class SequenceBindingSiteRecordV1(BaseModel):
    gene: str
    transcript: str
    strand_source: str
    match_type: str
    seed_class: str
    mismatch_count: int
    mismatch_positions: list[int]
    transcript_start: int
    transcript_end: int
    region: str
    site_sequence: str
    guide_coordinates: list[int]
    target_window_coordinates: list[int]
    genomic_coordinates: list[str | int] | None
    complementarity_score: float
    full_length_complementarity: bool
    central_pairing: bool
    cleavage_compatible: bool
    supplementary_pairing: bool
    gu_wobble_count: int
    accessibility_evidence: EvidenceMetricRecordV1
    opening_energy_evidence: EvidenceMetricRecordV1
    duplex_energy_evidence: EvidenceMetricRecordV1
    provenance: dict[str, str] = Field(default_factory=dict)


class TranscriptSequenceEvidenceRecordV1(BaseModel):
    gene: str
    transcript: str
    binding_sites: list[SequenceBindingSiteRecordV1]


class GeneSequenceEvidenceRecordV1(BaseModel):
    gene: str
    transcripts: list[TranscriptSequenceEvidenceRecordV1]


class ExpressionRecordV1(BaseModel):
    gene: str
    baseline_expression: float | None
    normalized_control_expression: float | None
    normalized_treated_expression: float | None
    log2_fold_change: float
    shrunken_log2_fold_change: float | None
    adjusted_p_value: float | None
    replicate_consistency: float | None
    direction: str
    low_count_flag: bool
    backend_name: str
    backend_version: str
    design_formula: str
    shrinkage_status: str
    standard_error: float | None = None
    raw_p_value: float | None = None
    p_value_status: str
    demonstration_only: bool


class IsoformRecordV1(BaseModel):
    gene: str
    all_transcripts: list[str]
    eligible_transcripts: list[str]
    excluded_transcripts: list[list[str]]
    transcripts_with_site: list[str]
    transcripts_without_site: list[str]
    total_transcript_count: int
    target_site_transcript_count: int
    equal_transcript_prior: float
    inferred_fraction_min: float | None
    inferred_fraction_max: float | None
    warning: str | None


class PathwayEnrichmentRecordV1(BaseModel):
    gene: str
    target_pathway_distance: int | None
    direction_consistency: bool | None
    pathway_coherence: float
    regulon_evidence: float
    stress_signature_evidence: float
    paths: list[str] = Field(default_factory=list)
    shortest_signed_path: list[str] = Field(default_factory=list)
    shortest_unsigned_supported_path: list[str] = Field(default_factory=list)
    composed_path_sign: int | None = None
    expected_candidate_direction: str | None = None
    conflicting_paths: bool = False
    supporting_path_count: int = 0
    contradictory_path_count: int = 0
    provider_sources: list[str] = Field(default_factory=list)
    evidence_limitations: list[str] = Field(default_factory=list)


class MechanisticEdgeRecordV1(BaseModel):
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
    original_sources: list[str]
    references: list[str]
    organism: str
    evidence_level: str
    signed_support_count: int
    unsigned_support_count: int
    source_count: int
    reference_count: int
    predicted_only: bool
    conflict: bool
    database_versions: list[str]
    retrieval_snapshots: list[str]
    lineage_key: str
    warnings: list[str] = Field(default_factory=list)


class ProviderEdgeEvidenceRecordV1(MechanisticEdgeRecordV1):
    evidence_id: str | None = None
    access_route: str | None = None
    functional_only: bool = False
    causal_eligible: bool = True
    provider_record_id: str | None = None


class ConsensusMechanisticEdgeRecordV1(BaseModel):
    edge_id: str
    source: str
    target: str
    directed: bool
    consensus_sign: str
    relation_type: str
    mechanism: str
    provider_sources: list[str]
    references: list[str]
    evidence_ids: list[str]
    lineage_groups: list[str]
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
    database_versions: list[str]
    retrieval_snapshots: list[str]
    warnings: list[str] = Field(default_factory=list)


class MechanisticPathRecordV1(BaseModel):
    path_id: str
    intended_target: str
    candidate: str
    ordered_nodes: list[str]
    ordered_edge_ids: list[str]
    path_length: int
    directed: bool
    fully_signed: bool
    composed_sign: str | None
    expected_candidate_direction_after_target_decrease: str | None
    observed_candidate_direction: str
    direction_consistent: bool | None
    provider_sources: list[str]
    references: list[str]
    evidence_score: float
    conflicting_with_other_paths: bool
    unsigned_edge_count: int
    conflicting_edge_count: int = 0
    positive_composed_path_count: int = 0
    negative_composed_path_count: int = 0
    warnings: list[str] = Field(default_factory=list)


class LegacyMechanisticPathRecordV1(BaseModel):
    gene: str
    path_nodes: list[str]
    path_direction: str | None = None
    path_confidence: float | None = None
    signed: bool = False


class ValidationPayload(BaseModel):
    yaml_schema_version: str
    missing_files: list[str]
    dag_stage_count: int


class PreparedInputsPayload(BaseModel):
    inputs: list[dict[str, JsonValue]]


class IdentifierMappingPayload(BaseModel):
    mapped_count: int
    unmapped_count: int
    ambiguous_count: int
    genes: list[str]


class SequenceAnalysisPayload(BaseModel):
    sequence_hits: dict[str, GeneSequenceEvidenceRecordV1]
    total_sites: int
    transcript_count: int


class ExpressionAnalysisPayload(BaseModel):
    expression_results: dict[str, ExpressionRecordV1]
    tested_genes: int
    sample_count: int


class ExpressionAnalysisPayloadV2(BaseModel):
    canonical: bool = True
    normalization_run_artifact: str
    contrasts_artifact: str
    normalized_gene_effects_artifact: str
    identifier_resolutions_artifact: str
    input_validation_artifact: str
    filtering_summary_artifact: str
    warnings_artifact: str
    execution_support_artifact: str
    downstream_compatibility_artifact: str | None = None
    artifact_checksums: dict[str, str] = Field(default_factory=dict)
    record_counts: dict[str, int] = Field(default_factory=dict)
    compatibility_metadata: dict[str, Any] = Field(default_factory=dict)


class IsoformAnalysisPayload(BaseModel):
    isoform_results: dict[str, IsoformRecordV1]
    gene_count: int


class PathwayEnrichmentPayload(BaseModel):
    deprecated_compatibility_payload: bool = True
    pathway_results: dict[str, PathwayEnrichmentRecordV1]
    pathway_gene_count: int
    provider_results: list[dict[str, Any]] = Field(default_factory=list)
    locally_calculated_results: list[dict[str, Any]] = Field(default_factory=list)
    consensus_results: list[dict[str, Any]] = Field(default_factory=list)
    regulon_context_results: list[dict[str, Any]] = Field(default_factory=list)
    gene_sets: dict[str, list[str]] = Field(default_factory=dict)
    gene_set_definitions: list[dict[str, Any]] = Field(default_factory=list)
    background_universe: list[str] = Field(default_factory=list)
    background_manifest: dict[str, Any] = Field(default_factory=dict)
    annotation_memberships: list[dict[str, Any]] = Field(default_factory=list)
    annotation_membership_summary: dict[str, Any] = Field(default_factory=dict)
    identifier_mapping_summary: dict[str, Any] = Field(default_factory=dict)
    provider_snapshot_manifest: dict[str, Any] = Field(default_factory=dict)
    annotation_lineage: list[dict[str, Any]] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    pathway_enrichment_v2: dict[str, Any] = Field(default_factory=dict)


class PathwayEnrichmentPayloadV2(BaseModel):
    gene_sets: dict[str, list[str]] = Field(default_factory=dict)
    background_universe: list[str] = Field(default_factory=list)
    provider_calculated_enrichment: list[dict[str, Any]] = Field(default_factory=list)
    locally_calculated_enrichment: list[dict[str, Any]] = Field(default_factory=list)
    enrichment_consensus: list[dict[str, Any]] = Field(default_factory=list)
    annotation_membership_summary: dict[str, Any] = Field(default_factory=dict)
    identifier_mapping_summary: dict[str, Any] = Field(default_factory=dict)
    provider_snapshot_manifest: dict[str, Any] = Field(default_factory=dict)
    annotation_snapshot_manifest: dict[str, Any] = Field(default_factory=dict)
    regulon_context: list[dict[str, Any]] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class MechanisticNetworkPayload(BaseModel):
    pathway_results: dict[str, PathwayEnrichmentRecordV1]
    edges: list[MechanisticEdgeRecordV1] = Field(default_factory=list)
    paths: list[MechanisticPathRecordV1] = Field(default_factory=list)
    provider_evidence_edges: list[dict[str, Any]] = Field(default_factory=list)
    consensus_edges: list[ConsensusMechanisticEdgeRecordV1] = Field(default_factory=list)
    conflicting_path_summaries: list[dict[str, Any]] = Field(default_factory=list)
    unsigned_context_paths: list[MechanisticPathRecordV1] = Field(default_factory=list)
    pathway_relations: list[dict[str, Any]] = Field(default_factory=list)
    reaction_participation: list[dict[str, Any]] = Field(default_factory=list)
    identifier_mapping_summary: dict[str, Any] = Field(default_factory=dict)
    provider_snapshot_manifest: dict[str, Any] = Field(default_factory=dict)
    supported_relation_count: int


class MechanisticNetworkPayloadV2(BaseModel):
    biological_entities: list[dict[str, Any]] = Field(default_factory=list)
    identifier_resolution_records: list[dict[str, Any]] = Field(default_factory=list)
    provider_evidence: list[dict[str, Any]] = Field(default_factory=list)
    evidence_quality: list[dict[str, Any]] = Field(default_factory=list)
    lineage_groups: list[dict[str, Any]] = Field(default_factory=list)
    consensus_edges: list[dict[str, Any]] = Field(default_factory=list)
    graph_layer_summary: dict[str, Any] = Field(default_factory=dict)
    path_search_policy: dict[str, Any] = Field(default_factory=dict)
    path_search_results: list[dict[str, Any]] = Field(default_factory=list)
    signed_paths: list[dict[str, Any]] = Field(default_factory=list)
    unsigned_context_paths: list[dict[str, Any]] = Field(default_factory=list)
    path_confidence_records: list[dict[str, Any]] = Field(default_factory=list)
    contextual_conflicts: list[dict[str, Any]] = Field(default_factory=list)
    structured_contexts: list[dict[str, Any]] = Field(default_factory=list)
    evidence_context_comparisons: list[dict[str, Any]] = Field(default_factory=list)
    unsupported_entities: list[dict[str, Any]] = Field(default_factory=list)
    provider_snapshot_manifest: dict[str, Any] = Field(default_factory=dict)
    identifier_snapshot_manifest: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    metrics: dict[str, Any] = Field(default_factory=dict)
    coverage_summary: dict[str, Any] = Field(default_factory=dict)
    migration_diagnostics: dict[str, Any] = Field(default_factory=dict)
    scientific_policy_manifest: dict[str, Any] = Field(default_factory=dict)


class ValidationResultV1(StageContract):
    expected_contract_name: ClassVar[str] = "ValidationResultV1"
    payload: ValidationPayload


class PreparedInputsResultV1(StageContract):
    expected_contract_name: ClassVar[str] = "PreparedInputsResultV1"
    payload: PreparedInputsPayload


class IdentifierMappingResultV1(StageContract):
    expected_contract_name: ClassVar[str] = "IdentifierMappingResultV1"
    payload: IdentifierMappingPayload


class SequenceAnalysisResultV1(StageContract):
    expected_contract_name: ClassVar[str] = "SequenceAnalysisResultV1"
    payload: SequenceAnalysisPayload


class ExpressionAnalysisResultV1(StageContract):
    expected_contract_name: ClassVar[str] = "ExpressionAnalysisResultV1"
    payload: ExpressionAnalysisPayload


class ExpressionAnalysisResultV2(StageContract):
    expected_contract_name: ClassVar[str] = "ExpressionAnalysisResultV2"
    expected_schema_version: ClassVar[str] = "2"
    payload: ExpressionAnalysisPayloadV2


class IsoformAnalysisResultV1(StageContract):
    expected_contract_name: ClassVar[str] = "IsoformAnalysisResultV1"
    payload: IsoformAnalysisPayload


class IsoformUncertaintyResultV1(StageContract):
    expected_contract_name: ClassVar[str] = "IsoformUncertaintyResultV1"
    payload: IsoformUncertaintyPayloadV1


class TranscriptTargetabilityResultV1(StageContract):
    expected_contract_name: ClassVar[str] = "TranscriptTargetabilityResultV1"
    payload: TranscriptTargetabilityPayloadV1


class TranscriptTargetabilityRatioResultV1(StageContract):
    expected_contract_name: ClassVar[str] = "TranscriptTargetabilityRatioResultV1"
    payload: TranscriptTargetabilityRatioPayloadV1


class PathwayEnrichmentResultV1(StageContract):
    expected_contract_name: ClassVar[str] = "PathwayEnrichmentResultV1"
    payload: PathwayEnrichmentPayload


class PathwayEnrichmentResultV2(StageContract):
    expected_contract_name: ClassVar[str] = "PathwayEnrichmentResultV2"
    expected_schema_version: ClassVar[str] = "2"
    payload: PathwayEnrichmentPayloadV2


class MechanisticNetworkResultV1(StageContract):
    expected_contract_name: ClassVar[str] = "MechanisticNetworkResultV1"
    payload: MechanisticNetworkPayload


class MechanisticNetworkResultV2(StageContract):
    expected_contract_name: ClassVar[str] = "MechanisticNetworkResultV2"
    expected_schema_version: ClassVar[str] = "2"
    payload: MechanisticNetworkPayloadV2


def _coerce_value(annotation: Any, value: Any) -> Any:
    if value is None:
        return None
    origin = get_origin(annotation)
    args = get_args(annotation)
    if origin in {tuple, list}:
        item_type = args[0] if args else Any
        return tuple(_coerce_value(item_type, item) for item in value)
    if origin is dict:
        return dict(value)
    if origin in {Union, UnionType}:
        non_none = [arg for arg in args if arg is not type(None)]
        return _coerce_value(non_none[0], value) if non_none else None
    if isinstance(annotation, type) and issubclass(annotation, Enum):
        return annotation(value)
    if isinstance(annotation, type) and is_dataclass(annotation):
        return _dataclass_from_dict(annotation, value)
    return value


def _dataclass_from_dict(cls: type[Any], data: dict[str, Any] | BaseModel) -> Any:
    if isinstance(data, BaseModel):
        data = data.model_dump(mode="json")
    values = {}
    hints = get_type_hints(cls)
    for item in fields(cls):
        if item.name in data:
            values[item.name] = _coerce_value(hints[item.name], data[item.name])
    return cls(**values)


def expression_results_from_contract(
    contract: ExpressionAnalysisResultV1,
) -> dict[str, ExpressionResult]:
    return {
        gene: _dataclass_from_dict(ExpressionResult, data)
        for gene, data in contract.payload.expression_results.items()
    }


def sequence_results_from_contract(
    contract: SequenceAnalysisResultV1,
) -> dict[str, GeneSequenceEvidence]:
    return {
        gene: _dataclass_from_dict(GeneSequenceEvidence, data)
        for gene, data in contract.payload.sequence_hits.items()
    }


def isoform_results_from_contract(contract: IsoformAnalysisResultV1) -> dict[str, IsoformResult]:
    return {
        gene: _dataclass_from_dict(IsoformResult, data)
        for gene, data in contract.payload.isoform_results.items()
    }


def pathway_results_from_contract(
    contract: PathwayEnrichmentResultV1 | MechanisticNetworkResultV1 | MechanisticNetworkResultV2,
) -> dict[str, PathwayResult]:
    if isinstance(contract, MechanisticNetworkResultV2):
        return _pathway_results_from_mechanistic_v2(contract)
    return {
        gene: _dataclass_from_dict(PathwayResult, data)
        for gene, data in contract.payload.pathway_results.items()
    }


def _pathway_results_from_mechanistic_v2(
    contract: MechanisticNetworkResultV2,
) -> dict[str, PathwayResult]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for path in [*contract.payload.signed_paths, *contract.payload.unsigned_context_paths]:
        candidate = str(path.get("candidate", ""))
        if candidate:
            grouped.setdefault(candidate, []).append(path)
    results: dict[str, PathwayResult] = {}
    for gene, paths in grouped.items():
        best = sorted(paths, key=lambda row: int(row.get("path_length", 999999)))[0]
        expected = best.get("expected_candidate_direction_after_target_decrease")
        expected_direction = Direction(expected) if expected else None
        results[gene] = PathwayResult(
            gene=gene,
            target_pathway_distance=int(best.get("path_length", 0)),
            direction_consistency=best.get("direction_consistent"),
            pathway_coherence=1.0 / max(int(best.get("path_length", 1)), 1),
            regulon_evidence=0.0,
            stress_signature_evidence=0.0,
            paths=tuple(best.get("ordered_nodes", ()) or ()),
            shortest_signed_path=tuple(best.get("ordered_nodes", ()) or ())
            if best.get("fully_signed")
            else (),
            shortest_unsigned_supported_path=tuple(best.get("ordered_nodes", ()) or ()),
            composed_path_sign=1
            if best.get("composed_sign") == "positive"
            else -1
            if best.get("composed_sign") == "negative"
            else None,
            expected_candidate_direction=expected_direction,
            conflicting_paths=any(path.get("conflicting_with_other_paths") for path in paths),
            supporting_path_count=sum(
                1 for path in paths if path.get("direction_consistent") is True
            ),
            contradictory_path_count=sum(
                1 for path in paths if path.get("direction_consistent") is False
            ),
            provider_sources=tuple(
                sorted({source for path in paths for source in path.get("provider_sources", [])})
            ),
            evidence_limitations=tuple(
                sorted({warning for path in paths for warning in path.get("warnings", [])})
            ),
        )
    return results
