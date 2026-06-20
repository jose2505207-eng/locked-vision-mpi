// Station readiness = camera locked + calibrated + zones clear.
// Reflects the CURRENT mock evidence: green when the station is clean,
// red while parts are out on the bench / tools are away from home.
export default function StationReadinessPanel({ ready, healthOk, zonesClear }) {
  const checks = [
    { label: "Backend / MES online", ok: healthOk },
    { label: "Camera locked (golden view)", ok: healthOk },
    { label: "Calibration within tolerance", ok: healthOk },
    { label: "Zones clear at home", ok: zonesClear },
  ];
  return (
    <div className="panel">
      <h2>Station Readiness</h2>
      {checks.map((c) => (
        <div className="sixs-item" key={c.label}>
          <span className={`dot ${c.ok ? "ok" : "bad"}`} />
          <span>{c.label}</span>
        </div>
      ))}
      <div
        className={ready && healthOk ? "ok-banner" : "error-banner"}
        style={{ marginTop: 12, fontSize: 15 }}
      >
        {ready && healthOk ? "✓ STATION READY" : "✗ STATION NOT READY"}
      </div>
    </div>
  );
}
