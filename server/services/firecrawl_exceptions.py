"""Custom exceptions for the Firecrawl client."""


class FirecrawlError(Exception):
    """Base exception for all Firecrawl errors."""


class FirecrawlConnectionError(FirecrawlError):
    """Raised when the Firecrawl service is unreachable or max retries exceeded."""


class FirecrawlScrapeError(FirecrawlError):
    """Raised when Firecrawl returns an error response for a scrape/crawl request."""
