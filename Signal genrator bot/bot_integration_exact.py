# EXACT INTEGRATION CODE FOR YOUR bot.py FILE
# Copy and paste these changes into your bot.py file

# ===========================================
# STEP 1: Add this import at the top (after line 9)
# ===========================================
from trading_bot_receiver import TradingBotReceiver

# ===========================================
# STEP 2: Add this after line 12 (after app = Client(...))
# ===========================================
receiver = TradingBotReceiver(app)

# ===========================================
# STEP 3: Add this function anywhere in your bot.py file
# ===========================================
async def start_signal_receiver():
    """Start the signal receiver to monitor for signals from signal bot"""
    try:
        print("[BOT] Starting signal receiver...")
        await receiver.start_monitoring()
    except Exception as e:
        print(f"[BOT] Error in signal receiver: {e}")

# ===========================================
# STEP 4: Replace the last 3 lines of your bot.py file
# ===========================================
# REPLACE THIS:
# if __name__ == "__main__":
#     print("Starting Telegram Bot...")
#     app.run()

# WITH THIS:
if __name__ == "__main__":
    print("Starting Telegram Bot...")
    # Start signal receiver
    asyncio.create_task(start_signal_receiver())
    # Start your bot
    app.run()

# ===========================================
# COMPLETE EXAMPLE OF WHAT YOUR FILE SHOULD LOOK LIKE:
# ===========================================

"""
# Your existing imports...
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message
from config import get_text, API_ID, API_HASH, BOT_TOKEN
from database import Database
import re
import asyncio
import aiohttp
import json
from datetime import datetime
import traceback
from pyrogram.types import BotCommand, BotCommandScope, BotCommandScopeAllPrivateChats, MenuButtonDefault, BotCommandScopeChat

# ADD THIS NEW IMPORT:
from trading_bot_receiver import TradingBotReceiver

# Initialize bot and database
app = Client("copytrading_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# ADD THIS NEW LINE:
receiver = TradingBotReceiver(app)

db = Database()
# ... rest of your existing code ...

# ADD THIS NEW FUNCTION (anywhere in your file):
async def start_signal_receiver():
    try:
        print("[BOT] Starting signal receiver...")
        await receiver.start_monitoring()
    except Exception as e:
        print(f"[BOT] Error in signal receiver: {e}")

# ... all your existing functions and handlers ...

# MODIFY THE END OF YOUR FILE:
if __name__ == "__main__":
    print("Starting Telegram Bot...")
    # Start signal receiver
    asyncio.create_task(start_signal_receiver())
    # Start your bot
    app.run()
""" 