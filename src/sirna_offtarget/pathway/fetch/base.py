from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ProviderRequest:
    provider: str
    endpoint: str
    method: str
    query_parameters: dict[str, str] = field(default_factory=dict)
    body: bytes | None = None
    headers: dict[str, str] = field(default_factory=dict)
    content_type: str | None = None
    pagination: str = "none"
    release_discovery: str = "response_metadata_or_null"
    timeout_seconds: float = 20.0
    retry_statuses: tuple[int, ...] = (408, 429, 500, 502, 503, 504)
    rate_limit_policy: str = "respect_retry_after"
    validation: tuple[str, ...] = ("non_empty_body", "status_2xx")
