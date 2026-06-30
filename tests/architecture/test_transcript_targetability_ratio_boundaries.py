from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RATIO_SRC = ROOT / "src/sirna_offtarget/transcript_targetability_ratio"


def _ratio_text() -> str:
    return "\n".join(path.read_text() for path in RATIO_SRC.glob("*.py"))


def test_ratio_does_not_depend_on_expression_or_pathway_magnitude() -> None:
    text = _ratio_text()
    assert "normalized_gene_effect" not in text
    assert "log2_fold_change" not in text
    assert "expression" not in text
    assert "pathway" not in text


def test_ratio_boundaries_exclude_downstream_effect_models() -> None:
    text = _ratio_text()
    forbidden = (
        "knockdown_efficiency",
        "expected_direct",
        "residual",
        "secondary_effect",
        "classification",
        "candidate_direct",
    )
    for term in forbidden:
        assert term not in text


def test_ratio_preserves_seed_only_boundary_in_code() -> None:
    text = _ratio_text()
    assert "include_seed_only" in text
    assert "seed_only_candidate" in text
    assert "require_cleavage_compatibility" in text
    assert "count_transcript_once" in text
