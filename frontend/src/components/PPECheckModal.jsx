import { useEffect, useRef, useState } from "react";
import { api } from "../api.js";

// Safety-Glasses verification gate shown before a Work Order can be opened.
// Uses the browser camera for a selfie snapshot, sends it to the backend, and
// only enables "Open Work Order" after the BACKEND verifies safety glasses.
// (The backend makes the decision — this UI never sets verified itself.)
export default function PPECheckModal({ workOrder, config, onCancel, onOpened }) {
  const videoRef = useRef(null);
  const streamRef = useRef(null);
  const [workerId, setWorkerId] = useState("operator-1");
  const [camError, setCamError] = useState(null);
  const [checking, setChecking] = useState(false);
  const [opening, setOpening] = useState(false);
  const [result, setResult] = useState(null); // backend ppe/check response
  const [error, setError] = useState(null);

  const modelConfigured = config?.model_configured;
  const verified = result?.safety_glasses_verified === true;
  const canOpen = modelConfigured ? verified : true; // demo mode when no model

  // Start / stop the browser camera with the modal lifecycle.
  useEffect(() => {
    let active = true;
    (async () => {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ video: true });
        if (!active) {
          stream.getTracks().forEach((t) => t.stop());
          return;
        }
        streamRef.current = stream;
        if (videoRef.current) videoRef.current.srcObject = stream;
      } catch (e) {
        setCamError("Camera unavailable or permission denied. You can still cancel.");
      }
    })();
    return () => {
      active = false;
      if (streamRef.current) streamRef.current.getTracks().forEach((t) => t.stop());
    };
  }, []);

  function captureBlob() {
    return new Promise((resolve, reject) => {
      const v = videoRef.current;
      if (!v || !v.videoWidth) return reject(new Error("Camera not ready."));
      const canvas = document.createElement("canvas");
      canvas.width = v.videoWidth;
      canvas.height = v.videoHeight;
      canvas.getContext("2d").drawImage(v, 0, 0);
      canvas.toBlob((b) => (b ? resolve(b) : reject(new Error("Capture failed."))), "image/jpeg", 0.9);
    });
  }

  async function onVerify() {
    setError(null);
    setChecking(true);
    try {
      const blob = await captureBlob();
      const res = await api.ppeCheck(workOrder.work_order_id, workerId, blob);
      setResult(res);
    } catch (e) {
      setError(String(e.message || e));
      setResult(null);
    } finally {
      setChecking(false);
    }
  }

  async function onOpen() {
    setError(null);
    setOpening(true);
    try {
      // Enforce the backend gate when a model is configured.
      if (modelConfigured) await api.unlock(workOrder.work_order_id, workerId);
      await onOpened(workOrder.work_order_id);
    } catch (e) {
      setError(String(e.message || e));
    } finally {
      setOpening(false);
    }
  }

  const pct = result ? Math.round((result.confidence || 0) * 100) : null;
  const when = result?.created_at ? new Date(result.created_at).toLocaleTimeString() : null;
  const expires = result?.expires_at ? new Date(result.expires_at).toLocaleTimeString() : null;

  return (
    <div className="modal-overlay" onClick={onCancel}>
      <div className="modal ppe-modal" onClick={(e) => e.stopPropagation()}>
        <div className="ppe-head">
          <h2>🥽 Safety Glasses Verification</h2>
          <span className="ppe-wo">{workOrder.work_order_id}</span>
        </div>
        <p className="ppe-sub">
          PPE check is required before opening this work order. Look at the camera
          with your safety glasses on, then verify.
        </p>

        <div className={`ppe-camera ${verified ? "ok" : result ? "bad" : ""}`}>
          <video ref={videoRef} autoPlay playsInline muted />
          {camError && <div className="ppe-camerr">{camError}</div>}
          {result && (
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

        {result && (
          <div className={`ppe-result ${verified ? "ok-banner" : "error-banner"}`}>
            <div style={{ fontSize: 16 }}>{verified ? "✓ " : "⛔ "}{result.reason}</div>
            <div className="ppe-meta">
              confidence <strong>{pct}%</strong> · checked {when} · expires {expires}
            </div>
          </div>
        )}

        {error && <div className="error-banner ppe-err">⚠️ {error}</div>}

        <div className="ppe-actions">
          <button className="btn-ghost" onClick={onCancel} disabled={opening}>
            Cancel
          </button>
          {modelConfigured && (
            <button className="btn-primary" onClick={onVerify} disabled={checking || opening}>
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
