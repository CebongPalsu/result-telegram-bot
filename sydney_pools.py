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

    # 2. EKSTRAKSI HANYA GAMBAR BOLA ANGKA (FILTER STRICT)
    digits = []
    
    # Mencari gambar bola yang biasanya berada di dalam folder khusus (misal /balls/, /images/, /ball/)
    # Atau nama file berupa 1 digit saja (contoh: 0.gif, 2.jpg, b0.png)
    for img in soup.find_all("img"):
        src = img.get("src") or img.get("data-src") or ""
        alt = img.get("alt") or ""
        
        # Abaikan gambar iklan / banner / logo
        if any(bad in src.lower() for bad in ["banner", "logo", "party", "casino", "titan", "noble"]):
            continue

        # Regex ketat: mencari nama file digit bola tunggal
        match = re.search(r"(?:/|ball[s_-]?|^)(\d)\.(?:jpg|jpeg|png|gif)", src, re.IGNORECASE)
        if match:
            digits.append(match.group(1))
        elif alt.isdigit() and len(alt) == 1:
            digits.append(alt)

    print(f"🔍 Total bola terdeteksi: {len(digits)}")

    if len(digits) < 30:
        # Fallback jika struktur URL gambar bola polos (contoh: .../0.gif)
        digits = []
        for img in soup.find_all("img"):
            src = img.get("src") or ""
            # Ambil digit terakhir sebelum ekstensi file gambar
            match = re.search(r"(\d)\.(?:gif|png|jpg)", src, re.IGNORECASE)
            if match and not any(bad in src.lower() for bad in ["banner", "party", "casino"]):
                digits.append(match.group(1))

    if len(digits) < 30:
        raise RuntimeError(
            f"Digit result Sydney tidak lengkap. Ditemukan {len(digits)} digit, seharusnya minimal 30."
        )

    # 5 Prize Pertama (Hari Ini): 1st, 2nd, 3rd, Starter, Consolation (Masing-masing 6 digit)
    first_6d = "".join(digits[0:6])
    second_6d = "".join(digits[6:12])
    third_6d = "".join(digits[12:18])
    starter_6d = "".join(digits[18:24])
    consolation_6d = "".join(digits[24:30])

    return {
        "date": result_date,
        "first": first_6d[-4:],        # 4D (misal 6929)
        "second": second_6d[-4:],      # 4D
        "third": third_6d[-4:],        # 4D
        "starter": starter_6d[-4:],    # 4D
        "consolation": consolation_6d[-4:], # 4D
        "first_full": first_6d,        # 6D Full (026929)
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
    print(f"🥇 1st Prize Full (6D): {result['first_full']} -> 4D: {result['first']}")
    print(f"🥈 2nd Prize Full (6D): {result['second_full']} -> 4D: {result['second']}")
    print(f"🥉 3rd Prize Full (6D): {result['third_full']} -> 4D: {result['third']}")

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
