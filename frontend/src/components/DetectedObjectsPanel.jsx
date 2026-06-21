const COLORS = {
  red_block: "#f85149",
  blue_block: "#2f81f7",
  yellow_block: "#f0c000",
  green_block: "#2ea043",
  finished_assembly: "#a371f7",
};

export default function DetectedObjectsPanel({ objects }) {
  return (
    <div className="panel">
      <h2>Detected Objects</h2>
      {(!objects || objects.length === 0) && (
        <div className="meta">No vision evidence yet.</div>
      )}
      {objects &&
        objects.map((o) => {
          const inHand = o.zone === null || o.zone === undefined;
          const placed = !inHand && o.zone !== `${o.object.replace("_block", "")}_home`;
          return (
            <div className="obj-row" key={o.object}>
              <span>
                <span className="swatch" style={{ background: COLORS[o.object] || "#666" }} />
                {o.object}
              </span>
              <span className={`zone-tag ${inHand ? "hand" : placed ? "placed" : ""}`}>
                {inHand ? "in hand / off-zone" : o.zone}
              </span>
            </div>
          );
        })}
    </div>
  );
}
