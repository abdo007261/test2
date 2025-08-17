import asyncio
import json
import logging
import sys
from os import getenv
from aiogram import Bot, Dispatcher, types, html
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.client.default import DefaultBotProperties
import requests
from aiogram.exceptions import TelegramBadRequest

# --- CONFIG ---
TOKEN = getenv("SIGNAL_BOT_TOKEN") or "7581385517:AAEwBMBhAl_65ZF378Z371vXSBio-h52nGI"
ADMIN_IDS = [1602528125, 6378849563]  # Add your admin user IDs here
CONFIG_FILE = "data.json"

# --- BOT SETUP ---
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# --- STATE ---
user_state = {}  # user_id: {"awaiting": ..., "game": ..., "nav_stack": [...], ...}
signal_tasks = {}  # user_id: asyncio.Task

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

# --- CONFIG LOAD/SAVE ---
def load_config():
    try:
        with open(CONFIG_FILE, "r") as f:
            cfg = json.load(f)
            # Migrate to per-group settings if not present
            if "group_settings" not in cfg:
                cfg["group_settings"] = {}
                for gid in cfg.get("groups", []):
                    cfg["group_settings"][gid] = {
                        "game": cfg.get("game", "red_green"),
                        "strategy": cfg.get("strategy", "random"),
                        "formula": cfg.get("formula", ""),
                        "stages": cfg.get("stages", 7),
                        "win_count": cfg.get("win_count", 10),
                        "timer": cfg.get("timer", "24/7"),
                        "status": cfg.get("status", "OFF")
                    }
            return cfg
    except Exception:
        return {
            "groups": [],
            "group_settings": {},
        }

def save_config(cfg):
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=2)

# --- SMART BACK HANDLER ---
async def smart_back(cb: CallbackQuery):
    user_id = cb.from_user.id
    prev = get_prev_nav(user_id)
    pop_nav(user_id)
    try:
        if prev == "list_group":
            await group_list_cb(cb)
        elif prev == "groups":
            await groups_cb(cb)
        elif prev == "signal_panel":
            await signal_panel_cb(cb)
        elif prev in ["red_green", "blocks", "discs"]:
            await game_strategy_cb(cb)
        elif prev == "settings":
            await settings_cb(cb)
        elif prev == "help":
            await help_cb(cb)
        else:
            await start_panel(cb.message)
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            pass  # Ignore harmless error
        else:
            raise

# --- START / CONTROL PANEL ---
@dp.message(CommandStart())
async def start_panel(msg: Message):
    user_id = msg.from_user.id
    push_nav(user_id, "main")
    if user_id not in ADMIN_IDS:
        await msg.answer("🚫 <b>You are not authorized to use this bot.</b>", parse_mode=ParseMode.HTML)
        return
    kb = InlineKeyboardBuilder()
    kb.button(text="👥 Group List", callback_data="list_group")
    kb.button(text="⚙️ Settings", callback_data="settings")
    kb.button(text="❓ Help", callback_data="help")
    kb.adjust(1, 2)
    await msg.answer(
        "<b>🤖 Premium Signal Generator Bot</b>\n\n"
        "Welcome, Admin! Please choose an option below:",
        reply_markup=kb.as_markup(),
        parse_mode=ParseMode.HTML
    )

# --- GROUP LIST ---
@dp.callback_query(lambda c: c.data == "list_group")
async def group_list_cb(cb: CallbackQuery):
    user_id = cb.from_user.id
    push_nav(user_id, "list_group")
    cfg = load_config()
    kb = InlineKeyboardBuilder()
    kb.button(text="📋 Groups", callback_data="groups")
    kb.button(text="🔙 Back", callback_data="back")
    kb.adjust(1)
    await cb.message.edit_text(
        "<b>👥 Group List</b>\n\nManage your signal groups below:",
        reply_markup=kb.as_markup(),
        parse_mode=ParseMode.HTML
    )

@dp.callback_query(lambda c: c.data == "groups")
async def groups_cb(cb: CallbackQuery):
    user_id = cb.from_user.id
    push_nav(user_id, "groups")
    cfg = load_config()
    kb = InlineKeyboardBuilder()
    if not cfg["groups"]:
        kb.button(text="➕ Add this chat", callback_data="add_this_chat")
    else:
        for gid in cfg["groups"]:
            active = any(t for t in signal_tasks.values() if not t.done() and getattr(t, "group_id", None) == gid)
            emoji = "🟢" if active else "🔴"
            kb.button(text=f"{emoji} {gid}", callback_data=f"group_{gid}")
    kb.button(text="➕ Add this chat", callback_data="add_this_chat")
    kb.button(text="🔙 Back", callback_data="back")
    kb.adjust(1)
    await cb.message.edit_text(
        "<b>👥 Group List</b>\n\nSelect a group to manage or add a new one:",
        reply_markup=kb.as_markup(),
        parse_mode=ParseMode.HTML
    )

