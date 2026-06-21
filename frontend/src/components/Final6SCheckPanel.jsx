// Final 6S reset gate. The work order cannot close until the backend's
// final-6s-check returns can_advance === true (assembly clear, finished
// assembly in complete zone). Blocks-only demo — no tool checks.
export default function Final6SCheckPanel({ visible, result, status, onCheck, busy }) {
  if (!visible) return null;

  const passed = result?.can_advance === true || status === "completed";

  return (
    <div className="panel">
      <h2>Final 6S — Station Reset</h2>
      <div className="meta" style={{ marginBottom: 10 }}>
        Assembly zone clear · finished assembly in complete zone.
      </div>

      <button
        className="btn-primary"
        style={{ width: "100%", marginBottom: 12 }}
        disabled={busy || status === "completed"}
        onClick={onCheck}
      >
        Run Final 6S Check
      </button>

      {result?.message && (
        <div className={passed ? "ok-banner" : "error-banner"}>
          {passed ? "✓ " : "⛔ "}
          {result.message}
        </div>
      )}

      {status === "completed" && (
        <div className="ok-banner" style={{ marginTop: 12, fontSize: 20 }}>
          ✅ WORK ORDER CLOSED
        </div>
      )}
    </div>
  );
}
