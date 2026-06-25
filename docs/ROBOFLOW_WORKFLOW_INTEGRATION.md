# Roboflow Workflow Integration

Wires the Roboflow Workflow **`find-object-and-safety-glasses`** (workspace
`joses-workspace-zokda`) into the project as the real PPE provider, and adds a
standalone live runner. The model returns **evidence**; the **backend decides**.

## About the pasted WebRTC snippet

The Roboflow UI snippet uses `inference_sdk.webrtc` (`WebcamSource`,
`StreamConfig`, `client.webrtc.stream`). That module is **not** in the installed
`inference-sdk` (it needs the `aiortc` extra) and the streaming path requires a
**paid hosted GPU plan** (`webrtc-gpu-medium`). So that exact snippet does not run
as written.

Instead we use the supported, snapshot-based call **`InferenceHTTPClient
.run_workflow(...)`** against serverless inference — same workflow, no GPU-stream
plan. This was verified live (HTTP 200, predictions returned).

## Two integration points

### 1) Backend PPE provider (`roboflow_workflow`)

`backend/app/ppe_service.py` gained `call_roboflow_workflow()` + a flattener
(`_extract_predictions`). `run_check()` picks the provider from config:

```
PPE_MODEL_PROVIDER (or auto):
  roboflow_workflow  -> ROBOFLOW_WORKSPACE + ROBOFLOW_WORKFLOW_ID (preferred)
  roboflow           -> ROBOFLOW_PPE_MODEL_ID (single detect model)
  mock               -> labeled dev fallback (no key)
```

The workflow's predictions feed the existing `decide()`, which applies the
positive/negative class policy + `PPE_MIN_CONFIDENCE`. **The model never unlocks
anything** — `verification_session_service` / `safety_gate` own the decision.

> ⚠️ Class names: confirm what the workflow labels safety glasses as (e.g.
> `safety_glasses`, `glasses`). If it differs, add it to `POSITIVE_CLASSES` in
> `ppe_service.py`. Object/block classes the workflow returns are ignored by the
> PPE decision (they don't match the PPE class sets).

### 2) Standalone live runner

`vision/roboflow_workflow_stream.py` — runs the workflow per webcam frame and
draws the predictions. The working replacement for the WebRTC snippet.

```bash
cd vision
../.venv/bin/python roboflow_workflow_stream.py --once            # one frame -> snapshot + preds
../.venv/bin/python roboflow_workflow_stream.py --image photo.jpg # still image
../.venv/bin/python roboflow_workflow_stream.py --show            # live window (q quits)
```

Per-frame serverless inference is a few FPS (network roundtrip per frame). For
high-FPS live overlay you'd use the paid WebRTC GPU stream.

## Environment variables (`.env`, gitignored)

```env
ROBOFLOW_API_KEY=<private key>            # server-side only
ROBOFLOW_WORKSPACE=joses-workspace-zokda
ROBOFLOW_WORKFLOW_ID=find-object-and-safety-glasses
ROBOFLOW_API_URL=https://serverless.roboflow.com
ROBOFLOW_PUBLISHABLE_KEY=<publishable key> # safe for browser/client use
```

Leaving `PPE_MODEL_PROVIDER` blank auto-selects `roboflow_workflow` when the
workspace + workflow are set. The backend auto-loads `.env`.

## Install

```bash
pip install inference-sdk        # also in backend/ and vision/ requirements
```

`inference-sdk` pulls numpy 2.x; OpenCV 4.10 is compatible (verified — color
detection still works).

## Security

Keys live only in `.env` (gitignored) — never hardcoded/committed. The keys
shared during setup were exposed in chat; **rotate them in Roboflow.**

## Verified

- `run_workflow` against the real workflow → HTTP 200, predictions parsed.
- `ppe_service.run_check()` with `roboflow_workflow` → `mode: live`, real call,
  blank image → not verified ("No PPE detected") — no fake pass.