@dp.callback_query(lambda c: c.data.startswith("group_"))
async def group_panel_cb(cb: CallbackQuery):
    user_id = cb.from_user.id
    push_nav(user_id, cb.data)
    group_id = cb.data.split("_", 1)[1]
    cfg = load_config()
    group_cfg = cfg["group_settings"].get(group_id, {})
    emoji = "🟢" if group_cfg.get("status", "OFF") == "ON" else "🔴"
    kb = InlineKeyboardBuilder()
    kb.button(text="🟢🔴 Red-Green Game (1m)", callback_data=f"gamepanel_{group_id}_red_green")
    kb.button(text="🟫 Block Game (1m)", callback_data=f"gamepanel_{group_id}_blocks")
    kb.button(text="🎲 Disk Game (1m)", callback_data=f"gamepanel_{group_id}_dices")
    kb.button(text="📊 Status", callback_data=f"status_{group_id}")
    kb.button(text="🏆 Win Count", callback_data=f"setwincount_{group_id}")
    kb.button(text="⏰ Timer Settings", callback_data=f"settimer_{group_id}")
    kb.button(text="🔎 Details", callback_data=f"details_{group_id}")
    kb.button(text="▶️ Start", callback_data=f"start_{group_id}")
    kb.button(text="⏹ Stop", callback_data=f"stop_{group_id}")
    kb.button(text="🔙 Back", callback_data="groups")
    kb.adjust(1, 1, 1, 2, 1, 1, 2, 1)
    await cb.message.edit_text(
        f"<b>Group:</b> <code>{group_id}</code> {emoji}\n\n"
        f"<b>Status:</b> <code>{group_cfg.get('status','OFF')}</code>\n"
        f"<b>Game:</b> <code>{group_cfg.get('game','')}</code>\n"
        f"<b>Strategy:</b> <code>{group_cfg.get('strategy','')}</code>\n"
        f"<b>Stages:</b> <code>{group_cfg.get('stages','')}</code>\n"
        f"<b>Win Count:</b> <code>{group_cfg.get('win_count','')}</code>\n"
        f"<b>Timer:</b> <code>{group_cfg.get('timer','')}</code>\n",
        reply_markup=kb.as_markup(),
        parse_mode=ParseMode.HTML
    )

# --- GAME PANEL STUBS ---
@dp.callback_query(lambda c: c.data.startswith("gamepanel_"))
async def gamepanel_cb(cb: CallbackQuery):
    group_id, game = cb.data.split("_", 2)[1:]
    await cb.message.edit_text(f"<b>{game.replace('_',' ').title()} Settings for Group:</b> <code>{group_id}</code>\n\n(Coming soon)", parse_mode=ParseMode.HTML)

# --- STATUS STUB ---
@dp.callback_query(lambda c: c.data.startswith("status_"))
async def status_cb(cb: CallbackQuery):
    group_id = cb.data.split("_", 1)[1]
    cfg = load_config()
    group_cfg = cfg["group_settings"].get(group_id, {})
    await cb.message.edit_text(f"<b>Status for Group:</b> <code>{group_id}</code>\n\n<b>Status:</b> <code>{group_cfg.get('status','OFF')}</code>", parse_mode=ParseMode.HTML)

# --- DETAILS STUB ---
@dp.callback_query(lambda c: c.data.startswith("details_"))
async def details_cb(cb: CallbackQuery):
    group_id = cb.data.split("_", 1)[1]
    cfg = load_config()
    group_cfg = cfg["group_settings"].get(group_id, {})
    text = (
        f"<b>📊 Group Details</b>\n\n"
        f"<b>GROUP ID:</b> <code>{group_id}</code>\n"
        f"<b>STATUS:</b> <code>{group_cfg.get('status', 'OFF')}</code>\n"
        f"<b>GAME:</b> <code>{group_cfg.get('game', '')}</code>\n"
        f"<b>STRATEGY:</b> <code>{group_cfg.get('strategy', '')}</code>\n"
        f"<b>STAGES:</b> <code>{group_cfg.get('stages', 7)}</code>\n"
        f"<b>WIN COUNT:</b> <code>{group_cfg.get('win_count', 10)}</code>\n"
        f"<b>TIMER:</b> <code>{group_cfg.get('timer', '24/7')}</code>\n"
    )
    await cb.message.edit_text(text, parse_mode=ParseMode.HTML)

@dp.callback_query(lambda c: c.data == "add_this_chat")
async def add_this_chat_cb(cb: CallbackQuery):
    cfg = load_config()
    chat_id = str(cb.message.chat.id)
    if chat_id not in cfg["groups"]:
        cfg["groups"].append(chat_id)
        # Ensure per-group settings
        if "group_settings" not in cfg:
            cfg["group_settings"] = {}
        if chat_id not in cfg["group_settings"]:
            cfg["group_settings"][chat_id] = {
                "game": "red_green",
                "strategy": "random",
                "formula": "",
                "stages": 7,
                "win_count": 10,
                "timer": "24/7",
                "status": "OFF"
            }
        save_config(cfg)
        await cb.message.answer(f"✅ <b>Added this chat ID:</b> <code>{chat_id}</code>", parse_mode=ParseMode.HTML)
    else:
        await cb.message.answer(f"ℹ️ <b>This chat ID is already in the group list.</b>", parse_mode=ParseMode.HTML)
    await groups_cb(cb)

