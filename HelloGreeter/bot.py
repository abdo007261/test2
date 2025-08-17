import os
import copy
from concurrent.futures import ThreadPoolExecutor
import pytz
import atexit
import json
from pyrogram.errors import MessageNotModified
from moviepy import VideoFileClip
from datetime import datetime, timedelta
import re
from pyrogram import filters, errors
from pyrogram.handlers import MessageHandler
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton, CallbackQuery
import sqlite3
import asyncio
import random
from pyrogram.client import Client
from pyrogram.types import BotCommand, BotCommandScope, BotCommandScopeAllPrivateChats, MenuButtonDefault
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.date import DateTrigger
from pyrogram.errors import ButtonUrlInvalid, MediaCaptionTooLong
import asyncio
from datetime import datetime
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR
import json
from datetime import datetime, timezone, timedelta
from collections import Counter
from pyrogram import Client, filters
import pytz
from filelock import FileLock
global admin_user_id
admin_user_id = 1602528125  # Replace with the actual admin user ID

# Create a ThreadPoolExecutor
executor = ThreadPoolExecutor(max_workers=2)

# Define the bot commands
COMMANDS = [
    BotCommand(command="start", description="Start the bot"),
    BotCommand(command="help", description="Show help message"),
    BotCommand(command="back", description="Return to main menu"),
]
# Replace 'my_bot' with the name you want for your bot, and fill in your API credentials
api_id = 26866999
api_hash = "0078471b8da9dd7c2b4658f85eebead2"
consecutive_losses = 0
consecutive_wins = 0
bot_token = "7769423370:AAE9mgtgBfssBzAEyMbeMZzhawz2Oeb1Gyo"
global user_id
user_id = 123456
global button_index
buttpn_index = {
    admin_user_id : 1
}
global user_lan
user_lan = {
    user_id : 'en'
}
import json
DATA_FILE = "data.json"
ADMINS_FILE = "admins.json"
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as file:
            return json.load(file)
        
# Function to save data to JSON file
def save_data(data):
    with open(DATA_FILE, "w") as file:
        json.dump(data, file, indent=4)
        
def load_data2():
    if os.path.exists(ADMINS_FILE):
        with open(ADMINS_FILE, "r") as file:
            return json.load(file)

# Function to save data to JSON file
def save_data2(data):
    with open(ADMINS_FILE, "w") as file:
        json.dump(data, file, indent=4)

def save_tasks(tasks):
    with open('tasks.json', 'w') as f:
        json.dump(tasks, f, default=str)

# Function to load tasks from a file
def load_tasks():
    try:
        with open('tasks.json', 'r') as f:
            content = f.read().strip()
            if not content:
                return {}
            return json.loads(content)
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError:
        print("Error decoding JSON from tasks.json. Returning empty task list.")
        return {}

def load_activity_data():
    if not os.path.exists("activity_data.json"):
        return {}
    
    try:
        with open("activity_data.json", "r", encoding="utf-8") as f:
            data = f.read().strip()
            # If the file is empty, return an empty dictionary
            if not data:
                return {}
            return json.loads(data)
    except (json.JSONDecodeError, ValueError) as e:
        print(f"Error loading activity data: {e}")
        return {}
    
#-------analysis_file
DATA_FILE2 = "activity_data.json"
if not os.path.exists(DATA_FILE2):
    # Create a new file with an empty JSON object
    with open(DATA_FILE2, "w", encoding="utf-8") as f:
        json.dump({}, f)

try:
    with open(DATA_FILE2, "r", encoding="utf-8", errors="replace") as f:
        content = f.read().strip()
        if not content:
            data=  {}
        else:
            # Load the JSON data
            data = json.loads(content)
except UnicodeDecodeError as e:
    print(f"Unicode error: {e}")
    exit(1)
    
def save_data3():
    lock = FileLock(f"{DATA_FILE2}.lock")
    try:
        with lock:
            with open(DATA_FILE2, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"Error in save_data3: {e}")

# -------------------------------
# File names and global variables
# -------------------------------
ACTIVITY_FILE = "activity_data.json"
DRAWS_FILE = "draws_data.json"
PRIZES_FILE = "prizes_config.json"

# Default prizes configuration
prizes_config = {
    "prizes": [
        {"name": "Prize 1", "odds": 50},   # 50% chance
        {"name": "Prize 2", "odds": 30},   # 30% chance
        {"name": "Prize 3", "odds": 20}    # 20% chance
    ]
}

# -------------------------------
# Helper functions for prizes config
# -------------------------------
def save_prizes_config():
    with open(PRIZES_FILE, "w", encoding="utf-8") as f:
        json.dump(prizes_config, f, indent=4, ensure_ascii=False)

def load_prizes_config():
    global prizes_config
    try:
        with open(PRIZES_FILE, "r", encoding="utf-8") as f:
            prizes_config = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        save_prizes_config()

load_prizes_config()

def save_activity_data(data):
    lock = FileLock(f"{ACTIVITY_FILE}.lock")
    try:
        with lock:
            with open(ACTIVITY_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"Error in save_data3: {e}")
        
        
data_store = load_data()
global admin_user_ids
admin_user_ids = load_data2() # Replace with the actual admin user ID

global new_button_title
new_button_title = {
    'title' : ''
}


the_data_dict = {
    'user_id': {
        "message": "Hello, world!",
        "buttons": [
            {
                'id': 1,
                "title": "Click me!",
                "url": "https://example.com/button1",
                'place': 0,
            }
        ],
        "type": "no_button",
    }
}

# Store the main event loop for use in sync wrappers
main_loop = asyncio.get_event_loop()

# Synchronous wrapper for broadcast_to_channels for BackgroundScheduler
# This allows running the async function in the main event loop from a background thread

def sync_broadcast_to_channels(*args, **kwargs):
    future = asyncio.run_coroutine_threadsafe(
        broadcast_to_channels(*args, **kwargs), main_loop
    )
    return future.result()

# Initialize the scheduler
scheduler = BackgroundScheduler()
tasks = {}
task_names = set()
global the_user_choice
the_user_choice = {
    "sch_type": None,
    "phase": 1,
    "task_name": None,
    "task_title": None,
    "task_message": None,
    "editing_buttons": None,
    "media_group": None,
}

def job_listener(event):
    if event.exception:
        print(f"Job {event.job_id} failed.")
    else:
        print(f"Job {event.job_id} executed successfully.")
        # Check if the job ID starts with "date_" before removing it
        if event.job_id.startswith("date_"):
            task_title = event.job_id[5:]  # Remove "date_" prefix to get the task title
            if task_title in tasks:
                del tasks[task_title]
                print(f"Date-type job {task_title} removed from tasks list.")
            else:
                print(f"Task {task_title} not found in tasks list.")#
        else:
            job = scheduler.get_job(event.job_id)
            if job and isinstance(job.trigger, DateTrigger):
                task_title = event.job_id[5:]  # Remove "date_" prefix to get the task title
                if task_title in tasks:
                    del tasks[task_title]
                    print(f"Date-type job {task_title} removed from tasks list.")
                else:
                    print(f"Task {task_title} not found in tasks list.")

user_session = {
    'id': {
        'input' : 'test',
        'user_id' : 45244,
        'type' : 'c7',
        'handeler' : 'c7',
        'output' : 'test'
    }
}

users_handlers = {
    'user_id' : {
        'handler' : 'ww'
    } 
}

app = Client("Scheduler_Bot23", api_id=api_id, api_hash=api_hash, bot_token=bot_token)
# Initialize the database
def init_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY)''')
    conn.commit()
    conn.close()

init_db()


async def setup_commands():
    try:
        # Set commands for private chats
        await app.set_bot_commands(
            commands=COMMANDS,
            scope=BotCommandScopeAllPrivateChats()
        )
        
        # Set the menu button using the correct method
        await app.set_chat_menu_button(
            chat_id=None,  # None means default for all chats
            menu_button=MenuButtonDefault()
        )
        
        print("Bot commands and menu button set up successfully!")
    except Exception as e:
        print(f"Error setting up commands: {e}")

def shutdown():
    # Convert tasks to a serializable format
    serializable_tasks = {}
    for task_title, job in tasks.items():
        trigger = job.trigger
        if isinstance(trigger, CronTrigger):
            trigger_type = 'cron'
            try:
                def parse_cron(cron_string):
                    # Define default values
                    defaults = {
                        'minute': '*',
                        'hour': '*',
                        'day': '*',
                        'month': '*',
                        'day_of_week': '*'
                    }

                    # Extract key-value pairs from the cron string
                    matches = re.findall(r"(\w+)='([^']*)'", cron_string)

                    # Update defaults with the extracted values
                    for key, value in matches:
                        if key in defaults:
                            defaults[key] = value

                    return defaults

                cron_list = str(trigger)
                print(cron_list)
                parsed_fields = parse_cron(cron_list)
                # parsed_fields = {
                #     'minute': minute1,
                #     'hour': hour1,
                #     'day': day1,
                #     'month': month1,
                #     'day_of_week': day_of_week1
                # }
                print(parsed_fields)
                # Construct the cron string representation
                cron_parts = []
                cron_parts.append(parsed_fields['minute'])
                cron_parts.append(parsed_fields['hour'])
                cron_parts.append(parsed_fields['day'])
                cron_parts.append(parsed_fields['month'])
                cron_parts.append(parsed_fields['day_of_week'])
                print(cron_parts)
                trigger_args = cron_parts
            except Exception as e:
                print(f"Error processing cron trigger fields: {e}")
                continue
        elif isinstance(trigger, IntervalTrigger):
            trigger_type = 'interval'
            trigger_args = {'seconds': trigger.interval.total_seconds()}
        elif isinstance(trigger, DateTrigger):
            trigger_type = 'date'
            trigger_args = {'run_date': trigger.run_date.isoformat()}
        else:
            continue

        serializable_tasks[task_title] = {
            'trigger_type': trigger_type,
            'trigger_args': trigger_args,
            'args': job.args
        }

    save_tasks(serializable_tasks)

def store_user_id(user_id):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''INSERT OR IGNORE INTO users (user_id) VALUES (?)''', (user_id,))
    conn.commit()
    conn.close()

# Function to find the index of a dictionary in the list using the ID
def find_index_by_id(id_to_find):
    for i, d in enumerate(broadcast_data["buttons"]):
        if d['id'] == id_to_find:
            print('-------------------------------')
            print(f'The id is {id_to_find}')
            print(f'The index is {i}')
            print('-------------------------------')
            return i
    return -1  # Return -1 if the ID is not found
global rescheduled_task_names
rescheduled_task_names = []

global is_first_time
is_first_time = True

user_tasks = {}


def is_admin(user_id):
    return user_id in admin_user_ids

@app.on_message(filters.command("start"))
async def start(client, message):
    global is_first_time
    if is_first_time:
        scheduler.start()
        
        
        
        is_first_time = False
    global user_id
    global rescheduled_task_names
    user_id = message.chat.id
    # Assuming user_lan is your dictionary
    if user_id not in user_lan:
        # User ID not found, add it to the dictionary
        user_lan[user_id] = 'en'  # Assuming the default language is English

    user_name = message.chat.first_name
    print(user_id)
    store_user_id(user_id)
    admins =  [6494713901]
    if message.chat.id in admin_user_ids: 
        if is_first_time == True:
            scheduler.start()
            await setup_commands()  # Add this line
        else:
            pass
        the_user_choice["sch_type"] = None
        the_user_choice["task_title"] = None
        is_first_time = False
        the_user_choice["phase"] == 1
        the_user_choice[user_id] = 'None'
        the_user_choice["media_group"] = False
        user_name = message.from_user.first_name
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("📅 Schedule a Massage", callback_data="broadcast"),
                InlineKeyboardButton("📢 Broadcast now", callback_data='broadcast')
            ],
            [InlineKeyboardButton("📋 Current Tasks", callback_data="current_tasks")],
            [InlineKeyboardButton("Add/Remove/Show admins 🛡️", callback_data='admins_part')],
            [InlineKeyboardButton("Show channels/groups list 📃📡", callback_data='show_channels')],
            [InlineKeyboardButton("📊 Show Groups/Channels Stats", callback_data="show_groups_channels")],
            [InlineKeyboardButton("🎮 Manage Sweepstakes", callback_data="manage_sweepstakes")],
            [InlineKeyboardButton("Active Groups", callback_data="active_groups")],
            [InlineKeyboardButton("ℹ️ Help", callback_data="help")]
        ])

        await app.send_message(message.chat.id, f"Hello, {user_name}! 😊\nWelcome to the Task Scheduler Bot! 📅\nWhat would you like to do today?", reply_markup=keyboard)

#=================================================================================================================================================
@app.on_message(filters.command('add_id'))
async def add_id(client, message):
    global data_store
    
    # Get the full message text and split it
    message_text = message.text.strip()
    split_message = message_text.split(' ')
    
    # Check if there's a value after the space
    if len(split_message) > 1:
        try:
            # Get the ID from the split message
            channel_id = str(split_message[1])
            print(f"Received ID to add: {channel_id}")  # Print the ID
            
            # Check if the ID already exists
            if channel_id not in data_store["channels"]:
                try:
                    # Try to get chat info to verify the ID is valid
                    chat = await client.get_chat(int(channel_id))
                    data_store["channels"][channel_id] = {
                        "name": chat.first_name or chat.title or "Unknown",
                        "selected": True
                    }
                    save_data(data_store)
                    await message.reply_text(f"Successfully added ID: {channel_id} 👍")
                except Exception as e:
                    await message.reply_text("❌ Error: Could not verify this ID. Make sure the bot is a member of the channel/group.")
            else:
                await message.reply_text(f"This ID '{channel_id}' is already added.")
        except (ValueError, IndexError):
            await message.reply_text("❌ Invalid ID format. Please provide a valid ID number.\nExample: `/add_id -100123456789`")
    else:
        await message.reply_text("❌ Please provide an ID after the command.\nExample: `/add_id -100123456789`")

@app.on_message(filters.command("check_m") & filters.group)
async def check_command(client, message):
    user_id = str(message.from_user.id)  # Convert to string to match JSON data
    chat_id = str(message.chat.id)
    now = datetime.now(pytz.UTC)

    # Time range for the last month
    one_month_ago = now - timedelta(days=30)

    # Initialize counters
    total_message_count = 0
    member_activity = Counter()

    # Load activity data from JSON
    try:
        with open("activity_data.json", "r", encoding="utf-8") as f:
            activity_data = json.load(f)
    except FileNotFoundError:
        await message.reply_text("❌ No activity data found. The bot hasn't tracked any messages yet.")
        return

    # Check if chat_id exists in the data
    if chat_id not in activity_data:
        await message.reply_text("❌ No activity data for this chat.")
        return

    # Iterate through messages for the specific chat
    for record in activity_data[chat_id]:
        # Extract and validate necessary fields
        user_id = record.get("user_id")
        msg_date_str = record.get("date")

        if not user_id or not msg_date_str:
            continue  # Skip records with missing data

        try:
            msg_date = datetime.strptime(msg_date_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=pytz.UTC)
        except ValueError:
            continue  # Skip invalid date formats

        if msg_date >= one_month_ago:
            total_message_count += 1
            member_activity[user_id] += 1

    # Get all members sorted by message count
    sorted_members = member_activity.most_common()

    # Count the total number of members
    total_members = len(sorted_members)

    # Get the month name for the rankings
    month_name = now.strftime("%B")

    # Prepare the response message
    for i, (member_id, count) in enumerate(sorted_members, 1):
        if member_id == user_id:
            try:
                user = await client.get_users(member_id)
                # response += f"{i}. {user.first_name or 'Unnamed User'}: {count} messages\n"
                response = f"📊 Your chat statistics for [{month_name}] 📊\n\n"
                response += f"👤 User: {user.first_name}\n"
                response += f"Total messages: {count}\n"
                response += f"Rating: {i}\n"
            except Exception:
                response = f"📊 Your chat statistics for [{month_name}] 📊\n\n"
                response += f"👤 User: {member_id}\n"
                response += f"Total messages: {count}\n"
                response += f"Rating: {i}\n"
                # response += f"{i}. User ID {member_id}: {count} messages\n"

    await message.reply_text(response)


@app.on_message(filters.command("top"))
async def top_command(client, message):
    chat_id = str(message.chat.id)
    now = datetime.now(pytz.UTC)

    # Time range for the last month
    one_month_ago = now - timedelta(days=30)

    # Initialize counters
    total_message_count = 0
    member_activity = Counter()

    # Load activity data from JSON
    try:
        with open("activity_data.json", "r", encoding="utf-8") as f:
            activity_data = json.load(f)
    except FileNotFoundError:
        await message.reply_text("❌ No activity data found. The bot hasn't tracked any messages yet.")
        return

    # Check if chat_id exists in the data
    if chat_id not in activity_data:
        await message.reply_text("❌ No activity data for this chat.")
        return

    # Iterate through messages for the specific chat
    for record in activity_data[chat_id]:
        # Extract and validate necessary fields
        user_id = record.get("user_id")
        msg_date_str = record.get("date")

        if not user_id or not msg_date_str:
            continue  # Skip records with missing data

        try:
            msg_date = datetime.strptime(msg_date_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=pytz.UTC)
        except ValueError:
            continue  # Skip invalid date formats

        if msg_date >= one_month_ago:
            total_message_count += 1
            member_activity[user_id] += 1

    # Get all members sorted by message count
    sorted_members = member_activity.most_common()

    # Count the total number of members
    total_members = len(sorted_members)

    # Get the month name for the rankings
    month_name = now.strftime("%B")

    # Prepare the response message
    response = f"📊 [{month_name}] Rankings 📊\n\n"
    response += f"Total messages: {total_message_count}\n"
    response += f"Number of chat members: {total_members}\n\n"

    response += "👥 The rankings are as follows:\n"
    for i, (member_id, count) in enumerate(sorted_members, 1):
        try:
            user = await client.get_users(member_id)
            response += f"{i}. {user.first_name or 'Unnamed User'}: {count} messages\n"
        except Exception:
            response += f"{i}. User ID {member_id}: {count} messages\n"

    await message.reply_text(response)

@app.on_message(filters.new_chat_members)
async def welcome_new_member(client, message):
    # Get the new member details
    new_member = message.new_chat_members[0]
    
    # Get the chat details
    chat = message.chat
    
    # Formatted welcome message
    fullname = new_member.first_name
    if new_member.last_name:
        fullname += f" {new_member.last_name}"

    # Welcome message
    welcome_message = f"Hello {fullname}! Welcome to {chat.title}!"
    
    # Send the welcome message to the chat
    await message.reply_text(welcome_message)


@app.on_message(filters.command('add_chat_id'))
def add_id(bot, message):
    global data_store
    channel_id = str(message.chat.id)  # Ensure the ID is a string for consistent key usage
    if channel_id not in data_store["channels"]:
        data_store["channels"][channel_id] = {"name": message.chat.first_name or message.chat.title}
        save_data(data_store)
        bot.send_message(message.chat.id, "Added 👍")
    else:
        bot.send_message(message.chat.id, f"This ID is '{channel_id}' already added.")
        
@app.on_message(filters.command("stats") & filters.private)
async def show_stats(client, message):
    if not is_admin(message.from_user.id):
        await message.reply_text("⚠️ You are not authorized to use this command.")
        return
        
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 Show Groups/Channels", callback_data="show_groups_channels")]
    ])
    await message.reply_text("Welcome to the Analytics Bot Admin Panel! 👋\nChoose an option below:", reply_markup=keyboard)

    
@app.on_message(filters.command('activate'))
def start_command(bot, message):
    global keyboard
    bot.send_message(message.chat.id, "Activated 👍")

@app.on_message(filters.command('id'))
def start_command(bot, message):
    global keyboard
    id = bot.get_chat(message.chat.id)
    bot.send_message(message.chat.id, id.id)
    print('ID: ',id.id)

the_data_dict[admin_user_id] = {
    "message": "Hello, new user!",
    "type": None,
    "buttons": [
        {
            'id': 1,
            "title": "Click me too!",
            "url": "https://example.com/button2",
            'place': 1,
        }
    ]
}
global broadcast_data
broadcast_data = the_data_dict[admin_user_id]

