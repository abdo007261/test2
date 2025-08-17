# 🚀 Complete Hosting Guide for All Bots

## 📋 **Overview**

This guide covers hosting all bots in your workspace on various platforms. The `requirements.txt` file contains all necessary dependencies for hosting.

## 🔧 **Requirements File**

### **Main Requirements File**
- **`requirements.txt`** - Comprehensive file with comments and explanations
- **`requirements_production.txt`** - Clean version for production deployment

### **Key Dependencies**
```txt
# Core Bot Frameworks
pyrogram>=2.0.106      # Main bot framework
telethon>=1.34.0       # Alternative bot framework  
aiogram>=3.4.1         # Modern async framework

# Essential Libraries
tgcrypto>=1.2.5        # Crypto for Pyrogram
requests>=2.32.3       # HTTP requests
aiohttp>=3.9.1         # Async HTTP client
redis>=5.0.1           # Data sharing between bots
APScheduler>=3.10.4    # Task scheduling
```

## 🌐 **Hosting Platforms**

### **1. Railway (Recommended)**
```bash
# Railway automatically detects requirements.txt
# Just push your code to GitHub and connect to Railway
```

**Steps:**
1. Push code to GitHub
2. Connect Railway to your repository
3. Railway auto-detects `requirements.txt`
4. Set environment variables for bot tokens
5. Deploy automatically

**Environment Variables Needed:**
```bash
# Bot Tokens
BOT_TOKEN_55BTC=your_55btc_bot_token
BOT_TOKEN_PYROBUDDY=your_pyrobuddy_bot_token
BOT_TOKEN_FIVEM_EN=your_fivem_english_bot_token
BOT_TOKEN_FIVEM_ID=your_fivem_indonesia_bot_token
BOT_TOKEN_FIVEM_VI=your_fivem_vietnam_bot_token
BOT_TOKEN_FIVEM_JP=your_fivem_japan_bot_token

# API Credentials
API_ID=your_telegram_api_id
API_HASH=your_telegram_api_hash

# Redis (if using)
REDIS_URL=your_redis_connection_string
```

### **2. Heroku**
```bash
# Create Procfile
echo "worker: python launch_all_bots.py" > Procfile

# Deploy
git add .
git commit -m "Deploy bots"
git push heroku main
```

### **3. DigitalOcean App Platform**
- Upload your code
- Select Python runtime
- App Platform auto-detects requirements.txt
- Set environment variables

### **4. VPS/Server Hosting**
```bash
# 1. Install Python 3.8+
sudo apt update
sudo apt install python3.9 python3.9-venv python3.9-pip

# 2. Create virtual environment
python3.9 -m venv botenv
source botenv/bin/activate

# 3. Install requirements
pip install -r requirements.txt

# 4. Run bots
python launch_all_bots.py
```

## 📁 **File Structure for Hosting**

```
hosted-bots2/
├── requirements.txt              # Main requirements file
├── requirements_production.txt   # Production requirements
├── launch_all_bots.py           # Main launcher
├── launcher_config.json         # Bot configuration
├── 55BTC/
│   ├── 55btcbot.py
│   └── config.py
├── PyroBuddy/
│   ├── bot.py
│   └── config.py
├── new all in one/
│   ├── fivem_r_g_en_bot.py
│   ├── fivem_r_g_indonisia_bot.py
│   ├── fivem_r_g_vitname_bot.py
│   ├── fivem_r_g_Jabanise_bot.py
│   └── other_bots.py
├── Signal genrator bot/
│   ├── signal_auto_bot_pyrogram.py
│   ├── bot.py
│   └── other_files.py
├── mebot/
│   ├── me_bot.py
│   └── bot.py
└── HelloGreeter/
    ├── bot.py
    └── bot_telthon.py
```

## 🔑 **Environment Variables Setup**

### **Required for All Bots**
```bash
# Telegram API
API_ID=your_api_id
API_HASH=your_api_hash

# Bot Tokens (one for each bot)
BOT_TOKEN_MAIN=your_main_bot_token
BOT_TOKEN_55BTC=your_55btc_bot_token
BOT_TOKEN_PYROBUDDY=your_pyrobuddy_bot_token
BOT_TOKEN_FIVEM_EN=your_fivem_english_bot_token
BOT_TOKEN_FIVEM_ID=your_fivem_indonesia_bot_token
BOT_TOKEN_FIVEM_VI=your_fivem_vietnam_bot_token
BOT_TOKEN_FIVEM_JP=your_fivem_japan_bot_token
BOT_TOKEN_SIGNAL=your_signal_bot_token
BOT_TOKEN_MEBOT=your_mebot_token
BOT_TOKEN_HELLO=your_hellogreeter_bot_token
```

