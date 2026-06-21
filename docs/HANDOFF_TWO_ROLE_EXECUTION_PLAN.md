# Vision MPI Two-Role Execution Plan

One unified handoff for the two people/agents working alongside the backend:
**Role 1 — Frontend Integration** and **Role 2 — Sponsor Integration**. Each role
has its own loop, checklist, and success condition. The backend is already built
and is the single source of truth.

## System Truth

- **Backend owns truth.** It is the only component that decides whether a Work
  Order may open. `can_open_work_order` is computed in exactly one place:
  `backend/app/verification_session_service.py`.
- **Frontend sends events.** Camera UI, snapshots, block submissions, status
  polling, and display — nothing more. It never computes pass/fail.
- **Sponsor integrations return evidence.** A PPE model returns predictions
  (labels, confidence, boxes, raw JSON). It never returns unlock permission.
- A Work Order opens **only** when the backend returns:
  ```json
  { "can_open_work_order": true }
  ```
- That requires **BOTH**:
  1. PPE verified **and not expired**, and
  2. the block sequence completed correctly.
- **Required sequence: GREEN → BLUE → RED → YELLOW** (single source:
  `safety_config.REQUIRED_BLOCK_SEQUENCE`).

### Hard rules (both roles)

- Do not hardcode success.
- Do not let frontend payloads override backend truth (a client-sent
  `can_open_work_order` is ignored).
- Do not silently fix operator mistakes. If the operator submits the wrong
  block/color/action, the **frontend still sends it**; the **backend catches it,
  logs it, returns the error, and keeps the Work Order locked**.

