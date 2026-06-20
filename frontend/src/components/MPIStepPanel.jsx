// The MPI step screen + the hard gate. The Next Step button is disabled unless
// the backend's last validation returned can_advance === true. There is NO
// client-side path to enable it.
export default function MPIStepPanel({ stepInfo, validation, onValidate, onNext, busy }) {
  if (!stepInfo) {
    return (
      <div className="panel">
        <h2>MPI Step</h2>
        <div className="meta">Select a work order and press Start.</div>
      </div>
    );
  }

  const status = stepInfo.status;
  const allStepsDone =
    status === "awaiting_final_6s" || status === "completed";
  const canAdvance = validation?.can_advance === true;

  return (
    <div className="panel">
      <div className="step-head">
        <h2>Current MPI Step</h2>
        <span className="step-num">
          {allStepsDone
            ? "All steps complete"
            : `Step ${stepInfo.current_step} of ${stepInfo.total_steps}`}
        </span>
      </div>

      <div className="step-instruction">{stepInfo.instruction}</div>

      {!allStepsDone && (
        <>
          <div className={`gate-state ${canAdvance ? "pass" : "block"}`}>
            {canAdvance ? "✓ Verified — clear to advance" : "● Awaiting visual verification"}
          </div>

          <div style={{ display: "flex", gap: 10, marginBottom: 12 }}>
            <button
              className="btn-primary"
              style={{ flex: 1 }}
              disabled={busy}
              onClick={onValidate}
            >
              Verify Step (check vision)
            </button>
          </div>

          <button
            className={`next-btn ${canAdvance ? "enabled" : "disabled"}`}
            disabled={!canAdvance || busy}
            onClick={onNext}
            title={canAdvance ? "" : "Backend has not returned can_advance=true"}
          >
            {canAdvance ? "NEXT STEP →" : "NEXT STEP LOCKED 🔒"}
          </button>
        </>
      )}

      {allStepsDone && (
        <div className="ok-banner">
          All MPI steps verified. Proceed to the Final 6S check to close the work order.
        </div>
      )}
    </div>
  );
}
