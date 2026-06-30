RETRYABLE_HTTP_STATUSES = (408, 429, 500, 502, 503, 504)


def backoff_seconds(attempt: int, retry_after: float | None = None) -> float:
    if retry_after is not None:
        return retry_after
    return min(2.0**attempt, 30.0)
