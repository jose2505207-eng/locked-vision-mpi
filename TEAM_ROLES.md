# Team Roles — Locked Vision MPI (4 members)

One rule binds all roles: **MES is truth · vision is evidence · the state
machine validates · the frontend never bypasses the backend.**

---

## Person 1 — Backend / MES Lead
**Owns:** `backend/`

- Fake MES, work orders, MPI step JSON, zones.
- State machine, validation engine, audit log, backend API.

**Files:** `backend/app/{main,fake_mes_service,mpi_state_machine,validation_engine,audit_logger,models}.py`,
`backend/app/data/*.json(l)`.

**Expected outcome:** the backend runs the full work order flow using **mocked
vision first**, then real vision state — without ever returning
`can_advance=true` unless validation passes, and without closing a work order
until final 6S passes.

**Skill:** `/backend-mes`

---

## Person 2 — Vision / Data Lead
**Owns:** `vision/`

- Camera input, golden view, zones, OpenCV color detection.
- Zone mapping, ArUco / camera-alignment placeholder, snapshots, dataset capture.

**Files:** `vision/{camera,color_detector,zone_mapper,calibration,mock_vision_state}.py`,
`vision/snapshots/`.

**Expected outcome:** the vision service returns objects + zones for
`red_block, blue_block, yellow_block, green_block, tool_1, tool_2` (and
`finished_assembly`), in the **same shape** as the mock — so it drops into the
backend with no changes. Vision reports; it never decides flow.

**Skill:** `/vision-camera`

---

## Person 3 — Frontend / UI Lead
**Owns:** `frontend/`

- Fake MES dashboard, MPI step screen, live camera / snapshot panel.
- Detected objects panel, disabled/enabled Next Step button, error banner,
  final 6S screen, audit log UI.

**Files:** `frontend/src/App.jsx`, `frontend/src/api.js`,
`frontend/src/components/*.jsx`.

**Expected outcome:** judges understand the workflow in **10 seconds**; the UI
is readable from 6 feet; the Next button is impossible to use unless
`can_advance=true`; errors are loud.

**Skill:** `/frontend-ui`

---

## Person 4 — Sponsor / Agents / DevOps Lead
**Owns:** `integrations/`, deployment, and the docs.

- Sponsor integrations; Fetch AI Agentverse / ASI:One agent scaffold.
- Redis / Sentry / Deepgram placeholders; deployment; README; demo script;
  Devpost readiness.

**Files:** `integrations/**`, `docker-compose.yml`, `README.md`,
`SPONSOR_INTEGRATIONS.md`, `DEMO_SCRIPT.md`.

**Expected outcome:** the repo is public-ready and clearly explains which prize
tracks we target and how each integration supports the project — without any
sponsor feature becoming a dependency of the core demo.

**Skills:** `/sponsor-integrations`, `/demo-readiness`, `/github-handoff`

---

## Shared definition of done

- Backend never returns `can_advance=true` unless validation passes.
- Frontend Next button cannot be used unless `can_advance=true`.
- Wrong / out-of-order actions are blocked **and logged**.
- Work order cannot close until final 6S passes.
- App runs from a clean clone with documented commands.
- Demo runs start to finish with no manual hacks.
- Sponsor integrations can be removed without breaking the core demo.
