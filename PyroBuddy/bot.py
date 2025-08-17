from decimal import ROUND_HALF_UP, Decimal
from pyrogram import filters, errors
from pyrogram.handlers import MessageHandler
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.types import BotCommand, BotCommandScope, BotCommandScopeAllPrivateChats, MenuButtonDefault
import json
import asyncio
import random
import requests
import time
from pyrogram.client import Client

# Add login credentials for automatic relogin
LOGIN_CREDENTIALS = {
    "username": "ahmed200789",
    "password": "AhmeD.2007"
}

# Global token management
current_blade_auth = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9.eyJpc3MiOiJpc3N1c2VyIiwiYXVkIjoiYXVkaWVuY2UiLCJ0ZW5hbnRfaWQiOiI2NzczNDMiLCJ1c2VyX25hbWUiOiJtcm5vYm9keTAwNyIsInRva2VuX3R5cGUiOiJhY2Nlc3NfdG9rZW4iLCJyb2xlX25hbWUiOiIiLCJ1c2VyX3R5cGUiOiJyb2NrZXQiLCJ1c2VyX2lkIjoiMTc1Nzc4MDk2ODQ0MTAxNjMyMiIsImRldGFpbCI6eyJhdmF0YXIiOiIyIiwidmlwTGV2ZWwiOjF9LCJhY2NvdW50IjoibXJub2JvZHkwMDciLCJjbGllbnRfaWQiOiJyb2NrZXRfd2ViIiwiZXhwIjoxNzQ4NTI0MTIxLCJuYmYiOjE3NDc5MTkzMjF9.g1rmHqMhlULI1OBO-koevtxUNqBXij9HpsHyjttWDOILO41bL6aUtnkC6WfNyL4EXdW0REQXHXcAevNU1UqUoA"

def login_to_coinvid():
    """Login to Coinvid API and get new blade_auth token"""
    global current_blade_auth
    try:
        url = "https://m.coinvidg.com/api/rocket-api/member/login"
        headers = {
            "Accept": "application/json, text/plain, */*",
            "Authorization": "Basic cm9ja2V0X3dlYjpyb2NrZXRfd2Vi",
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
        }
        data = {
            "username": LOGIN_CREDENTIALS["username"],
            "password": LOGIN_CREDENTIALS["password"]
        }
        
        print(f"[PyroBuddy] Attempting login with username: {LOGIN_CREDENTIALS['username']}")
        response = requests.post(url, data=data, headers=headers, timeout=30)
        
        print(f"[PyroBuddy] Login response status: {response.status_code}")
        print(f"[PyroBuddy] Login response headers: {dict(response.headers)}")
        print(f"[PyroBuddy] Login response body: {response.text}")
        
        if response.status_code == 200:
            try:
                response_data = response.json()
                print(f"[PyroBuddy] Parsed response data: {response_data}")
                
                if response_data.get('code') == 200 and 'data' in response_data and 'access_token' in response_data['data']:
                    new_token = response_data['data']['access_token']
                    current_blade_auth = new_token
                    print(f"[PyroBuddy] Login successful, new token obtained: {new_token[:50]}...")
                    return new_token
                else:
                    print(f"[PyroBuddy] Login failed: Invalid response structure or code: {response_data.get('code')}")
                    return None
            except json.JSONDecodeError as e:
                print(f"[PyroBuddy] Failed to parse JSON response: {e}")
                return None
        else:
            print(f"[PyroBuddy] Login failed with status {response.status_code}")
            return None
            
    except Exception as e:
        print(f"[PyroBuddy] Login error: {e}")
        return None

def get_headers_with_auth():
    """Get headers with current blade_auth token"""
    return {
        "accept": "application/json, text/plain, */*",
        "authorization": "Basic cm9ja2V0X3dlYjpyb2NrZXRfd2Vi",
        "blade-auth": current_blade_auth,
        "user-agent": "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Mobile Safari/537.36"
    }

COMMANDS = [
    BotCommand(command="start", description="Start the bot"),
    BotCommand(command="help", description="Show help message"),
    BotCommand(command="back", description="Return to main menu"),
]
api_id = 27112006
api_hash = "0d1019d7ca92aef12571c82cd163d2bd"
consecutive_losses = 0
global pre_message
pre_message = {'pre_message': 'Starting'}
bot_token = "7736378352:AAGCpdRmt-dbTPmoavQbF9FDUn1Xdbf8qik"
global admins_list, super_admin_list, group_chat_ids
with open("data.json", "r") as f:
    data_valuse = json.load(f)

with open("admins_list.json", "r") as f:
    admin_json = json.load(f)
    admins_list = admin_json["admins"]

with open("super_admin_list.json", "r") as f:
    super_admin_json = json.load(f)
    super_admin_list = super_admin_json["super_admins"]

with open("channel_list.json", "r") as f:
    channel_list_json = json.load(f)
    group_chat_ids = channel_list_json["group_chat_ids"]


def write_json_file(file_path, data):
    with open(file_path, 'w') as file:
        json.dump(data, file)


def update_admin_json():
    global admins_list, super_admin_list, group_chat_ids
    with open('admins_list.json', "w") as f:
        json.dump(admin_json, f, indent=4)
    with open("admins_list.json", "r") as f:
        admin_json = json.load(f)
        admins_list = admin_json["admins"]


def update_super_admin_json():
    global admins_list, super_admin_list, group_chat_ids
    with open('super_admin_list.json', "w") as f:
        json.dump(super_admin_json, f, indent=4)
    with open("super_admin_list.json", "r") as f:
        super_admin_json = json.load(f)
        super_admin_list = super_admin_json["super_admins"]


