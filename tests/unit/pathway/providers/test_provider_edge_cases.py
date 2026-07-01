from __future__ import annotations

import urllib.error
import urllib.request

import pytest

from sirna_offtarget.pathway.providers.exceptions import PathwayProviderError
from sirna_offtarget.pathway.providers.http import fetch_bytes
from sirna_offtarget.pathway.providers.omnipath import OmniPathProvider
from sirna_offtarget.pathway.providers.panther import PantherProvider
from sirna_offtarget.pathway.providers.reactome_analysis import ReactomeAnalysisProvider
from sirna_offtarget.pathway.providers.reactome_content import ReactomeContentProvider
from sirna_offtarget.pathway.providers.reactome_fi import ReactomeFIProvider
from sirna_offtarget.pathway.providers.signor import SignorProvider


class _FakeHTTPResponse:
    def __init__(
        self,
        *,
        status: int = 200,
        headers: dict[str, str] | None = None,
        body: bytes = b'{"ok": true}',
    ) -> None:
        self.status = status
        self.headers = headers or {"Content-Type": "application/json"}
        self._body = body

    def __enter__(self) -> _FakeHTTPResponse:
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self) -> bytes:
        return self._body


def test_fetch_bytes_http_success_and_validation(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_urlopen(request: urllib.request.Request, *, timeout: float) -> _FakeHTTPResponse:
        assert request.full_url == "https://example.test/provider.json"
        assert timeout == 2
        return _FakeHTTPResponse()

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    response = fetch_bytes(
        url="https://example.test/provider.json",
        timeout_seconds=2,
        retry_count=0,
        expected_content_type="application/json",
    )
    assert response.status_code == 200
    assert response.content_type == "application/json"
    assert response.body == b'{"ok": true}'


def test_fetch_bytes_rejects_unsupported_scheme() -> None:
    with pytest.raises(PathwayProviderError, match="unsupported provider URL scheme"):
        fetch_bytes(
            url="ftp://example.test/provider.json",
            timeout_seconds=1,
            retry_count=0,
            expected_content_type=None,
        )


@pytest.mark.parametrize(
    ("response", "message"),
    [
        (_FakeHTTPResponse(status=404), "provider HTTP status 404"),
        (
            _FakeHTTPResponse(headers={"Content-Type": "text/plain"}),
            "unexpected content type",
        ),
        (_FakeHTTPResponse(body=b""), "empty provider response"),
    ],
)
def test_fetch_bytes_http_response_failures(
    monkeypatch: pytest.MonkeyPatch,
    response: _FakeHTTPResponse,
    message: str,
) -> None:
    monkeypatch.setattr(urllib.request, "urlopen", lambda *args, **kwargs: response)
    with pytest.raises(PathwayProviderError, match=message):
        fetch_bytes(
            url="https://example.test/provider.json",
            timeout_seconds=1,
            retry_count=0,
            expected_content_type="application/json",
        )


def test_fetch_bytes_retries_transient_url_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    attempts = 0

    def fake_urlopen(*args: object, **kwargs: object) -> _FakeHTTPResponse:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise urllib.error.URLError("temporary")
        return _FakeHTTPResponse()

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    response = fetch_bytes(
        url="https://example.test/provider.json",
        timeout_seconds=1,
        retry_count=1,
        expected_content_type="application/json",
    )
    assert response.status_code == 200
    assert attempts == 2


def test_fetch_bytes_converts_final_url_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_urlopen(*args: object, **kwargs: object) -> _FakeHTTPResponse:
        raise urllib.error.URLError("offline")

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    with pytest.raises(PathwayProviderError, match="provider fetch failed"):
        fetch_bytes(
            url="https://example.test/provider.json",
            timeout_seconds=1,
            retry_count=0,
            expected_content_type=None,
        )


def test_fetch_bytes_retries_transient_http_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    attempts = 0

    def fake_urlopen(*args: object, **kwargs: object) -> _FakeHTTPResponse:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise urllib.error.HTTPError(
                url="https://example.test/provider.json",
                code=503,
                msg="unavailable",
                hdrs=None,
                fp=None,
            )
        return _FakeHTTPResponse()

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    response = fetch_bytes(
        url="https://example.test/provider.json",
        timeout_seconds=1,
        retry_count=1,
        expected_content_type="application/json",
    )
    assert response.status_code == 200
    assert attempts == 2


def test_fetch_bytes_converts_http_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_urlopen(*args: object, **kwargs: object) -> _FakeHTTPResponse:
        raise urllib.error.HTTPError(
            url="https://example.test/provider.json",
            code=503,
            msg="unavailable",
            hdrs=None,
            fp=None,
        )

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    with pytest.raises(PathwayProviderError, match="provider HTTP status 503"):
        fetch_bytes(
            url="https://example.test/provider.json",
            timeout_seconds=1,
            retry_count=0,
            expected_content_type=None,
        )


def test_provider_load_cached_methods(tmp_path) -> None:
    (tmp_path / "omnipath.tsv").write_text("source\ttarget\nA\tB\n")
    (tmp_path / "signor.tsv").write_text("source\ttarget\teffect\nA\tB\tactivation\n")
    (tmp_path / "reactome_fi.tsv").write_text("source\ttarget\nA\tB\n")
    (tmp_path / "reactome_content.tsv").write_text("source\ttarget\tpathway_id\nA\tB\tR\n")
    (tmp_path / "reactome_analysis.tsv").write_text("gene\tpathway_id\tpathway_name\nA\tR\tP\n")
    (tmp_path / "panther.tsv").write_text("gene\tpathway_id\tpathway_name\nA\tP\tP\n")
    assert OmniPathProvider().load_cached(tmp_path).record_count == 1
    assert SignorProvider().load_cached(tmp_path).record_count == 1
    assert ReactomeFIProvider().load_cached(tmp_path).record_count == 1
    assert ReactomeContentProvider().load_cached(tmp_path).record_count == 1
    assert ReactomeAnalysisProvider().load_cached(tmp_path).record_count == 1
    assert PantherProvider().load_cached(tmp_path).record_count == 1


def test_reactome_analysis_result_list_and_empty_panther() -> None:
    records = ReactomeAnalysisProvider().parse_raw(
        [
            {
                "pathway_id": "R",
                "pathway_name": "Path",
                "entities": {"found": ["A"]},
                "observed_count": 1,
                "expected_count": 1,
                "adjusted_p_value": 0.5,
            }
        ],
        snapshot_id="snap",
        organism="human",
    )
    assert records[0].term_id == "R"
    assert (
        PantherProvider().parse_raw({"results": {"result": {}}}, snapshot_id="s", organism="h")
        == []
    )
