# 🤖 Bot Launcher - Unified Bot Management System

This workspace contains multiple Telegram bots for various purposes. The `launch_all_bots.py` script provides a unified way to start, monitor, and manage all bots simultaneously.

## 📋 Available Bots

### 1. **Root Bot (Message Counter)**
- **File**: `bot.py`
- **Type**: Telethon
- **Purpose**: Message counter bot that sends periodic messages to a target bot
- **Description**: Simple telethon-based bot for message counting

### 2. **PyroBuddy Bot**
- **File**: `PyroBuddy/bot.py`
- **Type**: Pyrogram
- **Purpose**: Trading signal bot with admin management
- **Features**: 
  - Admin management system
  - Channel/group management
  - Trading signals broadcasting
  - Multi-language support

### 3. **55BTC Bot**
- **File**: `55BTC/55btcbot.py`
- **Type**: Pyrogram
- **Purpose**: 55BTC trading bot
- **Features**: Trading signals and cryptocurrency operations

### 4. **Signal Generator Bots** (Multiple Variants)
- **Location**: `Signal genrator bot/`
- **Bots**:
  - **Main GUI Bot** (`main.py`): Flet GUI-based signal generation bot
  - **Pyrogram Bot** (`signal_auto_bot_pyrogram.py`): Advanced Pyrogram-based signal generation
  - **Copy Trading Bot** (`bot.py`): Copy trading functionality with signal processing
  - **Auto Bot** (`signal_auto_bot.py`): Automated signal generation bot

### 5. **HelloGreeter Bot**
- **File**: `HelloGreeter/bot.py`
- **Type**: Pyrogram
- **Purpose**: Scheduler and greeting bot
- **Features**:
  - Task scheduling
  - Automated greetings
  - Chat analytics
  - Activity tracking

### 6. **New All In One Bots** (Multiple Game Bots)
- **Location**: `new all in one/`
- **Type**: Aiogram (mostly)
- **Bots**:
  - **Dices Bot** (`dices.py`): Dice game bot
  - **Number Guessing Bot** (`number_gussing.py`): Number guessing game
  - **Blocks Bot** (`blocks_bot.py`): Blocks game bot
  - **Red Green Bot** (`red_green.py`): Red/Green trading bot
  - **Telethon Guessing Bot** (`telethon_gusing_bot.py`): Telethon-based guessing game
  - **FiveM Multi-language Bot** (`main.py`): Multi-language FiveM red/green bots
  - **FiveM English Bot** (`fivem_r_g_en_bot.py`): English FiveM bot
  - **FiveM Indonesia Bot** (`fivem_r_g_indonisia_bot.py`): Indonesia FiveM bot
  - **FiveM Vietnam Bot** (`fivem_r_g_vitname_bot.py`): Vietnam FiveM bot
  - **FiveM Japan Bot** (`fivem_r_g_Jabanise_bot.py`): Japan FiveM bot

### 7. **Me Bot**
- **Location**: `mebot/`
- **Type**: Pyrogram
- **Bots**:
  - **Main Bot** (`me_bot.py`): Personal bot with custom functionality
  - **Alternative Bot** (`bot.py`): Alternative personal bot implementation

## 🚀 Quick Start

### Method 1: Using the Batch Files (Windows)
```bash
# Normal mode - all bots run in background
start_all_bots.bat

# DEBUG MODE - each bot opens in separate window
debug_all_bots.bat
```

### Method 2: Using Python Directly
```bash
# Start all bots in background (normal mode)
python launch_all_bots.py

# Start all bots in separate windows (DEBUG MODE)
python launch_all_bots.py --debug-mode

# Show configuration only
python launch_all_bots.py --config-only

# List all available bots
python launch_all_bots.py --list

# Exclude specific bots
python launch_all_bots.py --exclude signal_generator_main signal_generator_pyrogram

# Debug mode with exclusions
python launch_all_bots.py --debug-mode --exclude hellogreeter mebot
```

## 🐛 Debug Mode (NEW!)

The launcher now supports a **DEBUG MODE** that opens each bot in its own separate window/console. This is perfect for:

- **Individual debugging** of each bot
- **Monitoring output** from specific bots
- **Development and testing** of individual bot functionality
- **Isolated troubleshooting** without interference

### Debug Mode Features:
- ✅ **Separate Windows**: Each bot runs in its own console window
- ✅ **Individual Control**: Close individual bot windows to stop them
- ✅ **Clear Output**: See each bot's logs and errors separately
- ✅ **Easy Debugging**: Monitor specific bots without scrolling through mixed output
- ✅ **Cross-Platform**: Works on Windows, Linux, and macOS

### When to Use Debug Mode:
- 🔍 **Debugging specific bots**
- 🧪 **Testing individual bot functionality**
- 📊 **Monitoring specific bot performance**
- 🐛 **Troubleshooting errors in particular bots**
- 👨‍💻 **Development and testing phases**

### When to Use Normal Mode:
- 🚀 **Production deployment**
- 📱 **Background operation**
- 🔄 **Automated monitoring and restart**
- 💻 **Server environments**

## 📊 Bot Types and Technologies

| Bot Type | Technology | Description |
|----------|------------|-------------|
| **Telethon** | Telethon Library | Asynchronous Telegram client library |
| **Pyrogram** | Pyrogram Library | Modern Telegram client library |
| **Aiogram** | Aiogram Library | Modern Telegram Bot API framework |
| **Flet GUI** | Flet Framework | Python GUI framework for desktop apps |

## ⚙️ Configuration Options

### Command Line Arguments

- `--config-only`: Show bot configuration without starting
- `--exclude BOT1 BOT2`: Exclude specific bots from starting
- `--list`: List all available bots
- `--debug-mode`: **NEW!** Start each bot in separate window for debugging

