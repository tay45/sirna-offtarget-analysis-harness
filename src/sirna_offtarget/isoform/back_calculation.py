from __future__ import annotations


def inferred_targetable_fraction(
    control_expression: float,
    treated_expression: float,
    efficiency_min: float,
    efficiency_max: float,
) -> tuple[float | None, float | None, str | None]:
    if control_expression <= 0:
        return None, None, "Cannot infer fraction when baseline expression is zero or negative."
    d_gene = 1.0 - treated_expression / control_expression
    if d_gene < 0:
        return 0.0, 0.0, "Negative inferred fraction; target increased under treatment."
    f_min = d_gene / efficiency_max
    f_max = d_gene / efficiency_min
    warning = None
    if f_max > 1:
        warning = "Inferred fraction exceeds 1 under part of the efficiency interval."
    return round(max(0.0, min(f_min, 1.0)), 6), round(max(0.0, min(f_max, 1.0)), 6), warning
