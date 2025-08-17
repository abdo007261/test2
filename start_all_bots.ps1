# PowerShell Script to Launch All Bots
# Run this script in PowerShell

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "    Bot Launcher - Starting All Bots" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if Python is available
try {
    $pythonVersion = python --version 2>&1
    Write-Host "✅ Python found: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ ERROR: Python is not installed or not in PATH" -ForegroundColor Red
    Write-Host "Please install Python and try again" -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host ""
Write-Host "🚀 Starting bot launcher..." -ForegroundColor Green
Write-Host ""

# Run the launcher
try {
    python launch_all_bots.py
} catch {
    Write-Host "❌ Error running the launcher: $_" -ForegroundColor Red
}

Write-Host ""
Write-Host "Bot launcher has finished." -ForegroundColor Yellow
Read-Host "Press Enter to exit"