@app.on_message(filters.command("help"))
async def help_command(client, message):
    help_text = (
        '''
🤖 **Task Scheduler Bot - Complete Guide**

Welcome to the Task Scheduler Bot! Here's a comprehensive guide on how to use all features:

💡 **Quick Commands:**
- /start - Start the bot
- /stats - View analytics
- /add_id - Add channel/group ID by specifying the ID *(Example: /add_id -100123456789)*
- /add_chat_id - Add current chat ID to channels list
- /activate - activate the bot if it doesn't send any messages to a specific channel or group 
- /id - Get current chat ID

📱 **Main Features:**

1. **Message Scheduling** 📅
   - Schedule messages with or without buttons
   - Support for text, media, and media groups
   - Round video converter functionality
   - Three scheduling methods available

2. **Task Management** 📋
   - View all scheduled tasks
   - Edit task details (title/content/buttons)
   - Pause/Resume scheduling
   - Delete tasks
   - Send scheduled messages immediately

3. **Admin Controls** 👑
   - Manage admin access
   - Control channels/groups
   - View detailed analytics

📝 **Scheduling Methods:**

1. **Cron Schedule** ⏰
   Format: minute-hour-day-month-day_of_week
   
   Examples:
   - `30 10 * * 5` = Every Friday at 10:30 AM
   - `*/5 * * * *` = Every 5 minutes
   - `0 9 * * 1,5` = Every Monday and Friday at 9:00 AM
   
   Days: 0/7=Sun, 1=Mon, 2=Tue, 3=Wed, 4=Thu, 5=Fri, 6=Sat

2. **Interval Schedule** 🔄
   Format: Number of seconds
   
   Examples:
   - `3600` = Every hour
   - `86400` = Every day
   - `1800` = Every 30 minutes

3. **Date Schedule** 📆
   Format: YYYY-MM-DD HH:MM:SS
   
   Examples:
   - `2024-12-25 09:00:00` = December 25, 2024 at 9 AM
   - `2024-01-01 00:00:00` = New Year 2024 at midnight

🎛️ **Button Management:**
- Add unlimited buttons to messages
- Edit button text and URLs
- Arrange button layout
- Remove or modify existing buttons

📊 **Analytics Features:**
- Message count tracking
- Member activity monitoring
- Peak activity time analysis
- Daily/Monthly statistics
- Group/Channel performance metrics

🔍 **Task Operations:**
1. View tasks: Click "📋 Current Tasks"
2. Edit task: Select task → "✏️ Edit"
3. Pause/Resume: Use respective buttons on task view
4. Delete: Select task → "🗑️ Delete"
5. Send Now: Select task → "🚀 Send Now"

⚙️ **Additional Features:**
- Media group support
- Round video conversion
- Multiple button layouts
- Instant broadcasting
- Task scheduling queue

Need more help? Contact me! https://t.me/mrnobody2007
        '''
    )
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("🔙 Back to Home", callback_data="back_to_home")
    ]])
    await message.reply_text(help_text, reply_markup=keyboard)

@app.on_message(filters.command("back"))
async def back_home(client, message):
    if not is_admin(message.from_user.id):
        await message.reply_text("⚠️ You are not authorized to use this command.")
        return
        
    user_name = message.from_user.first_name
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📅 Schedule a Massage", callback_data="broadcast"),
            InlineKeyboardButton("📢 Broadcast now", callback_data='broadcast')
        ],
        [InlineKeyboardButton("📋 Current Tasks", callback_data="current_tasks")],
        [InlineKeyboardButton("Add/Remove/Show admins 🛡️", callback_data='admins_part')],
        [InlineKeyboardButton("Show channels/groups list 📃📡", callback_data='show_channels')],
        [InlineKeyboardButton("📊 Show Groups/Channels Stats", callback_data="show_groups_channels")],
        [InlineKeyboardButton("ℹ️ Help", callback_data="help")]
    ])
    
    await message.reply_text(
        f"Welcome back, {user_name}! 😊\nWhat would you like to do?",
        reply_markup=keyboard
    )
        
@app.on_message(filters.command("reset_chat"))
async def reset_chat_command(client, message):
    chat_id = message.chat.id
    activity_data = load_activity_data()

    if str(chat_id) in activity_data:
        del activity_data[str(chat_id)]
        save_activity_data(activity_data)
        await message.reply_text("✅ Data for this chat has been reset.")
    else:
        await message.reply_text("❌ No data found for this chat.")

# Command: /reset_all
@app.on_message(filters.command("reset_all"))
async def reset_all_command(client, message):
    save_activity_data({})
    await message.reply_text("✅ All data has been reset.")
 
# -------------------------------
# Function to calculate draws for a user
# -------------------------------
def calculate_user_draws(chat_id, user_id):
    """
    Returns a tuple (draws_available, message_count) for the given user in chat_id 
    from period_start (a datetime object). For every 268 messages the user earns one draw, capped at 100.
    """

    now = datetime.now(pytz.UTC)

    # Time range for the current month
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # Initialize counters
    message_count = 0

    # Load activity data from JSON
    try:
        with open("activity_data.json", "r", encoding="utf-8") as f:
            activity_data = json.load(f)
    except FileNotFoundError:
        return
    
    # Process the data for the specific user
    for record in activity_data[str(chat_id)]:  # Iterate through the list of records
        record_user_id = record.get("user_id")
        msg_date_str = record.get("date")

        if not record_user_id or not msg_date_str:
            continue  # Skip entries with missing user_id or date

        if record_user_id != user_id:
            continue  # Skip messages not sent by the current user

        try:
            msg_date = datetime.strptime(msg_date_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=pytz.UTC)
        except ValueError:
            continue  # Skip records with invalid date format

        if msg_date >= month_start:  # Only count messages from the current month
            message_count += 1


    # Prepare and send the response

    points = message_count // 268
    draws = min(points, 100)
    return draws, message_count

# -------------------------------
# Command: /points - show available draws for current user
# -------------------------------
@app.on_message(filters.command("points"))
async def points_command(client, message):
    chat_id = str(message.chat.id)
    user_id = str(message.from_user.id)
    
    # Calculate total available draws based on messages
    total_draws, msg_count = calculate_user_draws(chat_id, int(user_id))
    
    # Load draws data
    try:
        with open(DRAWS_FILE, "r", encoding="utf-8") as f:
            draws_data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        draws_data = {}
    
    # Retrieve user draw data
    user_draw_data = draws_data.get(chat_id, {}).get(user_id, {"used_draws": 0})
    used_draws = user_draw_data.get("used_draws", 0)
    
    # Calculate remaining draws
    remaining_draws = max(0, total_draws - used_draws)
    
    # Send response to the user
    await message.reply_text(
        f"📊 You have sent {msg_count} messages this month.\n"
        f"🎟 Total draws earned: {total_draws}\n"
        f"❌ Draws used: {used_draws}\n"
        f"✅ Remaining draws: {remaining_draws}\n\n"
        f"📝 1 draw per 268 messages sent"
    )

# -------------------------------
# Command: /draw - user draws a prize if they have available draws
# -------------------------------
@app.on_message(filters.command("draw"))
async def draw_command(client, message):
    chat_id = str(message.chat.id)
    user_id = str(message.from_user.id)
    
    # Calculate available draws dynamically
    available_draws, _ = calculate_user_draws(chat_id, int(user_id))
    
    # Load draws data with file locking
    lock = FileLock("draws_data.lock")
    try:
        with lock:
            try:
                with open(DRAWS_FILE, "r", encoding="utf-8") as f:
                    draws_data = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                draws_data = {}
            
            # Initialize user data if not present
            if chat_id not in draws_data:
                draws_data[chat_id] = {}
            if user_id not in draws_data[chat_id]:
                draws_data[chat_id][user_id] = {
                    "used_draws": 0,
                    "points": available_draws  # Set initial points
                }
            
            user_draw_data = draws_data[chat_id][user_id]
            
            # Update points only if it's the first time
            
            user_draw_data["points"] = available_draws - user_draw_data["used_draws"]
            
            # Check draw limit and available points
            if user_draw_data["points"] <= 0:
                await message.reply_text("❌ You don't have enough points for a draw.")
                return
            if user_draw_data["used_draws"] >= 100:
                await message.reply_text("❌ You have reached your draw limit for this month.")
                return
            
            # Deduct one draw
            user_draw_data["points"] -= 1
            user_draw_data["used_draws"] += 1
            
            # Save updated draws data
            with open(DRAWS_FILE, "w", encoding="utf-8") as f:
                json.dump(draws_data, f, indent=4, ensure_ascii=False)
    except Exception as e:
        await message.reply_text("❌ An error occurred. Please try again later.")
        print(f"Error in /draw command: {e}")
        return
    
    # Perform the prize draw based on the prizes_config odds
    total_odds = sum(prize["odds"] for prize in prizes_config["prizes"])
    random_number = random.randint(1, total_odds)
    cumulative = 0
    for prize in prizes_config["prizes"]:
        cumulative += prize["odds"]
        if random_number <= cumulative:
            await message.reply_text(f"🎉 Congratulations! You won: {prize['name']} 🎁")
            return
    await message.reply_text("🎲 Better luck next time!")
  
def move_button_up(buttons, index):
    global admin_user_id
    the_index = int(buttpn_index[admin_user_id])
    button_index = find_index_by_id(the_index)
    button_id = broadcast_data["buttons"][button_index]
    if index == 0:
        button_id['place'] = 1
        print('-------------------------------')
        print(button_id['place'])
    else:
        buttons[index], buttons[index - 1] = buttons[index - 1], buttons[index]
        button_id['place'] = 0
        print('-------------------------------###')
        print(button_id['place'])

def move_button_down(buttons, index, merge = False):
    global admin_user_id
    the_index = int(buttpn_index[admin_user_id])
    button_index = find_index_by_id(the_index)
    button_id = broadcast_data["buttons"][button_index]
    if index == len(buttons) - 1:
        broadcast_data["buttons"][button_index - 1]['place'] = 1
        print('-------------------------------###')
        print(f"the list len is: ",len(buttons) - 1)
        print(f"the button index is: ",index)
        print(f"the button place is: ",button_id['place'])
    else:
        buttons[index], buttons[index + 1] = buttons[index + 1], buttons[index]
        print('-------------------------------')
        print(f"the list len is: ",len(buttons) - 1)
        print(f"the button index is: ",index)
        print(f"the button place is: ",button_id['place'])
        # if merge == True:
        #     # button_id['place'] = 0
        #     # print(button_id['place'])
    
def place_button_beside(buttons, index1, index2):#
    global admin_user_id
    if index1 != index2:
        button = buttons.pop(index1)
        buttons.insert(index2, button)

def create_broadcast_keyboard(buttons_list):
    global admin_user_id
    button_rows = []
    row = []
    
    for i, button in enumerate(buttons_list["buttons"]):
        row.append(InlineKeyboardButton(button["title"], url=button["url"]))
        # Group buttons in rows of 2 for example, adjust as needed
        if len(row) == 2 or i == len(buttons_list["buttons"]) - 1 :
            button_rows.append(row)
            row = []

    return InlineKeyboardMarkup(button_rows)

global event_handler_4
global event_handler_2

global edting_task_button
edting_task_button = False

@app.on_callback_query(filters.regex("show_groups_channels2"))
async def show_groups_channels(client, callback_query):
    if not is_admin(callback_query.from_user.id):
        await callback_query.answer("⚠️ You are not authorized to use this feature.", show_alert=True)
        return
        
    try:
        await callback_query.answer()
        print('Starting show_groups_channels handler')
        
        # Filter out non-chat keys and convert valid chat IDs to integers
        chat_ids = []
        for k in data.keys():
            if k.startswith('-'):
                chat_ids.append(int(k))
        
        print(f"Found chat_ids: {chat_ids}")
        
        # Create keyboard with 2 buttons per row
        buttons = []
        current_row = []
        
        for chat_id in data_store["channels"]:
            str_chat_id = str(chat_id)
            if str_chat_id in data:
                current_row.append(
                    InlineKeyboardButton(
                        data[str_chat_id]["title"], 
                        callback_data=f"show_channelel_{str_chat_id}"
                    )
                )
                
                if len(current_row) == 2:  # When we have 2 buttons, add the row
                    buttons.append(current_row)
                    current_row = []
        
        # Add any remaining buttons
        if current_row:
            buttons.append(current_row)
            
        buttons.append([InlineKeyboardButton("🔙 Back", callback_data="show_channels")])
        keyboard = InlineKeyboardMarkup(buttons)
        
        # Delete old message and send new one
        await callback_query.message.delete()
        await app.send_message(
            callback_query.message.chat.id,
            "Select a group/channel to view stats:",
            reply_markup=keyboard
        )
        
    except Exception as e:
        print(f"Error in show_groups_channels: {e}")
        try:
            await app.send_message(
                callback_query.message.chat.id,
                f"An error occurred: {str(e)}"
            )
        except Exception as send_error:
            print(f"Error sending error message: {send_error}")

@app.on_callback_query(filters.regex(r"show_channelel_(.*)"))
async def show_group_channel_stats(client, callback_query):
    if not is_admin(callback_query.from_user.id):
        await callback_query.answer("⚠️ You are not authorized to use this feature.", show_alert=True)
        return
        
    try:
        await callback_query.answer()
        chat_id = callback_query.data.split("_")[2]
        chat_data = data[chat_id]
        
        response = f"Channel Name: {chat_data['title']} ({chat_data['type']}) \n\n"

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🗑️ Delete", callback_data=f"delete2_{chat_id}")],
            [InlineKeyboardButton("🔙 Back", callback_data="show_groups_channels2")]
        ])

        await callback_query.message.delete()
        await app.send_message(callback_query.message.chat.id, response, reply_markup=keyboard)
        
    except Exception as e:
        print(f"Error showing stats: {e}")
        error_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back", callback_data="show_groups_channels")]
        ])
        await callback_query.message.edit_text(
            "⚠️ Error accessing chat statistics. Please try again or contact support.",
            reply_markup=error_keyboard
        )


@app.on_callback_query(filters.regex("show_groups_channels"))
async def show_groups_channels(client, callback_query):
    if not is_admin(callback_query.from_user.id):
        await callback_query.answer("⚠️ You are not authorized to use this feature.", show_alert=True)
        return

    try:
        await callback_query.answer()
        print("Starting show_groups_channels handler")

        # Load activity data
        if os.path.exists("activity_data.json"):
            with open("activity_data.json", "r", encoding="utf-8") as f:
                activity_data = json.load(f)
        else:
            activity_data = {}

        # Get chat IDs from the activity data
        chat_ids = list(activity_data.keys())
        print(f"Found chat_ids: {chat_ids}")

        # Create keyboard with 2 buttons per row
        buttons = []
        current_row = []

        for chat_id in chat_ids:
            chat_data_list = activity_data.get(chat_id)
            if chat_data_list:
                # Use the title from the first entry in the list
                title = chat_data_list[0].get("title", "Unknown Chat")
                current_row.append(
                    InlineKeyboardButton(
                        title,
                        callback_data=f"show_stats_{chat_id}"
                    )
                )

                if len(current_row) == 2:  # When we have 2 buttons, add the row
                    buttons.append(current_row)
                    current_row = []

        # Add any remaining buttons
        if current_row:
            buttons.append(current_row)

        # Add reset and back buttons
        buttons.append([InlineKeyboardButton("🔄 Reset All Counts", callback_data="reset_all_counts")])
        buttons.append([InlineKeyboardButton("🔙 Back", callback_data="back_to_home")])
        keyboard = InlineKeyboardMarkup(buttons)

        # Delete old message and send a new one
        await callback_query.message.delete()
        await app.send_message(
            callback_query.message.chat.id,
            "Select a group/channel to view stats:",
            reply_markup=keyboard
        )

    except Exception as e:
        print(f"Error in show_groups_channels: {e}")
        try:
            await app.send_message(
                callback_query.message.chat.id,
                f"An error occurred: {str(e)}"
            )
        except Exception as send_error:
            print(f"Error sending error message: {send_error}")

@app.on_callback_query(filters.regex(r"navigate_(\d+)"))
async def navigate_pages(client, callback_query):
    if not is_admin(callback_query.from_user.id):
        await callback_query.answer("⚠️ You are not authorized to use this feature.", show_alert=True)
        return
        
    try:
        await callback_query.answer()
        page = int(callback_query.data.split("_")[1])
        chat_ids = [int(k) for k in data.keys() if k.startswith('-')]
        chat_ids.sort()
        await callback_query.message.delete()
        await send_group_channel_list(callback_query.message.chat.id, chat_ids, page)
    except Exception as e:
        print(f"Error in navigation: {e}")
        await app.send_message(callback_query.message.chat.id, f"An error occurred: {str(e)}")

@app.on_callback_query(filters.regex(r"show_stats_(.*)"))
async def show_group_channel_stats(client, callback_query):
    if not is_admin(callback_query.from_user.id):
        await callback_query.answer("⚠️ You are not authorized to use this feature.", show_alert=True)
        return
        
    try:
        await callback_query.answer()
        chat_id = callback_query.data.split("_")[2]
        now = datetime.now(pytz.UTC)

        # Time range for the last month
        one_month_ago = now - timedelta(days=30)

        # Initialize counters
        message_count = 0
        member_activity = Counter()
        hourly_activity = Counter()
        daily_activity = Counter()
        monthly_activity = Counter()

        # Load activity data from JSON
        try:
            with open("activity_data.json", "r", encoding="utf-8") as f:
                activity_data = json.load(f)
        except FileNotFoundError:
            await app.send_message(callback_query.message.chat.id, "❌ No activity data found. The bot hasn't tracked any messages yet.")
            return

        # Check if chat_id exists in the data
        if str(chat_id) not in activity_data:
            await app.send_message(callback_query.message.chat.id, "❌ No activity data for this chat.")
            return

        # Iterate through messages for the specific chat
        for msg in activity_data[str(chat_id)]:
            msg_date = datetime.strptime(msg["date"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=pytz.UTC)
            
            if msg_date >= one_month_ago:
                message_count += 1

                # Count member activity
                member_id = msg.get("user_id")
                if member_id:
                    member_activity[member_id] += 1

                    # Track hourly and daily activity
                    hourly_activity[msg_date.hour] += 1
                    daily_activity[msg_date.weekday()] += 1
                    monthly_activity[msg_date.month] += 1

        # Get top 5 active members
        top_members = member_activity.most_common(5)

        # Find peak activity times
        peak_hour = max(hourly_activity, key=hourly_activity.get, default=0)
        peak_day = max(daily_activity, key=daily_activity.get, default=0)
        peak_month = max(monthly_activity, key=monthly_activity.get, default=0)

        # Prepare the response message
        response = f"📊 Chat Analytics for the Last Month 📊\n\n"
        response += f"Total messages: {message_count}\n\n"

        response += "👥 Top 5 Active Members:\n"
        for i, (member_id, count) in enumerate(top_members, 1):
            # Check if member_id is valid before calling get_users
            if member_id:
                try:
                    user = await client.get_users(member_id)
                    response += f"{i}. {user.first_name}: {count} messages\n"
                except Exception as e:
                    response += f"{i}. User data unavailable: {count} messages\n"
            else:
                response += f"{i}. User data unavailable: {count} messages\n"

        response += f"\n⏰ Peak Activity Times:\n"
        response += f"• {peak_hour:02d}:00\n\n"
        response += f"📅 Most Active Day:\n"
        response += f"Day: {['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'][peak_day]}\n"
        response += f"Month: {['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'][peak_month-1]}\n"
        
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🗑️ Delete", callback_data=f"delete2_{chat_id}"),
                InlineKeyboardButton("🔄 Reset Counts", callback_data=f"reset_counts_{chat_id}")
            ], 
            [InlineKeyboardButton("🔙 Back", callback_data="show_groups_channels")]
        ])

        await callback_query.message.delete()
        await app.send_message(callback_query.message.chat.id, response, reply_markup=keyboard)
        
        
    except Exception as e:
        print(f"Error showing stats: {e}")
        error_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back", callback_data="show_groups_channels")]
        ])
        await callback_query.message.edit_text(
            "⚠️ Error accessing chat statistics. Please try again or contact support.",
            reply_markup=error_keyboard
        )

@app.on_callback_query(filters.regex(r"delete2_(.*)"))
async def delete2_group_channel(client, callback_query):
    if not is_admin(callback_query.from_user.id):
        await callback_query.answer("⚠️ You are not authorized to use this feature.", show_alert=True)
        return
        
    chat_id = callback_query.data.split("_")[1]
    if chat_id in data:
        del data[chat_id]
        save_data3()
        await callback_query.message.edit_text("Group/Channel has been deleted and will be ignored in future analytics.")
    else:
        await callback_query.message.edit_text("Group/Channel not found.")

@app.on_callback_query(filters.regex("back_to_main"))
async def back_to_main(client, callback_query):
    if not is_admin(callback_query.from_user.id):
        await callback_query.answer("⚠️ You are not authorized to use this feature.", show_alert=True)
        return
        
    await callback_query.message.delete()
    await show_stats(client, callback_query.message)

async def send_group_channel_list(chat_id, chat_ids, page):
    try:
        items_per_page = 6  # Show 6 items per page (3 rows of 2)
        start = page * items_per_page
        end = start + items_per_page
        current_page_ids = chat_ids[start:end]

        buttons = []
        current_row = []
        
        for chat_id in current_page_ids:
            str_chat_id = str(chat_id)
            if str_chat_id in data:
                current_row.append(
                    InlineKeyboardButton(
                        data[str_chat_id]["title"], 
                        callback_data=f"show_stats_{str_chat_id}"
                    )
                )
                
                if len(current_row) == 2:  # When we have 2 buttons, add the row
                    buttons.append(current_row)
                    current_row = []
        
        # Add any remaining buttons
        if current_row:
            buttons.append(current_row)
            
        # Add navigation buttons
        nav_row = []
        if start > 0:
            nav_row.append(InlineKeyboardButton("⬅️ Previous", callback_data=f"navigate_{page-1}"))
        if end < len(chat_ids):
            nav_row.append(InlineKeyboardButton("➡️ Next", callback_data=f"navigate_{page+1}"))
        
        if nav_row:
            buttons.append(nav_row)
            
        buttons.append([InlineKeyboardButton("🔙 Back", callback_data="back_to_main")])
        keyboard = InlineKeyboardMarkup(buttons)
        
        await app.send_message(
            chat_id,
            "Select a group/channel to view stats:",
            reply_markup=keyboard
        )
        
    except Exception as e:
        print(f"Error in send_group_channel_list: {e}")
        await app.send_message(chat_id, f"An error occurred: {str(e)}")

