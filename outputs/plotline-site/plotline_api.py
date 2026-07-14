#!/usr/bin/env python3
"""Scalable local backend for Plotline.

Runs with Python 3.11 standard library only:
  python3 plotline_api.py --port 8088
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import uuid
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parent
DB_PATH = Path(os.environ.get("PLOTLINE_DB", ROOT / "plotline.sqlite3"))
ADMIN_TOKEN = os.environ.get("PLOTLINE_ADMIN_TOKEN", "dev-admin-token")

PRICING = {
    "essentials": {"label": "Essentials itinerary", "starting_fee": 300},
    "full_plot": {"label": "Full plot", "starting_fee": 900},
    "concierge": {"label": "Concierge plot", "starting_fee": 2000},
}


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    db.execute("PRAGMA journal_mode = WAL")
    return db


def init_db() -> None:
    with conn() as db:
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS trip_briefs (
              id TEXT PRIMARY KEY,
              mood TEXT NOT NULL,
              travel_window TEXT NOT NULL,
              tier TEXT NOT NULL,
              status TEXT NOT NULL DEFAULT 'new',
              traveler_email TEXT,
              notes TEXT,
              estimated_fee INTEGER NOT NULL,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS itinerary_drafts (
              id TEXT PRIMARY KEY,
              brief_id TEXT NOT NULL,
              title TEXT NOT NULL,
              character TEXT NOT NULL,
              destination TEXT NOT NULL,
              days_json TEXT NOT NULL,
              pdf_status TEXT NOT NULL DEFAULT 'not_started',
              web_status TEXT NOT NULL DEFAULT 'draft',
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL,
              FOREIGN KEY (brief_id) REFERENCES trip_briefs(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS concierge_requests (
              id TEXT PRIMARY KEY,
              brief_id TEXT NOT NULL,
              urgency TEXT NOT NULL,
              request TEXT NOT NULL,
              status TEXT NOT NULL DEFAULT 'open',
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL,
              FOREIGN KEY (brief_id) REFERENCES trip_briefs(id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_briefs_status ON trip_briefs(status);
            CREATE INDEX IF NOT EXISTS idx_itinerary_brief ON itinerary_drafts(brief_id);
            CREATE INDEX IF NOT EXISTS idx_concierge_brief ON concierge_requests(brief_id);
            """
        )


def to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    item = dict(row)
    if "days_json" in item:
        item["days"] = json.loads(item.pop("days_json"))
    return item


def fee_for(tier: str, travel_window: str, notes: str = "") -> int:
    fee = PRICING[tier]["starting_fee"]
    text = f"{travel_window} {notes}".lower()
    if re.search(r"\b(10|11|12|13|14|two weeks|2 weeks)\b", text):
        fee += 250
    if any(word in text for word in ["honeymoon", "family", "multi-city", "dietary"]):
        fee += 180
    return fee


