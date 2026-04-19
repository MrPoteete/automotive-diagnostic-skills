# Checked AGENTS.md - delegated to quality-engineer agent
"""
Unit tests for src/data/chroma_service.py

Coverage targets (per TESTING.md): data layer utilities -> 80%+

All chromadb imports are fully mocked so this suite runs in CI
even when chromadb is not installed.

Test categories:
- ChromaService.__init__: success path, missing chromadb ImportError
- ChromaService.document_count: delegates to collection.count()
- ChromaService.search: empty query, empty collection, normal results,
                        min_score filtering, exception resilience
- ChromaService.search_for_components: no hits, result schema validation,
                                       confidence constant, source field,
                                       tag extraction and deduplication
"""

import sys
import types
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers: build a minimal fake chromadb module so we can import the service
# without the real package being installed.
# ---------------------------------------------------------------------------

def _make_fake_chromadb(
    collection: MagicMock | None = None,
    ebook_collection: MagicMock | None = None,
) -> types.ModuleType:
    """Return a fake chromadb module whose PersistentClient returns *collection*.

    By default, get_collection (used for the ebook) raises ValueError so the
    ebook collection is None and existing tests remain unaffected.
    Pass ebook_collection to test the dual-collection path.
    """
    fake_chromadb = types.ModuleType("chromadb")
    mock_client = MagicMock(name="PersistentClient_instance")
    if collection is None:
        collection = MagicMock(name="collection")
        collection.count.return_value = 0
    mock_client.get_or_create_collection.return_value = collection
    if ebook_collection is None:
        mock_client.get_collection.side_effect = ValueError("collection not found")
    else:
        mock_client.get_collection.return_value = ebook_collection
    fake_chromadb.PersistentClient = MagicMock(return_value=mock_client)  # type: ignore[attr-defined]
    return fake_chromadb


def _make_collection(count: int = 10) -> MagicMock:
    """Return a mock ChromaDB collection with a configurable document count."""
    col = MagicMock(name="collection")
    col.count.return_value = count
    return col


def _build_query_response(
    ids: list[str],
    documents: list[str],
    metadatas: list[dict],
    distances: list[float],
) -> dict:
    """Build the dict structure that chromadb.Collection.query() returns."""
    return {
        "ids": [ids],
        "documents": [documents],
        "metadatas": [metadatas],
        "distances": [distances],
    }


# ===========================================================================
# ChromaService.__init__
# ===========================================================================


