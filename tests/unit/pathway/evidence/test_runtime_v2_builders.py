from __future__ import annotations

from pathlib import Path

import pytest

from sirna_offtarget.identifiers.resolver_v2 import IdentifierResolverV2
from sirna_offtarget.identifiers.snapshots import write_identifier_snapshot
from sirna_offtarget.pathway.entities import BiologicalEntityRegistryV2
from sirna_offtarget.pathway.evidence.runtime_v2 import (
    _broad_relation_class,
    _entity_type,
    _first_tuple_value,
    _level_from_score,
    _provider_snapshot_id,
    _split_paths_by_graph_layer,
    build_consensus_edges_v2,
    build_contextual_conflicts_v2,
    build_graph_layers_v2,
    build_lineage_groups_v2,
    build_mechanistic_network_payload_v2,
    build_path_confidence_records_v2,
    build_provider_edge_evidence_v2,
    calculate_runtime_evidence_quality_v2,
)
from sirna_offtarget.pathway.semantics import ProviderEdgeEvidenceRecordV2


@pytest.fixture()
def resolver(tmp_path: Path) -> IdentifierResolverV2:
    snapshot = write_identifier_snapshot(tmp_path, "human")
    return IdentifierResolverV2(snapshot, "human")


def _edge(edge_id: str, sign: str = "positive", refs: tuple[str, ...] = ("PMID:1",)):
    return {
        "edge_id": edge_id,
        "source": "TARGET1",
        "target": "GENEA",
        "directed": True,
        "sign": sign,
        "relation_type": "regulates",
        "mechanism": "transcriptional_regulation",
        "provider": "signor",
        "original_sources": ("SIGNOR",),
        "references": refs,
        "organism": "human",
        "evidence_level": "curated",
        "predicted_only": False,
        "functional_only": sign == "unsigned",
        "causal_eligible": sign != "unsigned",
        "database_versions": ("signor-v1",),
        "retrieval_snapshots": ("snapshot-signor",),
        "lineage_key": "SIGNOR:R1",
        "warnings": (),
    }


def test_runtime_builder_removes_runtime_symbol_view_and_populates_quality(
    resolver: IdentifierResolverV2,
) -> None:
    payload = build_mechanistic_network_payload_v2(
        raw_provider_evidence_rows=[_edge("e1", refs=())],
        legacy_trace_paths=[
            {
                "path_id": "path_GENEA_001",
                "candidate": "GENEA",
                "ordered_edge_ids": ("e1",),
                "ordered_nodes": ("TARGET1", "GENEA"),
                "path_length": 1,
                "directed": True,
                "fully_signed": True,
                "composed_sign": "positive",
            }
        ],
        legacy_trace_edges=[],
        provider_snapshot_manifest={"providers": [{"snapshot_id": "snapshot-signor"}]},
        organism="human",
        identifier_resolver=resolver,
    )

    serialized = str(payload)
    assert "runtime_symbol_view" not in serialized
    assert payload["biological_entities"]
    assert payload["evidence_quality"][0]["missing_components"]
    assert (
        payload["path_confidence_records"][0]["capped_score"]
        <= payload["path_confidence_records"][0]["minimum_edge_quality_score"]
    )


def test_runtime_builder_requires_raw_provider_evidence(
    resolver: IdentifierResolverV2,
) -> None:
    with pytest.raises(RuntimeError, match="missing_canonical_provider_evidence"):
        build_mechanistic_network_payload_v2(
            raw_provider_evidence_rows=[],
            legacy_trace_paths=[
                {
                    "path_id": "legacy-path",
                    "candidate": "GENEA",
                    "ordered_edge_ids": ("legacy-edge",),
                }
            ],
            legacy_trace_edges=[{"edge_id": "legacy-edge"}],
            provider_snapshot_manifest={"providers": [{"snapshot_id": "legacy"}]},
            organism="human",
            identifier_resolver=resolver,
        )


