from __future__ import annotations

from pathlib import Path

from sirna_offtarget.config import ExpressionConfig
from sirna_offtarget.expression.contracts import (
    build_contrast_record,
    build_normalization_run_record,
    build_normalized_gene_effect_records,
)
from sirna_offtarget.models import Direction, ExpressionResult


def test_normalized_effect_preserves_gene_namespace_and_organism(tmp_path: Path) -> None:
    config = ExpressionConfig(
        backend="synthetic",
        count_matrix=tmp_path / "counts.tsv",
        sample_metadata=tmp_path / "samples.tsv",
        gene_id_namespace="ensembl_gene_id",
    )
    result = ExpressionResult(
        gene="ENSG000001",
        baseline_expression=10,
        normalized_control_expression=10,
        normalized_treated_expression=5,
        log2_fold_change=-1,
        shrunken_log2_fold_change=-0.8,
        adjusted_p_value=0.01,
        replicate_consistency=1,
        direction=Direction.DOWN,
        low_count_flag=False,
    )
    run = build_normalization_run_record({"ENSG000001": result}, config)
    contrast = build_contrast_record(config)
    record = build_normalized_gene_effect_records(
        {"ENSG000001": result},
        config,
        run,
        contrast,
        organism="human",
    )[0]
    assert record.gene == "ENSG000001"
    assert record.gene_id_namespace == "ensembl_gene_id"
    assert record.organism == "human"
