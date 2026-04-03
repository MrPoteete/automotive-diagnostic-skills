"""Unit tests for FirecrawlClient and the /api/health/firecrawl endpoint.

All tests are fully offline — no running Firecrawl instance required.
Uses httpx.MockTransport to simulate Firecrawl API responses.
"""
from __future__ import annotations

import json
import pytest
import httpx
import pytest_asyncio

from unittest.mock import AsyncMock, patch

from server.services.firecrawl_client import FirecrawlClient
from server.services.firecrawl_exceptions import (
    FirecrawlConnectionError,
    FirecrawlScrapeError,
    FirecrawlError,
)


def _mock_transport(responses: list[httpx.Response]) -> httpx.MockTransport:
    """Return a MockTransport that yields responses in order."""
    call_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        resp = responses[min(call_count, len(responses) - 1)]
        call_count += 1
        return resp

    return httpx.MockTransport(handler)


class TestFirecrawlExceptions:
    def test_hierarchy(self) -> None:
        assert issubclass(FirecrawlConnectionError, FirecrawlError)
        assert issubclass(FirecrawlScrapeError, FirecrawlError)
        assert issubclass(FirecrawlError, Exception)


class TestFirecrawlClientHealthCheck:
    @pytest.mark.asyncio
    async def test_health_check_success(self) -> None:
        ok_resp = httpx.Response(200, json={"status": "ok"})
        client = FirecrawlClient(base_url="http://localhost:3002", max_retries=3)

        with patch("httpx.AsyncClient") as mock_cls:
            mock_http = AsyncMock()
            mock_http.__aenter__ = AsyncMock(return_value=mock_http)
            mock_http.__aexit__ = AsyncMock(return_value=False)
            mock_http.get = AsyncMock(return_value=ok_resp)
            mock_cls.return_value = mock_http

            result = await client.health_check()

        assert result is True

    @pytest.mark.asyncio
    async def test_health_check_failure_on_connect_error(self) -> None:
        client = FirecrawlClient(base_url="http://localhost:3002")

        with patch("httpx.AsyncClient") as mock_cls:
            mock_http = AsyncMock()
            mock_http.__aenter__ = AsyncMock(return_value=mock_http)
            mock_http.__aexit__ = AsyncMock(return_value=False)
            mock_http.get = AsyncMock(side_effect=httpx.ConnectError("refused"))
            mock_cls.return_value = mock_http

            result = await client.health_check()

        assert result is False


