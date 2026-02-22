@echo off
echo [CYBERPUNK UI] Initializing System...
cd /d "%~dp0"
if not exist node_modules (
    echo [INSTALL] Installing dependencies...
    call npm install
)
echo [LAUNCH] Starting Development Server...
start http://localhost:3000
npm run dev
