# Locked Vision MPI — Project Control Document

> This is the central operating document for the repo. Read this first. Every contributor and every Claude Code session should align with this file before writing code.

---

## 1. Project Name

**Locked Vision MPI** — a fake MES-connected physical AI workstation.

## 2. One-Line Pitch

> This is not a camera watching a table. This is **visual proof connected to manufacturing execution**. The MPI only moves forward when the real world is correct.

## 3. Problem Statement

In real manufacturing, operators follow a Manufacturing Process Instruction (MPI) step by step. Today, compliance is mostly trust-based: the operator clicks "Next" and the MES believes them. There is no physical verification that the right part went to the right place in the right order, and no guarantee the station is reset (6S) before the work order closes.

This causes:
- Skipped or out-of-order steps
- Wrong parts/tools used without detection
- Stations left un-reset, breaking the next job
- Audit logs that record clicks, not reality

## 4. Product Vision

A locked overhead camera supervises a workstation containing colored LEGO blocks (parts) and simple tools. The system enforces the MPI:

- The operator **cannot advance** to the next step unless vision confirms the correct part/tool moved to the correct zone in the correct order.
- The work order **cannot close** until all tools/parts are returned to their home zones for a final **6S reset**.
- Every pass and every failure is **logged** as evidence.

The result is a workstation where the digital instruction and the physical reality are locked together.

## 5. Non-Negotiable Architecture Rules

These are absolute. Do not violate them, and do not let sponsor features erode them.

1. **The fake MES is the source of truth.** Work orders, MPI steps, and zones come from MES data.
2. **The vision system provides evidence only.** It reports what it sees; it does not decide flow.
3. **The state machine validates the MPI sequence.** It compares vision evidence against the expected step and decides `can_advance`.
4. **The frontend must NEVER allow manual advancement unless the backend returns `can_advance=true`.** No client-side override, ever.
5. **No work order closes until final 6S passes** (all parts/tools home).
6. **Every pass and every failure is logged** to the audit log.
7. **Sponsor integrations must never break the core demo.** They are additive and isolated.

Data flow:

```
Fake MES (truth) ──► MPI Step Data ──► State Machine ──► can_advance?
                                            ▲
                                            │ evidence
                                      Vision System
                                            │
                                            ▼
                                       Audit Log
                                            │
                                            ▼
                                        Frontend (obeys can_advance)
```

## 6. Team Roles (4 People)

### Person 1 — Backend / MES Lead
- Fake MES, work orders, MPI step data
- State machine, validation engine, audit log, backend API
- **Outcome:** backend runs the full work order flow with mocked vision data first, then real vision state later.
- **Skill:** `/backend-mes`

### Person 2 — Vision / Data Lead
- Camera setup, golden view, OpenCV color detection
- Zone mapping, camera lock/calibration placeholder, snapshot capture, dataset structure
- **Outcome:** vision module detects colored LEGO blocks, maps objects to zones, and returns structured vision state to the backend.
- **Skill:** `/vision-camera`

### Person 3 — Frontend / UI Lead
- Fake MES dashboard, work order queue, MPI step screen
- Disabled/enabled Next Step button, live camera/snapshot panel, detected objects panel, error banner, audit log UI, final 6S screen
- **Outcome:** the UI makes the workflow obvious in 10 seconds and never allows advancement unless `can_advance=true`.
- **Skill:** `/frontend-ui`

### Person 4 — Sponsor / Agents / DevOps Lead
- Sponsor integration plan, Fetch AI supervisor agent scaffold
- Sentry monitoring, Redis memory placeholder, Deepgram voice placeholder
- Deployment plan, README, Devpost readiness, demo script
- **Outcome:** the repo is public-ready, sponsor-aware, easy to run, and demo-ready.
- **Skill:** `/sponsor-integrations`, `/demo-readiness`, `/github-handoff`

## 7. Folder Structure

```
LockedVisionMPI/
├── MAIN.md                          # this file — the project brain
├── README.md                        # public-facing run instructions
├── ARCHITECTURE.md                  # technical architecture
├── TEAM_ROLES.md                    # who owns what
├── DEMO_SCRIPT.md                   # the exact demo run-of-show
├── SPONSOR_INTEGRATIONS.md          # sponsor mapping & isolation
│
├── backend/
│   └── app/
│       ├── main.py                  # FastAPI entrypoint
│       ├── fake_mes_service.py      # source-of-truth MES
│       ├── mpi_state_machine.py     # MPI sequence + can_advance
│       ├── validation_engine.py     # evidence vs expected
│       ├── audit_logger.py          # append-only audit log
│       ├── models.py                # pydantic models
│       └── data/
│           ├── work_orders.json
│           ├── mpi_steps.json
│           ├── zones.json
│           └── audit_log.jsonl
│
├── vision/
│   ├── camera.py                    # fixed camera capture
│   ├── color_detector.py            # OpenCV LEGO color detection
│   ├── zone_mapper.py               # object → zone mapping
│   ├── calibration.py               # camera lock / calibration placeholder
│   ├── mock_vision_state.py         # mocked vision for backend dev
│   └── snapshots/                   # captured evidence images
│
├── frontend/
│   └── src/
│       ├── App.jsx
│       ├── api.js
│       └── components/
│           ├── WorkOrderQueue.jsx
│           ├── StationReadinessPanel.jsx
│           ├── MPIStepPanel.jsx
│           ├── LiveCameraPanel.jsx
│           ├── DetectedObjectsPanel.jsx
│           ├── ErrorBanner.jsx
│           ├── AuditLogPanel.jsx
│           └── Final6SCheckPanel.jsx
│
├── integrations/
│   ├── fetch_agent/                 # Fetch AI supervisor agent scaffold
│   ├── sentry/                      # error monitoring
│   ├── redis/                       # memory placeholder
│   ├── deepgram/                    # voice placeholder
│   └── arize/                       # optional observability
│
└── .claude/
    └── skills/
        ├── project-orchestrator/SKILL.md
        ├── backend-mes/SKILL.md
        ├── vision-camera/SKILL.md
        ├── frontend-ui/SKILL.md
        ├── sponsor-integrations/SKILL.md
        ├── demo-readiness/SKILL.md
        ├── code-review/SKILL.md
        └── github-handoff/SKILL.md
```

