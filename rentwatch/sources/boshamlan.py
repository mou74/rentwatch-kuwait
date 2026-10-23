"""Bo Shamlan (boshamlan.com) – شقق للإيجار per city. Server-rendered Astro islands carry the first 20 posts."""
import html as H
import json
import re

from .base import get, parse_price

NAME = "boshamlan"
LABEL = "بوشملان"
BASE = "https://www.boshamlan.com"
ISLAND_RE = re.compile(r'<astro-island[^>]*props="([^"]*)"', re.S)


def _unwrap(x):
    # Astro serialises props as [typeTag, value]
    if isinstance(x, list) and len(x) == 2 and isinstance(x[0], int) and not isinstance(x[1], bool):
        return _unwrap(x[1])
    if isinstance(x, dict):
        return {k: _unwrap(v) for k, v in x.items()}
    if isinstance(x, list):
        return [_unwrap(v) for v in x]
    return x


def _posts(html):
    for raw in ISLAND_RE.findall(html):
        if "initialPosts" not in raw[:400]:
            continue
        props = _unwrap(json.loads(H.unescape(raw)))
        return props.get("initialPosts") or []
    raise RuntimeError("PostCardList island not found (page layout changed?)")


def fetch(cfg, log):
    out, seen = [], set()
    for area in cfg["areas"]:
        for path in area.get("boshamlan", []):
            url = f"{BASE}/rent/apartments/{path}"
            posts = _posts(get(url, timeout=cfg.get("request_timeout", 30)))
            for p in posts:
                pid = p.get("id")
                if not pid or pid in seen or p.get("is_active") is False:
                    continue
                seen.add(pid)
                img = (p.get("featured_image") or {}).get("path")
                pub = p.get("publisher") or {}
                out.append({
                    "id": f"{NAME}:{pid}",
                    "source": NAME,
                    "source_id": pid,
                    "url": f"{BASE}{p.get('slug') or '/rent/apartments/' + path}/{pid}",
                    "title": p.get("title_ar") or p.get("title_en"),
                    "description": p.get("description_ar") or p.get("description_en") or "",
                    "price": parse_price(p.get("price")),
                    "district": area["name"],
                    "area": area["name"],
                    "rooms": None,
                    "posted_at": p.get("published_at"),
                    "image": img,
                    "phone": pub.get("mobile"),
                })
            log(f"boshamlan {path}: {len(posts)} posts")
    return out
