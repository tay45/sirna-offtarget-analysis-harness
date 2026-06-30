from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


class PathwayProvider(Protocol):
    name: str
    production_provider: bool

    def load_cached(self, cache_dir: str | Path) -> object: ...


@dataclass(frozen=True)
class CachedProviderSnapshot:
    provider: str
    source_path: Path
    records: tuple[dict[str, str], ...]
    required_columns: tuple[str, ...]

    @property
    def record_count(self) -> int:
        return len(self.records)

    def as_dict(self) -> dict[str, object]:
        return {
            "provider": self.provider,
            "source_path": str(self.source_path),
            "record_count": self.record_count,
            "required_columns": list(self.required_columns),
            "records": [dict(record) for record in self.records],
        }


def load_cached_records(
    cache_dir: str | Path,
    provider: str,
    required_columns: tuple[str, ...],
    candidate_filenames: tuple[str, ...] | None = None,
) -> CachedProviderSnapshot:
    cache_path = Path(cache_dir)
    candidates = candidate_filenames or (
        f"{provider}.tsv",
        f"{provider}.csv",
        f"{provider}.json",
        f"{provider}.jsonl",
    )
    for filename in candidates:
        path = cache_path / filename
        if path.exists():
            records = _read_records(path)
            _validate_columns(provider, records, required_columns, path)
            return CachedProviderSnapshot(provider, path, tuple(records), required_columns)
    searched = ", ".join(candidates)
    raise FileNotFoundError(f"cached {provider} snapshot not found in {cache_path}: {searched}")


def _read_records(path: Path) -> list[dict[str, str]]:
    if path.suffix == ".jsonl":
        return [_coerce_record(json.loads(line)) for line in path.read_text().splitlines() if line]
    if path.suffix == ".json":
        payload = json.loads(path.read_text())
        if isinstance(payload, dict):
            payload = payload.get("records", [])
        if not isinstance(payload, list):
            raise ValueError(f"cached provider JSON must contain a list of records: {path}")
        return [_coerce_record(item) for item in payload]
    delimiter = "\t" if path.suffix == ".tsv" else ","
    with path.open(newline="") as handle:
        return [_coerce_record(row) for row in csv.DictReader(handle, delimiter=delimiter)]


def _coerce_record(record: object) -> dict[str, str]:
    if not isinstance(record, dict):
        raise ValueError("cached provider records must be objects")
    return {str(key): "" if value is None else str(value) for key, value in record.items()}


def _validate_columns(
    provider: str,
    records: list[dict[str, str]],
    required_columns: tuple[str, ...],
    path: Path,
) -> None:
    if not records:
        return
    missing = [column for column in required_columns if column not in records[0]]
    if missing:
        raise ValueError(f"cached {provider} snapshot {path} missing columns: {missing}")
