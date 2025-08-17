import flet as ft
from flet import *
import json
import os
import asyncio
import aiohttp
import logging
from datetime import datetime

# Configure logging to only show warnings and above
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

# Global variables
running = True
first_time = {}
user_balance = {}
crash_value = 0
last_issue_id = None
is_it_success = False

LAST_LOGIN_FILE = "storage/last_login.json"

# --- SESSION MANAGEMENT ---
# Create a global aiohttp session for all API calls
session_holder = {"session": None}
async def get_global_session():
    if session_holder["session"] is None or session_holder["session"].closed:
        session_holder["session"] = aiohttp.ClientSession()
    return session_holder["session"]

async def close_global_session():
    if session_holder["session"] is not None and not session_holder["session"].closed:
        await session_holder["session"].close()
    session_holder["session"] = None

def save_last_login(username, password):
    try:
        with open(LAST_LOGIN_FILE, "w") as f:
            json.dump({"username": username, "password": password}, f)
    except Exception as e:
        print(f"Error saving last login: {e}")

def load_last_login():
    try:
        with open(LAST_LOGIN_FILE, "r") as f:
            data = json.load(f)
            return data.get("username", ""), data.get("password", "")
    except Exception:
        return "", ""

# --- MODIFIED API FUNCTIONS FOR RED/GREEN (RG1M) ---
async def login(username, password):
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
                new_blade_auth = await login(username, password)
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
    url = "https://m.coinvidb.com/api/rocket-api/game/order/save"
    headers = {
        "Authorization": "Basic cm9ja2V0X3dlYjpyb2NrZXRfd2Vi",
        "Blade-Auth": blade_auth,
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16_6 Mobile/15E148 Safari/604.1",
    }
    if color == 'GREEN   🟢':
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
    else:
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
                print(f"Bet placed: {betamount} on {color} (issue {issue})")
                
                return True
            else:
                print(f"Failed to place bet. Status: {response.status}")
                return False
    except Exception as e:
        print(f"send_crash error: {e}")
        return False

async def check_result(blade_auth, issue_id):
    url = "https://m.coinvidb.com/api/rocket-api/game/issue-result/page"
    params = {"subServiceCode": "RG1M", "size": "1", "current": "1"}
    headers = {
        "Accept": "application/json, text/plain, */*",
        "Authorization": "Basic cm9ja2V0X3dlYjpyb2NrZXRfd2Vi",
        "Blade-Auth": blade_auth,
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16_6 Mobile/15E148 Safari/604.1",
    }
    try:
        session = await get_global_session()
        async with session.get(url, params=params, headers=headers) as response:
            if response.status == 200:
                data = await response.json()
                if data['data']['records'][0]['issue'] == issue_id:
                    return data['data']['records'][0]['value']
            return None
    except Exception as e:
        print(f"check_result error: {e}")
        return None

# --- STRATEGY TRADING LOOPS FOR RED/GREEN (RG1M) ---
async def strategy1(page, username, password, bet_amount, multiply_on_loss, take_profit=None, stop_loss=None, multiply_on_win=None, print_func=None, external_running=None, update_balance_func=None):
    blade_auth = getattr(page, "blade_auth", None)
    if not blade_auth:
        blade_auth = await login(username, password)
        if not blade_auth:
            if print_func:
                await print_func("❌ Login failed!")
            return
    if print_func:
        await print_func("🤖 Bot is starting (Strategy 1)...")
    bet_input = bet_amount
    orginal_bet = bet_amount
    trade_selection = 'GREEN   🟢'
    session_profit = 0  # Track session profit/loss
    while external_running is None or external_running.get('value', True):
        game_info, new_blade_auth = await get_game_info(blade_auth, username, password)
        if new_blade_auth and new_blade_auth != blade_auth:
            page.blade_auth = new_blade_auth
            blade_auth = new_blade_auth
        if not game_info:
            if print_func:
                await print_func("❌ Failed to get game info. Retrying...")
            await asyncio.sleep(2)
            continue
        balance = game_info['balance']
        issue_id = game_info['issue_id']
        start_time = game_info['start_time']
        result = game_info['result']
        # Stop if session profit/loss reached take profit or stop loss
        if (take_profit is not None and session_profit >= take_profit) or (stop_loss is not None and session_profit <= -stop_loss):
            if print_func:
                await print_func("🛑 Stopping bot due to session take profit/stop loss.")
            break
        # Place bet
        if print_func:
            details = (
                f"\n🟢✅ New Order Placed Successfully!\n"
                f"-----------------------------\n"
                f"🆔 Issue: {issue_id}\n"
                f"💵 Order Amount: {bet_input}\n"
                f"💰 Balance: {balance}\n"
                f"🎮 Game: RG1M\n"
                f"🎯 Bet Color: {trade_selection}\n"
                f"-----------------------------"
            )
            await print_func(details)
        await send_crash(blade_auth, issue_id, start_time, bet_input, trade_selection)
        # Wait for result
        res = None
        while res is None:
            res = await check_result(blade_auth, issue_id)
            if res is not None:
                break
            await asyncio.sleep(1)
        # Decide next trade
        if res is not None:
            value_number = int(str(res).replace(" ", ""))
            color_result = "GREEN   🟢" if value_number % 2 else "RED   🔴"
            if trade_selection == color_result:
                if print_func:
                    await print_func(f"📊 Result: {color_result}  🎉 Win!")
                session_profit += 0.95 * bet_input  # Add profit
                bet_input = orginal_bet if not multiply_on_win else bet_input * multiply_on_win
                trade_selection = "RED   🔴" if trade_selection == "GREEN   🟢" else "GREEN   🟢"
            else:
                if print_func:
                    await print_func(f"📊 Result: {color_result} 💔 Lose!")
                session_profit -= bet_input  # Subtract loss
                bet_input *= multiply_on_loss
            if print_func:
                await print_func(f"Session profit: {session_profit}")
            if update_balance_func:
                await update_balance_func(balance)
        else:
            if print_func:
                await print_func("⏳ No result received. Skipping...")
        await asyncio.sleep(2)
    if print_func:
        await print_func("🛑 Bot stopped (Strategy 1)")

