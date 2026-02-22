@echo off
REM Start Complete Automotive Diagnostic System
REM Launches both backend API and frontend UI

echo ====================================
echo  AUTOMOTIVE DIAGNOSTIC SYSTEM
echo  Full Stack Startup
echo ====================================
echo.

REM Start Backend API Server
echo [1/2] Starting Backend API Server...
cd server
start "Backend API Server" cmd /k "python home_server.py"
timeout /t 3 /nobreak > nul

REM Start Frontend UI
echo [2/2] Starting Frontend UI...
cd ..\src\frontend

REM Check if .env.local exists
if not exist .env.local (
    echo [WARNING] Frontend .env.local not found!
    echo Creating from .env.example...
    copy .env.example .env.local
    echo.
)

start "Frontend UI" cmd /k "npm run dev"

echo.
echo ====================================
echo  SYSTEM STARTED
echo ====================================
echo.
echo Backend API: http://localhost:8000
echo Frontend UI: http://localhost:3000
echo.
echo Two terminal windows have been opened:
echo   1. Backend API Server
echo   2. Frontend UI Server
echo.
echo Close those windows to stop the services.
echo.
pause
