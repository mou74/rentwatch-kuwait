"""OpenSooq Kuwait – شقق للإيجار per neighbourhood, sorted by newest."""
from urllib.parse import quote

from .base import get, next_data, parse_price, relative_ar_to_iso

NAME = "opensooq"
LABEL = "OpenSooq"
BASE = "https://kw.opensooq.com"
IMG = "https://opensooq-imagesv2.os-cdn.com/previews/640x480/{path}.webp"


def _url(gov, nhood, page):
    path = f"/ar/{gov}/{nhood}/عقارات/شقق-للايجار"
    q = "?sort_code=recent" + (f"&page={page}" if page > 1 else "")
    return BASE + quote(path, safe="/") + q


def fetch(cfg, log):
    out, seen = [], set()
    pages = min(cfg.get("max_pages_per_source", 4), 2)  # 30 per page, newest first – 2 pages is plenty
    for area in cfg["areas"]:
        for loc in area.get("opensooq", []):
            gov, nhood = loc["gov"], loc["nhood"]
            for page in range(1, pages + 1):
                html = get(_url(gov, nhood, page), timeout=cfg.get("request_timeout", 30))
                pp = next_data(html)["props"]["pageProps"]
                items = (pp.get("serpApiResponse") or {}).get("listings", {}).get("items") or []
                if not items:
                    break
                for it in items:
                    pid = it.get("id")
                    if not pid or pid in seen:
                        continue
                    seen.add(pid)
                    cps = " ، ".join(it.get("cps") or [])
                    out.append({
                        "id": f"{NAME}:{pid}",
                        "source": NAME,
                        "source_id": pid,
                        "url": f"{BASE}/ar/search/{pid}",
                        "title": it.get("title"),
                        "description": it.get("masked_description") or "",
                        "extra_text": cps,
                        "price": parse_price(it.get("price_amount")),
                        "district": f"{it.get('city_label', '')} , {it.get('nhood_label', '')}",
                        "area": area["name"],
                        "rooms": None,  # derived from cps text ("٣ غرف نوم") by filters.extract_rooms
                        "posted_at": relative_ar_to_iso(it.get("posted_at")),
                        "image": IMG.format(path=it["image_uri"]) if it.get("image_uri") else None,
                        "phone": None,
                    })
                log(f"opensooq {nhood} p{page}: {len(items)} listings")
    return out
