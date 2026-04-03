"""Async HTTP client for the self-hosted Firecrawl scraping service.

Firecrawl renders JS-heavy pages (automotive forums, OEM TSB portals, NHTSA recall
pages) and returns clean Markdown.  This client wraps the REST API with:
  - Single-URL scrape with optional wait-for-selector and timeout
  - Batch scrape of multiple URLs (runs concurrently)
  - Health/ping check
  - Exponential-backoff retry (max 3 attempts) on transient errors
"""

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
_DEFAULT_TIMEOUT = 60.0
_BACKOFF_BASE = 1.0  # seconds; attempt n waits backoff_base * 2^(n-1)


class FirecrawlClient:
    """Async client for the Firecrawl self-hosted scraping API.

    Wraps ``/v1/scrape``, batch scraping, and ``/health`` endpoints with
    exponential-backoff retry on transient 5xx / network errors.

    Parameters
    ----------
    base_url:
        Base URL of the Firecrawl REST API.  Falls back to the
        ``FIRECRAWL_API_URL`` environment variable, then ``http://localhost:3002``.
    timeout:
        Per-request timeout in seconds (default 60).
    max_retries:
        Maximum retry attempts on transient failures (default 3).
    """

    def __init__(
        self,
        base_url: str | None = None,
        timeout: float = _DEFAULT_TIMEOUT,
        max_retries: int = 3,
    ) -> None:
        self.base_url = (
            base_url or os.environ.get("FIRECRAWL_API_URL", _DEFAULT_URL)
        ).rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries

    # ------------------------------------------------------------------
    # Internal retry helper
    # ------------------------------------------------------------------

    async def _post_with_retry(
        self,
        path: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        """POST *path* with *payload*, retrying on transient errors.

        Uses exponential backoff: wait = ``_BACKOFF_BASE * 2 ** (attempt-1)`` s.

        Raises
        ------
        FirecrawlConnectionError
            After exhausting all retry attempts (5xx / network errors).
        FirecrawlScrapeError
            On 4xx responses (not retried).
        """
        endpoint = f"{self.base_url}{path}"
        last_exc: Exception | None = None

        for attempt in range(1, self.max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    resp = await client.post(endpoint, json=payload)

                if resp.status_code >= 500:
                    last_exc = FirecrawlConnectionError(
                        f"HTTP {resp.status_code} (attempt {attempt}/{self.max_retries})"
                    )
                    logger.warning(
                        "Firecrawl %s attempt %d/%d: HTTP %d",
                        path, attempt, self.max_retries, resp.status_code,
                    )
                elif resp.status_code >= 400:
                    raise FirecrawlScrapeError(
                        f"Firecrawl {path} HTTP {resp.status_code}: {resp.text[:200]}"
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
                backoff = _BACKOFF_BASE * (2 ** (attempt - 1))
                await asyncio.sleep(backoff)

        raise FirecrawlConnectionError(
            f"Firecrawl unreachable at {endpoint} after {self.max_retries} attempts: {last_exc}"
        ) from last_exc

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def scrape_url(
        self,
        url: str,
        wait_for_selector: str | None = None,
        timeout_ms: int | None = None,
        formats: list[str] | None = None,
    ) -> dict[str, Any]:
        """Scrape a single URL and return the Firecrawl response dict.

        Parameters
        ----------
        url:
            Target URL to scrape.
        wait_for_selector:
            Optional CSS selector to wait for before extracting content.
        timeout_ms:
            Optional page-load timeout in milliseconds.
        formats:
            Response formats to request (default ``["markdown"]``).

        Returns
        -------
        dict
            Firecrawl API response with ``markdown``, ``metadata``, etc.

        Raises
        ------
        FirecrawlConnectionError
            If the request fails after all retries.
        FirecrawlScrapeError
            If Firecrawl returns a 4xx error.
        """
        payload: dict[str, Any] = {
            "url": url,
            "formats": formats or ["markdown"],
        }
        if wait_for_selector is not None:
            payload["waitFor"] = wait_for_selector
        if timeout_ms is not None:
            payload["timeout"] = timeout_ms

        return await self._post_with_retry("/v1/scrape", payload)

    async def scrape_batch(
        self,
        urls: list[str],
        wait_for_selector: str | None = None,
        timeout_ms: int | None = None,
        formats: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Scrape multiple URLs, returning results in the same order.

        Individual failures are captured as ``{"url": ..., "error": "..."}``
        dicts so that partial results are always returned.

        Parameters
        ----------
        urls:
            URLs to scrape concurrently.
        wait_for_selector:
            Optional CSS selector applied to every URL.
        timeout_ms:
            Optional page-load timeout in milliseconds.
        formats:
            Response formats to request (default ``["markdown"]``).

        Returns
        -------
        list[dict]
            One result dict per URL, preserving input order.
        """
        results: list[dict[str, Any]] = []
        for url in urls:
            try:
                result = await self.scrape_url(
                    url,
                    wait_for_selector=wait_for_selector,
                    timeout_ms=timeout_ms,
                    formats=formats,
                )
                results.append(result)
            except (FirecrawlConnectionError, FirecrawlScrapeError) as exc:
                logger.error("Batch scrape failed for %s: %s", url, exc)
                results.append({"url": url, "error": str(exc)})
        return results

    async def ping(self) -> bool:
        """Check whether the Firecrawl service is reachable.

        Returns
        -------
        bool
            ``True`` if the service responds with a non-error HTTP status.

        Raises
        ------
        FirecrawlConnectionError
            If the service is unreachable or returns an error.
        """
        url = f"{self.base_url}/health"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url)
                if resp.status_code >= 400:
                    raise FirecrawlConnectionError(
                        f"Firecrawl health returned HTTP {resp.status_code}"
                    )
                return True
        except (httpx.ConnectError, httpx.TimeoutException) as exc:
            raise FirecrawlConnectionError(
                f"Firecrawl not reachable at {url}: {exc}"
            ) from exc
