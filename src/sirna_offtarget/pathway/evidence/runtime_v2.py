from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict, replace
from hashlib import sha1
from typing import Any, cast

import networkx as nx

from sirna_offtarget.identifiers.resolver_v2 import (
    IdentifierResolutionRecordV2,
    IdentifierResolverV2,
)
from sirna_offtarget.pathway.entities import BiologicalEntityRegistryV2
from sirna_offtarget.pathway.semantics import (
    ConsensusMechanisticEdgeRecordV2,
    ContextComparisonRecordV1,
    ContextDimensionRecordV1,
    EvidenceQualityComponentsV2,
    ExperimentalContextV1,
    LineageGroupRecordV2,
    PathConfidenceRecordV2,
    PathContextSummaryV1,
    PathSearchPolicyV1,
    PathSearchResultV1,
    ProviderEdgeEvidenceRecordV2,
    StructuredContextRecordV1,
    classify_contextual_conflict,
)


def build_mechanistic_network_payload_v2(
    *,
    raw_provider_evidence_rows: list[dict[str, Any]],
    legacy_trace_edges: list[dict[str, Any]],
    legacy_trace_paths: list[dict[str, Any]],
    provider_snapshot_manifest: dict[str, Any],
    organism: str,
    identifier_resolver: IdentifierResolverV2,
    identifier_snapshot_manifest: dict[str, Any] | None = None,
    path_search_source_symbols: list[str] | None = None,
    candidate_entity_ids: tuple[str, ...] | list[str] | None = None,
    observed_directions_by_symbol: dict[str, str] | None = None,
    max_path_length: int = 4,
    maximum_paths_per_candidate: int = 25,
    maximum_total_paths: int | None = None,
    shortest_paths_only: bool = False,
    trace_signed_paths: bool = True,
    trace_unsigned_paths: bool = True,
    trace_contextual_paths: bool = True,
    created_from_config_fingerprint: str = "",
    experiment_context: dict[str, Any] | None = None,
    migration_diagnostics_enabled: bool = False,
    warnings: list[str] | None = None,
) -> dict[str, Any]:
    snapshot = identifier_snapshot_manifest or _resolver_snapshot_manifest(identifier_resolver)
    snapshot_id = str(snapshot["snapshot_id"])
    registry = BiologicalEntityRegistryV2(organism, snapshot_id)
    resolutions: dict[str, IdentifierResolutionRecordV2] = {}
    if not raw_provider_evidence_rows:
        msg = "missing_canonical_provider_evidence: V2 runtime requires raw provider evidence"
        raise RuntimeError(msg)
    evidence_rows = raw_provider_evidence_rows
    experiment = _experimental_context_from_dict(experiment_context, organism=organism)
    evidence = [
        build_provider_edge_evidence_v2(
            row,
            registry=registry,
            resolutions=resolutions,
            organism=organism,
            identifier_resolver=identifier_resolver,
            identifier_snapshot_id=snapshot_id,
            provider_snapshot_id=_provider_snapshot_id(row, provider_snapshot_manifest),
        )
        for row in evidence_rows
    ]
    lineage_groups = build_lineage_groups_v2(evidence)
    quality_by_evidence_id = {
        item.evidence_id: calculate_runtime_evidence_quality_v2(
            item,
            lineage_groups=[
                group for group in lineage_groups if item.evidence_id in group.member_evidence_ids
            ],
            source_resolution=resolutions.get(item.source_entity_id),
            target_resolution=resolutions.get(item.target_entity_id),
            experiment_organism=organism,
            experiment_context=experiment,
        )
        for item in evidence
    }
    consensus_edges = build_consensus_edges_v2(evidence, lineage_groups, quality_by_evidence_id)
    graphs = build_graph_layers_v2(
        provider_evidence=evidence,
        consensus_edges=consensus_edges,
        lineage_groups=lineage_groups,
        quality_by_evidence_id=quality_by_evidence_id,
        resolutions=resolutions,
    )
    path_policy = PathSearchPolicyV1(
        schema_version="1",
        policy_id="v2-graph-path-search-1",
        max_path_length=max_path_length,
        maximum_paths_per_candidate=maximum_paths_per_candidate,
        maximum_total_paths=maximum_total_paths,
        shortest_paths_only=shortest_paths_only,
        trace_signed_paths=trace_signed_paths,
        trace_unsigned_paths=trace_unsigned_paths,
        trace_contextual_paths=trace_contextual_paths,
        include_conflicting_edges=False,
        deterministic_path_order=(
            "path_length",
            "ordered_entity_ids",
            "ordered_consensus_edge_ids",
            "path_id",
        ),
        source_selection_policy_version="requested-source-or-explicit-exploratory-v1",
        candidate_selection_policy_version="explicit-candidate-scope-or-all-reachable-v1",
        source_symbol_scope=tuple(path_search_source_symbols or ()),
        created_from_config_fingerprint=created_from_config_fingerprint,
    )
    signed_paths, unsigned_context_paths, path_search_results = trace_v2_graph_paths(
        graphs=graphs,
        consensus_edges=consensus_edges,
        provider_evidence=evidence,
        resolutions=resolutions,
        policy=path_policy,
        source_symbols=path_search_source_symbols,
        candidate_entity_ids=tuple(candidate_entity_ids) if candidate_entity_ids else None,
        observed_directions_by_symbol=observed_directions_by_symbol or {},
    )
    _validate_path_search_linkage([*signed_paths, *unsigned_context_paths], path_search_results)
    confidence_records = build_path_confidence_records_v2(
        paths=[*signed_paths, *unsigned_context_paths],
        consensus_edges=consensus_edges,
        quality_by_evidence_id=quality_by_evidence_id,
        provider_evidence=evidence,
        lineage_groups=lineage_groups,
        resolutions=resolutions,
    )
    contextual_conflicts = build_contextual_conflicts_v2(
        paths=[*signed_paths, *unsigned_context_paths],
        confidence_records=confidence_records,
        consensus_edges=consensus_edges,
        provider_evidence=evidence,
    )
    structured_contexts = [_structured_context_record(item) for item in evidence]
    context_comparisons = _evidence_context_comparisons(evidence, experiment)
    coverage_summary = {
        "biological_entity_count": len(registry.to_rows()),
        "provider_evidence_count": len(evidence),
        "lineage_group_count": len(lineage_groups),
        "consensus_edge_count": len(consensus_edges),
        "signed_path_count": len(signed_paths),
        "unsigned_context_path_count": len(unsigned_context_paths),
        "placeholder_records_removed": True,
    }
    metrics = build_mechanistic_runtime_metrics_v2(
        provider_evidence=evidence,
        lineage_groups=lineage_groups,
        consensus_edges=consensus_edges,
        signed_paths=signed_paths,
        unsigned_context_paths=unsigned_context_paths,
        path_search_results=path_search_results,
        contextual_conflicts=contextual_conflicts,
        graphs=graphs,
    )
    return {
        "biological_entities": registry.to_rows(),
        "identifier_resolution_records": [asdict(record) for record in resolutions.values()],
        "provider_evidence": [asdict(item) for item in evidence],
        "evidence_quality": [asdict(item) for item in quality_by_evidence_id.values()],
        "lineage_groups": [asdict(item) for item in lineage_groups],
        "consensus_edges": [_consensus_render_row(item) for item in consensus_edges],
        "graph_layer_summary": {name: graph.number_of_edges() for name, graph in graphs.items()},
        "path_search_policy": asdict(path_policy),
        "path_search_results": [asdict(item) for item in path_search_results],
        "signed_paths": signed_paths,
        "unsigned_context_paths": unsigned_context_paths,
        "path_confidence_records": [asdict(item) for item in confidence_records],
        "contextual_conflicts": [asdict(item) for item in contextual_conflicts],
        "structured_contexts": [asdict(item) for item in structured_contexts],
        "evidence_context_comparisons": [asdict(item) for item in context_comparisons],
        "unsupported_entities": registry.unsupported_rows(),
        "provider_snapshot_manifest": provider_snapshot_manifest,
        "identifier_snapshot_manifest": snapshot,
        "warnings": warnings or [],
        "metrics": metrics,
        "migration_diagnostics": {
            "enabled": migration_diagnostics_enabled,
            "provider_evidence_input": "raw_provider_evidence",
            "raw_provider_evidence_count": len(raw_provider_evidence_rows),
            "legacy_trace_edge_count": len(legacy_trace_edges)
            if migration_diagnostics_enabled
            else 0,
            "legacy_trace_paths_available": bool(legacy_trace_paths)
            if migration_diagnostics_enabled
            else False,
            "legacy_trace_paths_used_for_candidate_filtering": False,
            "legacy_paths_canonical": False,
            "canonical_path_source": "v2_semantic_graphs",
        },
        "coverage_summary": coverage_summary,
        "scientific_policy_manifest": {
            "mechanistic_contract_policy": "runtime-semantic-v2",
            "evidence_quality_policy": "runtime-evidence-quality-v2",
            "path_confidence_policy": "runtime-path-confidence-v2",
        },
    }


def build_provider_edge_evidence_v2(
    row: dict[str, Any],
    *,
    registry: BiologicalEntityRegistryV2,
    resolutions: dict[str, IdentifierResolutionRecordV2],
    organism: str,
    identifier_resolver: IdentifierResolverV2,
    identifier_snapshot_id: str,
    provider_snapshot_id: str,
) -> ProviderEdgeEvidenceRecordV2:
    provider = str(row.get("provider") or "local_snapshot")
    provider_record_id = str(row.get("provider_record_id") or row.get("edge_id") or "")
    source_entity_type = _entity_type(row, "source")
    target_entity_type = _entity_type(row, "target")
    source_resolution = identifier_resolver.resolve_provider_entity(
        provider, _source_identifier(row), source_entity_type
    )
    target_resolution = identifier_resolver.resolve_provider_entity(
        provider, _target_identifier(row), target_entity_type
    )
    source_entity = registry.register_from_resolution(
        source_resolution,
        provider=provider,
        provider_record_id=provider_record_id,
        raw_entity_type=source_entity_type,
    )
    target_entity = registry.register_from_resolution(
        target_resolution,
        provider=provider,
        provider_record_id=provider_record_id,
        raw_entity_type=target_entity_type,
    )
    resolutions[source_entity.entity_id] = source_resolution
    resolutions[target_entity.entity_id] = target_resolution
    sign = str(row.get("sign") or "unknown")
    functional_only = bool(row.get("functional_only")) or sign in {"unsigned", "unknown"}
    contextual_only = bool(row.get("contextual_only")) or str(row.get("relation_type") or "") in {
        "pathway_co_membership",
        "reaction_participation",
        "catalyst",
        "complex_membership",
        "entity_set_membership",
        "compartment_association",
    }
    return ProviderEdgeEvidenceRecordV2(
        evidence_id=str(row.get("evidence_id") or row.get("edge_id") or provider_record_id),
        source_entity_id=source_entity.entity_id,
        target_entity_id=target_entity.entity_id,
        source_resolution_id=source_resolution.resolution_id,
        target_resolution_id=target_resolution.resolution_id,
        source_entity_type=source_entity.entity_type,
        target_entity_type=target_entity.entity_type,
        directed=bool(row.get("directed", True)),
        sign=sign,
        relation_type=str(row.get("relation_type") or "regulates"),
        mechanism=str(row.get("mechanism") or ""),
        directness="predicted_or_indirect" if row.get("predicted_only") else "direct",
        functional_only=functional_only,
        contextual_only=contextual_only,
        causal_eligible=bool(row.get("causal_eligible", not functional_only)),
        original_provider=str(row.get("original_provider") or provider),
        access_provider=str(row.get("access_route") or row.get("access_provider") or provider),
        original_database=str(
            row.get("original_database")
            or _first_tuple_value(row.get("original_sources"))
            or row.get("lineage_key")
            or provider
        ),
        provider_record_id=provider_record_id,
        references=tuple(str(item) for item in row.get("references", ()) or ()),
        organism=str(row.get("organism") or organism),
        cell_type=_optional_str(row.get("cell_type")),
        tissue=_optional_str(row.get("tissue")),
        compartment=_optional_str(row.get("compartment")),
        experimental_system=_optional_str(row.get("experimental_system")),
        disease_state=_optional_str(row.get("disease_state")),
        predicted_only=bool(row.get("predicted_only", False)),
        curated_status="predicted" if row.get("predicted_only") else "curated",
        identifier_snapshot_id=identifier_snapshot_id,
        provider_snapshot_id=provider_snapshot_id,
        provider_version=str(row.get("database_version") or "")
        or ";".join(str(item) for item in row.get("database_versions", ()) or ()),
        normalization_version="provider-edge-evidence-v2-runtime",
        warnings=tuple(str(item) for item in row.get("warnings", ()) or ()),
    )


