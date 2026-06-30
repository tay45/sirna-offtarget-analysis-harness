def is_low_count(
    baseline: float, min_baseline: float, expressed_replicates: int, min_reps: int
) -> bool:
    return baseline < min_baseline or expressed_replicates < min_reps
