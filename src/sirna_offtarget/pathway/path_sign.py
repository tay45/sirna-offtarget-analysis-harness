from __future__ import annotations


def compose_path_sign(edge_signs: list[str]) -> int | None:
    product = 1
    for sign in edge_signs:
        if sign in {"activates", "positive", "+1"}:
            product *= 1
        elif sign in {"inhibits", "negative", "-1"}:
            product *= -1
        else:
            return None
    return product
