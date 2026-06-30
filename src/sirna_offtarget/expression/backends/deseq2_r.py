from __future__ import annotations

from typing import Any

import pandas as pd

from sirna_offtarget.models import ExpressionResult


class Deseq2RBackend:
    demonstration_only = False

    def __init__(self, _config: Any) -> None:
        raise RuntimeError(
            "expression.backend=deseq2_r requires an explicit local R/DESeq2 adapter. "
            "This harness will not silently switch to another backend; use backend=precomputed "
            "with exported DESeq2 results."
        )

    def run(
        self,
        _counts: pd.DataFrame,
        _metadata: pd.DataFrame,
    ) -> dict[str, ExpressionResult]:
        raise RuntimeError("DESeq2 R backend was not initialized")


class DESeq2RBackendUnavailable:
    def run(self) -> None:
        raise RuntimeError(
            "DESeq2 R backend is unavailable in this harness build; use backend=precomputed."
        )
