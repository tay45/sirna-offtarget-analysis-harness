from __future__ import annotations


class PathwayProviderError(RuntimeError):
    """Base error for pathway provider failures."""


class ProviderParseError(PathwayProviderError):
    """Raised when a provider response cannot be parsed."""


class ProviderSnapshotError(PathwayProviderError):
    """Raised when a provider cache snapshot is invalid."""
