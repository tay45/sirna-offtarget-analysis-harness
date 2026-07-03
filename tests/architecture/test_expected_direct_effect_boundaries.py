from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STAGE_SRC = ROOT / "src/sirna_offtarget/expected_direct_effect"


def _stage_text() -> str:
    return "\n".join(path.read_text() for path in STAGE_SRC.glob("*.py"))


def test_expected_direct_effect_uses_only_expression_and_ratio_evidence() -> None:
    text = _stage_text()
    assert "normalized_gene_effects_v2.jsonl" in text
    assert "gene_transcript_targetability_ratios_v1.jsonl" in text
    forbidden = (
        "pathway_enrichment",
        "mechanistic_network",
        "provider_evidence",
        "secondary_effect",
        "final_classification",
        "direct_classification",
        "mixed_classification",
    )
    for term in forbidden:
        assert term not in text


def test_expected_direct_effect_preserves_residual_boundary() -> None:
    text = _stage_text()
    assert "unresolved_residual_log2fc" in text
    assert "observed_vs_expected_log2_difference" in text
    assert "observed_vs_expected_difference" not in text
    assert "unresolved_residual_only" in text
