import requests
url = "https://m.coinvidg.com/api/rocket-api/game/issue-result/page"

params = {"subServiceCode": "RG1M", "size": "10", "current": "1"}

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
response = requests.get(url, headers=headers, params=params, cookies=cookies)
print(response.json())
