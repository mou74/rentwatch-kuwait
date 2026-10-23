import json
import re
import time
from datetime import datetime, timedelta

import requests

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/130.0 Safari/537.36")
HEADERS = {"User-Agent": UA, "Accept-Language": "ar,en;q=0.8", "Accept": "text/html,application/xhtml+xml"}

session = requests.Session()
session.headers.update(HEADERS)


def get(url, timeout=30, retries=2):
    last = None
    for attempt in range(retries + 1):
        try:
            r = session.get(url, timeout=timeout)
            if r.status_code == 200:
                return r.text
            last = f"HTTP {r.status_code}"
        except requests.RequestException as e:  # noqa: PERF203
            last = str(e)
        time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"{url}: {last}")


def next_data(html):
    m = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', html, re.S)
    if not m:
        raise RuntimeError("__NEXT_DATA__ not found (page layout changed?)")
    return json.loads(m.group(1))


AR_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")


def parse_price(value):
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return int(value) if value > 0 else None
    s = str(value).translate(AR_DIGITS).replace(",", "")
    m = re.search(r"\d+", s)
    return int(m.group()) if m else None


def relative_ar_to_iso(text, now=None):
    """Convert OpenSooq-style relative Arabic time ("قبل 9 دقائق", "أمس", "19-10-2026") to ISO."""
    now = now or datetime.now().astimezone()
    if not text:
        return None
    t = str(text).translate(AR_DIGITS).strip()
    m = re.match(r"(\d{2})-(\d{2})-(\d{4})", t)
    if m:
        d, mo, y = map(int, m.groups())
        return datetime(y, mo, d, tzinfo=now.tzinfo).isoformat(timespec="seconds")
    if "امس" in t or "أمس" in t:
        return (now - timedelta(days=1)).isoformat(timespec="seconds")
    n = re.search(r"\d+", t)
    num = int(n.group()) if n else None
    if "ثاني" in t or "ثوان" in t or "لحظ" in t:
        delta = timedelta(seconds=num or 30)
    elif "دقيق" in t or "دقائق" in t:
        delta = timedelta(minutes=num or 1)
    elif "ساعتان" in t or "ساعتين" in t:
        delta = timedelta(hours=2)
    elif "ساع" in t:
        delta = timedelta(hours=num or 1)
    elif "يومان" in t or "يومين" in t:
        delta = timedelta(days=2)
    elif "يوم" in t or "ايام" in t or "أيام" in t:
        delta = timedelta(days=num or 1)
    elif "اسبوع" in t or "أسبوع" in t:
        delta = timedelta(weeks=num or 1)
    elif "شهر" in t:
        delta = timedelta(days=30 * (num or 1))
    else:
        return None
    return (now - delta).isoformat(timespec="seconds")
