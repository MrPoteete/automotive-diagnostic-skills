"""
Database service layer for automotive diagnostic data.

Wraps both SQLite databases with a clean Python API.
Primary source:   automotive_complaints.db  843 MB  (562K complaints FTS5, 211K TSBs, 7,117 recalls, 49,806 EPA vehicles)
Secondary source: automotive_diagnostics.db 1.1 MB  (3,073 DTC codes, 792 vehicles ⚠️ 2005 only — known gap, see .claude/docs/DIAGRAMS.md)

Checked AGENTS.md - implementing directly because this is a one-line docstring
correction (row counts), not a schema or query change. No data-engineer design
decisions required.
"""

import logging
import re
import sqlite3
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Database paths resolved relative to this file's project root.
# src/data/db_service.py  ->  .parent.parent.parent  ->  project root
# ---------------------------------------------------------------------------
_PROJECT_ROOT: Path = Path(__file__).parent.parent.parent
COMPLAINTS_DB_PATH: Path = _PROJECT_ROOT / "database" / "automotive_complaints.db"
DIAGNOSTICS_DB_PATH: Path = _PROJECT_ROOT / "database" / "automotive_diagnostics.db"


def _sanitize_fts_query(query: str) -> str:
    """Sanitize a free-text query for safe use with FTS5 MATCH.

    Replicates the exact logic from home_server.py so every call site
    behaves identically.  Special characters that cause FTS5 syntax errors
    (quotes, parentheses, operators) are replaced with spaces.

    Args:
        query: Raw user-supplied search string.

    Returns:
        Sanitized query string.  If sanitization reduces the string to
        empty, the original value is returned unchanged.
    """
    clean_query = re.sub(r"[^a-zA-Z0-9\s]", " ", query)
    clean_query = re.sub(r"\s+", " ", clean_query).strip()
    if not clean_query:
        clean_query = query
    return clean_query


