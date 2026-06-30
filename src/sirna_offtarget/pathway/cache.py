from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PathwayCacheRecord:
    provider: str
    endpoint: str
    path: Path
    sha256_checksum: str
    retrieval_date: str
    license_notes: str