@dp.callback_query(lambda c: c.data.startswith("remove_"))
async def remove_group_cb(cb: CallbackQuery):
    group_id = cb.data.split("_", 1)[1]
    cfg = load_config()
    if group_id in cfg["groups"]:
        cfg["groups"].remove(group_id)
        save_config(cfg)
        await cb.message.answer(f"✅ <b>Removed group:</b> <code>{group_id}</code>", parse_mode=ParseMode.HTML)
    else:
        await cb.message.answer(f"❌ <b>Group not found.</b>", parse_mode=ParseMode.HTML)
    await groups_cb(cb)

@dp.callback_query(lambda c: c.data.startswith("start_"))
async def start_group_signal_cb(cb: CallbackQuery):
    user_id = cb.from_user.id
    group_id = cb.data.split("_", 1)[1]
    if user_id in signal_tasks and not signal_tasks[user_id].done():
        await cb.message.answer("<b>▶️ Signal already running for you!</b>", parse_mode=ParseMode.HTML)
        return
    await cb.message.answer(f"<b>▶️ Signal sending started for group:</b> <code>{group_id}</code>", parse_mode=ParseMode.HTML)
    task = asyncio.create_task(signal_task(user_id, group_id))
    task.group_id = group_id
    signal_tasks[user_id] = task
    await group_panel_cb(cb)

@dp.callback_query(lambda c: c.data.startswith("stop_"))
async def stop_group_signal_cb(cb: CallbackQuery):
    user_id = cb.from_user.id
    group_id = cb.data.split("_", 1)[1]
    if user_id in signal_tasks:
        signal_tasks[user_id].cancel()
        await cb.message.answer(f"<b>⏹ Signal sending stopped for group:</b> <code>{group_id}</code>", parse_mode=ParseMode.HTML)
    else:
        await cb.message.answer(f"<b>⏹ No signal task running for group:</b> <code>{group_id}</code>", parse_mode=ParseMode.HTML)
    await group_panel_cb(cb)

# --- SIGNAL PANEL ---
@dp.callback_query(lambda c: c.data == "signal_panel")
async def signal_panel_cb(cb: CallbackQuery):
    user_id = cb.from_user.id
    push_nav(user_id, "signal_panel")
    kb = InlineKeyboardBuilder()
    kb.button(text="🟢🔴 RED-GREEN", callback_data="red_green")
    kb.button(text="🟫 BLOCKS", callback_data="blocks")
    kb.button(text="🎲 DISCS", callback_data="discs")
    kb.button(text="🔙 Back", callback_data="back")
    kb.adjust(1)
    await cb.message.edit_text(
        "<b>📡 Signal Panel</b>\n\nSelect the game for signal generation:",
        reply_markup=kb.as_markup(),
        parse_mode=ParseMode.HTML
    )

# --- GAME STRATEGY PANELS ---
@dp.callback_query(lambda c: c.data in ["red_green", "blocks", "discs"])
async def game_strategy_cb(cb: CallbackQuery):
    user_id = cb.from_user.id
    push_nav(user_id, cb.data)
    game = cb.data
    cfg = load_config()
    cfg["game"] = game
    save_config(cfg)
    game_name = get_game_name(game)
    kb = InlineKeyboardBuilder()
    kb.button(text="🎲 Strategy Random", callback_data=f"{game}_random")
    kb.button(text="📝 Self-Made Strategy", callback_data=f"{game}_self")
    kb.button(text="🔙 Back", callback_data="back")
    kb.adjust(1)
    await cb.message.edit_text(
        f"<b>{game_name} Strategy</b>\n\nChoose your strategy:",
        reply_markup=kb.as_markup(),
        parse_mode=ParseMode.HTML
    )

@dp.callback_query(lambda c: c.data.endswith("_random"))
async def strategy_random_cb(cb: CallbackQuery):
    user_id = cb.from_user.id
    push_nav(user_id, cb.data)
    cfg = load_config()
    cfg["strategy"] = "random"
    save_config(cfg)
    await cb.message.edit_text(
        "<b>🎲 Random strategy selected!</b>\n\n<em>Signal logic will use random strategy.</em>",
        parse_mode=ParseMode.HTML
    )

