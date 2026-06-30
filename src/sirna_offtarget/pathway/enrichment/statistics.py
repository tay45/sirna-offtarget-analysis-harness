from __future__ import annotations

from math import comb


def simple_enrichment_score(observed: int, total: int) -> float:
    return 0.0 if total <= 0 else observed / total


def fisher_exact_greater(a: int, b: int, c: int, d: int) -> float:
    total = a + b + c + d
    row = a + b
    col = a + c
    maximum = min(row, col)
    denominator = comb(total, row)
    probability = 0.0
    for x in range(a, maximum + 1):
        probability += comb(col, x) * comb(total - col, row - x) / denominator
    return min(1.0, probability)


def hypergeometric_tail(
    observed: int,
    pathway_size: int,
    test_list_size: int,
    background_size: int,
) -> float:
    maximum = min(pathway_size, test_list_size)
    denominator = comb(background_size, test_list_size)
    probability = 0.0
    for x in range(observed, maximum + 1):
        probability += (
            comb(pathway_size, x)
            * comb(background_size - pathway_size, test_list_size - x)
            / denominator
        )
    return min(1.0, probability)


def benjamini_hochberg(p_values: list[float]) -> list[float]:
    if not p_values:
        return []
    indexed = sorted(enumerate(p_values), key=lambda item: item[1], reverse=True)
    adjusted = [1.0] * len(p_values)
    running = 1.0
    total = len(p_values)
    for rank_from_end, (index, value) in enumerate(indexed, start=1):
        rank = total - rank_from_end + 1
        running = min(running, value * total / rank)
        adjusted[index] = min(1.0, running)
    return adjusted
