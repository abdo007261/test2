from pyrogram import Client, filters
import json
import os

# Replace these with your actual values
api_id = 27112006  # Replace with your own if needed
api_hash = "0d1019d7ca92aef12571c82cd163d2bd"
bot_token = "7581385517:AAEwBMBhAl_65ZF378Z371vXSBio-h52nGI"

# File to store sticker IDs
STICKERS_FILE = "number_stickers.json"

def load_stickers():
    if os.path.exists(STICKERS_FILE):
        with open(STICKERS_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_stickers(stickers):
    with open(STICKERS_FILE, 'w') as f:
        json.dump(stickers, f, indent=4)

app = Client("simple_bot", api_id=api_id, api_hash=api_hash, bot_token=bot_token)

@app.on_message(filters.all)
def handle_message(client, message):
    print("📩 New Message Received:")
    print(f"From: {message.from_user.first_name} (ID: {message.from_user.id})")
    print(f"Chat ID: {message.chat.id}")
    
    # Check if the message contains a sticker
    if message.sticker:
        print("🎯 Sticker Details:")
        print(f"Sticker ID: {message.sticker.file_id}")
        print(f"Sticker Set: {message.sticker.set_name}")
        print(f"Emoji: {message.sticker.emoji}")
        
        # Load existing stickers
        stickers = load_stickers()
        
        # Get the next number (if no stickers exist, start with 1)
        next_number = len(stickers) + 1
        
        # Save the new sticker
        stickers[str(next_number)] = {
            "file_id": message.sticker.file_id,
            "emoji": message.sticker.emoji,
            "set_name": message.sticker.set_name
        }
        
        # Save to file
        save_stickers(stickers)
        
        # Send confirmation message
        message.reply_text(f"✅ Sticker saved as number {next_number}")
        
        # Print current collection
        print("\n📚 Current Sticker Collection:")
        for num, sticker_data in stickers.items():
            print(f"Number {num}: {sticker_data['emoji']} - {sticker_data['file_id']}")
        
        message.reply_sticker(message.sticker.file_id)
    
    print(message)
    print("-" * 40)

app.run()