# --- SELF-MADE STRATEGY FORMULA INPUT ---
@dp.callback_query(lambda c: c.data.endswith("_self"))
async def self_made_strategy_cb(cb: CallbackQuery):
    user_id = cb.from_user.id
    push_nav(user_id, cb.data)
    game = cb.data.split("_")[0]
    game_name = get_game_name(game)
    user_state[user_id]["awaiting"] = "formula"
    user_state[user_id]["game"] = game
    await cb.message.edit_text(
        f"<b>{game_name} - Self-Made Strategy</b>\n\n"
        "<i>👉 Enter your formula below:</i>\n"
        "<code>b</code>: Big   <code>s</code>: Small   <code>g</code>: Green   <code>r</code>: Red\n"
        "<code>o</code>: Odd   <code>e</code>: Even   <code>_</code>: Underscore (line break)\n"
        "\n<code>Example:</code>\n<code>rg_r\ngg_g\nrg_r</code>\n...\n\n<em>Send your formula as a message now.</em>",
        parse_mode=ParseMode.HTML
    )

# --- STAGES, WIN_COUNT, TIMER, DETAILS, BEGIN, STOP ---
@dp.callback_query(lambda c: c.data == "stages")
async def stages_cb(cb: CallbackQuery):
    user_id = cb.from_user.id
    push_nav(user_id, "stages")
    user_state[user_id]["awaiting"] = "stages"
    await cb.message.edit_text(
        "<b>🎯 Stages</b>\n\n<i>Send the number of stages (max 12):</i>",
        parse_mode=ParseMode.HTML
    )

@dp.callback_query(lambda c: c.data == "win_count")
async def win_count_cb(cb: CallbackQuery):
    user_id = cb.from_user.id
    push_nav(user_id, "win_count")
    user_state[user_id]["awaiting"] = "win_count"
    await cb.message.edit_text(
        "<b>🏆 Win Count</b>\n\n<i>Send the win count:</i>",
        parse_mode=ParseMode.HTML
    )

@dp.callback_query(lambda c: c.data == "timer")
async def timer_cb(cb: CallbackQuery):
    user_id = cb.from_user.id
    push_nav(user_id, "timer")
    user_state[user_id]["awaiting"] = "timer"
    await cb.message.edit_text(
        "<b>⏰ Timer</b>\n\n<i>Send the timer (e.g. '24/7' or '10:30'):</i>",
        parse_mode=ParseMode.HTML
    )

@dp.callback_query(lambda c: c.data == "begin")
async def begin_cb(cb: CallbackQuery):
    user_id = cb.from_user.id
    cfg = load_config()
    group_id = cfg.get("current_group") or cb.message.chat.id
    if user_id in signal_tasks and not signal_tasks[user_id].done():
        await cb.message.edit_text("<b>▶️ Signal already running!</b>", parse_mode=ParseMode.HTML)
        return
    await cb.message.edit_text(
        "<b>▶️ Signal sending started!</b>\n\n<em>Signals will be sent automatically based on your strategy.</em>",
        parse_mode=ParseMode.HTML
    )
    signal_tasks[user_id] = asyncio.create_task(signal_task(user_id, group_id))

@dp.callback_query(lambda c: c.data == "stop")
async def stop_cb(cb: CallbackQuery):
    user_id = cb.from_user.id
    if user_id in signal_tasks:
        signal_tasks[user_id].cancel()
        await cb.message.edit_text(
            "<b>⏹ Signal sending stopped!</b>\n\n<em>No more signals will be sent.</em>",
            parse_mode=ParseMode.HTML
        )
    else:
        await cb.message.edit_text(
            "<b>⏹ No signal task running.</b>",
            parse_mode=ParseMode.HTML
        )

@dp.callback_query(lambda c: c.data == "settings")
async def settings_cb(cb: CallbackQuery):
    user_id = cb.from_user.id
    push_nav(user_id, "settings")
    kb = InlineKeyboardBuilder()
    kb.button(text="🔑 Admins", callback_data="admins")
    kb.button(text="💬 Support", callback_data="support")
    kb.button(text="🔙 Back", callback_data="back")
    kb.adjust(1)
    await cb.message.edit_text(
        "<b>⚙️ Settings</b>\n\nManage your bot settings:",
        reply_markup=kb.as_markup(),
        parse_mode=ParseMode.HTML
    )

