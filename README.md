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

### Real camera workflow (3 terminals)

The dashboard has **two vision modes**: *Demo Mode* (mock simulator buttons) and
*Camera Bridge Mode*. The browser never opens the webcam — the real camera is
read by `vision/run_vision.py` (Python/OpenCV), which posts evidence to the
backend. The dashboard polls the backend and shows it as **source: camera**.

```bash
# Terminal 1 — backend
cd /home/ivancito/VisionMPI/backend
source ../.venv/bin/activate
uvicorn app.main:app --reload --port 8000

# Terminal 2 — frontend
cd /home/ivancito/VisionMPI/frontend
npm run dev

# Terminal 3 — camera bridge (real webcam, serves the feed to the UI + auto-posts)
cd /home/ivancito/VisionMPI/vision
../.venv/bin/python run_vision.py --show --serve-ui --post http://localhost:8000 --wo WO-1001 --camera-index 0 --auto-post-interval 1
```

`--serve-ui` streams the **annotated camera feed** to the dashboard (the browser
never opens the webcam — Python/OpenCV does, on `http://localhost:8010`).
`--auto-post-interval 1` posts camera evidence to the backend every second.

**Align zones to your real table first** (so the rectangles match the taped
station): `../.venv/bin/python zone_calibrator.py --camera-index 0` — draw each
zone with the mouse, `n` to accept, `s` to save, then restart the bridge. See
[vision/README.md](vision/README.md#calibrate-the-zones-to-your-real-table-zone_calibratorpy).

Open **http://localhost:5173**, then run the **Step 1 camera test**:

1. Start **WO-1001** in the dashboard (Station Readiness shows which blocks are home).
2. The dashboard shows the **live annotated feed** and **source: camera**.
3. Move a **red** object into the `assembly_zone` rectangle (auto-posts, or press **`p`**).
4. Detected objects update to `red_block @ assembly_zone`.
5. Click **Verify Step** → Step 1 passes → **Next Step** unlocks.

**Hybrid evidence:** the camera owns the colored blocks; the **simulator buttons**
own the **Tool 1** step and **Finished → complete** (the camera can't see those).
A camera post never erases tool state, and the tool simulator never erases the
camera's block state.

| Bridge endpoint (`:8010`) | Returns |
|---|---|
| `GET /health` | `{status, camera_index, camera_locked}` |
| `GET /latest-state` | latest `{source, camera_locked, objects, updated_at}` |
| `GET /latest-frame.jpg` | latest annotated JPEG |
| `GET /video.mjpg` | MJPEG stream |

**Notes / troubleshooting**

- No live video in the browser panel is **expected** — Python/OpenCV owns the camera.
- No OpenCV window? Run `../.venv/bin/python test_camera.py` (try `--camera-index 1`/`2`).
- Nothing detected? Use brighter colored paper / better lighting.
- Wrong zone? Move the object fully inside the visible zone rectangle.
- Dashboard not updating? Confirm the backend is on `localhost:8000` and press `p` again.
- Mock mode always works as a fallback — use the simulator buttons (no camera needed).

### Or with Docker

```bash
docker compose up
```

### Verify the backend

```bash
cd backend && .venv/bin/python smoke_test.py   # runs the full WO-1001 flow
```

## Safety-Glasses PPE gate (optional)

Before a work order opens, the operator can be required to verify they're wearing
safety glasses. A browser snapshot is sent to a hosted PPE model (Roboflow), but
**the backend decides** — the model is only evidence.

```bash
# .env (see .env.example)
ROBOFLOW_API_KEY=...                 # required to call the real model
ROBOFLOW_PPE_MODEL_ID=ppe-detection/3
PPE_MIN_CONFIDENCE=0.72              # backend threshold
PPE_CHECK_EXPIRATION_SECONDS=20     # a check is only valid this long
PPE_REQUIRED=false                  # true = block work-order start until verified
```

Flow: click **Start** → the **Safety Glasses** modal opens → camera preview →
**Verify Safety Glasses** → backend runs the model + decides → on success the
**Open Work Order** button unlocks (with confidence % + timestamp). Without a
model key the modal runs in a clearly-labeled **demo mode** (verification skipped,
never faked). Every check is written to the audit log and a `ppe_checks` SQLite
table.

Endpoints: `GET /api/ppe/config` · `POST /api/ppe/check` (image + work_order_id +
worker_id) · `POST /api/work-orders/{id}/unlock` (403 until verified).

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
