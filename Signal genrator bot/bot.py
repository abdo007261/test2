from pyrogram.client import Client
from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message
from pyrogram.enums import ChatType, ParseMode
from config import get_text, API_ID, API_HASH, BOT_TOKEN
from database import Database
import re
import asyncio
import aiohttp
import json
import sqlite3
import time
from datetime import datetime, timedelta
import traceback
from pyrogram.types import BotCommand, BotCommandScope, BotCommandScopeAllPrivateChats, MenuButtonDefault, BotCommandScopeChat

# ADD THIS NEW IMPORT:
from trading_bot_receiver import TradingBotReceiver
from bot_communication import bot_comm

# Initialize bot and database
app = Client("copytrading_bot2", api_id=API_ID, api_hash=API_HASH, bot_token="8266746246:AAG_KgNoayIyPMRQ6dRXBw9THf3D5eC3UXI")

# ADD THIS NEW LINE:
receiver = TradingBotReceiver(app)

# --- STICKER SYSTEM ---
def load_stickers():
    """Load sticker mappings from JSON file"""
    try:
        with open('number_stickers.json', 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading stickers: {e}")
        return {}

# Load stickers at startup
STICKERS = load_stickers()

# --- CHANNEL TRACKING SYSTEM ---
# Track wins per channel for sticker selection
channel_wins = {}  # {channel_id: win_count}
# Track active background tasks to prevent duplicates
active_tasks = {}  # {channel_id: task}

# Track per-channel signal history for /statistics
# Structure: {channel_id_str: [ { 'issue': str, 'choice': str, 'phase': int, 'win': bool, 'timestamp': float }, ... ]}
channel_history = {}

def _append_channel_history(channel_id: int, issue: str, choice: str, phase: int, win: bool):
    channel_id_str = str(channel_id)
    history_list = channel_history.setdefault(channel_id_str, [])
    history_list.append({
        'issue': str(issue),
        'choice': str(choice),
        'phase': int(phase),
        'win': bool(win),
        'timestamp': time.time(),
    })
    # Keep only the latest 200 entries to bound memory
    if len(history_list) > 200:
        del history_list[:-200]

@app.on_message(filters.command("statistics"))
async def statistics_command(client, message: Message):
    """Show recent signal history for this chat in a copy-friendly code block."""
    try:
        if not message.chat:
            return
        channel_id_str = str(message.chat.id)
        history_list = channel_history.get(channel_id_str, [])

        if not history_list:
            await message.reply_text("No statistics yet for this chat.")
            return

        # Build lines newest first
        lines = ["History:"]
        for entry in reversed(history_list[-50:]):  # show up to last 50
            issue = entry.get('issue', '—')
            choice = entry.get('choice', '?')
            phase = entry.get('phase', 1)
            win = entry.get('win', False)
            status = "✅ Win" if win else "❎"
            # Example: 0902 buy G order  3 ✅ Win
            lines.append(f"{issue} buy {choice} order  {phase} {status}")

        # Wrap each entry line (except header) with inline code backticks
        if len(lines) > 1:
            header = lines[0]
            body_lines = [f"`{ln}`" for ln in lines[1:]]
            text = header + "\n" + "\n".join(body_lines)
        else:
            text = "History:\n`—`"

        await message.reply_text(text, disable_web_page_preview=True, parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        await message.reply_text(f"Error: {e}")

# Acknowledge stop command from the signal bot (for channels - bots can see each other)
@app.on_message(filters.command("stop"))
async def stop_command(client, message: Message):
    try:
        # Use the copy bot's own win tracking for this channel/group
        current_wins = get_channel_win_count(message.chat.id)
        stop_message = f"✅ Target of {current_wins} wins reached! Stopping signals."
        
        await message.reply_text(stop_message)
        # Mark this group as stopped
        try:
            STOPPED_GROUPS.add(str(message.chat.id))
        except Exception:
            pass
    except Exception:
        pass

def get_channel_win_count(channel_id):
    """Get current win count for a channel"""
    return channel_wins.get(str(channel_id), 0)

def increment_channel_win(channel_id):
    """Increment win count for a channel"""
    channel_id_str = str(channel_id)
    if channel_id_str not in channel_wins:
        channel_wins[channel_id_str] = 0
    channel_wins[channel_id_str] += 1
    return channel_wins[channel_id_str]

def reset_channel_win_count(channel_id):
    """Reset win count for a channel to 0"""
    channel_id_str = str(channel_id)
    channel_wins[channel_id_str] = 0
    print(f"[BOT] Reset win count for channel/group {channel_id} to 0")
    return 0

def save_channel_signal_info(channel_id, signal_type, color, phase, issue_number: str | None = None):
    """Save signal info for later result processing. Optionally includes issue_number for precise gating."""
    channel_id_str = str(channel_id)
    if channel_id_str not in channel_wins:
        channel_wins[channel_id_str] = 0
    
    # Create unique signal ID to prevent conflicts
    signal_id = f"{channel_id_str}_{signal_type}_{int(datetime.now().timestamp())}"
    
    # Store signal info for this channel with timestamp
    current_time = datetime.now()
    info = {
        'type': signal_type,  # 'red_green', 'blocks', 'dices'
        'color': color,       # 'R', 'G', 'B', 'S', 'O', 'E'
        'phase': phase,
        'timestamp': current_time.timestamp(),  # Add timestamp to track signal age
        'signal_id': signal_id  # Unique identifier for this signal
    }
    if issue_number is not None:
        info['issue_number'] = str(issue_number)
    channel_wins[f"{channel_id_str}_signal"] = info
    
    print(f"DEBUG: Saved signal {signal_id} for channel {channel_id}")

# --- RESULT CHECKING HELPERS ---
async def wait_for_next_minute():
    """Wait until the start of the next minute"""
    now = datetime.now()
    seconds_until_next_minute = 60 - now.second
    await asyncio.sleep(seconds_until_next_minute)

async def wait_for_next_minute_plus_4():
    """Monitor machine time continuously and wait 4 seconds after minute changes"""
    start_minute = datetime.now().minute
    print(f"DEBUG: Starting time monitoring at minute {start_minute}")
    
    # Keep checking until minute changes
    while True:
        current_minute = datetime.now().minute
        if current_minute != start_minute:
            print(f"DEBUG: Minute changed from {start_minute} to {current_minute}, waiting 4 seconds...")
            await asyncio.sleep(4)
            print(f"DEBUG: 4 seconds passed, proceeding...")
            break
        await asyncio.sleep(0.1)  # Check every 100ms

async def wait_for_current_minute_plus_1():
    """Wait for the current minute + 1 second (shorter delay for faster response)"""
    current_time = datetime.now()
    current_minute = current_time.minute
    current_second = current_time.second
    
    # Calculate seconds to wait until current minute + 1 second
    if current_second >= 1:
        # If we're past 1 second in the current minute, wait for next minute + 1
        seconds_to_wait = (60 - current_second) + 1
        print(f"DEBUG: Current time: {current_time.strftime('%H:%M:%S')}, waiting {seconds_to_wait} seconds until next minute + 1 second")
    else:
        # If we're before 1 second, wait until current minute + 1
        seconds_to_wait = 1 - current_second
        print(f"DEBUG: Current time: {current_time.strftime('%H:%M:%S')}, waiting {seconds_to_wait} seconds until current minute + 1 second")
    
    await asyncio.sleep(seconds_to_wait)
    print(f"DEBUG: Waited {seconds_to_wait} seconds, proceeding...")

async def check_red_green_result(issue_number):
    """Check Red/Green result from database"""
    try:
        conn = sqlite3.connect("signals_data.db")
        c = conn.cursor()
        c.execute("""
            SELECT value, color, issue
            FROM red_green_results 
            ORDER BY timestamp DESC 
            LIMIT 1
        """)
        result = c.fetchone()
        conn.close()
        
        if result and int(result[2]) > int(issue_number):
            return result
        return None
    except Exception as e:
        print(f"Error checking Red/Green result: {e}")
        return None

async def check_blocks_result():
    """Check latest Blocks result from database"""
    try:
        conn = sqlite3.connect("signals_data.db")
        c = conn.cursor()
        c.execute("SELECT result FROM blocks_results ORDER BY timestamp DESC LIMIT 1")
        result = c.fetchone()
        conn.close()
        
        if result and result[0]:
            return result[0]
        return None
    except Exception as e:
        print(f"Error checking Blocks result: {e}")
        return None

async def check_dices_result():
    """Check latest Dices result from database"""
    try:
        conn = sqlite3.connect("signals_data.db")
        c = conn.cursor()
        c.execute("SELECT result FROM dices_results ORDER BY timestamp DESC LIMIT 1")
        result = c.fetchone()
        conn.close()
        
        if result and result[0]:
            return result[0]
        return None
    except Exception as e:
        print(f"Error checking Dices result: {e}")
        return None

# --- BACKGROUND RESULT CHECKING TASKS ---
async def check_and_send_red_green_result(client, message, color, phase, lang):
    """Background task to check and send Red/Green results"""
    print(f"DEBUG: Background Red/Green task started for {color}x{phase}")
    try:
        # Wait for next minute + 4 seconds (precise timing)
        print(f"DEBUG: Waiting for next minute + 4 seconds...")
        await wait_for_next_minute_plus_4()
        print(f"DEBUG: Starting result checking...")
        
        # Start checking for results
        max_attempts = 60  # Check for 60 seconds
        attempt = 0
        result = None
        
        # Get current issue number (approximate)
        current_time = datetime.now()
        issue_number = int(current_time.strftime("%Y%m%d%H%M"))
        
        while attempt < max_attempts:
            result = await check_red_green_result(issue_number)
            if result:
                break
            attempt += 1
            await asyncio.sleep(1)  # Check every second
        
        if result:
            print(f"DEBUG: Red/Green result found: {result}")
            try:
                # Process result
                result_lower = result[1].lower().strip()
                # Check for specific number rules first
                try:
                    value_num = int(result[0])  # result[0] is the value number
                    if value_num == 5:
                        is_red = False  # 5 = GREEN
                    elif value_num == 0:
                        is_red = True   # 0 = RED
                    else:
                        # Default text-based detection
                        is_red = 'red' in result_lower
                except:
                    # Fallback to text-based detection
                    is_red = 'red' in result_lower
                actual_result = get_text("result_red", lang) if is_red else get_text("result_green", lang)
                
                # Check if signal was correct
                is_win = (color == "R" and is_red) or (color == "G" and not is_red)
                print(f"DEBUG: Signal: {color}, Result: {'red' if is_red else 'green'}, Win: {is_win}")
                
                # Send result to channel using new system
                await send_channel_result(client, message.chat.id, 'red_green', color, phase, is_win, result[0], actual_result, lang)
                    
            except Exception as e:
                print(f"Error processing Red/Green result: {e}")
        else:
            print(f"DEBUG: No Red/Green result found after {max_attempts} attempts")
                
    except Exception as e:
        print(f"Error in Red/Green result checking: {e}")

async def send_channel_result(client, channel_id, signal_type, color, phase, is_win, result_value, result_text, lang):
    """Send formatted result to channel (without session profit)"""
    try:
        
        # Format signal text based on type
        if signal_type == 'red_green':
            if color == "R":
                signal_text = get_text("signal_red", lang)
            else:
                signal_text = get_text("signal_green", lang)
        elif signal_type == 'blocks':
            if color == "B":
                signal_text = get_text("signal_big", lang)
            else:
                signal_text = get_text("signal_small", lang)
        elif signal_type == 'dices':
            if color == "O":
                signal_text = get_text("signal_odd", lang)
            else:
                signal_text = get_text("signal_even", lang)
        
        # Create result message
        if is_win:
            win_text = get_text("result_win", lang)
            result_message = f"📥 {get_text('result', lang)}: {result_value}, {result_text}\n▫️ {get_text('buy', lang)}: {signal_text} 🔸 {win_text}"
            
            # Increment channel win count and send sticker
            win_count = increment_channel_win(channel_id)
            print(f"DEBUG: Channel {channel_id} win #{win_count}")
            
            # Send result message
            await client.send_message(channel_id, result_message)
            
            # Send win sticker based on channel win count
            if str(win_count) in STICKERS:
                try:
                    print(f"DEBUG: Sending win sticker #{win_count} to channel {channel_id}")
                    await client.send_sticker(channel_id, STICKERS[str(win_count)]["file_id"])
                except Exception as e:
                    print(f"Error sending win sticker: {e}")
            else:
                print(f"DEBUG: No sticker available for win count {win_count}")
        else:
            lose_text = get_text("result_lose", lang)
            result_message = f"📥 {get_text('result', lang)}: {result_value}, {result_text}\n▫️ {get_text('buy', lang)}: {signal_text} 🔸 {lose_text}"
            await client.send_message(channel_id, result_message)

        # Append to channel history using latest known issue
        try:
            # Try to extract issue from each game's latest db row
            issue = None
            if signal_type == 'red_green':
                # value, color, issue
                conn = sqlite3.connect('signals_data.db'); c = conn.cursor()
                c.execute("SELECT issue FROM red_green_results ORDER BY timestamp DESC LIMIT 1"); row = c.fetchone(); conn.close()
                issue = row[0] if row else '—'
                choice = 'R' if color == 'R' else 'G'
            elif signal_type == 'blocks':
                conn = sqlite3.connect('signals_data.db'); c = conn.cursor()
                c.execute("SELECT issue FROM blocks_results ORDER BY timestamp DESC LIMIT 1"); row = c.fetchone(); conn.close()
                issue = row[0] if row else '—'
                choice = 'B' if color == 'B' else 'S'
            else:  # dices
                conn = sqlite3.connect('signals_data.db'); c = conn.cursor()
                c.execute("SELECT issue FROM dices_results ORDER BY timestamp DESC LIMIT 1"); row = c.fetchone(); conn.close()
                issue = row[0] if row else '—'
                choice = 'O' if color == 'O' else 'E'
            _append_channel_history(channel_id, str(issue) if issue is not None else '—', choice, int(phase), bool(is_win))
        except Exception as _:
            pass
            
    except Exception as e:
        print(f"Error sending channel result: {e}")

async def send_channel_result_from_user_result(client, signal_type, color, phase, is_win, result_value, result_color, result_emoji, signal_choice, status):
    """Send result to channel from user result processing (clean format without session profit)"""
    try:
        # Get the channel ID from saved signal info
        channel_id = None
        for key, value in channel_wins.items():
            if key.endswith('_signal') and value.get('type') == signal_type:
                # Extract channel ID from key (remove '_signal' suffix)
                channel_id = int(key.replace('_signal', ''))
                break
        
        if not channel_id:
            print(f"DEBUG: No channel found for signal type {signal_type}")
            return
        
        # Get language for the channel
        lang = db.get_group_language(channel_id) or 'en'
        
        # Format result text based on signal type
        if signal_type == 'red_green':
            if result_color == "GREEN":
                result_text = get_text("result_green", lang)
            else:
                result_text = get_text("result_red", lang)
        elif signal_type == 'blocks':
            result_text = str(result_value)  # Use the result value directly
        elif signal_type == 'dices':
            result_text = str(result_value)  # Use the result value directly
        
        # Send result to channel using existing function
        await send_channel_result(client, channel_id, signal_type, color, phase, is_win, str(result_value), result_text, lang)
        
        # Clear the signal info after sending
        for key in list(channel_wins.keys()):
            if key.endswith('_signal') and channel_wins[key].get('type') == signal_type:
                del channel_wins[key]
                break
                
    except Exception as e:
        print(f"Error sending channel result from user result: {e}")

async def simulate_trade_for_channel_result(client, channel_id, signal_type, color, phase, lang):
    """Exact same logic as signal_auto_bot_pyrogram.py"""
    try:
        print(f"DEBUG: Starting result check for {signal_type} in channel {channel_id}")
        
        # Get stored signal info
        channel_id_str = str(channel_id)
        signal_info = channel_wins.get(f"{channel_id_str}_signal", {})
        
        if not signal_info:
            print(f"DEBUG: No stored signal info for channel {channel_id}, skipping result check")
            return
        
        # Check if signal is too old (more than 10 minutes)
        signal_timestamp = signal_info.get('timestamp', 0)
        current_timestamp = datetime.now().timestamp()
        if current_timestamp - signal_timestamp > 600:  # 10 minutes = 600 seconds
            print(f"DEBUG: Signal too old for channel {channel_id}, skipping result check")
            # Clear old signal
            if f"{channel_id_str}_signal" in channel_wins:
                del channel_wins[f"{channel_id_str}_signal"]
            return
        
        print(f"DEBUG: Processing result for channel {channel_id}")
        
        # GAME-SPECIFIC TIMING: All games wait for current minute + 1 second (faster response)
        print(f"DEBUG: {signal_type} - waiting for current minute + 1 second")
        try:
            await wait_for_current_minute_plus_1()
        except asyncio.CancelledError:
            print(f"DEBUG: Task cancelled for channel {channel_id} - new signal received")
            return
        print(f"DEBUG: {signal_type} - starting result checking")
        max_attempts = 30  # Check for 30 seconds
        
        attempt = 0
        latest_issue_row = None
        issue_gate = signal_info.get('issue_number')
        table = 'red_green_results' if signal_type == 'red_green' else ('blocks_results' if signal_type == 'blocks' else 'dices_results')
        # Gate like the signal bot: wait until latest issue > issued issue, then decide using latest row
        while attempt < max_attempts:
            try:
                conn = sqlite3.connect('signals_data.db')
                c = conn.cursor()
                c.execute(f"SELECT issue FROM {table} ORDER BY timestamp DESC LIMIT 1")
                latest_issue_row = c.fetchone()
                conn.close()
                if latest_issue_row and latest_issue_row[0]:
                    if issue_gate is not None:
                        try:
                            if int(latest_issue_row[0]) > int(issue_gate):
                                print(f"DEBUG: Issue gate passed for {signal_type}: latest {latest_issue_row[0]} > issued {issue_gate}")
                                break
                        except Exception:
                            # If comparison fails, fall back to proceeding once any issue exists
                            break
                    else:
                        # No issue bound; proceed when any latest issue exists
                        break
            except Exception as e:
                print(f"DEBUG: Error checking latest issue: {e}")
            attempt += 1
            try:
                await asyncio.sleep(1)
            except asyncio.CancelledError:
                print(f"DEBUG: Task cancelled during result checking for channel {channel_id}")
                return
        
        # Get the actual result (same as signal_auto_bot_pyrogram.py)
        conn = sqlite3.connect('signals_data.db')
        c = conn.cursor()
        
        if signal_type == 'red_green':
            c.execute("SELECT value, color, issue FROM red_green_results ORDER BY timestamp DESC LIMIT 1")
            latest_result = c.fetchone()
            if latest_result:
                value_number, result_color, result_issue = latest_result
                print(f"DEBUG: Got Red/Green result for issue {result_issue}: {value_number}, {result_color}")
                
                # Process result (same logic as signal_auto_bot_pyrogram.py)
                result_lower = result_color.lower().strip()
                # Check for specific number rules first
                try:
                    value_num = int(value_number)
                    if value_num == 5:
                        is_red = False  # 5 = GREEN
                    elif value_num == 0:
                        is_red = True   # 0 = RED
                    else:
                        # Default odd/even rule
                        is_red = 'red' in result_lower
                except:
                    # Fallback to text-based detection
                    is_red = 'red' in result_lower
                win = (color == "R" and is_red) or (color == "G" and not is_red)
                signal_choice = "Red" if color == "R" else "Green"
                result_text = f"{value_number}, {'RED 🔴' if is_red else 'GREEN 🟢'}"
                
        elif signal_type == 'blocks':
            c.execute("SELECT result, issue FROM blocks_results ORDER BY timestamp DESC LIMIT 1")
            latest_result = c.fetchone()
            if latest_result:
                result_value, result_issue = latest_result
                print(f"DEBUG: Got Blocks result for issue {result_issue}: {result_value}")
                
                # Process result (same logic as signal_auto_bot_pyrogram.py)
                result_lower = result_value.lower().strip()
                is_big = 'big' in result_lower
                win = (color == "B" and is_big) or (color == "S" and not is_big)
                signal_choice = "Big" if color == "B" else "Small"
                
                # Clean result text - show just "Big" or "Small"
                if is_big:
                    result_text = "BIG 🔷"
                else:
                    result_text = "SMALL 🔶"
                
        elif signal_type == 'dices':
            c.execute("SELECT result, issue FROM dices_results ORDER BY timestamp DESC LIMIT 1")
            latest_result = c.fetchone()
            if latest_result:
                result_value, result_issue = latest_result
                print(f"DEBUG: Got Dices result for issue {result_issue}: {result_value}")
                
                # Process result (same logic as signal_auto_bot_pyrogram.py)
                result_lower = result_value.lower().strip()
                is_odd = 'odd' in result_lower
                win = (color == "O" and is_odd) or (color == "E" and not is_odd)
                signal_choice = "Odd" if color == "O" else "Even"
                
                # Clean result text - show just "Odd" or "Even"
                if is_odd:
                    result_text = "ODD 🔢"
                else:
                    result_text = "EVEN 🔢"
        
        conn.close()
        
        # Send result message if we found a result
        if 'latest_result' in locals() and latest_result:
            if win:
                win_text = get_text("result_win", lang)
                result_message = f"📥 {get_text('result', lang)}: {result_text}\n▫️ {get_text('buy', lang)}: {signal_choice} 🔸 {win_text}"
                
                # Send message and sticker
                await client.send_message(channel_id, result_message)
                
                # Increment win count and send sticker
                win_count = increment_channel_win(channel_id)
                if str(win_count) in STICKERS:
                    await client.send_sticker(channel_id, STICKERS[str(win_count)]["file_id"])
                    
                # Append to history
                _append_channel_history(channel_id, str(result_issue), 'R' if signal_type=='red_green' and color=='R' else ('G' if signal_type=='red_green' else ('B' if signal_type=='blocks' and color=='B' else ('S' if signal_type=='blocks' else ('O' if signal_type=='dices' and color=='O' else 'E')))), int(phase), True)
            else:
                lose_text = get_text("result_lose", lang)
                result_message = f"📥 {get_text('result', lang)}: {result_text}\n▫️ {get_text('buy', lang)}: {signal_choice} 🔸 {lose_text}"
                await client.send_message(channel_id, result_message)
                # Append to history
                _append_channel_history(channel_id, str(result_issue), 'R' if signal_type=='red_green' and color=='R' else ('G' if signal_type=='red_green' else ('B' if signal_type=='blocks' and color=='B' else ('S' if signal_type=='blocks' else ('O' if signal_type=='dices' and color=='O' else 'E')))), int(phase), False)
            
            print(f"DEBUG: Result sent to channel {channel_id}")
            
            # Clear the signal info after processing to prevent duplicate processing
            if f"{channel_id_str}_signal" in channel_wins:
                del channel_wins[f"{channel_id_str}_signal"]
                print(f"DEBUG: Cleared signal info for channel {channel_id}")
        else:
            print(f"DEBUG: No result found after {max_attempts} attempts")
            
        # Clear signal info even if no result found (to prevent hanging)
        if f"{channel_id_str}_signal" in channel_wins:
            del channel_wins[f"{channel_id_str}_signal"]
            print(f"DEBUG: Cleared signal info for channel {channel_id} (no result)")
        
    except Exception as e:
        print(f"DEBUG: Error in result check: {e}")

async def check_and_send_blocks_result(client, message, bs, phase, lang):
    """Background task to check and send Blocks results"""
    try:
        # Wait for next minute + 4 seconds (precise timing)
        await wait_for_next_minute_plus_4()
        
        # Start checking for results
        max_attempts = 60  # Check for 60 seconds
        attempt = 0
        result = None
        
        while attempt < max_attempts:
            result = await check_blocks_result()
            if result:
                break
            attempt += 1
            await asyncio.sleep(1)  # Check every second
        
        if result:
            try:
                # Process result
                result_lower = result[1].lower().strip()
                is_big = 'big' in result_lower
                actual_result = get_text("result_big", lang) if is_big else get_text("result_small", lang)
                
                # Check if signal was correct
                is_win = (bs == "B" and is_big) or (bs == "S" and not is_big)
                print(f"DEBUG: Blocks Signal: {bs}, Result: {'big' if is_big else 'small'}, Win: {is_win}")
                
                # Send result to channel using new system
                await send_channel_result(client, message.chat.id, 'blocks', bs, phase, is_win, result[0], actual_result, lang)
                    
            except Exception as e:
                print(f"Error processing Blocks result: {e}")
                
    except Exception as e:
        print(f"Error in Blocks result checking: {e}")

async def check_and_send_dices_result(client, message, oe, phase, lang):
    """Background task to check and send Dices results"""
    try:
        # Wait for next minute + 4 seconds (precise timing)
        await wait_for_next_minute_plus_4()
        
        # Start checking for results
        max_attempts = 60  # Check for 60 seconds
        attempt = 0
        result = None
        
        while attempt < max_attempts:
            result = await check_dices_result()
            if result:
                break
            attempt += 1
            await asyncio.sleep(1)  # Check every second
        
        if result:
            try:
                # Process result
                result_lower = result[1].lower().strip()
                is_odd = 'odd' in result_lower
                actual_result = get_text("result_odd", lang) if is_odd else get_text("result_even", lang)
                
                # Check if signal was correct
                is_win = (oe == "O" and is_odd) or (oe == "E" and not is_odd)
                print(f"DEBUG: Dices Signal: {oe}, Result: {'odd' if is_odd else 'even'}, Win: {is_win}")
                
                # Send result to channel using new system
                await send_channel_result(client, message.chat.id, 'dices', oe, phase, is_win, result[0], actual_result, lang)
                    
            except Exception as e:
                print(f"Error processing Dices result: {e}")
                
    except Exception as e:
        print(f"Error in Dices result checking: {e}")

db = Database()
COMMANDS = [
    BotCommand(command="start", description="Start the bot"),
    BotCommand(command="home", description="Show main panel"),
    BotCommand(command="help", description="Show help message"),
    BotCommand(command="back", description="Return to main menu"),
    # BotCommand(command="add_group_chat", description="Add current chat as group"),
    # BotCommand(command="admin_account", description="Admin panel (admins only)"),
    # BotCommand(command="red_green", description="Start Red/Green signal reception"),
    # BotCommand(command="blocks", description="Start Blocks signal reception"),
    # BotCommand(command="dices", description="Start Dices signal reception"),
]
# User states for conversation flow
user_states = {}

# Navigation stack for back button functionality
user_navigation = {}

# Global session for API calls
session_holder = {"session": None}

# Trading states
user_trading_states = {}  # Track if user is ready to receive signals
user_selected_groups = {}  # Track which group each user is copying from

# Temporary storage for login process
temp_login_data = {}  # Store username temporarily during login

# --- In-memory session profit/loss tracking ---
user_session_profit = {}

# --- Per-group stop control ---
# Groups listed here will have all incoming signals ignored until explicitly re-activated
STOPPED_GROUPS: set[str] = set()

# --- In-memory per-user capital management state ---
user_capital_state = {}

# --- Capital Management Bet Calculation ---
def get_next_bet_amount(user_id, win_last_trade, base_amount_default=1.0, phase=1):
    strat_info = get_user_capital_strategy(user_id)
    strategy = strat_info.get('strategy', 'cm_martin')
    base_amounts = strat_info.get('base_amounts', {})
    custom_plans = strat_info.get('custom_plans', {})
    base_amount = base_amounts.get(strategy, base_amount_default)
    state = user_capital_state.get(user_id, {})
    if not state:
        state = {'stage': 0, 'win_streak': 0, 'fibo_seq': [1, 3, 8, 24, 72, 216, 648], 'custom_seq': [], 'last_bet': base_amount}
    # --- Martin (Martingale, 3x progression) ---
    if strategy == 'cm_martin':
        # Use phase-1 as exponent for 3^n
        bet = float(base_amount) * (3 ** (max(0, phase - 1)))
        state['stage'] = max(0, phase - 1)
    # --- Fibo (Fibonacci) ---
    elif strategy == 'cm_fibo':
        fibo_seq = [float(x) for x in custom_plans.get('cm_fibo', '1,3,8,24,72,216,648').replace('-', ',').split(',') if x.strip()]
        stage = max(0, min(phase - 1, len(fibo_seq) - 1))
        state['stage'] = stage
        bet = fibo_seq[stage]
    # --- Victory ---
    elif strategy == 'cm_victory':
        bet = float(base_amount) * (3 ** (max(0, phase - 1)))
        state['stage'] = max(0, phase - 1)
    # --- Fima ---
    elif strategy == 'cm_fima':
        fima_seq = [float(x) for x in custom_plans.get('cm_fima', '1,3,8,24,72,216,648').replace('-', ',').split(',') if x.strip()]
        stage = max(0, min(phase - 1, len(fima_seq) - 1))
        state['stage'] = stage
        bet = fima_seq[stage]
    # --- Custom (Capital1/2/3) ---
    elif strategy in ['cm_custom1', 'cm_custom2', 'cm_custom3']:
        seq = [float(x) for x in custom_plans.get(strategy, str(base_amount)).replace('-', ',').split(',') if x.strip()]
        stage = max(0, min(phase - 1, len(seq) - 1))
        state['stage'] = stage
        bet = seq[stage]
    # --- Default (Martin) ---
    else:
        bet = float(base_amount) * (3 ** (max(0, phase - 1)))
        state['stage'] = max(0, phase - 1)
    user_capital_state[user_id] = state
    return bet

async def get_global_session():
    if session_holder["session"] is None or session_holder["session"].closed:
        session_holder["session"] = aiohttp.ClientSession()
    return session_holder["session"]

async def close_global_session():
    if session_holder["session"] is not None and not session_holder["session"].closed:
        await session_holder["session"].close()
    session_holder["session"] = None

# --- API FUNCTIONS FOR COPY TRADING ---
async def login_to_coinvid(username, password):
    """Login to Coinvid API and get blade_auth token"""
    url = "https://m.coinvidb.com/api/rocket-api/member/login"
    headers = {
        "Accept": "application/json, text/plain, */*",
        "Authorization": "Basic cm9ja2V0X3dlYjpyb2NrZXRfd2Vi",
        "Content-Type": "application/x-www-form-urlencoded",
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
    }
    data = {"username": username, "password": password}
    try:
        session = await get_global_session()
        async with session.post(url, data=data, headers=headers) as response:
            if response.status == 200:
                data = await response.json()
                if data['code'] != 400:
                    return data['data']['access_token']
            return None
    except Exception as e:
        print(f"Login error: {e}")
        return None

async def get_game_info(blade_auth, username=None, password=None):
    """Get current game information"""
    url = "https://m.coinvidb.com/api/rocket-api/game/info/simple?gameName=RG1M"
    headers = {
        "Accept": "application/json, text/plain, */*",
        "Authorization": "Basic cm9ja2V0X3dlYjpyb2NrZXRfd2Vi",
        "Blade-Auth": blade_auth,
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
    }
    try:
        session = await get_global_session()
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                data = await response.json()
                if data['data'] and 'currentIssue' in data['data']:
                    balance = data['data']['balance']
                    current_issue = data['data']['currentIssue']
                    issue_id = current_issue['issue']
                    start_time = current_issue['issueStartTime']
                    last_issue = data['data']['lastIssue']
                    result = last_issue['resultVal']['value'] if last_issue and 'resultVal' in last_issue else None
                    return {
                        'balance': balance,
                        'issue_id': issue_id,
                        'start_time': start_time,
                        'result': result
                    }, blade_auth
            elif response.status == 401 and username and password:
                new_blade_auth = await login_to_coinvid(username, password)
                if new_blade_auth:
                    headers["Blade-Auth"] = new_blade_auth
                    session2 = await get_global_session()
                    async with session2.get(url, headers=headers) as retry_response:
                        if retry_response.status == 200:
                            data = await retry_response.json()
                            if data['data'] and 'currentIssue' in data['data']:
                                balance = data['data']['balance']
                                current_issue = data['data']['currentIssue']
                                issue_id = current_issue['issue']
                                start_time = current_issue['issueStartTime']
                                last_issue = data['data']['lastIssue']
                                result = last_issue['resultVal']['value'] if last_issue and 'resultVal' in last_issue else None
                                return {
                                    'balance': balance,
                                    'issue_id': issue_id,
                                    'start_time': start_time,
                                    'result': result
                                }, new_blade_auth
            return None, blade_auth
    except Exception as e:
        print(f"get_game_info error: {e}")
        return None, blade_auth

async def send_crash(blade_auth, issue, start_time, betamount, color):
    """Place a bet on Red/Green and return order info if possible"""
    url = "https://m.coinvidb.com/api/rocket-api/game/order/save"
    headers = {
        "Authorization": "Basic cm9ja2V0X3dlYjpyb2NrZXRfd2Vi",
        "Blade-Auth": blade_auth,
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16_6 Mobile/15E148 Safari/604.1",
    }
    if color == 'GREEN':
        data = {
            'issue': int(issue),
            "serviceCode": 'G',
            'orderAmount': betamount,
            "orderAmountDetail": betamount,
            "subServiceCode": "RG1M",
            "productId": "0",
            "frontTime": int(start_time),
            "orderDetail": ',,2_1,,,,,,,,,,',
            'orderDetailFormatByI18n': ['', '', 'Green', '', '', '', '', '', '', '', '', '', ''],
        }
    else:  # RED
        data = {
            'issue': int(issue),
            "serviceCode": 'G',
            'orderAmount': betamount,
            "orderAmountDetail": betamount,
            "subServiceCode": "RG1M",
            "productId": "0",
            "frontTime": int(start_time),
            "orderDetail": '2_0,,,,,,,,,,,,',
            'orderDetailFormatByI18n': ['Red', '', '', '', '', '', '', '', '', '', '', '', ''],
        }
    try:
        session = await get_global_session()
        async with session.post(url, json=data, headers=headers) as response:
            if response.status == 200:
                try:
                    resp_data = await response.json()
                    order_no = resp_data.get('data', {}).get('orderNo')
                    issue_id = resp_data.get('data', {}).get('issue')
                except Exception:
                    order_no = None
                    issue_id = None
                print(f"Bet placed: {betamount} on {color} (issue {issue}) orderNo={order_no}")
                return {"success": True, "order_no": order_no, "issue": issue_id}
            else:
                error_text = await response.text()
                print(f"Failed to place bet. Status: {response.status}. Error: {error_text}")
                return {"success": False}
    except Exception as e:
        print(f"send_crash error: {e}")
        return {"success": False}

async def check_result(blade_auth, issue_id, subServiceCode="RG1M"):
    """Check the result of a bet for a specific game."""
    url = "https://m.coinvidb.com/api/rocket-api/game/issue-result/page"
    params = {"subServiceCode": subServiceCode, "size": "1", "current": "1"}
    headers = {
        "Accept": "application/json, text/plain, */*",
        "Authorization": "Basic cm9ja2V0X3dlYjpyb2NrZXRfd2Vi",
        "Blade-Auth": blade_auth,
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
    }
    try:
        session = await get_global_session()
        async with session.get(url, params=params, headers=headers) as response:
            if response.status == 200:
                data = await response.json()
                if data.get('data') and data['data'].get('records'):
                    for record in data['data']['records']:
                        if record.get('issue') == issue_id:
                            # For Blocks/Dices, 'formatValue' is the result ('2_0', ',2_1,')
                            # For Red/Green, 'value' is the integer string
                            if subServiceCode == "RG1M":
                                # For Red/Green, prioritize 'value' field
                                return record.get('value') or record.get('formatValue')
                            else:
                                # For Blocks/Dices, use 'formatValue'
                                return record.get('formatValue') or record.get('value')
            return None
    except Exception as e:
        print(f"check_result error: {e}")
        return None

def create_keyboard(buttons, lang="en"):
    """Create inline keyboard from button list"""
    keyboard = []
    for row in buttons:
        keyboard_row = []
        for button in row:
            if isinstance(button, tuple):
                text, callback_data = button
                keyboard_row.append(InlineKeyboardButton(get_text(text, lang), callback_data=callback_data))
            else:
                keyboard_row.append(InlineKeyboardButton(get_text(button, lang), callback_data=button))
        keyboard.append(keyboard_row)
    return InlineKeyboardMarkup(keyboard)

def add_to_navigation(user_id: int, current_screen: str):
    """Add current screen to user's navigation stack"""
    if user_id not in user_navigation:
        user_navigation[user_id] = []
    user_navigation[user_id].append(current_screen)

def get_previous_screen(user_id: int) -> str:
    """Get the previous screen from user's navigation stack"""
    if user_id in user_navigation and len(user_navigation[user_id]) > 1:
        user_navigation[user_id].pop()  # Remove current screen
        return user_navigation[user_id][-1]  # Return previous screen
    return "start"  # Default to start if no navigation history

def clear_invalid_session(user_id: int):
    """Clear session if user doesn't have valid credentials"""
    session = db.get_session(user_id)
    credentials = db.get_coinvid_credentials(user_id)
    
    # If user has session but no credentials, clear the session
    if session and not credentials:
        db.remove_session(user_id)
        print(f"Cleared invalid session for user {user_id}")

async def setup_commands():
    try:
        # Set commands for private chats
        await app.set_bot_commands(commands=COMMANDS, scope=BotCommandScopeAllPrivateChats())

        # Set the menu button using the correct method
        await app.set_chat_menu_button(menu_button=MenuButtonDefault())

        # For each admin, add /admin_account to their commands
        conn = sqlite3.connect('bot.db')
        c = conn.cursor()
        c.execute("SELECT id FROM users WHERE is_admin=1")
        admin_ids = [row[0] for row in c.fetchall()]
        conn.close()
        for admin_id in admin_ids:
            await app.set_bot_commands(
                commands=COMMANDS + [BotCommand(command="admin_account", description="Admin panel")],
                scope=BotCommandScopeChat(admin_id)
            )
        print("Bot commands and menu button set up successfully!")
    except Exception as e:
        print(f"Error setting up commands: {e}")
global first_time
first_time = True
@app.on_message(filters.command("start"))
async def start_command(client, message: Message):
    """Handle /start command"""
    global first_time
    if first_time:
        await setup_commands()
        # Start signal receiver
        asyncio.create_task(start_signal_receiver())
        first_time = False
    # Check if message has a user
    if not message.from_user:
        await message.reply_text(get_text("cmd_user_only", lang))
        return
    
    user_id = message.from_user.id
    lang = db.get_user_language(user_id)
    
    # Add to navigation
    add_to_navigation(user_id, "start")
    
    # Clear invalid sessions first
    clear_invalid_session(user_id)
    
    # Check if user has valid session AND credentials
    session = db.get_session(user_id)
    credentials = db.get_coinvid_credentials(user_id)
    
    if session and credentials:
        # User is fully logged in with both session and credentials
        await show_home_panel(client, message, lang)
        return
    
    # Welcome message with login and language options
    welcome_text = get_text("welcome", lang)
    keyboard = create_keyboard([
        [("login_btn", "login"), ("language_btn", "language")]
    ], lang)
    
    await message.reply_text(welcome_text, reply_markup=keyboard)

@app.on_message(filters.command("home"))
async def home_command(client, message: Message):
    """Handle /home command"""
    # Check if message has a user
    if not message.from_user:
        await message.reply_text(get_text("cmd_user_only", lang))
        return
    
    user_id = message.from_user.id
    lang = db.get_user_language(user_id)
    
    session = db.get_session(user_id)
    if not session:
        await message.reply_text(get_text("not_logged_in", lang))
        return
    
    await show_home_panel(client, message, lang)

@app.on_message(filters.command("add_group_chat"))
async def add_group_chat_command(client, message: Message):
    """Handle /add_group_chat command - Add current chat to groups list"""
    # Check if message is from a user or channel
    if message.from_user:
        # Message from a user
        user_id = message.from_user.id
        lang = db.get_user_language(user_id)
        
        # Check if user is admin
        if not db.is_admin(user_id):
            await message.reply_text(get_text("not_admin", lang))
            return
    elif message.sender_chat:
        # Message from a channel
        user_id = message.sender_chat.id
        lang = "en"  # Default language for channels
    else:
        # Neither user nor channel
        await message.reply_text("❌ This command can only be used by users or channels.")
        return
    
    chat_id = message.chat.id
    chat_title = getattr(message.chat, 'title', None) or f"Chat {chat_id}"
    
    # Add group to database
    db.add_group(chat_title, get_text("chat_id_text", lang).format(chat_id=chat_id))
    
    await message.reply_text(get_text("group_added", lang))

@app.on_message(filters.command("admin_account"))
async def admin_account_command(client, message: Message):
    """Handle /admin_account command - Open admin panel"""
    # Check if message has a user
    if not message.from_user:
        await message.reply_text(get_text("cmd_user_only", lang))
        return
    
    user_id = message.from_user.id
    lang = db.get_user_language(user_id)
    
    # Check if user is admin
    if not db.is_admin(user_id):
        await message.reply_text(get_text("not_admin", lang))
        return
    
    # Show admin panel
    await show_admin_panel(client, message, lang)

@app.on_message(filters.command("red_green"))
async def red_green_command(client, message: Message):
    """Handle /red_green command - Start signal reception"""
    # Reactivate this group if it was stopped
    try:
        STOPPED_GROUPS.discard(str(message.chat.id))
    except Exception:
        pass
    print(f"DEBUG: /red_green command received in chat {message.chat.id}")
    print(f"DEBUG: Message type: {type(message)}")
    print(f"DEBUG: Message from_user: {message.from_user}")
    print(f"DEBUG: Message chat type: {message.chat.type}")
    chat_id = message.chat.id
    chat_title = getattr(message.chat, 'title', None) or f"Chat {chat_id}"
    print(f"DEBUG: chat_title: {chat_title}")
    # Use group language if set
    lang = get_effective_language(message)
    print(f"DEBUG: lang: {lang}")
    signal_message_1 = get_text("signal_start_msg1", lang)
    signal_message_2 = get_text("signal_start_msg2", lang)
    signal_message_3 = get_text("signal_start_msg3", lang)
    print(f"DEBUG: Sending signal messages to chat {chat_id}")
    await message.reply_text(signal_message_1)
    await message.reply_text(signal_message_2)
    await message.reply_text(signal_message_3)
    print(f"DEBUG: Signal messages sent successfully")
    # Set this group as active for signal reception
    for user_id in db.get_users():
        if db.get_user_selected_group(user_id) == chat_title and db.get_user_trading_status(user_id):
            pass
# --- LANGUAGE SWITCH COMMANDS FOR GROUPS ---
@app.on_message(filters.command("vietnamese"))
async def set_vietnamese_command(client, message: Message):
    chat_id = message.chat.id
    # Only allow in groups
    # if message.chat.type not in ["group", "supergroup"]:
    #     await message.reply_text("❌ This command can only be used in groups.")
    #     return
    print(f"DEBUG: /vietnamese command received")
    print(f"DEBUG: chat_id: {chat_id}")
    print(f"DEBUG: chat_type: {message.chat.type}")
    print(f"DEBUG: chat_title: {message.chat.title}")
    
    # Check current language before setting
    current_lang = db.get_group_language(chat_id)
    print(f"DEBUG: Current group language: {current_lang}")
    
    # Set the language
    db.set_group_language(chat_id, "vi")
    print(f"DEBUG: Language set to 'vi' for group {chat_id}")
    
    # Verify the language was set
    new_lang = db.get_group_language(chat_id)
    print(f"DEBUG: New group language: {new_lang}")
    
    # Show all group languages in database
    if "group_languages" in db.data:
        print(f"DEBUG: All group languages in DB: {db.data['group_languages']}")
    else:
        print(f"DEBUG: No group_languages in DB")
    
    await message.reply_text("🇻🇳 Ngôn ngữ nhóm đã được đặt thành Tiếng Việt!\nTất cả các thông báo sẽ hiển thị bằng tiếng Việt.")

@app.on_message(filters.command("english"))
async def set_english_command(client, message: Message):
    chat_id = message.chat.id
    # if message.chat.type not in ["group", "supergroup"]:
    #     await message.reply_text("❌ This command can only be used in groups.")
    #     return
    print(f"DEBUG: /english command received")
    print(f"DEBUG: chat_id: {chat_id}")
    print(f"DEBUG: chat_type: {message.chat.type}")
    print(f"DEBUG: chat_title: {message.chat.title}")
    
    # Check current language before setting
    current_lang = db.get_group_language(chat_id)
    print(f"DEBUG: Current group language: {current_lang}")
    
    # Set the language
    db.set_group_language(chat_id, "en")
    print(f"DEBUG: Language set to 'en' for group {chat_id}")
    
    # Verify the language was set
    new_lang = db.get_group_language(chat_id)
    print(f"DEBUG: New group language: {new_lang}")
    
    # Show all group languages in database
    if "group_languages" in db.data:
        print(f"DEBUG: All group languages in DB: {db.data['group_languages']}")
    else:
        print(f"DEBUG: No group_languages in DB")
    
    await message.reply_text("🇬🇧 Group language has been set to English!\nAll notifications will be shown in English.")

@app.on_message(filters.command("help"))
async def help_command(client, message: Message):
    """Handle /help command - comprehensive user guide"""
    user_id = message.from_user.id
    lang = db.get_user_language(user_id)
    
    help_text = get_comprehensive_help_text(lang)
    keyboard = create_help_keyboard(lang)
    
    await message.reply_text(help_text, reply_markup=keyboard)


# --- UTILITY: GET LANGUAGE FOR GROUP OR USER ---
def get_effective_language(message):
    print(f"DEBUG: get_effective_language called")
    print(f"DEBUG: message.chat.type: {message.chat.type}")
    print(f"DEBUG: message.chat.id: {message.chat.id}")
    print(f"DEBUG: message.chat.title: {getattr(message.chat, 'title', 'NO_TITLE')}")
    print(f"DEBUG: message.from_user: {message.from_user}")
    print(f"DEBUG: Checking if {message.chat.type} in ['group', 'supergroup', 'channel']")
    print(f"DEBUG: Result: {message.chat.type in ['group', 'supergroup', 'channel']}")
    
    # Check if chat type matches group types
    if message.chat.type in ['group', 'supergroup', 'channel']:
        print(f"DEBUG: Chat type matches, getting group language")
        group_lang = db.get_group_language(message.chat.id)
        print(f"DEBUG: Group {message.chat.id} language: {group_lang}")
        return group_lang
    elif message.from_user:
        print(f"DEBUG: Chat type doesn't match, checking user language")
        user_lang = db.get_user_language(message.from_user.id)
        print(f"DEBUG: User {message.from_user.id} language: {user_lang}")
        return user_lang
    else:
        print(f"DEBUG: No user found, returning default 'en'")
        return "en"

async def show_home_panel(client, message, lang: str, user_id=None):
    """Show home panel with main options"""
    if user_id is None:
        user_id = message.from_user.id
    session = db.get_session(user_id)
    credentials = db.get_coinvid_credentials(user_id)

    if not session or not credentials:
        await message.reply_text(get_text("not_logged_in", lang))
        return

    # Always show user panel by default, even for admins
    await show_user_panel(client, message, lang, user_id=user_id)

async def show_user_panel(client, message: Message, lang: str, user_id=None):
    """Show user dashboard"""
    if user_id is None:
        user_id = message.from_user.id
    add_to_navigation(user_id, "user_panel")
    session = db.get_session(user_id)
    credentials = db.get_coinvid_credentials(user_id)
    if not session or not credentials:
        await start_command(client, message)
        return
    selected_group = db.get_user_selected_group(user_id)
    trading_status = db.get_user_trading_status(user_id)
    # Get current balance
    balance = "Loading..."
    try:
        game_info, _ = await get_game_info(credentials["blade_auth"], credentials["username"], credentials["password"])
        if game_info:
            balance = f"${game_info['balance']}"
    except:
        balance = "Error loading balance"
    # Get user targets (take profit/stop loss)
    user_targets = db.get_user_targets(user_id) if hasattr(db, 'get_user_targets') else {}
    take_profit = user_targets.get('take_profit', 'Not set')
    stop_loss = user_targets.get('stop_loss', 'Not set')
    # Build user info text
    username = session.get("username", "Unknown")
    status_text = get_text("trading_active", lang) if trading_status else get_text("trading_stopped", lang)
    group_text = get_text("group_selected", lang).format(selected_group) if selected_group else get_text("group_not_selected", lang)
    # Get capital management strategy
    capital_strategy = get_user_capital_strategy(user_id)
    capital_strategy_key = capital_strategy.get('strategy', 'Not set')
    # Map strategy key to display name
    strategy_names = {
        'cm_martin': 'Martin',
        'cm_fibo': 'Fibo',
        'cm_victory': 'Victory',
        'cm_fima': 'Fima',
        'cm_custom1': 'Custom 1',
        'cm_custom2': 'Custom 2',
        'cm_custom3': 'Custom 3',
        'Not set': 'Not set'
    }
    capital_strategy_display = strategy_names.get(capital_strategy_key, capital_strategy_key)
    user_info = get_text("user_panel_info", lang).format(username=username, balance=balance, group=group_text, status=status_text)
    user_info += f"\n<b>Capital Management:</b> {capital_strategy_display}"
    keyboard = create_keyboard([
        [("groups_btn", "groups")],
        [("target_btn", "target_panel")],
        [("capital_mgmt_btn", "capital_management_panel")],
        [("history_btn", "user_history")],
        [("info_btn", "info_panel")],
        [("help_btn", "help")],  # Add help button
        [("language_btn", "language")],  # Add language button
        [("start_btn", "start"), ("stop_btn", "stop")],
        [("logout_btn", "logout")]
    ], lang)
    await message.reply_text(user_info, reply_markup=keyboard)

# --- Target Panel Handlers ---
async def show_target_panel(client, callback_query, lang: str):
    user_id = callback_query.from_user.id
    session = db.get_session(user_id)
    credentials = db.get_coinvid_credentials(user_id)
    username = session.get("username", "Unknown")
    balance = "Loading..."
    try:
        game_info, _ = await get_game_info(credentials["blade_auth"], credentials["username"], credentials["password"])
        if game_info:
            balance = f"${game_info['balance']}"
    except:
        balance = "Error loading balance"
    # Get user targets from database
    user_targets = {}
    if hasattr(db, 'data') and 'user_targets' in db.data:
        user_targets = db.data['user_targets'].get(str(user_id), {})
    take_profit = user_targets.get('take_profit', 'Not set')
    stop_loss = user_targets.get('stop_loss', 'Not set')
    # Get user's selected capital management strategy
    capital_strategy = get_user_capital_strategy(user_id)
    capital_strategy_text = capital_strategy.get('strategy', 'Not set')
    text = get_text("target_panel_info", lang).format(username=username, balance=balance, take_profit=take_profit, stop_loss=stop_loss, capital_strategy=capital_strategy_text)
    keyboard = create_keyboard([
        [("back_btn", "back")],
        [("edit_profit_loss_btn", "edit_profit_loss")]
    ], lang)
    await callback_query.message.edit_text(text, reply_markup=keyboard)

async def prompt_edit_profit_loss(client, callback_query, lang: str):
    user_id = callback_query.from_user.id
    user_states[user_id] = "waiting_edit_profit_loss"
    await callback_query.message.edit_text(
        get_text("edit_profit_loss_prompt", lang),
        reply_markup=create_keyboard([[('back_btn', 'target_panel')]], lang)
    )

async def handle_edit_profit_loss(client, message: Message, lang: str):
    user_id = message.from_user.id
    text = message.text.strip()
    take_profit = None
    stop_loss = None
    for line in text.splitlines():
        if line.lower().startswith('take profit:'):
            try:
                take_profit = float(line.split(':', 1)[1].strip())
            except:
                pass
        elif line.lower().startswith('stoploss:'):
            try:
                stop_loss = float(line.split(':', 1)[1].strip())
            except:
                pass
    if take_profit is None and stop_loss is None:
        await message.reply_text(get_text("invalid_format", lang))
        return
    
    # Save to user data
    if not hasattr(db, 'data'):
        db.data = {}
    if 'user_targets' not in db.data:
        db.data['user_targets'] = {}
    
    # Get existing targets and update only the ones provided
    existing_targets = db.data['user_targets'].get(str(user_id), {})
    if take_profit is not None:
        existing_targets['take_profit'] = take_profit
    if stop_loss is not None:
        existing_targets['stop_loss'] = stop_loss
    
    db.data['user_targets'][str(user_id)] = existing_targets
    
    # Save to disk
    if hasattr(db, 'save_data'):
        db.save_data()
    
    # Reset session profit on target change
    global user_session_profit
    user_session_profit[user_id] = 0.0
    
    await message.reply_text(f"✅ Targets updated!\nTake Profit: {take_profit}\nStop Loss: {stop_loss}")
    
    # Send new target panel instead of editing
    await show_target_panel_new_message(client, message, lang)

async def show_target_panel_new_message(client, message: Message, lang: str):
    """Show target panel as a new message instead of editing"""
    user_id = message.from_user.id
    session = db.get_session(user_id)
    credentials = db.get_coinvid_credentials(user_id)
    username = session.get("username", "Unknown")
    balance = "Loading..."
    try:
        game_info, _ = await get_game_info(credentials["blade_auth"], credentials["username"], credentials["password"])
        if game_info:
            balance = f"${game_info['balance']}"
    except:
        balance = "Error loading balance"
    
    # Get user targets from database
    user_targets = {}
    if hasattr(db, 'data') and 'user_targets' in db.data:
        user_targets = db.data['user_targets'].get(str(user_id), {})
    take_profit = user_targets.get('take_profit', 'Not set')
    stop_loss = user_targets.get('stop_loss', 'Not set')
    
    text = get_text("target_panel_info", lang).format(username=username, balance=balance, take_profit=take_profit, stop_loss=stop_loss, capital_strategy="")
    keyboard = create_keyboard([
        [("back_btn", "back")],
        [("edit_profit_loss_btn", "edit_profit_loss")]
    ], lang)
    await message.reply_text(text, reply_markup=keyboard)

async def show_admin_panel(client, message: Message, lang: str):
    """Show admin dashboard"""
    user_id = message.from_user.id
    add_to_navigation(user_id, "admin_panel")
    keyboard = create_keyboard([
        [("group_list", "admin_groups")],
        [("add_username", "add_username"), ("delete_username", "delete_username")],
        [("search_usernames", "search_usernames")],
        [("online_list", "online_list"), ("added_list", "added_list")],
        [("add_admin", "add_admin"), ("remove_admin", "remove_admin")],
        [("added_admins", "added_admins")],
        [("help", "help")],  # Add help button
        [("back", "back_to_start")],
    ], lang)
    help_text = "<b>Admin Help</b>\n\n- Use the buttons below to manage users, groups, and admins.\n- /add_group_chat: Add the current chat as a group.\n- /admin_account: Open this admin panel.\n- /red_green, /blocks, /dices: Start signal reception in a group.\n- Use the user management buttons to add/remove/search users.\n- Use the admin management buttons to add/remove admins.\n- Use the group management buttons to edit group info.\n- Use the language button in the home panel to change language.\n"
    await message.reply_text(get_text("admin_panel", lang) + "\n\n" + help_text, reply_markup=keyboard)

# --- Capital Management Handlers ---
async def show_capital_management_panel(client, callback_query, lang: str):
    user_id = callback_query.from_user.id
    add_to_navigation(user_id, "capital_management_panel")
    # Get user's selected strategy and custom plans
    capital_strategy = get_user_capital_strategy(user_id)
    selected_strategy = capital_strategy.get('strategy', 'Not set')
    base_amounts = capital_strategy.get('base_amounts', {})
    custom_plans = capital_strategy.get('custom_plans', {})
    custom1 = custom_plans.get('cm_custom1', 'Not set')
    custom2 = custom_plans.get('cm_custom2', 'Not set')
    custom3 = custom_plans.get('cm_custom3', 'Not set')
    # Show selected strategy and custom plans
    if selected_strategy in ['cm_custom1', 'cm_custom2', 'cm_custom3']:
        plan = custom_plans.get(selected_strategy, 'Not set') if isinstance(custom_plans, dict) else str(custom_plans)
        text = get_text("capital_management_panel_info", lang).format(
            strategy=selected_strategy,
            base_amount='-',
            custom_plans=plan,
            capital1=custom1,
            capital2=custom2,
            capital3=custom3
        )
    else:
        # Convert custom_plans dict to a string for display, avoid KeyError
        custom_plans_str = ''
        if isinstance(custom_plans, dict):
            custom_plans_str = '\n'.join(f"{k}: {v}" for k, v in custom_plans.items()) if custom_plans else 'Not set'
        else:
            custom_plans_str = str(custom_plans)
        text = get_text("capital_management_panel_info", lang).format(
            strategy=selected_strategy,
            base_amount=base_amounts.get(selected_strategy, 'Not set'),
            custom_plans=custom_plans_str,
            capital1=custom1,
            capital2=custom2,
            capital3=custom3
        )
    keyboard = create_keyboard([
        [("martin_btn", "cm_martin"), ("fibo_btn", "cm_fibo")],
        [("victory_btn", "cm_victory"), ("fima_btn", "cm_fima")],
        [("capital1_btn", "cm_custom1"), ("select_capital1_btn", "select_cm_custom1")],
        [("capital2_btn", "cm_custom2"), ("select_capital2_btn", "select_cm_custom2")],
        [("capital3_btn", "cm_custom3"), ("select_capital3_btn", "select_cm_custom3")],
        [("stages_calculator_btn", "cm_stages_calculator")],
        [("back_btn", "back")]
    ], lang)
    try:
        await callback_query.message.edit_text(text, reply_markup=keyboard)
    except Exception as e:
        if 'MESSAGE_NOT_MODIFIED' in str(e):
            pass  # Ignore this error
        else:
            raise

# When a user selects a custom strategy's Select button
async def confirm_custom_strategy_selected(client, callback_query, lang: str, custom_key: str):
    user_id = callback_query.from_user.id
    set_user_capital_strategy(user_id, custom_key)
    await callback_query.message.edit_text(
        get_text("custom_strategy_selected", lang).format(custom_key.replace('cm_', '').capitalize()),
        reply_markup=create_keyboard([[('back_btn', 'capital_management_panel')]], lang)
    )

# When a custom strategy is saved, show confirmation and Back button
async def confirm_custom_strategy_saved(client, message, lang: str, custom_key: str, custom_plan: str):
    await message.reply_text(
        get_text("custom_strategy_saved", lang).format(custom_key=custom_key, plan=custom_plan),
        reply_markup=create_keyboard([[('back_btn', 'capital_management_panel')]], lang)
    )

# When a user selects a strategy that needs a base amount or sequence, prompt for it
async def prompt_base_amount(client, callback_query, lang: str, strategy_key: str):
    user_id = callback_query.from_user.id
    user_states[user_id] = f"waiting_base_{strategy_key}"
    await callback_query.message.edit_text(
        get_text("prompt_base_amount", lang).format(strategy=strategy_key.replace('cm_', '').capitalize()),
        reply_markup=create_keyboard([[('back_btn', 'capital_management_panel')]], lang)
    )

async def prompt_sequence_plan(client, callback_query, lang: str, strategy_key: str):
    user_id = callback_query.from_user.id
    user_states[user_id] = f"waiting_seq_{strategy_key}"
    await callback_query.message.edit_text(
        get_text("prompt_sequence_plan", lang).format(strategy=strategy_key.replace('cm_', '').capitalize()),
        reply_markup=create_keyboard([[('back_btn', 'capital_management_panel')]], lang)
    )

capital_strategy_descriptions = {
    "cm_martin": "<b>Martin (Martingale)</b>\nDouble the order when losing.\nExample: Lose $1 → bet $3, lose $3 → bet $8, ... If you win, go back to the first order.",
    "cm_fibo": "<b>Fibo (Fibonacci)</b>\nWhen you win, retreat 1 order. When you lose, double the order.\nPlan: 1-3-8-24-72-216-648. If you lose at $648, go back to $1.",
    "cm_victory": "<b>Victory</b>\nDouble the capital when winning.\nExample: Win $1 → bet $3, win $3 → bet $8, ... If you lose, go back to the first order.",
    "cm_fima": "<b>Fima</b>\nWhen winning 2 consecutive orders, return to the first order. When winning 1 order, double the 2nd order. When losing, double the order.\nPlan: 1-3-8. Win $1 → bet $3, win $3 → return to $1. If you lose at $3, bet $8.",
    "cm_stages_calculator": "<b>Stages Calculator</b>\nA tool to help calculate stages for the above strategies.",
}

async def show_capital_strategy_description(client, callback_query, lang: str, strategy_key: str):
    user_id = callback_query.from_user.id
    desc = capital_strategy_descriptions.get(strategy_key, "No description available.")
    # For strategies that require a prompt, show Select and Back
    if strategy_key in ["cm_martin", "cm_victory", "cm_fibo", "cm_fima"]:
        keyboard = create_keyboard([
            [("select_btn", f"select_{strategy_key}"), ("back_btn", "capital_management_panel")]
        ], lang)
    else:
        keyboard = create_keyboard([
            [("select_btn", f"select_{strategy_key}")],
            [("back_btn", "capital_management_panel")]
        ], lang)
    await callback_query.message.edit_text(desc, reply_markup=keyboard)

async def prompt_custom_capital_strategy(client, callback_query, lang: str, custom_key: str):
    user_id = callback_query.from_user.id
    user_states[user_id] = f"waiting_{custom_key}"
    await callback_query.message.edit_text(
        get_text("prompt_custom_capital_strategy", lang).format(custom_key=custom_key),
        reply_markup=create_keyboard([[('back_btn', 'capital_management_panel')]], lang)
    )

# --- Store and get user's selected capital management strategy ---
def set_user_capital_strategy(user_id: int, strategy_key: str, base_amount: float = None, custom_plan: str = None):
    if not hasattr(db, 'data'):
        db.data = {}
    if 'user_capital_strategy' not in db.data:
        db.data['user_capital_strategy'] = {}
    strat = db.data['user_capital_strategy'].get(str(user_id), {})
    strat['strategy'] = strategy_key
    if base_amount is not None:
        if 'base_amounts' not in strat:
            strat['base_amounts'] = {}
        strat['base_amounts'][strategy_key] = base_amount
    if custom_plan is not None:
        if 'custom_plans' not in strat:
            strat['custom_plans'] = {}
        strat['custom_plans'][strategy_key] = custom_plan
    db.data['user_capital_strategy'][str(user_id)] = strat
    if hasattr(db, 'save_data'):
        db.save_data()

def get_user_capital_strategy(user_id: int):
    if hasattr(db, 'data') and 'user_capital_strategy' in db.data:
        return db.data['user_capital_strategy'].get(str(user_id), {})
    return {}

@app.on_callback_query()
async def handle_callback(client, callback_query):
    """Handle all callback queries"""
    user_id = callback_query.from_user.id
    data = callback_query.data
    lang = db.get_user_language(user_id)
    
    try:
        if data == "login":
            await handle_login(client, callback_query, lang)
        elif data == "language":
            await show_language_menu(client, callback_query, lang)
        elif data in ["en", "vi"]:
            await change_language(client, callback_query, data)
        elif data == "back":
            # If coming from groups list, go to user panel without login check
            previous_screen = get_previous_screen(user_id)
            if previous_screen == "groups":
                session = db.get_session(user_id)
                credentials = db.get_coinvid_credentials(user_id)
                if session and credentials:
                    await show_user_panel(client, callback_query.message, lang, user_id=user_id)
                else:
                    await start_command(client, callback_query.message)
            else:
                await go_back_dynamic(client, callback_query, lang)
        elif data == "admin_panel":
            await show_admin_panel(client, callback_query.message, lang)
        elif data == "logout":
            await handle_logout(client, callback_query, lang)
        elif data == "help":
            await show_help_panel(client, callback_query, lang)
        elif data == "groups":
            await show_groups_list(client, callback_query, lang)
        elif data == "start":
            await handle_start(client, callback_query, lang)
        elif data == "stop":
            await handle_stop(client, callback_query, lang)
        elif data == "target_panel":
            await show_target_panel(client, callback_query, lang)
        elif data == "edit_profit_loss":
            await prompt_edit_profit_loss(client, callback_query, lang)
        elif data.startswith("group_"):
            await handle_group_selection(client, callback_query, lang)
        elif data.startswith("select_group_"):
            await select_group(client, callback_query, lang)
        elif data == "done":
            # Go back to user panel (home panel) without login validation
            session = db.get_session(user_id)
            credentials = db.get_coinvid_credentials(user_id)
            if session and credentials:
                await show_user_panel(client, callback_query.message, lang, user_id=user_id)
            else:
                await start_command(client, callback_query.message)
        elif data == "admin_groups":
            await show_admin_groups(client, callback_query, lang)
        elif data.startswith("edit_group_"):
            await show_group_edit(client, callback_query, lang)
        elif data.startswith("delete_group_"):
            await prompt_delete_group(client, callback_query, lang)
        elif data.startswith("toggle_language_"):
            await toggle_group_language(client, callback_query, lang)
        elif data.startswith("confirm_delete_group_"):
            await confirm_delete_group(client, callback_query, lang)
        elif data.startswith("edit_description_"):
            await prompt_edit_description(client, callback_query, lang)
        elif data == "add_group_prompt":
            await prompt_add_group(client, callback_query, lang)
        elif data == "add_username":
            await prompt_add_username(client, callback_query, lang)
        elif data == "delete_username":
            await prompt_delete_username(client, callback_query, lang)
        elif data == "search_usernames":
            await show_search_results(client, callback_query, lang)
        elif data == "online_list":
            await show_online_users(client, callback_query, lang)
        elif data == "added_list":
            await show_added_users(client, callback_query, lang)
        elif data == "add_admin":
            await prompt_add_admin(client, callback_query, lang)
        elif data == "remove_admin":
            await prompt_remove_admin(client, callback_query, lang)
        elif data == "added_admins":
            await show_added_admins(client, callback_query, lang)
        elif data == "back_to_start":
            await start_command(client, callback_query.message)
        elif data == "capital_management_panel":
            await show_capital_management_panel(client, callback_query, lang)
        elif data in ["cm_martin", "cm_victory", "cm_fibo", "cm_fima"]:
            await show_capital_strategy_description(client, callback_query, lang, data)
        elif data == "select_cm_martin":
            await prompt_base_amount(client, callback_query, lang, "cm_martin")
        elif data == "select_cm_victory":
            await prompt_base_amount(client, callback_query, lang, "cm_victory")
        elif data == "select_cm_fibo":
            await prompt_sequence_plan(client, callback_query, lang, "cm_fibo")
        elif data == "select_cm_fima":
            await prompt_sequence_plan(client, callback_query, lang, "cm_fima")
        elif data.startswith("select_cm_custom"):
            # User selects a custom strategy
            await confirm_custom_strategy_selected(client, callback_query, lang, data.replace("select_", ""))
        elif data in ["cm_custom1", "cm_custom2", "cm_custom3"]:
            await prompt_custom_capital_strategy(client, callback_query, lang, data)
        elif data == "user_history":
            await show_user_history_panel(client, callback_query, lang)
        elif data == "info_panel":
            await show_information_panel(client, callback_query, lang)
        elif data == "blocks":
            await blocks_command(client, callback_query, lang)
        elif data == "dices":
            await dices_command(client, callback_query, lang)
        elif data == "cm_stages_calculator":
            await show_stages_calculator_panel(client, callback_query, lang)
        elif data == "stages_calculator_panel":
            await show_stages_calculator_panel(client, callback_query, lang)
        elif data in ["stages_plan7", "stages_plan8", "stages_plan9", "stages_plan10"]:
            await prompt_stages_capital_input(client, callback_query, lang, data)
        else:
            await callback_query.answer("Unknown action")
    
    except Exception as e:
        print(f"Error in callback: {e}")
        traceback.print_exc()
        await callback_query.answer(f"An error occurred: {e}")

async def handle_login(client, callback_query, lang: str):
    """Handle login button click"""
    user_id = callback_query.from_user.id
    # Check if already logged in
    session = db.get_session(user_id)
    credentials = db.get_coinvid_credentials(user_id)
    if session and credentials:
        await callback_query.answer(get_text("already_logged_in", lang))
        return
    # Send login prompt for username&password
    login_text = get_text("login_prompt", lang)
    await callback_query.message.edit_text(login_text)
    # Set user state to waiting for login
    user_states[user_id] = "waiting_login"

async def show_language_menu(client, callback_query, lang: str):
    """Show language selection menu"""
    user_id = callback_query.from_user.id
    add_to_navigation(user_id, "language")
    
    keyboard = create_keyboard([
        [("english", "en"), ("vietnamese", "vi")],
        [("back", "back")]
    ], lang)
    
    await callback_query.message.edit_text(
        get_text("language", lang),
        reply_markup=keyboard
    )

async def change_language(client, callback_query, new_lang: str):
    """Change user language"""
    user_id = callback_query.from_user.id
    db.set_user_language(user_id, new_lang)
    # After changing language, return to home panel if logged in, else start
    session = db.get_session(user_id)
    credentials = db.get_coinvid_credentials(user_id)
    if session and credentials:
        await show_home_panel(client, callback_query.message, new_lang, user_id=user_id)
    else:
        await start_command(client, callback_query.message)

async def go_back(client, callback_query, lang: str):
    """Go back to previous menu"""
    user_id = callback_query.from_user.id
    session = db.get_session(user_id)
    
    if session:
        # Always show user panel by default, even for admins
        await show_user_panel(client, callback_query.message, lang)
    else:
        await start_command(client, callback_query.message)

async def go_back_dynamic(client, callback_query, lang: str):
    """Go back to previous screen based on navigation history"""
    user_id = callback_query.from_user.id
    previous_screen = get_previous_screen(user_id)
    session = db.get_session(user_id)
    credentials = db.get_coinvid_credentials(user_id)
    if previous_screen == "start":
        if session and credentials:
            await show_home_panel(client, callback_query.message, lang, user_id=user_id)
        else:
            await start_command(client, callback_query.message)
    elif previous_screen == "user_panel":
        if session and credentials:
            await show_user_panel(client, callback_query.message, lang, user_id=user_id)
        else:
            await start_command(client, callback_query.message)
    elif previous_screen == "admin_panel":
        await show_admin_panel(client, callback_query.message, lang)
    elif previous_screen == "groups":
        await show_groups_list(client, callback_query, lang)
    elif previous_screen == "admin_groups":
        await show_admin_groups(client, callback_query, lang)
    elif previous_screen == "language":
        await show_language_menu(client, callback_query, lang)
    elif previous_screen == "capital_management_panel":
        await show_capital_management_panel(client, callback_query, lang)
    else:
        # Default fallback
        if session and credentials:
            await show_home_panel(client, callback_query.message, lang, user_id=user_id)
        else:
            await start_command(client, callback_query.message)

async def handle_logout(client, callback_query, lang: str):
    """Handle logout"""
    user_id = callback_query.from_user.id
    db.remove_session(user_id)
    db.remove_online_user(user_id)
    
    await callback_query.answer(get_text("logout", lang))
    await start_command(client, callback_query.message)

async def show_groups_list(client, callback_query, lang: str):
    """Show groups list for users"""
    user_id = callback_query.from_user.id
    add_to_navigation(user_id, "groups")

    groups = db.get_groups()
    selected_group = db.get_user_selected_group(user_id)

    if not groups:
        keyboard = create_keyboard([[('back', 'back')]], lang)
        await callback_query.message.edit_text(
            get_text('no_groups', lang),
            reply_markup=keyboard
        )
        return

    # Create group buttons, mark selected group with ✅
    buttons = []
    for group_name in groups.keys():
        display_name = group_name
        if selected_group == group_name:
            display_name += ' ✅'
        buttons.append([(display_name, f"group_{group_name}")])

    buttons.append([(get_text('done', lang), 'done'), (get_text('back', lang), 'back')])
    keyboard = create_keyboard(buttons, lang)

    await callback_query.message.edit_text(
        get_text('groups', lang),
        reply_markup=keyboard
    )

async def handle_group_selection(client, callback_query, lang: str):
    """Handle group selection"""
    group_name = callback_query.data.replace("group_", "")
    group = db.get_groups().get(group_name)
    
    if not group:
        await callback_query.answer(get_text("group_not_found", lang))
        return
    
    keyboard = create_keyboard([
        [("select", f"select_group_{group_name}")],
        [("back", "groups")]
    ], lang)
    
    await callback_query.message.edit_text(
        f"**{group_name}**\n\n{group['description']}",
        reply_markup=keyboard
    )

async def select_group(client, callback_query, lang: str):
    """Select a group"""
    user_id = callback_query.from_user.id
    group_name = callback_query.data.replace("select_group_", "")

    # Save the selected group for this user
    db.save_user_selected_group(user_id, group_name)

    await callback_query.answer(f"✅ {group_name} selected as your signal source!")

    # Show updated group list with selected group marked
    await show_groups_list(client, callback_query, lang)

async def handle_start(client, callback_query, lang: str):
    """Handle start button"""
    user_id = callback_query.from_user.id
    
    # Check if user has selected a group
    selected_group = db.get_user_selected_group(user_id)
    if not selected_group:
        await callback_query.answer(get_text("please_select_group", lang))
        return
    
    # Check if user has valid credentials
    credentials = db.get_coinvid_credentials(user_id)
    if not credentials:
        await callback_query.answer(get_text("please_login_to_coinvid", lang))
        return
    
    # Fetch and store initial balance
    try:
        game_info, _ = await get_game_info(credentials["blade_auth"], credentials["username"], credentials["password"])
        if game_info and "balance" in game_info:
            db.set_user_initial_balance(user_id, float(game_info["balance"]))
    except Exception as e:
        print(f"Error fetching initial balance: {e}")
    
    # Start trading
    db.set_user_trading_status(user_id, True)
    db.add_online_user(user_id)
    
    await callback_query.answer(get_text("trading_started", lang))
    
    # Update the user panel to show new status
    await show_user_panel(client, callback_query.message, lang, user_id=user_id)

async def handle_stop(client, callback_query, lang: str):
    """Handle stop button"""
    user_id = callback_query.from_user.id
    
    # Stop trading
    db.set_user_trading_status(user_id, False)
    db.remove_online_user(user_id)
    
    await callback_query.answer(get_text("trading_stopped", lang))
    
    # Update the user panel to show new status
    await show_user_panel(client, callback_query.message, lang, user_id=user_id)

# Admin functions
async def show_admin_groups(client, callback_query, lang: str):
    """Show admin groups management"""
    user_id = callback_query.from_user.id
    add_to_navigation(user_id, "admin_groups")
    
    groups = db.get_groups()
    
    if not groups:
        keyboard = create_keyboard([[('back', 'admin_panel')]], lang)
        await callback_query.message.edit_text(
            get_text("no_groups", lang),
            reply_markup=keyboard
        )
        return
    
    # Create group management buttons
    buttons = []
    for group_name in groups.keys():
        buttons.append([(group_name, f"edit_group_{group_name}")])
    
    # Add the "Add Group" button (only once, above the back button)
    buttons.append([(get_text("add_group", lang), "add_group_prompt")])
    buttons.append([("back", "admin_panel")])
    keyboard = create_keyboard(buttons, lang)
    
    await callback_query.message.edit_text(
        get_text("group_list", lang),
        reply_markup=keyboard
    )

async def show_group_edit(client, callback_query, lang: str):
    """Show group edit interface"""
    group_name = callback_query.data.replace("edit_group_", "")
    group = db.get_groups().get(group_name)
    
    if not group:
        await callback_query.answer(get_text("group_not_found", lang))
        return
    
    # Get current group language
    current_lang = db.get_group_language_by_name(group_name)
    lang_emoji = "🇻🇳" if current_lang == "vi" else "🇬🇧"
    lang_text = "Vietnamese" if current_lang == "vi" else "English"
    
    keyboard = create_keyboard([
        [("✏️ Edit", f"edit_description_{group_name}"), (get_text("delete_group", lang), f"delete_group_{group_name}")],
        [(get_text("language_toggle", lang), f"toggle_language_{group_name}")],
        [("back", "admin_groups")]
    ], lang)
    
    await callback_query.message.edit_text(
        f"**{group_name}**\n\n{group['description']}\n\n{get_text('current_language', lang).format(lang_emoji=lang_emoji, lang_text=lang_text)}",
        reply_markup=keyboard
    )

async def prompt_edit_description(client, callback_query, lang: str):
    """Prompt admin to edit group description"""
    user_id = callback_query.from_user.id
    group_name = callback_query.data.replace("edit_description_", "")
    
    # Set user state to waiting for description
    user_states[user_id] = f"waiting_edit_description_{group_name}"
    
    await callback_query.message.edit_text(
        get_text("edit_description_prompt", lang).format(group_name=group_name),
        reply_markup=create_keyboard([[('🔙 Back', f'edit_group_{group_name}')]], lang)
    )

async def prompt_delete_group(client, callback_query, lang: str):
    """Prompt admin to confirm group deletion"""
    user_id = callback_query.from_user.id
    group_name = callback_query.data.replace("delete_group_", "")
    
    keyboard = create_keyboard([
        [(get_text("yes_delete", lang), f"confirm_delete_group_{group_name}")],
        [(get_text("cancel", lang), f"edit_group_{group_name}")]
    ], lang)
    
    await callback_query.message.edit_text(
        f"{get_text('delete_group_confirm_title', lang)}\n\n{get_text('delete_group_confirm_message', lang).format(group_name=group_name)}",
        reply_markup=keyboard
    )

async def toggle_group_language(client, callback_query, lang: str):
    """Toggle group language between English and Vietnamese"""
    user_id = callback_query.from_user.id
    group_name = callback_query.data.replace("toggle_language_", "")
    
    # Get current language and toggle it
    current_lang = db.get_group_language_by_name(group_name)
    new_lang = "vi" if current_lang == "en" else "en"
    
    # Update group language
    db.set_group_language_by_name(group_name, new_lang)
    
    # Show updated group edit panel
    await show_group_edit(client, callback_query, lang)
    
    # Show confirmation message
    lang_emoji = "🇻🇳" if new_lang == "vi" else "🇬🇧"
    lang_text = "Vietnamese" if new_lang == "vi" else "English"
    await callback_query.answer(get_text("language_changed", lang).format(lang_emoji=lang_emoji, lang_text=lang_text))

async def confirm_delete_group(client, callback_query, lang: str):
    """Confirm and execute group deletion"""
    user_id = callback_query.from_user.id
    group_name = callback_query.data.replace("confirm_delete_group_", "")
    
    # Delete the group
    db.remove_group(group_name)
    
    # Show success message and return to admin groups
    keyboard = create_keyboard([[("back", "admin_groups")]], lang)
    await callback_query.message.edit_text(
        f"{get_text('group_deleted_success', lang)}\n\n{get_text('group_deleted_message', lang).format(group_name=group_name)}",
        reply_markup=keyboard
    )

async def prompt_add_group(client, callback_query, lang: str):
    """Prompt admin to add a new group by ID"""
    user_id = callback_query.from_user.id
    user_states[user_id] = "waiting_add_group"
    
    await callback_query.message.edit_text(
        f"{get_text('add_group_prompt_title', lang)}\n\n{get_text('add_group_prompt_message', lang)}\n\n{get_text('add_group_requirements', lang)}",
        reply_markup=create_keyboard([[('🔙 Back', 'admin_groups')]], lang)
    )

async def prompt_add_username(client, callback_query, lang: str):
    """Prompt admin to add username"""
    user_id = callback_query.from_user.id
    user_states[user_id] = "waiting_add_username"
    
    await callback_query.message.edit_text(
        get_text("add_username_prompt", lang),
        reply_markup=create_keyboard([[('back', 'admin_panel')]], lang)
    )

async def prompt_delete_username(client, callback_query, lang: str):
    """Prompt admin to delete username"""
    user_id = callback_query.from_user.id
    user_states[user_id] = "waiting_delete_username"
    
    await callback_query.message.edit_text(
        get_text("delete_username_prompt", lang),
        reply_markup=create_keyboard([[('back', 'admin_panel')]], lang)
    )

async def show_search_results(client, callback_query, lang: str):
    """Show user search results"""
    users = db.get_users()
    
    if not users:
        keyboard = create_keyboard([[("back", "back")]], lang)
        await callback_query.message.edit_text(
            get_text("no_users", lang),
            reply_markup=keyboard
        )
        return
    
    # Create user buttons
    buttons = []
    for username in users.keys():
        buttons.append([(f"user_{username}", f"user_{username}")])
    
    buttons.append([("back", "admin_panel")])
    keyboard = create_keyboard(buttons, lang)
    
    await callback_query.message.edit_text(
        "Search Results:",
        reply_markup=keyboard
    )

async def show_online_users(client, callback_query, lang: str):
    """Show online users"""
    online_users = db.get_online_users()
    users = db.get_users()
    
    if not online_users:
        keyboard = create_keyboard([[("back", "back")]], lang)
        await callback_query.message.edit_text(
            "No online users",
            reply_markup=keyboard
        )
        return
    
    # Find usernames for online user IDs
    online_usernames = []
    for user_id in online_users:
        for username, user_data in users.items():
            if user_data["user_id"] == user_id:
                online_usernames.append(username)
                break
    
    text = "Online Users:\n"
    for username in online_usernames:
        text += f"• {username}\n"
    
    keyboard = create_keyboard([[('back', 'admin_panel')]], lang)
    await callback_query.message.edit_text(text, reply_markup=keyboard)

async def show_added_users(client, callback_query, lang: str):
    """Show added users"""
    users = db.get_users()
    
    if not users:
        keyboard = create_keyboard([[("back", "back")]], lang)
        await callback_query.message.edit_text(
            get_text("no_users", lang),
            reply_markup=keyboard
        )
        return
    
    # Create user buttons
    buttons = []
    for username in users.keys():
        buttons.append([(f"user_{username}", f"user_{username}")])
    
    buttons.append([("back", "admin_panel")])
    keyboard = create_keyboard(buttons, lang)
    
    await callback_query.message.edit_text(
        get_text("added_list", lang),
        reply_markup=keyboard
    )

async def prompt_add_admin(client, callback_query, lang: str):
    """Prompt to add admin"""
    user_id = callback_query.from_user.id
    user_states[user_id] = "waiting_add_admin"
    
    await callback_query.message.edit_text(
        get_text("admin_add_prompt", lang),
        reply_markup=create_keyboard([[('back', 'admin_panel')]], lang)
    )

async def prompt_remove_admin(client, callback_query, lang: str):
    """Prompt to remove admin"""
    user_id = callback_query.from_user.id
    user_states[user_id] = "waiting_remove_admin"
    
    await callback_query.message.edit_text(
        get_text("admin_remove_prompt", lang),
        reply_markup=create_keyboard([[('back', 'admin_panel')]], lang)
    )

async def show_added_admins(client, callback_query, lang: str):
    """Show added admins"""
    admins = db.get_admins()
    users = db.get_users()
    
    if not admins:
        keyboard = create_keyboard([[("back", "back")]], lang)
        await callback_query.message.edit_text(
            get_text("no_admins", lang),
            reply_markup=keyboard
        )
        return
    
    # Find usernames for admin IDs
    admin_usernames = []
    for admin_id in admins:
        for username, user_data in users.items():
            if user_data["user_id"] == admin_id:
                admin_usernames.append(username)
                break
    
    # Create admin buttons
    buttons = []
    for username in admin_usernames:
        buttons.append([(f"admin_{username}", f"admin_{username}")])
    
    buttons.append([("back", "admin_panel")])
    keyboard = create_keyboard(buttons, lang)
    
    await callback_query.message.edit_text(
        get_text("added_admins", lang),
        reply_markup=keyboard
    )

# --- BLK1M Blocks Trade Execution ---
@app.on_message(filters.command("blocks"))
async def blocks_command(client, message: Message):
    """Handle /blocks command - Start BLK1M signal reception"""
    try:
        STOPPED_GROUPS.discard(str(message.chat.id))
    except Exception:
        pass
    chat_id = message.chat.id
    chat_title = getattr(message.chat, 'title', None) or f"Chat {chat_id}"
    lang = get_effective_language(message)
    signal_message_1 = get_text("signal_start_msg4", lang)
    signal_message_2 = get_text("signal_start_msg2", lang)
    signal_message_3 = get_text("signal_start_msg3", lang)
    await message.reply_text(signal_message_1)
    await message.reply_text(signal_message_2)
    await message.reply_text(signal_message_3)
    # Set this group as active for signal reception (handled in process_trading_signal)
    for user_id in db.get_users():
        if db.get_user_selected_group(user_id) == chat_title and db.get_user_trading_status(user_id):
            pass

async def execute_blocks_trade_for_user(client, user_id: int, bs: str, phase: int):
    try:
        credentials = db.get_coinvid_credentials(user_id)
        if not credentials:
            await client.send_message(user_id, "❌ No Coinvid credentials found.")
            return

        # Get user targets from database
        user_targets = {}
        if hasattr(db, 'data') and 'user_targets' in db.data:
            user_targets = db.data['user_targets'].get(str(user_id), {})
        take_profit = user_targets.get('take_profit')
        stop_loss = user_targets.get('stop_loss')
        if user_id not in user_session_profit:
            user_session_profit[user_id] = 0.0
        session_profit = user_session_profit[user_id]

        # --- Check take profit/stop loss by balance ---
        initial_balance = db.get_user_initial_balance(user_id)
        # Always fetch current balance before trade
        # Get BLK1M game info with retry and re-login logic
        import aiohttp
        max_gameinfo_retries = 3
        game_info = None
        issue_id = None
        start_time = None
        for attempt in range(max_gameinfo_retries):
            url = "https://m.coinvidb.com/api/rocket-api/game/info/simple?gameName=BLK1M"
            headers = {
                "Accept": "application/json, text/plain, */*",
                "Authorization": "Basic cm9ja2V0X3dlYjpyb2NrZXRfd2Vi",
                "Blade-Auth": credentials["blade_auth"],
                "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
            }
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data['data'] and 'currentIssue' in data['data']:
                            game_info = data['data']
                            issue_id = game_info['currentIssue']['issue']
                            start_time = game_info['currentIssue']['issueStartTime']
                            break
                        else:
                            await client.send_message(user_id, "❌ Could not get Blocks game info.")
                            return
                    elif response.status == 401 and credentials["username"] and credentials["password"]:
                        # Try re-login
                        new_blade_auth = await login_to_coinvid(credentials["username"], credentials["password"])
                        if new_blade_auth:
                            db.update_blade_auth(user_id, new_blade_auth)
                            credentials["blade_auth"] = new_blade_auth
                        await asyncio.sleep(1)
                    else:
                        if attempt == max_gameinfo_retries - 1:
                            await client.send_message(user_id, f"❌ Failed to get Blocks game info. Status: {response.status}\n[DEBUG] Response: {await response.text()}")
                        await asyncio.sleep(1)
        if not game_info:
            return

        # --- Capital management: determine bet amount ---
        last_trade_win = user_capital_state.get(user_id, {}).get('last_win', True)
        base_amount = 1.0  # Or get from user settings
        bet_amount = get_next_bet_amount(user_id, last_trade_win, base_amount, phase)

        # --- Retry logic for placing bets ---
        max_retries = 10
        order_info = None
        url = "https://m.coinvidb.com/api/rocket-api/game/order/save"
        headers = {
            "Authorization": "Basic cm9ja2V0X3dlYjpyb2NrZXRfd2Vi",
            "Blade-Auth": credentials["blade_auth"],
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
        }
        for attempt in range(max_retries):
            if bs == 'B':
                data = {
                    "issue": int(issue_id),
                    "serviceCode": "G",
                    "orderAmount": bet_amount,
                    "orderAmountDetail": bet_amount,
                    "subServiceCode": "BLK1M",
                    "productId": "0",
                    "frontTime": int(start_time),
                    "orderDetail": "2_0,,,,,,,",
                    "orderDetailFormatByI18n": ["Big", "", "", "", "", "", "", ""]
                }
            else:  # S
                data = {
                    "issue": int(issue_id),
                    "serviceCode": "G",
                    "orderAmount": bet_amount,
                    "orderAmountDetail": bet_amount,
                    "subServiceCode": "BLK1M",
                    "productId": "0",
                    "frontTime": int(start_time),
                    "orderDetail": ",2_1,,,,,,",
                    "orderDetailFormatByI18n": ["", "Small", "", "", "", "", "", ""]
                }
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=data, headers=headers) as response:
                    if response.status == 200:
                        try:
                            resp_data = await response.json()
                            order_no = resp_data.get('data', {}).get('orderNo')
                            issue = resp_data.get('data', {}).get('issue')
                        except Exception as e:
                            order_no = None
                            issue = None
                            await client.send_message(user_id, f"[DEBUG] Error parsing order response: {str(e)}\nResponse: {await response.text()}")
                        order_info = {"success": True, "order_no": order_no, "issue": issue}
                        break
                    else:
                        error_text = await response.text()
                        # If unauthorized, re-login
                        if credentials["username"] and credentials["password"] and response.status == 401:
                            new_blade_auth = await login_to_coinvid(credentials["username"], credentials["password"])
                            if new_blade_auth:
                                db.update_blade_auth(user_id, new_blade_auth)
                                credentials["blade_auth"] = new_blade_auth
                        await asyncio.sleep(1)
        if not order_info or not order_info.get("success"):
            await client.send_message(user_id, f"❌ Blocks trade failed after multiple attempts.\n[DEBUG] Last data: {order_info}")
            return

        # --- Trade execution message with issue and order number ---
        trade_msg = (
            f"🎯 <b>Blocks Trade Executed</b>\n\n"
            f"▫️ Type: {'Big' if bs == 'B' else 'Small'}\n"
            f"▫️ Phase: {phase}\n"
            f"▫️ Amount: ${bet_amount}"
        )
        if order_info.get("issue"):
            trade_msg += f"\n▫️ Issue: {order_info['issue']}"
        if order_info.get("order_no"):
            trade_msg += f"\n▫️ Order No: {order_info['order_no']}"
        await client.send_message(user_id, trade_msg)

        # --- Check result and send result message ---
        # Wait for result (polling)
        result_value = None
        last_error = None
        max_attempts = 300  # Retry for a long time (e.g., 5 minutes)
        for _ in range(max_attempts):
            try:
                # For BLK1M, check result, specifying the subServiceCode
                result_value = await check_result(credentials["blade_auth"], issue_id, "BLK1M")
                if result_value is not None:
                    break
            except Exception as e:
                last_error = str(e)
                break
            await asyncio.sleep(1)
        if result_value is not None:
            # --- Parse BLK1M result for Big/Small and win/loss ---
            result_type = None
            if isinstance(result_value, str):
                if '2_0' in result_value:
                    result_type = 'Big'
                elif '2_1' in result_value:
                    result_type = 'Small'
            
            # Determine win/loss
            user_choice = 'Big' if bs == 'B' else 'Small'
            win = (result_type == user_choice)
            status = "Win" if win else "Lose"
            
            # Update session profit
            profit = 0.95 * bet_amount if win else -bet_amount
            user_session_profit[user_id] += profit
            
            # --- Update capital management state with win/loss ---
            if user_id in user_capital_state:
                user_capital_state[user_id]['last_win'] = win
                
            # Build result message like red/green
            session_profit_fmt = f"{user_session_profit[user_id]:.3f}"
            await client.send_message(
                user_id,
                f"📥 Result: {result_type or 'Unknown'}\n▫️ BUY: {user_choice} 🔸 {status}\nSession profit: {session_profit_fmt}"
            )
            
            # Don't send channel result here - let the background task handle it
            # await send_channel_result_from_user_result(client, 'blocks', bs, phase, win, result_type, result_type, "🎲", user_choice, status)
            
            # Check if targets reached after this trade (session profit)
            session_profit = user_session_profit[user_id]
            session_profit_fmt = f"{session_profit:.3f}"
            if take_profit is not None and session_profit >= float(take_profit):
                stop_msg = (
                    "🛑 <b>Trading Stopped</b>\n\n"
                    "▫️ Reason: Take profit target reached!\n"
                    f"▫️ Session profit: {session_profit_fmt}"
                )
                await client.send_message(user_id, stop_msg)
                db.set_user_trading_status(user_id, False)
            elif stop_loss is not None and session_profit <= -float(stop_loss):
                stop_msg = (
                    "🛑 <b>Trading Stopped</b>\n\n"
                    "▫️ Reason: Stop loss target reached!\n"
                    f"▫️ Session profit: {session_profit_fmt}"
                )
                await client.send_message(user_id, stop_msg)
                db.set_user_trading_status(user_id, False)
        else:
            error_msg = f"❌ Could not get Blocks result for issue {issue_id} after polling."
            if last_error:
                error_msg += f"\n[DEBUG] Error: {last_error}"
            else:
                error_msg += "\n[DEBUG] No result returned from API."
            await client.send_message(user_id, error_msg)
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        await client.send_message(user_id, f"❌ Blocks trade error!\nError: {str(e)}\n[DEBUG]\n{tb}")

@app.on_message(filters.command("activate"))
async def activate_command(client, message: Message):
    """Handle /activate command - confirms bot is working in the group/channel"""
    try:
        # Get chat information first
        chat = await client.get_chat(message.chat.id)
        chat_type = "Group" if chat.type in [ChatType.GROUP, ChatType.SUPERGROUP] else "Channel"
        chat_name = chat.title if hasattr(chat, 'title') else 'N/A'
        
        # Get language for the chat - check group language first
        lang = "en"  # default
        try:
            # Check if group has language setting
            group_lang = db.get_group_language(message.chat.id)
            if group_lang:
                lang = group_lang
                print(f"[ACTIVATE] Using group language: {lang} for chat {message.chat.id}")
            else:
                print(f"[ACTIVATE] No group language set, using default: {lang}")
        except Exception as lang_error:
            print(f"[ACTIVATE] Error getting group language: {lang_error}, using default: {lang}")
        
        # Create success message using translations
        success_message = get_text("bot_activated_success", lang).format(
            chat_type=chat_type,
            chat_name=chat_name
        )
        
        await message.reply_text(success_message)
        print(f"✅ Bot activated successfully in {chat_type} {message.chat.id} with language: {lang}")
        
    except Exception as e:
        # Get language for error message
        lang = "en"  # default
        try:
            group_lang = db.get_group_language(message.chat.id)
            if group_lang:
                lang = group_lang
        except:
            pass
        
        error_message = get_text("bot_activation_failed", lang).format(error=str(e))
        
        await message.reply_text(error_message)
        print(f"❌ Failed to activate bot in {message.chat.id}: {e}")

@app.on_message(filters.command("clean_signals"))
async def clean_signals_command(client, message: Message):
    """Handle /clean_signals command - manually clean old signals"""
    try:
        # Get language for the chat
        lang = get_effective_language(message)
        
        # Check if user is admin
        user_id = message.from_user.id
        if not db.is_admin(user_id):
            await message.reply_text("❌ Only admins can use this command")
            return
        
        # Send initial message
        status_msg = await message.reply_text("🧹 Cleaning old signals...")
        
        # Perform signal cleanup
        await clean_old_signals()
        
        # Update status message
        await status_msg.edit_text("✅ Signal cleanup completed!")
        
    except Exception as e:
        print(f"[BOT] Error in clean_signals command: {e}")
        await message.reply_text("❌ Error cleaning signals")

@app.on_message(filters.command("dices"))
async def dices_command(client, message: Message):
    """Handle /dices command - Start DS1M (Dices) signal reception"""
    try:
        STOPPED_GROUPS.discard(str(message.chat.id))
    except Exception:
        pass
    chat_id = message.chat.id
    chat_title = getattr(message.chat, 'title', None) or f"Chat {chat_id}"
    lang = get_effective_language(message)
    signal_message_1 = get_text("signal_start_msg5", lang)
    signal_message_2 = get_text("signal_start_msg2", lang)
    signal_message_3 = get_text("signal_start_msg3", lang)
    await message.reply_text(signal_message_1)
    await message.reply_text(signal_message_2)
    await message.reply_text(signal_message_3)
    for user_id in db.get_users():
        if db.get_user_selected_group(user_id) == chat_title and db.get_user_trading_status(user_id):
            pass

async def process_dices_signal(client, message: Message, signal: str):
    """Process DS1M signals like Ox1, Ex2, etc."""
    if str(message.chat.id) in STOPPED_GROUPS:
        print(f"DEBUG: Group {message.chat.id} is stopped; ignoring dices signal {signal}")
        return
    print(f"DEBUG: process_dices_signal START")
    print(f"DEBUG: message.chat.id: {message.chat.id}")
    print(f"DEBUG: message.chat.title: {getattr(message.chat, 'title', 'NO_TITLE')}")
    print(f"DEBUG: message.chat.type: {getattr(message.chat, 'type', 'NO_TYPE')}")
    print(f"DEBUG: signal: {signal}")
    
    chat_title = getattr(message.chat, 'title', None) or f"Chat {message.chat.id}"
    print(f"DEBUG: chat_title: {chat_title}")
    
    lang = get_effective_language(message)
    print(f"DEBUG: process_dices_signal - lang: {lang}")
    print(signal)
    # Parse signal - handle both formats: "Ox1" and "Ox1_2030900974" (with issue number)
    signal_match = re.match(r'([OEoe])x(\d+)(?:_(\d+))?', signal)
    print(signal_match)
    if not signal_match:
        print(f"DEBUG: Signal format not recognized: {signal}")
        return
    oe, phase, issue_number = signal_match.groups()
    oe = oe.upper()
    phase = int(phase)
    # issue_number will be None for groups, string for channels
    print(f"DEBUG: Extracted from signal - oe: {oe}, phase: {phase}, issue_number: {issue_number}")
    users = db.get_users()
    print("users db", users)
    type_text = get_text("odd", lang) if oe == "O" else get_text("even", lang)
    type_emoji = "❗️" if oe == "O" else "‼️"
    print(f"DEBUG: type_text: {type_text}")
    
    # Check group language before generating reply
    print(f"DEBUG: Checking group language for chat_id: {message.chat.id}")
    group_lang_check = db.get_group_language(message.chat.id)
    print(f"DEBUG: Group language from DB: {group_lang_check}")
    print(f"DEBUG: Current lang variable: {lang}")
    
    # Save signal info FIRST before creating background task
    print(f"DEBUG: Saving channel info for Dices: {oe}x{phase}")
    # Use issue_number from signal (for channels) or from message attribute (for background)
    final_issue_number = issue_number or getattr(message, 'issue_number', None)
    save_channel_signal_info(message.chat.id, 'dices', oe, phase, issue_number=final_issue_number)
    
    # Send acknowledgment message to the group
    reply_text = get_text("dices_command_received", lang).format(type=type_text, type_emoji=type_emoji, phase=phase)
    
    # Send acknowledgment message to the group
    try:
        # For background signals, send a new message to the group instead of replying
        if hasattr(message, 'reply_text') and callable(getattr(message, 'reply_text', None)):
            # Real message - can reply
            await message.reply_text(reply_text)
        else:
            # Background signal - send new message to the group
            await client.send_message(message.chat.id, reply_text)
            print(f"DEBUG: Background signal - sent acknowledgment message to group with issue {issue_number}")
    except Exception as e:
        print(f"DEBUG: Failed to send acknowledgment message: {e}")
    
    # Create and track the background task - START MONITORING IMMEDIATELY
    print(f"DEBUG: Starting time monitoring immediately for channel result")
    task = asyncio.create_task(simulate_trade_for_channel_result(client, message.chat.id, 'dices', oe, phase, lang))
    
    # Clean up completed tasks
    def cleanup_task():
        pass  # No need to track active tasks anymore
    
    task.add_done_callback(lambda _: cleanup_task())
    
    # Track results for summary
    total_users = len(users)
    executed_trades = 0
    skipped_users = 0
    error_users = 0
    
    for username, user_data in users.items():
        print("we are here 1")
        print("user_data: ", user_data)
        print("username: ", username)
        user_id = user_data["user_id"]
        selected_group = db.get_user_selected_group(user_id)
        trading_status = db.get_user_trading_status(user_id)
        print(selected_group)
        print(chat_title)
        print(trading_status)
        
        # Check if user should trade for this signal
        should_trade = False
        
        # Execute trades for both real messages and background signals
        if selected_group == chat_title and trading_status:
            should_trade = True
            if hasattr(message, 'reply_text') and callable(getattr(message, 'reply_text', None)):
                print(f"DEBUG: User {user_id} has matching group and trading enabled - executing trade (real message)")
            else:
                print(f"DEBUG: User {user_id} has matching group and trading enabled - executing trade (background signal)")
        else:
            if hasattr(message, 'reply_text') and callable(getattr(message, 'reply_text', None)):
                print(f"DEBUG: Real message - conditions not met for user {user_id}")
            else:
                print(f"DEBUG: Background signal - conditions not met for user {user_id}")
            print(f"DEBUG: User {user_id} selected_group: {selected_group}")
            print(f"DEBUG: User {user_id} trading_status: {trading_status}")
        
        if should_trade:
            print("we are here 2")
            try:
                await execute_dices_trade_for_user(client, user_id, oe, phase)
                executed_trades += 1
            except Exception as e:
                print(f"Error executing trade for user {user_id}: {e}")
                error_users += 1
        else:
            print("didn't match")
            print("selected_group: ", selected_group)
            print("chat_title: ", chat_title)
            print("trading_status: ", trading_status)
            skipped_users += 1
    
    # Signal info already saved earlier, no need to save again
    print(f"DEBUG: Signal processing completed")

async def execute_dices_trade_for_user(client, user_id: int, oe: str, phase: int):
    try:
        credentials = db.get_coinvid_credentials(user_id)
        if not credentials:
            await client.send_message(user_id, "❌ No Coinvid credentials found.")
            return
        user_targets = {}
        if hasattr(db, 'data') and 'user_targets' in db.data:
            user_targets = db.data['user_targets'].get(str(user_id), {})
        take_profit = user_targets.get('take_profit')
        stop_loss = user_targets.get('stop_loss')
        if user_id not in user_session_profit:
            user_session_profit[user_id] = 0.0
        session_profit = user_session_profit[user_id]
        initial_balance = db.get_user_initial_balance(user_id)
        import aiohttp
        max_gameinfo_retries = 3
        game_info = None
        issue_id = None
        start_time = None
        for attempt in range(max_gameinfo_retries):
            url = "https://m.coinvidb.com/api/rocket-api/game/info/simple?gameName=DS1M"
            headers = {
                "Accept": "application/json, text/plain, */*",
                "Authorization": "Basic cm9ja2V0X3dlYjpyb2NrZXRfd2Vi",
                "Blade-Auth": credentials["blade_auth"],
                "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
            }
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data['data'] and 'currentIssue' in data['data']:
                            game_info = data['data']
                            issue_id = game_info['currentIssue']['issue']
                            start_time = game_info['currentIssue']['issueStartTime']
                            break
                        else:
                            await client.send_message(user_id, "❌ Could not get Dices game info.")
                            return
                    elif response.status == 401 and credentials["username"] and credentials["password"]:
                        new_blade_auth = await login_to_coinvid(credentials["username"], credentials["password"])
                        if new_blade_auth:
                            db.update_blade_auth(user_id, new_blade_auth)
                            credentials["blade_auth"] = new_blade_auth
                        await asyncio.sleep(1)
                    else:
                        if attempt == max_gameinfo_retries - 1:
                            await client.send_message(user_id, f"❌ Failed to get Dices game info. Status: {response.status}\n[DEBUG] Response: {await response.text()}")
                        await asyncio.sleep(1)
        if not game_info:
            return
        last_trade_win = user_capital_state.get(user_id, {}).get('last_win', True)
        base_amount = 1.0
        bet_amount = get_next_bet_amount(user_id, last_trade_win, base_amount, phase)
        max_retries = 10
        order_info = None
        url = "https://m.coinvidb.com/api/rocket-api/game/order/save"
        headers = {
            "Authorization": "Basic cm9ja2V0X3dlYjpyb2NrZXRfd2Vi",
            "Blade-Auth": credentials["blade_auth"],
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
        }
        for attempt in range(max_retries):
            if oe == 'O':
                data = {
                    'issue': int(issue_id),
                    "serviceCode": 'G',
                    'orderAmount': bet_amount,
                    "orderAmountDetail": bet_amount,
                    "subServiceCode": "DS1M",
                    "productId": "0",
                    "frontTime": int(start_time),
                    'orderDetail': ',2_1,,,,',
                    'orderDetailFormatByI18n': ['', 'Odd', '', '', '', ''],
                }
            else:  # Even
                data = {
                    'issue': int(issue_id),
                    "serviceCode": 'G',
                    'orderAmount': bet_amount,
                    "orderAmountDetail": bet_amount,
                    "subServiceCode": "DS1M",
                    "productId": "0",
                    "frontTime": int(start_time),
                    'orderDetail': ',,,,2_0,',
                    'orderDetailFormatByI18n': ['', '', '', '', 'Even', ''],
                }
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=data, headers=headers) as response:
                    if response.status == 200:
                        try:
                            resp_data = await response.json()
                            order_no = resp_data.get('data', {}).get('orderNo')
                            issue = resp_data.get('data', {}).get('issue')
                        except Exception as e:
                            order_no = None
                            issue = None
                            await client.send_message(user_id, f"[DEBUG] Error parsing order response: {str(e)}\nResponse: {await response.text()}")
                        order_info = {"success": True, "order_no": order_no, "issue": issue}
                        break
                    else:
                        error_text = await response.text()
                        if credentials["username"] and credentials["password"] and response.status == 401:
                            new_blade_auth = await login_to_coinvid(credentials["username"], credentials["password"])
                            if new_blade_auth:
                                db.update_blade_auth(user_id, new_blade_auth)
                                credentials["blade_auth"] = new_blade_auth
                        await asyncio.sleep(1)
        if not order_info or not order_info.get("success"):
            await client.send_message(user_id, f"❌ Dices trade failed after multiple attempts.\n[DEBUG] Last data: {order_info}")
            return
        trade_msg = (
            f"🎯 <b>Dices Trade Executed</b>\n\n"
            f"▫️ Type: {'Odd' if oe == 'O' else 'Even'}\n"
            f"▫️ Phase: {phase}\n"
            f"▫️ Amount: ${bet_amount}"
        )
        if order_info.get("issue"):
            trade_msg += f"\n▫️ Issue: {order_info['issue']}"
        if order_info.get("order_no"):
            trade_msg += f"\n▫️ Order No: {order_info['order_no']}"
        await client.send_message(user_id, trade_msg)
        result_value = None
        last_error = None
        max_attempts = 300
        for _ in range(max_attempts):
            try:
                result_value = await check_result(credentials["blade_auth"], issue_id, "DS1M")
                if result_value is not None:
                    break
            except Exception as e:
                last_error = str(e)
                break
            await asyncio.sleep(1)
        if result_value is not None:
            result_type = None
            if isinstance(result_value, str):
                if '2_1' in result_value:
                    result_type = 'Odd'
                elif '2_0' in result_value:
                    result_type = 'Even'
            user_choice = 'Odd' if oe == 'O' else 'Even'
            win = (result_type == user_choice)
            status = "Win" if win else "Lose"
            profit = 0.95 * bet_amount if win else -bet_amount
            user_session_profit[user_id] += profit
            if user_id in user_capital_state:
                user_capital_state[user_id]['last_win'] = win
            session_profit_fmt = f"{user_session_profit[user_id]:.3f}"
            await client.send_message(
                user_id,
                f"📥 Result: {result_type or 'Unknown'}\n▫️ BUY: {user_choice} 🔸 {status}\nSession profit: {session_profit_fmt}"
            )
            

            
            session_profit = user_session_profit[user_id]
            session_profit_fmt = f"{session_profit:.3f}"
            if take_profit is not None and session_profit >= float(take_profit):
                stop_msg = (
                    "🛑 <b>Trading Stopped</b>\n\n"
                    "▫️ Reason: Take profit target reached!\n"
                    f"▫️ Session profit: {session_profit_fmt}"
                )
                await client.send_message(user_id, stop_msg)
                db.set_user_trading_status(user_id, False)
            elif stop_loss is not None and session_profit <= -float(stop_loss):
                stop_msg = (
                    "🛑 <b>Trading Stopped</b>\n\n"
                    "▫️ Reason: Stop loss target reached!\n"
                    f"▫️ Session profit: {session_profit_fmt}"
                )
                await client.send_message(user_id, stop_msg)
                db.set_user_trading_status(user_id, False)
        else:
            error_msg = f"❌ Could not get Dices result for issue {issue_id} after polling."
            if last_error:
                error_msg += f"\n[DEBUG] Error: {last_error}"
            else:
                error_msg += "\n[DEBUG] No result returned from API."
            await client.send_message(user_id, error_msg)
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        await client.send_message(user_id, f"❌ Dices trade error!\nError: {str(e)}\n[DEBUG]\n{tb}")


