@echo off
TITLE Automotive Diagnostic System Launcher
CD /D "%~dp0"

echo ========================================================
echo   AUTOMOTIVE DIAGNOSTIC SYSTEM - ONE-CLICK LAUNCHER
echo ========================================================

echo.
echo [1/2] Launching RAG Server...
echo (A new window will open. Keep it open!)
start "Automotive RAG Server" cmd /c "start_server.bat"

echo.
echo Waiting 5 seconds for server to initialize...
timeout /t 5 /nobreak >nul

echo.
echo [2/2] Launching Dashboard...
echo (A browser window should appear shortly)
start "Automotive Dashboard" cmd /c "start_dashboard.bat"

echo.
echo ========================================================
echo   SYSTEM ONLINE
echo ========================================================
echo You can close this launcher window now, 
echo but please keep the Server and Dashboard windows open.
echo.
pause
