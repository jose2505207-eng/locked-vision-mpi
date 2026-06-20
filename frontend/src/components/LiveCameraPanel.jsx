import { SCENARIOS } from "../api.js";

// Live camera / snapshot panel. In the real system this shows the locked
// camera feed. In the camera-less demo it doubles as the "vision simulator":
// each button posts a mock vision state to the backend as evidence.
export default function LiveCameraPanel({ onSimulate, lastScenario, recommended, disabled }) {
  const recLabel = SCENARIOS.find((s) => s.id === recommended)?.label;
  return (
    <div className="panel">
      <h2>Locked Camera — Golden View</h2>
      <div className="camera">
        <span className="lock">🔒 CAMERA LOCKED · CALIBRATED</span>
        <div className="reticle">
          {lastScenario ? (
            <>
              <div style={{ fontSize: 28 }}>▣</div>
              evidence: <strong>{lastScenario}</strong>
            </>
          ) : (
            <>[ live feed / snapshot ]<br />post vision evidence below</>
          )}
        </div>
      </div>

      <h2 style={{ marginTop: 16 }}>Vision Simulator (mock evidence)</h2>
      <div className="demo-note">
        🧪 Demo Mode — these buttons post <strong>simulated vision evidence</strong>.
        A real locked camera will replace them.
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
    </div>
  );
}
