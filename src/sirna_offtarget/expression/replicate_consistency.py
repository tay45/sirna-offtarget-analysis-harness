def consistency(signs: list[float]) -> float:
    return abs(sum(signs)) / len(signs) if signs else 0.0
