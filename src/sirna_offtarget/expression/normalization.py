from __future__ import annotations

import pandas as pd


def median_ratio_normalize(counts: pd.DataFrame) -> pd.DataFrame:
    library_sizes = counts.sum(axis=0)
    median_size = float(library_sizes.median())
    factors = library_sizes / median_size
    return counts.div(factors, axis=1)