def build_lineage_groups_v2(
    provider_evidence: list[ProviderEdgeEvidenceRecordV2],
) -> list[LineageGroupRecordV2]:
    broad_clusters: dict[tuple[str, str, bool, str, str], list[ProviderEdgeEvidenceRecordV2]] = (
        defaultdict(list)
    )
    for evidence in provider_evidence:
        broad_key = (
            evidence.source_entity_id,
            evidence.target_entity_id,
            evidence.directed,
            _broad_relation_class(evidence),
            evidence.organism,
        )
        broad_clusters[broad_key].append(evidence)
    lineages: list[LineageGroupRecordV2] = []
    index = 1
    for cluster_items in broad_clusters.values():
        grouped: dict[tuple[str, str, str, str, str], list[ProviderEdgeEvidenceRecordV2]] = (
            defaultdict(list)
        )
        for evidence in cluster_items:
            redistributed_key = (
                evidence.original_database,
                evidence.provider_record_id,
                ";".join(sorted(evidence.references)),
                evidence.sign,
                evidence.relation_type,
            )
            if evidence.provider_record_id or evidence.references:
                grouped[redistributed_key].append(evidence)
            else:
                unresolved_key = (
                    evidence.evidence_id,
                    "",
                    "",
                    evidence.sign,
                    evidence.relation_type,
                )
                grouped[unresolved_key].append(evidence)
        grouped_values = list(grouped.values())
        for items in grouped_values:
            publications = tuple(sorted({ref for item in items for ref in item.references}))
            original_databases = tuple(sorted({item.original_database for item in items}))
            providers = tuple(sorted({item.access_provider for item in items}))
            relationship_class = _lineage_relationship_class(items, cluster_items)
            lineages.append(
                LineageGroupRecordV2(
                    lineage_group_id=f"lineage:{index:05d}",
                    relationship_class=relationship_class,
                    member_evidence_ids=tuple(item.evidence_id for item in items),
                    normalized_source_entity_id=items[0].source_entity_id,
                    normalized_target_entity_id=items[0].target_entity_id,
                    signs=tuple(sorted({item.sign for item in items})),
                    mechanisms=tuple(sorted({item.mechanism for item in items if item.mechanism})),
                    original_databases=original_databases,
                    access_providers=providers,
                    provider_record_ids=tuple(sorted({item.provider_record_id for item in items})),
                    publication_ids=publications,
                    contexts=tuple(
                        sorted({_context_label(_structured_context(item)) for item in items})
                    ),
                    deduplication_rule=(
                        "broad_biological_cluster_then_origin_publication_record_analysis"
                    ),
                    confidence=_lineage_confidence(relationship_class),
                    independent_support_count=1
                    if relationship_class in {"independent_same_edge", "independent_opposing_edge"}
                    else 0,
                    warnings=(),
                )
            )
            index += 1
    return lineages


def calculate_runtime_evidence_quality_v2(
    evidence: ProviderEdgeEvidenceRecordV2,
    *,
    lineage_groups: list[LineageGroupRecordV2],
    source_resolution: IdentifierResolutionRecordV2 | None,
    target_resolution: IdentifierResolutionRecordV2 | None,
    experiment_organism: str,
    experiment_context: ExperimentalContextV1 | None = None,
) -> EvidenceQualityComponentsV2:
    weights = {
        "directed": 0.12,
        "signed": 0.14,
        "mechanism": 0.11,
        "direct": 0.12,
        "curated": 0.12,
        "publication": 0.14,
        "database": 0.1,
        "mapping": 0.15,
    }
    mapping_confidence = min(
        source_resolution.mapping_confidence if source_resolution else 0.0,
        target_resolution.mapping_confidence if target_resolution else 0.0,
    )
    publication_count = len({ref for group in lineage_groups for ref in group.publication_ids})
    database_count = len({db for group in lineage_groups for db in group.original_databases})
    missing = []
    if evidence.cell_type is None:
        missing.append("cell_type")
    if evidence.tissue is None:
        missing.append("tissue")
    if evidence.compartment is None:
        missing.append("compartment")
    if not evidence.references:
        missing.append("publication_ids")
    context_match = _context_match_states(evidence, experiment_context)
    directed = 1.0 if evidence.directed else 0.0
    signed = 1.0 if evidence.sign in {"positive", "negative"} else 0.0
    mechanism = 1.0 if evidence.mechanism else 0.0
    direct = 1.0 if evidence.directness == "direct" else 0.0
    curated = 1.0 if evidence.curated_status == "curated" else 0.0
    raw = (
        directed * weights["directed"]
        + signed * weights["signed"]
        + mechanism * weights["mechanism"]
        + direct * weights["direct"]
        + curated * weights["curated"]
        + min(publication_count, 3) / 3 * weights["publication"]
        + min(database_count, 2) / 2 * weights["database"]
        + mapping_confidence * weights["mapping"]
    )
    cap = raw
    cap_reasons = []
    if evidence.functional_only:
        cap = min(cap, 0.55)
        cap_reasons.append("functional_only_contextual_cap")
    if not evidence.directed or evidence.sign not in {"positive", "negative"}:
        cap = min(cap, 0.45)
        cap_reasons.append("missing_direction_or_sign_low_cap")
    if evidence.predicted_only:
        cap = min(cap, 0.7)
        cap_reasons.append("predicted_only_not_high_cap")
    if mapping_confidence < 0.5:
        cap = min(cap, 0.35)
        cap_reasons.append("low_mapping_confidence_cap")
    if "unknown" in {evidence.source_entity_type, evidence.target_entity_type}:
        cap = min(cap, 0.2)
        cap_reasons.append("unsupported_entity_insufficient_cap")
    return EvidenceQualityComponentsV2(
        directed_support=directed,
        signed_support=signed,
        explicit_mechanism_support=mechanism,
        direct_interaction_support=direct,
        curated_support=curated,
        independent_publication_count=publication_count,
        independent_original_database_count=database_count,
        identifier_mapping_confidence=mapping_confidence,
        organism_match=evidence.organism == experiment_organism,
        cell_type_match=context_match["cell_type"],
        tissue_match=context_match["tissue"],
        compartment_match=context_match["compartment"],
        experimental_system_match=context_match["experimental_system"],
        disease_state_match=context_match["disease_state"],
        predicted_only_penalty=0.3 if evidence.predicted_only else 0.0,
        indirect_relation_penalty=0.2 if evidence.directness != "direct" else 0.0,
        lineage_dependence_penalty=0.25
        if any(group.relationship_class == "exact_duplicate" for group in lineage_groups)
        else 0.0,
        conflict_penalty=0.4 if evidence.sign == "conflicting" else 0.0,
        missing_context_penalty=0.1 if missing else 0.0,
        unsupported_entity_penalty=0.8
        if "unknown" in {evidence.source_entity_type, evidence.target_entity_type}
        else 0.0,
        component_weights=weights,
        missing_components=tuple(missing),
        raw_score=round(raw, 6),
        capped_score=round(cap, 6),
        cap_reasons=tuple(cap_reasons),
        final_level=_level_from_score(cap),
        uncertainty=round(1.0 - cap, 6),
        policy_version="runtime-evidence-quality-v2",
    )


