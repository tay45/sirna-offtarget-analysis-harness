from __future__ import annotations

from pathlib import Path


def test_isoform_uncertainty_does_not_introduce_deferred_scope_terms() -> None:
    root = Path("src/sirna_offtarget/isoform_uncertainty")
    source = "\n".join(path.read_text() for path in root.glob("*.py"))
    forbidden = [
        "gene log2FC / transcript count",
        "targetable transcript count",
        "M/N",
        "siRNA sequence matching",
        "transcript-specific p-value",
        "transcript-specific fold change",
        "intended-target calibration",
    ]
    assert all(term not in source for term in forbidden)


def test_isoform_uncertainty_uses_committed_expression_v2_names_only() -> None:
    source = Path("src/sirna_offtarget/isoform_uncertainty/contracts.py").read_text()
    assert "source_expression_v2_record_id" in source
    assert "ExpressionAnalysisResultV1" not in source
