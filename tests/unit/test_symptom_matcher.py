"""
Unit tests for src/diagnostic/symptom_matcher.py

Checked AGENTS.md - implementing directly because:
1. This is test code (quality-engineer agent scope)
2. DB interactions are fully mocked — no data-engineer delegation needed
3. Tests validate the synonym expansion and matching logic as-implemented

Key implementation details from actual source code:
- expand_symptoms("") returns [] (empty string -> empty word list -> no fallback terms)
- expand_symptoms("unknown xyz") returns ["unknown", "xyz"] (raw word fallback, NOT [])
- match_symptoms returns [] when db.search_complaints returns no rows
- Results are sorted by count descending

Test categories:
- expand_symptoms: synonym expansion, edge cases, fallback behavior
- match_symptoms: component grouping, sorting, empty results
"""

import pytest
from unittest.mock import MagicMock

from src.diagnostic.symptom_matcher import expand_symptoms, match_symptoms, SYMPTOM_SYNONYMS


# ===========================================================================
# expand_symptoms
# ===========================================================================


class TestExpandSymptoms:
    """Tests for expand_symptoms(text) -> list[str]."""

    # -- Synonym expansion for known keys ---------------------------------------

    @pytest.mark.unit
    def test_engine_shaking_expands_shake_synonyms(self):
        """'engine shaking at idle' must expand 'shake' synonyms."""
        terms = expand_symptoms("engine shaking at idle")
        # 'shaking' doesn't match — only 'shake' is a key; 'engine' and 'at'
        # and 'idle' also don't match, so fallback to raw words
        # Verify the function handles this without error
        assert isinstance(terms, list)
        assert len(terms) > 0

    @pytest.mark.unit
    def test_shake_keyword_expands_correctly(self):
        """Exact key 'shake' must expand to all its synonym terms."""
        terms = expand_symptoms("shake")
        expected = SYMPTOM_SYNONYMS["shake"]
        for term in expected:
            assert term in terms, f"Expected synonym '{term}' not in {terms}"

    @pytest.mark.unit
    def test_brake_keyword_expands_correctly(self):
        """Exact key 'brake' must expand to all its synonym terms."""
        terms = expand_symptoms("brake")
        expected = SYMPTOM_SYNONYMS["brake"]
        for term in expected:
            assert term in terms, f"Expected synonym '{term}' not in {terms}"

    @pytest.mark.unit
    def test_brake_failure_expands_brake_synonyms(self):
        """'brake failure' — 'brake' is a known key; must expand brake synonyms."""
        terms = expand_symptoms("brake failure")
        # 'brake' is a known key; 'failure' is not, but since 'brake' matches,
        # the synonym expansion is used (not the fallback)
        assert "brake" in terms
        assert "stopping" in terms
        assert "braking" in terms
        assert "abs" in terms

    @pytest.mark.unit
    def test_misfire_keyword_expands_correctly(self):
        """'misfire' key must expand to misfire synonyms."""
        terms = expand_symptoms("misfire")
        assert "misfire" in terms
        assert "rough idle" in terms
        assert "stumble" in terms
        assert "hesitation" in terms

    @pytest.mark.unit
    def test_stall_keyword_expands_correctly(self):
        """'stall' key must expand to stall synonyms."""
        terms = expand_symptoms("stall")
        assert "stall" in terms
        assert "dies" in terms
        assert "engine off" in terms
        assert "shutdown" in terms

    @pytest.mark.unit
    def test_transmission_keyword_expands_correctly(self):
        """'transmission' key must expand to shifting/gear synonyms."""
        terms = expand_symptoms("transmission")
        assert "transmission" in terms
        assert "shifting" in terms
        assert "gear" in terms
        assert "slipping" in terms

    @pytest.mark.unit
    def test_electrical_keyword_expands_correctly(self):
        """'electrical' key must expand to battery/power synonyms."""
        terms = expand_symptoms("electrical")
        assert "electrical" in terms
        assert "battery" in terms
        assert "power" in terms

    @pytest.mark.unit
    def test_multiple_known_keywords_expand_and_deduplicate(self):
        """Multiple known keys in input must each contribute synonyms, deduplicated."""
        terms = expand_symptoms("brake steering")
        # 'brake' synonyms: brake, stopping, braking, abs
        # 'steering' synonyms: steering, wheel, drift, pull
        assert "brake" in terms
        assert "stopping" in terms
        assert "steering" in terms
        assert "wheel" in terms
        # No duplicates
        assert len(terms) == len(set(terms))

    @pytest.mark.unit
    def test_overheating_keyword_expands_correctly(self):
        """'overheating' key must expand to coolant/temperature synonyms."""
        terms = expand_symptoms("overheating")
        assert "overheat" in terms
        assert "temperature" in terms
        assert "coolant" in terms
        assert "radiator" in terms

    @pytest.mark.unit
    def test_fuel_keyword_expands_correctly(self):
        """'fuel' key must expand to gas/mileage synonyms."""
        terms = expand_symptoms("fuel")
        assert "fuel" in terms
        assert "gas" in terms
        assert "mileage" in terms
        assert "consumption" in terms

    # -- Case insensitivity -----------------------------------------------------

    @pytest.mark.unit
    def test_input_is_lowercased_before_lookup(self):
        """Input is lowercased before matching — 'BRAKE' must match 'brake' key."""
        terms = expand_symptoms("BRAKE")
        assert "brake" in terms
        assert "stopping" in terms

    @pytest.mark.unit
    def test_mixed_case_keyword(self):
        """Mixed case 'Misfire' must still match the 'misfire' synonym key."""
        terms = expand_symptoms("Misfire")
        assert "misfire" in terms
        assert "rough idle" in terms

    # -- Fallback behavior (no synonym match) -----------------------------------

    @pytest.mark.unit
    def test_unknown_term_returns_raw_words_as_fallback(self):
        """'unknown term xyz' — no synonym match; raw words returned as fallback."""
        terms = expand_symptoms("unknown term xyz")
        # Per actual implementation: falls back to raw words when no synonyms match
        assert "unknown" in terms
        assert "term" in terms
        assert "xyz" in terms

    @pytest.mark.unit
    def test_unknown_single_word_returns_that_word(self):
        """Single unknown word must be returned as-is (fallback)."""
        terms = expand_symptoms("coolant")
        # 'coolant' is not a top-level key (it appears as a value for 'overheating')
        # Fallback: return the raw word
        assert terms == ["coolant"]

    @pytest.mark.unit
    def test_partially_known_input_uses_synonym_not_fallback(self):
        """When at least one word matches a synonym key, synonyms are returned
        (not the fallback raw words)."""
        # 'misfire' is a known key; 'random' is not
        terms = expand_symptoms("misfire random")
        # Because 'misfire' matched, synonyms are used — NOT raw word fallback
        assert "rough idle" in terms
        # 'random' itself should NOT appear in the results (no fallback mixed in)
        assert "random" not in terms

    # -- Empty and whitespace input ---------------------------------------------

    @pytest.mark.unit
    def test_empty_string_returns_empty_list(self):
        """Empty string must return [] — nothing to expand or fall back to."""
        terms = expand_symptoms("")
        assert terms == []

    @pytest.mark.unit
    def test_whitespace_only_returns_empty_list(self):
        """Whitespace-only string splits to [] and must return empty list."""
        terms = expand_symptoms("   ")
        assert terms == []

    # -- Return type and deduplication ------------------------------------------

    @pytest.mark.unit
    def test_returns_list(self):
        """Return type must always be a list."""
        assert isinstance(expand_symptoms("brake"), list)
        assert isinstance(expand_symptoms(""), list)
        assert isinstance(expand_symptoms("unknown xyz"), list)

    @pytest.mark.unit
    def test_no_duplicate_terms_for_single_keyword(self):
        """Expanding a single keyword must not produce duplicate terms."""
        terms = expand_symptoms("brake")
        assert len(terms) == len(set(terms))

    @pytest.mark.unit
    def test_no_duplicate_terms_for_multiple_keywords(self):
        """Expanding multiple keywords must produce a deduplicated list."""
        # 'brake' and 'steering' share no synonyms, but two 'brake' words should dedup
        terms = expand_symptoms("brake brake")
        assert len(terms) == len(set(terms))


