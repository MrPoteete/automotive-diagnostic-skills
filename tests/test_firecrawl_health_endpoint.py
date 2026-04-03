"""Integration tests for the /api/firecrawl/health FastAPI endpoint.

All tests use mocked FirecrawlClient.ping() — no live Firecrawl required.
"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

from server.home_server import app
from server.services.firecrawl_exceptions import FirecrawlConnectionError

# The app requires the X-API-KEY header; read from env or use the dev fallback.
import os
_API_KEY = os.environ.get("API_KEY", "fallback-key-for-dev")
_HEADERS = {"X-API-KEY": _API_KEY}


def test_firecrawl_health_endpoint_ok() -> None:
    """GET /api/firecrawl/health returns 200 with status=ok when ping() succeeds."""
    with patch(
        "server.services.firecrawl_client.FirecrawlClient.ping",
        new_callable=AsyncMock,
        return_value=True,
    ):
        with TestClient(app, raise_server_exceptions=True) as client:
            resp = client.get("/api/firecrawl/health", headers=_HEADERS)

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert "url" in body


def test_firecrawl_health_endpoint_unavailable() -> None:
    """GET /api/firecrawl/health returns 503 when ping() raises FirecrawlConnectionError."""
    with patch(
        "server.services.firecrawl_client.FirecrawlClient.ping",
        new_callable=AsyncMock,
        side_effect=FirecrawlConnectionError("Connection refused"),
    ):
        with TestClient(app, raise_server_exceptions=False) as client:
            resp = client.get("/api/firecrawl/health", headers=_HEADERS)

    assert resp.status_code == 503
    body = resp.json()
    # FastAPI wraps HTTPException detail as {"detail": ...}
    assert "detail" in body
