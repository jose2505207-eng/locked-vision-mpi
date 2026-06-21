# Frontend API Contract — PPE + Block Sequence Gate

Hey 👋 — this is everything you need to wire the Safety-Glasses + Block-Sequence
gate. **You build the camera UI and feedback; the backend decides truth.**

## The one rule that matters

> Only enable the **Open Work Order** button when the backend returns:
> ```json
> { "can_open_work_order": true }
> ```

Never hardcode pass. Never compute the sequence or PPE result in the browser.
Never send `can_open_work_order` to "force" it — the backend ignores it.

Also important: **do not prevent operator mistakes.** If the operator does the
wrong thing, still send the event to the backend, then display whatever the
backend returns (including the error). The backend catches and logs it.

Base URL: `http://localhost:8000` (set `VITE_API_URL` to override).

---

## Flow overview

1. `start` a verification session for the Work Order → get a `session_id`.
2. Send a camera snapshot to `ppe-check`.
3. Submit each block color to `blocks/submit` (in whatever order the operator does it).
4. Poll `status` (or read each response) and enable **Open Work Order** when
   `can_open_work_order === true`.
5. Optionally call `unlock` as the final gate before opening.

---

## 1) Start a session

`POST /api/verification-sessions/start`

```json
{ "work_order_id": "WO-001", "worker_id": "operator-001" }
```

Response:
```json
{
  "session_id": "vs-ab12...",
  "work_order_id": "WO-001",
  "worker_id": "operator-001",
  "ppe_verified": false,
  "sequence_passed": false,
  "expected_next_color": "green",
  "submitted_sequence": [],
  "can_open_work_order": false
}
```

Keep `session_id` for all later calls.

## 2) PPE check (camera snapshot)

`POST /api/verification-sessions/{session_id}/ppe-check` — `multipart/form-data`:

- `image`: the snapshot file (required)
- `work_order_id`, `worker_id`: optional

```js
const fd = new FormData();
fd.append("image", blob, "snap.jpg");
await fetch(`${BASE}/api/verification-sessions/${sid}/ppe-check`, { method: "POST", body: fd });
```

Response:
```json
{
  "session_id": "vs-ab12...",
  "ppe_verified": true,
  "confidence": 0.86,
  "reason": "Safety glasses verified: 'safety_glasses' at 86.0%.",
  "mode": "mock",                     // "mock" in dev, "live" with a real model
  "expires_at": "2026-06-21T05:47:10Z",
  "predictions": [ /* raw model output */ ],
  "sequence_passed": false,
  "expected_next_color": "green",
  "can_open_work_order": false
}
```

- Show green when `ppe_verified: true`, red otherwise (use `reason`).
- If `mode === "mock"`, show a small **DEV / MOCK** badge so it's never confused
  with production.
- PPE expires (`expires_at`, ~20s). If it expires before the WO opens, re-check.
- If the model is misconfigured you'll get **HTTP 502** with `{ "detail": "..." }` —
  show the message; do not treat as verified.

## 3) Submit a block color

`POST /api/verification-sessions/{session_id}/blocks/submit`

```json
{ "submitted_color": "green" }
```

**Correct** response:
```json
{
  "session_id": "vs-ab12...",
  "accepted": true,
  "submitted_color": "green",
  "submitted_sequence": ["green"],
  "expected_next_color": "blue",
  "sequence_passed": false,
  "can_open_work_order": false
}
```

**Final correct** (after yellow): `"sequence_passed": true`, `"expected_next_color": null`.

**Wrong** response (operator submitted red when blue was expected):
```json
{
  "session_id": "vs-ab12...",
  "accepted": false,
  "error_detected": true,
  "error_type": "wrong_block_order",
  "expected_color": "blue",
  "received_color": "red",
  "submitted_sequence": ["green"],
  "sequence_passed": false,
  "can_open_work_order": false,
  "message": "Wrong block order detected. Work Order remains locked."
}
```

Other `error_type` values: `invalid_color`, `sequence_already_complete`.

UI: on `accepted: false`, show a red error using `message`, keep the WO locked,
and let them try the correct `expected_color` next. **Do not** block the wrong
submission client-side — send it, then show the backend's response.

## 4) Status (poll this)

`GET /api/verification-sessions/{session_id}/status`

```json
{
  "session_id": "vs-ab12...",
  "work_order_id": "WO-001",
  "worker_id": "operator-001",
  "ppe_verified": true,
  "ppe_confidence": 0.86,
  "sequence_passed": true,
  "required_sequence": ["green", "blue", "red", "yellow"],
  "submitted_sequence": ["green", "blue", "red", "yellow"],
  "expected_next_color": null,
  "can_open_work_order": true,
  "errors": [ { "error_type": "wrong_block_order", "message": "...", "created_at": "..." } ]
}
```

Render `required_sequence` vs `submitted_sequence` as a progress checklist, and
the `errors` list as a recent-attempts log. **Enable Open Work Order only when
`can_open_work_order === true`.**

## 5) Unlock (final gate)

`POST /api/work-orders/{work_order_id}/unlock`  (body optional)

Allowed:
```json
{ "work_order_id": "WO-001", "unlocked": true, "can_open_work_order": true,
  "message": "Work Order unlocked. PPE and block sequence verified." }
```
Blocked (HTTP 200, read the body — not the status code):
```json
{ "work_order_id": "WO-001", "unlocked": false, "can_open_work_order": false,
  "message": "Work Order remains locked.", "missing_requirements": ["ppe_verification", "block_sequence"] }
```

## UI states cheat-sheet

| Backend says | Show |
|---|---|
| `ppe_verified: false` | Red "Safety glasses not verified" + `reason`, Open disabled |
| `accepted: false` | Red error from `message`, highlight `expected_color`, Open disabled |
| `sequence_passed: false` | Progress checklist, Open disabled |
| `can_open_work_order: true` | Green "Verified", **enable Open Work Order** |
| HTTP 502 on ppe-check | "PPE model error" from `detail`, Open disabled |

## Do / Don't

- ✅ Send every operator action (even wrong ones) to the backend.
- ✅ Gate the button on `can_open_work_order`.
- ✅ Show `mode: mock` as a dev badge.
- ❌ Don't compute PPE/sequence pass in the browser.
- ❌ Don't send `can_open_work_order` / `accepted` to force state (ignored).
- ❌ Don't block wrong submissions locally — let the backend catch them.
