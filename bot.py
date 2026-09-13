import os
import re
import json
import requests
from bs4 import BeautifulSoup

URL = "https://www.magnumcambodia.com/"
STATE_FILE = "last_result.json"

# Support beberapa nama Secret supaya tidak perlu ubah workflow
BOT_TOKEN = (
    os.getenv("TELEGRAM_BOT_TOKEN")
    or os.getenv("BOT_TOKEN")
)

CHAT_ID = (
    os.getenv("TELEGRAM_CHAT_ID")
    or os.getenv("CHAT_ID")
)

if not BOT_TOKEN:
    raise RuntimeError("BOT TOKEN belum ditemukan di GitHub Secrets")

if not CHAT_ID:
    raise RuntimeError("CHAT ID belum ditemukan di GitHub Secrets")


def get_page():
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 Chrome/140 Safari/537.36"
        )
    }

    response = requests.get(
        URL,
        headers=headers,
        timeout=30
    )

    response.raise_for_status()
    return response.text


def extract_result(html):
    soup = BeautifulSoup(html, "html.parser")

    # ---------------------------------------------------------
    # AMBIL TANGGAL
    # ---------------------------------------------------------
    page_text = soup.get_text(" ", strip=True)

    date_match = re.search(
        r"Date\s*:\s*(\d{1,2}-[A-Za-z]{3}-\d{4})",
        page_text,
        re.IGNORECASE
    )

    if date_match:
        result_date = date_match.group(1)
    else:
        result_date = "Unknown Date"

    # ---------------------------------------------------------
    # AMBIL ANGKA DARI GAMBAR BOLA
    # ---------------------------------------------------------
    numbers = []

    for img in soup.find_all("img"):
        src = (
            img.get("src")
            or img.get("data-src")
            or img.get("data-original")
            or ""
        )

        # Hanya ambil gambar bola kuning bernomor
        match = re.search(
            r"kuning[_-](\d+)\.(?:jpg|jpeg|png|gif)",
            src,
            re.IGNORECASE
        )

        if match:
            digit = int(match.group(1))

            if 0 <= digit <= 9:
                numbers.append(str(digit))

    # ---------------------------------------------------------
    # STRUKTUR HALAMAN MAGNUM CAMBODIA
    #
    # 1st      = 4 digit
    # 2nd      = 4 digit
    # 3rd      = 4 digit
    # Lucky    = 5 x 4 digit
    # Consolation = 5 x 4 digit
    #
    # Total = 52 digit
    # ---------------------------------------------------------
    if len(numbers) < 52:
        raise RuntimeError(
            f"Digit result tidak lengkap. "
            f"Ditemukan {len(numbers)} digit, seharusnya minimal 52."
        )

    numbers = numbers[:52]

    first = "".join(numbers[0:4])
    second = "".join(numbers[4:8])
    third = "".join(numbers[8:12])

    lucky = []

    start = 12

    for i in range(5):
        lucky.append(
            "".join(numbers[start + (i * 4): start + (i * 4) + 4])
        )

    consolation = []

    start = 32

    for i in range(5):
        consolation.append(
            "".join(numbers[start + (i * 4): start + (i * 4) + 4])
        )

    return {
        "date": result_date,
        "first": first,
        "second": second,
        "third": third,
        "lucky": lucky,
        "consolation": consolation
    }


def make_result_id(result):
    return json.dumps(
        result,
        sort_keys=True,
        ensure_ascii=False
    )


def load_last_result():
    if not os.path.exists(STATE_FILE):
        return None

    try:
        with open(
            STATE_FILE,
            "r",
            encoding="utf-8"
        ) as f:
            return json.load(f)
    except Exception:
        return None


def save_last_result(result):
    with open(
        STATE_FILE,
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(
            result,
            f,
            ensure_ascii=False,
            indent=2
        )


def send_telegram(message):
    api_url = (
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    )

    payload = {
        "chat_id": CHAT_ID,
        "text": message
    }

    response = requests.post(
        api_url,
        data=payload,
        timeout=30
    )

    response.raise_for_status()

    data = response.json()

    if not data.get("ok"):
        raise RuntimeError(
            f"Telegram error: {data}"
        )


def format_message(result):
    lucky_text = "\n".join(
        f"{i + 1}. {number}"
        for i, number in enumerate(result["lucky"])
    )

    consolation_text = "\n".join(
        f"{i + 1}. {number}"
        for i, number in enumerate(result["consolation"])
    )

    message = f"""🇰🇭 CAMBODIA RESULT

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
{consolation_text}
"""

    return message


def main():
    print("================================")
    print("🇰🇭 CAMBODIA RESULT BOT")
    print("================================")

    print("🌐 Mengambil data Magnum Cambodia...")

    html = get_page()

    print("✅ Website berhasil diakses")

    result = extract_result(html)

    print()
    print("📅 Date:", result["date"])
    print("🥇 1st:", result["first"])
    print("🥈 2nd:", result["second"])
    print("🥉 3rd:", result["third"])
    print("🍀 Lucky:", result["lucky"])
    print("🎁 Consolation:", result["consolation"])

    last_result = load_last_result()

    current_id = make_result_id(result)

    if last_result:
        last_id = make_result_id(last_result)

        if current_id == last_id:
            print()
            print("⛔ Result sama.")
            print("⛔ Tidak mengirim spam ke Telegram.")
            return

    message = format_message(result)

    print()
    print("📤 Mengirim result ke Telegram...")

    send_telegram(message)

    save_last_result(result)

    print("✅ Result berhasil dikirim!")
    print("💾 Result disimpan sebagai result terakhir.")


if __name__ == "__main__":
    main()
