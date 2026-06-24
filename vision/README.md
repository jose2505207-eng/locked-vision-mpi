# Vision — Evidence, not Truth

The vision module turns a **fixed overhead camera** + **golden view** into
structured evidence the backend can validate. It reports what it sees; it never
decides flow.

## Build order (mock first)

1. `mock_vision_state.py` — canned scenarios so backend + frontend work with no
   camera. **Start here.** Its output shape is the contract.
2. `zone_mapper.py` — maps bounding-box centers to zones (reads the backend's
   `zones.json`, the single source of zone truth).
3. `color_detector.py` — OpenCV HSV detection for red/blue/yellow/green blocks.
4. `calibration.py` — ArUco camera-lock check ("camera moved" -> not ready).
5. `camera.py` — fixed-camera capture + snapshot evidence + end-to-end glue.

## Output contract (identical for mock and real)

```json
{
  "objects": [
    { "object": "red_block", "zone": "assembly_zone", "bbox": [x1,y1,x2,y2], "confidence": 0.98 }
  ],
  "source": "mock",
  "scenario": "step1_done"
}
```

`zone: null` means "detected, but not in any zone" (e.g. a tool in hand).

Detected object names must match `mpi_steps.json`:
`red_block, blue_block, yellow_block, green_block, tool_1, tool_2, finished_assembly`.

## Run

```bash
cd vision
pip install -r requirements.txt          # only needed for real camera
python mock_vision_state.py              # print all mock scenarios (no camera)
```

### Frontend + camera together (3 terminals)

The dashboard shows two modes — *Demo Mode* (mock buttons) and *Camera Bridge
Mode*. The browser never opens the webcam; this bridge does, and posts evidence
to the backend, which the dashboard polls and shows as **source: camera**.

```bash
# Terminal 1 — backend
cd /home/ivancito/VisionMPI/backend
source ../.venv/bin/activate
uvicorn app.main:app --reload --port 8000

# Terminal 2 — frontend
cd /home/ivancito/VisionMPI/frontend
npm run dev

# Terminal 3 — camera bridge (serves feed to UI + auto-posts)
cd /home/ivancito/VisionMPI/vision
../.venv/bin/python run_vision.py --show --serve-ui --post http://localhost:8000 --wo WO-1001 --camera-index 0 --auto-post-interval 1
```

Open **http://localhost:5173**. Real-camera Step 1 test:

1. Start **WO-1001** in the dashboard.
2. Put a **red** object inside `assembly_zone` in the OpenCV window.
3. Auto-post sends it every second (or press **`p`** to post now).
4. Dashboard shows the **live annotated feed**, **source: camera**, and
   `red_block @ assembly_zone` automatically.
5. Click **Verify Step** → Step 1 passes → **Next Step** unlocks.

**UI feed server (`--serve-ui`, default port 8010).** The browser only *displays*
the frame Python serves — it never opens the webcam.

| Endpoint | Returns |
|---|---|
| `GET /health` | `{status, camera_index, camera_locked}` |
| `GET /latest-state` | `{source, camera_locked, objects, updated_at}` |
| `GET /latest-frame.jpg` | latest annotated JPEG |
| `GET /video.mjpg` | MJPEG stream |

**Keys in the OpenCV window:** `p` post now · `s` snapshot · `q` quit.

