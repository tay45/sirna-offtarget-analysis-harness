def shrink_lfc(log2_fold_change: float) -> float:
    return log2_fold_change * min(abs(log2_fold_change) / (abs(log2_fold_change) + 0.35), 1.0)
