@echo off
TITLE Automotive Diagnostic RAG Server
CD /D "%~dp0"

:: Start the server and log output
:: Using absolute path to ensure it runs as SYSTEM
echo Starting Server...
set PYTHON_EXE=C:\Users\potee\AppData\Local\Programs\Python\Python310\python.exe

"%PYTHON_EXE%" home_server.py >> server_startup.log 2>&1

IF %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Server crashed with code %ERRORLEVEL%.
    echo Check server_startup.log for details.
    pause
)