@app.on_message(filters.text)
async def handle_text_message(client, message: Message):
    """Handle text messages for login, admin actions, and trading signals"""
    # Check if message has a user
    # if not message.from_user:
    # print(message)
    signal_text = message.text
    print(f"DEBUG: Received text message: '{signal_text}' in chat {message.chat.id}")
    print(f"DEBUG: Message type: {type(message)}")
    print(f"DEBUG: Message from_user: {message.from_user}")
    print(f"DEBUG: Message chat type: {message.chat.type}")
    print(signal_text)
    
    # Skip if this is a command (starts with /)
    if signal_text.startswith('/'):
        print(f"DEBUG: Skipping command message: {signal_text}")
        return
    if "Rx" in signal_text or "Gx" in signal_text or "rx" in signal_text or "gx" in signal_text:
        print("in the trading phase")
        await process_trading_signal(client, message, signal_text)
        return
    elif "Bx" in signal_text or "Sx" in signal_text or "bx" in signal_text or "sx" in signal_text:
        print("in the Blocks trading phase")
        await process_blocks_signal(client, message, signal_text)
        return
    elif "Ex" in signal_text or "Ox" in signal_text or "ex" in signal_text or "ox" in signal_text:
        print("in the Dices trading phase")
        await process_dices_signal(client, message, signal_text)
        return
    else:
        try:
            user_id = message.from_user.id
        except:
            user_id = message.chat.id
        lang = db.get_user_language(user_id)
        
        # Check if this is a trading signal in a group
        # if message.chat.type in ["group", "supergroup"]:
        
        
        # Handle user states for login/admin actions
        if user_id not in user_states:
            return
        
        state = user_states[user_id]
        
        if state == "waiting_login":
            await handle_login_credentials(client, message, lang)
        elif state == "waiting_coinvid_password":
            await handle_coinvid_password(client, message, lang)
        elif state == "waiting_add_username":
            await handle_add_username(client, message, lang)
        elif state == "waiting_delete_username":
            await handle_delete_username(client, message, lang)
        elif state == "waiting_add_admin":
            await handle_add_admin(client, message, lang)
        elif state == "waiting_remove_admin":
            await handle_remove_admin(client, message, lang)
        elif state.startswith("waiting_edit_description_"):
            await handle_edit_description(client, message, lang)
        elif state == "waiting_add_group":
            await handle_add_group(client, message, lang)
        elif state == "waiting_edit_profit_loss":
            await handle_edit_profit_loss(client, message, lang)
        elif state.startswith("waiting_base_"):
            # Handle base amount input
            strategy_key = state.replace("waiting_base_", "")
            try:
                base_amount = float(message.text.strip())
                set_user_capital_strategy(user_id, strategy_key, base_amount=base_amount)
                await message.reply_text(get_text("base_amount_set", lang).format(strategy=strategy_key.replace('cm_', '').capitalize(), amount=base_amount),
                                        reply_markup=create_keyboard([[('back_btn', 'capital_management_panel')]], lang))
            except Exception:
                await message.reply_text(get_text("invalid_base_amount", lang))
        elif state.startswith("waiting_seq_"):
            # Handle sequence input
            strategy_key = state.replace("waiting_seq_", "")
            custom_plan = message.text.strip()
            set_user_capital_strategy(user_id, strategy_key, custom_plan=custom_plan)
            await message.reply_text(get_text("sequence_set", lang).format(strategy=strategy_key.replace('cm_', '').capitalize(), sequence=custom_plan),
                                    reply_markup=create_keyboard([[('back_btn', 'capital_management_panel')]], lang))
        elif state.startswith("waiting_cm_custom"):
            # Handle custom capital management plan input
            custom_key = state.replace("waiting_", "")
            custom_plan = message.text.strip()
            set_user_capital_strategy(user_id, custom_key, custom_plan=custom_plan)
            await confirm_custom_strategy_saved(client, message, lang, custom_key, custom_plan)
        elif state.startswith("waiting_stages_"):
            plan = state.replace("waiting_stages_", "")
            await handle_stages_capital_input(client, message, lang, plan)
        # Clear state
        if user_id in user_states:
            del user_states[user_id]

