#!/usr/bin/env bash
# Checked AGENTS.md - setup script, no security-sensitive logic beyond API key prompt
# =============================================================================
# Automotive Diagnostic Skills — Setup Script
# Run this on any new machine (WSL Ubuntu recommended) to get fully operational.
# =============================================================================

set -e

REPO_URL="https://github.com/MrPoteete/automotive-diagnostic-skills.git"
PROJECT_DIR="$HOME/projects/automotive-diagnostic-skills"
BOLD="\033[1m"
GREEN="\033[0;32m"
YELLOW="\033[1;33m"
RED="\033[0;31m"
RESET="\033[0m"

info()    { echo -e "${BOLD}▶ $1${RESET}"; }
success() { echo -e "${GREEN}✓ $1${RESET}"; }
warn()    { echo -e "${YELLOW}⚠ $1${RESET}"; }
error()   { echo -e "${RED}✗ $1${RESET}"; }

echo ""
echo -e "${BOLD}========================================${RESET}"
echo -e "${BOLD}  Automotive Diagnostic Skills — Setup  ${RESET}"
echo -e "${BOLD}========================================${RESET}"
echo ""

# ── 1. CHECK OS ────────────────────────────────────────────────────────────────
if grep -qi microsoft /proc/version 2>/dev/null; then
    success "Running in WSL — correct environment"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    success "Running on Linux"
else
    warn "Not running in WSL or Linux. This setup is designed for WSL Ubuntu."
    warn "Install WSL first: https://learn.microsoft.com/en-us/windows/wsl/install"
    warn "Then re-run this script from inside WSL."
    read -rp "Continue anyway? (y/N): " cont
    [[ "$cont" != "y" && "$cont" != "Y" ]] && exit 1
fi

# ── 2. SYSTEM DEPENDENCIES ────────────────────────────────────────────────────
info "Checking system dependencies..."

# Python 3.11+
if ! command -v python3 &>/dev/null; then
    info "Installing Python 3..."
    sudo apt-get update -qq && sudo apt-get install -y python3 python3-pip python3-venv
fi
PY_VER=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
success "Python $PY_VER"

# uv (fast Python package manager)
if ! command -v uv &>/dev/null; then
    info "Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.cargo/bin:$HOME/.local/bin:$PATH"
fi
success "uv $(uv --version 2>/dev/null | head -1)"

# Node.js 18+
if ! command -v node &>/dev/null; then
    info "Installing Node.js 20 LTS..."
    curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
    sudo apt-get install -y nodejs
fi
NODE_VER=$(node --version)
success "Node.js $NODE_VER"

# git
if ! command -v git &>/dev/null; then
    sudo apt-get install -y git
fi
success "git $(git --version | awk '{print $3}')"

# ── 3. CLONE OR UPDATE REPO ───────────────────────────────────────────────────
info "Setting up project repository..."
mkdir -p "$HOME/projects"

if [[ -d "$PROJECT_DIR/.git" ]]; then
    info "Repository already exists — pulling latest..."
    git -C "$PROJECT_DIR" pull --ff-only
    success "Repository updated"
else
    info "Cloning repository..."
    git clone "$REPO_URL" "$PROJECT_DIR"
    success "Repository cloned to $PROJECT_DIR"
fi

cd "$PROJECT_DIR"

# ── 4. PYTHON DEPENDENCIES ────────────────────────────────────────────────────
info "Installing Python dependencies..."
uv sync 2>/dev/null || uv venv .venv && uv pip install -r requirements.txt 2>/dev/null || true

# Fallback: install key packages directly if pyproject.toml/requirements missing
if [[ ! -d ".venv" ]]; then
    uv venv .venv
fi
if ! .venv/bin/python3 -c "import anthropic" 2>/dev/null; then
    uv pip install anthropic fastapi uvicorn chromadb sentence-transformers
fi
success "Python dependencies installed"

# ── 5. NODE DEPENDENCIES ──────────────────────────────────────────────────────
info "Installing Node.js dependencies (frontend)..."
if [[ -d "src/frontend" ]]; then
    cd src/frontend
    npm install --silent
    success "Frontend dependencies installed"
    cd "$PROJECT_DIR"
fi

# ── 6. PLAYWRIGHT CHROMIUM (for PDF generation) ───────────────────────────────
info "Installing Playwright Chromium (needed for /report PDF generation)..."
if [[ -d "src/frontend/node_modules/.bin" ]]; then
    cd src/frontend
    npx playwright install chromium 2>/dev/null && \
        sudo npx playwright install-deps chromium 2>/dev/null || \
        warn "Playwright deps install failed — may need: sudo npx playwright install-deps chromium"
    success "Playwright Chromium installed"
    cd "$PROJECT_DIR"
fi

# ── 7. ANTHROPIC API KEY ──────────────────────────────────────────────────────
info "Configuring Anthropic API key..."
echo ""
echo "  You need an Anthropic API key to use Claude Code."
echo "  Get one at: https://console.anthropic.com"
echo ""