def update_channels_json():
    global admins_list, super_admin_list, group_chat_ids, channel_list_json
    with open('channel_list.json', "w") as f:
        json.dump(channel_list_json, f, indent=4)
    with open("channel_list.json", "r") as f:
        channel_list_json = json.load(f)
        group_chat_ids = channel_list_json["group_chat_ids"]


bot = Client("55btcbot", api_id, api_hash, bot_token=bot_token)
print("Bot has strated...")


async def setup_commands():
    try:
        # Set commands for private chats
        await bot.set_bot_commands(commands=COMMANDS,
                                   scope=BotCommandScopeAllPrivateChats())

        # Set the menu button using the correct method
        await bot.set_chat_menu_button(
            chat_id=None,  # None means default for all chats
            menu_button=MenuButtonDefault())

        print("Bot commands and menu button set up successfully!")
    except Exception as e:
        print(f"Error setting up commands: {e}")


global is_first_time
is_first_time = True


@bot.on_message(filters.command('start') & filters.private)
async def start_command(bot, message):
    global is_first_time
    global keyboard

    keyboard = InlineKeyboardMarkup(
        [[
            InlineKeyboardButton("Start the bot 🚀", callback_data='turn_on'),
            InlineKeyboardButton("Turn Off 🔌", callback_data='turn_off')
        ],
         [
             InlineKeyboardButton("Add/Remove/Show admins 🛡️",
                                  callback_data='admins_part')
         ],
         [
             InlineKeyboardButton("Add/Remove/Show channels/groups 📡",
                                  callback_data='channels_part')
         ], [InlineKeyboardButton("ℹ️ Help", callback_data="help")]])

    if message.from_user.id in super_admin_list:
        if is_first_time == True:
            await setup_commands()
            is_first_time = False
        else:
            pass
        await bot.send_message(message.chat.id,
                               "Choose an action: ",
                               reply_markup=keyboard)
    else:
        bot.send_message(message.chat.id,
                         'You are not authorized to use this bot.')
        if message.forward_from:
            id = message.forward_from.id
            await bot.send_message(message.chat.id, f'The Id is : `{id}`')
        else:
            id = message.from_user.id
            await bot.send_message(message.chat.id, f'Your Id is : `{id}`')


#=================================================================================================================================================
@bot.on_message(filters.command('activate'))
def start_command(bot, message):
    global keyboard
    bot.send_message(message.chat.id, "Activated 👍")


#=================================================================================================================================================
@bot.on_message(filters.command('id'))
def start_command(bot, message):
    global keyboard
    id = bot.get_chat(message.chat.id)
    bot.send_message(message.chat.id, id.id)
    print('ID: ', id.id)


#=================================================================================================================================================
@bot.on_message(filters.command('add_admin') & filters.private)
def start_command(bot, message):
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("admins section 🆙",
                                 callback_data='admins_part'),
            InlineKeyboardButton("Main Menu 🔝", callback_data='main_menu')
        ],
    ])
    if message.from_user.id in super_admin_list:
        print("\n")
        command = message.text
        # Split the string by space and get the second part
        number = command.split()[1]
        if number.isnumeric():
            new_admin_id = number
            admins_list.append(int(new_admin_id))
            update_admin_json()
            print("------------------------")
            print("New Admin Added!", number)
            print(admins_list)
            print("------------------------")
            bot.send_message(message.chat.id, new_admin_id)
            bot.send_message(message.chat.id, "Done👍", reply_markup=keyboard)
        else:
            message.reply_text("Invalid ID. Please send a numebrs only ID.",
                               reply_markup=keyboard)
            return
    else:
        bot.send_message(message.chat.id,
                         'You are not authorized to use this bot.')
        if message.forward_from:
            id = message.forward_from.id
            bot.send_message(message.chat.id, f'The Id is : `{id}`')
        else:
            id = message.from_user.id
            bot.send_message(message.chat.id, f'Your Id is : `{id}`')


#=================================================================================================================================================
@bot.on_message(filters.command('remove_admin'))
def start_command(bot, message):
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("admins section 🆙",
                                 callback_data='admins_part'),
            InlineKeyboardButton("Main Menu 🔝", callback_data='main_menu')
        ],
    ])
    if message.from_user.id in super_admin_list:
        print("\n")
        command = message.text
        # Split the string by space and get the second part
        number = command.split()[1]
        if number.isnumeric():
            old_admin_id = number
            admins_list.remove(int(old_admin_id))
            update_admin_json()
            print("------------------------\nOld Admin Deleted!", number)
            print(admins_list)
            print("------------------------")
            bot.send_message(message.chat.id, old_admin_id)
            bot.send_message(message.chat.id, "Done👍", reply_markup=keyboard)
        else:
            message.reply_text("Invalid ID. Please send a numebrs only ID.",
                               reply_markup=keyboard)
            return
    else:
        bot.send_message(message.chat.id,
                         'You are not authorized to use this bot.')
        if message.forward_from:
            id = message.forward_from.id
            bot.send_message(message.chat.id, f'The Id is : `{id}`')
        else:
            id = message.from_user.id
            bot.send_message(message.chat.id, f'Your Id is : `{id}`')


#=================================================================================================================================================
@bot.on_message(filters.command('start_signals'))
def start_command(bot, message):
    try:
        if message.from_user.id in admins_list:
            if message.chat.id in group_chat_ids:
                bot.send_message(message.chat.id,
                                 'channel/grooup is already added!')
                bot.send_message(message.chat.id, 'Starting...')
            else:
                group_chat_ids.append(int(message.chat.id))
                update_channels_json()
            print(group_chat_ids)
    except AttributeError:
        if message.chat.id in group_chat_ids:
            bot.send_message(message.chat.id,
                             'channel/grooup is already added!')
            bot.send_message(message.chat.id, 'Starting...')
        else:
            group_chat_ids.append(int(message.chat.id))
            update_channels_json()
        print(group_chat_ids)


