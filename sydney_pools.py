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

    # 1. AMBIL TANGGAL
    date_match = re.search(
        r"(Sunday|Monday|Tuesday|Wednesday|Thursday|Friday|Saturday),\s+([A-Za-z]+\s+\d{1,2}\s+\d{4})",
        page_text,
        re.IGNORECASE,
    )
    result_date = date_match.group(0) if date_match else "Today"

    # 2. EKSTRAKSI ANGKA BOLA MURNI
    digits = []
    for img in soup.find_all("img"):
        src = img.get("src") or img.get("data-src") or ""
        alt = img.get("alt") or ""
        src_lower = src.lower()
        
        # Filter kata kunci banner/iklan
        if any(bad in src_lower for bad in ["banner", "party", "casino", "titan", "noble", "captain", "cleopatra", "virgin", "header", "logo"]):
            continue

        match = re.search(r"(\d)\.(?:jpg|jpeg|png|gif)", src, re.IGNORECASE)
        if match:
            digits.append(match.group(1))
        elif alt.isdigit() and len(alt) == 1:
            digits.append(alt)

    print(f"🔍 Total digit terdeteksi: {len(digits)}")

    # 3. AMBIL EXACT 30 DIMIT RESULT (5 PRIZE x 6 BOLA)
    # Jika terdeteksi lebih dari 30 (karena iklan lolos), buang sisa digit di DEPAN (iklan)
    if len(digits) >= 30:
        # Ambil tepat 30 digit paling bawah yang merupakan tabel result asli
        digits = digits[len(digits)-30:]
    else:
        raise RuntimeError(f"Gagal memparsing bola Sydney. Hanya terbaca {len(digits)} digit.")

    first_6d = "".join(digits[0:6])
    second_6d = "".join(digits[6:12])
    third_6d = "".join(digits[12:18])
    starter_6d = "".join(digits[18:24])
    consolation_6d = "".join(digits[24:30])

    return {
        "date": result_date,
        "first_6d": first_6d,
        "second_6d": second_6d,
        "third_6d": third_6d,
        "starter_6d": starter_6d,
        "consolation_6d": consolation_6d,
    }


def format_message(result):
    return f"""🇦🇺 SYDNEY POOLS RESULT (6D)

📅 {result['date']}

🥇 1ST PRIZE
{result['first_6d']}

🥈 2ND PRIZE
{result['second_6d']}

🥉 3RD PRIZE
{result['third_6d']}

🍀 STARTER PRIZE
{result['starter_6d']}

🎁 CONSOLATION
{result['consolation_6d']}"""


def send_telegram(message):
    api_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message}
    res = requests.post(api_url, data=payload, timeout=30)
    res.raise_for_status()


def main():
    print("================================")
    print("🇦🇺 SYDNEY POOLS BOT (6D)")
    print("================================")
    print("🌐 Mengambil data Sydney Pools...")

    html = get_page()
    result = extract_sydney(html)

    print(f"📅 Date: {result['date']}")
    print(f"🥇 1st Prize (6D): {result['first_6d']}")

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

    print("✅ Result Sydney Pools 6D berhasil dikirim dan disimpan!")


if __name__ == "__main__":
    main()
