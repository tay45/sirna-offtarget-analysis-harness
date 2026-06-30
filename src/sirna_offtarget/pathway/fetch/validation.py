from __future__ import annotations


def validate_response_metadata(
    *,
    status_code: int,
    content_length: int,
    max_response_size: int,
    content_type: str,
    expected_content_type: str | None,
) -> list[str]:
    errors: list[str] = []
    if status_code < 200 or status_code >= 300:
        errors.append(f"unexpected status {status_code}")
    if content_length <= 0:
        errors.append("empty response")
    if content_length > max_response_size:
        errors.append("response exceeds maximum configured size")
    if expected_content_type and expected_content_type not in content_type:
        errors.append(f"unexpected content type {content_type!r}")
    return errors
