from __future__ import annotations

import time
import urllib.error
import urllib.request
from dataclasses import dataclass

from sirna_offtarget.pathway.providers.exceptions import PathwayProviderError


@dataclass(frozen=True)
class FetchResponse:
    url: str
    status_code: int
    headers: dict[str, str]
    body: bytes
    content_type: str


def fetch_bytes(
    *,
    url: str,
    timeout_seconds: float,
    retry_count: int,
    expected_content_type: str | None,
    user_agent: str = "sirna-offtarget-analysis-harness/0.1",
) -> FetchResponse:
    if not url:
        raise PathwayProviderError("provider endpoint is required for public_fetch mode")
    last_error: Exception | None = None
    for attempt in range(retry_count + 1):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": user_agent})
            with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
                status = int(getattr(response, "status", 200) or 200)
                headers = {str(k): str(v) for k, v in response.headers.items()}
                content_type = headers.get("Content-Type", "")
                body = response.read()
            if status < 200 or status >= 300:
                raise PathwayProviderError(f"provider HTTP status {status} for {url}")
            if expected_content_type and expected_content_type not in content_type:
                raise PathwayProviderError(
                    f"unexpected content type {content_type!r}; expected {expected_content_type!r}"
                )
            if not body:
                raise PathwayProviderError(f"empty provider response from {url}")
            return FetchResponse(url, status, headers, body, content_type)
        except urllib.error.HTTPError as exc:
            last_error = exc
            if exc.code not in {408, 429, 500, 502, 503, 504} or attempt == retry_count:
                raise PathwayProviderError(f"provider HTTP status {exc.code} for {url}") from exc
        except (urllib.error.URLError, TimeoutError) as exc:
            last_error = exc
            if attempt == retry_count:
                raise PathwayProviderError(f"provider fetch failed for {url}: {exc}") from exc
        time.sleep(min(2**attempt, 8))
    raise PathwayProviderError(f"provider fetch failed for {url}: {last_error}")
