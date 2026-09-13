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


def extract_digits_from_element(element):
    """Mengambil digit bola bernomor hanya dari dalam satu elemen baris/tabel tertentu."""
    digits = []
    for img in element.find_all("img"):
        src = img.get("src") or img.get("data-src") or ""
        alt = img.get("alt") or ""
        
        # Cari pola angka 0-9 pada nama file gambar
        match = re.search(r"(\d)\.(?:jpg|jpeg|png|gif)", src, re.IGNORECASE)
        if match:
            digits.append(match.group(1))
        elif alt.isdigit() and len(alt) == 1:
            digits.append(alt)
    return "".join(digits)


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

    prizes = {
        "first": "",
        "second": "",
        "third": "",
        "starter": "",
        "consolation": ""
    }

    # 2. EKSTRAKSI BERDASARKAN BARIS TABEL (TR / DIV)
    rows = soup.find_all(["tr", "div"])
    
    for row in rows:
        row_text = row.get_text(" ", strip=True).lower()
        
        if "1st prize" in row_text and not prizes["first"]:
            digits = extract_digits_from_element(row)
            if len(digits) >= 6:
                prizes["first"] = digits[:6]

        elif "2nd prize" in row_text and not prizes["second"]:
            digits = extract_digits_from_element(row)
            if len(digits) >= 6:
                prizes["second"] = digits[:6]

        elif "3rd prize" in row_text and not prizes["third"]:
            digits = extract_digits_from_element(row)
            if len(digits) >= 6:
                prizes["third"] = digits[:6]

        elif "starter" in row_text and not prizes["starter"]:
            digits = extract_digits_from_element(row)
            if len(digits) >= 6:
                prizes["starter"] = digits[:6]

        elif "consolation" in row_text and not prizes["consolation"]:
            digits = extract_digits_from_element(row)
            if len(digits) >= 6:
                prizes["consolation"] = digits[:6]

    # Fallback jika selector baris tidak menemukan secara spesifik
    if not prizes["first"]:
        all_digits = []
        for img in soup.find_all("img"):
            src = img.get("src") or ""
            if any(bad in src.lower() for bad in ["banner", "logo", "party", "casino", "titan"]):
                continue
            match = re.search(r"(\d)\.(?:jpg|jpeg|png|gif)", src, re.IGNORECASE)
            if match:
                all_digits.append(match.group(1))

        if len(all_digits) >= 30:
            prizes["first"] = "".join(all_digits[0:6])
            prizes["second"] = "".join(all_digits[6:12])
            prizes["third"] = "".join(all_digits[12:18])
            prizes["starter"] = "".join(all_digits[18:24])
            prizes["consolation"] = "".join(all_digits[24:30])

    if not prizes["first"] or len(prizes["first"]) < 6:
        raise RuntimeError("Gagal memparsing angka Sydney Pools dengan tepat.")

    # Ambil 4 digit terakhir (4D)
    return {
        "date": result_date,
        "first": prizes["first"][-4:],
        "second": prizes["second"][-4:],
        "third": prizes["third"][-4:],
        "starter": prizes["starter"][-4:],
        "consolation": prizes["consolation"][-4:],
        "first_full": prizes["first"],
        "second_full": prizes["second"],
        "third_full": prizes["third"],
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
