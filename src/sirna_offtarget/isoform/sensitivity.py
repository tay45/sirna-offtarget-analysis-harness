def efficiency_grid(minimum: float, maximum: float, step: float) -> list[float]:
    values: list[float] = []
    current = minimum
    while current <= maximum + 1e-9:
        values.append(round(current, 6))
        current += step
    return values
