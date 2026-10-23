"""CLI:  python -m rentwatch run | serve | dashboard | test-notify | status"""
import argparse
import http.server
import json
import os
import socketserver
import sys
import threading
import webbrowser
from datetime import datetime
from pathlib import Path

from . import dashboard, notify
from .config import abs_path, load_config
from .db import Store, now_iso
from .filters import evaluate
from .sources import SOURCES


def log(msg):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}", flush=True)


def run_once(cfg, use_macos=True):
    started = now_iso()
    store = Store(abs_path(cfg, "db_path"))
    fetched, errors, new_ids = 0, [], []
    enabled = cfg.get("sources") or list(SOURCES)
    for name in enabled:
        mod = SOURCES.get(name)
        if not mod:
            errors.append(f"unknown source {name}")
            continue
        try:
            listings = mod.fetch(cfg, log)
        except Exception as e:  # noqa: BLE001
            msg = f"{name}: {e}"
            errors.append(msg)
            log("ERROR " + msg)
            continue
        for l in listings:
            evaluate(l, cfg)
            if store.upsert(l):
                new_ids.append(l["id"])
        fetched += len(listings)
        store.commit()
    pending = store.pending_alerts(strong_only=cfg.get("require_new_finish_for_alerts", True))
    # Only alert on listings first seen in this run or still unsent from earlier runs
    log(f"fetched {fetched} listings, {len(new_ids)} new, {len(pending)} alerts to send")
    if pending:
        notify.send_all(pending, cfg, log, use_macos=use_macos)
        store.mark_notified([p["id"] for p in pending])
    # anything matched but not alert-worthy is marked as seen too (shown on the dashboard only)
    quiet = store.pending_alerts(strong_only=False)
    store.mark_notified([q["id"] for q in quiet])
    store.log_run(started, fetched, len(pending), errors)
    store.commit()
    out = dashboard.build(store, cfg, abs_path(cfg, "dashboard_path"))
    log(f"dashboard written: {out}")
    return len(pending), errors


def serve(cfg, port, open_browser, loop_minutes):
    docroot = abs_path(cfg, "dashboard_path").parent
    docroot.mkdir(parents=True, exist_ok=True)
    if not (docroot / "index.html").exists():
        dashboard.build(Store(abs_path(cfg, "db_path")), cfg, abs_path(cfg, "dashboard_path"))

    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *a, **k):
            super().__init__(*a, directory=str(docroot), **k)

        def log_message(self, *a):  # quiet
            pass

    if loop_minutes:
        def loop():
            while True:
                try:
                    run_once(cfg)
                except Exception as e:  # noqa: BLE001
                    log(f"run failed: {e}")
                threading.Event().wait(loop_minutes * 60)
        threading.Thread(target=loop, daemon=True).start()
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("127.0.0.1", port), Handler) as httpd:
        url = f"http://127.0.0.1:{port}/"
        log(f"dashboard at {url}  (Ctrl+C to stop)")
        if open_browser:
            webbrowser.open(url)
        httpd.serve_forever()


def main(argv=None):
    p = argparse.ArgumentParser(prog="rentwatch")
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="فحص واحد لكل المصادر + تنبيهات + تحديث اللوحة")
    r.add_argument("--no-macos", action="store_true", help="بدون إشعار ماك (للتشغيل في السحابة)")
    s = sub.add_parser("serve", help="تشغيل لوحة العرض محلياً")
    s.add_argument("--port", type=int, default=8765)
    s.add_argument("--open", action="store_true")
    s.add_argument("--loop", type=int, metavar="MINUTES", default=0, help="أيضاً افحص كل N دقيقة داخل نفس العملية")
    sub.add_parser("dashboard", help="إعادة توليد لوحة العرض فقط")
    sub.add_parser("status", help="إحصائيات سريعة")
    t = sub.add_parser("test-notify", help="إرسال تنبيه تجريبي عبر كل القنوات المفعّلة")
    t.add_argument("--no-macos", action="store_true")
    a = p.parse_args(argv)
    cfg = load_config()

    if a.cmd == "run":
        n, errors = run_once(cfg, use_macos=not a.no_macos)
        if errors:
            log("errors: " + " | ".join(errors))
        return 0
    if a.cmd == "serve":
        serve(cfg, a.port, a.open, a.loop)
        return 0
    if a.cmd == "dashboard":
        out = dashboard.build(Store(abs_path(cfg, "db_path")), cfg, abs_path(cfg, "dashboard_path"))
        log(f"dashboard written: {out}")
        return 0
    if a.cmd == "status":
        st = Store(abs_path(cfg, "db_path")).stats()
        print(json.dumps(st, ensure_ascii=False, indent=2))
        return 0
    if a.cmd == "test-notify":
        sample = [{"id": "test:1", "source": "4sale", "title": "تنبيه تجريبي – شقة 3 غرف تشطيب جديد في السالمية",
                   "description": "هذا تنبيه تجريبي من مراقب الشقق للتأكد أن قنوات التنبيه تعمل.", "price": 350,
                   "area": "السالمية", "district": "حولي , السالمية", "rooms": 3, "is_new_finish": True, "strong": True,
                   "matched": True, "url": "https://www.q84sale.com/ar/property/for-rent/apartment-for-rent/1",
                   "image": None, "phone": None}]
        notify.send_all(sample, cfg, log, use_macos=not a.no_macos)
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
