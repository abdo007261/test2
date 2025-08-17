# Configuration settings for the Telegram bot
import os

# Get credentials from environment variables
API_ID = os.environ.get("TELEGRAM_API_ID")
API_HASH = os.environ.get("TELEGRAM_API_HASH")
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")

# Bot settings
BOT_NAME = "Greeting Bot"