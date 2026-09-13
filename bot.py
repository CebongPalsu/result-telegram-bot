import os
import re
import requests
from bs4 import BeautifulSoup

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]

SOURCE_URL = "https://www.magnumcambodia.com/apps/resultv2?monthly=mon"


def get_page():
    response = requests.get(
        SOURCE_URL,
        timeout=30,
        headers={
            "User-Agent": "Mozilla/5.0"
        }
    )
    response.raise_for_status()
    return response.text


def get_latest_result(html):
    soup = BeautifulSoup(html, "html.parser")

    # Cari tanggal terbaru dengan format YYYY-MM-DD
    page_text = soup.get_text(" ", strip=True)
    dates = re.findall(r"\d{4}-\d{2}-\d{2}", page_text)

    if not dates:
        raise RuntimeError("Tanggal result tidak ditemukan")

    latest_date = dates[0]

    # Cari posisi tanggal terbaru di HTML
    date_node = soup.find(string=lambda x: x and latest_date in x)

    if not date_node:
        raise RuntimeError("Blok result terbaru tidak ditemukan")

    # Ambil parent container result
    container = date_node.parent

    # Ambil semua gambar digit dari blok tersebut
    images = container.find_all_next("img")

    digits = []

    for img in images:
        src = img.get("src", "")

        match = re.search(r"pink_(\d)\.jpg", src)

        if match:
            digits.append(match.group(1))

        # Kita hanya butuh result pertama untuk test
        if len(digits) >= 4:
            break

    if len(digits) != 4:
        raise RuntimeError(
            f"Digit result tidak lengkap. Ditemukan: {digits}"
        )

    return latest_date, "".join(digits)


def send_telegram(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    response = requests.post(
        url,
        data={
            "chat_id": CHAT_ID,
            "text": message,
        },
        timeout=30,
    )

    response.raise_for_status()


def main():
    html = get_page()

    date, result = get_latest_result(html)

    message = f"""🇰🇭 CAMBODIA RESULT
━━━━━━━━━━━━━━━━

📅 {date}

🥇 1st Prize
{result}

━━━━━━━━━━━━━━━━
📌 Source: Cambodia
"""

    print(message)

    send_telegram(message)


if __name__ == "__main__":
    main()
