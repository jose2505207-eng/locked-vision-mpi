# PPE + Block Sequence — Backend Truth Engine

This document explains the backend workflow that decides whether a Work Order may
be opened. **The backend owns truth.** The frontend captures images, shows
feedback, and sends events — it never decides PPE pass, sequence pass, or unlock.

## The unlock rule (non-negotiable)

A Work Order may open **only** when BOTH are true:

1. **Safety glasses verified** (and the check has not expired), and
2. **Block sequence completed correctly.**

```
can_open_work_order = (ppe_verified AND not expired) AND sequence_passed
```

This is computed in exactly one place: `verification_session_service._can_open()`.
A client-supplied `can_open_work_order` is **ignored**.

## Required block sequence (single source of truth)

```python
# backend/app/safety_config.py
REQUIRED_BLOCK_SEQUENCE = ["green", "blue", "red", "yellow"]
```

Change this one list and the whole backend follows (expected color, validation,
status, tests). Order is **GREEN → BLUE → RED → YELLOW**.

## PPE verification flow

1. Frontend posts a camera snapshot to `POST /api/verification-sessions/{id}/ppe-check`.
2. `ppe_service.run_check()` sends the image to the configured provider:
   - **roboflow** (live) when `ROBOFLOW_API_KEY` + `ROBOFLOW_PPE_MODEL_ID` are set;
   - **mock** (development) otherwise — every mock response is labeled `mode: "mock"`
     and the reason is prefixed `[MOCK]`. Mock is never silently treated as production.
3. The model returns predictions (class, confidence, bbox, raw JSON). **The model
   does not unlock anything.**
4. `ppe_service.decide()` applies the policy (the backend decision):
   - accepted labels: `goggles, safety_glasses, safety-glasses, glasses, eye_protection, …`
   - rejected labels: `no_goggles, no-safety-glasses, missing_goggles, missing_eye_protection, …`
   - a positive label at/above `PPE_MIN_CONFIDENCE` (default 0.72) verifies; a strong
     negative label blocks.
5. The check is persisted (`ppe_checks`) with the evidence image path and an
   `expires_at` (now + `PPE_CHECK_EXPIRATION_SECONDS`, default 20s). After expiry,
   the session's PPE is no longer "current" and the WO re-locks.

## Block sequence flow

1. Frontend posts each detected/selected color to
   `POST /api/verification-sessions/{id}/blocks/submit` as `{"submitted_color": "..."}`.
2. `block_sequence_service.validate_submission()` checks it against the expected
   next color. It **never** reorders, skips, or silently fixes input:
   - correct → appended; `expected_next_color` advances; on the last color
     `sequence_passed = true`.
   - wrong → **rejected**, `error_type: "wrong_block_order"`, the submitted sequence
     is left **unchanged**, WO stays locked.
   - unknown color → `error_type: "invalid_color"`.
   - extra after completion → `error_type: "sequence_already_complete"`.

## Unlock logic

`POST /api/work-orders/{id}/unlock` evaluates the **latest** verification session
for that Work Order and returns the flat contract body (HTTP 200 either way):

- allowed → `{ unlocked: true, can_open_work_order: true, missing_requirements: [] }`
- blocked → `{ unlocked: false, can_open_work_order: false, missing_requirements: [...] }`
  with `missing_requirements` listing `ppe_verification` and/or `block_sequence`.

The optional legacy `/work-orders/{id}/start` gate enforces the same combined
decision **only** when `PPE_REQUIRED=true` (off by default, so the mock vision demo
is unaffected).

## Audit / error logging

Every meaningful action is recorded as append-only evidence:

- `verification_events` (SQLite): `session_started`, `ppe_check`, `block_submit`
  — including **failed** attempts with `error_type` and `message`.
- `ppe_checks` (SQLite): each PPE decision with confidence, reason, raw
  predictions JSON, evidence image path, `created_at`, `expires_at`.
- The shared audit log (`audit_log.jsonl`) also receives PPE check events.

## Why the backend owns truth

The operator's physical state (glasses on, correct blocks placed) is what gates a
real manufacturing step. If the frontend could set `can_open_work_order`, a bug or
a tampered client could open a Work Order with no PPE and the wrong build. The
backend is the single arbiter; the frontend is a sensor + display.

## Code map

| File | Responsibility |
|---|---|
| `backend/app/safety_config.py` | `REQUIRED_BLOCK_SEQUENCE` + PPE env config (single source) |
| `backend/app/block_sequence_service.py` | Pure sequence validation (no I/O) |
| `backend/app/ppe_service.py` | Provider call (roboflow/mock) + `decide()` |
| `backend/app/verification_session_service.py` | Combines PPE + sequence; computes `can_open_work_order` |
| `backend/app/verification_store.py` | `verification_sessions` + `verification_events` (SQLite) |
| `backend/app/ppe_store.py` | `ppe_checks` table (SQLite) |
| `backend/app/verification_routes.py` | The 5 session endpoints + authoritative unlock |
| `backend/app/ppe_routes.py` | Standalone `/api/ppe/*` check + config |