@dp.callback_query(lambda c: c.data == "help")
async def help_cb(cb: CallbackQuery):
    user_id = cb.from_user.id
    push_nav(user_id, "help")
    text = (
        "<b>🤖 Signal Generator Bot Help</b>\n\n"
        "<b>Description:</b>\n"
        "This bot allows you to manage groups, configure signal strategies, and send trading signals automatically.\n\n"
        "<b>Commands:</b>\n"
        "<code>/start</code> - Open the main control panel\n"
        "<code>/help</code> - Show this help message\n"
        "<code>/id</code> - Get the current chat ID\n"
        "<code>/add_chat_id</code> - Add the current chat ID to the group list\n"
        "<code>/add_id &lt;id&gt;</code> - Add a group/channel ID\n"
        "<code>/remove_id &lt;id&gt;</code> - Remove a group/channel ID\n"
        "<code>/groups</code> - List all groups and their status\n\n"
        "<b>Buttons & Navigation:</b>\n"
        "- <b>👥 Group List</b>: Manage your groups\n"
        "- <b>📡 Signal</b>: Configure signal strategies\n"
        "- <b>▶️ Start/⏹ Stop</b>: Start/stop signal sending\n"
        "- <b>Back</b>: Return to the previous step\n\n"
        "<b>How to Use:</b>\n"
        "1. Add your group(s) using /add_chat_id or /add_id.\n"
        "2. Use /start or the menu to open the control panel.\n"
        "3. Select a group to manage and configure its strategy.\n"
        "4. Use the control panel to start/stop signals, set formula, stages, win count, timer, etc.\n"
        "5. All navigation is step-by-step with back buttons everywhere.\n\n"
        "<b>Strategy:</b>\n"
        "- <b>Random</b>: Bot sends random signals.\n"
        "- <b>Self-Made</b>: Enter your own formula for signal generation.\n\n"
        "<b>Premium Features:</b>\n"
        "- Smart navigation\n"
        "- Per-group control\n"
        "- Status indicators\n"
        "- Detailed statistics (coming soon)\n\n"
        "For more info, contact support."
    )
    kb = InlineKeyboardBuilder()
    kb.button(text="🔙 Back", callback_data="back")
    kb.adjust(1)
    try:
        await cb.message.edit_text(text, reply_markup=kb.as_markup(), parse_mode=ParseMode.HTML)
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            pass
        else:
            raise

@dp.callback_query(lambda c: c.data == "back")
async def back_cb(cb: CallbackQuery):
    await smart_back(cb)

# --- GROUP MANAGEMENT COMMANDS ---
@dp.message(Command("id"))
async def cmd_id(msg: Message):
    await msg.answer(f"<b>Current chat ID:</b> <code>{msg.chat.id}</code>", parse_mode=ParseMode.HTML)

@dp.message(Command("add_chat_id"))
async def cmd_add_chat_id(msg: Message):
    cfg = load_config()
    chat_id = str(msg.chat.id)
    if chat_id not in cfg["groups"]:
        cfg["groups"].append(chat_id)
        # Ensure per-group settings
        if "group_settings" not in cfg:
            cfg["group_settings"] = {}
        if chat_id not in cfg["group_settings"]:
            cfg["group_settings"][chat_id] = {
                "game": "red_green",
                "strategy": "random",
                "formula": "",
                "stages": 7,
                "win_count": 10,
                "timer": "24/7",
                "status": "OFF"
            }
        save_config(cfg)
        await msg.answer(f"✅ <b>Added this chat ID:</b> <code>{chat_id}</code>", parse_mode=ParseMode.HTML)
    else:
        await msg.answer(f"ℹ️ <b>This chat ID is already in the group list.</b>", parse_mode=ParseMode.HTML)

@dp.message(Command("add_id"))
async def cmd_add_id(msg: Message):
    parts = msg.text.strip().split()
    if len(parts) < 2:
        await msg.answer("❌ Usage: /add_id <chat_id>")
        return
    chat_id = parts[1]
    cfg = load_config()
    if chat_id not in cfg["groups"]:
        cfg["groups"].append(chat_id)
        save_config(cfg)
        await msg.answer(f"✅ <b>Added chat ID:</b> <code>{chat_id}</code>", parse_mode=ParseMode.HTML)
    else:
        await msg.answer(f"ℹ️ <b>This chat ID is already in the group list.</b>", parse_mode=ParseMode.HTML)

@dp.message(Command("remove_id"))
async def cmd_remove_id(msg: Message):
    parts = msg.text.strip().split()
    if len(parts) < 2:
        await msg.answer("❌ Usage: /remove_id <chat_id>")
        return
    chat_id = parts[1]
    cfg = load_config()
    if chat_id in cfg["groups"]:
        cfg["groups"].remove(chat_id)
        save_config(cfg)
        await msg.answer(f"✅ <b>Removed chat ID:</b> <code>{chat_id}</code>", parse_mode=ParseMode.HTML)
    else:
        await msg.answer(f"❌ <b>Chat ID not found in group list.</b>", parse_mode=ParseMode.HTML)

@dp.message(Command("groups"))
async def cmd_groups(msg: Message):
    cfg = load_config()
    if not cfg["groups"]:
        await msg.answer("<b>No groups added yet.</b>", parse_mode=ParseMode.HTML)
        return
    text = "<b>Group List:</b>\n"
    for gid in cfg["groups"]:
        active = any(t for t in signal_tasks.values() if not t.done() and getattr(t, "group_id", None) == gid)
        emoji = "🟢" if active else "🔴"
        text += f"{emoji} <code>{gid}</code>\n"
    await msg.answer(text, parse_mode=ParseMode.HTML)

