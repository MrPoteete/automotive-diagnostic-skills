@echo off
TITLE Automotive Diagnostic System - Deployment Setup
CLS

ECHO ========================================================
ECHO    Automotive Diagnostic Assistant - Setup Wizard
ECHO ========================================================
ECHO.

:: 1. Check Python
python --version >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    ECHO [ERROR] Python is not installed or not in PATH.
    ECHO Please install Python 3.10+ and try again.
    PAUSE
    EXIT /B
)
ECHO [OK] Python found.

:: 2. Install Dependencies
ECHO.
ECHO [1/3] Installing Python Dependencies...
pip install -r requirements.txt
IF %ERRORLEVEL% NEQ 0 (
    ECHO [ERROR] Failed to install dependencies.
    PAUSE
    EXIT /B
)

:: 3. Seed Database
ECHO.
ECHO [2/3] Mining Fleet Dataset (2005-2026)
ECHO --------------------------------------------------------
ECHO WARNING: This will take a SIGNIFICANT amount of time.
ECHO It is downloading data for 50+ models across 20 years.
ECHO You can press Ctrl+C to stop it at any time (data is saved).
ECHO --------------------------------------------------------
python data_miner.py --fleet

:: 4. Install Autostart
ECHO.
ECHO [3/3] Configuring Autostart Service...
CALL install_autostart.bat

ECHO.
ECHO ========================================================
ECHO    SETUP COMPLETE!
ECHO ========================================================
ECHO.
ECHO You can now start the dashboard with: start_dashboard.bat
ECHO.
PAUSE
