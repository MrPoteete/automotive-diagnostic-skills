# Checked AGENTS.md - implementing directly because:
# File I/O persistence layer with no auth surfaces. Design follows DDIA WAL
# and log-structured patterns. No open-ended architecture decisions to delegate.
"""
SessionStore — flat-file persistence for DiagnosticSession objects.

File format: YAML frontmatter + JSONL log body
  <sessions_dir>/<date>_<MAKE>_<MODEL>_<short-id>.session

The YAML frontmatter (between --- delimiters) stores fast-scan metadata
(vehicle, phase, turn_count, repair_order). The JSONL body is the append-only
log. Reading only frontmatter is cheap — no need to parse the full transcript
for vehicle lookups or recent-session lists.

Path traversal is sanitised: session_id and filename_stem are stripped of
path-separator characters before building file paths.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any, Iterator

import yaml

from src.diagnostic.session_state import DiagnosticSession

logger = logging.getLogger(__name__)

_DEFAULT_SESSIONS_DIR = (
    Path(__file__).resolve().parent.parent.parent / "data" / "sessions"
)
_FRONTMATTER_SEP = "---"
_SESSION_EXT = ".session"


class SessionStore:
    """Read/write DiagnosticSession objects as YAML-frontmatter + JSONL files."""

    def __init__(self, sessions_dir: Path | str | None = None) -> None:
        self._dir = Path(sessions_dir) if sessions_dir else _DEFAULT_SESSIONS_DIR
        self._dir.mkdir(parents=True, exist_ok=True)

    # ── Write ─────────────────────────────────────────────────────────────────

    def save(self, session: DiagnosticSession) -> Path:
        """Persist *session* to disk as frontmatter + JSONL.

        Overwrites if a file for this session already exists (idempotent).
        Returns the file path written.
        """
        path = self._path_for(session)
        frontmatter = self._build_frontmatter(session)
        jsonl_body = "\n".join(json.dumps(entry) for entry in session.full_log)
        content = f"{_FRONTMATTER_SEP}\n{frontmatter}{_FRONTMATTER_SEP}\n{jsonl_body}"
        path.write_text(content, encoding="utf-8")
        logger.debug("SessionStore: saved %s → %s", session.session_id, path.name)
        return path

    # ── Read ──────────────────────────────────────────────────────────────────

    def load(self, session_id: str) -> DiagnosticSession | None:
        """Load a session by ID. Returns None if not found or file is corrupt."""
        path = self._find_by_id(session_id)
        if path is None:
            logger.debug("SessionStore: not found: %s", session_id)
            return None
        return self._parse_file(path)

    def load_file(self, path: Path) -> DiagnosticSession | None:
        """Load a session directly from a file path."""
        return self._parse_file(path)

    def exists(self, session_id: str) -> bool:
        return self._find_by_id(session_id) is not None

    # ── Search ────────────────────────────────────────────────────────────────

    def find_by_vehicle(
        self,
        make: str | None = None,
        model: str | None = None,
        year: int | str | None = None,
    ) -> list[DiagnosticSession]:
        """Return sessions matching the given vehicle fields (case-insensitive).

        Only the YAML frontmatter is read — no JSONL parsing for fast lookup.
        Results are sorted newest-first.
        """
        matches = []
        for path in self._all_paths():
            try:
                fm = self._read_frontmatter(path)
            except Exception:
                continue
            if make and fm.get("vehicle_make", "").upper() != make.upper():
                continue
            if model and fm.get("vehicle_model", "").upper() != model.upper():
                continue
            if year is not None and str(fm.get("vehicle_year", "")) != str(year):
                continue
            session = self._parse_file(path)
            if session is not None:
                matches.append(session)
        matches.sort(key=lambda s: s.last_updated, reverse=True)
        return matches

    def find_recent(self, n: int = 10) -> list[DiagnosticSession]:
        """Return the *n* most recently updated sessions."""
        paths = sorted(
            self._all_paths(),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        results = []
        for path in paths[:n]:
            session = self._parse_file(path)
            if session is not None:
                results.append(session)
        return results

    def find_by_vin(self, vin: str) -> list[DiagnosticSession]:
        """Return all sessions matching the given VIN (case-insensitive), newest-first."""
        vin_upper = vin.strip().upper()
        matches = []
        for path in self._all_paths():
            try:
                fm = self._read_frontmatter(path)
            except Exception:
                continue
            if fm.get("vehicle_vin", "").upper() == vin_upper:
                session = self._parse_file(path)
                if session is not None:
                    matches.append(session)
        matches.sort(key=lambda s: s.last_updated, reverse=True)
        return matches

    def find_by_repair_order(self, repair_order: str) -> DiagnosticSession | None:
        """Return the most recent session with the given repair_order, or None."""
        for path in sorted(self._all_paths(), key=lambda p: p.stat().st_mtime, reverse=True):
            try:
                fm = self._read_frontmatter(path)
            except Exception:
                continue
            if str(fm.get("repair_order", "")).strip() == repair_order.strip():
                return self._parse_file(path)
        return None

    def list_summaries(self) -> list[dict[str, Any]]:
        """Return frontmatter-only metadata for all sessions (no body parsing)."""
        summaries = []
        for path in sorted(self._all_paths(), key=lambda p: p.stat().st_mtime, reverse=True):
            try:
                fm = self._read_frontmatter(path)
                fm["_file"] = path.name
                summaries.append(fm)
            except Exception:
                continue
        return summaries

    # ── Enumerate ─────────────────────────────────────────────────────────────

    def iter_sessions(self) -> Iterator[DiagnosticSession]:
        """Yield all sessions, newest-first. Skips corrupt files."""
        for path in sorted(self._all_paths(), key=lambda p: p.stat().st_mtime, reverse=True):
            session = self._parse_file(path)
            if session is not None:
                yield session

    def count(self) -> int:
        return sum(1 for _ in self._all_paths())

    # ── Delete ────────────────────────────────────────────────────────────────

    def delete(self, session_id: str) -> bool:
        path = self._find_by_id(session_id)
        if path is not None:
            path.unlink()
            logger.debug("SessionStore: deleted %s", session_id)
            return True
        return False

    # ── Internal ──────────────────────────────────────────────────────────────

    def _path_for(self, session: DiagnosticSession) -> Path:
        stem = self._sanitise_filename(session.filename_stem)
        return self._dir / f"{stem}{_SESSION_EXT}"

    def _find_by_id(self, session_id: str) -> Path | None:
        """Locate a session file containing *session_id* in its stem."""
        short = session_id[:8].replace("-", "")
        for path in self._all_paths():
            if short in path.stem:
                # Verify it's really this session (avoid prefix collisions)
                try:
                    fm = self._read_frontmatter(path)
                    if fm.get("session_id") == session_id:
                        return path
                except Exception:
                    continue
        return None

    def _all_paths(self) -> list[Path]:
        return list(self._dir.glob(f"*{_SESSION_EXT}"))

    @staticmethod
    def _sanitise_filename(name: str) -> str:
        """Strip characters that could cause path traversal or OS issues."""
        return re.sub(r"[^A-Za-z0-9_\-]", "_", name)

    @staticmethod
    def _build_frontmatter(session: DiagnosticSession) -> str:
        data: dict[str, Any] = {
            "session_id":    session.session_id,
            "vehicle_year":  session.vehicle.get("year", ""),
            "vehicle_make":  session.vehicle.get("make", ""),
            "vehicle_model": session.vehicle.get("model", ""),
            "vehicle_engine": session.vehicle.get("engine", ""),
            "symptoms":      session.symptoms,
            "phase":         session.phase,
            "turns":         session.turn_count,
            "resolved":      session.phase in ("RESOLUTION",),
            "created_at":    session.created_at,
            "last_updated":  session.last_updated,
        }
        if session.repair_order is not None:
            data["repair_order"] = session.repair_order
        if session.eliminated_hypotheses:
            data["eliminated_hypotheses"] = session.eliminated_hypotheses
        # Store VIN in frontmatter for fast lookup without JSONL parse
        vin = session.vehicle.get("vin", "")
        if vin and vin.upper() != "N/A":
            data["vehicle_vin"] = vin.upper()
        return yaml.dump(data, default_flow_style=False, allow_unicode=True)

    @staticmethod
    def _read_frontmatter(path: Path) -> dict[str, Any]:
        """Parse only the YAML frontmatter block without reading the JSONL body."""
        text = path.read_text(encoding="utf-8")
        if not text.startswith(_FRONTMATTER_SEP):
            raise ValueError(f"No frontmatter in {path.name}")
        # Find second --- delimiter
        second = text.find(_FRONTMATTER_SEP, len(_FRONTMATTER_SEP))
        if second == -1:
            raise ValueError(f"Unclosed frontmatter in {path.name}")
        yaml_text = text[len(_FRONTMATTER_SEP):second].strip()
        return yaml.safe_load(yaml_text) or {}

    def _parse_file(self, path: Path) -> DiagnosticSession | None:
        """Parse a full session file (frontmatter + JSONL body)."""
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            logger.warning("SessionStore: cannot read %s: %s", path.name, exc)
            return None

        # ── Split frontmatter from body ───────────────────────────────────────
        if not text.startswith(_FRONTMATTER_SEP):
            logger.warning("SessionStore: no frontmatter in %s — skipping", path.name)
            return None
        second = text.find(_FRONTMATTER_SEP, len(_FRONTMATTER_SEP))
        if second == -1:
            logger.warning("SessionStore: unclosed frontmatter in %s — skipping", path.name)
            return None

        yaml_text  = text[len(_FRONTMATTER_SEP):second].strip()
        jsonl_text = text[second + len(_FRONTMATTER_SEP):].strip()

        # ── Parse YAML frontmatter ────────────────────────────────────────────
        try:
            fm = yaml.safe_load(yaml_text) or {}
        except yaml.YAMLError as exc:
            logger.warning("SessionStore: YAML parse error in %s: %s", path.name, exc)
            return None

        # ── Parse JSONL log entries ───────────────────────────────────────────
        log: list[dict[str, Any]] = []
        for lineno, line in enumerate(jsonl_text.splitlines(), 1):
            line = line.strip()
            if not line:
                continue
            try:
                log.append(json.loads(line))
            except json.JSONDecodeError as exc:
                logger.warning(
                    "SessionStore: bad JSON on line %d of %s: %s — skipping line",
                    lineno, path.name, exc,
                )

        # ── Reconstruct session ───────────────────────────────────────────────
        vehicle = {
            "year":   fm.get("vehicle_year", ""),
            "make":   fm.get("vehicle_make", ""),
            "model":  fm.get("vehicle_model", ""),
            "engine": fm.get("vehicle_engine", ""),
        }
        if fm.get("vehicle_vin"):
            vehicle["vin"] = fm["vehicle_vin"]
        try:
            return DiagnosticSession(
                session_id=str(fm["session_id"]),
                vehicle=vehicle,
                symptoms=str(fm.get("symptoms", "")),
                repair_order=str(fm["repair_order"]) if "repair_order" in fm else None,
                phase=str(fm.get("phase", "SYMPTOM_COLLECTION")),
                turn_count=int(fm.get("turns", 0)),
                eliminated_hypotheses=list(fm.get("eliminated_hypotheses", [])),
                full_log=log,
                created_at=str(fm.get("created_at", "")),
                last_updated=str(fm.get("last_updated", "")),
            )
        except (KeyError, TypeError, ValueError) as exc:
            logger.warning("SessionStore: cannot reconstruct session from %s: %s", path.name, exc)
            return None
