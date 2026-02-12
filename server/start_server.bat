@echo off
TITLE Automotive Diagnostic RAG Server
CD /D "%~dp0"

:: Start the server and log output
:: Using 'python' from PATH.
echo Starting Server...
python home_server.py
IF %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Server crashed with code %ERRORLEVEL%.
    pause
)
