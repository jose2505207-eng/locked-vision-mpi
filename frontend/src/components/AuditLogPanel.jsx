export default function AuditLogPanel({ entries }) {
  const rows = [...(entries || [])].reverse();
  return (
    <div className="panel">
      <h2>Audit Log</h2>
      <div className="audit">
        {rows.length === 0 && <div className="meta">No events yet.</div>}
        {rows.map((e, i) => {
          const passed = e.status === "passed";
          const blocked = e.status === "blocked";
          const cls = passed ? "passed" : blocked ? "blocked" : "info";
          const icon = passed ? "✓ PASS" : blocked ? "⛔ FAIL" : "•";
          return (
            <div className={`row ${cls}`} key={i}>
              <span className="t">{(e.timestamp || "").slice(11, 19)} </span>
              <span className={`tag ${cls}`}>{icon}</span>{" "}
              <span>
                {e.step ? `step ${e.step} · ` : ""}
                {e.message}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
