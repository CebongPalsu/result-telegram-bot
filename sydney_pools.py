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
            "Chrome/140.0.0.0 Safari/537.36"
        )
    }
    response = requests.get(URL, headers=headers, timeout=30)
    response.raise_for_status()
    return response.text


def extract_sydney(html):
    soup = BeautifulSoup(html, "html.parser")
    page_text = soup.get_text(" ", strip=True)

    # 1. AMBIL TANGGAL HARI INI
    date_match = re.search(
        r"(Sunday|Monday|Tuesday|Wednesday|Thursday|Friday|Saturday),\s+([A-Za-z]+\s+\d{1,2}\s+\d{4})",
        page_text,
        re.IGNORECASE,
    )
    result_date = date_match.group(0) if date_match else "Today"

    # 2. EKSTRAKSI ANGKA DARI NAMA FILE GAMBAR BOLA (0-9)
    digits = []
    for img in soup.find_all("img"):
        src = img.get("src") or img.get("data-src") or ""
        # Mencari pola gambar digit (misal: 0.gif, ball_1.png, 2.jpg, dst)
        match = re.search(r"(\d)\.(?:jpg|jpeg|png|gif)", src, re.IGNORECASE)
        if match:
            digits.append(match.group(1))

    # Jika parser src gambar tidak menemukan, fallback cari text langsung
    if len(digits) < 30:
        digits = []
        for img in soup.find_all("img"):
            alt = img.get("alt") or ""
            if alt.isdigit() and len(alt) == 1:
                digits.append(alt)

    print(f"🔍 Digit terdeteksi total: {len(digits)}")

    if len(digits) < 30:
        raise RuntimeError(
            f"Digit result Sydney tidak lengkap. Ditemukan {len(digits)} digit, minimal 30 digit (5 prize x 6 digit)."
        )

    # Mengambil 5 Prize Pertama (Tampilan Hari Ini)
    # 1st Prize = 6 digit
    # 2nd Prize = 6 digit
    # 3rd Prize = 6 digit
    # Starter   = 6 digit
    # Consolation = 6 digit
    first_6d = "".join(digits[0:6])
    second_6d = "".join(digits[6:12])
    third_6d = "".join(digits[12:18])
    starter_6d = "".join(digits[18:24])
    consolation_6d = "".join(digits[24:30])

    # Ambil 4 digit terakhir untuk format 4D standar
    return {
        "date": result_date,
        "first": first_6d[-4:],
        "second": second_6d[-4:],
        "third": third_6d[-4:],
        "starter": starter_6d[-4:],
        "consolation": consolation_6d[-4:],
        "first_full": first_6d,
    }


def format_message(result):
    return f"""🇦🇺 SYDNEY POOLS RESULT

📅 {result['date']}

🥇 1ST PRIZE
{result['first']}

🥈 2ND PRIZE
{result['second']}

🥉 3RD PRIZE
{result['third']}

🍀 STARTER PRIZE
{result['starter']}

🎁 CONSOLATION
{result['consolation']}"""


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
    print(f"🥇 1st (4D): {result['first']} (6D Full: {result['first_full']})")
    print(f"🥈 2nd (4D): {result['second']}")
    print(f"🥉 3rd (4D): {result['third']}")
    print(f"🍀 Starter: {result['starter']}")
    print(f"🎁 Consolation: {result['consolation']}")

    last_result = None
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                last_result = json.load(f)
        except Exception:
            pass

    if last_result == result:
        print("⛔ Result Sydney Pools sama. Skip kirim Telegram.")
        return

    msg = format_message(result)
    print("📤 Mengirim ke Telegram...")
    send_telegram(msg)

    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print("✅ Result Sydney Pools berhasil dikirim dan disimpan!")


if __name__ == "__main__":
    main()
