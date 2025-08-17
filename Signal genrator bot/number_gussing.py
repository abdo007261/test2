# number_guessing_telethon.py
import os
import json
import time
import random
import threading
import requests
import asyncio

from telethon import TelegramClient, events, Button

# ——————————————————————————————————————————————————
# 1) CONFIGURATION (fill in your own or via env‐vars)
# ——————————————————————————————————————————————————
API_ID = 27112006
API_HASH = "0d1019d7ca92aef12571c82cd163d2bd"

BOT_TOKEN = "6860661147:AAFRmCFOuCcBvH2vaJ47mGy8iEAWhm190iU"

# The channel where signals are posted (use an integer here)
TARGET_CHANNEL_ID = -1002018963230

# Only these users can /start the bot
ALLOWED_USERS = {1602528125, 6378849563}

# Simple JSON‐backed "loop" flag (your existing data.json)
DATA_FILE = "data.json"
with open(DATA_FILE, "r") as f:
    data_values = json.load(f)

def write_json(file_path, data):
    with open(file_path, "w") as f:
        json.dump(data, f, indent=2)

# Global control flag for your background logic
exit_flag = False
latest_issue = None
consecutive_losses = 0

# ——————————————————————————————————————————————————
# 2) TELETHON CLIENT SETUP
# ——————————————————————————————————————————————————
client = TelegramClient("bot_session3", API_ID, API_HASH)

@client.on(events.NewMessage(pattern=r"^/start$"))
async def start_handler(event):
    """
    When a user sends /start, show them an inline keyboard
    with Turn On / Turn Off buttons.
    """
    uid = event.sender_id
    if uid not in ALLOWED_USERS:
        await event.reply("You are not authorized to use this bot.")
        return

    buttons = [
        [Button.inline("Turn On ▶", b"turn_on")],
        [Button.inline("Turn Off ⏹", b"turn_off")],
    ]
    await event.reply(
        f"Hello, {event.sender.first_name}!\nChoose an option:",
        buttons=buttons
    )

@client.on(events.CallbackQuery)
async def callback_handler(event):
    """
    Handle clicks on our inline buttons.
    """
    global exit_flag, data_values
    data = event.data.decode()

    if data == "turn_on":
        # ack & edit the message
        await event.answer("Turning on the bot…")
        # replace buttons with just Turn Off
        buttons = [[Button.inline("Turn Off ⏹", b"turn_off")]]
        await event.edit("Starting…\nPlease be patient, first signal may take 2 min.", buttons=buttons)

        # reset our loop flag
        exit_flag = False
        data_values["loop"] = 0
        write_json(DATA_FILE, data_values)

        # launch background task
        client.loop.create_task(main2())

    elif data == "turn_off":
        await event.answer("Turning off the bot…")
        # flip the JSON flag
        data_values["loop"] = 1
        write_json(DATA_FILE, data_values)

        # signal background logic to exit
        exit_flag = True
        # restore buttons
        buttons = [[Button.inline("Turn On ▶", b"turn_on")]]
        await event.edit("Bot stopped successfully.", buttons=buttons)

    else:
        await event.answer("Unknown action")

