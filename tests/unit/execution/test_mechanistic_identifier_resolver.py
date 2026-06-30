from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from sirna_offtarget.execution.stages import (
    _expression_identifier_resolver,
    _mechanistic_identifier_resolver,
)
from sirna_offtarget.identifiers.snapshots import write_identifier_snapshot


def _context(*, synthetic_mode: bool, cache_dir: Path | None = None) -> SimpleNamespace:
    return SimpleNamespace(
        config=SimpleNamespace(
            project=SimpleNamespace(organism="human"),
            pathway=SimpleNamespace(synthetic_mode=synthetic_mode, cache_dir=cache_dir),
        )
    )


def test_mechanistic_identifier_resolver_creates_synthetic_verified_snapshot(
    tmp_path: Path,
) -> None:
    resolver = _mechanistic_identifier_resolver(_context(synthetic_mode=True), tmp_path / "attempt")

    assert resolver.snapshot_id == "human_identifier-snapshot-v1"
    assert resolver.resolve_provider_entity("signor", "TARGET1", "gene").canonical_gene_ids


def test_mechanistic_identifier_resolver_requires_production_cache(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="requires a verified identifier snapshot cache"):
        _mechanistic_identifier_resolver(_context(synthetic_mode=False), tmp_path / "attempt")


def test_mechanistic_identifier_resolver_requires_snapshot_in_cache(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="requires a verified identifier snapshot"):
        _mechanistic_identifier_resolver(
            _context(synthetic_mode=False, cache_dir=tmp_path / "cache"),
            tmp_path / "attempt",
        )


def test_mechanistic_identifier_resolver_uses_verified_cache_snapshot(tmp_path: Path) -> None:
    cache = tmp_path / "cache"
    write_identifier_snapshot(cache, "human")

    resolver = _mechanistic_identifier_resolver(
        _context(synthetic_mode=False, cache_dir=cache), tmp_path / "attempt"
    )

    assert resolver.resolve_provider_entity("signor", "GENEA", "gene").canonical_gene_ids


def test_expression_precomputed_resolver_requires_configured_snapshot(
    tmp_path: Path,
) -> None:
    context = SimpleNamespace(
        config=SimpleNamespace(
            project=SimpleNamespace(organism="human"),
            expression=SimpleNamespace(
                backend="precomputed",
                input_mode="precomputed_de",
                identifier_cache_dir=tmp_path / "cache",
                identifier_snapshot_id=None,
                require_verified_identifier_snapshot=True,
                identifier_ambiguity_policy="exclude",
            ),
        )
    )

    with pytest.raises(RuntimeError, match="identifier_snapshot_id"):
        _expression_identifier_resolver(context, tmp_path / "attempt")


def test_expression_resolver_uses_configured_snapshot_id(tmp_path: Path) -> None:
    cache = tmp_path / "cache"
    snapshot = write_identifier_snapshot(cache, "human")
    context = SimpleNamespace(
        config=SimpleNamespace(
            project=SimpleNamespace(organism="human"),
            expression=SimpleNamespace(
                backend="precomputed",
                input_mode="precomputed_de",
                identifier_cache_dir=cache,
                identifier_snapshot_id=snapshot.name,
                require_verified_identifier_snapshot=True,
                identifier_ambiguity_policy="exclude",
            ),
        )
    )

    resolver = _expression_identifier_resolver(context, tmp_path / "attempt")

    assert resolver.snapshot_id == snapshot.name
