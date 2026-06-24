// Voice output for the demo.
//
// PRIMARY (working): the browser Web Speech API (window.speechSynthesis). This
// requires a one-time user gesture ("Enable Voice") because browsers block
// autoplay audio until the user interacts with the page.
//
// SPONSOR PATH (Deepgram TTS): NOT wired. There is no Deepgram API key or SDK in
// this project, so we do NOT pretend it works. `speak()` always uses the browser
// fallback. To add Deepgram later, implement `speakWithDeepgram()` and switch
// the provider — keep the browser path as the offline fallback so the demo is
// always audible.

export const VOICE_PROVIDER = "browser"; // "browser" (working) | "deepgram" (TODO, not wired)

let _enabled = false;
let _onStatus = () => {};

// Statuses surfaced to the UI indicator.
export const VOICE_STATUS = {
  DISABLED: "disabled",
  READY: "ready",
  SPEAKING: "speaking",
  BLOCKED: "blocked",
  ERROR: "error",
};

export function isVoiceSupported() {
  return typeof window !== "undefined" && "speechSynthesis" in window;
}

export function onVoiceStatus(cb) {
  _onStatus = cb || (() => {});
}

// Must be called from a user gesture (button click) to satisfy autoplay rules.
export function enableVoice() {
  if (!isVoiceSupported()) {
    _onStatus(VOICE_STATUS.BLOCKED);
    console.warn("[voice] speechSynthesis not supported in this browser.");
    return false;
  }
  _enabled = true;
  // A tiny silent-ish priming utterance unlocks audio in most browsers.
  try {
    const u = new SpeechSynthesisUtterance("Voice enabled.");
    u.volume = 1;
    u.onend = () => _onStatus(VOICE_STATUS.READY);
    window.speechSynthesis.cancel();
    window.speechSynthesis.speak(u);
    _onStatus(VOICE_STATUS.SPEAKING);
    console.log("[voice] enabled via", VOICE_PROVIDER, "(Web Speech API)");
    return true;
  } catch (e) {
    _onStatus(VOICE_STATUS.ERROR);
    console.error("[voice] enable failed", e);
    return false;
  }
}

export function isVoiceEnabled() {
  return _enabled;
}

// Speak a line. No-op (but logs) until the user has enabled voice.
export function speak(text) {
  if (!text) return;
  if (!isVoiceSupported()) {
    _onStatus(VOICE_STATUS.BLOCKED);
    return;
  }
  if (!_enabled) {
    // Audio is blocked until the user clicks Enable Voice.
    _onStatus(VOICE_STATUS.BLOCKED);
    console.log("[voice] (blocked, click Enable Voice):", text);
    return;
  }
  try {
    const u = new SpeechSynthesisUtterance(text);
    u.rate = 1.02;
    u.pitch = 1.0;
    u.volume = 1.0;
    u.onstart = () => _onStatus(VOICE_STATUS.SPEAKING);
    u.onend = () => _onStatus(VOICE_STATUS.READY);
    u.onerror = () => _onStatus(VOICE_STATUS.ERROR);
    window.speechSynthesis.cancel(); // interrupt any queued line for snappy demo
    window.speechSynthesis.speak(u);
    console.log("[voice] speak:", text);
  } catch (e) {
    _onStatus(VOICE_STATUS.ERROR);
    console.error("[voice] speak failed", e);
  }
}