# ——————————————————————————————————————————————————
# 3) YOUR EXISTING BACKGROUND LOGIC
# ——————————————————————————————————————————————————
async def main2():
    """
    This coroutine should mimic your old main2() + main_async().
    Use `exit_flag` and `data_values["loop"]` to break out.
    Whenever you used `await send_message_to_telegram(msg)`,
    just do:
        await client.send_message(TARGET_CHANNEL_ID, msg)
    """
    async def send_message_to_telegram(message):
        await client.send_message(TARGET_CHANNEL_ID, message)
    
    # Example start-up message
    await client.send_message(TARGET_CHANNEL_ID, "Starting…🚀")

    # Example loop (replace with your actual fetch/process)
    while not exit_flag and data_values.get("loop", 0) == 0:
        # 1) fetch remote data
            async def check_loop_and_stop():
                    """Checks the loop value from a JSON file and stops the loop if it's 1."""
                    loop_value = data_values["loop"]
                    if loop_value == 1:
                        print("Bot stopped successfully.")
                        await asyncio.sleep(
                            0)  # Yield control back to the event loop
                        return  # Return without raising CancelledError

            # Flag to indicate whether new data has been processed
            new_data_processed = False
            FILE_PATH = "data_red_green_1m.json"

            def ensure_json_file():
                """Ensure the JSON file exists with an empty dictionary if not present."""
                if not os.path.exists(FILE_PATH):
                    with open(FILE_PATH, "w") as file:
                        json.dump({}, file)

            def update_json(data_to_fill):
                """Update the JSON file with a new key-value pair."""
                ensure_json_file()
                with open(FILE_PATH, "r") as file:
                    data = json.load(file)

                data = data_to_fill  # Update the key with the new value

                with open(FILE_PATH, "w") as file:
                    json.dump(data, file, indent=4)

            url = "https://m.coinvidg.com/api/rocket-api/game/issue-result/page"

            params = {"subServiceCode": "RG1M", "size": "1", "current": "1"}

            headers = {
                "accept": "application/json, text/plain, */*",
                "authorization": "Basic cm9ja2V0X3dlYjpyb2NrZXRfd2Vi",
                "user-agent":
                "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36...",
                "referer":
                "https://m.coinvidg.com/game/guessMain?gameName=RG1M&returnUrl=%2FgameList",
                "host": "m.coinvidg.com",
                "connection": "keep-alive",
                "cookie": "JSESSIONID=0AkjLljW2FNgeVLmOPWYudZwXcbZbjx9yxUrwMWE"
            }
            cookies = {
                "_fbp": "fb.1.1713463717428.1896775221",
                "JSESSIONID": "LjPmS6aEznOtW2SjOdhl-bM5q905w0XyfoEJcanF"
            }
            proxy = "85.254.13.12:59100"
            username = "coinvidhosting"
            password = "paPJV3Jfkk"
            proxies = {
                "http": f"http://{username}:{password}@{proxy}",
                "https": f"http://{username}:{password}@{proxy}"
            }

            def fetch_data():
                session = requests.Session(
                )  # Create a session to manage connections
                # session.proxies.update(
                #     proxies)  # Attach the proxy to the session

                MAX_RETRIES = 60
                for attempt in range(MAX_RETRIES):
                    try:
                        response = session.get(url,
                                               headers=headers,
                                               params=params,
                                               cookies=cookies,
                                               timeout=10)
                        response.raise_for_status()
                        update_json(response.json())
                        return response.json()

                    except (requests.exceptions.ConnectionError,
                            requests.exceptions.Timeout) as e:
                        print(
                            f"⚠ Connection issue detected: {e}. Restarting session with proxy..."
                        )
                        session.close()  # Close the session
                        session = requests.Session()  # Recreate the session
                        session.proxies.update(proxies)  # Re-attach proxy
                        time.sleep(2)  # Wait before retrying

                    except requests.exceptions.RequestException as e:
                        print(f"❌ Unrecoverable error: {e}")
                        break

                return None  # Return None if all retries fail

            global colors
            colors = None

            def generate_signal():
                numbers = random.sample(range(0, 10), 5)
                numbers.sort()
                return numbers

            def process_data(data):
                global latest_issue, new_data_processed, value_number, issue_number, colors
                if data and 'data' in data and 'records' in data['data']:
                    records = data['data']['records']
                    if records:
                        last_record = records[0]
                        # Check if the issue number is newer than the latest_issue
                        if latest_issue is None or last_record[
                                'issue'] > latest_issue:
                            # Update the latest_issue
                            latest_issue = last_record['issue']
                            # Extract the resultFormatValueI18n list
                            result_format = last_record['value']
                            if result_format == None:
                                while result_format == None:
                                    print("reeult is None. Retrying...")
                                    time.sleep(2)
                                    respnse = fetch_data()
                                    result_format = respnse['data']['records'][
                                        0]['value']
                            else:
                                pass

                            print("the result:", result_format)
                            clean_string = result_format.replace(" ", "")
                            # Convert to integer
                            value_number = int(clean_string)
                            # colors = ("GREEN   🟢" if int(value_number) % 2 else "RED   🔴")

                            issue_number = last_record['issue']
                            # Print assigned variables
                            # print("Issue number:", issue_number)
                            # print("The colors: ",colors)

                            print()
                            # Set flag to indicate new data processed
                            new_data_processed = True
                            # Break out of the loop after processing new data
                            return

            async def phases2():
                await check_loop_and_stop()
                global new_data_processed
                while True:
                    await check_loop_and_stop()
                    if data_values["loop"] == 1:
                        print("Breaking out of phases2 function.")
                        break

                    await asyncio.sleep(1)  # wait for 1 second
                    data = fetch_data()
                    process_data(data)
                    if new_data_processed:
                        new_data_processed = False  # Reset flag for next iteration
                        break

            detailed_results_history = []
            global highest_stage
            highest_stage = 1
            global Signals_Count
            Signals_Count = 0
            results_history = []
            global wins_history
            wins_history = []
            global pre_consecutive_losses
            pre_consecutive_losses = 0
            global consecutive_wins
            consecutive_wins = 0

            async def lose_counter(trade_selection, pre_extracted_time):
                global consecutive_losses
                global Result_W_L
                global pre_consecutive_losses
                global highest_stage
                global consecutive_wins
                global Signals_Count
                extracted_num = value_number

                if extracted_num in trade_selection:
                    consecutive_losses = 0
                    consecutive_wins += 1
                    results_history.append("Win")
                    Result_W_L = "🎉"
                else:
                    consecutive_losses += 1
                    consecutive_wins = 0
                    pre_consecutive_losses = consecutive_losses
                    results_history.append("Lose")
                    Result_W_L = "💔"
                Signals_Count += 1
                print(
                    "############################################################################"
                )
                print("Signals_Count : ", Signals_Count)
                print("Consecutive_Wins : ", consecutive_wins)
                print("Consecutive_Losses : ", consecutive_losses)
                # print("")
                # print("----------------")
                print('RESUALT: ', value_number)
                if consecutive_losses > highest_stage:
                    highest_stage = consecutive_losses + 1
                if pre_extracted_time == None:
                    pass
                else:
                    # Save detailed information for each signal
                    detailed_results_history.append({
                        'Issue No.': pre_extracted_time,
                        'Prediction': trade_selection,
                        'Result': Result_W_L
                    })

                    if Result_W_L == "🎉":
                        # Recalculate statistics after each set of 20 signals
                        if pre_consecutive_losses > highest_stage:
                            highest_stage = pre_consecutive_losses + 1
                        # Recalculate statistics after each set of 20 signals
                        wins_history.append({
                            'Issue No.':
                            pre_extracted_time + 1,
                            'Result':
                            Result_W_L,
                            'phase_Num':
                            pre_consecutive_losses + 1,
                        })
                        pre_consecutive_losses = 0

                        stats_message = f'Statistics function\n'
                        last_20_entries = wins_history[-20:]
                        for signal_info in last_20_entries:
                            stats_message += f"Period: {signal_info['Issue No.']} Result🎉 in {signal_info['phase_Num']} Phase \n"
                        stats_message += f'\nIn the last {len(results_history)} , {results_history.count("Win")} were successful up to {highest_stage} stages.\n'
                        # Reset results_history and detailed_results_history for the next 20 signals
                        await send_message_to_telegram(stats_message)
                    else:
                        pass

                return consecutive_losses, Result_W_L

            global current_bet_value, trade_selection, pre_extracted_time, first_time
            current_bet_value = 1
            pre_extracted_time = None
            trade_selection = generate_signal()
            await phases2()
            first_time = 0

            # async def main_async():
            # global pre_extracted_time, first_time, trade_selection, current_bet_value, exit_flag

            while not exit_flag:
                await check_loop_and_stop()
                extracted_time = issue_number + 1
                if first_time == 1:
                    await lose_counter(trade_selection, pre_extracted_time)
                else:
                    time.sleep(3.5)

                if consecutive_losses > 1 or consecutive_losses == 1:
                    trade_selection = generate_signal()
                    current_bet_value *= 3
                    current_bet_value = round(current_bet_value, 2)
                    result = f'RESUALT: {value_number}'
                    message = 'Lose💔'
                    message1 = f'''
🔝 Period : {extracted_time}

🌡 Choose :    {trade_selection}

⬆️ Stage :    X{current_bet_value}

🤲🤲 I recommend everyone to use the 3X plan for 30% - 50% guarantee of your profits 💸💸  Manage your funds 🤝
            '''

                    await send_message_to_telegram(result)
                    time.sleep(0.1)
                    await send_message_to_telegram(message)
                    time.sleep(0.1)
                    await send_message_to_telegram(message1)
                    time.sleep(0.1)
                    pre_extracted_time = extracted_time
                    print('fail!')
                    print(f"Current Issue id: {issue_number}")
                    print("Choosen Numbers", trade_selection)
                    await phases2()

        #=================================================================================
                else:
                    trade_selection = generate_signal()
                    current_bet_value = 1
                    result = f'RESUALT: {value_number}'
                    message = f'Win🎉'
                    message1 = f'''
🔝 Period : {extracted_time}

🌡 Choose :    {trade_selection}

⬆️ Stage :   X{current_bet_value}

🤲🤲 I recommend everyone to use the 3X plan for 30% - 50% guarantee of your profits 💸💸  Manage your funds 🤝
            '''
                    if first_time == 1:
                        await send_message_to_telegram(result)
                        time.sleep(0.1)
                        await send_message_to_telegram(message)
                        time.sleep(0.1)
                    else:
                        pass
                    await send_message_to_telegram(message1)
                    time.sleep(0.1)
                    pre_extracted_time = extracted_time
                    print('victory!')
                    # print('')
                    # print('-----------')
                    print(f"Current Issue id: {issue_number}")
                    print("Choosen Numbers", trade_selection)
                    await phases2()
                first_time = 1
            

    # final cleanup if needed
    await client.send_message(TARGET_CHANNEL_ID, "Background task has exited.")

# ——————————————————————————————————————————————————
# 4) RUN THE BOT
# ——————————————————————————————————————————————————
if __name__ == "__main__":
    client.start(bot_token=BOT_TOKEN)
    print("Bot is up. Press Ctrl+C to stop.")
    client.run_until_disconnected()