def build_consensus_edges_v2(
    provider_evidence: list[ProviderEdgeEvidenceRecordV2],
    lineage_groups: list[LineageGroupRecordV2],
    quality_by_evidence_id: dict[str, EvidenceQualityComponentsV2],
) -> list[ConsensusMechanisticEdgeRecordV2]:
    grouped: dict[tuple[str, str, str], list[ProviderEdgeEvidenceRecordV2]] = defaultdict(list)
    for evidence in provider_evidence:
        semantic_relation = "functional" if evidence.functional_only else evidence.relation_type
        grouped[(evidence.source_entity_id, evidence.target_entity_id, semantic_relation)].append(
            evidence
        )
    lineage_by_evidence = {
        evidence_id: lineage
        for lineage in lineage_groups
        for evidence_id in lineage.member_evidence_ids
    }
    consensus: list[ConsensusMechanisticEdgeRecordV2] = []
    for index, ((source, target, _relation), items) in enumerate(grouped.items(), start=1):
        lineages = tuple({lineage_by_evidence[item.evidence_id] for item in items})
        lineage_by_id = {lineage.lineage_group_id: lineage for lineage in lineages}
        independent_lineages = tuple(
            lineage
            for lineage in lineage_by_id.values()
            if lineage.relationship_class in {"independent_same_edge", "independent_opposing_edge"}
        )
        duplicate_lineages = tuple(
            lineage
            for lineage in lineage_by_id.values()
            if lineage.relationship_class
            in {"exact_duplicate", "publication_duplicate", "likely_duplicate"}
        )
        qualities = [quality_by_evidence_id[item.evidence_id].capped_score for item in items]
        lineage_ids = tuple(
            sorted({lineage_by_evidence[item.evidence_id].lineage_group_id for item in items})
        )
        publications = {ref for lineage in independent_lineages for ref in lineage.publication_ids}
        original_dbs = {db for lineage in independent_lineages for db in lineage.original_databases}
        access_providers = {
            provider
            for lineage in tuple(lineage_by_id.values())
            for provider in lineage.access_providers
        }
        sign_lineages = tuple(lineage_by_id.values())
        positive = sum(1 for lineage in independent_lineages if "positive" in lineage.signs)
        negative = sum(1 for lineage in independent_lineages if "negative" in lineage.signs)
        sign_positive = sum(1 for lineage in sign_lineages if "positive" in lineage.signs)
        sign_negative = sum(1 for lineage in sign_lineages if "negative" in lineage.signs)
        unsigned = sum(
            1 for lineage in independent_lineages if set(lineage.signs) & {"unsigned", "unknown"}
        )
        sign_unsigned = sum(
            1 for lineage in sign_lineages if set(lineage.signs) & {"unsigned", "unknown"}
        )
        contextual = sum(1 for item in items if item.contextual_only)
        conflict = sign_positive > 0 and sign_negative > 0
        consensus_sign = (
            "conflicting"
            if conflict
            else "positive"
            if sign_positive
            else "negative"
            if sign_negative
            else "unsigned"
        )
        graph_layers = []
        if conflict:
            graph_layers.append("conflicting")
        if (sign_positive or sign_negative) and not conflict:
            graph_layers.append("signed_causal")
        if sign_unsigned:
            graph_layers.append("unsigned_functional")
        if contextual:
            graph_layers.append("contextual")
        consensus.append(
            ConsensusMechanisticEdgeRecordV2(
                consensus_edge_id=f"consensus:{index:05d}",
                source_entity_id=source,
                target_entity_id=target,
                graph_layers=tuple(graph_layers),
                positive_signed_support=positive,
                negative_signed_support=negative,
                unsigned_functional_support=unsigned,
                contextual_support=contextual,
                exact_duplicate_count=sum(
                    1
                    for lineage in tuple(lineage_by_id.values())
                    if lineage.relationship_class == "exact_duplicate"
                ),
                likely_duplicate_count=len(duplicate_lineages),
                independent_lineage_count=len(independent_lineages),
                independent_publication_count=len(publications),
                original_database_count=len(original_dbs),
                access_provider_count=len(access_providers),
                consensus_sign=consensus_sign,
                conflict_status="opposing_signed_evidence" if conflict else "none",
                causal_eligible=bool((sign_positive or sign_negative) and not conflict),
                evidence_quality=round(min(qualities) if qualities else 0.0, 6),
                component_evidence_ids=tuple(item.evidence_id for item in items),
                lineage_group_ids=lineage_ids,
                context_summary={
                    key: ",".join(
                        sorted({value for item in items if (value := getattr(item, key))})
                    )
                    for key in ("cell_type", "tissue", "compartment", "experimental_system")
                },
            )
        )
    return consensus


def build_graph_layers_v2(
    *,
    provider_evidence: list[ProviderEdgeEvidenceRecordV2],
    consensus_edges: list[ConsensusMechanisticEdgeRecordV2],
    lineage_groups: list[LineageGroupRecordV2],
    quality_by_evidence_id: dict[str, EvidenceQualityComponentsV2],
    resolutions: dict[str, IdentifierResolutionRecordV2],
) -> dict[str, nx.MultiDiGraph[Any]]:
    graphs: dict[str, nx.MultiDiGraph[Any]] = {
        "provider_evidence": nx.MultiDiGraph(),
        "signed_causal": nx.MultiDiGraph(),
        "unsigned_functional": nx.MultiDiGraph(),
        "contextual": nx.MultiDiGraph(),
        "conflicting": nx.MultiDiGraph(),
    }
    lineage_by_evidence = {
        evidence_id: lineage
        for lineage in lineage_groups
        for evidence_id in lineage.member_evidence_ids
    }
    for evidence in provider_evidence:
        lineage = lineage_by_evidence.get(evidence.evidence_id)
        quality = quality_by_evidence_id.get(evidence.evidence_id)
        graphs["provider_evidence"].add_edge(
            evidence.source_entity_id,
            evidence.target_entity_id,
            key=evidence.evidence_id,
            evidence_id=evidence.evidence_id,
            provider_record_id=evidence.provider_record_id,
            original_database=evidence.original_database,
            access_provider=evidence.access_provider,
            sign=evidence.sign,
            directed=evidence.directed,
            relation_type=evidence.relation_type,
            mechanism=evidence.mechanism,
            directness=evidence.directness,
            functional_only=evidence.functional_only,
            contextual_only=evidence.contextual_only,
            causal_eligible=evidence.causal_eligible,
            references=evidence.references,
            context=_context_token(evidence),
            source_resolution_id=evidence.source_resolution_id,
            target_resolution_id=evidence.target_resolution_id,
            provider_snapshot_id=evidence.provider_snapshot_id,
            evidence_quality_id=evidence.evidence_id,
            evidence_quality=quality.capped_score if quality else 0.0,
            lineage_group_id=lineage.lineage_group_id if lineage else "",
        )
    for edge in consensus_edges:
        for layer in edge.graph_layers or ("contextual",):
            graph = graphs[layer]
            graph.add_edge(
                edge.source_entity_id,
                edge.target_entity_id,
                key=edge.consensus_edge_id,
                consensus_edge_id=edge.consensus_edge_id,
                sign=edge.consensus_sign,
                directed=True,
                causal_eligible=edge.causal_eligible,
                component_evidence_ids=edge.component_evidence_ids,
                lineage_group_ids=edge.lineage_group_ids,
                evidence_quality=edge.evidence_quality,
                graph_layer=layer,
            )
    return graphs


def trace_v2_graph_paths(
    *,
    graphs: dict[str, nx.MultiDiGraph[Any]],
    consensus_edges: list[ConsensusMechanisticEdgeRecordV2],
    provider_evidence: list[ProviderEdgeEvidenceRecordV2],
    resolutions: dict[str, IdentifierResolutionRecordV2],
    policy: PathSearchPolicyV1,
    source_symbols: list[str] | None = None,
    candidate_entity_ids: tuple[str, ...] | None = None,
    observed_directions_by_symbol: dict[str, str] | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[PathSearchResultV1]]:
    consensus_by_id = {edge.consensus_edge_id: edge for edge in consensus_edges}
    evidence_by_id = {item.evidence_id: item for item in provider_evidence}
    signed_paths: list[dict[str, Any]] = []
    unsigned_paths: list[dict[str, Any]] = []
    search_results: list[PathSearchResultV1] = []
    retained_total = 0
    signed_rows, signed_results, retained_total = _trace_layer_paths(
        graph=graphs["signed_causal"],
        graph_layer="signed_causal",
        consensus_by_id=consensus_by_id,
        evidence_by_id=evidence_by_id,
        resolutions=resolutions,
        policy=policy,
        source_symbols=source_symbols,
        candidate_entity_ids=candidate_entity_ids,
        observed_directions_by_symbol=observed_directions_by_symbol or {},
        signed=True,
        search_enabled=policy.trace_signed_paths,
        retained_total=retained_total,
    )
    signed_paths.extend(signed_rows)
    search_results.extend(signed_results)
    for layer, enabled in (
        ("unsigned_functional", policy.trace_unsigned_paths),
        ("contextual", policy.trace_contextual_paths),
    ):
        layer_rows, layer_results, retained_total = _trace_layer_paths(
            graph=graphs[layer],
            graph_layer=layer,
            consensus_by_id=consensus_by_id,
            evidence_by_id=evidence_by_id,
            resolutions=resolutions,
            policy=policy,
            source_symbols=source_symbols,
            candidate_entity_ids=candidate_entity_ids,
            observed_directions_by_symbol=observed_directions_by_symbol or {},
            signed=False,
            search_enabled=enabled,
            retained_total=retained_total,
        )
        unsigned_paths.extend(layer_rows)
        search_results.extend(layer_results)
    return signed_paths, unsigned_paths, search_results


