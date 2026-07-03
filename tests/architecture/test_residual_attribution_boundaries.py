from __future__ import annotations

from pathlib import Path

from sirna_offtarget.residual_attribution.contracts import (
    GeneResidualAttributionEvidenceRecordV1,
    ResidualAttributionResultV1,
    ResidualAttributionUnresolvedRecordV1,
)

ROOT = Path(__file__).resolve().parents[2]
STAGE_SRC = ROOT / "src/sirna_offtarget/residual_attribution"


def test_residual_attribution_does_not_emit_final_classification_fields() -> None:
    forbidden = (
        "_".join(("direct", "effect", "class")),
        "_".join(("secondary", "effect", "call")),
        "_".join(("mixed", "classification")),
        "_".join(("final", "classification")),
        "direct/secondary/mixed gene call",
    )
    emitted_fields = (
        set(GeneResidualAttributionEvidenceRecordV1.model_fields)
        | set(ResidualAttributionUnresolvedRecordV1.model_fields)
        | set(ResidualAttributionResultV1.model_fields)
    )
    for token in forbidden:
        assert token not in emitted_fields


def test_residual_attribution_keeps_pathway_support_optional() -> None:
    core = (STAGE_SRC / "core.py").read_text()
    assert "pathway_evidence_available: bool = False" in core
    assert "unresolved_missing_pathway_evidence" in core
    assert "unresolved_not_negative" in core


def test_expected_direct_effect_logic_is_not_importing_residual_attribution() -> None:
    expected_src = ROOT / "src/sirna_offtarget/expected_direct_effect"
    text = "\n".join(path.read_text() for path in expected_src.glob("*.py"))
    assert "residual_attribution" not in text
