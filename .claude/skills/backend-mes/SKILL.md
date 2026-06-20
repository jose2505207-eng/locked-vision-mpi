---
name: backend-mes
description: Use this skill when building or editing the backend — FastAPI app, fake MES, MPI step logic, the state machine, the validation engine, audit logging, work order state, or backend data files. It enforces that no step advances unless validation passes, no work order closes until final 6S passes, and every pass/fail is logged.
---

# Backend / MES

## Purpose

Build and maintain the backend that is the **source of truth** for Locked Vision MPI. The backend owns work orders, MPI steps, zones, the state machine that decides `can_advance`, the validation engine that compares vision evidence to the expected step, and the append-only audit log.

## When to use

- Creating or editing any file under `backend/`.
- Adding/changing work orders, MPI steps, or zone definitions.
- Implementing or fixing the state machine, validation engine, or audit logging.
- Wiring backend endpoints consumed by the frontend or sponsor agents.

## Inputs Claude should inspect

- `MAIN.md` sections 5 (rules), 8 (scope), 11 (build order), 12 (DoD).
- Existing `backend/app/models.py` for current data contracts.
- `vision/mock_vision_state.py` — the shape of vision evidence the backend consumes.
- Existing data files in `backend/app/data/`.

## Step-by-step procedure

1. Confirm the change keeps the MES as source of truth and vision as evidence only.
2. Define/extend pydantic models in `models.py` (WorkOrder, MPIStep, Zone, VisionState, AdvanceResult, AuditEntry).
3. Seed/maintain data files: `work_orders.json`, `mpi_steps.json`, `zones.json`.
4. Implement `fake_mes_service.py` to load and serve MES data (read-only truth).
5. Implement `mpi_state_machine.py`: track current step per work order; expose the expected step and transitions.
6. Implement `validation_engine.py`: take current step + vision state, return `can_advance` with a reason. Never return `can_advance=true` unless evidence matches the expected step.
7. Implement `audit_logger.py`: append every pass and failure to `audit_log.jsonl` (timestamp, work order, step, result, reason, evidence summary).
8. Expose endpoints in `main.py`: list work orders, get current step, submit/poll vision validation, attempt advance, attempt close (with final 6S gate), read audit log.
9. Build against mock vision first; keep the interface identical so real vision drops in later.
10. Add the final 6S gate: closing a work order requires all parts/tools confirmed home.

## Files this skill may edit

- `backend/app/main.py`
- `backend/app/fake_mes_service.py`
- `backend/app/mpi_state_machine.py`
- `backend/app/validation_engine.py`
- `backend/app/audit_logger.py`
- `backend/app/models.py`
- `backend/app/data/work_orders.json`
- `backend/app/data/mpi_steps.json`
- `backend/app/data/zones.json`
- `backend/app/data/audit_log.jsonl`

## Files this skill should not touch

- Anything under `frontend/`, `vision/` (beyond reading the mock-state contract), or `integrations/`.
- The skill files themselves and the top-level docs (use `/demo-readiness` or `/github-handoff`).

## Expected output

A running FastAPI backend that drives the full work order flow against mock vision, returns a correct `can_advance` with a reason for every step, blocks closure until final 6S passes, and logs every pass/fail to `audit_log.jsonl`.

## Definition of done

- No endpoint returns `can_advance=true` unless `validation_engine` passes.
- Work order closure is impossible until final 6S validation passes.
- Every pass and every failure is written to the audit log.
- The vision contract is identical for mock and real vision.
- Backend runs from a clean clone with documented commands.

## Common mistakes to avoid

- Letting `can_advance` default to true or be set anywhere except the validation engine.
- Mutating MES truth data based on vision (vision is evidence, not truth).
- Skipping audit entries on failures (failures are the most important evidence).
- Coupling endpoints to mock vision so real vision can't replace it.
- Forgetting the final 6S gate on close.