# --- HELP COMMAND ---
@dp.message(Command("help"))
async def cmd_help(msg: Message):
    text = (
        "<b>🤖 Signal Generator Bot Help</b>\n\n"
        "<b>Description:</b>\n"
        "This bot allows you to manage groups, configure signal strategies, and send trading signals automatically.\n\n"
        "<b>Commands:</b>\n"
        "<code>/start</code> - Open the main control panel\n"
        "<code>/help</code> - Show this help message\n"
        "<code>/id</code> - Get the current chat ID\n"
        "<code>/add_chat_id</code> - Add the current chat ID to the group list\n"
        "<code>/add_id &lt;id&gt;</code> - Add a group/channel ID\n"
        "<code>/remove_id &lt;id&gt;</code> - Remove a group/channel ID\n"
        "<code>/groups</code> - List all groups and their status\n\n"
        "<b>Buttons & Navigation:</b>\n"
        "- <b>👥 Group List</b>: Manage your groups\n"
        "- <b>📡 Signal</b>: Configure signal strategies\n"
        "- <b>▶️ Start/⏹ Stop</b>: Start/stop signal sending\n"
        "- <b>Back</b>: Return to the previous step\n\n"
        "<b>How to Use:</b>\n"
        "1. Add your group(s) using /add_chat_id or /add_id.\n"
        "2. Use /start or the menu to open the control panel.\n"
        "3. Select a group to manage and configure its strategy.\n"
        "4. Use the control panel to start/stop signals, set formula, stages, win count, timer, etc.\n"
        "5. All navigation is step-by-step with back buttons everywhere.\n\n"
        "<b>Strategy:</b>\n"
        "- <b>Random</b>: Bot sends random signals.\n"
        "- <b>Self-Made</b>: Enter your own formula for signal generation.\n\n"
        "<b>Premium Features:</b>\n"
        "- Smart navigation\n"
        "- Per-group control\n"
        "- Status indicators\n"
        "- Detailed statistics (coming soon)\n\n"
        "For more info, contact support."
    )
    await msg.answer(text, parse_mode=ParseMode.HTML)

@dp.message()
async def handle_admin_input(msg: Message):
    user_id = msg.from_user.id
    if user_id not in ADMIN_IDS:
        return
    state = user_state.get(user_id)
    if not state or "awaiting" not in state:
        return
    cfg = load_config()
    if state["awaiting"] == "formula":
        cfg["formula"] = msg.text.strip()
        cfg["strategy"] = "self"
        save_config(cfg)
        user_state[user_id].pop("awaiting", None)
        await msg.answer("✅ <b>Formula updated successfully!</b>", parse_mode=ParseMode.HTML)
        await start_panel(msg)
    elif state["awaiting"] == "stages":
        try:
            val = int(msg.text.strip())
            if 1 <= val <= 12:
                cfg["stages"] = val
                save_config(cfg)
                await msg.answer(f"✅ <b>Stages set to {val}!</b>", parse_mode=ParseMode.HTML)
            else:
                await msg.answer("❌ <b>Invalid number. Please enter a value between 1 and 12.</b>", parse_mode=ParseMode.HTML)
                return
        except Exception:
            await msg.answer("❌ <b>Invalid input. Please enter a number.</b>", parse_mode=ParseMode.HTML)
            return
        user_state[user_id].pop("awaiting", None)
        await start_panel(msg)
    elif state["awaiting"] == "win_count":
        try:
            val = int(msg.text.strip())
            if val > 0:
                cfg["win_count"] = val
                save_config(cfg)
                await msg.answer(f"✅ <b>Win count set to {val}!</b>", parse_mode=ParseMode.HTML)
            else:
                await msg.answer("❌ <b>Invalid number. Please enter a positive value.</b>", parse_mode=ParseMode.HTML)
                return
        except Exception:
            await msg.answer("❌ <b>Invalid input. Please enter a number.</b>", parse_mode=ParseMode.HTML)
            return
        user_state[user_id].pop("awaiting", None)
        await start_panel(msg)
    elif state["awaiting"] == "timer":
        val = msg.text.strip()
        cfg["timer"] = val
        save_config(cfg)
        user_state[user_id].pop("awaiting", None)
        await msg.answer(f"✅ <b>Timer set to {val}!</b>", parse_mode=ParseMode.HTML)
        await start_panel(msg)

# --- FIX GAME CALLBACK KEYERROR ---
def get_game_name(game):
    if game.startswith("red_green"): return "🟢🔴 RED-GREEN"
    if game.startswith("blocks"): return "🟫 BLOCKS"
    if game.startswith("dices"): return "🎲 DICES"
    return game

# --- PATCH ALL CALLBACKS TO USE get_game_name ---
# (Update all uses of game_name = {...}[game] to game_name = get_game_name(game))
# ... (rest of the code remains unchanged, but all game_name assignments use get_game_name)

