from __future__ import annotations

from typing import Any

import pandas as pd

from sirna_offtarget.models import ExpressionResult


class PyDeseq2Backend:
    demonstration_only = False

    def __init__(self, _config: Any) -> None:
        try:
            import pydeseq2  # type: ignore[import-not-found] # noqa: F401
        except ImportError as exc:
            raise RuntimeError(
                "expression.backend=pydeseq2 requires the optional PyDESeq2 dependency; "
                "install it explicitly or choose backend=precomputed."
            ) from exc

    def run(
        self,
        _counts: pd.DataFrame,
        _metadata: pd.DataFrame,
    ) -> dict[str, ExpressionResult]:
        raise RuntimeError(
            "PyDESeq2 routing is available, but execution is not bundled with this harness build. "
            "Use backend=precomputed for production DE results."
        )


class PyDESeq2BackendUnavailable:
    def run(self) -> None:
        raise RuntimeError(
            "PyDESeq2 backend is unavailable in this harness build; use backend=precomputed."
        )
