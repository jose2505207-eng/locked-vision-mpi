---
name: vision-camera
description: Use this skill when building or editing the vision system — camera capture, OpenCV color detection for LEGO blocks, zone mapping, camera lock/calibration, snapshot capture, or dataset structure. It produces structured vision evidence for the backend and prioritizes a fixed camera, a golden view, and consistent zones.
---

# Vision / Camera

## Purpose

Build and maintain the vision module that turns a locked overhead camera into **structured evidence** for the backend. It detects colored LEGO blocks, maps detected objects to zones, and returns a vision state that the backend's validation engine can consume. Vision reports what it sees — it never decides flow.

## When to use

- Creating or editing any file under `vision/`.
- Implementing or tuning OpenCV color detection for LEGO blocks.
- Defining or adjusting zones and object→zone mapping.
- Building the camera lock / calibration placeholder or snapshot capture.
- Producing the mock vision state used by the backend before the camera works.

## Inputs Claude should inspect

- `MAIN.md` sections 5 (rules) and 9 (demo flow).
- `backend/app/models.py` — the `VisionState` contract the backend expects.
- `backend/app/data/zones.json` — agreed zone definitions.
- Existing snapshots in `vision/snapshots/` for calibration reference.

## Step-by-step procedure

1. Lock the contract first: agree the exact `VisionState` shape with the backend (objects, colors, zones, confidence, timestamp).
2. Implement `mock_vision_state.py` returning that exact shape, so the backend can develop immediately.
3. Implement `camera.py`: capture from a fixed camera; expose a single frame grab. Assume the camera does not move.
4. Establish a **golden view** — the canonical framing all zones are defined against; document it.
5. Implement `color_detector.py`: HSV-based detection for the LEGO block colors used in the demo; return detected objects with color + position.
6. Implement `zone_mapper.py`: map each detected object's position to a zone from `zones.json`; output object→zone assignments.
7. Implement `calibration.py`: a camera lock / calibration placeholder that flags "camera moved" if the golden view drifts.
8. Implement snapshot capture into `vision/snapshots/` as evidence for the audit trail and dataset.
9. Keep the real detector's output identical to the mock, so it drops into the backend with no changes.

## Files this skill may edit

- `vision/camera.py`
- `vision/color_detector.py`
- `vision/zone_mapper.py`
- `vision/calibration.py`
- `vision/mock_vision_state.py`
- `vision/snapshots/` (captured images)

## Files this skill should not touch

- Anything under `backend/` (only read `models.py` and `zones.json` for the contract), `frontend/`, or `integrations/`.
- Validation/flow logic — vision produces evidence only; it must not decide `can_advance`.

## Expected output

A vision module that detects colored LEGO blocks, maps them to zones, and returns a structured `VisionState` matching the backend contract — with a mock implementation that is interface-identical to the real one, plus snapshot evidence and a calibration/"camera moved" placeholder.

## Definition of done

- Mock and real vision return the exact same `VisionState` shape.
- Color detection reliably distinguishes the demo's LEGO colors under the golden view.
- Object→zone mapping is consistent and uses `zones.json`.
- Calibration placeholder can flag a moved camera.
- Snapshots are captured for evidence.
- Vision never decides flow.

## Common mistakes to avoid

- Letting vision return `can_advance` or any flow decision — that belongs to the backend.
- Tuning detection to a moving camera; the camera is fixed and the view is golden.
- Diverging the mock and real output shapes.
- Hardcoding zone coordinates outside `zones.json` without documenting them.
- Over-engineering with ML when HSV color detection is enough for the MVP.
