from __future__ import annotations

from enum import StrEnum


class ProviderMode(StrEnum):
    PUBLIC_FETCH = "public_fetch"
    PUBLIC_CACHE = "public_cache"
    LOCAL_SNAPSHOT = "local_snapshot"
    SYNTHETIC_FIXTURE = "synthetic_fixture"
    DISABLED = "disabled"


def normalize_provider_name(name: str) -> str:
    return name.strip().lower().replace("-", "_")