### Bot Groups

The launcher supports predefined bot groups for easier management:

- **`trading_bots`**: All trading and signal generation bots
- **`game_bots`**: All game-related bots
- **`fivem_bots`**: All FiveM-related bots
- **`utility_bots`**: Utility and management bots
- **`signal_bots`**: All signal generation variants
- **`all_bots`**: Complete bot collection

### Environment Variables

The launcher automatically sets up the proper Python path for each bot's working directory.

## 🔧 Features

### ✅ Automatic Bot Detection
- Scans the workspace for all available bots
- Validates bot file existence
- Shows availability status
- **Total: 20 bots detected**

### ✅ Process Management
- Each bot runs in its own subprocess
- Isolated execution environments
- Proper working directory setup

### ✅ Monitoring & Recovery
- Continuous monitoring of running bots
- Automatic restart on failure
- Graceful shutdown handling

### ✅ Signal Handling
- Ctrl+C for graceful shutdown
- Proper cleanup of all processes
- Error handling and reporting

### ✅ Debug Mode (NEW!)
- Separate window for each bot
- Individual bot monitoring
- Easy debugging and troubleshooting
- Cross-platform support

## 📁 File Structure

```
workspace/
├── launch_all_bots.py          # Main launcher script
├── start_all_bots.bat          # Windows batch file (normal mode)
├── debug_all_bots.bat          # Windows batch file (debug mode)
├── start_all_bots.ps1          # PowerShell script
├── BOT_LAUNCHER_README.md      # This file
├── launcher_config.json        # Configuration file
├── requirements_launcher.txt    # Dependencies
├── bot.py                      # Root message counter bot
├── PyroBuddy/
│   └── bot.py                  # PyroBuddy trading bot
├── 55BTC/
│   └── 55btcbot.py             # 55BTC trading bot
├── Signal genrator bot/
│   ├── main.py                 # Main GUI signal generator
│   ├── signal_auto_bot_pyrogram.py  # Pyrogram signal bot
│   ├── bot.py                  # Copy trading bot
│   └── signal_auto_bot.py      # Auto signal bot
├── HelloGreeter/
│   └── bot.py                  # Scheduler bot
├── new all in one/
│   ├── dices.py                # Dice game bot
│   ├── number_gussing.py       # Number guessing bot
│   ├── blocks_bot.py           # Blocks game bot
│   ├── red_green.py            # Red/Green trading bot
│   ├── telethon_gusing_bot.py  # Telethon guessing bot
│   ├── main.py                 # FiveM multi-language bots
│   ├── fivem_r_g_en_bot.py     # FiveM English bot
│   ├── fivem_r_g_indonisia_bot.py  # FiveM Indonesia bot
│   ├── fivem_r_g_vitname_bot.py    # FiveM Vietnam bot
│   └── fivem_r_g_Jabanise_bot.py   # FiveM Japan bot
└── mebot/
    ├── me_bot.py               # Main personal bot
    └── bot.py                  # Alternative personal bot
```

## 🛠️ Troubleshooting

### Common Issues

1. **Python not found**
   - Ensure Python is installed and in PATH
   - Try running `python --version` in command prompt

2. **Bot fails to start**
   - Check if all required dependencies are installed
   - Verify bot configuration files exist
   - Check bot-specific error messages

3. **Permission errors**
   - Run as administrator if needed
   - Check file permissions in bot directories

4. **Import errors**
   - Ensure all required packages are installed
   - Check if virtual environments are activated

5. **Debug mode not working on Linux/Mac**
   - Install `xterm` or similar terminal emulator
   - The launcher will fallback to background mode if needed

### Dependencies

Most bots require these common packages:
```bash
pip install pyrogram telethon aiogram flet requests asyncio
```

## 📈 Monitoring

The launcher provides real-time monitoring:
- Process status updates
- Automatic restart on failure
- Exit code reporting
- Error logging

## 🔒 Security Notes

- Each bot runs in isolation
- No shared memory between bots
- Proper environment variable handling
- Secure process termination

## 📞 Support

For issues with specific bots, check their individual directories for:
- Configuration files
- Requirements files
- Bot-specific documentation

## 🎯 Usage Examples

```bash
# Start all bots in background (normal mode)
python launch_all_bots.py

# Start all bots in separate windows (debug mode)
python launch_all_bots.py --debug-mode

# Start only trading bots in debug mode
python launch_all_bots.py --debug-mode --exclude $(python -c "import json; print(' '.join(json.load(open('launcher_config.json'))['bot_groups']['game_bots']))"

# Start only signal bots in debug mode
python launch_all_bots.py --debug-mode --exclude $(python -c "import json; print(' '.join(json.load(open('launcher_config.json'))['bot_groups']['utility_bots']))"

# Check configuration
python launch_all_bots.py --config-only

# Start with specific exclusions in debug mode
python launch_all_bots.py --debug-mode --exclude signal_generator_main signal_generator_pyrogram
```

## 🔄 Updates

The launcher automatically detects new bots added to the workspace. Simply add new bot configurations to the `load_bot_configurations()` method in `launch_all_bots.py`.

## 📊 Bot Statistics

- **Total Bots**: 20
- **Bot Types**: 4 (Telethon, Pyrogram, Aiogram, Flet GUI)
- **Categories**: 6 (Trading, Games, FiveM, Signals, Utility, Personal)
- **Technologies**: Multiple Telegram libraries and frameworks
- **Launch Modes**: 2 (Normal background, Debug separate windows)

---

**Note**: Make sure all bots have their required configuration files (API keys, tokens, etc.) properly set up before running the launcher.
