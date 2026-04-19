"""
ChromaDB service for forum and ebook data retrieval.

Queries two collections in parallel and merges results by relevance:
  - mechanics_forum:     ~570K forum/YT transcript chunks  (confidence 0.5)
  - scannerdanner_ebook: 182 ScannerDanner textbook frames (confidence 0.9)

Ebook collection is optional — service degrades gracefully if absent.
"""

from __future__ import annotations

import logging
import pathlib
from typing import Any

logger = logging.getLogger(__name__)

_CHROMA_PATH = str(
    pathlib.Path(__file__).resolve().parent.parent.parent / "data" / "vector_store" / "chroma"
)
_COLLECTION_NAME = "mechanics_forum"
_EBOOK_COLLECTION_NAME = "scannerdanner_ebook"

# Base confidence by source tier (DOMAIN.md)
FORUM_BASE_CONFIDENCE = 0.5   # Tier 3 — community/forum data
EBOOK_BASE_CONFIDENCE = 0.85  # T5 — professional textbook (ScannerDanner UTM)


class ChromaService:
    """Semantic search over mechanics_forum and scannerdanner_ebook collections."""

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

        # Ebook collection is optional — created separately, may not exist yet
        self._ebook_collection: Any = None
        try:
            self._ebook_collection = self._client.get_collection(name=_EBOOK_COLLECTION_NAME)
            logger.debug(
                "ChromaService: ebook collection loaded count=%d",
                self._ebook_collection.count(),
            )
        except Exception:
            logger.debug("scannerdanner_ebook collection not available — ebook search disabled")

        logger.debug(
            "ChromaService initialized: forum=%d ebook=%s",
            self._collection.count(),
            self._ebook_collection.count() if self._ebook_collection else "n/a",
        )

    @property
    def document_count(self) -> int:
        """Total indexed documents across both collections."""
        total = self._collection.count()
        if self._ebook_collection is not None:
            total += self._ebook_collection.count()
        return total

    def _query_collection(
        self,
        collection: Any,
        base_confidence: float,
        query: str,
        n_results: int,
        min_score: float,
    ) -> list[dict[str, Any]]:
        """Run a query against one collection and return normalised result dicts."""
        if collection.count() == 0:
            return []
        try:
            raw = collection.query(
                query_texts=[query],
                n_results=min(n_results, collection.count()),
                include=["documents", "metadatas", "distances"],
            )
        except Exception as exc:
            logger.error("ChromaService._query_collection failed: %s", exc)
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
            # Ebook metadata stores its own confidence; forum uses the base constant
            confidence = float((meta or {}).get("confidence", base_confidence))
            results.append({
                "id": doc_id,
                "document": doc,
                "metadata": meta or {},
                "distance": round(dist, 4),
                "relevance": round(relevance, 4),
                "confidence": confidence,
            })

        return results

    def search(
        self,
        query: str,
        n_results: int = 10,
        min_score: float = 0.0,
    ) -> list[dict[str, Any]]:
        """
        Semantic search across mechanics_forum and scannerdanner_ebook.

        Results from both collections are merged and sorted by relevance.
        Returns at most n_results results total.

        Returns:
            List of result dicts:
            {
                "id": str,
                "document": str,
                "metadata": dict,
                "distance": float,
                "relevance": float,   # 1 - distance (higher = more relevant)
                "confidence": float,  # 0.5 forum | 0.85–0.9 ebook
            }
        """
        if not query or not query.strip():
            return []

        # Guard: both collections empty
        if self._collection.count() == 0 and (
            self._ebook_collection is None or self._ebook_collection.count() == 0
        ):
            logger.warning("ChromaService: all collections empty — run ingestion scripts")
            return []

        forum_results = self._query_collection(
            self._collection, FORUM_BASE_CONFIDENCE, query, n_results, min_score
        )
        ebook_results: list[dict[str, Any]] = []
        if self._ebook_collection is not None:
            ebook_results = self._query_collection(
                self._ebook_collection, EBOOK_BASE_CONFIDENCE, query, n_results, min_score
            )

        merged = sorted(
            forum_results + ebook_results,
            key=lambda r: r["relevance"],
            reverse=True,
        )[:n_results]

        logger.debug(
            "ChromaService.search(%r): %d forum + %d ebook → %d merged",
            query[:50], len(forum_results), len(ebook_results), len(merged),
        )
        return merged

    def search_for_components(
        self,
        query: str,
        n_results: int = 20,
    ) -> list[dict[str, Any]]:
        """
        Search and extract likely component mentions from results.

        Forum hits contribute via metadata tags.
        Ebook hits (no tags) pass through as raw context but don't
        produce structured component candidates.

        Returns list of {component, count, confidence, source, samples} matching
        the same schema as DiagnosticDB complaint candidates.
        """
        hits = self.search(query, n_results=n_results, min_score=0.3)
        if not hits:
            return []

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
