import os
import requests

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN belum diset")

if not CHAT_ID:
    raise RuntimeError("CHAT_ID belum diset")


def send_message(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    response = requests.post(
        url,
        data={
            "chat_id": CHAT_ID,
            "text": text,
        },
        timeout=30,
    )

    response.raise_for_status()
    return response.json()


if __name__ == "__main__":
    message = """🇰🇭 CAMBODIA RESULT BOT

✅ Bot berhasil terhubung!

📡 Auto-result system sedang disiapkan.

🤖 @BoyWestWood_bot
"""

    result = send_message(message)

    print("Telegram response:")
    print(result)
