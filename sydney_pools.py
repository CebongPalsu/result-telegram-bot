import os
import re
import json
import requests
from bs4 import BeautifulSoup

URL = "https://www.sydneypoolstoday.com/"
STATE_FILE = "sydney_last_result.json"

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID") or os.getenv("CHAT_ID")

if not BOT_TOKEN or not CHAT_ID:
    raise RuntimeError("BOT_TOKEN atau CHAT_ID belum dikonfigurasi di GitHub Secrets.")


def get_page():
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/122.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }
    response = requests.get(URL, headers=headers, timeout=30)
    print(f"📡 HTTP Status Code: {response.status_code}")
    response.raise_for_status()
    return response.text


def extract_sydney(html):
    soup = BeautifulSoup(html, "html.parser")
    page_text = soup.get_text(" ", strip=True)

    # Ambil Tanggal
    date_match = re.search(
        r"(\d{1,2}[\s\-/]+[A-Za-z]+[\s\-/]+\d{4}|\d{4}-\d{2}-\d{2})",
        page_text
    )
    result_date = date_match.group(1) if date_match else "Today"

    # Ambil semua teks angka 4 digit
    raw_numbers = []
    for elem in soup.find_all(True):
        text = elem.get_text(strip=True)
        if re.match(r"^\d{4}$", text):
            raw_numbers.append(text)

    # Filter angka unik berurutan
    clean_numbers = []
    for num in raw_numbers:
        if not clean_numbers or clean_numbers[-1] != num:
            clean_numbers.append(num)

    print(f"🔍 Digit angka 4D terdeteksi: {clean_numbers}")

    if len(clean_numbers) < 1:
        raise RuntimeError(f"Gagal mengambil angka! Halaman tidak mengembalikan pola 4D. Total ditemukan: {len(clean_numbers)}")

    first = clean_numbers[0]
    second = clean_numbers[1] if len(clean_numbers) > 1 else "----"
    third = clean_numbers[2] if len(clean_numbers) > 2 else "----"
    lucky = clean_numbers[3:8] if len(clean_numbers) >= 8 else clean_numbers[3:]
    consolation = clean_numbers[8:13] if len(clean_numbers) >= 13 else []

    return {
        "date": result_date,
        "first": first,
        "second": second,
        "third": third,
        "lucky": lucky,
        "consolation": consolation
    }


def format_message(result):
    lucky_text = "\n".join(f"{i + 1}. {num}" for i, num in enumerate(result["lucky"])) if result["lucky"] else "-"
    consolation_text = "\n".join(f"{i + 1}. {num}" for i, num in enumerate(result["consolation"])) if result["consolation"] else "-"

    return f"""🇦🇺 SYDNEY POOLS RESULT

📅 {result['date']}

🥇 1ST PRIZE
{result['first']}

🥈 2ND PRIZE
{result['second']}

🥉 3RD PRIZE
{result['third']}

🍀 LUCKY PRIZES
{lucky_text}

🎁 CONSOLATION PRIZES
{consolation_text}"""


def send_telegram(message):
    api_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message}
    res = requests.post(api_url, data=payload, timeout=30)
    res.raise_for_status()


def main():
    print("================================")
    print("🇦🇺 SYDNEY POOLS BOT")
    print("================================")
    print("🌐 Mengambil data Sydney Pools...")

    html = get_page()
    result = extract_sydney(html)

    print(f"📅 Date: {result['date']}")
    print(f"🥇 1st: {result['first']}")

    last_result = None
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                last_result = json.load(f)
        except Exception:
            pass

    if last_result == result:
        print("⛔ Result Sydney Pools sama. Tidak ada pesan dikirim.")
        return

    msg = format_message(result)
    print("📤 Mengirim ke Telegram...")
    send_telegram(msg)

    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print("✅ Result Sydney Pools berhasil dikirim!")


if __name__ == "__main__":
    main()
