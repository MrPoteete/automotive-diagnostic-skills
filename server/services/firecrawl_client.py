"""Async HTTP client for the local Firecrawl scraping service."""
from __future__ import annotations

import asyncio
import logging
import os
from typing import Any

import httpx

from server.services.firecrawl_exceptions import (
    FirecrawlConnectionError,
    FirecrawlScrapeError,
)

logger = logging.getLogger(__name__)

_DEFAULT_URL = "http://localhost:3002"
_DEFAULT_TIMEOUT = 30.0


class FirecrawlClient:
    """Async wrapper around the local Firecrawl /v1/scrape and /v1/crawl endpoints.

    Parameters
    ----------
    base_url:
        Override the service URL (defaults to FIRECRAWL_API_URL env var, then
        http://localhost:3002).
    timeout:
        Per-request timeout in seconds.
    max_retries:
        Maximum number of attempts before raising FirecrawlConnectionError.
        Retries are triggered by network errors and 5xx responses.
    """

    def __init__(
        self,
        base_url: str | None = None,
        timeout: float = _DEFAULT_TIMEOUT,
        max_retries: int = 3,
    ) -> None:
        self.base_url = (
            base_url
            or os.environ.get("FIRECRAWL_API_URL", _DEFAULT_URL)
        ).rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries

    async def health_check(self) -> bool:
        """Return True if the Firecrawl service responds to /health."""
        url = f"{self.base_url}/health"
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(url)
                return resp.status_code < 400
        except (httpx.ConnectError, httpx.TimeoutException, Exception):
            return False

    async def scrape(
        self,
        url: str,
        *,
        formats: list[str] | None = None,
        wait_for: int = 0,
    ) -> dict[str, Any]:
        """Scrape a single URL and return the Firecrawl response dict.

        Parameters
        ----------
        url:
            The page to scrape.
        formats:
            Output formats to request, e.g. ["markdown", "html"].
            Defaults to ["markdown"].
        wait_for:
            Milliseconds to wait for JS rendering before extracting content.
        """
        if formats is None:
            formats = ["markdown"]

        payload: dict[str, Any] = {"url": url, "formats": formats}
        if wait_for:
            payload["waitFor"] = wait_for

        return await self._post_with_retry("/v1/scrape", payload)

    async def crawl(
        self,
        url: str,
        *,
        limit: int = 10,
        formats: list[str] | None = None,
    ) -> dict[str, Any]:
        """Start a crawl job and return the Firecrawl response dict."""
        if formats is None:
            formats = ["markdown"]

        payload: dict[str, Any] = {"url": url, "limit": limit, "scrapeOptions": {"formats": formats}}
        return await self._post_with_retry("/v1/crawl", payload)

    async def _post_with_retry(
        self, path: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        """POST to path with exponential-backoff retry logic.

        Retries on:
        - httpx.ConnectError / httpx.TimeoutException
        - HTTP 5xx responses

        Raises FirecrawlConnectionError after max_retries exhausted.
        Raises FirecrawlScrapeError on 4xx responses (not retried).
        """
        endpoint = f"{self.base_url}{path}"
        last_exc: Exception | None = None

        for attempt in range(1, self.max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    resp = await client.post(endpoint, json=payload)

                if resp.status_code >= 500:
                    last_exc = FirecrawlConnectionError(
                        f"Firecrawl returned HTTP {resp.status_code} (attempt {attempt}/{self.max_retries})"
                    )
                    logger.warning(
                        "Firecrawl %s attempt %d/%d: HTTP %d",
                        path, attempt, self.max_retries, resp.status_code,
                    )
                elif resp.status_code >= 400:
                    raise FirecrawlScrapeError(
                        f"Firecrawl {path} failed with HTTP {resp.status_code}: {resp.text[:200]}"
                    )
                else:
                    return resp.json()

            except FirecrawlScrapeError:
                raise
            except (httpx.ConnectError, httpx.TimeoutException) as exc:
                last_exc = exc
                logger.warning(
                    "Firecrawl %s attempt %d/%d: %s",
                    path, attempt, self.max_retries, exc,
                )

            if attempt < self.max_retries:
                backoff = 2 ** (attempt - 1)
                await asyncio.sleep(backoff)

        raise FirecrawlConnectionError(
            f"Firecrawl unreachable at {endpoint} after {self.max_retries} attempts: {last_exc}"
        ) from last_exc
