"""
Symptom matcher using FTS5 full-text search on NHTSA complaint narratives.

Two-stage matching:
1. Expand symptom keywords using a hard-coded synonym map.
2. Query complaints_fts with FTS5 MATCH for each expanded term, then group
   results by component to surface the most-reported failure areas.

Checked AGENTS.md - implementing directly because the synonym map, matching
algorithm, and return schema are fully specified by the user. No open-ended
design decisions require a specialized subagent.
"""

import logging
from collections import defaultdict

from src.data.db_service import DiagnosticDB

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Synonym expansion map
# Keys are canonical symptom names; values are the terms used in FTS queries.
# ---------------------------------------------------------------------------
SYMPTOM_SYNONYMS: dict[str, list[str]] = {
    "misfire": ["misfire", "rough idle", "stumble", "hesitation"],
    "stall": ["stall", "dies", "engine off", "shutdown"],
    "shake": ["shake", "vibration", "shudder", "wobble"],
    "brake": ["brake", "stopping", "braking", "abs"],
    "steering": ["steering", "wheel", "drift", "pull"],
    "transmission": ["transmission", "shifting", "gear", "slipping"],
    "electrical": ["electrical", "battery", "power", "electronics"],
    "fuel": ["fuel", "gas", "mileage", "consumption"],
    "overheating": ["overheat", "temperature", "coolant", "radiator"],
}


def expand_symptoms(text: str) -> list[str]:
    """Expand free-text symptom description into a deduplicated list of search terms.

    Splits ``text`` into individual words, checks each word against the keys
    of :data:`SYMPTOM_SYNONYMS`, and returns the union of all matching synonym
    lists.  The result is deduplicated while preserving insertion order.

    Args:
        text: Free-text symptom description, e.g. ``"engine misfire and shake"``.

    Returns:
        Deduplicated list of expanded search terms.  If no synonyms match,
        the original words from ``text`` are returned as-is so callers always
        receive something to search with.
    """
    words = text.lower().split()
    seen: dict[str, None] = {}  # ordered-set via dict keys

    for word in words:
        if word in SYMPTOM_SYNONYMS:
            for term in SYMPTOM_SYNONYMS[word]:
                seen[term] = None

    if not seen:
        # No synonym matches — fall back to the raw words so the caller
        # still gets terms to pass to the FTS engine.
        for word in words:
            seen[word] = None

    return list(seen.keys())


def match_symptoms(
    make: str,
    model: str,
    year: int,
    description: str,
    db: DiagnosticDB,
    limit: int = 20,
) -> list[dict]:
    """Match a symptom description against NHTSA complaints and group by component.

    Two-stage process:

    1. **Expand**: convert ``description`` into a list of search terms via
       :func:`expand_symptoms`.
    2. **Search**: query ``complaints_fts`` for each term and aggregate the
       results, counting how many complaints reference each component.

    Args:
        make: Vehicle manufacturer, e.g. ``"FORD"``.
        model: Vehicle model, e.g. ``"F-150"``.
        year: Model year, e.g. ``2020``.
        description: Free-text symptom description from the mechanic.
        db: Open :class:`~src.data.db_service.DiagnosticDB` instance.
        limit: Total maximum number of complaint rows to retrieve across all
            expanded terms.

    Returns:
        List of dicts sorted by ``count`` descending, each containing:

        - ``component`` (str): Component name as stored in the complaints DB.
        - ``count`` (int): Number of complaints mentioning this component.
        - ``confidence_hint`` (float): Rough estimate in [0, 1] — ``min(1.0, count / 50)``.
        - ``samples`` (list[str]): Up to 3 complaint summary strings.

        Returns an empty list if no complaints are found.
    """
    terms = expand_symptoms(description)
    if not terms:
        logger.warning("expand_symptoms returned no terms for description: %r", description)
        return []

    # Per-term budget: split the total limit evenly, minimum 5 per term.
    per_term_limit = max(5, limit // len(terms))

    # Accumulate raw complaint rows across all terms.
    # component -> list of summary strings
    component_summaries: dict[str, list[str]] = defaultdict(list)
    # component -> total hit count
    component_counts: dict[str, int] = defaultdict(int)

    for term in terms:
        rows = db.search_complaints(make, model, year, term, limit=per_term_limit)
        for row in rows:
            component: str = row.get("component") or "UNKNOWN"
            summary: str = row.get("summary") or ""
            component_counts[component] += 1
            if summary:
                component_summaries[component].append(summary)

    if not component_counts:
        logger.info(
            "match_symptoms('%s','%s',%d): no complaints found for terms %s",
            make, model, year, terms,
        )
        return []

    results: list[dict] = []
    for component, count in component_counts.items():
        confidence_hint = min(1.0, count / 50)
        samples = component_summaries[component][:3]
        results.append(
            {
                "component": component,
                "count": count,
                "confidence_hint": confidence_hint,
                "samples": samples,
            }
        )

    # Sort by complaint count descending so the most-reported component comes first.
    results.sort(key=lambda r: r["count"], reverse=True)

    logger.debug(
        "match_symptoms('%s','%s',%d,'%s') -> %d components",
        make, model, year, description, len(results),
    )
    return results
