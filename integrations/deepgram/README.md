# Deepgram — Hands-free Operator Voice

**Track:** Best Use of Deepgram.

## Status: scaffold only (NOT wired)

> ⚠️ There is **no Deepgram code, SDK, or API key** wired into the app. The demo's
> audible voice is produced by the **browser Web Speech API** (`speechSynthesis`)
> in `frontend/src/voice.js` — a clearly-labeled fallback so the demo is always
> audible. We do **not** pretend Deepgram is active.
>
> To wire Deepgram TTS later: implement `speakWithDeepgram()` in
> `frontend/src/voice.js` (or a backend `/api/voice` route that streams Deepgram
> audio), set `VOICE_PROVIDER = "deepgram"`, and keep the browser path as the
> offline fallback. Phrases are already backend-generated (the `voice` field on
> `/api/verification-sessions/{id}/blocks/submit`), so only the audio transport
> changes.

## Why it fits

A real operator's hands are on the parts and tools, not the keyboard. Deepgram
speech-to-text lets the operator say "verify step" or "next step" and the
backend still enforces the gate — voice is just another way to *request*
advancement, never a way to bypass it.

## Planned usage (placeholder)

- **STT:** stream mic audio to Deepgram; map intents to API calls:
  - "verify" / "check" → `POST /validate-step`
  - "next" / "advance" → `POST /advance` (still gated by `can_advance`)
  - "reset" / "six s" → `POST /final-6s-check`
- **TTS (optional):** read the step instruction and the block/pass reason aloud.

## Wiring sketch

```bash
pip install deepgram-sdk
export DEEPGRAM_API_KEY="..."
```

Voice commands call the same endpoints as the buttons. The backend remains the
source of truth, so a misheard "next" on an unverified step is still blocked.
