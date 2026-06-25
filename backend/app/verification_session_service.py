"""Verification session service — the backend truth engine.

Owns the combined gate: a Work Order may open only when BOTH
  1. safety glasses are verified (and not expired), AND
  2. the predefined block sequence is completed correctly.

This module is the ONLY place can_open_work_order is computed. Routes call in;
they never compute truth themselves, and a client-supplied can_open_work_order is
ignored entirely.
"""
import uuid
from datetime import datetime, timezone

from . import block_sequence_service as seq
from . import safety_config, verification_store


def _now():
    return datetime.now(timezone.utc)


def _ppe_current(session: dict) -> bool:
    """True if PPE is verified and the check has not expired."""
    if not session.get("ppe_verified"):
        return False
    exp = session.get("ppe_expires_at")
    if not exp:
        return False
    try:
        dt = datetime.fromisoformat(exp)
    except ValueError:
        return False
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return _now() < dt


def _can_open(session: dict) -> bool:
    return _ppe_current(session) and bool(session.get("sequence_passed"))


# --- lifecycle ---------------------------------------------------------------

def start_session(work_order_id: str, worker_id: str = None) -> dict:
    verification_store.init_db()
    required = safety_config.required_sequence()
    now = verification_store.now_iso()
    session_id = f"vs-{uuid.uuid4().hex[:12]}"
    row = {
        "session_id": session_id,
        "work_order_id": work_order_id,
        "worker_id": worker_id,
        "ppe_verified": 0,
        "ppe_confidence": None,
        "ppe_reason": None,
        "ppe_expires_at": None,
        "sequence_passed": 0,
        "required_sequence_json": _json(required),
        "submitted_sequence_json": _json([]),
        "expected_next_color": required[0] if required else None,
        "can_open_work_order": 0,
        "created_at": now,
        "updated_at": now,
    }
    verification_store.insert_session(row)
    verification_store.record_event(
        session_id=session_id, work_order_id=work_order_id, worker_id=worker_id,
        event_type="session_started", success=True, message="Verification session started.",
    )
    return public(verification_store.get_session(session_id))


def get_session(session_id: str):
    return verification_store.get_session(session_id)


# --- PPE update --------------------------------------------------------------

def apply_ppe_result(session_id: str, result: dict, expires_at: str) -> dict:
    """Record a PPE decision onto the session and recompute can_open."""
    session = verification_store.get_session(session_id)
    if session is None:
        return None
    verified = bool(result["safety_glasses_verified"])
    fields = {
        "ppe_verified": 1 if verified else 0,
        "ppe_confidence": float(result.get("confidence") or 0.0),
        "ppe_reason": result.get("reason"),
        "ppe_expires_at": expires_at if verified else None,
    }
    verification_store.update_session(session_id, fields)
    session = verification_store.get_session(session_id)
    can = _can_open(session)
    verification_store.update_session(session_id, {"can_open_work_order": 1 if can else 0})

    verification_store.record_event(
        session_id=session_id, work_order_id=session["work_order_id"],
        worker_id=session["worker_id"], event_type="ppe_check",
        success=verified, error_type=None if verified else "ppe_not_verified",
        message=result.get("reason", ""),
        payload={"confidence": result.get("confidence"), "mode": result.get("mode")},
    )
    return public(verification_store.get_session(session_id))


# --- block submission --------------------------------------------------------

def submit_block(session_id: str, submitted_color: str) -> dict:
    """Validate a block submission against the required sequence."""
    session = verification_store.get_session(session_id)
    if session is None:
        return None

    outcome = seq.validate_submission(session["submitted_sequence"], submitted_color)

    if outcome["accepted"]:
        verification_store.update_session(session_id, {
            "submitted_sequence_json": _json(outcome["submitted_sequence"]),
            "expected_next_color": outcome["expected_next_color"],
            "sequence_passed": 1 if outcome["sequence_passed"] else 0,
        })
    session = verification_store.get_session(session_id)
    can = _can_open(session)
    verification_store.update_session(session_id, {"can_open_work_order": 1 if can else 0})

    # Audit EVERY attempt, including wrong ones.
    verification_store.record_event(
        session_id=session_id, work_order_id=session["work_order_id"],
        worker_id=session["worker_id"], event_type="block_submit",
        success=outcome["accepted"], error_type=outcome["error_type"],
        message=outcome["message"],
        payload={"submitted_color": safety_config.normalize_color(submitted_color)},
    )

    resp = {
        "session_id": session_id,
        "accepted": outcome["accepted"],
        "submitted_color": outcome["received_color"],
        "submitted_sequence": session["submitted_sequence"],
        "expected_next_color": session["expected_next_color"],
        "sequence_passed": session["sequence_passed"],
        "can_open_work_order": can,
    }
    if not outcome["accepted"]:
        resp.update({
            "error_detected": True,
            "error_type": outcome["error_type"],
            "expected_color": outcome["expected_color"],
            "received_color": outcome["received_color"],
            "message": outcome["message"],
        })
    return resp


# --- status & unlock ---------------------------------------------------------

def status(session_id: str):
    session = verification_store.get_session(session_id)
    if session is None:
        return None
    errors = [
        {
            "error_type": e["error_type"],
            "message": e["message"],
            "created_at": e["created_at"],
        }
        for e in verification_store.events_for_session(session_id)
        if e.get("error_type")
    ]
    pub = public(session)
    pub["errors"] = errors
    return pub


def evaluate_unlock(work_order_id: str) -> dict:
    """Gatekeeper for a Work Order based on its latest verification session."""
    session = verification_store.latest_session_for_wo(work_order_id)
    if session is None:
        return {
            "work_order_id": work_order_id,
            "unlocked": False,
            "can_open_work_order": False,
            "message": "Work Order remains locked. No verification session found.",
            "missing_requirements": ["ppe_verification", "block_sequence"],
            "session_id": None,
        }
    missing = []
    if not _ppe_current(session):
        missing.append("ppe_verification")
    if not session["sequence_passed"]:
        missing.append("block_sequence")
    can = not missing
    return {
        "work_order_id": work_order_id,
        "unlocked": can,
        "can_open_work_order": can,
        "message": (
            "Work Order unlocked. PPE and block sequence verified." if can
            else "Work Order remains locked."
        ),
        "missing_requirements": missing,
        "session_id": session["session_id"],
    }


def latest_session_can_open(work_order_id: str) -> bool:
    session = verification_store.latest_session_for_wo(work_order_id)
    return bool(session and _can_open(session))


# --- serialization -----------------------------------------------------------

def public(session: dict) -> dict:
    """The canonical session shape returned to clients."""
    return {
        "session_id": session["session_id"],
        "work_order_id": session["work_order_id"],
        "worker_id": session["worker_id"],
        "ppe_verified": session["ppe_verified"],
        "ppe_confidence": session["ppe_confidence"],
        "sequence_passed": session["sequence_passed"],
        "required_sequence": session["required_sequence"],
        "submitted_sequence": session["submitted_sequence"],
        "expected_next_color": session["expected_next_color"],
        "can_open_work_order": _can_open(session),
    }


def _json(obj):
    import json
    return json.dumps(obj)
