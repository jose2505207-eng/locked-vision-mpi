import { useEffect, useState } from "react";
import { api } from "./api.js";
import WorkOrderQueue from "./components/WorkOrderQueue.jsx";
import StationReadinessPanel from "./components/StationReadinessPanel.jsx";
import MPIStepPanel from "./components/MPIStepPanel.jsx";
import LiveCameraPanel from "./components/LiveCameraPanel.jsx";
import DetectedObjectsPanel from "./components/DetectedObjectsPanel.jsx";
import ErrorBanner from "./components/ErrorBanner.jsx";
import AuditLogPanel from "./components/AuditLogPanel.jsx";
import Final6SCheckPanel from "./components/Final6SCheckPanel.jsx";

export default function App() {
  const [healthOk, setHealthOk] = useState(false);
  const [workOrders, setWorkOrders] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [stepInfo, setStepInfo] = useState(null);
  const [validation, setValidation] = useState(null); // last validate-step result
  const [sixSResult, setSixSResult] = useState(null);
  const [objects, setObjects] = useState([]);
  const [lastScenario, setLastScenario] = useState(null);
  const [audit, setAudit] = useState([]);
  const [stationReady, setStationReady] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  async function refreshWorkOrders() {
    const list = await api.listWorkOrders();
    setWorkOrders(list);
    return list;
  }

  async function refreshStep(id) {
    const info = await api.currentStep(id);
    setStepInfo(info);
    return info;
  }

  async function refreshAudit(id) {
    const { entries } = await api.auditLog(id);
    setAudit(entries);
  }

  useEffect(() => {
    api
      .health()
      .then(() => setHealthOk(true))
      .catch(() => setHealthOk(false));
    refreshWorkOrders()
      .then((list) => {
        if (list.length) setSelectedId(list[0].work_order_id);
      })
      .catch((e) => setError(String(e)));
  }, []);

  useEffect(() => {
    if (!selectedId) return;
    refreshStep(selectedId).catch((e) => setError(String(e)));
    refreshAudit(selectedId).catch(() => {});
  }, [selectedId]);

  async function guard(fn) {
    setBusy(true);
    setError(null);
    try {
      await fn();
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  const onStart = (id) =>
    guard(async () => {
      await api.start(id);
      setValidation(null);
      setSixSResult(null);
      await refreshWorkOrders();
      await refreshStep(id);
      await refreshAudit(id);
    });

  const onSimulate = (scenario) =>
    guard(async () => {
      const res = await api.postVisionState(selectedId, { scenario });
      setObjects(res.objects);
      setLastScenario(scenario);
      // Station-ready evidence flips the readiness panel green.
      if (scenario === "station_ready") setStationReady(true);
    });

  const onValidate = () =>
    guard(async () => {
      const res = await api.validateStep(selectedId);
      setValidation(res);
      setObjects(res.detected_objects || objects);
      await refreshAudit(selectedId);
    });

  const onNext = () =>
    guard(async () => {
      const res = await api.advance(selectedId);
      // After advancing, the new step must be re-verified from scratch.
      setValidation(null);
      await refreshWorkOrders();
      await refreshStep(selectedId);
      await refreshAudit(selectedId);
      if (res.status !== "passed") setValidation(res);
    });

  const onSixSCheck = () =>
    guard(async () => {
      const res = await api.finalSixS(selectedId);
      setSixSResult(res);
      setObjects(res.detected_objects || objects);
      await refreshWorkOrders();
      await refreshStep(selectedId);
      await refreshAudit(selectedId);
    });

  const status = stepInfo?.status;
  const showSixS = status === "awaiting_final_6s" || status === "completed";

  return (
    <div className="app">
      <div className="topbar">
        <div>
          <h1>🔒 Locked Vision MPI</h1>
          <div className="pitch">
            Visual proof connected to manufacturing execution — the MPI only moves
            forward when the real world is correct.
          </div>
        </div>
        <div className="health">
          <span className={`dot ${healthOk ? "ok" : "bad"}`} />
          backend {healthOk ? "online" : "offline"}
        </div>
      </div>

      {error && (
        <div className="error-banner" style={{ marginBottom: 16 }}>
          <span style={{ fontSize: 22 }}>⚠️</span> {error}
        </div>
      )}

      <div className="grid">
        {/* Left column */}
        <div className="col">
          <WorkOrderQueue
            workOrders={workOrders}
            selectedId={selectedId}
            onSelect={setSelectedId}
            onStart={onStart}
          />
          <StationReadinessPanel ready={stationReady} healthOk={healthOk} />
        </div>

        {/* Center column */}
        <div className="col">
          <ErrorBanner validation={showSixS ? null : validation} />
          <MPIStepPanel
            stepInfo={stepInfo}
            validation={validation}
            onValidate={onValidate}
            onNext={onNext}
            busy={busy}
          />
          <Final6SCheckPanel
            visible={showSixS}
            result={sixSResult}
            status={status}
            onCheck={onSixSCheck}
            busy={busy}
          />
          <DetectedObjectsPanel objects={objects} />
        </div>

        {/* Right column */}
        <div className="col">
          <LiveCameraPanel
            onSimulate={onSimulate}
            lastScenario={lastScenario}
            disabled={busy || !selectedId}
          />
          <AuditLogPanel entries={audit} />
        </div>
      </div>
    </div>
  );
}
