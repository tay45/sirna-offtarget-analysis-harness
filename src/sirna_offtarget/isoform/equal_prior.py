def equal_transcript_prior(targeted_count: int, total_count: int) -> float:
    if total_count <= 0:
        raise ValueError("total transcript count N must be positive")
    if targeted_count > total_count:
        raise ValueError("targeted transcript count M cannot exceed N")
    return targeted_count / total_count