def _trace_layer_paths(
    *,
    graph: nx.MultiDiGraph[Any],
    graph_layer: str,
    consensus_by_id: dict[str, ConsensusMechanisticEdgeRecordV2],
    evidence_by_id: dict[str, ProviderEdgeEvidenceRecordV2],
    resolutions: dict[str, IdentifierResolutionRecordV2],
    policy: PathSearchPolicyV1,
    source_symbols: list[str] | None,
    candidate_entity_ids: tuple[str, ...] | None,
    observed_directions_by_symbol: dict[str, str],
    signed: bool,
    search_enabled: bool,
    retained_total: int,
) -> tuple[list[dict[str, Any]], list[PathSearchResultV1], int]:
    rows: list[dict[str, Any]] = []
    search_results: list[PathSearchResultV1] = []
    seen_edge_sequences: set[tuple[str, ...]] = set()
    if not search_enabled:
        search_results.append(
            PathSearchResultV1(
                schema_version="1",
                search_result_id=_search_result_id(
                    graph_layer=graph_layer,
                    source_entity_id="disabled",
                    candidate_entity_id=None,
                    policy_id=policy.policy_id,
                ),
                search_policy_id=policy.policy_id,
                graph_layer=graph_layer,
                source_entity_id="",
                candidate_entity_id=None,
                target_entity_id=None,
                candidate=None,
                candidate_scope="search_disabled",
                requested_source_identifier=_requested_identifier(source_symbols),
                requested_candidate_identifier=None,
                source_resolution_status="not_applicable",
                candidate_resolution_status="not_applicable",
                generated_path_count=0,
                retained_path_count=0,
                discarded_path_count=0,
                discarded_by_per_candidate_cap_count=0,
                discarded_by_global_cap_count=0,
                discarded_duplicate_path_count=0,
                discarded_by_graph_layer_policy_count=0,
                retained_path_ids=(),
                maximum_depth_reached=0,
                truncation_status="search_disabled",
                termination_reason="disabled_by_path_search_policy",
                truncated=False,
            )
        )
        return rows, search_results, retained_total
    sources = _graph_search_sources(graph, resolutions, source_symbols)
    for source_scope in sources:
        if source_scope["status"] != "resolved":
            search_results.append(
                _path_search_result(
                    graph_layer=graph_layer,
                    policy=policy,
                    source=source_scope.get("entity_id") or "",
                    target=None,
                    candidate=None,
                    candidate_scope="requested_source",
                    requested_source_identifier=source_scope.get("requested_identifier"),
                    requested_candidate_identifier=None,
                    source_resolution_status=source_scope["status"],
                    candidate_resolution_status="not_applicable",
                    generated=0,
                    retained=0,
                    discarded=0,
                    discarded_by_per_candidate_cap=0,
                    discarded_by_global_cap=0,
                    discarded_duplicate=0,
                    discarded_by_graph_layer_policy=0,
                    retained_path_ids=(),
                    max_depth=0,
                    status=source_scope["status"],
                    reason=source_scope["status"],
                )
            )
            continue
        source = source_scope["entity_id"]
        targets = _graph_search_targets(
            graph=graph,
            source=source,
            candidate_entity_ids=candidate_entity_ids,
        )
        for target in targets:
            target_id = str(target["entity_id"]) if target["entity_id"] is not None else None
            if (
                policy.maximum_total_paths is not None
                and retained_total >= policy.maximum_total_paths
            ):
                search_results.append(
                    _path_search_result(
                        graph_layer=graph_layer,
                        policy=policy,
                        source=source,
                        target=target_id,
                        candidate=_entity_symbol(target_id, resolutions) if target_id else None,
                        candidate_scope=target["scope"],
                        requested_source_identifier=source_scope.get("requested_identifier"),
                        requested_candidate_identifier=target.get("requested_identifier"),
                        source_resolution_status=source_scope["status"],
                        candidate_resolution_status=target["status"],
                        generated=0,
                        retained=0,
                        discarded=0,
                        discarded_by_per_candidate_cap=0,
                        discarded_by_global_cap=0,
                        discarded_duplicate=0,
                        discarded_by_graph_layer_policy=0,
                        retained_path_ids=(),
                        max_depth=0,
                        status="maximum_total_paths_reached",
                        reason="maximum_total_paths_reached",
                    )
                )
                return rows, search_results, retained_total
            if target["status"] != "resolved" or target_id is None:
                search_results.append(
                    _path_search_result(
                        graph_layer=graph_layer,
                        policy=policy,
                        source=source,
                        target=target_id,
                        candidate=_entity_symbol(target_id, resolutions) if target_id else None,
                        candidate_scope=target["scope"],
                        requested_source_identifier=source_scope.get("requested_identifier"),
                        requested_candidate_identifier=target.get("requested_identifier"),
                        source_resolution_status=source_scope["status"],
                        candidate_resolution_status=target["status"],
                        generated=0,
                        retained=0,
                        discarded=0,
                        discarded_by_per_candidate_cap=0,
                        discarded_by_global_cap=0,
                        discarded_duplicate=0,
                        discarded_by_graph_layer_policy=0,
                        retained_path_ids=(),
                        max_depth=0,
                        status=target["status"],
                        reason=target["status"],
                    )
                )
                continue
            if not nx.has_path(graph, source, target_id):
                search_results.append(
                    _path_search_result(
                        graph_layer=graph_layer,
                        policy=policy,
                        source=source,
                        target=target_id,
                        candidate=_entity_symbol(target_id, resolutions),
                        candidate_scope=target["scope"],
                        requested_source_identifier=source_scope.get("requested_identifier"),
                        requested_candidate_identifier=target.get("requested_identifier"),
                        source_resolution_status=source_scope["status"],
                        candidate_resolution_status=target["status"],
                        generated=0,
                        retained=0,
                        discarded=0,
                        discarded_by_per_candidate_cap=0,
                        discarded_by_global_cap=0,
                        discarded_duplicate=0,
                        discarded_by_graph_layer_policy=0,
                        retained_path_ids=(),
                        max_depth=0,
                        status="no_path_found",
                        reason="target_not_reachable_in_graph_layer",
                    )
                )
                continue
            generated = 0
            retained_for_target = 0
            discarded = 0
            discarded_by_per_candidate_cap = 0
            discarded_by_global_cap = 0
            discarded_duplicate = 0
            discarded_by_graph_layer_policy = 0
            max_depth_reached = 0
            status = "complete"
            reason = "all_simple_paths_exhausted"
            search_id = _search_result_id(
                graph_layer=graph_layer,
                source_entity_id=str(source),
                candidate_entity_id=target_id,
                policy_id=policy.policy_id,
            )
            retained_path_ids: list[str] = []
            path_candidates = _candidate_node_paths(
                graph,
                source=source,
                target=target_id,
                max_path_length=policy.max_path_length,
                shortest_paths_only=policy.shortest_paths_only,
            )
            if _has_frontier_beyond_cutoff(
                graph, source=source, target=target_id, max_path_length=policy.max_path_length
            ):
                status = "maximum_path_length_reached"
                reason = "search_cutoff_depth_reached"
            for node_path in path_candidates:
                edge_steps = _edge_steps_for_node_path(graph, node_path)
                if not edge_steps:
                    continue
                generated += 1
                max_depth_reached = max(max_depth_reached, len(edge_steps))
                consensus_ids = tuple(step["consensus_edge_id"] for step in edge_steps)
                if consensus_ids in seen_edge_sequences:
                    discarded += 1
                    discarded_duplicate += 1
                    continue
                seen_edge_sequences.add(consensus_ids)
                edges = [consensus_by_id[edge_id] for edge_id in consensus_ids]
                if signed and not _is_signed_causal_path(edges):
                    discarded += 1
                    discarded_by_graph_layer_policy += 1
                    continue
                if retained_for_target >= policy.maximum_paths_per_candidate:
                    discarded += 1
                    discarded_by_per_candidate_cap += 1
                    status = "maximum_paths_per_candidate_reached"
                    reason = "maximum_paths_per_candidate_reached"
                    break
                if (
                    policy.maximum_total_paths is not None
                    and retained_total >= policy.maximum_total_paths
                ):
                    discarded += 1
                    discarded_by_global_cap += 1
                    status = "maximum_total_paths_reached"
                    reason = "maximum_total_paths_reached"
                    break
                component_ids = tuple(
                    dict.fromkeys(
                        evidence_id for edge in edges for evidence_id in edge.component_evidence_ids
                    )
                )
                lineage_ids = tuple(
                    dict.fromkeys(
                        lineage_id for edge in edges for lineage_id in edge.lineage_group_ids
                    )
                )
                cumulative_sign = _cumulative_path_sign(edges) if signed else "unsupported"
                candidate_symbol = _entity_symbol(target_id, resolutions)
                expected_direction = (
                    _expected_direction_after_source_decrease(cumulative_sign) if signed else None
                )
                observed_direction = observed_directions_by_symbol.get(candidate_symbol)
                path_rank = retained_for_target + 1
                path_id = f"v2path:{_safe_id(search_id)}:{path_rank:05d}"
                row = {
                    "path_id": path_id,
                    "source_entity_id": str(source),
                    "target_entity_id": target_id,
                    "source_type": "v2_semantic_graph_source",
                    "selection_reason": "reachable_in_v2_semantic_graph",
                    "selection_policy_version": "v2-graph-path-search-1",
                    "candidate": candidate_symbol,
                    "graph_layer": graph_layer,
                    "ordered_entity_ids": [str(node) for node in node_path],
                    "ordered_nodes": [str(node) for node in node_path],
                    "ordered_consensus_edge_ids": list(consensus_ids),
                    "component_provider_evidence_ids": list(component_ids),
                    "lineage_group_ids": list(lineage_ids),
                    "graph_edge_keys": [str(step["key"]) for step in edge_steps],
                    "path_length": len(consensus_ids),
                    "directed": signed,
                    "fully_signed": signed,
                    "cumulative_path_sign": cumulative_sign,
                    "composed_sign": cumulative_sign if signed else "unknown",
                    "expected_downstream_direction_after_source_decrease": (expected_direction),
                    "expected_candidate_direction_after_target_decrease": (expected_direction),
                    "observed_candidate_direction": observed_direction,
                    "direction_consistent": (
                        expected_direction == observed_direction
                        if expected_direction and observed_direction
                        else None
                    ),
                    "directional_interpretation": "signed_causal" if signed else "unsupported",
                    "search_result_id": search_id,
                    "search_policy_id": policy.policy_id,
                    "search_policy_version": policy.policy_id,
                    "path_rank": path_rank,
                    "context_summary": _path_context_summary(component_ids, evidence_by_id),
                    "canonical_path_source": "v2_semantic_graph",
                    "legacy_path": False,
                    "warnings": [],
                }
                rows.append(row)
                retained_path_ids.append(path_id)
                retained_for_target += 1
                retained_total += 1
            search_results.append(
                _path_search_result(
                    graph_layer=graph_layer,
                    policy=policy,
                    source=source,
                    target=target_id,
                    candidate=_entity_symbol(target_id, resolutions),
                    candidate_scope=target["scope"],
                    requested_source_identifier=source_scope.get("requested_identifier"),
                    requested_candidate_identifier=target.get("requested_identifier"),
                    source_resolution_status=source_scope["status"],
                    candidate_resolution_status=target["status"],
                    generated=generated,
                    retained=retained_for_target,
                    discarded=discarded,
                    discarded_by_per_candidate_cap=discarded_by_per_candidate_cap,
                    discarded_by_global_cap=discarded_by_global_cap,
                    discarded_duplicate=discarded_duplicate,
                    discarded_by_graph_layer_policy=discarded_by_graph_layer_policy,
                    retained_path_ids=tuple(retained_path_ids),
                    max_depth=max_depth_reached,
                    status=status,
                    reason=reason,
                )
            )
    return rows, search_results, retained_total


def _path_search_result(
    *,
    graph_layer: str,
    policy: PathSearchPolicyV1,
    source: Any,
    target: Any | None,
    candidate: str | None,
    candidate_scope: str,
    requested_source_identifier: str | None,
    requested_candidate_identifier: str | None,
    source_resolution_status: str,
    candidate_resolution_status: str,
    generated: int,
    retained: int,
    discarded: int,
    discarded_by_per_candidate_cap: int,
    discarded_by_global_cap: int,
    discarded_duplicate: int,
    discarded_by_graph_layer_policy: int,
    retained_path_ids: tuple[str, ...],
    max_depth: int,
    status: str,
    reason: str,
) -> PathSearchResultV1:
    target_id = str(target) if target is not None else None
    truncated = status in {
        "maximum_path_length_reached",
        "maximum_paths_per_candidate_reached",
        "maximum_total_paths_reached",
    }
    return PathSearchResultV1(
        schema_version="1",
        search_result_id=_search_result_id(
            graph_layer=graph_layer,
            source_entity_id=str(source),
            candidate_entity_id=target_id,
            policy_id=policy.policy_id,
        ),
        search_policy_id=policy.policy_id,
        graph_layer=graph_layer,
        source_entity_id=str(source),
        candidate_entity_id=target_id,
        target_entity_id=target_id,
        candidate=candidate,
        candidate_scope=candidate_scope,
        requested_source_identifier=requested_source_identifier,
        requested_candidate_identifier=requested_candidate_identifier,
        source_resolution_status=source_resolution_status,
        candidate_resolution_status=candidate_resolution_status,
        generated_path_count=generated,
        retained_path_count=retained,
        discarded_path_count=discarded,
        discarded_by_per_candidate_cap_count=discarded_by_per_candidate_cap,
        discarded_by_global_cap_count=discarded_by_global_cap,
        discarded_duplicate_path_count=discarded_duplicate,
        discarded_by_graph_layer_policy_count=discarded_by_graph_layer_policy,
        retained_path_ids=retained_path_ids,
        maximum_depth_reached=max_depth,
        truncation_status=status,
        termination_reason=reason,
        truncated=truncated,
    )


