"""Sponsor-stack HTTP surface (all under /api).

  GET  /api/sponsors/status     -> flags, key presence, live adapter state

Assistant (Claude) and voice (Deepgram) endpoints are added to this router in
their respective phases. Everything here is observational / advisory and never
changes a validation decision.
"""
import logging

from fastapi import APIRouter

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
