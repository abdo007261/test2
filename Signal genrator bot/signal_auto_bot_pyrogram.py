import asyncio
import json
import logging
import sys
from os import getenv
from pyrogram.client import Client
from pyrogram import filters
from pyrogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
)
from pyrogram.enums import ChatType, ParseMode
import bot_communication
import pyrogram.errors
import sqlite3
import requests
from datetime import datetime
import threading
import time
import random
from pyrogram.types import BotCommand, BotCommandScope, BotCommandScopeAllPrivateChats, MenuButtonDefault
import re
from bot_communication import bot_comm, get_signal_command

# Global variables and constants
signal_tasks = {}  # Track running signal generation tasks
ALL_GAMES = ["red_green", "blocks", "dices"]  # Supported games
SESSION_START_TS = {}  # Track session start times
GROUP_SESSION_STATS = {}  # Track session statistics per group
# New: Track groups that are in starting phase (after start button, before 5-min delay)
groups_in_starting_phase = {}
last_timer_triggers = {}  # Track when each timer was last triggered to prevent duplicates

# Default game settings template
DEFAULT_GAME_SETTINGS = {
    "strategy": "random",
    "formula": "",
    "stages": 1,
    "win_count": 10,
    "timer_formula": "24/7",
    "timer_random": "24/7"
}

COMMANDS = [
    BotCommand(command="start", description="Start the bot"),
    BotCommand(command="back", description="Return to main menu"),
]
# --- CONFIG ---
api_id = 27112006  # Replace with your own if needed
api_hash = "0d1019d7ca92aef12571c82cd163d2bd"
bot_token = "7920551517:AAFDAB_nMso_h7y-RC-_5IzCOk2BTcLX2l4"
# Default admin IDs - these will be loaded from config file if available
DEFAULT_ADMIN_IDS = [1602528125, 6378849563, 7581385517, 7920551517]
CONFIG_FILE = "data2.json"

# Function to get admin IDs from config
def get_admin_ids():
    """Get admin IDs from config file, fallback to default if not found"""
    try:
        cfg = load_config()
        return cfg.get("admin_ids", DEFAULT_ADMIN_IDS)
    except Exception:
        return DEFAULT_ADMIN_IDS

# Function to save admin IDs to config
def save_admin_ids(admin_ids):
    """Save admin IDs to config file"""
    try:
        cfg = load_config()
        cfg["admin_ids"] = admin_ids
        save_config(cfg)
        return True
    except Exception as e:
        print(f"Error saving admin IDs: {e}")
        return False
DB_FILE = "signals_data.db"

DICES_URL = "https://m.coinvidg.com/api/rocket-api/game/issue-result/page"
DICES_PARAMS = {"subServiceCode": "DS1M", "size": "15", "current": "1"}
DICES_HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Encoding": "gzip, deflate, br, zstd",
    "Accept-Language": "en-US",
    "Authorization": "Basic cm9ja2V0X3dlYjpyb2NrZXRfd2Vi",
    "User_type": "admin"
}

BLOCKS_URL = "https://m.coinvidg.com/api/rocket-api/game/issue-result/page"
BLOCKS_PARAMS = {"subServiceCode": "BLK1M", "size": "15", "current": "1"}
BLOCKS_HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Encoding": "gzip, deflate, br, zstd",
    "Accept-Language": "en-US",
    "Authorization": "Basic cm9ja2V0X3dlYjpyb2NrZXRfd2Vi",
    "Blade-Auth": "",
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
    "User_type": "rocket"
}

RED_GREEN_URL = "https://m.coinvidg.com/api/rocket-api/game/issue-result/page"
RED_GREEN_PARAMS = {"subServiceCode": "RG1M", "size": "15", "current": "1"}
RED_GREEN_HEADERS = {
    "accept": "application/json, text/plain, */*",
    "authorization": "Basic cm9ja2V0X3dlYjpyb2NrZXRfd2Vi",
    "user-agent": "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36...",
    "referer": "https://m.coinvidg.com/game/guessMain?gameName=RG1M&returnUrl=%2FgameList",
    "host": "m.coinvidg.com",
    "connection": "keep-alive",
    "cookie": "JSESSIONID=0AkjLljW2FNgeVLmOPWYudZwXcbZbjx9yxUrwMWE"
}

# --- BOT SETUP ---
app = Client("signal_bot2", bot_token=bot_token, api_id=api_id, api_hash=api_hash)

# Initialize bot communication
bot_comm = bot_communication.BotCommunication()

# --- STATE ---
user_state = {}  # user_id: {"awaiting": ..., "game": ..., "nav_stack": [...], ...}

# Global FakeCB class for simulating callback queries
class FakeCB:
    def __init__(self, from_user, data, message):
        self.from_user = from_user
        self.data = data
        self.message = message

def _ensure_session_stats_entry(group_id: str):
    if group_id not in GROUP_SESSION_STATS:
        GROUP_SESSION_STATS[group_id] = {
            "session_started_at": SESSION_START_TS.get(group_id, int(time.time())),
            "red_green": {"signals": 0, "wins": 0, "losses": 0},
            "blocks": {"signals": 0, "wins": 0, "losses": 0},
            "dices": {"signals": 0, "wins": 0, "losses": 0},
        }

# --- NAVIGATION STACK HELPERS ---
def push_nav(user_id, step):
    if user_id not in user_state:
        user_state[user_id] = {}
    stack = user_state[user_id].setdefault("nav_stack", [])
    stack.append(step)

def pop_nav(user_id):
    stack = user_state.get(user_id, {}).get("nav_stack", [])
    if stack:
        stack.pop()
    return stack[-1] if stack else None

def get_prev_nav(user_id):
    stack = user_state.get(user_id, {}).get("nav_stack", [])
    return stack[-2] if len(stack) > 1 else None

# --- CONFIG LOAD/SAVE (PER-GROUP, PER-GAME) ---
DEFAULT_GAME_SETTINGS = {
    "strategy": "random",
    "formula": "",
    "stages": 7,
    "win_count": 10,
    "timer": "24/7",  # legacy, for backward compatibility
    "timer_formula": "24/7",
    "timer_random": "24/7",
    "lan": "en"  # Default language is English
}

# Vietnamese translations for all signal messages
VIETNAMESE_TRANSLATIONS = {
    # Red-Green game messages
    "red_green_start": "Bắt đầu chiến lược ĐỎ-XANH 1 PHÚT.\nVui lòng chờ một chút.",
    "red_green_instructions": """👉 Sử dụng các ký tự sau:\n▫️ B: Lớn\n▫️ S: Nhỏ\n▫️ G: Xanh\n▫️ R: Đỏ\n▫️ P: Tím\n▫️ O: Lẻ\n▫️ E: Chẵn\n▫️ 0–9: Chỉ mức cược hoặc số tiền\n\n✒️ Ví dụ:\n\nBx1 (Cược Lớn, mức cược 1)\nGx3 (Cược Xanh, mức cược 3)""",
    "red_green_ready": "Sẵn sàng nhận lệnh...",
    
    # Blocks game messages
    "blocks_start": "Bắt đầu chiến lược Đoán khối 1 PHÚT.\nVui lòng chờ một chút.",
    "blocks_instructions": """👉 Sử dụng các ký tự sau:\n▫️ B: Lớn\n▫️ S: Nhỏ\n▫️ G: Xanh\n▫️ R: Đỏ\n▫️ P: Tím\n▫️ O: Lẻ\n▫️ E: Chẵn\n▫️ 0–9: Chỉ mức cược hoặc số tiền\n\n✒️ Ví dụ:\n\nBx1 (Cược Lớn, mức cược 1)\nGx3 (Cược Xanh, mức cược 3)""",
    "blocks_ready": "Sẵn sàng nhận lệnh...",
    
    # Dices game messages
    "dices_start": "Bắt đầu chiến lược Xóc Đĩa 1 PHÚT.\nVui lòng chờ một chút.",
    "dices_instructions": """👉 Sử dụng các ký tự sau:\n▫️ B: Lớn\n▫️ S: Nhỏ\n▫️ G: Xanh\n▫️ R: Đỏ\n▫️ P: Tím\n▫️ O: Lẻ\n▫️ E: Chẵn\n▫️ 0–9: Chỉ mức cược hoặc số tiền\n\n✒️ Ví dụ:\n\nBx1 (Cược Lớn, mức cược 1)\nGx3 (Cược Xanh, mức cược 3)""",
    "dices_ready": "Sẵn sàng nhận lệnh...",
    
    # Result messages
    "result_win": "Chiến thắng!",
    "result_lose": "Thua cuộc",
    "result_red": "ĐỎ   🔴",
    "result_green": "XANH   🟢",
    "result_big": "LỚN   🔷",
    "result_small": "NHỎ   🔶",
    "result_odd": "LẺ   🔢",
    "result_even": "CHẴN   🔢",
    
    # Signal messages
    "signal_red": "Đỏ",
    "signal_green": "Xanh",
    "signal_big": "Lớn",
    "signal_small": "Nhỏ",
    "signal_odd": "Lẻ",
    "signal_even": "Chẵn",
    
    # Status messages
    "already_running": "❌ Máy phát tín hiệu đang chạy cho nhóm này!",
    "no_formula": "❌ Chưa cấu hình công thức cho nhóm này. Vui lòng đặt công thức trước.",
    "stopping": "Đang dừng...",
    "stopped": "✅ Máy phát tín hiệu đã dừng!",
    "no_generator": "❌ Không có máy phát tín hiệu nào đang chạy cho nhóm này!",
    "target_reached": "✅ Đã đạt mục tiêu {win_count} lần thắng! Dừng tín hiệu.",
    "max_stages": "Đã đạt số giai đoạn tối đa ({max_stages})! Đang đặt lại...",
    
    # Language messages
    "language_set_vietnamese": "Ngôn ngữ đã được đặt thành Tiếng Việt 🇻🇳.",
    "language_set_english": "Ngôn ngữ đã được đặt thành Tiếng Anh 🇬🇧.",
    "chat_not_in_list": "ID chat này không có trong danh sách. Vui lòng thêm trước.",
    
    # Additional translations for result messages
    "result": "Kết quả",
    "buy": "Cược",
    # Bot activation messages
    "bot_activated_success": "✅ **Bot đã được kích hoạt thành công!** ✅\n\n🎉 **Trạng thái:** Bot đang hoạt động bình thường\n📋 **Loại chat:** {chat_type}\n\n📛 **Tên chat:** {chat_name}",
    "bot_activation_failed": "❌ **Kích hoạt thất bại!** ❌\n\n⚠️ **Lỗi:** {error}\n\n🔧 **Vui lòng đảm bảo:**\n• Bot đã được thêm vào nhóm/kênh\n• Bot có quyền quản trị viên\n• Bot có thể gửi tin nhắn\n\n📞 **Liên hệ hỗ trợ nếu vấn đề vẫn tiếp tục.**",
    # Background signal processing
    "signal_acknowledgment": "🎯 **TÍN HIỆU ĐÃ NHẬN**\n\n📥 **Tín hiệu:** {signal}\n📋 **Nhóm:** {group_name}\n⏰ **Thời gian:** {timestamp}",
    "background_signal_processed": "✅ **Tín hiệu nền đã được xử lý thành công!**",
    "command_code_sent": "✅ **Mã lệnh đã được gửi:** {command_code}",
    "signal_monitoring_active": "🔄 **Giám sát tín hiệu đang hoạt động**",
    "old_signal_skipped": "⏭️ **Tín hiệu cũ đã bỏ qua** (quá 5 phút)",
    "signal_cleaner_active": "🧹 **Dọn dẹp tín hiệu cũ đang hoạt động**",
    # Admin/Settings panel
    "admin_management": "Quản lý Quản trị viên",
    "current_admins": "Quản trị viên hiện tại:",
    "total_admins": "Tổng số quản trị viên:",
    "add_admin": "➕ Thêm Quản trị viên",
    "remove_admin": "➖ Xóa Quản trị viên",
    "back": "🔙 Quay lại",
    "add_admin_prompt": "<b>➕ Thêm Quản trị viên</b>\n\nBạn có thể thêm quản trị viên bằng 2 cách:\n\n1️⃣ <b>Gửi trực tiếp ID người dùng:</b>\n   Chỉ cần nhập số ID\n\n2️⃣ <b>Chuyển tiếp tin nhắn từ người đó:</b>\n   Chuyển tiếp bất kỳ tin nhắn nào từ người muốn thêm\n\n<i>Bạn có thể lấy ID bằng cách chuyển tiếp tin nhắn đến @userinfobot</i>",
    "remove_admin_prompt": "<b>➖ Xóa Quản trị viên</b>\n\nChọn quản trị viên muốn xóa:",
    "admin_added": "✅ Đã thêm quản trị viên <code>{admin_id}</code> ({admin_name}) thành công!",
    "admin_exists": "❌ Người này đã là quản trị viên!",
    "admin_invalid": "❌ ID không hợp lệ. Vui lòng nhập số hợp lệ.",
    "admin_removed": "✅ Đã xóa quản trị viên <code>{admin_id}</code> ({admin_name}) thành công!",
    "admin_not_found": "❌ Không tìm thấy quản trị viên!",
    "cannot_remove_self": "❌ Bạn không thể tự xóa mình!",
    "not_authorized": "🚫 Bạn không có quyền sử dụng chức năng này.",
    "group_list": "<b>👥 Danh sách nhóm</b>\n\nQuản lý các nhóm tín hiệu:",
    "add_group": "➕ Thêm Nhóm",
    "select_group": "<b>👥 Nhóm</b>\n\nChọn nhóm để quản lý:",
    "removed_group": "✅ <b>Đã xóa nhóm:</b> <code>{group_id}</code>",
    "group_not_found": "❌ <b>Không tìm thấy nhóm trong danh sách.</b>",
    "settings": "<b>⚙️ Cài đặt</b>\n\nQuản lý cài đặt bot:",
    "help": "<b>❓ Trợ giúp</b>\n\nHướng dẫn sử dụng bot:",
    "start": "Bắt đầu",
    "stop": "Dừng",
    "status": "Trạng thái",
    "details": "Chi tiết",
    "edit_strategy": "Chỉnh sửa chiến lược",
    "change_strategy": "Thay đổi chiến lược: {strategy}",
    "stages": "Số giai đoạn",
    "win_count": "Số lần thắng",
    "timer": "Hẹn giờ",
    "assigned_formula": "Công thức đã gán",
    "selected_strategy": "Chiến lược đã chọn",
    "language": "Ngôn ngữ",
    "delete_group": "Xóa nhóm",
    "game_settings": "Cài đặt trò chơi cho nhóm:",
    "game_details": "Chi tiết trò chơi",
    "game": "Trò chơi",
    "on": "BẬT",
    "off": "TẮT"
}

ALL_GAMES = ["red_green", "blocks", "dices"]

# --- SIMPLE HISTORY STORAGE (in-memory for this runtime) ---
# Keep a rolling list of sent signal summaries per group for lightweight /history
SENT_HISTORY = {}  # group_id(str) -> list of (ts:int, text:str)

def _append_history(group_id: str, text: str):
    arr = SENT_HISTORY.setdefault(group_id, [])
    arr.append((int(time.time()), text))
    # Keep last 500 entries to avoid memory bloat
    if len(arr) > 500:
        del arr[: len(arr) - 500]


# --- NEW COMMANDS: /check and /history ---
@app.on_message(filters.command("check"))
async def check_command(client, message: Message):
    """Show session statistics for this group."""
    gid = str(message.chat.id)
    _ensure_session_stats_entry(gid)
    stats = GROUP_SESSION_STATS.get(gid, {})
    started_at = stats.get("session_started_at")
    started_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(started_at)) if started_at else "N/A"
    rg = stats.get("red_green", {})
    bl = stats.get("blocks", {})
    dc = stats.get("dices", {})
    def line(name, d):
        return f"{name}: signals={d.get('signals',0)}, wins={d.get('wins',0)}, losses={d.get('losses',0)}"
    text = (
        f"<b>📊 Session Statistics</b>\n"
        f"<b>Group:</b> <code>{gid}</code>\n"
        f"<b>Session start:</b> {started_str}\n\n"
        f"{line('🔴🟢 Red/Green', rg)}\n"
        f"{line('🟦 Blocks', bl)}\n"
        f"{line('🎲 Dices', dc)}\n"
    )
    await message.reply_text(text)


@app.on_message(filters.command("history"))
async def history_command(client, message: Message):
    """Show the bot's history in this chat for the last 24 hours (in-memory)."""
    gid = str(message.chat.id)
    now_ts = int(time.time())
    one_day_ago = now_ts - 24*60*60
    entries = [e for e in SENT_HISTORY.get(gid, []) if e[0] >= one_day_ago]
    if not entries:
        await message.reply_text("No history in the last 24 hours.")
        return
    # Format compact list
    lines = []
    for ts, text in entries[-200:]:  # cap to last 200 lines
        tstr = time.strftime("%H:%M:%S", time.localtime(ts))
        lines.append(f"[{tstr}] {text}")
    out = "<b>🗂️ History (last 24h)</b>\n" + "\n".join(lines)
    # Telegram message length limit; truncate if too long
    if len(out) > 3800:
        out = out[:3800] + "\n... (truncated)"
    await message.reply_text(out)

@app.on_message(filters.command("tasks"))
async def tasks_command(client, message: Message):
    """Show detailed information about all signal tasks"""
    user_id = message.from_user.id
    if user_id not in get_admin_ids():
        await message.reply("🚫 You are not authorized to use this bot.")
        return
    
    if not signal_tasks:
        await message.reply("📭 No signal tasks found.")
        return
    
    tasks_text = f"📋 <b>Signal Tasks ({len(signal_tasks)})</b>\n\n"
    
    for key, task_info in signal_tasks.items():
        tasks_text += f"🔑 <b>Task Key:</b> <code>{key}</code>\n"
        
        if "thread" in task_info:
            thread = task_info["thread"]
            if thread.is_alive():
                tasks_text += f"🟢 <b>Status:</b> Running\n"
            else:
                tasks_text += f"🔴 <b>Status:</b> Stopped\n"
        else:
            tasks_text += f"⚠️ <b>Status:</b> No thread info\n"
        
        if "stop_event" in task_info:
            tasks_text += f"🛑 <b>Stop Event:</b> Set\n"
        else:
            tasks_text += f"⚠️ <b>Stop Event:</b> Missing\n"
        
        tasks_text += "─" * 30 + "\n"
    
    await message.reply(tasks_text, parse_mode=ParseMode.HTML)

def load_config():
    try:
        with open(CONFIG_FILE, "r") as f:
            raw = json.load(f)
    except Exception:
        raw = None

    # If file missing or contained null, start with baseline
    if not isinstance(raw, dict):
        cfg = {"groups": [], "group_settings": {}, "admin_ids": DEFAULT_ADMIN_IDS}
    else:
        cfg = raw

    # Normalize required top-level keys
    if "groups" not in cfg or not isinstance(cfg["groups"], list):
        cfg["groups"] = []
    if "group_settings" not in cfg or not isinstance(cfg["group_settings"], dict):
        cfg["group_settings"] = {}
    if "admin_ids" not in cfg or not isinstance(cfg["admin_ids"], list):
        cfg["admin_ids"] = DEFAULT_ADMIN_IDS

    # Migrate/ensure per-group, per-game structure
    for gid in cfg.get("groups", []):
        gset = cfg["group_settings"].get(gid, {})
        if not isinstance(gset, dict):
            gset = {}
        # If not per-game, migrate
        if not any(game in gset for game in ALL_GAMES):
            for game in ALL_GAMES:
                gset[game] = {
                    "strategy": gset.get("strategy", "random"),
                    "formula": gset.get("formula", ""),
                    "stages": gset.get("stages", 7),
                    "win_count": gset.get("win_count", 10),
                    "timer": gset.get("timer", "24/7"),
                    "timer_formula": gset.get("timer", "24/7"),
                    "timer_random": gset.get("timer", "24/7"),
                }
            for k in ["strategy", "formula", "stages", "win_count", "timer", "game"]:
                gset.pop(k, None)
        # Ensure all games present and timers migrated
        for game in ALL_GAMES:
            if game not in gset or not isinstance(gset[game], dict):
                gset[game] = DEFAULT_GAME_SETTINGS.copy()
            if "timer_formula" not in gset[game]:
                gset[game]["timer_formula"] = gset[game].get("timer", "24/7")
            if "timer_random" not in gset[game]:
                gset[game]["timer_random"] = gset[game].get("timer", "24/7")
        if "status" not in gset:
            gset["status"] = "OFF"
        cfg["group_settings"][gid] = gset

    return cfg

def save_config(cfg):
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=2)

# --- UTILS ---
def get_game_name(game):
    if game.startswith("red_green"): return "🟢🔴 RED-GREEN"
    if game.startswith("blocks"): return "🟫 BLOCKS"
    if game.startswith("dices"): return "🎲 DICES"
    return game

async def send_game_panel(client, chat_id, group_id, game):
    """Send a new game panel message"""
    cfg = load_config()
    group_cfg = cfg["group_settings"].get(group_id, {})
    game_cfg = group_cfg.get(game, {})
    game_name = get_game_name(game)
    strategy = game_cfg.get('strategy', 'random')
    strategy_label = "Formula" if strategy == "self" else "Random"
    toggle_label = f"🔁 Change Strategy: {strategy_label}"
    timer_value = game_cfg.get('timer_formula', '24/7') if strategy == 'self' else game_cfg.get('timer_random', '24/7')
    text = (
        f"<b>{game_name} Settings for Group:</b> <code>{group_id}</code>\n\n"
        f"<b>💠 Selected Strategy:</b> <code>{strategy}</code>\n"
    )
    if strategy == "self":
        text += f"<b>🔢 Assigned Formula:</b> <code>{game_cfg.get('formula','')}</code>\n"
    text += (
        f"<b>🎯 Stages:</b> <code>{game_cfg.get('stages',7)}</code>\n"
        f"<b>🏆 Win Count:</b> <code>{game_cfg.get('win_count',10)}</code>\n"
        f"<b>⏰ Timer:</b> <code>{timer_value}</code>\n"
    )
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎲 Edit Strategy", callback_data=f"setstrategy_{group_id}_{game}")],
        [InlineKeyboardButton(toggle_label, callback_data=f"toggle_strategy_{group_id}_{game}")],
        [InlineKeyboardButton("🎯 Stages", callback_data=f"setstages_{group_id}_{game}"), InlineKeyboardButton("🏆 Win Count", callback_data=f"setwincount_{group_id}_{game}")],
        [InlineKeyboardButton("⏰ Timer", callback_data=f"settimer_{group_id}_{game}"), InlineKeyboardButton("📊 Status", callback_data=f"status_{group_id}_{game}")],
        [InlineKeyboardButton("🔎 Details", callback_data=f"details_{group_id}_{game}")],
        [InlineKeyboardButton("▶️ Start", callback_data=f"start_{group_id}_{game}"), InlineKeyboardButton("⏹ Stop", callback_data=f"stop_{group_id}_{game}")],
        [InlineKeyboardButton("🔙 Back", callback_data=f"group_{group_id}")],
    ])
    await client.send_message(chat_id, text, reply_markup=kb)

# --- SMART BACK HANDLER ---
async def smart_back(client, cb: CallbackQuery):
    user_id = cb.from_user.id
    prev = get_prev_nav(user_id)
    pop_nav(user_id)
    if prev == "list_group":
        await group_list_cb(client, cb)
    elif prev == "groups":
        await groups_cb(client, cb)
    elif prev == "signal_panel":
        await signal_panel_cb(client, cb)
    elif prev in ["red_green", "blocks", "discs"]:
        await game_strategy_cb(client, cb)
    elif prev == "settings":
        await settings_cb(client, cb)
    elif prev == "help":
        await help_cb(client, cb)
    elif prev == "admins":
        await admins_cb(client, cb)
    elif prev == "add_admin":
        await add_admin_cb(client, cb)
    elif prev == "remove_admin":
        await remove_admin_cb(client, cb)
    else:
        await start_panel(client, cb.message)
async def setup_commands():
    try:
        # Set commands for private chats
        await app.set_bot_commands(commands=COMMANDS,
                                   scope=BotCommandScopeAllPrivateChats())

        # Set the menu button using the correct method
        await app.set_chat_menu_button(menu_button=MenuButtonDefault())

        print("Bot commands and menu button set up successfully!")
    except Exception as e:
        print(f"Error setting up commands: {e}")
global first_time
first_time = True
# --- START / CONTROL PANEL ---
@app.on_message(filters.command("start") & filters.private)
async def start_panel(client, msg: Message):
    global first_time
    if first_time:
        await setup_commands()
        first_time = False
    user_id = msg.from_user.id
    print(user_id)
    push_nav(user_id, "main")
    
    if user_id not in get_admin_ids():
        await msg.reply("🚫 <b>You are not authorized to use this bot.</b>")
        return
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("👥 Group List", callback_data="groups")],
        [InlineKeyboardButton("⚙️ Settings", callback_data="settings"), InlineKeyboardButton("❓ Help", callback_data="help" )],
    ])
    try:
        await msg.reply(
            "<b>🤖 Premium Signal Generator Bot</b>\n\n"
            "Welcome, Admin! Please choose an option below:",
            reply_markup=kb
        )
    except pyrogram.errors.exceptions.bad_request_400.MessageNotModified:
        pass

# --- GROUP LIST ---
@app.on_callback_query(filters.regex("^list_group$"))
async def group_list_cb(client, cb: CallbackQuery):
    user_id = cb.from_user.id
    push_nav(user_id, "list_group")
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("📋 Groups", callback_data="groups")],
        [InlineKeyboardButton("🔙 Back", callback_data="3back")],
    ])
    try:
        await cb.message.edit_text(
            "<b>👥 Group List</b>\n\nManage your signal groups below:",
            reply_markup=kb
        )
    except pyrogram.errors.exceptions.bad_request_400.MessageNotModified:
        pass

@app.on_callback_query(filters.regex("^groups$"))
async def groups_cb(client, cb: CallbackQuery):
    """Handle groups button click"""
    user_id = cb.from_user.id
    if user_id not in get_admin_ids():
        await cb.answer("🚫 You are not authorized to use this bot.", show_alert=True)
        return
    
    push_nav(user_id, "groups")
    cfg = load_config()
    config_changed = False
    
    kb = []
    for gid_str, settings in cfg["group_settings"].items():
        # Check active tasks first
        has_active_task = False
        for key, task_info in signal_tasks.items():
            if isinstance(task_info, dict) and "thread" in task_info and task_info["thread"].is_alive():
                if key == gid_str or (isinstance(key, str) and key.startswith(f"{gid_str}_")):
                    has_active_task = True
                    break
        
        # Also check if group is in starting phase
        is_in_starting_phase = gid_str in groups_in_starting_phase
        
        # Determine final status: show ON if there are actual active tasks OR if in starting phase
        final_status = "ON" if (has_active_task or is_in_starting_phase) else "OFF"
        
        # Update config if it doesn't match reality
        if settings.get("status", "OFF") != final_status:
            settings["status"] = final_status
            config_changed = True
        
        status = "🟢" if final_status == "ON" else "🔴"
        
        # Get group title, fetching and saving if necessary
        group_title = settings.get("title")
        if not group_title or group_title == "None":
            try:
                chat = await client.get_chat(int(gid_str))
                group_title = chat.title
                if group_title:
                    settings["title"] = group_title
                    config_changed = True
                else:
                    group_title = f"Group {gid_str}"
            except Exception as e:
                print(f"Could not get title for group {gid_str}: {e}")
                group_title = f"Group {gid_str}"
        
        # Create button for this group
        button = InlineKeyboardButton(f"{status} {group_title}", callback_data=f"group_{gid_str}")
        
        # Add to keyboard in pairs (2 groups per row)
        if len(kb) == 0 or len(kb[-1]) >= 2:
            # Start new row
            kb.append([button])
        else:
            # Add to existing row
            kb[-1].append(button)
    
    if config_changed:
        save_config(cfg)

    kb.append([InlineKeyboardButton("➕ Add Group", callback_data="add_group_prompt")])
    kb.append([InlineKeyboardButton("🔙 Back", callback_data="back")])
    
    try:
        await cb.message.edit_text(
            "<b>👥 Groups</b>\n\nSelect a group to manage:",
            reply_markup=InlineKeyboardMarkup(kb)
        )
    except pyrogram.errors.exceptions.bad_request_400.MessageNotModified:
        pass

