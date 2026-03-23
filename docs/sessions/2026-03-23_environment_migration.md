# Session Summary — Environment Migration & NAS Setup
**Date**: 2026-03-23
**Scope**: Full environment migration from Windows-side WSL2 to dual-environment setup (WSL2 PC + NAS Ubuntu VM)

---

## What Was Done

### 1. Git Configuration (WSL2 PC)
- Configured global git identity: `MrPoteete / poteete.michael.mp@gmail.com`
- Default branch: `main`, editor: `nano`, credential helper: `store`
- SSH key already existed at `~/.ssh/id_ed25519` (fingerprint: `SHA256:2dAiRaP9L78+xzX+9Vj0sZPH/3qm6IQb4FdBPi0f2xA`)
- Key registered in GitHub as `Claude_dev_Server_Ubuntu_Key` — verified working

### 2. NAS SMB Mount (WSL2 PC)
- Installed `cifs-utils` and `smbclient`
- Mounted TrueNAS share at `/mnt/z/`
  - Share: `//100.99.29.103/claude-code-diag-reports`
  - User: `Michael` / credentials in `/etc/samba/nas_credentials` (root-readable only)
  - Mount options: `vers=2.1,sec=ntlmssp,uid=1000,gid=1000`
- Made persistent via `/etc/fstab`
- NAS share structure: `/mnt/z/Customer/`, `/mnt/z/Fleet/`, `/mnt/z/Pre-Purchase/`
- `scripts/nas_output.py` auto-detects mount and routes reports there; falls back to local `reports/` if unmounted

### 3. Environment & Line Endings Fix
- Added `.gitattributes` to normalize all text files to LF (CRLF → LF migration from Windows)
- Updated `docs/TROUBLESHOOTING_WSL.md`: reflects WSL-native setup at `/home/poteete/`
- Updated `docs/ENVIRONMENT_SETUP.md`: added NAS mount documentation
- Committed and pushed: `db8e9d4`

### 4. GCP Secret Manager Integration
- Installed `google-cloud-cli` on WSL2 PC
- Authenticated: `gcloud auth login` + `gcloud config set project poteete-secrets`
- Secret: `gemini-api-key` in project `poteete-secrets` → exported as `GOOGLE_API_KEY`
- Created `~/.claude/load-secrets.sh` — fetches secrets at shell startup
- Added `source ~/.claude/load-secrets.sh` to `~/.bashrc`
- To add more secrets: add `_fetch_secret "secret-name" "ENV_VAR_NAME"` to `load-secrets.sh`

### 5. Gemini MCP Server
- Created `.mcp.json` in project root (committed to repo)
- Uses bash wrapper to fetch key at runtime (Claude Code doesn't source `.bashrc`):
  ```json
  {
    "mcpServers": {
      "gemini": {
        "type": "stdio",
        "command": "bash",
        "args": ["-c", "export GEMINI_API_KEY=$(gcloud secrets versions access latest --secret=gemini-api-key --project=poteete-secrets 2>/dev/null) && npx -y @houtini/gemini-mcp"]
      }
    }
  }
  ```
- `.gitignore` updated to allow `.mcp.json` (safe — no hardcoded keys)

### 6. Project `.env.local` Files
- **WSL2 PC** (`/home/poteete/projects/automotive-diagnostic-skills/.env.local`):
  ```
  NAS_REPORTS_MOUNT=/mnt/z
  ```
- **NAS** (`/home/poteete/projects/automotive-diagnostic-skills/.env.local`):
  ```
  NAS_REPORTS_MOUNT=/mnt/nas-reports
  ```
- These files are gitignored — each machine maintains its own

### 7. NAS Ubuntu VM Setup (claude-dev)
- **Host**: `claude-dev` / `192.168.1.175` / Tailscale `100.78.80.127`
- **User**: `poteete` (Linux user); `Michael` is the TrueNAS UI user only
- SSH access from WSL2 PC: key authorized at `/home/poteete/.ssh/authorized_keys`
- **Tools confirmed**: Claude Code 2.1.81, Python 3.12.3, Node v22.22.1, uv, git, gcloud 561.0.0
- **Repo**: already cloned at `~/projects/automotive-diagnostic-skills` (up to date with `main`)
- **Reports mount**: `/mnt/nas-reports/` → TrueNAS share (already mounted, has Customer/Fleet/Pre-Purchase)
- **GitHub SSH**: authenticated as `MrPoteete` ✅
- **gcloud**: authenticated, project set to `poteete-secrets`, `gemini-api-key` accessible
- **Claude config**: `~/.claude/` already populated (agents, hooks, settings, load-secrets.sh)

---

## Current Environment Map

| Resource | WSL2 PC | NAS (claude-dev) |
|----------|---------|-----------------|
| Hostname | (Windows PC) | `claude-dev` |
| IP | local | `192.168.1.175` / `100.78.80.127` (Tailscale) |
| Project path | `/home/poteete/projects/automotive-diagnostic-skills` | `/home/poteete/projects/automotive-diagnostic-skills` |
| Reports mount | `/mnt/z/` | `/mnt/nas-reports/` |
| NAS_REPORTS_MOUNT env | `/mnt/z` | `/mnt/nas-reports` |
| Claude config | `~/.claude/` | `~/.claude/` |
| gcloud project | `poteete-secrets` | `poteete-secrets` |

---

## Pending Tasks

1. **Voice input in WSL2** — WSL2 has no audio device (no ALSA/PulseAudio). Need to bridge Windows microphone. Options: PulseAudio Windows server + WSL client, or PipeWire. Required since server is primary work environment.

---

## Key File Locations

| File | Purpose |
|------|---------|
| `~/.claude/load-secrets.sh` | Fetches GCP secrets into env vars at shell startup |
| `/etc/samba/nas_credentials` | NAS SMB credentials (WSL2 PC only, root-readable) |
| `scripts/nas_output.py` | Report path resolver — auto-detects NAS mount |
| `.mcp.json` | Gemini MCP server config (committed, GCP key fetched at runtime) |
| `.env.local` | Per-machine overrides (gitignored) |
| `docs/ENVIRONMENT_SETUP.md` | NAS mount documentation |
| `docs/TROUBLESHOOTING_WSL.md` | WSL-native environment guide |

---

## How to Start Working on NAS

```bash
ssh poteete@192.168.1.175
cd ~/projects/automotive-diagnostic-skills
claude
```

The Gemini MCP will load automatically from `.mcp.json` when Claude Code starts in the project directory.