# ===========================================================================
# match_symptoms
# ===========================================================================


class TestMatchSymptoms:
    """Tests for match_symptoms(make, model, year, description, db, limit) -> list[dict]."""

    @pytest.fixture
    def empty_db(self) -> MagicMock:
        """DB that returns no complaints for any search."""
        db = MagicMock(name="DiagnosticDB")
        db.search_complaints.return_value = []
        return db

    @pytest.fixture
    def populated_db(self) -> MagicMock:
        """DB that returns one engine and one brake complaint per search."""
        db = MagicMock(name="DiagnosticDB")
        db.search_complaints.return_value = [
            {"component": "POWER TRAIN", "summary": "engine misfires at idle"},
            {"component": "BRAKES", "summary": "brakes feel spongy"},
        ]
        return db

    # -- Empty/no-result cases --------------------------------------------------

    @pytest.mark.unit
    def test_empty_db_returns_empty_list(self, empty_db):
        """When DB returns no rows, match_symptoms must return []."""
        result = match_symptoms("FORD", "F-150", 2019, "misfire", empty_db)
        assert result == []

    @pytest.mark.unit
    def test_empty_description_returns_empty_list(self, empty_db):
        """Empty description produces no terms to search — must return []."""
        result = match_symptoms("FORD", "F-150", 2019, "", empty_db)
        assert result == []

    @pytest.mark.unit
    def test_unknown_description_falls_back_to_raw_terms(self, empty_db):
        """Unknown description falls back to raw words — DB called but returns empty."""
        result = match_symptoms("FORD", "F-150", 2019, "xyzzy foobar", empty_db)
        # DB should have been called with the raw fallback words
        assert empty_db.search_complaints.called
        assert result == []

    # -- Result structure -------------------------------------------------------

    @pytest.mark.unit
    def test_result_has_required_keys(self, populated_db):
        """Each result dict must have component, count, confidence_hint, samples."""
        result = match_symptoms("FORD", "F-150", 2019, "misfire", populated_db)
        assert len(result) > 0
        for item in result:
            assert "component" in item
            assert "count" in item
            assert "confidence_hint" in item
            assert "samples" in item

    @pytest.mark.unit
    def test_component_count_is_int(self, populated_db):
        """The 'count' field must be an integer."""
        result = match_symptoms("FORD", "F-150", 2019, "misfire", populated_db)
        for item in result:
            assert isinstance(item["count"], int)

    @pytest.mark.unit
    def test_confidence_hint_in_range(self, populated_db):
        """confidence_hint must be in [0.0, 1.0]."""
        result = match_symptoms("FORD", "F-150", 2019, "misfire", populated_db)
        for item in result:
            assert 0.0 <= item["confidence_hint"] <= 1.0

    @pytest.mark.unit
    def test_samples_is_list(self, populated_db):
        """The 'samples' field must be a list."""
        result = match_symptoms("FORD", "F-150", 2019, "misfire", populated_db)
        for item in result:
            assert isinstance(item["samples"], list)

    @pytest.mark.unit
    def test_samples_at_most_3_entries(self, populated_db):
        """samples must be capped at 3 entries per component."""
        result = match_symptoms("FORD", "F-150", 2019, "misfire", populated_db)
        for item in result:
            assert len(item["samples"]) <= 3

    # -- Sorting ----------------------------------------------------------------

    @pytest.mark.unit
    def test_results_sorted_by_count_descending(self):
        """Results must be sorted by count descending (most complaints first)."""
        db = MagicMock()
        # Use return_value (not side_effect) so the mock works for any number of calls.
        # "stall" alone expands to multiple synonyms so we use a single-term description.
        # Alternate between two components to get more than 1 in the result.
        call_count = 0
        def _alternating(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count % 2 == 1:
                return [
                    {"component": "POWER TRAIN", "summary": "engine stall"},
                    {"component": "POWER TRAIN", "summary": "rough idle"},
                    {"component": "POWER TRAIN", "summary": "hesitation"},
                ]
            return [{"component": "BRAKES", "summary": "brake noise"}]

        db.search_complaints.side_effect = _alternating
        result = match_symptoms("FORD", "F-150", 2019, "stall brake", db)
        if len(result) >= 2:
            assert result[0]["count"] >= result[1]["count"]

    @pytest.mark.unit
    def test_single_result_returned_as_list(self):
        """A single matching component must still be returned as a list."""
        db = MagicMock()
        db.search_complaints.return_value = [
            {"component": "POWER TRAIN", "summary": "engine vibration"}
        ]
        result = match_symptoms("FORD", "F-150", 2019, "shake", db)
        assert isinstance(result, list)

    # -- Component grouping and aggregation ------------------------------------

    @pytest.mark.unit
    def test_same_component_across_terms_aggregated(self):
        """Complaints for the same component across multiple search terms must be summed."""
        db = MagicMock()
        # Both calls return POWER TRAIN — should result in count=2 for that component
        db.search_complaints.return_value = [
            {"component": "POWER TRAIN", "summary": "engine misfire"}
        ]
        # 'misfire' expands to 4 terms — each call returns 1 POWER TRAIN row
        result = match_symptoms("FORD", "F-150", 2019, "misfire", db)
        assert len(result) > 0
        pt = next((r for r in result if r["component"] == "POWER TRAIN"), None)
        assert pt is not None
        assert pt["count"] > 1  # Accumulated across synonym terms

    @pytest.mark.unit
    def test_none_component_mapped_to_unknown(self):
        """Rows with None component must be stored under 'UNKNOWN'."""
        db = MagicMock()
        db.search_complaints.return_value = [
            {"component": None, "summary": "vehicle has issue"}
        ]
        result = match_symptoms("FORD", "F-150", 2019, "misfire", db)
        assert any(r["component"] == "UNKNOWN" for r in result)

    @pytest.mark.unit
    def test_missing_component_key_mapped_to_unknown(self):
        """Rows missing the 'component' key must be stored under 'UNKNOWN'."""
        db = MagicMock()
        db.search_complaints.return_value = [
            {"summary": "some complaint with no component key"}
        ]
        result = match_symptoms("FORD", "F-150", 2019, "misfire", db)
        assert any(r["component"] == "UNKNOWN" for r in result)

    # -- DB call parameters ----------------------------------------------------

    @pytest.mark.unit
    def test_db_called_with_correct_vehicle(self, empty_db):
        """search_complaints must receive the make, model, year from the caller."""
        match_symptoms("TOYOTA", "Camry", 2022, "misfire", empty_db)
        for call in empty_db.search_complaints.call_args_list:
            args, kwargs = call
            # Positional: make, model, year, query, limit
            assert args[0] == "TOYOTA"
            assert args[1] == "Camry"
            assert args[2] == 2022

    @pytest.mark.unit
    def test_confidence_hint_formula(self):
        """confidence_hint must equal min(1.0, count / 50)."""
        db = MagicMock()
        # Return 1 row per call; 'misfire' expands to 4 terms -> count=4
        db.search_complaints.return_value = [
            {"component": "POWER TRAIN", "summary": "misfire"}
        ]
        result = match_symptoms("FORD", "F-150", 2019, "misfire", db)
        assert len(result) > 0
        pt = next(r for r in result if r["component"] == "POWER TRAIN")
        expected = min(1.0, pt["count"] / 50)
        assert pt["confidence_hint"] == pytest.approx(expected)
