def local_context(sequence: str, start: int, flank: int = 3) -> str:
    return sequence[max(start - flank, 0) : start + flank]
