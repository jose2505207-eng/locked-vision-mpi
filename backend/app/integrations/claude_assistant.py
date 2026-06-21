"""Claude operator assistant (ADVISORY ONLY).

Claude NEVER decides pass/fail. It only rephrases the decision the backend has
already made into a short operator instruction, or summarizes the audit log.
If ENABLE_CLAUDE_ASSIST is off, ANTHROPIC_API_KEY is missing, or the SDK/API
fails, a deterministic LOCAL fallback is returned — so the feature always
responds and never blocks anything.
"""
import logging
import os

from . import sponsor_flags

log = logging.getLogger("sponsors")

_DEFAULT_MODEL = "claude-opus-4-8"

_SYSTEM = (
    "You are a manufacturing line assistant for a LEGO assembly station. "
    "You DO NOT decide whether a step passes or fails — the backend already "
    "decided that. Given the structured state and the backend's verdict, reply "
    "with ONE short, calm instruction (max 2 sentences) telling the operator "
    "what to physically do next. Never invent detections or change the verdict."
)


def _humanize(name):
    return (name or "").replace("_", " ") if name else None


def _fallback_instruction(state: dict) -> str:
    """Deterministic local instruction built from the structured state.

    Prefers the backend's own message (already clear and authoritative).
    """
    if state.get("message"):
        return state["message"]
    status = (state.get("validation_status") or "").lower()
    expected = _humanize(state.get("expected_block"))
    if status == "passed":
        return "Step verified. Proceed to the next step."
    if expected and state.get("in_assembly_zone") is False:
        return (f"{expected} is not in the assembly zone yet. Move {expected} "
                f"into the assembly zone, then press Verify Step.")
    if expected:
        return f"Place {expected} as the current step requires, then press Verify Step."
    return "Check the station against the current step, then press Verify Step."


def _fallback_summary(entries: list) -> str:
    passed = sum(1 for e in entries if e.get("status") == "passed")
    blocked = sum(1 for e in entries if e.get("status") == "blocked")
    last = entries[-1].get("message") if entries else "no events yet"
    return (f"{len(entries)} audit events: {passed} passed, {blocked} blocked. "
            f"Most recent: {last}")


def _call_claude(system: str, user: str) -> str:
    import anthropic  # lazy
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"), timeout=8.0)
    msg = client.messages.create(
        model=os.getenv("ANTHROPIC_MODEL", _DEFAULT_MODEL),
        max_tokens=200,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return "".join(
        b.text for b in msg.content if getattr(b, "type", None) == "text"
    ).strip()


def operator_instruction(state: dict) -> dict:
    """Return {instruction, source}. `source` is 'claude' or 'fallback'."""
    if not sponsor_flags.active("claude_assist"):
        return {"instruction": _fallback_instruction(state), "source": "fallback"}
    try:
        user = (
            "Structured step state (the backend already decided the verdict):\n"
            f"- current_step: {state.get('current_step')}\n"
            f"- expected_block: {state.get('expected_block')}\n"
            f"- detected_block: {state.get('detected_block')}\n"
            f"- in_assembly_zone: {state.get('in_assembly_zone')}\n"
            f"- validation_status (AUTHORITATIVE): {state.get('validation_status')}\n"
            f"- backend_message: {state.get('message')}\n"
            "Give the operator one short instruction consistent with that verdict."
        )
        text = _call_claude(_SYSTEM, user)
        if not text:
            raise ValueError("empty response")
        return {"instruction": text, "source": "claude"}
    except Exception as e:  # any SDK/API/key error -> deterministic fallback
        log.warning("[claude] operator_instruction fell back (soft): %s", e)
        return {"instruction": _fallback_instruction(state), "source": "fallback"}


def audit_summary(entries: list) -> dict:
    """Return {summary, source}."""
    entries = entries or []
    if not sponsor_flags.active("claude_assist"):
        return {"summary": _fallback_summary(entries), "source": "fallback"}
    try:
        lines = "\n".join(
            f"- step {e.get('step')}: {e.get('status')} — {e.get('message')}"
            for e in entries[-30:]
        ) or "(no events)"
        text = _call_claude(
            "You summarize a manufacturing audit log in 2-3 sentences. Be factual; "
            "do not change any pass/fail outcome.",
            f"Audit log events:\n{lines}\n\nSummarize what happened on this work order.",
        )
        if not text:
            raise ValueError("empty response")
        return {"summary": text, "source": "claude"}
    except Exception as e:
        log.warning("[claude] audit_summary fell back (soft): %s", e)
        return {"summary": _fallback_summary(entries), "source": "fallback"}