### **Optional (for specific features)**
```bash
# Redis (for data sharing)
REDIS_URL=redis://username:password@host:port

# Database URLs
DATABASE_URL=your_database_url

# API Keys for external services
COINVID_API_KEY=your_coinvid_api_key
55BTC_API_KEY=your_55btc_api_key
```

## 🚀 **Deployment Steps**

### **Step 1: Prepare Your Code**
```bash
# 1. Ensure requirements.txt is in root directory
# 2. Check all bot files have correct imports
# 3. Verify environment variable usage in config files
```

### **Step 2: Choose Hosting Platform**
- **Railway**: Easiest, auto-detects requirements
- **Heroku**: Good free tier, manual setup
- **VPS**: Full control, manual setup
- **DigitalOcean**: Good balance, auto-detection

### **Step 3: Deploy**
```bash
# For Railway/Heroku/DigitalOcean
git add .
git commit -m "Deploy bots"
git push origin main

# For VPS
scp -r hosted-bots2/ user@your-server:/home/user/
ssh user@your-server
cd hosted-bots2
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python launch_all_bots.py
```

### **Step 4: Monitor and Maintain**
```bash
# Check bot status
ps aux | grep python

# View logs
tail -f bot_logs.log

# Restart if needed
pkill -f "python launch_all_bots.py"
python launch_all_bots.py
```

## 📊 **Bot Categories and Dependencies**

### **Pyrogram Bots (55BTC, PyroBuddy, Signal, Mebot)**
- **Dependencies**: `pyrogram`, `tgcrypto`, `requests`
- **Features**: Trading signals, API integration
- **Data**: JSON files, SQLite databases

### **Aiogram Bots (FiveM Red/Green, Game Bots)**
- **Dependencies**: `aiogram`, `redis`, `requests`
- **Features**: Real-time gaming, data sharing
- **Data**: Redis + local file fallback

### **Telethon Bots (HelloGreeter)**
- **Dependencies**: `telethon`, `apscheduler`, `pytz`
- **Features**: Scheduling, timezone handling
- **Data**: JSON configuration files

### **GUI Bots (Signal Generator Main)**
- **Dependencies**: `flet`, `aiohttp`
- **Features**: Desktop interface, web integration
- **Data**: Multiple data sources

## 🛠 **Troubleshooting**

### **Common Issues**

#### **1. Import Errors**
```bash
# Solution: Install missing packages
pip install -r requirements.txt

# Check Python version (needs 3.8+)
python --version
```

#### **2. Bot Token Issues**
```bash
# Verify environment variables are set
echo $BOT_TOKEN_MAIN

# Check config files use correct variable names
```

#### **3. Redis Connection Issues**
```bash
# FiveM bots will fall back to local file system
# Check fivem_shared_data.json is being created
```

#### **4. Memory Issues**
```bash
# Monitor memory usage
htop

# Restart bots if memory usage is high
```

### **Performance Optimization**
```bash
# Use virtual environment
python -m venv venv
source venv/bin/activate

# Install only production requirements
pip install -r requirements_production.txt

# Monitor resource usage
top
htop
```

## 📈 **Scaling Considerations**

### **For Multiple Bots**
- Use separate processes (already implemented in launcher)
- Monitor memory usage per bot
- Consider using supervisor or systemd for process management

### **For High Traffic**
- Implement rate limiting
- Use Redis for caching
- Consider load balancing for multiple instances

### **For Production**
- Use proper logging
- Implement health checks
- Set up monitoring and alerting
- Use environment-specific configurations

## 🎯 **Quick Start Commands**

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set environment variables
export BOT_TOKEN_MAIN="your_token"
export API_ID="your_api_id"
export API_HASH="your_api_hash"

# 3. Run all bots
python launch_all_bots.py

# 4. Run specific bots only
python launch_all_bots.py --exclude fivem_en fivem_indonesia

# 5. Debug mode (separate windows)
python launch_all_bots.py --debug-mode
```

## 🎉 **Success Checklist**

- [ ] All dependencies installed from requirements.txt
- [ ] Environment variables set correctly
- [ ] Bot tokens configured
- [ ] Database connections working
- [ ] Bots starting without errors
- [ ] Data sharing between bots working
- [ ] Monitoring and logging set up
- [ ] Backup and recovery procedures in place

Your bots are now ready for hosting! 🚀