async def strategy2(page, username, password, bet_amount, multiply_on_loss, take_profit=None, stop_loss=None, multiply_on_win=None, print_func=None, external_running=None, update_balance_func=None):
    blade_auth = getattr(page, "blade_auth", None)
    if not blade_auth:
        blade_auth = await login(username, password)
        if not blade_auth:
            if print_func:
                await print_func("❌ Login failed!")
            return
    if print_func:
        await print_func("🤖 Bot is starting (Strategy 2)...")
    bet_input = bet_amount
    orginal_bet = bet_amount
    trade_selection = 'GREEN   🟢'
    num_signals = 0
    session_profit = 0  # Track session profit/loss
    while external_running is None or external_running.get('value', True):
        game_info, new_blade_auth = await get_game_info(blade_auth, username, password)
        if new_blade_auth and new_blade_auth != blade_auth:
            page.blade_auth = new_blade_auth
            blade_auth = new_blade_auth
        if not game_info:
            if print_func:
                await print_func("❌ Failed to get game info. Retrying...")
            await asyncio.sleep(2)
            continue
        balance = game_info['balance']
        issue_id = game_info['issue_id']
        start_time = game_info['start_time']
        result = game_info['result']
        # Stop if session profit/loss reached take profit or stop loss
        if (take_profit is not None and session_profit >= take_profit) or (stop_loss is not None and session_profit <= -stop_loss):
            if print_func:
                await print_func("🛑 Stopping bot due to session take profit/stop loss.")
            break
        # Place bet
        if print_func:
            details = (
                f"\n🟢✅ New Order Placed Successfully!\n"
                f"-----------------------------\n"
                f"🆔 Issue: {issue_id}\n"
                f"💵 Order Amount: {bet_input}\n"
                f"💰 Balance: {balance}\n"
                f"🎮 Game: RG1M\n"
                f"🎯 Bet Color: {trade_selection}\n"
                f"-----------------------------"
            )
            await print_func(details)
        await send_crash(blade_auth, issue_id, start_time, bet_input, trade_selection)
        # Wait for result
        res = None
        while res is None:
            res = await check_result(blade_auth, issue_id)
            if res is not None:
                break
            await asyncio.sleep(1)
        # Decide next trade
        if res is not None:
            value_number = int(str(res).replace(" ", ""))
            color_result = "GREEN   🟢" if value_number % 2 else "RED   🔴"
            if trade_selection == color_result:
                if print_func:
                    await print_func(f"📊 Result: {color_result} 🎉 Win!")
                session_profit += 0.95 * bet_input  # Add profit
                bet_input = orginal_bet if not multiply_on_win else bet_input * multiply_on_win
            else:
                if print_func:
                    await print_func(f"📊 Result: {color_result} 💔 Lose!")
                session_profit -= bet_input  # Subtract loss
                bet_input *= multiply_on_loss
            num_signals += 1
            if num_signals == 3:
                trade_selection = "RED   🔴" if trade_selection == "GREEN   🟢" else "GREEN   🟢"
                num_signals = 0
            if print_func:
                await print_func(f"Session profit: {session_profit}")
            if update_balance_func:
                await update_balance_func(balance)
        else:
            if print_func:
                await print_func("⏳ No result received. Skipping...")
        await asyncio.sleep(2)
    if print_func:
        await print_func("🛑 Bot stopped (Strategy 2)")

