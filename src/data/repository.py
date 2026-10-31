from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from src.domain.models import SecurityEvent


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB = ROOT / "data" / "secops.db"
SAMPLE_FILE = Path(__file__).with_name("sample_events.json")


def database_path() -> Path:
    configured = os.getenv("SECOPS_DATABASE_PATH")
    path = Path(configured) if configured else DEFAULT_DB
    if not path.is_absolute():
        path = ROOT / path
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def connect() -> sqlite3.Connection:
    connection = sqlite3.connect(database_path())
    connection.row_factory = sqlite3.Row
    return connection


def initialize() -> None:
    with connect() as db:
        db.execute("""CREATE TABLE IF NOT EXISTS events (
            event_id TEXT PRIMARY KEY, source TEXT NOT NULL, timestamp TEXT NOT NULL,
            actor TEXT, event_type TEXT NOT NULL, payload TEXT NOT NULL
        )""")
        db.execute("""CREATE TABLE IF NOT EXISTS investigations (
            investigation_id TEXT PRIMARY KEY, created_at TEXT NOT NULL,
            question TEXT NOT NULL, alert_id TEXT, report TEXT NOT NULL
        )""")
        if db.execute("SELECT COUNT(*) FROM events").fetchone()[0] == 0:
            samples = json.loads(SAMPLE_FILE.read_text(encoding="utf-8"))
            db.executemany(
                "INSERT INTO events VALUES (?, ?, ?, ?, ?, ?)",
                [
                    (e["event_id"], e["source"], e["timestamp"], e.get("actor"),
                     e["event_type"], json.dumps(e))
                    for e in samples
                ],
            )


def add_event(event: SecurityEvent) -> None:
    payload = event.model_dump(mode="json")
    with connect() as db:
        db.execute(
            "INSERT OR REPLACE INTO events VALUES (?, ?, ?, ?, ?, ?)",
            (event.event_id, event.source, event.timestamp.isoformat(), event.actor,
             event.event_type, json.dumps(payload)),
        )


def get_events() -> list[dict[str, Any]]:
    with connect() as db:
        rows = db.execute("SELECT payload FROM events ORDER BY timestamp").fetchall()
    return [json.loads(row["payload"]) for row in rows]


def save_investigation(question: str, alert_id: str | None, report: dict[str, Any]) -> dict[str, Any]:
    item = {
        "investigation_id": str(uuid4()),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "question": question,
        "alert_id": alert_id,
        **report,
    }
    with connect() as db:
        db.execute(
            "INSERT INTO investigations VALUES (?, ?, ?, ?, ?)",
            (item["investigation_id"], item["created_at"], question, alert_id,
             json.dumps(item)),
        )
    return item


def get_investigations() -> list[dict[str, Any]]:
    with connect() as db:
        rows = db.execute(
            "SELECT report FROM investigations ORDER BY created_at DESC LIMIT 50"
        ).fetchall()
    return [json.loads(row["report"]) for row in rows]