#-----------------------------------------------
@app.on_callback_query(filters.regex("schedule_(.*)"))
async def schedule_type(client, callback_query: CallbackQuery):
    global the_user_choice
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Back", callback_data="back_to_scdedule_menu")]
    ])
    scheduling_type = callback_query.data.split("_")[1]
    await callback_query.answer()
    print(f"Scheduling type: {scheduling_type}")
    if scheduling_type in ["cron", "interval", "date"]:
        the_user_choice["phase"] = 1
        the_user_choice["sch_type"] = scheduling_type
        await callback_query.message.delete(callback_query.message.id)
        await callback_query.message.reply("Please provide a title for your task:", reply_markup=keyboard)

@app.on_callback_query(filters.regex("current_tasks"))
async def current_tasks(client, callback_query: CallbackQuery):
    await callback_query.answer()
    if tasks:
        task_buttons = []
        for i, title in enumerate(tasks):
            if i % 2 == 0:
                task_buttons.append([])
            task_buttons[-1].append(InlineKeyboardButton(title, callback_data=f"task_details_{title}"))
        the_user_choice["sch_type"] = None
        task_buttons.append([InlineKeyboardButton("🔙 Back", callback_data="back_to_home")])

        await callback_query.message.delete(callback_query.message.id)
        await callback_query.message.reply(
            "Select a task to view details:",
            reply_markup=InlineKeyboardMarkup(task_buttons)
        )
    else:
        await callback_query.message.delete(callback_query.message.id)
        await callback_query.message.reply("No current tasks.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="back_to_home")]]))

from datetime import datetime

from datetime import datetime, timezone

def parse_cron_expression(cron_expression):
    days_of_week = {
        '0': 'Sunday', '1': 'Monday', '2': 'Tuesday', '3': 'Wednesday',
        '4': 'Thursday', '5': 'Friday', '6': 'Saturday'
    }

    # Handle list format: ['*', '*', '*', '*', '*']
    if cron_expression.startswith("[") and cron_expression.endswith("]"):
        # Remove brackets and split by comma
        parts = [p.strip(" '") for p in cron_expression[1:-1].split(",")]
        if len(parts) == 5:
            minute, hour, day, month, day_of_week = parts
        else:
            # fallback to all wildcards
            minute = hour = day = month = day_of_week = "*"
    else:
        # Handle string format: minute='*', hour='*', ...
        cron_expression = cron_expression.strip('cron[').strip(']')
        parts = cron_expression.split(', ')
        cron_parts = {
            'minute': '*',
            'hour': '*',
            'day': '*',
            'month': '*',
            'day_of_week': '*'
        }
        for part in parts:
            if '=' in part:
                key, value = part.split('=')
                cron_parts[key.strip()] = value.strip().strip("'")
        minute = cron_parts['minute']
        hour = cron_parts['hour']
        day = cron_parts['day']
        month = cron_parts['month']
        day_of_week = cron_parts['day_of_week']

    # Construct the human-readable description (same as before)
    description = []
    if day == '*' and month == '*' and day_of_week == '*':
        description.append("Every day")
    elif day_of_week != '*':
        days = day_of_week.split(',')
        day_names = [days_of_week.get(day, day) for day in days]
        description.append(f"Every {' and '.join(day_names)}")
    elif day != '*':
        days = day.split(',')
        description.append(f"on {' and '.join(days)}")

    if hour != '*' and minute != '*':
        hours = hour.split(',')
        times = [f"{h}:{minute.zfill(2)}" for h in hours]
        description.append(f"at {' and '.join(times)}")

    if month != '*':
        description.append(f"in month {month}")

    if minute.startswith('*/'):
        interval = minute[2:]
        description.append(f"Every {interval} minute(s)")

    return ' '.join(description)

# Ensure the task_details function uses the updated parse_cron_expression
@app.on_callback_query(filters.regex(r"task_details_(.*)"))
async def task_details(client, callback_query: CallbackQuery):
    task_title = callback_query.data.split("_")[2]
    await callback_query.answer()
    if task_title in tasks:
        job = tasks[task_title]
        missed_status = ""
        the_user_choice["sch_type"] = None
        if job.next_run_time:
            next_run_time = job.next_run_time.astimezone(timezone.utc)
            current_time = datetime.now(timezone.utc)
            if next_run_time < current_time:
                missed_status = "       (missed while offline)"
        
        # Use the parse_cron_expression function to get a user-friendly description
        if isinstance(job.trigger, CronTrigger):
            cron_description = parse_cron_expression(str(job.trigger))
        else:
            cron_description = str(job.trigger)

        task_info = f"Task: {task_title}{missed_status}\nTrigger: {cron_description}\nNext Run: {job.next_run_time}"
        await callback_query.message.delete(callback_query.message.id)
        if isinstance(job.trigger, DateTrigger):
            await callback_query.message.reply(
                task_info,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("✏️ Edit", callback_data=f"edit_task-{task_title}"),
                    InlineKeyboardButton("🗑️ Delete", callback_data=f"delete_{task_title}")],
                    [InlineKeyboardButton("⏸️ Pause", callback_data=f"pause_{task_title}"),
                    InlineKeyboardButton("▶️ Resume", callback_data=f"resume_{task_title}")],
                    [InlineKeyboardButton("🚀 Send Now", callback_data=f"send_now-{task_title}")],
                    [InlineKeyboardButton("🚀 Send Now & 🗑️ Delete", callback_data=f"send_now_delete-{task_title}")],
                    [InlineKeyboardButton("🔙 Back", callback_data="current_tasks")]
                ])
            )
        else:
            await callback_query.message.reply(
                task_info,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("✏️ Edit", callback_data=f"edit_task-{task_title}"),
                    InlineKeyboardButton("🗑️ Delete", callback_data=f"delete_{task_title}")],
                    [InlineKeyboardButton("⏸️ Pause", callback_data=f"pause_{task_title}"),
                    InlineKeyboardButton("▶️ Resume", callback_data=f"resume_{task_title}")],
                    [InlineKeyboardButton("🔙 Back", callback_data="current_tasks")]
                ])
            )
    else:
        await callback_query.message.reply("Task not found.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="current_tasks")]]))


@app.on_callback_query(filters.regex(r"delete_(.*)"))
async def delete_task(client, callback_query: CallbackQuery):
    print('Tasks list', tasks)
    task_title = callback_query.data.split("_")[1]
    print('Task title 2', task_title)
    await callback_query.answer()
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🏠 Home", callback_data="back_to_home"), 
        InlineKeyboardButton("📋 Current Tasks", callback_data="current_tasks")],
        [InlineKeyboardButton("📅 Schedule another Task", callback_data="broadcast")]
    ])
    try:
        if task_title in tasks:
            job = tasks[task_title]
            if job.next_run_time is not None:  # Check if the job is still scheduled
                job.remove()
                del tasks[task_title]
                await callback_query.message.delete(callback_query.message.id)
                await callback_query.message.reply(f"Task '{task_title}' has been deleted.", reply_markup=keyboard)
                shutdown()
            else:
                del tasks[task_title]  # Remove from the dictionary if it's not in the scheduler
                await callback_query.message.reply(f"Task '{task_title}' was already executed and removed.", reply_markup=keyboard)
        else:
            await callback_query.message.reply("Task not found.")
    except Exception as e:
        print(f"Error deleting task: {e}")
        try:
            if task_title in tasks:
                del tasks[task_title]
                await callback_query.message.reply(f"Task '{task_title}' has been deleted from the tasks list.", reply_markup=keyboard)
                shutdown()
            else:
                await callback_query.message.reply(f"Task '{task_title}' not found in the tasks list.", reply_markup=keyboard)
        except Exception as e:
            print(f"Error removing task from tasks list: {e}")
            await callback_query.message.reply("An error occurred while trying to delete the task.", reply_markup=keyboard)

async def broadcast_to_channels(client, admin_id, message_id, data_type, buttons_data, is_media_group=False, selected_channels=data_store["channels"]):
    successful = []
    failed = []
    
    for channel_id in selected_channels:
        if selected_channels[channel_id].get("selected", True):
            try:
                # First, forward the original message to preserve premium emojis
                if is_media_group:    
                    await client.copy_media_group(channel_id, admin_id, int(message_id))  # Convert to int
                else:
                    await client.forward_messages(channel_id, admin_id, int(message_id))  # Convert to int
                
                # Then, if there are buttons, send them in a separate message
                if data_type == "with_button":
                    keyboard = create_broadcast_keyboard(buttons_data)
                    await client.send_message(
                        channel_id,
                        "Or Click below 👇",
                        reply_markup=keyboard
                    )
                successful.append(channel_id)
            except Exception as e:
                failed.append((channel_id, str(e)))
                print(f"Error broadcasting to {channel_id}: {e}")
                continue

    

@app.on_callback_query(filters.regex(r"send_now-(.*)"))
async def send_now(client, callback_query: CallbackQuery):
    task_title = callback_query.data.split("-")[1]
    admin_id = tasks[task_title].args[1]  
    message = tasks[task_title].args[2]
    data_type = tasks[task_title].args[3]
    buttons_data = tasks[task_title].args[4]
    media_group = tasks[task_title].args[5]  # True or False
    print('task_title:', task_title)
    print('Admin ID:', admin_id)
    # print('Message:', message)
    print('Data type:', data_type)
    if data_type == "with_button":
        keyboard = create_broadcast_keyboard(buttons_data)
        for channel_id in data_store["channels"]:
            if data_store["channels"][channel_id].get("selected", True):  # Only send to selected channels
                try:
                    if media_group == True:    
                        await app.copy_media_group(channel_id, admin_user_id, message)
                        await app.send_message(channel_id, ":", reply_markup=keyboard)
                    else:    
                        await app.forward_messages(channel_id, admin_user_id, message, reply_markup=keyboard)
                except errors.UserIsBlocked:
                    print(f"Channel {channel_id} has blocked the bot.")
                except errors.PeerIdInvalid:
                    print(f"Invalid Channel ID: {channel_id}")
    else:
        for channel_id in data_store["channels"]:
            if data_store["channels"][channel_id].get("selected", True):  # Only send to selected channels
                try:
                    if media_group == True:    
                        await app.copy_media_group(channel_id, admin_user_id, message)
                    else:    
                        await app.forward_messages(channel_id, admin_user_id, message)
                except errors.UserIsBlocked:
                    print(f"Channel {channel_id} has blocked the bot.")
                except errors.PeerIdInvalid:
                    print(f"Invalid Channel ID: {channel_id}")

@app.on_callback_query(filters.regex(r"send_now_delete-(.*)"))
async def send_now(client, callback_query: CallbackQuery):
    task_title = callback_query.data.split("-")[1]
    admin_id = tasks[task_title].args[1] 
    message = tasks[task_title].args[2]
    data_type = tasks[task_title].args[3]
    buttons_data = tasks[task_title].args[4]
    media_group = tasks[task_title].args[5]  # True or False
    print('task_title:', task_title)
    print('Admin ID:', admin_id)
    print('Message:', message)
    print('Data type:', data_type)
    if data_type == "with_button":
        keyboard = create_broadcast_keyboard(buttons_data)
        for channel_id in data_store["channels"]:
            if data_store["channels"][channel_id].get("selected", True):  # Only send to selected channels
                try:
                    if media_group == True:    
                        await app.copy_media_group(channel_id, admin_user_id, message)
                        await app.send_message(channel_id, ":", reply_markup=keyboard)
                    else:    
                        await app.forward_messages(channel_id, admin_user_id, message, reply_markup=keyboard)
                except errors.UserIsBlocked:
                    print(f"Channel {channel_id} has blocked the bot.")
                except errors.PeerIdInvalid:
                    print(f"Invalid Channel ID: {channel_id}")
    else:
        for channel_id in data_store["channels"]:
            if data_store["channels"][channel_id].get("selected", True):  # Only send to selected channels
                try:
                    if media_group == True:    
                        await app.copy_media_group(channel_id, admin_user_id, message)
                    else:    
                        await app.forward_messages(channel_id, admin_user_id, message)
                except errors.UserIsBlocked:
                    print(f"Channel {channel_id} has blocked the bot.")
                except errors.PeerIdInvalid:
                    print(f"Invalid Channel ID: {channel_id}")
                
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🏠 Home", callback_data="back_to_home"), 
        InlineKeyboardButton("📋 Current Tasks", callback_data="current_tasks")],
        [InlineKeyboardButton("📅 Schedule another Task", callback_data="broadcast")]
    ])
    job = tasks[task_title]
    if job.next_run_time is not None:  # Check if the job is still scheduled
        job.remove()
        del tasks[task_title]
        await callback_query.message.reply(f"Task '{task_title}' has been deleted.", reply_markup=keyboard)

@app.on_callback_query(filters.regex(r"edit_task-(.*)"))
async def edit_task(client, callback_query: CallbackQuery):
    task_title = callback_query.data.split("-")[1]
    global edting_task_button
    edting_task_button = False
    the_user_choice["editing_buttons"] = False
    the_user_choice["sch_type"] = None
    await callback_query.answer()
    if task_title in tasks:
        job = tasks[task_title]
        task_info = f"Task: **{task_title}**\nTrigger: {job.trigger}\nNext Run: {job.next_run_time}"
        buttons_data = job.args[4]
        await callback_query.message.delete(callback_query.message.id)
        if buttons_data["type"] == "with_button":
            keybord = InlineKeyboardMarkup(
                    [
                        [InlineKeyboardButton("✏️ Edit Title", callback_data=f"edit_task_title-{task_title}"), 
                        InlineKeyboardButton("📝 Edit Message Content", callback_data=f"edit_task_message-{task_title}")],
                        [InlineKeyboardButton("⚙️ Edit Buttons", callback_data=f"edit_task_buttons-{task_title}")],
                        [InlineKeyboardButton("🔙 Back", callback_data=f"task_details_{task_title}")]
                    ]
                )
        else:
            keybord = InlineKeyboardMarkup(
                    [
                        [InlineKeyboardButton("✏️ Edit Title", callback_data=f"edit_task_title-{task_title}"), 
                        InlineKeyboardButton("📝 Edit Message Content", callback_data=f"edit_task_message-{task_title}")],
                        [InlineKeyboardButton("🔙 Back", callback_data=f"task_details_{task_title}")]
                    ]
                )
        await callback_query.message.reply(
            task_info,
            reply_markup=keybord
        )
        
    else:
        await callback_query.message.reply("Task not found.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="current_tasks")]]))

@app.on_callback_query(filters.regex(r"edit_task_buttons-(.*)"))
async def edit_task(client, callback_query: CallbackQuery):
    task_title = callback_query.data.split("-")[1]
    await callback_query.answer()
    global edting_task_button
    edting_task_button = False 
    edting_task_button = True
    admin_id = tasks[task_title].args[1]  
    message_id = tasks[task_title].args[2]
    data_type = tasks[task_title].args[3]
    buttons_data = tasks[task_title].args[4]
    print('task_title:', task_title)
    print('Admin ID:', admin_id)
    # print('Message:', message)
    print('Data type:', data_type)
    broadcast_data = copy.deepcopy(buttons_data)
    broadcast_data["message"] = message_id
    keyboard = create_broadcast_keyboard(broadcast_data)
    await client.send_message(callback_query.message.chat.id, "This is a preview of your message. 👇")
    await client.forward_messages(callback_query.message.chat.id, callback_query.message.chat.id, broadcast_data["message"], reply_markup=keyboard)
    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(f"Edit {button['id']}: {button['title']}", callback_data=f'edit_button_{button["id"]}')for button in broadcast_data["buttons"]],
            [InlineKeyboardButton("Add New Button ➕", callback_data='add_new_button')],
            [InlineKeyboardButton("Back ↩️", callback_data=f'edit_task-{task_title}')],
        ]
    )
    the_user_choice["task_title"] = task_title
    the_user_choice["editing_buttons"] = True
    await client.send_message(callback_query.message.chat.id, "Select a button to edit:", reply_markup=keyboard)

@app.on_callback_query(filters.regex(r"edit_task_title-(.*)"))
async def edit_task(client, callback_query: CallbackQuery):
    task_title = callback_query.data.split("-")[1]
    await callback_query.answer()
    if task_title in tasks:
        await callback_query.message.delete(callback_query.message.id)
        await callback_query.message.reply(f"The current title is: **{task_title}**:")
        await callback_query.message.reply(
            "Send me the new title for this task or click back to return.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data=f"edit_task-{task_title}")]])
        )
        
        the_user_choice["task_title"] = task_title
        the_user_choice["sch_type"] = "edit_title"
    else:
        await callback_query.message.reply("Task not found.")

@app.on_callback_query(filters.regex(r"edit_task_message-(.*)"))
async def edit_task(client, callback_query: CallbackQuery):
    task_title = callback_query.data.split("-")[1]
    media_group = tasks[task_title].args[5]
    await callback_query.answer()
    if task_title in tasks:
        await callback_query.message.reply(f"Current message for task **{task_title}**:") 
        buttons_data = tasks[task_title].args[4]
        if buttons_data["type"] == "with_button":
            keyboard = create_broadcast_keyboard(buttons_data)
            await app.forward_messages(callback_query.message.chat.id, callback_query.message.chat.id, tasks[task_title].args[2], reply_markup=keyboard)
            await callback_query.message.reply("Send me the new message for this task or click back to return.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data=f"edit_task-{task_title}")]]))
        else:
            if media_group == True:
                await app.copy_media_group(callback_query.message.chat.id, callback_query.message.chat.id, tasks[task_title].args[2])
            else:
                await app.forward_messages(callback_query.message.chat.id, callback_query.message.chat.id, tasks[task_title].args[2])
            await callback_query.message.reply("Send me the new message for this task or click back to return.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data=f"edit_task-{task_title}")]]))
        
        the_user_choice["task_title"] = task_title
        the_user_choice["sch_type"] = "edit_message"
    else:
        await callback_query.message.reply("Task not found.")

@app.on_callback_query(filters.regex(r"pause_(.*)"))
async def pause_task(client, callback_query: CallbackQuery):
    task_title = callback_query.data.split("_")[1]
    await callback_query.answer()
    if task_title in tasks:
        tasks[task_title].pause()
        await callback_query.message.reply(f"Task '{task_title}' has been paused.")
        shutdown()
    else:
        await callback_query.message.reply("Task not found.")

@app.on_callback_query(filters.regex(r"resume_(.*)"))
async def resume_task(client, callback_query: CallbackQuery):
    task_title = callback_query.data.split("_")[1]
    await callback_query.answer()
    if task_title in tasks:
        tasks[task_title].resume()
        await callback_query.message.reply(f"Task '{task_title}' has been resumed.")
        shutdown()
    else:
        await callback_query.message.reply("Task not found.")

@app.on_callback_query(filters.regex("cancel"))
async def cancel_menu(client, callback_query: CallbackQuery):
    await callback_query.answer()
    await callback_query.message.reply("Use /start to schedule a new task or view current tasks.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="back_to_home")]]))
@app.on_callback_query(filters.regex("help"))
async def help_menu(client, callback_query: CallbackQuery):
    await callback_query.answer()
    help_text = (
        '''
🤖 **Task Scheduler Bot - Complete Guide**

Welcome to the Task Scheduler Bot! Here's a comprehensive guide on how to use all features:

📱 **Main Features:**

1. **Message Scheduling** 📅
   - Schedule messages with or without buttons
   - Support for text, media, and media groups
   - Round video converter functionality
   - Three scheduling methods available

2. **Task Management** 📋
   - View all scheduled tasks
   - Edit task details (title/content/buttons)
   - Pause/Resume scheduling
   - Delete tasks
   - Send scheduled messages immediately

3. **Admin Controls** 👑
   - Manage admin access
   - Control channels/groups
   - View detailed analytics

📝 **Scheduling Methods:**

1. **Cron Schedule** ⏰
   Format: minute-hour-day-month-day_of_week
   
   Examples:
   - `30 10 * * 5` = Every Friday at 10:30 AM
   - `*/5 * * * *` = Every 5 minutes
   - `0 9 * * 1,5` = Every Monday and Friday at 9:00 AM
   
   Days: 0/7=Sun, 1=Mon, 2=Tue, 3=Wed, 4=Thu, 5=Fri, 6=Sat

2. **Interval Schedule** 🔄
   Format: Number of seconds
   
   Examples:
   - `3600` = Every hour
   - `86400` = Every day
   - `1800` = Every 30 minutes

3. **Date Schedule** 📆
   Format: YYYY-MM-DD HH:MM:SS
   
   Examples:
   - `2024-12-25 09:00:00` = December 25, 2024 at 9 AM
   - `2024-01-01 00:00:00` = New Year 2024 at midnight

🎛️ **Button Management:**
- Add unlimited buttons to messages
- Edit button text and URLs
- Arrange button layout
- Remove or modify existing buttons

📊 **Analytics Features:**
- Message count tracking
- Member activity monitoring
- Peak activity time analysis
- Daily/Monthly statistics
- Group/Channel performance metrics

🔍 **Task Operations:**
1. View tasks: Click "📋 Current Tasks"
2. Edit task: Select task → "✏️ Edit"
3. Pause/Resume: Use respective buttons on task view
4. Delete: Select task → "🗑️ Delete"
5. Send Now: Select task → "🚀 Send Now"

⚙️ **Additional Features:**
- Media group support
- Round video conversion
- Multiple button layouts
- Instant broadcasting
- Task scheduling queue

Need more help? Contact me! https://t.me/mrnobody2007
        '''
    )
    await callback_query.message.delete(callback_query.message.id)
    await callback_query.message.reply(help_text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="back_to_home")]]))

