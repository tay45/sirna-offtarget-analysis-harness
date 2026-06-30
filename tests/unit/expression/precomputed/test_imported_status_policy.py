from __future__ import annotations

from sirna_offtarget.expression.status_policy import normalize_imported_status


def test_normalize_imported_status_maps_known_values() -> None:
    status = normalize_imported_status(
        tested="yes",
        filter_status="cooks-outlier",
        low_count="filtered_low_count",
        model_status="not estimable",
    )

    assert status.tested_status == "tested"
    assert status.filter_status == "outlier_filtered"
    assert status.low_count_status == "low_count"
    assert status.model_status == "model_not_estimable"
    assert status.warnings == ()


def test_normalize_imported_status_preserves_unknown_values_as_warnings() -> None:
    status = normalize_imported_status(
        tested="maybe",
        filter_status="",
        low_count=None,
        model_status="nan",
    )

    assert status.tested_status == "imported_unknown"
    assert status.filter_status == "not_filtered"
    assert status.low_count_status == "not_imported"
    assert status.model_status == "estimated"
    assert status.raw_tested_status == "maybe"
    assert status.raw_filter_status is None
    assert status.raw_low_count_status is None
    assert status.raw_model_status is None
    assert status.warnings == ("tested_status imported unknown value 'maybe'",)
