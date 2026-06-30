from __future__ import annotations

from pathlib import Path

import pandas as pd

from sirna_offtarget.config import ExpressionConfig
from sirna_offtarget.expression.contracts_v2 import (
    build_expression_contrast_record_v2,
    build_expression_normalization_run_record_v2,
    build_precomputed_gene_effect_records_v2,
)
from sirna_offtarget.expression.support import expression_execution_support
from sirna_offtarget.identifiers.resolver_v2 import IdentifierResolverV2
from sirna_offtarget.identifiers.snapshots import write_identifier_snapshot


def test_nullable_canonical_effect_and_unresolved_identifier_record(tmp_path: Path) -> None:
    config = ExpressionConfig(
        backend="precomputed",
        count_matrix=tmp_path / "counts.tsv",
        sample_metadata=tmp_path / "samples.tsv",
        precomputed_table=tmp_path / "de.tsv",
        input_mode="precomputed_de",
    )
    snapshot = write_identifier_snapshot(tmp_path / "ids", "human")
    resolver = IdentifierResolverV2(snapshot, "human")
    table = pd.DataFrame(
        {"gene": ["UNKNOWN"], "baseMean": [1], "log2FoldChange": [None], "padj": [None]}
    )
    record = build_precomputed_gene_effect_records_v2(
        table=table,
        config=config,
        organism="human",
        contrast_id="treated_vs_control",
        normalization_run_id="run1",
        source_checksum="abc",
        resolutions={"UNKNOWN": resolver.resolve_expression_gene("UNKNOWN")},
    )[0]
    assert record.original_gene_id == "UNKNOWN"
    assert record.canonical_gene_id is None
    assert record.canonical_log2_fold_change is None
    assert record.numerical_direction == "uncertain"
    assert record.statistical_support_status == "adjusted_pvalue_unavailable"


def test_normalization_run_v2_and_contrast_v2_include_provenance(tmp_path: Path) -> None:
    counts = tmp_path / "counts.tsv"
    metadata_path = tmp_path / "samples.tsv"
    de = tmp_path / "de.tsv"
    counts.write_text("gene\ts1\nA\t1\n")
    metadata_path.write_text("sample\tcondition\ns1\tcontrol\n")
    de.write_text("gene\tbaseMean\tlog2FoldChange\tpadj\nA\t1\t0\t1\n")
    metadata = pd.DataFrame({"sample": ["s1"], "condition": ["control"]})
    config = ExpressionConfig(
        backend="precomputed",
        count_matrix=counts,
        sample_metadata=metadata_path,
        precomputed_table=de,
        input_mode="precomputed_de",
    )
    support = expression_execution_support(config)
    run = build_expression_normalization_run_record_v2(
        config=config,
        organism="human",
        support=support,
        counts_path=counts,
        metadata_path=metadata_path,
        source_result_path=de,
        metadata=metadata,
        identifier_snapshot_id="ids1",
        started_at=None,
        completed_at=None,
        warnings=(),
    )
    contrast = build_expression_contrast_record_v2(config)
    assert run.source_result_checksum is not None
    assert run.identifier_snapshot_id == "ids1"
    assert run.execution_support_level == "validated_import"
    assert contrast.treatment_condition == "treated"
    assert contrast.control_condition == "control"