### Endpoints (already implemented)

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/verification-sessions/start` | Start a session for a Work Order |
| POST | `/api/verification-sessions/{id}/ppe-check` | Submit a PPE snapshot (multipart) |
| POST | `/api/verification-sessions/{id}/blocks/submit` | Submit one block color |
| GET | `/api/verification-sessions/{id}/status` | Read current state + `can_open_work_order` |
| POST | `/api/work-orders/{id}/unlock` | Authoritative gate (PPE + sequence) |

### Core backend flow

1. Start verification session.
2. Submit PPE snapshot.
3. Backend checks PPE through the configured provider (or labeled mock).
4. Submit block colors one by one.
5. Backend validates against `REQUIRED_BLOCK_SEQUENCE`.
6. Backend catches and logs wrong block order.
7. Backend computes `can_open_work_order` in exactly one place.
8. Unlock only succeeds when backend state says `can_open_work_order: true`.

---

## Role 1: Frontend Integration Role

For the person/agent **building the frontend**. You own the camera UI and what the
operator sees — not the decision.

**Frontend responsibilities**
- Build camera UI.
- Start a verification session.
- Capture a PPE snapshot.
- Submit the PPE image to the backend.
- Submit block colors/events to the backend.
- Poll or request status from the backend.
- Display backend messages/errors.
- Enable **Open Work Order** only when backend returns `can_open_work_order: true`.
- Show a **DEV/MOCK** badge when the backend response indicates `mode: "mock"`.
- Do **not** prevent wrong actions locally.
- Do **not** hardcode pass/fail.
- Do **not** reorder block colors.
- Do **not** skip failed states.
- Do **not** open the WO from frontend-only logic.

### LOOP 1: Frontend Verification Loop

1. **Start session**
   - Call `POST /api/verification-sessions/start`.
   - Store `session_id`.
   - Display **WO locked**.

2. **PPE check**
   - Capture a camera snapshot.
   - Call `POST /api/verification-sessions/{id}/ppe-check`.
   - Display `ppe_verified`, `confidence`, `reason`, `expires_at`.
   - If `mode` is `mock`, show a **DEV/MOCK** badge.

3. **Block sequence submission**
   - Operator submits/scans/selects a block color.
   - Frontend sends the submitted color to
     `POST /api/verification-sessions/{id}/blocks/submit`.
   - Do **not** block wrong local actions.
   - Display the backend response clearly enough for the operator to understand.

4. **Status refresh**
   - Call `GET /api/verification-sessions/{id}/status`.
   - Show `expected_next_color`.
   - Show `submitted_sequence`.
   - Show `sequence_passed`.
   - Show `can_open_work_order`.

5. **Unlock attempt**
   - Enable **Open Work Order** only if `can_open_work_order` is `true`.
   - Call `POST /api/work-orders/{id}/unlock`.
   - Display the backend result.

**Frontend success condition** — the loop is complete only when it:
- uses the session endpoints,
- displays backend errors,
- sends wrong actions to the backend instead of preventing them locally, and
- enables the WO only from backend `can_open_work_order: true`.

Full contract: [`docs/frontend/API_CONTRACT_FOR_FRONTEND.md`](frontend/API_CONTRACT_FOR_FRONTEND.md).

---

## Role 2: Sponsor Integration Role

For the person/agent **connecting sponsor APIs or a real PPE model provider**. You
provide evidence — not the decision.

**Sponsor responsibilities**
- Replace mock PPE mode with a real provider.
- Add the provider integration inside `ppe_service.py` or a clean provider module.
- Keep provider responses **evidence-only**.
- Return labels/classes, confidence, bounding boxes if available, and raw JSON.
- Do **not** let the sponsor/model directly unlock the WO.
- Map provider labels into the backend positive/negative classes.
- Document required environment variables.
- Keep the **backend** as the final decision-maker.

### LOOP 2: Sponsor PPE Provider Loop

1. **Choose provider**
   - Confirm `PPE_MODEL_PROVIDER`.
   - Confirm whether using Roboflow or another sponsor/model API.
   - Confirm the required env vars.

2. **Configure credentials**
   - Add/update `.env.example`.
   - Document real env vars in `docs/setup/ENVIRONMENT_VARIABLES.md`.
   - Never commit secrets.

3. **Implement provider call**
   - Add the real call in `ppe_service.py` or a provider-specific module.
   - Send the image/snapshot to the provider.
   - Receive the prediction/evidence response.
   - Normalize the response into the backend format
     (`[{ "class", "confidence", "x", "y", "width", "height" }]`).

4. **Map labels**
   - Positive PPE labels may include: `goggles`, `safety_glasses`,
     `safety-glasses`, `glasses`, `eye_protection`.
   - Negative/missing PPE labels may include: `no_goggles`, `no-safety-glasses`,
     `missing_goggles`, `missing_eye_protection`.

5. **Decision remains backend-owned**
   - The provider returns evidence.
   - `ppe_service.decide()` applies the thresholds/policy.
   - `verification_session_service.py` computes `can_open_work_order`.
   - The provider must **never** return final unlock permission.

6. **Test real provider or labeled mock mode**
   - Confirm the PPE **pass** case.
   - Confirm the PPE **fail** case.
   - Confirm **expired** PPE keeps the WO locked.
   - Confirm **full sequence + valid PPE** unlocks the WO.
   - Confirm a **wrong block** is still logged and rejected.

**Sponsor success condition** — the loop is complete only when:
- a real provider or sponsor integration is wired cleanly,
- env vars are documented,
- provider output is normalized,
- the backend remains the final decision-maker, and
- tests or manual verification prove **no hardcoded unlock** exists.

Full handoff: [`docs/sponsors/SPONSOR_INTEGRATION_HANDOFF.md`](sponsors/SPONSOR_INTEGRATION_HANDOFF.md).

---

## Boundaries at a glance

| | Frontend Role | Sponsor Role | Backend |
|---|---|---|---|
| Owns truth | ❌ | ❌ | ✅ |
| Sends events | ✅ | — | — |
| Returns evidence | — | ✅ | — |
| Decides `can_open_work_order` | ❌ | ❌ | ✅ |
| Catches wrong actions | ❌ (forwards them) | — | ✅ (logs + rejects) |

## Validation

```bash
cd backend
../.venv/bin/python tests/test_verification.py   # PPE + block-sequence workflow
../.venv/bin/python smoke_test.py                # existing MPI flow (no regressions)
```

Both must pass. No frontend build is required, and no secrets are committed.

## Related docs

- Backend truth engine: [`docs/backend/PPE_AND_SEQUENCE_BACKEND.md`](backend/PPE_AND_SEQUENCE_BACKEND.md)
- Frontend contract + loop: [`docs/frontend/API_CONTRACT_FOR_FRONTEND.md`](frontend/API_CONTRACT_FOR_FRONTEND.md)
- Sponsor handoff + loop: [`docs/sponsors/SPONSOR_INTEGRATION_HANDOFF.md`](sponsors/SPONSOR_INTEGRATION_HANDOFF.md)
- Environment variables: [`docs/setup/ENVIRONMENT_VARIABLES.md`](setup/ENVIRONMENT_VARIABLES.md)
- Testing guide: [`docs/testing/BACKEND_TESTING_GUIDE.md`](testing/BACKEND_TESTING_GUIDE.md)
