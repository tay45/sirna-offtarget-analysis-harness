from __future__ import annotations

from pathlib import Path

import pandas as pd


def read_network(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, sep="\t")


def read_regulons(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, sep="\t")
