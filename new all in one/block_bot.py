import asyncio
import logging
import sys
from os import getenv
from threading import Thread, Event
import threading
from aiogram import Bot, Dispatcher, html
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram import Router, F
from aiogram.types import Message
from aiogram.types import CallbackQuery
import json
import time
import random
import logging
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from aiogram.exceptions import TelegramRetryAfter, TelegramAPIError, TelegramNetworkError, TelegramBadRequest

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
# Bot token can be obtained via https://t.me/BotFather
TOKEN = getenv("7054269991:AAGhvhXMFrxwOxodempZnMc747hnZPl3yV8")
TOKEN = "7054269991:AAGhvhXMFrxwOxodempZnMc747hnZPl3yV8"
global consecutive_losses
consecutive_losses = 0

# All handlers should be attached to the Router (or Dispatcher)
dp = Dispatcher()
my_router = Router()

with open(r"data.json", "r") as f:
    data_valuse = json.load(f)


def write_json_file(file_path, data):
    with open(file_path, 'w') as file:
        json.dump(data, file)


# Replace this with the chat ID of the target channel
TARGET_CHANNEL_ID = "-1002069191829"
exit_flag = False

# Event to signal the thread to stop
stop_event = Event()
allowed_user_ids = [1602528125, 6378849563]


@dp.message(CommandStart())
async def command_start_handler(message: Message, bot: Bot) -> None:
    """
    This handler receives messages with `/start` command
    """
    if message.from_user.id in allowed_user_ids:
        await message.answer(
            f"Hello, {html.bold(message.from_user.full_name)}!")
        # Create an inline keyboard builder
        builder = InlineKeyboardBuilder()

        # Add the "Turn On ▶" and "Turn Off ⏹" buttons
        builder.button(text="Turn On ▶", callback_data="turn_on")
        builder.button(text="Turn Off ⏹", callback_data="turn_off")

        # Construct the inline keyboard markup
        markup = builder.as_markup()

        # Send the message with the inline keyboard
        await message.answer("Choose an option:", reply_markup=markup)
    else:
        await message.answer("You are not authorized to use this bot.")