# --- SIGNAL PROCESSING FUNCTIONS ---
async def  process_trading_signal(client, message: Message, signal: str):
    """Process trading signals like Gx1, Rx2, etc."""
    # Respect group stop state
    if str(message.chat.id) in STOPPED_GROUPS:
        print(f"DEBUG: Group {message.chat.id} is stopped; ignoring trading signal {signal}")
        return
    print(f"DEBUG: process_trading_signal START")
    print(f"DEBUG: message.chat.id: {message.chat.id}")
    print(f"DEBUG: message.chat.title: {getattr(message.chat, 'title', 'NO_TITLE')}")
    print(f"DEBUG: message.chat.type: {getattr(message.chat, 'type', 'NO_TYPE')}")
    print(f"DEBUG: signal: {signal}")
    
    chat_title = getattr(message.chat, 'title', None) or f"Chat {message.chat.id}"
    print(f"DEBUG: chat_title: {chat_title}")
    
    lang = get_effective_language(message)
    print(f"DEBUG: process_trading_signal - lang: {lang}")
    print(signal)
    # Parse signal - handle both formats: "Gx1" and "Gx1_2030900974" (with issue number)
    signal_match = re.match(r'([GRgr])x(\d+)(?:_(\d+))?', signal)
    print(signal_match)
    if not signal_match:
        return
    color, phase, issue_number = signal_match.groups()
    color = color.upper()  # Normalize to uppercase for consistency
    phase = int(phase)
    # issue_number will be None for groups, string for channels
    print(f"DEBUG: Extracted from signal - color: {color}, phase: {phase}, issue_number: {issue_number}")
    users = db.get_users()
    print("users db", users)
    # Acknowledge in group
    color_text = get_text("red", lang) if color == "R" else get_text("green", lang)
    color_emoji = "🔴" if color == "R" else "🟢"
    print(f"DEBUG: color_text: {color_text}")
    
    # Check group language before generating reply
    print(f"DEBUG: Checking group language for chat_id: {message.chat.id}")
    group_lang_check = db.get_group_language(message.chat.id)
    print(f"DEBUG: Group language from DB: {group_lang_check}")
    print(f"DEBUG: Current lang variable: {lang}")
    
    # Save signal info FIRST before creating background task
    print(f"DEBUG: Saving channel info for Red/Green: {color}x{phase}")
    # Use issue_number from signal (for channels) or from message attribute (for background)
    final_issue_number = issue_number or getattr(message, 'issue_number', None)
    save_channel_signal_info(message.chat.id, 'red_green', color, phase, issue_number=final_issue_number)
    
    # Send acknowledgment message to the group
    reply_text = get_text("command_received", lang).format(color=color_text, color_emoji=color_emoji, phase=phase)
    
    # Send acknowledgment message to the group
    try:
        # For background signals, send a new message to the group instead of replying
        if hasattr(message, 'reply_text') and callable(getattr(message, 'reply_text', None)):
            # Real message - can reply
            await message.reply_text(reply_text)
        else:
            # Background signal - send new message to the group
            await client.send_message(message.chat.id, reply_text)
            print(f"DEBUG: Background signal - sent acknowledgment message to group with issue {issue_number}")
    except Exception as e:
        print(f"DEBUG: Failed to send acknowledgment message: {e}")
    
    # Create and track the background task - START MONITORING IMMEDIATELY
    print(f"DEBUG: Starting time monitoring immediately for channel result")
    task = asyncio.create_task(simulate_trade_for_channel_result(client, message.chat.id, 'red_green', color, phase, lang))
    
    # Clean up completed tasks
    def cleanup_task():
        pass  # No need to track active tasks anymore
    
    task.add_done_callback(lambda _: cleanup_task())
    
    # Track results for summary
    total_users = len(users)
    executed_trades = 0
    skipped_users = 0
    error_users = 0
    
    for username, user_data in users.items():
        print("we are here 1")
        print("user_data: ", user_data)
        print("username: ", username)
        user_id = user_data["user_id"]
        selected_group = db.get_user_selected_group(user_id)
        trading_status = db.get_user_trading_status(user_id)
        print("Selected_group: ",selected_group)
        print("chat_title:",chat_title)
        print("trading_status: ", trading_status)
        
        # Check if user should trade for this signal
        should_trade = False
        
        # Execute trades for both real messages and background signals
        if selected_group == chat_title and trading_status:
            should_trade = True
            if hasattr(message, 'reply_text') and callable(getattr(message, 'reply_text', None)):
                print(f"DEBUG: User {user_id} has matching group and trading enabled - executing trade (real message)")
            else:
                print(f"DEBUG: User {user_id} has matching group and trading enabled - executing trade (background signal)")
        else:
            if hasattr(message, 'reply_text') and callable(getattr(message, 'reply_text', None)):
                print(f"DEBUG: Real message - conditions not met for user {user_id}")
            else:
                print(f"DEBUG: Background signal - conditions not met for user {user_id}")
            print(f"DEBUG: User {user_id} selected_group: {selected_group}")
            print(f"DEBUG: User {user_id} trading_status: {trading_status}")
        
        if should_trade:
            print("we are here 2")
            try:
                await execute_trade_for_user(client, user_id, color, phase)
                executed_trades += 1
            except Exception as e:
                print(f"Error executing trade for user {user_id}: {e}")
                error_users += 1
        else:
            print("didn't match")
            print("selected_group: ", selected_group)
            print("chat_title: ", chat_title)
            print("trading_status: ", trading_status)
            skipped_users += 1
    
    # Signal info already saved earlier, no need to save again
    print(f"DEBUG: Signal processing completed")

