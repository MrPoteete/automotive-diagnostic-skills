"""NAS output path resolver for all report types.

All diagnostic reports are written to the NAS at /mnt/z/ (Z:\\ on Windows),
which maps directly to the Claude-Code-Diag-Reports share on the NAS
(\\\\100.99.29.103\\Claude-Code-Diag-Reports).

If the NAS is not mounted, falls back to the local project reports/ directory.

NAS folder structure (Z:\\ root = share root):
    /mnt/z/
        Customer/       — customer-facing diagnostic PDFs (generate_report.py)
        Pre-Purchase/   — pre-purchase inspection checklists
        Fleet/          — batch/fleet comparison reports (batch_report.py, report_builder.py)
"""

import os
from datetime import datetime
from pathlib import Path

# ── NAS configuration ─────────────────────────────────────────────────────────
# /mnt/z = desktop WSL (Windows SMB mount), /mnt/nas-reports = NAS VM (NFS mount)
NAS_MOUNT = Path(os.environ.get("NAS_REPORTS_MOUNT", "/mnt/z"))
NAS_REPORTS_ROOT = NAS_MOUNT  # share root IS the reports root (no subfolder needed)

# Subfolders per report type — sit directly at Z:\ root
NAS_CUSTOMER_DIR = NAS_MOUNT / "Customer"
NAS_PREPURCHASE_DIR = NAS_MOUNT / "Pre-Purchase"
NAS_FLEET_DIR = NAS_MOUNT / "Fleet"

# ── Local fallback ─────────────────────────────────────────────────────────────
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
LOCAL_REPORTS_DIR = _PROJECT_ROOT / "reports"


def nas_available() -> bool:
    """Return True if the NAS is mounted and writable."""
    try:
        return NAS_MOUNT.is_mount() or (NAS_MOUNT.exists() and any(NAS_MOUNT.iterdir()))
    except OSError:
        return False


def _ensure(path: Path) -> Path:
    """Create directory and return it."""
    path.mkdir(parents=True, exist_ok=True)
    return path


def customer_reports_dir() -> Path:
    """Return the directory for customer diagnostic PDF reports."""
    if nas_available():
        return _ensure(NAS_CUSTOMER_DIR)
    return _ensure(LOCAL_REPORTS_DIR / "Customer")


def prepurchase_reports_dir() -> Path:
    """Return the directory for pre-purchase inspection reports."""
    if nas_available():
        return _ensure(NAS_PREPURCHASE_DIR)
    return _ensure(LOCAL_REPORTS_DIR / "Pre-Purchase")


def fleet_reports_dir() -> Path:
    """Return the directory for fleet / batch reports."""
    if nas_available():
        return _ensure(NAS_FLEET_DIR)
    return _ensure(LOCAL_REPORTS_DIR / "Fleet")


def customer_report_path(year: str, make: str, model: str, ro_number: str = "") -> Path:
    """Build a timestamped PDF path for a customer diagnostic report."""
    slug = "_".join(filter(None, [str(year), make.upper(), model.upper().replace(" ", "-"), ro_number]))
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    return customer_reports_dir() / f"diag_report_{slug}_{timestamp}.pdf"


def prepurchase_report_path(make: str, model: str, year_start: int, year_end: int, ext: str = "pdf") -> Path:
    """Build a timestamped path for a pre-purchase inspection report."""
    slug = f"{make.upper()}_{model.upper().replace(' ', '-')}_{year_start}_{year_end}"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    return prepurchase_reports_dir() / f"prepurchase_{slug}_{timestamp}.{ext}"


def fleet_report_path(make: str, model: str, yr_start: int, yr_end: int) -> Path:
    """Build the path for a fleet / batch markdown report."""
    slug = f"{make.lower()}_{model.lower().replace(' ', '_').replace('-', '_')}_{yr_start}_{yr_end}"
    return fleet_reports_dir() / f"{slug}.md"


def report_location_summary() -> str:
    """Return a human-readable string describing where reports are being saved."""
    if nas_available():
        return f"NAS ({NAS_REPORTS_ROOT})"
    return f"local fallback ({LOCAL_REPORTS_DIR})"
