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


def get_digit_from_src(src_path):
    """Mengekstrak 1 digit angka dari nama file gambar bola (contoh: /images/b6.gif, 9.jpg, dll)."""
    # Regex strict hanya ambil digit yang berdiri sendiri sebelum ekstensi file
    match = re.search(r"(?:[^\d]|^)(\d)\.(?:jpg|jpeg|png|gif)", src_path, re.IGNORECASE)
    if match:
        return match.group(1)
    return None


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

    # 2. CARI KUMPULAN BOLA HASIL RESULT
    # Ambil semua tag <img> yang BUKAN banner/iklan
    balls = []
    for img in soup.find_all("img"):
        src = img.get("src") or img.get("data-src") or ""
        
        # Filter iklan & header logo
        if any(bad in src.lower() for bad in ["banner", "logo", "party", "casino", "titan", "noble", "header"]):
            continue
            
        digit = get_digit_from_src(src)
        if digit is not None:
            balls.append(digit)

    print(f"🔍 Digit bola result murni terdeteksi ({len(balls)} digit): {balls}")

    if len(balls) < 30:
        raise RuntimeError(f"Gagal mengambil angka bola Sydney. Hanya ditemukan {len(balls)} digit.")

    # Di website Sydney Pools Today:
    # 1st Prize   = 6 digit pertama [0:6]
    # 2nd Prize   = 6 digit kedua   [6:12]
    # 3rd Prize   = 6 digit ketiga  [12:18]
    # Starter     = 6 digit keempat [18:24]
    # Consolation = 6 digit kelima  [24:30]
    
    first_6d = "".join(balls[0:6])
    second_6d = "".join(balls[6:12])
    third_6d = "".join(balls[12:18])
    starter_6d = "".join(balls[18:24])
    consolation_6d = "".join(balls[24:30])

    return {
        "date": result_date,
        "first": first_6d[-4:],        # 4D (6929)
        "second": second_6d[-4:],      # 4D (7445)
        "third": third_6d[-4:],        # 4D (7112)
        "starter": starter_6d[-4:],    # 4D (6004)
        "consolation": consolation_6d[-4:], # 4D (8884)
        "first_full": first_6d,
        "second_full": second_6d,
        "third_full": third_6d,
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
    print(f"🥇 1st Prize (6D): {result['first_full']} -> 4D: {result['first']}")
    print(f"🥈 2nd Prize (6D): {result['second_full']} -> 4D: {result['second']}")
    print(f"🥉 3rd Prize (6D): {result['third_full']} -> 4D: {result['third']}")

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