@app.on_callback_query(filters.regex("^add_group_prompt$"))
async def add_group_prompt_cb(client, cb: CallbackQuery):
    """Handle add group button click"""
    user_id = cb.from_user.id
    push_nav(user_id, "add_group_prompt")
    user_state[user_id] = {"awaiting": "add_group_id"}
    
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Back", callback_data="groups")],
    ])
    
    try:
        await cb.message.edit_text(
            "<b>➕ Add Group</b>\n\n"
            "Send the ID of the group or channel you want to add.",
            reply_markup=kb
        )
    except pyrogram.errors.exceptions.bad_request_400.MessageNotModified:
        pass

@app.on_callback_query(filters.regex(r"^group_(.+)$"))
async def group_panel_cb(client, cb: CallbackQuery):
    user_id = cb.from_user.id
    push_nav(user_id, cb.data)
    group_id = cb.data.split("_", 1)[1]
    cfg = load_config()
    group_cfg = cfg["group_settings"].get(group_id, {})
    
    # Check if there's an active task for this group (check all possible keys)
    has_active_task = False
    for key, task in signal_tasks.items():
        # Check for tasks associated with this group_id
        if (isinstance(key, str) and key.startswith(f"{group_id}_")) or key == group_id:
            if "thread" in task and task["thread"].is_alive():
                has_active_task = True
                break
    
    # Also check if group is in starting phase
    is_in_starting_phase = group_id in groups_in_starting_phase
    
    # Determine final status: show ON if there are actual active tasks OR if in starting phase
    final_status = "ON" if (has_active_task or is_in_starting_phase) else "OFF"
    status_display = "🟢 ON" if final_status == "ON" else "🔴 OFF"
    
    emoji = "🟢" if final_status == "ON" else "🔴"
    
    # Get current language for the group
    current_language = "en"  # default
    for game in ALL_GAMES:
        if game in group_cfg:
            game_lan = group_cfg[game].get("lan", "en")
            if game_lan == "vit":
                current_language = "vit"
                break
    
    # Language emoji
    lang_emoji = "🇻🇳" if current_language == "vit" else "🇬🇧"
    
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🟢🔴 Red-Green Game (1m)", callback_data=f"gamepanel_{group_id}_red_green")],
        [InlineKeyboardButton("🟫 Block Game (1m)", callback_data=f"gamepanel_{group_id}_blocks")],
        [InlineKeyboardButton("🎲 Dice Game (1m)", callback_data=f"gamepanel_{group_id}_dices")],
        [InlineKeyboardButton("🛑 Stop All Games", callback_data=f"stop_all_{group_id}")],
        [InlineKeyboardButton(f"{lang_emoji} Language: {current_language.upper()}", callback_data=f"toggle_language_{group_id}"), InlineKeyboardButton("🗑️ Delete Group", callback_data=f"delete_group_{group_id}")],
        [InlineKeyboardButton("🔙 Back", callback_data="groups")],
    ])
    try:
        await cb.message.edit_text(
            f"<b>Group:</b> <code>{group_id}</code> {emoji}\n\n"
            f"<b>📊 Status:</b> <code>{final_status}</code>\n",
            reply_markup=kb
        )
    except pyrogram.errors.exceptions.bad_request_400.MessageNotModified:
        pass

@app.on_callback_query(filters.regex(r"^toggle_language_(.+)$"))
async def toggle_language_cb(client, cb: CallbackQuery):
    """Handle language toggle button click"""
    group_id = cb.data.split("_", 2)[2]
    cfg = load_config()
    
    if group_id in cfg.get("group_settings", {}):
        # Get current language
        current_language = "en"  # default
        for game in ALL_GAMES:
            if game in cfg["group_settings"][group_id]:
                game_lan = cfg["group_settings"][group_id][game].get("lan", "en")
                if game_lan == "vit":
                    current_language = "vit"
                    break
        
        # Toggle language
        new_language = "vit" if current_language == "en" else "en"
        
        # Set new language for all games in this group
        for game in ALL_GAMES:
            if game in cfg["group_settings"][group_id]:
                cfg["group_settings"][group_id][game]["lan"] = new_language
        
        save_config(cfg)
        
        # Send confirmation message
        if new_language == "vit":
            await cb.answer("🇻🇳 Language changed to Vietnamese!", show_alert=True)
        else:
            await cb.answer("🇬🇧 Language changed to English!", show_alert=True)
        
        # Refresh the group panel by creating a proper callback
        class FakeCB:
            def __init__(self, from_user, data, message):
                self.from_user = from_user
                self.data = data
                self.message = message
        
        fake_cb = FakeCB(cb.from_user, f"group_{group_id}", cb.message)
        await group_panel_cb(client, fake_cb)
    else:
        await cb.answer("❌ Group not found!", show_alert=True)

@app.on_callback_query(filters.regex(r"^delete_group_(.+)$"))
async def delete_group_cb(client, cb: CallbackQuery):
    group_id = cb.data.split("_", 1)[1]
    cfg = load_config()
    found = False
    # Remove from groups list
    # Extract only the numeric group ID if group_id is like "group_-1002160035199"
    numeric_group_id = group_id
    if group_id.startswith("group_"):
        numeric_group_id = group_id.split("_", 1)[1]
    print(numeric_group_id)
    group_id = numeric_group_id  # Use the numeric ID for the rest of the function
    print("this is the group id", group_id)
    # Remove from group_settings dict
    if group_id in cfg.get("group_settings", {}):
        del cfg["group_settings"][group_id]
        found = True
    # Remove from groups list
    if str(group_id) in cfg.get("groups", []):
        cfg["groups"].remove(str(group_id))
        found = True
    # if group_id in cfg.get("group_settings", {}):
        # found = True

    if found:
        save_config(cfg)
        await cb.message.reply(f"✅ <b>Removed group:</b> <code>{group_id}</code>", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="groups")]]))
    else:
        await cb.message.reply(f"❌ <b>Group ID not found in group list.</b>", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="groups")]]))
    await groups_cb(client, cb)

@app.on_callback_query(filters.regex(r"^toggle_strategy_(.+)_(.+)$"))
async def toggle_strategy_cb(client, cb: CallbackQuery):
    # cb.data: 'toggle_strategy_{group_id}_{game}'
    parts = cb.data.split('_', 3)
    if len(parts) < 4:
        await cb.answer("Invalid callback data!", show_alert=True)
        return
    group_id, game = parts[2], parts[3]
    cfg = load_config()
    group_cfg = cfg["group_settings"].get(group_id, {})
    game_cfg = group_cfg.get(game, {})
    current = game_cfg.get('strategy', 'random')
    new_strategy = 'self' if current == 'random' else 'random'
    cfg["group_settings"][group_id][game]["strategy"] = new_strategy
    save_config(cfg)
    # Refresh the game panel
    fake_cb = FakeCB(cb.from_user, f"gamepanel_{group_id}_{game}", cb.message)
    await gamepanel_cb(client, fake_cb)

@app.on_callback_query(filters.regex(r"^settimer_(.+)_(.+)$"))
async def settimer_cb(client, cb: CallbackQuery):
    user_id = cb.from_user.id
    group_id, game = cb.data.split("_", 2)[1:]
    user_state[user_id] = {"awaiting": "settimer", "group_id": group_id, "game": game}
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Back", callback_data=f"gamepanel_{group_id}_{game}")],
    ])
    # Show which timer is being set
    cfg = load_config()
    group_cfg = cfg["group_settings"].get(group_id, {})
    game_cfg = group_cfg.get(game, {})
    strategy = game_cfg.get('strategy', 'random')
    timer_label = "Formula" if strategy == "self" else "Random"
    current_timer = game_cfg.get('timer_formula', '24/7') if strategy == 'self' else game_cfg.get('timer_random', '24/7')
    await cb.message.edit_text(
        f"<b>⏰ Enter timer for {timer_label} strategy in {get_game_name(game)} for Group:</b> <code>{group_id}</code>\n"
        f"<b>Current timer:</b> <code>{current_timer}</code>\n\n"
        f"<b>📝 Format Examples:</b>\n"
        f"• Single time: <code>20:00</code>\n"
        f"• Multiple times: <code>06:00-20:00-12:00</code> (use dashes)\n"
        f"• Always on: <code>24/7</code>",
        reply_markup=kb
    )


@app.on_callback_query(filters.regex(r"^gamepanel_(.+)_(.+)$"))
async def gamepanel_cb(client, cb: CallbackQuery):
    group_id, game = cb.data.split("_", 2)[1:]
    cfg = load_config()
    group_cfg = cfg["group_settings"].get(group_id, {})
    game_cfg = group_cfg.get(game, {})
    game_name = get_game_name(game)
    strategy = game_cfg.get('strategy', 'random')
    strategy_label = "Formula" if strategy == "self" else "Random"
    toggle_label = f"🔁 Change Strategy: {strategy_label}"
    timer_value = game_cfg.get('timer_formula', '24/7') if strategy == 'self' else game_cfg.get('timer_random', '24/7')
    
    # Check if there's an active task for this specific game
    has_active_task = False
    for key, task in signal_tasks.items():
        if isinstance(key, str) and key.startswith(f"{group_id}_{game}_"):
            if "thread" in task and task["thread"].is_alive():
                has_active_task = True
                break
    
    # Determine final status: ONLY show ON if there are actual active tasks
    # This fixes the issue where config says ON but no tasks are running
    is_running = has_active_task
    
    # If no active tasks but config says ON, fix the config
    config_status = group_cfg.get("status", "OFF")
    if config_status == "ON" and not has_active_task:
        # Fix the config - set status to OFF since no tasks are running
        cfg["group_settings"][group_id]["status"] = "OFF"
        save_config(cfg)
        print(f"🔧 Fixed config: Group {group_id} status set to OFF (no active tasks)")
    
    text = (
        f"<b>{game_name} Settings for Group:</b> <code>{group_id}</code>\n\n"
        f"<b>💠 Selected Strategy:</b> <code>{strategy}</code>\n"
    )
    if strategy == "self":
        text += f"<b>🔢 Assigned Formula:</b> <code>{game_cfg.get('formula','')}</code>\n"
    text += (
        f"<b>🎯 Stages:</b> <code>{game_cfg.get('stages',7)}</code>\n"
        f"<b>🏆 Win Count:</b> <code>{game_cfg.get('win_count',10)}</code>\n"
        f"<b>⏰ Timer:</b> <code>{timer_value}</code>\n"
        f"<b>🔄 Status:</b> {'🟢 ON' if is_running else '🔴 OFF'}\n"
    )
    
    # Create buttons based on status
    if is_running:
        # Group is running - show disabled start button and enabled stop button
        start_button = InlineKeyboardButton("⏸️ Already Running", callback_data="already_running")
        stop_button = InlineKeyboardButton("⏹ Stop", callback_data=f"stop_{group_id}_{game}")
    else:
        # Group is stopped - show enabled start button and disabled stop button
        start_button = InlineKeyboardButton("▶️ Start", callback_data=f"start_{group_id}_{game}")
        stop_button = InlineKeyboardButton("⏹ Stop", callback_data=f"stop_{group_id}_{game}")
    
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎲 Edit Strategy", callback_data=f"setstrategy_{group_id}_{game}")],
        [InlineKeyboardButton(toggle_label, callback_data=f"toggle_strategy_{group_id}_{game}")],
        [InlineKeyboardButton("🎯 Stages", callback_data=f"setstages_{group_id}_{game}"), InlineKeyboardButton("🏆 Win Count", callback_data=f"setwincount_{group_id}_{game}")],
        [InlineKeyboardButton("⏰ Timer", callback_data=f"settimer_{group_id}_{game}"), InlineKeyboardButton("📊 Status", callback_data=f"status_{group_id}_{game}")],
        [InlineKeyboardButton("🔎 Details", callback_data=f"details_{group_id}_{game}")],
        [start_button, stop_button],
        [InlineKeyboardButton("🔙 Back", callback_data=f"group_{group_id}")],
    ])
    try:
        await cb.message.edit_text(text, reply_markup=kb)
    except pyrogram.errors.exceptions.bad_request_400.MessageNotModified:
        pass

@app.on_callback_query(filters.regex(r"^status_(.+)_(.+)$"))


@app.on_callback_query(filters.regex(r"^details_(.+)_(.+)$"))
async def details_cb(client, cb: CallbackQuery):
    group_id, game = cb.data.split("_", 2)[1:]
    cfg = load_config()  # Always reload config to get the latest status
    group_cfg = cfg["group_settings"].get(group_id, {})
    game_cfg = group_cfg.get(game, {})
    game_name = get_game_name(game)
    
    # Check both config status and active tasks
    config_status = group_cfg.get("status", "OFF")
    has_active_task = False
    
    # Check if there's an active task for this specific game
    for key, task in signal_tasks.items():
        if isinstance(key, str) and key.startswith(f"{group_id}_{game}_"):
            if "thread" in task and task["thread"].is_alive():
                has_active_task = True
                break
    
    # Also check if group is in starting phase
    is_in_starting_phase = group_id in groups_in_starting_phase
    
    # Determine final status: show ON if there are actual active tasks OR if in starting phase
    final_status = "ON" if (has_active_task or is_in_starting_phase) else "OFF"
    status_display = "🟢 ON" if final_status == "ON" else "🔴 OFF"
    
    strategy = game_cfg.get('strategy', 'random')
    if strategy == "self":
        timer_label = "TIMER (Formula)"
        timer_value = game_cfg.get('timer_formula', '24/7')
    else:
        timer_label = "TIMER (Random)"
        timer_value = game_cfg.get('timer_random', '24/7')

    text = (
        f"<b>📊 {game_name} Details</b>\n\n"
        f"<b>GROUP ID:</b> <code>{group_id}</code>\n"
        f"<b>GAME:</b> <code>{game}</code>\n"
        f"<b>STATUS:</b> {status_display}\n"
        f"<b>CONFIG STATUS:</b> <code>{config_status}</code>\n"
        f"<b>ACTIVE TASK:</b> {'Yes' if has_active_task else 'No'}\n"
        f"<b>Selected STRATEGY:</b> <code>{strategy}</code>\n"
    )
    if strategy == "self":
        text += f"<b>Assigned FORMULA:</b> <code>{game_cfg.get('formula', '')}</code>\n"
    text += (
        f"<b>STAGES:</b> <code>{game_cfg.get('stages', 7)}</code>\n"
        f"<b>WIN COUNT:</b> <code>{game_cfg.get('win_count', 10)}</code>\n"
        f"<b>{timer_label}:</b> <code>{timer_value}</code>\n"
        f"<b>LANGUAGE:</b> <code>{game_cfg.get('lan', 'en')}</code>"
    )
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Back", callback_data=f"gamepanel_{group_id}_{game}")]
    ])
    try:
        await cb.message.edit_text(text, reply_markup=kb)
    except pyrogram.errors.exceptions.bad_request_400.MessageNotModified:
        pass

@app.on_callback_query(filters.regex(r"^remove_(.+)$"))
async def remove_group_cb(client, cb: CallbackQuery):
    group_id = cb.data.split("_", 1)[1]
    cfg = load_config()
    if group_id in cfg["groups"]:
        cfg["groups"].remove(group_id)
        save_config(cfg)
        await cb.message.reply(f"✅ <b>Removed group:</b> <code>{group_id}</code>", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data=f"groups")]]))
    else:
        await cb.message.reply(f"❌ <b>Group not found.</b>", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data=f"groups")]]))
    await groups_cb(client, cb)

@app.on_callback_query(filters.regex(r"^start_(.+)_(.+)$"))
async def start_group_signal_cb(client, cb: CallbackQuery):
    user_id = cb.from_user.id
    username = cb.from_user.username or "No username"
    first_name = cb.from_user.first_name or "No first name"
    last_name = cb.from_user.last_name or ""
    
    # Log start button click
    print(f"🚀 [START BUTTON CLICKED] User ID: {user_id}, Username: @{username}, Name: {first_name} {last_name}")
    print(f"🚀 [START BUTTON CLICKED] Group ID: {cb.data.split('_', 2)[1:] if '_' in cb.data else 'Unknown'}")
    
    group_id, game = cb.data.split("_", 2)[1:]
    
    # Check if ANY signal generator is already running for this group
    if is_signal_generator_running_for_group(group_id):
        await cb.answer("❌ Signal generator is already running for this group! Please stop existing tasks first.", show_alert=True)
        return
    
    # Check if group is already in starting phase
    if group_id in groups_in_starting_phase:
        await cb.answer("❌ Group is already in starting phase! Please wait or stop it first.", show_alert=True)
        return
    
    # Get settings from config
    cfg = load_config()
    group_cfg = cfg["group_settings"].get(group_id, {})
    game_cfg = group_cfg.get(game, {})
    strategy = game_cfg.get("strategy", "random")
    formula = game_cfg.get("formula", "")
    win_count = game_cfg.get("win_count", 10)
    
    # Check if formula exists for formula strategy
    if strategy == "self" and not formula:
        await cb.answer("❌ No formula configured for this group. Please set a formula first.", show_alert=True)
        return
    
    # IMMEDIATELY change group status to ON and disable start button
    try:
        # Update group status to ON immediately
        if group_id in cfg["group_settings"]:
            cfg["group_settings"][group_id]["status"] = "ON"
            save_config(cfg)
            print(f"✅ Group {group_id} status immediately updated to ON")
        
        # Add group to starting phase
        groups_in_starting_phase[group_id] = {
            "game": game,
            "strategy": strategy,
            "start_time": time.time(),
            "stop_event": threading.Event()
        }
        print(f"🔄 Group {group_id} added to starting phase")
        
        # Immediately answer the callback to show "already working"
        await cb.answer("✅ Starting signals... Group status set to ON", show_alert=False)
        
        # Send immediate confirmation message
        immediate_msg = await cb.message.reply(
            f"🚀 **Starting {get_game_name(game).title()} Signals!** 🚀\n\n"
            f"📺 **Target:** Group `{group_id}`\n"
            f"🎮 **Game:** {get_game_name(game).title()}\n"
            f"📊 **Strategy:** {strategy.title()}\n"
            f"🔄 **Status:** ON\n\n"
            f"⏰ **Next step:** Sending game command and waiting 5 minutes...\n\n"
            f"⚠️ **Note:** You can stop this operation at any time!",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⏹️ Stop Signals", callback_data=f"stop_{group_id}_{game}")
            ]])
        )
        
    except Exception as e:
        print(f"Error updating group status: {e}")
        await cb.answer("❌ Error updating group status", show_alert=True)
        return
    
    # Send the same initial messages as the /commands
    try:
        # Check if this is a group or channel to determine sending behavior
        is_group = await is_group_chat(group_id)
        
        if game == "red_green":
            if is_group:
                # For groups: send direct command + background signal
                await client.send_message(int(group_id), "/red_green")
                print(f"✅ Sent /red_green command to group {group_id}")
                # Send command code to bot.py immediately
                bot_comm.send_signal(
                    group_id=str(group_id),
                    game="cr",  # Command code for red_green
                    signal="command",
                    issue_number="0",
                    current_stage=1,
                    strategy="command"
                )
                print(f"✅ Sent red_green command code to bot.py")
            else:
                # For channels: only send background signal (no direct command)
                bot_comm.send_signal(
                    group_id=str(group_id),
                    game="cr",  # Command code for red_green
                    signal="command",
                    issue_number="0",
                    current_stage=1,
                    strategy="command"
                )
                print(f"✅ Sent red_green command code to bot.py for channel {group_id}")
            # Add 2 second delay to give bot.py time to send reply messages
            await asyncio.sleep(2)
        elif game == "blocks":
            if is_group:
                # For groups: send direct command + background signal
                await client.send_message(int(group_id), "/blocks")
                print(f"✅ Sent /blocks command to group {group_id}")
                # Send command code to bot.py immediately
                bot_comm.send_signal(
                    group_id=str(group_id),
                    game="cb",  # Command code for blocks
                    signal="command",
                    issue_number="0",
                    current_stage=1,
                    strategy="command"
                )
                print(f"✅ Sent blocks command code to bot.py")
            else:
                # For channels: only send background signal (no direct command)
                bot_comm.send_signal(
                    group_id=str(group_id),
                    game="cb",  # Command code for blocks
                    signal="command",
                    issue_number="0",
                    current_stage=1,
                    strategy="command"
                )
                print(f"✅ Sent blocks command code to bot.py for channel {group_id}")
            # Add 2 second delay to give bot.py time to send reply messages
            await asyncio.sleep(2)
        elif game == "dices":
            if is_group:
                # For groups: send direct command + background signal
                await client.send_message(int(group_id), "/dices")
                print(f"✅ Sent /dices command to group {group_id}")
                # Send command code to bot.py immediately
                bot_comm.send_signal(
                    group_id=str(group_id),
                    game="cd",  # Command code for dices
                    signal="command",
                    issue_number="0",
                    current_stage=1,
                    strategy="command"
                )
                print(f"✅ Sent dices command code to bot.py")
            else:
                # For channels: only send background signal (no direct command)
                bot_comm.send_signal(
                    group_id=str(group_id),
                    game="cd",  # Command code for dices
                    signal="command",
                    issue_number="0",
                    current_stage=1,
                    strategy="command"
                )
                print(f"✅ Sent dices command code to bot.py for channel {group_id}")
            # Add 2 second delay to give bot.py time to send reply messages
            await asyncio.sleep(2)
        
        # Now sending game commands before starting signals
        # This delay happens for BOTH groups and channels after all commands are sent
        print(f"⏰ Waiting 5 minutes after sending game commands before starting signals for {'group' if is_group else 'channel'} {group_id}")
        
        # Send a message to inform users about the delay
        try:
            chat_type = "group" if is_group else "channel"
            delay_message = f"⏰ **Game Command Sent Successfully!** ⏰\n\n🎮 **Game:** {get_game_name(game).title()}\n📺 **Target:** {chat_type.title()}\n⏱️ **Delay:** 5 minutes before signals start\n\n📝 **What happens now:**\n1️⃣ Game command has been sent to the {chat_type}\n2️⃣ Bot is now waiting 5 minutes\n3️⃣ Signals will start automatically after delay\n\n🔄 **Please wait...**\n⚠️ **You can still stop this operation!**"
            await immediate_msg.edit_text(delay_message)
        except Exception as e:
            print(f"Failed to send delay message: {e}")
        
        # Wait 5 minutes with progress updates and cancellation checks
        print(f"⏰ Starting 5-minute countdown for {'group' if is_group else 'channel'} {group_id}")
        for remaining in range(300, 0, -60):  # Update every minute (60 seconds)
            # Check if user stopped the operation
            if group_id not in groups_in_starting_phase:
                print(f"🛑 Group {group_id} was stopped during countdown")
                return
            
            minutes_left = remaining // 60
            try:
                progress_message = f"⏰ **Countdown in Progress...** ⏰\n\n⏱️ **Time remaining:** {minutes_left} minute{'s' if minutes_left > 1 else ''}\n🎮 **Game:** {get_game_name(game).title()}\n📺 **Target:** {chat_type.title()}\n📊 **Strategy:** {strategy.title()}\n\n🔄 **Signals will start automatically...**\n⚠️ **You can still stop this operation!**"
                # Edit the previous message to show progress
                await immediate_msg.edit_text(progress_message)
            except Exception as e:
                print(f"Failed to update progress message: {e}")
            
            if remaining > 60:  # Don't sleep on the last iteration
                # Sleep in smaller chunks to check for cancellation
                for _ in range(6):  # Check every 10 seconds
                    if group_id not in groups_in_starting_phase:
                        print(f"🛑 Group {group_id} was stopped during countdown")
                        return
                    await asyncio.sleep(10)
        
        # Final countdown (last minute)
        for _ in range(6):  # Check every 10 seconds
            if group_id not in groups_in_starting_phase:
                print(f"🛑 Group {group_id} was stopped during countdown")
                return
            await asyncio.sleep(10)
        
        # Check one final time before starting
        if group_id not in groups_in_starting_phase:
            print(f"🛑 Group {group_id} was stopped during countdown")
            return
        
        print(f"✅ 5-minute delay completed, now starting signals for {'group' if is_group else 'channel'} {group_id}")
        
        # Send completion message
        try:
            completion_message = f"✅ **Delay Completed!** ✅\n\n🎯 **Starting signals now for:** {get_game_name(game).title()}\n📺 **Target:** {chat_type.title()}\n📊 **Strategy:** {strategy.title()}\n\n🚀 **Signals are now active!**"
            await immediate_msg.edit_text(completion_message)
        except Exception as e:
            print(f"Failed to send completion message: {e}")
        
        # Remove from starting phase and start actual signal generation
        if group_id in groups_in_starting_phase:
            # Store the stop_event before removing from starting phase
            stop_event = groups_in_starting_phase[group_id]["stop_event"]
            del groups_in_starting_phase[group_id]
            print(f"🔄 Group {group_id} removed from starting phase, starting signals")
        else:
            # If somehow not in starting phase, create a new stop event
            stop_event = threading.Event()
            print(f"⚠️ Group {group_id} not in starting phase, created new stop event")
        
        # Mark session start for this group/channel
        SESSION_START_TS[str(group_id)] = int(time.time())
        _ensure_session_stats_entry(str(group_id))
        
        # Now start the actual signal generation
        if strategy == "self":
            # Formula strategy
            if game == "red_green":
                thread = run_signal_task_in_thread(formula_signal_generator, group_id, formula, stop_event)
            elif game == "blocks":
                thread = run_signal_task_in_thread(blocks_formula_signal_generator, group_id, formula, stop_event)
            elif game == "dices":
                thread = run_signal_task_in_thread(dices_formula_signal_generator, group_id, formula, stop_event)
        else:
            # Random strategy
            if game == "red_green":
                thread = run_signal_task_in_thread(random_signal_generator, group_id, win_count, stop_event)
            elif game == "blocks":
                thread = run_signal_task_in_thread(blocks_random_signal_generator, group_id, win_count, stop_event)
            elif game == "dices":
                thread = run_signal_task_in_thread(dices_random_signal_generator, group_id, win_count, stop_event)
        
        # Add to signal_tasks
        task_key = f"{group_id}_{game}_{strategy}"
        signal_tasks[task_key] = {"thread": thread, "stop_event": stop_event}
        
        print(f"✅ Successfully started {game} {strategy} signals for group {group_id}")
        
    except (ValueError, KeyError) as e:
        # Handle "Peer id invalid" error - bot is not in the group/channel
        error_message = f"""🚫 **Bot Activation Required!** 🚫

❌ **Error:** Cannot send messages to group/channel `{group_id}`

🔧 **Solution:**
1️⃣ **Add the bot to the group/channel**
2️⃣ **Make the bot an admin** with permission to send messages
3️⃣ **Send the command** `/activate` in the group/channel

📋 **Steps:**
• Go to the group/channel settings
• Add @{client.me.username} as a member
• Promote @{client.me.username} to admin
• Give it permission to send messages
• Send `/activate` command in the group/channel

⚠️ **Note:** The bot must be an admin to send signals and results!"""
        
        await immediate_msg.edit_text(error_message)
        return
    except Exception as e:
        # Handle other errors
        error_message = f"""⚠️ **Unexpected Error!** ⚠️

❌ **Error:** {str(e)}

🔧 **Please try again or contact support if the issue persists.**"""
        
        await immediate_msg.edit_text(error_message)
        return
    
    # Go back to game panel
    await gamepanel_cb(client, cb)

