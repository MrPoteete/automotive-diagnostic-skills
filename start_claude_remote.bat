@echo off
TITLE Claude Code - Remote Control Session
CLS

ECHO ============================================================
ECHO   Automotive Diagnostic System - Claude Code Remote Control
ECHO ============================================================
ECHO.
ECHO Starting remote control session...
ECHO Once connected, open the URL or scan the QR code from any device.
ECHO.
ECHO Press Ctrl+C to stop the session.
ECHO.

claude remote-control --name "Automotive Diagnostic"

IF %ERRORLEVEL% NEQ 0 (
    ECHO.
    ECHO [ERROR] Could not start remote control.
    ECHO Make sure you are logged in: claude /login
    ECHO Claude Code v2.1.51+ required: claude --version
    PAUSE
)
