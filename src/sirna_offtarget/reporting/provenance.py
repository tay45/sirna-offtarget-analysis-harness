from __future__ import annotations

from datetime import UTC, datetime

from sirna_offtarget import __version__
from sirna_offtarget.config import HarnessConfig


def build_provenance(config: HarnessConfig) -> dict[str, object]:
    return {
        "package": "sirna_offtarget",
        "version": __version__,
        "project": config.project.name,
        "random_seed": config.project.random_seed,
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "biological_validation_status": "synthetic software validation only",
    }