def test_path_search_policy_records_disabled_unsigned_search(
    resolver: IdentifierResolverV2,
) -> None:
    payload = build_mechanistic_network_payload_v2(
        raw_provider_evidence_rows=[{**_edge("unsigned", "unsigned"), "target": "GENEB"}],
        legacy_trace_paths=[],
        legacy_trace_edges=[],
        provider_snapshot_manifest={"providers": [{"snapshot_id": "snapshot-signor"}]},
        organism="human",
        identifier_resolver=resolver,
        trace_signed_paths=False,
        trace_unsigned_paths=False,
        trace_contextual_paths=False,
        created_from_config_fingerprint="fingerprint",
    )

    statuses = {row["truncation_status"] for row in payload["path_search_results"]}
    assert statuses == {"search_disabled"}
    assert payload["path_search_policy"]["created_from_config_fingerprint"] == "fingerprint"
    assert payload["metrics"]["mechanistic_path_count"] == 0
    assert payload["migration_diagnostics"]["provider_evidence_input"] == "raw_provider_evidence"


def test_paths_and_search_results_are_bidirectionally_linked(
    resolver: IdentifierResolverV2,
) -> None:
    payload = build_mechanistic_network_payload_v2(
        raw_provider_evidence_rows=[_edge("linked", "positive")],
        legacy_trace_paths=[],
        legacy_trace_edges=[],
        provider_snapshot_manifest={"providers": [{"snapshot_id": "snapshot-signor"}]},
        organism="human",
        identifier_resolver=resolver,
    )

    paths = [*payload["signed_paths"], *payload["unsigned_context_paths"]]
    results = {row["search_result_id"]: row for row in payload["path_search_results"]}
    assert paths
    for path in paths:
        parent = results[path["search_result_id"]]
        assert path["path_id"] in parent["retained_path_ids"]
        assert parent["source_entity_id"] == path["source_entity_id"]
        assert parent["target_entity_id"] == path["target_entity_id"]
        assert parent["graph_layer"] == path["graph_layer"]
        assert "truncation_status" not in path


def test_requested_source_is_not_replaced_by_graph_root(
    resolver: IdentifierResolverV2,
) -> None:
    payload = build_mechanistic_network_payload_v2(
        raw_provider_evidence_rows=[{**_edge("other", "positive"), "source": "OTHER"}],
        legacy_trace_paths=[],
        legacy_trace_edges=[],
        provider_snapshot_manifest={"providers": [{"snapshot_id": "snapshot-signor"}]},
        organism="human",
        identifier_resolver=resolver,
        path_search_source_symbols=["TARGET1"],
    )

    assert payload["signed_paths"] == []
    assert {row["truncation_status"] for row in payload["path_search_results"]} >= {
        "source_unresolved"
    }


def test_candidate_scope_limits_targets_and_reports_absent_candidate(
    resolver: IdentifierResolverV2,
) -> None:
    broad = build_mechanistic_network_payload_v2(
        raw_provider_evidence_rows=[
            _edge("a", "positive"),
            {**_edge("b", "positive"), "target": "GENEB"},
        ],
        legacy_trace_paths=[],
        legacy_trace_edges=[],
        provider_snapshot_manifest={"providers": [{"snapshot_id": "snapshot-signor"}]},
        organism="human",
        identifier_resolver=resolver,
    )
    genea_id = next(
        row["entity_id"] for row in broad["biological_entities"] if row["display_name"] == "GENEA"
    )
    scoped = build_mechanistic_network_payload_v2(
        raw_provider_evidence_rows=[
            _edge("a", "positive"),
            {**_edge("b", "positive"), "target": "GENEB"},
        ],
        legacy_trace_paths=[],
        legacy_trace_edges=[],
        provider_snapshot_manifest={"providers": [{"snapshot_id": "snapshot-signor"}]},
        organism="human",
        identifier_resolver=resolver,
        candidate_entity_ids=(genea_id, "gene:not-in-graph"),
    )

    assert {path["candidate"] for path in scoped["signed_paths"]} == {"GENEA"}
    assert any(
        row["truncation_status"] == "candidate_not_in_graph"
        for row in scoped["path_search_results"]
    )


