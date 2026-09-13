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

    # 2. EKSTRAKSI ANGKA BOLA
    digits = []
    for img in soup.find_all("img"):
        src = img.get("src") or img.get("data-src") or ""
        alt = img.get("alt") or ""
        src_lower = src.lower()
        
        # Filter kata kunci banner/iklan
        if any(bad in src_lower for bad in ["banner", "party", "casino", "titan", "noble", "captain", "cleopatra", "virgin"]):
            continue

        match = re.search(r"(\d)\.(?:jpg|jpeg|png|gif)", src, re.IGNORECASE)
        if match:
            digits.append(match.group(1))
        elif alt.isdigit() and len(alt) == 1:
            digits.append(alt)

    print(f"🔍 Total digit terdeteksi: {len(digits)}")

    # 3. FIX PERGESERAN: Ambil 30 digit TERAKHIR dari blok result utama
    # Jika iklan atas masih lolos 2 digit (misal total 32 digit), kita ambil 30 digit bola resminya
    if len(digits) > 30:
        # Menghapus digit sampah iklan di bagian paling atas
        digits = digits[-30:]

    if len(digits) < 30:
        raise RuntimeError(f"Gagal memparsing bola Sydney. Terbaca {len(digits)} digit, butuh minimal 30.")

    first_6d = "".join(digits[0:6])       # Akan pas: 026929
    second_6d = "".join(digits[6:12])     # 776745
    third_6d = "".join(digits[12:18])    # 049712
    starter_6d = "".join(digits[18:24])  # 657604
    consolation_6d = "".join(digits[24:30]) # 072884

    return {
        "date": result_date,
        "first_6d": first_6d,
        "second_6d": second_6d,
        "third_6d": third_6d,
        "starter_6d": starter_6d,
        "consolation_6d": consolation_6d,
    }
