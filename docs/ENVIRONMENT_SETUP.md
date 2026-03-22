# Environment Setup Guide

**Environment**: WSL2 Ubuntu 24.04 — native Linux, project at `/home/poteete/projects/automotive-diagnostic-skills`

## NAS Mount (Report Output)

Reports are written to the TrueNAS share at `\\100.99.29.103\claude-code-diag-reports`, mounted at `/mnt/z/`.

**Folder structure on NAS:**
```
/mnt/z/
├── Customer/       — customer diagnostic PDFs
├── Fleet/          — batch/fleet markdown reports
└── Pre-Purchase/   — pre-purchase inspection reports
```

**Mount is persistent** via `/etc/fstab`. If it drops, remount with:
```bash
sudo mount /mnt/z
```

Credentials stored at `/etc/samba/nas_credentials` (root-readable only).
The `scripts/nas_output.py` module auto-detects the NAS and falls back to `reports/` locally if unmounted.

---

## Quick Start

1. **Copy the template**:
   ```bash
   cp .env.example .env
   ```

2. **Edit `.env`** with your actual credentials (NEVER commit this file)

3. **Load variables** in your Python code:
   ```python
   import os
   from dotenv import load_dotenv

   load_dotenv()

   github_token = os.getenv("GITHUB_TOKEN")
   ```

## Required Variables

### GitHub Authentication
```bash
GITHUB_TOKEN=ghp_your_token_here
GITHUB_USERNAME=your_username
```

**How to get a GitHub token**:
1. Go to GitHub Settings → Developer Settings → Personal Access Tokens
2. Generate new token (classic)
3. Select scopes: `repo`, `read:org` (for private repos)
4. Copy token immediately (can't view it again)

### NHTSA API
```bash
NHTSA_API_BASE_URL=https://api.nhtsa.gov
```

No API key required, but rate limits apply (~1000 requests/hour).

### Optional: AI Services

**OpenAI** (for embeddings):
```bash
OPENAI_API_KEY=sk-your_key_here
```

**Anthropic** (Claude API):
```bash
ANTHROPIC_API_KEY=sk-ant-your_key_here
```

## Using Environment Variables

### In Python Scripts
```python
import os
from dotenv import load_dotenv
from pathlib import Path

# Load .env from project root
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

# Access variables
db_path = os.getenv("DATABASE_PATH", "database/automotive_diagnostics.db")
log_level = os.getenv("LOG_LEVEL", "INFO")

# Required variables (fail if missing)
github_token = os.environ["GITHUB_TOKEN"]  # Raises KeyError if missing
```

### In Shell Scripts
```bash
#!/bin/bash
set -a  # Auto-export all variables
source .env
set +a

echo "Using database: $DATABASE_PATH"
```

### In Claude Code Hooks
```python
#!/usr/bin/env python3
import os
from dotenv import load_dotenv

load_dotenv()

# Hooks have access to environment variables
api_key = os.getenv("CONTEXT7_API_KEY")
```

## Security Best Practices

### ✅ DO
- Keep `.env` in `.gitignore` (already configured)
- Use `.env.example` as a template (safe to commit)
- Rotate tokens regularly
- Use read-only tokens when possible
- Store production secrets in secure vaults (not `.env`)

### ❌ DON'T
- Commit `.env` to git
- Share `.env` files via email/chat
- Use production credentials in development
- Hard-code secrets in source files
- Check in files containing tokens

## Claude Code Hook Protection

The pre-tool-use hook **blocks** writing to `.env` files:
```
BLOCKED: Writing to .env files is not allowed via hooks.
Credential files should be managed manually to prevent leaks.
```

This prevents accidental commits of secrets.

## Troubleshooting

### "KeyError: GITHUB_TOKEN"
**Cause**: Variable not set in `.env`

**Fix**:
```bash
# Check if .env exists
ls -la .env

# If missing, copy template
cp .env.example .env

# Edit and add your token
nano .env
```

### "Module not found: dotenv"
**Install python-dotenv**:
```bash
pip install python-dotenv
# or
uv add python-dotenv
```

### Variables not loading
**Check load order**:
```python
from dotenv import load_dotenv
import os

# MUST call load_dotenv() BEFORE accessing os.getenv()
load_dotenv()
print(os.getenv("GITHUB_TOKEN"))  # Now works
```

## Database Configuration

Default database paths:
```bash
DATABASE_PATH=database/automotive_diagnostics.db
DATABASE_BACKUP_PATH=database/backups/
```

Override in `.env` if using custom locations.

## RAG Server Configuration

If running the local RAG server:
```bash
RAG_SERVER_HOST=localhost
RAG_SERVER_PORT=5000
RAG_MODEL_PATH=models/diagnostic-model
```

Start server:
```bash
python server/home_server.py
```

## Security Settings

Safety-critical thresholds:
```bash
SAFETY_CRITICAL_CONFIDENCE_THRESHOLD=0.9
REQUIRE_SOURCE_ATTRIBUTION=true
MAX_QUERY_LENGTH=2000
```

These enforce automotive safety requirements from `CLAUDE.md`.

## Example: Complete Setup

```bash
# 1. Clone repo
git clone https://github.com/your-username/automotive-diagnostic-skills
cd automotive-diagnostic-skills

# 2. Create .env from template
cp .env.example .env

# 3. Edit with your credentials
nano .env
# Add GITHUB_TOKEN, OPENAI_API_KEY, etc.

# 4. Install dependencies
pip install python-dotenv

# 5. Test environment loading
python -c "from dotenv import load_dotenv; import os; load_dotenv(); print('GITHUB_TOKEN:', 'SET' if os.getenv('GITHUB_TOKEN') else 'MISSING')"
```

## Reference

- [python-dotenv documentation](https://pypi.org/project/python-dotenv/)
- [GitHub Personal Access Tokens](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/creating-a-personal-access-token)
- [NHTSA API Documentation](https://vpic.nhtsa.dot.gov/api/)