def test_shortest_paths_only_changes_retained_paths(
    resolver: IdentifierResolverV2,
) -> None:
    rows = [
        {**_edge("direct", "positive"), "target": "GENEA", "lineage_key": "SIGNOR:R1"},
        {**_edge("via-b", "positive"), "target": "GENEB", "lineage_key": "SIGNOR:R2"},
        {
            **_edge("b-to-a", "positive"),
            "source": "GENEB",
            "target": "GENEA",
            "lineage_key": "SIGNOR:R3",
        },
    ]
    all_paths = build_mechanistic_network_payload_v2(
        raw_provider_evidence_rows=rows,
        legacy_trace_paths=[],
        legacy_trace_edges=[],
        provider_snapshot_manifest={"providers": [{"snapshot_id": "snapshot-signor"}]},
        organism="human",
        identifier_resolver=resolver,
        shortest_paths_only=False,
    )
    shortest = build_mechanistic_network_payload_v2(
        raw_provider_evidence_rows=rows,
        legacy_trace_paths=[],
        legacy_trace_edges=[],
        provider_snapshot_manifest={"providers": [{"snapshot_id": "snapshot-signor"}]},
        organism="human",
        identifier_resolver=resolver,
        shortest_paths_only=True,
    )

    all_genea_lengths = sorted(
        path["path_length"] for path in all_paths["signed_paths"] if path["candidate"] == "GENEA"
    )
    shortest_genea_lengths = sorted(
        path["path_length"] for path in shortest["signed_paths"] if path["candidate"] == "GENEA"
    )
    assert all_genea_lengths == [1, 2]
    assert shortest_genea_lengths == [1]


def test_path_search_records_candidate_and_total_truncation(
    resolver: IdentifierResolverV2,
) -> None:
    rows = [
        {**_edge("direct", "positive"), "target": "GENEA", "lineage_key": "SIGNOR:R1"},
        {**_edge("via-b", "positive"), "target": "GENEB", "lineage_key": "SIGNOR:R2"},
        {
            **_edge("b-to-a", "positive"),
            "source": "GENEB",
            "target": "GENEA",
            "lineage_key": "SIGNOR:R3",
        },
    ]
    candidate_limited = build_mechanistic_network_payload_v2(
        raw_provider_evidence_rows=rows,
        legacy_trace_paths=[],
        legacy_trace_edges=[],
        provider_snapshot_manifest={"providers": [{"snapshot_id": "snapshot-signor"}]},
        organism="human",
        identifier_resolver=resolver,
        maximum_paths_per_candidate=1,
    )
    assert any(
        row["truncation_status"] == "maximum_paths_per_candidate_reached"
        for row in candidate_limited["path_search_results"]
    )

    total_limited = build_mechanistic_network_payload_v2(
        raw_provider_evidence_rows=rows,
        legacy_trace_paths=[],
        legacy_trace_edges=[],
        provider_snapshot_manifest={"providers": [{"snapshot_id": "snapshot-signor"}]},
        organism="human",
        identifier_resolver=resolver,
        maximum_total_paths=1,
    )
    assert total_limited["metrics"]["mechanistic_path_count"] == 1
    assert total_limited["metrics"]["truncated_path_search_count"] >= 1


