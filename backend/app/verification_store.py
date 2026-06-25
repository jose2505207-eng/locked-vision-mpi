"""Verification persistence — sessions + audit events (SQLite).

Shares the same database file as ppe_store (data/ppe_checks.db). init_db() is the
migration: it creates verification_sessions and verification_events if missing.
Each session is the durable record of a Work Order's PPE + block-sequence state;
each event is append-only audit evidence (including failed attempts).
"""
import json
import sqlite3
from datetime import datetime, timezone

from . import ppe_store

_SCHEMA = """
CREATE TABLE IF NOT EXISTS verification_sessions (
    session_id             TEXT PRIMARY KEY,
    work_order_id          TEXT NOT NULL,
    worker_id              TEXT,
    ppe_verified           INTEGER NOT NULL DEFAULT 0,
    ppe_confidence         REAL,
    ppe_reason             TEXT,
    ppe_expires_at         TEXT,
    sequence_passed        INTEGER NOT NULL DEFAULT 0,
    required_sequence_json TEXT NOT NULL,
    submitted_sequence_json TEXT NOT NULL,
    expected_next_color    TEXT,
    can_open_work_order    INTEGER NOT NULL DEFAULT 0,
    created_at             TEXT NOT NULL,
    updated_at             TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS verification_events (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id    TEXT,
    work_order_id TEXT,
    worker_id     TEXT,
    event_type    TEXT NOT NULL,
    payload_json  TEXT,
    success       INTEGER,
    error_type    TEXT,
    message       TEXT,
    created_at    TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_vsessions_wo ON verification_sessions (work_order_id, created_at);
CREATE INDEX IF NOT EXISTS idx_vevents_session ON verification_events (session_id, id);
"""


def _connect():
    # Reference ppe_store.DB_PATH dynamically so the DB location (e.g. tests)
    # can be overridden in one place.
    conn = sqlite3.connect(ppe_store.DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def init_db():
    """Idempotent migration for the verification tables."""
    with _connect() as conn:
        conn.executescript(_SCHEMA)


def _session_to_dict(row):
    if row is None:
        return None
    d = dict(row)
    d["ppe_verified"] = bool(d["ppe_verified"])
    d["sequence_passed"] = bool(d["sequence_passed"])
    d["can_open_work_order"] = bool(d["can_open_work_order"])
    d["required_sequence"] = json.loads(d.pop("required_sequence_json") or "[]")
    d["submitted_sequence"] = json.loads(d.pop("submitted_sequence_json") or "[]")
    return d


def insert_session(session: dict):
    with _connect() as conn:
        conn.execute(
            """INSERT INTO verification_sessions
               (session_id, work_order_id, worker_id, ppe_verified, ppe_confidence,
                ppe_reason, ppe_expires_at, sequence_passed, required_sequence_json,
                submitted_sequence_json, expected_next_color, can_open_work_order,
                created_at, updated_at)
               VALUES (:session_id, :work_order_id, :worker_id, :ppe_verified,
                :ppe_confidence, :ppe_reason, :ppe_expires_at, :sequence_passed,
                :required_sequence_json, :submitted_sequence_json,
                :expected_next_color, :can_open_work_order, :created_at, :updated_at)""",
            session,
        )
        conn.commit()


def update_session(session_id: str, fields: dict):
    fields = dict(fields)
    fields["updated_at"] = now_iso()
    sets = ", ".join(f"{k} = :{k}" for k in fields)
    fields["session_id"] = session_id
    with _connect() as conn:
        conn.execute(
            f"UPDATE verification_sessions SET {sets} WHERE session_id = :session_id",
            fields,
        )
        conn.commit()


def get_session(session_id: str):
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM verification_sessions WHERE session_id = ?", (session_id,)
        ).fetchone()
    return _session_to_dict(row)


def latest_session_for_wo(work_order_id: str):
    with _connect() as conn:
        row = conn.execute(
            """SELECT * FROM verification_sessions
               WHERE work_order_id = ? ORDER BY created_at DESC, rowid DESC LIMIT 1""",
            (work_order_id,),
        ).fetchone()
    return _session_to_dict(row)


def record_event(*, session_id, work_order_id, worker_id, event_type,
                 payload=None, success=None, error_type=None, message=""):
    with _connect() as conn:
        conn.execute(
            """INSERT INTO verification_events
               (session_id, work_order_id, worker_id, event_type, payload_json,
                success, error_type, message, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (session_id, work_order_id, worker_id, event_type,
             json.dumps(payload or {}),
             None if success is None else (1 if success else 0),
             error_type, message, now_iso()),
        )
        conn.commit()


def events_for_session(session_id: str):
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM verification_events WHERE session_id = ? ORDER BY id",
            (session_id,),
        ).fetchall()
    return [dict(r) for r in rows]