def _validate_path_search_linkage(
    paths: list[dict[str, Any]], search_results: list[PathSearchResultV1]
) -> None:
    results_by_id = {result.search_result_id: result for result in search_results}
    if len(results_by_id) != len(search_results):
        msg = "duplicate_path_search_result_ids"
        raise RuntimeError(msg)
    paths_by_id = {str(path["path_id"]): path for path in paths}
    for path in paths:
        search_result_id = str(path.get("search_result_id") or "")
        result = results_by_id.get(search_result_id)
        if result is None:
            msg = f"path_search_result_not_found:{search_result_id}"
            raise RuntimeError(msg)
        if result.graph_layer != path.get("graph_layer"):
            msg = f"path_search_graph_layer_mismatch:{path['path_id']}"
            raise RuntimeError(msg)
        if result.source_entity_id != path.get("source_entity_id"):
            msg = f"path_search_source_mismatch:{path['path_id']}"
            raise RuntimeError(msg)
        if result.target_entity_id != path.get("target_entity_id"):
            msg = f"path_search_target_mismatch:{path['path_id']}"
            raise RuntimeError(msg)
        if result.search_policy_id != path.get("search_policy_id"):
            msg = f"path_search_policy_mismatch:{path['path_id']}"
            raise RuntimeError(msg)
    for result in search_results:
        for path_id in result.retained_path_ids:
            child = paths_by_id.get(path_id)
            if child is None:
                msg = f"search_result_child_path_not_found:{result.search_result_id}:{path_id}"
                raise RuntimeError(msg)
            if child.get("search_result_id") != result.search_result_id:
                msg = f"search_result_child_parent_mismatch:{path_id}"
                raise RuntimeError(msg)


def _graph_search_sources(
    graph: nx.MultiDiGraph[Any],
    resolutions: dict[str, IdentifierResolutionRecordV2],
    source_symbols: list[str] | None,
) -> list[dict[str, Any]]:
    requested = {symbol.upper() for symbol in source_symbols or []}
    if requested:
        matched = sorted(
            node
            for node in graph.nodes
            if _entity_symbol(str(node), resolutions).upper() in requested
            and graph.out_degree(node) > 0
        )
        if matched:
            return [
                {
                    "entity_id": str(node),
                    "status": "resolved",
                    "requested_identifier": _entity_symbol(str(node), resolutions),
                }
                for node in matched
            ]
        known = [
            entity_id
            for entity_id, resolution in resolutions.items()
            if (resolution.approved_symbol or "").upper() in requested
        ]
        if known:
            return [
                {
                    "entity_id": str(entity_id),
                    "status": "source_not_in_graph",
                    "requested_identifier": _entity_symbol(str(entity_id), resolutions),
                }
                for entity_id in sorted(known)
            ]
        return [
            {
                "entity_id": "",
                "status": "source_unresolved",
                "requested_identifier": symbol,
            }
            for symbol in sorted(requested)
        ]
    roots = [
        node for node in graph.nodes if graph.out_degree(node) > 0 and graph.in_degree(node) == 0
    ]
    if roots:
        return [
            {
                "entity_id": str(node),
                "status": "resolved",
                "requested_identifier": None,
            }
            for node in sorted(roots)
        ]
    return [
        {
            "entity_id": str(node),
            "status": "resolved",
            "requested_identifier": None,
        }
        for node in sorted(node for node in graph.nodes if graph.out_degree(node) > 0)
    ]


def _graph_search_targets(
    *,
    graph: nx.MultiDiGraph[Any],
    source: str,
    candidate_entity_ids: tuple[str, ...] | None,
) -> list[dict[str, Any]]:
    if candidate_entity_ids is not None:
        targets = []
        for candidate_id in candidate_entity_ids:
            if candidate_id in graph and candidate_id != source:
                targets.append(
                    {
                        "entity_id": candidate_id,
                        "status": "resolved",
                        "scope": "explicit_candidate_scope",
                        "requested_identifier": candidate_id,
                    }
                )
            else:
                targets.append(
                    {
                        "entity_id": candidate_id,
                        "status": "candidate_not_in_graph",
                        "scope": "explicit_candidate_scope",
                        "requested_identifier": candidate_id,
                    }
                )
        return targets
    return [
        {
            "entity_id": str(node),
            "status": "resolved",
            "scope": "all_reachable_entities",
            "requested_identifier": None,
        }
        for node in sorted(node for node in graph.nodes if node != source)
    ]


def _candidate_node_paths(
    graph: nx.MultiDiGraph[Any],
    *,
    source: str,
    target: str,
    max_path_length: int,
    shortest_paths_only: bool,
) -> list[list[Any]]:
    if shortest_paths_only:
        try:
            shortest_length = nx.shortest_path_length(graph, source=source, target=target)
        except nx.NetworkXNoPath:
            return []
        if shortest_length > max_path_length:
            return []
        cutoff = int(shortest_length)
    else:
        cutoff = max_path_length
    paths = list(nx.all_simple_paths(graph, source=source, target=target, cutoff=cutoff))
    if shortest_paths_only:
        paths = [path for path in paths if len(path) - 1 == cutoff]
    return sorted(paths, key=_node_path_sort_key(graph))


def _node_path_sort_key(graph: nx.MultiDiGraph[Any]) -> Any:
    def sort_key(node_path: list[Any]) -> tuple[int, tuple[str, ...], tuple[str, ...]]:
        edge_steps = _edge_steps_for_node_path(graph, node_path)
        consensus_ids = tuple(str(step["consensus_edge_id"]) for step in edge_steps)
        return (len(edge_steps), tuple(str(node) for node in node_path), consensus_ids)

    return sort_key


def _has_frontier_beyond_cutoff(
    graph: nx.MultiDiGraph[Any], *, source: str, target: str, max_path_length: int
) -> bool:
    if max_path_length < 1:
        return nx.has_path(graph, source, target)
    return any(
        len(path) - 1 > max_path_length
        for path in nx.all_simple_paths(
            graph, source=source, target=target, cutoff=max_path_length + 1
        )
    )


def _search_result_id(
    *,
    graph_layer: str,
    source_entity_id: str,
    candidate_entity_id: str | None,
    policy_id: str,
) -> str:
    raw = "|".join((graph_layer, source_entity_id, candidate_entity_id or "broad", policy_id))
    return "search:" + sha1(raw.encode("utf-8")).hexdigest()[:16]


def _safe_id(value: str) -> str:
    return sha1(value.encode("utf-8")).hexdigest()[:16]


def _requested_identifier(source_symbols: list[str] | None) -> str | None:
    return ",".join(source_symbols) if source_symbols else None


def _edge_steps_for_node_path(
    graph: nx.MultiDiGraph[Any], node_path: list[Any]
) -> list[dict[str, Any]]:
    steps = []
    for source, target in zip(node_path[:-1], node_path[1:], strict=True):
        edges = graph.get_edge_data(source, target) or {}
        if not edges:
            return []
        key, data = sorted(edges.items(), key=lambda item: str(item[0]))[0]
        steps.append({"key": key, **data})
    return steps


def _is_signed_causal_path(edges: list[ConsensusMechanisticEdgeRecordV2]) -> bool:
    return all(
        edge.consensus_sign in {"positive", "negative"}
        and edge.causal_eligible
        and edge.conflict_status == "none"
        and "signed_causal" in edge.graph_layers
        for edge in edges
    )


def _cumulative_path_sign(edges: list[ConsensusMechanisticEdgeRecordV2]) -> str:
    negative_count = sum(1 for edge in edges if edge.consensus_sign == "negative")
    return "positive" if negative_count % 2 == 0 else "negative"


def _expected_direction_after_source_decrease(cumulative_sign: str) -> str:
    return "down" if cumulative_sign == "positive" else "up"


def _entity_symbol(entity_id: str, resolutions: dict[str, IdentifierResolutionRecordV2]) -> str:
    resolution = resolutions.get(entity_id)
    if resolution and resolution.approved_symbol:
        return resolution.approved_symbol
    return entity_id.split(":", 1)[-1]


def build_path_confidence_records_v2(
    *,
    paths: list[dict[str, Any]],
    consensus_edges: list[ConsensusMechanisticEdgeRecordV2],
    quality_by_evidence_id: dict[str, EvidenceQualityComponentsV2],
    provider_evidence: list[ProviderEdgeEvidenceRecordV2],
    lineage_groups: list[LineageGroupRecordV2],
    resolutions: dict[str, IdentifierResolutionRecordV2],
) -> list[PathConfidenceRecordV2]:
    consensus_by_id = {edge.consensus_edge_id: edge for edge in consensus_edges}
    provider_to_consensus = {
        evidence_id: edge.consensus_edge_id
        for edge in consensus_edges
        for evidence_id in edge.component_evidence_ids
    }
    evidence_by_id = {item.evidence_id: item for item in provider_evidence}
    lineage_by_id = {lineage.lineage_group_id: lineage for lineage in lineage_groups}
    records = []
    for path in paths:
        explicit_consensus_ids = tuple(
            str(edge_id) for edge_id in path.get("ordered_consensus_edge_ids", ()) or ()
        )
        provider_edge_ids = tuple(
            str(edge_id) for edge_id in path.get("ordered_edge_ids", ()) or ()
        )
        edge_ids = explicit_consensus_ids or tuple(
            dict.fromkeys(
                provider_to_consensus.get(edge_id, edge_id) for edge_id in provider_edge_ids
            )
        )
        edges = [consensus_by_id[edge_id] for edge_id in edge_ids if edge_id in consensus_by_id]
        edge_scores = {edge.consensus_edge_id: edge.evidence_quality for edge in edges}
        if not edge_scores:
            continue
        bottleneck_edge_id, minimum = min(edge_scores.items(), key=lambda item: item[1])
        average = sum(edge_scores.values()) / len(edge_scores)
        fully_directed = bool(path.get("directed", True))
        fully_signed = bool(path.get("fully_signed", False))
        component_evidence = [
            evidence_by_id[evidence_id]
            for edge in edges
            for evidence_id in edge.component_evidence_ids
            if evidence_id in evidence_by_id
        ]
        mapping_values = [
            resolutions[entity_id].mapping_confidence
            for evidence in component_evidence
            for entity_id in (evidence.source_entity_id, evidence.target_entity_id)
            if entity_id in resolutions
        ]
        mapping_confidence = min(mapping_values) if mapping_values else 0.0
        publications = {
            publication
            for edge in edges
            for lineage_id in edge.lineage_group_ids
            if lineage_id in lineage_by_id
            for publication in lineage_by_id[lineage_id].publication_ids
        }
        lineage_ids = {
            lineage_id
            for edge in edges
            for lineage_id in edge.lineage_group_ids
            if lineage_id in lineage_by_id
        }
        predicted_count = sum(1 for evidence in component_evidence if evidence.predicted_only)
        indirect_count = sum(
            1 for evidence in component_evidence if evidence.directness != "direct"
        )
        missing_context_count = sum(
            1
            for evidence in component_evidence
            if not any(
                (
                    evidence.cell_type,
                    evidence.tissue,
                    evidence.compartment,
                    evidence.experimental_system,
                    evidence.disease_state,
                )
            )
        )
        unsupported_entity_count = sum(
            1
            for evidence in component_evidence
            for entity_type in (evidence.source_entity_type, evidence.target_entity_type)
            if entity_type == "unknown"
        )
        edge_count = max(len(component_evidence), 1)
        conflict_count = sum(1 for edge in edges if edge.conflict_status != "none")
        capped = min(average, minimum, mapping_confidence)
        cap_reasons = []
        if unsupported_entity_count:
            capped = min(capped, 0.2)
            cap_reasons.append("unsupported_entity_cap")
        if predicted_count:
            capped = min(capped, 0.7)
            cap_reasons.append("predicted_edge_cap")
        if indirect_count == edge_count:
            capped = min(capped, 0.55)
            cap_reasons.append("indirect_path_cap")
        if conflict_count:
            capped = min(capped, 0.4)
            cap_reasons.append("conflicting_component_cap")
        if not fully_signed:
            capped = min(capped, 0.55)
            cap_reasons.append("mixed_contextual_path_cap")
        records.append(
            PathConfidenceRecordV2(
                path_id=str(path["path_id"]),
                path_type="signed_causal" if fully_directed and fully_signed else "contextual",
                edge_ids=edge_ids,
                path_length=int(path.get("path_length", len(edge_ids))),
                minimum_edge_quality_score=round(minimum, 6),
                average_edge_quality_score=round(average, 6),
                bottleneck_edge_id=bottleneck_edge_id,
                bottleneck_cap=round(minimum, 6),
                fully_directed=fully_directed,
                fully_signed=fully_signed,
                independent_lineage_count=len(lineage_ids),
                independent_publication_count=len(publications),
                minimum_identifier_mapping_confidence=round(mapping_confidence, 6),
                predicted_edge_fraction=round(predicted_count / edge_count, 6),
                indirect_edge_fraction=round(indirect_count / edge_count, 6),
                context_match_fraction=0.0 if missing_context_count else 1.0,
                missing_context_fraction=round(missing_context_count / edge_count, 6),
                conflicting_edge_count=conflict_count,
                unsupported_entity_count=unsupported_entity_count,
                truncation_status=str(path.get("truncation_status") or "search_not_truncated"),
                component_weights={"average_edge_quality": 0.5, "bottleneck": 0.3, "mapping": 0.2},
                raw_score=round(average, 6),
                capped_score=round(capped, 6),
                confidence_level=_level_from_score(capped),
                uncertainty=round(1.0 - capped, 6),
                policy_version="runtime-path-confidence-v2",
                warnings=tuple(cap_reasons),
            )
        )
    return records