def test_path_search_records_no_path_and_maximum_depth(
    resolver: IdentifierResolverV2,
) -> None:
    payload = build_mechanistic_network_payload_v2(
        raw_provider_evidence_rows=[
            {**_edge("a", "positive"), "target": "GENEA", "lineage_key": "SIGNOR:R1"},
            {
                **_edge("a-c", "positive"),
                "source": "GENEA",
                "target": "GENEC",
                "lineage_key": "SIGNOR:R2",
            },
            {
                **_edge("c-d", "positive"),
                "source": "GENEC",
                "target": "GENED",
                "lineage_key": "SIGNOR:R4",
            },
            {
                **_edge("other-b", "positive"),
                "source": "OTHER",
                "target": "GENEB",
                "lineage_key": "SIGNOR:R3",
            },
        ],
        legacy_trace_paths=[],
        legacy_trace_edges=[],
        provider_snapshot_manifest={"providers": [{"snapshot_id": "snapshot-signor"}]},
        organism="human",
        identifier_resolver=resolver,
        path_search_source_symbols=["TARGET1"],
        max_path_length=2,
    )

    statuses = {row["truncation_status"] for row in payload["path_search_results"]}
    assert "no_path_found" in statuses
    assert "maximum_path_length_reached" in statuses


def test_experimental_context_quality_and_comparison_states(
    resolver: IdentifierResolverV2,
) -> None:
    payload = build_mechanistic_network_payload_v2(
        raw_provider_evidence_rows=[
            {
                **_edge("contextualized", "positive"),
                "cell_type": "HeLa",
                "tissue": "liver",
                "experimental_system": "lipid_transfection",
            }
        ],
        legacy_trace_paths=[],
        legacy_trace_edges=[],
        provider_snapshot_manifest={"providers": [{"snapshot_id": "snapshot-signor"}]},
        organism="human",
        identifier_resolver=resolver,
        experiment_context={
            "organism": "human",
            "cell_type": "HeLa",
            "tissue": "kidney",
            "experimental_system": "lipid_transfection",
        },
    )

    quality = payload["evidence_quality"][0]
    comparison_states = {
        row["dimension"]: row["match_state"] for row in payload["evidence_context_comparisons"]
    }
    assert quality["cell_type_match"] is True
    assert quality["tissue_match"] is False
    assert comparison_states["cell_type"] == "match"
    assert comparison_states["tissue"] == "mismatch"
    assert comparison_states["disease_state"] == "unknown_both"
    assert (
        payload["structured_contexts"][0]["dimensions"]["cell_type"]["missing_status"] == "present"
    )


def test_lineage_groups_duplicate_provider_records_together(
    resolver: IdentifierResolverV2,
) -> None:
    registry = BiologicalEntityRegistryV2("human", "snapshot-1")
    resolutions = {}
    evidence = [
        build_provider_edge_evidence_v2(
            _edge("e1"),
            registry=registry,
            resolutions=resolutions,
            organism="human",
            identifier_resolver=resolver,
            identifier_snapshot_id="snapshot-1",
            provider_snapshot_id="provider-snapshot",
        ),
        build_provider_edge_evidence_v2(
            _edge("e1"),
            registry=registry,
            resolutions=resolutions,
            organism="human",
            identifier_resolver=resolver,
            identifier_snapshot_id="snapshot-1",
            provider_snapshot_id="provider-snapshot",
        ),
    ]
    lineages = build_lineage_groups_v2(evidence)
    assert len(lineages) == 1
    assert lineages[0].relationship_class == "exact_duplicate"