@app.on_callback_query(filters.regex(r"^stop_(.+)_(.+)$"))
async def stop_group_signal_cb(client, cb: CallbackQuery):
    """Handle stop button click"""
    user_id = cb.from_user.id
    username = cb.from_user.username or "No username"
    first_name = cb.from_user.first_name or "No first name"
    last_name = cb.from_user.last_name or ""
    
    # Log stop button click
    print(f"⏹️ [STOP BUTTON CLICKED] User ID: {user_id}, Username: @{username}, Name: {first_name} {last_name}")
    
    if user_id not in get_admin_ids():
        await cb.answer("🚫 You are not authorized to use this bot.", show_alert=True)
        return
    
    group_id, game = cb.data.split("_", 2)[1:]
    
    print(f"⏹️ [STOP BUTTON CLICKED] Group ID: {group_id}, Game: {game}")
    
    print(f"🔍 Looking for tasks to stop for group {group_id}, game {game}")
    print(f"🔍 Current signal_tasks: {list(signal_tasks.keys())}")
    print(f"🔍 Groups in starting phase: {list(groups_in_starting_phase.keys())}")
    
    # First, check if group is in starting phase (after start button, before 5-min delay)
    if group_id in groups_in_starting_phase:
        print(f"🛑 Found group {group_id} in starting phase - cancelling operation")
        
        # Get the stop event and set it
        stop_event = groups_in_starting_phase[group_id]["stop_event"]
        stop_event.set()
        
        # Remove from starting phase
        del groups_in_starting_phase[group_id]
        
        # Update group status to OFF
        cfg = load_config()
        if group_id in cfg["group_settings"]:
            cfg["group_settings"][group_id]["status"] = "OFF"
            save_config(cfg)
            print(f"✅ Group {group_id} status set to OFF")
        
        await cb.answer("✅ Operation cancelled! Group status set to OFF", show_alert=True)
        print(f"✅ Successfully cancelled starting operation for group {group_id}")
        
        # Refresh the game panel to show updated status
        await gamepanel_cb(client, cb)
        return
    
    # Stop ALL signal generators for this group (not just the specific game)
    stopped_count = stop_all_signal_generators_for_group(group_id)
    
    # Update group status to OFF since we stopped all generators
    cfg = load_config()
    if group_id in cfg["group_settings"]:
        cfg["group_settings"][group_id]["status"] = "OFF"
        save_config(cfg)
        print(f"✅ Group {group_id} status set to OFF")
    
    if stopped_count > 0:
        await cb.answer(f"✅ Stopped {stopped_count} signal generator(s) for this group!", show_alert=True)
        print(f"✅ Successfully stopped {stopped_count} signal generator(s) for group {group_id}")
    else:
        await cb.answer("❌ No signal generators were running for this group!", show_alert=True)
        print(f"❌ No signal generators found for group {group_id}")
    
    # Refresh the game panel to show updated status
    await gamepanel_cb(client, cb)

@app.on_callback_query(filters.regex(r"^stop_all_(.+)$"))
async def stop_all_games_cb(client, cb: CallbackQuery):
    """Handle general stop all games button click"""
    user_id = cb.from_user.id
    username = cb.from_user.username or "No username"
    first_name = cb.from_user.first_name or "No first name"
    last_name = cb.from_user.last_name or ""
    
    # Log stop all games button click
    print(f"⏹️ [STOP ALL GAMES BUTTON CLICKED] User ID: {user_id}, Username: @{username}, Name: {first_name} {last_name}")
    
    if user_id not in get_admin_ids():
        await cb.answer("🚫 You are not authorized to use this bot.", show_alert=True)
        return
    
    group_id = cb.data.split("_", 2)[2]
    
    print(f"⏹️ [STOP ALL GAMES BUTTON CLICKED] Group ID: {group_id}")
    
    # Stop ALL signal generators for this group using the comprehensive function
    stopped_count = stop_all_signal_generators_for_group(group_id)
    
    # Update group status to OFF since we stopped all generators
    cfg = load_config()
    if group_id in cfg["group_settings"]:
        cfg["group_settings"][group_id]["status"] = "OFF"
        save_config(cfg)
        print(f"✅ Group {group_id} status set to OFF")
    
    if stopped_count > 0:
        await cb.answer(f"✅ Stopped {stopped_count} signal generator(s) for this group!", show_alert=True)
        print(f"✅ Successfully stopped {stopped_count} signal generator(s) for group {group_id}")
    else:
        await cb.answer("❌ No signal generators were running for this group!", show_alert=True)
        print(f"❌ No signal generators found for group {group_id}")
    
    # Refresh the group panel to show updated status
    fake_cb = FakeCB(cb.from_user, f"group_{group_id}", cb.message)
    await group_panel_cb(client, fake_cb)

@app.on_callback_query(filters.regex("^signal_panel$"))
async def signal_panel_cb(client, cb: CallbackQuery):
    user_id = cb.from_user.id
    push_nav(user_id, "signal_panel")
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🟢🔴 RED-GREEN", callback_data="red_green")],
        [InlineKeyboardButton("🎛 BLOCKS", callback_data="blocks")],
        [InlineKeyboardButton("🎲 DISCS", callback_data="discs")],
        [InlineKeyboardButton("🔙 Back", callback_data="back")],
    ])
    try:
        await cb.message.edit_text(
            "<b>📡 Signal Panel</b>\n\nSelect the game for signal generation:",
            reply_markup=kb
        )
    except pyrogram.errors.exceptions.bad_request_400.MessageNotModified:
        pass

@app.on_callback_query(filters.regex(r"^(red_green|blocks|discs)$"))
async def game_strategy_cb(client, cb: CallbackQuery):
    user_id = cb.from_user.id
    push_nav(user_id, cb.data)
    game = cb.data
    cfg = load_config()
    cfg["game"] = game
    save_config(cfg)
    game_name = get_game_name(game)
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎲 Strategy Random", callback_data=f"{game}_random")],
        [InlineKeyboardButton("📝 Self-Made Strategy", callback_data=f"{game}_self")],
        [InlineKeyboardButton("🔙 Back", callback_data="back")],
    ])
    try:
        await cb.message.edit_text(
            f"<b>{game_name} Strategy</b>\n\nChoose your strategy:",
            reply_markup=kb
        )
    except pyrogram.errors.exceptions.bad_request_400.MessageNotModified:
        pass

@app.on_callback_query(filters.regex(r"_(random)$"))
async def strategy_random_cb(client, cb: CallbackQuery):
    user_id = cb.from_user.id
    push_nav(user_id, cb.data)
    cfg = load_config()
    cfg["strategy"] = "random"
    save_config(cfg)
    try:
        await cb.message.edit_text(
            "<b>🎲 Random strategy selected!</b>\n\n<em>Signal logic will use random strategy.</em>"
        )
    except pyrogram.errors.exceptions.bad_request_400.MessageNotModified:
        pass

@app.on_callback_query(filters.regex(r"_(self)$"))
async def self_made_strategy_cb(client, cb: CallbackQuery):
    user_id = cb.from_user.id
    push_nav(user_id, cb.data)
    game = cb.data.split("_")[0]
    game_name = get_game_name(game)
    user_state[user_id]["awaiting"] = "formula"
    user_state[user_id]["game"] = game
    try:
        await cb.message.edit_text(
            f"<b>{game_name} - Self-Made Strategy</b>\n\n"
            "<i>👉 Enter your formula below:</i>\n"
            "<code>b</code>: Big   <code>s</code>: Small   <code>g</code>: Green   <code>r</code>: Red\n"
            "<code>o</code>: Odd   <code>e</code>: Even   <code>_</code>: Underscore (line break)\n"
            "\n<code>Example:</code>\n<code>rg_r\ngg_g\nrg_r</code>\n\n"
            "<b>💡 Multiple Patterns:</b>\n"
            "• Each line = one pattern\n"
            "• Different lengths allowed\n"
            "• Bot checks ALL patterns\n"
            "• First match wins!\n\n"
            "<em>Send your formula as a message now.</em>"
        )
    except pyrogram.errors.exceptions.bad_request_400.MessageNotModified:
        pass

@app.on_callback_query(filters.regex("^back$"))
async def back_cb(client, cb: CallbackQuery):
    await smart_back(client, cb)
@app.on_callback_query(filters.regex("^3back$"))
async def back_3_cb(client, cb: CallbackQuery):
    await start_panel(client, cb.message)

# --- GROUP MANAGEMENT COMMANDS ---
@app.on_message(filters.command("id"))
async def cmd_id(client, msg: Message):
    await msg.reply(f"<b>Current chat ID:</b> <code>{msg.chat.id}</code>")

@app.on_message(filters.command("test_chat_type"))
async def test_chat_type(client, msg: Message):
    """Test chat type detection"""
    try:
        chat = await app.get_chat(msg.chat.id)
        is_group = await is_group_chat(msg.chat.id)
        
        response = f"""
🔍 **Chat Type Test Results:**

📋 **Chat ID:** `{msg.chat.id}`
📝 **Chat Type:** `{chat.type}`
👥 **Is Group:** `{is_group}`
📛 **Chat Title:** `{chat.title if hasattr(chat, 'title') else 'N/A'}`
        """
        
        await msg.reply(response)
    except Exception as e:
        await msg.reply(f"❌ Error testing chat type: {e}")

@app.on_message(filters.command("add_chat_id"))
async def cmd_add_chat_id(client, msg: Message):
    cfg = load_config()
    print("we are in add chat id")
    chat_id = str(msg.chat.id)
    if chat_id not in cfg["groups"]:
        cfg["groups"].append(chat_id)
        if "group_settings" not in cfg:
            cfg["group_settings"] = {}
        
        # Try to get chat title
        group_title = None
        try:
            chat = await client.get_chat(int(chat_id))
            group_title = chat.title
        except Exception as e:
            print(f"Could not get title for new group {chat_id}: {e}")

        if chat_id not in cfg["group_settings"]:
            cfg["group_settings"][chat_id] = {
                "title": group_title or f"Group {chat_id}",
                "game": "red_green",
                "strategy": "random",
                "formula": "",
                "stages": 7,
                "win_count": 10,
                "timer": "24/7",
                "status": "OFF"
            }
        save_config(cfg)
        await msg.reply(f"✅ <b>Added this chat ID:</b> <code>{chat_id}</code>")
    else:
        await msg.reply(f"ℹ️ <b>This chat ID is already in the group list.</b>")

@app.on_message(filters.command("add_id"))
async def cmd_add_id(client, msg: Message):
    parts = msg.text.strip().split()
    if len(parts) < 2:
        await msg.reply("❌ Usage: /add_id <chat_id>")
        return
    chat_id = parts[1]
    cfg = load_config()
    if chat_id not in cfg["groups"]:
        cfg["groups"].append(chat_id)
        
        # Try to get chat title
        group_title = None
        try:
            chat = await client.get_chat(int(chat_id))
            group_title = chat.title
        except Exception as e:
            print(f"Could not get title for new group {chat_id}: {e}")

        if chat_id not in cfg.get("group_settings", {}):
            if "group_settings" not in cfg:
                cfg["group_settings"] = {}
            cfg["group_settings"][chat_id] = {
                "title": group_title or f"Group {chat_id}",
                "game": "red_green",
                "strategy": "random",
                "formula": "",
                "stages": 7,
                "win_count": 10,
                "timer": "24/7",
                "status": "OFF"
            }
        
        save_config(cfg)
        await msg.reply(f"✅ <b>Added chat ID:</b> <code>{chat_id}</code>")
    else:
        await msg.reply(f"ℹ️ <b>This chat ID is already in the group list.</b>")

@app.on_message(filters.command("remove_id") & filters.private)
async def cmd_remove_id(client, msg: Message):
    parts = msg.text.strip().split()
    if len(parts) < 2:
        await msg.reply("❌ Usage: /remove_id <chat_id>")
        return
    chat_id = parts[1]
    cfg = load_config()
    
    found = False
    # Use .get() to avoid KeyErrors if keys don't exist
    if chat_id in cfg.get("groups", []):
        cfg["groups"].remove(chat_id)
        found = True
        
    if chat_id in cfg.get("group_settings", {}):
        cfg["group_settings"].pop(chat_id, None)
        found = True

    if found:
        save_config(cfg)
        await msg.reply(f"✅ <b>Removed chat ID:</b> <code>{chat_id}</code>")
    else:
        await msg.reply(f"❌ <b>Chat ID not found in group list.</b>")

@app.on_message(filters.command("groups") & filters.private)
async def cmd_groups(client, msg: Message):
    cfg = load_config()
    if not cfg["groups"]:
        await msg.reply("<b>No groups added yet.</b>")
        return
    text = "<b>Group List:</b>\n"
    for gid in cfg["groups"]:
        active = any(t for t in signal_tasks.values() if not t.done() and getattr(t, "group_id", None) == gid)
        emoji = "🟢" if active else "🔴"
        text += f"{emoji} <code>{gid}</code>\n"
    await msg.reply(text)

@app.on_message(filters.command("vietnamese"))
async def set_language_vietnamese(client, message):
    """Set group language to Vietnamese"""
    cfg = load_config()
    chat_id = str(message.chat.id)
    print(chat_id)
    
    if chat_id in cfg.get("group_settings", {}):
        # Set language for all games in this group
        for game in ALL_GAMES:
            if game in cfg["group_settings"][chat_id]:
                cfg["group_settings"][chat_id][game]["lan"] = "vit"
        save_config(cfg)
        await message.reply_text(VIETNAMESE_TRANSLATIONS["language_set_vietnamese"])
    else:
        await message.reply_text(VIETNAMESE_TRANSLATIONS["chat_not_in_list"])

@app.on_message(filters.command("english"))
async def set_language_english(client, message):
    """Set group language to English"""
    cfg = load_config()
    chat_id = str(message.chat.id)
    
    if chat_id in cfg.get("group_settings", {}):
        # Set language for all games in this group
        for game in ALL_GAMES:
            if game in cfg["group_settings"][chat_id]:
                cfg["group_settings"][chat_id][game]["lan"] = "en"
        save_config(cfg)
        await message.reply_text(VIETNAMESE_TRANSLATIONS["language_set_english"])
    else:
        await message.reply_text("This chat ID is not in the list. Please add it first.")


@app.on_message(filters.command("activate"))
async def activate_command(client, msg: Message):
    """Handle /activate command - confirms bot is working in the group/channel"""
    try:
        # Get chat information
        chat = await client.get_chat(msg.chat.id)
        chat_type = "Group" if chat.type in [ChatType.GROUP, ChatType.SUPERGROUP] else "Channel"
        chat_name = chat.title if hasattr(chat, 'title') else 'N/A'
        
        # Get language for the chat - check group language properly
        lang = "en"  # default
        try:
            cfg = load_config()
            if msg.chat.id in cfg.get("group_settings", {}):
                # Check if any game has language setting
                for game in ALL_GAMES:
                    if game in cfg["group_settings"][msg.chat.id]:
                        game_lan = cfg["group_settings"][msg.chat.id][game].get("lan", "en")
                        if game_lan == "vit":
                            lang = "vit"
                            break
                print(f"[ACTIVATE] Using language: {lang} for chat {msg.chat.id}")
            else:
                print(f"[ACTIVATE] Chat not in group settings, using default: {lang}")
        except Exception as lang_error:
            print(f"[ACTIVATE] Error getting language: {lang_error}, using default: {lang}")
        
        # Create success message using translations
        if lang == "vit":
            success_message = get_message_by_language(msg.chat.id, "bot_activated_success", 
                "✅ **Bot đã được kích hoạt thành công!** ✅\n\n🎉 **Trạng thái:** Bot đang hoạt động bình thường\n📋 **Loại chat:** {chat_type}\n\n📛 **Tên chat:** {chat_name}",
                chat_type=chat_type, chat_name=chat_name)
        else:
            success_message = f"""✅ **Bot Activated Successfully!** ✅

🎉 **Status:** Bot is working properly
📋 **Chat Type:** {chat_type}

📛 **Chat Name:** {chat_name}"""
        
        await msg.reply(success_message)
        print(f"✅ Bot activated successfully in {chat_type} {msg.chat.id}")
        
    except Exception as e:
        # Get language for error message
        lang = "vit" if msg.chat.id in load_config().get("group_settings", {}) else "en"
        
        if lang == "vit":
            error_message = get_message_by_language(msg.chat.id, "bot_activation_failed",
                "❌ **Kích hoạt thất bại!** ❌\n\n⚠️ **Lỗi:** {error}\n\n🔧 **Vui lòng đảm bảo:**\n• Bot đã được thêm vào nhóm/kênh\n• Bot có quyền quản trị viên\n• Bot có thể gửi tin nhắn\n\n📞 **Liên hệ hỗ trợ nếu vấn đề vẫn tiếp tục.**",
                error=str(e))
        else:
            error_message = f"""❌ **Activation Failed!** ❌

⚠️ **Error:** {str(e)}

🔧 **Please ensure:**
• Bot is added to the group/channel
• Bot has admin permissions
• Bot can send messages

📞 **Contact support if the issue persists.**"""
        
        await msg.reply(error_message)
        print(f"❌ Failed to activate bot in {msg.chat.id}: {e}")


# --- HELP COMMAND ---
@app.on_message(filters.command("help") & filters.private)
async def cmd_help(client, msg: Message):
    text = (
        "<b>🤖 Premium Signal Generator Bot Help</b>\n\n"
        "<b>Description:</b>\n"
        "Advanced signal generator bot for trading games with per-group management, custom strategies, and automated signal generation.\n\n"
        "<b>🎮 Supported Games:</b>\n"
        "• <b>🟢🔴 RED-GREEN</b> - Red/Green prediction (1-minute intervals)\n"
        "• <b>🟫 BLOCKS</b> - Big/Small prediction (1-minute intervals)\n"
        "• <b>🎲 DICES</b> - Odd/Even prediction (1-minute intervals)\n\n"
        "<b>📋 Private Commands:</b>\n"
        "<code>/start</code> - Open main control panel\n"
        "<code>/help</code> - Show this help message\n"
        "<code>/id</code> - Get current chat ID\n"
        "<code>/add_chat_id</code> - Add current chat to group list\n"
        "<code>/add_id &lt;id&gt;</code> - Add specific group/channel ID\n"
        "<code>/remove_id &lt;id&gt;</code> - Remove group from list\n"
        "<code>/groups</code> - List all groups and their status\n\n"
        "<b>🎯 Group Commands:</b>\n"
        "<code>/stop</code> - Stop all signal generators for this group\n"
        "<code>/red_green</code> - Start Red-Green signals with formula strategy\n"
        "<code>/red_green_ran</code> - Start Red-Green signals with random strategy\n"
        "<code>/blocks</code> - Start Blocks signals with formula strategy\n"
        "<code>/blocks_ran</code> - Start Blocks signals with random strategy\n"
        "<code>/dices</code> - Start Dices signals with formula strategy\n"
        "<code>/dices_ran</code> - Start Dices signals with random strategy\n\n"
        "<b>🎲 Strategy Types:</b>\n"
        "• <b>Random Strategy:</b> Bot sends random signals automatically\n"
        "• <b>Formula Strategy:</b> Custom pattern-based signals using formulas\n\n"
        "<b>📝 Formula Format:</b>\n"
        "• <b>Red-Green:</b> <code>rg_r</code> (if last results = red,green → send red)\n"
        "• <b>Blocks:</b> <code>bs_b</code> (if last results = big,small → send big)\n"
        "• <b>Dices:</b> <code>oe_o</code> (if last results = odd,even → send odd)\n"
        "• Use <code>_</code> for line breaks in multi-line formulas\n\n"
        "<b>⚙️ Game Settings:</b>\n"
        "• <b>Stages:</b> Maximum stages before reset (1-12, default: 7)\n"
        "• <b>Win Count:</b> Target wins before stopping (default: 10)\n"
        "• <b>Timer:</b> Schedule automatic start times (e.g., 10:00, 06:00-20:00-12:00, 24/7)\n\n"
        "<b>🔄 Stage Progression:</b>\n"
        "• Win: Reset to stage 1\n"
        "• Loss: Add 1 to stage\n"
        "• Max stages reached: Auto-reset to stage 1\n\n"
        "<b>🔧 Control Panel Features:</b>\n"
        "• <b>👥 Group List:</b> Manage multiple groups\n"
        "• <b>⚙️ Settings:</b> Admin management and bot configuration\n"
        "• <b>📊 Status:</b> Real-time group and signal status\n"
        "• <b>🔎 Details:</b> Detailed group information\n"
        "• <b>▶️ Start/⏹ Stop:</b> Control signal generation\n\n"
        "<b>🔑 Admin Management:</b>\n"
        "• Add/remove admin users\n"
        "• Manage bot access permissions\n"
        "• Secure admin-only operations\n\n"
        "<b>🚀 Premium Features:</b>\n"
        "• Multi-group management\n"
        "• Per-group, per-game settings\n"
        "• Real-time status indicators\n"
        "• Automated scheduling\n"
        "• Background data fetching\n"
        "• Smart navigation system\n"
        "• Win count tracking with stickers\n"
        "• Maximum stage protection\n\n"
        "<b>📱 User Flow:</b>\n"
        "1. Use <code>/start</code> to open control panel\n"
        "2. Add groups using <code>/add_chat_id</code> or <code>/add_id</code>\n"
        "3. Configure game settings (strategy, stages, win count, timer)\n"
        "4. Start signals using group commands or control panel\n"
        "5. Monitor status and manage operations\n\n"
        "<b>💡 Tips:</b>\n"
        "• Use formula strategy for pattern-based signals\n"
        "• Set appropriate win counts to avoid over-trading\n"
        "• Configure timers for automated operation\n"
        "• Monitor group status regularly\n"
        "• Use <code>/stop</code> to halt all signals\n\n"
        
    )
    await msg.reply(text)

@app.on_callback_query(filters.regex("^settings$"))
async def settings_cb(client, cb: CallbackQuery):
    user_id = cb.from_user.id
    push_nav(user_id, "settings")
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔑 Admins", callback_data="admins")],
        [InlineKeyboardButton("🔙 Back", callback_data="3back")],
    ])
    try:
        await cb.message.edit_text(
            "<b>⚙️ Settings</b>\n\nManage your bot settings:",
            reply_markup=kb
        )
    except pyrogram.errors.exceptions.bad_request_400.MessageNotModified:
        pass

@app.on_callback_query(filters.regex("^admins$"))
async def admins_cb(client, cb: CallbackQuery):
    """Handle admins button click"""
    user_id = cb.from_user.id
    if user_id not in get_admin_ids():
        await cb.answer("🚫 You are not authorized to manage admins.", show_alert=True)
        return
    
    push_nav(user_id, "admins")
    
    # Display current admins with names
    admin_list = []
    admin_ids = get_admin_ids()
    for admin_id in admin_ids:
        try:
            # Try to get user info
            user = await client.get_users(admin_id)
            admin_name = user.first_name or user.username or "Unknown"
            admin_list.append(f"• <code>{admin_id}</code> - {admin_name}")
        except Exception as e:
            # If can't fetch user info, show Unknown
            admin_list.append(f"• <code>{admin_id}</code> - Unknown")
    
    admin_list_text = "\n".join(admin_list)
    
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Add Admin", callback_data="add_admin")],
        [InlineKeyboardButton("➖ Remove Admin", callback_data="yaremove_admin")],
        [InlineKeyboardButton("🔙 Back", callback_data="settings")],
    ])
    
    try:
        await cb.message.edit_text(
            f"<b>🔑 Admin Management</b>\n\n"
            f"<b>Current Admins:</b>\n{admin_list_text}\n\n"
            f"<b>Total Admins:</b> <code>{len(admin_ids)}</code>",
            reply_markup=kb
        )
    except pyrogram.errors.exceptions.bad_request_400.MessageNotModified:
        pass

@app.on_callback_query(filters.regex("^add_admin$"))
async def add_admin_cb(client, cb: CallbackQuery):
    """Handle add admin button click"""
    user_id = cb.from_user.id
    if user_id not in get_admin_ids():
        await cb.answer("🚫 You are not authorized to manage admins.", show_alert=True)
        return
    
    push_nav(user_id, "add_admin")
    user_state[user_id] = {"awaiting": "add_admin"}
    
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Back", callback_data="admins")],
    ])
    
    try:
        await cb.message.edit_text(
            "<b>➕ Add Admin</b>\n\n"
            "You can add an admin in two ways:\n\n"
            "1️⃣ <b>Send the user ID directly:</b>\n"
            "   Just type the numeric user ID\n\n"
            "2️⃣ <b>Forward a message from the user:</b>\n"
            "   Forward any message from the person you want to add as admin\n\n"
            "<i>You can get a user's ID by forwarding their message to @userinfobot</i>",
            reply_markup=kb
        )
    except pyrogram.errors.exceptions.bad_request_400.MessageNotModified:
        pass

@app.on_callback_query(filters.regex("^yaremove_admin$"))
async def remove_admin_cb(client, cb: CallbackQuery):
    """Handle remove admin button click"""
    user_id = cb.from_user.id
    if user_id not in get_admin_ids():
        await cb.answer("🚫 You are not authorized to manage admins.", show_alert=True)
        return
    
    push_nav(user_id, "remove_admin")
    
    # Create buttons for each admin (except the current user)
    kb = []
    admin_ids = get_admin_ids()
    for admin_id in admin_ids:
        if admin_id != user_id:  # Don't allow removing yourself
            try:
                # Try to get user info
                user = await client.get_users(admin_id)
                admin_name = user.first_name or user.username or "Unknown"
                kb.append([InlineKeyboardButton(f"❌ {admin_id} - {admin_name}", callback_data=f"yaremove_admin_{admin_id}")])
            except Exception as e:
                # If can't fetch user info, show Unknown
                kb.append([InlineKeyboardButton(f"❌ {admin_id} - Unknown", callback_data=f"yaremove_admin_{admin_id}")])
    
    kb.append([InlineKeyboardButton("🔙 Back", callback_data="admins")])
    
    try:
        await cb.message.edit_text(
            "<b>➖ Remove Admin</b>\n\n"
            "Select the admin you want to remove:",
            reply_markup=InlineKeyboardMarkup(kb)
        )
    except pyrogram.errors.exceptions.bad_request_400.MessageNotModified:
        pass

@app.on_callback_query(filters.regex(r"^yaremove_admin_(.+)$"))
async def remove_admin_confirm_cb(client, cb: CallbackQuery):
    """Handle remove admin confirmation"""
    user_id = cb.from_user.id
    if user_id not in get_admin_ids():
        await cb.answer("🚫 You are not authorized to manage admins.", show_alert=True)
        return
    
    admin_to_remove = int(cb.data.split("_")[2])
    
    if admin_to_remove == user_id:
        await cb.answer("❌ You cannot remove yourself!", show_alert=True)
        return
    
    admin_ids = get_admin_ids()
    if admin_to_remove in admin_ids:
        # Try to get admin name for confirmation message
        try:
            user = await client.get_users(admin_to_remove)
            admin_name = user.first_name or user.username or "Unknown"
        except Exception as e:
            admin_name = "Unknown"
        
        # Remove from list and save to config
        admin_ids.remove(admin_to_remove)
        if save_admin_ids(admin_ids):
            await cb.answer(f"✅ Admin {admin_to_remove} ({admin_name}) removed successfully!", show_alert=True)
        else:
            await cb.answer("❌ Error saving admin list!", show_alert=True)
            return
    else:
        await cb.answer("❌ Admin not found!", show_alert=True)
        return
    
    # Go back to admins list
    fake_cb = FakeCB(cb.from_user, "admins", cb.message)
    await admins_cb(client, fake_cb)

def get_message_by_language(group_id, message_key, default_message, **kwargs):
    """Get message based on group language setting"""
    cfg = load_config()
    if group_id in cfg.get("group_settings", {}):
        # Check if any game has language setting, default to English
        language = "en"
        for game in ALL_GAMES:
            if game in cfg["group_settings"][group_id]:
                game_lan = cfg["group_settings"][group_id][game].get("lan", "en")
                if game_lan == "vit":
                    language = "vit"
                    break
        
        if language == "vit" and message_key in VIETNAMESE_TRANSLATIONS:
            message = VIETNAMESE_TRANSLATIONS[message_key]
            # Replace any placeholders
            for key, value in kwargs.items():
                message = message.replace(f"{{{key}}}", str(value))
            return message
    
    # Return default message with placeholders replaced
    message = default_message
    for key, value in kwargs.items():
        message = message.replace(f"{{{key}}}", str(value))
    return message

