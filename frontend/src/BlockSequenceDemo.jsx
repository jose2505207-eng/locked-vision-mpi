import { useEffect, useRef, useState } from "react";
import { api, VISION_URL } from "./api.js";
import {
  enableVoice,
  isVoiceSupported,
  onVoiceStatus,
  speak,
  VOICE_PROVIDER,
  VOICE_STATUS,
} from "./voice.js";

const WO = "WO-1001";
const COLOR_HEX = { green: "#2ea043", blue: "#2f81f7", red: "#f85149", yellow: "#f0c000" };
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

// Clean, presentation-ready demo: voice + Lego block sequence + work-order unlock.
// Flow: GREEN -> BLUE -> RED -> YELLOW. No tools, no tool checklist. The backend
// owns truth (can_open_work_order); this UI only sends events and speaks results.
export default function BlockSequenceDemo() {
  const [sessionId, setSessionId] = useState(null);
  const [required, setRequired] = useState(["green", "blue", "red", "yellow"]);
  const [submitted, setSubmitted] = useState([]);
  const [expected, setExpected] = useState("green");
  const [passed, setPassed] = useState(false);
  const [canOpen, setCanOpen] = useState(false);
  const [lastEvent, setLastEvent] = useState(null); // { ok, text }
  const [busy, setBusy] = useState(false);

  const [backendOk, setBackendOk] = useState(false);
  const [visionOk, setVisionOk] = useState(false);
  const [voiceStatus, setVoiceStatus] = useState(VOICE_STATUS.DISABLED);
  const startedRef = useRef(false);

  // Wire voice status -> UI indicator.
  useEffect(() => onVoiceStatus(setVoiceStatus), []);

  // Boot: backend health + start a verification session.
  useEffect(() => {
    if (startedRef.current) return;
    startedRef.current = true;
    api.health().then(() => setBackendOk(true)).catch(() => setBackendOk(false));
    startSession();
  }, []);

  // Poll the vision bridge (Python/OpenCV) for connection status.
  useEffect(() => {
    let active = true;
    const ping = async () => {
      try {
        const c = new AbortController();
        const t = setTimeout(() => c.abort(), 1000);
        const r = await fetch(`${VISION_URL}/health`, { signal: c.signal });
        clearTimeout(t);
        if (active) setVisionOk(r.ok);
      } catch (_) {
        if (active) setVisionOk(false);
      }
    };
    ping();
    const h = setInterval(ping, 2000);
    return () => {
      active = false;
      clearInterval(h);
    };
  }, []);

  function applySession(s) {
    if (s.required_sequence) setRequired(s.required_sequence);
    setSubmitted(s.submitted_sequence || []);
    setExpected(s.expected_next_color ?? null);
    setPassed(!!s.sequence_passed);
    setCanOpen(!!s.can_open_work_order);
  }

  async function startSession() {
    try {
      const s = await api.vsStart(WO);
      setSessionId(s.session_id);
      applySession(s);
      setLastEvent(null);
    } catch (e) {
      setLastEvent({ ok: false, text: String(e.message || e) });
    }
  }

  // Send a block color to the backend; speak whatever the backend decided.
  async function submit(color) {
    if (!sessionId || busy) return;
    setBusy(true);
    try {
      const r = await api.vsSubmitBlock(sessionId, color);
      setSubmitted(r.submitted_sequence || []);
      setExpected(r.expected_next_color ?? null);
      setPassed(!!r.sequence_passed);
      setCanOpen(!!r.can_open_work_order);
      setLastEvent({ ok: r.accepted, text: r.message || r.voice });
      speak(r.voice); // backend-generated phrase
      if (r.can_open_work_order) {
        // Confirm with the authoritative gate.
        await api.vsUnlock(WO).catch(() => {});
      }
    } catch (e) {
      setLastEvent({ ok: false, text: String(e.message || e) });
    } finally {
      setBusy(false);
    }
  }

  // Deliberate wrong move: submit a color that is NOT the expected next one.
  function submitWrong() {
    const wrong = required.find((c) => c !== expected) || "red";
    submit(wrong);
  }

  // Drive the full correct sequence with pauses so each line is heard.
  async function runFullSequence() {
    await startSession();
    for (const c of ["green", "blue", "red", "yellow"]) {
      await submit(c);
      await sleep(950);
    }
  }

  function onEnableVoice() {
    enableVoice();
    speak("Vision system ready.");
  }

  const voiceLabel = {
    [VOICE_STATUS.DISABLED]: "Voice off",
    [VOICE_STATUS.READY]: "Voice ready",
    [VOICE_STATUS.SPEAKING]: "Speaking…",
    [VOICE_STATUS.BLOCKED]: "Muted / blocked",
    [VOICE_STATUS.ERROR]: "Voice error",
  }[voiceStatus];

  return (
    <div className="bsd">
      <header className="bsd-top">
        <div>
          <h1>🔒 Locked Vision MPI — Block Sequence</h1>
          <div className="bsd-sub">
            Complete <strong>GREEN → BLUE → RED → YELLOW</strong> to unlock the work order.
          </div>
        </div>
        <div className="bsd-status">
          <Pill ok={backendOk} label={`Backend ${backendOk ? "online" : "offline"}`} />
          <Pill ok={visionOk} label={`Camera ${visionOk ? "connected" : "offline"}`} />
          <Pill
            ok={voiceStatus === VOICE_STATUS.READY || voiceStatus === VOICE_STATUS.SPEAKING}
            warn={voiceStatus === VOICE_STATUS.BLOCKED || voiceStatus === VOICE_STATUS.DISABLED}
            label={voiceLabel}
          />
        </div>
      </header>

      {/* Sequence progress */}
      <section className="bsd-seq">
        {required.map((c, i) => {
          const done = submitted.includes(c) && submitted.indexOf(c) === i;
          const current = c === expected;
          return (
            <div key={c} className={`bsd-block ${done ? "done" : current ? "current" : "todo"}`}>
              <span className="bsd-swatch" style={{ background: COLOR_HEX[c] }} />
              <span className="bsd-name">{c.toUpperCase()}</span>
              <span className="bsd-mark">{done ? "✓" : current ? "▶" : ""}</span>
            </div>
          );
        })}
      </section>

      {/* Work order lock state */}
      <section className={`bsd-lock ${canOpen ? "open" : "locked"}`}>
        {canOpen ? "✅ WORK ORDER UNLOCKED" : "🔒 WORK ORDER LOCKED"}
        <div className="bsd-locksub">
          {canOpen
            ? "Block sequence verified by the backend."
            : expected
            ? `Next required block: ${expected.toUpperCase()}`
            : "Sequence complete."}
        </div>
      </section>

      {/* Last event / backend message */}
      {lastEvent && (
        <div className={lastEvent.ok ? "bsd-msg ok" : "bsd-msg bad"}>
          {lastEvent.ok ? "✓ " : "⛔ "}
          {lastEvent.text}
        </div>
      )}

      {/* Voice controls */}
      <section className="bsd-controls">
        <button className="bsd-btn voice" onClick={onEnableVoice} disabled={!isVoiceSupported()}>
          🔊 Enable Voice
        </button>
        <span className="bsd-voiceprov">
          voice: Web Speech API{VOICE_PROVIDER !== "browser" ? ` (${VOICE_PROVIDER})` : ""}
          {!isVoiceSupported() && " — not supported in this browser"}
        </span>
      </section>

      {/* Mock controls (work without a camera) */}
      <section className="bsd-mock">
        <div className="bsd-mocklabel">Mock blocks (no camera needed)</div>
        <div className="bsd-mockgrid">
          {required.map((c) => (
            <button
              key={c}
              className={`bsd-btn block ${c === expected ? "rec" : ""}`}
              style={{ borderColor: COLOR_HEX[c] }}
              onClick={() => submit(c)}
              disabled={busy || !sessionId}
            >
              <span className="bsd-swatch" style={{ background: COLOR_HEX[c] }} />
              {c}
            </button>
          ))}
          <button className="bsd-btn warn" onClick={submitWrong} disabled={busy || !sessionId}>
            ✗ Wrong block
          </button>
          <button className="bsd-btn" onClick={runFullSequence} disabled={busy}>
            ▶ Full sequence
          </button>
          <button className="bsd-btn" onClick={startSession} disabled={busy}>
            ⟲ Reset
          </button>
        </div>
      </section>

      {/* Optional live camera feed when the vision bridge is up */}
      {visionOk && (
        <section className="bsd-feed">
          <div className="bsd-mocklabel">Live camera (Python/OpenCV bridge)</div>
          <img src={`${VISION_URL}/latest-frame.jpg?t=${Date.now()}`} alt="camera feed" />
        </section>
      )}
    </div>
  );
}

function Pill({ ok, warn, label }) {
  const cls = ok ? "ok" : warn ? "warn" : "bad";
  return (
    <span className={`bsd-pill ${cls}`}>
      <span className="bsd-dot" /> {label}
    </span>
  );
}