@my_router.callback_query(lambda c: c.data in ["turn_on", "turn_off"])
async def callback_query_handler(callback_query: CallbackQuery, bot: Bot):
    # Get the data from the clicked inline button
    data = callback_query.data

    if data == "turn_on":
        from argparse import ArgumentParser

        from aiogram import Bot
        from aiogram.client.default import DefaultBotProperties
        from aiogram.enums import ParseMode
        # Create an inline keyboard builder
        builder = InlineKeyboardBuilder()

        # Add the "Turn On ▶" and "Turn Off ⏹" buttons
        builder.button(text="Turn Off ⏹", callback_data="turn_off")

        # Construct the inline keyboard markup
        markup = builder.as_markup()
        # Handle the click on the "Turn On ▶" button
        await callback_query.answer("Turning on the bot...")
        await callback_query.message.answer("Starting.....")
        await callback_query.message.answer(
            "Please be patient for the next signal to be puplished it may take 2 minutes",
            reply_markup=markup)
        global exit_flag
        exit_flag = False
        data_valuse["loop"] = 0
        write_json_file("data.json", data_valuse)

        async def main2():

            def create_parser() -> ArgumentParser:
                parser = ArgumentParser()
                parser.add_argument("--token", help=TOKEN)
                parser.add_argument("--chat-id",
                                    type=int,
                                    help=TARGET_CHANNEL_ID)
                parser.add_argument("--message",
                                    "-m",
                                    help="Message text to sent",
                                    default="Hello, World!")

                return parser

            async def send_message_to_telegram(message, max_retries=5):
                retry_delay = 1  # Starting with 1 second delay
                for attempt in range(max_retries):
                    try:
                        parser = create_parser()
                        ns = parser.parse_args()

                        token = ns.token

                        async with Bot(
                                token=TOKEN,
                                default=DefaultBotProperties(
                                    parse_mode=ParseMode.HTML, ),
                        ) as bot:
                            await bot.send_message(chat_id=TARGET_CHANNEL_ID,
                                                   text=message)
                        break  # Break out of the loop if message is sent successfully
                    except asyncio.TimeoutError:
                        logging.warning(
                            f"Timeout error on try {attempt + 1}. Retrying in {retry_delay} seconds..."
                        )
                        await asyncio.sleep(retry_delay)
                        retry_delay *= 2  # Exponential back-off
                    except TelegramRetryAfter as e:
                        logging.warning(
                            f"Rate limit hit, retrying after {2} seconds.")
                        await asyncio.sleep(
                            2
                        )  # Wait for retry_after seconds before the next attempt
                    except TelegramNetworkError as e:
                        logging.warning(
                            f"Rate limit hit, retrying after {2} seconds.")
                        await asyncio.sleep(
                            2
                        )  # Wait for retry_after seconds before the next attempt
                    except TelegramBadRequest as e:
                        logging.warning(
                            f"Rate limit hit, retrying after {2} seconds.")
                        await asyncio.sleep(
                            2
                        )  # Wait for retry_after seconds before the next attempt
                    except TelegramAPIError as e:
                        logging.error(
                            f"Telegram API error: {e}. Retrying in {retry_delay} seconds..."
                        )
                        await asyncio.sleep(retry_delay)
                        retry_delay *= 2  # Exponential back-off
                    except Exception as e:
                        logging.error(
                            f"Unexpected error: {e}. Retrying in {retry_delay} seconds..."
                        )
                        await asyncio.sleep(retry_delay)
                        retry_delay *= 2  # Exponential back-off

            async def check_loop_and_stop():
                """Checks the loop value from a JSON file and stops the loop if it's 1."""
                loop_value = data_valuse["loop"]
                if loop_value == 1:
                    print("Bot stopped successfully.")
                    await asyncio.sleep(
                        0)  # Yield control back to the event loop
                    return  # Return without raising CancelledError

            await send_message_to_telegram('Starting...🚀')

            import requests
            import time
            import asyncio

            import json
            import time

            global latest_order_id
            global latest_issue
            latest_order_id = None
            latest_issue = None
            global new_data_processed
            global issue_number, the_result
            issue_number = 0
            the_result = "jo"

            # Global variable to store the latest order_id

            # Flag to indicate whether new data has been processed
            new_data_processed = False

            def fetch_data():
                session = requests.Session()
                retries = Retry(total=5,
                                backoff_factor=0.1,
                                status_forcelist=[500, 502, 503, 504])
                session.mount('https://', HTTPAdapter(max_retries=retries))
                url = "https://m.coinvidg.com/api/rocket-api/game/issue-result/page"

                params = {
                    "subServiceCode": "BLK1M",
                    "size": "1",
                    "current": "1"
                }

                headers = {
                    "Accept": "application/json, text/plain, */*",
                    "Accept-Encoding": "gzip, deflate, br, zstd",
                    "Accept-Language": "en-US",
                    "Authorization": "Basic cm9ja2V0X3dlYjpyb2NrZXRfd2Vi",
                    "Blade-Auth":
                    "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9.eyJpc3MiOiJpc3N1c2VyIiwiYXVkIjoiYXVkaWVuY2UiLCJ0ZW5hbnRfaWQiOiI2NzczNDMiLCJ1c2VyX25hbWUiOiJhaG1lZDIwMDc4OSIsInRva2VuX3R5cGUiOiJhY2Nlc3NfdG9rZW4iLCJyb2xlX25hbWUiOiIiLCJ1c2VyX3R5cGUiOiJyb2NrZXQiLCJ1c2VyX2lkIjoiMTc2MDY0ODM5NTE2ODM0NjExNCIsImRldGFpbCI6eyJhdmF0YXIiOiIyMiIsInZpcExldmVsIjoxfSwiYWNjb3VudCI6ImFobWVkMjAwNzg5IiwiY2xpZW50X2lkIjoicm9ja2V0X3dlYiIsImV4cCI6MTcxNDM0MDI2NywibmJmIjoxNzEzNzM1NDY3fQ.aXRhEncmu0FqESL4jVkfQUJT0p0UzVa70rxZq-GItzOQxq_XJJpXJHtsjPKejlsf-Sp7mtbhrzVICkqdRZl-QQ",
                    "User-Agent":
                    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
                    "User_type": "rocket"
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

                try:
                    response = session.get(url,
                                           params=params,
                                           headers=headers,
                                        #    proxies=proxies,
                                           cookies=cookies,
                                           timeout=30)
                    response.raise_for_status()
                    return response.json()
                except requests.RequestException as e:
                    logging.error(f"Request failed: {e}")
                except Exception as e:
                    logging.error(f"Request failed: {e}")

            def process_data(data):
                global latest_issue, new_data_processed, the_result, issue_number, the_result
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
                            result_format = last_record.get(
                                'resultFormatValueI18n', [])
                            if result_format == None:
                                while result_format == None:
                                    print("reeult is None. Retrying...")
                                    time.sleep(2)
                                    respnse = fetch_data()
                                    result_format = respnse['data']['records'][
                                        0].get('resultFormatValueI18n', [])
                            else:
                                pass
                            # Print the entire resultFormatValueI18n list
                            print("ResultFormatValueI18n:", result_format)

                            # Find the item containing '-' and assign it to the_result
                            for item in result_format:
                                if '-' in item:
                                    the_result = item
                                    break

                            issue_number = last_record['issue']
                            # Print assigned variables
                            print("Issue number:", issue_number)
                            print("Result:", the_result)

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
                    if data_valuse["loop"] == 1:
                        print("Breaking out of phases2 function.")
                        break
                    await asyncio.sleep(1)
                    data = fetch_data()
                    process_data(data)
                    if new_data_processed:
                        new_data_processed = False  # Reset flag for next iteration
                        break

            consecutive_losses = 0
            results_history = []

            # List to store detailed information about the last 20 signals
            detailed_results_history = []
            global wins_history
            wins_history = []
            global highest_stage
            highest_stage = 1
            global consecutive_Signals
            consecutive_Signals = 0
            global pre_consecutive_losses
            pre_consecutive_losses = 0
            global Signals_Count
            Signals_Count = 0

            async def lose_counter(trade_selection, pre_extracted_time):
                global issue_number, the_result
                global consecutive_losses
                global Result_W_L
                global highest_stage
                global Signals_Count
                global consecutive_losses  # Declare that consecutive_losses is a global variable
                global consecutive_wins  # Declare that consecutive_wins is a global variable
                global extracted_text
                extracted_text = the_result.replace("-", " ")
                consecutive_wins = data_valuse["consecutive_wins"]
                consecutive_losses = data_valuse["consecutive_losses"]

                if extracted_text in trade_selection:
                    # If it's a win, reset the consecutive_losses counter
                    consecutive_wins += 1
                    data_valuse["consecutive_wins"] += 1
                    data_valuse["consecutive_losses"] = 0
                    consecutive_losses = 0
                    results_history.append("Win")
                    Result_W_L = "Win 🎉"
                else:
                    # If it's a loss, increase the consecutive_losses counter
                    consecutive_losses += 1
                    consecutive_wins = 0
                    data_valuse["consecutive_wins"] = 0
                    data_valuse["consecutive_losses"] += 1
                    results_history.append("Lose")
                    Result_W_L = "Lose 💔"
                Signals_Count += 1
                print("Consecutive Losses : ", consecutive_losses)
                print("Consecutive Wins : ", consecutive_wins)
                print('Histroy count : ', Signals_Count)
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

                    if Result_W_L == "Win 🎉":
                        # Recalculate statistics after each set of 20 signals

                        success_rate = (results_history.count("Win") /
                                        len(results_history)) * 100
                        stats_message = f'Statistics function\n'
                        last_20_entries = detailed_results_history[-20:]
                        for signal_info in last_20_entries:
                            stats_message += f"Issue No.: {signal_info['Issue No.']} {signal_info['Result']}\n"
                        stats_message += f'\nIn the last {len(results_history)} predictions, {results_history.count("Win")} were successful and {results_history.count("Lose")} failed, with a prediction success rate of {round(success_rate, 2)}%, up to {highest_stage} stages.\n'
                        # Reset results_history and detailed_results_history for the next 20 signals
                        await send_message_to_telegram(stats_message)
                    else:
                        pass
                write_json_file("data.json", data_valuse)
                return consecutive_losses, Result_W_L

            format1 = {
                "combinations": "⏰ Big Odd、Small Odd、Small Even⏰",
                "Wining_Words": ['Big Odd', 'Small Odd', 'Small Even'],
            }
            format2 = {
                "combinations": "⏰ Small Odd、Big Even、Small Even⏰",
                "Wining_Words": ['Small Odd', 'Big Even', 'Small Even'],
            }
            format3 = {
                "combinations": "⏰ Big Odd、Small Odd、Big Even⏰",
                "Wining_Words": ['Big Odd', 'Small Odd', 'Big Even'],
            }
            format1_2 = {
                "combinations": "⏰ Big Odd、Small Odd、Small Even⏰",
                "Wining_Words": ['Big Odd', 'Small Odd', 'Small Even'],
            }
            format2_2 = {
                "combinations": "⏰ Big Odd、Big Even、Small Even⏰",
                "Wining_Words": ['Big Odd', 'Big Even', 'Small Even'],
            }
            format3_2 = {
                "combinations": "⏰ Big Odd、Small Odd、Big Even⏰",
                "Wining_Words": ['Big Odd', 'Small Odd', 'Big Even'],
            }
            format1_3 = {
                "combinations": "⏰ Big Odd、Small Odd、Small Even⏰",
                "Wining_Words": ['Big Odd', 'Small Odd', 'Small Even'],
            }
            format2_3 = {
                "combinations": "⏰ Small Odd、Big Even、Small Even⏰",
                "Wining_Words": ['Small Odd', 'Big Even', 'Small Even'],
            }
            format3_3 = {
                "combinations": "⏰ Big Odd、Small Odd、Big Even⏰",
                "Wining_Words": ['Big Odd', 'Small Odd', 'Big Even'],
            }
            format1_4 = {
                "combinations": "⏰ Big Odd、Small Odd、Small Even⏰",
                "Wining_Words": ['Big Odd', 'Small Odd', 'Small Even'],
            }
            format2_4 = {
                "combinations": "⏰ Big Odd、Big Even、Small Even⏰",
                "Wining_Words": ['Big Odd', 'Big Even', 'Small Even'],
            }
            format3_4 = {
                "combinations": "⏰ Big Odd、Small Odd、Big Even⏰",
                "Wining_Words": ['Big Odd', 'Small Odd', 'Big Even'],
            }
            format5 = {
                "combinations": "⏰ Big Odd、Small Odd、Small Even⏰",
                "Wining_Words": ['Big Odd', 'Small Odd', 'Small Even'],
            }
            format6 = {
                "combinations": "⏰ Big Odd、Big Even、Small Even⏰",
                "Wining_Words": ['Big Odd', 'Big Even', 'Small Even'],
            }

            stage_1 = [format1, format2, format3]
            stage_2 = [format1_2, format2_2, format3_2]
            stage_3 = [format1_3, format2_3, format3_3]
            stage_4 = [format1_4, format2_4, format3_4]
            weights = [0.7, 0.7, 0.3]
            global trade_selection, combinations, pre_extracted_time

            trade_selection = format1["Wining_Words"]
            combinations = format1["combinations"]
            global current_bet_value
            current_bet_value = 1
            pre_extracted_time = None
            await phases2()

            async def main_async():
                global pre_extracted_time, first_time, trade_selection, current_bet_value, exit_flag
                try:
                    while not exit_flag:
                        try:
                            await check_loop_and_stop()
                            extracted_time = issue_number + 1
                            await lose_counter(trade_selection,
                                               pre_extracted_time)

                            if data_valuse["consecutive_losses"] == 1:
                                random_signal = random.choices(stage_2,
                                                               weights=weights,
                                                               k=1)[0]
                                combinations = random_signal["combinations"]
                                trade_selection = random_signal["Wining_Words"]
                                data_valuse["chosen_format"] = random_signal
                                write_json_file("data.json", data_valuse)
                                # Capitalize all characters and replace spaces with dashes
                                formatted_string = extracted_text.upper(
                                ).replace(" ", "-")

                                # Print the formatted string
                                print(formatted_string)
                                message1 = f"RESULT: {formatted_string} 💔LOSE"
                                message2 = 'Enter stage 2'
                                message = f'''
🔝 Period : {extracted_time}
⬆️ Stage :    X 2

🌡 Choose :    \n{combinations}

🤲🤲 I recommend everyone to use the 3X plan for 30% - 50% guarantee of your profits 💸💸  Manage your funds 🤝
                                '''
                                await send_message_to_telegram(message1)
                                time.sleep(0.1)
                                await send_message_to_telegram(message2)
                                time.sleep(0.1)
                                await send_message_to_telegram(message)
                                pre_extracted_time = extracted_time
                                print("Combination for this round are : ",
                                      combinations)
                                print(
                                    "#########################################################################"
                                )
                                await phases2()
                            elif data_valuse["consecutive_losses"] == 2:

                                random_signal = random.choices(stage_3,
                                                               weights=weights,
                                                               k=1)[0]
                                combinations = random_signal["combinations"]
                                trade_selection = random_signal["Wining_Words"]
                                data_valuse["chosen_format"] = random_signal
                                write_json_file("data.json", data_valuse)
                                # Capitalize all characters and replace spaces with dashes
                                formatted_string = extracted_text.upper(
                                ).replace(" ", "-")

                                # Print the formatted string
                                print(formatted_string)
                                message1 = f"RESULT: {formatted_string} 💔LOSE"
                                message2 = 'Enter stage 3'
                                message = f'''
🔝 Period : {extracted_time}
⬆️ Stage :    X 3

🌡 Choose :    \n{combinations}

🤲🤲 I recommend everyone to use the 3X plan for 30% - 50% guarantee of your profits 💸💸  Manage your funds 🤝
                                '''
                                await send_message_to_telegram(message1)
                                time.sleep(0.1)
                                await send_message_to_telegram(message2)
                                time.sleep(0.1)
                                await send_message_to_telegram(message)
                                pre_extracted_time = extracted_time
                                print("Combination for this round are : ",
                                      combinations)
                                print(
                                    "#########################################################################"
                                )
                                await phases2()
                            elif data_valuse["consecutive_losses"] == 3:

                                random_signal = random.choices(stage_4,
                                                               weights=weights,
                                                               k=1)[0]
                                combinations = random_signal["combinations"]
                                trade_selection = random_signal["Wining_Words"]
                                data_valuse["chosen_format"] = random_signal
                                write_json_file("data.json", data_valuse)
                                # Capitalize all characters and replace spaces with dashes
                                formatted_string = extracted_text.upper(
                                ).replace(" ", "-")

                                # Print the formatted string
                                print(formatted_string)
                                message1 = f"RESULT: {formatted_string} 💔LOSE"
                                message2 = 'Enter stage 4'
                                message = f'''
        🔝 Period :  {extracted_time}

⬆️ Stage :    X 4

🌡 Choose :    \n{combinations}

🤲🤲 I recommend everyone to use the 3X plan for 30% - 50% guarantee of your profits 💸💸  Manage your funds 🤝
                                '''
                                await send_message_to_telegram(message1)
                                time.sleep(0.1)
                                await send_message_to_telegram(message2)
                                time.sleep(0.1)
                                await send_message_to_telegram(message)
                                pre_extracted_time = extracted_time
                                print("Combination for this round are : ",
                                      combinations)
                                print(
                                    "#########################################################################"
                                )
                                await phases2()
                            elif data_valuse["consecutive_losses"] == 4:
                                combinations = format5["combinations"]
                                trade_selection = format5["Wining_Words"]
                                data_valuse["chosen_format"] = format5
                                write_json_file("data.json", data_valuse)
                                # Capitalize all characters and replace spaces with dashes
                                formatted_string = extracted_text.upper(
                                ).replace(" ", "-")

                                # Print the formatted string
                                print(formatted_string)
                                message1 = f"RESULT: {formatted_string} 💔LOSE"
                                message2 = 'Enter stage 5'
                                message = f'''
        🔝 Period :  {extracted_time}

⬆️ Stage :    X 5

🌡 Choose :    \n{combinations}

🤲🤲 I recommend everyone to use the 3X plan for 30% - 50% guarantee of your profits 💸💸  Manage your funds 🤝
                                '''
                                await send_message_to_telegram(message1)
                                time.sleep(0.1)
                                await send_message_to_telegram(message2)
                                time.sleep(0.1)
                                await send_message_to_telegram(message)
                                pre_extracted_time = extracted_time
                                print("Combination for this round are : ",
                                      combinations)
                                print(
                                    "#########################################################################"
                                )
                                await phases2()
                            elif data_valuse["consecutive_losses"] == 5:
                                combinations = format6["combinations"]
                                trade_selection = format6["Wining_Words"]
                                data_valuse["chosen_format"] = format6
                                write_json_file("data.json", data_valuse)
                                # Capitalize all characters and replace spaces with dashes
                                formatted_string = extracted_text.upper(
                                ).replace(" ", "-")

                                # Print the formatted string
                                print(formatted_string)
                                message1 = f"RESULT: {formatted_string} 💔LOSE"
                                message2 = 'Enter stage 6'
                                message = f'''
        🔝 Period :  {extracted_time}

⬆️ Stage :    X 6

🌡 Choose :    \n{combinations}

🤲🤲 I recommend everyone to use the 3X plan for 30% - 50% guarantee of your profits 💸💸  Manage your funds 🤝
                                '''
                                await send_message_to_telegram(message1)
                                time.sleep(0.1)
                                await send_message_to_telegram(message2)
                                time.sleep(0.1)
                                await send_message_to_telegram(message)
                                pre_extracted_time = extracted_time
                                print("Combination for this round are : ",
                                      combinations)
                                print(
                                    "#########################################################################"
                                )
                                await phases2()
                            elif data_valuse[
                                    "consecutive_losses"] == 6 or data_valuse[
                                        "consecutive_losses"] > 6:
                                random_signal = random.choices(stage_1,
                                                               weights=weights,
                                                               k=1)[0]
                                combinations = random_signal["combinations"]
                                trade_selection = random_signal["Wining_Words"]
                                data_valuse["consecutive_wins"] = 0
                                data_valuse["chosen_format"] = random_signal
                                data_valuse["consecutive_losses"] = 0
                                write_json_file("data.json", data_valuse)

                                message1 = "Restarting"
                                message = f'''
        🔝 Period :  {extracted_time}

⬆️ Stage :    X 1

🌡 Choose :    \n{combinations}

🤲🤲 I recommend everyone to use the 3X plan for 30% - 50% guarantee of your profits 💸💸  Manage your funds 🤝
                                    '''
                                await send_message_to_telegram(message1)
                                time.sleep(0.1)
                                await send_message_to_telegram(message)
                                pre_extracted_time = extracted_time
                                print("Combination for this round are : ",
                                      combinations)
                                print(
                                    "#########################################################################"
                                )
                                await phases2()

                            else:
                                random_signal = random.choices(stage_1,
                                                               weights=weights,
                                                               k=1)[0]
                                combinations = random_signal["combinations"]
                                trade_selection = random_signal["Wining_Words"]
                                data_valuse["consecutive_wins"] = 0
                                data_valuse["chosen_format"] = random_signal
                                write_json_file("data.json", data_valuse)
                                # Capitalize all characters and replace spaces with dashes
                                formatted_string = extracted_text.upper(
                                ).replace(" ", "-")

                                # Print the formatted string
                                print(formatted_string)
                                message1 = f"RESULT: {formatted_string} 🎉WIN"
                                message = f'''
        🔝 Period :  {extracted_time}

⬆️ Stage :    X 1

🌡 Choose :    \n{combinations}

🤲🤲 I recommend everyone to use the 3X plan for 30% - 50% guarantee of your profits 💸💸  Manage your funds 🤝
                                    '''
                                await send_message_to_telegram(message1)
                                time.sleep(0.1)
                                await send_message_to_telegram(message)
                                pre_extracted_time = extracted_time
                                print("Combination for this round are : ",
                                      combinations)
                                print(
                                    "#########################################################################"
                                )
                                await phases2()
                        except Exception as specific_error:
                            logging.error(
                                f"An error occurred in main_async: {specific_error}"
                            )
                            # Implement necessary recovery or retry logic here
                            await asyncio.sleep(2)
                except Exception as e:
                    print(f"An error occurred in main_async: {e}")

                    # Check if the thread should be terminated
                    if not threading.current_thread().is_alive():
                        print("Thread is being terminated.")
                        return

            def run_async_main():
                # Set up a new event loop for the thread
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

                # Now we run the main async function within this loop
                loop.run_until_complete(main_async())
                loop.close()

                # Start the main2() function in a separate thread

            global my_thread
            my_thread = threading.Thread(target=run_async_main)
            my_thread.start()

        try:
            user_task2 = asyncio.create_task(main2())
        except:
            user_task2 = asyncio.create_task(main2())
        await callback_query.message.answer("Bot started successfully.",
                                            reply_markup=markup)

    elif data == "turn_off":
        # Create an inline keyboard builder
        builder = InlineKeyboardBuilder()

        # Add the "Turn On ▶" and "Turn Off ⏹" buttons
        builder.button(text="Turn Off ⏹", callback_data="turn_off")

        # Construct the inline keyboard markup
        markup = builder.as_markup()

        # Handle the click on the "Turn Off ⏹" button
        await callback_query.answer("Turning off the bot...")
        data_valuse["loop"] = 1
        write_json_file("data.json", data_valuse)
        global my_thread
        # To close the thread, set the exit flag to True
        exit_flag = True
        my_thread.join(
        )  # Wait for the thread to finish before exiting the main program
        print("Thread has been closed.")

        await callback_query.message.answer("Bot stopped successfully.",
                                            reply_markup=markup)
    else:
        # Handle any other callback data
        await callback_query.answer("Unknown button clicked")


async def main() -> None:
    # Initialize Bot instance with default bot properties which will be passed to all API calls
    bot = Bot(token=TOKEN,
              default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    await bot.delete_webhook()
    # Attach the my_router to the dispatcher
    dp.include_router(my_router)
    # And the run events dispatching
    await dp.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
