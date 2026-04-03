"""Unit tests for FirecrawlClient.

All tests are fully offline — no running Firecrawl instance required.
Uses unittest.mock to simulate httpx responses.
"""
from __future__ import annotations

import pytest
import httpx

from unittest.mock import AsyncMock, patch, MagicMock

from server.services.firecrawl_client import FirecrawlClient
from server.services.firecrawl_exceptions import (
    FirecrawlConnectionError,
    FirecrawlScrapeError,
    FirecrawlError,
)

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _async_client_mock(get_resp: httpx.Response | None = None, post_resp: httpx.Response | None = None) -> MagicMock:
    """Build a mock httpx.AsyncClient context manager."""
    mock_http = AsyncMock()
    mock_http.__aenter__ = AsyncMock(return_value=mock_http)
    mock_http.__aexit__ = AsyncMock(return_value=False)
    if get_resp is not None:
        mock_http.get = AsyncMock(return_value=get_resp)
    if post_resp is not None:
        mock_http.post = AsyncMock(return_value=post_resp)
    return mock_http


# ---------------------------------------------------------------------------
# Exception hierarchy
# ---------------------------------------------------------------------------

def test_firecrawl_exception_hierarchy() -> None:
    assert issubclass(FirecrawlConnectionError, FirecrawlError)
    assert issubclass(FirecrawlScrapeError, FirecrawlError)
    assert issubclass(FirecrawlError, Exception)


# ---------------------------------------------------------------------------
# ping() — success and failure
# ---------------------------------------------------------------------------

async def test_firecrawl_ping_success() -> None:
    """ping() returns True when the health endpoint returns 200."""
    ok_resp = httpx.Response(200, json={"status": "ok"})
    client = FirecrawlClient(base_url="http://localhost:3002")

    with patch("httpx.AsyncClient") as mock_cls:
        mock_cls.return_value = _async_client_mock(get_resp=ok_resp)
        result = await client.ping()

    assert result is True


async def test_firecrawl_ping_failure_connect_error() -> None:
    """ping() raises FirecrawlConnectionError on connection refused."""
    client = FirecrawlClient(base_url="http://localhost:3002")

    with patch("httpx.AsyncClient") as mock_cls:
        mock_http = _async_client_mock()
        mock_http.get = AsyncMock(side_effect=httpx.ConnectError("refused"))
        mock_cls.return_value = mock_http

        with pytest.raises(FirecrawlConnectionError):
            await client.ping()


async def test_firecrawl_ping_failure_timeout() -> None:
    """ping() raises FirecrawlConnectionError on timeout."""
    client = FirecrawlClient(base_url="http://localhost:3002")

    with patch("httpx.AsyncClient") as mock_cls:
        mock_http = _async_client_mock()
        mock_http.get = AsyncMock(side_effect=httpx.TimeoutException("timeout"))
        mock_cls.return_value = mock_http

        with pytest.raises(FirecrawlConnectionError):
            await client.ping()


# ---------------------------------------------------------------------------
# scrape_url() — success, HTTP 500, HTTP 4xx, timeout
# ---------------------------------------------------------------------------

async def test_firecrawl_scrape_url_success() -> None:
    """scrape_url() returns the parsed JSON on HTTP 200."""
    payload = {"success": True, "data": {"markdown": "# Recall Notice"}}
    ok_resp = httpx.Response(200, json=payload)
    client = FirecrawlClient(base_url="http://localhost:3002", max_retries=3)

    with patch("httpx.AsyncClient") as mock_cls:
        mock_cls.return_value = _async_client_mock(post_resp=ok_resp)
        result = await client.scrape_url("https://example.com/recall")

    assert result["success"] is True
    assert result["data"]["markdown"] == "# Recall Notice"