EXISTING_KEY=$(grep -r "ANTHROPIC_API_KEY" ~/.bashrc ~/.zshrc ~/.profile 2>/dev/null | grep -v "^#" | grep "=" | head -1 | cut -d'=' -f2 | tr -d '"' | tr -d "'" | tr -d ' ')
if [[ -n "$EXISTING_KEY" && "$EXISTING_KEY" != "your_key_here" ]]; then
    success "Anthropic API key already configured in shell profile"
else
    read -rp "  Enter your Anthropic API key (sk-ant-...): " API_KEY
    if [[ -n "$API_KEY" ]]; then
        SHELL_RC="$HOME/.bashrc"
        [[ -f "$HOME/.zshrc" ]] && SHELL_RC="$HOME/.zshrc"
        echo "" >> "$SHELL_RC"
        echo "# Anthropic API key (added by automotive-diagnostic-skills setup)" >> "$SHELL_RC"
        echo "export ANTHROPIC_API_KEY=\"$API_KEY\"" >> "$SHELL_RC"
        export ANTHROPIC_API_KEY="$API_KEY"
        success "API key saved to $SHELL_RC"
    else
        warn "No API key entered — set it manually: export ANTHROPIC_API_KEY=sk-ant-..."
    fi
fi

# ── 8. FRONTEND ENV ───────────────────────────────────────────────────────────
if [[ -d "src/frontend" && ! -f "src/frontend/.env.local" ]]; then
    info "Creating frontend environment file..."
    cat > src/frontend/.env.local << 'EOF'
API_KEY=mechanic-secret-key-123
NEXT_PUBLIC_API_URL=http://localhost:8000
EOF
    success "Frontend .env.local created"
fi

# ── 9. REPORTS DIRECTORY ─────────────────────────────────────────────────────
mkdir -p "$PROJECT_DIR/reports"
success "reports/ directory ready"

# ── 10. CLAUDE CODE ───────────────────────────────────────────────────────────
info "Checking Claude Code installation..."
if ! command -v claude &>/dev/null; then
    info "Installing Claude Code..."
    npm install -g @anthropic-ai/claude-code
    success "Claude Code installed"
else
    success "Claude Code $(claude --version 2>/dev/null || echo 'installed')"
fi

# ── 11. DATABASE RESTORE (OPTIONAL) ──────────────────────────────────────────
echo ""
echo -e "${BOLD}── Optional: Restore Databases ────────────────────────────────────────${RESET}"
echo ""
echo "  The diagnostic backend uses a large NHTSA complaints database (839MB)."
echo "  Without it, /diagnose and /report still work — Claude uses built-in knowledge."
echo "  With it, searches pull real NHTSA complaint counts and TSBs for the vehicle."
echo ""
read -rp "  Do you have the databases to restore from a USB or network path? (y/N): " HAS_DB

if [[ "$HAS_DB" == "y" || "$HAS_DB" == "Y" ]]; then
    read -rp "  Path to database files (e.g. /mnt/d or /mnt/usb): " DB_SOURCE
    if [[ -d "$DB_SOURCE" ]]; then
        if [[ -f "$DB_SOURCE/automotive_complaints.db" ]]; then
            info "Copying automotive_complaints.db (839MB — may take a minute)..."
            cp "$DB_SOURCE/automotive_complaints.db" "$PROJECT_DIR/database/"
            success "automotive_complaints.db restored"
        else
            warn "automotive_complaints.db not found at $DB_SOURCE"
        fi
        if [[ -f "$DB_SOURCE/automotive_diagnostics.db" ]]; then
            cp "$DB_SOURCE/automotive_diagnostics.db" "$PROJECT_DIR/database/"
            success "automotive_diagnostics.db restored"
        fi
    else
        warn "Path not found: $DB_SOURCE"
    fi
fi

# ── DONE ──────────────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}========================================${RESET}"
echo -e "${GREEN}${BOLD}  Setup complete!${RESET}"
echo -e "${BOLD}========================================${RESET}"
echo ""
echo "  Project location: $PROJECT_DIR"
echo ""
echo "  To use:"
echo "    cd $PROJECT_DIR"
echo "    claude"
echo ""
echo "  Key commands inside Claude Code:"
echo "    /diagnose  — Start a vehicle diagnostic"
echo "    /report    — Generate a PDF report for the customer"
echo ""
echo "  To start the full web UI (optional):"
echo "    nohup uv run python server/home_server.py > /tmp/backend.log 2>&1 &"
echo "    cd src/frontend && nohup npm run dev > /tmp/frontend.log 2>&1 &"
echo "    Then open: http://localhost:3000"
echo ""
if [[ -n "$EXISTING_KEY" || -n "$API_KEY" ]]; then
    echo -e "${GREEN}  API key is configured. You're ready to go.${RESET}"
else
    echo -e "${YELLOW}  Remember to set your API key:${RESET}"
    echo "    export ANTHROPIC_API_KEY=sk-ant-..."
fi
echo ""