#=================================================================================================================================================
@bot.on_message(filters.command('stop_signals'))
def start_command(bot, message):
    try:
        if message.from_user.id in admins_list:
            group_chat_ids.remove(int(message.chat.id))
            update_channels_json()
            print(group_chat_ids)
            bot.send_message(message.chat.id, 'Stoping...')
    except AttributeError:
        group_chat_ids.remove(int(message.chat.id))
        update_channels_json()
        print(group_chat_ids)
        bot.send_message(message.chat.id, 'Stoping...')


#============================================================================================================================
@bot.on_message(filters.command('start_signals_pre'))
def start_command(bot, message):
    global pre_message
    try:
        if message.from_user.id in admins_list:
            if message.chat.id in group_chat_ids:
                bot.send_message(message.chat.id,
                                 'channel/grooup is already added!')
                bot.send_message(message.chat.id, 'Starting...')
            else:
                group_chat_ids.append(int(message.chat.id))
                update_channels_json()
            print(group_chat_ids)
            bot.send_message(message.chat.id, pre_message["pre_message"])
    except AttributeError:
        if message.chat.id in group_chat_ids:
            bot.send_message(message.chat.id,
                             'channel/grooup is already added!')
            bot.send_message(message.chat.id, 'Starting...')
        else:
            group_chat_ids.append(int(message.chat.id))
            update_channels_json()
        print(group_chat_ids)
        bot.send_message(message.chat.id, pre_message["pre_message"])


#================================================================================================================================
@bot.on_message(filters.command('add_id'))
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
            if channel_id not in group_chat_ids:
                try:
                    # Try to get chat info to verify the ID is valid
                    chat = await client.get_chat(int(channel_id))
                    group_chat_ids.append(int(channel_id))
                    update_channels_json()
                    await message.reply_text(
                        f"Successfully added ID: {channel_id} 👍")
                except Exception as e:
                    await message.reply_text(
                        "❌ Error: Could not verify this ID. Make sure the bot is a member of the channel/group."
                    )
            else:
                await message.reply_text(
                    f"This ID '{channel_id}' is already added.")
        except (ValueError, IndexError):
            await message.reply_text(
                "❌ Invalid ID format. Please provide a valid ID number.\nExample: `/add_id -100123456789`"
            )
    else:
        await message.reply_text(
            "❌ Please provide an ID after the command.\nExample: `/add_id -100123456789`"
        )


#================================================================================================================================
@bot.on_message(filters.command('remove_id'))
async def remove_id(client, message):
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
            if channel_id in group_chat_ids:
                try:
                    # Try to get chat info to verify the ID is valid
                    # chat = await client.get_chat(int(channel_id))
                    group_chat_ids.remove(int(channel_id))
                    update_channels_json()
                    await message.reply_text(
                        f"Successfully removed ID: {channel_id} 👍")
                except Exception as e:
                    await message.reply_text(
                        "❌ Error: Could not verify this ID. Make sure the bot is a member of the channel/group."
                    )
            else:
                await message.reply_text(
                    f"This ID '{channel_id}' is not added.")
        except (ValueError, IndexError):
            await message.reply_text(
                "❌ Invalid ID format. Please provide a valid ID number.\nExample: `/remove_id -100123456789`"
            )
    else:
        await message.reply_text(
            "❌ Please provide an ID after the command.\nExample: `/remove_id -100123456789`"
        )


#================================================================================================================================
@bot.on_message(filters.command('add_chat_id'))
def add_id(bot, message):
    channel_id = str(
        message.chat.id)  # Ensure the ID is a string for consistent key usage
    if channel_id not in group_chat_ids:
        print(channel_id)
        group_chat_ids.append(int(channel_id))
        update_channels_json()
        bot.send_message(message.chat.id, "Added 👍")
    else:
        bot.send_message(message.chat.id,
                         f"This ID is '{channel_id}' already added.")


#================================================================================================================================================================================================
# Define the help message
HELP_MESSAGE = """
🤖 **MetaeggBR Bot - Complete Guide**

Welcome to the MetaeggBR Bot! Here's a comprehensive guide on how to use the commands:

💡 **General commands :**
- **/start** - Start the bot and display the main menu.
- **/help** - Show this help message.
- **/activate** - Activate the bot in the current chat.
- **/id** - Get the chat ID of the current chat.
- **/add_admin** (ID) - Add a new admin by user ID.
- **/remove_admin** (ID) - Remove an admin by user ID.
- **/start_signals** - Start sending signals in the current chat.
- **/stop_signals** - Stop sending signals in the current chat.
- **/start_signals_pre** - Start sending pre-defined signals in the current chat.
- **/add_id** (ID) - Add a new channel/group by ID.
- **/add_chat_id** - Add the current chat ID to the list of channels/groups.
- **/remove_id** (ID) - Remove channel/group by ID.

**Buttons:**
  - **Start the bot 🚀**: Start the bot.
  - **Turn Off 🔌**: Turn off the bot.
  - **Add/Remove/Show admins 🛡️**: Manage admins.
  - **Add/Remove/Show channels/groups 📡**: Manage channels/groups.
"""


# Create a new command handler for the /help command
@bot.on_message(filters.command('help') & filters.private)
async def help_command(bot, message):
    await bot.send_message(message.chat.id, HELP_MESSAGE)


@bot.on_callback_query(filters.regex("help"))
async def help_text(bot, callback_query):
    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton("Back 🔙", callback_data='main_menu')]], )
    await callback_query.message.edit_text(HELP_MESSAGE, reply_markup=keyboard)