async def process_blocks_signal(client, message: Message, signal: str):
    """Process BLK1M signals like Bx1, Sx2, etc."""
    if str(message.chat.id) in STOPPED_GROUPS:
        print(f"DEBUG: Group {message.chat.id} is stopped; ignoring blocks signal {signal}")
        return
    print(f"DEBUG: process_blocks_signal START")
    print(f"DEBUG: message.chat.id: {message.chat.id}")
    print(f"DEBUG: message.chat.title: {getattr(message.chat, 'title', 'NO_TITLE')}")
    print(f"DEBUG: message.chat.type: {getattr(message.chat, 'type', 'NO_TYPE')}")
    print(f"DEBUG: signal: {signal}")
    
    chat_title = getattr(message.chat, 'title', None) or f"Chat {message.chat.id}"
    print(f"DEBUG: chat_title: {chat_title}")
    
    lang = get_effective_language(message)
    print(f"DEBUG: process_blocks_signal - lang: {lang}")
    print(signal)
    # Parse signal - handle both formats: "Bx1" and "Bx1_2030900974" (with issue number)
    signal_match = re.match(r'([bBsS])x(\d+)(?:_(\d+))?', signal)
    print(signal_match)
    if not signal_match:
        return
    bs, phase, issue_number = signal_match.groups()
    bs = bs.upper()  # Normalize to uppercase for consistency
    phase = int(phase)
    # issue_number will be None for groups, string for channels
    print(f"DEBUG: Extracted from signal - bs: {bs}, phase: {phase}, issue_number: {issue_number}")
    users = db.get_users()
    print("users db", users)
    # Acknowledge in group
    type_text = get_text("big", lang) if bs == "B" else get_text("small", lang)
    type_emoji = "🔷" if bs == "B" else "🔸"
    print(f"DEBUG: type_text: {type_text}")
    
    # Check group language before generating reply
    print(f"DEBUG: Checking group language for chat_id: {message.chat.id}")
    group_lang_check = db.get_group_language(message.chat.id)
    print(f"DEBUG: Group language from DB: {group_lang_check}")
    print(f"DEBUG: Current lang variable: {lang}")
    
    # Track results for summary
    total_users = len(users)
    executed_trades = 0
    skipped_users = 0
    error_users = 0
    
    for username, user_data in users.items():
        print("we are here 1")
        print("user_data: ", user_data)
        print("username: ", username)
        user_id = user_data["user_id"]
        selected_group = db.get_user_selected_group(user_id)
        trading_status = db.get_user_trading_status(user_id)
        print(selected_group)
        print(chat_title)
        print(trading_status)
        
        # Check if user should trade for this signal
        should_trade = False
        
        # Execute trades for both real messages and background signals
        if selected_group == chat_title and trading_status:
            should_trade = True
            if hasattr(message, 'reply_text') and callable(getattr(message, 'reply_text', None)):
                print(f"DEBUG: User {user_id} has matching group and trading enabled - executing trade (real message)")
            else:
                print(f"DEBUG: User {user_id} has matching group and trading enabled - executing trade (background signal)")
        else:
            if hasattr(message, 'reply_text') and callable(getattr(message, 'reply_text', None)):
                print(f"DEBUG: Real message - conditions not met for user {user_id}")
            else:
                print(f"DEBUG: Background signal - conditions not met for user {user_id}")
            print(f"DEBUG: User {user_id} selected_group: {selected_group}")
            print(f"DEBUG: User {user_id} trading_status: {trading_status}")
        
        if should_trade:
            print("we are here 2")
            try:
                await execute_blocks_trade_for_user(client, user_id, bs, phase)
                executed_trades += 1
            except Exception as e:
                print(f"Error executing trade for user {user_id}: {e}")
                error_users += 1
        else:
            print("didn't match")
            print("selected_group: ", selected_group)
            print("chat_title: ", chat_title)
            print("trading_status: ", trading_status)
            skipped_users += 1
    
    # Save signal info FIRST before creating background task
    print(f"DEBUG: Saving channel info for Blocks: {bs}x{phase}")
    # Use issue_number from signal (for channels) or from message attribute (for background)
    final_issue_number = issue_number or getattr(message, 'issue_number', None)
    save_channel_signal_info(message.chat.id, 'blocks', bs, phase, issue_number=final_issue_number)
    
    # Send acknowledgment message to the group
    reply_text = get_text("blocks_command_received", lang).format(type=type_text, type_emoji=type_emoji, phase=phase)
    
    # Send acknowledgment message to the group
    try:
        # For background signals, send a new message to the group instead of replying
        if hasattr(message, 'reply_text') and callable(getattr(message, 'reply_text', None)):
            # Real message - can reply
            await message.reply_text(reply_text)
        else:
            # Background signal - send new message to the group
            await client.send_message(message.chat.id, reply_text)
            print(f"DEBUG: Background signal - sent acknowledgment message to group with issue {issue_number}")
    except Exception as e:
        print(f"DEBUG: Failed to send acknowledgment message: {e}")
    
    # Create and track the background task - START MONITORING IMMEDIATELY
    print(f"DEBUG: Starting time monitoring immediately for channel result")
    task = asyncio.create_task(simulate_trade_for_channel_result(client, message.chat.id, 'blocks', bs, phase, lang))
    
    # Clean up completed tasks
    def cleanup_task():
        pass  # No need to track active tasks anymore
    
    task.add_done_callback(lambda _: cleanup_task())
    
    # Signal info already saved earlier, no need to save again
    print(f"DEBUG: Signal processing completed")

