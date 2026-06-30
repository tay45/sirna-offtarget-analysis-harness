from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from sirna_offtarget.config import ExpressionConfig
from sirna_offtarget.expression.contracts_v2 import (
    build_precomputed_gene_effect_records_v2,
)
from sirna_offtarget.expression.downstream import normalized_gene_effect_v2_to_downstream_view
from sirna_offtarget.expression.importer_v2 import import_precomputed_expression_v2
from sirna_offtarget.identifiers.resolver_v2 import IdentifierResolverV2
from sirna_offtarget.identifiers.snapshots import write_identifier_snapshot


def _resolver(tmp_path: Path) -> IdentifierResolverV2:
    snapshot = write_identifier_snapshot(tmp_path / "ids", "human")
    return IdentifierResolverV2(snapshot, "human")


def _config(tmp_path: Path) -> ExpressionConfig:
    return ExpressionConfig(
        backend="precomputed",
        count_matrix=tmp_path / "counts.tsv",
        sample_metadata=tmp_path / "samples.tsv",
        precomputed_table=tmp_path / "de.tsv",
        input_mode="precomputed_de",
        tested_column="tested",
        filter_status_column="filter_status",
        model_status_column="model_status",
        test_statistic_column="stat",
        standard_error_column="se",
    )


def test_base_mean_not_used_as_control_or_treatment_mean(tmp_path: Path) -> None:
    config = _config(tmp_path)
    table = pd.DataFrame(
        {
            "gene": ["TP53"],
            "baseMean": [100],
            "log2FoldChange": [-1.5],
            "lfcShrink": [None],
            "padj": [None],
            "tested": ["tested"],
            "filter_status": ["independent_filtered"],
            "model_status": ["estimated"],
            "se": [0.2],
            "stat": [-4.2],
        }
    )
    resolver = _resolver(tmp_path)
    records = build_precomputed_gene_effect_records_v2(
        table=table,
        config=config,
        organism="human",
        contrast_id="treated_vs_control",
        normalization_run_id="run1",
        source_checksum="abc",
        resolutions={"TP53": resolver.resolve_expression_gene("TP53")},
    )
    record = records[0]
    assert record.control_abundance_summary is None
    assert record.treatment_abundance_summary is None
    assert record.mean_abundance_summary == 100
    assert record.reported_log2_fold_change == -1.5
    assert record.shrunken_log2_fold_change is None
    assert record.canonical_effect_source == "reported_unshrunken_log2fc"
    assert record.adjusted_p_value is None
    assert record.adjusted_pvalue_status == "independent_filtered"
    assert record.tested_status == "tested"
    assert record.filter_status == "independent_filtered"
    assert record.standard_error == 0.2
    assert record.test_statistic == -4.2
    assert record.numerical_direction == "decreased"


def test_deterministic_record_id_uses_source_checksum(tmp_path: Path) -> None:
    config = _config(tmp_path)
    table = pd.DataFrame({"gene": ["TP53"], "baseMean": [1], "log2FoldChange": [0], "padj": [1]})
    resolver = _resolver(tmp_path)
    args = {
        "table": table,
        "config": config,
        "organism": "human",
        "contrast_id": "treated_vs_control",
        "normalization_run_id": "run1",
        "resolutions": {"TP53": resolver.resolve_expression_gene("TP53")},
    }
    first = build_precomputed_gene_effect_records_v2(source_checksum="a", **args)[0]
    second = build_precomputed_gene_effect_records_v2(source_checksum="b", **args)[0]
    assert first.record_id != second.record_id


def test_import_precomputed_expression_v2_preserves_nulls_and_records_downstream_exclusion(
    tmp_path: Path,
) -> None:
    config = _config(tmp_path)
    config.precomputed_table.write_text(
        "gene\tbaseMean\tlog2FoldChange\tlfcShrink\tpadj\ttested\tfilter_status\tmodel_status\n"
        "TP53\t25\t\t\t\ttested\tnot_filtered\testimated\n"
    )
    config.sample_metadata.write_text("sample\tcondition\ns1\tcontrol\ns2\ttreated\n")
    imported = import_precomputed_expression_v2(
        config=config,
        organism="human",
        metadata=pd.DataFrame({"sample": ["s1", "s2"], "condition": ["control", "treated"]}),
        resolver=_resolver(tmp_path),
        counts_path=config.count_matrix,
        metadata_path=config.sample_metadata,
    )
    record = imported.records[0]
    assert record.canonical_log2_fold_change is None
    assert record.canonical_effect_source == "unavailable"
    assert record.adjusted_p_value is None
    view = normalized_gene_effect_v2_to_downstream_view(imported.records)
    assert view.records == ()
    assert view.exclusions[0].exclusion_reason == "canonical_effect_unavailable"
    assert imported.validation_payload["sample_validation"] == "not_applicable"


def test_import_precomputed_expression_v2_requires_table_path(tmp_path: Path) -> None:
    config = _config(tmp_path).model_copy(update={"precomputed_table": None})
    with pytest.raises(ValueError, match="precomputed_table"):
        import_precomputed_expression_v2(
            config=config,
            organism="human",
            metadata=pd.DataFrame(),
            resolver=_resolver(tmp_path),
            counts_path=config.count_matrix,
            metadata_path=config.sample_metadata,
        )