class Handler(BaseHTTPRequestHandler):
    server_version = "PlotlineAPI/1.0"

    def log_message(self, fmt: str, *args: Any) -> None:
        if os.environ.get("PLOTLINE_DEBUG") == "1":
            super().log_message(fmt, *args)

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.cors()
        self.end_headers()

    def do_GET(self) -> None:
        path, query = urlparse(self.path).path, parse_qs(urlparse(self.path).query)
        if path == "/health":
            return self.json({"ok": True, "service": "plotline-api", "time": now()})
        if path == "/api/services/pricing":
            return self.json({"tiers": PRICING})
        if path == "/api/briefs":
            return self.list_briefs()
        if m := re.fullmatch(r"/api/briefs/([^/]+)", path):
            return self.get_brief(m.group(1))
        if path == "/api/itineraries":
            return self.list_itineraries(query.get("brief_id", [None])[0])
        if m := re.fullmatch(r"/api/itineraries/([^/]+)", path):
            return self.get_itinerary(m.group(1))
        if path == "/api/concierge/requests":
            return self.list_concierge()
        return self.static(path)

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        if path == "/api/briefs":
            return self.create_brief()
        if path == "/api/itineraries":
            return self.create_itinerary()
        if path == "/api/concierge/requests":
            return self.create_concierge()
        return self.error(404, "Endpoint not found")

    def do_PATCH(self) -> None:
        path = urlparse(self.path).path
        if m := re.fullmatch(r"/api/briefs/([^/]+)/status", path):
            return self.update_status(m.group(1))
        return self.error(404, "Endpoint not found")

    def body(self) -> dict[str, Any] | None:
        try:
            raw = self.rfile.read(int(self.headers.get("Content-Length", "0")))
            return json.loads(raw or b"{}")
        except (ValueError, json.JSONDecodeError):
            self.error(400, "Invalid JSON body")
            return None

    def json(self, payload: dict[str, Any], status: int = 200) -> None:
        data = json.dumps(payload, indent=2).encode()
        self.send_response(status)
        self.cors()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def error(self, status: int, message: str) -> None:
        self.json({"error": message, "status": status}, status)

    def cors(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,PATCH,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type,Authorization")

    def admin(self) -> bool:
        if self.headers.get("Authorization") == f"Bearer {ADMIN_TOKEN}":
            return True
        self.error(401, "Admin token required")
        return False

    def list_briefs(self) -> None:
        if not self.admin():
            return
        with conn() as db:
            rows = db.execute("SELECT * FROM trip_briefs ORDER BY created_at DESC").fetchall()
        self.json({"briefs": [to_dict(row) for row in rows]})

    def get_brief(self, brief_id: str) -> None:
        with conn() as db:
            brief = to_dict(db.execute("SELECT * FROM trip_briefs WHERE id=?", (brief_id,)).fetchone())
            if not brief:
                return self.error(404, "Brief not found")
            itineraries = [to_dict(r) for r in db.execute("SELECT * FROM itinerary_drafts WHERE brief_id=?", (brief_id,))]
            requests = [to_dict(r) for r in db.execute("SELECT * FROM concierge_requests WHERE brief_id=?", (brief_id,))]
        self.json({"brief": brief, "itineraries": itineraries, "concierge_requests": requests})

    def create_brief(self) -> None:
        data = self.body()
        if data is None:
            return
        missing = [k for k in ["mood", "travel_window", "tier"] if not str(data.get(k, "")).strip()]
        if missing:
            return self.error(400, "Missing fields: " + ", ".join(missing))
        tier = str(data["tier"]).strip()
        if tier not in PRICING:
            return self.error(400, "Unknown planning tier")
        ts = now()
        brief = {
            "id": "brief_" + uuid.uuid4().hex[:12],
            "mood": str(data["mood"]).strip(),
            "travel_window": str(data["travel_window"]).strip(),
            "tier": tier,
            "status": "new",
            "traveler_email": str(data.get("traveler_email", "")).strip() or None,
            "notes": str(data.get("notes", "")).strip() or None,
            "estimated_fee": fee_for(tier, str(data["travel_window"]), str(data.get("notes", ""))),
            "created_at": ts,
            "updated_at": ts,
        }
        with conn() as db:
            db.execute(
                """INSERT INTO trip_briefs
                (id,mood,travel_window,tier,status,traveler_email,notes,estimated_fee,created_at,updated_at)
                VALUES (:id,:mood,:travel_window,:tier,:status,:traveler_email,:notes,:estimated_fee,:created_at,:updated_at)""",
                brief,
            )
        self.json({"brief": brief}, 201)

    def update_status(self, brief_id: str) -> None:
        if not self.admin():
            return
        data = self.body()
        if data is None:
            return
        status = str(data.get("status", "")).strip()
        if status not in {"new", "qualified", "designing", "delivered", "archived"}:
            return self.error(400, "Invalid status")
        with conn() as db:
            cur = db.execute("UPDATE trip_briefs SET status=?, updated_at=? WHERE id=?", (status, now(), brief_id))
            if cur.rowcount == 0:
                return self.error(404, "Brief not found")
            brief = to_dict(db.execute("SELECT * FROM trip_briefs WHERE id=?", (brief_id,)).fetchone())
        self.json({"brief": brief})

    def list_itineraries(self, brief_id: str | None) -> None:
        if not self.admin():
            return
        sql, params = "SELECT * FROM itinerary_drafts", ()
        if brief_id:
            sql, params = sql + " WHERE brief_id=?", (brief_id,)
        with conn() as db:
            rows = db.execute(sql + " ORDER BY created_at DESC", params).fetchall()
        self.json({"itineraries": [to_dict(row) for row in rows]})

    def get_itinerary(self, itinerary_id: str) -> None:
        with conn() as db:
            item = to_dict(db.execute("SELECT * FROM itinerary_drafts WHERE id=?", (itinerary_id,)).fetchone())
        if not item:
            return self.error(404, "Itinerary not found")
        self.json({"itinerary": item})

    def create_itinerary(self) -> None:
        if not self.admin():
            return
        data = self.body()
        if data is None:
            return
        missing = [k for k in ["brief_id", "title", "character", "destination", "days"] if not data.get(k)]
        if missing:
            return self.error(400, "Missing fields: " + ", ".join(missing))
        if not isinstance(data["days"], list):
            return self.error(400, "days must be a list")
        ts = now()
        draft = {
            "id": "itin_" + uuid.uuid4().hex[:12],
            "brief_id": str(data["brief_id"]).strip(),
            "title": str(data["title"]).strip(),
            "character": str(data["character"]).strip(),
            "destination": str(data["destination"]).strip(),
            "days_json": json.dumps(data["days"]),
            "pdf_status": str(data.get("pdf_status", "not_started")),
            "web_status": str(data.get("web_status", "draft")),
            "created_at": ts,
            "updated_at": ts,
        }
        try:
            with conn() as db:
                db.execute(
                    """INSERT INTO itinerary_drafts
                    (id,brief_id,title,character,destination,days_json,pdf_status,web_status,created_at,updated_at)
                    VALUES (:id,:brief_id,:title,:character,:destination,:days_json,:pdf_status,:web_status,:created_at,:updated_at)""",
                    draft,
                )
        except sqlite3.IntegrityError:
            return self.error(404, "Brief not found")
        draft["days"] = data["days"]
        del draft["days_json"]
        self.json({"itinerary": draft}, 201)

    def list_concierge(self) -> None:
        if not self.admin():
            return
        with conn() as db:
            rows = db.execute("SELECT * FROM concierge_requests ORDER BY created_at DESC").fetchall()
        self.json({"requests": [to_dict(row) for row in rows]})

    def create_concierge(self) -> None:
        data = self.body()
        if data is None:
            return
        missing = [k for k in ["brief_id", "urgency", "request"] if not str(data.get(k, "")).strip()]
        if missing:
            return self.error(400, "Missing fields: " + ", ".join(missing))
        ts = now()
        item = {
            "id": "concierge_" + uuid.uuid4().hex[:12],
            "brief_id": str(data["brief_id"]).strip(),
            "urgency": str(data["urgency"]).strip(),
            "request": str(data["request"]).strip(),
            "status": "open",
            "created_at": ts,
            "updated_at": ts,
        }
        try:
            with conn() as db:
                db.execute(
                    """INSERT INTO concierge_requests
                    (id,brief_id,urgency,request,status,created_at,updated_at)
                    VALUES (:id,:brief_id,:urgency,:request,:status,:created_at,:updated_at)""",
                    item,
                )
        except sqlite3.IntegrityError:
            return self.error(404, "Brief not found")
        self.json({"request": item}, 201)

    def static(self, path: str) -> None:
        rel = "index.html" if path in {"", "/"} else path.lstrip("/")
        target = (ROOT / rel).resolve()
        if ROOT not in target.parents and target != ROOT:
            return self.error(403, "Forbidden")
        if not target.exists() or target.name == Path(__file__).name:
            target = ROOT / "index.html"
        types = {".html": "text/html; charset=utf-8", ".css": "text/css", ".js": "application/javascript", ".png": "image/png"}
        body = target.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", types.get(target.suffix, "application/octet-stream"))
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", "8088")))
    args = parser.parse_args()
    init_db()
    print(f"Plotline API running at http://{args.host}:{args.port}")
    print(f"Admin token: {ADMIN_TOKEN}")
    ThreadingHTTPServer((args.host, args.port), Handler).serve_forever()


if __name__ == "__main__":
    main()
