"""
Unit tests for src/analysis/trend_analyzer.py

Checked AGENTS.md - implementing directly because:
1. This is test code (quality-engineer agent scope)
2. All DB interactions are mocked — no data-engineer delegation needed
3. Tests validate the trend algorithm logic as-implemented

Algorithm recap (from source):
- Needs >= 3 data points (year buckets) to draw any conclusion
- Takes last 5 years of the sorted window
- Compares avg(last 2 years) vs avg(first 2 years of window)
- ratio > 1.5  -> INCREASING
- ratio < 0.5  -> DECREASING
- otherwise    -> STABLE
- first_avg == 0 and last_avg > 0 -> INCREASING
- first_avg == 0 and last_avg == 0 -> INSUFFICIENT_DATA

Test categories:
- analyze_trend: insufficient data, INCREASING, DECREASING, STABLE, edge cases
- get_trend_summary: return structure, total_complaints aggregation
"""

import pytest
from unittest.mock import MagicMock

from src.analysis.trend_analyzer import (
    analyze_trend,
    get_trend_summary,
    INSUFFICIENT_DATA,
    INCREASING,
    DECREASING,
    STABLE,
)


# ===========================================================================
# Helpers
# ===========================================================================


def _year_data(*counts: int, start_year: int = 2018) -> list[dict]:
    """Build a year-bucket list from a sequence of complaint counts.

    Example: _year_data(10, 20, 30) -> [
        {"year": "2018", "count": 10},
        {"year": "2019", "count": 20},
        {"year": "2020", "count": 30},
    ]
    """
    return [
        {"year": str(start_year + i), "count": c}
        for i, c in enumerate(counts)
    ]


def _mock_db(year_data: list[dict]) -> MagicMock:
    """Return a mock DB whose get_complaints_by_year returns year_data."""
    db = MagicMock(name="DiagnosticDB")
    db.get_complaints_by_year.return_value = year_data
    return db


# ===========================================================================
# analyze_trend
# ===========================================================================


