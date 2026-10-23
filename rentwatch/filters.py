"""Matching rules: area, price, rooms and "new finish / first tenant" detection."""
import re

AR_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")


def norm(text):
    if not text:
        return ""
    t = str(text).translate(AR_DIGITS)
    t = t.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا").replace("ة", "ه").replace("ى", "ي")
    t = re.sub(r"[ً-ْـ]", "", t)  # harakat + tatweel
    return re.sub(r"\s+", " ", t).strip().lower()


NEW_FINISH_PATTERNS = [
    r"اول ساكن", r"أول ساكن", r"اول سكن", r"لم تسكن", r"لم يسكن", r"غير مسكون",
    r"تشطيب جديد", r"تشطيب سوبر", r"تشطيب ديلوكس", r"تشطيب فاخر", r"تشطيب راقي", r"تشطيب حديث",
    r"بنايه جديد", r"عماره جديد", r"بناء جديد", r"مبني جديد", r"مجمع جديد", r"برج جديد",
    r"جديد(?:ه)?(?: كليا| تماما| بالكامل)", r"سوبر ديلوكس", r"سوبر لوكس", r"مجدد(?:ه)? بالكامل",
    r"first tenant", r"brand new", r"new building", r"newly (?:finished|renovated|built)", r"super deluxe",
    r"عمر البناء:? 0", r"0 - 11 شهر",
]
NEW_FINISH_RE = re.compile("|".join(NEW_FINISH_PATTERNS))

ROOMS_PATTERNS = [
    (re.compile(r"(?<!\d)(\d{1,2})\s*(?:غرف|غرفه|غرفة|غرفتين|غ(?:\s|$)|نوم|bed|br\b|bhk)"), None),
    (re.compile(r"غرفتين|غرفتان|غرفتا|two bed|2bed"), 2),
    (re.compile(r"ثلاث(?:ه)?\s*غرف|three bed|3bed"), 3),
    (re.compile(r"اربع(?:ه)?\s*غرف|four bed"), 4),
    (re.compile(r"خمس(?:ه)?\s*غرف|five bed"), 5),
    (re.compile(r"غرفه? واحده|غرفه و\s*صاله|غرفه وصاله|one bed|1bed"), 1),
    (re.compile(r"ستوديو|استوديو|studio"), 0),
]


def extract_rooms(text):
    t = norm(text)
    if not t:
        return None
    # "غرفتين" before the generic pattern so that "2 حمام" is not read as rooms
    for rx, val in ROOMS_PATTERNS[1:]:
        if rx.search(t):
            # prefer explicit numeric if there is also "N غرف"
            m = ROOMS_PATTERNS[0][0].search(t)
            if m and 0 < int(m.group(1)) < 10:
                return int(m.group(1))
            return val
    m = ROOMS_PATTERNS[0][0].search(t)
    if m:
        n = int(m.group(1))
        if 0 < n < 10:
            return n
    return None


def is_new_finish(text):
    return bool(NEW_FINISH_RE.search(norm(text)))


def match_area(areas, *candidates):
    """Return the configured area name matched by any candidate string, else None."""
    for cand in candidates:
        c = norm(cand)
        if not c:
            continue
        for area in areas:
            if any(norm(x) in c for x in area.get("exclude", [])):
                continue  # e.g. "علي صباح السالم" (Umm Al-Hayman) is not "صباح السالم"
            for alias in [area["name"]] + area.get("aliases", []):
                a = norm(alias)
                if a and re.search(r"(?<![\w؀-ۿ])" + re.escape(a) + r"(?![\w؀-ۿ])", c):
                    return area["name"]
    return None


def evaluate(listing, cfg):
    """Fill area/rooms/is_new_finish/matched/strong/reasons on the listing dict (in place)."""
    text = " ".join(filter(None, [listing.get("title"), listing.get("description"), listing.get("extra_text")]))
    reasons = []
    # detected for every listing (shown on the dashboard even when the listing does not match)
    listing["is_new_finish"] = bool(listing.get("is_new_finish")) or is_new_finish(text)
    if listing.get("rooms") is None:
        listing["rooms"] = extract_rooms(text)

    district_key = listing.get("district_key") or listing.get("district")
    area = listing.get("area") or match_area(cfg["areas"], *([district_key] if district_key else [text]))
    listing["area"] = area
    if not area:
        listing.update(matched=False, strong=False, reasons="خارج المناطق المطلوبة")
        return listing
    reasons.append(f"المنطقة: {area}")

    price = listing.get("price")
    if price in (0, None):
        if not cfg.get("include_unpriced", True):
            listing.update(matched=False, strong=False, reasons="بدون سعر")
            return listing
        reasons.append("السعر غير مذكور")
        listing["price"] = None
    elif not (cfg["price_min"] <= price <= cfg["price_max"]):
        listing.update(matched=False, strong=False, reasons=f"السعر {price} خارج الميزانية")
        return listing
    else:
        reasons.append(f"السعر {price} د.ك")

    rooms = listing.get("rooms")
    want = cfg.get("rooms", 3)
    if rooms is None:
        if not cfg.get("include_unknown_rooms", False):
            listing.update(matched=False, strong=False, reasons="عدد الغرف غير معروف")
            return listing
        reasons.append("عدد الغرف غير مذكور")
    elif rooms != want:
        listing.update(matched=False, strong=False, reasons=f"{rooms} غرف (المطلوب {want})")
        return listing
    else:
        reasons.append(f"{want} غرف")

    new = listing["is_new_finish"]
    if new:
        reasons.append("تشطيب جديد / أول ساكن")
    listing["matched"] = True
    listing["strong"] = new if cfg.get("require_new_finish_for_alerts", True) else True
    listing["reasons"] = " · ".join(reasons)
    return listing