@app.on_callback_query(filters.regex("^help$"))
async def help_cb(client, cb: CallbackQuery):
    user_id = cb.from_user.id
    push_nav(user_id, "help")
    text = (
        "<b>🤖 Premium Signal Generator Bot Help</b>\n\n"
        "<b>Description:</b>\n"
        "Advanced signal generator bot for trading games with per-group management, custom strategies, and automated signal generation.\n\n"
        "<b>🎮 Supported Games:</b>\n"
        "• <b>🟢🔴 RED-GREEN</b> - Red/Green prediction (1-minute intervals)\n"
        "• <b>🟫 BLOCKS</b> - Big/Small prediction (1-minute intervals)\n"
        "• <b>🎲 DICES</b> - Odd/Even prediction (1-minute intervals)\n\n"
        "<b>📋 Private Commands:</b>\n"
        "<code>/start</code> - Open main control panel\n"
        "<code>/help</code> - Show this help message\n"
        "<code>/id</code> - Get current chat ID\n"
        "<code>/add_chat_id</code> - Add current chat to group list\n"
        "<code>/add_id &lt;id&gt;</code> - Add specific group/channel ID\n"
        "<code>/remove_id &lt;id&gt;</code> - Remove group from list\n"
        "<code>/groups</code> - List all groups and their status\n\n"
        "<b>🎯 Group Commands:</b>\n"
        "<code>/stop</code> - Stop all signal generators for this group\n"
        "<code>/red_green</code> - Start Red-Green signals with formula strategy\n"
        "<code>/red_green_ran</code> - Start Red-Green signals with random strategy\n"
        "<code>/blocks</code> - Start Blocks signals with formula strategy\n"
        "<code>/blocks_ran</code> - Start Blocks signals with random strategy\n"
        "<code>/dices</code> - Start Dices signals with formula strategy\n"
        "<code>/dices_ran</code> - Start Dices signals with random strategy\n\n"
        "<b>🎲 Strategy Types:</b>\n"
        "• <b>Random Strategy:</b> Bot sends random signals automatically\n"
        "• <b>Formula Strategy:</b> Custom pattern-based signals using formulas\n\n"
        "<b>📝 Formula Format:</b>\n"
        "• <b>Red-Green:</b> <code>rg_r</code> (if last results = red,green → send red)\n"
        "• <b>Blocks:</b> <code>bs_b</code> (if last results = big,small → send big)\n"
        "• <b>Dices:</b> <code>oe_o</code> (if last results = odd,even → send odd)\n"
        "• Use <code>_</code> for line breaks in multi-line formulas\n\n"
        "<b>⚙️ Game Settings:</b>\n"
        "• <b>Stages:</b> Maximum stages before reset (1-12, default: 7)\n"
        "• <b>Win Count:</b> Target wins before stopping (default: 10)\n"
        "• <b>Timer:</b> Schedule automatic start times (e.g., 10:00, 06:00-20:00-12:00, 24/7)\n\n"
        "<b>🔄 Stage Progression:</b>\n"
        "• Win: Reset to stage 1\n"
        "• Loss: Add 1 to stage\n"
        "• Max stages reached: Auto-reset to stage 1\n\n"
        "<b>🔧 Control Panel Features:</b>\n"
        "• <b>👥 Group List:</b> Manage multiple groups\n"
        "• <b>⚙️ Settings:</b> Admin management and bot configuration\n"
        "• <b>📊 Status:</b> Real-time group and signal status\n"
        "• <b>🔎 Details:</b> Detailed group information\n"
        "• <b>▶️ Start/⏹ Stop:</b> Control signal generation\n\n"
        "<b>🔑 Admin Management:</b>\n"
        "• Add/remove admin users\n"
        "• Manage bot access permissions\n"
        "• Secure admin-only operations\n\n"
        "<b>🚀 Premium Features:</b>\n"
        "• Multi-group management\n"
        "• Per-group, per-game settings\n"
        "• Real-time status indicators\n"
        "• Automated scheduling\n"
        "• Background data fetching\n"
        "• Smart navigation system\n"
        "• Win count tracking with stickers\n"
        "• Maximum stage protection\n\n"
        "<b>📱 User Flow:</b>\n"
        "1. Use <code>/start</code> to open control panel\n"
        "2. Add groups using <code>/add_chat_id</code> or <code>/add_id</code>\n"
        "3. Configure game settings (strategy, stages, win count, timer)\n"
        "4. Start signals using group commands or control panel\n"
        "5. Monitor status and manage operations\n\n"
        "<b>💡 Tips:</b>\n"
        "• Use formula strategy for pattern-based signals\n"
        "• Set appropriate win counts to avoid over-trading\n"
        "• Configure timers for automated operation\n"
        "• Monitor group status regularly\n"
        "• Use <code>/stop</code> to halt all signals\n\n"
        
    )
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="back")]])
    try:
        await cb.message.edit_text(text, reply_markup=kb)
    except pyrogram.errors.exceptions.bad_request_400.MessageNotModified:
        pass

# --- GROUP SETTINGS PANEL ---
@app.on_callback_query(filters.regex(r"^setgame_(.+)$"))
async def setgame_cb(client, cb: CallbackQuery):
    user_id = cb.from_user.id
    group_id = cb.data.split("_", 1)[1]
    user_state[user_id] = {"awaiting": "setgame", "group_id": group_id}
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🟢🔴 RED-GREEN", callback_data=f"setgameval_{group_id}_red_green")],
        [InlineKeyboardButton("🟫 BLOCKS", callback_data=f"setgameval_{group_id}_blocks")],
        [InlineKeyboardButton("🎲 DICES", callback_data=f"setgameval_{group_id}_dices")],
        [InlineKeyboardButton("🔙 Back", callback_data=f"settings_{group_id}")],
    ])
    try:
        await cb.message.edit_text(
            f"<b>🎮 Select Game for Group:</b> <code>{group_id}</code>",
            reply_markup=kb
        )
    except pyrogram.errors.exceptions.bad_request_400.MessageNotModified:
        pass

@app.on_callback_query(filters.regex(r"^setgameval_(.+)_(.+)$"))
async def setgameval_cb(client, cb: CallbackQuery):
    _, group_id, game = cb.data.split("_", 2)
    cfg = load_config()
    cfg["group_settings"][group_id]["game"] = game
    save_config(cfg)
    try:
        await cb.message.edit_text(f"✅ Game set to <b>{game}</b>!")
    except pyrogram.errors.exceptions.bad_request_400.MessageNotModified:
        pass
    class FakeCB:
        def __init__(self, from_user, data, message):
            self.from_user = from_user
            self.data = data
            self.message = message
    fake_cb = FakeCB(cb.from_user, f"settings_{group_id}", cb.message)
    await settings_cb(client, fake_cb)

@app.on_callback_query(filters.regex(r"^setstrategy_(.+)_(.+)$"))
async def setstrategy_cb(client, cb: CallbackQuery):
    user_id = cb.from_user.id
    group_id, game = cb.data.split("_", 2)[1:]
    user_state[user_id] = {"awaiting": "setstrategy", "group_id": group_id, "game": game}
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎲 Random", callback_data=f"setstrategyval_{group_id}_{game}_random")],
        [InlineKeyboardButton("📝 Self-Made", callback_data=f"setformula_{group_id}_{game}")],
        [InlineKeyboardButton("🔙 Back", callback_data=f"gamepanel_{group_id}_{game}")],
    ])
    try:
        await cb.message.edit_text(
            f"<b>🎲 Select Strategy for {get_game_name(game)} in Group:</b> <code>{group_id}</code>",
            reply_markup=kb
        )
    except pyrogram.errors.exceptions.bad_request_400.MessageNotModified:
        pass

@app.on_callback_query(filters.regex(r"^setstrategyval_(.+)_(.+)_(random|self)$"))
async def setstrategyval_cb(client, cb: CallbackQuery):
    _, group_id, game, strategy = cb.data.split("_", 3)
    cfg = load_config()
    cfg["group_settings"][group_id][game]["strategy"] = strategy
    save_config(cfg)
    if strategy == "random":
        try:
            await cb.message.edit_text(f"✅ Strategy set to <b>{strategy}</b>!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data=f"gamepanel_{group_id}_{game}")]]))
        except pyrogram.errors.exceptions.bad_request_400.MessageNotModified:
            pass
    else:  # self-made
        user_id = cb.from_user.id
        user_state[user_id] = {"awaiting": "setformula", "group_id": group_id, "game": game}
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back", callback_data=f"gamepanel_{group_id}_{game}")],
        ])
        try:
                    await cb.message.edit_text(
            f"<b>📝 Self-Made Strategy for {get_game_name(game)} in Group:</b> <code>{group_id}</code>\n\n"
            "<i>👉 Enter your formula below:</i>\n"
            "<code>b</code>: Big   <code>s</code>: Small   <code>g</code>: Green   <code>r</code>: Red\n"
            "<code>o</code>: Odd   <code>e</code>: Even   <code>_</code>: Underscore (line break)\n"
            "\n<code>Example:</code>\n<code>rg_r\ngg_g\nrg_r</code>\n\n"
            "<b>💡 Multiple Patterns:</b>\n"
            "• Each line = one pattern\n"
            "• Different lengths allowed\n"
            "• Bot checks ALL patterns\n"
            "• First match wins!\n\n"
            "<em>Send your formula as a message now.</em>",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data=f"gamepanel_{group_id}_{game}")]])
        )
        except pyrogram.errors.exceptions.bad_request_400.MessageNotModified:
            pass

@app.on_callback_query(filters.regex(r"^setformula_(.+)_(.+)$"))
async def setformula_cb(client, cb: CallbackQuery):
    user_id = cb.from_user.id
    group_id, game = cb.data.split("_", 2)[1:]
    user_state[user_id] = {"awaiting": "setformula", "group_id": group_id, "game": game}
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Back", callback_data=f"gamepanel_{group_id}_{game}")],
    ])
    try:
        await cb.message.edit_text(
            f"<b>📝 Self-Made Strategy for {get_game_name(game)} in Group:</b> <code>{group_id}</code>\n\n"
                "<i>👉 Enter your formula below:</i>\n"
                "<code>b</code>: Big   <code>s</code>: Small   <code>g</code>: Green   <code>r</code>: Red\n"
                "<code>o</code>: Odd   <code>e</code>: Even   <code>_</code>: Underscore (line break)\n"
                "\n<code>Example:</code>\n<code>rg_r\ngg_g\nrg_r</code>\n\n"
                "<b>💡 Multiple Patterns:</b>\n"
                "• Each line = one pattern\n"
                "• Different lengths allowed\n"
                "• Bot checks ALL patterns\n"
                "• First match wins!\n\n"
                "<em>Send your formula as a message now.</em>",
            reply_markup=kb
        )
    except pyrogram.errors.exceptions.bad_request_400.MessageNotModified:
        pass

@app.on_callback_query(filters.regex(r"^setstages_(.+)_(.+)$"))
async def setstages_cb(client, cb: CallbackQuery):
    user_id = cb.from_user.id
    group_id, game = cb.data.split("_", 2)[1:]
    user_state[user_id] = {"awaiting": "setstages", "group_id": group_id, "game": game}
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Back", callback_data=f"gamepanel_{group_id}_{game}")],
    ])
    try:
        await cb.message.edit_text(
            f"<b>🎯 Enter number of stages for {get_game_name(game)} in Group:</b> <code>{group_id}</code>",
            reply_markup=kb
        )
    except pyrogram.errors.exceptions.bad_request_400.MessageNotModified:
        pass

@app.on_callback_query(filters.regex(r"^setwincount_(.+)_(.+)$"))
async def setwincount_cb(client, cb: CallbackQuery):
    user_id = cb.from_user.id
    group_id, game = cb.data.split("_", 2)[1:]
    user_state[user_id] = {"awaiting": "setwincount", "group_id": group_id, "game": game}
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Back", callback_data=f"gamepanel_{group_id}_{game}")],
    ])
    try:
        await cb.message.edit_text(
            f"<b>🏆 Enter win count for {get_game_name(game)} in Group:</b> <code>{group_id}</code>",
            reply_markup=kb
        )
    except pyrogram.errors.exceptions.bad_request_400.MessageNotModified:
        pass

@app.on_callback_query(filters.regex(r"^settimerformula_(.+)_(.+)$"))
async def settimerformula_cb(client, cb: CallbackQuery):
    user_id = cb.from_user.id
    group_id, game = cb.data.split("_", 2)[1:]
    user_state[user_id] = {"awaiting": "settimerformula", "group_id": group_id, "game": game}
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Back", callback_data=f"gamepanel_{group_id}_{game}")],
    ])
    try:
        await cb.message.edit_text(
            f"<b>⏰ Enter formula timer for {get_game_name(game)} in Group:</b> <code>{group_id}</code>\n\n"
            f"<b>Format:</b>\n"
            f"• Single time: <code>20:00</code>\n"
            f"• Multiple times: <code>00:00,16:00,19:00,20:30</code>\n"
            f"• Always on: <code>24/7</code>",
            reply_markup=kb
        )
    except pyrogram.errors.exceptions.bad_request_400.MessageNotModified:
        pass

@app.on_callback_query(filters.regex(r"^settimerrandom_(.+)_(.+)$"))
async def settimerrandom_cb(client, cb: CallbackQuery):
    user_id = cb.from_user.id
    group_id, game = cb.data.split("_", 2)[1:]
    user_state[user_id] = {"awaiting": "settimerrandom", "group_id": group_id, "game": game}
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Back", callback_data=f"gamepanel_{group_id}_{game}")],
    ])
    try:
        await cb.message.edit_text(
            f"<b>⏰ Enter random timer for {get_game_name(game)} in Group:</b> <code>{group_id}</code>\n\n"
            f"<b>Format:</b>\n"
            f"• Single time: <code>20:00</code>\n"
            f"• Multiple times: <code>00:00,16:00,19:00,20:30</code>\n"
            f"• Always on: <code>24/7</code>",
            reply_markup=kb
        )
    except pyrogram.errors.exceptions.bad_request_400.MessageNotModified:
        pass

