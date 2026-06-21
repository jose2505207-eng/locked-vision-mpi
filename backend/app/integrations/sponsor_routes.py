"""Sponsor-stack HTTP surface (all under /api).

  GET  /api/sponsors/status     -> flags, key presence, live adapter state

Assistant (Claude) and voice (Deepgram) endpoints are added to this router in
their respective phases. Everything here is observational / advisory and never
changes a validation decision.
"""
import logging

from fastapi import APIRouter, Body, File, HTTPException, UploadFile

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

    # Orkes shadow workflow summary (in-memory mirror; never authoritative).
    if sponsor_flags.active("orkes_shadow"):
        try:
            from . import orkes_workflow
            snap["orkes"] = orkes_workflow.get_status()
        except Exception as e:  # pragma: no cover
            snap["orkes"] = {"active": True, "error": str(e)}

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


# --- Deepgram voice commands (optional; never bypasses validation) -----------

@router.post("/voice/command")
def voice_command(payload: dict = Body(default={})):
    """Recognize a voice-command intent from text (local, always available).

    The frontend feeds in a transcript (or types it); we return the intent so it
    can call the NORMAL endpoint (e.g. /validate-step). Voice never decides.
    """
    from . import deepgram_voice
    text = (payload or {}).get("text", "")
    return {
        "intent": deepgram_voice.recognize_intent(text),
        "text": text,
        "supported": deepgram_voice.SUPPORTED_COMMANDS,
        "transcription_active": sponsor_flags.active("deepgram_voice"),
    }


@router.post("/voice/transcribe")
async def voice_transcribe(audio: UploadFile = File(...)):
    """Transcribe an audio clip via Deepgram, then recognize the intent.

    Returns transcript=None with a reason if Deepgram is inactive — never errors.
    """
    from . import deepgram_voice
    data = await audio.read()
    result = deepgram_voice.transcribe(data, audio.content_type or "audio/wav")
    result["intent"] = deepgram_voice.recognize_intent(result.get("transcript") or "")
    return result