def test_consensus_layers_split_conflicting_and_unsigned_edges(
    resolver: IdentifierResolverV2,
) -> None:
    payload = build_mechanistic_network_payload_v2(
        raw_provider_evidence_rows=[
            _edge("positive", "positive"),
            {**_edge("negative", "negative"), "provider": "reactome"},
            {**_edge("unsigned", "unsigned"), "target": "GENEB", "directed": False},
        ],
        legacy_trace_paths=[
            {
                "path_id": "path_GENEA_pos",
                "candidate": "GENEA",
                "ordered_edge_ids": ("positive",),
                "ordered_nodes": ("TARGET1", "GENEA"),
                "path_length": 1,
                "directed": True,
                "fully_signed": True,
                "composed_sign": "positive",
            },
            {
                "path_id": "path_GENEA_neg",
                "candidate": "GENEA",
                "ordered_edge_ids": ("negative",),
                "ordered_nodes": ("TARGET1", "GENEA"),
                "path_length": 1,
                "directed": True,
                "fully_signed": True,
                "composed_sign": "negative",
            },
            {
                "path_id": "path_GENEB_unsigned",
                "candidate": "GENEB",
                "ordered_edge_ids": ("unsigned",),
                "ordered_nodes": ("TARGET1", "GENEB"),
                "path_length": 1,
                "directed": False,
                "fully_signed": False,
                "composed_sign": "unknown",
            },
        ],
        legacy_trace_edges=[],
        provider_snapshot_manifest={"providers": [{"snapshot_id": "snapshot-signor"}]},
        organism="human",
        identifier_resolver=resolver,
        identifier_snapshot_manifest={"snapshot_id": "verified-snapshot"},
        warnings=["fixture warning"],
    )

    assert payload["warnings"] == ["fixture warning"]
    assert payload["identifier_snapshot_manifest"]["snapshot_id"] == "verified-snapshot"
    assert payload["graph_layer_summary"]["conflicting"] == 1
    assert payload["graph_layer_summary"]["unsigned_functional"] == 1
    assert payload["contextual_conflicts"][0]["candidate_entity_id"] == "GENEA"
    assert payload["unsigned_context_paths"][0]["graph_layer"] == "unsigned_functional"


def test_quality_caps_predicted_low_mapping_and_unsupported_entities(
    resolver: IdentifierResolverV2,
) -> None:
    registry = BiologicalEntityRegistryV2("human", "snapshot-1")
    resolutions = {}
    evidence = build_provider_edge_evidence_v2(
        {
            **_edge("predicted", refs=()),
            "directed": False,
            "predicted_only": True,
            "functional_only": True,
            "source": "",
            "warnings": ("missing source",),
        },
        registry=registry,
        resolutions=resolutions,
        organism="human",
        identifier_resolver=resolver,
        identifier_snapshot_id="snapshot-1",
        provider_snapshot_id="provider-snapshot",
    )
    lineage = build_lineage_groups_v2([evidence])
    quality = calculate_runtime_evidence_quality_v2(
        evidence,
        lineage_groups=lineage,
        source_resolution=None,
        target_resolution=None,
        experiment_organism="mouse",
    )

    assert quality.capped_score <= 0.35
    assert "functional_only_contextual_cap" in quality.cap_reasons
    assert "missing_direction_or_sign_low_cap" in quality.cap_reasons
    assert "predicted_only_not_high_cap" in quality.cap_reasons
    assert "low_mapping_confidence_cap" in quality.cap_reasons
    assert quality.organism_match is False
    assert quality.predicted_only_penalty == 0.3


def test_graph_layer_and_path_helpers_handle_empty_and_contextual_cases(
    resolver: IdentifierResolverV2,
) -> None:
    registry = BiologicalEntityRegistryV2("human", "snapshot-1")
    resolutions = {}
    evidence = [
        build_provider_edge_evidence_v2(
            {**_edge("e1", "positive"), "cell_type": "HeLa", "compartment": "nucleus"},
            registry=registry,
            resolutions=resolutions,
            organism="human",
            identifier_resolver=resolver,
            identifier_snapshot_id="snapshot-1",
            provider_snapshot_id="provider-snapshot",
        )
    ]
    lineages = build_lineage_groups_v2(evidence)
    quality = {
        item.evidence_id: calculate_runtime_evidence_quality_v2(
            item,
            lineage_groups=lineages,
            source_resolution=resolutions[item.source_entity_id],
            target_resolution=resolutions[item.target_entity_id],
            experiment_organism="human",
        )
        for item in evidence
    }
    consensus = build_consensus_edges_v2(evidence, lineages, quality)
    graphs = build_graph_layers_v2(
        provider_evidence=evidence,
        consensus_edges=consensus,
        lineage_groups=lineages,
        quality_by_evidence_id=quality,
        resolutions=resolutions,
    )
    records = build_path_confidence_records_v2(
        paths=[
            {
                "path_id": "empty",
                "ordered_edge_ids": (),
            },
            {
                "path_id": "fallback",
                "ordered_edge_ids": ("e1",),
                "path_length": 1,
                "directed": False,
                "fully_signed": False,
            },
        ],
        consensus_edges=consensus,
        quality_by_evidence_id=quality,
        provider_evidence=evidence,
        lineage_groups=lineages,
        resolutions=resolutions,
    )
    conflicts = build_contextual_conflicts_v2(
        paths=[],
        confidence_records=records,
        consensus_edges=consensus,
        provider_evidence=evidence,
    )

    assert graphs["signed_causal"].number_of_edges() == 1
    assert [record.path_id for record in records] == ["fallback"]
    assert records[0].confidence_level == "low"
    assert conflicts == []


