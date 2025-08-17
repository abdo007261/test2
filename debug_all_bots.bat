@echo off
title Bot Launcher - Debug Mode (Separate Windows)
echo ========================================
echo    Bot Launcher - DEBUG MODE
echo    Each bot will open in separate window
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

echo Python found. Starting bot launcher in DEBUG MODE...
echo.
echo 🐛 DEBUG MODE: Each bot will open in its own console window
echo 💡 This allows you to see each bot's output separately for debugging
echo.

REM Run the launcher in debug mode
python launch_all_bots.py --debug-mode

echo.
echo Debug launcher has finished.
pause
