from __future__ import annotations

import inspect

from sirna_offtarget.contracts.stage_results import ExpressionAnalysisResultV2
from sirna_offtarget.execution import stages
from sirna_offtarget.expression.downstream import IsoformGeneEffectInputV1
from sirna_offtarget.isoform import analyze_isoforms_from_gene_effect_inputs
from sirna_offtarget.models import (
    BindingSiteEvidence,
    EvidenceMetric,
    GeneSequenceEvidence,
    TranscriptRecord,
    TranscriptSequenceEvidence,
)


def test_isoform_stage_accepts_expression_v2_dependency() -> None:
    source = inspect.getsource(stages.FunctionStage._execute_isoform_analysis)

    assert "expected_contract=ExpressionAnalysisResultV2" in source
    assert "expected_contract=ExpressionAnalysisResultV1" not in source


def test_isoform_stage_loads_v2_derived_view() -> None:
    source = inspect.getsource(stages.FunctionStage._execute_isoform_analysis)

    assert "load_isoform_gene_effect_inputs" in source
    assert "analyze_isoforms_from_gene_effect_inputs" in source
    assert ExpressionAnalysisResultV2.expected_contract_name == "ExpressionAnalysisResultV2"


def _isoform_input(**updates: object) -> IsoformGeneEffectInputV1:
    values = {
        "schema_version": "1",
        "input_record_id": "isoform-input:r1",
        "source_expression_v2_record_id": "r1",
        "canonical_gene_id": "HGNC:11998",
        "approved_symbol": "TP53",
        "original_gene_id": "TP53",
        "contrast_id": "treated_vs_control",
        "canonical_log2_fold_change": -1.0,
        "canonical_effect_source": "reported_unshrunken_log2fc",
        "shrunken_log2_fold_change": None,
        "numerical_direction": "decreased",
        "tested_status": "tested",
        "filter_status": "not_filtered",
        "low_count_status": "not_imported",
        "model_status": "estimated",
        "statistical_support_status": "adjusted_pvalue_unavailable",
        "adjusted_p_value": None,
        "adjusted_pvalue_status": "adjusted_pvalue_unavailable",
        "control_abundance_summary": None,
        "treatment_abundance_summary": None,
        "abundance_status": "condition_summaries_unavailable",
        "mean_abundance_summary": 10.0,
        "replicate_consistency": None,
        "replicate_consistency_status": "unavailable",
        "warnings": (),
    }
    values.update(updates)
    return IsoformGeneEffectInputV1(**values)


def _sequence_evidence() -> dict[str, GeneSequenceEvidence]:
    metric = EvidenceMetric(None, "none", "none", "not_calculated", True, "test")
    site = BindingSiteEvidence(
        "TP53",
        "tx1",
        "guide",
        "seed",
        "seed8",
        0,
        (),
        0,
        8,
        "CDS",
        "AAAAAAAA",
        (2, 9),
        (0, 8),
        None,
        10.0,
        False,
        True,
        False,
        False,
        0,
        metric,
        metric,
        metric,
    )
    return {
        "TP53": GeneSequenceEvidence("TP53", (TranscriptSequenceEvidence("TP53", "tx1", (site,)),))
    }


def test_isoform_stage_receives_nonempty_usable_gene_set() -> None:
    result = analyze_isoforms_from_gene_effect_inputs(
        [TranscriptRecord("tx1", "TP53", "AAAA")],
        _sequence_evidence(),
        {"TP53": _isoform_input()},
        0.6,
        0.9,
    )

    assert result["TP53"].target_site_transcript_count == 1


def test_isoform_stage_does_not_require_condition_means() -> None:
    result = analyze_isoforms_from_gene_effect_inputs(
        [TranscriptRecord("tx1", "TP53", "AAAA")],
        _sequence_evidence(),
        {"TP53": _isoform_input()},
        0.6,
        0.9,
    )

    assert result["TP53"].inferred_fraction_min is None
    assert "condition-specific abundance unavailable" in str(result["TP53"].warning)


def test_isoform_stage_does_not_require_replicate_consistency() -> None:
    expression_input = _isoform_input(replicate_consistency=None)
    result = analyze_isoforms_from_gene_effect_inputs(
        [TranscriptRecord("tx1", "TP53", "AAAA")],
        _sequence_evidence(),
        {"TP53": expression_input},
        0.6,
        0.9,
    )

    assert result["TP53"].gene == "TP53"


def test_isoform_stage_preserves_canonical_effect_on_input_object() -> None:
    expression_input = _isoform_input(canonical_log2_fold_change=-2.5)

    assert expression_input.canonical_log2_fold_change == -2.5


def test_isoform_stage_does_not_parse_expression_file() -> None:
    source = inspect.getsource(stages.FunctionStage._execute_isoform_analysis)

    assert "read_counts" not in source
    assert "read_sample_metadata" not in source
    assert "import_precomputed_expression_v2" not in source


def test_isoform_scientific_logic_unchanged_when_condition_means_exist() -> None:
    result = analyze_isoforms_from_gene_effect_inputs(
        [TranscriptRecord("tx1", "TP53", "AAAA")],
        _sequence_evidence(),
        {
            "TP53": _isoform_input(
                control_abundance_summary=100.0,
                treatment_abundance_summary=50.0,
            )
        },
        0.5,
        1.0,
    )

    assert result["TP53"].inferred_fraction_min == 0.5
    assert result["TP53"].inferred_fraction_max == 1.0
