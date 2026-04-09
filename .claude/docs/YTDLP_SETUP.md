# yt-dlp Setup — Desktop CLI

## Context for Claude Code

This project uses `yt-dlp` to pull YouTube transcripts (not video) as the primary ingestion mechanism for the RAG knowledge base. Two scripts consume it:

| Script | Purpose |
|---|---|
| `scripts/ingest_url.py` | Ingest a single URL (YouTube or web page) |
| `scripts/bulk_ingest.py` | Batch ingest latest N videos from curated channels |

Both scripts run on the NAS VM (`claude-dev`, 192.168.1.175). The desktop setup described here lets you run the same tools locally without the VM.

---

## Desktop Installation (Windows)

### Option A — Standalone binary (no Python required)

Download `yt-dlp.exe` from the GitHub releases page and place it somewhere on your PATH (e.g. `C:\tools\`):

```powershell
# PowerShell — download to C:\tools\ (create dir first if needed)
mkdir C:\tools -Force
Invoke-WebRequest -Uri "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe" `
    -OutFile "C:\tools\yt-dlp.exe"

# Add C:\tools to your user PATH if not already there
[Environment]::SetEnvironmentVariable(
    "Path",
    "$env:Path;C:\tools",
    [EnvironmentVariableTarget]::User
)
```

Verify:
```powershell
yt-dlp --version
```

### Option B — via pip / uv (Python already installed)

```powershell
pip install yt-dlp
# or, if using uv:
uv pip install yt-dlp
```

---

## ffmpeg (required for audio fallback)

If a video has no auto-captions, the scripts fall back to downloading lowest-quality audio. `ffmpeg` is needed for that fallback path.

```powershell
# winget (Windows 11 / updated Win10)
winget install Gyan.FFmpeg

# or Chocolatey
choco install ffmpeg
```

After install, verify ffmpeg is on PATH: `ffmpeg -version`

> **Note**: If you only care about transcript-first (Phase 1), ffmpeg is optional — most major automotive channels have auto-captions.

---

## Basic CLI Usage

```bash
# Test that yt-dlp can reach a video
yt-dlp --print title "https://www.youtube.com/watch?v=VIDEO_ID"

# Download English auto-captions only (no video) — what the project does
yt-dlp --write-auto-subs --sub-lang en --sub-format vtt \
       --skip-download -o "%(id)s" "URL"

# List available subtitle languages for a video
yt-dlp --list-subs "URL"

# Fetch channel video list (flat, no download)
yt-dlp --flat-playlist --print "%(url)s %(title)s" \
       "https://www.youtube.com/@ScannerDanner/videos"
```

---

## Running the Project Scripts on Desktop

The scripts use `yt-dlp` as a Python library (`import yt_dlp`), not as a subprocess. Install the project deps first:

```bash
# From the project root
uv sync          # installs all deps including yt-dlp

# Ingest a single video
uv run python scripts/ingest_url.py "https://www.youtube.com/watch?v=VIDEO_ID"

# Dry-run bulk ingest for one channel
uv run python scripts/bulk_ingest.py --channel rainman --limit 5 --dry-run

# Full bulk ingest (all channels, 20 videos each)
uv run python scripts/bulk_ingest.py
```

---

## How the Project Uses yt-dlp Internally

Both scripts share the same two-phase strategy to protect disk space:

**Phase 1** — `skip_download=True`  
Fetches only the `.vtt` subtitle file. No video or audio bytes touch disk. This succeeds for ~90% of channels (YouTube auto-captions exist).

**Phase 2** — `format: worstaudio/worst`  
Only runs if Phase 1 returns no subtitles. Downloads the smallest possible audio stream to a `tempfile.TemporaryDirectory` — the directory is auto-deleted on exit regardless of success or failure.

A disk-space guardrail (`MIN_FREE_GB = 5`) aborts the run if the root filesystem is too full before any download attempt.

---

## Updating yt-dlp

YouTube's extractor breaks frequently. Update before a bulk run if you see 403/410 errors:

```bash
# Standalone binary
yt-dlp -U

# pip / uv
uv pip install -U yt-dlp
```

---

## Environment Variables (optional)

| Variable | Purpose | Default |
|---|---|---|
| `FIRECRAWL_URL` | Local Firecrawl instance for web scraping fallback | `""` (disabled) |
| `FIRECRAWL_API_KEY` | Firecrawl auth key | `local-only` |

Set in `.env` at project root or export in your shell. Not required for YouTube ingestion.

---

## Manifest File

`data/ingested_videos_manifest.jsonl` — append-only log of every ingested video URL. The bulk script checks this before downloading to skip already-processed videos. Keep it committed and in sync between the VM and desktop if you run ingestion on both.