def build_contextual_conflicts_v2(
    *,
    paths: list[dict[str, Any]],
    confidence_records: list[PathConfidenceRecordV2],
    consensus_edges: list[ConsensusMechanisticEdgeRecordV2],
    provider_evidence: list[ProviderEdgeEvidenceRecordV2],
) -> list[Any]:
    by_candidate = cast(
        dict[str, dict[str, list[str]]],
        defaultdict(lambda: {"positive": [], "negative": []}),
    )
    for path in paths:
        sign = str(path.get("composed_sign") or "")
        if sign in {"positive", "negative"}:
            by_candidate[str(path.get("candidate", ""))][sign].append(str(path.get("path_id")))
    conflicts = []
    confidence_by_path = {record.path_id: record.capped_score for record in confidence_records}
    contexts_by_path = _contexts_by_path(paths, consensus_edges, provider_evidence)
    for index, (candidate, groups) in enumerate(sorted(by_candidate.items()), start=1):
        if groups["positive"] and groups["negative"]:
            summary = classify_contextual_conflict(
                f"context-conflict:{index:05d}",
                candidate,
                tuple(groups["positive"]),
                tuple(groups["negative"]),
                tuple(
                    sorted(
                        {ctx for path_id in groups["positive"] for ctx in contexts_by_path[path_id]}
                    )
                ),
                tuple(
                    sorted(
                        {ctx for path_id in groups["negative"] for ctx in contexts_by_path[path_id]}
                    )
                ),
            )
            positive = max(groups["positive"], key=lambda item: confidence_by_path.get(item, 0.0))
            negative = max(groups["negative"], key=lambda item: confidence_by_path.get(item, 0.0))
            conflicts.append(
                replace(
                    summary,
                    strongest_positive_path=positive,
                    strongest_negative_path=negative,
                    warnings=(_warning_for_conflict_class(summary.conflict_class),),
                )
            )
    conflict_index = len(conflicts) + 1
    evidence_by_id = {item.evidence_id: item for item in provider_evidence}
    for edge in consensus_edges:
        if edge.conflict_status == "none":
            continue
        component = [
            evidence_by_id[evidence_id]
            for evidence_id in edge.component_evidence_ids
            if evidence_id in evidence_by_id
        ]
        positive_ids = tuple(item.evidence_id for item in component if item.sign == "positive")
        negative_ids = tuple(item.evidence_id for item in component if item.sign == "negative")
        if not positive_ids or not negative_ids:
            continue
        candidate = _resolution_symbol(component[0].target_resolution_id)
        summary = classify_contextual_conflict(
            f"context-conflict:{conflict_index:05d}",
            candidate,
            positive_ids,
            negative_ids,
            tuple(
                _typed_context_key(_structured_context_record(item))
                for item in component
                if item.sign == "positive"
            ),
            tuple(
                _typed_context_key(_structured_context_record(item))
                for item in component
                if item.sign == "negative"
            ),
        )
        conflicts.append(
            replace(summary, warnings=(_warning_for_conflict_class(summary.conflict_class),))
        )
        conflict_index += 1
    return conflicts


def _warning_for_conflict_class(conflict_class: str) -> str:
    return {
        "global_sign_conflict": (
            "independent opposing evidence exists in overlapping known context"
        ),
        "context_specific_conflict": (
            "opposing evidence is separated by known biological or experimental context"
        ),
        "unresolved_context_conflict": (
            "missing or unresolved context prevents global or context-specific classification"
        ),
        "duplicate_access_disagreement": (
            "apparent disagreement is not independent because evidence shares an original source"
        ),
        "mapping_related_conflict": "unresolved identifier mapping contributes to the disagreement",
        "mechanism_disagreement": (
            "mechanisms differ without a definitive signed directional conflict"
        ),
    }.get(conflict_class, "contextual conflict requires review")


