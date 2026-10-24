import asyncio

import httpx
import pytest

from scripts.ingest_january import fetch


def run_fetch(handler, dataset="WINDFOR", params=None):
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    try:
        return asyncio.run(fetch(client, dataset, params or {}))
    finally:
        asyncio.run(client.aclose())


def test_fetch_uses_official_stream_route_and_preserves_empty_array():
    requested = []

    def handler(request):
        requested.append(request)
        return httpx.Response(200, json=[])

    assert run_fetch(handler) == []
    assert requested[0].url.path.endswith("/datasets/WINDFOR/stream")
    assert requested[0].headers["accept"] == "application/json"


def test_fetch_retries_transient_server_error():
    attempts = 0

    def handler(_request):
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return httpx.Response(503, text="temporarily unavailable", headers={"Retry-After": "0"})
        return httpx.Response(200, json=[{"startTime": "2026-01-01T00:00:00Z"}])

    assert len(run_fetch(handler)) == 1
    assert attempts == 2


def test_fetch_reports_malformed_response_with_bounded_excerpt(capsys):
    def handler(_request):
        return httpx.Response(200, text="not-json", headers={"content-type": "text/plain"})

    with pytest.raises(ValueError, match="Malformed JSON"):
        run_fetch(handler)


def test_fetch_rejects_pagination_metadata_instead_of_truncating():
    def handler(_request):
        return httpx.Response(200, json={"data": [], "next": "https://example.invalid/next"})

    with pytest.raises(ValueError, match="pagination"):
        run_fetch(handler)


def test_fetch_does_not_retry_bad_request_and_logs_response_details(capsys):
    attempts = 0

    def handler(_request):
        nonlocal attempts
        attempts += 1
        return httpx.Response(400, text="invalid parameter", headers={"content-type": "text/plain"})

    with pytest.raises(httpx.HTTPStatusError):
        run_fetch(handler)
    assert attempts == 1
    output = capsys.readouterr().err
    assert "status=400" in output
    assert "content_type=text/plain" in output
    assert "invalid parameter" in output
