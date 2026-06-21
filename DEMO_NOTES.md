# Demo Notes — Voice + Block Sequence

The presentation demo is intentionally simple: **voice + Lego blocks + work-order
unlock**. Complete **GREEN → BLUE → RED → YELLOW** and the Work Order unlocks.
No tools, no tool checklist, no tool detection.

## Start everything

```bash
# Terminal 1 — backend
cd /home/ivancito/VisionMPI/backend
../.venv/bin/uvicorn app.main:app --reload --port 8000

# Terminal 2 — frontend
cd /home/ivancito/VisionMPI/frontend
npm run dev                # http://localhost:5173

# Terminal 3 (optional) — live camera bridge
cd /home/ivancito/VisionMPI/vision
../.venv/bin/python run_vision.py --show --serve-ui --camera-index 0
```

Open **http://localhost:5173**.

## Manual demo checklist

1. Start the **backend**.
2. Start the **frontend**.
3. (Optional) Start the **vision bridge** (camera or mock). The "Camera" pill
   turns green and a live feed appears; the demo also works with no camera.
4. Click **🔊 Enable Voice** (required once — browsers block audio until a click).
   You should hear *"Vision system ready."* and the voice pill shows **Voice ready**.
5. Run the block sequence — click **green → blue → red → yellow** (or **▶ Full
   sequence**).
6. Confirm voice is heard: *"Green block verified."* … *"Sequence complete. Work
   order unlocked."*
7. Confirm the banner flips to **✅ WORK ORDER UNLOCKED** after the yellow block.
8. Confirm **no tool requirements** appear anywhere in the UI.

Try **✗ Wrong block** at any point: you'll hear *"Wrong block. Please follow the
sequence."*, the banner stays **🔒 LOCKED**, and the backend logs the failed
attempt (it is not silently fixed).

## Mock commands (no camera needed)

The UI mock buttons map directly to the backend. To drive it from a terminal:

```bash
B=http://localhost:8000

# Start a session
SID=$(curl -s -X POST $B/api/verification-sessions/start \
  -H 'content-type: application/json' \
  -d '{"work_order_id":"WO-1001","worker_id":"operator-001"}' \
  | python3 -c "import sys,json;print(json.load(sys.stdin)['session_id'])")

submit () { curl -s -X POST $B/api/verification-sessions/$SID/blocks/submit \
  -H 'content-type: application/json' -d "{\"submitted_color\":\"$1\"}"; echo; }

submit green     # -> "Green block verified."
submit blue      # -> "Blue block verified."
submit red       # -> "Red block verified."
submit yellow    # -> "Sequence complete. Work order unlocked."

# Wrong sequence (rejected + logged, WO stays locked):
submit yellow    # when green is expected -> "Wrong block. Please follow the sequence."

# Unlock (only succeeds after the full correct sequence):
curl -s -X POST $B/api/work-orders/WO-1001/unlock; echo
```

## Voice provider

- **Working path:** the browser **Web Speech API** (`speechSynthesis`). This is why
  the **Enable Voice** button exists — autoplay audio is blocked until a user
  gesture.
- **Sponsor path (Deepgram TTS):** scaffolded but **not wired** (no key/SDK in the
  repo). We do not pretend it works; see `frontend/src/voice.js` and
  `integrations/deepgram/README.md`. The browser fallback keeps the demo audible.

## Unlock rule (backend truth)

`can_open_work_order` is computed in one place
(`verification_session_service._can_open`) and depends **only on the completed
block sequence** by default. No tool state is ever involved. To additionally
require a safety-glasses (PPE) check, set `PPE_GATE_ENABLED=true` — the PPE
machinery stays intact and tested either way.

## Tests

```bash
cd backend
../.venv/bin/python tests/test_verification.py   # 11 checks
../.venv/bin/python smoke_test.py                # legacy MPI flow (unchanged)
```