@app.on_callback_query(filters.regex("back_to_home"))
async def back_to_home(client, callback_query):
    the_user_choice["broadcasting_now"] = False  # Reset broadcasting mode
    await callback_query.answer()
    await callback_query.message.delete(callback_query.message.id)
    await start(client, callback_query.message)

async def show_channels(client, callback_query):
    try:
        buttons = []
        current_row = []
        
        for chat_id in data_store["channels"]:
            try:
                channel_name = data_store["channels"][chat_id].get("name")
                is_selected = data_store["channels"][chat_id].get("selected", True)
                toggle_symbol = "✅" if is_selected else "❌"
                current_row.append(
                    InlineKeyboardButton(f"{toggle_symbol} {channel_name}", 
                        callback_data=f"2toggle_channel1_{chat_id}")
                )
                if len(current_row) == 2:
                    buttons.append(current_row)
                    current_row = []
            except Exception as e:
                print(f"Error getting chat info: {e}")
                continue
        
        if current_row:
            buttons.append(current_row)
        
        buttons.append([
            InlineKeyboardButton("Select All ☑", callback_data="select_all_channels"),
            InlineKeyboardButton("Deselect All ❌", callback_data="deselect_all_channels")
        ])
        buttons.append([
            InlineKeyboardButton("🗑️ Delete Channels", callback_data="channels_list_remover")
        ])
        buttons.append([InlineKeyboardButton("Back 🔙", callback_data='back_to_home')])
        
        keyboard = InlineKeyboardMarkup(buttons)
        await callback_query.message.edit_text(
            "Select channels to broadcast to:\n(✅ = Selected, ❌ = Not Selected)", 
            reply_markup=keyboard
        )
    except Exception as e:
        print(f"Error in show_channels: {e}")
    
@app.on_callback_query(filters.regex("^reset_all_counts$"))
async def reset_all_counts(client, callback_query):
    if not is_admin(callback_query.from_user.id):
        await callback_query.answer("⚠️ You are not authorized to use this feature.", show_alert=True)
        return
    
    try:
        # Load activity data
        activity_data = load_activity_data()
        
        # Reset counts for all channels/groups
        for chat_id in activity_data:
            activity_data[chat_id] = []  # Clear all message data
        
        # Save the updated activity data
        with open("activity_data.json", "w", encoding="utf-8") as f:
            json.dump(activity_data, f, indent=4, ensure_ascii=False)
        
        await callback_query.answer("All message counts have been reset to 0.", show_alert=True)
        await show_channels(client, callback_query)  # Refresh the channels list
    except Exception as e:
        print(f"Error resetting all counts: {e}")
        await callback_query.answer("An error occurred while resetting counts.", show_alert=True)    

@app.on_callback_query(filters.regex(r"reset_counts_(.*)"))
async def reset_counts(client, callback_query):
    if not is_admin(callback_query.from_user.id):
        await callback_query.answer("⚠️ You are not authorized to use this feature.", show_alert=True)
        return
    
    try:
        chat_id = callback_query.data.split("_")[2]
        
        # Load activity data
        activity_data = load_activity_data()
        
        # Reset counts for the specific channel/group
        if chat_id in activity_data:
            activity_data[chat_id] = []  # Clear all message data for this channel/group
        
        # Save the updated activity data
        with open("activity_data.json", "w", encoding="utf-8") as f:
            json.dump(activity_data, f, indent=4, ensure_ascii=False)
        
        await callback_query.answer(f"Message counts for this channel/group have been reset to 0.", show_alert=True)
        await show_group_channel_stats(client, callback_query)  # Refresh the stats view
    except Exception as e:
        print(f"Error resetting counts: {e}")
        await callback_query.answer("An error occurred while resetting counts.", show_alert=True)
        
@app.on_callback_query(filters.regex("^show_channels$"))
async def show_channels_handler(client, callback_query):
    await show_channels(client, callback_query)

@app.on_callback_query(filters.regex("^confirm_broadcast_now2"))
async def confirm_broadcast_now(client, callback_query):
    global broadcast_data
    the_user_choice["sch_type"] = None
    the_user_choice["phase"] = 1
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🕒 Cron", callback_data="schedule_cron"),
        InlineKeyboardButton("⏲️ Interval", callback_data="schedule_interval"),
        InlineKeyboardButton("📅 Date", callback_data="schedule_date")],
        [InlineKeyboardButton("🔙 Back", callback_data="back_to_pre")]
    ])
    await callback_query.message.edit_text("Choose a scheduling type:", reply_markup=keyboard)


@app.on_callback_query(filters.regex("^confirm_broadcast_now"))
async def confirm_broadcast_now(client, callback_query):
    global broadcast_data
    task_buttons = copy.deepcopy(broadcast_data)
    admin_id = callback_query.message.chat.id
    data_type = broadcast_data["type"]
    buttons_data = task_buttons
    
    successful_broadcasts = []
    failed_broadcasts = []
    
    for channel_id in data_store["channels"]:
        if data_store["channels"][channel_id].get("selected", True):
            try:
                # First, forward the original message to preserve premium emojis
                if the_user_choice["media_group"] == True:    
                    await app.copy_media_group(channel_id, admin_user_id, int(broadcast_data["message"]))  # Convert to int
                else:
                    await app.forward_messages(channel_id, admin_user_id, int(broadcast_data["message"]))  # Convert to int
                
                # Then, if there are buttons, send them in a separate message
                if data_type == "with_button":
                    keyboard = create_broadcast_keyboard(buttons_data)
                    await app.send_message(
                        channel_id,
                        "Or Click below 👇",
                        reply_markup=keyboard
                    )
                successful_broadcasts.append(channel_id)
            except Exception as e:
                failed_broadcasts.append((channel_id, str(e)))
                print(f"Error broadcasting to {channel_id}: {e}")

    # Prepare success message
    channel_list = "Broadcast Status:\n\n"
    if successful_broadcasts:
        channel_list += "Successfully sent to:\n"
        for channel_id in successful_broadcasts:
            try:
                chat = await app.get_chat(int(channel_id))
                channel_name = chat.title or chat.first_name or channel_id
                channel_list += f"✅ {channel_name}\n"
            except Exception:
                channel_list += f"✅ Channel {channel_id}\n"

    if failed_broadcasts:
        channel_list += "\nFailed to send to:\n"
        for channel_id, error in failed_broadcasts:
            channel_list += f"❌ Channel {channel_id} (Error: {error})\n"

    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("🔙 Back to Home", callback_data="back_to_home")
    ]])
    
    await callback_query.message.edit_text(channel_list, reply_markup=keyboard)


    # Add new handlers for toggle actions

@app.on_callback_query(filters.regex(r"^23toggle_channel_(.+)"))
async def toggle_channel_selection(client, callback_query):
    channel_id = callback_query.data.split("_")[2]
    
    # Toggle the selection
    current_selection = data_store["channels"][channel_id].get("selected", True)
    data_store["channels"][channel_id]["selected"] = not current_selection
    save_data(data_store)
    
    # Recreate the channel selection keyboard with updated status
    buttons = []
    for ch_id in data_store["channels"]:
        try:
            channel_name = data_store["channels"][ch_id].get("name")
            is_selected = data_store["channels"][ch_id].get("selected", True)
            status = "✅" if is_selected else "❌"
            buttons.append([InlineKeyboardButton(
                f"{status} {channel_name}",
                callback_data=f"23toggle_channel_{ch_id}"
            )])
        except Exception as e:
            print(f"Error getting chat info for {ch_id}: {e}")
            continue

    buttons.append([InlineKeyboardButton("☑ Confirm & Save", callback_data="confirm_broadcast_now2")])
    buttons.append([InlineKeyboardButton("🔙 Back", callback_data="back_to_home")])

    # Update the message in place instead of sending a new one
    try:
        await callback_query.message.edit_text(
            "Select channels to broadcast to:\n"
            "✅ - Selected\n"
            "❌ - Not selected",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    except MessageNotModified:
        # Message content is the same, ignore this error
        pass
    
@app.on_callback_query(filters.regex(r"^toggle_channel_(.+)"))
async def toggle_channel_selection(client, callback_query):
    channel_id = callback_query.data.split("_")[2]
    
    # Toggle the selection
    current_selection = data_store["channels"][channel_id].get("selected", True)
    data_store["channels"][channel_id]["selected"] = not current_selection
    save_data(data_store)
    
    # Recreate the channel selection keyboard with updated status
    buttons = []
    for ch_id in data_store["channels"]:
        try:
            channel_name = data_store["channels"][ch_id].get("name")
            is_selected = data_store["channels"][ch_id].get("selected", True)
            status = "✅" if is_selected else "❌"
            buttons.append([InlineKeyboardButton(
                f"{status} {channel_name}",
                callback_data=f"toggle_channel_{ch_id}"
            )])
        except Exception as e:
            print(f"Error getting chat info for {ch_id}: {e}")
            continue

    buttons.append([InlineKeyboardButton("☑ Confirm & Send Now", callback_data="confirm_broadcast_now")])
    buttons.append([InlineKeyboardButton("🔙 Back", callback_data="back_to_home")])

    # Update the message in place instead of sending a new one
    try:
        await callback_query.message.edit_text(
            "Select channels to broadcast to:\n"
            "✅ - Selected\n"
            "❌ - Not selected",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    except MessageNotModified:
        # Message content is the same, ignore this error
        pass

@app.on_callback_query(filters.regex(r"^2toggle_channel1_(.+)"))
async def toggle_channel_selection(client, callback_query):
    chat_id = callback_query.data.split("_")[2]
    if chat_id in data_store["channels"]:
        # Toggle the selected state
        current_state = data_store["channels"][chat_id].get("selected", True)
        data_store["channels"][chat_id]["selected"] = not current_state
        save_data(data_store)
        # Refresh the channels list
        await show_channels(client, callback_query)

@app.on_callback_query(filters.regex("^select_all_channels$"))
async def select_all_channels(client, callback_query):
    for chat_id in data_store["channels"]:
        data_store["channels"][chat_id]["selected"] = True
    save_data(data_store)
    await show_channels(client, callback_query)

@app.on_callback_query(filters.regex("^deselect_all_channels$"))
async def deselect_all_channels(client, callback_query):
    for chat_id in data_store["channels"]:
        data_store["channels"][chat_id]["selected"] = False
    save_data(data_store)
    await show_channels(client, callback_query)
loaded_tasks = load_tasks()

for task_title, task_info in loaded_tasks.items():
    trigger_type = task_info['trigger_type']
    trigger_args = task_info['trigger_args']
    args = task_info['args']

    # Replace the first argument with `app`
    args[0] = app

    print(trigger_args)
    if trigger_type == 'cron':
        def parse_cron_list(cron_string):
            # Extract the list of values from the cron string
            values = cron_string.strip('cron[]').split(', ')

            # Assign the values to individual variables
            minute, hour, day, month, day_of_week = values

            return minute, hour, day, month, day_of_week
        try:
            minute, hour, day, month, day_of_week = parse_cron_list(trigger_args)
        except:
            minute, hour, day, month, day_of_week = trigger_args
        
        trigger = CronTrigger(
                    minute=minute if minute != '*' else None,
                    hour=hour if hour != '*' else None,
                    day=day if day != '*' else None,
                    month=month if month != '*' else None,
                    day_of_week=day_of_week if day_of_week != '*' else None
                )
    elif trigger_type == 'interval':
        trigger = IntervalTrigger(**trigger_args)
    elif trigger_type == 'date':
        trigger = DateTrigger(run_date=datetime.fromisoformat(trigger_args['run_date']))
    else:
        continue

    job = scheduler.add_job(sync_broadcast_to_channels, trigger, args=args, id=task_title, max_instances=2)
    tasks[task_title] = job
    rescheduled_task_names.append(task_title)

#Sweepstakes game section
#==================================================================================

@app.on_callback_query(filters.regex("manage_sweepstakes"))
async def manage_sweepstakes_callback(client, callback_query):
    await show_prizes(callback_query)

@app.on_callback_query(filters.regex("back_to_game_manager"))
async def back_to_game_manager(client, callback_query):
    try:
        client.remove_handler(handler_update2)
    except ValueError:
        pass
    except:
        pass
    try:
        client.remove_handler(handler_update)
    except ValueError:
        pass
    except:
        pass
        
    await show_prizes(callback_query)

async def show_prizes(callback_query):
    keyboard = []
    for index, prize in enumerate(prizes_config["prizes"]):
        keyboard.append([
            InlineKeyboardButton(f"✏️ Edit {prize['name']}", callback_data=f"edit_prize_{index}"),
            InlineKeyboardButton("❌ Delete", callback_data=f"delete_prize_{index}")
        ])
    keyboard.append([InlineKeyboardButton("➕ Add Prize", callback_data="add_prize")])
    keyboard.append([InlineKeyboardButton("🔄 Reset all draws", callback_data="reset_draws")])
    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="back")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await callback_query.message.edit_text("🎁 Sweepstakes Prizes:", reply_markup=reply_markup)

@app.on_callback_query(filters.regex("^edit_prize_"))
async def edit_prize_callback(client, callback_query):
    global handler_update2
    data = callback_query.data  # format: "edit_prize_<index>"
    prize_index = int(data.split("_")[-1])
    prize = prizes_config["prizes"][prize_index]
    Keyboard = [
        [InlineKeyboardButton("🔙 Back", callback_data="back_to_game_manager")]
    ]
    await callback_query.message.reply_text(
        f"Editing Prize: {prize['name']}\nCurrent Odds: {prize['odds']}\n\n"
        "Send the updated prize in the format: `Prize Name | Odds`", reply_markup=Keyboard)
    
    async def update_prize_handler(client, message):
        try:
            name, odds = message.text.split("|")
            prizes_config["prizes"][prize_index] = {"name": name.strip(), "odds": int(odds.strip())}
            save_prizes_config()
            await message.reply_text("✅ Prize updated successfully!")
            global handler_update2
            client.remove_handler(handler_update2)
        except Exception as e:
            await message.reply_text("❌ Invalid format. Please use `Prize Name | Odds`.")
    
    handler_update2 = MessageHandler(update_prize_handler, filters.text & filters.user(callback_query.from_user.id))
    client.add_handler(handler_update2)

@app.on_callback_query(filters.regex("^delete_prize_"))
async def delete_prize_callback(client, callback_query):
    data = callback_query.data
    prize_index = int(data.split("_")[-1])
    del prizes_config["prizes"][prize_index]
    save_prizes_config()
    await callback_query.answer("Prize deleted successfully!", show_alert=True)
    await show_prizes(callback_query)

@app.on_callback_query(filters.regex("^add_prize$"))
async def add_prize_callback(client, callback_query):
    Keyboard = [
        [InlineKeyboardButton("🔙 Back", callback_data="back_to_game_manager")]
    ]
    await callback_query.message.reply_text("Send the new prize in the format: `Prize Name | Odds`", reply_markup=Keyboard)
    global handler_update
    handler_update = MessageHandler(add_prize_handler, filters.text & filters.user(callback_query.from_user.id))
    client.add_handler(handler_update)

async def add_prize_handler(client, message):
    global handler_update
    try:
        name, odds = message.text.split("|")
        prizes_config["prizes"].append({"name": name.strip(), "odds": int(odds.strip())})
        save_prizes_config()
        await message.reply_text("✅ New prize added successfully!")
        client.remove_handler(handler_update)
    except Exception as e:
        await message.reply_text("❌ Invalid format. Please use `Prize Name | Odds`.")

@app.on_callback_query(filters.regex("^reset_draws$"))
async def reset_draws(client, message):
    try:
        with open(DRAWS_FILE, "r", encoding="utf-8") as f:
            draws_data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        draws_data = {}
        
    
    for chat in draws_data:
        for user in draws_data[chat]:
            draws_data[chat][user] = {"points": 0, "draws": 0, "used_draws": 0}
    
    with open(DRAWS_FILE, "w", encoding="utf-8") as f:
        json.dump(draws_data, f, indent=4, ensure_ascii=False)
    keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="back")]]
    markup = InlineKeyboardMarkup(keyboard)
    await message.message.edit_text("✅ All draws have been reset for the month!", reply_markup=markup)
# ---------------   ----------------

