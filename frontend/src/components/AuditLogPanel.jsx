export default function AuditLogPanel({ entries }) {
  const rows = [...(entries || [])].reverse();
  return (
    <div className="panel">
      <h2>Audit Log</h2>
      <div className="audit">
        {rows.length === 0 && <div className="meta">No events yet.</div>}
        {rows.map((e, i) => (
          <div className="row" key={i}>
            <span className="t">{(e.timestamp || "").slice(11, 19)} </span>
            <span className={e.status === "passed" ? "passed" : "blocked"}>
              [{(e.status || e.event || "").toUpperCase()}]
            </span>{" "}
            <span>
              {e.event}
              {e.step ? ` · step ${e.step}` : ""} — {e.message}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
