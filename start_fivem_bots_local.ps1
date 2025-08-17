# FiveM Red/Green Game Bots - Local File System Launcher
# PowerShell Version

Write-Host "========================================" -ForegroundColor Green
Write-Host "   FiveM Red/Green Game Bots" -ForegroundColor Green
Write-Host "   Local File System Launcher" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""

Write-Host "🚀 Starting all bots with local file system..." -ForegroundColor Yellow
Write-Host ""

# Check shared data file
Write-Host "📁 Checking shared data file..." -ForegroundColor Cyan
if (Test-Path "new all in one\fivem_shared_data.json") {
    Write-Host "✅ Shared data file found" -ForegroundColor Green
} else {
    Write-Host "⚠️  Shared data file not found" -ForegroundColor Yellow
    Write-Host "💡 Will be created when English bot starts" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "🔄 Starting bots in sequence..." -ForegroundColor Cyan
Write-Host ""

# Get current directory
$currentDir = Get-Location

# Start English Bot (Data Master)
Write-Host "1️⃣ Starting English Bot (Data Master)..." -ForegroundColor Green
Start-Process -FilePath "cmd" -ArgumentList "/k", "cd /d `"$currentDir\new all in one`" && python fivem_r_g_en_bot.py" -WindowStyle Normal -Title "English Bot - Data Master"
Start-Sleep -Seconds 3

# Start Vietnamese Bot
Write-Host "2️⃣ Starting Vietnamese Bot..." -ForegroundColor Green
Start-Process -FilePath "cmd" -ArgumentList "/k", "cd /d `"$currentDir\new all in one`" && python fivem_r_g_vitname_bot.py" -WindowStyle Normal -Title "Vietnamese Bot"
Start-Sleep -Seconds 2

# Start Japanese Bot
Write-Host "3️⃣ Starting Japanese Bot..." -ForegroundColor Green
Start-Process -FilePath "cmd" -ArgumentList "/k", "cd /d `"$currentDir\new all in one`" && python fivem_r_g_Jabanise_bot.py" -WindowStyle Normal -Title "Japanese Bot"
Start-Sleep -Seconds 2

# Start Indonesian Bot
Write-Host "4️⃣ Starting Indonesian Bot..." -ForegroundColor Green
Start-Process -FilePath "cmd" -ArgumentList "/k", "cd /d `"$currentDir\new all in one`" && python fivem_r_g_indonisia_bot.py" -WindowStyle Normal -Title "Indonesian Bot"
Start-Sleep -Seconds 2

Write-Host ""
Write-Host "✅ All bots started successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "📊 Expected Console Output:" -ForegroundColor Cyan
Write-Host "   [EN] Shared data updated to local file successfully" -ForegroundColor White
Write-Host "   [VI] Data read from local file successfully" -ForegroundColor White
Write-Host "   [JP] Data read from local file successfully" -ForegroundColor White
Write-Host "   [ID] Data read from local file successfully" -ForegroundColor White
Write-Host ""
Write-Host "🔍 Monitor shared data file:" -ForegroundColor Cyan
Write-Host "   Get-ChildItem 'new all in one\fivem_shared_data.json'" -ForegroundColor White
Write-Host ""
Write-Host "🧪 Test local file system:" -ForegroundColor Cyan
Write-Host "   python test_local_file_system.py" -ForegroundColor White
Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "🎉 Bots are now running with local file system!" -ForegroundColor Green
Write-Host "💾 No more Redis dependency!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""

Read-Host "Press Enter to continue..."