class TestChromaServiceInit:
    """Tests for ChromaService.__init__."""

    @pytest.mark.unit
    def test_init_success_creates_client(self):
        """Successful init must call PersistentClient with the given path."""
        col = _make_collection(count=0)
        fake = _make_fake_chromadb(collection=col)

        with patch.dict(sys.modules, {"chromadb": fake}):
            from src.data.chroma_service import ChromaService
            ChromaService(path="/tmp/test_chroma")

        fake.PersistentClient.assert_called_once_with(path="/tmp/test_chroma")  # type: ignore[attr-defined]

    @pytest.mark.unit
    def test_init_success_creates_collection(self):
        """Successful init must call get_or_create_collection for mechanics_forum."""
        col = _make_collection(count=0)
        fake = _make_fake_chromadb(collection=col)

        with patch.dict(sys.modules, {"chromadb": fake}):
            from src.data.chroma_service import ChromaService
            ChromaService(path="/tmp/test_chroma")

        client_instance = fake.PersistentClient.return_value  # type: ignore[attr-defined]
        client_instance.get_or_create_collection.assert_called_once_with(
            name="mechanics_forum",
            metadata={"hnsw:space": "cosine"},
        )

    @pytest.mark.unit
    def test_init_attempts_ebook_collection(self):
        """Init must attempt to load scannerdanner_ebook via get_collection."""
        col = _make_collection(count=0)
        fake = _make_fake_chromadb(collection=col)

        with patch.dict(sys.modules, {"chromadb": fake}):
            from src.data.chroma_service import ChromaService
            ChromaService(path="/tmp/test_chroma")

        client_instance = fake.PersistentClient.return_value  # type: ignore[attr-defined]
        client_instance.get_collection.assert_called_once_with(name="scannerdanner_ebook")

    @pytest.mark.unit
    def test_init_ebook_unavailable_does_not_raise(self):
        """If scannerdanner_ebook collection is absent, init must succeed silently."""
        col = _make_collection(count=5)
        fake = _make_fake_chromadb(collection=col)  # get_collection raises by default

        with patch.dict(sys.modules, {"chromadb": fake}):
            from src.data.chroma_service import ChromaService
            svc = ChromaService()  # must not raise

        assert svc._ebook_collection is None

    @pytest.mark.unit
    def test_init_raises_import_error_if_chromadb_missing(self):
        """ImportError must be raised (not swallowed) when chromadb is absent."""
        with patch.dict(sys.modules, {"chromadb": None}):
            # Remove the cached import so the module re-executes the import
            sys.modules.pop("src.data.chroma_service", None)
            import importlib
            import src.data.chroma_service as mod
            importlib.reload(mod)

            with pytest.raises(ImportError, match="chromadb not installed"):
                mod.ChromaService()

    @pytest.mark.unit
    def test_init_calls_count_for_debug_logging(self):
        """__init__ must call collection.count() (used in the debug log statement)."""
        col = _make_collection(count=7)
        fake = _make_fake_chromadb(collection=col)

        with patch.dict(sys.modules, {"chromadb": fake}):
            from src.data.chroma_service import ChromaService
            ChromaService(path="/tmp/test_chroma")

        col.count.assert_called()


# ===========================================================================
# ChromaService.document_count
# ===========================================================================


class TestDocumentCount:
    """Tests for ChromaService.document_count property."""

    @pytest.mark.unit
    def test_document_count_forum_only(self):
        """document_count without ebook collection returns forum count only."""
        col = _make_collection(count=24_000)
        fake = _make_fake_chromadb(collection=col)

        with patch.dict(sys.modules, {"chromadb": fake}):
            from src.data.chroma_service import ChromaService
            svc = ChromaService()

        col.count.reset_mock()
        col.count.return_value = 24_000
        assert svc.document_count == 24_000

    @pytest.mark.unit
    def test_document_count_zero_for_empty_collection(self):
        """document_count must return 0 when the forum collection is empty."""
        col = _make_collection(count=0)
        fake = _make_fake_chromadb(collection=col)

        with patch.dict(sys.modules, {"chromadb": fake}):
            from src.data.chroma_service import ChromaService
            svc = ChromaService()

        col.count.reset_mock()
        col.count.return_value = 0
        assert svc.document_count == 0

    @pytest.mark.unit
    def test_document_count_sums_both_collections(self):
        """document_count must return forum + ebook counts when ebook is present."""
        col = _make_collection(count=1000)
        ebook_col = _make_collection(count=182)
        fake = _make_fake_chromadb(collection=col, ebook_collection=ebook_col)

        with patch.dict(sys.modules, {"chromadb": fake}):
            from src.data.chroma_service import ChromaService
            svc = ChromaService()

        col.count.reset_mock()
        col.count.return_value = 1000
        ebook_col.count.reset_mock()
        ebook_col.count.return_value = 182
        assert svc.document_count == 1182


# ===========================================================================
# ChromaService.search
# ===========================================================================