# Handling button clicks
@bot.on_callback_query()
def handle_button_click(bot, callback_query):
    data = callback_query.data
    if data == 'turn_on':
        keyboard = InlineKeyboardMarkup(
            [[
                InlineKeyboardButton("Start the bot 🚀",
                                     callback_data='turn_on'),
                InlineKeyboardButton("Turn Off 🔌", callback_data='turn_off')
            ],
             [
                 InlineKeyboardButton("Add/Remove/Show admins 🛡️",
                                      callback_data='admins_part')
             ],
             [
                 InlineKeyboardButton("Add/Remove/Show channels/groups 📡",
                                      callback_data='channels_part')
             ]])
        bot.send_message(callback_query.message.chat.id, "Starting...")
        bot.send_message(
            callback_query.message.chat.id,
            "Please be patient for the next signal to be puplished it may take 3 minutes",
            reply_markup=keyboard)
        data_valuse["loop"] = 0
        write_json_file("data.json", data_valuse)

        async def send_messages_concurrently(group_chat_id, message):

            async def print_chat_name(chat_id):
                try:
                    chat = await bot.get_chat(chat_id)
                    chat_name = chat.title or chat.first_name or "No name"
                    the_info = f"Chat Name: {chat_name}, Chat ID: {chat_id}"
                    return the_info
                except Exception as e:
                    # print(f"Error fetching chat name for ID {chat_id}: {e}")
                    the_info = f"Chat Name: Unknown, Chat ID: {chat_id}"
                    return the_info

            try:
                await bot.send_message(group_chat_id, message)
                the_info = await print_chat_name(group_chat_id)
                info = f'- Successfully broadcast to {the_info}'
                print(info)
            except Exception as e:
                the_info = await print_chat_name(group_chat_id)
                print(
                    f"- Error broadcasting to {the_info}:\nPlease make sure the bot is in the desired channel and is an admin in it. If it doesn't work, try sending the command /activate or /id and try again.\n"
                )

        async def send_message_to_telegram(message):
            tasks = [
                send_messages_concurrently(group_chat_id, message)
                for group_chat_id in group_chat_ids
            ]
            await asyncio.gather(*tasks)

        async def check_loop_and_stop():
            """Checks the loop value from a JSON file and stops the loop if it's 1."""
            loop_value = data_valuse["loop"]
            if loop_value == 1:
                print("Bot stopped successfully.")
                await asyncio.sleep(0)  # Yield control back to the event loop
                raise asyncio.CancelledError  # Signal for loop termination

        async def main():
            global latest_order_id
            global new_data_processed

            import requests
            import json
            import time

            # Global variable to store the latest order_id
            latest_order_id = None

            # Flag to indicate whether new data has been processed
            new_data_processed = False

            global start_time, end_time, issue
            start_time = 1740227344593
            end_time = 1740227344593
            issue = 12345

            def robust_requests_get(url, **kwargs):
                max_retries = 10
                for attempt in range(max_retries):
                    try:
                        response = requests.get(url, **kwargs)
                        
                        # Check for 401 Unauthorized and attempt relogin
                        if response.status_code == 401:
                            print(f"[PyroBuddy] 401 Unauthorized detected, attempting relogin...")
                            new_token = login_to_coinvid()
                            if new_token:
                                # Update headers with new token and retry
                                if 'headers' in kwargs:
                                    kwargs['headers']['blade-auth'] = new_token
                                response = requests.get(url, **kwargs)
                                if response.status_code == 200:
                                    print(f"[PyroBuddy] Request successful after relogin")
                                    return response
                        
                        # Check for other error status codes
                        if response.status_code >= 400:
                            print(f"[PyroBuddy] HTTP error {response.status_code}: {response.text}")
                            if attempt < max_retries - 1:
                                time.sleep(2)
                                continue
                        
                        return response
                    except requests.exceptions.RequestException as e:
                        print(f"[PyroBuddy] Network error: {e}. Attempt {attempt+1}/{max_retries}")
                        if attempt < max_retries - 1:
                            time.sleep(2)
                        else:
                            print("[PyroBuddy] Max retries reached, skipping this request.")
                            return None

            def fetch_data():
                global start_time, end_time
                url = "https://m.coinvidg.com/api/rocket-api/option/getInfo?symbol=BTC%2FUSDT"
                headers = get_headers_with_auth()
                # Set up parameters and proxy
                # params = {"subServiceCode": "RG1M", "size": "1"}
                proxy = "85.254.13.12:59100"
                username = "coinvidhosting"
                password = "paPJV3Jfkk"

                # Proxy setup
                proxies = {
                    "http": f"http://{username}:{password}@{proxy}",
                    "https": f"http://{username}:{password}@{proxy}"
                }

                session = requests.Session(
                )  # Create a session to manage connections
                session.proxies.update(
                    proxies)  # Attach the proxy to the session

                response = robust_requests_get(url, headers=headers, timeout=30)
                if response is None:
                    print("[PyroBuddy] fetch_data: No response received")
                    return None
                
                try:
                    data = response.json()
                    if 'data' not in data or 'oneMinCurrentIssueDetail' not in data['data']:
                        print(f"[PyroBuddy] fetch_data: Invalid data structure: {data}")
                        return None
                    
                    start_time = data['data']['oneMinCurrentIssueDetail']['startTime']
                    end_time = data['data']['oneMinCurrentIssueDetail']['endTime']
                    return data
                except Exception as e:
                    print(f"[PyroBuddy] fetch_data: Error parsing response: {e}")
                    return None

            global resualt
            resualt = 'white'
            global open_price_2, close_price_2
            open_price_2, close_price_2 = 0, 0

            def signal_data(start_time, end_time):
                global resualt
                global open_price_2, close_price_2
                end_time2 = end_time - 60000
                url = f"https://m.coinvid.com/api/rocket-api/contract/market/kline-history?symbol=BTC/USDT&from=1740215361077&to={end_time2}&period=1min"
                headers = get_headers_with_auth()
                proxy = "85.254.13.12:59100"
                username = "coinvidhosting"
                password = "paPJV3Jfkk"

                # Proxy setup
                proxies = {
                    "http": f"http://{username}:{password}@{proxy}",
                    "https": f"http://{username}:{password}@{proxy}"
                }
                
                response = robust_requests_get(url, headers=headers, timeout=30)
                data = response.json()
                print(data)
                if response is None:
                    print("[signal_data] Failed to fetch data after retries. Skipping.")
                    return
                try:
                    data = response.json()
                except Exception as e:
                    print(f"[signal_data] Failed to parse response: {e}")
                    return

                print("Start Time:", start_time)
                print("End Time:", end_time)
                # print("Data:", data)
                # # Extract last two candles
                last_two = data["data"][-10:]
                red = 0
                green = 0
                # # Determine candle colors
                for i, candle in enumerate(last_two, start=1):
                    time, open_price, close_price = candle[0], candle[
                        1], candle[4]
                    color = "Long 🟢" if close_price > open_price else "Short 🔴"
                    if close_price == open_price:
                        color = "Doji"
                    if color == "Red":
                        red += 1
                    if color == "Green":
                        green += 1
                    # if time == end_time or time == start_time:
                    # print(f"Candle {i}: {color} and time {time}")

                    if i == 9:
                        resualt = color
                        resualt_candle = candle
                        open_price_2, close_price_2 = open_price, close_price

                print(f'\nThe result is: {resualt}, {resualt_candle}')
                print(f"Red: {red}")
                print(f"Green: {green}")
                checked = True

                # print(f"\n The resualt: {resualt}")

            global last_issue_no
            last_issue_no = None
            global checked
            checked = True

            def process_data(data):
                global start_time, end_time
                global new_data_processed, issue
                global last_issue_no  # Access the global variable
                global checked
                global start_time, end_time
                if data is None:
                    print("Error: Received None data. Retrying...")
                    return False  # Exit the function if data is None

                try:
                    current_issue_no = data.get('data', {}).get('oneMinCurrentIssueDetail', {}).get('issueNo')
                except AttributeError:
                    print("Error: Unable to extract issue number. Retrying...")
                    return False  # Exit the function if an error occurs

                if current_issue_no is None:
                    return False  # No issue number found in the data

                if last_issue_no is None:
                    last_issue_no = current_issue_no
                    return False  # First time checking, no previous issue to compare

                if checked == True:
                    start_time = data['data']['oneMinCurrentIssueDetail'][
                        'startTime']
                    end_time = data['data']['oneMinCurrentIssueDetail'][
                        'endTime']
                    print(f"Start Time: {start_time}")
                    print(f"End Time: {end_time}")

                    checked = False

                if current_issue_no == last_issue_no + 2 or current_issue_no > last_issue_no + 2:
                    last_issue_no = current_issue_no
                    new_data_processed = True
                    issue = current_issue_no
                    return  # Issue number has changed
                else:
                    print(current_issue_no)
                    print(last_issue_no)

                return False

            async def phases2():
                await check_loop_and_stop()
                global new_data_processed
                while True:
                    await check_loop_and_stop()
                    data = fetch_data()
                    process_data(data)
                    time.sleep(2)
                    print(1)
                    if new_data_processed:
                        new_data_processed = False  # Reset flag for next iteration
                        time.sleep(4)
                        signal_data(start_time, end_time)
                        break
                await check_loop_and_stop()

            await send_message_to_telegram("Starting...🚀")

            consecutive_losses = 0
            results_history = []
            wins_history = []

            # List to store detailed information about the last 20 signals
            detailed_results_history = []
            global highest_stage
            highest_stage = 1
            global Signals_Count
            global pre_consecutive_losses
            pre_consecutive_losses = 0
            Signals_Count = 0

            async def lose_counter(trade_selection, pre_extracted_time):
                global consecutive_losses
                global pre_consecutive_losses
                global Result_W_L
                global highest_stage
                global Signals_Count

                if trade_selection == resualt:
                    consecutive_losses = 0
                    results_history.append("Win")
                    Result_W_L = "🎉"
                elif resualt == 'Doji':
                    print('Doji 🤔')
                    results_history.append("Win")
                    Result_W_L = "🎉"
                else:
                    consecutive_losses += 1
                    results_history.append("Lose")
                    Result_W_L = "💔"
                    pre_consecutive_losses = consecutive_losses
                Signals_Count += 1
                print("Signals_Count : ", Signals_Count)
                if consecutive_losses > highest_stage:
                    highest_stage = consecutive_losses + 1
                if pre_extracted_time == None:
                    pass
                else:

                    print('Histroy count : ', len(results_history))
                    if Result_W_L == "🎉":
                        # Save detailed information for each signal
                        detailed_results_history.append({
                            'Issue No.':
                            pre_extracted_time,
                            'Prediction':
                            "🔴" if trade_selection == "Short 🔴" else "🟢",
                            'Result':
                            Result_W_L
                        })
                        # Recalculate statistics after each set of 20 signals

                        success_rate = (results_history.count("Win") /
                                        len(results_history)) * 100
                        stats_message = f'Statistics function\n'
                        last_20_entries = detailed_results_history[-20:]
                        for signal_info in last_20_entries:
                            stats_message += f"Issue No.: {signal_info['Issue No.']} Prediction{signal_info['Prediction']}Result{signal_info['Result']}\n"

                        await send_message_to_telegram(stats_message)
                    else:
                        pass

                return consecutive_losses, Result_W_L

            print(
                '============================================================')
            fetch_data()
            await phases2()
            pre_extracted_time = None
            trade_selection = 'Red'
            current_bet_value = 1
            Num_of_signals = 0
            first_time = 0
            Result_W_L = '🎉'
            while consecutive_losses < 100:
                if first_time == 1:
                    consecutive_losses, Result_W_L = await lose_counter(
                        trade_selection, pre_extracted_time)
                extracted_time = int(issue)
                print("The Num_of_signals = ", Num_of_signals)
                words = ["Long 🟢", "Short 🔴"]

                trade_selection = random.choice(words)

                print("trade selection: ", trade_selection)
                # Modify the print statements to send messages to Telegram
                if Result_W_L == "💔":
                    current_bet_value *= Decimal('3')
                    current_bet_value = current_bet_value.quantize(
                        Decimal('1.00'), rounding=ROUND_HALF_UP)
                    if consecutive_losses >= 7:
                        current_bet_value = 1

                    result = f"""
✅Open Price: {open_price_2}

❎Close Price: {close_price_2}

➡️RESUALT: {resualt} Lose💔"""
                    message1 = f'''
✨1min BINARY OPTION✨

💱 BTC/USDT 💱            

🔝 Period : {extracted_time}

🌡 Choose : {trade_selection}

⬆️ Stage :       X{current_bet_value}

🤲🤲 I recommend everyone to use the 3X plan for 30% - 50% guarantee of your profits 💸💸  Manage your funds 🤝
                        '''

                    await send_message_to_telegram(result)
                    time.sleep(0.1)
                    await send_message_to_telegram(message1)
                    pre_extracted_time = extracted_time
                    print('fail!')
                    Num_of_signals += 1
                    await phases2()
        #=================================================================================
                else:
                    current_bet_value = 1
                    result = f"""
✅Open Price: {open_price_2}

❎Close Price: {close_price_2}

➡️RESUALT: {resualt} Win🎉"""
                    message1 = f'''
✨1min BINARY OPTION✨

💱 BTC/USDT 💱

🔝 Period : {extracted_time}

🌡 Choose : {trade_selection}

⬆️ Stage :       X{current_bet_value}

🤲🤲 I recommend everyone to use the 3X plan for 30% - 50% guarantee of your profits 💸💸  Manage your funds 🤝
                        '''

                    if first_time == 1:
                        await send_message_to_telegram(result)
                        time.sleep(0.1)
                        await send_message_to_telegram(message1)

                    else:
                        await send_message_to_telegram(result)
                        time.sleep(0.1)
                        await send_message_to_telegram(message1)
                        # await send_message_to_telegram(message1)
                        first_time = 1
                    pre_extracted_time = extracted_time
                    print('victory!')
                    Num_of_signals += 1
                    await phases2()

        # Run the main function using asyncio

        async def main_task():
            global task
            task = asyncio.create_task(main())
            await task
            print("Task completed.")

        # Run the main_task function
        asyncio.run(main_task())