@app.on_callback_query(filters.regex("channels_list_remover"))
async def show_delete_channels_list(client, callback_query):
    if not is_admin(callback_query.from_user.id):
        await callback_query.answer("⚠️ You are not authorized to use this feature.", show_alert=True)
        return
        
    buttons = []
    current_row = []
    
    for channel_id in data_store["channels"]:
        try:
            channel_name = data_store["channels"][channel_id].get("name")
            current_row.append(
                InlineKeyboardButton(
                    f"🗑️ {channel_name}", 
                    callback_data=f"confirm_remove_{channel_id}"
                )
            )
            
            if len(current_row) == 2:  # Two buttons per row
                buttons.append(current_row)
                current_row = []
                
        except Exception as e:
            print(f"Error getting chat info for {channel_id}: {e}")
            continue
    
    if current_row:  # Add any remaining buttons
        buttons.append(current_row)
        
    buttons.append([InlineKeyboardButton("🔙 Back", callback_data="show_channels")])
    
    await callback_query.message.edit_text(
        "Select a channel/group to delete:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

@app.on_callback_query(filters.regex(r"confirm_remove_(.*)"))
async def confirm_channel_deletion(client, callback_query):
    if not is_admin(callback_query.from_user.id):
        await callback_query.answer("⚠️ You are not authorized to use this feature.", show_alert=True)
        return
        
    channel_id = callback_query.data.split("_")[-1]
    try:
        channel_name = data_store["channels"][channel_id].get("name")
        
        buttons = [
            [
                InlineKeyboardButton("✅ Delete", callback_data=f"remove_confirmed_{channel_id}"),
                InlineKeyboardButton("❌ Cancel", callback_data="channels_list_remover")
            ]
        ]
        
        await callback_query.message.edit_text(
            f"Are you sure you want to delete {channel_name}?",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    except Exception as e:
        print(f"Error in confirm_deletion: {e}")
        await callback_query.answer("Error getting channel information", show_alert=True)

@app.on_callback_query(filters.regex(r"remove_confirmed_(.*)"))
async def delete_channel_confirmed(client, callback_query):
    if not is_admin(callback_query.from_user.id):
        await callback_query.answer("⚠️ You are not authorized to use this feature.", show_alert=True)
        return
        
    channel_id = callback_query.data.split("_")[-1]
    try:
        channel_name = data_store["channels"][channel_id].get("name", "Unknown Channel")
        del data_store["channels"][channel_id]
        save_data(data_store)
        
        await callback_query.answer(f"Channel {channel_name} deleted successfully!", show_alert=True)
        # Return to the delete channels list
        await show_delete_channels_list(client, callback_query)
        
    except Exception as e:
        print(f"Error in delete_confirmed: {e}")
        await callback_query.answer("Error deleting channel", show_alert=True)


#==================================================================================

@app.on_callback_query()
def handle_button_click(bot, callback_query):
    data = callback_query.data
    global admin_user_id
    global event_handler_3, event_handler_4, event_handler_5, event_handler_6, event_handler_7, event_handler_8, event_handler_9, event_hande_1
    global event_handel_5
    global rescheduled_task_names, is_first_time
    global broadcast_data, the_data_dict, edting_task_button, the_user_choice, close_handelrs
    def close_handelrs():
        try:
            bot.remove_handler(event_handel_5, 3)
        except ValueError:
            pass
        except:
            pass
        try:
            bot.remove_handler(event_handel, 1)
        except ValueError:
            pass
        except:
            pass
        try:
            bot.remove_handler(event_hande_1, 2)
        except ValueError:
            pass
        except:
            pass
            
        try:
            bot.remove_handler(event_handler_3, 4)
        except ValueError:
            pass
        except:
            pass
            
        
        try:
            bot.remove_handler(event_handler_4, 4)
        except ValueError:
            pass
        except:
            pass
        
        try:
            bot.remove_handler(event_handler_5, 5)
        except ValueError:
            pass
        except:
            pass
        
        try:
            bot.remove_handler(event_handler_6, 6)
        except ValueError:
            pass
        except:
            pass
        
        try:
            bot.remove_handler(event_handler_7, 7)
        except ValueError:
            pass
        except:
            pass
        
        try:
            bot.remove_handler(event_handler_8, 5)
        except ValueError:
            pass
        except:
            pass
        
        try:
            bot.remove_handler(event_handler_9, 6)
        except ValueError:
            pass
        except:
            pass
        the_user_choice["sch_type"] = None
        the_user_choice["task_title"] = None
        the_user_choice["task_message"] = None
    if data == 'broadcast':
        close_handelrs()
        try:
            bot.remove_handler(event_handel_5, 3)
        except ValueError:
            pass
        except:
            pass
        try:
            bot.remove_handler(event_hande_1, 2)
        except ValueError:
            pass
        except:
            pass
        
        try:
            bot.remove_handler(event_handler_3, 4)
        except ValueError:
            pass
        except:
            pass
            
        
        try:
            bot.remove_handler(event_handler_4, 4)
        except ValueError:
            pass
        except:
            pass
        
        try:
            bot.remove_handler(event_handler_5, 5)
        except ValueError:
            pass
        except:
            pass
        
        try:
            bot.remove_handler(event_handler_6, 6)
        except ValueError:
            pass
        except:
            pass
        
        try:
            bot.remove_handler(event_handler_7, 7)
        except ValueError:
            pass
        except:
            pass
        
        try:
            bot.remove_handler(event_handler_8, 5)
        except ValueError:
            pass
        except:
            pass
        
        try:
            bot.remove_handler(event_handler_9, 6)
        except ValueError:
            pass
        except:
            pass
        
        admin_user_id = 1602528125 
        user_id = callback_query.message.chat.id
        admins =  [6494713901]
        if callback_query.message.chat.id in admin_user_ids and callback_query.message.text != '/start': 
            
            keyboard = InlineKeyboardMarkup(
                [
                    [InlineKeyboardButton("Without a button ❌🎛", callback_data='without_button'), InlineKeyboardButton("With a button 🎛", callback_data='button')],
                    [InlineKeyboardButton("🎥 Round Video Converter", callback_data='round_video')],
                    [InlineKeyboardButton("🔙 Back", callback_data='back_to_home')],
                ]
            )
            the_user_choice["media_group"] = False
            callback_query.message.delete(callback_query.message.id)
            bot.send_message(callback_query.message.chat.id, "Please Choose do you want to send a message with a button or no", reply_markup=keyboard)

    #----------------------------------------------------------------------
    
    elif data == "button":
        close_handelrs()
        
        admin_user_id = 1602528125 
        user_id = callback_query.message.chat.id
        admins =  [6494713901]
        async def on_button_url(client, message):
            if message.chat.id in admin_user_ids and message.text != '/start': 

                def is_valid_url(url):
                    # Regular expression to match URLs, including single-character subdomains like m.coinvid.com
                    pattern = r'^(https?://)?([a-zA-Z0-9-]+\.[a-zA-Z0-9-]+\.[a-zA-Z]{2,}|[a-zA-Z0-9-]+\.[a-zA-Z]{2,}|t\.me/[a-zA-Z0-9_]+|@[a-zA-Z0-9_]+)(/.*)?$'
                    return re.match(pattern, url) is not None

                # Example usage
                if is_valid_url(message.text):
                    try:
                        broadcast_data["buttons"][0]["url"] = message.text
                        
                        keyboard = create_broadcast_keyboard(broadcast_data)
                        
                        await bot.send_message(callback_query.message.chat.id, "Very well here is how your message will look like 👇")
                        
                        if the_user_choice['media_group'] == True:    
                            await bot.copy_media_group(callback_query.message.chat.id, callback_query.message.chat.id, broadcast_data["message"])
                            await bot.send_message(callback_query.message.chat.id, "Choose an option:", reply_markup=keyboard)
                        else:    
                            await bot.forward_messages(callback_query.message.chat.id, callback_query.message.chat.id, broadcast_data["message"])
                            await bot.send_message(callback_query.message.chat.id, "Choose an option:", reply_markup=keyboard)
                        
                        bot.remove_handler(event_handler_7, 7)
                        
                        keyboard = ReplyKeyboardMarkup(
                            [
                                ["Edit Message Content 📝", "Edit Buttons ⚙️"],
                                ["📅 Schedule it", "📢 Broadcast it now"],
                                ["Back 🔙"]
                            ],
                            one_time_keyboard=True,
                            resize_keyboard=True
                        )
                        await bot.send_message(callback_query.message.chat.id, "Choose an option:", reply_markup=keyboard)
                    except ButtonUrlInvalid:
                        await bot.send_message(callback_query.message.chat.id,"The button URL is invalid. Please check the URL format. and try again.")
                else:
                    await bot.send_message(callback_query.message.chat.id,"The URL provided is not valid. Please check the URL format and try again.")
            
        async def on_button_title(client, message):
            if message.chat.id in admin_user_ids or message.chat.id == 7077099636 or callback_query.message.chat.id == 6494713901 or callback_query.message.chat.id in admins:
                if len(message.text) > 40:
                    await bot.send_message(message.chat.id, "The button title is too long. Please send a title with 40 characters or less.")
                    return
                
                broadcast_data["buttons"][0]["title"] = message.text
                broadcast_data["buttons"][0]["id"] = 1
                broadcast_data["buttons"][0]['place'] = 2
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Back & Cancel ❌", callback_data="broadcast")]
                ])
                await bot.send_message(message.chat.id, "Done 👍")
                bot.remove_handler(event_handler_6, 6)
                
                global event_handler_7
                await bot.send_message(message.chat.id, "Please send your button URL.", reply_markup=keyboard)
                event_handler_7 = MessageHandler(on_button_url)
                bot.add_handler(event_handler_7, 7)
            
        processed_media_groups = {}
        async def on_new_message_content(client, message):
            # Check if the message is part of a media group
            try:
                if message.media_group_id:
                    # Inform the user to send a single media message
                        # If this media group has already been processed, return early
                    if message.media_group_id in processed_media_groups:
                        return
                    processed_media_groups[message.media_group_id] = True
                    keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Back & Cancel ❌", callback_data="broadcast")]
                    ])
                    await bot.send_message(message.chat.id, "Please send a message with a single media only, not a media group.", reply_markup=keyboard)
                else:
                # Your existing logic to handle the message
                    if message.chat.id in admin_user_ids and message.text != '/start':
                        broadcast_data["message"] = message.id
                        broadcast_data["type"] = "with_button"
                        await bot.send_message(message.chat.id, "Done 👍")
                        bot.remove_handler(event_handler_5, 5)

                        global event_handler_6
                        keyboard = InlineKeyboardMarkup([
                            [InlineKeyboardButton("🔙 Back & Cancel ❌", callback_data="broadcast")]
                        ])
                        await bot.send_message(message.chat.id, "Please send your button title.", reply_markup=keyboard)
                        event_handler_6 = MessageHandler(on_button_title)
                        bot.add_handler(event_handler_6, 6)
            except MediaCaptionTooLong:
                    await bot.send_message(callback_query.message.chat.id, "The message caption is too long. Please send another message with a shorter caption.")

            
        if callback_query.message.chat.id in admin_user_ids and callback_query.message.text != '/start': 
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back & Cancel ❌", callback_data="broadcast")]
            ])
            callback_query.message.delete(callback_query.message.id)
            if broadcast_data["type"] == "with_video":
                bot.send_message(callback_query.message.chat.id, "Please forward the video above to the current chat.", reply_markup=keyboard)
                
            else:
                bot.send_message(callback_query.message.chat.id, "Please send your broadcast message.", reply_markup=keyboard)
            event_handler_5 = MessageHandler(on_new_message_content)
            bot.add_handler(event_handler_5, 5)
    #----------------------------------------------------------------------
    elif data == "add_new_button":
        admin_user_id = 1602528125 
        user_id = callback_query.message.chat.id
        global new_button_title
        admins =  [6494713901]
        url = " "
        if the_user_choice["editing_buttons"] == True:
            task_title = the_user_choice["task_title"]
            buttons_data = tasks[task_title].args[4]
            print('task_title:', task_title)
            broadcast_data = copy.deepcopy(buttons_data)
        async def on_button_url(client, message):
            if message.chat.id in admin_user_ids and message.text != '/start': 
                url = message.text
                def is_valid_url(url):
                    # Regular expression to match www.example.com, https://www.example.com, t.me/username, or @username
                    pattern = r'^(https?://)?(www\.[a-zA-Z0-9-]+\.[a-zA-Z]{2,}|t\.me/[a-zA-Z0-9_]+|@[a-zA-Z0-9_]+)(/.*)?$'
                    return re.match(pattern, url) is not None

                # Example usage
                if is_valid_url(message.text):
                    try:
                        bot.remove_handler(event_handler_7, 7)
                        # Assuming broadcast_data is defined and has a 'buttons' key
                        buttons = broadcast_data["buttons"]
                        # Check the length of buttons
                        if len(buttons) % 2 == 0:
                            new_button_place = 1
                        else:
                            new_button_place = 2

                        new_button_id = len(broadcast_data["buttons"]) + 1  # generate unique ID
                        new_button = {"id": new_button_id, "title": new_button_title["title"], "url": url, 'place': new_button_place}
                        broadcast_data["buttons"].append(new_button)
                        if the_user_choice["editing_buttons"] == True:
                            task_title = the_user_choice["task_title"]
                            job = tasks[task_title]
                            admin_id = tasks[task_title].args[1]  
                            task_type = tasks[task_title].args[3]
                            task_buttons = copy.deepcopy(broadcast_data)
                            print('task_title:', task_title)
                            print('Admin ID:', admin_id)
                            print('Data type:', task_type)
                            is_media_group = tasks[task_title].args[5]
                            job.modify(args=[bot, admin_id, broadcast_data["message"], task_type, buttons_data, is_media_group])
                            shutdown()
                        keyboard = create_broadcast_keyboard(broadcast_data)
                        
                        await bot.send_message(callback_query.message.chat.id, "Very well here is how your message will look like 👇")
                        if the_user_choice['media_group'] == True:    
                            await bot.copy_media_group(callback_query.message.chat.id, callback_query.message.chat.id, broadcast_data["message"])
                            await bot.send_message(callback_query.message.chat.id, "Choose an option:", reply_markup=keyboard)
                        else:    
                            await bot.forward_messages(callback_query.message.chat.id, callback_query.message.chat.id, broadcast_data["message"])
                            await bot.send_message(callback_query.message.chat.id, "Choose an option:", reply_markup=keyboard)
                        if edting_task_button == True:
                            keyboard = ReplyKeyboardMarkup(
                                [
                                    ["Edit Message Content 📝", "Edit Buttons ⚙️"],
                                    ["Back 🔙"]
                                ],
                                one_time_keyboard=True,
                                resize_keyboard=True
                            )
                        else:
                            keyboard = ReplyKeyboardMarkup(
                                [
                                    ["Edit Message Content 📝", "Edit Buttons ⚙️"],
                                    ["📅 Schedule it", "📢 Broadcast it now"],
                                    ["Back 🔙"]
                                ],
                                one_time_keyboard=True,
                                resize_keyboard=True
                            )
                        await bot.send_message(callback_query.message.chat.id, "Choose an option:", reply_markup=keyboard)
                    except ButtonUrlInvalid:
                            await bot.send_message(callback_query.message.chat.id,"The button URL is invalid. Please check the URL format. and try again.")
                else:
                    await bot.send_message(callback_query.message.chat.id,"The URL provided is not valid. Please check the URL format and try again.")
            
            
        async def on_button_title(client, message):
            if message.chat.id in admin_user_ids and message.text != '/start': 
                title = message.text
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Back & Cancel ❌", callback_data="back_edit_buttons")]
                ])
                new_button_title["title"] = title
                await bot.send_message(message.chat.id, "Done 👍")
                bot.remove_handler(event_handler_6, 6)
                
                global event_handler_7
                await bot.send_message(message.chat.id, "Please send your button URL.", reply_markup=keyboard)
                event_handler_7 = MessageHandler(on_button_url)
                bot.add_handler(event_handler_7, 7)
                
        if callback_query.message.chat.id in admin_user_ids and callback_query.message.text != '/start': 
            # global event_handler_6
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back & Cancel ❌", callback_data="back_edit_buttons")]
            ])
            callback_query.message.delete(callback_query.message.id)
            bot.send_message(callback_query.message.chat.id, "Please send your button title.", reply_markup=keyboard)
            event_handler_6 = MessageHandler(on_button_title)
            bot.add_handler(event_handler_6, 6)
    
    #----------------------------------------------------------------------
    elif data == "round_video":
        admin_user_id = 1602528125 
        user_id = callback_query.message.chat.id
        global new_button_title
        admins =  [6494713901]
        close_handelrs()
        async def on_button_title(client, message):
            if message.chat.id in admin_user_ids and message.text != '/start': 
                broadcast_data["type"] = "with_video"
                video = message
                print(message)
                bot.remove_handler(event_handler_9, 6)
                
                async def progress(current, total):
                    print(f"{current * 100 / total:.1f}%")
                
                # await app.send_reaction(message.chat.id, message.id, "🤗")
                await bot.send_animation(message.chat.id, animation='load-loading.gif')
                
                
                file_path = await app.download_media(video, progress=progress)

                def convert_to_round_video(input_video, output_video):
                    clip = VideoFileClip(input_video)
                    min_dimension = min(clip.w, clip.h)
                    clip = clip.crop(x_center=clip.w / 2, y_center=clip.h / 2, width=min_dimension, height=min_dimension)
                    clip = clip.subclip(0, min(clip.duration, 60))
                    clip.write_videofile(output_video, codec="libx264", audio_codec="aac")

                round_video_path = 'round_video.mp4'

                # Run the conversion in the background
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(executor, convert_to_round_video, file_path, round_video_path)

                print(f"File downloaded to: {round_video_path}")
                await app.send_video_note(message.chat.id, video_note=round_video_path, progress=progress)
                keyboard = InlineKeyboardMarkup(
                    [
                        [InlineKeyboardButton("Without a button ❌🎛", callback_data='without_button'), InlineKeyboardButton("With a button 🎛", callback_data='button')],
                        [InlineKeyboardButton("🎥 Make another Video", callback_data='round_video')],
                        [InlineKeyboardButton("🔙 Back", callback_data='broadcast')],
                    ]
                )
                await bot.send_message(callback_query.message.chat.id, "Please Choose do you want to send a message with a button or no", reply_markup=keyboard)  
        
            if os.path.exists(file_path):
                os.remove(file_path)
                print(f"File {file_path} has been deleted.")
            else:
                print(f"File {file_path} not found.")


        if callback_query.message.chat.id in admin_user_ids and callback_query.message.text != '/start': 
            # global event_handler_9
            the_user_choice["media_group"] = False
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back & Cancel ❌", callback_data="broadcast")]
            ])
            callback_query.message.delete(callback_query.message.id)
            bot.send_message(callback_query.message.chat.id, "Please send your video.\nPreferred to be in a range of 60-second video.", reply_markup=keyboard)
            event_handler_9 = MessageHandler(on_button_title)
            bot.add_handler(event_handler_9, 6)
    #----------------------------------------------------------------------
    
    elif data == "without_button":
        close_handelrs()
        
        admin_user_id = 1602528125 
        user_id = callback_query.message.chat.id
        admins =  [6494713901]
        keyboard = InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("Back 🔙", callback_data='broadcast')],
            ]
        )
        processed_media_groups = {}
        async def on_broadcast_message(client, message):
            # Check if the message is part of a media group
            if message.media_group_id:
                # If this media group has already been processed, return early
                if message.media_group_id in processed_media_groups:
                    return
                # Mark this media group as processed
                processed_media_groups[message.media_group_id] = True
                the_user_choice['media_group'] = True

            if message.chat.id in admin_user_ids and message.text != '/start': 
                broadcast_data["message"] = message.id
                broadcast_data["type"] = "no_button"
                await bot.send_message(callback_query.message.chat.id, "Very well here is how your message will look like 👇")
                keyboard = ReplyKeyboardMarkup(
                    [
                        ["📅 Schedule it", "📢 Broadcast it now"],
                        ["Edit Message Content 📝"],
                        ["Back 🔙"]
                    ],
                    one_time_keyboard=True,
                    resize_keyboard=True
                )
                try:
                    if the_user_choice['media_group'] == True:    
                        await bot.copy_media_group(callback_query.message.chat.id, callback_query.message.chat.id, broadcast_data["message"])
                        await bot.send_message(callback_query.message.chat.id, "Choose an option:", reply_markup=keyboard)
                    else:    
                        await bot.forward_messages(callback_query.message.chat.id, callback_query.message.chat.id, broadcast_data["message"])
                        await bot.send_message(callback_query.message.chat.id, "Choose an option:", reply_markup=keyboard)
                    bot.remove_handler(event_handler_3, 4)
                except MediaCaptionTooLong:
                    await bot.send_message(callback_query.message.chat.id, "The message caption is too long. Please send another message with a shorter caption.")

            
        if callback_query.message.chat.id in admin_user_ids and callback_query.message.text != '/start': 
            # global event_handler_3
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back & Cancel ❌", callback_data="broadcast")]
            ])
            callback_query.message.delete(callback_query.message.id)
            if broadcast_data["type"] == "with_video":
                bot.send_message(callback_query.message.chat.id, "Please forward the video above to the current chat.", reply_markup=keyboard)
                
            else:
                bot.send_message(callback_query.message.chat.id, "Please send your broadcast message.", reply_markup=keyboard)
            event_handler_3 = MessageHandler(on_broadcast_message)
            bot.add_handler(event_handler_3, 4)

    #----------------------------------------------------------------------

    elif data.startswith('edit_button_'):
        admins = [6494713901]
        if the_user_choice["editing_buttons"] == True:
            task_title = the_user_choice["task_title"]
            buttons_data = tasks[task_title].args[4]
            print('task_title:', task_title)
            broadcast_data = copy.deepcopy(buttons_data)
        the_index = int(data.split('_')[-1])
        button_index = find_index_by_id(the_index)
        buttpn_index[admin_user_id] = the_index
        buttpn_index["under_use"] = True
        print(f"\nBroadcast_data: {broadcast_data}\n")
        button = broadcast_data["buttons"][button_index]

        keyboard = ReplyKeyboardMarkup(
            [
                ["Edit Title ✏️", "Edit URL 🔗"],
                ["Move Up 🔼", "Move Down 🔽"],
                ["Delete Button ❌"],  # Add a delete button
                ["Back ⬅"],
                ["Home 🏠"],
            ],
            one_time_keyboard=True,
            resize_keyboard=True
        )

        bot.send_message(callback_query.message.chat.id, f"Editing Button: {button['title']}", reply_markup=keyboard)
        global know_the_index
        def know_the_index():
            button_index = int(data.split('_')[-1])
            buttpn_index[admin_user_id] = button_index

    #----------------------------------------------------------------------
    elif data == 'back':
        admin_user_id = 1602528125 
        user_id = callback_query.message.chat.id
        the_user_choice[user_id] = 'None'
        try:
            bot.remove_handler(event_handel_5, 3)
        except ValueError:
            pass
        except:
            pass
        try:
            bot.remove_handler(event_handel, 1)
        except ValueError:
            pass
        except:
            pass
        try:
            bot.remove_handler(event_hande_1, 2)
        except ValueError:
            pass
        except:
            pass
        try:
            bot.remove_handler(event_handler_3, 4)
        except ValueError:
            pass
        except:
            pass
            
        
        try:
            bot.remove_handler(event_handler_4, 4)
        except ValueError:
            pass
        except:
            pass
        
        try:
            bot.remove_handler(event_handler_5, 5)
        except ValueError:
            pass
        except:
            pass
        
        try:
            bot.remove_handler(event_handler_6, 6)
        except ValueError:
            pass
        except:
            pass
        
        try:
            bot.remove_handler(event_handler_7, 7)
        except ValueError:
            pass
        except:
            pass
        
        try:
            bot.remove_handler(event_handler_8, 5)
        except ValueError:
            pass
        except:
            pass
        
        callback_query.message.delete(callback_query.message.id)
        asyncio.run(start(bot, callback_query.message))
    
    #----------------------------------------------------------------------
    elif data == 'back_to_pre':
        admin_user_id = 1602528125 
        user_id = callback_query.message.chat.id
        the_user_choice[user_id] = 'None'
        try:
            bot.remove_handler(event_handel_5, 3)
        except ValueError:
            pass
        except:
            pass
        try:
            bot.remove_handler(event_handel, 1)
        except ValueError:
            pass
        except:
            pass
        try:
            bot.remove_handler(event_hande_1, 2)
        except ValueError:
            pass
        except:
            pass
        try:
            bot.remove_handler(event_handler_3, 4)
        except ValueError:
            pass
        except:
            pass
            
        
        try:
            bot.remove_handler(event_handler_4, 4)
        except ValueError:
            pass
        except:
            pass
        
        try:
            bot.remove_handler(event_handler_5, 5)
        except ValueError:
            pass
        except:
            pass
        
        try:
            bot.remove_handler(event_handler_6, 6)
        except ValueError:
            pass
        except:
            pass
        
        try:
            bot.remove_handler(event_handler_7, 7)
        except ValueError:
            pass
        except:
            pass
        
        try:
            bot.remove_handler(event_handler_8, 5)
        except ValueError:
            pass
        except:
            pass
        
        callback_query.message.delete(callback_query.message.id)
        keyboard = ReplyKeyboardMarkup(
            [
                ["📅 Schedule it", "📢 Broadcast it now"],
                ["Edit Message Content 📝"],
                ["Back 🔙"]
            ],
            one_time_keyboard=True,
            resize_keyboard=True
        )
        bot.send_message(callback_query.message.chat.id, "Choose an option:", reply_markup=keyboard)
    
    #----------------------------------------------------------------------
    elif data == 'back_editing':
        admin_user_id = 1602528125 
        user_id = callback_query.message.chat.id
        close_handelrs()
        callback_query.message.delete(callback_query.message.id)
        if broadcast_data["type"] == "with_button":
            keyboard = create_broadcast_keyboard(broadcast_data)
            
            bot.send_message(callback_query.message.chat.id, "Here is how your message will look like 👇.")
            if the_user_choice['media_group'] == True:    
                bot.copy_media_group(callback_query.message.chat.id, callback_query.message.chat.id, broadcast_data["message"])
                bot.send_message(callback_query.message.chat.id, "Choose an option:", reply_markup=keyboard)
            else:    
                bot.forward_messages(callback_query.message.chat.id, callback_query.message.chat.id, broadcast_data["message"])
                bot.send_message(callback_query.message.chat.id, "Choose an option:", reply_markup=keyboard)
            if edting_task_button == True:
                keyboard = ReplyKeyboardMarkup(
                    [
                        ["Edit Message Content 📝", "Edit Buttons ⚙️"],
                        ["Back 🔙"]
                    ],
                    one_time_keyboard=True,
                    resize_keyboard=True
                )
            else:
                keyboard = ReplyKeyboardMarkup(
                    [
                        ["Edit Message Content 📝", "Edit Buttons ⚙️"],
                        ["📅 Schedule it", "📢 Broadcast it now"],
                        ["Back 🔙"]
                    ],
                    one_time_keyboard=True,
                    resize_keyboard=True
                )
            bot.send_message(callback_query.message.chat.id, "Choose an option:", reply_markup=keyboard)
        else:
            if edting_task_button == True:
                keyboard = ReplyKeyboardMarkup(
                    [
                        ["Edit Message Content 📝"],
                        ["Back 🔙"]
                    ],
                    one_time_keyboard=True,
                    resize_keyboard=True
                )
            else:
                keyboard = ReplyKeyboardMarkup(
                    [
                        ["📢 Broadcast it now", "📅 Schedule it"],
                        ["Edit Message Content 📝"],
                        ["Back 🔙"]
                    ],
                    one_time_keyboard=True,
                    resize_keyboard=True
                )
            
            bot.send_message(callback_query.message.chat.id, "Here is how your message will look like 👇.")
            if the_user_choice['media_group'] == True:    
                bot.copy_media_group(callback_query.message.chat.id, callback_query.message.chat.id, broadcast_data["message"])
                bot.send_message(callback_query.message.chat.id, "Choose an option:", reply_markup=keyboard)
            else:    
                bot.forward_messages(callback_query.message.chat.id, callback_query.message.chat.id, broadcast_data["message"])
                bot.send_message(callback_query.message.chat.id, "Choose an option:", reply_markup=keyboard)

    #----------------------------------------------------------------------
    elif data == 'back_edit_buttons':
        admin_user_id = 1602528125 
        try:
            bot.remove_handler(event_handel_5, 3)
        except ValueError:
            pass
        except:
            pass
        try:
            bot.remove_handler(event_handel, 1)
        except ValueError:
            pass
        except:
            pass
        try:
            bot.remove_handler(event_hande_1, 2)
        except ValueError:
            pass
        except:
            pass
        try:
            bot.remove_handler(event_handler_3, 4)
        except ValueError:
            pass
        except:
            pass
            
        
        try:
            bot.remove_handler(event_handler_4, 4)
        except ValueError:
            pass
        except:
            pass
        
        try:
            bot.remove_handler(event_handler_5, 5)
        except ValueError:
            pass
        except:
            pass
        
        try:
            bot.remove_handler(event_handler_6, 6)
        except ValueError:
            pass
        except:
            pass
        
        try:
            bot.remove_handler(event_handler_7, 7)
        except ValueError:
            pass
        except:
            pass
        
        try:
            bot.remove_handler(event_handler_8, 5)
        except ValueError:
            pass
        except:
            pass
        
        keyboard = InlineKeyboardMarkup(
            [
                [InlineKeyboardButton(f"Edit {i + 1}: {button['title']}", callback_data=f'edit_button_{i}') for i, button in enumerate(broadcast_data["buttons"])],
                [InlineKeyboardButton("Add New Button ➕", callback_data='add_new_button')],
                [InlineKeyboardButton("Back ↩️", callback_data='back_editing')],
            ]
        )
        callback_query.message.delete(callback_query.message.id)
        bot.send_message(callback_query.message.chat.id, "Select a button to edit:", reply_markup=keyboard)
        
    #----------------------------------------------------------------------
    elif data == 'back_edit_message':
        try:
            bot.remove_handler(event_handel_5, 3)
        except ValueError:
            pass
        except:
            pass
        try:
            bot.remove_handler(event_handel, 1)
        except ValueError:
            pass
        except:
            pass
        try:
            bot.remove_handler(event_hande_1, 2)
        except ValueError:
            pass
        except:
            pass
        try:
            bot.remove_handler(event_handler_3, 4)
        except ValueError:
            pass
        except:
            pass
            
        
        try:
            bot.remove_handler(event_handler_4, 4)
        except ValueError:
            pass
        except:
            pass
        
        try:
            bot.remove_handler(event_handler_5, 5)
        except ValueError:
            pass
        except:
            pass
        
        try:
            bot.remove_handler(event_handler_6, 6)
        except ValueError:
            pass
        except:
            pass
        
        try:
            bot.remove_handler(event_handler_7, 7)
        except ValueError:
            pass
        except:
            pass
        
        try:
            bot.remove_handler(event_handler_8, 5)
        except ValueError:
            pass
        except:
            pass
        
        try:
            bot.remove_handler(event_handler_9, 6)
        except ValueError:
            pass
        except:
            pass
        
        callback_query.message.delete(callback_query.message.id)
        if broadcast_data["type"] == "with_button":
            keyboard = create_broadcast_keyboard(broadcast_data)
            
            bot.send_message(callback_query.message.chat.id, "Here is how your message will look like 👇.")
            if the_user_choice['media_group'] == True:    
                bot.copy_media_group(callback_query.message.chat.id, callback_query.message.chat.id, broadcast_data["message"])
                bot.send_message(callback_query.message.chat.id, "Choose an option:", reply_markup=keyboard)
            else:    
                bot.forward_messages(callback_query.message.chat.id, callback_query.message.chat.id, broadcast_data["message"])
                bot.send_message(callback_query.message.chat.id, "Choose an option:", reply_markup=keyboard)
            keyboard = ReplyKeyboardMarkup(
                [
                    ["Edit Message Content 📝", "Edit Buttons ⚙️"],
                    ["📅 Schedule it", "📢 Broadcast it now"],
                    ["Back 🔙"]
                ],
                one_time_keyboard=True,
                resize_keyboard=True
            )
            bot.send_message(callback_query.message.chat.id, "Choose an option:", reply_markup=keyboard)
        else:
            keyboard = ReplyKeyboardMarkup(
                [
                    ["📢 Broadcast it now", "📅 Schedule it"],
                    ["Edit Message Content 📝"],
                    ["Back 🔙"]
                ],
                one_time_keyboard=True,
                resize_keyboard=True
            )
            
            bot.send_message(callback_query.message.chat.id, "Here is how your message will look like 👇.")
            if the_user_choice['media_group'] == True:    
                bot.copy_media_group(callback_query.message.chat.id, callback_query.message.chat.id, broadcast_data["message"])
                bot.send_message(callback_query.message.chat.id, "Choose an option:", reply_markup=keyboard)
            else:    
                bot.forward_messages(callback_query.message.chat.id, callback_query.message.chat.id, broadcast_data["message"])
                bot.send_message(callback_query.message.chat.id, "Choose an option:", reply_markup=keyboard)

    #----------------------------------------------------------------------
    if data == 'show_channels':
        try:
            buttons = []
            current_row = []
            
            for chat_id in data_store["channels"]:
                try:
                    channel_name = data_store["channels"][chat_id].get("name")
                    
                    # Check if channel is selected (default to True if not set)
                    is_selected = data_store["channels"][chat_id].get("selected", True)
                    
                    # Create toggle button with checkmark or cross
                    toggle_symbol = "✅" if is_selected else "❌"
                    current_row.append(
                        InlineKeyboardButton(
                            f"{toggle_symbol} {channel_name}", 
                            callback_data=f"2toggle_channel1_{chat_id}"
                        )
                    )
                    
                    if len(current_row) == 2:  # Two buttons per row
                        buttons.append(current_row)
                        current_row = []
                        
                except Exception as e:
                    print(f"Error getting chat info: {e}")
                    continue
            
            # Add any remaining buttons
            if current_row:
                buttons.append(current_row)
                
            # Add control buttons at the bottom
            buttons.append([
                InlineKeyboardButton("Select All ✔", callback_data="select_all_channels"),
                InlineKeyboardButton("Deselect All ❌", callback_data="deselect_all_channels")
            ])
            buttons.append([
                InlineKeyboardButton("🗑️ Delete Channels", callback_data="channels_list_remover")
            ])
            buttons.append([InlineKeyboardButton("Back 🔙", callback_data='back_to_home')])
            
            keyboard = InlineKeyboardMarkup(buttons)
            callback_query.message.edit_text(
                "Select channels to broadcast to:\n(✅ = Selected, ❌ = Not Selected)", 
                reply_markup=keyboard
            )
            
        except Exception as e:
            print(f"Error in show_channels: {e}")
            bot.send_message(
                callback_query.message.chat.id,
                "Error loading channels list. Please try again."
            )

    #-----------------------------------------------------------------------=============================
    if data == 'remove_channel':
        # Ask the admin to send the new admin ID or forward a message from the new admin
        bot.send_message(callback_query.message.chat.id, "Please send the channel/group ID you want to remove.\nYou can copy it from the list above.")
        keyboard = InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("Back 🔙", callback_data='show_channels')],
            ]
        )
        async def on_new_admin_message(client, message):
            new_channel_id = message.text
            print(f"ID: {new_channel_id}")
            print(data_store["channels"])
            if data_store["channels"][new_channel_id]:
                del data_store["channels"][new_channel_id]
                save_data(data_store["channels"])
                print(data_store["channels"])
                await bot.send_message(callback_query.message.chat.id, str(new_channel_id))
                await bot.send_message(callback_query.message.chat.id, "Done👍", reply_markup=keyboard)
                bot.remove_handler(event_handel_5, 3)
            else:
                await message.reply_text("Invalid ID. Channel/group ID is not in the channels/groups list.", reply_markup=keyboard)

        # Listen for the next message
        
        event_handel_5 = MessageHandler(on_new_admin_message)
        bot.add_handler(event_handel_5, 3)

    #----------------------------------------------------------------------
    elif data == 'back_to_scdedule_menu':
        close_handelrs()
        admin_user_id = 1602528125 
        if callback_query.message.chat.id in admin_user_ids or callback_query.message.chat.id == 7077099636 or callback_query.message.chat.id == 6494713901:
            the_user_choice["sch_type"] = None
            the_user_choice["phase"] = 1
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🕒 Cron", callback_data="schedule_cron"),
                InlineKeyboardButton("⏲️ Interval", callback_data="schedule_interval"),
                InlineKeyboardButton("📅 Date", callback_data="schedule_date")],
                [InlineKeyboardButton("🔙 Back", callback_data="back_to_home")]
            ])
            callback_query.message.delete(callback_query.message.id)
            callback_query.message.reply("Choose a scheduling type:", reply_markup=keyboard)

    #=========================================================================================================================
    if data == 'admins_part':
        
        # Ask the admin to send the new admin ID or forward a message from the new admin
        close_handelrs()
        keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("Add new admin 🆕👮‍♂️", callback_data='add_admin'), InlineKeyboardButton("Remove an admin  🗑️👮‍♂️", callback_data='remove_admin')],
            [InlineKeyboardButton("Show admins list 📋👮‍♂️", callback_data='show_admins')],
            [InlineKeyboardButton("Back 🔙", callback_data='back_to_home')],
        ],
    )
        if 'Super Admins List' in callback_query.message.text or 'Admin List' in callback_query.message.text:
            callback_query.message.delete()
        else:
            callback_query.message.edit_text("Choose an action:", reply_markup=keyboard)

    #===========================================================================================================================
    if data == 'add_admin':
        # Ask the admin to send the new admin ID or forward a message from the new admin
        keyboard = InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("Back 🔙", callback_data='admins_part')],
            ]
        )
        bot.send_message(callback_query.message.chat.id, "Please send the new admin's user ID.\nYou can obtain it by make the new admin send a private message to this bot and then send you his ID.", reply_markup=keyboard)
        async def on_new_admin_message(client, message):
            if message.text.isnumeric():
                new_admin_id = message.text 
                admin_user_ids.append(int(new_admin_id))
                save_data2(admin_user_ids)
                print("------------------------")
                print("New Admin Added!", new_admin_id)
                print(admin_user_ids)
                print("------------------------")
                await bot.send_message(callback_query.message.chat.id, new_admin_id)
                await bot.send_message(callback_query.message.chat.id, "Done👍", reply_markup=keyboard)
                bot.remove_handler(event_hande_1, 2)
            else:
                await message.reply_text("Invalid ID. Please send a numebrs only ID.", reply_markup=keyboard)
                # bot.remove_handler(event_hande_1, 2)
                return 
        
        event_hande_1 = MessageHandler(on_new_admin_message)
        bot.add_handler(event_hande_1, 2)
    
    #===========================================================================================================================
    if data == 'remove_admin':
        # Ask the admin to send the new admin ID or forward a message from the new admin
        keyboard = InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("Back 🔙", callback_data='admins_part')],
            ]
        )
        bot.send_message(callback_query.message.chat.id, "Please send the admin's user ID to delete it.\nYou can obtain it by reviewing the admin list.", reply_markup=keyboard)
        async def delete_admin(client, message):
            if message.text.isnumeric():
                new_admin_id = message.text 
                try:
                    admin_user_ids.remove(int(new_admin_id))
                    save_data2(admin_user_ids)
                    print("------------------------")
                    print("Admin Removed!", new_admin_id)
                    print(admin_user_ids)
                    print("------------------------")
                    await bot.send_message(callback_query.message.chat.id, new_admin_id)
                    await bot.send_message(callback_query.message.chat.id, "Done👍", reply_markup=keyboard)
                    bot.remove_handler(event_handel, 1)
                except ValueError:
                    await message.reply_text("Invalid ID. Admin is not in the admins list. Please send a correct ID.", reply_markup=keyboard)
                    # bot.remove_handler(event_handel, 1)
                    
            else:
                await message.reply_text("Invalid ID. Please send a numebrs only ID.", reply_markup=keyboard)
                # bot.remove_handler(event_handel, 1)
                return 
        event_handel = MessageHandler(delete_admin)
        bot.add_handler(event_handel, 1)
        
    #==============================================================================================================================
    if data == 'show_admins':
        keyboard = InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("Back 🔙", callback_data='admins_part')],
            ]
        )
        async def get_user_info(user_id):
            try:
                user = await bot.get_users(user_id)
                username = user.username or "No username"
                first_name = user.first_name or "No first name"
                last_name = user.last_name or "No last name"
                return f"@{username} , Mr.{first_name} {last_name} , ID: {user_id}\n"
            except errors.FloodWait as e:
                print(f"Rate limit exceeded. Waiting for {e.x} seconds.")
                await asyncio.sleep(e.x)
                return await get_user_info(user_id)  # Retry after sleep
            except Exception:
                return f"@Unknown , Mr.Unknown , ID: {user_id}\n"

        async def show_admins():
            message = "Admin List:\n"
            for user_id in admin_user_ids:
                user_info = await get_user_info(user_id)
                message += f"{user_info}\n"
            await bot.send_message(callback_query.message.chat.id, message, reply_markup=keyboard) 
        asyncio.run(show_admins())



