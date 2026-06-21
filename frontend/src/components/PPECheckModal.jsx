import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "../api.js";

// Safety-Glasses verification gate shown before a Work Order can be opened.
// Uses the browser camera for a selfie snapshot, sends it to the backend, and
// only enables "Open Work Order" after the BACKEND verifies safety glasses.
// (The backend makes the decision — this UI never sets verified itself.)
//
// Demo-safety contract:
//   * The video preview stays live while the modal is open.
//   * Verify can NEVER hang forever — there is a client-side timeout and the
//     request is aborted on close.
//   * Every terminal state (verified / failed / camera_error) offers a way out.
//
// Explicit state machine — `phase` is the single source of UI truth:
//   starting_camera → camera_ready → capturing → verifying → verified | failed
//   camera_error is reachable from any camera operation.
// Slightly longer than the backend provider cap (12s) so a cold-start serverless
// call still surfaces a real verdict rather than a premature client abort.
const VERIFY_TIMEOUT_MS = 15000;

const log = (...a) => console.debug("[PPE]", ...a);

const PHASE_LABEL = {
  starting_camera: "Camera starting…",
  camera_ready: "Camera ready",
  capturing: "Capturing…",
  verifying: "Verifying…",
  verified: "Verified",
  failed: "Failed",
  camera_error: "Camera error",
};

// Map a getUserMedia DOMException to a clear, actionable message.
function cameraErrorMessage(e) {
  const name = e?.name || "";
  if (name === "NotAllowedError" || name === "SecurityError")
    return "Camera permission denied. Allow camera access in the browser, then Retry.";
  if (name === "NotReadableError" || name === "TrackStartError" || name === "AbortError")
    return "Camera is busy — likely held by the vision bridge (OpenCV). Close the bridge or use another camera, then Retry.";
  if (name === "NotFoundError" || name === "OverconstrainedError")
    return "No camera found. Plug one in (or pick another device) and Retry.";
  return `Camera unavailable: ${e?.message || e}. You can still Cancel.`;
}