def _split_paths_by_graph_layer(
    paths: list[dict[str, Any]],
    consensus_edges: list[ConsensusMechanisticEdgeRecordV2],
    provider_evidence: list[ProviderEdgeEvidenceRecordV2] | None = None,
    legacy_trace_edges: list[dict[str, Any]] | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    consensus_by_id = {edge.consensus_edge_id: edge for edge in consensus_edges}
    consensus_by_provider_evidence = {
        evidence_id: edge for edge in consensus_edges for evidence_id in edge.component_evidence_ids
    }
    legacy_aliases = _legacy_consensus_aliases(
        legacy_trace_edges or (), consensus_edges, provider_evidence or []
    )
    signed_consensus_ids = {
        edge.consensus_edge_id
        for edge in consensus_edges
        if "signed_causal" in edge.graph_layers and edge.causal_eligible
    }
    signed_paths = []
    unsigned_paths = []
    for path in paths:
        input_edge_ids = tuple(str(edge_id) for edge_id in path.get("ordered_edge_ids", ()) or ())
        consensus_ids = tuple(
            dict.fromkeys(
                consensus_by_provider_evidence[edge_id].consensus_edge_id
                if edge_id in consensus_by_provider_evidence
                else legacy_aliases.get(edge_id, edge_id)
                for edge_id in input_edge_ids
                if edge_id in consensus_by_provider_evidence
                or edge_id in consensus_by_id
                or edge_id in legacy_aliases
            )
        )
        provider_evidence_ids = tuple(
            evidence_id
            for consensus_id in consensus_ids
            for evidence_id in consensus_by_id[consensus_id].component_evidence_ids
        )
        lineage_group_ids = tuple(
            dict.fromkeys(
                lineage_id
                for consensus_id in consensus_ids
                for lineage_id in consensus_by_id[consensus_id].lineage_group_ids
            )
        )
        row = dict(path)
        row["ordered_consensus_edge_ids"] = list(consensus_ids)
        row["component_provider_evidence_ids"] = list(provider_evidence_ids)
        row["lineage_group_ids"] = list(lineage_group_ids)
        row["graph_edge_keys"] = list(consensus_ids)
        source_nodes = path.get("ordered_nodes", ()) or ()
        if source_nodes:
            row["source_entity_id"] = str(source_nodes[0])
            row["target_entity_id"] = str(source_nodes[-1])
        if (
            consensus_ids
            and set(consensus_ids) <= signed_consensus_ids
            and path.get("fully_signed")
        ):
            row["graph_layer"] = "signed_causal"
            signed_paths.append(row)
        else:
            row["graph_layer"] = "unsigned_functional_or_contextual"
            unsigned_paths.append(row)
    return signed_paths, unsigned_paths


def _legacy_consensus_aliases(
    legacy_trace_edges: tuple[dict[str, Any], ...] | list[dict[str, Any]],
    consensus_edges: list[ConsensusMechanisticEdgeRecordV2],
    provider_evidence: list[ProviderEdgeEvidenceRecordV2],
) -> dict[str, str]:
    evidence_by_id = {item.evidence_id: item for item in provider_evidence}
    consensus_tokens: dict[tuple[str, str, str], str] = {}
    for edge in consensus_edges:
        for evidence_id in edge.component_evidence_ids:
            evidence = evidence_by_id.get(evidence_id)
            if evidence is None:
                continue
            consensus_tokens[
                (
                    _resolution_symbol(evidence.source_resolution_id),
                    _resolution_symbol(evidence.target_resolution_id),
                    edge.consensus_sign,
                )
            ] = edge.consensus_edge_id
    aliases: dict[str, str] = {}
    for row in legacy_trace_edges:
        edge_id = str(row.get("edge_id") or row.get("consensus_edge_id") or "")
        if not edge_id:
            continue
        source = str(row.get("source_identifier") or row.get("source") or "")
        target = str(row.get("target_identifier") or row.get("target") or "")
        sign = str(row.get("consensus_sign") or row.get("sign") or "")
        if match := consensus_tokens.get((source, target, sign)):
            aliases[edge_id] = match
    return aliases


def _resolution_symbol(resolution_id: str) -> str:
    return resolution_id.rsplit(":", 1)[-1]


def _consensus_render_row(edge: ConsensusMechanisticEdgeRecordV2) -> dict[str, Any]:
    row = asdict(edge)
    source = edge.source_entity_id.split(":", 1)[-1]
    target = edge.target_entity_id.split(":", 1)[-1]
    row.update(
        {
            "edge_id": edge.consensus_edge_id,
            "source": source,
            "target": target,
            "directed": True,
            "sign": edge.consensus_sign,
            "functional_only": "unsigned_functional" in edge.graph_layers,
            "causal_eligible": edge.causal_eligible,
            "relation_type": "runtime_consensus",
            "evidence_level": _level_from_score(edge.evidence_quality),
            "provider_sources": [],
            "references": [],
            "lineage_groups": list(edge.lineage_group_ids),
            "positive_independent_lineage_count": edge.positive_signed_support,
            "negative_independent_lineage_count": edge.negative_signed_support,
            "unsigned_independent_lineage_count": edge.unsigned_functional_support,
            "contextual_independent_lineage_count": edge.contextual_support,
            "duplicate_lineage_count": edge.likely_duplicate_count,
            "unresolved_lineage_count": row.get("unresolved_lineage_count", 0),
            "positive_raw_evidence_count": len(
                [item for item in edge.component_evidence_ids if item]
            )
            if edge.consensus_sign == "positive"
            else 0,
            "negative_raw_evidence_count": len(
                [item for item in edge.component_evidence_ids if item]
            )
            if edge.consensus_sign == "negative"
            else 0,
            "unsigned_raw_evidence_count": len(
                [item for item in edge.component_evidence_ids if item]
            )
            if edge.consensus_sign == "unsigned"
            else 0,
        }
    )
    return row


def _structured_context(evidence: ProviderEdgeEvidenceRecordV2) -> dict[str, Any]:
    return {
        "organism": _context_dimension(
            evidence.organism, "organism", evidence.evidence_id, required=True
        ),
        "cell_type": _context_dimension(evidence.cell_type, "cell_type", evidence.evidence_id),
        "tissue": _context_dimension(evidence.tissue, "tissue", evidence.evidence_id),
        "compartment": _context_dimension(
            evidence.compartment, "cellular_component", evidence.evidence_id
        ),
        "experimental_system": _context_dimension(
            evidence.experimental_system, "experimental_system", evidence.evidence_id
        ),
        "disease_state": _context_dimension(
            evidence.disease_state, "disease_state", evidence.evidence_id
        ),
    }


def _context_dimension(
    value: str | None, vocabulary: str, evidence_id: str, *, required: bool = False
) -> dict[str, Any]:
    missing = value is None or value == ""
    return {
        "raw_value": value,
        "normalized_value": value.strip().lower() if isinstance(value, str) and value else None,
        "vocabulary": vocabulary,
        "mapping_confidence": 1.0 if value else 0.0,
        "missing_status": "present" if not missing else "missing",
        "unresolved_status": "resolved" if value or required else "unknown",
        "source_record_ids": [evidence_id],
    }


def _context_dimension_record(
    dimension: str,
    value: str | None,
    vocabulary: str,
    evidence_id: str,
    *,
    required: bool = False,
) -> ContextDimensionRecordV1:
    row = _context_dimension(value, vocabulary, evidence_id, required=required)
    return ContextDimensionRecordV1(
        dimension=dimension,
        raw_value=cast(str | None, row["raw_value"]),
        normalized_value=cast(str | None, row["normalized_value"]),
        vocabulary=cast(str, row["vocabulary"]),
        mapping_confidence=cast(float, row["mapping_confidence"]),
        missing_status=cast(str, row["missing_status"]),
        unresolved_status=cast(str, row["unresolved_status"]),
        source_record_ids=tuple(cast(list[str], row["source_record_ids"])),
    )


def _structured_context_record(
    evidence: ProviderEdgeEvidenceRecordV2,
) -> StructuredContextRecordV1:
    dimensions = {
        "organism": _context_dimension_record(
            "organism", evidence.organism, "organism", evidence.evidence_id, required=True
        ),
        "cell_type": _context_dimension_record(
            "cell_type", evidence.cell_type, "cell_type", evidence.evidence_id
        ),
        "tissue": _context_dimension_record(
            "tissue", evidence.tissue, "tissue", evidence.evidence_id
        ),
        "compartment": _context_dimension_record(
            "compartment", evidence.compartment, "cellular_component", evidence.evidence_id
        ),
        "experimental_system": _context_dimension_record(
            "experimental_system",
            evidence.experimental_system,
            "experimental_system",
            evidence.evidence_id,
        ),
        "disease_state": _context_dimension_record(
            "disease_state", evidence.disease_state, "disease_state", evidence.evidence_id
        ),
    }
    missing = tuple(
        name for name, dimension in dimensions.items() if dimension.missing_status == "missing"
    )
    unresolved = tuple(
        name for name, dimension in dimensions.items() if dimension.unresolved_status != "resolved"
    )
    complete = len(dimensions) - len(missing)
    return StructuredContextRecordV1(
        context_id=f"context:{evidence.evidence_id}",
        dimensions=dimensions,
        completeness_fraction=round(complete / len(dimensions), 6),
        missing_dimensions=missing,
        unresolved_dimensions=unresolved,
    )


def _experimental_context_from_dict(
    experiment_context: dict[str, Any] | None, *, organism: str
) -> ExperimentalContextV1:
    data = experiment_context or {}
    return ExperimentalContextV1(
        organism=str(data.get("organism") or organism),
        cell_type=_optional_str(data.get("cell_type")),
        tissue=_optional_str(data.get("tissue")),
        compartment=_optional_str(data.get("compartment")),
        experimental_system=_optional_str(data.get("experimental_system")),
        disease_state=_optional_str(data.get("disease_state")),
    )


def _context_match_states(
    evidence: ProviderEdgeEvidenceRecordV2, experiment: ExperimentalContextV1 | None
) -> dict[str, bool | None]:
    if experiment is None:
        return {
            "cell_type": None,
            "tissue": None,
            "compartment": None,
            "experimental_system": None,
            "disease_state": None,
        }
    return {
        dimension: _dimension_match(getattr(evidence, dimension), getattr(experiment, dimension))
        for dimension in (
            "cell_type",
            "tissue",
            "compartment",
            "experimental_system",
            "disease_state",
        )
    }


def _dimension_match(evidence_value: str | None, experiment_value: str | None) -> bool | None:
    if not evidence_value or not experiment_value:
        return None
    return evidence_value.strip().casefold() == experiment_value.strip().casefold()


def _context_comparison_state(*, experiment_value: str | None, evidence_value: str | None) -> str:
    left = _optional_str(experiment_value)
    right = _optional_str(evidence_value)
    if left is None and right is None:
        return "unknown_both"
    if left is None:
        return "unknown_left"
    if right is None:
        return "unknown_right"
    left_values = {item.strip().casefold() for item in left.split(",") if item.strip()}
    right_values = {item.strip().casefold() for item in right.split(",") if item.strip()}
    if not left_values and not right_values:
        return "unknown_both"
    if not left_values:
        return "unknown_left"
    if not right_values:
        return "unknown_right"
    if left_values == right_values:
        return "match"
    if left_values & right_values:
        return "partial_overlap"
    return "mismatch"


def _evidence_context_comparisons(
    evidence: list[ProviderEdgeEvidenceRecordV2], experiment: ExperimentalContextV1
) -> list[ContextComparisonRecordV1]:
    records: list[ContextComparisonRecordV1] = []
    for item in evidence:
        for dimension in (
            "organism",
            "cell_type",
            "tissue",
            "compartment",
            "experimental_system",
            "disease_state",
        ):
            evidence_value = getattr(item, dimension)
            experiment_value = getattr(experiment, dimension)
            records.append(
                ContextComparisonRecordV1(
                    comparison_id=f"context-comparison:{item.evidence_id}:{dimension}",
                    evidence_id=item.evidence_id,
                    dimension=dimension,
                    left_context_role="experimental_context",
                    right_context_role="provider_evidence_context",
                    evidence_value=evidence_value,
                    experiment_value=experiment_value,
                    match_state=_context_comparison_state(
                        experiment_value=experiment_value,
                        evidence_value=evidence_value,
                    ),
                )
            )
    return records


def _path_context_summary(
    component_evidence_ids: tuple[str, ...],
    evidence_by_id: dict[str, ProviderEdgeEvidenceRecordV2],
) -> dict[str, Any]:
    dimensions = (
        "organism",
        "cell_type",
        "tissue",
        "compartment",
        "experimental_system",
        "disease_state",
    )
    evidence = [
        evidence_by_id[evidence_id]
        for evidence_id in component_evidence_ids
        if evidence_id in evidence_by_id
    ]
    summary: dict[str, Any] = {
        "shared_known_context": {},
        "conflicting_context_dimensions": [],
        "missing_context_dimensions": [],
        "unresolved_context_dimensions": [],
        "context_supporting_evidence_ids": list(component_evidence_ids),
        "dimensions": {},
    }
    complete = 0
    for dimension in dimensions:
        values = {
            getattr(item, dimension)
            for item in evidence
            if getattr(item, dimension, None) not in {None, ""}
        }
        if len(values) == 1:
            value = next(iter(values))
            summary["shared_known_context"][dimension] = value
            summary["dimensions"][dimension] = {
                "state": "shared_known",
                "value": value,
                "source_record_ids": [
                    item.evidence_id for item in evidence if getattr(item, dimension, None) == value
                ],
            }
            complete += 1
        elif len(values) > 1:
            summary["conflicting_context_dimensions"].append(dimension)
            summary["dimensions"][dimension] = {
                "state": "conflicting",
                "values": sorted(values),
                "source_record_ids": [item.evidence_id for item in evidence],
            }
            complete += 1
        else:
            summary["missing_context_dimensions"].append(dimension)
            summary["dimensions"][dimension] = {
                "state": "unknown",
                "value": None,
                "source_record_ids": [item.evidence_id for item in evidence],
            }
    summary["context_completeness_fraction"] = round(complete / len(dimensions), 6)
    return asdict(
        PathContextSummaryV1(
            context_summary_id="path-context:" + ":".join(component_evidence_ids),
            shared_known_context=summary["shared_known_context"],
            conflicting_context_dimensions=tuple(summary["conflicting_context_dimensions"]),
            missing_context_dimensions=tuple(summary["missing_context_dimensions"]),
            unresolved_context_dimensions=tuple(summary["unresolved_context_dimensions"]),
            context_supporting_evidence_ids=tuple(summary["context_supporting_evidence_ids"]),
            dimensions=summary["dimensions"],
            context_completeness_fraction=summary["context_completeness_fraction"],
        )
    )


def build_mechanistic_runtime_metrics_v2(
    *,
    provider_evidence: list[ProviderEdgeEvidenceRecordV2],
    lineage_groups: list[LineageGroupRecordV2],
    consensus_edges: list[ConsensusMechanisticEdgeRecordV2],
    signed_paths: list[dict[str, Any]],
    unsigned_context_paths: list[dict[str, Any]],
    path_search_results: list[PathSearchResultV1],
    contextual_conflicts: list[Any],
    graphs: dict[str, nx.MultiDiGraph[Any]],
) -> dict[str, Any]:
    status_counts: dict[str, int] = defaultdict(int)
    for result in path_search_results:
        status_counts[result.truncation_status] += 1
    conflict_counts: dict[str, int] = defaultdict(int)
    for conflict in contextual_conflicts:
        conflict_counts[getattr(conflict, "conflict_class", "unknown")] += 1
    signed_edges = [edge for edge in consensus_edges if "signed_causal" in edge.graph_layers]
    unsigned_edges = [
        edge for edge in consensus_edges if "unsigned_functional" in edge.graph_layers
    ]
    contextual_edges = [edge for edge in consensus_edges if "contextual" in edge.graph_layers]
    conflicting_edges = [edge for edge in consensus_edges if "conflicting" in edge.graph_layers]
    unresolved_provider_count = sum(
        1
        for evidence in provider_evidence
        if "unknown" in {evidence.source_entity_type, evidence.target_entity_type}
    )
    duplicate_lineage_count = sum(
        1
        for lineage in lineage_groups
        if lineage.relationship_class
        in {"exact_duplicate", "publication_duplicate", "likely_duplicate"}
    )
    independent_lineage_count = sum(
        1
        for lineage in lineage_groups
        if lineage.relationship_class in {"independent_same_edge", "independent_opposing_edge"}
    )
    unresolved_lineage_count = sum(
        1 for lineage in lineage_groups if lineage.relationship_class == "unresolved"
    )
    unsigned_functional_paths = [
        path for path in unsigned_context_paths if path.get("graph_layer") == "unsigned_functional"
    ]
    contextual_paths = [
        path for path in unsigned_context_paths if path.get("graph_layer") == "contextual"
    ]
    graph_metrics = {
        f"{name}_graph_node_count": graph.number_of_nodes() for name, graph in graphs.items()
    }
    graph_metrics.update(
        {f"{name}_graph_edge_count": graph.number_of_edges() for name, graph in graphs.items()}
    )
    return {
        "provider_evidence_count": len(provider_evidence),
        "resolved_provider_evidence_count": len(provider_evidence) - unresolved_provider_count,
        "unresolved_provider_evidence_count": unresolved_provider_count,
        "lineage_group_count": len(lineage_groups),
        "confirmed_independent_lineage_count": independent_lineage_count,
        "duplicate_lineage_count": duplicate_lineage_count,
        "unresolved_lineage_count": unresolved_lineage_count,
        "consensus_edge_count": len(consensus_edges),
        "signed_consensus_edge_count": len(signed_edges),
        "unsigned_consensus_edge_count": len(unsigned_edges),
        "contextual_consensus_edge_count": len(contextual_edges),
        "conflicting_consensus_edge_count": len(conflicting_edges),
        "supported_relation_count": len(consensus_edges),
        "signed_path_count": len(signed_paths),
        "unsigned_functional_path_count": len(unsigned_functional_paths),
        "contextual_path_count": len(contextual_paths),
        "unsigned_context_path_count": len(unsigned_context_paths),
        "total_canonical_path_count": len(signed_paths) + len(unsigned_context_paths),
        "mechanistic_path_count": len(signed_paths) + len(unsigned_context_paths),
        "path_search_result_count": len(path_search_results),
        "complete_search_count": status_counts["complete"],
        "truncated_search_count": sum(1 for result in path_search_results if result.truncated),
        "maximum_path_length_reached_count": status_counts["maximum_path_length_reached"],
        "maximum_paths_per_candidate_reached_count": status_counts[
            "maximum_paths_per_candidate_reached"
        ],
        "maximum_total_paths_reached_count": status_counts["maximum_total_paths_reached"],
        "source_not_in_graph_count": status_counts["source_not_in_graph"],
        "source_unresolved_count": status_counts["source_unresolved"],
        "candidate_not_in_graph_count": status_counts["candidate_not_in_graph"],
        "no_path_search_count": status_counts["no_path_found"],
        "search_error_count": status_counts["search_error"],
        "truncated_path_search_count": sum(1 for result in path_search_results if result.truncated),
        "contextual_conflict_count": len(contextual_conflicts),
        "global_sign_conflict_count": conflict_counts["global_sign_conflict"],
        "context_specific_conflict_count": conflict_counts["context_specific_conflict"],
        "unresolved_context_conflict_count": conflict_counts["unresolved_context_conflict"],
        "duplicate_access_disagreement_count": conflict_counts["duplicate_access_disagreement"],
        "mapping_related_conflict_count": conflict_counts["mapping_related_conflict"],
        "mechanism_disagreement_count": conflict_counts["mechanism_disagreement"],
        "graph_layer_edge_counts": {
            name: graph.number_of_edges() for name, graph in graphs.items()
        },
        **graph_metrics,
        "canonical_path_source": "v2_semantic_graphs",
    }


def _context_label(context: dict[str, Any]) -> str:
    values = [
        dimension["normalized_value"]
        for dimension in context.values()
        if dimension.get("normalized_value")
    ]
    return "|".join(values)


def _typed_context_key(context: StructuredContextRecordV1) -> str:
    values = [
        dimension.normalized_value
        for dimension in context.dimensions.values()
        if dimension.normalized_value
    ]
    return "|".join(values)


def _provider_snapshot_id(row: dict[str, Any], manifest: dict[str, Any]) -> str:
    explicit = row.get("provider_snapshot_id") or row.get("retrieval_snapshot")
    if explicit:
        return str(explicit)
    snapshots = row.get("retrieval_snapshots", ()) or ()
    if snapshots:
        return str(next(iter(snapshots)))
    provider_name = str(row.get("provider") or row.get("original_provider") or "")
    providers = manifest.get("providers", [])
    if isinstance(providers, list) and providers:
        for provider in providers:
            if isinstance(provider, dict) and provider.get("provider") == provider_name:
                return str(provider.get("snapshot_id", "unknown_provider_snapshot"))
    return "unknown_provider_snapshot"


def _context_token(evidence: ProviderEdgeEvidenceRecordV2) -> str:
    fields = [
        evidence.cell_type,
        evidence.tissue,
        evidence.compartment,
        evidence.experimental_system,
        evidence.disease_state,
    ]
    return "|".join(item for item in fields if item)


def _resolver_snapshot_manifest(resolver: IdentifierResolverV2) -> dict[str, Any]:
    manifest = dict(resolver.manifest)
    manifest.setdefault("snapshot_id", resolver.snapshot_id)
    manifest.setdefault("organism", resolver.organism)
    manifest["ambiguity_policy"] = resolver.ambiguity_policy
    manifest["resolver_version"] = "IdentifierResolverV2"
    return manifest


def _source_identifier(row: dict[str, Any]) -> str:
    return str(row.get("source_identifier") or row.get("source") or "")


def _target_identifier(row: dict[str, Any]) -> str:
    return str(row.get("target_identifier") or row.get("target") or "")


def _entity_type(row: dict[str, Any], side: str) -> str:
    value = row.get(f"{side}_entity_type") or row.get(f"{side}_type") or row.get("entity_type")
    normalized = str(value or "unknown").strip().lower()
    aliases = {
        "family": "protein_family",
        "proteinfamily": "protein_family",
        "definedset": "entity_set",
        "candidateset": "entity_set",
        "openset": "entity_set",
        "simpleentity": "small_molecule",
        "reactionlikeevent": "reaction",
    }
    normalized = aliases.get(normalized, normalized)
    if normalized in {
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
    }:
        return normalized
    return "unknown"


def _first_tuple_value(value: object) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, tuple | list) and value:
        return str(value[0])
    return ""