#=================================================================================================================================================
    if data == 'turn_off':
        keyboard = InlineKeyboardMarkup(
            [[
                InlineKeyboardButton("Start the bot 🚀",
                                     callback_data='turn_on'),
                InlineKeyboardButton("Turn Off 🔌", callback_data='turn_off')
            ],
             [
                 InlineKeyboardButton("Add/Remove/Show admins 🛡️",
                                      callback_data='admins_part')
             ],
             [
                 InlineKeyboardButton("Add/Remove/Show channels/groups 📡",
                                      callback_data='channels_part')
             ]])
        data_valuse["loop"] = 1
        write_json_file("data.json", data_valuse)
        try:
            task.cancel()
        except:
            pass
        bot.send_message(callback_query.message.chat.id, "Done👍")
        bot.send_message(callback_query.message.chat.id,
                         "Choose an action:",
                         reply_markup=keyboard)

#=================================================================================================================================================
    if data == 'reaccumulating':
        #
        data_valuse["cumulative_profit"] = 0
        data_valuse["consecutive_wins"] = 0
        data_valuse["consecutive_losses"] = 0
        data_valuse["First-Time"] = 0
        write_json_file("data.json", data_valuse)
        reco = 0
        the_message = f"Accumulating Value: {reco}"
        bot.send_message(callback_query.message.chat.id, "Done👍")
        bot.send_message(callback_query.message.chat.id,
                         the_message,
                         reply_markup=keyboard)

