"""Safety gate — decides whether a work order may be opened/executed.

A work order may only unlock if there is a RECENT, VALID PPE check:
  * a check exists for the work order (+ worker),
  * safety_glasses_verified is true, and
  * it has not expired.

This is the backend gate. The frontend cannot bypass it.
"""
from datetime import datetime, timezone

from . import ppe_store


def _is_expired(expires_at_iso: str) -> bool:
    if not expires_at_iso:
        return True
    try:
        exp = datetime.fromisoformat(expires_at_iso)
    except ValueError:
        return True
    if exp.tzinfo is None:
        exp = exp.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc) >= exp


def evaluate(work_order_id: str, worker_id: str) -> dict:
    """Gate decision for a specific worker on a work order.

    Returns {allowed, reason, check}.
    """
    check = ppe_store.latest_for(work_order_id, worker_id)
    return _evaluate_check(check, f"worker '{worker_id}'")


def evaluate_wo(work_order_id: str) -> dict:
    """Gate decision for a work order regardless of worker (legacy start gate)."""
    check = ppe_store.latest_for_wo(work_order_id)
    return _evaluate_check(check, "this work order")


def _evaluate_check(check, who: str) -> dict:
    if check is None:
        return {
            "allowed": False,
            "reason": f"No safety-glasses check on record for {who}.",
            "check": None,
        }
    if not check["safety_glasses_verified"]:
        return {
            "allowed": False,
            "reason": f"Safety glasses were NOT verified ({check['reason']}).",
            "check": check,
        }
    if _is_expired(check["expires_at"]):
        return {
            "allowed": False,
            "reason": "Safety-glasses check has expired. Please re-verify.",
            "check": check,
        }
    return {
        "allowed": True,
        "reason": "Safety glasses verified and current.",
        "check": check,
    }
