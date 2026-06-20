# Backend — Fake MES + State Machine + Validation

FastAPI service that is the **source of truth** for Locked Vision MPI. It owns
work orders, MPI steps, the state machine, the validation engine, and the audit
log. It runs fully on **mocked vision** so the whole flow is testable without a
camera.

## Run

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Open http://localhost:8000/docs for interactive API docs.

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Liveness check |
| GET | `/work-orders` | List work orders + live status |
| POST | `/work-orders/{id}/start` | Start a work order |
| GET | `/work-orders/{id}/current-step` | Current MPI step + instruction |
| POST | `/work-orders/{id}/vision-state` | Submit vision evidence (`objects` or `scenario`) |
| POST | `/work-orders/{id}/validate-step` | Validate current step → `can_advance` |
| POST | `/work-orders/{id}/advance` | Advance (hard-gated by validation) |
| POST | `/work-orders/{id}/final-6s-check` | Final 6S reset gate |
| GET | `/work-orders/{id}/audit-log` | Full pass/fail audit trail |

## Vision evidence

POST a full object list:

```json
{ "objects": [ { "object": "red_block", "zone": "assembly_zone" } ] }
```

…or a named mock scenario (resolved from `vision/mock_vision_state.py`):

```json
{ "scenario": "step1_done" }
```

## Quick demo via curl

```bash
WO=WO-1001
curl -s localhost:8000/work-orders
curl -s -X POST localhost:8000/work-orders/$WO/start
# Block: wrong sequence
curl -s -X POST localhost:8000/work-orders/$WO/validate-step -H 'content-type: application/json' -d '{"scenario":"wrong_sequence"}'
# Pass step 1
curl -s -X POST localhost:8000/work-orders/$WO/validate-step -H 'content-type: application/json' -d '{"scenario":"step1_done"}'
curl -s -X POST localhost:8000/work-orders/$WO/advance
```

## Non-negotiables enforced here

- `can_advance` is set **only** by `validation_engine.py`.
- `/advance` re-validates before moving — no trust in the caller.
- Work order cannot reach `completed` until `final-6s-check` passes.
- Every validate / advance / 6S call is written to `data/audit_log.jsonl`.
