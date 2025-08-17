# 🤖 Copy Trading Telegram Bot

A comprehensive Telegram bot that combines user management, admin controls, and automated copy trading functionality for Red/Green trading on Coinvid platform.

## 🚀 Features

### 🔐 **Enhanced Login System**
- **Username Activation**: Only admin-activated usernames can login
- **Coinvid Integration**: Automatic login to Coinvid API with blade_auth token
- **Session Management**: 3-day session persistence with secure credential storage

### 🏠 **Smart Home Panel**
- **User Info Display**: Shows username, real-time balance, selected group
- **Trading Status**: Visual indicators for active/stopped trading
- **Group Selection**: Easy group management for signal sources

### 📡 **Signal Processing**
- **Command Recognition**: Automatically detects `/red_green` commands in groups
- **Signal Parsing**: Processes signals like "Gx1", "Rx2", "Gx3", etc.
- **Martingale Strategy**: Implements phase-based betting (1x, 2x, 4x, 8x, etc.)

### 🎯 **Trading Execution**
- **Real-time Orders**: Places bets on Coinvid platform automatically
- **Balance Updates**: Real-time balance monitoring
- **Trade Notifications**: Instant feedback on trade success/failure
- **Error Handling**: Robust error management and retry logic

### 👥 **Admin Features**
- **User Management**: Add/remove users with auto-generated passwords
- **Group Management**: Add/edit/remove groups with descriptions
- **Admin Controls**: Add/remove admins, view online users
- **Multi-language Support**: English and Vietnamese

## 📋 Installation

### 1. **Install Dependencies**
```bash
pip install pyrogram tgcrypto aiohttp
```

### 2. **Configure Bot**
Edit `config.py` with your Telegram bot credentials:
```python
API_ID = "your_api_id"
API_HASH = "your_api_hash"
BOT_TOKEN = "your_bot_token"
```

### 3. **Run the Bot**
```bash
python bot.py
```

## 🎮 Usage Guide

### **For Users**

#### 1. **Login Process**
```
1. Start bot with /start
2. Click "Login"
3. Send your username (must be activated by admin)
4. Send your Coinvid password
5. ✅ Login successful!
```

#### 2. **Select Signal Group**
```
1. Click "Groups" in home panel
2. Choose your signal source group
3. Click "Select" to confirm
4. ✅ Group selected!
```

#### 3. **Start Trading**
```
1. Ensure you have selected a group
2. Click "Start" in home panel
3. ✅ Trading active! Ready for signals
```

#### 4. **Receive Signals**
The bot automatically:
- Monitors selected groups for `/red_green` commands
- Processes signals like "Gx1", "Rx2", "Gx3"
- Executes trades with martingale strategy
- Sends trade notifications

### **For Admins**

#### 1. **Add Users**
```
1. Use /admin_account command
2. Click "Add Username"
3. Send username to add
4. ✅ User added with auto-generated password
```

#### 2. **Add Groups**
```
1. In target group, send: /add_group_chat
2. ✅ Group added to bot's monitoring list
```

#### 3. **Manage Groups**
```
1. Admin panel → Group List
2. Select group to edit
3. Click "Edit" → "Edit Description"
4. Send new description
5. ✅ Group updated!
```

## 📊 Signal Format

### **Signal Commands**
- `/red_green` - Start signal reception in group
- `Gx1` - Green bet, phase 1 ($1)
- `Rx2` - Red bet, phase 2 ($2)
- `Gx3` - Green bet, phase 3 ($4)
- `Rx4` - Red bet, phase 4 ($8)

### **Martingale Strategy**
```
Phase 1: $1
Phase 2: $2
Phase 3: $4
Phase 4: $8
Phase 5: $16
...and so on
```

## 🔧 Technical Details

### **API Integration**
- **Coinvid Login**: Secure authentication with blade_auth tokens
- **Game Info**: Real-time balance and issue tracking
- **Order Placement**: Automated bet placement with proper headers
- **Result Checking**: Automatic result verification

### **Database Structure**
```json
{
  "users": {
    "username": {
      "user_id": 12345,
      "password": "hashed_password",
      "created_at": "2024-01-01T00:00:00",
      "is_admin": false
    }
  },
  "coinvid_credentials": {
    "user_id": {
      "username": "coinvid_user",
      "password": "coinvid_pass",
      "blade_auth": "token_here",
      "saved_at": "2024-01-01T00:00:00"
    }
  },
  "user_selected_groups": {
    "user_id": "group_name"
  },
  "user_trading_status": {
    "user_id": true
  }
}
```

### **Signal Processing Flow**
1. **Command Detection**: Monitor groups for `/red_green`
2. **Signal Parsing**: Regex match for `[GR]x\d+` format
3. **User Filtering**: Find users listening to this group
4. **Trade Execution**: Place bets with martingale strategy
5. **Notification**: Send results to users

## 🛡️ Security Features

- **Admin-only Access**: Critical functions require admin privileges
- **Session Management**: Secure session handling with expiration
- **Credential Encryption**: Safe storage of Coinvid credentials
- **Error Handling**: Graceful error management and recovery

## 🌐 Multi-language Support

### **Supported Languages**
- 🇺🇸 English
- 🇻🇳 Vietnamese

### **Language Switching**
```
1. Click "Language" in main menu
2. Select preferred language
3. ✅ Language changed!
```

## 🧪 Testing

Run the test script to verify functionality:
```bash
python test_bot.py
```

## 📝 File Structure

```
├── bot.py              # Main bot file with all functionality
├── config.py           # Configuration and language dictionaries
├── database.py         # Database management and storage
├── test_bot.py         # Testing script
└── README.md           # This file
```

## 🚨 Important Notes

1. **Admin Setup**: First user should be added as admin manually
2. **Group Monitoring**: Only groups added via `/add_group_chat` are monitored
3. **Signal Format**: Signals must follow exact format (Gx1, Rx2, etc.)
4. **Trading Risk**: Martingale strategy can be risky - use responsibly
5. **API Limits**: Respect Coinvid API rate limits

## 🔄 Updates & Maintenance

- **Session Cleanup**: Automatic cleanup of expired sessions
- **Token Refresh**: Automatic blade_auth token refresh
- **Error Recovery**: Automatic retry on API failures
- **Balance Monitoring**: Real-time balance updates

## 📞 Support

For issues or questions:
1. Check the test script output
2. Verify all credentials are correct
3. Ensure groups are properly added
4. Check user activation status

---

**🎯 Ready to start copy trading!** 🚀 