async def execute_trade_for_user(client, user_id: int, color: str, phase: int):
    try:
        credentials = db.get_coinvid_credentials(user_id)
        if not credentials:
            await client.send_message(user_id, "❌ No Coinvid credentials found.")
            return

        # Get user targets from database
        user_targets = {}
        if hasattr(db, 'data') and 'user_targets' in db.data:
            user_targets = db.data['user_targets'].get(str(user_id), {})
        take_profit = user_targets.get('take_profit')
        stop_loss = user_targets.get('stop_loss')
        if user_id not in user_session_profit:
            user_session_profit[user_id] = 0.0
        session_profit = user_session_profit[user_id]

        # --- Check take profit/stop loss by balance ---
        initial_balance = db.get_user_initial_balance(user_id)
        # Always fetch current balance before trade
        game_info, new_blade_auth = await get_game_info(
            credentials["blade_auth"], credentials["username"], credentials["password"]
        )
        if not game_info and credentials["username"] and credentials["password"]:
            # Try re-login
            new_blade_auth = await login_to_coinvid(credentials["username"], credentials["password"])
            if new_blade_auth:
                db.update_blade_auth(user_id, new_blade_auth)
                credentials["blade_auth"] = new_blade_auth
                game_info, _ = await get_game_info(new_blade_auth, credentials["username"], credentials["password"])
        if not game_info:
            await client.send_message(user_id, "❌ Failed to get game info after re-login.")
            return
        current_balance = float(game_info["balance"])
        # --- SESSION PROFIT/LOSS LOGIC (Flet app style) ---
        session_profit_fmt = f"{session_profit:.3f}"
        if take_profit is not None and session_profit >= float(take_profit):
            stop_msg = (
                "🛑 <b>Trading Stopped</b>\n\n"
                "▫️ Reason: Take profit target reached!\n"
                f"▫️ Session profit: {session_profit_fmt}"
            )
            await client.send_message(user_id, stop_msg)
            db.set_user_trading_status(user_id, False)
            return
        if stop_loss is not None and session_profit <= -float(stop_loss):
            stop_msg = (
                "🛑 <b>Trading Stopped</b>\n\n"
                "▫️ Reason: Stop loss target reached!\n"
                f"▫️ Session profit: {session_profit_fmt}"
            )
            await client.send_message(user_id, stop_msg)
            db.set_user_trading_status(user_id, False)
            return

        # --- Capital management: determine bet amount ---
        # Determine if last trade was a win (for first trade, assume win)
        last_trade_win = user_capital_state.get(user_id, {}).get('last_win', True)
        base_amount = 1.0  # Default fallback
        bet_amount = get_next_bet_amount(user_id, last_trade_win, base_amount, phase)

        # --- Retry logic for placing bets ---
        max_retries = 10
        order_info = None
        for attempt in range(max_retries):
            order_info = await send_crash(
                credentials["blade_auth"],
                game_info["issue_id"],
                game_info["start_time"],
                bet_amount,
                "GREEN" if color == "G" else "RED"
            )
            if order_info and order_info.get("success"):
                break
            # If unauthorized, re-login
            if credentials["username"] and credentials["password"]:
                new_blade_auth = await login_to_coinvid(credentials["username"], credentials["password"])
                if new_blade_auth:
                    db.update_blade_auth(user_id, new_blade_auth)
                    credentials["blade_auth"] = new_blade_auth
            await asyncio.sleep(1)  # Wait before retry
        if not order_info or not order_info.get("success"):
            await client.send_message(user_id, "❌ Trade failed after multiple attempts.")
            return

        # --- Trade execution message with issue and order number ---
        color_emoji = '🟢' if color == 'G' else '🔴'
        trade_msg = (
            f"🎯 <b>Trade Executed</b>\n\n"
            f"▫️ Color: {'Green' if color == 'G' else 'Red'} {color_emoji}\n"
            f"▫️ Phase: {phase}\n"
            f"▫️ Amount: ${bet_amount}"
        )
        if order_info.get("issue"):
            trade_msg += f"\n▫️ Issue: {order_info['issue']}"
        if order_info.get("order_no"): 
            trade_msg += f"\n▫️ Order No: {order_info['order_no']}"
        await client.send_message(user_id, trade_msg)
        # --- Check result and send result message ---
        # Wait for result (polling)
        result_value = None
        last_error = None
        max_attempts = 300  # Retry for a long time (e.g., 5 minutes)
        for _ in range(max_attempts):
            try:
                result_value = await check_result(credentials["blade_auth"], game_info["issue_id"])
                if result_value is not None:
                    break
            except Exception as e:
                last_error = str(e)
                break
            await asyncio.sleep(1)
        if result_value is not None:
            # Determine result color
            try:
                # Clean the result value and try to extract a number
                cleaned_result = str(result_value).strip()
                
                # For Red/Green games, the result should be a simple integer
                # For Blocks/Dices, it might be in format like ",,2_1,,,,,,,,10_7,,"
                if cleaned_result.isdigit():
                    # Simple integer (Red/Green game)
                    value_number = int(cleaned_result)
                elif ',' in cleaned_result and '_' in cleaned_result:
                    # Format like ",,2_1,,,,,,,,10_7,," (Blocks/Dices game)
                    # For Red/Green, we should not be getting this format
                    # This indicates we're getting formatValue instead of value
                    print(f"DEBUG: Got formatValue instead of value for Red/Green: {cleaned_result}")
                    # Try to extract the actual result number from the format
                    parts = cleaned_result.split(',')
                    value_number = None
                    for part in parts:
                        if '_' in part:
                            # Extract number before underscore
                            num_part = part.split('_')[0]
                            if num_part.isdigit():
                                value_number = int(num_part)
                                break
                    if value_number is None:
                        # If no underscore found, try to find any number
                        import re
                        numbers = re.findall(r'\d+', cleaned_result)
                        if numbers:
                            value_number = int(numbers[0])
                else:
                    # Try to extract any number from the string
                    import re
                    numbers = re.findall(r'\d+', cleaned_result)
                    if numbers:
                        value_number = int(numbers[0])
                    else:
                        value_number = None
                
                print(f"DEBUG: Parsed result_value: {result_value}")
                print(f"DEBUG: Extracted value_number: {value_number}")
                
            except Exception as e:
                print(f"DEBUG: Error parsing result: {e}")
                value_number = None
                
            if value_number is not None:
                result_color = "GREEN" if value_number % 2 else "RED"
                result_emoji = "🟢" if result_color == "GREEN" else "🔴"
                signal_choice = "Green" if color == "G" else "Red"
                # Win if signal matches result
                win = (result_color == ("GREEN" if color == "G" else "RED"))
                status = "Win" if win else "Lose"
                # Update session profit
                profit = 0.95 * bet_amount if win else -bet_amount
                user_session_profit[user_id] += profit
                # --- Update capital management state with win/loss ---
                if user_id in user_capital_state:
                    user_capital_state[user_id]['last_win'] = win
                await client.send_message(
                    user_id,
                    f"📥 Result: {value_number}, {result_color}   {result_emoji}\n"
                    f"▫️ BUY: {signal_choice} 🔸 {status}\n"
                    f"Session profit: {user_session_profit[user_id]:.3f}"
                )
                
                            # Don't send channel result here - let the background task handle it
            # await send_channel_result_from_user_result(client, 'red_green', color, phase, win, value_number, result_color, result_emoji, signal_choice, status)

                # Check if targets reached after this trade (session profit)
                session_profit = user_session_profit[user_id]
                session_profit_fmt = f"{session_profit:.3f}"
                if take_profit is not None and session_profit >= float(take_profit):
                    stop_msg = (
                        "🛑 <b>Trading Stopped</b>\n\n"
                        "▫️ Reason: Take profit target reached!\n"
                        f"▫️ Session profit: {session_profit_fmt}"
                    )
                    await client.send_message(user_id, stop_msg)
                    db.set_user_trading_status(user_id, False)
                elif stop_loss is not None and session_profit <= -float(stop_loss):
                    stop_msg = (
                        "🛑 <b>Trading Stopped</b>\n\n"
                        "▫️ Reason: Stop loss target reached!\n"
                        f"▫️ Session profit: {session_profit_fmt}"
                    )
                    await client.send_message(user_id, stop_msg)
                    db.set_user_trading_status(user_id, False)
            else:
                await client.send_message(user_id, f"📥 Result: {result_value}\n▫️ BUY: Unknown 🔸 Unknown")
        else:
            error_msg = f"❌ Could not get result for issue {game_info['issue_id']} after polling."
            if last_error:
                error_msg += f"\nError: {last_error}"
            else:
                error_msg += "\nError: No result returned from API."
            await client.send_message(user_id, error_msg)
    except Exception as e:
        print(f"Error executing trade for user {user_id}: {e}")
        await client.send_message(
            user_id,
            f"❌ Trade error!\nError: {str(e)}"
        )