class TestSearch:
    """Tests for ChromaService.search(query, n_results, min_score)."""

    # -- Guard-rail: early returns ----------------------------------------

    @pytest.mark.unit
    def test_empty_query_returns_empty_list(self):
        """search('') must return [] without calling collection.query."""
        col = _make_collection(count=5)
        fake = _make_fake_chromadb(collection=col)

        with patch.dict(sys.modules, {"chromadb": fake}):
            from src.data.chroma_service import ChromaService
            svc = ChromaService()

        result = svc.search("")
        assert result == []
        col.query.assert_not_called()

    @pytest.mark.unit
    def test_whitespace_only_query_returns_empty_list(self):
        """search('   ') must return [] (whitespace-only is treated as empty)."""
        col = _make_collection(count=5)
        fake = _make_fake_chromadb(collection=col)

        with patch.dict(sys.modules, {"chromadb": fake}):
            from src.data.chroma_service import ChromaService
            svc = ChromaService()

        result = svc.search("   ")
        assert result == []
        col.query.assert_not_called()

    @pytest.mark.unit
    def test_empty_collection_returns_empty_list(self):
        """search on an empty collection must return [] and log a warning."""
        col = _make_collection(count=0)
        fake = _make_fake_chromadb(collection=col)

        with patch.dict(sys.modules, {"chromadb": fake}):
            from src.data.chroma_service import ChromaService
            svc = ChromaService()

        result = svc.search("engine misfire")
        assert result == []
        col.query.assert_not_called()

    # -- Normal query path ------------------------------------------------

    @pytest.mark.unit
    def test_normal_query_returns_structured_results(self):
        """Valid query on non-empty collection must return a list of result dicts."""
        col = _make_collection(count=3)
        col.query.return_value = _build_query_response(
            ids=["doc1", "doc2"],
            documents=["Engine misfires at idle", "Rough idle after cold start"],
            metadatas=[
                {"source": "stackexchange", "year": 2021, "tags": "engine,misfire", "url": "http://a.com"},
                {"source": "stackexchange", "year": 2022, "tags": "idle", "url": "http://b.com"},
            ],
            distances=[0.1, 0.3],
        )
        fake = _make_fake_chromadb(collection=col)

        with patch.dict(sys.modules, {"chromadb": fake}):
            from src.data.chroma_service import ChromaService
            svc = ChromaService()

        results = svc.search("engine misfire")
        assert len(results) == 2

    @pytest.mark.unit
    def test_result_schema_has_required_keys(self):
        """Every result must have id, document, metadata, distance, relevance, confidence."""
        col = _make_collection(count=1)
        col.query.return_value = _build_query_response(
            ids=["doc1"],
            documents=["Misfire on cylinder 3"],
            metadatas=[{"source": "stackexchange", "tags": "engine"}],
            distances=[0.2],
        )
        fake = _make_fake_chromadb(collection=col)

        with patch.dict(sys.modules, {"chromadb": fake}):
            from src.data.chroma_service import ChromaService
            svc = ChromaService()

        result = svc.search("misfire")[0]
        for key in ("id", "document", "metadata", "distance", "relevance", "confidence"):
            assert key in result, f"Missing key: {key}"

    @pytest.mark.unit
    def test_relevance_is_one_minus_distance(self):
        """relevance must equal round(1.0 - distance, 4)."""
        col = _make_collection(count=1)
        col.query.return_value = _build_query_response(
            ids=["doc1"],
            documents=["Brake squeal under light braking"],
            metadatas=[{"tags": "brake"}],
            distances=[0.35],
        )
        fake = _make_fake_chromadb(collection=col)

        with patch.dict(sys.modules, {"chromadb": fake}):
            from src.data.chroma_service import ChromaService
            svc = ChromaService()

        result = svc.search("brake noise")[0]
        assert result["relevance"] == pytest.approx(0.65, abs=1e-4)

    @pytest.mark.unit
    def test_confidence_is_always_forum_base(self):
        """confidence in every result must equal FORUM_BASE_CONFIDENCE (0.5)."""
        col = _make_collection(count=2)
        col.query.return_value = _build_query_response(
            ids=["doc1", "doc2"],
            documents=["A", "B"],
            metadatas=[{"tags": "engine"}, {"tags": "brake"}],
            distances=[0.1, 0.4],
        )
        fake = _make_fake_chromadb(collection=col)

        with patch.dict(sys.modules, {"chromadb": fake}):
            from src.data.chroma_service import ChromaService, FORUM_BASE_CONFIDENCE
            svc = ChromaService()

        results = svc.search("any query")
        for r in results:
            assert r["confidence"] == FORUM_BASE_CONFIDENCE

    # -- min_score filtering -----------------------------------------------

    @pytest.mark.unit
    def test_min_score_filters_low_relevance_results(self):
        """Results with relevance < min_score must be excluded."""
        col = _make_collection(count=3)
        col.query.return_value = _build_query_response(
            ids=["doc1", "doc2", "doc3"],
            documents=["High relevance", "Medium relevance", "Low relevance"],
            metadatas=[{"tags": "engine"}, {"tags": "engine"}, {"tags": "engine"}],
            distances=[0.05, 0.40, 0.80],  # relevances: 0.95, 0.60, 0.20
        )
        fake = _make_fake_chromadb(collection=col)

        with patch.dict(sys.modules, {"chromadb": fake}):
            from src.data.chroma_service import ChromaService
            svc = ChromaService()

        results = svc.search("engine", min_score=0.5)
        # Only the first two results have relevance >= 0.5
        assert len(results) == 2
        assert results[0]["id"] == "doc1"
        assert results[1]["id"] == "doc2"

    @pytest.mark.unit
    def test_min_score_zero_includes_all_results(self):
        """min_score=0.0 (default) must not filter out any result."""
        col = _make_collection(count=3)
        col.query.return_value = _build_query_response(
            ids=["doc1", "doc2", "doc3"],
            documents=["A", "B", "C"],
            metadatas=[{"tags": "e"}, {"tags": "e"}, {"tags": "e"}],
            distances=[0.1, 0.5, 0.9],
        )
        fake = _make_fake_chromadb(collection=col)

        with patch.dict(sys.modules, {"chromadb": fake}):
            from src.data.chroma_service import ChromaService
            svc = ChromaService()

        results = svc.search("query", min_score=0.0)
        assert len(results) == 3

    @pytest.mark.unit
    def test_min_score_excludes_all_results_returns_empty(self):
        """min_score=1.0 must exclude all results (nothing is a perfect match)."""
        col = _make_collection(count=2)
        col.query.return_value = _build_query_response(
            ids=["doc1", "doc2"],
            documents=["A", "B"],
            metadatas=[{"tags": "e"}, {"tags": "e"}],
            distances=[0.3, 0.7],
        )
        fake = _make_fake_chromadb(collection=col)

        with patch.dict(sys.modules, {"chromadb": fake}):
            from src.data.chroma_service import ChromaService
            svc = ChromaService()

        results = svc.search("query", min_score=1.0)
        assert results == []

    # -- Exception resilience -----------------------------------------------

    @pytest.mark.unit
    def test_collection_query_exception_returns_empty_list(self):
        """If collection.query raises, search must return [] without re-raising."""
        col = _make_collection(count=5)
        col.query.side_effect = RuntimeError("ChromaDB internal error")
        fake = _make_fake_chromadb(collection=col)

        with patch.dict(sys.modules, {"chromadb": fake}):
            from src.data.chroma_service import ChromaService
            svc = ChromaService()

        result = svc.search("engine stall")
        assert result == []


