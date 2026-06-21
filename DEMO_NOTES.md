# Demo Notes — Safety Glasses (PPE) Verification

Operational runbook for the PPE / Safety-Glasses gate. This is the part that
froze during the demo; it is now timeout-bounded, debuggable, and has a
guaranteed-working mock mode.

## TL;DR for a safe demo

```bash
# Use mock PPE so the demo never depends on the external API (default in .env now)
#   PPE_MOCK_MODE=true   ->  Verify passes in ~1s, mode "mock", clearly labeled
```

If PPE ever "stays on Verifying…", it now self-recovers: the backend caps the
provider call at `PPE_PROVIDER_TIMEOUT` (12s) and the frontend aborts at 10s and
shows a Retry button. It can no longer hang forever.

---

## 1. Start the backend

```bash
cd /home/ivancito/VisionMPI/backend
../.venv/bin/uvicorn app.main:app --reload --port 8000   # http://localhost:8000/docs
```

## 2. Start the frontend

```bash
cd /home/ivancito/VisionMPI/frontend
npm run dev                                               # http://localhost:5173
```

## 3. Start the vision bridge (optional — block detection, NOT PPE)

The vision bridge is for the LEGO block sequence, not safety glasses. The PPE
modal uses the **browser** camera; the bridge uses **OpenCV**. Run them on
*different* camera indexes so they don't fight over a device.

```bash
cd /home/ivancito/VisionMPI/vision
../.venv/bin/python run_vision.py --show --serve-ui --post http://localhost:8000 \
  --wo WO-1001 --camera-index 2 --auto-post-interval 1
```

> **Camera rule:** the browser PPE modal grabs the *default* webcam (usually
> index 0 / `/dev/video0`). So run the vision bridge on **index 2**. If the
> bridge holds the same device the browser wants, the PPE camera shows
> "Camera is busy — likely held by the vision bridge" and offers Retry.

## 4. Test the PPE modal

1. Open http://localhost:5173.
2. Click **Start Work Order** on WO-1001 → the Safety Glasses modal opens.
3. The status pill walks through: `Camera starting…` → `Camera ready`.
4. Put glasses on, click **Verify Safety Glasses** → `Verifying…` → `Verified`
   (mock) or a real verdict (Roboflow).
5. **Open Work Order** unlocks once verified. **Cancel** closes cleanly and
   stops the camera. On any failure/timeout a **Retry** button appears.

Backend (curl) smoke test — should return `ok:true`, `verified:true` in ~1s:

```bash
python3 -c "open('/tmp/ppe.jpg','wb').write(bytes.fromhex('ffd8ffe000104a46494600010100000100010000ffd9'))"
curl -s -w "\nHTTP %{http_code} in %{time_total}s\n" -X POST \
  http://localhost:8000/api/ppe/check \
  -F image=@/tmp/ppe.jpg -F work_order_id=WO-1001 -F worker_id=operator-1
curl -s http://localhost:8000/api/ppe/config   # provider / mock_mode / model_configured
```

## 5. Run PPE mock mode

Mock mode simulates verification locally — no Roboflow call, passes in ~1s,
returns `reason:"Mock PPE verification passed"`, `mode:"mock"`. It is always
labeled in logs (`[PPE][MOCK] ... NOT a real model call`) and in the UI banner;
it never pretends the external API ran.

```bash
# In repo-root .env:
PPE_MOCK_MODE=true        # then restart the backend

# To make mock FAIL instead (test the failure path):
PPE_MOCK_RESULT=fail
```

### Run with REAL PPE verification (Roboflow workflow)

```bash
# In .env:
PPE_MOCK_MODE=false
ROBOFLOW_API_KEY=...                       # required
ROBOFLOW_WORKSPACE=joses-workspace-zokda
ROBOFLOW_WORKFLOW_ID=find-object-and-safety-glasses
# (PPE_MODEL_PROVIDER blank => auto-resolves to "roboflow_workflow")
```
Then restart the backend. `GET /api/ppe/config` should show `"provider":
"roboflow_workflow"`, `"mock_mode": false`. Note: a cold Roboflow serverless
endpoint can take several seconds on the first call; the 12s backend timeout
keeps that from hanging the UI.

## 6. Confirm the camera is not locked

```bash
ls -l /dev/video*                 # which devices exist
fuser /dev/video0 /dev/video2     # PIDs holding each camera (empty = free)
lsof /dev/video0                  # what process has it open
sudo fuser -v /dev/video0         # verbose: user + command holding it
```

If a process holds the camera the browser needs, the modal reports it instead of
freezing.

## 7. Recover if the camera freezes

```bash
# Kill the OpenCV vision bridge (most common camera holder)
pkill -f run_vision.py
pkill -f roboflow_workflow_stream.py
fuser /dev/video0 /dev/video2     # confirm both are free now
```

In the browser: click **Cancel** (aborts the request + releases the camera),
then **Start** again to reopen the modal with a fresh camera. Reloading the tab
(F5) also fully releases the browser's camera tracks.

---

## Camera assignment cheat-sheet

| Situation | Do this |
|---|---|
| Browser PPE uses camera 0 (default) | Run vision bridge on `--camera-index 2` |
| Vision bridge must use camera 0 | Stop it before PPE, or give the browser a 2nd camera |
| "Camera is busy" in the modal | A process holds the device → `pkill -f run_vision.py` |
| No external API / unreliable network | `PPE_MOCK_MODE=true` |

## What changed (freeze fix)

- **Root cause:** the Roboflow *workflow* call (`call_roboflow_workflow`) had no
  timeout, and the frontend `fetch` had no timeout/abort — so a slow or
  unreachable model left "Verifying…" stuck forever.
- **Backend:** `/api/ppe/check` now runs the provider in a worker thread bounded
  by `PPE_PROVIDER_TIMEOUT` and always returns a structured body
  (`ok / verified / reason / confidence`). `PPE_MOCK_MODE` added. Debug logging
  on the `ppe` logger.
- **Frontend:** `PPECheckModal` is a state machine
  (`starting_camera → camera_ready → capturing → verifying → verified|failed`,
  plus `camera_error`) with an `AbortController`, a 10s client timeout, live
  preview (`play()` + `onloadedmetadata`), clean track teardown on close, and
  **Retry** / working **Cancel**.

## Is PPE still required to open a work order?

Server-side enforcement is **off by default** (`PPE_REQUIRED=false`), so the
LEGO block sequence (the main flow) is never blocked by PPE. The modal is a
front-of-demo gate. Set `PPE_REQUIRED=true` to make the backend `/start` route
refuse until a verification session passes PPE **and** the block sequence.
