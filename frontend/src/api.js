// Single point of contact with the backend. No component computes flow state;
// the backend is the source of truth and the only thing that sets can_advance.

const BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

async function req(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      detail = (await res.json()).detail || detail;
    } catch (_) {}
    throw new Error(`${res.status}: ${detail}`);
  }
  return res.json();
}

export const api = {
  health: () => req("/health"),
  listWorkOrders: () => req("/work-orders"),
  start: (id) => req(`/work-orders/${id}/start`, { method: "POST" }),
  currentStep: (id) => req(`/work-orders/${id}/current-step`),
  postVisionState: (id, body) =>
    req(`/work-orders/${id}/vision-state`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  validateStep: (id, body = {}) =>
    req(`/work-orders/${id}/validate-step`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  advance: (id, body = {}) =>
    req(`/work-orders/${id}/advance`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  finalSixS: (id, body = {}) =>
    req(`/work-orders/${id}/final-6s-check`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  auditLog: (id) => req(`/work-orders/${id}/audit-log`),
};

// Mock vision scenarios the operator/demo-driver can post (camera-less demo).
// These names match vision/mock_vision_state.py.
export const SCENARIOS = [
  { id: "station_ready", label: "Station ready (all home)" },
  { id: "wrong_sequence", label: "Wrong move (blue first)" },
  { id: "step1_done", label: "Red → assembly" },
  { id: "step2_done", label: "Blue → assembly" },
  { id: "step3_tool_removed", label: "Tool 1 removed" },
  { id: "step3_tool_returned", label: "Tool 1 returned" },
  { id: "step4_done", label: "Yellow → assembly" },
  { id: "step5_done", label: "Finished → complete" },
  { id: "final_6s_tool_missing", label: "6S: tool missing" },
  { id: "final_6s_pass", label: "6S: all home" },
];