# ===========================================================================
# ChromaService.search_for_components
# ===========================================================================


class TestSearchForComponents:
    """Tests for ChromaService.search_for_components(query, n_results)."""

    # -- Guard-rails -------------------------------------------------------

    @pytest.mark.unit
    def test_no_hits_returns_empty_list(self):
        """When search returns no results, search_for_components must return []."""
        col = _make_collection(count=0)
        fake = _make_fake_chromadb(collection=col)

        with patch.dict(sys.modules, {"chromadb": fake}):
            from src.data.chroma_service import ChromaService
            svc = ChromaService()

        # Empty collection -> search returns [] -> search_for_components returns []
        result = svc.search_for_components("transmission slip")
        assert result == []

    @pytest.mark.unit
    def test_hits_below_min_score_returns_empty_list(self):
        """Hits filtered by min_score=0.3 that all fall below threshold -> []."""
        col = _make_collection(count=2)
        # Both distances give relevance < 0.3
        col.query.return_value = _build_query_response(
            ids=["doc1", "doc2"],
            documents=["A", "B"],
            metadatas=[{"tags": "engine"}, {"tags": "transmission"}],
            distances=[0.85, 0.90],
        )
        fake = _make_fake_chromadb(collection=col)

        with patch.dict(sys.modules, {"chromadb": fake}):
            from src.data.chroma_service import ChromaService
            svc = ChromaService()

        result = svc.search_for_components("query")
        assert result == []

    # -- Result schema validation -------------------------------------------

    @pytest.mark.unit
    def test_candidates_have_required_schema_keys(self):
        """Each candidate must contain component, count, confidence, source, samples."""
        col = _make_collection(count=3)
        col.query.return_value = _build_query_response(
            ids=["doc1"],
            documents=["Brake pad wear causes squealing"],
            metadatas=[{"tags": "brake,abs", "url": "http://x.com", "year": 2020}],
            distances=[0.1],  # relevance 0.9 -> passes min_score=0.3
        )
        fake = _make_fake_chromadb(collection=col)

        with patch.dict(sys.modules, {"chromadb": fake}):
            from src.data.chroma_service import ChromaService
            svc = ChromaService()

        results = svc.search_for_components("brake noise")
        assert len(results) >= 1
        for candidate in results:
            for key in ("component", "count", "confidence", "source", "samples"):
                assert key in candidate, f"Missing key '{key}' in candidate: {candidate}"

    @pytest.mark.unit
    def test_confidence_is_always_forum_base_confidence(self):
        """confidence on every candidate must be FORUM_BASE_CONFIDENCE (0.5)."""
        col = _make_collection(count=3)
        col.query.return_value = _build_query_response(
            ids=["doc1", "doc2"],
            documents=["Engine knock on cold start", "Engine oil pressure low"],
            metadatas=[
                {"tags": "engine,oil", "url": "", "year": 2019},
                {"tags": "engine", "url": "", "year": 2020},
            ],
            distances=[0.1, 0.15],
        )
        fake = _make_fake_chromadb(collection=col)

        with patch.dict(sys.modules, {"chromadb": fake}):
            from src.data.chroma_service import ChromaService, FORUM_BASE_CONFIDENCE
            svc = ChromaService()

        results = svc.search_for_components("engine knock")
        for candidate in results:
            assert candidate["confidence"] == FORUM_BASE_CONFIDENCE

    @pytest.mark.unit
    def test_source_field_is_forum(self):
        """source field must be the string 'forum' for all candidates."""
        col = _make_collection(count=2)
        col.query.return_value = _build_query_response(
            ids=["doc1"],
            documents=["Transmission slipping between 2nd and 3rd"],
            metadatas=[{"tags": "transmission,shift", "url": "", "year": 2021}],
            distances=[0.2],
        )
        fake = _make_fake_chromadb(collection=col)

        with patch.dict(sys.modules, {"chromadb": fake}):
            from src.data.chroma_service import ChromaService
            svc = ChromaService()

        results = svc.search_for_components("transmission slip")
        for candidate in results:
            assert candidate["source"] == "forum"

    @pytest.mark.unit
    def test_component_name_is_uppercased_tag(self):
        """Component names must be the uppercased tag string from metadata."""
        col = _make_collection(count=2)
        col.query.return_value = _build_query_response(
            ids=["doc1"],
            documents=["Coolant leak from thermostat housing"],
            metadatas=[{"tags": "cooling,thermostat", "url": "", "year": 2018}],
            distances=[0.05],
        )
        fake = _make_fake_chromadb(collection=col)

        with patch.dict(sys.modules, {"chromadb": fake}):
            from src.data.chroma_service import ChromaService
            svc = ChromaService()

        results = svc.search_for_components("coolant leak")
        component_names = {r["component"] for r in results}
        assert "COOLING" in component_names or "THERMOSTAT" in component_names

    @pytest.mark.unit
    def test_count_reflects_number_of_hits_per_tag(self):
        """count must reflect how many search hits mentioned that tag."""
        col = _make_collection(count=3)
        # Two hits both tag 'engine'; one additionally tags 'oil'
        col.query.return_value = _build_query_response(
            ids=["doc1", "doc2"],
            documents=["Engine knock", "Engine misfire and oil burn"],
            metadatas=[
                {"tags": "engine", "url": "", "year": 2019},
                {"tags": "engine,oil", "url": "", "year": 2020},
            ],
            distances=[0.1, 0.2],
        )
        fake = _make_fake_chromadb(collection=col)

        with patch.dict(sys.modules, {"chromadb": fake}):
            from src.data.chroma_service import ChromaService
            svc = ChromaService()

        results = svc.search_for_components("engine problem")
        engine_candidate = next((r for r in results if r["component"] == "ENGINE"), None)
        assert engine_candidate is not None
        assert engine_candidate["count"] == 2

    @pytest.mark.unit
    def test_samples_list_present_and_not_empty(self):
        """samples must be a non-empty list for each candidate."""
        col = _make_collection(count=2)
        col.query.return_value = _build_query_response(
            ids=["doc1"],
            documents=["ABS light on and brake pedal pulsating"],
            metadatas=[{"tags": "abs,brake", "url": "http://q.com", "year": 2022}],
            distances=[0.15],
        )
        fake = _make_fake_chromadb(collection=col)

        with patch.dict(sys.modules, {"chromadb": fake}):
            from src.data.chroma_service import ChromaService
            svc = ChromaService()

        results = svc.search_for_components("abs brake pulsate")
        for candidate in results:
            assert isinstance(candidate["samples"], list)
            assert len(candidate["samples"]) >= 1

    @pytest.mark.unit
    def test_samples_schema_has_summary_url_year_relevance(self):
        """Each sample must contain summary, url, year, relevance."""
        col = _make_collection(count=2)
        doc_text = "Fuel pump fails intermittently causing stall"
        col.query.return_value = _build_query_response(
            ids=["doc1"],
            documents=[doc_text],
            metadatas=[{"tags": "fuel_pump", "url": "http://se.com", "year": 2017}],
            distances=[0.1],
        )
        fake = _make_fake_chromadb(collection=col)

        with patch.dict(sys.modules, {"chromadb": fake}):
            from src.data.chroma_service import ChromaService
            svc = ChromaService()

        results = svc.search_for_components("fuel pump stall")
        sample = results[0]["samples"][0]
        for key in ("summary", "url", "year", "relevance"):
            assert key in sample, f"Sample missing key '{key}': {sample}"

    @pytest.mark.unit
    def test_samples_summary_is_truncated_to_200_chars(self):
        """sample summary must be at most 200 characters long."""
        long_doc = "X" * 500
        col = _make_collection(count=1)
        col.query.return_value = _build_query_response(
            ids=["doc1"],
            documents=[long_doc],
            metadatas=[{"tags": "engine", "url": "", "year": 2020}],
            distances=[0.1],
        )
        fake = _make_fake_chromadb(collection=col)

        with patch.dict(sys.modules, {"chromadb": fake}):
            from src.data.chroma_service import ChromaService
            svc = ChromaService()

        results = svc.search_for_components("engine")
        sample_summary = results[0]["samples"][0]["summary"]
        assert len(sample_summary) <= 200

    @pytest.mark.unit
    def test_results_capped_at_ten_candidates(self):
        """search_for_components must return at most 10 candidates."""
        # Create 15 distinct tags, each in a separate hit
        tags = [f"tag{i}" for i in range(15)]
        col = _make_collection(count=15)
        col.query.return_value = _build_query_response(
            ids=[f"doc{i}" for i in range(15)],
            documents=[f"Document about {t}" for t in tags],
            metadatas=[{"tags": t, "url": "", "year": 2021} for t in tags],
            distances=[0.1] * 15,
        )
        fake = _make_fake_chromadb(collection=col)

        with patch.dict(sys.modules, {"chromadb": fake}):
            from src.data.chroma_service import ChromaService
            svc = ChromaService()

        results = svc.search_for_components("many components")
        assert len(results) <= 10

    @pytest.mark.unit
    def test_tags_with_whitespace_are_stripped(self):
        """Tags like ' engine , oil ' must be stripped before uppercasing."""
        col = _make_collection(count=1)
        col.query.return_value = _build_query_response(
            ids=["doc1"],
            documents=["Engine oil consumption"],
            metadatas=[{"tags": " engine , oil ", "url": "", "year": 2020}],
            distances=[0.1],
        )
        fake = _make_fake_chromadb(collection=col)

        with patch.dict(sys.modules, {"chromadb": fake}):
            from src.data.chroma_service import ChromaService
            svc = ChromaService()

        results = svc.search_for_components("engine oil")
        component_names = {r["component"] for r in results}
        # Must not produce ' ENGINE' or 'ENGINE ' with surrounding spaces
        assert "ENGINE" in component_names
        assert "OIL" in component_names

    @pytest.mark.unit
    def test_empty_tags_in_metadata_are_ignored(self):
        """Hits with empty tags string must not produce empty-string components."""
        col = _make_collection(count=1)
        col.query.return_value = _build_query_response(
            ids=["doc1"],
            documents=["Generic issue with no tags"],
            metadatas=[{"tags": "", "url": "", "year": 2021}],
            distances=[0.1],
        )
        fake = _make_fake_chromadb(collection=col)

        with patch.dict(sys.modules, {"chromadb": fake}):
            from src.data.chroma_service import ChromaService
            svc = ChromaService()

        results = svc.search_for_components("generic issue")
        # No tags -> no components extracted
        assert results == []

    @pytest.mark.unit
    def test_missing_tags_key_in_metadata_does_not_raise(self):
        """Metadata without a 'tags' key must not raise a KeyError."""
        col = _make_collection(count=1)
        col.query.return_value = _build_query_response(
            ids=["doc1"],
            documents=["Metadata has no tags field"],
            metadatas=[{"url": "http://x.com", "year": 2019}],  # no 'tags' key
            distances=[0.1],
        )
        fake = _make_fake_chromadb(collection=col)

        with patch.dict(sys.modules, {"chromadb": fake}):
            from src.data.chroma_service import ChromaService
            svc = ChromaService()

        # Must not raise
        result = svc.search_for_components("any query")
        assert result == []


