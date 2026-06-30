from __future__ import annotations

from sirna_offtarget.models import ExpressionResult


def tested_expression_background(results: dict[str, ExpressionResult]) -> tuple[str, ...]:
    return tuple(sorted(results))
