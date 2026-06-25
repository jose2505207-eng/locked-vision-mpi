# Architecture — Locked Vision MPI

## The one rule everything serves

> **The fake MES is the source of truth. The vision system provides evidence.
> The state machine validates the MPI sequence. The frontend must never allow
> manual advancement unless the backend returns `can_advance=true`.**

## Data flow

```
┌─────────────┐   defines    ┌──────────────┐
│  Fake MES   │ ───────────► │  MPI steps   │
│ (truth)     │              │  + zones     │
└─────────────┘              └──────┬───────┘
                                    │ expected step
                                    ▼
┌─────────────┐  evidence   ┌──────────────────┐  can_advance?  ┌───────────┐
│   Vision    │ ──────────► │  State machine   │ ─────────────► │ Frontend  │
│ mock/OpenCV │             │  + Validation    │                │ (obeys it)│
└─────────────┘             └────────┬─────────┘                └───────────┘
                                     │ every pass/fail
                                     ▼
                              ┌──────────────┐
                              │  Audit log   │
                              └──────────────┘
```

## Components

### Backend (`backend/app/`) — source of truth
- `fake_mes_service.py` — loads work orders, MPI steps, zones (read-only truth).
- `mpi_state_machine.py` — per-work-order runtime: current step, status,
  temporal progress flags, latest vision evidence; controls transitions.
- `validation_engine.py` — **the only place `can_advance` becomes `True`.** Pure
  functions: `validate_step()` and `validate_final_6s()`.
- `audit_logger.py` — append-only `data/audit_log.jsonl`; every pass/fail.
- `models.py` — pydantic contracts (`VisionObject`, `VisionState`,
  `ValidationResponse`, …).
- `main.py` — FastAPI endpoints; `/advance` **re-validates** before moving.
- `data/` — `work_orders.json`, `mpi_steps.json`, `zones.json`, `audit_log.jsonl`.

### Vision (`vision/`) — evidence only
- `mock_vision_state.py` — canned scenarios; the **contract** for real vision.
- `zone_mapper.py` — bounding-box center → zone (reads backend `zones.json`).
- `color_detector.py` — OpenCV HSV detection for LEGO blocks.
- `calibration.py` — ArUco camera-lock / "camera moved" check.
- `camera.py` — fixed-camera capture + snapshot evidence + end-to-end glue.

### Frontend (`frontend/src/`) — obeys the backend
- `api.js` — the only thing that talks to the backend.
- `App.jsx` — orchestration + state.
- `components/` — queue, station readiness, MPI step (gated Next button), live
  camera / vision simulator, detected objects, error banner, audit log, final 6S.

## The vision contract

Both mock and real vision return the identical shape, so real vision drops in
with **no backend changes**:

```json
{
  "objects": [
    { "object": "red_block", "zone": "assembly_zone", "bbox": [x1,y1,x2,y2], "confidence": 0.98 }
  ],
  "source": "mock",
  "scenario": "step1_done"
}
```

`zone: null` = detected but not inside any zone (e.g. tool in hand).

## MPI: WO-1001 / MPI-LEGO-001

| Step | Type | Rule |
|---|---|---|
| 1 | move | `red_block` → `assembly_zone` |
| 2 | move | `blue_block` → `assembly_zone` |
| 3 | tool_use | `tool_1` leaves `tool_1_home` **and returns** |
| 4 | move | `yellow_block` → `assembly_zone` |
| 5 | move | `finished_assembly` → `complete_zone` |
| Final 6S | gate | tools home · `green_block` home · assembly clear · finished in complete |

## Why the gate cannot be bypassed

- The frontend's Next button is `disabled` unless the last validation returned
  `can_advance === true`. No client code sets that flag.
- Even if a caller hits `/advance` directly, the endpoint **re-runs the
  validation engine** and refuses to move unless evidence satisfies the step.
- `status` cannot become `completed` until `/final-6s-check` passes.
- Every attempt — pass or block — is appended to the audit log.

## Status lifecycle

`queued → in_progress → awaiting_final_6s → completed`