# ===========================================================================
# scannerdanner_ebook collection — dual-collection behaviour
# ===========================================================================


class TestEbookCollection:
    """Tests for dual-collection (forum + ebook) search behaviour."""

    @pytest.mark.unit
    def test_ebook_results_included_in_search(self):
        """search must return results from both forum and ebook collections."""
        forum_col = _make_collection(count=5)
        forum_col.query.return_value = _build_query_response(
            ids=["forum1"],
            documents=["Forum post about MAF sensor cleaning"],
            metadatas=[{"tags": "maf,fuel", "source": "stackexchange"}],
            distances=[0.2],
        )
        ebook_col = _make_collection(count=182)
        ebook_col.query.return_value = _build_query_response(
            ids=["ebook1"],
            documents=["[scannerdanner_ebook] frame_0042 MAF sensor diagnostic procedure"],
            metadatas=[{"source": "scannerdanner_ebook", "frame": "frame_0042.png",
                        "content_type": "ebook_image", "confidence": 0.9}],
            distances=[0.1],
        )
        fake = _make_fake_chromadb(collection=forum_col, ebook_collection=ebook_col)

        with patch.dict(sys.modules, {"chromadb": fake}):
            from src.data.chroma_service import ChromaService
            svc = ChromaService()

        results = svc.search("MAF sensor")
        ids = [r["id"] for r in results]
        assert "forum1" in ids
        assert "ebook1" in ids

    @pytest.mark.unit
    def test_ebook_results_sorted_by_relevance(self):
        """Higher relevance ebook result must rank above lower relevance forum result."""
        forum_col = _make_collection(count=5)
        forum_col.query.return_value = _build_query_response(
            ids=["forum1"],
            documents=["Forum post"],
            metadatas=[{"tags": "maf"}],
            distances=[0.4],  # relevance 0.6
        )
        ebook_col = _make_collection(count=182)
        ebook_col.query.return_value = _build_query_response(
            ids=["ebook1"],
            documents=["Ebook frame"],
            metadatas=[{"source": "scannerdanner_ebook", "confidence": 0.9}],
            distances=[0.1],  # relevance 0.9 — higher
        )
        fake = _make_fake_chromadb(collection=forum_col, ebook_collection=ebook_col)

        with patch.dict(sys.modules, {"chromadb": fake}):
            from src.data.chroma_service import ChromaService
            svc = ChromaService()

        results = svc.search("MAF sensor")
        assert results[0]["id"] == "ebook1"

    @pytest.mark.unit
    def test_ebook_confidence_from_metadata(self):
        """Ebook result confidence must use the value stored in metadata (0.9)."""
        forum_col = _make_collection(count=1)
        forum_col.query.return_value = _build_query_response(
            ids=[], documents=[], metadatas=[], distances=[]
        )
        ebook_col = _make_collection(count=182)
        ebook_col.query.return_value = _build_query_response(
            ids=["ebook1"],
            documents=["Ebook content"],
            metadatas=[{"source": "scannerdanner_ebook", "confidence": 0.9}],
            distances=[0.15],
        )
        fake = _make_fake_chromadb(collection=forum_col, ebook_collection=ebook_col)

        with patch.dict(sys.modules, {"chromadb": fake}):
            from src.data.chroma_service import ChromaService
            svc = ChromaService()

        results = svc.search("vacuum leak")
        ebook_result = next(r for r in results if r["id"] == "ebook1")
        assert ebook_result["confidence"] == pytest.approx(0.9)

    @pytest.mark.unit
    def test_ebook_missing_does_not_affect_forum_search(self):
        """When ebook collection is absent, search returns forum results normally."""
        col = _make_collection(count=3)
        col.query.return_value = _build_query_response(
            ids=["forum1"],
            documents=["Forum misfire diagnosis"],
            metadatas=[{"tags": "engine,misfire"}],
            distances=[0.2],
        )
        fake = _make_fake_chromadb(collection=col)  # no ebook_collection → raises

        with patch.dict(sys.modules, {"chromadb": fake}):
            from src.data.chroma_service import ChromaService
            svc = ChromaService()

        results = svc.search("misfire")
        assert len(results) == 1
        assert results[0]["id"] == "forum1"

    @pytest.mark.unit
    def test_search_respects_n_results_cap_after_merge(self):
        """Merged results must be capped at n_results even when both collections return hits."""
        forum_col = _make_collection(count=10)
        forum_col.query.return_value = _build_query_response(
            ids=[f"f{i}" for i in range(5)],
            documents=[f"Forum doc {i}" for i in range(5)],
            metadatas=[{"tags": "engine"}] * 5,
            distances=[0.1 + i * 0.05 for i in range(5)],
        )
        ebook_col = _make_collection(count=182)
        ebook_col.query.return_value = _build_query_response(
            ids=[f"e{i}" for i in range(5)],
            documents=[f"Ebook doc {i}" for i in range(5)],
            metadatas=[{"source": "scannerdanner_ebook", "confidence": 0.9}] * 5,
            distances=[0.12 + i * 0.05 for i in range(5)],
        )
        fake = _make_fake_chromadb(collection=forum_col, ebook_collection=ebook_col)

        with patch.dict(sys.modules, {"chromadb": fake}):
            from src.data.chroma_service import ChromaService
            svc = ChromaService()

        results = svc.search("engine", n_results=4)
        assert len(results) <= 4
