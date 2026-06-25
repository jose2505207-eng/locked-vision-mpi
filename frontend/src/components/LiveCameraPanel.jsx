import { useEffect, useState } from "react";
import { SCENARIOS, VISION_URL } from "../api.js";

// Vision panel with TWO clearly separated modes:
//   1. Camera Bridge Mode — the real webcam is read by vision/run_vision.py
//      (Python/OpenCV) and served as an annotated MJPEG/JPEG feed. This browser
//      panel only DISPLAYS that feed; it never opens the webcam itself.
//   2. Demo Mode (Mock Vision) — the simulator buttons post canned evidence,
//      used as the fallback for tools / final steps.
export default function LiveCameraPanel({
  onSimulate,
  recommended,
  disabled,
  visionMeta,
  objects,
  healthOk,
  workOrderId,
  recommendedAction,
}) {
  const recLabel = SCENARIOS.find((s) => s.id === recommended)?.label;
  const wo = workOrderId || "WO-1001";
  const source = visionMeta?.source || "none";
  const updatedAt = visionMeta?.updated_at;
  const cmd =
    `cd vision\n../.venv/bin/python run_vision.py --show --serve-ui ` +
    `--post http://localhost:8000 --wo ${wo} --camera-index 0 --auto-post-interval 1`;

  // Poll the vision bridge: /health for online state, and bump a cache-buster
  // so the <img> refreshes the latest annotated frame (~700ms).
  const [bridgeOnline, setBridgeOnline] = useState(false);
  const [frameTick, setFrameTick] = useState(0);
  useEffect(() => {
    let active = true;
    const ping = async () => {
      try {
        const ctrl = new AbortController();
        const t = setTimeout(() => ctrl.abort(), 1000);
        const r = await fetch(`${VISION_URL}/health`, { signal: ctrl.signal });
        clearTimeout(t);
        if (active) setBridgeOnline(r.ok);
      } catch (_) {
        if (active) setBridgeOnline(false);
      }
    };
    ping();
    const hp = setInterval(ping, 2000);
    const hf = setInterval(() => active && setFrameTick((n) => n + 1), 700);
    return () => {
      active = false;
      clearInterval(hp);
      clearInterval(hf);
    };
  }, []);

  const sourceLabel =
    source === "camera"
      ? "📷 CAMERA (Python bridge)"
      : source === "simulator"
      ? "🧪 SIMULATOR (mock)"
      : "— no evidence yet";
  const sourceClass =
    source === "camera" ? "src-camera" : source === "simulator" ? "src-sim" : "src-none";

  const summary =
    objects && objects.length
      ? objects.map((o) => `${o.object} @ ${o.zone || "no-zone"}`).join(", ")
      : "(nothing detected)";
  const when = updatedAt ? new Date(updatedAt).toLocaleTimeString() : "—";

  return (
    <div className="panel">
      <h2>Vision Source</h2>

      {/* Live annotated feed served by Python/OpenCV (browser only displays it) */}
      <div className="camera">
        <span className="lock">
          🔒 {bridgeOnline ? "BRIDGE LIVE · CALIBRATED" : "BRIDGE OFFLINE"}
        </span>
        {bridgeOnline ? (
          <img
            className="cam-feed"
            src={`${VISION_URL}/latest-frame.jpg?t=${frameTick}`}
            alt="annotated camera feed"
          />
        ) : (
          <div className="reticle">
            Camera bridge offline. Start it with the command below.
            <br />
            (The browser never opens the webcam — Python/OpenCV does.)
          </div>
        )}
      </div>

      {/* Live status labels */}
      <div className="vision-status">
        <div className="vs-row">
          <span className="vs-key">Backend</span>
          <span className={healthOk ? "vs-ok" : "vs-bad"}>
            {healthOk ? "online" : "offline"}
          </span>
        </div>
        <div className="vs-row">
          <span className="vs-key">Vision bridge</span>
          <span className={bridgeOnline ? "vs-ok" : "vs-bad"}>
            {bridgeOnline ? "online" : "offline"}
          </span>
        </div>
        <div className="vs-row">
          <span className="vs-key">Source</span>
          <span className={`vs-source ${sourceClass}`}>{sourceLabel}</span>
        </div>
        <div className="vs-row">
          <span className="vs-key">Camera locked</span>
          <span className={visionMeta?.camera_locked ? "vs-ok" : "vs-val"}>
            {visionMeta?.camera_locked ? "yes" : "—"}
          </span>
        </div>
        <div className="vs-row">
          <span className="vs-key">Last objects</span>
          <span className="vs-val">{summary}</span>
        </div>
        <div className="vs-row">
          <span className="vs-key">Updated</span>
          <span className="vs-val">{when}</span>
        </div>
      </div>

      {recommendedAction && (
        <div className="rec-hint" style={{ marginBottom: 10 }}>
          ▶ {recommendedAction}
        </div>
      )}

      {/* Camera Bridge Mode command */}
      <div className="bridge-box">
        <div className="bridge-title">📷 Camera Bridge Mode</div>
        <p>
          Run <code>vision/run_vision.py</code> with <code>--serve-ui</code> to
          stream the annotated feed here and auto-post camera evidence. Press{" "}
          <strong>p</strong> to post now, <strong>s</strong> to snapshot,{" "}
          <strong>q</strong> to quit.
        </p>
        <pre className="cmd">{cmd}</pre>
      </div>

      {/* Demo Mode fallback — simulator buttons (camera-less / final step) */}
      <h2 style={{ marginTop: 16 }}>Simulator fallback (no camera)</h2>
      <div className="demo-note">
        🧪 Mock evidence for a camera-less run, or for the{" "}
        <strong>Finished → complete</strong> step the camera can't see. Clicking
        one sets the source to <strong>simulator</strong>.
      </div>
      {recLabel && (
        <div className="rec-hint">
          ▶ Recommended next: <strong>{recLabel}</strong>
        </div>
      )}
      <div className="sim-grid">
        {SCENARIOS.map((s) => (
          <button
            key={s.id}
            className={s.id === recommended ? "recommended" : ""}
            disabled={disabled}
            onClick={() => onSimulate(s.id)}
          >
            {s.label}
          </button>
        ))}
      </div>

      <details className="trouble">
        <summary>Camera troubleshooting</summary>
        <ul>
          <li>
            No live video here? Confirm the bridge is running with{" "}
            <code>--serve-ui</code> on port 8010.
          </li>
          <li>
            No OpenCV window opens? Run{" "}
            <code>../.venv/bin/python test_camera.py</code> (try{" "}
            <code>--camera-index 1</code>/<code>2</code>).
          </li>
          <li>Nothing detected? Use brighter colored paper / better lighting.</li>
          <li>
            Detected in the wrong zone? Move the object fully inside the visible
            zone rectangle.
          </li>
          <li>
            Frontend not updating? Confirm the backend is on{" "}
            <code>localhost:8000</code> and the bridge is auto-posting (or press{" "}
            <strong>p</strong>).
          </li>
        </ul>
      </details>
    </div>
  );
}