async def handle_login_credentials(client, message: Message, lang: str):
    """Handle login credentials in username&password format"""
    user_id = message.from_user.id
    text = message.text.strip()
    
    # Expecting format: username&password
    if '&' not in text:
        await message.reply_text(get_text("invalid_format", lang))
        return
    username, password = text.split('&', 1)
    username = username.strip()
    password = password.strip()
    
    print(f"Login attempt - User ID: {user_id}, Username: {username}")
    
    # Check if username exists and is activated
    user_data = db.get_user_by_username(username)
    print(f"User data found: {user_data}")
    
    if user_data:
        # Username is activated - proceed with Coinvid login
        await message.reply_text(get_text("username_activated", lang))
        
        # Attempt Coinvid login
        blade_auth = await login_to_coinvid(username, password)
        if blade_auth:
            print(f"Coinvid login successful for user {username}")
            await message.reply_text(get_text("coinvid_login_success", lang))
            
            # Save credentials and create session
            db.save_coinvid_credentials(user_id, username, password, blade_auth)
            db.create_session(user_id, username)
            db.add_online_user(user_id)
            
            # --- Update user_id and password in users section ---
            user_data["user_id"] = user_id  # Update to real Telegram user ID
            user_data["password"] = password  # Update to latest password
            db.save_data()  # Persist changes
            
            # Go to home panel
            await show_home_panel(client, message, lang)
        else:
            print(f"Coinvid login failed for user {username}")
            await message.reply_text(get_text("coinvid_login_failed", lang))
    else:
        print(f"Login failed - username '{username}' not found or not activated")
        await message.reply_text(get_text("login_failed", lang))