class DiagnosticDB:
    """Service wrapper around the two automotive SQLite databases.

    Connections are opened lazily on first use and can be re-opened
    automatically via ``_connect()`` if they have been externally closed.

    Example::

        with DiagnosticDB() as db:
            rows = db.search_complaints("FORD", "F-150", 2020, "misfire")
    """

    def __init__(self) -> None:
        self._complaints_conn: Optional[sqlite3.Connection] = None
        self._diagnostics_conn: Optional[sqlite3.Connection] = None

    # ------------------------------------------------------------------
    # Internal connection helpers
    # ------------------------------------------------------------------

    def _connect_complaints(self) -> sqlite3.Connection:
        """Return (or lazily open) the complaints database connection."""
        if self._complaints_conn is None:
            try:
                self._complaints_conn = sqlite3.connect(
                    str(COMPLAINTS_DB_PATH), check_same_thread=False
                )
                self._complaints_conn.row_factory = sqlite3.Row
                logger.debug("Opened complaints DB: %s", COMPLAINTS_DB_PATH)
            except sqlite3.Error as exc:
                logger.error(
                    "Failed to connect to complaints DB at %s: %s",
                    COMPLAINTS_DB_PATH,
                    exc,
                )
                raise
        return self._complaints_conn

    def _connect_diagnostics(self) -> sqlite3.Connection:
        """Return (or lazily open) the diagnostics database connection."""
        if self._diagnostics_conn is None:
            try:
                self._diagnostics_conn = sqlite3.connect(
                    str(DIAGNOSTICS_DB_PATH), check_same_thread=False
                )
                self._diagnostics_conn.row_factory = sqlite3.Row
                logger.debug("Opened diagnostics DB: %s", DIAGNOSTICS_DB_PATH)
            except sqlite3.Error as exc:
                logger.error(
                    "Failed to connect to diagnostics DB at %s: %s",
                    DIAGNOSTICS_DB_PATH,
                    exc,
                )
                raise
        return self._diagnostics_conn

    def _connect(self) -> sqlite3.Connection:
        """Return the primary connection, reconnecting automatically if closed.

        Performs a lightweight probe query to detect a stale connection and
        re-opens it transparently.

        Returns:
            An open ``sqlite3.Connection`` to the complaints database.
        """
        try:
            conn = self._connect_complaints()
            conn.execute("SELECT 1")
            return conn
        except sqlite3.ProgrammingError:
            # Connection was closed externally — discard it and reconnect.
            self._complaints_conn = None
            return self._connect_complaints()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def search_complaints(
        self,
        make: str,
        model: str,
        year: int,
        query: str,
        limit: int = 20,
    ) -> list[dict]:
        """Search NHTSA complaints using FTS5 full-text search.

        When ``query`` produces a non-empty sanitized string, FTS5 MATCH is
        used for ranked relevance ordering.  When the sanitized query is
        empty, results are returned by vehicle filter alone.

        The ``year`` column in ``complaints_fts`` is TEXT; it is cast to
        INTEGER in the WHERE clause.  A ±3 year window is applied to
        surface complaints from adjacent model years.

        Args:
            make: Vehicle manufacturer, e.g. ``"FORD"``.
            model: Vehicle model, e.g. ``"F-150"``.
            year: Center model year, e.g. ``2020``.
            query: Free-text symptom or keyword description.
            limit: Maximum number of rows to return.

        Returns:
            List of dicts with keys: ``make``, ``model``, ``year``,
            ``component``, ``summary``.  Empty list on error.
        """
        clean_query = _sanitize_fts_query(query)
        year_low = year - 3
        year_high = year + 3

        try:
            conn = self._connect()
            cursor = conn.cursor()

            if clean_query:
                sql = """
                    SELECT make, model, year, component, summary
                    FROM complaints_fts
                    WHERE complaints_fts MATCH ?
                      AND make LIKE ?
                      AND model LIKE ?
                      AND CAST(year AS INTEGER) BETWEEN ? AND ?
                    ORDER BY rank
                    LIMIT ?
                """
                params: tuple = (
                    clean_query,
                    f"%{make}%",
                    f"%{model}%",
                    year_low,
                    year_high,
                    limit,
                )
            else:
                # Empty query after sanitization — filter-only fallback.
                sql = """
                    SELECT make, model, year, component, summary
                    FROM complaints_fts
                    WHERE make LIKE ?
                      AND model LIKE ?
                      AND CAST(year AS INTEGER) BETWEEN ? AND ?
                    LIMIT ?
                """
                params = (
                    f"%{make}%",
                    f"%{model}%",
                    year_low,
                    year_high,
                    limit,
                )

            cursor.execute(sql, params)
            results: list[dict] = [dict(row) for row in cursor.fetchall()]
            logger.debug(
                "search_complaints('%s','%s',%d,'%s') -> %d rows",
                make, model, year, query, len(results),
            )
            return results

        except sqlite3.Error as exc:
            logger.error(
                "search_complaints error for %s %s %d '%s': %s",
                make, model, year, query, exc,
            )
            return []

    def search_tsbs(
        self,
        make: str,
        model: str,
        year: int,
        component: str = "",
        limit: int = 10,
    ) -> list[dict]:
        """Retrieve TSBs matching the given vehicle, with optional component filter.

        Queries the structured ``nhtsa_tsbs`` table directly (not the FTS
        virtual table) so all columns are available in the result set.
        Year is compared as TEXT because the schema stores it that way.

        Args:
            make: Vehicle manufacturer.
            model: Vehicle model.
            year: Model year (exact TEXT match against the ``year`` column).
            component: Optional component keyword for additional filtering.
            limit: Maximum number of rows to return.

        Returns:
            List of dicts containing all ``nhtsa_tsbs`` columns.
            Empty list on error.
        """
        year_str = str(year)

        try:
            conn = self._connect()
            cursor = conn.cursor()

            params: tuple  # width varies between the two branches below
            if component:
                sql = """
                    SELECT nhtsa_id, bulletin_no, bulletin_date,
                           make, model, year, component, summary, created_at
                    FROM nhtsa_tsbs
                    WHERE make LIKE ?
                      AND model LIKE ?
                      AND year = ?
                      AND component LIKE ?
                    LIMIT ?
                """
                params = (
                    f"%{make}%",
                    f"%{model}%",
                    year_str,
                    f"%{component}%",
                    limit,
                )
            else:
                sql = """
                    SELECT nhtsa_id, bulletin_no, bulletin_date,
                           make, model, year, component, summary, created_at
                    FROM nhtsa_tsbs
                    WHERE make LIKE ?
                      AND model LIKE ?
                      AND year = ?
                    LIMIT ?
                """
                params = (f"%{make}%", f"%{model}%", year_str, limit)

            cursor.execute(sql, params)
            results: list[dict] = [dict(row) for row in cursor.fetchall()]
            logger.debug(
                "search_tsbs('%s','%s',%d,'%s') -> %d rows",
                make, model, year, component, len(results),
            )
            return results

        except sqlite3.Error as exc:
            logger.error(
                "search_tsbs error for %s %s %d '%s': %s",
                make, model, year, component, exc,
            )
            return []

    # Checked AGENTS.md - implementing directly: same SQL pattern as search_tsbs above,
    # read-only query, no schema changes, no safety logic.
    def search_tsbs_for_platform(
        self,
        siblings: list[dict],
        component: str,
        year_window: int = 3,
        limit: int = 10,
    ) -> list[dict]:
        """Retrieve TSBs across a list of platform sibling vehicles.

        siblings: list of {make, model, year_from, year_to} dicts from PlatformService.
        component: NHTSA component keyword to filter by (e.g. 'ENGINE').
        year_window: how many years on either side of year_from/year_to to search.
        Returns up to limit TSBs, tagged with platform_source=True.
        """
        if not siblings:
            return []

        conditions: list[str] = []
        params: list[str | int] = []

        for s in siblings:
            year_from = (s.get("year_from") or 1990) - year_window
            year_to = (s.get("year_to") or 2030) + year_window
            conditions.append(
                "(make LIKE ? AND model LIKE ? AND CAST(year AS INTEGER) BETWEEN ? AND ?)"
            )
            params.extend([f"%{s['make']}%", f"%{s['model']}%", year_from, year_to])

        where = " OR ".join(conditions)
        if component:
            where = f"({where}) AND component LIKE ?"
            params.append(f"%{component}%")

        sql = f"""
            SELECT nhtsa_id, bulletin_no, bulletin_date,
                   make, model, year, component, summary, created_at
            FROM nhtsa_tsbs
            WHERE {where}
            ORDER BY bulletin_date DESC
            LIMIT ?
        """
        params.append(limit)

        try:
            conn = self._connect()
            cursor = conn.cursor()
            cursor.execute(sql, params)
            results = [dict(row) for row in cursor.fetchall()]
            for r in results:
                r["platform_source"] = True
            logger.debug(
                "search_tsbs_for_platform: %d siblings, component=%r → %d rows",
                len(siblings), component, len(results),
            )
            return results
        except sqlite3.Error as exc:
            logger.error("search_tsbs_for_platform error: %s", exc)
            return []

    def count_complaints(
        self,
        make: str,
        model: str,
        year: int,
        component: str,
    ) -> int:
        """Count complaints matching a vehicle and component keyword.

        A ±5 year window is used to capture broader component failure
        frequency across a vehicle generation, which gives more stable
        frequency estimates than a single-year count.

        Args:
            make: Vehicle manufacturer.
            model: Vehicle model.
            year: Center model year for the search window.
            component: Component keyword, e.g. ``"engine"`` or ``"brake"``.

        Returns:
            Integer count of matching complaints.  Returns ``0`` on error.
        """
        year_low = year - 5
        year_high = year + 5

        try:
            conn = self._connect()
            cursor = conn.cursor()

            sql = """
                SELECT COUNT(*) AS cnt
                FROM complaints_fts
                WHERE make LIKE ?
                  AND model LIKE ?
                  AND component LIKE ?
                  AND CAST(year AS INTEGER) BETWEEN ? AND ?
            """
            cursor.execute(
                sql,
                (
                    f"%{make}%",
                    f"%{model}%",
                    f"%{component}%",
                    year_low,
                    year_high,
                ),
            )
            row = cursor.fetchone()
            count: int = int(row["cnt"]) if row else 0
            logger.debug(
                "count_complaints('%s','%s',%d,'%s') -> %d",
                make, model, year, component, count,
            )
            return count

        except sqlite3.Error as exc:
            logger.error(
                "count_complaints error for %s %s %d '%s': %s",
                make, model, year, component, exc,
            )
            return 0

    def get_complaint_samples(
        self,
        make: str,
        model: str,
        year: int,
        component: str,
        limit: int = 5,
    ) -> list[str]:
        """Return sample complaint summary strings for a vehicle and component.

        Uses FTS5 MATCH with ``component`` as the search term so results
        are ranked by relevance.  Year window is ±3.

        Args:
            make: Vehicle manufacturer.
            model: Vehicle model.
            year: Center model year.
            component: Component keyword used as the FTS query term.
            limit: Maximum number of summaries to return.

        Returns:
            List of summary strings.  Empty list when no data found or on error.
        """
        clean_component = _sanitize_fts_query(component)
        if not clean_component:
            clean_component = component

        year_low = year - 3
        year_high = year + 3

        try:
            conn = self._connect()
            cursor = conn.cursor()

            sql = """
                SELECT summary
                FROM complaints_fts
                WHERE complaints_fts MATCH ?
                  AND make LIKE ?
                  AND model LIKE ?
                  AND CAST(year AS INTEGER) BETWEEN ? AND ?
                ORDER BY rank
                LIMIT ?
            """
            cursor.execute(
                sql,
                (
                    clean_component,
                    f"%{make}%",
                    f"%{model}%",
                    year_low,
                    year_high,
                    limit,
                ),
            )
            summaries: list[str] = [row["summary"] for row in cursor.fetchall()]
            logger.debug(
                "get_complaint_samples('%s','%s',%d,'%s') -> %d rows",
                make, model, year, component, len(summaries),
            )
            return summaries

        except sqlite3.Error as exc:
            logger.error(
                "get_complaint_samples error for %s %s %d '%s': %s",
                make, model, year, component, exc,
            )
            return []

    def get_complaints_by_year(
        self,
        make: str,
        model: str,
        component: str,
    ) -> list[dict]:
        """Aggregate complaint counts by year for trend analysis.

        Groups all matching complaints by the ``year`` TEXT column and
        returns them in chronological order.

        Args:
            make: Vehicle manufacturer.
            model: Vehicle model.
            component: Component keyword filter.

        Returns:
            List of dicts with keys ``year`` (str) and ``count`` (int),
            ordered by year ascending.  Empty list on error.
        """
        try:
            conn = self._connect()
            cursor = conn.cursor()

            sql = """
                SELECT year, COUNT(*) AS count
                FROM complaints_fts
                WHERE make LIKE ?
                  AND model LIKE ?
                  AND component LIKE ?
                GROUP BY year
                ORDER BY year
            """
            cursor.execute(
                sql,
                (f"%{make}%", f"%{model}%", f"%{component}%"),
            )
            results: list[dict] = [
                {"year": row["year"], "count": int(row["count"])}
                for row in cursor.fetchall()
            ]
            logger.debug(
                "get_complaints_by_year('%s','%s','%s') -> %d year buckets",
                make, model, component, len(results),
            )
            return results

        except sqlite3.Error as exc:
            logger.error(
                "get_complaints_by_year error for %s %s '%s': %s",
                make, model, component, exc,
            )
            return []

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    # Checked AGENTS.md - implementing directly: simple read-only SQL on existing complaints DB
    def get_recalls(self, make: str, model: str, year: int, limit: int = 20) -> list[dict]:
        """Return NHTSA recalls for a vehicle/year from the nhtsa_recalls table.

        Uses year-range matching (year_from <= year <= year_to) to handle
        multi-year campaigns correctly.

        Args:
            make: Vehicle manufacturer (uppercase).
            model: Vehicle model (uppercase).
            year: Model year integer.
            limit: Maximum number of rows to return.

        Returns:
            List of recall dicts. Empty list on error or no data.
        """
        try:
            conn = self._connect()
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT campaign_no, component, summary, consequence,
                       remedy, vehicles_affected, report_date,
                       park_it, park_outside, year_from, year_to
                FROM nhtsa_recalls
                WHERE UPPER(make) = ? AND UPPER(model) = ?
                  AND (year_from IS NULL OR year_from <= ?)
                  AND (year_to IS NULL OR year_to >= ?)
                ORDER BY report_date DESC
                LIMIT ?
                """,
                (make.upper(), model.upper(), year, year, limit),
            )
            rows = cursor.fetchall()
            return [dict(r) for r in rows]
        except Exception as exc:
            logger.warning("get_recalls failed for %s %s %d: %s", make, model, year, exc)
            return []

    def close(self) -> None:
        """Close both database connections."""
        for attr, label in (
            ("_complaints_conn", "complaints"),
            ("_diagnostics_conn", "diagnostics"),
        ):
            conn: Optional[sqlite3.Connection] = getattr(self, attr)
            if conn is not None:
                try:
                    conn.close()
                    logger.debug("Closed %s DB connection.", label)
                except sqlite3.Error as exc:
                    logger.warning("Error closing %s DB: %s", label, exc)
                finally:
                    setattr(self, attr, None)

    def __enter__(self) -> "DiagnosticDB":
        return self

    def __exit__(
        self,
        exc_type: object,
        exc_val: object,
        exc_tb: object,
    ) -> None:
        self.close()
