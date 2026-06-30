from __future__ import annotations

from sirna_offtarget.models import Direction


def sign_to_int(sign: str) -> int | None:
    normalized = sign.lower()
    if normalized in {"positive", "activates", "activation", "+1", "stimulation"}:
        return 1
    if normalized in {"negative", "inhibits", "inhibition", "-1"}:
        return -1
    return None


def compose_signed_path(edge_signs: list[str]) -> int | None:
    product = 1
    for sign in edge_signs:
        value = sign_to_int(sign)
        if value is None:
            return None
        product *= value
    return product


def expected_after_target_decrease(composed_sign: int | None) -> Direction | None:
    if composed_sign is None:
        return None
    return Direction.DOWN if composed_sign > 0 else Direction.UP