#=================================================================================================================================================
    if data == 'accumulating_Value':
        reco = data_valuse["cumulative_profit"]
        the_message = f"Accumulating Value: {reco}"
        bot.send_message(callback_query.message.chat.id,
                         the_message,
                         reply_markup=keyboard)

#=================================================================================================================================================
    if data == 'admins_part':
        # Ask the admin to send the new admin ID or forward a message from the new admin
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("Add new admin 🆕👮‍♂️",
                                     callback_data='add_admin'),
                InlineKeyboardButton("Remove an admin  🗑️👮‍♂️",
                                     callback_data='remove_admin')
            ],
            [
                InlineKeyboardButton("Add super admin 🆕♕️👨‍✈️",
                                     callback_data='add_super_admin'),
                InlineKeyboardButton("Remove a super admin  🗑️♕️👨‍✈️",
                                     callback_data='remove_super_admin')
            ],
            [
                InlineKeyboardButton("Show super admins list 📋♕️👨‍✈️",
                                     callback_data='show_super_admins')
            ],
            [
                InlineKeyboardButton("Show admins list 📋👮‍♂️",
                                     callback_data='show_admins')
            ],
            [InlineKeyboardButton("Back 🔙", callback_data='main_menu')],
        ], )
        if 'Super Admins List' in callback_query.message.text or 'Admin List' in callback_query.message.text:
            callback_query.message.delete()
        else:
            callback_query.message.edit_text("Choose an action:",
                                             reply_markup=keyboard)

