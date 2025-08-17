import asyncio
import logging
import sys
from os import getenv
from threading import Thread, Event
import threading
import logging
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
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from aiogram.exceptions import TelegramRetryAfter, TelegramAPIError, TelegramNetworkError, TelegramBadRequest
# Bot token can be obtained via https://t.me/BotFather
TOKEN = getenv("6801309878:AAFJ6YfeDoveUYo33nnqzVaYwF6ySj85BWs")
TOKEN = "6801309878:AAFJ6YfeDoveUYo33nnqzVaYwF6ySj85BWs"
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
TARGET_CHANNEL_ID = "-1002018091310"
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
        import asyncio
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

            await send_message_to_telegram('Starting...🚀')

            async def check_loop_and_stop():
                """Checks the loop value from a JSON file and stops the loop if it's 1."""
                loop_value = data_valuse["loop"]
                if loop_value == 1:
                    print("Bot stopped successfully.")
                    await asyncio.sleep(
                        0)  # Yield control back to the event loop
                    return  # Return without raising CancelledError

            import requests
            import random
            import asyncio
            global latest_order_id
            global latest_issue
            latest_order_id = None
            latest_issue = None
            global new_data_processed
            global issue_number, the_result
            issue_number = 0
            the_result = "jo"

            # Flag to indicate whether new data has been processed
            new_data_processed = False
            url = "https://m.coinvidg.com/api/rocket-api/game/issue-result/page"

            params = {"subServiceCode": "DS1M", "size": "1", "current": "1"}
            headers = {
                "Accept": "application/json, text/plain, */*",
                "Accept-Encoding": "gzip, deflate, br, zstd",
                "Accept-Language": "en-US",
                "Authorization": "Basic cm9ja2V0X3dlYjpyb2NrZXRfd2Vi",
                "User_type": "admin"
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

                MAX_RETRIES = 6
                for attempt in range(MAX_RETRIES):
                    try:
                        response = session.get(url,
                                               headers=headers,
                                               params=params,
                                               cookies=cookies,
                                               timeout=10)
                        response.raise_for_status()
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
                            # ... existing code ...
                            if result_format is None:
                                max_retries = 10
                                retry_count = 0
                                while result_format is None and retry_count < max_retries:
                                    print("Result is None. Retrying...")
                                    time.sleep(2)
                                    respnse = fetch_data()
                                    try:
                                        # Safely access nested data with .get() and provide default empty list
                                        result_format = respnse.get('data', {}).get('records', [{}])[0].get('resultFormatValueI18n', [])
                                        retry_count += 1
                                    except (IndexError, TypeError, KeyError) as e:
                                        print(f"Error accessing data: {e}")
                                        result_format = None
                                        retry_count += 1
                                        continue
                                
                                # If we still don't have a result after retries, log and continue
                                if result_format is None:
                                    print("Failed to get result after maximum retries")
                                    return  # Exit the function or handle the error case
                            # ... existing code ...
                            # Print the entire resultFormatValueI18n list

                            # Find the item containing '-' and assign it to the_result
                            for item in result_format:
                                if 'Even' in item or 'Odd' in item:
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

            detailed_results_history = []
            global highest_stage
            highest_stage = 1
            global Signals_Count
            Signals_Count = 0
            results_history = []

            async def lose_counter(trade_selection, pre_extracted_time):
                global consecutive_losses
                global Result_W_L
                global highest_stage
                global Signals_Count
                extracted_text = the_result

                if trade_selection == extracted_text:
                    consecutive_losses = 0
                    results_history.append("Win")
                    Result_W_L = "🎉"
                else:
                    consecutive_losses += 1
                    results_history.append("Lose")
                    Result_W_L = "💔"
                Signals_Count += 1
                print("Signals_Count : ", Signals_Count)
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

                    print('Histroy count : ', len(results_history))
                    if Result_W_L == "🎉":
                        # Recalculate statistics after each set of 20 signals

                        success_rate = (results_history.count("Win") /
                                        len(results_history)) * 100
                        stats_message = f'Statistics function\n'
                        last_20_entries = detailed_results_history[-20:]
                        for signal_info in last_20_entries:
                            stats_message += f"Issue No.: {signal_info['Issue No.']} Prediction {signal_info['Prediction']} Result{signal_info['Result']}\n"
                        stats_message += f'\nIn the last {len(results_history)} predictions, {results_history.count("Win")} were successful and {results_history.count("Lose")} failed, with a prediction success rate of {round(success_rate, 2)}%, up to {highest_stage} stages.\n'
                        # Reset results_history and detailed_results_history for the next 20 signals
                        results_history.clear()
                        detailed_results_history.clear()
                        await send_message_to_telegram(stats_message)
                    else:
                        pass

                return consecutive_losses, Result_W_L

            global pre_extracted_time
            pre_extracted_time = None
            global trade_selection
            trade_selection = "Odd"
            global first_time
            first_time = 0
            global current_bet_value
            current_bet_value = 1

            await phases2()

            async def main_async():
                global pre_extracted_time, first_time, trade_selection, current_bet_value, exit_flag

                while not exit_flag:
                    await check_loop_and_stop()
                    extracted_time = issue_number + 1
                    if first_time == 1:
                        await lose_counter(trade_selection, pre_extracted_time)
                    else:
                        time.sleep(3.5)

                    if consecutive_losses > 1 or consecutive_losses == 1:
                        current_bet_value *= 3
                        current_bet_value = round(current_bet_value, 2)
                        result = f'RESUALT: {the_result}'
                        message = 'Lose💔'
                        message1 = f'''
🔝 Period : {extracted_time}

🌡 Choose : {trade_selection}

⬆️ Stage :       X{current_bet_value}

🤲🤲 I recommend everyone to use the 3X plan for 30% - 50% guarantee of your profits 💸💸  Manage your funds 🤝
                        '''

                        await send_message_to_telegram(result)
                        time.sleep(0.1)
                        await send_message_to_telegram(message)
                        time.sleep(0.1)
                        await send_message_to_telegram(message1)
                        pre_extracted_time = extracted_time
                        print('fail!')
                        await phases2()
                    else:
                        if trade_selection == "Odd":
                            trade_selection = "Even"
                        else:
                            trade_selection = "Odd"
                        current_bet_value = 1
                        result = f'RESUALT: {the_result}'
                        message = f'Win🎉'
                        message1 = f'''
🔝 Period : {extracted_time}

🌡 Choose : {trade_selection}

⬆️ Stage :       X{current_bet_value}

🤲🤲 I recommend everyone to use the 3X plan for 30% - 50% guarantee of your profits 💸💸  Manage your funds 🤝
                        '''
                        await send_message_to_telegram(result)
                        time.sleep(0.1)
                        await send_message_to_telegram(message)
                        time.sleep(0.1)
                        await send_message_to_telegram(message1)
                        pre_extracted_time = extracted_time
                        print('victory!')
                        await phases2()
                    first_time = 1

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
            user_task4 = asyncio.create_task(main2())
        except:
            user_task4 = asyncio.create_task(main2())
        await callback_query.message.answer("Bot started successfully.",
                                            reply_markup=markup)

    elif data == "turn_off":
        # Create an inline keyboard builder
        builder = InlineKeyboardBuilder()

        # Add the "Turn On ▶" and "Turn Off ⏹" buttons
        builder.button(text="Turn On ▶", callback_data="turn_on")

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
