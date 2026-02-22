@echo off
set "TASK_NAME=AutomotiveRAGServer"
set "SCRIPT_PATH=%~dp0start_server.bat"

echo Creating Auto-Start Task: %TASK_NAME%
echo Script Path: %SCRIPT_PATH%
echo.

:: Check for Admin privileges
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo Requesting Administrative Privileges...
    powershell -Command "Start-Process '%~dpnx0' -Verb RunAs"
    exit /b
)

:: Delete existing task if it exists (to avoid errors)
schtasks /delete /tn "%TASK_NAME%" /f >nul 2>&1

:: Create the new task
:: /sc ONSTART  -> Run when computer turns on
:: /ru SYSTEM   -> Run as SYSTEM (no user login needed)
:: /rl HIGHEST  -> Run with highest privileges
schtasks /create /tn "%TASK_NAME%" /tr "\"%SCRIPT_PATH%\"" /sc ONSTART /ru SYSTEM /rl HIGHEST /f

if %errorLevel% == 0 (
    echo.
    echo SUCCESS! The server will now start automatically when you turn on the computer.
    echo NOTE: Since we moved the files, the old task (if any) is now updated to point to:
    echo %SCRIPT_PATH%
) else (
    echo.
    echo FAILURE. Something went wrong.
)
pause