**Hybrid evidence.** The camera owns the four colored blocks; the simulator owns
tools and finished-assembly. The backend merges evidence per object, so neither
side erases the other. Tool step uses the partial scenarios
`tool_1_removed_only` / `tool_1_returned_only` (they don't touch camera blocks).

### Calibrate the zones to your real table (`zone_calibrator.py`)

The default zones in `zones.json` are a generic layout. To make the on-screen
rectangles line up with your **physical taped station**, mount the camera, then
draw each zone on the live image:

```bash
cd /home/ivancito/VisionMPI/vision
../.venv/bin/python zone_calibrator.py --camera-index 2
```

You'll be prompted to draw zones in this order: `red_home`, `blue_home`,
`yellow_home`, `green_home`, `tool_1_home`, `tool_2_home`, `assembly_zone`,
`complete_zone`.

Controls in the window:

| Key | Action |
|---|---|
| drag mouse | draw a rectangle for the current zone |
| `n` | accept the rectangle, move to the next zone |
| `r` | redraw the current zone |
| `b` | go back to the previous zone |
| `s` | save `zones.json` |
| `q` | quit without saving |

It saves to `backend/app/data/zones.json` (the same file the pipeline reads) with
frame-size metadata:

```json
{ "frame_width": 1280, "frame_height": 720,
  "zones": { "red_home": [x1, y1, x2, y2], "...": [] } }
```

`run_vision.py` reads `frame_width`/`frame_height` (falling back to the older
`golden_view` format) and scales the zones to the live frame, so they stay
aligned. After saving, just restart the bridge:

```bash
../.venv/bin/python run_vision.py --show --serve-ui --post http://localhost:8000 --wo WO-1001 --camera-index 2 --auto-post-interval 1
```

> Calibrate from the camera's final mounted position — moving the camera
> afterward invalidates the zones (re-run the calibrator).

### Test the camera with ANY colored object (no LEGO needed)

You can validate the whole pipeline — webcam, color detection, zone mapping,
backend posting — with sticky notes, colored paper, markers, a notebook, or a
phone screen. The four colors you need are **red, blue, yellow, green**.

**Step A — check the camera:**
```bash
cd /home/ivancito/VisionMPI/vision
../.venv/bin/python test_camera.py
```
Probes indexes 0–4, prints which open + frame shape, and saves
`snapshots/camera_test.jpg` from the first working camera. Note the working
index it reports.

**Step B — generate on-screen color targets:**
```bash
../.venv/bin/python make_test_colors.py
```
Writes `red_test.png`, `blue_test.png`, `yellow_test.png`, `green_test.png`, and
`all_colors_grid.png` to `snapshots/test_targets/`.

**Step C — pick a target:** open one of those PNGs on your phone or a second
screen, or just grab a red/blue/yellow/green piece of paper or a sticky note.

**Step D — open the live debug window:**
```bash
../.venv/bin/python run_vision.py --show --camera-index 0
```
(use the index Step A reported; try `1` or `2` if `0` is wrong).

**Step E — confirm detection:** move a **red** object into the on-screen
`assembly_zone` rectangle. The debug window should label it:
```
red_block @ assembly_zone
```
Blue/yellow/green work the same way — drop them in any zone rectangle and watch
the label update.

**Step F — test backend posting** (backend must be running on :8000):
```bash
../.venv/bin/python run_vision.py --show --post http://localhost:8000 --wo WO-1001 --camera-index 0
```
In the live window:
- `q` = quit
- `s` = save a snapshot to `snapshots/`
- `p` = POST the current camera state to the backend

After pressing `p` with a red object in the assembly zone, validating step 1 on
the backend will pass (`can_advance: true`) — driven by your real webcam.

#### Troubleshooting

- **No camera opens:** try `--camera-index 1` or `2`. Re-run `test_camera.py` to
  see which index works.
- **Camera busy / black frame:** another app is holding it — close Zoom,
  Discord, Meet, or any browser tab using the webcam, then retry.
- **Color not detected:** use a brighter/more saturated target and good lighting;
  a glossy screen can glare — tilt it. Tune `COLOR_RANGES` / `MIN_CONTOUR_AREA`
  in `color_detector.py` for your lighting if needed.
- **Detected but wrong/`no-zone`:** the object's center must sit *inside* a
  visible zone rectangle — move it fully into the box (e.g. `assembly_zone`).
- **Backend doesn't update:** confirm the API is running at
  `http://localhost:8000` (`curl localhost:8000/health`) and that you passed
  `--post http://localhost:8000 --wo WO-1001`.
- **No camera at all:** the pipeline still runs on mock —
  `../.venv/bin/python run_vision.py --once --mock step1_done`.

### Real webcam bridge (`run_vision.py`)

The runnable bridge: webcam → HSV color detection (red/blue/yellow/green) →
zone mapping → backend-ready vision state. No model training; pure OpenCV.

```bash
cd vision

# One-shot: grab a frame, save an ANNOTATED snapshot, print the state, exit.
python run_vision.py --once

# Live debug window with the zone overlay (q=quit, s=snapshot, p=post).
python run_vision.py --show

# Live and push every frame to the backend for a work order.
python run_vision.py --show --post http://localhost:8000 --wo WO-1001

# No camera / wrong lighting? Fall back to a mock scenario (same shape).
python run_vision.py --once --mock step1_done
```

Output adds `camera_locked` to the standard contract and is accepted by the
backend's `/work-orders/{id}/vision-state` endpoint unchanged:

```json
{ "camera_locked": true,
  "objects": [ { "object": "red_block", "zone": "assembly_zone", "confidence": 0.9 } ] }
```

Zones are **scaled from the golden view to the live frame resolution**, so the
boxes line up on any webcam. Tune `COLOR_RANGES` / `MIN_CONTOUR_AREA` in
`color_detector.py` under your demo lighting if a block is missed. Tools and
`finished_assembly` are still mock-only (see TODOs) — run those steps with
`--mock` or the dashboard's Vision Simulator.

## Push real/mock vision to the backend

```python
import requests
from mock_vision_state import build_state
requests.post(
    "http://localhost:8000/work-orders/WO-1001/vision-state",
    json=build_state("step1_done"),
)
```

## TODOs (clearly marked in code)

- HSV thresholds: tune in `color_detector.py` under demo lighting.
- Tool detection: ArUco tags on `tool_1` / `tool_2` (`color_detector.py`).
- `finished_assembly` definition (coordinate with backend lead).
- ArUco camera lock implementation (`calibration.py`).
