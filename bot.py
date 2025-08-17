from telethon import TelegramClient
import asyncio

api_id = 26866999
api_hash = "0078471b8da9dd7c2b4658f85eebead2"
session_name = "my_session"
bot_username = "@CV_messages_counter_bot"

# نجهز السيشن
client = TelegramClient(session_name, api_id, api_hash)

async def send_to_bot():
    await client.start()
    while True:
        try:
            await client.send_message(bot_username, "/start")
            print("Message sent to the bot!")
        except Exception as e:
            print(f"Error occurred: {e}")
        await asyncio.sleep(200)

if __name__ == "__main__":
    asyncio.run(send_to_bot())