class TestAnalyzeTrend:
    """Tests for analyze_trend(make, model, component, db) -> str."""

    # -- INSUFFICIENT_DATA cases ------------------------------------------------

    @pytest.mark.unit
    def test_zero_data_points_returns_insufficient(self):
        """Empty data must return INSUFFICIENT_DATA."""
        db = _mock_db([])
        result = analyze_trend("FORD", "F-150", "engine", db)
        assert result == INSUFFICIENT_DATA

    @pytest.mark.unit
    def test_one_data_point_returns_insufficient(self):
        """A single year bucket must return INSUFFICIENT_DATA (need >= 3)."""
        db = _mock_db(_year_data(50))
        result = analyze_trend("FORD", "F-150", "engine", db)
        assert result == INSUFFICIENT_DATA

    @pytest.mark.unit
    def test_two_data_points_returns_insufficient(self):
        """Two year buckets must return INSUFFICIENT_DATA (need >= 3)."""
        db = _mock_db(_year_data(50, 60))
        result = analyze_trend("FORD", "F-150", "engine", db)
        assert result == INSUFFICIENT_DATA

    @pytest.mark.unit
    def test_db_exception_returns_insufficient(self):
        """DB exception must be caught and return INSUFFICIENT_DATA."""
        db = MagicMock()
        db.get_complaints_by_year.side_effect = RuntimeError("DB error")
        result = analyze_trend("FORD", "F-150", "engine", db)
        assert result == INSUFFICIENT_DATA

    @pytest.mark.unit
    def test_all_zero_counts_returns_insufficient(self):
        """If all complaint counts are zero, INSUFFICIENT_DATA must be returned.

        When first_avg == 0 and last_avg == 0, division is guarded and returns
        INSUFFICIENT_DATA.
        """
        db = _mock_db(_year_data(0, 0, 0))
        result = analyze_trend("FORD", "F-150", "engine", db)
        assert result == INSUFFICIENT_DATA

    # -- INCREASING cases -------------------------------------------------------

    @pytest.mark.unit
    def test_clearly_increasing_trend(self):
        """Complaint count doubling year-over-year must return INCREASING.

        Window: [10, 20, 30, 60, 120]
        first_avg = (10 + 20) / 2 = 15
        last_avg  = (60 + 120) / 2 = 90
        ratio = 90 / 15 = 6.0 > 1.5 -> INCREASING
        """
        db = _mock_db(_year_data(10, 20, 30, 60, 120))
        result = analyze_trend("FORD", "F-150", "engine", db)
        assert result == INCREASING

    @pytest.mark.unit
    def test_ratio_exactly_above_threshold_is_increasing(self):
        """Ratio of 1.6 (> 1.5 threshold) must return INCREASING.

        3 points: [10, 10, 16]
        first_avg = (10 + 10) / 2 = 10
        last_avg  = (10 + 16) / 2 = 13  -> ratio 1.3 -> STABLE
        Use 4 points: [10, 10, 10, 32]
        first_avg = (10 + 10) / 2 = 10
        last_avg  = (10 + 32) / 2 = 21 -> ratio 2.1 -> INCREASING
        """
        db = _mock_db(_year_data(10, 10, 10, 32))
        result = analyze_trend("FORD", "F-150", "engine", db)
        assert result == INCREASING

    @pytest.mark.unit
    def test_zero_first_avg_nonzero_last_avg_is_increasing(self):
        """When first_avg == 0 and last_avg > 0, must return INCREASING.

        This handles a new failure mode appearing in recent years.
        """
        db = _mock_db(_year_data(0, 0, 50))
        result = analyze_trend("FORD", "F-150", "engine", db)
        assert result == INCREASING

    @pytest.mark.unit
    def test_large_spike_in_recent_years(self):
        """Large spike in recent complaint counts must be INCREASING.

        Window: [5, 5, 5, 100, 200]
        first_avg = (5 + 5) / 2 = 5
        last_avg  = (100 + 200) / 2 = 150
        ratio = 150 / 5 = 30 -> INCREASING
        """
        db = _mock_db(_year_data(5, 5, 5, 100, 200))
        result = analyze_trend("FORD", "F-150", "engine", db)
        assert result == INCREASING

    # -- DECREASING cases -------------------------------------------------------

    @pytest.mark.unit
    def test_clearly_decreasing_trend(self):
        """Complaint count halving each year must return DECREASING.

        Window: [200, 100, 50, 25, 12]
        first_avg = (200 + 100) / 2 = 150
        last_avg  = (25 + 12) / 2 = 18.5
        ratio = 18.5 / 150 = 0.123 < 0.5 -> DECREASING
        """
        db = _mock_db(_year_data(200, 100, 50, 25, 12))
        result = analyze_trend("FORD", "F-150", "engine", db)
        assert result == DECREASING

    @pytest.mark.unit
    def test_ratio_below_half_is_decreasing(self):
        """Ratio < 0.5 must return DECREASING.

        4 points: [100, 100, 10, 10]
        first_avg = (100 + 100) / 2 = 100
        last_avg  = (10 + 10) / 2 = 10
        ratio = 0.10 < 0.5 -> DECREASING
        """
        db = _mock_db(_year_data(100, 100, 10, 10))
        result = analyze_trend("FORD", "F-150", "engine", db)
        assert result == DECREASING

    @pytest.mark.unit
    def test_steep_falloff_is_decreasing(self):
        """Near-zero recent counts after high early counts must be DECREASING."""
        db = _mock_db(_year_data(500, 400, 300, 5, 2))
        result = analyze_trend("FORD", "F-150", "engine", db)
        assert result == DECREASING

    # -- STABLE cases -----------------------------------------------------------

    @pytest.mark.unit
    def test_flat_counts_are_stable(self):
        """Constant complaint counts must return STABLE.

        3 points: [50, 50, 50]
        first_avg = last_avg = 50
        ratio = 1.0 -> STABLE (between 0.5 and 1.5)
        """
        db = _mock_db(_year_data(50, 50, 50))
        result = analyze_trend("FORD", "F-150", "engine", db)
        assert result == STABLE

    @pytest.mark.unit
    def test_slight_increase_within_stable_range(self):
        """Ratio of 1.3 (between 0.5 and 1.5) must return STABLE."""
        db = _mock_db(_year_data(10, 10, 10, 13))
        result = analyze_trend("FORD", "F-150", "engine", db)
        assert result == STABLE

    @pytest.mark.unit
    def test_slight_decrease_within_stable_range(self):
        """Ratio of 0.7 (between 0.5 and 1.5) must return STABLE."""
        db = _mock_db(_year_data(100, 100, 100, 70))
        result = analyze_trend("FORD", "F-150", "engine", db)
        assert result == STABLE

    @pytest.mark.unit
    def test_noise_around_baseline_is_stable(self):
        """Minor fluctuations around a baseline must be STABLE."""
        db = _mock_db(_year_data(48, 52, 50, 53, 47))
        result = analyze_trend("FORD", "F-150", "engine", db)
        assert result == STABLE

    # -- Window and boundary conditions -----------------------------------------

    @pytest.mark.unit
    def test_exactly_three_data_points_sufficient(self):
        """Exactly 3 data points must be enough to compute a trend."""
        db = _mock_db(_year_data(10, 10, 10))
        result = analyze_trend("FORD", "F-150", "engine", db)
        assert result in {INCREASING, DECREASING, STABLE, INSUFFICIENT_DATA}
        # With equal counts the ratio is 1.0 -> STABLE
        assert result == STABLE

    @pytest.mark.unit
    def test_more_than_five_points_uses_last_five(self):
        """With > 5 data points, only the most recent 5 are used in the window.

        Old data: [1000, 1000, 1000, 1000] — would show DECREASING vs recent
        Recent data (last 5): [10, 10, 10, 10, 10] — ratio 1.0 -> STABLE

        Providing 6 points where the oldest is anomalously high should not
        affect the trend if the most recent 5 are stable.
        """
        # 6 points: oldest is 1000 (excluded), rest are 10 -> STABLE
        db = _mock_db(_year_data(1000, 10, 10, 10, 10, 10))
        result = analyze_trend("FORD", "F-150", "engine", db)
        assert result == STABLE

    @pytest.mark.unit
    def test_unsorted_data_sorted_before_windowing(self):
        """Data returned out of chronological order must be sorted before analysis."""
        # Provide years out of order
        year_data = [
            {"year": "2022", "count": 100},
            {"year": "2019", "count": 10},
            {"year": "2020", "count": 10},
            {"year": "2021", "count": 10},
        ]
        db = _mock_db(year_data)
        result = analyze_trend("FORD", "F-150", "engine", db)
        # Sorted: 2019(10), 2020(10), 2021(10), 2022(100)
        # first_avg=(10+10)/2=10, last_avg=(10+100)/2=55, ratio=5.5 -> INCREASING
        assert result == INCREASING

    # -- Return type validation -------------------------------------------------

    @pytest.mark.unit
    def test_return_value_is_string(self):
        """analyze_trend must always return a string."""
        db = _mock_db([])
        result = analyze_trend("FORD", "F-150", "engine", db)
        assert isinstance(result, str)

    @pytest.mark.unit
    def test_return_value_is_one_of_known_constants(self):
        """Return value must be one of the four defined sentinel strings."""
        valid = {INSUFFICIENT_DATA, INCREASING, DECREASING, STABLE}
        for year_data, expected in [
            ([], INSUFFICIENT_DATA),
            (_year_data(50, 50, 50), STABLE),
            (_year_data(10, 10, 10, 10, 100), INCREASING),
            (_year_data(100, 100, 10, 10, 10), DECREASING),
        ]:
            db = _mock_db(year_data)
            result = analyze_trend("FORD", "F-150", "engine", db)
            assert result in valid

    # -- DB interaction ---------------------------------------------------------

    @pytest.mark.unit
    def test_db_called_with_correct_arguments(self):
        """get_complaints_by_year must receive the correct make, model, component."""
        db = _mock_db([])
        analyze_trend("RAM", "1500", "TIPM", db)
        db.get_complaints_by_year.assert_called_once_with("RAM", "1500", "TIPM")


