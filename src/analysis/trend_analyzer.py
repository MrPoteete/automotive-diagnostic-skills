"""
Trend analyzer for NHTSA complaint data.

Groups complaints_fts results by year to detect increasing, decreasing,
or stable complaint patterns for a given vehicle and component.

Algorithm:
- Retrieve year-bucket counts via DiagnosticDB.get_complaints_by_year().
- Require at least 3 data points before drawing any conclusion.
- Use the last 5 years of data (chronologically) for the trend window.
- Compare the average count of the last 2 years against the first 2 years
  within that window.
- Ratio > 1.5  -> INCREASING
- Ratio < 0.5  -> DECREASING
- Otherwise    -> STABLE

Checked AGENTS.md - implementing directly because the trend algorithm and
return schema are fully specified by the user. No open-ended design decisions
require a specialized subagent.
"""

import logging

from src.data.db_service import DiagnosticDB

logger = logging.getLogger(__name__)

# Sentinel returned when there is not enough data to compute a trend.
INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
INCREASING = "INCREASING"
DECREASING = "DECREASING"
STABLE = "STABLE"

# Minimum number of year buckets required to compute a trend.
_MIN_DATA_POINTS = 3

# How many of the most-recent years to include in the trend window.
_TREND_WINDOW = 5

# Thresholds for classifying the last-vs-first ratio.
_INCREASING_THRESHOLD = 1.5
_DECREASING_THRESHOLD = 0.5


def analyze_trend(
    make: str,
    model: str,
    component: str,
    db: DiagnosticDB,
) -> str:
    """Determine whether complaint volume is increasing, decreasing, or stable.

    Args:
        make: Vehicle manufacturer, e.g. ``"FORD"``.
        model: Vehicle model, e.g. ``"F-150"``.
        component: Component keyword, e.g. ``"engine"`` or ``"brake"``.
        db: Open :class:`~src.data.db_service.DiagnosticDB` instance.

    Returns:
        One of ``"INCREASING"``, ``"DECREASING"``, ``"STABLE"``, or
        ``"INSUFFICIENT_DATA"``.
    """
    try:
        year_data = db.get_complaints_by_year(make, model, component)
    except Exception as exc:
        logger.error(
            "analyze_trend error fetching data for %s %s '%s': %s",
            make, model, component, exc,
        )
        return INSUFFICIENT_DATA

    if len(year_data) < _MIN_DATA_POINTS:
        logger.debug(
            "analyze_trend('%s','%s','%s'): only %d data point(s), need %d",
            make, model, component, len(year_data), _MIN_DATA_POINTS,
        )
        return INSUFFICIENT_DATA

    # Sort chronologically and take the most recent TREND_WINDOW years.
    sorted_data = sorted(year_data, key=lambda d: d["year"])
    window = sorted_data[-_TREND_WINDOW:]

    if len(window) < _MIN_DATA_POINTS:
        return INSUFFICIENT_DATA

    try:
        # Average of the first 2 years in the window (oldest complaints).
        first_avg = (window[0]["count"] + window[1]["count"]) / 2.0
        # Average of the last 2 years in the window (most recent complaints).
        last_avg = (window[-2]["count"] + window[-1]["count"]) / 2.0
    except (IndexError, KeyError, TypeError) as exc:
        logger.error(
            "analyze_trend('%s','%s','%s'): error computing averages: %s",
            make, model, component, exc,
        )
        return INSUFFICIENT_DATA

    # Guard against division by zero when there were no early complaints.
    if first_avg == 0:
        if last_avg > 0:
            return INCREASING
        return INSUFFICIENT_DATA

    ratio = last_avg / first_avg

    if ratio > _INCREASING_THRESHOLD:
        trend = INCREASING
    elif ratio < _DECREASING_THRESHOLD:
        trend = DECREASING
    else:
        trend = STABLE

    logger.debug(
        "analyze_trend('%s','%s','%s'): first_avg=%.1f last_avg=%.1f ratio=%.2f -> %s",
        make, model, component, first_avg, last_avg, ratio, trend,
    )
    return trend


def get_trend_summary(
    make: str,
    model: str,
    component: str,
    db: DiagnosticDB,
) -> dict:
    """Return a structured trend summary for a vehicle and component.

    Args:
        make: Vehicle manufacturer.
        model: Vehicle model.
        component: Component keyword.
        db: Open :class:`~src.data.db_service.DiagnosticDB` instance.

    Returns:
        Dict with keys:

        - ``trend`` (str): Result of :func:`analyze_trend`.
        - ``years`` (list[dict]): Raw year-bucket data from the database,
          each dict has ``year`` (str) and ``count`` (int).
        - ``total_complaints`` (int): Sum of all complaint counts across years.
    """
    try:
        year_data = db.get_complaints_by_year(make, model, component)
    except Exception as exc:
        logger.error(
            "get_trend_summary error for %s %s '%s': %s",
            make, model, component, exc,
        )
        year_data = []

    trend = analyze_trend(make, model, component, db)
    total = sum(d["count"] for d in year_data)

    return {
        "trend": trend,
        "years": year_data,
        "total_complaints": total,
    }
