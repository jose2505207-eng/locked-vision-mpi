// Station readiness = camera locked + calibrated + zones clear.
// In the mock demo, "station_ready" evidence drives this green.
export default function StationReadinessPanel({ ready, healthOk }) {
  const checks = [
    { label: "Backend / MES online", ok: healthOk },
    { label: "Camera locked (golden view)", ok: ready },
    { label: "Calibration within tolerance", ok: ready },
    { label: "Zones clear at home", ok: ready },
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