# ===========================================================================
# get_trend_summary
# ===========================================================================


class TestGetTrendSummary:
    """Tests for get_trend_summary(make, model, component, db) -> dict."""

    @pytest.mark.unit
    def test_returns_dict(self):
        """get_trend_summary must return a dict."""
        db = _mock_db([])
        result = get_trend_summary("FORD", "F-150", "engine", db)
        assert isinstance(result, dict)

    @pytest.mark.unit
    def test_result_has_trend_key(self):
        """Result dict must have a 'trend' key."""
        db = _mock_db([])
        result = get_trend_summary("FORD", "F-150", "engine", db)
        assert "trend" in result

    @pytest.mark.unit
    def test_result_has_years_key(self):
        """Result dict must have a 'years' key."""
        db = _mock_db([])
        result = get_trend_summary("FORD", "F-150", "engine", db)
        assert "years" in result

    @pytest.mark.unit
    def test_result_has_total_complaints_key(self):
        """Result dict must have a 'total_complaints' key."""
        db = _mock_db([])
        result = get_trend_summary("FORD", "F-150", "engine", db)
        assert "total_complaints" in result

    @pytest.mark.unit
    def test_total_complaints_sums_all_year_counts(self):
        """total_complaints must be the sum of all year bucket counts."""
        db = _mock_db(_year_data(10, 20, 30))
        result = get_trend_summary("FORD", "F-150", "engine", db)
        assert result["total_complaints"] == 60

    @pytest.mark.unit
    def test_total_complaints_zero_for_empty_data(self):
        """total_complaints must be 0 when there is no year data."""
        db = _mock_db([])
        result = get_trend_summary("FORD", "F-150", "engine", db)
        assert result["total_complaints"] == 0

    @pytest.mark.unit
    def test_years_matches_db_data(self):
        """The 'years' field must reflect the raw data returned by the DB."""
        year_data = _year_data(10, 20, 30)
        db = _mock_db(year_data)
        result = get_trend_summary("FORD", "F-150", "engine", db)
        assert result["years"] == year_data

    @pytest.mark.unit
    def test_trend_field_consistent_with_analyze_trend(self):
        """The 'trend' field must match what analyze_trend returns for the same data."""
        year_data = _year_data(50, 50, 50)
        db = _mock_db(year_data)
        summary = get_trend_summary("FORD", "F-150", "engine", db)
        assert summary["trend"] == STABLE

    @pytest.mark.unit
    def test_trend_increasing_reflected_in_summary(self):
        """An INCREASING trend must be reflected in the summary dict."""
        db = _mock_db(_year_data(10, 10, 10, 10, 100))
        result = get_trend_summary("FORD", "F-150", "engine", db)
        assert result["trend"] == INCREASING

    @pytest.mark.unit
    def test_trend_decreasing_reflected_in_summary(self):
        """A DECREASING trend must be reflected in the summary dict."""
        db = _mock_db(_year_data(100, 100, 10, 10, 5))
        result = get_trend_summary("FORD", "F-150", "engine", db)
        assert result["trend"] == DECREASING

    @pytest.mark.unit
    def test_db_exception_returns_empty_years_and_zero_total(self):
        """DB exception must produce empty years list and 0 total_complaints."""
        db = MagicMock()
        db.get_complaints_by_year.side_effect = RuntimeError("connection lost")
        result = get_trend_summary("FORD", "F-150", "engine", db)
        assert result["years"] == []
        assert result["total_complaints"] == 0
        assert result["trend"] == INSUFFICIENT_DATA
