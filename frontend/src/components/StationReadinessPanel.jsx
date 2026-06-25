// Station readiness = camera locked + calibrated + zones clear.
// When the backend readiness check is available, show exactly which objects are
// home and which are out of place (Part D).
const BLOCKS = ["red_block", "blue_block", "yellow_block", "green_block"];

export default function StationReadinessPanel({ ready, healthOk, zonesClear, readiness }) {
  const checks = [
    { label: "Backend / MES online", ok: healthOk },
    { label: "Camera locked (golden view)", ok: healthOk },
    { label: "Calibration within tolerance", ok: healthOk },
    { label: "Zones clear at home", ok: zonesClear },
  ];

  // Map object -> wrong entry (if the backend flagged it).
  const wrong = {};
  for (const w of readiness?.missing_or_wrong || []) wrong[w.object] = w;
  const canStart = readiness?.can_start === true;

  return (
    <div className="panel">
      <h2>Station Readiness</h2>
      {checks.map((c) => (
        <div className="sixs-item" key={c.label}>
          <span className={`dot ${c.ok ? "ok" : "bad"}`} />
          <span>{c.label}</span>
        </div>
      ))}

      {readiness && (
        <div className="ready-objs">
          {BLOCKS.map((b) => {
            const w = wrong[b];
            return (
              <div className="sixs-item" key={b}>
                <span className={`dot ${w ? "bad" : "ok"}`} />
                <span>
                  {b.replace("_block", " block")}
                  {w ? (
                    <span className="ro-wrong">
                      {" "}
                      → {(w.actual_zone || "missing").replace(/_/g, " ")} (need{" "}
                      {(w.expected_zone || "home").replace(/_/g, " ")})
                    </span>
                  ) : (
                    <span className="ro-ok"> home ✓</span>
                  )}
                </span>
              </div>
            );
          })}
        </div>
      )}

      <div
        className={
          (readiness ? canStart : ready && healthOk) ? "ok-banner" : "error-banner"
        }
        style={{ marginTop: 12, fontSize: 15 }}
      >
        {readiness
          ? canStart
            ? "✓ STATION READY — clear to start"
            : "✗ STATION NOT READY"
          : ready && healthOk
          ? "✓ STATION READY"
          : "✗ STATION NOT READY"}
      </div>
    </div>
  );
}