class TestFirecrawlClientScrape:
    @pytest.mark.asyncio
    async def test_scrape_success(self) -> None:
        payload = {"success": True, "data": {"markdown": "# Hello"}}
        ok_resp = httpx.Response(200, json=payload)
        client = FirecrawlClient(base_url="http://localhost:3002", max_retries=3)

        with patch("httpx.AsyncClient") as mock_cls:
            mock_http = AsyncMock()
            mock_http.__aenter__ = AsyncMock(return_value=mock_http)
            mock_http.__aexit__ = AsyncMock(return_value=False)
            mock_http.post = AsyncMock(return_value=ok_resp)
            mock_cls.return_value = mock_http

            result = await client.scrape("https://example.com")

        assert result["success"] is True
        assert "markdown" in result["data"]

    @pytest.mark.asyncio
    async def test_scrape_retries_on_connect_error(self) -> None:
        ok_resp = httpx.Response(200, json={"success": True, "data": {}})
        client = FirecrawlClient(base_url="http://localhost:3002", max_retries=3)
        call_count = 0

        async def post_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise httpx.ConnectError("refused")
            return ok_resp

        with patch("httpx.AsyncClient") as mock_cls:
            mock_http = AsyncMock()
            mock_http.__aenter__ = AsyncMock(return_value=mock_http)
            mock_http.__aexit__ = AsyncMock(return_value=False)
            mock_http.post = AsyncMock(side_effect=post_side_effect)
            mock_cls.return_value = mock_http

            with patch("asyncio.sleep", new_callable=AsyncMock):
                result = await client.scrape("https://example.com")

        assert call_count == 3
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_scrape_retries_on_http_500(self) -> None:
        err_resp = httpx.Response(500, text="Internal Server Error")
        ok_resp = httpx.Response(200, json={"success": True, "data": {}})
        client = FirecrawlClient(base_url="http://localhost:3002", max_retries=3)
        call_count = 0

        async def post_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                return err_resp
            return ok_resp

        with patch("httpx.AsyncClient") as mock_cls:
            mock_http = AsyncMock()
            mock_http.__aenter__ = AsyncMock(return_value=mock_http)
            mock_http.__aexit__ = AsyncMock(return_value=False)
            mock_http.post = AsyncMock(side_effect=post_side_effect)
            mock_cls.return_value = mock_http

            with patch("asyncio.sleep", new_callable=AsyncMock):
                result = await client.scrape("https://example.com")

        assert call_count == 3

    @pytest.mark.asyncio
    async def test_max_retries_exceeded_raises_connection_error(self) -> None:
        client = FirecrawlClient(base_url="http://localhost:3002", max_retries=3)

        with patch("httpx.AsyncClient") as mock_cls:
            mock_http = AsyncMock()
            mock_http.__aenter__ = AsyncMock(return_value=mock_http)
            mock_http.__aexit__ = AsyncMock(return_value=False)
            mock_http.post = AsyncMock(side_effect=httpx.ConnectError("refused"))
            mock_cls.return_value = mock_http

            with patch("asyncio.sleep", new_callable=AsyncMock):
                with pytest.raises(FirecrawlConnectionError):
                    await client.scrape("https://example.com")

    @pytest.mark.asyncio
    async def test_scrape_4xx_raises_scrape_error(self) -> None:
        err_resp = httpx.Response(422, json={"error": "invalid url"})
        client = FirecrawlClient(base_url="http://localhost:3002", max_retries=3)

        with patch("httpx.AsyncClient") as mock_cls:
            mock_http = AsyncMock()
            mock_http.__aenter__ = AsyncMock(return_value=mock_http)
            mock_http.__aexit__ = AsyncMock(return_value=False)
            mock_http.post = AsyncMock(return_value=err_resp)
            mock_cls.return_value = mock_http

            with pytest.raises(FirecrawlScrapeError):
                await client.scrape("https://example.com")


from fastapi.testclient import TestClient
from server.home_server import app, get_firecrawl_client


class TestHealthEndpoint:
    def test_health_endpoint_ok(self) -> None:
        async def mock_health_ok() -> bool:
            return True

        mock_client = FirecrawlClient.__new__(FirecrawlClient)
        mock_client.base_url = "http://localhost:3002"
        mock_client.timeout = 30.0
        mock_client.max_retries = 3
        mock_client.health_check = mock_health_ok

        app.dependency_overrides[get_firecrawl_client] = lambda: mock_client
        try:
            with TestClient(app, raise_server_exceptions=False) as tc:
                resp = tc.get("/api/health/firecrawl", headers={"X-API-KEY": "fallback-key-for-dev"})
            assert resp.status_code == 200
            assert resp.json()["status"] == "ok"
        finally:
            app.dependency_overrides.pop(get_firecrawl_client, None)

    def test_health_endpoint_503_when_client_fails(self) -> None:
        async def mock_health_fail() -> bool:
            return False

        mock_client = FirecrawlClient.__new__(FirecrawlClient)
        mock_client.base_url = "http://localhost:3002"
        mock_client.timeout = 30.0
        mock_client.max_retries = 3
        mock_client.health_check = mock_health_fail

        app.dependency_overrides[get_firecrawl_client] = lambda: mock_client
        try:
            with TestClient(app, raise_server_exceptions=False) as tc:
                resp = tc.get("/api/health/firecrawl", headers={"X-API-KEY": "fallback-key-for-dev"})
            assert resp.status_code == 503
            assert resp.json()["status"] == "error"
        finally:
            app.dependency_overrides.pop(get_firecrawl_client, None)