#=================================================================================================================================================
    if data == 'add_super_admin':
        # Ask the admin to send the new admin ID or forward a message from the new admin
        bot.send_message(
            callback_query.message.chat.id,
            "Please send the new admin's user ID.\nYou can obtain it by make the new admin send a private message to this bot and then send you his ID."
        )
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Back 🔙", callback_data='admins_part')],
        ])

        async def on_new_admin_message(client, message):
            if message.text.isnumeric():
                new_admin_id = message.text
                super_admin_list.append(int(new_admin_id))
                update_super_admin_json()
                print(super_admin_list)
                await bot.send_message(callback_query.message.chat.id,
                                       new_admin_id)
                await bot.send_message(callback_query.message.chat.id,
                                       "Done👍",
                                       reply_markup=keyboard)
                bot.remove_handler(event_handel_2, 4)

            else:
                await message.reply_text(
                    "Invalid ID. Please send a numebrs only ID.",
                    reply_markup=keyboard)
                bot.remove_handler(event_handel_2, 4)
                return

        # Listen for the next message
        global event_handel_2
        event_handel_2 = MessageHandler(on_new_admin_message)
        bot.add_handler(event_handel_2, 4)

#=================================================================================================================================================
    if data == 'remove_super_admin':
        # Ask the admin to send the new admin ID or forward a message from the new admin
        bot.send_message(
            callback_query.message.chat.id,
            "Please send the new admin's user ID.\nYou can obtain it by make the new admin send a private message to this bot and then send you his ID."
        )
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Back 🔙", callback_data='admins_part')],
        ])

        async def on_new_admin_message(client, message):
            if message.text.isnumeric():
                try:
                    old_admin_id = message.text
                    super_admin_list.remove(int(old_admin_id))
                    update_super_admin_json()
                    print(super_admin_list)
                    await bot.send_message(callback_query.message.chat.id,
                                           old_admin_id)
                    await bot.send_message(callback_query.message.chat.id,
                                           "Done👍",
                                           reply_markup=keyboard)
                    bot.remove_handler(event_handel_3, 5)
                except ValueError:
                    await message.reply_text(
                        "Invalid ID. Super admin is not in the admins list.",
                        reply_markup=keyboard)
                    bot.remove_handler(event_handel_3, 1)
            else:
                await message.reply_text(
                    "Invalid ID. Please send a numebrs only ID.",
                    reply_markup=keyboard)
                bot.remove_handler(event_handel_3, 5)
                return

        # Listen for the next message
        # @bot.on_message(group=5)
        global event_handel_3
        event_handel_3 = MessageHandler(on_new_admin_message)
        bot.add_handler(event_handel_3, 5)

#=================================================================================================================================================
    if data == 'add_admin':
        # Ask the admin to send the new admin ID or forward a message from the new admin
        bot.send_message(
            callback_query.message.chat.id,
            "Please send the new admin's user ID.\nYou can obtain it by make the new admin send a private message to this bot and then send you his ID."
        )
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Back 🔙", callback_data='admins_part')],
        ])

        async def on_new_admin_message(client, message):
            if message.text.isnumeric():
                new_admin_id = message.text
                admins_list.append(int(new_admin_id))
                update_admin_json()
                print("------------------------")
                print("New Admin Added!", new_admin_id)
                print(admins_list)
                print("------------------------")
                await bot.send_message(callback_query.message.chat.id,
                                       new_admin_id)
                await bot.send_message(callback_query.message.chat.id,
                                       "Done👍",
                                       reply_markup=keyboard)
                bot.remove_handler(event_hande_1)
            else:
                await message.reply_text(
                    "Invalid ID. Please send a numebrs only ID.",
                    reply_markup=keyboard)
                bot.remove_handler(event_hande_1)
                return

        global event_hande_1
        event_hande_1 = MessageHandler(on_new_admin_message)
        bot.add_handler(event_hande_1)

#=================================================================================================================================================
    if data == 'remove_admin':
        # Ask the admin to send the new admin ID or forward a message from the new admin
        bot.send_message(
            callback_query.message.chat.id,
            "Please send the new admin's user ID.\nYou can obtain it by reviewing the admin list."
        )
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Back 🔙", callback_data='admins_part')],
        ])

        async def delete_admin(client, message):
            if message.text.isnumeric():
                new_admin_id = message.text
                try:
                    admins_list.remove(int(new_admin_id))
                    update_admin_json()
                    print("------------------------")
                    print("Admin Removed!", new_admin_id)
                    print(admins_list)
                    print("------------------------")
                    await bot.send_message(callback_query.message.chat.id,
                                           new_admin_id)
                    await bot.send_message(callback_query.message.chat.id,
                                           "Done👍",
                                           reply_markup=keyboard)
                    bot.remove_handler(event_handel, 1)
                except ValueError:
                    await message.reply_text(
                        "Invalid ID. Admin is not in the admins list.",
                        reply_markup=keyboard)
                    bot.remove_handler(event_handel, 1)

            else:
                await message.reply_text(
                    "Invalid ID. Please send a numebrs only ID.",
                    reply_markup=keyboard)
                bot.remove_handler(event_handel, 1)
                return

        global event_handel
        event_handel = MessageHandler(delete_admin)
        bot.add_handler(event_handel, 1)

#=================================================================================================================================================
    if data == 'show_admins':
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Back 🔙", callback_data='admins_part')],
        ])

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
            for user_id in admins_list:
                user_info = await get_user_info(user_id)
                message += f"{user_info}\n"
            await bot.send_message(callback_query.message.chat.id,
                                   message,
                                   reply_markup=keyboard)

        asyncio.run(show_admins())

