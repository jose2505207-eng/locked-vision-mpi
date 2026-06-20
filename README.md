# 🔒 Locked Vision MPI

**A fake MES-connected physical AI workstation.** A locked camera supervises a
workstation of colored LEGO blocks and simple tools. The operator cannot advance
to the next manufacturing step unless the system *visually verifies* that the
correct part/tool moved to the correct zone in the correct order — and the work
order cannot close until every tool and part is returned home for a final 6S
reset.

> **Pitch:** This is not a camera watching a table. This is **visual proof
> connected to manufacturing execution.** The MPI only moves forward when the
> real world is correct.

Built for **UC Berkeley AI Hackathon 2026**.

---

## Problem

In real manufacturing, MPI (Manufacturing Process Instruction) compliance is
mostly trust-based: the operator clicks "Next" and the MES believes them. There
is no physical verification that the right part went to the right place in the
right order, and no guarantee the station is reset before the next job. Result:
skipped/out-of-order steps, wrong parts, un-reset stations, and audit logs that
record *clicks*, not *reality*.

## Solution

Lock the digital instruction to the physical reality:

- A **fixed overhead camera** + OpenCV detects colored LEGO blocks and tools and
  maps them to **zones**.
- A **fake MES** holds the work order and the MPI step sequence (source of truth).
- A **state machine + validation engine** compare vision evidence to the expected
  step and decide `can_advance`.
- The **dashboard** physically cannot advance unless the backend returns
  `can_advance=true`, and cannot close the work order until **final 6S** passes.
- **Every** pass and failure is written to an **audit log**.

## Architecture

```
Fake MES (truth) ─► MPI step data ─► State machine ─► Validation ─► can_advance?
                                          ▲                              │
                                          │ evidence                     ▼
                                    Vision system  ───────────────►  Audit log
                                  (mock OR OpenCV)                       │
                                                                        ▼
                                                  Frontend (obeys can_advance only)
```

Core rule: **MES is truth · vision is evidence · the state machine validates ·
the frontend never bypasses the backend.** Full detail in
[ARCHITECTURE.md](ARCHITECTURE.md).

## Repo structure

```
locked-vision-mpi/
├── backend/      FastAPI fake MES, state machine, validation, audit log
├── vision/       Camera, OpenCV color detection, zone mapping, mock vision
├── frontend/     Vite + React fake MES dashboard (gated Next button)
├── integrations/ Sponsor scaffolds (Fetch, Sentry, Redis, Deepgram, Arize)
└── docs          README · ARCHITECTURE · TEAM_ROLES · SPONSOR_INTEGRATIONS · DEMO_SCRIPT
```

## Setup

The whole system runs on **mocked vision**, so you need no camera to demo it.

### 1. Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000     # http://localhost:8000/docs
```

### 2. Frontend

```bash
cd frontend
npm install
npm run dev                                    # http://localhost:5173
```

### 3. (Optional) Real vision

```bash
cd vision
pip install -r requirements.txt
python mock_vision_state.py                    # prints all mock scenarios
```

### Or with Docker

```bash
docker compose up
```

### Verify the backend

```bash
cd backend && .venv/bin/python smoke_test.py   # runs the full WO-1001 flow
```

## Demo flow (4 moments)

1. **Station readiness passes** — post `station_ready`; readiness goes green.
2. **Correct step passes** — `red → assembly`, Verify, `can_advance=true`, Next unlocks.
3. **Wrong sequence is blocked** — `blue first`, Verify → red banner, Next stays locked, failure logged.
4. **Final 6S blocks close** — `6S: tool missing` blocks; return the tool (`6S: all home`) → **Work Order Closed**.

Full run-of-show in [DEMO_SCRIPT.md](DEMO_SCRIPT.md).

## Sponsor tracks targeted

| Track | How |
|---|---|
| **Best Physical AI Hack** (primary) | Locked camera + real workstation + visual MPI gating |
| **Best Use of Fetch AI** | MES Supervisor Agent operates the gated API |
| **Best Use of Anthropic** | Built with Claude Code; Claude explains audit logs |
| **Best Use of Sentry** | Live backend/frontend/vision error monitoring |
| **Best Use of Deepgram** | Optional hands-free operator voice commands |
| **Best Use of Redis** | Optional real-time station memory + audit stream |
| **Best Use of Arize / Terac** | Optional vision evaluation + labeling loop |

Details: [SPONSOR_INTEGRATIONS.md](SPONSOR_INTEGRATIONS.md).

## Team roles

| Person | Role |
|---|---|
| 1 | Backend / MES Lead |
| 2 | Vision / Data Lead |
| 3 | Frontend / UI Lead |
| 4 | Sponsor / Agents / DevOps Lead |

Details: [TEAM_ROLES.md](TEAM_ROLES.md).

## Safety / compliance

- **No prior project code was reused.** All code in this repo is original and
  written fresh for UC Berkeley AI Hackathon 2026.
- This is a **fake/mock MES** for demonstration — not a production system and not
  to be represented as production-grade.
- No real PII or customer data; dummy work orders only.
- The audit log is demo evidence, not a certified compliance record.
- API keys live in `.env` (see `.env.example`) and are never committed.
- The camera supervises blocks and tools only — no people/biometric tracking.

## License

MIT (see hackathon submission).
