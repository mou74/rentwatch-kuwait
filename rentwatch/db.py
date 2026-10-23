import sqlite3
from datetime import datetime, timezone

SCHEMA = """
CREATE TABLE IF NOT EXISTS listings (
    id TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    source_id TEXT NOT NULL,
    url TEXT,
    title TEXT,
    description TEXT,
    price INTEGER,
    area TEXT,
    district TEXT,
    rooms INTEGER,
    posted_at TEXT,
    image TEXT,
    phone TEXT,
    is_new_finish INTEGER DEFAULT 0,
    matched INTEGER DEFAULT 0,
    strong INTEGER DEFAULT 0,
    reasons TEXT,
    first_seen TEXT NOT NULL,
    last_seen TEXT NOT NULL,
    notified INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at TEXT,
    finished_at TEXT,
    fetched INTEGER,
    new_matches INTEGER,
    errors TEXT
);
"""


def now_iso():
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


class Store:
    def __init__(self, path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(path))
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)

    def upsert(self, listing):
        """Insert or refresh a listing. Returns True when the listing is new."""
        ts = now_iso()
        cur = self.conn.execute("SELECT id FROM listings WHERE id=?", (listing["id"],))
        exists = cur.fetchone() is not None
        if exists:
            self.conn.execute(
                """UPDATE listings SET last_seen=?, price=COALESCE(?, price), title=?, description=?,
                   rooms=COALESCE(?, rooms), is_new_finish=?, matched=?, strong=?, reasons=?, image=COALESCE(?, image),
                   area=?, district=COALESCE(?, district)
                   WHERE id=?""",
                (ts, listing.get("price"), listing.get("title"), listing.get("description"),
                 listing.get("rooms"), int(listing.get("is_new_finish", False)), int(listing.get("matched", False)),
                 int(listing.get("strong", False)), listing.get("reasons"), listing.get("image"),
                 listing.get("area"), listing.get("district"), listing["id"]),
            )
        else:
            self.conn.execute(
                """INSERT INTO listings (id, source, source_id, url, title, description, price, area, district, rooms,
                   posted_at, image, phone, is_new_finish, matched, strong, reasons, first_seen, last_seen, notified)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,0)""",
                (listing["id"], listing["source"], str(listing["source_id"]), listing.get("url"), listing.get("title"),
                 listing.get("description"), listing.get("price"), listing.get("area"), listing.get("district"),
                 listing.get("rooms"), listing.get("posted_at"), listing.get("image"), listing.get("phone"),
                 int(listing.get("is_new_finish", False)), int(listing.get("matched", False)),
                 int(listing.get("strong", False)), listing.get("reasons"), ts, ts),
            )
        return not exists

    def pending_alerts(self, strong_only):
        q = "SELECT * FROM listings WHERE matched=1 AND notified=0"
        if strong_only:
            q += " AND strong=1"
        return [dict(r) for r in self.conn.execute(q + " ORDER BY first_seen DESC")]

    def mark_notified(self, ids):
        self.conn.executemany("UPDATE listings SET notified=1 WHERE id=?", [(i,) for i in ids])

    def matches(self, limit=300):
        return [dict(r) for r in self.conn.execute(
            "SELECT * FROM listings WHERE matched=1 ORDER BY strong DESC, first_seen DESC LIMIT ?", (limit,))]

    def recent_all(self, limit=200):
        return [dict(r) for r in self.conn.execute(
            "SELECT * FROM listings ORDER BY first_seen DESC LIMIT ?", (limit,))]

    def stats(self):
        r = self.conn.execute(
            "SELECT COUNT(*) total, SUM(matched) matched, SUM(strong) strong FROM listings").fetchone()
        last = self.conn.execute("SELECT * FROM runs ORDER BY id DESC LIMIT 1").fetchone()
        return {"total": r["total"] or 0, "matched": r["matched"] or 0, "strong": r["strong"] or 0,
                "last_run": dict(last) if last else None}

    def log_run(self, started, fetched, new_matches, errors):
        self.conn.execute("INSERT INTO runs (started_at, finished_at, fetched, new_matches, errors) VALUES (?,?,?,?,?)",
                          (started, now_iso(), fetched, new_matches, "\n".join(errors) if errors else None))

    def commit(self):
        self.conn.commit()