def _lineage_relationship_class(
    items: list[ProviderEdgeEvidenceRecordV2],
    cluster_items: list[ProviderEdgeEvidenceRecordV2],
) -> str:
    if any(
        item.source_entity_type == "unknown" or item.target_entity_type == "unknown"
        for item in items
    ):
        return "unresolved"
    if len(items) > 1:
        origins = {
            (
                item.original_database,
                item.provider_record_id,
                tuple(sorted(item.references)),
            )
            for item in items
        }
        return "exact_duplicate" if len(origins) == 1 else "likely_duplicate"
    item = items[0]
    same_biology = [
        peer
        for peer in cluster_items
        if peer.evidence_id != item.evidence_id
        and peer.source_entity_id == item.source_entity_id
        and peer.target_entity_id == item.target_entity_id
    ]
    same_relation = [
        peer
        for peer in same_biology
        if peer.source_entity_id == item.source_entity_id
        and peer.target_entity_id == item.target_entity_id
        and peer.relation_type == item.relation_type
    ]
    if any(_same_origin(item, peer) for peer in same_biology):
        return "publication_duplicate" if item.references else "likely_duplicate"
    if any(_opposing_sign(item.sign, peer.sign) for peer in same_relation):
        return "independent_opposing_edge"
    if item.references and any(
        set(item.references) & set(peer.references) for peer in same_relation
    ):
        return "publication_duplicate"
    if not item.provider_record_id and any(
        peer.original_database == item.original_database for peer in same_relation
    ):
        return "likely_duplicate"
    return "independent_same_edge"


def _same_origin(left: ProviderEdgeEvidenceRecordV2, right: ProviderEdgeEvidenceRecordV2) -> bool:
    if left.original_database != right.original_database:
        return False
    if left.provider_record_id and left.provider_record_id == right.provider_record_id:
        return True
    return bool(left.references and set(left.references) & set(right.references))


def _broad_relation_class(evidence: ProviderEdgeEvidenceRecordV2) -> str:
    if evidence.functional_only:
        return "functional"
    if evidence.contextual_only:
        return "contextual"
    if evidence.relation_type in {"regulates", "regulation", "interaction"}:
        return "regulatory"
    return evidence.relation_type


def _lineage_confidence(relationship_class: str) -> float:
    return {
        "exact_duplicate": 0.6,
        "publication_duplicate": 0.7,
        "likely_duplicate": 0.5,
        "independent_same_edge": 1.0,
        "independent_opposing_edge": 1.0,
        "unresolved": 0.25,
    }.get(relationship_class, 0.25)


def _opposing_sign(left: str, right: str) -> bool:
    return {left, right} == {"positive", "negative"}


def _contexts_by_path(
    paths: list[dict[str, Any]],
    consensus_edges: list[ConsensusMechanisticEdgeRecordV2],
    provider_evidence: list[ProviderEdgeEvidenceRecordV2],
) -> dict[str, tuple[str, ...]]:
    provider_to_consensus = {
        evidence_id: edge.consensus_edge_id
        for edge in consensus_edges
        for evidence_id in edge.component_evidence_ids
    }
    evidence_by_id = {item.evidence_id: item for item in provider_evidence}
    contexts_by_consensus = {
        edge.consensus_edge_id: tuple(
            sorted(
                {
                    token
                    for evidence_id in edge.component_evidence_ids
                    if evidence_id in evidence_by_id
                    if (
                        token := _typed_context_key(
                            _structured_context_record(evidence_by_id[evidence_id])
                        )
                    )
                }
            )
        )
        for edge in consensus_edges
    }
    contexts: dict[str, tuple[str, ...]] = {}
    for path in paths:
        path_id = str(path.get("path_id", ""))
        consensus_ids = tuple(
            str(edge_id) for edge_id in path.get("ordered_consensus_edge_ids", ()) or ()
        )
        if not consensus_ids:
            edge_ids = tuple(str(edge_id) for edge_id in path.get("ordered_edge_ids", ()) or ())
            consensus_ids = tuple(
                provider_to_consensus.get(edge_id, edge_id) for edge_id in edge_ids
            )
        contexts[path_id] = tuple(
            sorted(
                {ctx for edge_id in consensus_ids for ctx in contexts_by_consensus.get(edge_id, ())}
            )
        )
    return contexts


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    text = str(value)
    return text if text else None


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
