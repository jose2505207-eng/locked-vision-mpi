"""PPE check persistence — SQLite store for the ppe_checks table.

Lightweight, dependency-free (stdlib sqlite3). init_db() acts as the migration:
it creates the table if it does not exist. Each PPE check is stored as audit
evidence with its decision, confidence, raw predictions, and the evidence image
path.
"""
import json
import os
import sqlite3
from datetime import datetime, timezone

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "ppe_checks.db")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS ppe_checks (
    id                       INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id               TEXT,
    work_order_id            TEXT NOT NULL,
    worker_id                TEXT NOT NULL,
    safety_glasses_verified  INTEGER NOT NULL,
    confidence               REAL NOT NULL,
    reason                   TEXT,
    predictions_json         TEXT,
    image_path               TEXT,
    created_at               TEXT NOT NULL,
    expires_at               TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_ppe_wo_worker
    ON ppe_checks (work_order_id, worker_id, id);
"""


def _connect():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create the ppe_checks table if needed (idempotent migration)."""
    with _connect() as conn:
        conn.executescript(_SCHEMA)
        # Migration for pre-existing DBs that lack session_id.
        cols = [r[1] for r in conn.execute("PRAGMA table_info(ppe_checks)").fetchall()]
        if "session_id" not in cols:
            conn.execute("ALTER TABLE ppe_checks ADD COLUMN session_id TEXT")
        conn.commit()


def insert_check(*, work_order_id, worker_id, verified, confidence, reason,
                 predictions, image_path, created_at, expires_at, session_id=None) -> int:
    with _connect() as conn:
        cur = conn.execute(
            """INSERT INTO ppe_checks
               (session_id, work_order_id, worker_id, safety_glasses_verified,
                confidence, reason, predictions_json, image_path, created_at, expires_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (session_id, work_order_id, worker_id, 1 if verified else 0,
             float(confidence), reason, json.dumps(predictions), image_path,
             created_at, expires_at),
        )
        conn.commit()
        return cur.lastrowid


def _row_to_dict(row):
    if row is None:
        return None
    d = dict(row)
    d["safety_glasses_verified"] = bool(d["safety_glasses_verified"])
    try:
        d["predictions"] = json.loads(d.pop("predictions_json") or "[]")
    except Exception:
        d["predictions"] = []
    return d


def latest_for(work_order_id, worker_id):
    """Most recent check for a specific worker on a work order."""
    with _connect() as conn:
        row = conn.execute(
            """SELECT * FROM ppe_checks
               WHERE work_order_id = ? AND worker_id = ?
               ORDER BY id DESC LIMIT 1""",
            (work_order_id, worker_id),
        ).fetchone()
    return _row_to_dict(row)


def latest_for_wo(work_order_id):
    """Most recent check for a work order, regardless of worker."""
    with _connect() as conn:
        row = conn.execute(
            """SELECT * FROM ppe_checks
               WHERE work_order_id = ?
               ORDER BY id DESC LIMIT 1""",
            (work_order_id,),
        ).fetchone()
    return _row_to_dict(row)


def now_iso():
    return datetime.now(timezone.utc).isoformat()
