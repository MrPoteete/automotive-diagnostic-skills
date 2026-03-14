#!/usr/bin/env bash
set -euo pipefail

echo "============================================================"
echo "  Automotive Diagnostic System - Claude Code Remote Control"
echo "============================================================"
echo ""
echo "Starting remote control session..."
echo "Once connected, open the URL or scan the QR code from any device."
echo ""
echo "Press Ctrl+C to stop the session."
echo ""

claude remote-control --name "Automotive Diagnostic"
