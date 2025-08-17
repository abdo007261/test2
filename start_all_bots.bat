@echo off
title Bot Launcher - Starting All Bots
echo ========================================
echo    Bot Launcher - Starting All Bots
echo ========================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python and try again
    pause
    exit /b 1
)

echo Python found. Starting bot launcher...
echo.

REM Run the launcher
python launch_all_bots.py

echo.
echo Bot launcher has finished.
pause
