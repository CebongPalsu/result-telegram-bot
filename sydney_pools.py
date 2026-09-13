import os
import re
import json
import requests
from bs4 import BeautifulSoup

URL = "https://www.sydneypoolstoday.com/"
STATE_FILE = "sydney_pools_last.json"

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID") or os.getenv("CHAT_ID")

def get_page():
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/140.0.0.0 Safari/537.36"
        )
    }
    response = requests.get(URL, headers=headers, timeout=30)
    response.raise_for_status()
    return response.text

def extract_sydney(html):
    soup = BeautifulSoup(html, "html.parser")
    page_text = soup.get_text(" ", strip=True)

    # 1. AMBIL TANGGAL
    date_match = re.search(
        r"(\d{1,2}[\s\-/]+[A-Za-z]+[\s\-/]+\d{4}|\d{4}-\d{2}-\d{2})",
        page_text
    )
    result_date = date_match.group(1) if date_match else "Today"

    # 2. AMBIL SEMUA ANGKA 4 DIGIT DARI TABEL RESULT
    # Sydney Pools umumnya menggunakan teks / tabel HTML
    numbers = []
    
    # Mencari pola 4 digit spesifik di dalam elemen tabel/div
    for cell in soup.find_all(['td', 'div', 'span']):
        text = cell.get_text(strip=True)
        if re.match(r"^\d{4}$", text):
            numbers.append(text)

    # Eliminasi duplikasi berurutan jika scraper mengambil elemen nested
    clean_numbers = []
    for num in numbers:
        if not clean_numbers or clean_numbers[-1] != num:
            clean_numbers.append(num)

    # minimal 1st, 2nd, 3rd, 4 Starter/Lucky, 4 Consolation
    if len(clean_numbers) < 3:
        raise RuntimeError(f"Data Sydney Pools tidak lengkap. Ditemukan {len(clean_numbers)} angka.")

    first = clean_numbers[0]
    second = clean_numbers[1] if len(clean_numbers) > 1 else "----"
    third = clean_numbers[2] if len(clean_numbers) > 2 else "----"
    
    # Lucky / Starter (ambil hingga 4-5 angka berikutnya)
    lucky = clean_numbers[3:8] if len(clean_numbers) >= 8 else clean_numbers[3:]
    
    # Consolation (ambil sisanya)
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
    lucky_text = "\n".join(
        f"{i + 1}. {number}"
        for i, number in enumerate(result["lucky"])
    ) if result["lucky"] else "-"

    consolation_text = "\n".join(
        f"{i + 1}. {number}"
        for i, number in enumerate(result["consolation"])
    ) if result["consolation"] else "-"

    message = f"""🇦🇺 SYDNEY POOLS RESULT

📅 {result["date"]}

🥇 1ST PRIZE
{result["first"]}

🥈 2ND PRIZE
{result["second"]}

🥉 3RD PRIZE
{result["third"]}

🍀 LUCKY PRIZES
{lucky_text}

🎁 CONSOLATION PRIZES
{consolation_text}"""

    return message

def send_telegram(message):
    api_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message}
    res = requests.post(api_url, data=payload, timeout=30)
    res.raise_for_status()

def main():
    print("🌐 Mengambil data Sydney Pools...")
    html = get_page()
    result = extract_sydney(html)
    
    print(f"✅ Result Sydney Parsed: 1st={result['first']}, 2nd={result['second']}, 3rd={result['third']}")

    # Check Anti-Spam Persistence
    last_result = None
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            last_result = json.load(f)

    if last_result == result:
        print("⛔ Result Sydney Pools sama. Skip kirim Telegram.")
        return

    msg = format_message(result)
    send_telegram(msg)

    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print("✅ Result Sydney Pools berhasil terkirim ke Telegram!")

if __name__ == "__main__":
    main()