async def test_firecrawl_scrape_url_http500_retries_then_succeeds() -> None:
    """scrape_url() retries on HTTP 500 and succeeds on the third attempt."""
    err_resp = httpx.Response(500, text="Internal Server Error")
    ok_resp = httpx.Response(200, json={"success": True, "data": {}})
    client = FirecrawlClient(base_url="http://localhost:3002", max_retries=3)
    call_count = 0

    async def post_side_effect(*args: object, **kwargs: object) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        return ok_resp if call_count >= 3 else err_resp

    with patch("httpx.AsyncClient") as mock_cls:
        mock_http = _async_client_mock()
        mock_http.post = AsyncMock(side_effect=post_side_effect)
        mock_cls.return_value = mock_http

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await client.scrape_url("https://example.com")

    assert call_count == 3
    assert result["success"] is True


async def test_firecrawl_scrape_url_4xx_raises_scrape_error() -> None:
    """scrape_url() raises FirecrawlScrapeError immediately on HTTP 422 (not retried)."""
    err_resp = httpx.Response(422, json={"error": "invalid url"})
    client = FirecrawlClient(base_url="http://localhost:3002", max_retries=3)

    with patch("httpx.AsyncClient") as mock_cls:
        mock_cls.return_value = _async_client_mock(post_resp=err_resp)

        with pytest.raises(FirecrawlScrapeError):
            await client.scrape_url("not-a-url")


async def test_firecrawl_scrape_url_timeout_raises_after_retries() -> None:
    """scrape_url() raises FirecrawlConnectionError after max retries on TimeoutException."""
    client = FirecrawlClient(base_url="http://localhost:3002", max_retries=3)

    with patch("httpx.AsyncClient") as mock_cls:
        mock_http = _async_client_mock()
        mock_http.post = AsyncMock(side_effect=httpx.TimeoutException("timeout"))
        mock_cls.return_value = mock_http

        with patch("asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(FirecrawlConnectionError):
                await client.scrape_url("https://example.com")


async def test_firecrawl_scrape_url_retry_exhaustion() -> None:
    """scrape_url() raises after exactly max_retries attempts."""
    client = FirecrawlClient(base_url="http://localhost:3002", max_retries=3)
    call_count = 0

    async def post_side_effect(*args: object, **kwargs: object) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        raise httpx.ConnectError("refused")

    with patch("httpx.AsyncClient") as mock_cls:
        mock_http = _async_client_mock()
        mock_http.post = AsyncMock(side_effect=post_side_effect)
        mock_cls.return_value = mock_http

        with patch("asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(FirecrawlConnectionError):
                await client.scrape_url("https://example.com")

    assert call_count == 3  # exactly max_retries attempts


# ---------------------------------------------------------------------------
# scrape_batch() — success and partial failure
# ---------------------------------------------------------------------------

async def test_firecrawl_scrape_batch_success() -> None:
    """scrape_batch() returns one result dict per URL on success."""
    ok_payload = {"success": True, "data": {"markdown": "# Page"}}
    ok_resp = httpx.Response(200, json=ok_payload)
    client = FirecrawlClient(base_url="http://localhost:3002", max_retries=1)

    with patch("httpx.AsyncClient") as mock_cls:
        mock_cls.return_value = _async_client_mock(post_resp=ok_resp)
        results = await client.scrape_batch(
            ["https://example.com/a", "https://example.com/b"]
        )

    assert len(results) == 2
    assert all(r.get("success") is True for r in results)


async def test_firecrawl_scrape_batch_partial_failure() -> None:
    """scrape_batch() includes error dicts for failed URLs, success for others."""
    ok_payload = {"success": True, "data": {"markdown": "# Good"}}
    ok_resp = httpx.Response(200, json=ok_payload)
    err_resp = httpx.Response(500, text="Server Error")
    client = FirecrawlClient(base_url="http://localhost:3002", max_retries=1)
    call_count = 0

    async def post_side_effect(*args: object, **kwargs: object) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        return err_resp if call_count == 1 else ok_resp

    with patch("httpx.AsyncClient") as mock_cls:
        mock_http = _async_client_mock()
        mock_http.post = AsyncMock(side_effect=post_side_effect)
        mock_cls.return_value = mock_http

        with patch("asyncio.sleep", new_callable=AsyncMock):
            results = await client.scrape_batch(
                ["https://fail.example.com", "https://ok.example.com"]
            )

    assert len(results) == 2
    assert "error" in results[0]  # first URL failed
    assert results[1].get("success") is True  # second URL succeeded
