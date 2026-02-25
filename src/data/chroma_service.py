"""
ChromaDB service for forum data retrieval (Phase 4).

Checked AGENTS.md - implementing directly because:
1. This is the data layer integration point for the diagnostic engine
2. Must correctly apply 0.5 base confidence (DOMAIN.md Tier 3 community data)
3. Integrates with confidence_scorer and engine_agent (safety-critical orchestration)

Provides semantic search over 24K StackExchange mechanics Q&A.
Collection: mechanics_forum
Confidence: 0.5 base (forum/community data per DOMAIN.md)
"""

from __future__ import annotations

import logging
import pathlib
from typing import Any

logger = logging.getLogger(__name__)

# Absolute path so ChromaDB works regardless of launch directory
_CHROMA_PATH = str(
    pathlib.Path(__file__).resolve().parent.parent.parent / "data" / "vector_store" / "chroma"
)
_COLLECTION_NAME = "mechanics_forum"

# Base confidence for community/forum data (DOMAIN.md Tier 3)
FORUM_BASE_CONFIDENCE = 0.5


class ChromaService:
    """Thin wrapper around ChromaDB for forum semantic search."""

    def __init__(self, path: str = _CHROMA_PATH) -> None:
        try:
            import chromadb  # type: ignore[import-untyped]
        except ImportError as exc:
            raise ImportError("chromadb not installed. Run: pip install chromadb") from exc

        self._client = chromadb.PersistentClient(path=path)
        self._collection = self._client.get_or_create_collection(
            name=_COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
        logger.debug(
            "ChromaService initialized: collection=%s count=%d",
            _COLLECTION_NAME,
            self._collection.count(),
        )

    @property
    def document_count(self) -> int:
        """Number of indexed forum documents."""
        return self._collection.count()

    def search(
        self,
        query: str,
        n_results: int = 10,
        min_score: float = 0.0,
    ) -> list[dict[str, Any]]:
        """
        Semantic search over indexed forum posts.

        Args:
            query: Natural language query (symptoms, component names, etc.)
            n_results: Max results to return
            min_score: Minimum relevance score (0.0–1.0; 1.0 = perfect cosine match)

        Returns:
            List of result dicts:
            {
                "id": str,
                "document": str,
                "metadata": {source, year, tags, score, url, is_answered},
                "distance": float,       # cosine distance (lower = more similar)
                "relevance": float,      # 1 - distance (higher = more relevant)
                "confidence": float,     # FORUM_BASE_CONFIDENCE (0.5)
            }
        """
        if not query or not query.strip():
            return []

        if self._collection.count() == 0:
            logger.warning("ChromaService: collection is empty — run scripts/index_forum_data.py")
            return []

        try:
            raw = self._collection.query(
                query_texts=[query],
                n_results=min(n_results, self._collection.count()),
                include=["documents", "metadatas", "distances"],
            )
        except Exception as exc:
            logger.error("ChromaService.search failed: %s", exc)
            return []

        results: list[dict[str, Any]] = []
        documents = (raw.get("documents") or [[]])[0]
        metadatas = (raw.get("metadatas") or [[]])[0]
        distances = (raw.get("distances") or [[]])[0]
        ids = (raw.get("ids") or [[]])[0]

        for doc_id, doc, meta, dist in zip(ids, documents, metadatas, distances):
            relevance = max(0.0, 1.0 - dist)
            if relevance < min_score:
                continue
            results.append({
                "id": doc_id,
                "document": doc,
                "metadata": meta or {},
                "distance": round(dist, 4),
                "relevance": round(relevance, 4),
                "confidence": FORUM_BASE_CONFIDENCE,
            })

        logger.debug("ChromaService.search(%r): %d results", query[:50], len(results))
        return results

    def search_for_components(
        self,
        query: str,
        n_results: int = 20,
    ) -> list[dict[str, Any]]:
        """
        Search and extract likely component mentions from results.

        Returns list of {component, count, confidence, samples} matching
        the same schema as DiagnosticDB complaint candidates, so engine_agent
        can merge them uniformly.
        """
        hits = self.search(query, n_results=n_results, min_score=0.3)
        if not hits:
            return []

        # Extract tag-based components from metadata
        component_hits: dict[str, list[dict]] = {}
        for hit in hits:
            tags_str = hit["metadata"].get("tags", "")
            tags = [t.strip() for t in tags_str.split(",") if t.strip()]
            for tag in tags:
                component = tag.upper()
                if component not in component_hits:
                    component_hits[component] = []
                component_hits[component].append(hit)

        candidates = []
        for component, component_results in sorted(
            component_hits.items(), key=lambda x: -len(x[1])
        ):
            top = component_results[:3]
            candidates.append({
                "component": component,
                "count": len(component_results),
                "confidence": FORUM_BASE_CONFIDENCE,
                "source": "forum",
                "samples": [
                    {
                        "summary": r["document"][:200],
                        "url": r["metadata"].get("url", ""),
                        "year": r["metadata"].get("year"),
                        "relevance": r["relevance"],
                    }
                    for r in top
                ],
            })

        return candidates[:10]
