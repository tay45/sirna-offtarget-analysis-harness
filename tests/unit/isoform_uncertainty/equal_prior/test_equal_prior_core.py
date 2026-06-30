from __future__ import annotations

import math

from sirna_offtarget.isoform_uncertainty.core import assign_isoform_uncertainty_for_gene
from tests.unit.isoform_uncertainty.conftest import tx


def _assign(records, snapshot, policy):
    return assign_isoform_uncertainty_for_gene(
        source_expression_v2_record_id="expr-r1",
        original_gene_id="TP53",
        canonical_gene_id="HGNC:11998",
        approved_symbol="TP53",
        organism="human",
        assembly="GRCh38",
        annotation_snapshot=snapshot,
        annotation_records=records,
        policy=policy,
    )


def test_zero_transcripts_produces_no_weights(snapshot, policy) -> None:
    gene, weights, exclusions = _assign([], snapshot, policy)
    assert gene.eligible_transcript_count == 0
    assert gene.isoform_resolution_status == "no_eligible_transcripts"
    assert weights == []
    assert exclusions == []


def test_single_transcript_weight_is_one(snapshot, policy) -> None:
    gene, weights, _ = _assign([tx("ENST1")], snapshot, policy)
    assert gene.isoform_resolution_status == "single_eligible_transcript"
    assert weights[0].weight == 1.0
    assert weights[0].weight_type == "equal_prior"


def test_two_transcripts_receive_equal_weights(snapshot, policy) -> None:
    gene, weights, _ = _assign([tx("ENST2"), tx("ENST1")], snapshot, policy)
    assert gene.isoform_resolution_status == "multiple_transcripts_equal_prior"
    assert [item.weight for item in weights] == [0.5, 0.5]


def test_many_transcripts_receive_equal_weights_and_sum_to_one(snapshot, policy) -> None:
    gene, weights, _ = _assign([tx("ENST1"), tx("ENST2"), tx("ENST3")], snapshot, policy)
    assert gene.eligible_transcript_count == 3
    assert math.isclose(sum(item.weight or 0 for item in weights), 1.0)
    assert {round(item.weight or 0, 6) for item in weights} == {0.333333}


def test_equal_prior_is_labeled_assumption(snapshot, policy) -> None:
    _gene, weights, _ = _assign([tx("ENST1"), tx("ENST2")], snapshot, policy)
    assert {item.weight_evidence_status for item in weights} == {
        "assumption_due_to_unresolved_isoform_abundance"
    }
    assert "measured" not in weights[0].weight_source


def test_equal_prior_does_not_create_transcript_effects(snapshot, policy) -> None:
    gene, weights, _ = _assign([tx("ENST1")], snapshot, policy)
    payload = gene.model_dump_json() + weights[0].model_dump_json()
    assert "log2_fold_change" not in payload
    assert "p_value" not in payload
    assert "knockdown" not in payload


def test_deterministic_weight_record_ids_and_order(snapshot, policy) -> None:
    _gene1, weights1, _ = _assign([tx("ENST2"), tx("ENST1")], snapshot, policy)
    _gene2, weights2, _ = _assign([tx("ENST1"), tx("ENST2")], snapshot, policy)
    assert [item.record_id for item in weights1] == [item.record_id for item in weights2]
    assert [item.canonical_transcript_id for item in weights1] == ["ENST1", "ENST2"]


def test_numerical_tolerance(snapshot, policy) -> None:
    gene, _weights, _ = assign_isoform_uncertainty_for_gene(
        source_expression_v2_record_id="expr-r1",
        original_gene_id="TP53",
        canonical_gene_id="HGNC:11998",
        approved_symbol="TP53",
        organism="human",
        assembly="GRCh38",
        annotation_snapshot=snapshot,
        annotation_records=[tx("ENST1"), tx("ENST2"), tx("ENST3")],
        policy=policy,
        tolerance=1e-12,
    )
    assert math.isclose(gene.weight_sum or 0, 1.0, abs_tol=1e-12)
