# Locked Vision MPI

### Vision-verified manufacturing process instructions — the first step toward autonomous manufacturing.

A fixed camera observes a workstation. The backend validates whether the physical
world matches the required manufacturing step. The operator can only continue when
the real-world evidence is correct. Every check — pass or fail — becomes a
permanent, evidence-backed record.

> **The core idea:** MES is the source of truth. Vision is the evidence. The state
> machine is the judge. The frontend obeys the backend.

`FastAPI · OpenCV · React/Vite · Roboflow` — runs end-to-end on mocked vision with
**no camera required**, and drops straight onto a real camera with no backend changes.

---

## Table of contents

- [What it is](#what-it-is)
- [Why it matters](#why-it-matters)
- [The core idea](#the-core-idea)
- [How it works](#how-it-works)
- [Physical AI training loop](#physical-ai-training-loop)
- [The road to autonomous manufacturing](#the-road-to-autonomous-manufacturing)
- [Relevance to FDA-regulated environments](#relevance-to-fda-regulated-environments)
- [Architecture](#architecture)
- [Repo structure](#repo-structure)
- [Setup](#setup)
- [Safety-Glasses PPE gate (optional)](#safety-glasses-ppe-gate-optional)
- [Demo flow](#demo-flow)
- [Safety and limitations](#safety-and-limitations)

---

## What it is

Locked Vision MPI is a prototype that fuses a **digital Manufacturing Process
Instruction (MPI)** with the **physical reality** of a workstation. A locked
overhead camera watches a station of colored blocks (standing in for parts) and
simple tools. A fake Manufacturing Execution System (MES) holds the work order and
the ordered MPI steps. A validation engine compares what the camera actually sees
against the step the MES expects, and decides — in exactly one place — whether the
operator is allowed to advance.

This is **not just a camera demo**. It is a bridge between physical manufacturing
work and digital manufacturing execution. The dashboard cannot move to the next
step, and cannot close the work order, until the physical evidence satisfies the
instruction. Every check — pass or fail — is written to an audit log as objective
evidence of what actually happened at the station, when, and why.

Because the system already captures snapshots, detections, timestamps, and
pass/fail outcomes, it is also a **foundation for a future Physical AI training
dataset** — a structured record of real assembly steps, deviations, and corrections
that machine-learning models could one day learn from.

## Why it matters

In most MPI/MES workflows, step compliance is **trust-based**: the operator clicks
"Next" and the system believes them. There is no objective check that the right
part went to the right place in the right order, or that the station was reset
before the next job. The physical state is simply *assumed* to match the digital
record.

That assumption is where defects, recalls, and audit findings come from — skipped
or out-of-order steps, the wrong part installed, a tool left in the assembly, a
station never cleaned up. And when something does go wrong, the records only prove
that a **button was pressed**, not that the **work was done correctly**.

Locked Vision MPI closes that gap. It requires **visual evidence before a step can
advance**, and it captures that evidence as a permanent record. The digital
instruction and the physical reality are *locked together*.

## The core idea

> **MES is the source of truth. Vision is the evidence. The state machine is the
> judge. The frontend obeys the backend.**

- The **MES** owns the work order and the ordered MPI steps.
- **Vision** only reports what it sees — it never decides flow.
- The **state machine + validation engine** compare expected vs. observed and set `can_advance`.
- The **frontend** can do nothing but obey that decision.

This separation is the whole point: the part of the system that *sees* is never the
part that *decides*, and the part the operator *touches* can never override the
truth.

## How it works

```
Fake MES (truth) ─► MPI step data ─► State machine ─► Validation ─► can_advance?
                                          ▲                              │
                                          │ evidence                     ▼
                                    Vision system  ───────────────►  Audit log
                                  (mock OR OpenCV)                       │
                                                                        ▼
                                                  Frontend (obeys can_advance only)
```

- A **fixed camera** watches the workstation from a locked, calibrated "golden view."
- **Vision** (OpenCV color detection) detects blocks/tools and maps them to **zones**.
- A **fake MES** stores the work order and its ordered MPI steps (the source of truth).
- A **validation engine** compares the expected step against the observed state.
- The **backend** returns `can_advance: true/false` — and **re-validates on every advance**, so even a direct API call cannot skip a step.
- The **frontend** keeps the operator locked until the physical step is correct.
- An **audit log** records every pass/fail with the supporting evidence.
- A **final 6S gate** blocks closing the work order until tools are home, parts are home, and the assembly zone is clear.

The vision contract is identical whether evidence comes from a real camera or the
mock simulator, so the system runs end-to-end with no camera attached.

## Physical AI training loop

Every validation already produces structured artifacts: camera snapshots, detected
objects with zones and confidence, timestamps, the expected vs. observed step, and
the pass/fail outcome — all appended to an audit trail.

Captured over time, that stream becomes **labeled manufacturing data**. Each event
is a small, grounded example:

> *"This is what step N looks like when it is done correctly."*
> *"This is what an out-of-sequence error looks like, and this is the rework that fixed it."*

That is exactly the kind of dataset Physical AI models need — and it is generated as
a *byproduct of normal operation*, not a separate labeling project.

With enough captured examples, future models could learn to understand **station
state, assembly progress, tool usage, material flow, mistakes, and rework
patterns** — and to verify a process **independently of which operator is running
it**. The goal is operator-independent process verification grounded in real,
labeled evidence rather than self-reported clicks.

> This is a **future direction**, not a shipped capability — but the data foundation
> is being laid by the prototype today.

## The road to autonomous manufacturing

Autonomy in manufacturing is not a single leap. It is a ladder, and every rung
depends on the one below it. You cannot automate a process you cannot verify, and
you cannot verify a process you cannot observe. Locked Vision MPI is built to climb
that ladder:

| # | Rung | What it means | Status |
|---|------|---------------|--------|
| 1 | **Observe** | A locked, calibrated camera sees the real workstation. | ✅ Prototype |
| 2 | **Verify** | Each step is validated against the required MPI before it can advance. | ✅ Prototype |
| 3 | **Build traceable datasets** | Snapshots, detections, and pass/fail events accumulate as labeled evidence. | ✅ Foundation |
| 4 | **Learn process patterns** | Models learn normal sequences, common deviations, and rework. | 🔭 Future |
| 5 | **Recommend corrections** | The system guides the operator in real time when reality drifts. | 🔭 Future |
| 6 | **Assist** | Pre-filled checks, predictive prompts, and guided recovery. | 🔭 Future |
| 7 | **Automate** | Autonomous or semi-autonomous manufacturing cells. | 🔭 Future |

This prototype delivers rungs **1–3** and is deliberately architected to feed the
rest. **First observe, then verify, then recommend, then assist, then automate.**

The key insight: the same evidence that *gates a step today* is the evidence that
*trains the model tomorrow*. Verification and autonomy are not separate
programs — verification is how autonomy earns its training data.

## Relevance to FDA-regulated environments

In FDA-regulated and medical-device manufacturing, the product is only half the
deliverable — the **evidence that it was built correctly** is the other half.
Traceability, step compliance, station readiness, auditability, and error
prevention are not nice-to-haves; they are the difference between a releasable lot
and a recall.

The concepts this prototype explores map directly onto those needs:

- **Step-by-step compliance** — a step cannot advance until evidence confirms it,
  echoing controlled MPI / work-instruction execution.
- **Objective evidence over click-only records** — the audit trail is grounded in
  what the camera *saw*, not only what the operator *claimed*. This is the spirit of
  data-integrity expectations (often summarized as **ALCOA+**: attributable,
  legible, contemporaneous, original, accurate — and complete, consistent,
  enduring, available).
- **Traceable audit history** — every pass and failure is logged with its evidence
  and timestamp, the conceptual seed of an electronic record / device history
  record.
- **Station readiness and final reset verification** — a work order cannot close
  until the final **6S** reset passes (tools home, parts home, assembly clear),
  reducing cross-contamination and mix-up risk between jobs.
- **Error prevention** — skipped steps, wrong parts, wrong sequence, and incomplete
  cleanup are caught *at the station*, before they propagate downstream.
- A **foundation for stronger electronic manufacturing records** that link a digital
  step to physical proof.

> **Disclaimer — read this carefully.** This repository is a **prototype**. It is
> **not** a validated quality system, **not** certified medical-device software, and
> **not** an FDA-compliant production MES. It is **designed around regulated-
> manufacturing concepts** (such as 21 CFR Part 11 electronic-records thinking,
> ALCOA+ data integrity, and MES traceability) as inspiration and direction — it is
> **not** FDA-certified, validated, or production-ready. Any real regulated use would
> require formal validation (IQ/OQ/PQ), security review, quality-system integration,
> and the appropriate regulatory controls.

## Architecture

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

Core rule: **MES is truth · vision is evidence · the state machine validates · the
frontend never bypasses the backend.** Full detail in [ARCHITECTURE.md](ARCHITECTURE.md).

## Repo structure

```
locked-vision-mpi/
├── backend/      FastAPI fake MES, state machine, validation, audit log, PPE gate
├── vision/       Camera, OpenCV color detection, zone mapping, mock vision
├── frontend/     Vite + React fake MES dashboard (gated Next button)
├── docs/         backend · frontend · setup · testing guides
├── ARCHITECTURE.md · DEMO_SCRIPT.md · MAIN.md
```

## Setup

The whole system runs on **mocked vision**, so no camera is needed to run it.

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
*Camera Bridge Mode*. The browser never opens the webcam — the real camera is read
by `vision/run_vision.py` (Python/OpenCV), which posts evidence to the backend. The
dashboard polls the backend and shows it as **source: camera**.

```bash
# Terminal 1 — backend
cd backend && source .venv/bin/activate
uvicorn app.main:app --reload --port 8000

# Terminal 2 — frontend
cd frontend && npm run dev

# Terminal 3 — camera bridge (real webcam, serves the feed to the UI + auto-posts)
cd vision
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
own the **Tool 1** step and **Finished → complete** (the camera can't see those). A
camera post never erases tool state, and the tool simulator never erases the
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
**Verify Safety Glasses** → backend runs the model + decides → on success the **Open
Work Order** button unlocks (with confidence % + timestamp). Without a model key the
modal runs in a clearly-labeled **demo mode** (verification skipped, never faked).
Every check is written to the audit log and a `ppe_checks` SQLite table. See
[docs/ROBOFLOW_WORKFLOW_INTEGRATION.md](docs/ROBOFLOW_WORKFLOW_INTEGRATION.md).

Endpoints: `GET /api/ppe/config` · `POST /api/ppe/check` (image + work_order_id +
worker_id) · `POST /api/work-orders/{id}/unlock` (403 until verified).

## Demo flow

A manufacturing validation scenario in four moments:

1. **Station readiness passes** — post `station_ready`; readiness goes green.
2. **Correct step passes** — `red → assembly`, Verify, `can_advance=true`, Next unlocks.
3. **Wrong sequence is blocked** — `blue first`, Verify → red banner, Next stays locked, failure logged.
4. **Final 6S blocks close** — `6S: tool missing` blocks; return the tool (`6S: all home`) → **Work Order Closed**.

Full run-of-show in [DEMO_SCRIPT.md](DEMO_SCRIPT.md).

## Safety and limitations

- **Prototype only.** Not production-ready without validation, security review,
  quality-process integration, and regulatory controls.
- **Fake/mock MES.** Not connected to any real production system; do not represent
  it as production-grade.
- **Dummy work orders only.** No real PII or customer data.
- The **camera is intended for workstation objects**, not biometric or people
  tracking.
- The **audit log is prototype evidence**, not a certified compliance record.
- API keys live in `.env` (see `.env.example`) and are never committed.

## License

MIT.