export default function PPECheckModal({ workOrder, config, onCancel, onOpened }) {
  const videoRef = useRef(null);
  const streamRef = useRef(null);
  const abortRef = useRef(null);
  const timerRef = useRef(null);

  const [workerId, setWorkerId] = useState("operator-1");
  const [phase, setPhase] = useState("starting_camera");
  const [camError, setCamError] = useState(null);
  const [opening, setOpening] = useState(false);
  const [result, setResult] = useState(null); // backend ppe/check response
  const [error, setError] = useState(null);

  const modelConfigured = config?.model_configured;
  const mockMode = config?.mock_mode;
  const verified = result?.safety_glasses_verified === true;
  const canOpen = modelConfigured ? verified : true; // demo mode when no model
  const checking = phase === "capturing" || phase === "verifying";

  // --- Camera lifecycle ------------------------------------------------------
  const stopStream = useCallback(() => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop());
      log("camera tracks stopped");
      streamRef.current = null;
    }
    if (videoRef.current) videoRef.current.srcObject = null;
  }, []);

  const startCamera = useCallback(async () => {
    stopStream();
    setCamError(null);
    setPhase("starting_camera");
    log("getUserMedia requested");
    let stream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
    } catch (e) {
      log("getUserMedia failed", e?.name, e?.message);
      setCamError(cameraErrorMessage(e));
      setPhase("camera_error");
      return;
    }
    // If the modal was torn down while awaiting, release immediately.
    if (!videoRef.current) {
      stream.getTracks().forEach((t) => t.stop());
      return;
    }
    streamRef.current = stream;
    const v = videoRef.current;
    v.srcObject = stream;
    v.onloadedmetadata = () => {
      v.play()
        .then(() => {
          log("camera stream ready", `${v.videoWidth}x${v.videoHeight}`);
          setPhase("camera_ready");
        })
        .catch((e) => {
          log("video.play() failed", e);
          // Autoplay can be blocked; the stream is still live, allow verify.
          setPhase("camera_ready");
        });
    };
  }, [stopStream]);

  // Start the camera with the modal; tear everything down on close.
  useEffect(() => {
    log("modal opened", workOrder?.work_order_id, "provider:", config?.provider);
    startCamera();
    return () => {
      log("modal closed — aborting + stopping camera");
      if (abortRef.current) abortRef.current.abort();
      if (timerRef.current) clearTimeout(timerRef.current);
      stopStream();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // --- Capture + verify ------------------------------------------------------
  function captureBlob() {
    return new Promise((resolve, reject) => {
      const v = videoRef.current;
      if (!v || !v.videoWidth) return reject(new Error("Camera not ready — wait for the preview, then retry."));
      const canvas = document.createElement("canvas");
      canvas.width = v.videoWidth;
      canvas.height = v.videoHeight;
      canvas.getContext("2d").drawImage(v, 0, 0);
      canvas.toBlob((b) => (b ? resolve(b) : reject(new Error("Capture failed."))), "image/jpeg", 0.9);
    });
  }

  async function onVerify() {
    setError(null);
    setResult(null);
    setPhase("capturing");

    let blob;
    try {
      blob = await captureBlob();
      log("frame captured", blob.size, "bytes");
    } catch (e) {
      setError(String(e.message || e));
      setPhase("failed");
      return;
    }

    const controller = new AbortController();
    abortRef.current = controller;
    timerRef.current = setTimeout(() => {
      log("verify request timed out — aborting");
      controller.abort();
    }, VERIFY_TIMEOUT_MS);

    setPhase("verifying");
    log("verify request started");
    try {
      const res = await api.ppeCheck(workOrder.work_order_id, workerId, blob, controller.signal);
      log("verify request finished", res);
      setResult(res);
      setPhase(res?.safety_glasses_verified ? "verified" : "failed");
      if (res && res.ok === false) setError(res.reason); // timeout / provider error
    } catch (e) {
      if (controller.signal.aborted) {
        // Either the client timeout fired or the modal closed.
        log("verify request aborted");
        setError(`Verification timed out after ${VERIFY_TIMEOUT_MS / 1000}s. Check the backend/model or use mock mode, then Retry.`);
      } else {
        log("verify request failed", e);
        setError(String(e.message || e));
      }
      setPhase("failed");
    } finally {
      clearTimeout(timerRef.current);
      timerRef.current = null;
      abortRef.current = null;
    }
  }

  function handleCancel() {
    if (abortRef.current) abortRef.current.abort();
    if (timerRef.current) clearTimeout(timerRef.current);
    stopStream();
    onCancel();
  }

  async function onOpen() {
    setError(null);
    setOpening(true);
    try {
      // The PPE gate here is enforced client-side via `canOpen`. Server-side
      // enforcement only kicks in when PPE_REQUIRED=true (the backend /start
      // route checks the verification session); in the default demo it does not.
      await onOpened(workOrder.work_order_id);
    } catch (e) {
      setError(String(e.message || e));
    } finally {
      setOpening(false);
    }
  }

  const pct = result && result.confidence != null ? Math.round((result.confidence || 0) * 100) : null;
  const when = result?.created_at ? new Date(result.created_at).toLocaleTimeString() : null;
  const expires = result?.expires_at ? new Date(result.expires_at).toLocaleTimeString() : null;
  const canRetry = phase === "failed" || phase === "camera_error";

  // Honest PPE source: prefer the actual result's mode, fall back to config.
  const ppeSource =
    result && result.ok === false
      ? "unavailable"
      : result?.mode === "mock" || (mockMode && !result)
      ? "mock"
      : result?.mode === "live"
      ? "real"
      : modelConfigured
      ? mockMode
        ? "mock"
        : "real"
      : "unavailable";
  // One-line reason the work order is locked / unlocked (debug honesty).
  const lockReason = canOpen
    ? modelConfigured
      ? `unlocked — safety glasses verified (${ppeSource})`
      : "unlocked — demo mode (no PPE model configured)"
    : verified === false && result
    ? `locked — ${result.reason || "not verified"}`
    : "locked — verify safety glasses first";

  return (
    <div className="modal-overlay" onClick={handleCancel}>
      <div className="modal ppe-modal" onClick={(e) => e.stopPropagation()}>
        <div className="ppe-head">
          <h2>🥽 Safety Glasses Verification</h2>
          <span className="ppe-wo">{workOrder.work_order_id}</span>
        </div>
        <p className="ppe-sub">
          PPE check is required before opening this work order. Look at the camera
          with your safety glasses on, then verify.
          <span className={`ppe-phase ppe-phase-${phase}`}>{PHASE_LABEL[phase] || phase}</span>
        </p>

        <div className={`ppe-camera ${verified ? "ok" : result ? "bad" : ""}`}>
          <video ref={videoRef} autoPlay playsInline muted />
          {phase === "camera_error" && <div className="ppe-camerr">{camError}</div>}
          {phase === "starting_camera" && <div className="ppe-camerr">Camera starting…</div>}
          {result && phase !== "camera_error" && (
            <div className={`ppe-stamp ${verified ? "ok" : "bad"}`}>
              {verified ? "✓ VERIFIED" : "✗ NOT VERIFIED"}
            </div>
          )}
        </div>

        <div className="ppe-row">
          <label className="ppe-label">Worker ID</label>
          <input
            className="ppe-input"
            value={workerId}
            onChange={(e) => setWorkerId(e.target.value)}
          />
        </div>

        {!modelConfigured && (
          <div className="ppe-note">
            ⚠️ PPE model not configured (no <code>ROBOFLOW_API_KEY</code>). Running
            in <strong>demo mode</strong> — verification is skipped, not faked.
          </div>
        )}
        {modelConfigured && mockMode && (
          <div className="ppe-note">
            🧪 <strong>DEMO_MOCK_PPE</strong> is on — EMERGENCY fallback. Verification
            is simulated locally (no real model call). Clearly labeled, never faked as live.
          </div>
        )}

        {result && (
          <div className={`ppe-result ${verified ? "ok-banner" : "error-banner"}`}>
            <div style={{ fontSize: 16 }}>{verified ? "✓ " : "⛔ "}{result.reason}</div>
            <div className="ppe-meta">
              {pct != null && <>confidence <strong>{pct}%</strong> · </>}
              {when && <>checked {when}</>}
              {verified && expires && <> · expires {expires}</>}
              {result.mode && <> · mode {result.mode}</>}
            </div>
          </div>
        )}

        {error && phase !== "camera_error" && <div className="error-banner ppe-err">⚠️ {error}</div>}

        {/* Honest debug panel — what the gate is actually deciding on. */}
        <div className="ppe-debug">
          <div className="ppe-debug-row">
            <span>PPE source</span>
            <strong className={`ppe-src ppe-src-${ppeSource}`}>{ppeSource}</strong>
          </div>
          <div className="ppe-debug-row">
            <span>Safety glasses detected</span>
            <strong>{result ? String(verified) : "—"}</strong>
          </div>
          <div className="ppe-debug-row">
            <span>Confidence</span>
            <strong>{pct != null ? `${pct}%` : "—"}</strong>
          </div>
          <div className="ppe-debug-row">
            <span>Last PPE check</span>
            <strong>{when || "—"}</strong>
          </div>
          <div className="ppe-debug-row">
            <span>Work order</span>
            <strong className={canOpen ? "ppe-src-real" : "ppe-src-unavailable"}>{lockReason}</strong>
          </div>
        </div>

        <div className="ppe-actions">
          <button className="btn-ghost" onClick={handleCancel} disabled={opening}>
            Cancel
          </button>
          {canRetry && (
            <button
              className="btn-primary"
              onClick={phase === "camera_error" ? startCamera : onVerify}
              disabled={opening}
            >
              ↻ Retry
            </button>
          )}
          {modelConfigured && !canRetry && (
            <button
              className="btn-primary"
              onClick={onVerify}
              disabled={checking || opening || phase === "starting_camera"}
            >
              {checking ? "Verifying…" : "Verify Safety Glasses"}
            </button>
          )}
          <button
            className={`btn-open ${canOpen ? "enabled" : "disabled"}`}
            onClick={onOpen}
            disabled={!canOpen || opening}
            title={canOpen ? "" : "Verify safety glasses first"}
          >
            {opening
              ? "Opening…"
              : canOpen
              ? `Open Work Order${modelConfigured ? "" : " (demo)"} →`
              : "🔒 Locked — verify first"}
          </button>
        </div>
      </div>
    </div>
  );
}
