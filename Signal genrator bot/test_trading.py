import asyncio
import aiohttp

# Hardcoded user data for coinvidbotvip1 from data.json
user_id = 1602528125
username = "coinvidbotvip1"
password = "coinvidbotvip1"
blade_auth = None

# Example signal
color = "G"  # 'G' for Green, 'R' for Red
phase = 1     # Martingale phase

async def login_to_coinvid(username, password):
    url = "https://m.coinvidb.com/api/rocket-api/member/login"
    headers = {
        "Accept": "application/json, text/plain, */*",
        "Authorization": "Basic cm9ja2V0X3dlYjpyb2NrZXRfd2Vi",
        "Content-Type": "application/x-www-form-urlencoded",
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
    }
    data = {"username": username, "password": password}
    async with aiohttp.ClientSession() as session:
        async with session.post(url, data=data, headers=headers) as response:
            if response.status == 200:
                data = await response.json()
                if data['code'] != 400:
                    return data['data']['access_token']
            return None

async def get_game_info(blade_auth, username=None, password=None):
    url = "https://m.coinvidb.com/api/rocket-api/game/info/simple?gameName=BLK1M"
    headers = {
        "Accept": "application/json, text/plain, */*",
        "Authorization": "Basic cm9ja2V0X3dlYjpyb2NrZXRfd2Vi",
        "Blade-Auth": blade_auth,
        "accept-language": "en-US",
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
    }
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                data = await response.json()
                print(f"Game Info: {data}")
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
            return None, blade_auth

def get_bet_amount(phase, base_amount=1.0):
    return base_amount * (2 ** (phase - 1))

async def send_crash(blade_auth, issue, start_time, betamount, color):
    url = "https://m.coinvidb.com/api/rocket-api/game/order/save"
    headers = {
        "Authorization": "Basic cm9ja2V0X3dlYjpyb2NrZXRfd2Vi",
        "Blade-Auth": blade_auth,
        "accept-language": "en-US",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16_6 Mobile/15E148 Safari/604.1",
    }
    if color == 'Odd':
        data = {
            'issue': int(issue),
            "serviceCode": 'G',
            'orderAmount': betamount,
            "orderAmountDetail": betamount,
            "subServiceCode": "DS1M",
            "productId": "0",
            "frontTime": int(start_time),
            'orderDetail': ',2_1,,,,',
            'orderDetailFormatByI18n': ['', 'Odd', '', '', '', ''],
        }
    else:  # Even
        data = {
            'issue': int(issue),
            "serviceCode": 'G',
            'orderAmount': betamount,
            "orderAmountDetail": betamount,
            "subServiceCode": "DS1M",
            "productId": "0",
            "frontTime": int(start_time),
            'orderDetail': ',,,,2_0,',
            'orderDetailFormatByI18n': ['', '', '', '', 'Even', ''],
        }
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=data, headers=headers) as response:
            if response.status == 200:
                print(f"Bet placed: {betamount} on {color} (issue {issue})")
                return True
            else:
                error_text = await response.text()
                print(f"Failed to place bet. Status: {response.status}. Error: {error_text}")
                return False

async def check_result(blade_auth, issue_id):
    url = "https://m.coinvidb.com/api/rocket-api/game/issue-result/page"
    params = {"subServiceCode": "BLK1M", "size": "1", "current": "1"}
    headers = {
        "Accept": "application/json, text/plain, */*",
        "Authorization": "Basic cm9ja2V0X3dlYjpyb2NrZXRfd2Vi",
        "Blade-Auth": blade_auth,
        "accept-language": "en-US",
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
    }
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params, headers=headers) as response:
            if response.status == 200:
                data = await response.json()
                print("Result checked: ", data)
                if data['data']['records'][0]['issue'] == issue_id:
                    return data['data']['records'][0]['value']
            return None

async def get_user_history(blade_auth):
    url = "https://m.coinvidb.com/api/rocket-api/game/order/page?current=1&size=10&isPageNum=false&serviceCode=G"
    headers = {
        "Authorization": "Basic cm9ja2V0X3dlYjpyb2NrZXRfd2Vi",
        "Blade-Auth": blade_auth or "",
        "Accept-Language": "en-US",
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
        "Accept": "application/json",
    }
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                data = await response.json()
                print("User History: ", data)
                records = [r for r in data['data']['records'] if r.get('subServiceCode') == 'BLK1M']
                if not records:
                    print("No trades found.")
                    return
                print("\n--- Last 10 Trades ---")
                for r in records:
                    status = r.get('statusI18n', 'Unknown')
                    if status == 'No Result':
                        status_emoji = '⏳'
                    elif status == 'Lost':
                        status_emoji = '❌'
                    elif status == 'Won':
                        status_emoji = '✅'
                    else:
                        status_emoji = '❔'
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
                    print(f"Issue: {r.get('issue', '')} | Order: {r.get('orderNo', '')}")
                    print(f"Color: {bet_color} | Amount: ${r.get('orderAmount', '')}")
                    print(f"Status: {status} {status_emoji} | Profit: {profit} | Loss: {loss}")
                    print(f"Back Amount: {back_amount} | Time: {time_str}\n")
            else:
                print(f"Failed to fetch history. Status: {response.status}")

async def test_trade():
    print("Logging in to Coinvid...")
    global blade_auth
    blade_auth = await login_to_coinvid(username, password)
    if not blade_auth:
        print("Failed to login to Coinvid.")
        return
    print("Login successful. blade_auth:", blade_auth)
    print("Getting game info...")
    game_info, _ = await get_game_info(blade_auth, username, password)
    if not game_info:
        print("Failed to get game info.")
        return
    print("Game info:", game_info)
    bet_amount = get_bet_amount(phase)
    print(f"Placing bet: {bet_amount} on {'GREEN' if color == 'G' else 'RED'}")
    success = await send_crash(
        blade_auth,
        game_info["issue_id"],
        game_info["start_time"],
        bet_amount,
        "Odd"
    )
    if not success:
        print("Trade failed.")
        await check_result(blade_auth, game_info["issue_id"])
        await get_user_history(blade_auth)
        return
    print("Trade executed, checking result...")
    result_value = None
    for _ in range(30):
        result_value = await check_result(blade_auth, game_info["issue_id"])
        
        if result_value is not None:
            break
        await asyncio.sleep(1)
    if result_value is not None:
        try:
            value_number = int(str(result_value).replace(" ", ""))
        except Exception:
            value_number = None
        if value_number is not None:
            result_color = "GREEN" if value_number % 2 else "RED"
            result_emoji = "🟢" if result_color == "GREEN" else "🔴"
            signal_choice = "Green" if color == "G" else "Red"
            win = (result_color == ("GREEN" if color == "G" else "RED"))
            status = "Win" if win else "Lose"
            print(f"Result: {value_number}, {result_color} {result_emoji}\nBUY: {signal_choice} {status}")
        else:
            print(f"Result: {result_value}\nBUY: Unknown Unknown")
    else:
        print("Result: Not available yet. Please check later.")
    # Print user history at the end
    

if __name__ == "__main__":
    asyncio.run(test_trade()) 