# --- HANDLE ADMIN INPUT FOR ALL SETTINGS (MERGED) ---
@app.on_message(filters.private)
async def handle_admin_input(client, msg: Message):
    user_id = msg.from_user.id
    if not user_state.get(user_id) or "awaiting" not in user_state[user_id]:
        return
    state = user_state.get(user_id)
    cfg = load_config()

    if state.get("awaiting") == "add_group_id":
        try:
            chat_id = msg.text.strip()
            # Basic validation: check if it's a number, possibly negative.
            int(chat_id) 

            if chat_id in cfg.get("groups", []):
                await msg.reply("❌ This group is already in the list!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="groups")]]))
                return

            # Add the group
            cfg.setdefault("groups", []).append(chat_id)
            
            group_title = None
            try:
                chat = await client.get_chat(int(chat_id))
                group_title = chat.title
            except Exception as e:
                print(f"Could not get title for new group {chat_id}: {e}")

            # Use the new, correct structure for group settings
            group_settings = cfg.setdefault("group_settings", {})
            group_settings[chat_id] = {
                "title": group_title or f"Group {chat_id}",
                "status": "OFF",
            }
            for game in ALL_GAMES:
                group_settings[chat_id][game] = DEFAULT_GAME_SETTINGS.copy()
            
            save_config(cfg)
            await msg.reply(f"✅ Group `{chat_id}` added successfully!")

        except ValueError:
            await msg.reply("❌ Invalid ID. Please send a valid chat ID.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="groups")]]))
            return
        except Exception as e:
            await msg.reply(f"❌ An error occurred: {e}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="groups")]]))
            return

        user_state[user_id] = {}
        # Go back to groups list by calling groups_cb
        new_msg = await msg.reply("...")
        fake_cb = FakeCB(msg.from_user, "groups", new_msg)
        await groups_cb(client, fake_cb)
        return
    
    if state["awaiting"] == "add_admin":
            try:
                new_admin_id = int(msg.text.strip())
                admin_ids = get_admin_ids()
                if new_admin_id in admin_ids:
                    await msg.reply("❌ This user is already an admin!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="admins")]]))
                    return
                else:
                    # Add to list and save to config
                    admin_ids.append(new_admin_id)
                    if save_admin_ids(admin_ids):
                        # Try to get admin name for success message
                        try:
                            user = await client.get_users(new_admin_id)
                            admin_name = user.first_name or user.username or "Unknown"
                        except Exception as e:
                            admin_name = "Unknown"
                        
                        await msg.reply(f"✅ Admin <code>{new_admin_id}</code> ({admin_name}) added successfully!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="admins")]]))
                    else:
                        await msg.reply("❌ Error saving admin list!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="admins")]]))
                        return
            except ValueError:
                await msg.reply("❌ Invalid user ID. Please enter a valid number.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="admins")]]))
                return
            user_state[user_id] = {}
            # Go back to admins list
            fake_cb = FakeCB(msg.from_user, "admins", msg)
            await admins_cb(client, fake_cb)
            return
    # --- Timer logic should be here, not inside the next if ---
    if state["awaiting"] == "settimer":
        val = msg.text.strip()
        group_id = state["group_id"]
        game = state["game"]
        cfg = load_config()
        group_cfg = cfg["group_settings"].get(group_id, {})
        game_cfg = group_cfg.get(game, {})
        strategy = game_cfg.get('strategy', 'random')
        if strategy == 'self':
            game_cfg["timer_formula"] = val
            game_cfg["timer_random"] = "none"
        else:
            game_cfg["timer_random"] = val
            game_cfg["timer_formula"] = "none"
        group_cfg[game] = game_cfg
        cfg["group_settings"][group_id] = group_cfg
        save_config(cfg)
        user_state[user_id] = {}
        await msg.reply(f"✅ Timer set to {val} for {get_game_name(game)} in group <code>{group_id}</code>!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data=f"gamepanel_{group_id}_{game}")]]))
        fake_cb = FakeCB(msg.from_user, f"gamepanel_{group_id}_{game}", msg)
        await gamepanel_cb(client, fake_cb)
        return

    # --- Per-group, per-game settings ---
    if state.get("game") and state.get("group_id"):
        group_id = state["group_id"]
        game = state["game"]
        group_cfg = cfg["group_settings"].get(group_id, {})
        game_cfg = group_cfg.get(game, {})
        if state["awaiting"] == "setformula":
            game_cfg["formula"] = msg.text.strip()
            group_cfg[game] = game_cfg
            cfg["group_settings"][group_id] = group_cfg
            save_config(cfg)
            user_state[user_id] = {}
            await msg.reply(f"✅ Formula updated for group <code>{group_id}</code>!")
            # Create a new message for the game panel
            await send_game_panel(client, msg.chat.id, group_id, game)
            return
        elif state["awaiting"] == "setstages":
            try:
                val = int(msg.text.strip())
                if 1 <= val <= 12:
                    game_cfg["stages"] = val
                    group_cfg[game] = game_cfg
                    cfg["group_settings"][group_id] = group_cfg
                    save_config(cfg)
                    user_state[user_id] = {}
                    await msg.reply(f"✅ Stages set to {val} for {get_game_name(game)} in group <code>{group_id}</code>!")
                    # Create a new message for the game panel
                    await send_game_panel(client, msg.chat.id, group_id, game)
                else:
                    await msg.reply("❌ Invalid number. Please enter a value between 1 and 12.")
                    return
            except Exception:
                await msg.reply("❌ Invalid input. Please enter a number.")
                return
        elif state["awaiting"] == "setwincount":
            try:
                val = int(msg.text.strip())
                if val > 0:
                    game_cfg["win_count"] = val
                    group_cfg[game] = game_cfg
                    cfg["group_settings"][group_id] = group_cfg
                    save_config(cfg)
                    user_state[user_id] = {}
                    await msg.reply(f"✅ Win count set to {val} for {get_game_name(game)} in group <code>{group_id}</code>!")
                    # Create a new message for the game panel
                    await send_game_panel(client, msg.chat.id, group_id, game)
                else:
                    await msg.reply("❌ Invalid number. Please enter a positive value.")
                    return
            except Exception:
                await msg.reply("❌ Invalid input. Please enter a number.")
                return
        elif state["awaiting"] == "settimerformula":
            val = msg.text.strip()
            # Validate timer format
            if val != "24/7":
                parsed_times = parse_cron_time(val)
                if parsed_times is None:
                    await msg.reply("❌ Invalid timer format! Please use:\n"
                                  "• Single time: <code>20:00</code>\n"
                                  "• Multiple times: <code>00:00,16:00,19:00,20:30</code>\n"
                                  "• Always on: <code>24/7</code>")
                    return
            
            game_cfg["timer_formula"] = val
            group_cfg[game] = game_cfg
            cfg["group_settings"][group_id] = group_cfg
            save_config(cfg)
            user_state[user_id] = {}
            await msg.reply(f"✅ Formula timer set to {val} for {get_game_name(game)} in group <code>{group_id}</code>!")
            # Create a new message for the game panel
            await send_game_panel(client, msg.chat.id, group_id, game)
        elif state["awaiting"] == "settimerrandom":
            val = msg.text.strip()
            # Validate timer format
            if val != "24/7":
                parsed_times = parse_cron_time(val)
                if parsed_times is None:
                    await msg.reply("❌ Invalid timer format! Please use:\n"
                                  "• Single time: <code>20:00</code>\n"
                                  "• Multiple times: <code>00:00,16:00,19:00,20:30</code>\n"
                                  "• Always on: <code>24/7</code>")
                    return
            
            game_cfg["timer_random"] = val
            group_cfg[game] = game_cfg
            cfg["group_settings"][group_id] = group_cfg
            save_config(cfg)
            user_state[user_id] = {}
            await msg.reply(f"✅ Random timer set to {val} for {get_game_name(game)} in group <code>{group_id}</code>!")
            # Create a new message for the game panel
            await send_game_panel(client, msg.chat.id, group_id, game)
        
        elif state["awaiting"] == "add_group_id":
            try:
                chat_id = msg.text.strip()
                # Basic validation: check if it's a number, possibly negative.
                int(chat_id) 

                if chat_id in cfg.get("groups", []):
                    await msg.reply("❌ This group is already in the list!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="groups")]]))
                    return

                # Add the group
                cfg.setdefault("groups", []).append(chat_id)
                
                group_title = None
                try:
                    chat = await client.get_chat(int(chat_id))
                    group_title = chat.title
                except Exception as e:
                    print(f"Could not get title for new group {chat_id}: {e}")

                # Use the new, correct structure for group settings
                group_settings = cfg.setdefault("group_settings", {})
                group_settings[chat_id] = {
                    "title": group_title or f"Group {chat_id}",
                    "status": "OFF",
                }
                for game in ALL_GAMES:
                    group_settings[chat_id][game] = DEFAULT_GAME_SETTINGS.copy()
                
                save_config(cfg)
                await msg.reply(f"✅ Group `{chat_id}` added successfully!")

            except ValueError:
                await msg.reply("❌ Invalid ID. Please send a valid chat ID.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="groups")]]))
                return
            except Exception as e:
                await msg.reply(f"❌ An error occurred: {e}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="groups")]]))
                return

            user_state[user_id] = {}
            # Go back to groups list by calling groups_cb
            new_msg = await msg.reply("...")
            fake_cb = FakeCB(msg.from_user, "groups", new_msg)
            await groups_cb(client, fake_cb)
            return
        return
    # --- Fallback: global/group settings (old logic) ---
    if state["awaiting"] == "formula":
        cfg["formula"] = msg.text.strip()
        cfg["strategy"] = "self"
        save_config(cfg)
        user_state[user_id].pop("awaiting", None)
        await msg.reply("✅ <b>Formula updated successfully!</b>", parse_mode=ParseMode.HTML)
        await start_panel(client, msg)
    elif state["awaiting"] == "stages":
        try:
            val = int(msg.text.strip())
            if 1 <= val <= 12:
                cfg["stages"] = val
                save_config(cfg)
                await msg.reply(f"✅ <b>Stages set to {val}!</b>", parse_mode=ParseMode.HTML)
            else:
                await msg.reply("❌ <b>Invalid number. Please enter a value between 1 and 12.</b>", parse_mode=ParseMode.HTML)
                return
        except Exception:
            await msg.reply("❌ <b>Invalid input. Please enter a number.</b>", parse_mode=ParseMode.HTML)
            return
        user_state[user_id].pop("awaiting", None)
        await start_panel(client, msg)
    elif state["awaiting"] == "win_count":
        try:
            val = int(msg.text.strip())
            if val > 0:
                cfg["win_count"] = val
                save_config(cfg)
                await msg.reply(f"✅ <b>Win count set to {val}!</b>", parse_mode=ParseMode.HTML)
            else:
                await msg.reply("❌ <b>Invalid number. Please enter a positive value.</b>", parse_mode=ParseMode.HTML)
                return
        except Exception:
            await msg.reply("❌ <b>Invalid input. Please enter a number.</b>", parse_mode=ParseMode.HTML)
            return
        user_state[user_id].pop("awaiting", None)
        await start_panel(client, msg)
    elif state["awaiting"] == "timer_formula":
        val = msg.text.strip()
        cfg["timer_formula"] = val
        save_config(cfg)
        user_state[user_id].pop("awaiting", None)
        await msg.reply(f"✅ <b>Formula timer set to {val}!</b>", parse_mode=ParseMode.HTML)
        await start_panel(client, msg)
    elif state["awaiting"] == "timer_random":
        val = msg.text.strip()
        cfg["timer_random"] = val
        save_config(cfg)
        user_state[user_id].pop("awaiting", None)
        await msg.reply(f"✅ <b>Random timer set to {val}!</b>", parse_mode=ParseMode.HTML)
        await start_panel(client, msg)
    # --- new timer edit logic ---
    elif state["awaiting"] == "settimer":
        print(f"\n\nSetting timer to {msg.text.strip()}")
        val = msg.text.strip()
        group_id = state["group_id"]
        game = state["game"]
        cfg = load_config()
        group_cfg = cfg["group_settings"].get(group_id, {})
        game_cfg = group_cfg.get(game, {})
        strategy = game_cfg.get('strategy', 'random')
        if strategy == 'self':
            game_cfg["timer_formula"] = val
            game_cfg["timer_random"] = "none"
        else:
            game_cfg["timer_random"] = val
            game_cfg["timer_formula"] = "none"
        group_cfg[game] = game_cfg
        cfg["group_settings"][group_id] = group_cfg
        save_config(cfg)
        user_state[user_id] = {}
        await msg.reply(f"✅ Timer set to {val} for {get_game_name(game)} in group <code>{group_id}</code>!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data=f"gamepanel_{group_id}_{game}")]]))
        # Create a new message for the game panel
        await send_game_panel(client, msg.chat.id, group_id, game)
        return

def wait_for_next_minute():
    """Wait until the next minute starts"""
    current_minute = datetime.now().minute
    while True:
        if datetime.now().minute != current_minute:
            break
        time.sleep(1)

def print_latest_issue(table, game_name):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    if table == "dices_results" or table == "blocks_results":
        c.execute(f"SELECT issue, result, timestamp FROM {table} ORDER BY timestamp DESC LIMIT 1")
    elif table == "red_green_results":
        c.execute(f"SELECT issue, value, color, timestamp FROM {table} ORDER BY timestamp DESC LIMIT 1")
    else:
        print(f"[{game_name}] Unknown table: {table}")
        conn.close()
        return
    row = c.fetchone()
    if row:
        print(f"[{game_name}] Latest issue:")
        print(row)
    conn.close()

def insert_dices_results(records):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    new_issue = False
    for rec in records:
        issue = str(rec.get('issue'))
        result_list = rec.get('resultFormatValueI18n', [])
        result = ",".join(result_list) if result_list else None
        c.execute("INSERT OR IGNORE INTO dices_results (issue, result) VALUES (?, ?)", (issue, result))
        if c.rowcount > 0:
            new_issue = True
    conn.commit()
    conn.close()
    if new_issue:
        print_latest_issue('dices_results', 'DICES')

def insert_blocks_results(records):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    new_issue = False
    for rec in records:
        issue = str(rec.get('issue'))
        result_list = rec.get('resultFormatValueI18n', [])
        result = ",".join(result_list) if result_list else None
        c.execute("INSERT OR IGNORE INTO blocks_results (issue, result) VALUES (?, ?)", (issue, result))
        if c.rowcount > 0:
            new_issue = True
    conn.commit()
    conn.close()
    if new_issue:
        print_latest_issue('blocks_results', 'BLOCKS')

def insert_red_green_results(records):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    new_issue = False
    for rec in records:
        issue = str(rec.get('issue'))
        value = str(rec.get('value'))
        color = None
        try:
            clean_val = int(value.replace(" ", ""))
            # Special rules for specific numbers
            if clean_val == 5:
                color = "GREEN   🟢"
            elif clean_val == 0:
                color = "RED   🔴"
            else:
                # Default odd/even rule
                color = "GREEN   🟢" if clean_val % 2 else "RED   🔴"
        except:
            pass
        c.execute("INSERT OR IGNORE INTO red_green_results (issue, value, color) VALUES (?, ?, ?)", (issue, value, color))
        if c.rowcount > 0:
            new_issue = True
    conn.commit()
    conn.close()
    if new_issue:
        print_latest_issue('red_green_results', 'RED_GREEN')

def fetch_and_store_dices():
    while True:
        try:
            resp = requests.get(DICES_URL, params=DICES_PARAMS, headers=DICES_HEADERS, timeout=10)
            data = resp.json()
            records = data.get('data', {}).get('records', [])
            # Filter for valid records
            valid_records = [rec for rec in records if rec.get('resultFormatValueI18n') and any(x for x in rec.get('resultFormatValueI18n') if x)]
            if valid_records:
                insert_dices_results(valid_records)
                break
            else:
                print("[DICES] No valid result yet, retrying...")
                time.sleep(2)
        except Exception as e:
            try:
                print(f"[DICES] Fetch error: {e}\nResponse: {resp.text}")
            except Exception:
                print(f"[DICES] Fetch error: {e}")
            time.sleep(2)

def fetch_and_store_blocks():
    while True:
        try:
            resp = requests.get(BLOCKS_URL, params=BLOCKS_PARAMS, headers=BLOCKS_HEADERS, timeout=10)
            data = resp.json()
            records = data.get('data', {}).get('records', [])
            valid_records = [rec for rec in records if rec.get('resultFormatValueI18n') and any(x for x in rec.get('resultFormatValueI18n') if x)]
            if valid_records:
                insert_blocks_results(valid_records)
                break
            else:
                print("[BLOCKS] No valid result yet, retrying...")
                time.sleep(2)
        except Exception as e:
            try:
                print(f"[BLOCKS] Fetch error: {e}\nResponse: {resp.text}")
            except Exception:
                print(f"[BLOCKS] Fetch error: {e}")
            time.sleep(2)

def fetch_and_store_red_green():
    while True:
        try:
            resp = requests.get(RED_GREEN_URL, params=RED_GREEN_PARAMS, headers=RED_GREEN_HEADERS, timeout=10)
            data = resp.json()
            records = data.get('data', {}).get('records', [])
            valid_records = [rec for rec in records if rec.get('value') not in (None, "None", "")]
            if valid_records:
                insert_red_green_results(valid_records)
                break
            else:
                print("[RED_GREEN] No valid result yet, retrying...")
                time.sleep(2)
        except Exception as e:
            try:
                print(f"[RED_GREEN] Fetch error: {e}\nResponse: {resp.text}")
            except Exception:
                print(f"[RED_GREEN] Fetch error: {e}")
            time.sleep(2)

def background_fetcher_thread(fetch_func, name):
    print(f"[{name}] Background fetcher thread started.")
    while True:
        try:
            fetch_func()
        except Exception as e:
            print(f"[{name}] Background fetch error: {e}")
        time.sleep(1)

def check_dices_formula_pattern(formula, last_results):
    """
    Check if the last results match the pattern in formula
    formula format: "oe_o" or multi-line like "oe_o\neo_e" where:
    - First part (oe) is the pattern to match (will be reversed to match actual results)
    - After underscore (_) is the signal to send
    o = odd, e = even
    """
    try:
        # Split formula into lines to handle multi-line formulas
        formula_lines = formula.strip().split('\n')
        
        for line in formula_lines:
            line = line.strip()
            if not line or '_' not in line:
                continue
                
            try:
                pattern, signal = line.split('_', 1)  # Split on first underscore only
                # Convert last results to string format (most recent first)
                results_str = ''
                for result in last_results:
                    if result and result.strip():
                        try:
                            # Convert to lowercase and remove extra spaces for easier matching
                            result_lower = result.lower().strip()
                            # Check if result contains 'odd' or 'even' anywhere in the text
                            if 'odd' in result_lower:
                                results_str += 'o'
                            elif 'even' in result_lower:
                                results_str += 'e'
                            else:
                                print(f"Could not find Odd/Even in result: {result}")
                                continue
                        except Exception as e:
                            print(f"Error parsing result {result}: {e}")
                            continue
                
                # Reverse the pattern to match actual results order
                reversed_pattern = pattern[::-1]  # This will convert "oe" to "eo"
                
                print(f"Checking dices pattern: {reversed_pattern} against results: {results_str}")
                # Check if pattern matches
                if results_str == reversed_pattern:
                    return True, signal
            except Exception as e:
                print(f"Error processing formula line '{line}': {e}")
                continue
        
        return False, None
    except Exception as e:
        print(f"Error in check_dices_formula_pattern: {e}")
        return False, None

async def send_dices_signal_message(group_id, signal, issue_number, current_stage=1, strategy="formula"):
    """Send formatted dices signal message to group"""
    try:
        # Ensure numeric values
        issue_number = str(issue_number)
        # Keep current_stage as int for background API
        
        # Check if this is a group or channel to determine message format
        is_group = await is_group_chat(group_id)
        
        if is_group:
            # For groups: use compact format (background communication will handle issue numbers)
            message = f"{signal.upper()}x{current_stage}"
        else:
            # For channels: include issue number for precise result gating
            message = f"{signal.upper()}x{current_stage}_{issue_number}"
        
        # Send the message with error handling
        try:
            await app.send_message(group_id, message)
        except (ValueError, KeyError) as e:
            # Handle "Peer id invalid" error - bot is not in the group/channel
            print(f"🚫 Bot not in group/channel {group_id}: {e}")
            return int(current_stage)  # Return current stage on error
        except Exception as e:
            print(f"⚠️ Error sending signal to {group_id}: {e}")
            return int(current_stage)  # Return current stage on error
        
        # Only send background signals for groups (not channels)
        if is_group:
            # Send signal to trading bot via communication system
            try:
                bot_comm.send_signal(
                    group_id=group_id,
                    game="dices",
                    signal=signal,
                    issue_number=issue_number,
                    current_stage=int(current_stage),
                    strategy=strategy
                )
                print(f"✅ Background signal sent for group {group_id}")
                gid = str(group_id)
                _ensure_session_stats_entry(gid)
                GROUP_SESSION_STATS[gid]["dices"]["signals"] += 1
            except Exception as e:
                print(f"Error sending signal to trading bot: {e}")
        else:
            print(f"⏭️ Skipping background signal for channel {group_id}")
        
        # Start checking for results immediately
        max_attempts = 3000  # Check for 30 seconds
        attempt = 0
        result = None
        
        while attempt < max_attempts:
            # Get the actual result
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute("SELECT result FROM dices_results WHERE issue = ?", (issue_number,))
            result = c.fetchone()
            conn.close()
            
            # if result and result[0]:
            #     break
                
            # Check latest issue number
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute("SELECT issue FROM dices_results ORDER BY timestamp DESC LIMIT 1")
            latest_issue = c.fetchone()
            conn.close()
            print(latest_issue[0], issue_number)
            if int(latest_issue[0]) > int(issue_number):
                break
                
            attempt += 1
            await asyncio.sleep(1)  # Check every second
            
        # if result and result[0]:
        try:
            # Convert to lowercase and remove extra spaces for easier matching
            # Get latest result from database
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute("SELECT result FROM dices_results ORDER BY timestamp DESC LIMIT 1")
            latest_result = c.fetchone()
            conn.close()
            
            result_lower = latest_result[0].lower().strip()
            print(result_lower, latest_result[0])
            # Check if result contains 'odd' or 'even' anywhere in the text
            is_odd = 'odd' in result_lower
            actual_result = get_message_by_language(group_id, "result_odd", "LẺ   🔢") if is_odd else get_message_by_language(group_id, "result_even", "CHẴN   🔢")
            
            # Check if signal was correct
            is_win = (signal == "o" and is_odd) or (signal == "e" and not is_odd)
            
            # Send result message
            result_message = f"RESULT: {actual_result}"
            if signal == "o":
                    signal = "Odd"
            else:
                signal = "Even"
            # Send win/lose message
            if is_win:
                gid = str(group_id)
                _ensure_session_stats_entry(gid)
                GROUP_SESSION_STATS[gid]["dices"]["wins"] += 1
                _append_history(gid, f"DICES: WIN | {actual_result}")
                return 1  # Reset stage to 1 on win
            else:
                result_lower = latest_result[0].lower().strip()
                print(result_lower, latest_result[0])
                # Check if result contains 'odd' or 'even' anywhere in the text
                is_odd = 'odd' in result_lower
                actual_result = "ODD   🔢" if is_odd else "EVEN   🔢"
                gid = str(group_id)
                _ensure_session_stats_entry(gid)
                GROUP_SESSION_STATS[gid]["dices"]["losses"] += 1
                _append_history(gid, f"DICES: LOSS | {actual_result}")
                # Get max stages from config
                cfg = load_config()
                max_stages = 12  # Default
                if group_id in cfg["group_settings"]:
                    game_cfg = cfg["group_settings"][group_id].get("dices", {})
                    max_stages = game_cfg.get("stages", 12)
                
                new_stage = int(current_stage) + 1
                if new_stage > max_stages:
                    max_stages_msg = get_message_by_language(group_id, "max_stages", "Maximum stages ({max_stages}) reached! Resetting...", max_stages=max_stages)
                    await app.send_message(group_id, max_stages_msg)
                    await app.send_message(group_id, "/stop")
                    
                    # Send stop command when max stages reached - different approach for groups vs channels
                    try:
                        is_group = await is_group_chat(group_id)
                        if is_group:
                            # For groups: use background bridge
                            bot_comm.send_signal(
                                group_id=str(group_id),
                                game="stop",  # Command code for stop
                                signal="max_stages_reached",  # Stop command
                                issue_number="0",
                                current_stage=1,
                                strategy="command"
                            )
                            print(f"✅ Sent stop command via background bridge for group {group_id} (max stages reached)")
                        else:
                            # For channels: send direct command
                            await app.send_message(group_id, "/stop")
                            print(f"✅ Sent stop command directly to channel {group_id} (max stages reached)")
                    except Exception as e:
                        print(f"Error sending stop command: {e}")
                    
                    return 0  # Reset to stage 1
                else:
                    return new_stage  # Add 1 to stage on loss
        except Exception as e:
            print(f"Error processing result: {e}")
            return int(current_stage)  # Return current stage on error
        # return int(current_stage)  # Return current stage if no result
        
    except Exception as e:
        print(f"Error in send_dices_signal_message: {e}")
        return int(current_stage)  # Return current stage on error

async def dices_formula_signal_generator(group_id, formula, stop_event):
    """Background task to generate signals based on formula for dices"""
    last_results = []  # Store last results
    last_issue = None  # Track last issue to avoid duplicates
    current_stage = 1  # Track current stage
    wins = 0  # Track number of wins
    win_count = 10  # Default win count
    
    try:
        # Determine target wins from config (default 10)
        target_wins = 10
        try:
            cfg = load_config()
            gid = str(group_id)
            target_wins = int(cfg.get("group_settings", {}).get(gid, {}).get("dices", {}).get("win_count", 10))
        except Exception:
            pass
        # Get win count from config
        cfg = load_config()
        if group_id in cfg["group_settings"]:
            game_cfg = cfg["group_settings"][group_id].get("dices", {})
            win_count = game_cfg.get("win_count", 10)
        
        # Get pattern length from formula
        pattern_length = len(formula.split('_')[0])
        print(f"Pattern length from formula: {pattern_length}")
        
        while wins < win_count:
            if stop_event.is_set():
                print(f"Stop signal received for group {group_id}")
                break
            try:
                # Check if we should stop
                if group_id in signal_tasks and signal_tasks[group_id].get("stop_event", None) and signal_tasks[group_id]["stop_event"].is_set():
                    print(f"Stop signal received for group {group_id}")
                    break

                # Get latest result from database
                conn = sqlite3.connect(DB_FILE)
                c = conn.cursor()
                # Fetch results based on pattern length
                c.execute(f"SELECT issue, result FROM dices_results ORDER BY timestamp DESC LIMIT {pattern_length}")
                results = c.fetchall()
                conn.close()
                
                if len(results) >= pattern_length:
                    current_issue = results[0][0]
                    
                    # Only process if we have a new issue
                    if current_issue != last_issue:
                        # Update last results (most recent first)
                        last_results = [r[1] for r in results]
                        
                        # Check if pattern matches (last results match our pattern)
                        pattern_matches, signal = check_dices_formula_pattern(formula, last_results)
                        
                        if pattern_matches:
                            print(f"Pattern matched! Last results: {last_results}, Sending signal: {signal}")
                            # Send signal and get new stage
                            new_stage = await send_dices_signal_message(group_id, signal, current_issue, current_stage)
                            
                            # Update stage and check for win
                            if new_stage == 1:  # Win condition
                                wins += 1
                                if wins >= target_wins:
                                    # Send stop and statistics commands - different approach for groups vs channels
                                    try:
                                        is_group = await is_group_chat(group_id)
                                        if is_group:
                                            # For groups: use background bridge
                                            bot_comm.send_signal(
                                                group_id=str(group_id),
                                                game="stop",  # Command code for stop
                                                signal="command",  # Stop command
                                                issue_number="0",
                                                current_stage=1,
                                                strategy="command"
                                            )
                                            await asyncio.sleep(1)
                                            bot_comm.send_signal(
                                                group_id=str(group_id),
                                                game="statistics",  # Command code for statistics
                                                signal="command",
                                                issue_number="0",
                                                current_stage=1,
                                                strategy="command"
                                            )
                                            print(f"✅ Sent stop and statistics command codes to bot.py for group {group_id}")
                                        else:
                                            # For channels: send direct commands (bots can see each other)
                                            await app.send_message(group_id, "/stop")
                                            await asyncio.sleep(1)
                                            await app.send_message(group_id, "/statistics")
                                            print(f"✅ Sent direct stop and statistics commands to channel {group_id}")
                                    except Exception as e:
                                        print(f"Error sending stop/statistics commands: {e}")
                                    break
                                pass
                                # await app.send_sticker(group_id, STICKERS[str(wins)]["file_id"])
                            elif new_stage == 0:
                                print(f"🚫 Max stages reached for group {group_id} - stopping signal generator")
                                # Send stop and statistics commands - same as win count reached
                                try:
                                    is_group = await is_group_chat(group_id)
                                    if is_group:
                                        # For groups: use background bridge
                                        bot_comm.send_signal(
                                            group_id=str(group_id),
                                            game="stop",
                                            signal="max_stages_reached",
                                            issue_number="0",
                                            current_stage=1,
                                            strategy="command"
                                        )
                                        await asyncio.sleep(1)
                                        bot_comm.send_signal(
                                            group_id=str(group_id),
                                            game="statistics",
                                            signal="command",
                                            issue_number="0",
                                            current_stage=1,
                                            strategy="command"
                                        )
                                        await app.send_message(group_id, "/stop")
                                        print(f"✅ Sent stop and statistics command codes to bot.py for group {group_id}")
                                    else:
                                        # For channels: send direct commands
                                        await app.send_message(group_id, "/stop")
                                        await asyncio.sleep(1)
                                        await app.send_message(group_id, "/statistics")
                                        print(f"✅ Sent direct stop and statistics commands to channel {group_id}")
                                except Exception as e:
                                    print(f"Error sending stop/statistics commands: {e}")
                                
                                # Call stop_signals_loss to properly stop and clean up signal generators
                                try:
                                    await stop_signals_loss(app, group_id)
                                    print(f"✅ Called stop_signals_loss for group {group_id}")
                                except Exception as e:
                                    print(f"Error calling stop_signals_loss: {e}")
                                
                                # Send completion message for max stages
                                completion_msg = get_message_by_language(group_id, "max_stages_reached", "🛑 Maximum stages reached! Stopping signals.")
                                await app.send_message(group_id, completion_msg)
                                break
                            
                            current_stage = new_stage
                            last_issue = current_issue
                            
                            # Add 2-second delay after sending signal
                            print(f"DEBUG: Adding 2-second delay after sending signal")
                            await asyncio.sleep(2)
                        
                    await asyncio.sleep(1)  # Check every second
                else:
                    await asyncio.sleep(1)  # Wait if not enough results

            except asyncio.CancelledError:
                # Task was cancelled by stop button
                break
            except Exception as e:
                print(f"Error in dices formula signal generator: {e}")
                await asyncio.sleep(1)
    finally:
        # Update group status in config
        cfg = load_config()
        if group_id in cfg["group_settings"]:
            cfg["group_settings"][group_id]["status"] = "OFF"
            save_config(cfg)
        # Remove task from signal_tasks (support both old and scheduler keys)
        for key, task in list(signal_tasks.items()):
            if (hasattr(task, 'group_id') and task.group_id == group_id) or key == group_id or key.startswith(f"{group_id}_"):
                del signal_tasks[key]
        # Only send completion message if we reached win count
        if wins >= win_count:
            completion_msg = get_message_by_language(group_id, "target_reached", "✅ Target of {win_count} wins reached! Stopping signals.", win_count=win_count)
            await app.send_message(group_id, completion_msg)

async def dices_random_signal_generator(group_id, win_count, stop_event):
    """Background task to generate random signals for dices"""
    current_stage = 1  # Track current stage
    wins = 0  # Track number of wins
    last_issue = None  # Track last issue to avoid duplicates
    
    try:
        target_wins = win_count if isinstance(win_count, int) and win_count > 0 else 10
        while wins < win_count:
            if stop_event.is_set():
                print(f"Stop signal received for group {group_id}")
                break
            try:
                # Check if we should stop
                if group_id in signal_tasks and signal_tasks[group_id].get("stop_event", None) and signal_tasks[group_id]["stop_event"].is_set():
                    print(f"Stop signal received for group {group_id}")
                    break

                # Get latest result from database
                conn = sqlite3.connect(DB_FILE)
                c = conn.cursor()
                c.execute("SELECT issue FROM dices_results ORDER BY timestamp DESC LIMIT 1")
                result = c.fetchone()
                conn.close()

                if result:
                    current_issue = result[0]
                    
                    # Only process if we have a new issue
                    if current_issue != last_issue:
                        # Randomly choose between odd and even
                        signal = random.choice(['o', 'e'])
                        
                        # Send signal and get new stage
                        new_stage = await send_dices_signal_message(group_id, signal, current_issue, current_stage, strategy="random")
                        
                        # Update stage and check for win
                        print(new_stage)
                        if new_stage == 1:  # Win condition
                            wins += 1
                            if wins >= target_wins:
                                try:
                                    is_group = await is_group_chat(group_id)
                                    if is_group:
                                        # For groups: use background bridge
                                        bot_comm.send_signal(
                                            group_id=str(group_id),
                                            game="stop",
                                            signal=str(wins),
                                            issue_number="0",
                                            current_stage=1,
                                            strategy="command"
                                        )
                                        await asyncio.sleep(1)
                                        bot_comm.send_signal(
                                            group_id=str(group_id),
                                            game="statistics",
                                            signal="command",
                                            issue_number="0",
                                            current_stage=1,
                                            strategy="command"
                                        )
                                        print(f"✅ Sent stop and statistics command codes to bot.py for group {group_id}")
                                    else:
                                        # For channels: send direct commands
                                        await app.send_message(group_id, f"/stop {wins}")
                                        await asyncio.sleep(1)
                                        await app.send_message(group_id, "/statistics")
                                        print(f"✅ Sent direct stop and statistics commands to channel {group_id}")
                                except Exception as e:
                                    print(f"Error sending stop/statistics commands: {e}")
                                break
                            pass
                            # await app.send_sticker(group_id, STICKERS[str(wins)]["file_id"])
                        elif new_stage == 0:
                            print(f"🚫 Max stages reached for group {group_id} - stopping signal generator")
                            # Send stop and statistics commands - same as win count reached
                            try:
                                is_group = await is_group_chat(group_id)
                                if is_group:
                                    # For groups: use background bridge
                                    bot_comm.send_signal(
                                        group_id=str(group_id),
                                        game="stop",
                                        signal="max_stages_reached",
                                        issue_number="0",
                                        current_stage=1,
                                        strategy="command"
                                    )
                                    await asyncio.sleep(1)
                                    bot_comm.send_signal(
                                        group_id=str(group_id),
                                        game="statistics",
                                        signal="command",
                                        issue_number="0",
                                        current_stage=1,
                                        strategy="command"
                                    )
                                    await app.send_message(group_id, "/stop")
                                    print(f"✅ Sent stop and statistics command codes to bot.py for group {group_id}")
                                else:
                                    # For channels: send direct commands
                                    await app.send_message(group_id, "/stop")
                                    await asyncio.sleep(1)
                                    await app.send_message(group_id, "/statistics")
                                    print(f"✅ Sent direct stop and statistics commands to channel {group_id}")
                            except Exception as e:
                                print(f"Error sending stop/statistics commands: {e}")
                            
                            # Call stop_signals_loss to properly stop and clean up signal generators
                            try:
                                await stop_signals_loss(app, group_id)
                                print(f"✅ Called stop_signals_loss for group {group_id}")
                            except Exception as e:
                                print(f"Error calling stop_signals_loss: {e}")
                            
                            # Send completion message for max stages
                            completion_msg = get_message_by_language(group_id, "max_stages_reached", "🛑 Maximum stages reached! Stopping signals.")
                            await app.send_message(group_id, completion_msg)
                            break
                        
                        current_stage = new_stage
                        last_issue = current_issue
                        
                        # Add 2-second delay after sending signal
                        print(f"DEBUG: Adding 2-second delay after sending signal")
                        await asyncio.sleep(2)
                    
                    await asyncio.sleep(1)  # Check every second
                else:
                    await asyncio.sleep(1)  # Wait if no results

            except asyncio.CancelledError:
                # Task was cancelled by stop button
                break
            except Exception as e:
                print(f"Error in dices random signal generator: {e}")
                await asyncio.sleep(1)
    finally:
        # Update group status in config
        cfg = load_config()
        if group_id in cfg["group_settings"]:
            cfg["group_settings"][group_id]["status"] = "OFF"
            save_config(cfg)
        # Remove task from signal_tasks (support both old and scheduler keys)
        for key, task in list(signal_tasks.items()):
            if (hasattr(task, 'group_id') and task.group_id == group_id) or key == group_id or key.startswith(f"{group_id}_"):
                del signal_tasks[key]
        # Only send completion message if we reached win count
        if wins >= win_count:
            completion_msg = get_message_by_language(group_id, "target_reached", "✅ Target of {win_count} wins reached! Stopping signals.", win_count=win_count)
            await app.send_message(group_id, completion_msg)

def check_blocks_formula_pattern(formula, last_results):
    """
    Check if the last results match the pattern in formula
    formula format: "bs_b" or multi-line like "bs_b\nsb_s" where:
    - First part (bs) is the pattern to match (will be reversed to match actual results)
    - After underscore (_) is the signal to send
    b = big, s = small
    """
    try:
        # Split formula into lines to handle multi-line formulas
        formula_lines = formula.strip().split('\n')
        
        for line in formula_lines:
            line = line.strip()
            if not line or '_' not in line:
                continue
                
            try:
                pattern, signal = line.split('_', 1)  # Split on first underscore only
                # Convert last results to string format (most recent first)
                results_str = ''
                for result in last_results:
                    if result and result.strip():
                        try:
                            # Convert to lowercase and remove extra spaces for easier matching
                            result_lower = result.lower().strip()
                            # Check if result contains 'big' or 'small' anywhere in the text
                            if 'big' in result_lower:
                                results_str += 'b'
                            elif 'small' in result_lower:
                                results_str += 's'
                            else:
                                print(f"Could not find Big/Small in result: {result}")
                                continue
                        except Exception as e:
                            print(f"Error parsing result {result}: {e}")
                            continue
                
                # Reverse the pattern to match actual results order
                reversed_pattern = pattern[::-1]  # This will convert "bs" to "sb"
                
                print(f"Checking blocks pattern: {reversed_pattern} against results: {results_str}")
                # Check if pattern matches
                if results_str == reversed_pattern:
                    return True, signal
            except Exception as e:
                print(f"Error processing formula line '{line}': {e}")
                continue
        
        return False, None
    except Exception as e:
        print(f"Error in check_blocks_formula_pattern: {e}")
        return False, None

async def send_blocks_signal_message_random(group_id, signal, issue_number, current_stage=1):
    """Send formatted blocks signal message to group - RANDOM STRATEGY FORMAT"""
    try:
        # Ensure numeric values
        issue_number = str(issue_number)
        # Keep current_stage as int for background API
        
        # Create the message
        message = f"{signal.upper()}x{current_stage}"

        # Send the message
        await app.send_message(group_id, message)
        
        # Only send background signals for groups (not channels)
        is_group = await is_group_chat(group_id)
        if is_group:
            # Send signal to trading bot via communication system
            try:
                bot_comm.send_signal(
                    group_id=group_id,
                    game="blocks",
                    signal=signal,
                    issue_number=issue_number,
                    current_stage=current_stage,
                    strategy="formula"
                )
                print(f"✅ Background signal sent for group {group_id}")
            except Exception as e:
                print(f"Error sending signal to trading bot: {e}")
        else:
            print(f"⏭️ Skipping background signal for channel {group_id}")
        

        
        # Wait until next minute
        wait_for_next_minute()
        
        # Start checking for results
        max_attempts = 3000  # Check for 30 seconds
        attempt = 0
        result = None
        
        while attempt < max_attempts:
            # Get the latest issue from the db
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute("SELECT issue FROM blocks_results ORDER BY timestamp DESC LIMIT 1")
            latest_issue_rec = c.fetchone()
            conn.close()
            
            # Check if the latest issue is newer than the one we sent a signal for
            if int(latest_issue_rec[0]) > int(issue_number):
                break
                
            attempt += 1
            await asyncio.sleep(1)  # Check every second
        
        # if result and result[0]:
        try:
            # Convert to lowercase and remove extra spaces for easier matching
            # Get latest result from database
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute("SELECT result FROM blocks_results ORDER BY timestamp DESC LIMIT 1")
            latest_result = c.fetchone()
            conn.close()
            print(latest_result)
            result_lower = latest_result[0].lower().strip()
            print(result_lower)
            # Check if result contains 'big' or 'small' anywhere in the text
            is_big = 'big' in result_lower
            actual_result = get_message_by_language(group_id, "result_big", "BIG   🔷") if is_big else get_message_by_language(group_id, "result_small", "SMALL   🔶")
            
            # Check if signal was correct
            is_win = (signal == "b" and is_big) or (signal == "s" and not is_big)
            
            # Send result message
            result_message = f"RESULT: {actual_result}"
            if signal == "b":
                signal = "Big"
            else:
                signal = "Small"
            # Send win/lose message
            if is_win:
                result_lower = latest_result[0].lower().strip()
                print(result_lower)
                # Check if result contains 'big' or 'small' anywhere in the text
                is_big = 'big' in result_lower
                actual_result = get_message_by_language(group_id, "signal_big", "BIG") if is_big else get_message_by_language(group_id, "signal_small", "SMALL")
                win_text = get_message_by_language(group_id, "result_win", "Win")
                # await app.send_message(group_id, f"📥 {get_message_by_language(group_id, 'result', 'Result')}: {actual_result}\n▫️ {get_message_by_language(group_id, 'buy', 'BUY')}: {signal} 🔸 {win_text}")
                # await app.send_message(group_id, "Win🎉")
                return 1  # Reset stage to 1 on win
            else:
                result_lower = latest_result[0].lower().strip()
                print(result_lower)
                # Check if result contains 'big' or 'small' anywhere in the text
                is_big = 'big' in result_lower
                get_message_by_language(group_id, "signal_big", "BIG") if is_big else get_message_by_language(group_id, "signal_small", "SMALL")
                lose_text = get_message_by_language(group_id, "result_lose", "Lose")
                # await app.send_message(group_id, f"📥 {get_message_by_language(group_id, 'result', 'Result')}: {actual_result}\n▫️ {get_message_by_language(group_id, 'buy', 'BUY')}: {signal} 🔸 {lose_text}")
                # Get max stages from config
                cfg = load_config()
                max_stages = 12  # Default
                if group_id in cfg["group_settings"]:
                    game_cfg = cfg["group_settings"][group_id].get("blocks", {})
                    max_stages = game_cfg.get("stages", 12)
                
                new_stage = int(current_stage) + 1
                if new_stage > max_stages:
                    max_stages_msg = get_message_by_language(group_id, "max_stages", "Maximum stages ({max_stages}) reached! Resetting...", max_stages=max_stages)
                    await app.send_message(group_id, max_stages_msg)
                    
                    # Send stop command when max stages reached - different approach for groups vs channels
                    try:
                        is_group = await is_group_chat(group_id)
                        if is_group:
                            # For groups: use background bridge
                            bot_comm.send_signal(
                                group_id=str(group_id),
                                game="stop",  # Command code for stop
                                signal="max_stages_reached",  # Stop command
                                issue_number="0",
                                current_stage=1,
                                strategy="command"
                            )
                            await app.send_message(group_id, "/stop")
                            print(f"✅ Sent stop command via background bridge for group {group_id} (max stages reached)")
                        else:
                            # For channels: send direct command
                            await app.send_message(group_id, "/stop")
                            print(f"✅ Sent stop command directly to channel {group_id} (max stages reached)")
                    except Exception as e:
                        print(f"Error sending stop command: {e}")
                    
                    return 0  # Reset to stage 1
                else:
                    return new_stage  # Add 1 to stage on loss
        except Exception as e:
            print(f"Error processing result: {e}")
            return int(current_stage)  # Return current stage on error
        return int(current_stage)  # Return current stage if no result
        
    except Exception as e:
        print(f"Error in send_blocks_signal_message: {e}")
        return int(current_stage)  # Return current stage on error

async def send_blocks_signal_message(group_id, signal, issue_number, current_stage=1, strategy="formula"):
    """Send formatted blocks signal message to group"""
    try:
        # Ensure numeric values
        issue_number = str(issue_number)
        # Keep current_stage as int for background API
        
        # Check if this is a group or channel to determine message format
        is_group = await is_group_chat(group_id)
        
        if is_group:
            # For groups: use compact format (background communication will handle issue numbers)
            message = f"{signal.upper()}x{current_stage}"
        else:
            # For channels: include issue number for precise result gating
            message = f"{signal.upper()}x{current_stage}_{issue_number}"
        
        # Send the message with error handling
        try:
            await app.send_message(group_id, message)
        except (ValueError, KeyError) as e:
            # Handle "Peer id invalid" error - bot is not in the group/channel
            print(f"🚫 Bot not in group/channel {group_id}: {e}")
            return int(current_stage)  # Return current stage on error
        except Exception as e:
            print(f"⚠️ Error sending signal to {group_id}: {e}")
            return int(current_stage)  # Return current stage on error
        
        # Only send background signals for groups (not channels)
        if is_group:
            # Send signal to trading bot via communication system
            try:
                bot_comm.send_signal(
                    group_id=group_id,
                    game="blocks",
                    signal=signal,
                    issue_number=issue_number,
                    current_stage=int(current_stage),
                    strategy=strategy
                )
                print(f"✅ Background signal sent for group {group_id}")
                gid = str(group_id)
                _ensure_session_stats_entry(gid)
                GROUP_SESSION_STATS[gid]["blocks"]["signals"] += 1
            except Exception as e:
                print(f"Error sending signal to trading bot: {e}")
        else:
            print(f"⏭️ Skipping background signal for channel {group_id}")
        
        # Wait until next minute
        wait_for_next_minute()
        
        # Start checking for results
        max_attempts = 3000  # Check for 30 seconds
        attempt = 0
        result = None
        
        while attempt < max_attempts:
            # Get the latest issue from the db
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute("SELECT issue FROM blocks_results ORDER BY timestamp DESC LIMIT 1")
            latest_issue_rec = c.fetchone()
            conn.close()
            
            # Check if the latest issue is newer than the one we sent a signal for
            if int(latest_issue_rec[0]) > int(issue_number):
                break
                
            attempt += 1
            await asyncio.sleep(1)  # Check every second
        
        # if result and result[0]:
        try:
            # Convert to lowercase and remove extra spaces for easier matching
            # Get latest result from database
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute("SELECT result FROM blocks_results ORDER BY timestamp DESC LIMIT 1")
            latest_result = c.fetchone()
            conn.close()
            print(latest_result)
            result_lower = latest_result[0].lower().strip()
            print(result_lower)
            # Check if result contains 'big' or 'small' anywhere in the text
            is_big = 'big' in result_lower
            actual_result = get_message_by_language(group_id, "result_big", "BIG   🔷") if is_big else get_message_by_language(group_id, "result_small", "SMALL   🔶")
            
            # Check if signal was correct
            is_win = (signal == "b" and is_big) or (signal == "s" and not is_big)
            
            # Send result message
            result_message = f"RESULT: {actual_result}"
            if signal == "b":
                    signal = "Big"
            else:
                signal = "Small"
            # Send win/lose message
            if is_win:
                result_lower = latest_result[0].lower().strip()
                print(result_lower)
                # Check if result contains 'big' or 'small' anywhere in the text
                is_big = 'big' in result_lower
                get_message_by_language(group_id, "signal_big", "BIG") if is_big else get_message_by_language(group_id, "signal_small", "SMALL")
                win_text = get_message_by_language(group_id, "result_win", "Win")
                # await app.send_message(group_id, f"📥 {get_message_by_language(group_id, 'result', 'Result')}: {actual_result}\n▫️ {get_message_by_language(group_id, 'buy', 'BUY')}: {signal} 🔸 {win_text}")
                # await app.send_message(group_id, "Win🎉")
                gid = str(group_id)
                _ensure_session_stats_entry(gid)
                GROUP_SESSION_STATS[gid]["blocks"]["wins"] += 1
                _append_history(gid, f"BLK: WIN | {actual_result}")
                return 1  # Reset stage to 1 on win
            else:
                result_lower = latest_result[0].lower().strip()
                print(result_lower)
                # Check if result contains 'big' or 'small' anywhere in the text
                is_big = 'big' in result_lower
                get_message_by_language(group_id, "signal_big", "BIG") if is_big else get_message_by_language(group_id, "signal_small", "SMALL")
                lose_text = get_message_by_language(group_id, "result_lose", "Lose")
                gid = str(group_id)
                _ensure_session_stats_entry(gid)
                GROUP_SESSION_STATS[gid]["blocks"]["losses"] += 1
                # We don't have stage progression here, just record
                _append_history(gid, f"BLK: LOSS | {actual_result}")
                # await app.send_message(group_id, f"📥 {get_message_by_language(group_id, 'result', 'Result')}: {actual_result}\n▫️ {get_message_by_language(group_id, 'buy', 'BUY')}: {signal} 🔸 {lose_text}")
                # Get max stages from config
                cfg = load_config()
                max_stages = 12  # Default
                if group_id in cfg["group_settings"]:
                    game_cfg = cfg["group_settings"][group_id].get("blocks", {})
                    max_stages = game_cfg.get("stages", 12)
                
                new_stage = int(current_stage) + 1
                if new_stage > max_stages:
                    max_stages_msg = get_message_by_language(group_id, "max_stages", "Maximum stages ({max_stages}) reached! Resetting...", max_stages=max_stages)
                    await app.send_message(group_id, max_stages_msg)
                    
                    # Send stop command when max stages reached - different approach for groups vs channels
                    try:
                        is_group = await is_group_chat(group_id)
                        if is_group:
                            # For groups: use background bridge
                            bot_comm.send_signal(
                                group_id=str(group_id),
                                game="stop",  # Command code for stop
                                signal="max_stages_reached",  # Stop command
                                issue_number="0",
                                current_stage=1,
                                strategy="command"
                            )
                            await app.send_message(group_id, "/stop")
                            print(f"✅ Sent stop command via background bridge for group {group_id} (max stages reached)")
                        else:
                            # For channels: send direct command
                            await app.send_message(group_id, "/stop")
                            print(f"✅ Sent stop command directly to channel {group_id} (max stages reached)")
                    except Exception as e:
                        print(f"Error sending stop command: {e}")
                    
                    return 0  # Reset to stage 1
                else:
                    return new_stage  # Add 1 to stage on loss
        except Exception as e:
            print(f"Error processing result: {e}")
            return int(current_stage)  # Return current stage on error
        return int(current_stage)  # Return current stage if no result
        
    except Exception as e:
        print(f"Error in send_blocks_signal_message: {e}")
        return int(current_stage)  # Return current stage on error

async def blocks_formula_signal_generator(group_id, formula, stop_event):
    """Background task to generate blocks signals based on formula"""
    last_results = []  # Store last results
    last_issue = None  # Track last issue to avoid duplicates
    current_stage = 1  # Track current stage
    wins = 0  # Track number of wins
    win_count = 10  # Default win count
    
    try:
        target_wins = 10
        try:
            cfg = load_config()
            gid = str(group_id)
            target_wins = int(cfg.get("group_settings", {}).get(gid, {}).get("blocks", {}).get("win_count", 10))
        except Exception:
            pass
        # Get win count from config
        cfg = load_config()
        if group_id in cfg["group_settings"]:
            game_cfg = cfg["group_settings"][group_id].get("blocks", {})
            win_count = game_cfg.get("win_count", 10)
        
        # Get pattern length from formula
        pattern_length = len(formula.split('_')[0])
        print(f"Blocks pattern length from formula: {pattern_length}")
        
        while wins < win_count:
            if stop_event.is_set():
                print(f"Stop signal received for group {group_id}")
                break
            try:
                # Check if we should stop
                if group_id in signal_tasks and signal_tasks[group_id].get("stop_event", None) and signal_tasks[group_id]["stop_event"].is_set():
                    print(f"Stop signal received for group {group_id}")
                    break

                # Get latest result from database
                conn = sqlite3.connect(DB_FILE)
                c = conn.cursor()
                # Fetch results based on pattern length
                c.execute(f"SELECT issue, result FROM blocks_results ORDER BY timestamp DESC LIMIT {pattern_length}")
                results = c.fetchall()
                conn.close()
                
                if len(results) >= pattern_length:
                    current_issue = results[0][0]
                    
                    # Only process if we have a new issue
                    if current_issue != last_issue:
                        # Update last results (most recent first)
                        last_results = [r[1] for r in results]
                        
                        # Check if pattern matches (last results match our pattern)
                        pattern_matches, signal = check_blocks_formula_pattern(formula, last_results)
                        
                        if pattern_matches:
                            print(f"Pattern matched! Last results: {last_results}, Sending signal: {signal}")
                            # Send signal and get new stage
                            new_stage = await send_blocks_signal_message_random(group_id, signal, current_issue, current_stage)
                            
                            # Update stage and check for win
                            if new_stage == 1:  # Win condition
                                wins += 1
                                if wins >= target_wins:
                                    try:
                                        is_group = await is_group_chat(group_id)
                                        if is_group:
                                            # For groups: use background bridge
                                            bot_comm.send_signal(
                                                group_id=str(group_id),
                                                game="stop",
                                                signal=str(wins),
                                                issue_number="0",
                                                current_stage=1,
                                                strategy="command"
                                            )
                                            await asyncio.sleep(1)
                                            bot_comm.send_signal(
                                                group_id=str(group_id),
                                                game="statistics",
                                                signal="command",
                                                issue_number="0",
                                                current_stage=1,
                                                strategy="command"
                                            )
                                            print(f"✅ Sent stop and statistics command codes to bot.py for group {group_id}")
                                        else:
                                            # For channels: send direct commands
                                            await app.send_message(group_id, "/stop")
                                            await asyncio.sleep(1)
                                            await app.send_message(group_id, "/statistics")
                                            print(f"✅ Sent direct stop and statistics commands to channel {group_id}")
                                    except Exception as e:
                                        print(f"Error sending stop/statistics commands: {e}")
                                    break
                                pass
                                # await app.send_sticker(group_id, STICKERS[str(wins)]["file_id"])
                            elif new_stage == 0:
                                print(f"🚫 Max stages reached for group {group_id} - stopping signal generator")
                                # Send stop and statistics commands - same as win count reached
                                try:
                                    is_group = await is_group_chat(group_id)
                                    if is_group:
                                        # For groups: use background bridge
                                        bot_comm.send_signal(
                                            group_id=str(group_id),
                                            game="stop",
                                            signal="max_stages_reached",
                                            issue_number="0",
                                            current_stage=1,
                                            strategy="command"
                                        )
                                        await asyncio.sleep(1)
                                        bot_comm.send_signal(
                                            group_id=str(group_id),
                                            game="statistics",
                                            signal="command",
                                            issue_number="0",
                                            current_stage=1,
                                            strategy="command"
                                        )
                                        await app.send_message(group_id, "/stop")
                                        print(f"✅ Sent stop and statistics command codes to bot.py for group {group_id}")
                                    else:
                                        # For channels: send direct commands
                                        await app.send_message(group_id, "/stop")
                                        await asyncio.sleep(1)
                                        await app.send_message(group_id, "/statistics")
                                        print(f"✅ Sent direct stop and statistics commands to channel {group_id}")
                                except Exception as e:
                                    print(f"Error sending stop/statistics commands: {e}")
                                
                                # Call stop_signals_loss to properly stop and clean up signal generators
                                try:
                                    await stop_signals_loss(app, group_id)
                                    print(f"✅ Called stop_signals_loss for group {group_id}")
                                except Exception as e:
                                    print(f"Error calling stop_signals_loss: {e}")
                                
                                # Send completion message for max stages
                                completion_msg = get_message_by_language(group_id, "max_stages_reached", "🛑 Maximum stages reached! Stopping signals.")
                                await app.send_message(group_id, completion_msg)
                                break
                            
                            current_stage = new_stage
                            last_issue = current_issue
                            
                            # Add 2-second delay after sending signal
                            print(f"DEBUG: Adding 2-second delay after sending signal")
                            await asyncio.sleep(2)
                        
                    await asyncio.sleep(1)  # Check every second
                else:
                    await asyncio.sleep(1)  # Wait if not enough results

            except asyncio.CancelledError:
                # Task was cancelled by stop button
                break
            except Exception as e:
                print(f"Error in blocks formula signal generator: {e}")
                await asyncio.sleep(1)
    finally:
        # Update group status in config
        cfg = load_config()
        if group_id in cfg["group_settings"]:
            cfg["group_settings"][group_id]["status"] = "OFF"
            save_config(cfg)
        # Remove task from signal_tasks (support both old and scheduler keys)
        for key, task in list(signal_tasks.items()):
            if (hasattr(task, 'group_id') and task.group_id == group_id) or key == group_id or key.startswith(f"{group_id}_"):
                del signal_tasks[key]
        # Only send completion message if we reached win count
        if wins >= win_count:
            completion_msg = get_message_by_language(group_id, "target_reached", "✅ Target of {win_count} wins reached! Stopping signals.", win_count=win_count)
            await app.send_message(group_id, completion_msg)

async def blocks_random_signal_generator(group_id, win_count, stop_event):
    """Background task to generate random blocks signals"""
    current_stage = 1  # Track current stage
    wins = 0  # Track number of wins
    last_issue = None  # Track last issue to avoid duplicates
    
    try:
        target_wins = win_count if isinstance(win_count, int) and win_count > 0 else 10
        while wins < win_count:
            if stop_event.is_set():
                print(f"Stop signal received for group {group_id}")
                break
            try:
                # Check if we should stop
                if group_id in signal_tasks and signal_tasks[group_id].get("stop_event", None) and signal_tasks[group_id]["stop_event"].is_set():
                    print(f"Stop signal received for group {group_id}")
                    break

                # Get latest result from database
                conn = sqlite3.connect(DB_FILE)
                c = conn.cursor()
                c.execute("SELECT issue FROM blocks_results ORDER BY timestamp DESC LIMIT 1")
                result = c.fetchone()
                conn.close()

                if result:
                    current_issue = result[0]
                    
                    # Only process if we have a new issue
                    if current_issue != last_issue:
                        # Randomly choose between big and small
                        signal = random.choice(['b', 's'])
                        
                        # Send signal and get new stage
                        new_stage = await send_blocks_signal_message_random(group_id, signal, current_issue, current_stage)
                        
                        # Update stage and check for win
                        if new_stage == 1:  # Win condition
                            wins += 1
                            if wins >= target_wins:
                                try:
                                    is_group = await is_group_chat(group_id)
                                    if is_group:
                                        # For groups: use background bridge
                                        bot_comm.send_signal(
                                            group_id=str(group_id),
                                            game="stop",
                                            signal=str(wins),
                                            issue_number="0",
                                            current_stage=1,
                                            strategy="command"
                                        )
                                        await asyncio.sleep(1)
                                        bot_comm.send_signal(
                                            group_id=str(group_id),
                                            game="statistics",
                                            signal="command",
                                            issue_number="0",
                                            current_stage=1,
                                            strategy="command"
                                        )
                                        print(f"✅ Sent stop and statistics command codes to bot.py for group {group_id}")
                                    else:
                                        # For channels: send direct commands
                                        await app.send_message(group_id, f"/stop {wins}")
                                        await asyncio.sleep(1)
                                        await app.send_message(group_id, "/statistics")
                                        print(f"✅ Sent direct stop and statistics commands to channel {group_id}")
                                except Exception as e:
                                    print(f"Error sending stop/statistics commands: {e}")
                                break
                            pass
                            # await app.send_sticker(group_id, STICKERS[str(wins)]["file_id"])
                        elif new_stage == 0:
                            print(f"🚫 Max stages reached for group {group_id} - stopping signal generator")
                            # Send stop and statistics commands - same as win count reached
                            try:
                                is_group = await is_group_chat(group_id)
                                if is_group:
                                    # For groups: use background bridge
                                    bot_comm.send_signal(
                                        group_id=str(group_id),
                                        game="stop",
                                        signal="max_stages_reached",
                                        issue_number="0",
                                        current_stage=1,
                                        strategy="command"
                                    )
                                    await asyncio.sleep(1)
                                    bot_comm.send_signal(
                                        group_id=str(group_id),
                                        game="statistics",
                                        signal="command",
                                        issue_number="0",
                                        current_stage=1,
                                        strategy="command"
                                    )
                                    await app.send_message(group_id, "/stop")
                                    print(f"✅ Sent stop and statistics command codes to bot.py for group {group_id}")
                                else:
                                    # For channels: send direct commands
                                    await app.send_message(group_id, "/stop")
                                    await asyncio.sleep(1)
                                    await app.send_message(group_id, "/statistics")
                                    print(f"✅ Sent direct stop and statistics commands to channel {group_id}")
                            except Exception as e:
                                print(f"Error sending stop/statistics commands: {e}")
                            
                            # Call stop_signals_loss to properly stop and clean up signal generators
                            try:
                                await stop_signals_loss(app, group_id)
                                print(f"✅ Called stop_signals_loss for group {group_id}")
                            except Exception as e:
                                print(f"Error calling stop_signals_loss: {e}")
                            
                            # Send completion message for max stages
                            completion_msg = get_message_by_language(group_id, "max_stages_reached", "🛑 Maximum stages reached! Stopping signals.")
                            await app.send_message(group_id, completion_msg)
                            break
                        
                        current_stage = new_stage
                        last_issue = current_issue
                    
                    await asyncio.sleep(1)  # Check every second
                else:
                    await asyncio.sleep(1)  # Wait if no results

            except asyncio.CancelledError:
                # Task was cancelled by stop button
                break
            except Exception as e:
                print(f"Error in blocks random signal generator: {e}")
                await asyncio.sleep(1)
    finally:
        # Update group status in config
        cfg = load_config()
        if group_id in cfg["group_settings"]:
            cfg["group_settings"][group_id]["status"] = "OFF"
            save_config(cfg)
        # Remove task from signal_tasks (support both old and scheduler keys)
        for key, task in list(signal_tasks.items()):
            if (hasattr(task, 'group_id') and task.group_id == group_id) or key == group_id or key.startswith(f"{group_id}_"):
                del signal_tasks[key]
        # Only send completion message if we reached win count
        if wins >= win_count:
            completion_msg = get_message_by_language(group_id, "target_reached", "✅ Target of {win_count} wins reached! Stopping signals.", win_count=win_count)
            await app.send_message(group_id, completion_msg)

def check_formula_pattern(formula, last_results):
    """
    Check if the last results match ANY pattern in formula
    formula format: "rg_r" or multi-line like "rg_r\ngg_g\nrgrrgr_r" where:
    - First part (rg, gg, rgrrgr) is the pattern to match (will be reversed to match actual results)
    - After underscore (_) is the signal to send
    r = red, g = green
    - Each line can have different lengths
    - Bot checks ALL patterns and returns first match
    """
    try:
        # Split formula into lines to handle multi-line formulas
        formula_lines = formula.strip().split('\n')
        
        for line in formula_lines:
            line = line.strip()
            if not line or '_' not in line:
                continue
                
            try:
                pattern, signal = line.split('_', 1)  # Split on first underscore only
                pattern_length = len(pattern)
                
                # Check if we have enough results for this pattern
                if len(last_results) < pattern_length:
                    print(f"Not enough results for pattern '{pattern}' (need {pattern_length}, have {len(last_results)})")
                    continue
                
                # Convert last results to string format (most recent first, limited to pattern length)
                results_str = ''
                for i in range(pattern_length):
                    result = last_results[i]
                    if result and result.strip():
                        try:
                            # Convert to lowercase and remove extra spaces for easier matching
                            result_lower = result.lower().strip()
                            # Check if result contains 'red' or 'green' anywhere in the text
                            if 'red' in result_lower:
                                results_str += 'r'
                            elif 'green' in result_lower:
                                results_str += 'g'
                            else:
                                print(f"Could not find Red/Green in result: {result}")
                                continue
                        except Exception as e:
                            print(f"Error parsing result {result}: {e}")
                            continue
                
                # Reverse the pattern to match actual results order
                reversed_pattern = pattern[::-1]  # This will convert "rg" to "gr"
                
                print(f"Checking pattern: {reversed_pattern} (length: {pattern_length}) against results: {results_str}")
                # Check if pattern matches
                if results_str == reversed_pattern:
                    print(f"✅ Pattern matched! '{reversed_pattern}' = '{results_str}', sending signal: {signal}")
                    return True, signal
                else:
                    print(f"❌ Pattern mismatch: '{reversed_pattern}' ≠ '{results_str}'")
            except Exception as e:
                print(f"Error processing formula line '{line}': {e}")
                continue
        
        print(f"❌ No patterns matched from formula: {formula}")
        return False, None
    except Exception as e:
        print(f"Error in check_formula_pattern: {e}")
        return False, None

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

async def is_group_chat(chat_id):
    """Check if the given chat_id is a group (not a channel)"""
    try:
        # Try to get chat information
        chat = await app.get_chat(chat_id)
        print(f"DEBUG: Chat {chat_id} type: {chat.type}")
        
        # Use proper ChatType enum comparison
        is_group = chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]
        print(f"DEBUG: Chat {chat_id} is_group: {is_group}")
        return is_group
    except Exception as e:
        print(f"Error checking chat type for {chat_id}: {e}")
        # Default to True (group) if we can't determine
        print(f"DEBUG: Defaulting to group for {chat_id}")
        return True

async def send_signal_message(group_id, signal, issue_number, current_stage=1, strategy="formula"):
    """Send formatted signal message to group"""
    try:
        # Ensure numeric values are strings
        issue_number = str(issue_number)
        current_stage = str(current_stage)
        
        # Check if this is a group or channel to determine message format
        is_group = await is_group_chat(group_id)
        
        if is_group:
            # For groups: use compact format (background communication will handle issue numbers)
            message = f"{signal.upper()}x{current_stage}"
        else:
            # For channels: include issue number for precise result gating
            message = f"{signal.upper()}x{current_stage}_{issue_number}"
        
        # Send the message with error handling
        try:
            await app.send_message(group_id, message)
        except (ValueError, KeyError) as e:
            # Handle "Peer id invalid" error - bot is not in the group/channel
            print(f"🚫 Bot not in group/channel {group_id}: {e}")
            return int(current_stage)  # Return current stage on error
        except Exception as e:
            print(f"⚠️ Error sending signal to {group_id}: {e}")
            return int(current_stage)  # Return current stage on error
        
        # Only send background signals for groups (not channels)
        if is_group:
            # Send signal to trading bot via communication system
            try:
                bot_comm.send_signal(
                    group_id=group_id,
                    game="red_green",
                    signal=signal,
                    issue_number=issue_number,
                    current_stage=int(current_stage),
                    strategy=strategy
                )
                print(f"✅ Background signal sent for group {group_id}")
                # Update session stats: count signals
                gid = str(group_id)
                _ensure_session_stats_entry(gid)
                GROUP_SESSION_STATS[gid]["red_green"]["signals"] += 1
            except Exception as e:
                print(f"Error sending signal to trading bot: {e}")
        else:
            print(f"⏭️ Skipping background signal for channel {group_id}")
        
        # Wait until next minute
        wait_for_next_minute()
        
        # Start checking for results
        max_attempts = 30  # Check for 30 seconds
        attempt = 0
        result = None
        
        while attempt < max_attempts:
            # Get the actual result
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            # Get the latest result for this issue
            c.execute("""
                SELECT color, issue 
                FROM red_green_results 
                ORDER BY timestamp DESC 
                LIMIT 1
            """)
            result = c.fetchone()
            print(f"Result: {result}")
            conn.close()
            
            if result and result[0]:
                # Verify this is the latest result by checking timestamp
                conn = sqlite3.connect(DB_FILE)
                c = conn.cursor()
                c.execute("""
                    SELECT timestamp 
                    FROM red_green_results 
                    WHERE issue = ? 
                    ORDER BY timestamp DESC 
                    LIMIT 1
                """, (issue_number,))
                latest_timestamp = c.fetchone()[0]
                print(f"Latest timestamp: {latest_timestamp}")
                conn.close()
                
                # Only process if this is the latest result
                print(f"Result: {result}", f"Issue: {issue_number}")
                if result[1] > issue_number:
                    break
                
            attempt += 1
            await asyncio.sleep(1)  # Check every second
        
        if result and result[0]:
            try:
                # Convert to lowercase and remove extra spaces for easier matching
                conn = sqlite3.connect(DB_FILE)
                c = conn.cursor()
                c.execute("""
                SELECT value, color, issue
                FROM red_green_results 
                ORDER BY timestamp DESC 
                LIMIT 1
            """)
                latest_result = c.fetchone()
                print(f"Latest result: {latest_result}")
                conn.close()
                result_lower = latest_result[1].lower().strip()
                # Check for specific number rules first
                try:
                    value_num = int(latest_result[0])  # latest_result[0] is the value number
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
                actual_result = get_message_by_language(group_id, "result_red", "RED   🔴") if is_red else get_message_by_language(group_id, "result_green", "GREEN   🟢")
                
                # Check if signal was correct
                is_win = (signal == "r" and is_red) or (signal == "g" and not is_red)
                
                # Send result message
                result_message = f"RESULT: {actual_result}"
                if signal == "r":
                    signal = get_message_by_language(group_id, "signal_red", "Red")
                else:
                    signal = get_message_by_language(group_id, "signal_green", "Green")
                
                # Send win/lose message
                if is_win:
                    win_text = get_message_by_language(group_id, "result_win", "Win")
                    # await app.send_message(group_id, f"📥 {get_message_by_language(group_id, 'result', 'Result')}: {latest_result[0]}, {actual_result}\n▫️ {get_message_by_language(group_id, 'buy', 'BUY')}: {signal} 🔸 {win_text}")
                    # Send sticker for win count
                    # if str(current_stage) in STICKERS:
                    #     await app.send_sticker(group_id, STICKERS[str(current_stage)]["file_id"])
                    # Stats + history update
                    gid = str(group_id)
                    _ensure_session_stats_entry(gid)
                    GROUP_SESSION_STATS[gid]["red_green"]["wins"] += 1
                    _append_history(gid, f"RG: WIN | {actual_result} | stage->{current_stage}")
                    return 1  # Reset stage to 1 on win
                else:
                    lose_text = get_message_by_language(group_id, "result_lose", "Lose")
                    # await app.send_message(group_id, f"📥 {get_message_by_language(group_id, 'result', 'Result')}: {latest_result[0]}, {actual_result}\n▫️ {get_message_by_language(group_id, 'buy', 'BUY')}: {signal} 🔸 {lose_text}")
                    # Get max stages from config
                    cfg = load_config()
                    max_stages = 12  # Default
                    if group_id in cfg["group_settings"]:
                        game_cfg = cfg["group_settings"][group_id].get("red_green", {})
                        max_stages = game_cfg.get("stages", 12)
                    
                    new_stage = int(current_stage) + 1
                    if new_stage > max_stages:
                        max_stages_msg = get_message_by_language(group_id, "max_stages", "Maximum stages ({max_stages}) reached! Resetting...", max_stages=max_stages)
                        await app.send_message(group_id, max_stages_msg)
                        
                        # Send stop command when max stages reached - different approach for groups vs channels
                        try:
                            is_group = await is_group_chat(group_id)
                            if is_group:
                                # For groups: use background bridge
                                bot_comm.send_signal(
                                    group_id=str(group_id),
                                    game="stop",  # Command code for stop
                                    signal="max_stages_reached",  # Stop command
                                    issue_number="0",
                                    current_stage=1,
                                    strategy="command"
                                )
                                await app.send_message(group_id, "/stop")
                                print(f"✅ Sent stop command via background bridge for group {group_id} (max stages reached)")
                            else:
                                # For channels: send direct command
                                await app.send_message(group_id, "/stop")
                                print(f"✅ Sent stop command directly to channel {group_id} (max stages reached)")
                            await stop_signals_loss(app, group_id)
                            print(f"✅ Called stop_signals_loss for group {group_id}")
                        except Exception as e:
                            print(f"Error sending stop command: {e}")
                        
                        gid = str(group_id)
                        _ensure_session_stats_entry(gid)
                        GROUP_SESSION_STATS[gid]["red_green"]["losses"] += 1
                        _append_history(gid, f"RG: LOSS | {actual_result} | stage->reset")
                        return 0  # Reset to stage 1
                    else:
                        gid = str(group_id)
                        _ensure_session_stats_entry(gid)
                        GROUP_SESSION_STATS[gid]["red_green"]["losses"] += 1
                        _append_history(gid, f"RG: LOSS | {actual_result} | stage->{new_stage}")
                        return new_stage  # Add 1 to stage on loss
            except Exception as e:
                print(f"Error processing result: {e}")
                return int(current_stage)  # Return current stage on error
        return int(current_stage)  # Return current stage if no result
        
    except Exception as e:
        print(f"Error in send_signal_message: {e}")
        return int(current_stage)  # Return current stage on error

async def random_signal_generator(group_id, win_count, stop_event):
    """Background task to generate random signals"""
    current_stage = 1  # Track current stage
    wins = 0  # Track number of wins
    last_issue = None  # Track last issue to avoid duplicates
    
    try:
        target_wins = win_count if isinstance(win_count, int) and win_count > 0 else 10
        while wins < win_count:
            if stop_event.is_set():
                print(f"Stop signal received for group {group_id}")
                break
            try:
                # Check if we should stop
                if group_id in signal_tasks and signal_tasks[group_id].get("stop_event", None) and signal_tasks[group_id]["stop_event"].is_set():
                    print(f"Stop signal received for group {group_id}")
                    break

                # Get latest result from database
                conn = sqlite3.connect(DB_FILE)
                c = conn.cursor()
                c.execute("SELECT issue FROM red_green_results ORDER BY timestamp DESC LIMIT 1")
                result = c.fetchone()
                conn.close()

                if result:
                    current_issue = result[0]
                    
                    # Only process if we have a new issue
                    if current_issue != last_issue:
                        # Randomly choose between red and green
                        signal = random.choice(['r', 'g'])
                        
                        # Send signal and get new stage
                        new_stage = await send_signal_message(group_id, signal, current_issue, current_stage, strategy="random")
                        
                        # Update stage and check for win
                        print(f"New stage: {new_stage}")
                        if new_stage == 1:  # Win condition
                            wins += 1
                            if wins >= target_wins:
                                try:
                                    is_group = await is_group_chat(group_id)
                                    if is_group:
                                        # For groups: use background bridge
                                        bot_comm.send_signal(
                                            group_id=str(group_id),
                                            game="stop",
                                            signal=str(wins),
                                            issue_number="0",
                                            current_stage=1,
                                            strategy="command"
                                        )
                                        await asyncio.sleep(1)
                                        bot_comm.send_signal(
                                            group_id=str(group_id),
                                            game="statistics",
                                            signal="command",
                                            issue_number="0",
                                            current_stage=1,
                                            strategy="command"
                                        )
                                        print(f"✅ Sent stop and statistics command codes to bot.py for group {group_id}")
                                    else:
                                        # For channels: send direct commands
                                        await app.send_message(group_id, f"/stop {wins}")
                                        await asyncio.sleep(1)
                                        await app.send_message(group_id, "/statistics")
                                        print(f"✅ Sent direct stop and statistics commands to channel {group_id}")
                                except Exception as e:
                                    print(f"Error sending stop/statistics commands: {e}")
                                break
                            # Send sticker for win count
                            # if str(wins) in STICKERS:
                            #     # await app.send_sticker(group_id, STICKERS[str(wins)]["file_id"])
                            #     pass
                            elif new_stage == 0:
                                print(f"🚫 Max stages reached for group {group_id} - stopping signal generator")
                                # Send stop and statistics commands - same as win count reached
                                try:
                                    is_group = await is_group_chat(group_id)
                                    if is_group:
                                        # For groups: use background bridge
                                        bot_comm.send_signal(
                                            group_id=str(group_id),
                                            game="stop",
                                            signal="max_stages_reached",
                                            issue_number="0",
                                            current_stage=1,
                                            strategy="command"
                                        )
                                        await asyncio.sleep(1)
                                        bot_comm.send_signal(
                                            group_id=str(group_id),
                                            game="statistics",
                                            signal="command",
                                            issue_number="0",
                                            current_stage=1,
                                            strategy="command"
                                        )
                                        await app.send_message(group_id, "/stop")
                                        print(f"✅ Sent stop and statistics command codes to bot.py for group {group_id}")
                                    else:
                                        # For channels: send direct commands
                                        await app.send_message(group_id, "/stop")
                                        await asyncio.sleep(1)
                                        await app.send_message(group_id, "/statistics")
                                        print(f"✅ Sent direct stop and statistics commands to channel {group_id}")
                                except Exception as e:
                                    print(f"Error sending stop/statistics commands: {e}")
                                
                                # Call stop_signals_loss to properly stop and clean up signal generators
                                try:
                                    await stop_signals_loss(app, group_id)
                                    print(f"✅ Called stop_signals_loss for group {group_id}")
                                except Exception as e:
                                    print(f"Error calling stop_signals_loss: {e}")
                                
                                # Send completion message for max stages
                                completion_msg = get_message_by_language(group_id, "max_stages_reached", "🛑 Maximum stages reached! Stopping signals.")
                                await app.send_message(group_id, completion_msg)
                                break
                        
                        current_stage = new_stage
                        last_issue = current_issue
                        
                        # Add 2-second delay after sending signal
                        print(f"DEBUG: Adding 2-second delay after sending signal")
                        await asyncio.sleep(2)
                    
                    await asyncio.sleep(1)  # Check every second
                else:
                    await asyncio.sleep(1)  # Wait if no results

            except asyncio.CancelledError:
                # Task was cancelled by stop button
                break
            except Exception as e:
                print(f"Error in random signal generator: {e}")
                await asyncio.sleep(1)
    finally:
        # Update group status in config
        cfg = load_config()
        if group_id in cfg["group_settings"]:
            cfg["group_settings"][group_id]["status"] = "OFF"
            save_config(cfg)
        # Remove task from signal_tasks (support both old and scheduler keys)
        for key, task in list(signal_tasks.items()):
            if (hasattr(task, 'group_id') and task.group_id == group_id) or key == group_id or key.startswith(f"{group_id}_"):
                del signal_tasks[key]
        # Only send completion message if we reached win count
        if wins >= win_count:
            completion_msg = get_message_by_language(group_id, "target_reached", "✅ Target of {win_count} wins reached! Stopping signals.", win_count=win_count)
            await app.send_message(group_id, completion_msg)

async def formula_signal_generator(group_id, formula, stop_event):
    """Background task to generate signals based on formula"""
    last_results = []  # Store last results
    last_issue = None  # Track last issue to avoid duplicates
    current_stage = 1  # Track current stage
    wins = 0  # Track number of wins
    win_count = 10  # Default win count

    try:
        target_wins = 10
        try:
            cfg = load_config()
            gid = str(group_id)
            target_wins = int(cfg.get("group_settings", {}).get(gid, {}).get("red_green", {}).get("win_count", 10))
        except Exception:
            pass
        # Get win count from config
        cfg = load_config()
        if group_id in cfg["group_settings"]:
            game_cfg = cfg["group_settings"][group_id].get("red_green", {})
            win_count = game_cfg.get("win_count", 10)

        # Get the maximum pattern length from all formula lines to ensure we fetch enough results
        formula_lines = formula.strip().split('\n')
        max_pattern_length = 0
        for line in formula_lines:
            line = line.strip()
            if line and '_' in line:
                pattern = line.split('_')[0]
                max_pattern_length = max(max_pattern_length, len(pattern))

        print(f"Maximum pattern length from formula: {max_pattern_length}")
        print(f"Formula lines: {formula_lines}")

        while wins < win_count:
            if stop_event.is_set():
                print(f"Stop signal received for group {group_id}")
                break
            try:
                # Get latest result from database
                conn = sqlite3.connect(DB_FILE)
                c = conn.cursor()
                # Fetch results based on maximum pattern length to cover all patterns
                c.execute(f"SELECT issue, color FROM red_green_results ORDER BY timestamp DESC LIMIT {max_pattern_length}")
                results = c.fetchall()
                conn.close()

                if len(results) >= max_pattern_length:
                    current_issue = results[0][0]

                    # Only process if we have a new issue
                    if current_issue != last_issue:
                        # Update last results (most recent first)
                        last_results = [r[1] for r in results]

                        # Check if pattern matches (last results match our pattern)
                        pattern_matches, signal = check_formula_pattern(formula, last_results)

                        if pattern_matches:
                            print(f"Pattern matched! Last results: {last_results}, Sending signal: {signal}")
                            # Send signal and get new stage
                            new_stage = await send_signal_message(group_id, signal, current_issue, current_stage, strategy="formula")

                            # Update stage and check for win
                            if new_stage == 1:  # Win condition
                                wins += 1
                                if wins >= target_wins:
                                    try:
                                        is_group = await is_group_chat(group_id)
                                        if is_group:
                                            await app.send_message(group_id, f"/stop")
                                            # For groups: use background bridge
                                            bot_comm.send_signal(
                                                group_id=str(group_id),
                                                game="stop",
                                                signal=str(wins),
                                                issue_number="0",
                                                current_stage=1,
                                                strategy="command"
                                            )
                                            await asyncio.sleep(1)
                                            await app.send_message(group_id, "/statistics")
                                            bot_comm.send_signal(
                                                group_id=str(group_id),
                                                game="statistics",
                                                signal="command",
                                                issue_number="0",
                                                current_stage=1,
                                                strategy="command"
                                            )
                                            print(f"✅ Sent stop and statistics command codes to bot.py for group {group_id}")
                                        else:
                                            # For channels: send direct commands
                                            await app.send_message(group_id, "/stop")
                                            await asyncio.sleep(1)
                                            await app.send_message(group_id, "/statistics")
                                            print(f"✅ Sent direct stop and statistics commands to channel {group_id}")
                                    except Exception as e:
                                        print(f"Error sending stop/statistics commands: {e}")
                                    break
                                # Send sticker for win count
                                # if str(wins) in STICKERS:
                                #     await app.send_sticker(group_id, STICKERS[str(wins)]["file_id"])
                            elif new_stage == 0:
                                print(f"🚫 Max stages reached for group {group_id} - stopping signal generator")
                                # Send stop and statistics commands - same as win count reached
                                try:
                                    is_group = await is_group_chat(group_id)
                                    if is_group:
                                        await app.send_message(group_id, f"/stop")
                                        # For groups: use background bridge
                                        bot_comm.send_signal(
                                            group_id=str(group_id),
                                            game="stop",
                                            signal="max_stages_reached",
                                            issue_number="0",
                                            current_stage=1,
                                            strategy="command"
                                        )
                                        await asyncio.sleep(1)
                                        await app.send_message(group_id, "/statistics")
                                        bot_comm.send_signal(
                                            group_id=str(group_id),
                                            game="statistics",
                                            signal="command",
                                            issue_number="0",
                                            current_stage=1,
                                            strategy="command"
                                        )
                                        await app.send_message(group_id, "/stop")
                                        print(f"✅ Sent stop and statistics command codes to bot.py for group {group_id}")
                                    else:
                                        # For channels: send direct commands
                                        await app.send_message(group_id, "/stop")
                                        await asyncio.sleep(1)
                                        await app.send_message(group_id, "/statistics")
                                        print(f"✅ Sent direct stop and statistics commands to channel {group_id}")
                                except Exception as e:
                                    print(f"Error sending stop/statistics commands: {e}")

                                # Call stop_signals_loss to properly stop and clean up signal generators
                                try:
                                    await stop_signals_loss(app, group_id)
                                    print(f"✅ Called stop_signals_loss for group {group_id}")
                                except Exception as e:
                                    print(f"Error calling stop_signals_loss: {e}")

                                # Send completion message for max stages
                                completion_msg = get_message_by_language(group_id, "max_stages_reached", "🛑 Maximum stages reached! Stopping signals.")
                                await app.send_message(group_id, completion_msg)
                                break

                            current_stage = new_stage
                            last_issue = current_issue

                        await asyncio.sleep(1)  # Check every second
                    else:
                        await asyncio.sleep(1)  # Wait if not enough results

            except asyncio.CancelledError:
                # Task was cancelled by stop button
                break
            except Exception as e:
                print(f"Error in formula signal generator: {e}")
                await asyncio.sleep(1)
    finally:
        # Update group status in config
        cfg = load_config()
        if group_id in cfg["group_settings"]:
            cfg["group_settings"][group_id]["status"] = "OFF"
            save_config(cfg)
        # Remove task from signal_tasks (support both old and scheduler keys)
        for key, task in list(signal_tasks.items()):
            if (hasattr(task, 'group_id') and task.group_id == group_id) or key == group_id or key.startswith(f"{group_id}_"):
                del signal_tasks[key]
        # Only send completion message if we reached win count
        if wins >= win_count:
            completion_msg = get_message_by_language(group_id, "target_reached", "✅ Target of {win_count} wins reached! Stopping signals.", win_count=win_count)
            await app.send_message(group_id, completion_msg)

def run_signal_task_in_thread(task_func, *args):
    """Run a signal task in a separate thread"""
    def run_in_thread():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(task_func(*args))
        finally:
            loop.close()
    
    thread = threading.Thread(target=run_in_thread)
    thread.daemon = True  # Make thread daemon so it exits when main program exits
    thread.start()
    return thread

@app.on_message(filters.command("stop"))
async def stop_signals_command(client, message):
    """Handle /stop command"""
    group_id = str(message.chat.id)
    
    # Find and stop ALL tasks for this group (any game, any strategy)
    task_found = False
    keys_to_delete = set()
    
    print(f"🔍 Looking for tasks to stop for group {group_id}")
    print(f"🔍 Current signal_tasks: {list(signal_tasks.keys())}")
    
    for key, task_info in list(signal_tasks.items()):
        if isinstance(key, str) and key.startswith(f"{group_id}_"):
            task_found = True
            print(f"🛑 Found task to stop: {key}")
            
            # Stop the task
            if "stop_event" in task_info:
                task_info["stop_event"].set()
                print(f"✅ Set stop event for task {key}")
            
            # Wait for thread to finish
            if "thread" in task_info and task_info["thread"].is_alive():
                print(f"⏳ Waiting for thread {key} to finish...")
                task_info["thread"].join(timeout=5)
                if task_info["thread"].is_alive():
                    print(f"⚠️ Thread {key} did not finish within timeout")
                else:
                    print(f"✅ Thread {key} finished successfully")
            
            # Mark for deletion
            keys_to_delete.add(key)

    # Delete stopped tasks
    for key in keys_to_delete:
        if key in signal_tasks:
            del signal_tasks[key]
            print(f"🗑️ Deleted task {key} from signal_tasks")

    if not task_found:
        await message.reply(get_message_by_language(group_id, "no_generator", "❌ No signal generator is running for this group!"))
        return
    
    # Update group status in config
    cfg = load_config()
    if group_id in cfg["group_settings"]:
        cfg["group_settings"][group_id]["status"] = "OFF"
        save_config(cfg)
    
    await message.reply(get_message_by_language(group_id, "stopping", "🛑 Stopping all signal generators for this group..."))
    print(f"✅ Successfully stopped all tasks for group {group_id}")

async def stop_signals_loss(client, group_id):
    """Handle /stop command for a group/channel by sending messages directly to the group/channel."""
    
    # Find and stop ALL tasks for this group (any game, any strategy)
    task_found = False
    keys_to_delete = set()
    
    print(f"🔍 Looking for tasks to stop for group {group_id}")
    print(f"🔍 Current signal_tasks: {list(signal_tasks.keys())}")
    
    for key, task_info in list(signal_tasks.items()):
        if isinstance(key, str) and key.startswith(f"{group_id}_"):
            task_found = True
            print(f"🛑 Found task to stop: {key}")
            
            # Stop the task
            if "stop_event" in task_info:
                task_info["stop_event"].set()
                print(f"✅ Set stop event for task {key}")
            
            # Wait for thread to finish
            if "thread" in task_info and task_info["thread"].is_alive():
                print(f"⏳ Waiting for thread {key} to finish...")
                task_info["thread"].join(timeout=5)
                if task_info["thread"].is_alive():
                    print(f"⚠️ Thread {key} did not finish within timeout")
                else:
                    print(f"✅ Thread {key} finished successfully")
            
            # Mark for deletion
            keys_to_delete.add(key)

    # Delete stopped tasks
    for key in keys_to_delete:
        if key in signal_tasks:
            del signal_tasks[key]
            print(f"🗑️ Deleted task {key} from signal_tasks")

    if not task_found:
        await client.send_message(
            int(group_id),
            get_message_by_language(group_id, "no_generator", "❌ No signal generator is running for this group!")
        )
        return
    
    # Update group status in config
    cfg = load_config()
    if group_id in cfg["group_settings"]:
        cfg["group_settings"][group_id]["status"] = "OFF"
        save_config(cfg)
    
    await client.send_message(
        int(group_id),
        get_message_by_language(group_id, "stopping", "🛑 Stopping all signal generators for this group...")
    )
    print(f"✅ Successfully stopped all tasks for group {group_id}")
    
# @app.on_message(filters.command("red_green_ran"))
async def start_red_green_random_signals(client, message):
    """Handle /red_green_ran command in groups - starts with random strategy"""
    group_id = str(message.chat.id)
    
    # Get settings from config
    cfg = load_config()
    group_cfg = cfg["group_settings"].get(group_id, {})
    game_cfg = group_cfg.get("red_green", {})
    win_count = game_cfg.get("win_count", 10)  # Default to 10 if not set
    
    # Check if a task is already running for this group
    for key, task in signal_tasks.items():
        if isinstance(key, str) and (key == group_id or key.startswith(f"{group_id}_")) and "thread" in task and task["thread"].is_alive():
            await message.reply(get_message_by_language(group_id, "already_running", "❌ Signal generator is already running for this group!"))
            return
    
    await message.reply(get_message_by_language(group_id, "red_green_start", "Starting RED-GREEN 1MIN strategy.\nPlease wait a moment."))
    # Send the actual command to the group
    await client.send_message(message.chat.id, "/red_green")
    await client.send_message(message.chat.id, get_message_by_language(group_id, "red_green_instructions", """👉 Use the following control characters:
▫️ B: Big
▫️ S: Small
▫️ G: Green
▫️ R: Red
▫️ P: Purple
▫️ O: Odd
▫️ E: Even
▫️ 0–9: Used to indicate bet level or amount

✒️ Example:

Bx1 (Bet on Big, with bet level 1)

Gx3 (Bet on Green, with bet level 3)"""))
    await client.send_message(message.chat.id, get_message_by_language(group_id, "red_green_ready", "Ready to receive commands..."))
    
    # Start random signal generator in a separate thread
    stop_event = threading.Event()
    thread = run_signal_task_in_thread(random_signal_generator, group_id, win_count, stop_event)
    signal_tasks[group_id] = {"thread": thread, "stop_event": stop_event}
    
    # Update group status
    cfg = load_config()
    if group_id in cfg["group_settings"]:
        cfg["group_settings"][group_id]["status"] = "ON"
        save_config(cfg)

# @app.on_message(filters.command("red_green"))
async def start_red_green_signals(client, message):
    """Handle /red_green command in groups - starts with formula strategy"""
    group_id = str(message.chat.id)
    
    # Get settings from config
    cfg = load_config()
    group_cfg = cfg["group_settings"].get(group_id, {})
    game_cfg = group_cfg.get("red_green", {})
    formula = game_cfg.get("formula", "")
    
    # Check if a task is already running for this group
    for key, task in signal_tasks.items():
        if isinstance(key, str) and (key == group_id or key.startswith(f"{group_id}_")) and "thread" in task and task["thread"].is_alive():
            await message.reply(get_message_by_language(group_id, "already_running", "❌ Signal generator is already running for this group!"))
            return
    
    # Check if formula exists
    if not formula:
        await message.reply(get_message_by_language(group_id, "no_formula", "❌ No formula configured for this group. Please set a formula first."))
        return
    
    await message.reply(get_message_by_language(group_id, "red_green_start", "Starting RED-GREEN 1MIN strategy.\nPlease wait a moment."))
    # Send the actual command to the group
    await client.send_message(message.chat.id, "/red_green")
    await client.send_message(message.chat.id, get_message_by_language(group_id, "red_green_instructions", """👉 Use the following control characters:
▫️ B: Big
▫️ S: Small
▫️ G: Green
▫️ R: Red
▫️ P: Purple
▫️ O: Odd
▫️ E: Even
▫️ 0–9: Used to indicate bet level or amount

✒️ Example:

Bx1 (Bet on Big, with bet level 1)

Gx3 (Bet on Green, with bet level 3)"""))
    await client.send_message(message.chat.id, get_message_by_language(group_id, "red_green_ready", "Ready to receive commands..."))
    
    # Start formula signal generator in a separate thread
    stop_event = threading.Event()
    thread = run_signal_task_in_thread(formula_signal_generator, group_id, formula, stop_event)
    signal_tasks[group_id] = {"thread": thread, "stop_event": stop_event}
    
    # Update group status
    cfg = load_config()
    if group_id in cfg["group_settings"]:
        cfg["group_settings"][group_id]["status"] = "ON"
        save_config(cfg)

# @app.on_message(filters.command("blocks_ran"))
async def start_blocks_random_signals(client, message):
    """Handle /blocks_ran command in groups - starts with random strategy"""
    group_id = str(message.chat.id)
    
    # Get settings from config
    cfg = load_config()
    group_cfg = cfg["group_settings"].get(group_id, {})
    game_cfg = group_cfg.get("blocks", {})
    win_count = game_cfg.get("win_count", 10)  # Default to 10 if not set
    
    # Check if a task is already running for this group
    for key, task in signal_tasks.items():
        if isinstance(key, str) and (key == group_id or key.startswith(f"{group_id}_")) and "thread" in task and task["thread"].is_alive():
            await message.reply("❌ Signal generator is already running for this group!")
            return
    
    await message.reply(get_message_by_language(group_id, "blocks_start", "Starting BLOCKS 1MIN strategy.\nPlease wait a moment."))
    # Send the actual command to the group
    await client.send_message(message.chat.id, "/blocks")
    await client.send_message(message.chat.id, get_message_by_language(group_id, "blocks_instructions", """👉 Use the following control characters:
▫️ B: Big
▫️ S: Small
▫️ G: Green
▫️ R: Red
▫️ P: Purple
▫️ O: Odd
▫️ E: Even
▫️ 0–9: Used to indicate bet level or amount

✒️ Example:

Bx1 (Bet on Big, with bet level 1)

Gx3 (Bet on Green, with bet level 3)"""))
    await client.send_message(message.chat.id, get_message_by_language(group_id, "blocks_ready", "Ready to receive commands..."))
    
    # Start random signal generator in a separate thread
    stop_event = threading.Event()
    thread = run_signal_task_in_thread(blocks_random_signal_generator, group_id, win_count, stop_event)
    signal_tasks[group_id] = {"thread": thread, "stop_event": stop_event}
    
    # Update group status
    cfg = load_config()
    if group_id in cfg["group_settings"]:
        cfg["group_settings"][group_id]["status"] = "ON"
        save_config(cfg)
    
# @app.on_message(filters.command("blocks"))
async def start_blocks_signals(client, message):
    """Handle /blocks command in groups - starts with formula strategy"""
    group_id = str(message.chat.id)
    
    # Get settings from config
    cfg = load_config()
    group_cfg = cfg["group_settings"].get(group_id, {})
    game_cfg = group_cfg.get("blocks", {})
    formula = game_cfg.get("formula", "")
    
    # Check if a task is already running for this group
    for key, task in signal_tasks.items():
        if isinstance(key, str) and (key == group_id or key.startswith(f"{group_id}_")) and "thread" in task and task["thread"].is_alive():
            await message.reply("❌ Signal generator is already running for this group!")
            return
    
    # Check if formula exists
    if not formula:
        await message.reply("❌ No formula configured for this group. Please set a formula first.")
        return
    
    await message.reply(get_message_by_language(group_id, "blocks_start", "Starting BLOCKS 1MIN strategy.\nPlease wait a moment."))
    await client.send_message(message.chat.id, get_message_by_language(group_id, "blocks_instructions", """👉 Use the following control characters:
▫️ B: Big
▫️ S: Small
▫️ G: Green
▫️ R: Red
▫️ P: Purple
▫️ O: Odd
▫️ E: Even
▫️ 0–9: Used to indicate bet level or amount

✒️ Example:

Bx1 (Bet on Big, with bet level 1)

Gx3 (Bet on Green, with bet level 3)"""))
    await client.send_message(message.chat.id, get_message_by_language(group_id, "blocks_ready", "Ready to receive commands..."))
    
    # Start formula signal generator in a separate thread
    stop_event = threading.Event()
    thread = run_signal_task_in_thread(blocks_formula_signal_generator, group_id, formula, stop_event)
    signal_tasks[group_id] = {"thread": thread, "stop_event": stop_event}
    
    # Update group status
    cfg = load_config()
    if group_id in cfg["group_settings"]:
        cfg["group_settings"][group_id]["status"] = "ON"
        save_config(cfg)

# @app.on_message(filters.command("dices_ran"))
async def start_dices_random_signals(client, message):
    """Handle /dices_ran command in groups - starts with random strategy"""
    group_id = str(message.chat.id)
    
    # Get settings from config
    cfg = load_config()
    group_cfg = cfg["group_settings"].get(group_id, {})
    game_cfg = group_cfg.get("dices", {})
    win_count = game_cfg.get("win_count", 10)  # Default to 10 if not set
    
    # Check if a task is already running for this group
    for key, task in signal_tasks.items():
        if isinstance(key, str) and (key == group_id or key.startswith(f"{group_id}_")) and "thread" in task and task["thread"].is_alive():
            await message.reply("❌ Signal generator is already running for this group!")
            return
    
    await message.reply(get_message_by_language(group_id, "dices_start", "Starting DICES 1MIN strategy.\nPlease wait a moment."))
    await client.send_message(message.chat.id, get_message_by_language(group_id, "dices_instructions", """👉 Use the following control characters:
▫️ B: Big
▫️ S: Small
▫️ G: Green
▫️ R: Red
▫️ P: Purple
▫️ O: Odd
▫️ E: Even
▫️ 0–9: Used to indicate bet level or amount

✒️ Example:

Bx1 (Bet on Big, with bet level 1)

Gx3 (Bet on Green, with bet level 3)"""))
    await client.send_message(message.chat.id, get_message_by_language(group_id, "dices_ready", "Ready to receive commands..."))
    
    # Start random signal generator in a separate thread
    stop_event = threading.Event()
    thread = run_signal_task_in_thread(dices_random_signal_generator, group_id, win_count, stop_event)
    signal_tasks[group_id] = {"thread": thread, "stop_event": stop_event}
    
    
    # Update group status
    cfg = load_config()
    if group_id in cfg["group_settings"]:
        cfg["group_settings"][group_id]["status"] = "ON"
        save_config(cfg)
    

# @app.on_message(filters.command("dices"))
async def start_dices_signals(client, message):
    """Handle /dices command in groups - starts with formula strategy"""
    group_id = str(message.chat.id)
    
    # Get settings from config
    cfg = load_config()
    group_cfg = cfg["group_settings"].get(group_id, {})
    game_cfg = group_cfg.get("dices", {})
    formula = game_cfg.get("formula", "")
    
    # Check if a task is already running for this group
    for key, task in signal_tasks.items():
        if isinstance(key, str) and (key == group_id or key.startswith(f"{group_id}_")) and "thread" in task and task["thread"].is_alive():
            await message.reply("❌ Signal generator is already running for this group!")
            return
    
    # Check if formula exists
    if not formula:
        await message.reply("❌ No formula configured for this group. Please set a formula first.")
        return
    
    await message.reply(get_message_by_language(group_id, "dices_start", "Starting DICES 1MIN strategy.\nPlease wait a moment."))
    await client.send_message(message.chat.id, get_message_by_language(group_id, "dices_instructions", """👉 Use the following control characters:
▫️ B: Big
▫️ S: Small
▫️ G: Green
▫️ R: Red
▫️ P: Purple
▫️ O: Odd
▫️ E: Even
▫️ 0–9: Used to indicate bet level or amount

✒️ Example:

Bx1 (Bet on Big, with bet level 1)

Gx3 (Bet on Green, with bet level 3)"""))
    await client.send_message(message.chat.id, get_message_by_language(group_id, "dices_ready", "Ready to receive commands..."))
    
    
    # Start formula signal generator in a separate thread
    stop_event = threading.Event()
    thread = run_signal_task_in_thread(dices_formula_signal_generator, group_id, formula, stop_event)
    signal_tasks[group_id] = {"thread": thread, "stop_event": stop_event}
    
    # Update group status
    cfg = load_config()
    if group_id in cfg["group_settings"]:
        cfg["group_settings"][group_id]["status"] = "ON"
        save_config(cfg)


# --- DB INIT ---
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    # DICES
    c.execute("""
        CREATE TABLE IF NOT EXISTS dices_results (
            issue TEXT PRIMARY KEY,
            result TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    # Remove extra columns from dices_results
    c.execute("PRAGMA table_info(dices_results)")
    cols = [row[1] for row in c.fetchall()]
    for col in cols:
        if col not in ("issue", "result", "timestamp"):
            try:
                c.execute(f"ALTER TABLE dices_results DROP COLUMN {col}")
            except Exception:
                pass
    # BLOCKS
    c.execute("""
        CREATE TABLE IF NOT EXISTS blocks_results (
            issue TEXT PRIMARY KEY,
            result TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    c.execute("PRAGMA table_info(blocks_results)")
    cols = [row[1] for row in c.fetchall()]
    for col in cols:
        if col not in ("issue", "result", "timestamp"):
            try:
                c.execute(f"ALTER TABLE blocks_results DROP COLUMN {col}")
            except Exception:
                pass
    # RED_GREEN
    c.execute("""
        CREATE TABLE IF NOT EXISTS red_green_results (
            issue TEXT PRIMARY KEY,
            value TEXT,
            color TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    c.execute("PRAGMA table_info(red_green_results)")
    cols = [row[1] for row in c.fetchall()]
    for col in cols:
        if col not in ("issue", "value", "color", "timestamp"):
            try:
                c.execute(f"ALTER TABLE red_green_results DROP COLUMN {col}")
            except Exception:
                pass
    conn.commit()
    conn.close()

def parse_cron_time(timer_str):
    """Parse timer string like '10:00' or '6:25' or '24/7' or multiple times like '06:00-20:00-12:00' and return list of (hour, minute) tuples or None for always-on."""
    if timer_str is None:
        return None
    timer_str = timer_str.strip()
    if timer_str == "24/7":
        return None
    
    # Check if it's multiple times separated by dashes
    if "-" in timer_str:
        times = []
        for time_part in timer_str.split("-"):
            time_part = time_part.strip()
            m = re.match(r"^(\d{1,2}):(\d{2})$", time_part)
            if m:
                hour, minute = int(m.group(1)), int(m.group(2))
                times.append((hour, minute))
        return times if times else None
    
    # Single time format
    m = re.match(r"^(\d{1,2}):(\d{2})$", timer_str)
    if m:
        hour, minute = int(m.group(1)), int(m.group(2))
        return [(hour, minute)]
    return None

def should_start_now(timer_str, group_id=None, game=None, strategy=None):
    """Return True if the current time matches any of the timer_str times (or always-on)."""
    cron_times = parse_cron_time(timer_str)
    if cron_times is None:
        return False  # 24/7 means don't auto-start, only manual
    
    now = datetime.now()
    for hour, minute in cron_times:
        # Check if current time is within the same minute as the scheduled time
        # Since scheduler now runs every 10 seconds, we can be more precise
        if now.hour == hour and now.minute == minute:
            # Only trigger once per minute to avoid multiple starts
            # Use seconds to ensure we trigger early in the minute
            if now.second < 30:  # Trigger within first 30 seconds of the minute
                # Create a unique key for this timer to prevent duplicate triggers
                if group_id and game and strategy:
                    timer_key = f"{group_id}_{game}_{strategy}_{hour:02d}:{minute:02d}"
                    current_minute = f"{now.hour:02d}:{now.minute:02d}"
                    
                    # Check if we already triggered this timer this minute
                    if timer_key in last_timer_triggers:
                        last_trigger = last_timer_triggers[timer_key]
                        if last_trigger == current_minute:
                            return False  # Already triggered this minute
                    
                    # Mark this timer as triggered for this minute
                    last_timer_triggers[timer_key] = current_minute
                    print(f"[TIMER] Triggering timer {timer_key} at {current_minute}")
                
                return True
    return False

async def handle_timer_start(group_id, game, strategy):
    """Handle timer-based start with proper status updates and admin notifications"""
    try:
        # Log timer-based start
        print(f"⏰ [TIMER TRIGGERED] Group ID: {group_id}, Game: {game}, Strategy: {strategy}")
        print(f"⏰ [TIMER TRIGGERED] Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Check if ANY signal generator is already running for this group
        if is_signal_generator_running_for_group(group_id):
            print(f"[SCHEDULER] Signal generator already running for group {group_id}, skipping timer start")
            return
        
        # Get settings from config
        cfg = load_config()
        group_cfg = cfg["group_settings"].get(group_id, {})
        game_cfg = group_cfg.get(game, {})
        formula = game_cfg.get("formula", "")
        win_count = game_cfg.get("win_count", 10)
        
        # Check if formula exists for formula strategy
        if strategy == "self" and not formula:
            print(f"[SCHEDULER] No formula configured for group {group_id}, skipping timer start")
            return
        
        # IMMEDIATELY change group status to ON and add to starting phase
        try:
            # Update group status to ON immediately
            if group_id in cfg["group_settings"]:
                cfg["group_settings"][group_id]["status"] = "ON"
                save_config(cfg)
                print(f"[SCHEDULER] Group {group_id} status immediately updated to ON")
            
            # Add group to starting phase
            groups_in_starting_phase[group_id] = {
                "game": game,
                "strategy": strategy,
                "start_time": time.time(),
                "stop_event": threading.Event()
            }
            print(f"[SCHEDULER] Group {group_id} added to starting phase")
            
            # Send immediate confirmation message to admin and store for countdown updates
            admin_messages = {}
            try:
                # Get admin IDs to send notification
                admin_ids = get_admin_ids()
                for admin_id in admin_ids:
                    try:
                        immediate_msg = await app.send_message(
                            admin_id,
                            f"⏰ **Timer Triggered!** ⏰\n\n"
                            f"🚀 **Starting {get_game_name(game).title()} Signals!** 🚀\n\n"
                            f"📺 **Target:** Group `{group_id}`\n"
                            f"🎮 **Game:** {get_game_name(game).title()}\n"
                            f"📊 **Strategy:** {strategy.title()}\n"
                            f"🔄 **Status:** ON\n\n"
                            f"⏰ **Next step:** Sending game command and waiting 5 minutes...\n\n"
                            f"⚠️ **Note:** You can stop this operation at any time!",
                            reply_markup=InlineKeyboardMarkup([[
                                InlineKeyboardButton("⏹️ Stop Signals", callback_data=f"stop_{group_id}_{game}")
                            ]])
                        )
                        admin_messages[admin_id] = immediate_msg
                        print(f"[SCHEDULER] Sent timer notification to admin {admin_id}")
                    except Exception as e:
                        print(f"[SCHEDULER] Error sending notification to admin {admin_id}: {e}")
            except Exception as e:
                print(f"[SCHEDULER] Error sending admin notifications: {e}")
            
        except Exception as e:
            print(f"[SCHEDULER] Error updating group status: {e}")
            return
        
        # Send the same initial messages as the manual start button
        try:
            # Check if this is a group or channel to determine sending behavior
            is_group = await is_group_chat(group_id)
            
            if game == "red_green":
                if is_group:
                    # For groups: send direct command + background signal
                    await app.send_message(int(group_id), "/red_green")
                    print(f"[SCHEDULER] Sent /red_green command to group {group_id}")
                    # Send command code to bot.py immediately
                    bot_comm.send_signal(
                        group_id=str(group_id),
                        game="cr",  # Command code for red_green
                        signal="command",
                        issue_number="0",
                        current_stage=1,
                        strategy="command"
                    )
                    print(f"[SCHEDULER] Sent red_green command code to bot.py")
                else:
                    # For channels: only send background signal (no direct command)
                    bot_comm.send_signal(
                        group_id=str(group_id),
                        game="cr",  # Command code for red_green
                        signal="command",
                        issue_number="0",
                        current_stage=1,
                        strategy="command"
                    )
                    print(f"[SCHEDULER] Sent red_green command code to bot.py for channel {group_id}")
                # Add 2 second delay to give bot.py time to send reply messages
                await asyncio.sleep(2)
            elif game == "blocks":
                if is_group:
                    # For groups: send direct command + background signal
                    await app.send_message(int(group_id), "/blocks")
                    print(f"[SCHEDULER] Sent /blocks command to group {group_id}")
                    # Send command code to bot.py immediately
                    bot_comm.send_signal(
                        group_id=str(group_id),
                        game="cb",  # Command code for blocks
                        signal="command",
                        issue_number="0",
                        current_stage=1,
                        strategy="command"
                    )
                    print(f"[SCHEDULER] Sent blocks command code to bot.py")
                else:
                    # For channels: only send background signal (no direct command)
                    bot_comm.send_signal(
                        group_id=str(group_id),
                        game="cb",  # Command code for blocks
                        signal="command",
                        issue_number="0",
                        current_stage=1,
                        strategy="command"
                    )
                    print(f"[SCHEDULER] Sent blocks command code to bot.py for channel {group_id}")
                # Add 2 second delay to give bot.py time to send reply messages
                await asyncio.sleep(2)
            elif game == "dices":
                if is_group:
                    # For groups: send direct command + background signal
                    await app.send_message(int(group_id), "/dices")
                    print(f"[SCHEDULER] Sent /dices command to group {group_id}")
                    # Send command code to bot.py immediately
                    bot_comm.send_signal(
                        group_id=str(group_id),
                        game="cd",  # Command code for dices
                        signal="command",
                        issue_number="0",
                        current_stage=1,
                        strategy="command"
                    )
                    print(f"[SCHEDULER] Sent dices command code to bot.py")
                else:
                    # For channels: only send background signal (no direct command)
                    bot_comm.send_signal(
                        group_id=str(group_id),
                        game="cd",  # Command code for dices
                        signal="command",
                        issue_number="0",
                        current_stage=1,
                        strategy="command"
                    )
                    print(f"[SCHEDULER] Sent dices command code to bot.py for channel {group_id}")
                # Add 2 second delay to give bot.py time to send reply messages
                await asyncio.sleep(2)
            
            # Now sending game commands before starting signals
            # This delay happens for BOTH groups and channels after all commands are sent
            print(f"[SCHEDULER] Waiting 5 minutes after sending game commands before starting signals for {'group' if is_group else 'channel'} {group_id}")
            
            # Send a message to inform users about the delay
            try:
                chat_type = "group" if is_group else "channel"
                delay_message = f"⏰ **Game Command Sent Successfully!** ⏰\n\n🎮 **Game:** {get_game_name(game).title()}\n📺 **Target:** {chat_type.title()}\n⏱️ **Delay:** 5 minutes before signals start\n\n📝 **What happens now:**\n1️⃣ Game command has been sent to the {chat_type}\n2️⃣ Bot is now waiting 5 minutes\n3️⃣ Signals will start automatically after delay\n\n🔄 **Please wait...**\n⚠️ **You can still stop this operation!**"
                
                # Send to admin
                admin_ids = get_admin_ids()
                for admin_id in admin_ids:
                    try:
                        await app.send_message(admin_id, delay_message)
                    except Exception as e:
                        print(f"[SCHEDULER] Error sending delay message to admin {admin_id}: {e}")
            except Exception as e:
                print(f"[SCHEDULER] Failed to send delay message: {e}")
            
            # Wait 5 minutes with progress updates and cancellation checks
            print(f"[SCHEDULER] Starting 5-minute countdown for {'group' if is_group else 'channel'} {group_id}")
            for remaining in range(300, 0, -60):  # Update every minute (60 seconds)
                # Check if user stopped the operation
                if group_id not in groups_in_starting_phase:
                    print(f"[SCHEDULER] Group {group_id} was stopped during countdown")
                    return
                
                minutes_left = remaining // 60
                try:
                    progress_message = f"⏰ **Countdown in Progress...** ⏰\n\n⏱️ **Time remaining:** {minutes_left} minute{'s' if minutes_left > 1 else ''}\n🎮 **Game:** {get_game_name(game).title()}\n📺 **Target:** {chat_type.title()}\n📊 **Strategy:** {strategy.title()}\n\n🔄 **Signals will start automatically...**\n⚠️ **You can still stop this operation!**"
                    
                    # Edit the stored messages in place for each admin
                    for admin_id, message in admin_messages.items():
                        try:
                            await message.edit_text(progress_message)
                        except Exception as e:
                            print(f"[SCHEDULER] Error updating progress message for admin {admin_id}: {e}")
                except Exception as e:
                    print(f"[SCHEDULER] Failed to update progress message: {e}")
                
                if remaining > 60:  # Don't sleep on the last iteration
                    # Sleep in smaller chunks to check for cancellation
                    for _ in range(6):  # Check every 10 seconds
                        if group_id not in groups_in_starting_phase:
                            print(f"[SCHEDULER] Group {group_id} was stopped during countdown")
                            return
                        await asyncio.sleep(10)
            
            # Final countdown (last minute)
            for _ in range(6):  # Check every 10 seconds
                if group_id not in groups_in_starting_phase:
                    print(f"[SCHEDULER] Group {group_id} was stopped during countdown")
                    return
                await asyncio.sleep(10)
            
            # Check one final time before starting
            if group_id not in groups_in_starting_phase:
                print(f"[SCHEDULER] Group {group_id} was stopped during countdown")
                return
            
            print(f"[SCHEDULER] 5-minute delay completed, now starting signals for {'group' if is_group else 'channel'} {group_id}")
            
            # Send completion message by editing the existing message
            try:
                completion_message = f"✅ **Delay Completed!** ✅\n\n🎯 **Starting signals now for:** {get_game_name(game).title()}\n📺 **Target:** {chat_type.title()}\n📊 **Strategy:** {strategy.title()}\n\n🚀 **Signals are now active!**"
                
                # Edit the stored messages in place for each admin
                for admin_id, message in admin_messages.items():
                    try:
                        await message.edit_text(completion_message)
                    except Exception as e:
                        print(f"[SCHEDULER] Error updating completion message for admin {admin_id}: {e}")
            except Exception as e:
                print(f"[SCHEDULER] Failed to send completion message: {e}")
            
            # Remove from starting phase and start actual signal generation
            if group_id in groups_in_starting_phase:
                # Store the stop_event before removing from starting phase
                stop_event = groups_in_starting_phase[group_id]["stop_event"]
                del groups_in_starting_phase[group_id]
                print(f"[SCHEDULER] Group {group_id} removed from starting phase, starting signals")
            else:
                # If somehow not in starting phase, create a new stop event
                stop_event = threading.Event()
                print(f"[SCHEDULER] Group {group_id} not in starting phase, created new stop event")
            
            # Mark session start for this group/channel
            SESSION_START_TS[str(group_id)] = int(time.time())
            _ensure_session_stats_entry(str(group_id))
            
            # Now start the actual signal generation
            if strategy == "self":
                # Formula strategy
                if game == "red_green":
                    thread = run_signal_task_in_thread(formula_signal_generator, group_id, formula, stop_event)
                elif game == "blocks":
                    thread = run_signal_task_in_thread(blocks_formula_signal_generator, group_id, formula, stop_event)
                elif game == "dices":
                    thread = run_signal_task_in_thread(dices_formula_signal_generator, group_id, formula, stop_event)
            else:
                # Random strategy
                if game == "red_green":
                    thread = run_signal_task_in_thread(random_signal_generator, group_id, win_count, stop_event)
                elif game == "blocks":
                    thread = run_signal_task_in_thread(blocks_random_signal_generator, group_id, win_count, stop_event)
                elif game == "dices":
                    thread = run_signal_task_in_thread(dices_random_signal_generator, group_id, win_count, stop_event)
            
            # Add to signal tasks
            task_key = f"{group_id}_{game}_{strategy}"
            signal_tasks[task_key] = {"thread": thread, "stop_event": stop_event}
            print(f"[SCHEDULER] Started {game} {strategy} signal generation for group {group_id}")
            
        except Exception as e:
            print(f"[SCHEDULER] Error in timer start process: {e}")
            # Clean up on error
            if group_id in groups_in_starting_phase:
                del groups_in_starting_phase[group_id]
    
    except Exception as e:
        print(f"[SCHEDULER] Error in handle_timer_start: {e}")

async def scheduler_loop():
    """Background scheduler to start signals at the right time for each group/game/strategy."""
    while True:
        try:
            cfg = load_config()
            for group_id, group_cfg in cfg.get("group_settings", {}).items():
                for game in ALL_GAMES:
                    game_cfg = group_cfg.get(game, {})
                    # Formula strategy
                    timer_formula = game_cfg.get("timer_formula", "24/7")
                    if should_start_now(timer_formula, group_id, game, "self"):
                        # Only start if not already running
                        task_key = f"{group_id}_{game}_self"
                        if task_key not in signal_tasks:
                            print(f"[SCHEDULER] Timer triggered for {game} formula strategy in group {group_id}")
                            await handle_timer_start(group_id, game, "self")
                    
                    # Random strategy
                    timer_random = game_cfg.get("timer_random", "24/7")
                    if should_start_now(timer_random, group_id, game, "random"):
                        task_key = f"{group_id}_{game}_random"
                        if task_key not in signal_tasks:
                            print(f"[SCHEDULER] Timer triggered for {game} random strategy in group {group_id}")
                            await handle_timer_start(group_id, game, "random")
        except Exception as e:
            print(f"[SCHEDULER] Error: {e}")
        await asyncio.sleep(5)  # Check every 5 seconds for more precise timing

def run_scheduler_in_thread():
    """Wrapper to run the async scheduler in a thread"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(scheduler_loop())
    except Exception as e:
        print(f"[SCHEDULER THREAD] Error: {e}")
    finally:
        loop.close()

@app.on_callback_query(filters.regex("^already_running$"))
async def already_running_cb(client, cb: CallbackQuery):
    """Handle clicks on the disabled start button when group is already running"""
    user_id = cb.from_user.id
    username = cb.from_user.username or "No username"
    first_name = cb.from_user.first_name or "No first name"
    last_name = cb.from_user.last_name or ""
    
    # Log already running button click
    print(f"⏸️ [ALREADY RUNNING BUTTON CLICKED] User ID: {user_id}, Username: @{username}, Name: {first_name} {last_name}")
    print(f"⏸️ [ALREADY RUNNING BUTTON CLICKED] User tried to start signals but they were already running")
    
    await cb.answer("⏸️ Signals are already running for this group! Use the stop button to stop them first.", show_alert=True)

@app.on_callback_query(filters.regex(r"^status_(.+)_(.+)$"))
async def status_cb(client, cb: CallbackQuery):
    group_id, game = cb.data.split("_", 2)[1:]
    cfg = load_config()
    group_cfg = cfg["group_settings"].get(group_id, {})
    game_cfg = group_cfg.get(game, {})
    game_name = get_game_name(game)
    
    # Check if there's an active task for this specific game
    has_active_task = False
    for key, task in signal_tasks.items():
        if isinstance(key, str) and key.startswith(f"{group_id}_{game}_"):
            if "thread" in task and task["thread"].is_alive():
                has_active_task = True
                break
    
    # Also check if group is in starting phase
    is_in_starting_phase = group_id in groups_in_starting_phase
    
    # Determine final status: show ON if there are actual active tasks OR if in starting phase
    final_status = "ON" if (has_active_task or is_in_starting_phase) else "OFF"
    status_display = "🟢 ON" if final_status == "ON" else "🔴 OFF"
    
    try:
        await cb.message.edit_text(
            f"<b>Status for {game_name} in Group:</b> <code>{group_id}</code>\n\n"
            f"<b>Status:</b> {status_display}\n"
            f"<b>Config Status:</b> <code>{group_cfg.get('status', 'OFF')}</code>\n"
            f"<b>Active Task:</b> {'Yes' if has_active_task else 'No'}\n"
            f"<b>Selected Strategy:</b> <code>{game_cfg.get('strategy', 'random')}</code>\n"
            f"<b>Assigned Formula:</b> <code>{game_cfg.get('formula', '')}</code>\n"
            f"<b>Stages:</b> <code>{game_cfg.get('stages', 7)}</code>\n"
            f"<b>Win Count:</b> <code>{game_cfg.get('win_count', 10)}</code>", 
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data=f"gamepanel_{group_id}_{game}")]])
        )
    except pyrogram.errors.exceptions.bad_request_400.MessageNotModified:
        pass

def is_signal_generator_running_for_group(group_id):
    """Check if ANY signal generator is running for the specified group"""
    group_id_str = str(group_id)
    
    # Check signal_tasks for any running tasks for this group
    for key, task in signal_tasks.items():
        if isinstance(key, str) and key.startswith(f"{group_id_str}_"):
            if "thread" in task and task["thread"].is_alive():
                print(f"🔍 Found running signal generator: {key}")
                return True
    
    # Check if group is in starting phase
    if group_id_str in groups_in_starting_phase:
        print(f"🔍 Found group in starting phase: {group_id_str}")
        return True
    
    return False

def stop_all_signal_generators_for_group(group_id):
    """Stop ALL signal generators for the specified group"""
    group_id_str = str(group_id)
    stopped_count = 0
    
    print(f"🛑 Stopping ALL signal generators for group {group_id_str}")
    
    # Stop all running tasks for this group
    tasks_to_stop = []
    for key, task in signal_tasks.items():
        if isinstance(key, str) and key.startswith(f"{group_id_str}_"):
            tasks_to_stop.append(key)
    
    for task_key in tasks_to_stop:
        try:
            task = signal_tasks[task_key]
            if "stop_event" in task:
                task["stop_event"].set()
                print(f"✅ Set stop event for task {task_key}")
            if "thread" in task and task["thread"].is_alive():
                print(f"⏳ Waiting for thread {task_key} to finish...")
                task["thread"].join(timeout=5)  # Wait up to 5 seconds
                if task["thread"].is_alive():
                    print(f"⚠️ Thread {task_key} did not finish in time")
                else:
                    print(f"✅ Thread {task_key} finished successfully")
                    stopped_count += 1
            del signal_tasks[task_key]
            print(f"🗑️ Removed task {task_key} from signal_tasks")
        except Exception as e:
            print(f"❌ Error stopping task {task_key}: {e}")
    
    # Remove from starting phase if present
    if group_id_str in groups_in_starting_phase:
        try:
            stop_event = groups_in_starting_phase[group_id_str]["stop_event"]
            stop_event.set()
            del groups_in_starting_phase[group_id_str]
            print(f"✅ Removed group {group_id_str} from starting phase")
            stopped_count += 1
        except Exception as e:
            print(f"❌ Error removing from starting phase: {e}")
    
    print(f"🛑 Stopped {stopped_count} signal generators for group {group_id_str}")
    return stopped_count

@app.on_message(filters.command("debug_stop_all") & filters.private)
async def debug_stop_all_command(client, message: Message):
    """Debug command to stop all signal generators for a group"""
    user_id = message.from_user.id
    if user_id not in get_admin_ids():
        await message.reply("🚫 You are not authorized to use this command.")
        return
    
    try:
        # Get group ID from command arguments
        args = message.text.split()
        if len(args) < 2:
            await message.reply("❌ Usage: /debug_stop_all <group_id>")
            return
        
        group_id = args[1]
        
        # Check if any signal generators are running
        is_running = is_signal_generator_running_for_group(group_id)
        
        if is_running:
            # Stop all signal generators
            stopped_count = stop_all_signal_generators_for_group(group_id)
            
            # Update group status
            cfg = load_config()
            if group_id in cfg["group_settings"]:
                cfg["group_settings"][group_id]["status"] = "OFF"
                save_config(cfg)
            
            await message.reply(f"✅ Debug: Stopped {stopped_count} signal generator(s) for group {group_id}")
        else:
            await message.reply(f"ℹ️ Debug: No signal generators running for group {group_id}")
            
    except Exception as e:
        await message.reply(f"❌ Error: {e}")

@app.on_message(filters.command("emergency_stop") & filters.private)
async def emergency_stop_command(client, message: Message):
    """Emergency command to force stop ALL signal generators"""
    user_id = message.from_user.id
    if user_id not in get_admin_ids():
        await message.reply("🚫 You are not authorized to use this command.")
        return
    
    await message.reply("🚨 **EMERGENCY STOP INITIATED!** 🚨\n\nStopping ALL signal generators immediately...")
    
    # Force stop all signal generators
    stopped_count = 0
    all_keys = list(signal_tasks.keys())
    
    for key in all_keys:
        try:
            task_info = signal_tasks[key]
            print(f"🚨 EMERGENCY STOPPING: {key}")
            
            if "stop_event" in task_info:
                task_info["stop_event"].set()
            
            if "thread" in task_info and task_info["thread"].is_alive():
                task_info["thread"].join(timeout=2)
            
            del signal_tasks[key]
            stopped_count += 1
            
        except Exception as e:
            print(f"Error in emergency stop: {e}")
    
    # Clear starting phase
    starting_phase_count = len(groups_in_starting_phase)
    groups_in_starting_phase.clear()
    
    # Reset all group statuses
    cfg = load_config()
    for gid in cfg.get("group_settings", {}):
        cfg["group_settings"][gid]["status"] = "OFF"
    save_config(cfg)
    
    await message.reply(f"🚨 **EMERGENCY STOP COMPLETED!** 🚨\n\n✅ Stopped {stopped_count} signal generators\n✅ Cleared {starting_phase_count} groups from starting phase\n✅ Reset all group statuses\n\n🔄 **All operations halted!**")

@app.on_message(filters.command("debug_check") & filters.private)
async def debug_check_command(client, message: Message):
    """Debug command to check signal generator status"""
    user_id = message.from_user.id
    if user_id not in get_admin_ids():
        await message.reply("🚫 You are not authorized to use this command.")
        return
    
    try:
        # Get group ID from command arguments
        args = message.text.split()
        if len(args) < 2:
            await message.reply("❌ Usage: /debug_check <group_id>")
            return
        
        group_id = args[1]
        
        # Check status
        is_running = is_signal_generator_running_for_group(group_id)
        
        # Get detailed information
        running_tasks = []
        for key, task in signal_tasks.items():
            if isinstance(key, str) and key.startswith(f"{group_id}_"):
                if "thread" in task and task["thread"].is_alive():
                    running_tasks.append(key)
        
        in_starting_phase = group_id in groups_in_starting_phase
        
        status_text = f"🔍 **Debug Status for Group {group_id}**\n\n"
        status_text += f"📊 **Overall Status:** {'🟢 Running' if is_running else '🔴 Stopped'}\n"
        status_text += f"🎯 **In Starting Phase:** {'✅ Yes' if in_starting_phase else '❌ No'}\n"
        status_text += f"📋 **Running Tasks:** {len(running_tasks)}\n"
        
        if running_tasks:
            status_text += "\n**Active Tasks:**\n"
            for task in running_tasks:
                status_text += f"• `{task}`\n"
        
        await message.reply(status_text)
        
    except Exception as e:
        await message.reply(f"❌ Error: {e}")

# --- MAIN ---
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    init_db()  # Ensure DB tables exist before starting threads
    
    # Start bot communication cleaner thread
    from bot_communication import start_cleaner_thread
    start_cleaner_thread()
    print("[MAIN] Bot communication cleaner thread started.")
    
    # Start background fetchers as threads
    threading.Thread(target=background_fetcher_thread, args=(fetch_and_store_dices, "DICES"), daemon=True).start()
    threading.Thread(target=background_fetcher_thread, args=(fetch_and_store_blocks, "BLOCKS"), daemon=True).start()
    threading.Thread(target=background_fetcher_thread, args=(fetch_and_store_red_green, "RED_GREEN"), daemon=True).start()
    # Start scheduler thread
    threading.Thread(target=run_scheduler_in_thread, daemon=True).start()
    print("[MAIN] All background fetcher threads and scheduler started.")
    app.run()