#=================================================================================================================================================
    if data == 'show_super_admins':
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Back 🔙", callback_data='admins_part')],
        ])

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
            message = "Super Admins List:\n"
            for user_id in super_admin_list:
                user_info = await get_user_info(user_id)
                message += f"{user_info}\n"
            await bot.send_message(callback_query.message.chat.id,
                                   message,
                                   reply_markup=keyboard)

        asyncio.run(show_admins())

#=================================================================================================================================================
    if data == 'channels_part':
        # Ask the admin to send the new admin ID or forward a message from the new admin
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("Add new channels/groups ➕📡",
                                     callback_data='add_channel')
            ],
            [
                InlineKeyboardButton("Remove channels/groups ➖📡",
                                     callback_data='remove_channel')
            ],
            [
                InlineKeyboardButton("Show channels/groups list 📃📡",
                                     callback_data='show_channels')
            ],
            [InlineKeyboardButton("Back 🔙", callback_data='main_menu')],
        ])
        if 'Super Admins List' in callback_query.message.text or 'Admin List' in callback_query.message.text:
            callback_query.message.delete()
        else:
            callback_query.message.edit_text("Choose an action:",
                                             reply_markup=keyboard)

#=================================================================================================================================================
    if data == 'add_channel':
        # Ask the admin to send the new admin ID or forward a message from the new admin
        bot.send_message(
            callback_query.message.chat.id,
            "Please send the new channel/group ID.\n if it a channel you can obtain it's id by forwrd a message from it to this bot https://t.me/getmyid_bot and then send me the ID.\nAnd if it was a group please add this bot to the gorup and make it admin and send the command `/id` in the chat to get the id"
        )
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Back 🔙", callback_data='channels_part')],
        ])

        async def on_new_admin_message(client, message):
            if len(message.text) > 0:
                new_channel_id = message.text
                print(new_channel_id)
                group_chat_ids.append(int(new_channel_id))
                update_channels_json()
                print(group_chat_ids)
                await bot.send_message(callback_query.message.chat.id,
                                       new_channel_id)

                await bot.send_message(callback_query.message.chat.id, "Done👍")
                await bot.send_message(
                    callback_query.message.chat.id,
                    "Please you must send the command `/activate` in the new channel after addin the bot to it to be activated",
                    reply_markup=keyboard)
                bot.remove_handler(event_handel_4, 2)
            else:
                await message.reply_text("Invalid ID.The id must be 13 digts.",
                                         reply_markup=keyboard)
                bot.remove_handler(event_handel_4, 2)
                return

        # Listen for the next message
        # @bot.on_message(group=2)
        global event_handel_4
        event_handel_4 = MessageHandler(on_new_admin_message)
        bot.add_handler(event_handel_4, 2)

#=================================================================================================================================================
    if data == 'remove_channel':
        # Ask the admin to send the new admin ID or forward a message from the new admin
        bot.send_message(
            callback_query.message.chat.id,
            "Please send the old channel/group ID.\n if it a channel you can obtain it \nPLease send the numbers only"
        )
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Back 🔙", callback_data='channels_part')],
        ])

        async def on_new_admin_message(client, message):
            if len(message.text) == 13:
                try:
                    new_channel_id = message.text
                    print(new_channel_id)
                    group_chat_ids.remove(int(new_channel_id))
                    update_channels_json()
                    print(group_chat_ids)
                    await bot.send_message(callback_query.message.chat.id,
                                           new_channel_id)
                    await bot.send_message(callback_query.message.chat.id,
                                           "Done👍",
                                           reply_markup=keyboard)
                    bot.remove_handler(event_handel_5, 3)
                except ValueError:
                    await message.reply_text(
                        "Invalid ID. channel/group ID is not in the channels/groups list.",
                        reply_markup=keyboard)
                    bot.remove_handler(event_handel_5, 3)
            else:
                await message.reply_text("Invalid ID.The id must be 13 digts.",
                                         reply_markup=keyboard)
                bot.remove_handler(event_handel_5, 3)
                return

        # Listen for the next message
        global event_handel_5
        event_handel_5 = MessageHandler(on_new_admin_message)
        bot.add_handler(event_handel_5, 3)

#=================================================================================================================================================
    if data == 'show_channels':
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Back 🔙", callback_data='channels_part')],
        ])

        async def get_chat_info(user_id):
            try:
                user = await bot.get_chat(user_id)
                username = user.username or "No username"
                first_name = user.title or "No first name"
                return f"@{username} , {first_name} , ID: {user_id}\n"
            except errors.FloodWait as e:
                print(f"Rate limit exceeded. Waiting for {e.x} seconds.")
                await asyncio.sleep(e.x)
                return await get_chat_info(user_id)  # Retry after sleep
            except Exception:
                return f"@Unknown , Unknown , ID: {user_id}\n"

        async def show_chats():
            message = "Admin List:\n"
            for chat_id in group_chat_ids:
                user_info = await get_chat_info(chat_id)
                message += f"{user_info}\n"
            await bot.send_message(callback_query.message.chat.id,
                                   message,
                                   reply_markup=keyboard)

        asyncio.run(show_chats())


# #=================================================================================================================================================
    if data == 'main_menu':
        keyboard = InlineKeyboardMarkup(
            [[
                InlineKeyboardButton("Start the bot 🚀",
                                     callback_data='turn_on'),
                InlineKeyboardButton("Turn Off 🔌", callback_data='turn_off')
            ],
             [
                 InlineKeyboardButton("Add/Remove/Show admins 🛡️",
                                      callback_data='admins_part')
             ],
             [
                 InlineKeyboardButton("Add/Remove/Show channels/groups 📡",
                                      callback_data='channels_part')
             ]])
        callback_query.message.edit_text("Choose an action:",
                                         reply_markup=keyboard)

bot.run()