def test_legacy_path_splitter_is_diagnostic_only_and_maps_aliases(
    resolver: IdentifierResolverV2,
) -> None:
    registry = BiologicalEntityRegistryV2("human", "snapshot-1")
    resolutions = {}
    evidence = [
        build_provider_edge_evidence_v2(
            _edge("signed", "positive"),
            registry=registry,
            resolutions=resolutions,
            organism="human",
            identifier_resolver=resolver,
            identifier_snapshot_id="snapshot-1",
            provider_snapshot_id="provider-snapshot",
        ),
        build_provider_edge_evidence_v2(
            {**_edge("unsigned", "unsigned"), "target": "GENEB"},
            registry=registry,
            resolutions=resolutions,
            organism="human",
            identifier_resolver=resolver,
            identifier_snapshot_id="snapshot-1",
            provider_snapshot_id="provider-snapshot",
        ),
    ]
    lineages = build_lineage_groups_v2(evidence)
    quality = {
        item.evidence_id: calculate_runtime_evidence_quality_v2(
            item,
            lineage_groups=lineages,
            source_resolution=resolutions[item.source_entity_id],
            target_resolution=resolutions[item.target_entity_id],
            experiment_organism="human",
        )
        for item in evidence
    }
    consensus = build_consensus_edges_v2(evidence, lineages, quality)

    signed, unsigned = _split_paths_by_graph_layer(
        [
            {
                "path_id": "signed",
                "ordered_edge_ids": ("legacy-signed",),
                "ordered_nodes": ("TARGET1", "GENEA"),
                "fully_signed": True,
            },
            {
                "path_id": "unsigned",
                "ordered_edge_ids": ("unsigned",),
                "ordered_nodes": ("TARGET1", "GENEB"),
                "fully_signed": False,
            },
            {"path_id": "unmapped", "ordered_edge_ids": ("missing",), "fully_signed": True},
        ],
        consensus,
        provider_evidence=evidence,
        legacy_trace_edges=[
            {
                "edge_id": "legacy-signed",
                "source": "TARGET1",
                "target": "GENEA",
                "sign": "positive",
            },
            {"source": "TARGET1", "target": "GENEA", "sign": "positive"},
        ],
    )

    assert signed[0]["graph_layer"] == "signed_causal"
    assert signed[0]["ordered_consensus_edge_ids"]
    assert unsigned[0]["graph_layer"] == "unsigned_functional_or_contextual"
    assert unsigned[1]["ordered_consensus_edge_ids"] == []


