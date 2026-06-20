export default function WorkOrderQueue({ workOrders, selectedId, onSelect, onStart }) {
  return (
    <div className="panel">
      <h2>Work Order Queue</h2>
      {workOrders.length === 0 && <div className="meta">No work orders.</div>}
      {workOrders.map((wo) => (
        <div
          key={wo.work_order_id}
          className={`wo ${wo.work_order_id === selectedId ? "selected" : ""}`}
          onClick={() => onSelect(wo.work_order_id)}
          style={{ marginBottom: 10 }}
        >
          <div style={{ display: "flex", justifyContent: "space-between" }}>
            <span className="id">{wo.work_order_id}</span>
            <span className={`badge ${wo.status}`}>{wo.status.replace(/_/g, " ")}</span>
          </div>
          <div className="meta">{wo.product}</div>
          <div className="meta">
            {wo.mpi_id} · step {Math.min(wo.current_step, wo.total_steps)}/{wo.total_steps}
          </div>
          {wo.status === "queued" && (
            <button
              className="btn-start"
              style={{ marginTop: 10, width: "100%" }}
              onClick={(e) => {
                e.stopPropagation();
                onStart(wo.work_order_id);
              }}
            >
              ▶ Start Work Order
            </button>
          )}
        </div>
      ))}
    </div>
  );
}