def main(page: ft.Page):
    # Persistent state for trading output and input fields (in-memory only)
    if not hasattr(page, "trading_output"):
        page.trading_output = []
    if not hasattr(page, "trading_inputs"):
        page.trading_inputs = {
            "bet_amount": "",
            "cashout_number": "",
            "multiply_on_loss": "",
            "stop_take_profit": "",
            "stop_loss": "",
            "multiply_on_win": "",
        }
    # Track if we are on the home page
    page.on_home_page = False
    # Persist trading state across navigation
    if not hasattr(page, "trading_running"):
        page.trading_running = {"value": False}
    if not hasattr(page, "trading_task_ref"):
        page.trading_task_ref = {"task": None}
    # Set page properties
    
    page.title = "Red & Green Auto Trading Bot"
    page.theme_mode = ft.ThemeMode.DARK
    # page.window_maximized = True
    page.bgcolor = ft.Colors.TRANSPARENT
    page.decoration = ft.BoxDecoration(
        gradient=ft.LinearGradient(
                    colors=["#292734", "#000000"],
                    stops= [0,1],
                    begin=ft.alignment.top_left,
                    end=ft.alignment.bottom_right
                ),
    )
    page.padding = 0
    page.spacing = 0
    page.expand=True,
    page.margin=0,
    page.window_resizable = True
    page.scroll = ft.ScrollMode.AUTO

    # Define colors
    primary_gradient = ft.LinearGradient(
        begin=ft.alignment.top_left,
        end=ft.alignment.bottom_right,
        colors=["#292734", "#000000"]
    )
    
    secondary_gradient = ft.LinearGradient(
        begin=ft.alignment.top_right,
        end=ft.alignment.bottom_left,
        colors=["#292734", "#000000"]
    )

    # Login Page
    def login_page():
        last_username, last_password = load_last_login()
        username_field = ft.TextField(
            label="Username",
            value=last_username,
            border_radius=8,
            bgcolor="#1E1F2D",
            border_color=ft.Colors.TRANSPARENT,
            text_style=ft.TextStyle(
                color=ft.Colors.WHITE54,
                size=20,
            ),
            filled=True,
            cursor_color=ft.Colors.WHITE,
        )
        password_field = ft.TextField(
            label="Password",
            password=True,
            value=last_password,
            border_radius=8,
            bgcolor="#1E1F2D",
            border_color=ft.Colors.TRANSPARENT,
            text_style=ft.TextStyle(
                color=ft.Colors.WHITE54,
                size=20,
            ),
            filled=True,
            cursor_color=ft.Colors.WHITE,
        )
        is_loading = ft.Ref()
        is_loading.current = False
        username_error = ft.Ref()
        password_error = ft.Ref()
        username_error.current = False
        password_error.current = False

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Login Failed"),
            content=ft.Text("Invalid username or password."),
            actions=[ft.TextButton("OK", on_click=lambda e: close_dialog())]
        )

        def close_dialog(e=None):
            dialog.open = False
            page.update()

        async def handle_login(e):
            on_button1_click(e)
            is_loading.current = True
            username_error.current = False
            password_error.current = False
            username_field.border_color = ft.Colors.TRANSPARENT
            password_field.border_color = ft.Colors.TRANSPARENT
            username_field.cursor_color = ft.Colors.WHITE
            password_field.cursor_color = ft.Colors.WHITE
            page.update()
            username = username_field.value
            password = password_field.value
            try:
                blade_auth = await login(username, password)
                is_loading.current = False
                page.update()
                if blade_auth:
                    print("blade_auth:", blade_auth)
                    # Show a tiny success message (SnackBar)
                    page.snack_bar = ft.SnackBar(ft.Text("Login successful!"), open=True)
                    page.update()
                    await asyncio.sleep(1)  # Show message for a moment
                    page.username = username
                    page.password = password
                    page.blade_auth = blade_auth
                    page.go("/home")
                    save_last_login(username, password)
                else:
                    # Try to get the error message from the login function
                    session = await get_global_session()
                    url = "https://m.coinvidb.com/api/rocket-api/member/login"
                    headers = {
                        "Accept": "application/json, text/plain, */*",
                        "Authorization": "Basic cm9ja2V0X3dlYjpyb2NrZXRfd2Vi",
                        "Accept-Encoding": "gzip, deflate, br, zstd",
                        "Accept-Language": "en-US",
                        "Content-Type": "application/x-www-form-urlencoded",
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
                    }
                    data = {"username": username, "password": password}
                    async with session.post(url, data=data, headers=headers) as response:
                        if response.status == 200:
                            data = await response.json()
                            if data.get('msg') == 'Wrong user name or password':
                                dialog.content = ft.Text("Wrong user name or password!")
                                username_error.current = True
                                password_error.current = True
                                username_field.border_color = ft.Colors.RED
                                password_field.border_color = ft.Colors.RED
                                username_field.cursor_color = ft.Colors.RED
                                password_field.cursor_color = ft.Colors.RED
                                on_button1_click_err(e)
                                page.open(dialog)
                                return
                            else:
                                dialog.content = ft.Text("Error, please try again later\n Or contact support!")
                                username_error.current = True
                                password_error.current = True
                                username_field.border_color = ft.Colors.RED
                                password_field.border_color = ft.Colors.RED
                                username_field.cursor_color = ft.Colors.RED
                                password_field.cursor_color = ft.Colors.RED
                                on_button1_click_err(e)
                                page.open(dialog)
                                return
                        else:
                            dialog.content = ft.Text("Error, please try again later\n Or contact support!")
                            username_error.current = True
                            password_error.current = True
                            username_field.border_color = ft.Colors.RED
                            password_field.border_color = ft.Colors.RED
                            username_field.cursor_color = ft.Colors.RED
                            password_field.cursor_color = ft.Colors.RED
                            on_button1_click_err(e)
                            page.open(dialog)
                            return
            except Exception as ex:
                is_loading.current = False
                dialog.content = ft.Text("Error, please try again later\n Or contact support!")
                username_error.current = True
                password_error.current = True
                username_field.border_color = ft.Colors.RED
                password_field.border_color = ft.Colors.RED
                username_field.cursor_color = ft.Colors.RED
                password_field.cursor_color = ft.Colors.RED
                page.open(dialog)
                return



        dlg = ft.AlertDialog(
            title=ft.Text("Hello"),
            content=ft.Text("You are notified!"),
            alignment=ft.alignment.center,
            on_dismiss=lambda e: print("Dialog dismissed!"),
            title_padding=ft.padding.all(25),
        )

        dlg_modal = ft.AlertDialog(
            modal=True,
            title=ft.Text("Please confirm"),
            content=ft.Text("Do you really want to delete all those files?"),
            actions=[
                ft.TextButton("Yes", on_click=lambda e: page.close(dlg_modal)),
                ft.TextButton("No", on_click=lambda e: page.close(dlg_modal)),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
            on_dismiss=lambda e: print("Modal dialog dismissed!"),
        )
        # Spinner overlay

        # Button with spinner logic
        def on_button1_click(e):
            btn.content = ft.Row(
                [
                    ft.ProgressRing(width=16, height=16, stroke_width=2),
                    ft.Text(" Loading..."),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                tight=True  # <== أضف دي عشان ما يتمددش
            )
            page.update()
        def on_button1_click_err(e):
            btn.content = ft.Row([
                    ft.ProgressRing(visible=is_loading.current, width=24, height=24),
                    ft.Text("Login", visible=not is_loading.current)
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                tight=True  # <== أضف دي عشان ما يتمددش
            )
            page.update()
        
        btn = ft.ElevatedButton(
                text="Login",
                width=400,
                height=50,
                style=ft.ButtonStyle(
                    color=ft.Colors.WHITE,
                    bgcolor="#2196F3",
                    shape=ft.RoundedRectangleBorder(radius=8),
                    text_style=ft.TextStyle(
                        size=24,
                        weight=ft.FontWeight.BOLD,
                    ),
                ),
                on_click=handle_login,
                disabled=is_loading.current,
                content=ft.Row([
                    ft.ProgressRing(visible=is_loading.current, width=24, height=24),
                    ft.Text("Login", visible=not is_loading.current)
                ], alignment=ft.MainAxisAlignment.CENTER),
            )
    

        return ft.Container(
            expand=True,
            margin=0,
            padding=0,
            gradient=primary_gradient,
            border_radius=4,
            content=ft.Container(
                alignment=ft.alignment.center,
                expand=True,
                margin=0,
                padding=0,
                content=ft.Column(
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    alignment=ft.MainAxisAlignment.CENTER,
                    controls=[
                        ft.Container(
                            width=150,
                            height=150,
                            border_radius=75,
                            content=ft.Image(
                                src="assets/frame-2@2x.png",
                                fit=ft.ImageFit.COVER,
                            ),
                        ),
                        ft.Text(
                            "Welcome",
                            size=48,
                            weight=ft.FontWeight.BOLD,
                            color=ft.Colors.WHITE,
                        ),
                        ft.Text(
                            "to Red & Green auto trading bot🤖",
                            size=14,
                            weight=ft.FontWeight.W_500,
                            color=ft.Colors.WHITE70,
                        ),
                        ft.Container(
                            width=400,
                            padding=20,
                            content=ft.Column(
                                controls=[
                                    username_field,
                                    password_field,
                                    btn
                                ],
                                spacing=10,
                            ),
                        ),
                    ],
                    # spacing=24,
                ),
            ),
        )

    # Home Page
    def home_page():
        username = getattr(page, "username", "Unknown")
        blade_auth = getattr(page, "blade_auth", None)
        balance_text = ft.Ref()

        async def fetch_and_set_balance():
            blade_auth = getattr(page, "blade_auth", None)
            if blade_auth:
                info, new_blade_auth = await get_game_info(blade_auth, getattr(page, "username", None), getattr(page, "password", None))
                if new_blade_auth and new_blade_auth != blade_auth:
                    page.blade_auth = new_blade_auth
                    blade_auth = new_blade_auth
                if info and 'balance' in info:
                    # Only update if still on home page and control exists
                    if hasattr(page, "on_home_page") and page.on_home_page and balance_text.current:
                        balance_text.current.value = f"${info['balance']}"
                        page.update()

        balance_text.current = ft.Text("$0.0", color=ft.Colors.WHITE, size=20)
        page.run_task(fetch_and_set_balance)

        # Remove cashout_number from trading_inputs if present
        if "cashout_number" in page.trading_inputs:
            del page.trading_inputs["cashout_number"]

        # Ensure selected_strategy is initialized
        if not hasattr(page, "selected_strategy") or not page.selected_strategy:
            page.selected_strategy = "1"

        # Helper to create input fields with persistent state
        def make_input_field(label, key):
            return ft.TextField(
                label=label,
                value=page.trading_inputs.get(key, ""),
                on_change=lambda e, k=key: page.trading_inputs.update({k: e.control.value}),
                border_radius=8,
                bgcolor="#1E1F2D",
                border_color=ft.Colors.TRANSPARENT,
                color=ft.Colors.YELLOW,
                cursor_color=ft.Colors.YELLOW,
            )

        bet_amount_field = make_input_field("Bet Amount*", "bet_amount")
        multiply_on_loss_field = make_input_field("Multiply on Loss*", "multiply_on_loss")
        stop_take_profit_field = make_input_field("Stop Take Profit", "stop_take_profit")
        stop_loss_field = make_input_field("Stop Loss", "stop_loss")
        multiply_on_win_field = make_input_field("Multiply on Win", "multiply_on_win")

        # Strategy selection UI as buttons
        # page.selected_strategy = "1"

        # ref to Row for dynamic update
        strategy_row_ref = ft.Ref[ft.Row]()

        def on_strategy_button_click(e, strategy_value):
            page.selected_strategy = strategy_value
            strategy_row_ref.current.controls = strategy_buttons()
            strategy_row_ref.current.update()

        def strategy_buttons():
            selected = page.selected_strategy
            btn1_bg = "#3a3a4d" if selected == "1" else "#191924"
            btn2_bg = "#3a3a4d" if selected == "2" else "#191924"
            text_color = ft.Colors.WHITE
            return [
                ft.TextButton(
                    text="1🔴1🟢",
                    style=ft.ButtonStyle(
                        bgcolor=btn1_bg,
                        color=text_color,
                        shape=ft.RoundedRectangleBorder(radius=8),
                        elevation=0,
                        text_style=ft.TextStyle(size=18, weight=ft.FontWeight.BOLD),
                    ),
                    expand=True,
                    height=50,
                    on_click=lambda e: on_strategy_button_click(e, "1"),
                ),
                ft.Container(width=6),
                ft.TextButton(
                    text="3🟢3🔴",
                    style=ft.ButtonStyle(
                        bgcolor=btn2_bg,
                        color=text_color,
                        shape=ft.RoundedRectangleBorder(radius=8),
                        elevation=0,
                        text_style=ft.TextStyle(size=18, weight=ft.FontWeight.BOLD),
                    ),
                    expand=True,
                    height=50,
                    on_click=lambda e: on_strategy_button_click(e, "2"),
                ),
            ]

        strategy_row = ft.Row(ref=strategy_row_ref, controls=strategy_buttons(), alignment=ft.MainAxisAlignment.CENTER)

        # Output list with persistent state
        output_list = ft.ListView(
            controls=[ft.Text(msg, color=ft.Colors.WHITE) for msg in page.trading_output],
            expand=True,
            auto_scroll=True
        )
        # Store reference to current output_list for trading loop
        page.current_output_list = output_list

        # Helper to scroll to the latest message
        def scroll_output_to_end():
            try:
                output_list.scroll_to(len(output_list.controls) - 1)
            except Exception:
                pass

        # --- Shared running state for trading loop ---
        trading_running = page.trading_running
        trading_task_ref = page.trading_task_ref

        # --- Async handler for Turn On button ---
        async def handle_turn_on(e):
            if trading_running["value"]:
                output_list.controls.append(ft.Text("Trading is already running!", color=ft.Colors.YELLOW))
                page.trading_output.append("Trading is already running!")
                if hasattr(page, "on_home_page") and page.on_home_page:
                    page.update()
                    scroll_output_to_end()
                return
            trading_running["value"] = True
            output_list.controls.clear()
            page.trading_output.clear()
            output_list.controls.append(ft.Text("Starting trading bot..🚀", color=ft.Colors.WHITE))
            page.trading_output.append("Starting trading bot...🚀")
            if hasattr(page, "on_home_page") and page.on_home_page:
                page.update()
                scroll_output_to_end()
            # Gather input values
            try:
                bet_amount = float(bet_amount_field.value)
                multiply_on_loss = float(multiply_on_loss_field.value)
                stop_take_profit = float(stop_take_profit_field.value) if stop_take_profit_field.value else None
                stop_loss = float(stop_loss_field.value) if stop_loss_field.value else None
                multiply_on_win = float(multiply_on_win_field.value) if multiply_on_win_field.value else None
            except Exception as ex:
                output_list.controls.append(ft.Text(f"Input error: {ex}", color=ft.Colors.RED))
                page.trading_output.append(f"Input error: {ex}")
                if hasattr(page, "on_home_page") and page.on_home_page:
                    page.update()
                    scroll_output_to_end()
                trading_running["value"] = False
                return
            username2 = getattr(page, "username", "Unknown")
            password2 = getattr(page, "password", "")
            blade_auth2 = getattr(page, "blade_auth", None)

            import asyncio
            from functools import partial

            async def trading_output_writer(msg):
                page.trading_output.append(str(msg))
                if hasattr(page, "current_output_list") and hasattr(page, "on_home_page") and page.on_home_page:
                    page.current_output_list.controls.append(ft.Text(str(msg), color=ft.Colors.WHITE))
                    page.update()
                    # Scroll to the last message (by index)
                    page.current_output_list.scroll_to(len(page.current_output_list.controls) - 1)
                    page.update()

            async def update_balance_func(new_balance):
                if hasattr(page, "on_home_page") and page.on_home_page and balance_text.current:
                    balance_text.current.value = f"${new_balance}"
                    page.update()

            async def trading_loop_with_output():
                async def print_func(msg):
                    await trading_output_writer(msg)
                # Gather all arguments explicitly
                kwargs = {
                    'page': page,
                    'username': getattr(page, 'username', ''),
                    'password': getattr(page, 'password', ''),
                    'bet_amount': float(bet_amount_field.value),
                    'multiply_on_loss': float(multiply_on_loss_field.value),
                    'take_profit': float(stop_take_profit_field.value) if stop_take_profit_field.value else None,
                    'stop_loss': float(stop_loss_field.value) if stop_loss_field.value else None,
                    'multiply_on_win': float(multiply_on_win_field.value) if multiply_on_win_field.value else None,
                    'print_func': print_func,
                    'external_running': trading_running,
                    'update_balance_func': update_balance_func,
                }
                try:
                    if page.selected_strategy == "1":
                        await strategy1(**kwargs)
                    else:
                        await strategy2(**kwargs)
                except Exception as e:
                    await print_func(f"Error in trading_loop: {e}")
                trading_running["value"] = False
                page.trading_output.append("Trading stopped.")
                if hasattr(page, "current_output_list") and hasattr(page, "on_home_page") and page.on_home_page:
                    page.current_output_list.controls.append(ft.Text("Trading stopped.", color=ft.Colors.YELLOW))
                    page.update()

            # Run trading_loop in the background and keep a reference
            task = page.run_task(trading_loop_with_output)
            trading_task_ref["task"] = task

        # --- Async handler for Turn Off button ---
        async def handle_turn_off(e):
            if not trading_running["value"]:
                output_list.controls.append(ft.Text("Trading is not running!", color=ft.Colors.YELLOW))
                page.trading_output.append("Trading is not running!")
                if hasattr(page, "on_home_page") and page.on_home_page:
                    page.update()
                    scroll_output_to_end()
                return
            trading_running["value"] = False
            output_list.controls.append(ft.Text("Stopping trading...", color=ft.Colors.YELLOW))
            page.trading_output.append("Stopping trading...")
            if hasattr(page, "on_home_page") and page.on_home_page:
                page.update()
                scroll_output_to_end()
            # Optionally, cancel the task if needed (not always necessary)
            # task = trading_task_ref["task"]
            # if task:
            #     task.cancel()

        global overlay_spinner
        overlay_spinner = ft.Container(
            content=ft.Column(
                    [
                        ft.ProgressRing(),
                        ft.Text("Loading...", size=20),
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                bgcolor=ft.Colors.BLACK54,
                alignment=ft.alignment.center,
                expand=True,
                visible=False,
            )
        page.overlay.append(overlay_spinner)
        def on_button2_click(e):
            overlay_spinner.visible = True
            page.update()
            page.go("/history")
            # overlay_spinner.visible = False
            # page.update()

        def clear_last_login():
            try:
                if os.path.exists(LAST_LOGIN_FILE):
                    os.remove(LAST_LOGIN_FILE)
            except Exception as e:
                print(f"Error clearing last login: {e}")

        return ft.Container(
            expand=True,
            margin=0,
            padding=0,
            gradient=secondary_gradient,
            content=ft.Column(
                expand=True,
                controls=[
                    ft.Stack(
                        expand=True,
                        controls=[
                            ft.Container(
                                expand=True,
                                content=ft.Column(
                                    expand=True,
                                    scroll=ft.ScrollMode.AUTO,
                                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                    controls=[
                                        ft.Container(height=80),
                                        ft.Image(
                                            src="assets/frame-2@2x.png",
                                            width=110,
                                            height=110,
                                            fit=ft.ImageFit.COVER,
                                        ),
                                        ft.Text(
                                            "Coinvid",
                                            size=40,
                                            weight=ft.FontWeight.BOLD,
                                            color=ft.Colors.WHITE,
                                        ),
                                        ft.Text(
                                            "Red/Green Auto Trading Bot",
                                            size=20,
                                            weight=ft.FontWeight.BOLD,
                                            color=ft.Colors.WHITE70,
                                        ),
                                        ft.Container(height=24),
                                        ft.Row(
                                            controls=[
                                                ft.Row(
                                                    controls=[
                                                        ft.Icon(ft.Icons.PERSON, color=ft.Colors.WHITE),
                                                        ft.Text(username, color=ft.Colors.WHITE, size=20),
                                                    ],
                                                ),
                                                ft.Container(width=20),
                                                ft.Row(
                                                    controls=[
                                                        ft.Icon(ft.Icons.WALLET, color=ft.Colors.WHITE),
                                                        balance_text.current,
                                                    ],
                                                ),
                                            ],
                                            alignment=ft.MainAxisAlignment.CENTER,
                                        ),
                                        ft.Container(
                                            padding=20,
                                            content=ft.Column(
                                                scroll=ft.ScrollMode.AUTO,
                                                controls=[
                                                    ft.Text(
                                                        "The stop take profit, stop loss and multiply on win are optional. If you don't want them, leave them empty.",
                                                        size=12,
                                                        color=ft.Colors.WHITE,
                                                    ),
                                                    ft.Text("Please choose the strategy:", size=16, color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD),
                                                    strategy_row,
                                                    bet_amount_field,
                                                    multiply_on_loss_field,
                                                    stop_take_profit_field,
                                                    stop_loss_field,
                                                    multiply_on_win_field,
                                                    ft.Row(
                                                        alignment=ft.MainAxisAlignment.CENTER,
                                                        spacing=20,
                                                        controls=[
                                                            ft.ElevatedButton(
                                                                text="Turn On",
                                                                height=40,
                                                                expand=True,
                                                                style=ft.ButtonStyle(
                                                                    color=ft.Colors.WHITE,
                                                                    bgcolor="#42F148",
                                                                    shape=ft.RoundedRectangleBorder(radius=8),
                                                                ),
                                                                on_click=handle_turn_on,
                                                            ),
                                                            ft.ElevatedButton(
                                                                text="Turn Off",
                                                                height=40,
                                                                expand=True,
                                                                style=ft.ButtonStyle(
                                                                    color=ft.Colors.WHITE,
                                                                    bgcolor=ft.Colors.RED,
                                                                    shape=ft.RoundedRectangleBorder(radius=8),
                                                                ),
                                                                on_click=handle_turn_off,
                                                            ),
                                                        ],
                                                    ),
                                                    ft.Container(
                                                        height=300,
                                                        padding=16,
                                                        bgcolor="#1E1F2D",
                                                        border_radius=8,
                                                        content=output_list,
                                                    ),
                                                ],
                                                spacing=10,
                                            ),
                                        ),
                                    ],
                                ),
                            ),
                            ft.Row(
                                controls=[
                                    ft.IconButton(
                                        icon=ft.Icons.ARROW_BACK,
                                        icon_color=ft.Colors.WHITE,
                                        icon_size=30,
                                        on_click=lambda e: (trading_running.update({"value": False}), clear_last_login(), page.go("/")),
                                    ),
                                    ft.Container(expand=True),
                                    ft.IconButton(
                                        icon=ft.Icons.HISTORY,
                                        icon_color=ft.Colors.WHITE,
                                        icon_size=30,
                                        on_click=on_button2_click,
                                    ),
                                ],
                                top=40,
                                left=20,
                                right=20,
                                expand=True,
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            ),
                        ],
                    ),
                ],
            ),
        )

    # History Page
    def history_page():
        # Get user credentials from page
        
        

        blade_auth = getattr(page, "blade_auth", None)
        username = getattr(page, "username", None)
        password = getattr(page, "password", None)
        history_records = ft.Ref()
        history_records.current = []

        async def fetch_history():
            url = "https://m.coinvidb.com/api/rocket-api/game/order/page?current=1&size=10&isPageNum=false&serviceCode=G"
            headers = {
                "Authorization": "Basic cm9ja2V0X3dlYjpyb2NrZXRfd2Vi",
                "Blade-Auth": blade_auth or "",
                "Accept-Language": "en-US",
                "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
                "Accept": "application/json",
            }
            session = await get_global_session()
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    print(data)  # For debugging
                    records = [r for r in data['data']['records'] if r.get('subServiceCode') == 'RG1M']
                    history_records.current = records
                elif response.status == 401 and username and password:
                    new_blade_auth = await login(username, password)
                    if new_blade_auth:
                        page.blade_auth = new_blade_auth
                        headers["Blade-Auth"] = new_blade_auth
                        session2 = await get_global_session()
                        async with session2.get(url, headers=headers) as retry_response:
                            if retry_response.status == 200:
                                data = await retry_response.json()
                                records = [r for r in data['data']['records'] if r.get('subServiceCode') == 'RG1M']
                                history_records.current = records
                            else:
                                history_records.current = []
                else:
                    history_records.current = []
            page.update()

        def build_history_card(record):
            status = record.get('statusI18n', 'Unknown')
            print(status)
            if status == 'No Result':
                status_color = ft.Colors.YELLOW
                status_text = 'No Result ⏳'
            elif status == 'Lost':
                status_color = ft.Colors.RED
                status_text = 'Lost 💔'
            elif status == 'Won':
                status_color = ft.Colors.GREEN
                status_text = 'Won 🎉'
            else:
                status_color = ft.Colors.GREY
                status_text = 'Unknown'
            # Determine bet color
            bet_color = 'Unknown'
            if 'orderDetailFormatByI18n' in record:
                if 'Green' in record['orderDetailFormatByI18n']:
                    bet_color = 'Green 🟢'
                elif 'Red' in record['orderDetailFormatByI18n']:
                    bet_color = 'Red 🔴'
            controls = [
                ft.Container(height=8),
                ft.Text(f'Status: {status_text}', color=status_color, size=18, weight=ft.FontWeight.BOLD),
                ft.Container(height=8),
                ft.Text(f'Issue ID: {record.get("issue", "")}', color=ft.Colors.WHITE, size=16),
                ft.Text(f'Order Number: {record.get("orderNo", "")}', color=ft.Colors.WHITE, size=16),
                ft.Text(f'Bet Color: {bet_color}', color=ft.Colors.WHITE, size=16),
                ft.Text(f'Order Amount: ${record.get("orderAmount", "")}', color=ft.Colors.WHITE, size=16),
            ]
            if status in ['Lost', 'Won']:
                controls.append(ft.Text(f'Back Amount: ${record.get("backAmount", "____")}', color=ft.Colors.WHITE, size=16))
                if status == 'Lost':
                    controls.append(ft.Text(f'Loss: ${record.get("loss", "____")}', color=ft.Colors.WHITE, size=16))
                if status == 'Won':
                    controls.append(ft.Text(f'Profit: ${record.get("profit", "____")}', color=ft.Colors.WHITE, size=16))
            controls.append(ft.Text(f'Result: {record.get("resultFormatValueI18n", "")}', color=ft.Colors.WHITE, size=16))
            if status == 'No Result':
                controls.extend([
                    ft.Text('Back Amount: ____', color=ft.Colors.WHITE, size=16),
                    ft.Text('Loss: ____', color=ft.Colors.WHITE, size=16),
                    ft.Text('Profit: ____', color=ft.Colors.WHITE, size=16),
                ])
            return ft.Card(
                color="#1E1F2D",
                margin=10,
                content=ft.Container(
                    padding=16,
                    content=ft.Column(
                        controls=controls,
                        spacing=6,
                        horizontal_alignment=ft.CrossAxisAlignment.START,
                    ),
                ),
            )

        async def build_content():
            await fetch_history()
            global overlay_spinner
            overlay_spinner.visible = False
            page.update()
            if not history_records.current:
                return ft.Container(
                    expand=True,
                    alignment=ft.alignment.center,
                    content=ft.Text('No history records yet!', size=24, color=ft.Colors.WHITE),
                )
            else:
                return ft.Container(
                    padding=ft.padding.only(top=30),
                    expand=True,
                    content=ft.ListView(
                        expand=True,
                        controls=[build_history_card(r) for r in history_records.current],
                    ),
                )

        content_ref = ft.Ref()
        content_ref.current = ft.Container(
            expand=True,
            alignment=ft.alignment.center,
            content=ft.Text('Loading...', size=24, color=ft.Colors.WHITE),
        )

        async def build_content_and_update():
            content = await build_content()
            content_ref.current.content = content
            page.update()

        # Schedule the async content build
        page.run_task(build_content_and_update)

        return ft.Container(
            expand=True,
            margin=0,
            padding=0,
            gradient=primary_gradient,
            content=ft.Stack(
                expand=True,
                controls=[
                    content_ref.current,
                    ft.IconButton(
                        icon=ft.Icons.ARROW_BACK,
                        icon_color=ft.Colors.WHITE,
                        icon_size=30,
                        on_click=lambda e: page.go("/home"),
                        top=25,
                        left=20,
                    ),
                ],
            ),
        )

    # Route handler
    def route_change(route):
        page.views.clear()
        if page.route == "/":
            page.on_home_page = False
            page.views.append(ft.View("/", [login_page()]))
        elif page.route == "/home":
            page.on_home_page = True
            page.views.append(ft.View("/home", [home_page()]))
        elif page.route == "/history":
            page.on_home_page = False
            page.views.append(ft.View("/history", [history_page()]))
        page.update()

    page.on_route_change = route_change
    page.go("/")

    # Test image path
    # print(os.path.exists("assets/frame-2@2x.png"))  # Should print True

ft.app(target=main)

