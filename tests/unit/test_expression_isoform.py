import pandas as pd
import pytest

from sirna_offtarget.expression import analyze_expression
from sirna_offtarget.isoform import equal_transcript_prior, inferred_targetable_fraction


def test_expression_uses_relative_change_and_low_count() -> None:
    counts = pd.DataFrame(
        {"c1": [100, 4, 50], "c2": [100, 4, 50], "t1": [50, 1, 100], "t2": [50, 1, 100]},
        index=["A", "LOW", "BALANCE"],
    )
    meta = pd.DataFrame(
        {
            "sample": ["c1", "c2", "t1", "t2"],
            "condition": ["control", "control", "treated", "treated"],
        }
    )
    results = analyze_expression(counts, meta, 10, 2)
    assert results["A"].direction == "down"
    assert results["LOW"].low_count_flag


def test_equal_prior_and_back_calculation_guards() -> None:
    assert equal_transcript_prior(1, 3) == pytest.approx(1 / 3)
    with pytest.raises(ValueError):
        equal_transcript_prior(2, 1)
    assert inferred_targetable_fraction(100, 60, 0.5, 1.0)[:2] == (0.4, 0.8)
    assert inferred_targetable_fraction(0, 0, 0.5, 1.0)[2] is not None