## 8. MVP Scope

**In scope (must work for the demo):**
- Fake MES with at least one work order and a multi-step MPI.
- Backend state machine returning `can_advance` per step.
- Validation engine comparing vision evidence to the expected step.
- Mock vision state so the backend works without a camera.
- Real OpenCV color detection mapping LEGO blocks to zones.
- Frontend dashboard: work order queue, MPI step, gated Next button, detected objects, error banner, audit log, final 6S screen.
- Final 6S gate blocking work order closure until tools/parts are home.
- Audit log recording every pass/fail.

**Out of scope (do not build for MVP):**
- Real MES integration, auth, multi-user, databases.
- ML model training, object classification beyond color.
- Mobile, multi-station, scaling, fancy auth.
- Any sponsor feature that doesn't reinforce the MPI story.

## 9. Demo Flow

1. **Station readiness passes** — show the station is calibrated and zones are clear; readiness goes green.
2. **Correct step passes** — operator moves the correct LEGO block to the correct zone; vision confirms; `can_advance=true`; Next enables.
3. **Wrong sequence is blocked** — operator does the wrong thing or out of order; vision evidence mismatches; Next stays disabled; error banner fires; failure logged.
4. **Final 6S blocks close** — work order won't close until the tool/part is returned home; return it; 6S passes; work order closes.

Narration anchor: *"The MPI only moves forward when the real world is correct."*

## 10. Sponsor Prize Strategy

- **Primary:** Best Physical AI Hack — the locked camera + MES + state machine is the whole story.
- **Strong fits:** Fetch AI (supervisor agent), Anthropic / Claude Code (built with this skill system), Sentry (live error monitoring), Deepgram (voice operator prompts), Redis (station memory).
- **Optional:** Arize or Terac (observability) if time allows.

Rule: **every sponsor integration must support the manufacturing/MPI story.** No random sponsor feature is allowed to distract from the core physical AI demo.

## 11. Build Order

1. **Backend skeleton + data files** — MES data, models, FastAPI up.
2. **Mock vision state** — so backend can run end-to-end without a camera.
3. **State machine + validation engine** — `can_advance` logic against mock data.
4. **Audit logger** — every pass/fail recorded.
5. **Frontend wired to backend** — gated Next button proven against mock vision.
6. **Real vision (OpenCV)** — color detection + zone mapping replaces mock.
7. **Final 6S gate** — closure blocked until home.
8. **Sponsor integrations** — isolated, additive.
9. **Demo readiness** — README, demo script, dry run.

## 12. Definition of Done

- Backend never returns `can_advance=true` unless validation passes.
- Frontend Next button is impossible to use unless `can_advance=true`.
- Out-of-order / wrong-part actions are blocked and logged.
- Work order cannot close until final 6S passes.
- Every pass and failure appears in the audit log.
- App runs from a clean clone with documented commands.
- Demo flow runs start to finish without manual hacks.
- Sponsor integrations can be removed without breaking the core demo.

## 13. Safety / Compliance Notes

- This is a **fake/mock MES** for demonstration. It is not connected to any real production system and must not be represented as production-grade.
- No real PII, credentials, or customer data. Use dummy work orders only.
- The audit log is demo evidence, not a certified compliance record.
- Sponsor API keys must be stored in environment variables / `.env`, never committed.
- The camera supervises blocks and tools only — no people-tracking, no biometric capture.

## 14. Claude Code Usage Instructions

- **Start every session by reading this file (MAIN.md).**
- Pick the skill that matches your task and invoke it (see section 15). Skills enforce the rules so you don't have to remember them.
- For planning or cross-cutting decisions, use `/project-orchestrator` first.
- Stay inside your role's files. Respect each skill's "Files this skill should not touch."
- Before any commit or demo, run `/code-review`.
- Never bypass the architecture rules in section 5, even if a shortcut is faster.

## 15. Available Project Skills

| Skill | Slash command | Use when... |
|---|---|---|
| project-orchestrator | `/project-orchestrator` | Planning or coordinating the whole repo; preventing scope creep; checking alignment with MVP and the core rules. |
| backend-mes | `/backend-mes` | Building/editing FastAPI, fake MES, MPI logic, state machine, validation, audit logs, work order state. |
| vision-camera | `/vision-camera` | Building/editing camera, OpenCV detection, zone mapping, calibration, snapshots, dataset capture. |
| frontend-ui | `/frontend-ui` | Building/editing the fake MES dashboard and all UI components. |
| sponsor-integrations | `/sponsor-integrations` | Adding sponsor features (Fetch, Sentry, Redis, Deepgram, Arize) without corrupting the main product. |
| demo-readiness | `/demo-readiness` | Preparing the demo, pitch, README, architecture doc, or final submission. |
| code-review | `/code-review` | Before commits and before the demo — checking rules, demo path, and demo-killing bugs. |
| github-handoff | `/github-handoff` | Preparing commits, repo structure, handoff docs, and teammate instructions. |

**Recommended first command:** `/project-orchestrator`
