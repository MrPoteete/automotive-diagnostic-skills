@echo off
REM Start Frontend Development Server
REM This script starts the Next.js development server

echo ====================================
echo  AUTOMOTIVE DIAGNOSTIC UI
echo  Cyberpunk Edition
echo ====================================
echo.

REM Check if node_modules exists
if not exist node_modules (
    echo [ERROR] Dependencies not installed!
    echo.
    echo Run: npm install
    echo.
    pause
    exit /b 1
)

REM Check if .env.local exists
if not exist .env.local (
    echo [WARNING] .env.local not found!
    echo.
    echo Creating from .env.example...
    copy .env.example .env.local
    echo.
    echo Please edit .env.local with your settings.
    echo.
)

echo Starting development server...
echo.
echo Backend URL: %NEXT_PUBLIC_API_URL%
echo Frontend: http://localhost:3000
echo.
echo Press Ctrl+C to stop
echo.

npm run dev
