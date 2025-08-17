@echo off
title FiveM Red/Green Game Bots - Local File System
color 0A

echo.
echo ========================================
echo    FiveM Red/Green Game Bots
echo    Local File System Launcher
echo ========================================
echo.

echo 🚀 Starting all bots with local file system...
echo.

echo 📁 Checking shared data file...
if exist "new all in one\fivem_shared_data.json" (
    echo ✅ Shared data file found
) else (
    echo ⚠️  Shared data file not found
    echo 💡 Will be created when English bot starts
)

echo.
echo 🔄 Starting bots in sequence...
echo.

echo 1️⃣ Starting English Bot (Data Master)...
start "English Bot - Data Master" cmd /k "cd /d "%~dp0new all in one" && python fivem_r_g_en_bot.py"
timeout /t 3 /nobreak >nul

echo 2️⃣ Starting Vietnamese Bot...
start "Vietnamese Bot" cmd /k "cd /d "%~dp0new all in one" && python fivem_r_g_vitname_bot.py"
timeout /t 2 /nobreak >nul

echo 3️⃣ Starting Japanese Bot...
start "Japanese Bot" cmd /k "cd /d "%~dp0new all in one" && python fivem_r_g_Jabanise_bot.py"
timeout /t 2 /nobreak >nul

echo 4️⃣ Starting Indonesian Bot...
start "Indonesian Bot" cmd /k "cd /d "%~dp0new all in one" && python fivem_r_g_indonisia_bot.py"
timeout /t 2 /nobreak >nul

echo.
echo ✅ All bots started successfully!
echo.
echo 📊 Expected Console Output:
echo    [EN] Shared data updated to local file successfully
echo    [VI] Data read from local file successfully
echo    [JP] Data read from local file successfully
echo    [ID] Data read from local file successfully
echo.
echo 🔍 Monitor shared data file:
echo    dir "new all in one\fivem_shared_data.json"
echo.
echo 🧪 Test local file system:
echo    python test_local_file_system.py
echo.
echo ========================================
echo 🎉 Bots are now running with local file system!
echo 💾 No more Redis dependency!
echo ========================================
echo.
pause
