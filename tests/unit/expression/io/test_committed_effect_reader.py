from __future__ import annotations

import json
from pathlib import Path

import pytest

from sirna_offtarget.expression.committed import (
    LegacyExpressionArtifactNotSupportedError,
    load_committed_normalized_gene_effects,
)


def _write_artifact(artifact: Path) -> None:
    artifact.parent.mkdir(parents=True)
    artifact.write_text(
        "\n"
        + json.dumps(
            {
                "gene": "A",
                "gene_id_namespace": "symbol",
                "organism": "human",
                "contrast_id": "treated_vs_control",
                "normalization_run_id": "exprnorm-test",
                "canonical_log2_fold_change": -1.2,
                "effect_scale": "log2_fold_change",
                "direction": "decreased",
                "threshold_status": "above_threshold",
                "tested_status": "tested",
                "low_count_status": "passes_count_filter",
                "raw_p_value": 0.01,
                "adjusted_p_value": 0.02,
                "significance_status": "significant",
                "backend_name": "precomputed",
                "backend_version": "user-supplied",
                "demonstration_only": False,
                "provenance": {"input_mode": "precomputed_de"},
            }
        )
        + "\n"
    )


def test_loader_requires_manifest_even_when_attempt_commit_exists(tmp_path: Path) -> None:
    artifact = (
        tmp_path
        / "stages"
        / "05_expression_analysis"
        / "attempts"
        / "attempt_001"
        / "committed"
        / "outputs"
        / "normalized_gene_effects_v1.jsonl"
    )
    _write_artifact(artifact)
    with pytest.raises(LegacyExpressionArtifactNotSupportedError):
        load_committed_normalized_gene_effects(tmp_path)


def test_load_committed_normalized_gene_effects_from_direct_stage_output(tmp_path: Path) -> None:
    artifact = (
        tmp_path
        / "stages"
        / "05_expression_analysis"
        / "outputs"
        / "normalized_gene_effects_v1.jsonl"
    )
    _write_artifact(artifact)
    with pytest.raises(LegacyExpressionArtifactNotSupportedError):
        load_committed_normalized_gene_effects(tmp_path)


def test_load_committed_normalized_gene_effects_from_uncommitted_attempt(tmp_path: Path) -> None:
    artifact = (
        tmp_path
        / "stages"
        / "05_expression_analysis"
        / "attempts"
        / "attempt_001"
        / "outputs"
        / "normalized_gene_effects_v1.jsonl"
    )
    _write_artifact(artifact)
    with pytest.raises(LegacyExpressionArtifactNotSupportedError):
        load_committed_normalized_gene_effects(tmp_path)


def test_load_committed_normalized_gene_effects_requires_artifact(tmp_path: Path) -> None:
    with pytest.raises(LegacyExpressionArtifactNotSupportedError) as exc_info:
        load_committed_normalized_gene_effects(tmp_path)
    assert "normalized_gene_effects_v1.jsonl" in str(exc_info.value)
