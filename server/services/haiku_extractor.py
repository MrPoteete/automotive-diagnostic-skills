# Checked AGENTS.md - implementing directly because this IS the Haiku delegation layer itself.
# Checked HAIKU_DELEGATION.md - Haiku extractor is core infrastructure, not a simple boilerplate task.
"""Haiku-powered content extractor for Firecrawl scraped markdown.

Firecrawl returns raw markdown from TSB portals, NHTSA pages, and forums.
This module uses Claude Haiku to strip boilerplate and extract structured data,
keeping costs low while handling high-volume scraping sessions.

Usage::

    extractor = HaikuExtractor()
    result = await extractor.extract(markdown, source_url="https://...")
    # result: {"vehicles": [...], "symptoms": [...], "procedure": "...", "source_url": "..."}
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

_HAIKU_MODEL = "claude-haiku-4-5-20251001"

_EXTRACTION_PROMPT = """\
You are a technical extraction assistant for automotive repair content.

Given scraped markdown from a TSB portal, NHTSA page, or forum post, extract ONLY the factual content.
Ignore navigation, ads, cookie notices, headers, footers, and boilerplate.

Return a JSON object with these fields (omit fields you cannot find):
{
  "title": "document or thread title",
  "vehicles": [{"year_from": 2018, "year_to": 2022, "make": "Ford", "model": "F-150"}],
  "dtc_codes": ["P0128", "P0301"],
  "symptoms": ["rough idle", "check engine light"],
  "cause": "brief root cause if stated",
  "procedure": "repair procedure or diagnostic steps (plain text, concise)",
  "parts": ["thermostat", "coolant temperature sensor"],
  "doc_type": "tsb" | "recall" | "forum" | "unknown"
}

Return ONLY valid JSON — no explanation, no markdown fences.

MARKDOWN TO EXTRACT:
"""


class HaikuExtractor:
    """Extract structured automotive data from Firecrawl markdown using Claude Haiku.

    Parameters
    ----------
    api_key:
        Anthropic API key. Falls back to ``ANTHROPIC_API_KEY`` env var.
    max_chars:
        Maximum markdown characters sent to Haiku (default 8000).
        Longer content is truncated from the front to keep the most relevant tail.
    """

    def __init__(
        self,
        api_key: str | None = None,
        max_chars: int = 8000,
    ) -> None:
        self._api_key = api_key if api_key is not None else os.environ.get("ANTHROPIC_API_KEY", "")
        self.max_chars = max_chars

    def _truncate(self, markdown: str) -> str:
        """Keep the last max_chars characters — usually the most content-rich."""
        if len(markdown) <= self.max_chars:
            return markdown
        return "...[truncated]\n" + markdown[-self.max_chars :]

    async def extract(
        self,
        markdown: str,
        source_url: str = "",
    ) -> dict[str, Any]:
        """Extract structured automotive data from scraped markdown.

        Parameters
        ----------
        markdown:
            Raw markdown returned by Firecrawl.
        source_url:
            Origin URL — added to the result for provenance tracking.

        Returns
        -------
        dict
            Structured extraction result. Always includes ``source_url`` and
            ``doc_type``. Returns ``{"error": "...", "source_url": "..."}``
            on failure rather than raising.
        """
        if not markdown or not markdown.strip():
            return {"error": "empty markdown", "source_url": source_url}

        try:
            import anthropic  # type: ignore[import-untyped]
        except ImportError:
            logger.error("anthropic package not installed")
            return {"error": "anthropic not installed", "source_url": source_url}

        if not self._api_key:
            logger.error("ANTHROPIC_API_KEY not set")
            return {"error": "ANTHROPIC_API_KEY not set", "source_url": source_url}

        content = self._truncate(markdown)
        prompt = _EXTRACTION_PROMPT + content

        try:
            client = anthropic.Anthropic(api_key=self._api_key)
            # Run sync client in executor to stay async-friendly
            loop = asyncio.get_running_loop()
            response = await loop.run_in_executor(
                None,
                lambda: client.messages.create(
                    model=_HAIKU_MODEL,
                    max_tokens=1024,
                    messages=[{"role": "user", "content": prompt}],
                ),
            )

            raw = response.content[0].text.strip()
            result: dict[str, Any] = json.loads(raw)
            result["source_url"] = source_url
            result.setdefault("doc_type", "unknown")
            return result

        except json.JSONDecodeError as exc:
            logger.warning("Haiku returned non-JSON: %s", exc)
            return {"error": f"json_decode: {exc}", "source_url": source_url, "raw": raw}
        except Exception as exc:
            logger.error("HaikuExtractor error: %s", exc)
            return {"error": str(exc), "source_url": source_url}

    async def extract_batch(
        self,
        items: list[dict[str, str]],
    ) -> list[dict[str, Any]]:
        """Extract from multiple {markdown, url} dicts concurrently.

        Parameters
        ----------
        items:
            List of ``{"markdown": "...", "url": "..."}`` dicts,
            matching the shape returned by ``FirecrawlClient.scrape_batch``.

        Returns
        -------
        list[dict]
            One result per input item, preserving order.
        """
        tasks = [
            self.extract(item.get("markdown", ""), source_url=item.get("url", ""))
            for item in items
        ]
        return list(await asyncio.gather(*tasks))
