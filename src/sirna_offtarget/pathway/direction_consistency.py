from __future__ import annotations

from sirna_offtarget.models import Direction


def is_direction_consistent(edge_sign: str, candidate_direction: Direction) -> bool:
    if edge_sign in {"activates", "positive", "+1"}:
        return candidate_direction == Direction.DOWN
    if edge_sign in {"inhibits", "negative", "-1"}:
        return candidate_direction == Direction.UP
    return False


def sign_to_int(edge_sign: str) -> int | None:
    if edge_sign in {"activates", "positive", "+1"}:
        return 1
    if edge_sign in {"inhibits", "negative", "-1"}:
        return -1
    return None


def expected_direction_after_target_decrease(composed_sign: int | None) -> Direction | None:
    if composed_sign == 1:
        return Direction.DOWN
    if composed_sign == -1:
        return Direction.UP
    return None