# --- GROUP SETTINGS PANEL ---
@dp.callback_query(lambda c: c.data.startswith("settings_"))
async def group_settings_cb(cb: CallbackQuery):
    user_id = cb.from_user.id
    group_id = cb.data.split("_", 1)[1]
    push_nav(user_id, cb.data)
    cfg = load_config()
    group_cfg = cfg["group_settings"].get(group_id, {})
    kb = InlineKeyboardBuilder()
    kb.button(text="🎮 Game", callback_data=f"setgame_{group_id}")
    kb.button(text="🎲 Strategy", callback_data=f"setstrategy_{group_id}")
    kb.button(text="📝 Formula", callback_data=f"setformula_{group_id}")
    kb.button(text="🎯 Stages", callback_data=f"setstages_{group_id}")
    kb.button(text="🏆 Win Count", callback_data=f"setwincount_{group_id}")
    kb.button(text="⏰ Timer", callback_data=f"settimer_{group_id}")
    kb.button(text="🔙 Back", callback_data=f"group_{group_id}")
    kb.adjust(2, 1, 2, 1, 1)
    text = (
        f"<b>⚙️ Settings for Group:</b> <code>{group_id}</code>\n\n"
        f"<b>Game:</b> <code>{group_cfg.get('game','')}</code>\n"
        f"<b>Strategy:</b> <code>{group_cfg.get('strategy','')}</code>\n"
        f"<b>Formula:</b> <code>{group_cfg.get('formula','')}</code>\n"
        f"<b>Stages:</b> <code>{group_cfg.get('stages','')}</code>\n"
        f"<b>Win Count:</b> <code>{group_cfg.get('win_count','')}</code>\n"
        f"<b>Timer:</b> <code>{group_cfg.get('timer','')}</code>\n"
    )
    await cb.message.edit_text(text, reply_markup=kb.as_markup(), parse_mode=ParseMode.HTML)

# --- GROUP SETTING INPUT HANDLERS ---
@dp.callback_query(lambda c: c.data.startswith("setgame_"))
async def setgame_cb(cb: CallbackQuery):
    user_id = cb.from_user.id
    group_id = cb.data.split("_", 1)[1]
    user_state[user_id] = {"awaiting": "setgame", "group_id": group_id}
    kb = InlineKeyboardBuilder()
    kb.button(text="🟢🔴 RED-GREEN", callback_data=f"setgameval_{group_id}_red_green")
    kb.button(text="🟫 BLOCKS", callback_data=f"setgameval_{group_id}_blocks")
    kb.button(text="🎲 DICES", callback_data=f"setgameval_{group_id}_dices")
    kb.button(text="🔙 Back", callback_data=f"settings_{group_id}")
    kb.adjust(1)
    await cb.message.edit_text(
        f"<b>🎮 Select Game for Group:</b> <code>{group_id}</code>",
        reply_markup=kb.as_markup(),
        parse_mode=ParseMode.HTML
    )

@dp.callback_query(lambda c: c.data.startswith("setgameval_"))
async def setgameval_cb(cb: CallbackQuery):
    group_id, game = cb.data.split("_", 2)[1:]
    cfg = load_config()
    cfg["group_settings"][group_id]["game"] = game
    save_config(cfg)
    await cb.message.edit_text(f"✅ Game set to <b>{game}</b>!", parse_mode=ParseMode.HTML)
    await group_settings_cb(cb)

@dp.callback_query(lambda c: c.data.startswith("setstrategy_"))
async def setstrategy_cb(cb: CallbackQuery):
    user_id = cb.from_user.id
    group_id = cb.data.split("_", 1)[1]
    user_state[user_id] = {"awaiting": "setstrategy", "group_id": group_id}
    kb = InlineKeyboardBuilder()
    kb.button(text="🎲 Random", callback_data=f"setstrategyval_{group_id}_random")
    kb.button(text="📝 Self-Made", callback_data=f"setstrategyval_{group_id}_self")
    kb.button(text="🔙 Back", callback_data=f"settings_{group_id}")
    kb.adjust(1)
    await cb.message.edit_text(
        f"<b>🎲 Select Strategy for Group:</b> <code>{group_id}</code>",
        reply_markup=kb.as_markup(),
        parse_mode=ParseMode.HTML
    )

@dp.callback_query(lambda c: c.data.startswith("setstrategyval_"))
async def setstrategyval_cb(cb: CallbackQuery):
    group_id, strategy = cb.data.split("_", 2)[1:]
    cfg = load_config()
    cfg["group_settings"][group_id]["strategy"] = strategy
    save_config(cfg)
    await cb.message.edit_text(f"✅ Strategy set to <b>{strategy}</b>!", parse_mode=ParseMode.HTML)
    await group_settings_cb(cb)

@dp.callback_query(lambda c: c.data.startswith("setformula_"))
async def setformula_cb(cb: CallbackQuery):
    user_id = cb.from_user.id
    group_id = cb.data.split("_", 1)[1]
    user_state[user_id] = {"awaiting": "setformula", "group_id": group_id}
    kb = InlineKeyboardBuilder()
    kb.button(text="🔙 Back", callback_data=f"settings_{group_id}")
    kb.adjust(1)
    await cb.message.edit_text(
        f"<b>📝 Enter formula for Group:</b> <code>{group_id}</code>\n\nSend your formula as a message now.",
        reply_markup=kb.as_markup(),
        parse_mode=ParseMode.HTML
    )

