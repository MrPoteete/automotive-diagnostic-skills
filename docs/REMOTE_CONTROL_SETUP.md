# Remote Control Setup

This guide covers two types of remote access for the Automotive Diagnostic System:

1. **Claude Code Remote Control** — access your Claude Code session from any device (phone/browser)
2. **Diagnostic Server Remote Access** — access the FastAPI diagnostic server over Tailscale

---

## Part 1: Claude Code Remote Control

Claude Code Remote Control lets you continue your local session from a phone, tablet, or another browser tab without moving anything to the cloud.

### Requirements

- Claude Code v2.1.51 or later (`claude --version`)
- A Pro, Max, Team, or Enterprise Claude subscription
- Logged in (`claude /login`)

### Start Remote Control

**Windows (from project root):**
```bat
start_claude_remote.bat
```

**Linux / Mac (from project root):**
```bash
./start_claude_remote.sh
```

**Or manually:**
```bash
claude remote-control --name "Automotive Diagnostic"
```

### Connect from Another Device

After starting, Claude Code prints a URL and QR code:

- **Browser**: open the URL shown in the terminal (claude.ai/code)
- **Mobile**: scan the QR code with the Claude mobile app (press `Space` to toggle display)
- **Session list**: open claude.ai/code and find the session by name

### Enable for All Sessions Automatically

Inside any Claude Code session:
```
/config
```
Set **"Enable Remote Control for all sessions"** to `true`.

---

## Part 2: Diagnostic Server Remote Access (Tailscale)

The FastAPI server at port 8000 binds to `0.0.0.0` so it's reachable over Tailscale.

### Step 1 — Install Tailscale

- **Windows**: download from https://tailscale.com/download and run the installer
- **Linux**: `curl -fsSL https://tailscale.com/install.sh | sh`

### Step 2 — Authenticate

```bash
tailscale up
```

Find your Tailscale IP:
```bash
tailscale ip -4
# e.g. 100.64.1.23
```

### Step 3 — Configure the Server

In your `.env` file at the project root, add:
```
# Tailscale remote access
REMOTE_ORIGIN=http://100.64.1.23:3000
API_KEY=your-secure-key-here
```

For multiple remote origins, comma-separate them:
```
REMOTE_ORIGIN=http://100.64.1.23:3000,http://100.64.1.24:3000
```

### Step 4 — Configure the Frontend

In `src/frontend/.env.local`, set the backend URL to your Tailscale IP:
```
API_KEY=your-secure-key-here
BACKEND_URL=http://100.64.1.23:8000
NEXT_PUBLIC_BACKEND_URL=http://100.64.1.23:8000
```

### Step 5 — Start the System

```bash
# Terminal 1 — backend
cd server && python home_server.py

# Terminal 2 — frontend
cd src/frontend && npm run dev
```

Then open `http://100.64.1.23:3000` from any device on your Tailscale network.

---

## Troubleshooting

### "SYSTEM OFFLINE" in the UI

The frontend cannot reach the backend. Check:
1. `server/home_server.py` is running
2. `BACKEND_URL` in `src/frontend/.env.local` matches your Tailscale IP
3. Tailscale is connected on both devices (`tailscale status`)

### CORS errors in browser console

Your remote device's origin is not in the allowed list. Add it to `REMOTE_ORIGIN` in `.env` and restart the server.

### Tailscale not connecting

```bash
tailscale status          # check peers
tailscale ping 100.x.x.x  # test reachability
```

---

## Security Notes

- The API key (`X-API-KEY` header) is required for all diagnostic endpoints
- CORS only permits origins explicitly listed in `ALLOWED_ORIGINS` (no wildcards)
- Tailscale encrypts all traffic between devices — no inbound ports are opened
- Never expose port 8000 directly to the public internet; use Tailscale
