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
  visionState: (id) => req(`/work-orders/${id}/vision-state`),
  validateReadiness: (id, body = {}) =>
    req(`/work-orders/${id}/validate-readiness`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  resetDemo: () => req(`/demo/reset`, { method: "POST" }),

  // --- Block-sequence verification session (the demo flow) ---
  vsStart: (workOrderId, workerId = "operator-001") =>
    req(`/api/verification-sessions/start`, {
      method: "POST",
      body: JSON.stringify({ work_order_id: workOrderId, worker_id: workerId }),
    }),
  vsSubmitBlock: (sessionId, color) =>
    req(`/api/verification-sessions/${sessionId}/blocks/submit`, {
      method: "POST",
      body: JSON.stringify({ submitted_color: color }),
    }),
  vsStatus: (sessionId) => req(`/api/verification-sessions/${sessionId}/status`),
  vsUnlock: (workOrderId) =>
    req(`/api/work-orders/${workOrderId}/unlock`, { method: "POST", body: "{}" }),

  // --- Safety-Glasses PPE verification ---
  ppeConfig: () => req("/api/ppe/config"),
  ppeCheck: async (workOrderId, workerId, blob) => {
    const fd = new FormData();
    fd.append("image", blob, "ppe.jpg");
    fd.append("work_order_id", workOrderId);
    fd.append("worker_id", workerId);
    const res = await fetch(`${BASE}/api/ppe/check`, { method: "POST", body: fd });
    if (!res.ok) {
      let detail = res.statusText;
      try {
        detail = (await res.json()).detail || detail;
      } catch (_) {}
      throw new Error(`${res.status}: ${detail}`);
    }
    return res.json();
  },
  unlock: (workOrderId, workerId) =>
    req(`/api/work-orders/${workOrderId}/unlock`, {
      method: "POST",
      body: JSON.stringify({ worker_id: workerId }),
    }),
};

// Base URL of the Python vision bridge's UI server (--serve-ui). The browser
// only reads frames/state from here; it never opens the webcam itself.
export const VISION_URL =
  import.meta.env.VITE_VISION_URL || "http://localhost:8010";

// Mock vision scenarios the operator/demo-driver can post (camera-less demo).
// These names match vision/mock_vision_state.py.
export const SCENARIOS = [
  { id: "station_ready", label: "Station ready (all home)" },
  { id: "wrong_sequence", label: "Wrong move (blue first)" },
  { id: "step1_done", label: "Red → assembly" },
  { id: "step2_done", label: "Blue → assembly" },
  { id: "tool_1_removed_only", label: "Tool 1 removed (sim)" },
  { id: "tool_1_returned_only", label: "Tool 1 returned (sim)" },
  { id: "step4_done", label: "Yellow → assembly" },
  { id: "step5_done", label: "Finished → complete (sim)" },
  { id: "final_6s_tool_missing", label: "6S: tool missing" },
  { id: "final_6s_pass", label: "6S: all home" },
];