@app.on_message(filters.group | filters.channel)
async def track_activity(client, message):
    chat_id = message.chat.id
    user_id = message.from_user.id if message.from_user else None
    msg_date = message.date.astimezone(pytz.UTC).strftime("%Y-%m-%d %H:%M:%S")
    chat_title = message.chat.title or "Unnamed Chat"
    chat_type = str(message.chat.type)  # Convert chat_type to string

    # Prepare message data
    message_data = {
        "title": chat_title,
        "type": chat_type,
        "user_id": user_id,
        "date": msg_date,
    }

    # Append message data under the group/channel ID
    if str(chat_id) not in data:
        data[str(chat_id)] = []
    data[str(chat_id)].append(message_data)

    # Save updated data back to the JSON file
    save_data3()


@app.on_message(filters.command("check") & filters.group)
async def check_member_stats(client, message):
    chat_id = str(message.chat.id)
    user_id = str(message.from_user.id)

    if chat_id not in data or user_id not in data[chat_id]["member_activity"]:
        await message.reply_text("No activity data available for you.")
        return

    chat_data = data[chat_id]
    member_activity = chat_data["member_activity"].get(user_id, 0)
    today = datetime.now().strftime("%Y-%m-%d")
    today_activity = chat_data["messages"].get(user_id, {}).get(today, 0)

    # Calculate this week's and this month's activity
    this_week_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=datetime.now().weekday())
    this_week_end = this_week_start + timedelta(days=7)
    this_month_start = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    this_month_end = this_month_start.replace(month=this_month_start.month + 1) if this_month_start.month != 12 else this_month_start.replace(year=this_month_start.year + 1, month=1)
    this_week_activity = sum(chat_data["messages"].get(user_id, {}).get(date, 0) for date in (this_week_start + timedelta(days=i) for i in range((this_week_end - this_week_start).days)))
    this_month_activity = sum(chat_data["messages"].get(user_id, {}).get(date, 0) for date in (this_month_start + timedelta(days=i) for i in range((this_month_end - this_month_start).days)))

    user_name = chat_data["member_names"].get(user_id, "Unknown")
    stats_text = (
        f"📊 **Stats for {user_name}:**\n\n"
        f"**All Time:** {member_activity} messages\n"
        f"**Today:** {today_activity} messages\n"
        f"**This Week:** {this_week_activity} messages\n"
        f"**This Month:** {this_month_activity} messages\n"
    )

    await message.reply_text(stats_text)

async def validate_channel_id(app, channel_id):
    try:
        await app.get_chat(int(channel_id))
        return True
    except (errors.PeerIdInvalid, errors.UserDeactivated, errors.ChannelPrivate):
        print(f"Invalid channel ID detected: {channel_id}")
        return False