async def handle_coinvid_password(client, message: Message, lang: str):
    """Handle Coinvid password"""
    user_id = message.from_user.id
    password = message.text.strip()
    
    print(f"Coinvid password attempt - User ID: {user_id}")
    
    # Get username from temporary storage
    username = temp_login_data.get(user_id)
    if not username:
        await message.reply_text("❌ Error: Username not found. Please try logging in again.")
        if user_id in user_states:
            del user_states[user_id]
        return
    
    # Attempt Coinvid login
    blade_auth = await login_to_coinvid(username, password)
    
    if blade_auth:
        print(f"Coinvid login successful for user {username}")
        await message.reply_text("✅ Coinvid login successful! You are now logged in.")
        
        # Save credentials and create session
        db.save_coinvid_credentials(user_id, username, password, blade_auth)
        db.create_session(user_id, username)
        db.add_online_user(user_id)
        
        # Clean up temporary data
        if user_id in temp_login_data:
            del temp_login_data[user_id]
        if user_id in user_states:
            del user_states[user_id]
        
        # Go back to home panel
        await show_home_panel(client, message, lang)
    else:
        print(f"Coinvid login failed for user {username}")
        await message.reply_text("❌ Coinvid login failed. Please check your password and try again.")
        # Clear temporary data
        if user_id in temp_login_data:
            del temp_login_data[user_id]
        if user_id in user_states:
            del user_states[user_id]

async def handle_add_username(client, message: Message, lang: str):
    """Handle adding username"""
    user_id = message.from_user.id
    
    if not db.is_admin(user_id):
        await message.reply_text(get_text("not_admin", lang))
        return
    
    username = message.text.strip()
    
    # Generate a random password for future use
    import random
    import string
    password = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
    
    # Add user with generated password
    db.add_user(0, username, password)  # Placeholder user_id
    
    keyboard = create_keyboard([[("back", "admin_panel")]], lang)
    await message.reply_text(
        f"✅ User '{username}' added and activated successfully!",
        reply_markup=keyboard
    )

async def handle_delete_username(client, message: Message, lang: str):
    """Handle deleting username"""
    user_id = message.from_user.id
    
    if not db.is_admin(user_id):
        await message.reply_text(get_text("not_admin", lang))
        return
    
    username = message.text.strip()
    
    # Remove user
    users = db.get_users()
    if username in users:
        del users[username]
        db.save_data()
        await message.reply_text(get_text("username_removed", lang))
    else:
        await message.reply_text(get_text("user_not_found", lang))

async def handle_add_admin(client, message: Message, lang: str):
    """Handle adding admin"""
    user_id = message.from_user.id
    
    if not db.is_admin(user_id):
        await message.reply_text(get_text("not_admin", lang))
        return
    
    try:
        admin_id = int(message.text.strip())
        db.add_admin(admin_id)
        await message.reply_text(get_text("admin_added", lang))
    except ValueError:
        await message.reply_text(get_text("invalid_admin_id", lang))

async def handle_edit_description(client, message: Message, lang: str):
    """Handle editing group description"""
    user_id = message.from_user.id
    
    if not db.is_admin(user_id):
        await message.reply_text(get_text("not_admin", lang))
        return
    
    # Extract group name from state
    state = user_states.get(user_id, "")
    group_name = state.replace("waiting_edit_description_", "")
    
    new_description = message.text.strip()
    
    # Update group description
    db.update_group_description(group_name, new_description)
    
    # Show success message with back button
    keyboard = create_keyboard([[("🔙 Back", f"edit_group_{group_name}")]], lang)
    await message.reply_text(
        f"{get_text('description_updated', lang).format(group_name=group_name)}\n\n{get_text('new_description', lang).format(new_description=new_description)}",
        reply_markup=keyboard
    )

async def handle_remove_admin(client, message: Message, lang: str):
    """Handle removing admin"""
    user_id = message.from_user.id
    
    if not db.is_admin(user_id):
        await message.reply_text(get_text("not_admin", lang))
        return
    
    try:
        admin_id = int(message.text.strip())
        db.remove_admin(admin_id)
        await message.reply_text(get_text("admin_removed", lang))
    except ValueError:
        await message.reply_text(get_text("invalid_admin_id", lang))

async def handle_add_group(client, message: Message, lang: str):
    """Handle adding a new group by ID"""
    user_id = message.from_user.id
    
    if not db.is_admin(user_id):
        await message.reply_text(get_text("not_admin", lang))
        return
    
    try:
        group_id = int(message.text.strip())
        
        # Try to get chat information
        try:
            chat = await client.get_chat(group_id)
            chat_title = chat.title
            chat_username = getattr(chat, 'username', None)
            
            # Check if bot is in the group
            bot_member = await client.get_chat_member(group_id, (await client.get_me()).id)
            
            # Add group with title and username (regardless of admin status)
            group_name = chat_title
            description = get_text("group_id_text", lang).format(group_id=group_id)
            if chat_username:
                description += f" | @{chat_username}"
            
            db.add_group(group_name, description)
            
            keyboard = create_keyboard([[("🔙 Back", "admin_groups")]], lang)
            await message.reply_text(
                f"{get_text('group_added_success', lang)}\n\n{get_text('group_added_with_info', lang).format(chat_title=chat_title, group_id=group_id, chat_username=chat_username if chat_username else 'None')}",
                reply_markup=keyboard
            )
            
        except Exception as e:
            # If we can't get chat info, add with ID only
            group_name = f"Group {group_id}"
            description = get_text("group_id_text", lang).format(group_id=group_id)
            
            db.add_group(group_name, description)
            
            keyboard = create_keyboard([[("🔙 Back", "admin_groups")]], lang)
            await message.reply_text(
                f"{get_text('group_added_success', lang)}\n\n{get_text('group_added_fallback', lang).format(group_name=group_name, group_id=group_id)}",
                reply_markup=keyboard
            )
            
    except ValueError:
        keyboard = create_keyboard([[("🔙 Back", "admin_groups")]], lang)
        await message.reply_text(
            f"{get_text('invalid_group_id', lang)}\n\n{get_text('invalid_group_id_message', lang)}",
            reply_markup=keyboard
        )

# --- User History Panel ---
async def show_user_history_panel(client, callback_query, lang: str):
    user_id = callback_query.from_user.id
    credentials = db.get_coinvid_credentials(user_id)
    if not credentials:
        await callback_query.message.edit_text("❌ Please login to view your history.", reply_markup=create_keyboard([[('Back', 'back')]], lang))
        return

    blade_auth = credentials.get("blade_auth")
    username = credentials.get("username")
    password = credentials.get("password")

    # Fetch last 20 trades from Coinvid API (to cover both games)
    url = "https://m.coinvidb.com/api/rocket-api/game/order/page?current=1&size=20&isPageNum=false&serviceCode=G"
    headers = {
        "Authorization": "Basic cm9ja2V0X3dlYjpyb2NrZXRfd2Vi",
        "Blade-Auth": blade_auth or "",
        "Accept-Language": "en-US",
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
        "Accept": "application/json",
    }

    history_text = "<b>📜 Trade History (last 20)</b>\n\n"
    try:
        session = await get_global_session()
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                data = await response.json()
                print(data)  # For debugging
                records = data['data']['records']
                # Separate RG1M and BLK1M
                rg_trades = [r for r in records if r.get('subServiceCode') == 'RG1M']
                blk_trades = [r for r in records if r.get('subServiceCode') == 'BLK1M']
                if rg_trades:
                    history_text += '<b>🔴🟢 Red/Green</b>\n'
                    for r in rg_trades:
                        status = r.get('statusI18n', 'Unknown')
                        status_emoji = '✅' if status == 'Won' else '❌' if status == 'Lost' else '⏳' if status == 'No Result' else '❔'
                        # Determine color
                        bet_color = 'Unknown'
                        if 'orderDetailFormatByI18n' in r:
                            if 'Green' in r['orderDetailFormatByI18n']:
                                bet_color = 'Green 🟢'
                            elif 'Red' in r['orderDetailFormatByI18n']:
                                bet_color = 'Red 🔴'
                        profit = r.get('profit', '')
                        loss = r.get('loss', '')
                        back_amount = r.get('backAmount', '')
                        time_str = r.get('orderTime', '')
                        history_text += (
                            f"<b>Issue:</b> {r.get('issue', '')} | <b>Order:</b> {r.get('orderNo', '')}\n"
                            f"<b>Color:</b> {bet_color} | <b>Amount:</b> ${r.get('orderAmount', '')}\n"
                            f"<b>Status:</b> {status} {status_emoji} | <b>Profit:</b> {profit} | <b>Loss:</b> {loss}\n"
                            f"<b>Back Amount:</b> {back_amount} | <b>Time:</b> {time_str}\n\n"
                        )
                if blk_trades:
                    history_text += '<b>🟦 Blocks</b>\n'
                    for r in blk_trades:
                        status = r.get('statusI18n', 'Unknown')
                        status_emoji = '✅' if status == 'Won' else '❌' if status == 'Lost' else '⏳' if status == 'No Result' else '❔'
                        # Determine Big/Small
                        bet_type = 'Unknown'
                        if 'orderDetailFormatByI18n' in r:
                            if 'Big' in r['orderDetailFormatByI18n']:
                                bet_type = 'Big'
                            elif 'Small' in r['orderDetailFormatByI18n']:
                                bet_type = 'Small'
                        profit = r.get('profit', '')
                        loss = r.get('loss', '')
                        back_amount = r.get('backAmount', '')
                        time_str = r.get('orderTime', '')
                        history_text += (
                            f"<b>Issue:</b> {r.get('issue', '')} | <b>Order:</b> {r.get('orderNo', '')}\n"
                            f"<b>Type:</b> {bet_type} | <b>Amount:</b> ${r.get('orderAmount', '')}\n"
                            f"<b>Status:</b> {status} {status_emoji} | <b>Profit:</b> {profit} | <b>Loss:</b> {loss}\n"
                            f"<b>Back Amount:</b> {back_amount} | <b>Time:</b> {time_str}\n\n"
                        )
                if not rg_trades and not blk_trades:
                    history_text += "No trades found."
            elif response.status == 401 and username and password:
                # Try to re-login and retry the request
                print(f"DEBUG: 401 error for user {user_id}, attempting re-login...")
                new_blade_auth = await login_to_coinvid(username, password)
                if new_blade_auth:
                    # Update the stored credentials with new blade_auth
                    credentials["blade_auth"] = new_blade_auth
                    db.save_coinvid_credentials(user_id, credentials)
                    print(f"DEBUG: Re-login successful for user {user_id}, retrying history request...")

                    # Retry with new blade_auth
                    headers["Blade-Auth"] = new_blade_auth
                    session2 = await get_global_session()
                    async with session2.get(url, headers=headers) as retry_response:
                        if retry_response.status == 200:
                            data = await retry_response.json()
                            print(f"DEBUG: History request successful after re-login for user {user_id}")
                            records = data['data']['records']
                            # Separate RG1M and BLK1M
                            rg_trades = [r for r in records if r.get('subServiceCode') == 'RG1M']
                            blk_trades = [r for r in records if r.get('subServiceCode') == 'BLK1M']
                            if rg_trades:
                                history_text += '<b>🔴🟢 Red/Green</b>\n'
                                for r in rg_trades:
                                    status = r.get('statusI18n', 'Unknown')
                                    status_emoji = '✅' if status == 'Won' else '❌' if status == 'Lost' else '⏳' if status == 'No Result' else '❔'
                                    # Determine color
                                    bet_color = 'Unknown'
                                    if 'orderDetailFormatByI18n' in r:
                                        if 'Green' in r['orderDetailFormatByI18n']:
                                            bet_color = 'Green 🟢'
                                        elif 'Red' in r['orderDetailFormatByI18n']:
                                            bet_color = 'Red 🔴'
                                    profit = r.get('profit', '')
                                    loss = r.get('loss', '')
                                    back_amount = r.get('backAmount', '')
                                    time_str = r.get('orderTime', '')
                                    history_text += (
                                        f"<b>Issue:</b> {r.get('issue', '')} | <b>Order:</b> {r.get('orderNo', '')}\n"
                                        f"<b>Color:</b> {bet_color} | <b>Amount:</b> ${r.get('orderAmount', '')}\n"
                                        f"<b>Status:</b> {status} {status_emoji} | <b>Profit:</b> {profit} | <b>Loss:</b> {loss}\n"
                                        f"<b>Back Amount:</b> {back_amount} | <b>Time:</b> {time_str}\n\n"
                                    )
                            if blk_trades:
                                history_text += '<b>🟦 Blocks</b>\n'
                                for r in blk_trades:
                                    status = r.get('statusI18n', 'Unknown')
                                    status_emoji = '✅' if status == 'Won' else '❌' if status == 'Lost' else '⏳' if status == 'No Result' else '❔'
                                    # Determine Big/Small
                                    bet_type = 'Unknown'
                                    if 'orderDetailFormatByI18n' in r:
                                        if 'Big' in r['orderDetailFormatByI18n']:
                                            bet_type = 'Big'
                                        elif 'Small' in r['orderDetailFormatByI18n']:
                                            bet_type = 'Small'
                                    profit = r.get('profit', '')
                                    loss = r.get('loss', '')
                                    back_amount = r.get('backAmount', '')
                                    time_str = r.get('orderTime', '')
                                    history_text += (
                                        f"<b>Issue:</b> {r.get('issue', '')} | <b>Order:</b> {r.get('orderNo', '')}\n"
                                        f"<b>Type:</b> {bet_type} | <b>Amount:</b> ${r.get('orderAmount', '')}\n"
                                        f"<b>Status:</b> {status} {status_emoji} | <b>Profit:</b> {profit} | <b>Loss:</b> {loss}\n"
                                        f"<b>Back Amount:</b> {back_amount} | <b>Time:</b> {time_str}\n\n"
                                    )
                            if not rg_trades and not blk_trades:
                                history_text += "No trades found."
                        else:
                            error_text = await retry_response.text()
                            history_text += f"❌ Failed to fetch history after re-login. Status: {retry_response.status}\n[DEBUG] {error_text}"
                else:
                    history_text += "❌ Failed to re-login. Please login again manually."
            else:
                error_text = await response.text()
                history_text += f"❌ Failed to fetch history. Status: {response.status}\n[DEBUG] {error_text}"
    except Exception as e:
        history_text += f"❌ Error: {e}"
    keyboard = create_keyboard([[('Back', 'back')]], lang)
    await callback_query.message.edit_text(history_text, reply_markup=keyboard)

# --- Information Panel ---
async def show_information_panel(client, callback_query, lang: str):
    user_id = callback_query.from_user.id
    session = db.get_session(user_id)
    credentials = db.get_coinvid_credentials(user_id)
    selected_group = db.get_user_selected_group(user_id)
    trading_status = db.get_user_trading_status(user_id)
    # Initial balance
    initial_balance = db.get_user_initial_balance(user_id)
    # Current balance
    balance = 0.0
    try:
        game_info, _ = await get_game_info(credentials["blade_auth"], credentials["username"], credentials["password"])
        if game_info:
            balance = float(game_info['balance'])
    except:
        pass
    # Current profit
    session_profit = user_session_profit.get(user_id, 0.0)
    # Targets
    user_targets = db.get_user_targets(user_id) if hasattr(db, 'get_user_targets') else {}
    take_profit = user_targets.get('take_profit')
    stop_loss = user_targets.get('stop_loss')
    # Capital management
    capital_strategy = get_user_capital_strategy(user_id)
    capital_mgmt = capital_strategy.get('strategy', 'Not set').replace('cm_', '').capitalize()
    custom_plans = capital_strategy.get('custom_plans', {})
    capital1 = custom_plans.get('cm_custom1', '0')
    capital2 = custom_plans.get('cm_custom2', '0')
    capital3 = custom_plans.get('cm_custom3', '0')
    # Format values
    def fmt(val):
        try:
            if val is None or val == "Not set":
                return "Not set"
            return f"{float(val):.3f}"
        except:
            return str(val)
    username = session.get("username", "Unknown")
    status_text = get_text("trading_active", lang) if trading_status else get_text("trading_stopped", lang)
    group_text = get_text("group_selected", lang).format(selected_group) if selected_group else get_text("group_not_selected", lang)
    info_text = get_text("info_panel_info", lang).format(username=username, status=status_text, initial_balance=fmt(initial_balance), balance=fmt(balance), profit=fmt(session_profit), take_profit=fmt(take_profit), stop_loss=fmt(stop_loss), group=group_text, capital_mgmt=capital_mgmt, capital1=capital1, capital2=capital2, capital3=capital3)
    keyboard = create_keyboard([
        [("groups_btn", "groups"), ("settings_btn", "settings")],
        [("start_btn", "start"), ("stop_btn", "stop")],
        [("target_btn", "target_panel")],
        [("capital_mgmt_btn", "capital_management_panel")],
        [("history_btn", "user_history")],
        [("info_btn", "info_panel")],
        [("logout_btn", "logout")],
        [("back_btn", "back")]
    ], lang)
    await callback_query.message.edit_text(info_text, reply_markup=keyboard)

# --- Stages Calculator Logic (from Calculator bot2.py) ---
def calculate_stages_plan7(capital, multiple=2.5):
    calculated_amounts = {2.5: 406.2, 3: 1093, 3.5: 2573.1718, 4: 5461}
    calculated_amount = calculated_amounts.get(multiple, 406.2)
    bet_amounts = []
    for i in range(1, 8):
        bet_amount = round(capital / (calculated_amount / (multiple ** (i - 1))), 3)
        bet_amounts.append(bet_amount)
    return bet_amounts

def calculate_stages_plan8(capital):
    ba1 = capital / 342.9
    bet_amounts = [ba1]
    for _ in range(7):
        bet_amounts.append(bet_amounts[-1] * 2.1)
    bet_amounts = [round(x, 2 if capital <= 18 else 1) for x in bet_amounts[:8]]
    return bet_amounts

def calculate_stages_plan9(capital, multiple=2.5):
    calculated_amounts = {2.5: 2542.46484375, 3: 9841, 3.5: 31525.8554, 4: 87381}
    calculated_amount = calculated_amounts.get(multiple, 2542.46484375)
    bet_amounts = []
    for i in range(1, 10):
        bet_amount = round(capital / (calculated_amount / (multiple ** (i - 1))), 3)
        bet_amounts.append(bet_amount)
    return bet_amounts

def calculate_stages_plan10(capital, multiple=2.5):
    calculated_amounts = {2.5: 6357.162109375, 3: 29524, 3.5: 110341.4941, 4: 349525}
    calculated_amount = calculated_amounts.get(multiple, 6357.162109375)
    bet_amounts = []
    for i in range(1, 11):
        bet_amount = round(capital / (calculated_amount / (multiple ** (i - 1))), 3)
        bet_amounts.append(bet_amount)
    return bet_amounts

