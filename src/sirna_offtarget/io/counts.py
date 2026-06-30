from __future__ import annotations

from pathlib import Path

import pandas as pd


def read_counts(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, sep="\t").set_index("gene")


def read_sample_metadata(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, sep="\t")