#---------------------------------------------------------------
@app.on_message(filters.text & filters.private)
async def handle_text(bot, message):
    global the_user_choice
    global admin_user_id, edting_task_button, the_data_dict
    global event_handler_3, event_handler_4, event_handler_5, event_handler_6, event_handler_7, event_handler_8, event_handler_9, event_hande_1
    global broadcast_data, the_data_dict, edting_task_button, the_user_choice, edting_task_button
    global event_handel_5
    def close_handelrs():
        try:
            bot.remove_handler(event_handel_5, 3)
        except ValueError:
            pass
        except:
            pass
        try:
            bot.remove_handler(event_hande_1, 1)
        except ValueError:
            pass
        except:
            pass
        try:
            bot.remove_handler(event_hande_1, 2)
        except ValueError:
            pass
        except:
            pass
            
        try:
            bot.remove_handler(event_handler_3, 4)
        except ValueError:
            pass
        except:
            pass
            
        
        try:
            bot.remove_handler(event_handler_4, 4)
        except ValueError:
            pass
        except:
            pass
        
        try:
            bot.remove_handler(event_handler_5, 5)
        except ValueError:
            pass
        except:
            pass
        
        try:
            bot.remove_handler(event_handler_6, 6)
        except ValueError:
            pass
        except:
            pass
        
        try:
            bot.remove_handler(event_handler_7, 7)
        except ValueError:
            pass
        except:
            pass
        
        try:
            bot.remove_handler(event_handler_8, 5)
        except ValueError:
            pass
        except:
            pass
        
        try:
            bot.remove_handler(event_handler_9, 6)
        except ValueError:
            pass
        except:
            pass
        the_user_choice["sch_type"] = None
        the_user_choice["task_title"] = None
        the_user_choice["task_message"] = None
    
    if message.text == "📅 Schedule it":
        close_handelrs()
        admin_user_id = 1602528125 
        if message.chat.id in admin_user_ids or message.chat.id == 7077099636 or message.chat.id == 6494713901:
            buttons = []
            for channel_id in data_store["channels"]:
                try:
                    channel_name = data_store["channels"][channel_id].get("name")
                    is_selected = data_store["channels"][channel_id].get("selected", True)
                    status = "✅" if is_selected else "❌"
                    buttons.append([InlineKeyboardButton(
                        f"{status} {channel_name}",
                        callback_data=f"23toggle_channel_{channel_id}"
                    )])
                except Exception as e:
                    print(f"Error getting chat info for {channel_id}: {e}")
                    continue

            buttons.append([InlineKeyboardButton("☑ Confirm & Save", callback_data="confirm_broadcast_now2")])
            buttons.append([InlineKeyboardButton("🔙 Back", callback_data="back_to_home")])

            await message.reply_text(
                "Select channels to broadcast to:\n"
                "✅ - Selected\n"
                "❌ - Not selected",
                reply_markup=InlineKeyboardMarkup(buttons)
            )

            # message.reply_text("Broadcast message sent to all users.", reply_markup=keyboard2)
    #--------------------------------------------------------------------------
    if message.text == "📢 Broadcast it now":
        print("Broadcast it now")
        the_user_choice["sch_type"] = None
        the_user_choice["broadcasting_now"] = True  # Set broadcasting mode
        admin_user_id = 1602528125 
        if message.chat.id in admin_user_ids or message.chat.id == 7077099636 or message.chat.id == 6494713901:
            buttons = []
            for channel_id in data_store["channels"]:
                try:
                    channel_name = data_store["channels"][channel_id].get("name")
                    is_selected = data_store["channels"][channel_id].get("selected", True)
                    status = "✅" if is_selected else "❌"
                    buttons.append([InlineKeyboardButton(
                        f"{status} {channel_name}",
                        callback_data=f"toggle_channel_{channel_id}"
                    )])
                except Exception as e:
                    print(f"Error getting chat info for {channel_id}: {e}")
                    continue

            buttons.append([InlineKeyboardButton("☑ Confirm & Send Now", callback_data="confirm_broadcast_now")])
            buttons.append([InlineKeyboardButton("🔙 Back", callback_data="back_to_home")])

            await message.reply_text(
                "Select channels to broadcast to:\n"
                "✅ - Selected\n"
                "❌ - Not selected",
                reply_markup=InlineKeyboardMarkup(buttons)
            )
   
    #--------------------------------------------------------------------------
    elif message.text == "Edit Buttons ⚙️":
        close_handelrs()
        admin_user_id = 1602528125 
        if message.chat.id in admin_user_ids or message.chat.id == 7077099636 or message.chat.id == 6494713901:
            keyboard = InlineKeyboardMarkup(
                [
                    [InlineKeyboardButton(f"Edit {button['id']}: {button['title']}", callback_data=f'edit_button_{button["id"]}')for button in broadcast_data["buttons"]],
                    [InlineKeyboardButton("Add New Button ➕", callback_data='add_new_button')],
                    [InlineKeyboardButton("Back ↩️", callback_data='back_editing')],
                ]
            )
            await bot.send_message(message.chat.id, "Select a button to edit:", reply_markup=keyboard)
    
    #--------------------------------------------------------------------------
    
    elif message.text == "Edit Message Content 📝":
        close_handelrs()
        admin_user_id = 1602528125 
        processed_media_groups = {}
        if message.chat.id in admin_user_ids or message.chat.id == 7077099636 or message.chat.id == 6494713901:
            async def on_new_message_content(client, message):
                global broadcast_data
                broadcast_data["message"] = message.id
                # Check if the message is part of a media group
                if message.media_group_id:
                    # If this media group has already been processed, return early
                    if message.media_group_id in processed_media_groups:
                        return
                    # Mark this media group as processed
                    processed_media_groups[message.media_group_id] = True
                if broadcast_data["type"] == "with_button":
                    keyboard = create_broadcast_keyboard(broadcast_data)
                    
                    await bot.send_message(message.chat.id, "Here is how your message will look like 👇.")
                    if the_user_choice['media_group'] == True:    
                        await bot.copy_media_group(message.chat.id, message.chat.id, broadcast_data["message"])
                        await bot.send_message(message.chat.id, "Choose an option:", reply_markup=keyboard)
                    else:    
                        await bot.forward_messages(message.chat.id, message.chat.id, broadcast_data["message"], reply_markup=keyboard)
                    if edting_task_button == True:
                            keyboard = ReplyKeyboardMarkup(
                                [
                                    ["Edit Message Content 📝", "Edit Buttons ⚙️"],
                                    ["Back 🔙"]
                                ],
                                one_time_keyboard=True,
                                resize_keyboard=True
                            )
                    else:
                        keyboard = ReplyKeyboardMarkup(
                            [
                                ["Edit Message Content 📝", "Edit Buttons ⚙️"],
                                ["📅 Schedule it", "📢 Broadcast it now"],
                                ["Back 🔙"]
                            ],
                            one_time_keyboard=True,
                            resize_keyboard=True
                        )
                    await bot.send_message(message.chat.id, "Choose an option:", reply_markup=keyboard)
                else:
                    keyboard = ReplyKeyboardMarkup(
                        [
                            ["📢 Broadcast it now", "📅 Schedule it"],
                            ["Edit Message Content 📝"],
                            ["Back 🔙"]
                        ],
                        one_time_keyboard=True,
                        resize_keyboard=True
                    )
                    await bot.send_message(message.chat.id, "Here is how your message will look like 👇.")
                    try:
                        if the_user_choice['media_group'] == True:    
                            await bot.copy_media_group(message.chat.id, message.chat.id, broadcast_data["message"])
                            await bot.send_message(message.chat.id, "Choose an option:", reply_markup=keyboard)
                        else:    
                            await bot.forward_messages(message.chat.id, message.chat.id, broadcast_data["message"])
                            await bot.send_message(message.chat.id, "Choose an option:", reply_markup=keyboard)
                    
                        bot.remove_handler(event_handler_8, 5)
                    except MediaCaptionTooLong:
                        await bot.send_message(message.chat.id, "The message caption is too long. Please send another message with a shorter caption.")

                

            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back & Cancel ❌", callback_data="back_edit_message")]
            ])
            await bot.send_message(message.chat.id, "Please send the new message content.", reply_markup=keyboard)
            event_handler_8 = MessageHandler(on_new_message_content)
            bot.add_handler(event_handler_8, 5)
        
    #--------------------------------------------------------------------------
    elif message.text == "Move Up 🔼":
        close_handelrs()
        admin_user_id = 1602528125 
        if message.chat.id in admin_user_ids or message.chat.id == 7077099636 or message.chat.id == 6494713901:
            if the_user_choice["editing_buttons"] == True:
                task_title = the_user_choice["task_title"]
                buttons_data = tasks[task_title].args[4]
                print('task_title:', task_title)
                broadcast_data = copy.deepcopy(buttons_data)
            the_index = int(buttpn_index[admin_user_id])
            button_index = find_index_by_id(the_index)
            button = broadcast_data["buttons"][button_index]
            print(f"The button idex is: {button_index} and title is: {button['title']}")
            move_button_up(broadcast_data["buttons"], button_index)
            if the_user_choice["editing_buttons"] == True:
                task_title = the_user_choice["task_title"]
                job = tasks[task_title]
                admin_id = tasks[task_title].args[1]  
                task_type = tasks[task_title].args[3]
                task_buttons = copy.deepcopy(broadcast_data)
                print('task_title:', task_title)
                print('Admin ID:', admin_id)
                print('Data type:', task_type)
                is_media_group = tasks[task_title].args[5]
                job.modify(args=[bot, admin_id, broadcast_data["message"], task_type, buttons_data, is_media_group])
                shutdown()
            keyboard = create_broadcast_keyboard(broadcast_data)
                
            await bot.send_message(message.chat.id, "Here is how your message will look like 👇.")
            if the_user_choice['media_group'] == True:    
                await bot.copy_media_group(message.chat.id, message.chat.id, broadcast_data["message"])
                await bot.send_message(message.chat.id, "Choose an option:", reply_markup=keyboard)
            else:    
                await bot.forward_messages(message.chat.id, message.chat.id, broadcast_data["message"], reply_markup=keyboard)
            keyboard = ReplyKeyboardMarkup(
                [
                    ["Edit Title ✏️", "Edit URL 🔗"],
                    ["Move Up 🔼", "Move Down 🔽"],
                    ["Back ⬅"],
                    ["Home 🏠"],
                ],
                one_time_keyboard=True,
                resize_keyboard=True
            )
            await bot.send_message(message.chat.id, f"Editing Button: {button['title']}", reply_markup=keyboard)
    #--------------------------------------------------------------------------
    
    elif message.text == "Move Down 🔽":
        close_handelrs()
        admin_user_id = 1602528125 
        if message.chat.id in admin_user_ids or message.chat.id == 7077099636 or message.chat.id == 6494713901:
            if the_user_choice["editing_buttons"] == True:
                task_title = the_user_choice["task_title"]
                buttons_data = tasks[task_title].args[4]
                print('task_title:', task_title)
                broadcast_data = copy.deepcopy(buttons_data)
            know_the_index()
            the_index = int(buttpn_index[admin_user_id])
            button_index = find_index_by_id(the_index)
            button = broadcast_data["buttons"][button_index]
            print(f"The button idex is: {buttpn_index} and title is: {button['title']}")
            move_button_down(broadcast_data["buttons"], button_index)
            await bot.send_message(message.chat.id, "Button moved down successfully!")
            if the_user_choice["editing_buttons"] == True:
                    task_title = the_user_choice["task_title"]
                    job = tasks[task_title]
                    admin_id = tasks[task_title].args[1]  
                    task_type = tasks[task_title].args[3]
                    task_buttons = copy.deepcopy(broadcast_data)
                    print('task_title:', task_title)
                    print('Admin ID:', admin_id)
                    print('Data type:', task_type)
                    is_media_group = tasks[task_title].args[5]
                    job.modify(args=[bot, admin_id, broadcast_data["message"], task_type, buttons_data, is_media_group])
                    shutdown()
            keyboard = create_broadcast_keyboard(broadcast_data)
                
            await bot.send_message(message.chat.id, "Here is how your message will look like 👇.")
            if the_user_choice['media_group'] == True:    
                await bot.copy_media_group(message.chat.id, message.chat.id, broadcast_data["message"])
                await bot.send_message(message.chat.id, "Choose an option:", reply_markup=keyboard)
            else:    
                await bot.forward_messages(message.chat.id, message.chat.id, broadcast_data["message"], reply_markup=keyboard)
            
            keyboard = ReplyKeyboardMarkup(
                [
                    ["Edit Title ✏️", "Edit URL 🔗"],
                    ["Move Up 🔼", "Move Down 🔽"],
                    ["Back ⬅"],
                    ["Home 🏠"],
                ],
                one_time_keyboard=True,
                resize_keyboard=True
            )
            await bot.send_message(message.chat.id, f"Editing Button: {button['title']}", reply_markup=keyboard)
    
    #--------------------------------------------------------------------------
    elif message.text == "Edit Title ✏️":
        close_handelrs()
        admin_user_id = 1602528125 
        if the_user_choice["editing_buttons"] == True:
            task_title = the_user_choice["task_title"]
            buttons_data = tasks[task_title].args[4]
            print('task_title:', task_title)
            broadcast_data = copy.deepcopy(buttons_data)
        if message.chat.id in admin_user_ids or message.chat.id == 7077099636 or message.chat.id == 6494713901:
            the_index = int(buttpn_index[admin_user_id])
            button_index = find_index_by_id(the_index)
            button = broadcast_data["buttons"][button_index]
            print(f"The button idex is: {buttpn_index} and title is: {button['title']}")
            async def on_button_title(client, message):
                title = message.text
                button['title'] = title
                await bot.send_message(message.chat.id, "Done 👍")
                bot.remove_handler(event_handler_6, 6)
                if the_user_choice["editing_buttons"] == True:
                    task_title = the_user_choice["task_title"]
                    job = tasks[task_title]
                    admin_id = tasks[task_title].args[1]  
                    task_type = tasks[task_title].args[3]
                    task_buttons = copy.deepcopy(broadcast_data)
                    print('task_title:', task_title)
                    print('Admin ID:', admin_id)
                    print('Data type:', task_type)
                    is_media_group = tasks[task_title].args[5]
                    job.modify(args=[bot, admin_id, broadcast_data["message"], task_type, buttons_data, is_media_group])
                    shutdown()
                keyboard = create_broadcast_keyboard(broadcast_data)
                
                await bot.send_message(message.chat.id, "Very well here is how your message will look like 👇.")
                if the_user_choice['media_group'] == True:    
                    await bot.copy_media_group(message.chat.id, message.chat.id, broadcast_data["message"])
                    await bot.send_message(message.chat.id, "Choose an option:", reply_markup=keyboard)
                else:    
                    await bot.forward_messages(message.chat.id, message.chat.id, broadcast_data["message"], reply_markup=keyboard)
                keyboard = ReplyKeyboardMarkup(
                    [
                        ["Edit Title ✏️", "Edit URL 🔗"],
                        ["Move Up 🔼", "Move Down 🔽"],
                        ["Back ⬅"],
                        ["Home 🏠"],
                    ],
                    one_time_keyboard=True,
                    resize_keyboard=True
                )
                await bot.send_message(message.chat.id, f"Editing Button: {button['title']}", reply_markup=keyboard)
            
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back & Cancel ❌", callback_data="back_edit_buttons")]
            ])
            await bot.send_message(message.chat.id, "Please send your New button title.", reply_markup=keyboard)
            event_handler_6 = MessageHandler(on_button_title)
            bot.add_handler(event_handler_6, 6)
    
    #--------------------------------------------------------------------------
    
    elif message.text == "Delete Button ❌":
        close_handelrs()
        admin_user_id = 1602528125
        
        if message.chat.id in admin_user_ids or message.chat.id == 7077099636 or message.chat.id == 6494713901:
            if the_user_choice["editing_buttons"] == True:
                task_title = the_user_choice["task_title"]
                buttons_data = tasks[task_title].args[4]
                print('task_title:', task_title)
                broadcast_data = copy.deepcopy(buttons_data)
            the_index = int(buttpn_index[admin_user_id])
            button_index = find_index_by_id(the_index)
            del broadcast_data["buttons"][button_index]  # Delete the button
            await bot.send_message(message.chat.id, "Button deleted successfully!")
            if the_user_choice["editing_buttons"] == True:
                task_title = the_user_choice["task_title"]
                job = tasks[task_title]
                admin_id = tasks[task_title].args[1]  
                task_type = tasks[task_title].args[3]
                task_buttons = copy.deepcopy(broadcast_data)
                print('task_title:', task_title)
                print('Admin ID:', admin_id)
                print('Data type:', task_type)
                is_media_group = tasks[task_title].args[5]
                job.modify(args=[bot, admin_id, broadcast_data["message"], task_type, buttons_data, is_media_group])
                shutdown()
            keyboard = create_broadcast_keyboard(broadcast_data)
            await bot.send_message(message.chat.id, "Here is how your message will look like 👇.")
            if the_user_choice['media_group'] == True:    
                await bot.copy_media_group(message.chat.id, message.chat.id, broadcast_data["message"])
                await bot.send_message(message.chat.id, "Choose an option:", reply_markup=keyboard)
            else:    
                await bot.forward_messages(message.chat.id, message.chat.id, broadcast_data["message"], reply_markup=keyboard)
            keyboard = ReplyKeyboardMarkup(
                [
                    ["Edit Message Content 📝", "Edit Buttons ⚙️"],
                    ["📅 Schedule it", "📢 Broadcast it now"],
                    ["Back 🔙"]
                ],
                one_time_keyboard=True,
                resize_keyboard=True
            )
            await bot.send_message(message.chat.id, "Choose an option:", reply_markup=keyboard)

    
    #--------------------------------------------------------------------------
    elif message.text == "Edit URL 🔗":
        close_handelrs()
        admin_user_id = 1602528125 
        if message.chat.id in admin_user_ids or message.chat.id == 7077099636 or message.chat.id == 6494713901:
            if the_user_choice["editing_buttons"] == True:
                task_title = the_user_choice["task_title"]
                buttons_data = tasks[task_title].args[4]
                print('task_title:', task_title)
                broadcast_data = copy.deepcopy(buttons_data)
            the_index = int(buttpn_index[admin_user_id])
            button_index = find_index_by_id(the_index)
            button = broadcast_data["buttons"][button_index]
            print(f"The button idex is: {buttpn_index} and title is: {button['title']}")
            async def on_button_url(client, message):
                url = message.text
                def is_valid_url(url):
                    # Regular expression to match www.example.com, https://www.example.com, t.me/username, or @username
                    pattern = r'^(https?://)?(www\.[a-zA-Z0-9-]+\.[a-zA-Z]{2,}|t\.me/[a-zA-Z0-9_]+|@[a-zA-Z0-9_]+)(/.*)?$'
                    return re.match(pattern, url) is not None

                # Example usage
                if is_valid_url(url):
                    try:
                        button['url'] = url
                        await bot.send_message(message.chat.id, "Done 👍")
                        bot.remove_handler(event_handler_7, 7)
                        if the_user_choice["editing_buttons"] == True:
                            task_title = the_user_choice["task_title"]
                            job = tasks[task_title]
                            admin_id = tasks[task_title].args[1]  
                            task_type = tasks[task_title].args[3]
                            task_buttons = copy.deepcopy(broadcast_data)
                            print('task_title:', task_title)
                            print('Admin ID:', admin_id)
                            print('Data type:', task_type)
                            is_media_group = tasks[task_title].args[5]
                            job.modify(args=[bot, admin_id, broadcast_data["message"], task_type, buttons_data, is_media_group])
                            shutdown()
                        keyboard = create_broadcast_keyboard(broadcast_data)
                        
                        await bot.send_message(message.chat.id, "Very well here is how your message will look like 👇.")
                        if the_user_choice['media_group'] == True:    
                            await bot.copy_media_group(message.chat.id, message.chat.id, broadcast_data["message"])
                            await bot.send_message(message.chat.id, "Choose an option:", reply_markup=keyboard)
                        else:    
                            await bot.forward_messages(message.chat.id, message.chat.id, broadcast_data["message"], reply_markup=keyboard)
                        keyboard = ReplyKeyboardMarkup(
                            [
                                ["Edit Title ✏️", "Edit URL 🔗"],
                                ["Move Up 🔼", "Move Down 🔽"],
                                ["Back ⬅"],
                                ["Home 🏠"],
                            ],
                            one_time_keyboard=True,
                            resize_keyboard=True
                        )
                        await bot.send_message(message.chat.id, f"Editing Button: {button['title']}", reply_markup=keyboard)
                    except ButtonUrlInvalid:
                            await bot.send_message(message.chat.id,"The button URL is invalid. Please check the URL format. and try again.")
                else:
                    await bot.send_message(message.chat.id,"The URL provided is not valid. Please check the URL format and try again.")
                
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back & Cancel ❌", callback_data="back_edit_buttons")]
            ])
            await bot.send_message(message.chat.id, "Please send your New button URL.", reply_markup=keyboard)
            event_handler_7 = MessageHandler(on_button_url)
            bot.add_handler(event_handler_7, 7)
    
    #--------------------------------------------------------------------------
    elif message.text == "Back 🔙":
        admin_user_id = 1602528125 
        if edting_task_button == True:
            close_handelrs()
            task_title = the_user_choice["task_title"]
            job = tasks[task_title]
            admin_id = tasks[task_title].args[1]  
            task_type = tasks[task_title].args[3]
            task_buttons = copy.deepcopy(broadcast_data)
            print('task_title:', task_title)
            print('Admin ID:', admin_id)
            print('Data type:', task_type)
            is_media_group = tasks[task_title].args[5]
            job.modify(args=[bot, admin_id, broadcast_data["message"], task_type, buttons_data, is_media_group])
            shutdown()
            
            keyboard = InlineKeyboardMarkup(
                [
                    [InlineKeyboardButton(f"Edit {i + 1}: {button['title']}", callback_data=f'edit_button_{i}') for i, button in enumerate(broadcast_data["buttons"])],
                    [InlineKeyboardButton("Add New Button ➕", callback_data='add_new_button')],
                    [InlineKeyboardButton("Back ↩️", callback_data=f"edit_task-{task_title}")],
                ]
            )
            await bot.send_message(message.chat.id, "Choose an option:", reply_markup=keyboard)
            broadcast_data = the_data_dict[message.chat.id]
        else:
            await start(bot, message)
        
    
    #--------------------------------------------------------------------------
    elif message.text == "Home 🏠":
        close_handelrs()
        admin_user_id = 1602528125 
        message.delete()
        await start(bot, message)
    
    #--------------------------------------------------------------------------
    elif message.text == "Back ⬅":
        close_handelrs()
        admin_user_id = 1602528125 
        if edting_task_button == True:
            task_title = the_user_choice["task_title"]
            job = tasks[task_title]
            admin_id = tasks[task_title].args[1]  
            task_type = tasks[task_title].args[3]
            task_buttons = copy.deepcopy(broadcast_data)
            print('task_title:', task_title)
            print('Admin ID:', admin_id)
            print('Data type:', task_type)
            is_media_group = tasks[task_title].args[5]
            job.modify(args=[bot, admin_id, broadcast_data["message"], task_type, task_buttons])
            shutdown()
            keyboard = InlineKeyboardMarkup(
                [
                    [InlineKeyboardButton(f"Edit {i + 1}: {button['title']}", callback_data=f'edit_button_{i}') for i, button in enumerate(broadcast_data["buttons"])],
                    [InlineKeyboardButton("Add New Button ➕", callback_data='add_new_button')],
                    [InlineKeyboardButton("Back ↩️", callback_data=f"edit_task-{task_title}")],
                ]
            )
        else:
            keyboard = InlineKeyboardMarkup(
                [
                    [InlineKeyboardButton(f"Edit {i + 1}: {button['title']}", callback_data=f'edit_button_{i}') for i, button in enumerate(broadcast_data["buttons"])],
                    [InlineKeyboardButton("Add New Button ➕", callback_data='add_new_button')],
                    [InlineKeyboardButton("Back ↩️", callback_data='back')],
                ]
            )
        await bot.send_message(message.chat.id, "Select a button to edit:", reply_markup=keyboard)
    
    #--------------------------------------------------------------------------
    elif message.text == "Back ↩️":
        close_handelrs()
        admin_user_id = 1602528125 
        keyboard = ReplyKeyboardMarkup(
                [
                    ["Edit Message Content 📝", "Edit Buttons ⚙️"],
                    ["📅 Schedule it", "📢 Broadcast it now"],
                    ["Back 🔙"]
                ],
                one_time_keyboard=True,
                resize_keyboard=True
            )
        await bot.send_message(message.chat.id, "Choose an option:", reply_markup=keyboard)
    
    #--------------------------------------------------------------------------
    elif message.text == "Back ⬅":
        close_handelrs()
        admin_user_id = 1602528125 
        if edting_task_button == True:
            job = tasks[task_title]
            task_title = the_user_choice["task_title"]
            admin_id = tasks[task_title].args[1]  
            task_type = tasks[task_title].args[3]
            task_buttons = copy.deepcopy(broadcast_data)
            print('task_title:', task_title)
            print('Admin ID:', admin_id)
            print('Data type:', task_type)
            is_media_group = tasks[task_title].args[5]
            job.modify(args=[bot, admin_id, broadcast_data["message"], task_type, task_buttons])
            shutdown()
            keyboard = InlineKeyboardMarkup(
                [
                    [InlineKeyboardButton(f"Edit {i + 1}: {button['title']}", callback_data=f'edit_button_{i}') for i, button in enumerate(broadcast_data["buttons"])],
                    [InlineKeyboardButton("Add New Button ➕", callback_data='add_new_button')],
                    [InlineKeyboardButton("Back ↩️", callback_data=f"edit_task-{task_title}")],
                ]
            )
        else:
            keyboard = InlineKeyboardMarkup(
                [
                    [InlineKeyboardButton(f"Edit {i + 1}: {button['title']}", callback_data=f'edit_button_{i}') for i, button in enumerate(broadcast_data["buttons"])],
                    [InlineKeyboardButton("Add New Button ➕", callback_data='add_new_button')],
                    [InlineKeyboardButton("Back ↩️", callback_data='back')],
                ]
            )
        await bot.send_message(message.chat.id, "Select a button to edit:", reply_markup=keyboard)
    
    #--------------------------------------------------------------------------
    if the_user_choice["sch_type"] in ["cron", "interval", "date"] and the_user_choice["phase"] == 1:
        print(the_user_choice["phase"])
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 chose another type", callback_data="back_to_scdedule_menu")]
        ])
        task_title = message.text.strip()
        if task_title in task_names:
            
            await message.reply("Task title already exists. Please provide a different title.", reply_markup=keyboard)
        else:
            the_user_choice["task_title"] = task_title
            the_user_choice["phase"] = 2
            print(the_user_choice["phase"])
            if the_user_choice["sch_type"] == "cron":
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 chose another type", callback_data="back_to_scdedule_menu")]
                ])
                await message.reply("""
Finally, please provide the scheduling time. 

The format is:

**`minute-hour-day-month-day_of_week`** 

or 

**`hour:minute`**

Use '*' as a wildcard for any field.

0 or 7 = Sunday
1 = Monday
2 = Tuesday
3 = Wednesday
4 = Thursday
5 = Friday
6 = Saturday

Examples:
-  `30-10-*-*-5`  - Every Friday at 10:30 AM
**-  `30-10-*-*-*`  - Every day at 10:30 AM**
**-  `10:30`  - Every day at 10:30 AM**
-  `*/5-*-*-*-*`  - Every 5 minutes
-  `0-9-*-*-1`    - Every Monday at 9:00 AM
-  `30-10-*-*-2`  would mean "Every Tuesday at 10:30 AM"
-  `0-9-*-*-1,5`  would mean "Every Monday and Friday at 9:00 AM"

    """, reply_markup=keyboard)
            
            elif the_user_choice["sch_type"] == "interval":
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 chose another type", callback_data="back_to_scdedule_menu")]
                ])
                await message.reply("""
Please provide the interval in seconds.

Use an interval to define how often to send your message. Specify the number of seconds.

Format:
(interval_in_seconds)

Examples:
- `10` - Every 10 seconds
- `3600` - Every hour (3600 seconds)
    """, reply_markup=keyboard)
            
            elif the_user_choice["sch_type"] == "date":
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 chose another type", callback_data="back_to_scdedule_menu")]
                ])
                now = datetime.now()

                current_time = now.strftime("%Y-%m-%d %H:%M:%S")
                await message.reply(f"""
Please provide the date and time for when to send your message.

Specify an exact date and time for when to send your message (This is a one-time message.). The format is:

`YYYY-MM-DD HH:MM:SS`

Current time: **`{current_time}`**

Examples:
- **`2024-11-09 15:30:00`** = On November 9, 2024, at 3:30 PM
- **`2024-12-25 09:00:00`** = On December 25, 2024, at 9:00 AM
    """, reply_markup=keyboard)

    #--------------------------------------------------------------------------
    elif the_user_choice["sch_type"] == "edit_message":
        task_title = the_user_choice["task_title"]
        broadcast_data["message"] = message.id
        print(broadcast_data["message"])
        
        if task_title in tasks:
            job = tasks[task_title]
            # Retrieve the type associated with the task title
            admin_id = tasks[task_title].args[1]  
            task_type = tasks[task_title].args[3]
            buttons_data_dict = tasks[task_title].args[4]
            buttons_data = copy.deepcopy(buttons_data_dict)
            print('task_title:', task_title)
            print('Admin ID:', admin_id)
            print('Data type:', task_type)
            job.modify(args=[bot, admin_id, broadcast_data["message"], task_type, buttons_data, False])
            shutdown()
            # await message.delete(message.id)
            await message.reply(f"Task **{task_title}** message has been updated.")
            buttons_data = tasks[task_title].args[4]
            try:
                if buttons_data["type"] == "with_button":
                    keyboard = create_broadcast_keyboard(buttons_data)
                    await bot.send_message(message.chat.id, "Here is how your message will look like 👇.")
                    await bot.forward_messages(message.chat.id, message.chat.id, broadcast_data["message"], reply_markup=keyboard)
                    keyboard = InlineKeyboardMarkup([
                        [InlineKeyboardButton("🏠 Home", callback_data="back_to_home"), 
                        InlineKeyboardButton("📋 Current Tasks", callback_data="current_tasks")],
                        [InlineKeyboardButton("📅 Schedule another Task", callback_data="broadcast")],
                        [InlineKeyboardButton("🔙 Back", callback_data=f"edit_task-{task_title}")],
                    ])
                    await bot.send_message(message.chat.id, "Choose an option:", reply_markup=keyboard)
                else:
                    keyboard = InlineKeyboardMarkup([
                        [InlineKeyboardButton("🏠 Home", callback_data="back_to_home"), 
                        InlineKeyboardButton("📋 Current Tasks", callback_data="current_tasks")],
                        [InlineKeyboardButton("📅 Schedule another Task", callback_data="broadcast")],
                        [InlineKeyboardButton("🔙 Back", callback_data=f"edit_task-{task_title}")],
                    ])
                    await bot.send_message(message.chat.id, "Here is how your message will look like 👇.")
                    await bot.forward_messages(message.chat.id, message.chat.id, broadcast_data["message"])
                    await bot.send_message(message.chat.id, "Choose an option:", reply_markup=keyboard)
                the_user_choice["sch_type"] = None
                the_user_choice["task_title"] = None
                the_user_choice["task_message"] = None
            except MediaCaptionTooLong:
                await bot.send_message(message.chat.id, "The message caption is too long. Please send another message with a shorter caption.")


    #--------------------------------------------------------------------------
    elif the_user_choice["sch_type"] == "edit_title":
        print(the_user_choice["phase"])
        task_title = the_user_choice["task_title"]
        new_task_title = message.text.strip()
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🏠 Home", callback_data="back_to_home"), 
            InlineKeyboardButton("📋 Current Tasks", callback_data="current_tasks")],
            [InlineKeyboardButton("📅 Schedule another Task", callback_data="broadcast")],
            [InlineKeyboardButton("🔙 Back", callback_data=f"edit_task-{task_title}")],
        ])
        if task_title in tasks:
            # Retrieve the job using the old task title
            job = tasks[task_title]
            # Remove the old key-value pair
            del tasks[task_title]
            # Insert the job back with the new task title
            tasks[new_task_title] = job
            await message.delete(message.id)
            await message.reply(f"Task **{task_title}** title has been updated to **{new_task_title}**.", reply_markup=keyboard)
        the_user_choice["sch_type"] = None
        the_user_choice["task_title"] = None
        the_user_choice["task_message"] = None

    #--------------------------------------------------------------------------
    elif the_user_choice["phase"] == 2:
        print(the_user_choice["phase"])
        await schedule_task(bot, message)