@dp.callback_query(lambda c: c.data.startswith("setstages_"))
async def setstages_cb(cb: CallbackQuery):
    user_id = cb.from_user.id
    group_id = cb.data.split("_", 1)[1]
    user_state[user_id] = {"awaiting": "setstages", "group_id": group_id}
    kb = InlineKeyboardBuilder()
    kb.button(text="🔙 Back", callback_data=f"settings_{group_id}")
    kb.adjust(1)
    await cb.message.edit_text(
        f"<b>🎯 Enter number of stages for Group:</b> <code>{group_id}</code>",
        reply_markup=kb.as_markup(),
        parse_mode=ParseMode.HTML
    )

@dp.callback_query(lambda c: c.data.startswith("setwincount_"))
async def setwincount_cb(cb: CallbackQuery):
    user_id = cb.from_user.id
    group_id = cb.data.split("_", 1)[1]
    user_state[user_id] = {"awaiting": "setwincount", "group_id": group_id}
    kb = InlineKeyboardBuilder()
    kb.button(text="🔙 Back", callback_data=f"settings_{group_id}")
    kb.adjust(1)
    await cb.message.edit_text(
        f"<b>🏆 Enter win count for Group:</b> <code>{group_id}</code>",
        reply_markup=kb.as_markup(),
        parse_mode=ParseMode.HTML
    )

@dp.callback_query(lambda c: c.data.startswith("settimer_"))
async def settimer_cb(cb: CallbackQuery):
    user_id = cb.from_user.id
    group_id = cb.data.split("_", 1)[1]
    user_state[user_id] = {"awaiting": "settimer", "group_id": group_id}
    kb = InlineKeyboardBuilder()
    kb.button(text="🔙 Back", callback_data=f"settings_{group_id}")
    kb.adjust(1)
    await cb.message.edit_text(
        f"<b>⏰ Enter timer for Group:</b> <code>{group_id}</code>",
        reply_markup=kb.as_markup(),
        parse_mode=ParseMode.HTML
    )

# --- HANDLE ADMIN INPUT FOR GROUP SETTINGS ---
@dp.message()
async def handle_group_admin_input(msg: Message):
    user_id = msg.from_user.id
    state = user_state.get(user_id)
    if not state or "awaiting" not in state:
        return
    group_id = state.get("group_id")
    cfg = load_config()
    group_cfg = cfg["group_settings"].get(group_id, {})
    if state["awaiting"] == "setformula":
        group_cfg["formula"] = msg.text.strip()
        cfg["group_settings"][group_id] = group_cfg
        save_config(cfg)
        user_state[user_id] = {}
        await msg.answer(f"✅ Formula updated for group <code>{group_id}</code>!", parse_mode=ParseMode.HTML)
        # Show settings panel again
        fake_cb = type('FakeCB', (), {'from_user': msg.from_user, 'data': f'settings_{group_id}', 'message': msg})
        await group_settings_cb(fake_cb)
    elif state["awaiting"] == "setstages":
        try:
            val = int(msg.text.strip())
            if 1 <= val <= 12:
                group_cfg["stages"] = val
                cfg["group_settings"][group_id] = group_cfg
                save_config(cfg)
                await msg.answer(f"✅ Stages set to {val} for group <code>{group_id}</code>!", parse_mode=ParseMode.HTML)
            else:
                await msg.answer("❌ Invalid number. Please enter a value between 1 and 12.", parse_mode=ParseMode.HTML)
                return
        except Exception:
            await msg.answer("❌ Invalid input. Please enter a number.", parse_mode=ParseMode.HTML)
            return
        user_state[user_id] = {}
        fake_cb = type('FakeCB', (), {'from_user': msg.from_user, 'data': f'settings_{group_id}', 'message': msg})
        await group_settings_cb(fake_cb)
    elif state["awaiting"] == "setwincount":
        try:
            val = int(msg.text.strip())
            if val > 0:
                group_cfg["win_count"] = val
                cfg["group_settings"][group_id] = group_cfg
                save_config(cfg)
                await msg.answer(f"✅ Win count set to {val} for group <code>{group_id}</code>!", parse_mode=ParseMode.HTML)
            else:
                await msg.answer("❌ Invalid number. Please enter a positive value.", parse_mode=ParseMode.HTML)
                return
        except Exception:
            await msg.answer("❌ Invalid input. Please enter a number.", parse_mode=ParseMode.HTML)
            return
        user_state[user_id] = {}
        fake_cb = type('FakeCB', (), {'from_user': msg.from_user, 'data': f'settings_{group_id}', 'message': msg})
        await group_settings_cb(fake_cb)
    elif state["awaiting"] == "settimer":
        val = msg.text.strip()
        group_cfg["timer"] = val
        cfg["group_settings"][group_id] = group_cfg
        save_config(cfg)
        user_state[user_id] = {}
        await msg.answer(f"✅ Timer set to {val} for group <code>{group_id}</code>!", parse_mode=ParseMode.HTML)
        fake_cb = type('FakeCB', (), {'from_user': msg.from_user, 'data': f'settings_{group_id}', 'message': msg})
        await group_settings_cb(fake_cb)

# --- MAIN ---
async def main():
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main()) 