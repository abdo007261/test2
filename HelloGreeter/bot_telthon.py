import os
import json
import pytz
from datetime import datetime, timedelta
from telethon import TelegramClient, events, Button
from telethon.tl.types import PeerChannel, PeerChat
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.date import DateTrigger
import asyncio

# Credentials
api_id = 26866999
api_hash = "0078471b8da9dd7c2b4658f85eebead2"
bot_token = "7550043947:AAGvm1OCEU2EbwvrZJEAk95_QJ1hzMYzF3s"

# Initialize Telthon client
client = TelegramClient('Scheduler_Bot_telthon', api_id, api_hash).start(bot_token=bot_token)

# Scheduler
scheduler = AsyncIOScheduler()

# Data files
DATA_FILE = "data.json"
ADMINS_FILE = "admins.json"
ACTIVITY_FILE = "activity_data.json"

# Load data helpers
def load_json(filename):
    if os.path.exists(filename):
        with open(filename, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if not content:
                return {}
            return json.loads(content)
    return {}

def save_json(filename, data):
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

data_store = load_json(DATA_FILE)
admin_user_ids = load_json(ADMINS_FILE) or [1602528125]

# /start command
def get_main_keyboard():
    return [
        [Button.inline("📅 Schedule a Message", b"broadcast"), Button.inline("📢 Broadcast now", b"broadcast")],
        [Button.inline("📋 Current Tasks", b"current_tasks")],
        [Button.inline("Add/Remove/Show admins 🛡️", b"admins_part")],
        [Button.inline("Show channels/groups list 📃📡", b"show_channels")],
        [Button.inline("📊 Show Groups/Channels Stats", b"show_groups_channels")],
        [Button.inline("🎮 Manage Sweepstakes", b"manage_sweepstakes")],
        [Button.inline("Active Groups", b"active_groups")],
        [Button.inline("ℹ️ Help", b"help")],
    ]

@client.on(events.NewMessage(pattern=r"/start"))
async def start_handler(event):
    user_id = event.sender_id
    user = await event.get_sender()
    user_name = user.first_name or "User"
    if user_id not in admin_user_ids:
        admin_user_ids.append(user_id)
        save_json(ADMINS_FILE, admin_user_ids)
    await event.respond(
        f"Hello, {user_name}! 😊\nWelcome to the Task Scheduler Bot! 📅\nWhat would you like to do today?",
        buttons=get_main_keyboard()
    )

# /help command
@client.on(events.NewMessage(pattern=r"/help"))
async def help_handler(event):
    help_text = (
        '🤖 **Task Scheduler Bot - Complete Guide**\n\n'
        'Welcome to the Task Scheduler Bot! Here\'s a comprehensive guide on how to use all features:\n\n'
        '💡 **Quick Commands:**\n'
        '- /start - Start the bot\n'
        '- /stats - View analytics\n'
        '- /add_id - Add channel/group ID by specifying the ID *(Example: /add_id -100123456789)*\n'
        '- /add_chat_id - Add current chat ID to channels list\n'
        '- /activate - activate the bot if it doesn\'t send any messages to a specific channel or group \n'
        '- /id - Get current chat ID\n\n'
        '... (rest of help text as in original) ...\n'
        'Need more help? Contact me! https://t.me/mrnobody2007'
    )
    await event.respond(help_text, buttons=[[Button.inline("🔙 Back to Home", b"back_to_home")]])

# Example group command: /check_m
@client.on(events.NewMessage(pattern=r"/check_m", func=lambda e: e.is_group))
async def check_m_handler(event):
    chat_id = str(event.chat_id)
    user_id = str(event.sender_id)
    now = datetime.now(pytz.UTC)
    one_month_ago = now - timedelta(days=30)
    activity_data = load_json(ACTIVITY_FILE)
    if chat_id not in activity_data:
        await event.reply("❌ No activity data for this chat.")
        return
    from collections import Counter
    member_activity = Counter()
    for record in activity_data[chat_id]:
        uid = record.get("user_id")
        msg_date_str = record.get("date")
        if not uid or not msg_date_str:
            continue
        try:
            msg_date = datetime.strptime(msg_date_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=pytz.UTC)
        except ValueError:
            continue
        if msg_date >= one_month_ago:
            member_activity[uid] += 1
    sorted_members = member_activity.most_common()
    month_name = now.strftime("%B")
    for i, (member_id, count) in enumerate(sorted_members, 1):
        if member_id == user_id:
            try:
                user = await client.get_entity(int(member_id))
                response = f"📊 Your chat statistics for [{month_name}] 📊\n\n"
                response += f"👤 User: {user.first_name}\n"
                response += f"Total messages: {count}\n"
                response += f"Rating: {i}\n"
            except Exception:
                response = f"📊 Your chat statistics for [{month_name}] 📊\n\n"
                response += f"👤 User: {member_id}\n"
                response += f"Total messages: {count}\n"
                response += f"Rating: {i}\n"
    await event.reply(response)

# /add_id command
@client.on(events.NewMessage(pattern=r"/add_id"))
async def add_id_handler(event):
    message_text = event.raw_text.strip()
    split_message = message_text.split(' ')
    if len(split_message) > 1:
        channel_id = str(split_message[1])
        if "channels" not in data_store:
            data_store["channels"] = {}
        if channel_id not in data_store["channels"]:
            try:
                chat = await client.get_entity(int(channel_id))
                name = getattr(chat, 'title', None) or getattr(chat, 'first_name', None) or "Unknown"
                data_store["channels"][channel_id] = {"name": name, "selected": True}
                save_json(DATA_FILE, data_store)
                await event.reply(f"Successfully added ID: {channel_id} 👍")
            except Exception as e:
                await event.reply("❌ Error: Could not verify this ID. Make sure the bot is a member of the channel/group.")
        else:
            await event.reply(f"This ID '{channel_id}' is already added.")
    else:
        await event.reply("❌ Please provide an ID after the command.\nExample: `/add_id -100123456789`")

# /add_chat_id command
@client.on(events.NewMessage(pattern=r"/add_chat_id"))
async def add_chat_id_handler(event):
    channel_id = str(event.chat_id)
    if "channels" not in data_store:
        data_store["channels"] = {}
    if channel_id not in data_store["channels"]:
        name = event.chat.title if hasattr(event.chat, 'title') else "Unknown"
        data_store["channels"][channel_id] = {"name": name}
        save_json(DATA_FILE, data_store)
        await event.reply("Added 👍")
    else:
        await event.reply(f"This ID is '{channel_id}' already added.")

# /stats command (private only)
@client.on(events.NewMessage(pattern=r"/stats", func=lambda e: e.is_private))
async def stats_handler(event):
    if event.sender_id not in admin_user_ids:
        await event.reply("⚠️ You are not authorized to use this command.")
        return
    await event.respond(
        "Welcome to the Analytics Bot Admin Panel! 👋\nChoose an option below:",
        buttons=[[Button.inline("📊 Show Groups/Channels", b"show_groups_channels")]]
    )

# /activate command
@client.on(events.NewMessage(pattern=r"/activate"))
async def activate_handler(event):
    await event.reply("Activated 👍")

# /id command
@client.on(events.NewMessage(pattern=r"/id"))
async def id_handler(event):
    await event.reply(f"ID: {event.chat_id}")

# /top command
@client.on(events.NewMessage(pattern=r"/top"))
async def top_handler(event):
    chat_id = str(event.chat_id)
    now = datetime.now(pytz.UTC)
    one_month_ago = now - timedelta(days=30)
    activity_data = load_json(ACTIVITY_FILE)
    if chat_id not in activity_data:
        await event.reply("❌ No activity data for this chat.")
        return
    from collections import Counter
    member_activity = Counter()
    total_message_count = 0
    for record in activity_data[chat_id]:
        uid = record.get("user_id")
        msg_date_str = record.get("date")
        if not uid or not msg_date_str:
            continue
        try:
            msg_date = datetime.strptime(msg_date_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=pytz.UTC)
        except ValueError:
            continue
        if msg_date >= one_month_ago:
            total_message_count += 1
            member_activity[uid] += 1
    sorted_members = member_activity.most_common()
    total_members = len(sorted_members)
    month_name = now.strftime("%B")
    response = f"📊 [{month_name}] Rankings 📊\n\n"
    response += f"Total messages: {total_message_count}\n"
    response += f"Number of chat members: {total_members}\n\n"
    response += "👥 The rankings are as follows:\n"
    for i, (member_id, count) in enumerate(sorted_members, 1):
        try:
            user = await client.get_entity(int(member_id))
            name = getattr(user, 'first_name', None) or "Unnamed User"
            response += f"{i}. {name}: {count} messages\n"
        except Exception:
            response += f"{i}. User ID {member_id}: {count} messages\n"
    await event.reply(response)

# --- Admin and Channel Management State ---
admin_add_state = {}
admin_remove_state = {}

# --- Inline Button Callback Handler ---
@client.on(events.CallbackQuery)
async def callback_handler(event):
    data = event.data.decode() if isinstance(event.data, bytes) else event.data
    user_id = event.sender_id

    # --- Admins Menu ---
    if data == 'admins_part':
        keyboard = [
            [Button.inline("Add new admin 🆕👮‍♂️", b"add_admin"), Button.inline("Remove an admin  🗑️👮‍♂️", b"remove_admin")],
            [Button.inline("Show admins list 📋👮‍♂️", b"show_admins")],
            [Button.inline("Back 🔙", b"back_to_home")],
        ]
        await event.edit("Choose an action:", buttons=keyboard)

    # --- Add Admin ---
    elif data == 'add_admin':
        admin_add_state[user_id] = True
        await event.respond("Please send the new admin's user ID.", buttons=[[Button.inline("Back 🔙", b"admins_part")]])

    # --- Remove Admin ---
    elif data == 'remove_admin':
        admin_remove_state[user_id] = True
        await event.respond("Please send the admin's user ID to delete it.", buttons=[[Button.inline("Back 🔙", b"admins_part")]])

    # --- Show Admins ---
    elif data == 'show_admins':
        msg = "Admin List:\n"
        for uid in admin_user_ids:
            try:
                user = await client.get_entity(uid)
                username = getattr(user, 'username', None) or "No username"
                first_name = getattr(user, 'first_name', None) or "No first name"
                last_name = getattr(user, 'last_name', None) or "No last name"
                msg += f"@{username} , Mr.{first_name} {last_name} , ID: {uid}\n"
            except Exception:
                msg += f"@Unknown , Mr.Unknown , ID: {uid}\n"
        await event.respond(msg, buttons=[[Button.inline("Back 🔙", b"admins_part")]])

    # --- Channel/Group Management ---
    elif data == 'show_channels':
        buttons = []
        current_row = []
        for chat_id in data_store.get("channels", {}):
            channel_name = data_store["channels"][chat_id].get("name", chat_id)
            is_selected = data_store["channels"][chat_id].get("selected", True)
            toggle_symbol = "✅" if is_selected else "❌"
            current_row.append(Button.inline(f"{toggle_symbol} {channel_name}", f"toggle_channel_{chat_id}".encode()))
            if len(current_row) == 2:
                buttons.append(current_row)
                current_row = []
        if current_row:
            buttons.append(current_row)
        buttons.append([Button.inline("Select All ☑", b"select_all_channels"), Button.inline("Deselect All ❌", b"deselect_all_channels")])
        buttons.append([Button.inline("🗑️ Delete Channels", b"channels_list_remover")])
        buttons.append([Button.inline("Back 🔙", b"back_to_home")])
        await event.edit("Select channels to broadcast to:\n(✅ = Selected, ❌ = Not Selected)", buttons=buttons)

    # --- Toggle Channel Selection ---
    elif data.startswith('toggle_channel_'):
        chat_id = data.split('_', 2)[2]
        if chat_id in data_store.get("channels", {}):
            current = data_store["channels"][chat_id].get("selected", True)
            data_store["channels"][chat_id]["selected"] = not current
            save_json(DATA_FILE, data_store)
        # Refresh the channel list
        await callback_handler(await event._replace(data=b'show_channels'))

    # --- Select All Channels ---
    elif data == 'select_all_channels':
        for chat_id in data_store.get("channels", {}):
            data_store["channels"][chat_id]["selected"] = True
        save_json(DATA_FILE, data_store)
        await callback_handler(await event._replace(data=b'show_channels'))

    # --- Deselect All Channels ---
    elif data == 'deselect_all_channels':
        for chat_id in data_store.get("channels", {}):
            data_store["channels"][chat_id]["selected"] = False
        save_json(DATA_FILE, data_store)
        await callback_handler(await event._replace(data=b'show_channels'))

    # --- Delete Channels List ---
    elif data == 'channels_list_remover':
        buttons = []
        current_row = []
        for chat_id in data_store.get("channels", {}):
            channel_name = data_store["channels"][chat_id].get("name", chat_id)
            current_row.append(Button.inline(f"🗑️ {channel_name}", f"confirm_remove_{chat_id}".encode()))
            if len(current_row) == 2:
                buttons.append(current_row)
                current_row = []
        if current_row:
            buttons.append(current_row)
        buttons.append([Button.inline("Back 🔙", b"show_channels")])
        await event.edit("Select a channel/group to delete:", buttons=buttons)

    # --- Confirm Remove Channel ---
    elif data.startswith('confirm_remove_'):
        chat_id = data.split('_', 2)[2]
        channel_name = data_store["channels"].get(chat_id, {}).get("name", chat_id)
        buttons = [
            [Button.inline("✅ Delete", f"remove_confirmed_{chat_id}".encode()), Button.inline("❌ Cancel", b"channels_list_remover")]
        ]
        await event.edit(f"Are you sure you want to delete {channel_name}?", buttons=buttons)

    # --- Remove Confirmed Channel ---
    elif data.startswith('remove_confirmed_'):
        chat_id = data.split('_', 2)[2]
        channel_name = data_store["channels"].get(chat_id, {}).get("name", chat_id)
        if chat_id in data_store["channels"]:
            del data_store["channels"][chat_id]
            save_json(DATA_FILE, data_store)
        await event.respond(f"Channel {channel_name} deleted successfully!", buttons=[[Button.inline("Back", b"channels_list_remover")]])
        await callback_handler(await event._replace(data=b'channels_list_remover'))

    # --- Back to Home ---
    elif data == 'back_to_home':
        await start_handler(event)

# --- Admin Add/Remove Message Handlers ---
@client.on(events.NewMessage)
async def admin_add_remove_message_handler(event):
    user_id = event.sender_id
    text = event.raw_text.strip()
    # Add admin
    if admin_add_state.get(user_id):
        if text.isdigit():
            new_admin_id = int(text)
            if new_admin_id not in admin_user_ids:
                admin_user_ids.append(new_admin_id)
                save_json(ADMINS_FILE, admin_user_ids)
                await event.reply(f"New admin added: {new_admin_id}")
            else:
                await event.reply("This user is already an admin.")
        else:
            await event.reply("Invalid ID. Please send a numeric user ID.")
        admin_add_state.pop(user_id, None)
    # Remove admin
    elif admin_remove_state.get(user_id):
        if text.isdigit():
            remove_admin_id = int(text)
            if remove_admin_id in admin_user_ids:
                admin_user_ids.remove(remove_admin_id)
                save_json(ADMINS_FILE, admin_user_ids)
                await event.reply(f"Admin removed: {remove_admin_id}")
            else:
                await event.reply("This user is not in the admin list.")
        else:
            await event.reply("Invalid ID. Please send a numeric user ID.")
        admin_remove_state.pop(user_id, None)

# --- Broadcasting Functionality ---
@client.on(events.NewMessage(pattern=r"/broadcast"))
async def broadcast_handler(event):
    if event.sender_id not in admin_user_ids:
        await event.reply("⚠️ You are not authorized to use this command.")
        return
    await event.reply("Please send the message you want to broadcast to all channels/groups.")

@client.on(events.NewMessage)
async def handle_broadcast_message(event):
    if event.sender_id in admin_user_ids and event.raw_text:
        message_to_broadcast = event.raw_text.strip()
        channels = data_store.get("channels", {})
        for chat_id, channel_info in channels.items():
            if channel_info.get("selected", False):
                try:
                    await client.send_message(int(chat_id), message_to_broadcast)
                except Exception as e:
                    print(f"Failed to send message to {chat_id}: {e}")
        await event.reply("Broadcast message sent to all selected channels/groups!")

if __name__ == "__main__":
    print("Telthon bot started.")
    scheduler.start()  # Start the scheduler here
    client.run_until_disconnected() 