# Bot Integration Code - Add this to your bot.py file

# Add this import at the top of your bot.py file (after other imports)
from trading_bot_receiver import TradingBotReceiver

# Add this after your bot client initialization (after app = Client(...))
receiver = TradingBotReceiver(app)

# Add this function to start the signal receiver
async def start_signal_receiver():
    """Start the signal receiver to monitor for signals from signal bot"""
    try:
        print("[BOT] Starting signal receiver...")
        await receiver.start_monitoring()
    except Exception as e:
        print(f"[BOT] Error in signal receiver: {e}")

# Modify your main function or add this to your bot startup
# If you have a main() function, add this line:
# asyncio.create_task(start_signal_receiver())

# If you're using app.run(), add this before app.run():
# asyncio.create_task(start_signal_receiver())

# Example integration with your existing bot structure:
"""
# Add this to your bot.py file:

# 1. Add import at the top
from trading_bot_receiver import TradingBotReceiver

# 2. Add after your bot client initialization
receiver = TradingBotReceiver(app)

# 3. Add this function
async def start_signal_receiver():
    try:
        print("[BOT] Starting signal receiver...")
        await receiver.start_monitoring()
    except Exception as e:
        print(f"[BOT] Error in signal receiver: {e}")

# 4. Modify your main function or startup code
# If you have a main() function:
async def main():
    # Your existing startup code...
    
    # Start signal receiver
    asyncio.create_task(start_signal_receiver())
    
    # Start your bot
    await app.start()
    await app.idle()

# Or if you're using app.run():
if __name__ == "__main__":
    # Start signal receiver
    asyncio.create_task(start_signal_receiver())
    
    # Start your bot
    app.run()
""" 