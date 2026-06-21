import { useEffect, useState } from "react";
import { api } from "../api.js";

// Small, read-only status badges for the sponsor stack (shadow mode). This panel
// is purely informational — it never affects the work-order flow. If the status
// endpoint is unreachable, it quietly shows everything inactive.
const BADGES = [
  ["sentry", "Sentry"],
  ["redis_events", "Redis events"],
  ["claude_assist", "Claude assist"],
  ["arize_logging", "Arize logging"],
  ["orkes_shadow", "Orkes shadow"],
];

export default function SponsorPanel() {
  const [badges, setBadges] = useState({});
  const [masterOn, setMasterOn] = useState(false);

  useEffect(() => {
    let live = true;
    const load = () =>
      api
        .sponsorsStatus()
        .then((s) => {
          if (!live) return;
          setBadges(s.badges || {});
          setMasterOn(!!s.sponsor_stack_enabled);
        })
        .catch(() => {});
    load();
    const id = setInterval(load, 5000);
    return () => {
      live = false;
      clearInterval(id);
    };
  }, []);

  return (
    <div className="panel sponsor-panel">
      <h2>
        Sponsor Stack <span className="sponsor-shadow">shadow{masterOn ? "" : " · off"}</span>
      </h2>
      <div className="sponsor-badges">
        {BADGES.map(([key, label]) => {
          const on = !!badges[key];
          return (
            <span key={key} className={`sponsor-badge ${on ? "on" : "off"}`}>
              <span className="sponsor-dot" />
              {label}: {on ? "active" : "inactive"}
            </span>
          );
        })}
      </div>
    </div>
  );
}