@app.on_message(filters.media & filters.private)  # Filter to check for media messages
async def on_new_message_content(bot, message):
    global the_user_choice
    global admin_user_id, edting_task_button, the_data_dict
    global event_handler_3, event_handler_4, event_handler_5, event_handler_6, event_handler_7, event_handler_8, event_handler_9, event_hande_1
    global broadcast_data, the_data_dict, edting_task_button, the_user_choice, edting_task_button
    global event_handel_5
    def close_handelrs():
        try:
            bot.remove_handler(event_handel_5, 3)
        except ValueError:
            pass
        except:
            pass
        try:
            bot.remove_handler(event_hande_1, 1)
        except ValueError:
            pass
        except:
            pass
        try:
            bot.remove_handler(event_hande_1, 2)
        except ValueError:
            pass
        except:
            pass
            
        try:
            bot.remove_handler(event_handler_3, 4)
        except ValueError:
            pass
        except:
            pass
            
        
        try:
            bot.remove_handler(event_handler_4, 4)
        except ValueError:
            pass
        except:
            pass
        
        try:
            bot.remove_handler(event_handler_5, 5)
        except ValueError:
            pass
        except:
            pass
        
        try:
            bot.remove_handler(event_handler_6, 6)
        except ValueError:
            pass
        except:
            pass
        
        try:
            bot.remove_handler(event_handler_7, 7)
        except ValueError:
            pass
        except:
            pass
        
        try:
            bot.remove_handler(event_handler_8, 5)
        except ValueError:
            pass
        except:
            pass
        
        try:
            bot.remove_handler(event_handler_9, 6)
        except ValueError:
            pass
        except:
            pass
        the_user_choice["sch_type"] = None
        # the_user_choice["task_title"] = None
        the_user_choice["task_message"] = None

    #--------------------------------------------------------------------------------------
    processed_media_groups = {}
    if message.media_group_id:
        # If this media group has already been processed, return early
        if message.media_group_id in processed_media_groups:
            return
        else:
            # Mark this media group as processed
            processed_media_groups[message.media_group_id] = True

            # Check if the message is the first in the media group
            media_group_messages = await app.get_media_group(message.chat.id, message.id)
            if media_group_messages[0].id != message.id:
                return

            if the_user_choice["sch_type"] == "edit_message":
                task_title = the_user_choice["task_title"]
                broadcast_data["message"] = message.id
                print(broadcast_data["message"])
                
                if task_title in tasks:
                    job = tasks[task_title]
                    # Retrieve the type associated with the task title
                    admin_id = tasks[task_title].args[1]  
                    task_type = tasks[task_title].args[3]
                    buttons_data_dict = tasks[task_title].args[4]
                    buttons_data = copy.deepcopy(buttons_data_dict)
                    print('task_title:', task_title)
                    print('Admin ID:', admin_id)
                    print('Data type:', task_type)
                    job.modify(args=[bot, admin_id, broadcast_data["message"], task_type, buttons_data, True])
                    shutdown()
                    await message.reply(f"Task **{task_title}** message has been updated.")
                    buttons_data = tasks[task_title].args[4]
                    if buttons_data["type"] == "with_button":
                        keyboard = create_broadcast_keyboard(buttons_data)
                        await bot.send_message(message.chat.id, "Here is how your message will look like 👇.")
                        await bot.copy_media_group(message.chat.id, message.chat.id, broadcast_data["message"])
                        await bot.send_message(message.chat.id, "Choose an option:", reply_markup=keyboard)
                        keyboard = InlineKeyboardMarkup([
                            [InlineKeyboardButton("🏠 Home", callback_data="back_to_home"), 
                            InlineKeyboardButton("📋 Current Tasks", callback_data="current_tasks")],
                            [InlineKeyboardButton("📅 Schedule another Task", callback_data="broadcast")],
                            [InlineKeyboardButton("🔙 Back", callback_data=f"edit_task-{task_title}")],
                        ])
                        await bot.send_message(message.chat.id, "Choose an option:", reply_markup=keyboard)
                    else:
                        keyboard = InlineKeyboardMarkup([
                            [InlineKeyboardButton("🏠 Home", callback_data="back_to_home"), 
                            InlineKeyboardButton("📋 Current Tasks", callback_data="current_tasks")],
                            [InlineKeyboardButton("📅 Schedule another Task", callback_data="broadcast")],
                            [InlineKeyboardButton("🔙 Back", callback_data=f"edit_task-{task_title}")],
                        ])
                        await bot.send_message(message.chat.id, "Here is how your message will look like 👇.")
                        await bot.copy_media_group(message.chat.id, message.chat.id, broadcast_data["message"])
                        await bot.send_message(message.chat.id, "Choose an option:", reply_markup=keyboard)
                the_user_choice["sch_type"] = None
                the_user_choice["task_title"] = None
                the_user_choice["task_message"] = None

@app.on_message(filters.text & filters.private)
async def schedule_task(client, message):
    global the_user_choice
    sch_type = the_user_choice["sch_type"]

    if sch_type == "cron" and the_user_choice["phase"] == 2:
        text = message.text.strip()
        day = '*'
        month = '*'
        day_of_week = '*'
        hour = '*'
        minute = '*'

        if '-' in text:
            parts = text.split('-')
            if len(parts) == 5:
                minute, hour, day, month, day_of_week = parts
            else:
                # fallback: all wildcards
                pass
        elif ':' in text:
            hour, minute = text.split(':')
        else:
            # fallback: all wildcards
            pass

        # Check if the time is in the past
        now = datetime.now()
        # Create a datetime object for the scheduled time
        scheduled_time = datetime(
            year=now.year,
            month=int(month) if month.isdigit() else now.month,
            day=int(day) if day.isdigit() else now.day,
            hour=int(hour) if hour != '*' and hour.isdigit() else now.hour,
            minute=int(minute) if minute != '*' and minute.isdigit() else now.minute
        )

        if scheduled_time < now and '*' not in [minute, hour, day, month, day_of_week]:
            await message.reply("The scheduled time is in the past. Please choose a future date and time then try again")
            return
        task_buttons = copy.deepcopy(broadcast_data)
        selected_channels = copy.deepcopy(data_store["channels"])
        if the_user_choice["media_group"] == True:
            job = scheduler.add_job(
                sync_broadcast_to_channels,
                CronTrigger(
                    minute=minute if minute != '*' else None,
                    hour=hour if hour != '*' else None,
                    day=day if day != '*' else None,
                    month=month if month != '*' else None,
                    day_of_week=day_of_week if day_of_week != '*' else None
                ),
                args=[client, message.chat.id, broadcast_data["message"], broadcast_data["type"],task_buttons, True, selected_channels],
                id=the_user_choice["task_title"]
            )
        else:
            job = scheduler.add_job(
                sync_broadcast_to_channels,
                CronTrigger(
                    minute=minute if minute != '*' else None,
                    hour=hour if hour != '*' else None,
                    day=day if day != '*' else None,
                    month=month if month != '*' else None,
                    day_of_week=day_of_week if day_of_week != '*' else None
                ),
                args=[client, message.chat.id, broadcast_data["message"], broadcast_data["type"],task_buttons, False, selected_channels],
                id=the_user_choice["task_title"]
            )

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🏠 Home", callback_data="back_to_home"), 
            InlineKeyboardButton("📋 Current Tasks", callback_data="current_tasks")],
            [InlineKeyboardButton("📅 Schedule another Task", callback_data="broadcast")]
        ])
        tasks[the_user_choice["task_title"]] = job  # Store the job with a meaningful name
        await message.reply(f"Scheduled a cron task: {the_user_choice['task_title']}", reply_markup=keyboard)
        shutdown()
        the_user_choice["sch_type"] = None
        the_user_choice["media_group"] = None

    #--------------------------------------------------------------------------
    elif sch_type == "interval" and the_user_choice["phase"] == 2:
        try:
            task_buttons = copy.deepcopy(broadcast_data)
            selected_channels = copy.deepcopy(data_store["channels"])
            interval = int(message.text)
            if the_user_choice["media_group"] == True:
                job = scheduler.add_job(sync_broadcast_to_channels, IntervalTrigger(seconds=interval), args=[client, message.chat.id, broadcast_data["message"], broadcast_data["type"],task_buttons, True, selected_channels], id=the_user_choice["task_title"])
            else:
                job = scheduler.add_job(sync_broadcast_to_channels, IntervalTrigger(seconds=interval), args=[client, message.chat.id, broadcast_data["message"], broadcast_data["type"],task_buttons, False, selected_channels], id=the_user_choice["task_title"])
            
            tasks[the_user_choice["task_title"]] = job
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🏠 Home", callback_data="back_to_home"), 
                InlineKeyboardButton("📋 Current Tasks", callback_data="current_tasks")],
                [InlineKeyboardButton("📅 Schedule another Task", callback_data="broadcast")]
            ])
            await message.reply(f"Scheduled an interval job: {the_user_choice['task_title']}", reply_markup=keyboard)
            shutdown()
            the_user_choice["sch_type"] = None
            the_user_choice["media_group"] = None
            
        except Exception as e:
            print(f"Error scheduling job: {e}")
            await message.reply("Please enter a valid integer for the interval.")

    #--------------------------------------------------------------------------
    elif sch_type == "date" and the_user_choice["phase"] == 2:
        run_date = message.text
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🏠 Home", callback_data="back_to_home"), 
            InlineKeyboardButton("📋 Current Tasks", callback_data="current_tasks")],
            [InlineKeyboardButton("📅 Schedule another Task", callback_data="broadcast")]
        ])
        
        try:
            # Parse the provided date and time
            scheduled_time = datetime.strptime(run_date, "%Y-%m-%d %H:%M:%S")
            
            # Check if the scheduled time is in the future
            now = datetime.now()
            if scheduled_time <= now:
                await message.reply("The scheduled date and time is in the past. Please choose a future date and time then try again")
                return
            task_buttons = copy.deepcopy(broadcast_data)
            selected_channels = copy.deepcopy(data_store["channels"])
            if the_user_choice["media_group"] == True:
                job = scheduler.add_job(
                    sync_broadcast_to_channels,
                    DateTrigger(run_date=scheduled_time),
                    args=[client, message.chat.id, broadcast_data["message"], broadcast_data["type"],task_buttons, True, selected_channels],
                    id=f"date_{the_user_choice['task_title']}"  # Add a prefix to identify date-type jobs
                )
            else:
                job = scheduler.add_job(
                    sync_broadcast_to_channels,
                    DateTrigger(run_date=scheduled_time),
                    args=[client, message.chat.id, broadcast_data["message"], broadcast_data["type"],task_buttons, False, selected_channels],
                    id=f"date_{the_user_choice['task_title']}"  # Add a prefix to identify date-type jobs
                )
            
            tasks[the_user_choice["task_title"]] = job
            await message.reply(f"Scheduled a date job: {the_user_choice['task_title']}", reply_markup=keyboard)
            shutdown()
            the_user_choice["media_group"] = None
            the_user_choice["sch_type"] = None
            
        except ValueError:
            await message.reply("Please enter a valid date and time format (YYYY-MM-DD HH:MM:SS).")
        except Exception as e:
            print(f"Error scheduling job: {e}")
            await message.reply("An error occurred while scheduling the job. Please try again.")

atexit.register(shutdown)
scheduler.add_listener(job_listener, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR)


if __name__ == "__main__":
    print("Bot started.")
    app.run()

