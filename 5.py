from pybit.unified_trading import WebSocket
from time import sleep
from pybit.unified_trading import HTTP
from flask import Flask
import threading

import requests
import time
import os
import json


TOKEN = "8978150832:AAEQld_K3BUXGls4TJ13oTFzgzatwoKI3Yo"
CHAT_ID = "73455428"
API = f"https://api.telegram.org/bot{TOKEN}"
offset = 0


# ---------- Flask (для UptimeRobot) ----------

app = Flask(__name__)


@app.route("/")
def home():
    return "Bot is running!"


def run_flask():
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)


# ---------- Додаємо користувачів ----------

def get_users():
    if not os.path.exists("users.txt"):
        return []

    with open("users.txt", "r") as f:
        return [line.strip() for line in f if line.strip()]


def save_user(chat_id):
    users = get_users()

    if str(chat_id) not in users:
        with open("users.txt", "a") as f:
            f.write(f"{chat_id}\n")


def remove_user(chat_id):
    users = get_users()

    with open("users.txt", "w") as f:
        for user in users:
            if user != str(chat_id):
                f.write(user + "\n")


# ---------- Перевіряємо нові повідомлення ----------

def check_users():
    global offset

    data = requests.get(
        f"{API}/getUpdates",
        params={"offset": offset, "timeout": 10}
    ).json()

    for update in data["result"]:

        # Запам'ятовуємо ID обробленого update
        offset = update["update_id"] + 1

        if "message" in update:
            message = update["message"]

            if message.get("text") == "/start":

                chat_id = message["chat"]["id"]

                save_user(chat_id)

                requests.post(
                    f"{API}/sendMessage",
                    data={
                        "chat_id": chat_id,
                        "text": "✅ Ви підписані на сповіщення!"
                    }
                )

            if message.get("text") == "/cancel":

                chat_id = message["chat"]["id"]

                remove_user(chat_id)

                requests.post(
                    f"{API}/sendMessage",
                    data={
                        "chat_id": chat_id,
                        "text": "✅ Ви відписалися!"
                    }
                )
            


# ---------- Розсилка ----------

def send_message(text):
    for chat_id in get_users():
        requests.post(
            f"{API}/sendMessage",
            data={
                "chat_id": chat_id,
                "text": text,
                "parse_mode": "HTML",
                "disable_web_page_preview": True
            }
        )



# ==========================================
# Отримуємо всі USDT perpetual
# ==========================================

http = HTTP(
    testnet=False
)

response = http.get_instruments_info(
    category="linear",
    limit=1000
)

symbols = []

for item in response["result"]["list"]:

    if (
        item["quoteCoin"] == "USDT"
        and item["status"] == "Trading"
    ):
        symbols.append(item["symbol"])


print(f"Знайдено монет: {len(symbols)}")
print(symbols[:20])


# ==========================================
# WebSocket
# ==========================================

def handle_message(message):

    for liq in message["data"]:

        print(liq)

        symbol = liq["s"]
        side = liq["S"]

        volume = float(liq["v"])
        price = float(liq["p"])

        value = volume * price

        if side == "Buy":
            liquidation_type = "LONG 🟢"
        else:
            liquidation_type = "SHORT 🔴"

        message = f"<a href=\"https://www.coinglass.com/tv/Bybit_{symbol}\">{symbol}</a> | {liquidation_type:5} | {volume:12.4f} * ${price} = ${value:,.2f}\n"

        print(message)
        send_message(message)

        #url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        #requests.post(url, data={
        #    "chat_id": CHAT_ID,
        #    "text": message
        #})


ws = WebSocket(
    testnet=False,
    channel_type="linear",
)


# ==========================================
# Підписуємося на всі монети
# ==========================================

ws.all_liquidation_stream(
    symbol=symbols,
    #symbol=["BTCUSDT", "ETHUSDT", "SOLUSDT"],
    callback=handle_message
 
)


print("\n======================================")
print("BYBIT ALL LIQUIDATIONS")
print("Waiting for liquidations...")
print("======================================\n")


# Запускаємо Flask у окремому потоці, щоб UptimeRobot міг пінгувати сервіс
threading.Thread(target=run_flask, daemon=True).start()


while True:
    check_users()
    sleep(1)