def test_conflict_records_include_path_level_and_consensus_level_context(
    resolver: IdentifierResolverV2,
) -> None:
    payload = build_mechanistic_network_payload_v2(
        raw_provider_evidence_rows=[
            {**_edge("pos", "positive"), "cell_type": "HeLa", "lineage_key": "SIGNOR:R1"},
            {
                **_edge("neg", "negative"),
                "cell_type": "A549",
                "provider": "reactome",
                "lineage_key": "REACTOME:R2",
            },
            {
                **_edge("pos-b", "positive"),
                "target": "GENEB",
                "lineage_key": "SIGNOR:R3",
            },
            {
                **_edge("neg-b", "negative"),
                "target": "GENEB",
                "provider": "reactome",
                "lineage_key": "REACTOME:R4",
            },
        ],
        legacy_trace_paths=[],
        legacy_trace_edges=[],
        provider_snapshot_manifest={"providers": [{"snapshot_id": "snapshot-signor"}]},
        organism="human",
        identifier_resolver=resolver,
    )

    conflicts = payload["contextual_conflicts"]
    assert conflicts
    assert any(conflict["positive_path_ids"] for conflict in conflicts)
    assert {conflict["conflict_class"] for conflict in conflicts} == {
        "context_specific_conflict",
        "global_sign_conflict",
    }
    assert any(conflict["positive_contexts"] for conflict in conflicts)
    assert all(conflict["warnings"] for conflict in conflicts)


def test_lineage_relationship_classes_cover_duplicates_and_conflicts(
    resolver: IdentifierResolverV2,
) -> None:
    registry = BiologicalEntityRegistryV2("human", resolver.snapshot_id)
    resolutions = {}

    publication_a = build_provider_edge_evidence_v2(
        {**_edge("pub-a", refs=("PMID:shared",)), "target": "MODULE_A"},
        registry=registry,
        resolutions=resolutions,
        organism="human",
        identifier_resolver=resolver,
        identifier_snapshot_id=resolver.snapshot_id,
        provider_snapshot_id="snapshot-a",
    )
    publication_b = build_provider_edge_evidence_v2(
        {
            **_edge("pub-b", refs=("PMID:shared",)),
            "target": "MODULE_A",
            "lineage_key": "SIGNOR:R2",
        },
        registry=registry,
        resolutions=resolutions,
        organism="human",
        identifier_resolver=resolver,
        identifier_snapshot_id=resolver.snapshot_id,
        provider_snapshot_id="snapshot-b",
    )
    opposing = build_provider_edge_evidence_v2(
        {**_edge("opp", sign="negative"), "lineage_key": "SIGNOR:R3"},
        registry=registry,
        resolutions=resolutions,
        organism="human",
        identifier_resolver=resolver,
        identifier_snapshot_id=resolver.snapshot_id,
        provider_snapshot_id="snapshot-c",
    )
    opposing_positive = build_provider_edge_evidence_v2(
        {**_edge("opp-pos", refs=()), "lineage_key": "SIGNOR:R4"},
        registry=registry,
        resolutions=resolutions,
        organism="human",
        identifier_resolver=resolver,
        identifier_snapshot_id=resolver.snapshot_id,
        provider_snapshot_id="snapshot-c2",
    )
    likely_a = _without_provider_record(
        build_provider_edge_evidence_v2(
            {**_edge("likely-a", refs=()), "target": "GENEB", "lineage_key": "reactome"},
            registry=registry,
            resolutions=resolutions,
            organism="human",
            identifier_resolver=resolver,
            identifier_snapshot_id=resolver.snapshot_id,
            provider_snapshot_id="snapshot-d",
        )
    )
    likely_b = _without_provider_record(
        build_provider_edge_evidence_v2(
            {**_edge("likely-b", refs=()), "target": "GENEB", "lineage_key": "reactome"},
            registry=registry,
            resolutions=resolutions,
            organism="human",
            identifier_resolver=resolver,
            identifier_snapshot_id=resolver.snapshot_id,
            provider_snapshot_id="snapshot-e",
        )
    )
    unresolved = build_provider_edge_evidence_v2(
        {**_edge("unresolved"), "target": "NOT_A_GENE"},
        registry=registry,
        resolutions=resolutions,
        organism="human",
        identifier_resolver=resolver,
        identifier_snapshot_id=resolver.snapshot_id,
        provider_snapshot_id="snapshot-f",
    )

    classes = {
        lineage.relationship_class
        for lineage in build_lineage_groups_v2(
            [
                publication_a,
                publication_b,
                opposing,
                opposing_positive,
                likely_a,
                likely_b,
                unresolved,
            ]
        )
    }

    assert "publication_duplicate" in classes
    assert "independent_opposing_edge" in classes
    assert "likely_duplicate" in classes
    assert "unresolved" in classes


