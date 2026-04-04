# Checked AGENTS.md - implementing directly because these are unit tests for the haiku_extractor service.
"""Unit tests for HaikuExtractor — all Anthropic API calls are mocked."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from server.services.haiku_extractor import HaikuExtractor


@pytest.fixture
def extractor() -> HaikuExtractor:
    return HaikuExtractor(api_key="test-key", max_chars=500)


def _mock_response(text: str) -> MagicMock:
    """Build a mock Anthropic messages.create response."""
    content_block = MagicMock()
    content_block.text = text
    response = MagicMock()
    response.content = [content_block]
    return response


# ---------------------------------------------------------------------------
# Truncation
# ---------------------------------------------------------------------------

class TestTruncate:
    def test_short_content_unchanged(self, extractor):
        md = "short text"
        assert extractor._truncate(md) == md

    def test_long_content_truncated(self, extractor):
        md = "x" * 600
        result = extractor._truncate(md)
        assert len(result) <= extractor.max_chars + 20  # +20 for prefix
        assert result.startswith("...[truncated]")


# ---------------------------------------------------------------------------
# extract — happy path
# ---------------------------------------------------------------------------

class TestExtract:
    @pytest.mark.asyncio
    async def test_returns_structured_result(self, extractor):
        payload = {
            "title": "TSB 21-003",
            "vehicles": [{"year_from": 2019, "year_to": 2022, "make": "Ford", "model": "F-150"}],
            "dtc_codes": ["P0128"],
            "symptoms": ["check engine light"],
            "doc_type": "tsb",
        }
        mock_resp = _mock_response(json.dumps(payload))

        with patch("anthropic.Anthropic") as MockClient:
            MockClient.return_value.messages.create.return_value = mock_resp
            result = await extractor.extract("some markdown", source_url="https://example.com/tsb")

        assert result["title"] == "TSB 21-003"
        assert result["source_url"] == "https://example.com/tsb"
        assert result["doc_type"] == "tsb"

    @pytest.mark.asyncio
    async def test_adds_source_url(self, extractor):
        mock_resp = _mock_response(json.dumps({"doc_type": "forum"}))
        with patch("anthropic.Anthropic") as MockClient:
            MockClient.return_value.messages.create.return_value = mock_resp
            result = await extractor.extract("md", source_url="https://forum.example.com/1")
        assert result["source_url"] == "https://forum.example.com/1"

    @pytest.mark.asyncio
    async def test_defaults_doc_type_unknown(self, extractor):
        mock_resp = _mock_response(json.dumps({"title": "something"}))
        with patch("anthropic.Anthropic") as MockClient:
            MockClient.return_value.messages.create.return_value = mock_resp
            result = await extractor.extract("md")
        assert result["doc_type"] == "unknown"


# ---------------------------------------------------------------------------
# extract — error paths
# ---------------------------------------------------------------------------

class TestExtractErrors:
    @pytest.mark.asyncio
    async def test_empty_markdown_returns_error(self, extractor):
        result = await extractor.extract("")
        assert "error" in result
        assert result["error"] == "empty markdown"

    @pytest.mark.asyncio
    async def test_whitespace_only_returns_error(self, extractor):
        result = await extractor.extract("   \n  ")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_no_api_key_returns_error(self):
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": ""}, clear=False):
            ex = HaikuExtractor(api_key=None, max_chars=500)
        result = await ex.extract("some content")
        assert "error" in result
        assert "ANTHROPIC_API_KEY" in result["error"]

    @pytest.mark.asyncio
    async def test_invalid_json_response(self, extractor):
        mock_resp = _mock_response("not json at all")
        with patch("anthropic.Anthropic") as MockClient:
            MockClient.return_value.messages.create.return_value = mock_resp
            result = await extractor.extract("md")
        assert "error" in result
        assert "json_decode" in result["error"]

    @pytest.mark.asyncio
    async def test_api_exception_returns_error(self, extractor):
        with patch("anthropic.Anthropic") as MockClient:
            MockClient.return_value.messages.create.side_effect = RuntimeError("network error")
            result = await extractor.extract("md")
        assert "error" in result
        assert "network error" in result["error"]


# ---------------------------------------------------------------------------
# extract_batch
# ---------------------------------------------------------------------------

class TestExtractBatch:
    @pytest.mark.asyncio
    async def test_batch_returns_all_results(self, extractor):
        payload = json.dumps({"doc_type": "tsb"})
        mock_resp = _mock_response(payload)

        items = [
            {"markdown": "page one", "url": "https://a.com"},
            {"markdown": "page two", "url": "https://b.com"},
        ]

        with patch("anthropic.Anthropic") as MockClient:
            MockClient.return_value.messages.create.return_value = mock_resp
            results = await extractor.extract_batch(items)

        assert len(results) == 2
        assert results[0]["source_url"] == "https://a.com"
        assert results[1]["source_url"] == "https://b.com"

    @pytest.mark.asyncio
    async def test_batch_empty_list(self, extractor):
        results = await extractor.extract_batch([])
        assert results == []

    @pytest.mark.asyncio
    async def test_batch_handles_missing_keys(self, extractor):
        """Items without 'markdown' or 'url' keys don't crash."""
        results = await extractor.extract_batch([{}])
        assert len(results) == 1
        assert "error" in results[0]
