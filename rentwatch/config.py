import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = Path(os.environ.get("RENTWATCH_CONFIG", ROOT / "config.json"))

DEFAULTS = {
    "areas": [],
    "price_min": 300,
    "price_max": 400,
    "rooms": 3,
    "include_unpriced": True,
    "require_new_finish_for_alerts": True,
    "max_pages_per_source": 4,
    "request_timeout": 30,
    "db_path": "data/rentwatch.db",
    "dashboard_path": "dashboard/index.html",
    "notify": {"macos": True, "email": {"enabled": False}, "telegram": {"enabled": False}},
}


def load_config():
    cfg = json.loads(json.dumps(DEFAULTS))
    if CONFIG_PATH.exists():
        user = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        for k, v in user.items():
            if isinstance(v, dict) and isinstance(cfg.get(k), dict):
                cfg[k].update(v)
            else:
                cfg[k] = v
    # config.local.json (git-ignored) overrides config.json on this machine only
    local_path = CONFIG_PATH.with_name("config.local.json")
    if local_path.exists():
        for k, v in json.loads(local_path.read_text(encoding="utf-8")).items():
            if isinstance(v, dict) and isinstance(cfg.get(k), dict):
                cfg[k].update(v)
            else:
                cfg[k] = v
    # secrets.json (git-ignored) holds passwords/tokens: {"email": {...}, "telegram": {...}}
    secrets_path = CONFIG_PATH.with_name("secrets.json")
    if secrets_path.exists():
        sec = json.loads(secrets_path.read_text(encoding="utf-8"))
        for ch in ("email", "telegram"):
            if isinstance(sec.get(ch), dict):
                cfg["notify"].setdefault(ch, {}).update({k: v for k, v in sec[ch].items() if v not in ("", None)})
    # Environment variables override secrets (useful for GitHub Actions)
    env = os.environ
    email = cfg["notify"].setdefault("email", {})
    tg = cfg["notify"].setdefault("telegram", {})
    if env.get("RENTWATCH_SMTP_USER"):
        email["smtp_user"] = env["RENTWATCH_SMTP_USER"]
    if env.get("RENTWATCH_SMTP_PASSWORD"):
        email["smtp_password"] = env["RENTWATCH_SMTP_PASSWORD"]
    if env.get("RENTWATCH_EMAIL_TO"):
        email["to"] = env["RENTWATCH_EMAIL_TO"]
    if env.get("RENTWATCH_TELEGRAM_TOKEN"):
        tg["bot_token"] = env["RENTWATCH_TELEGRAM_TOKEN"]
    if env.get("RENTWATCH_TELEGRAM_CHAT_ID"):
        tg["chat_id"] = env["RENTWATCH_TELEGRAM_CHAT_ID"]
    if email.get("smtp_user") and email.get("smtp_password") and email.get("to"):
        email.setdefault("enabled", True)
    if tg.get("bot_token") and tg.get("chat_id"):
        tg.setdefault("enabled", True)
    cfg["_root"] = str(ROOT)
    return cfg


def abs_path(cfg, key):
    p = Path(cfg[key])
    return p if p.is_absolute() else Path(cfg["_root"]) / p
