"""Notification channels: macOS banner, e-mail (SMTP), Telegram bot."""
import html
import smtplib
import subprocess
from email.message import EmailMessage

import requests

SOURCE_LABELS = {"4sale": "4Sale", "opensooq": "OpenSooq", "boshamlan": "بوشملان"}


def _price(l):
    return f"{l['price']} د.ك" if l.get("price") else "السعر غير مذكور"


def _line(l):
    star = "⭐ " if l.get("strong") else ""
    return f"{star}{l.get('area') or ''} – {_price(l)} – {l.get('rooms') or '?'} غرف – {SOURCE_LABELS.get(l['source'], l['source'])}"


# ---------------------------------------------------------------- macOS
def macos(listings, log):
    if not listings:
        return
    first = listings[0]
    if len(listings) == 1:
        title = "🏠 إعلان جديد يطابق بحثك"
        body = f"{first.get('title') or ''}"
    else:
        title = f"🏠 {len(listings)} إعلانات جديدة تطابق بحثك"
        body = " | ".join(_line(l) for l in listings[:3])
    sub = _line(first)
    script = (f'display notification "{_esc(body)}" with title "{_esc(title)}" '
              f'subtitle "{_esc(sub)}" sound name "Glass"')
    try:
        subprocess.run(["osascript", "-e", script], check=True, capture_output=True, timeout=15)
        log("macOS notification sent")
    except Exception as e:  # noqa: BLE001
        log(f"macOS notification failed: {e}")


def _esc(s):
    return str(s).replace("\\", "\\\\").replace('"', '\\"')[:230]


# ---------------------------------------------------------------- e-mail
def _card_html(l):
    img = f'<img src="{html.escape(l["image"])}" style="width:100%;max-height:260px;object-fit:cover;border-radius:10px 10px 0 0">' if l.get("image") else ""
    phone = f'<a href="tel:{html.escape(str(l["phone"]))}" style="color:#0a7">📞 {html.escape(str(l["phone"]))}</a>' if l.get("phone") else ""
    desc = html.escape((l.get("description") or "")[:400])
    badge = '<span style="background:#ffd54f;color:#333;padding:2px 8px;border-radius:12px;font-size:12px">⭐ تشطيب جديد / أول ساكن</span>' if l.get("is_new_finish") else ""
    return f"""
    <div style="border:1px solid #e3e3e3;border-radius:12px;margin:14px 0;overflow:hidden;font-family:-apple-system,Segoe UI,Tahoma,Arial">
      {img}
      <div style="padding:14px">
        <div style="font-size:17px;font-weight:700;margin-bottom:6px">{html.escape(l.get('title') or '')}</div>
        <div style="color:#555;font-size:14px;margin-bottom:6px">📍 {html.escape(l.get('district') or l.get('area') or '')} · 🛏 {l.get('rooms') or '?'} غرف · 💰 <b>{_price(l)}</b> · {SOURCE_LABELS.get(l['source'], l['source'])}</div>
        <div style="margin-bottom:8px">{badge}</div>
        <div style="color:#333;font-size:14px;line-height:1.7;white-space:pre-wrap">{desc}</div>
        <div style="margin-top:12px;display:flex;gap:12px;align-items:center">
          <a href="{html.escape(l.get('url') or '#')}" style="background:#1769aa;color:#fff;text-decoration:none;padding:8px 14px;border-radius:8px;font-weight:600">افتح الإعلان</a>
          {phone}
        </div>
      </div>
    </div>"""


def email(listings, cfg, log):
    e = cfg["notify"]["email"]
    if not listings or not e.get("enabled"):
        return
    if not (e.get("smtp_user") and e.get("smtp_password") and e.get("to")):
        log("email skipped: smtp_user / smtp_password / to not configured")
        return
    msg = EmailMessage()
    n = len(listings)
    strong = sum(1 for l in listings if l.get("strong"))
    msg["Subject"] = f"🏠 {n} إعلان جديد" + (f" ({strong} تشطيب جديد/أول ساكن)" if strong else "") + " – شقق للإيجار"
    msg["From"] = e.get("from") or e["smtp_user"]
    msg["To"] = e["to"]
    msg.set_content("\n\n".join(f"{_line(l)}\n{l.get('title')}\n{l.get('url')}" for l in listings))
    body = "".join(_card_html(l) for l in listings)
    msg.add_alternative(f'<html><body dir="rtl" style="background:#f6f7f9;padding:10px;max-width:640px;margin:auto">'
                        f'<h2 style="font-family:Arial">إعلانات جديدة تطابق بحثك ({n})</h2>{body}</body></html>', subtype="html")
    host, port = e.get("smtp_host", "smtp.gmail.com"), int(e.get("smtp_port", 465))
    try:
        if port == 465:
            with smtplib.SMTP_SSL(host, port, timeout=30) as s:
                s.login(e["smtp_user"], e["smtp_password"])
                s.send_message(msg)
        else:
            with smtplib.SMTP(host, port, timeout=30) as s:
                s.starttls()
                s.login(e["smtp_user"], e["smtp_password"])
                s.send_message(msg)
        log(f"email sent to {e['to']}")
    except Exception as ex:  # noqa: BLE001
        log(f"email failed: {ex}")
        raise


# ---------------------------------------------------------------- Telegram
def telegram(listings, cfg, log):
    t = cfg["notify"]["telegram"]
    if not listings or not t.get("enabled"):
        return
    if not (t.get("bot_token") and t.get("chat_id")):
        log("telegram skipped: bot_token / chat_id not configured")
        return
    api = f"https://api.telegram.org/bot{t['bot_token']}"
    sent = 0
    for l in listings[:15]:
        badge = "⭐ <b>تشطيب جديد / أول ساكن</b>\n" if l.get("is_new_finish") else ""
        phone = f"\n📞 {l['phone']}" if l.get("phone") else ""
        text = (f"🏠 <b>{html.escape(l.get('title') or '')}</b>\n{badge}"
                f"📍 {html.escape(l.get('district') or l.get('area') or '')} · 🛏 {l.get('rooms') or '?'} غرف · 💰 {_price(l)}\n"
                f"🔗 <a href=\"{html.escape(l.get('url') or '')}\">افتح الإعلان على {SOURCE_LABELS.get(l['source'], l['source'])}</a>{phone}\n\n"
                f"{html.escape((l.get('description') or '')[:500])}")
        try:
            if l.get("image"):
                r = requests.post(f"{api}/sendPhoto", data={"chat_id": t["chat_id"], "photo": l["image"],
                                                            "caption": text[:1000], "parse_mode": "HTML"}, timeout=30)
                if r.status_code != 200:
                    r = requests.post(f"{api}/sendMessage", data={"chat_id": t["chat_id"], "text": text[:4000],
                                                                  "parse_mode": "HTML"}, timeout=30)
            else:
                r = requests.post(f"{api}/sendMessage", data={"chat_id": t["chat_id"], "text": text[:4000],
                                                              "parse_mode": "HTML"}, timeout=30)
            r.raise_for_status()
            sent += 1
        except Exception as ex:  # noqa: BLE001
            log(f"telegram failed for {l['id']}: {ex}")
    log(f"telegram: {sent}/{len(listings)} messages sent")


def send_all(listings, cfg, log, use_macos=True):
    if not listings:
        return
    if use_macos and cfg["notify"].get("macos", True):
        macos(listings, log)
    try:
        email(listings, cfg, log)
    except Exception:  # noqa: BLE001
        pass
    telegram(listings, cfg, log)
