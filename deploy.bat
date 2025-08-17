@echo off
title Bot Deployment Script - Windows
color 0A

echo.
echo ========================================
echo    Bot Deployment Script - Windows
echo ========================================
echo.

echo 🚀 Starting Bot Deployment Process...
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python is not installed. Please install Python 3.8+ first.
    echo Download from: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo ✅ Python detected
python --version

REM Check Python version
for /f "tokens=2" %%i in ('python -c "import sys; print(sys.version_info[0:2])" 2^>nul') do set PYTHON_VERSION=%%i
echo ✅ Python version: %PYTHON_VERSION%

REM Create virtual environment
echo.
echo 🔧 Creating virtual environment...
python -m venv botenv
if errorlevel 1 (
    echo ❌ Failed to create virtual environment
    pause
    exit /b 1
)

REM Activate virtual environment
echo 🔧 Activating virtual environment...
call botenv\Scripts\activate.bat

REM Upgrade pip
echo 🔧 Upgrading pip...
python -m pip install --upgrade pip

REM Install requirements
echo.
echo 📦 Installing dependencies...
if exist "requirements_production.txt" (
    echo 📦 Using production requirements...
    pip install -r requirements_production.txt
) else (
    echo 📦 Using full requirements...
    pip install -r requirements.txt
)

REM Check if installation was successful
if errorlevel 1 (
    echo ❌ Failed to install dependencies
    pause
    exit /b 1
)

echo ✅ Dependencies installed successfully!

REM Create necessary directories
echo.
echo 📁 Creating necessary directories...
if not exist "logs" mkdir logs
if not exist "data" mkdir data

REM Create .env file template if it doesn't exist
if not exist ".env" (
    echo.
    echo 📝 Creating .env template...
    (
        echo # Telegram API Configuration
        echo API_ID=your_api_id_here
        echo API_HASH=your_api_hash_here
        echo.
        echo # Bot Tokens
        echo BOT_TOKEN_MAIN=your_main_bot_token_here
        echo BOT_TOKEN_55BTC=your_55btc_bot_token_here
        echo BOT_TOKEN_PYROBUDDY=your_pyrobuddy_bot_token_here
        echo BOT_TOKEN_FIVEM_EN=your_fivem_english_bot_token_here
        echo BOT_TOKEN_FIVEM_ID=your_fivem_indonesia_bot_token_here
        echo BOT_TOKEN_FIVEM_VI=your_fivem_vietnam_bot_token_here
        echo BOT_TOKEN_FIVEM_JP=your_fivem_japan_bot_token_here
        echo BOT_TOKEN_SIGNAL=your_signal_bot_token_here
        echo BOT_TOKEN_MEBOT=your_mebot_token_here
        echo BOT_TOKEN_HELLO=your_hellogreeter_bot_token_here
        echo.
        echo # Optional: Redis Configuration
        echo # REDIS_URL=redis://username:password@host:port
        echo.
        echo # Optional: External API Keys
        echo # COINVID_API_KEY=your_coinvid_api_key_here
        echo # 55BTC_API_KEY=your_55btc_api_key_here
    ) > .env
    echo 📝 .env template created. Please edit it with your actual values.
)

REM Test launcher
echo.
echo 🧪 Testing launcher...
python launch_all_bots.py --config-only

if errorlevel 1 (
    echo ❌ Launcher test failed
    pause
    exit /b 1
)

echo ✅ Launcher test successful!

REM Create startup script
echo.
echo 📝 Creating startup script...
(
    echo @echo off
    echo title Bot Launcher
    echo color 0A
    echo.
    echo 🚀 Starting all bots...
    echo.
    echo Activating virtual environment...
    call botenv\Scripts\activate.bat
    echo.
    echo Starting bot launcher...
    python launch_all_bots.py
    echo.
    echo Bots stopped. Press any key to exit...
    pause
) > start_bots.bat

REM Create stop script
echo 📝 Creating stop script...
(
    echo @echo off
    echo title Bot Stopper
    echo color 0C
    echo.
    echo 🛑 Stopping all bots...
    echo.
    echo Finding and stopping bot processes...
    taskkill /f /im python.exe 2^>nul
    echo.
    echo ✅ All bots stopped
    echo.
    pause
) > stop_bots.bat

REM Create monitoring script
echo 📝 Creating monitoring script...
(
    echo @echo off
    echo title Bot Monitor
    echo color 0B
    echo.
    echo 📊 Bot Status Monitor
    echo =====================
    echo.
    echo Checking bot processes...
    echo.
    tasklist /fi "imagename eq python.exe" /fo table
    echo.
    echo Checking shared data file...
    if exist "new all in one\fivem_shared_data.json" (
        echo ✅ Shared data file exists
        dir "new all in one\fivem_shared_data.json"
    ) else (
        echo ❌ Shared data file not found
    )
    echo.
    echo Checking logs directory...
    if exist "logs" (
        echo ✅ Logs directory exists
        dir logs
    ) else (
        echo ❌ Logs directory not found
    )
    echo.
    pause
) > monitor_bots.bat

echo.
echo 🎉 Deployment completed successfully!
echo ========================================
echo.
echo 📋 Next Steps:
echo 1. Edit .env file with your bot tokens and API credentials
echo 2. Test the launcher: python launch_all_bots.py --config-only
echo 3. Start all bots: start_bots.bat
echo 4. Monitor bots: monitor_bots.bat
echo 5. Stop bots: stop_bots.bat
echo.
echo 📚 For more information, see HOSTING_GUIDE.md
echo.
echo 🚀 Your bots are ready for hosting!
echo.
pause
