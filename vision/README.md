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
