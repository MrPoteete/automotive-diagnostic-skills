# Environment Setup Guide

**Environment**: Ubuntu 24.04 LTS — TrueNAS VM (`claude-dev`), native Linux

| Detail | Value |
|--------|-------|
| Hostname | `claude-dev` |
| LAN IP | `192.168.1.175` |
| Tailscale | `100.78.80.127` |
| User | `poteete` |
| Home | `/home/poteete` |
| Project | `/home/poteete/projects/automotive-diagnostic-skills` |
| Shell | `bash` (native Linux — use Linux paths, no `/mnt/c`) |

---

## NAS Mount (Report Output)

Reports are written to the TrueNAS NFS share mounted at `/mnt/nas-reports`.

**Folder structure:**
```
/mnt/nas-reports/
├── Customer/       — customer diagnostic PDFs
├── Fleet/          — batch/fleet markdown reports
└── Pre-Purchase/   — pre-purchase inspection reports
```

If the mount drops, remount with:
```bash
sudo mount /mnt/nas-reports
```

The `scripts/nas_output.py` module auto-detects the NAS and falls back to `reports/` locally if unmounted.

---

## Services

Both services start automatically via systemd:

| Service | Port | Check |
|---------|------|-------|
| `diag-backend` | `:8000` | `systemctl status diag-backend` |
| `diag-frontend` | `:3000` | `systemctl status diag-frontend` |

---

## Python

Use `uv run` — no `.venv/bin/python` on this VM:

```bash
uv run python script.py
uv run --with requests python script.py   # ad-hoc deps
uv run pytest --tb=no -q                  # tests
```

---

## Quick Start

1. **Copy the template**:
   ```bash
   cp .env.example .env.local
   ```

2. **Edit `.env.local`** with your actual credentials (never commit this file)

3. **Load variables** in Python:
   ```python
   from dotenv import load_dotenv
   load_dotenv()
   ```

---

## Required Variables

### NHTSA API
```bash
NHTSA_API_BASE_URL=https://api.nhtsa.gov
```
No API key required. Rate limit: ~1000 requests/hour.

### Anthropic (Claude API)
```bash
ANTHROPIC_API_KEY=sk-ant-your_key_here
```

### Backend API Key (internal)
```bash
API_KEY=your-mechanic-api-key
```
Used by the Next.js proxy routes to authenticate against the FastAPI backend.

---

## Remote Access

The VM is reachable via Tailscale from anywhere:
- SSH: `ssh poteete@100.78.80.127`
- Frontend: `http://100.78.80.127:3000`
- Backend: `http://100.78.80.127:8000`

Telegram bot integration provides remote Claude Code access — see the Telegram MCP configuration in `.claude/settings.json`.
