"""4Sale (q84sale.com) – شقق للإيجار. Listings are embedded as Next.js page data, newest first."""
import re

from .base import get, next_data, parse_price

NAME = "4sale"
LABEL = "4Sale"
BASE = "https://www.q84sale.com"
LIST_URL = BASE + "/ar/property/for-rent/apartment-for-rent/{page}"
ROOMS_ATTR_ID = "46"


def _district_key(district):
    """'حولي , السالمية' -> 'السالمية'; 'صباح السالم , قطعة ٤' -> 'صباح السالم'; 'حولي' -> 'حولي'."""
    segs = [x.strip() for x in (district or "").split(",") if x.strip()]
    segs = [x for x in segs if not re.match(r"^(قطعة|قطعه|ق\s*\d|block)", x, re.I)]
    return segs[-1] if segs else ""


def fetch(cfg, log):
    out = []
    for page in range(1, cfg.get("max_pages_per_source", 4) + 1):
        html = get(LIST_URL.format(page=page), timeout=cfg.get("request_timeout", 30))
        pp = next_data(html)["props"]["pageProps"]
        items = pp.get("listings") or []
        if not items:
            break
        for it in items:
            if not it.get("id") or not it.get("title"):
                continue  # ad slots / promos
            rooms = None
            for a in it.get("attrs") or []:
                if str(a.get("id")) == ROOMS_ATTR_ID:
                    try:
                        rooms = int(a.get("val"))
                    except (TypeError, ValueError):
                        pass
            district = it.get("district_name") or ""
            out.append({
                "id": f"{NAME}:{it['id']}",
                "source": NAME,
                "source_id": it["id"],
                "url": f"{BASE}/ar/listing/{it.get('slug') or it['id']}",
                "title": it.get("title"),
                "description": it.get("desc_ar") or it.get("desc_en"),
                "price": parse_price(it.get("price")),
                "district": district,
                "district_key": _district_key(district),
                "rooms": rooms,
                "posted_at": (it.get("date_published") or it.get("date_sort") or "").replace(" ", "T") or None,
                "image": it.get("thumb") or it.get("image"),
                "phone": it.get("contact") or (it.get("contact_no") or [None])[0],
            })
        log(f"4sale page {page}: {len(items)} listings")
    return out
