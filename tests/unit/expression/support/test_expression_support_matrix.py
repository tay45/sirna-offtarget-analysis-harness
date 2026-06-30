from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from sirna_offtarget.config import ExpressionConfig
from sirna_offtarget.expression.api import analyze_expression_with_config
from sirna_offtarget.expression.support import expression_execution_support


def _config(tmp_path: Path, **updates: object) -> ExpressionConfig:
    values = {
        "backend": "synthetic",
        "count_matrix": tmp_path / "counts.tsv",
        "sample_metadata": tmp_path / "samples.tsv",
    }
    values.update(updates)
    return ExpressionConfig(**values)


def test_demo_mode_marked_demo_only(tmp_path: Path) -> None:
    support = expression_execution_support(_config(tmp_path, backend="synthetic"))
    assert support.execution_supported
    assert not support.production_supported
    assert support.execution_support_level == "demonstration_only"


def test_precomputed_import_support(tmp_path: Path) -> None:
    support = expression_execution_support(
        _config(
            tmp_path,
            backend="precomputed",
            input_mode="precomputed_de",
            precomputed_table=tmp_path / "de.tsv",
        )
    )
    assert support.execution_support_level == "validated_import"
    assert support.production_supported


def test_normalized_matrix_support_is_honest(tmp_path: Path) -> None:
    support = expression_execution_support(
        _config(tmp_path, backend="synthetic", input_mode="normalized_matrix", value_scale="tpm")
    )
    assert support.execution_support_level == "validation_only"
    assert not support.execution_supported
    with pytest.raises(RuntimeError, match="normalized_matrix_execution_not_supported"):
        analyze_expression_with_config(
            pd.DataFrame(),
            pd.DataFrame(),
            _config(tmp_path, input_mode="normalized_matrix", value_scale="tpm"),
        )


def test_unavailable_backend_fails_clearly(tmp_path: Path) -> None:
    counts = pd.DataFrame({"c1": [1], "t1": [2]}, index=["A"])
    metadata = pd.DataFrame({"sample": ["c1", "t1"], "condition": ["control", "treated"]})
    with pytest.raises(RuntimeError, match="raw_count_production_backend_unavailable"):
        analyze_expression_with_config(counts, metadata, _config(tmp_path, backend="deseq2_r"))