def test_non_gene_entity_type_is_preserved_and_contextual_graph_populates(
    resolver: IdentifierResolverV2,
) -> None:
    payload = build_mechanistic_network_payload_v2(
        raw_provider_evidence_rows=[
            {
                **_edge("ctx", "unsigned"),
                "source": "Reactome:Complex1",
                "source_entity_type": "complex",
                "target": "CHEBI:1",
                "target_entity_type": "small_molecule",
                "relation_type": "complex_membership",
                "contextual_only": True,
                "cell_type": "HeLa",
            }
        ],
        legacy_trace_paths=[
            {
                "path_id": "contextual-path",
                "candidate": "CHEBI:1",
                "ordered_edge_ids": ("ctx",),
                "path_length": 1,
                "directed": False,
                "fully_signed": False,
                "composed_sign": "unknown",
            }
        ],
        legacy_trace_edges=[],
        provider_snapshot_manifest={"providers": [{"snapshot_id": "snapshot-context"}]},
        organism="human",
        identifier_resolver=resolver,
    )

    entity_types = {row["entity_type"] for row in payload["biological_entities"]}
    assert {"complex", "small_molecule"} <= entity_types
    assert payload["graph_layer_summary"]["contextual"] == 1
    assert payload["graph_layer_summary"]["provider_evidence"] == 1
    assert payload["path_confidence_records"][0]["unsupported_entity_count"] == 0


def test_runtime_private_normalization_helpers_cover_fallback_branches(
    resolver: IdentifierResolverV2,
) -> None:
    registry = BiologicalEntityRegistryV2("human", "snapshot-1")
    resolutions = {}
    unknown = build_provider_edge_evidence_v2(
        {
            **_edge("unknown", refs=()),
            "source": "",
            "source_entity_type": "mystery",
            "target": "GENEA",
            "predicted_only": True,
            "predicted": True,
            "directed": False,
            "functional_only": True,
            "relation_type": "complex_membership",
        },
        registry=registry,
        resolutions=resolutions,
        organism="human",
        identifier_resolver=resolver,
        identifier_snapshot_id="snapshot-1",
        provider_snapshot_id="provider-snapshot",
    )

    assert _entity_type({"source_entity_type": "protein"}, "source") == "protein"
    assert _entity_type({"source_type": "bad"}, "source") == "unknown"
    assert _first_tuple_value("x") == "x"
    assert _first_tuple_value(["x", "y"]) == "x"
    assert _first_tuple_value(()) == ""
    assert (
        _provider_snapshot_id(
            {"provider": "signor"},
            {"providers": [{"provider": "signor", "snapshot_id": "snap"}]},
        )
        == "snap"
    )
    assert _provider_snapshot_id({"provider_snapshot_id": "explicit"}, {}) == "explicit"
    assert _provider_snapshot_id({"retrieval_snapshot": "retrieved"}, {}) == "retrieved"
    assert _provider_snapshot_id({"retrieval_snapshots": ("first", "second")}, {}) == "first"
    assert _provider_snapshot_id({"provider": "missing"}, {"providers": []}) == (
        "unknown_provider_snapshot"
    )
    assert _broad_relation_class(unknown) == "functional"
    assert _level_from_score(0.81) == "high"
    assert _level_from_score(0.61) == "moderate"
    assert _level_from_score(0.41) == "low"
    assert _level_from_score(0.26) == "contextual"
    assert _level_from_score(0.1) == "insufficient"


def _without_provider_record(
    evidence: ProviderEdgeEvidenceRecordV2,
) -> ProviderEdgeEvidenceRecordV2:
    from dataclasses import replace

    return replace(evidence, provider_record_id="")