# --- Stages Calculator Panel ---
async def show_stages_calculator_panel(client, callback_query, lang: str):
    user_id = callback_query.from_user.id
    add_to_navigation(user_id, "stages_calculator_panel")
    keyboard = create_keyboard([
        [("Plan 7 stages", "stages_plan7")],
        [("Plan 8 stages", "stages_plan8")],
        [("Plan 9 stages", "stages_plan9")],
        [("Plan 10 stages", "stages_plan10")],
        [("back_btn", "capital_management_panel")]
    ], lang)
    await callback_query.message.edit_text(
        "<b>Stages Calculator</b>\n\nChoose a plan to calculate stage values based on your capital.",
        reply_markup=keyboard
    )

# --- Prompt for capital input for each plan ---
async def prompt_stages_capital_input(client, callback_query, lang: str, plan: str):
    user_id = callback_query.from_user.id
    user_states[user_id] = f"waiting_stages_{plan}"
    plan_name = plan.replace("stages_", "").replace("plan", "Plan ")
    await callback_query.message.edit_text(
        f"Enter your capital for <b>{plan_name.title()}</b> (e.g., 100):",
        reply_markup=create_keyboard([[('back_btn', 'stages_calculator_panel')]], lang)
    )

# --- Handle capital input and show results ---
async def handle_stages_capital_input(client, message: Message, lang: str, plan: str):
    user_id = message.from_user.id
    try:
        capital = float(message.text.strip())
        if plan == "stages_plan7":
            stages = calculate_stages_plan7(capital)
        elif plan == "stages_plan8":
            stages = calculate_stages_plan8(capital)
        elif plan == "stages_plan9":
            stages = calculate_stages_plan9(capital)
        elif plan == "stages_plan10":
            stages = calculate_stages_plan10(capital)
        else:
            await message.reply_text("Unknown plan.")
            return
        stages_str = '\n'.join(f"`{x}`" for x in stages)
        await message.reply_text(
            f"<b>Stage values for {plan.replace('stages_', 'Plan ').title()}:</b>\n\n{stages_str}",
            reply_markup=create_keyboard([[('back_btn', 'stages_calculator_panel')]], lang)
        )
    except Exception:
        await message.reply_text(get_text("invalid_base_amount", lang))
        return

# Import bot communication
import bot_communication

# Initialize bot communication
bot_comm = bot_communication.BotCommunication()

# ADD THIS NEW FUNCTION:
async def start_signal_receiver():
    """Start the signal receiver to monitor for signals from signal bot"""
    try:
        print("[BOT] Starting signal receiver...")
        # Start monitoring for signals in background
        asyncio.create_task(monitor_signals())
        
        # Start the cleaner thread for old signals
        try:
            from bot_communication import start_cleaner_thread
            start_cleaner_thread()
            print("[BOT] 🧹 Signal cleaner thread started successfully!")
        except Exception as e:
            print(f"[BOT] Error starting cleaner thread: {e}")
            
    except Exception as e:
        print(f"[BOT] Error in signal receiver: {e}")

async def clean_old_signals():
    """Clean old signals to ensure only real-time signals are processed"""
    try:
        print("[BOT] 🧹 CLEANER: Starting signal cleanup...")
        
        # Clear signals older than 1 hour from communication file
        bot_comm.clear_old_signals(max_age_hours=1)
        
        # Clear signals older than 2 minutes (real-time threshold)
        pending_signals = bot_comm.get_pending_signals()
        current_time = datetime.now().timestamp()
        cleaned_count = 0
        
        for signal_data in pending_signals:
            signal_timestamp = signal_data.get("timestamp", 0)
            if current_time - signal_timestamp > 120:  # 2 minutes
                bot_comm.mark_signal_processed(signal_data["timestamp"])
                cleaned_count += 1
        
        if cleaned_count > 0:
            print(f"[BOT] 🧹 CLEANER: Cleaned {cleaned_count} old signals")
        else:
            print("[BOT] 🧹 CLEANER: No old signals to clean")
            
    except Exception as e:
        print(f"[BOT] 🧹 CLEANER: Error during signal cleanup: {e}")

async def monitor_signals():
    """Monitor for signals from signal_auto_bot_pyrogram.py"""
    print("[BOT] Signal monitor started")
    last_cleanup_time = time.time()
    
    while True:
        try:
            # Get pending signals
            pending_signals = bot_comm.get_pending_signals()
            
            current_time = datetime.now().timestamp()
            
            for signal_data in pending_signals:
                try:
                    # Check if signal is too old (more than 2 minutes for real-time processing)
                    signal_timestamp = signal_data.get("timestamp", 0)
                    if current_time - signal_timestamp > 120:  # 2 minutes = 120 seconds
                        print(f"[BOT] 🧹 CLEANER: Skipping old signal from {signal_timestamp} (current: {current_time})")
                        # Mark old signal as processed to remove it
                        bot_comm.mark_signal_processed(signal_data["timestamp"])
                        continue
                    
                    # Process the signal
                    await process_background_signal(signal_data)
                    
                    # Mark as processed
                    bot_comm.mark_signal_processed(signal_data["timestamp"])
                    
                except Exception as e:
                    print(f"[BOT] Error processing signal: {e}")
            
            # Clean old signals every 30 seconds
            if current_time - last_cleanup_time > 30:
                bot_comm.clear_old_signals(max_age_hours=1)  # Clear signals older than 1 hour
                last_cleanup_time = current_time
                print(f"[BOT] 🧹 CLEANER: Performed periodic cleanup of old signals")
            
            # Debug: Show signal monitoring status
            print(f"[BOT] Signal monitoring active - checking for new signals...")
            
            # Wait before next check
            await asyncio.sleep(1)
            
        except Exception as e:
            print(f"[BOT] Error in signal monitor: {e}")
            await asyncio.sleep(5)

async def process_background_signal(signal_data):
    """Process a background signal from signal_auto_bot_pyrogram.py"""
    try:
        print("\nsignal_data", signal_data)
        group_id = signal_data["group_id"]
        game = signal_data["game"]
        signal = signal_data["signal"]
        current_stage = signal_data["current_stage"]
        issue_number = str(signal_data.get("issue_number")) if signal_data.get("issue_number") is not None else None
        
        print(f"[BOT] Processing background signal: {game} {signal}x{current_stage} for group {group_id}")
        
        # Handle special command codes first
        if game in ["cr", "cb", "cd", "stop", "statistics"]:
            # This is a command code - send the appropriate command messages
            try:
                # Get language for the group - use the same logic as get_effective_language
                lang = "en"  # default
                try:
                    # Check if group has language setting
                    group_lang = db.get_group_language(group_id)
                    if group_lang:
                        lang = group_lang
                except:
                    pass
                
                print(f"[BOT] Using language: {lang} for group {group_id}")
                
                if game == "cr":  # Red/Green command
                    # Reactivate this group if it was stopped
                    try:
                        STOPPED_GROUPS.discard(str(group_id))
                        print(f"[BOT] Reactivated group {group_id} for red_green signals")
                    except Exception:
                        pass
                    # Send the same messages as @red_green_command
                    signal_message_1 = get_text("signal_start_msg1", lang)
                    signal_message_2 = get_text("signal_start_msg2", lang)
                    signal_message_3 = get_text("signal_start_msg3", lang)
                    await app.send_message(group_id, signal_message_1)
                    await app.send_message(group_id, signal_message_2)
                    await app.send_message(group_id, signal_message_3)
                    print(f"[BOT] Sent red_green command messages to group {group_id}")
                elif game == "cb":  # Blocks command
                    # Reactivate this group if it was stopped
                    try:
                        STOPPED_GROUPS.discard(str(group_id))
                        print(f"[BOT] Reactivated group {group_id} for blocks signals")
                    except Exception:
                        pass
                    # Send the same messages as @blocks_command
                    signal_message_1 = get_text("signal_start_msg4", lang)
                    signal_message_2 = get_text("signal_start_msg2", lang)
                    signal_message_3 = get_text("signal_start_msg3", lang)
                    await app.send_message(group_id, signal_message_1)
                    await app.send_message(group_id, signal_message_2)
                    await app.send_message(group_id, signal_message_3)
                    print(f"[BOT] Sent blocks command messages to group {group_id}")
                elif game == "cd":  # Dices command
                    # Reactivate this group if it was stopped
                    try:
                        STOPPED_GROUPS.discard(str(group_id))
                        print(f"[BOT] Reactivated group {group_id} for dices signals")
                    except Exception:
                        pass
                    # Send the same messages as @dices_command
                    signal_message_1 = get_text("signal_start_msg5", lang)
                    signal_message_2 = get_text("signal_start_msg2", lang)
                    signal_message_3 = get_text("signal_start_msg3", lang)
                    await app.send_message(group_id, signal_message_1)
                    await app.send_message(group_id, signal_message_2)
                    await app.send_message(group_id, signal_message_3)
                    print(f"[BOT] Sent dices command messages to group {group_id}")
                elif game == "stop":  # Stop command - announce target reached and stop signals
                    # Use the copy bot's own win tracking for this group
                    current_wins = get_channel_win_count(group_id)
                    stop_message = f"✅ Target of {current_wins} wins reached! Stopping signals."
                    await app.send_message(group_id, stop_message)
                    # Mark this group as stopped
                    try:
                        STOPPED_GROUPS.add(str(group_id))
                    except Exception:
                        pass
                    # Reset win counter when max stages are reached
                    reset_channel_win_count(group_id)
                    print(f"[BOT] Sent stop message to group {group_id} with {current_wins} wins and reset win counter")
                elif game == "statistics":  # Statistics command - show history
                    # Use existing statistics logic
                    try:
                        channel_id_str = str(group_id)
                        history_list = channel_history.get(channel_id_str, [])
                        
                        if not history_list:
                            await app.send_message(group_id, "No statistics yet for this chat.")
                        else:
                            # Build lines newest first
                            lines = ["History:"]
                            for entry in reversed(history_list[-50:]):  # show up to last 50
                                issue = entry.get('issue', '—')
                                choice = entry.get('choice', '?')
                                phase = entry.get('phase', 1)
                                win_status = '✅ Win' if entry.get('win', False) else '❎'
                                lines.append(f"`{issue} buy {choice} order  {phase} {win_status}`")
                            
                            if len(lines) == 1:
                                text = "History:\n`—`"
                            else:
                                text = "\n".join(lines)
                            
                            await app.send_message(group_id, text, parse_mode=ParseMode.MARKDOWN)
                        print(f"[BOT] Sent statistics to group {group_id}")
                    except Exception as e:
                        print(f"[BOT] Error sending statistics to group {group_id}: {e}")
            except Exception as e:
                print(f"[BOT] Error sending command message to group {group_id}: {e}")
            
            print(f"[BOT] Successfully processed command code: {game}")
            return  # Exit early - no need to process as a signal
        
        # This is a normal signal - process it normally
        # Get the actual group name from database
        group_name = f"Group {group_id}"  # Default fallback
        try:
            # Try to get group name from database by searching through descriptions
            groups = db.get_groups()
            for group_name_key, group_data in groups.items():
                description = group_data.get('description', '')
                # Check if the description contains the group ID
                if str(group_id) in description:
                    group_name = group_name_key
                    print(f"[BOT] Found group name: {group_name} for ID: {group_id}")
                    break
        except Exception as e:
            print(f"[BOT] Error getting group name: {e}, using default")
        
        # Create a fake message object for processing
        class FakeMessage:
            def __init__(self, chat_id, chat_title):
                self.chat = type('Chat', (), {'id': chat_id, 'title': chat_title, 'type': 'group'})()
                self.from_user = None
                self.text = f"{signal}x{current_stage}"
                self.reply_text = lambda text: app.send_message(chat_id, text)
                self.issue_number = issue_number
        
        fake_message = FakeMessage(group_id, group_name)
        print(f"[BOT] Created FakeMessage with group_name: {group_name}")
        print(f"[BOT] Processing background signal: {game} {signal}x{current_stage} for group {group_name} (ID: {group_id})")
        
        # Process based on game type
        if game == "red_green":
            print(f"[BOT] Calling process_trading_signal for red_green")
            await process_trading_signal(app, fake_message, f"{signal}x{current_stage}")
        elif game == "blocks":
            print(f"[BOT] Calling process_blocks_signal for blocks")
            await process_blocks_signal(app, fake_message, f"{signal}x{current_stage}")
        elif game == "dices":
            print(f"[BOT] Calling process_dices_signal for dices")
            await process_dices_signal(app, fake_message, f"{signal}x{current_stage}")
        
        print(f"[BOT] Successfully processed background signal for {game}")
        
    except Exception as e:
        print(f"[BOT] Error in process_background_signal: {e}")


def get_comprehensive_help_text(lang: str) -> str:
    """Generate comprehensive help text based on language"""
    if lang == "vi":
        return """🤖 **HƯỚNG DẪN SỬ DỤNG BOT - HƯỚNG DẪN ĐẦY ĐỦ** 🤖

🎯 **BOT LÀ GÌ?**
Đây là bot copy trading tự động cho các trò chơi Red/Green, Blocks, và Dices. Bot sẽ tự động thực hiện giao dịch dựa trên tín hiệu nhận được.

📋 **HƯỚNG DẪN BẮT ĐẦU:**

🔐 **BƯỚC 1: ĐĂNG NHẬP**
• Gửi `/start` để bắt đầu
• Chọn ngôn ngữ (Tiếng Anh/Tiếng Việt)
• Nhấn "🔐 Đăng nhập"
• Gửi thông tin đăng nhập theo định dạng: `username&password`
• Bot sẽ xác thực với Coinvid

👥 **BƯỚC 2: CHỌN NHÓM**
• Nhấn "👥 Groups" trong menu chính
• Chọn nhóm bạn muốn tham gia
• Nhóm sẽ hiển thị tín hiệu giao dịch

🎯 **BƯỚC 3: THIẾT LẬP MỤC TIÊU**
• Nhấn "🎯 Target" để thiết lập
• Đặt Take Profit (lợi nhuận mục tiêu)
• Đặt Stop Loss (cắt lỗ)
• Định dạng: `take profit:100` và `stoploss:50`

💼 **BƯỚC 4: QUẢN LÝ VỐN**
• Nhấn "💼 Capital management"
• Chọn chiến lược: Martin, Fibo, Victory, Fima
• Hoặc tạo chiến lược tùy chỉnh
• Thiết lập số tiền cơ bản và kế hoạch

▶️ **BƯỚC 5: BẮT ĐẦU GIAO DỊCH**
• Nhấn "▶️ Start" để bắt đầu
• Bot sẽ tự động thực hiện giao dịch
• Nhấn "⏹️ Stop" để dừng

🎮 **CÁC TRÒ CHƠI HỖ TRỢ:**

🔴🟢 **RED/GREEN:**
• Đặt cược vào màu đỏ hoặc xanh
• Tín hiệu: Rx1, Gx1 (x = số giai đoạn)
• Kết quả: Đỏ/Xanh

🔷🔶 **BLOCKS:**
• Đặt cược vào Big hoặc Small
• Tín hiệu: Bx1, Sx1
• Kết quả: Big/Small

🔢 **DICES:**
• Đặt cược vào Odd hoặc Even
• Tín hiệu: Ox1, Ex1
• Kết quả: Lẻ/Chẵn

📊 **THEO DÕI KẾT QUẢ:**
• Bot tự động kiểm tra kết quả
• Gửi thông báo thắng/thua
• Cập nhật số dư tự động
• Gửi kết quả đến nhóm

⚙️ **TÍNH NĂNG NÂNG CAO:**

📈 **QUẢN LÝ VỐN:**
• **Martin:** Tăng gấp đôi khi thua
• **Fibo:** Dựa trên dãy Fibonacci
• **Victory:** Tăng gấp đôi khi thắng
• **Fima:** Chiến lược kết hợp
• **Tùy chỉnh:** Tạo kế hoạch riêng

📋 **LỆNH HỮU ÍCH:**
• `/start` - Bắt đầu bot
• `/home` - Về trang chủ
• `/help` - Hiển thị hướng dẫn này
• `/activate` - Kiểm tra bot hoạt động
• `/red_green` - Bắt đầu Red/Green
• `/blocks` - Bắt đầu Blocks
• `/dices` - Bắt đầu Dices

🔧 **KHẮC PHỤC SỰ CỐ:**

❌ **Lỗi đăng nhập:**
• Kiểm tra username&password
• Liên hệ admin nếu cần

❌ **Không nhận tín hiệu:**
• Kiểm tra đã chọn nhóm chưa
• Đảm bảo bot đã Start

❌ **Giao dịch thất bại:**
• Kiểm tra số dư
• Kiểm tra thiết lập vốn

📞 **HỖ TRỢ:**
• Liên hệ admin: @admin
• Kiểm tra thông tin: Nhấn "ℹ️ Information"
• Xem lịch sử: Nhấn "📜 History"

⚠️ **LƯU Ý QUAN TRỌNG:**
• Chỉ giao dịch với số tiền bạn có thể mất
• Luôn thiết lập Stop Loss
• Theo dõi kết quả thường xuyên
• Không chia sẻ thông tin đăng nhập

🚀 **BẮT ĐẦU NGAY:**
Nhấn "🔐 Login" để bắt đầu hành trình giao dịch tự động!"""
    else:
        return """🤖 **COMPREHENSIVE BOT USER GUIDE** 🤖

🎯 **WHAT IS THIS BOT?**
This is an automated copy trading bot for Red/Green, Blocks, and Dices games. The bot automatically executes trades based on received signals.

📋 **GETTING STARTED GUIDE:**

🔐 **STEP 1: LOGIN**
• Send `/start` to begin
• Choose language (English/Vietnamese)
• Press "🔐 Login"
• Send login info in format: `username&password`
• Bot will authenticate with Coinvid

👥 **STEP 2: SELECT GROUP**
• Press "👥 Groups" in main menu
• Choose the group you want to join
• Group will display trading signals

🎯 **STEP 3: SET TARGETS**
• Press "🎯 Target" to configure
• Set Take Profit (target profit)
• Set Stop Loss (loss limit)
• Format: `take profit:100` and `stoploss:50`

💼 **STEP 4: CAPITAL MANAGEMENT**
• Press "💼 Capital management"
• Choose strategy: Martin, Fibo, Victory, Fima
• Or create custom strategy
• Set base amount and plan

▶️ **STEP 5: START TRADING**
• Press "▶️ Start" to begin
• Bot will automatically execute trades
• Press "⏹️ Stop" to halt

🎮 **SUPPORTED GAMES:**

🔴🟢 **RED/GREEN:**
• Bet on red or green color
• Signals: Rx1, Gx1 (x = stage number)
• Results: Red/Green

🔷🔶 **BLOCKS:**
• Bet on Big or Small
• Signals: Bx1, Sx1
• Results: Big/Small

🔢 **DICES:**
• Bet on Odd or Even
• Signals: Ox1, Ex1
• Results: Odd/Even

📊 **RESULT TRACKING:**
• Bot automatically checks results
• Sends win/loss notifications
• Updates balance automatically
• Broadcasts results to group

⚙️ **ADVANCED FEATURES:**

📈 **CAPITAL MANAGEMENT:**
• **Martin:** Double bet when losing
• **Fibo:** Based on Fibonacci sequence
• **Victory:** Double bet when winning
• **Fima:** Combined strategy
• **Custom:** Create your own plan

📋 **USEFUL COMMANDS:**
• `/start` - Start the bot
• `/home` - Go to home page
• `/help` - Show this guide
• `/activate` - Check bot status
• `/red_green` - Start Red/Green
• `/blocks` - Start Blocks
• `/dices` - Start Dices

🔧 **TROUBLESHOOTING:**

❌ **Login errors:**
• Check username&password format
• Contact admin if needed

❌ **No signals received:**
• Check if group is selected
• Ensure bot is Started

❌ **Trade failures:**
• Check balance
• Verify capital settings

📞 **SUPPORT:**
• Contact admin: @admin
• Check info: Press "ℹ️ Information"
• View history: Press "📜 History"

⚠️ **IMPORTANT NOTES:**
• Only trade with money you can afford to lose
• Always set Stop Loss
• Monitor results regularly
• Never share login credentials

🚀 **START NOW:**
Press "🔐 Login" to begin your automated trading journey!"""

def create_help_keyboard(lang: str) -> InlineKeyboardMarkup:
    """Create help navigation keyboard"""
    if lang == "vi":
        buttons = [
            [InlineKeyboardButton("🔐 Đăng nhập", callback_data="login")],
            [InlineKeyboardButton("👥 Groups", callback_data="groups")],
            [InlineKeyboardButton("🎯 Target", callback_data="target_panel")],
            [InlineKeyboardButton("💼 Capital Management", callback_data="capital_management_panel")],
            [InlineKeyboardButton("ℹ️ Information", callback_data="info_panel")],
            [InlineKeyboardButton("📜 History", callback_data="user_history")],
            [InlineKeyboardButton("🌐 Language", callback_data="language")],
            [InlineKeyboardButton("⬅️ Back", callback_data="back")]
        ]
    else:
        buttons = [
            [InlineKeyboardButton("🔐 Login", callback_data="login")],
            [InlineKeyboardButton("👥 Groups", callback_data="groups")],
            [InlineKeyboardButton("🎯 Target", callback_data="target_panel")],
            [InlineKeyboardButton("💼 Capital Management", callback_data="capital_management_panel")],
            [InlineKeyboardButton("ℹ️ Information", callback_data="info_panel")],
            [InlineKeyboardButton("📜 History", callback_data="user_history")],
            [InlineKeyboardButton("🌐 Language", callback_data="language")],
            [InlineKeyboardButton("⬅️ Back", callback_data="back")]
        ]
    
    return InlineKeyboardMarkup(buttons)

async def show_help_panel(client, callback_query, lang: str):
    """Show help panel with comprehensive guide"""
    help_text = get_comprehensive_help_text(lang)
    keyboard = create_help_keyboard(lang)
    
    await callback_query.message.edit_text(help_text, reply_markup=keyboard)

if __name__ == "__main__":
    print("Starting Telegram Bot...")
    
    
    # Start your bot
    app.run() 