"""Sponsor-stack HTTP surface (all under /api).

  GET  /api/sponsors/status     -> flags, key presence, live adapter state

Assistant (Claude) and voice (Deepgram) endpoints are added to this router in
their respective phases. Everything here is observational / advisory and never
changes a validation decision.
"""
import logging

from fastapi import APIRouter, Body, HTTPException

from . import sponsor_flags

log = logging.getLogger("sponsors")

router = APIRouter(prefix="/api", tags=["sponsors"])


@router.get("/sponsors/status")
def sponsors_status():
    """Honest report of what is enabled, configured, and actually active.

    A flag that is on but missing its keys reports active=false (never crashes).
    """
    snap = sponsor_flags.snapshot()

    # Live Redis connection probe (only if enabled + configured).
    redis_state = {"enabled": sponsor_flags.is_enabled("redis_events"), "connected": False}
    if sponsor_flags.active("redis_events"):
        try:
            from . import redis_event_bus
            redis_state = redis_event_bus.connection_status()
        except Exception as e:  # pragma: no cover
            redis_state = {"enabled": True, "connected": False, "error": str(e)}
    snap["redis"] = redis_state

    # Flat convenience booleans the frontend badges read directly.
    snap["badges"] = {
        "sentry": sponsor_flags.active("sentry"),
        "redis_events": sponsor_flags.active("redis_events"),
        "claude_assist": sponsor_flags.active("claude_assist"),
        "arize_logging": sponsor_flags.active("arize_logging"),
        "orkes_shadow": sponsor_flags.active("orkes_shadow"),
        "deepgram_voice": sponsor_flags.active("deepgram_voice"),
        "runpod_detector": sponsor_flags.active("runpod_detector"),
    }
    return snap


@router.get("/sponsors/test-error")
def sponsors_test_error():
    """Dev-only: raise a captured test error so Sentry wiring can be verified.

    Only allowed when Sentry is active, so it can't be used to spam errors in a
    plain demo. The raised exception is reported to Sentry (if installed) and
    returned as a normal 400 — it does not affect any work order.
    """
    if not sponsor_flags.active("sentry"):
        raise HTTPException(status_code=409, detail="Sentry is inactive — nothing to test.")
    raise RuntimeError("Locked Vision MPI — Sentry test error (intentional, safe).")


# --- Claude operator assistant (advisory; never decides pass/fail) -----------

@router.post("/assistant/operator-instruction")
def operator_instruction(payload: dict = Body(default={})):
    """Turn a structured step state into one short operator instruction.

    Claude only EXPLAINS the backend's verdict. With the flag off or no key, a
    deterministic local fallback is returned (source='fallback').
    """
    from . import claude_assistant
    return claude_assistant.operator_instruction(payload or {})


@router.post("/assistant/audit-summary")
def audit_summary(payload: dict = Body(default={})):
    """Summarize an audit-log entry list (advisory)."""
    from . import claude_assistant
    entries = (payload or {}).get("entries", [])
    return claude_assistant.audit_summary(entries)
