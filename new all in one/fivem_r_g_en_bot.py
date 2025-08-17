import asyncio
import logging
import sys
from os import getenv
from threading import Thread, Event
import threading
import os
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
TOKEN = getenv("7364169954:AAFBYBWqXTvVr_hIOCTXvPZmqMwjPWHLU7o")
TOKEN = "7364169954:AAFBYBWqXTvVr_hIOCTXvPZmqMwjPWHLU7o"
global consecutive_losses
consecutive_losses = 0

# All handlers should be attached to the Router (or Dispatcher)
dp = Dispatcher()
my_router = Router()

import redis


with open(r"data.json", "r") as f:
    data_valuse = json.load(f)


def write_json_file(file_path, data):
    with open(file_path, 'w') as file:
        json.dump(data, file)


# Replace this with the chat ID of the target channel
TARGET_CHANNEL_ID = "-1002160151325"
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
                            channels_list = [
                                -1001966567819, -1002185411344, -1002219999674,
                                -1002199401387, -1001749714035
                            ]
                            for id in channels_list:
                                await bot.send_message(chat_id=id,
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
            import os
            global latest_order_id
            global latest_issue
            latest_order_id = None
            latest_issue = None
            global new_data_processed
            global issue_number, the_result
            issue_number = 0
            the_result = "jo"

            def get_redis_connection():
                try:
                    r = redis.Redis(
                        host='redis-19425.c8.us-east-1-3.ec2.redns.redis-cloud.com',
                        port=19425,
                        decode_responses=True,
                        username="default",
                        password="wm3WGUb0VbsZ8drJQro7jkTQwOCFzxV3",
                        socket_timeout=5,  # 5 second timeout
                        socket_connect_timeout=5
                    )
                    # Test the connection
                    r.ping()
                    return r
                except Exception as e:
                    # print(f"[EN] Redis connection failed: {e}. Using direct API fallback.")
                    return None

            def update_redis(data_to_fill):
                try:
                    r = get_redis_connection()
                    if r:
                        # Create a comprehensive data structure for all bots
                        shared_data = {
                            "timestamp": int(time.time() * 1000),  # Current timestamp
                            "game_data": data_to_fill,  # Raw API response
                            "processed_data": {
                                "issue_number": latest_issue if 'latest_issue' in globals() else None,
                                "colors": colors if 'colors' in globals() else None,
                                "result_format": None,  # Will be set in process_data
                                "game_type": "RG5M",  # 5-minute Red/Green
                                "last_update": int(time.time() * 1000)
                            }
                        }
                        
                        # Update the shared Redis key
                        r.set("fivem_red_green_shared_data", json.dumps(shared_data))
                        r.expire("fivem_red_green_shared_data", 300)  # Expire in 5 minutes
                        # print("[EN] Shared data updated to Redis successfully")
                        
                        # Also keep the old key for backward compatibility
                        r.set("api_response", json.dumps(data_to_fill))
                        r.expire("api_response", 300)  # Expire in 5 minutes
                        
                    else:
                        print("[EN] Redis unavailable, using local file fallback")
                        # Fallback to local file when Redis is unavailable
                        update_local_file(data_to_fill)
                        
                except Exception as e:
                    print(f"[EN] Failed to update Redis: {e}. Using local file fallback.")
                    # Fallback to local file when Redis fails
                    update_local_file(data_to_fill)
            
            def update_local_file(data_to_fill):
                """Update local file when Redis is unavailable"""
                try:
                    # Create comprehensive shared data structure
                    shared_data = {
                        "timestamp": int(time.time() * 1000),
                        "game_data": data_to_fill,
                        "processed_data": {
                            "issue_number": latest_issue if 'latest_issue' in globals() else None,
                            "colors": colors if 'colors' in globals() else None,
                            "result_format": None,
                            "game_type": "RG5M",
                            "last_update": int(time.time() * 1000)
                        }
                    }
                    
                    # Write to local file
                    with open("fivem_shared_data.json", "w") as f:
                        json.dump(shared_data, f, indent=2)
                    
                    # print("[EN] Shared data updated to local file successfully")
                    
                except Exception as e:
                    print(f"[EN] Failed to update local file: {e}")
            
            def update_processed_data_local(issue_number, colors, result_format):
                """Update processed data in local file when Redis is unavailable"""
                try:
                    if os.path.exists("fivem_shared_data.json"):
                        with open("fivem_shared_data.json", "r") as f:
                            shared_data = json.load(f)
                        
                        # Update processed data
                        shared_data["processed_data"].update({
                            "issue_number": issue_number,
                            "colors": colors,
                            "result_format": result_format,
                            "last_update": int(time.time() * 1000)
                        })
                        
                        # Write updated data back to file
                        with open("fivem_shared_data.json", "w") as f:
                            json.dump(shared_data, f, indent=2)
                        
                        print("[EN] Processed data updated in local file for other bots")
                    else:
                        print("[EN] Local file not found, cannot update processed data")
                        
                except Exception as e:
                    print(f"[EN] Failed to update processed data in local file: {e}")

            def read_redis():
                try:
                    r = get_redis_connection()
                    if r:
                        raw = r.get("api_response")
                        if raw:
                            # print("[EN] Data read from Redis successfully")
                            return json.loads(raw)
                        else:
                            # print("[EN] No data in Redis, checking local file")
                            return read_local_file()
                    else:
                        # print("[EN] Redis unavailable, checking local file")
                        return read_local_file()
                except Exception as e:
                    # print(f"[EN] Failed to read from Redis: {e}. Checking local file.")
                    return read_local_file()
            
            def read_local_file():
                """Read from local file when Redis is unavailable"""
                try:
                    if os.path.exists("fivem_shared_data.json"):
                        with open("fivem_shared_data.json", "r") as f:
                            shared_data = json.load(f)
                        
                        # Check if data is fresh (less than 30 seconds old)
                        current_time = int(time.time() * 1000)
                        if current_time - shared_data["timestamp"] < 30000:
                            # print(f"[EN] Data read from local file successfully (updated {current_time - shared_data['timestamp']}ms ago)")
                            return shared_data["game_data"]
                        else:
                            print("[EN] Local file data is stale, using direct API")
                            return None
                    else:
                        print("[EN] No local file found, using direct API")
                        return None
                        
                except Exception as e:
                    print(f"[EN] Failed to read local file: {e}")
                    return None

            # Example Usage

            # Flag to indicate whether new data has been processed
            new_data_processed = False

            url = "https://m.coinvidg.com/api/rocket-api/game/issue-result/page"
            headers = {
                "accept": "application/json, text/plain, */*",
                "authorization": "Basic cm9ja2V0X3dlYjpyb2NrZXRfd2Vi",
                "blade-auth": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9...",
                "user-agent":
                "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36...",
                "referer":
                "https://m.coinvid.com/game/guessMain?gameName=RG1M&returnUrl=%2FgameList",
                "host": "m.coinvid.com",
                "connection": "keep-alive",
                "cookie": "JSESSIONID=0AkjLljW2FNgeVLmOPWYudZwXcbZbjx9yxUrwMWE"
            }

            params = {"subServiceCode": "RG5M", "size": "2", "current": "1"}

            proxy = "85.254.13.12:59100"
            username = "coinvidhosting"
            password = "paPJV3Jfkk"
            proxies = {
                "http": f"http://{username}:{password}@{proxy}",
                "https": f"http://{username}:{password}@{proxy}"
            }

            def fetch_data():
                # First try to get data from Redis
                redis_data = read_redis()
                if redis_data:
                    return redis_data
                
                # If Redis fails, use direct API call
                # print("[EN] Using direct API call as Redis fallback")
                session = requests.Session()
                
                MAX_RETRIES = 5
                for attempt in range(MAX_RETRIES):
                    try:
                        response = session.get(url,
                                               headers=headers,
                                               params=params,
                                               timeout=10)
                        response.raise_for_status()
                        api_data = response.json()
                        
                        # Try to update Redis (but don't fail if it doesn't work)
                        try:
                            update_redis(api_data)
                        except:
                            pass  # Ignore Redis update failures
                        
                        return api_data

                    except (requests.exceptions.ConnectionError,
                            requests.exceptions.Timeout) as e:
                        print(f"[EN] ⚠ Connection issue detected: {e}. Retrying...")
                        if attempt < MAX_RETRIES - 1:
                            time.sleep(2)
                        else:
                            print(f"[EN] ❌ Max retries reached for API call")
                            return None

                    except requests.exceptions.RequestException as e:
                        print(f"[EN] ❌ API request error: {e}")
                        if attempt < MAX_RETRIES - 1:
                            time.sleep(2)
                        else:
                            return None

                return None

            global colors
            colors = None

            def process_data(data):
                global latest_issue, new_data_processed, the_result, issue_number, the_result, colors
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
                                    print(respnse)
                                    try:
                                        result_format = respnse['data']['records'][
                                        0]['value']
                                    except:
                                        pass
                            else:
                                pass

                            print("the result:", result_format)
                            clean_string = result_format.replace(" ", "")
                            # Convert to integer
                            value_number = int(clean_string)
                            colors = ("GREEN   🟢" if int(value_number) %
                                      2 else "RED   🔴")

                            issue_number = last_record['issue']
                            # Print assigned variables
                            print("Issue number:", issue_number)
                            print("The colors: ", colors)
                            
                            # Update Redis with processed data for other bots
                            try:
                                r = get_redis_connection()
                                if r:
                                    # Update the shared data with processed information
                                    existing_data = r.get("fivem_red_green_shared_data")
                                    if existing_data:
                                        shared_data = json.loads(existing_data)
                                        shared_data["processed_data"].update({
                                            "issue_number": issue_number,
                                            "colors": colors,
                                            "result_format": result_format,
                                            "last_update": int(time.time() * 1000)
                                        })
                                        r.set("fivem_red_green_shared_data", json.dumps(shared_data))
                                        r.expire("fivem_red_green_shared_data", 300)
                                        print("[EN] Processed data updated in Redis for other bots")
                                    else:
                                        # If Redis doesn't have the data, update local file
                                        update_processed_data_local(issue_number, colors, result_format)
                                else:
                                    # Redis unavailable, update local file
                                    update_processed_data_local(issue_number, colors, result_format)
                            except Exception as e:
                                # print(f"[EN] Failed to update processed data in Redis: {e}")
                                # Fallback to local file
                                update_processed_data_local(issue_number, colors, result_format)
                            
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
                extracted_text = colors

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
                        'Issue No.':
                        pre_extracted_time,
                        'Prediction':
                        "🔴" if trade_selection == "RED   🔴" else "🟢",
                        'Result':
                        Result_W_L
                    })

                    print('Histroy count : ', len(results_history))
                    if Result_W_L == "🎉":
                        # Recalculate statistics after each set of 20 signals

                        success_rate = (results_history.count("Win") /
                                        len(results_history)) * 100
                        stats_message = f'Statistics function\n'
                        last_20_entries = detailed_results_history[-20:]
                        for signal_info in last_20_entries:
                            stats_message += f"Issue No.: {signal_info['Issue No.']} Prediction{signal_info['Prediction']}Result{signal_info['Result']}\n"
                        stats_message += f'\nIn the last {len(results_history)} predictions, {results_history.count("Win")} were successful and {results_history.count("Lose")} failed, with a prediction success rate of {round(success_rate, 2)}%, up to {highest_stage} stages.\n'

                        await send_message_to_telegram(stats_message)
                    else:
                        pass

                return consecutive_losses, Result_W_L

            global pre_extracted_time
            pre_extracted_time = None
            global trade_selection
            trade_selection = 'GREEN   🟢'
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
                        result = f'RESUALT: {colors}'
                        message = 'Lose💔'
                        message1 = f'''
✨5min Red_Green✨
Period:  {extracted_time}
Buy : {trade_selection}
Win rate: 80%
Multiple:  x{current_bet_value}
Using 3X plan,  earn 30% interest on each deposit🥳🥳👉🏻The higher the stage, the more profit you make🎉🎉
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
                        if trade_selection == "GREEN   🟢":
                            trade_selection = "RED   🔴"
                        else:
                            trade_selection = "GREEN   🟢"
                        current_bet_value = 1
                        result = f'RESUALT: {colors}'
                        message = f'Win🎉'
                        message1 = f'''
✨5min Red_Green✨
Period:  {extracted_time}
Buy : {trade_selection}
Win rate: 80%
Multiple:  x{current_bet_value}
Using 3X plan,  earn 30% interest on each deposit🥳🥳👉🏻The higher the stage, the more profit you make🎉🎉
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
            user_task3 = asyncio.create_task(main2())
        except:
            user_task3 = asyncio.create_task(main2())
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
