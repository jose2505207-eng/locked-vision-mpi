"""Optional Deepgram voice commands.

Two layers:
  * intent recognition (LOCAL, always works) — maps text to one of the three
    supported commands: verify_step, repeat_instruction, status.
  * transcription (Deepgram) — turns audio into text; only when active.

Voice NEVER bypasses validation. Recognizing "verify step" just tells the
frontend to call the normal /validate-step endpoint — the backend still decides.
"""
import logging
import os

from . import sponsor_flags

log = logging.getLogger("sponsors")

SUPPORTED_COMMANDS = ["verify_step", "repeat_instruction", "status"]


def recognize_intent(text: str):
    """Deterministic keyword -> command. Returns a command id or None."""
    t = (text or "").lower()
    if "verify" in t or "check step" in t or "check the step" in t:
        return "verify_step"
    if "repeat" in t or "again" in t or "say that" in t:
        return "repeat_instruction"
    if "status" in t or "where are we" in t or "progress" in t:
        return "status"
    return None


def transcribe(audio_bytes: bytes, content_type: str = "audio/wav") -> dict:
    """Transcribe audio via Deepgram. Returns {transcript, source}.

    If inactive or the SDK/API fails, returns transcript=None with a reason —
    never raises.
    """
    if not sponsor_flags.active("deepgram_voice"):
        return {"transcript": None, "source": "inactive",
                "reason": "ENABLE_DEEPGRAM_VOICE off or DEEPGRAM_API_KEY missing"}
    try:
        from deepgram import DeepgramClient, PrerecordedOptions  # lazy
        dg = DeepgramClient(os.getenv("DEEPGRAM_API_KEY"))
        resp = dg.listen.rest.v("1").transcribe_file(
            {"buffer": audio_bytes, "mimetype": content_type},
            PrerecordedOptions(model="nova-2", smart_format=True),
        )
        text = resp.results.channels[0].alternatives[0].transcript
        return {"transcript": text, "source": "deepgram"}
    except Exception as e:
        log.warning("[deepgram] transcription failed (soft): %s", e)
        return {"transcript": None, "source": "error", "reason": str(e)}
