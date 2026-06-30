from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import pandas as pd

from sirna_offtarget.models import ExpressionResult


@dataclass(frozen=True)
class ExpressionBackendMetadata:
    name: str
    version: str
    demonstration_only: bool
    design_formula: str
    tested_gene_universe: tuple[str, ...]


class ExpressionBackend(Protocol):
    metadata: ExpressionBackendMetadata

    def run(self, counts: pd.DataFrame, metadata: pd.DataFrame) -> dict[str, ExpressionResult]: ...
