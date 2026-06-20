---
name: frontend-ui
description: Use this skill when building or editing the frontend fake MES dashboard — the work order queue, MPI step screen, gated Next Step button, live camera/snapshot panel, detected objects panel, error banner, audit log UI, and final 6S screen. It enforces that Next is disabled unless the backend returns can_advance=true and that the demo story is obvious immediately.
---

# Frontend / UI

## Purpose

Build and maintain the fake MES dashboard. The UI must make the workflow obvious in 10 seconds, be readable from 6 feet away, make errors unmissable, and — above all — **never allow advancement unless the backend returns `can_advance=true`.**

## When to use

- Creating or editing any file under `frontend/`.
- Building or wiring any dashboard component.
- Adjusting the gated Next button, error states, or the final 6S screen.
- Connecting the UI to backend endpoints via `api.js`.

## Inputs Claude should inspect

- `MAIN.md` sections 5 (rules), 9 (demo flow), 12 (DoD).
- Backend endpoints and response shapes (especially `can_advance` and its `reason`).
- `backend/app/models.py` for `AdvanceResult`, `VisionState`, `AuditEntry` shapes.

## Step-by-step procedure

1. Implement `api.js` as the single place that talks to the backend; no component fabricates flow state.
2. `App.jsx`: layout and routing between queue, step screen, and final 6S screen; poll backend for current state.
3. `WorkOrderQueue.jsx`: list work orders; select one to start.
4. `StationReadinessPanel.jsx`: show readiness/calibration status; green only when backend confirms.
5. `MPIStepPanel.jsx`: show the current step, instruction, and the **Next Step** button. The button is `disabled` whenever `can_advance !== true`; never enable it client-side.
6. `LiveCameraPanel.jsx`: show the live camera or the latest snapshot evidence.
7. `DetectedObjectsPanel.jsx`: render the backend/vision detected objects and their zones.
8. `ErrorBanner.jsx`: render the failure reason loudly when validation fails or sequence is wrong.
9. `AuditLogPanel.jsx`: render the append-only audit log (passes and failures).
10. `Final6SCheckPanel.jsx`: show the 6S return-to-home checklist; the Close button stays disabled until the backend confirms 6S passes.
11. Verify big type, high contrast, and clear color states (green pass / red fail) for 6-foot readability.

## Files this skill may edit

- `frontend/src/App.jsx`
- `frontend/src/api.js`
- `frontend/src/components/WorkOrderQueue.jsx`
- `frontend/src/components/StationReadinessPanel.jsx`
- `frontend/src/components/MPIStepPanel.jsx`
- `frontend/src/components/LiveCameraPanel.jsx`
- `frontend/src/components/DetectedObjectsPanel.jsx`
- `frontend/src/components/ErrorBanner.jsx`
- `frontend/src/components/AuditLogPanel.jsx`
- `frontend/src/components/Final6SCheckPanel.jsx`

## Files this skill should not touch

- Anything under `backend/`, `vision/`, or `integrations/`.
- Validation logic — the UI must only reflect backend decisions, never compute them.

## Expected output

A clear, high-contrast fake MES dashboard where the gated Next button is impossible to use unless `can_advance=true`, errors are visually obvious, detected objects and audit log are visible, and the final 6S screen blocks closure until the backend confirms 6S.

## Definition of done

- Next Step is `disabled` and visually inert whenever `can_advance !== true`.
- There is no client-side path to advance or to fake `can_advance`.
- Errors are large, red, and immediate.
- The Close action is blocked until backend confirms final 6S.
- The workflow is understandable in 10 seconds and readable from 6 feet.

## Common mistakes to avoid

- Enabling Next based on local state, optimism, or a timer instead of `can_advance`.
- Computing validation or zone logic in the frontend.
- Tiny text or low contrast that fails the 6-foot test.
- Hiding or softening errors — failures must be loud for the demo.
- Letting the Close button work before final 6S passes.
