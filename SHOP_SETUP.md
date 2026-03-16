# Setting Up on a New Computer

## What You Need

| Item | Where to get it |
|---|---|
| Anthropic API key | https://console.anthropic.com (same account as home) |
| USB drive (optional) | For transferring the NHTSA complaints database (839MB) |
| Internet connection | To download everything else |

---

## Step 1 — Install WSL (Windows only)

Open **PowerShell as Administrator** and run:
```
wsl --install
```
Restart when prompted. WSL installs Ubuntu automatically.

After restart, open **Ubuntu** from the Start menu. Create a username and password when asked.

---

## Step 2 — Run the Setup Script

Inside Ubuntu (WSL), run these two commands:

```bash
curl -fsSL https://raw.githubusercontent.com/MrPoteete/automotive-diagnostic-skills/main/setup.sh -o setup.sh
bash setup.sh
```

The script will:
- Install Python, Node.js, and other tools automatically
- Clone the project from GitHub
- Install all dependencies
- Ask for your Anthropic API key
- Ask if you want to restore databases from USB (optional)

**Total time:** ~5–10 minutes on a fast connection (longer if copying the database)

---

## Step 3 — Transfer the NHTSA Database (Optional but recommended)

The NHTSA complaints database (839MB) powers the complaint counts and TSB lookups in the web dashboard. Without it, `/diagnose` and `/report` still work fully — Claude just won't pull live NHTSA data.

**To transfer it:**

On your home computer, copy these files to a USB drive:
```
database/automotive_complaints.db    (839MB)
database/automotive_diagnostics.db  (1MB)
```

Plug the USB into the shop computer. In WSL, USB drives appear at `/mnt/d`, `/mnt/e`, etc. (check which letter in File Explorer).

When the setup script asks *"Do you have the databases to restore?"*, say **y** and enter the path to your USB drive (e.g. `/mnt/e`).

---

## Step 4 — Verify It Works

```bash
cd ~/projects/automotive-diagnostic-skills
claude
```

Then type `/diagnose` to test. If it loads the diagnostic framework, you're good.

---

## What's Installed vs. What's Not

| Feature | Available | Notes |
|---|---|---|
| `/diagnose` | ✅ Always | Works on built-in knowledge |
| `/report` PDF | ✅ Always | Needs Node.js (installed by script) |
| NHTSA complaint data | ✅ With USB transfer | Adds complaint counts to diagnoses |
| Web dashboard (localhost:3000) | ✅ With databases | Run servers manually |
| Forum search (ChromaDB) | ❌ Not transferred | 8.1GB — rebuild takes ~2 hrs if needed |

---

## Daily Use

```bash
# Open terminal (Ubuntu/WSL)
cd ~/projects/automotive-diagnostic-skills
claude
```

Then use `/diagnose` or `/report` as normal.

---

## Keeping Both Computers in Sync

The skill files, commands, and scripts are all on GitHub. To pull updates on any machine:

```bash
cd ~/projects/automotive-diagnostic-skills
git pull
```

The databases stay local on each machine — they don't sync through git (too large). If you update the NHTSA data at home, copy the `.db` files to the shop via USB again.

---

## Troubleshooting

**"claude: command not found"**
```bash
npm install -g @anthropic-ai/claude-code
```

**"API key not set"**
```bash
export ANTHROPIC_API_KEY=sk-ant-your-key-here
echo 'export ANTHROPIC_API_KEY=sk-ant-your-key-here' >> ~/.bashrc
```

**PDF generation fails**
```bash
cd ~/projects/automotive-diagnostic-skills/src/frontend
npx playwright install chromium
sudo npx playwright install-deps chromium
```

**Backend won't start (missing database)**
The backend requires `database/automotive_complaints.db`. Either transfer it from your home machine or run without the backend — `/diagnose` and `/report` work without it.
