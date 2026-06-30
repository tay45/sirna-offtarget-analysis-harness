from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ImportedExpressionStatus:
    tested_status: str
    filter_status: str
    low_count_status: str
    model_status: str
    raw_tested_status: str | None
    raw_filter_status: str | None
    raw_low_count_status: str | None
    raw_model_status: str | None
    warnings: tuple[str, ...]


def normalize_imported_status(
    *,
    tested: object,
    filter_status: object,
    low_count: object,
    model_status: object,
) -> ImportedExpressionStatus:
    raw_tested = _text_or_none(tested)
    raw_filter = _text_or_none(filter_status)
    raw_low_count = _text_or_none(low_count)
    raw_model = _text_or_none(model_status)
    canonical_tested, tested_warning = _map_status(
        raw_tested,
        {
            "tested": "tested",
            "yes": "tested",
            "true": "tested",
            "1": "tested",
            "not_tested": "not_tested",
            "untested": "not_tested",
            "filtered_low_count": "filtered_low_count",
            "low_count": "filtered_low_count",
            "false": "not_tested",
            "0": "not_tested",
        },
        "tested",
        "tested_status",
    )
    canonical_filter, filter_warning = _map_status(
        raw_filter,
        {
            "not_filtered": "not_filtered",
            "pass": "not_filtered",
            "passed": "not_filtered",
            "independent_filtered": "independent_filtered",
            "independentfilter": "independent_filtered",
            "outlier_filtered": "outlier_filtered",
            "cooks_outlier": "outlier_filtered",
            "unsupported": "unsupported",
        },
        "not_filtered",
        "filter_status",
    )
    canonical_low_count, low_count_warning = _map_status(
        raw_low_count,
        {
            "passes_count_filter": "passes_count_filter",
            "pass": "passes_count_filter",
            "not_low_count": "passes_count_filter",
            "low_count": "low_count",
            "filtered_low_count": "low_count",
            "not_imported": "not_imported",
        },
        "not_imported",
        "low_count_status",
    )
    canonical_model, model_warning = _map_status(
        raw_model,
        {
            "estimated": "estimated",
            "fit": "estimated",
            "ok": "estimated",
            "model_not_estimable": "model_not_estimable",
            "not_estimable": "model_not_estimable",
            "model_failure": "model_failure",
            "failed": "model_failure",
        },
        "estimated",
        "model_status",
    )
    warnings = tuple(
        warning
        for warning in (
            tested_warning,
            filter_warning,
            low_count_warning,
            model_warning,
        )
        if warning is not None
    )
    return ImportedExpressionStatus(
        tested_status=canonical_tested,
        filter_status=canonical_filter,
        low_count_status=canonical_low_count,
        model_status=canonical_model,
        raw_tested_status=raw_tested,
        raw_filter_status=raw_filter,
        raw_low_count_status=raw_low_count,
        raw_model_status=raw_model,
        warnings=warnings,
    )


def _map_status(
    raw: str | None,
    mapping: dict[str, str],
    default: str,
    label: str,
) -> tuple[str, str | None]:
    if raw is None:
        return default, None
    normalized = raw.strip().lower().replace("-", "_").replace(" ", "_")
    if normalized in mapping:
        return mapping[normalized], None
    return "imported_unknown", f"{label} imported unknown value {raw!r}"


def _text_or_none(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() == "nan":
        return None
    return text
