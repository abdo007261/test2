#!/bin/bash

# 🚀 Bot Deployment Script
# This script automates the deployment process for all bots

echo "🚀 Starting Bot Deployment Process..."
echo "======================================"

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 is not installed. Please install Python 3.8+ first."
    exit 1
fi

# Check Python version
PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
REQUIRED_VERSION="3.8"

if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then
    echo "❌ Python version $PYTHON_VERSION is too old. Please install Python 3.8+"
    exit 1
fi

echo "✅ Python $PYTHON_VERSION detected"

# Create virtual environment
echo "🔧 Creating virtual environment..."
python3 -m venv botenv

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source botenv/bin/activate

# Upgrade pip
echo "🔧 Upgrading pip..."
pip install --upgrade pip

# Install requirements
echo "📦 Installing dependencies..."
if [ -f "requirements_production.txt" ]; then
    echo "📦 Using production requirements..."
    pip install -r requirements_production.txt
else
    echo "📦 Using full requirements..."
    pip install -r requirements.txt
fi

# Check if installation was successful
if [ $? -eq 0 ]; then
    echo "✅ Dependencies installed successfully!"
else
    echo "❌ Failed to install dependencies"
    exit 1
fi

# Create necessary directories
echo "📁 Creating necessary directories..."
mkdir -p logs
mkdir -p data

# Check environment variables
echo "🔑 Checking environment variables..."
REQUIRED_VARS=("API_ID" "API_HASH" "BOT_TOKEN_MAIN")

for var in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!var}" ]; then
        echo "⚠️  Warning: $var is not set"
    else
        echo "✅ $var is set"
    fi
done

# Create .env file template if it doesn't exist
if [ ! -f ".env" ]; then
    echo "📝 Creating .env template..."
    cat > .env << EOF
# Telegram API Configuration
API_ID=your_api_id_here
API_HASH=your_api_hash_here

# Bot Tokens
BOT_TOKEN_MAIN=your_main_bot_token_here
BOT_TOKEN_55BTC=your_55btc_bot_token_here
BOT_TOKEN_PYROBUDDY=your_pyrobuddy_bot_token_here
BOT_TOKEN_FIVEM_EN=your_fivem_english_bot_token_here
BOT_TOKEN_FIVEM_ID=your_fivem_indonesia_bot_token_here
BOT_TOKEN_FIVEM_VI=your_fivem_vietnam_bot_token_here
BOT_TOKEN_FIVEM_JP=your_fivem_japan_bot_token_here
BOT_TOKEN_SIGNAL=your_signal_bot_token_here
BOT_TOKEN_MEBOT=your_mebot_token_here
BOT_TOKEN_HELLO=your_hellogreeter_bot_token_here

# Optional: Redis Configuration
# REDIS_URL=redis://username:password@host:port

# Optional: External API Keys
# COINVID_API_KEY=your_coinvid_api_key_here
# 55BTC_API_KEY=your_55btc_api_key_here
EOF
    echo "📝 .env template created. Please edit it with your actual values."
fi

# Test launcher
echo "🧪 Testing launcher..."
python3 launch_all_bots.py --config-only

if [ $? -eq 0 ]; then
    echo "✅ Launcher test successful!"
else
    echo "❌ Launcher test failed"
    exit 1
fi

# Create startup script
echo "📝 Creating startup script..."
cat > start_bots.sh << 'EOF'
#!/bin/bash

# 🚀 Bot Startup Script
echo "🚀 Starting all bots..."

# Activate virtual environment
source botenv/bin/activate

# Start bots
python3 launch_all_bots.py

# Keep script running
wait
EOF

chmod +x start_bots.sh

# Create stop script
echo "📝 Creating stop script..."
cat > stop_bots.sh << 'EOF'
#!/bin/bash

# 🛑 Bot Stop Script
echo "🛑 Stopping all bots..."

# Find and kill bot processes
pkill -f "python3 launch_all_bots.py"
pkill -f "python3.*bot.py"

echo "✅ All bots stopped"
EOF

chmod +x stop_bots.sh

# Create systemd service file
echo "📝 Creating systemd service file..."
cat > bot-launcher.service << EOF
[Unit]
Description=Telegram Bot Launcher
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$(pwd)
Environment=PATH=$(pwd)/botenv/bin
ExecStart=$(pwd)/botenv/bin/python3 $(pwd)/launch_all_bots.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

echo "📝 Systemd service file created: bot-launcher.service"

# Create monitoring script
echo "📝 Creating monitoring script..."
cat > monitor_bots.sh << 'EOF'
#!/bin/bash

# 📊 Bot Monitoring Script
echo "📊 Bot Status Monitor"
echo "====================="

# Check if bots are running
if pgrep -f "python3 launch_all_bots.py" > /dev/null; then
    echo "✅ Bot launcher is running"
    ps aux | grep "python3 launch_all_bots.py" | grep -v grep
else
    echo "❌ Bot launcher is not running"
fi

# Check individual bot processes
echo ""
echo "🤖 Individual Bot Status:"
for bot in "55btcbot" "pyrobuddy" "fivem" "signal" "mebot"; do
    if pgrep -f "$bot" > /dev/null; then
        echo "✅ $bot is running"
    else
        echo "❌ $bot is not running"
    fi
done

# Check shared data file
if [ -f "new all in one/fivem_shared_data.json" ]; then
    echo "✅ Shared data file exists"
    echo "📁 Size: $(du -h "new all in one/fivem_shared_data.json" | cut -f1)"
else
    echo "❌ Shared data file not found"
fi

# Check logs
if [ -d "logs" ]; then
    echo "✅ Logs directory exists"
    echo "📁 Log files: $(ls -la logs/ | wc -l)"
else
    echo "❌ Logs directory not found"
fi
EOF

chmod +x monitor_bots.sh

echo ""
echo "🎉 Deployment completed successfully!"
echo "======================================"
echo ""
echo "📋 Next Steps:"
echo "1. Edit .env file with your bot tokens and API credentials"
echo "2. Test the launcher: python3 launch_all_bots.py --config-only"
echo "3. Start all bots: ./start_bots.sh"
echo "4. Monitor bots: ./monitor_bots.sh"
echo "5. Stop bots: ./stop_bots.sh"
echo ""
echo "🔧 For systemd service:"
echo "sudo cp bot-launcher.service /etc/systemd/system/"
echo "sudo systemctl enable bot-launcher.service"
echo "sudo systemctl start bot-launcher.service"
echo ""
echo "📚 For more information, see HOSTING_GUIDE.md"
echo ""
echo "🚀 Your bots are ready for hosting!"
