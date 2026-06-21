#!/usr/bin/env python3
"""Roboflow Workflow runner — webcam -> hosted Workflow -> predictions overlay.

This is the WORKING equivalent of the Roboflow "WebRTC stream" snippet. That
snippet uses `inference_sdk.webrtc` (WebcamSource / StreamConfig / client.webrtc
.stream) which:
  * is NOT part of the installed inference-sdk (it needs the `aiortc` extra), and
  * requires a PAID hosted GPU-streaming plan (`webrtc-gpu-medium`).

Instead, this script runs the SAME workflow (find-object-and-safety-glasses) per
frame via `InferenceHTTPClient.run_workflow` against serverless inference — no
GPU-streaming plan needed. Per-frame network inference is slower than WebRTC GPU
streaming (expect a few FPS), which is fine for a demo.

Secrets come from the environment / repo .env (ROBOFLOW_API_KEY) — never hardcoded.

Examples
--------
    # one frame from the webcam -> print predictions + save annotated snapshot
    ../.venv/bin/python roboflow_workflow_stream.py --once

    # run on a still image instead of the camera
    ../.venv/bin/python roboflow_workflow_stream.py --image /path/to/photo.jpg

    # live window, workflow per frame (q to quit)
    ../.venv/bin/python roboflow_workflow_stream.py --show --camera-index 0
"""
import argparse
import os
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, ".."))
SNAP_DIR = os.path.join(_HERE, "snapshots")

DEFAULT_WORKSPACE = "joses-workspace-zokda"
DEFAULT_WORKFLOW = "find-object-and-safety-glasses"
DEFAULT_API_URL = "https://serverless.roboflow.com"


def _load_dotenv():
    path = os.path.join(_ROOT, ".env")
    if not os.path.exists(path):
        return
    for line in open(path):
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def _extract_predictions(result):
    """Flatten a workflow result into a list of detection dicts."""
    out = result[0] if isinstance(result, list) else result
    preds = []
    if isinstance(out, dict):
        for v in out.values():
            if isinstance(v, dict) and isinstance(v.get("predictions"), list):
                preds.extend([d for d in v["predictions"] if isinstance(d, dict) and "class" in d])
            elif isinstance(v, dict) and "class" in v and "confidence" in v:
                preds.append(v)
            elif isinstance(v, list):
                preds.extend([d for d in v if isinstance(d, dict) and "class" in d])
    return preds


def _client(args):
    from inference_sdk import InferenceHTTPClient
    key = os.getenv("ROBOFLOW_API_KEY", "")
    if not key:
        print("[error] ROBOFLOW_API_KEY not set (put it in .env).", file=sys.stderr)
        sys.exit(1)
    return InferenceHTTPClient(api_url=args.api_url, api_key=key)


def _run_workflow(client, args, image):
    return _extract_predictions(client.run_workflow(
        workspace_name=args.workspace,
        workflow_id=args.workflow,
        images={"image": image},
        use_cache=True,
    ))


def _annotate(frame, preds):
    import cv2
    out = frame.copy()
    for p in preds:
        cls, conf = p.get("class", "?"), float(p.get("confidence", 0))
        if all(k in p for k in ("x", "y", "width", "height")):
            x, y, w, h = p["x"], p["y"], p["width"], p["height"]
            x1, y1, x2, y2 = int(x - w / 2), int(y - h / 2), int(x + w / 2), int(y + h / 2)
            cv2.rectangle(out, (x1, y1), (x2, y2), (60, 200, 60), 2)
            cv2.putText(out, f"{cls} {conf:.2f}", (x1, max(0, y1 - 8)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (60, 200, 60), 2, cv2.LINE_AA)
    return out


def run_once(args):
    import cv2
    client = _client(args)
    if args.image:
        frame = cv2.imread(args.image)
        if frame is None:
            print(f"[error] could not read image {args.image}", file=sys.stderr)
            return 1
    else:
        cap = cv2.VideoCapture(args.camera_index)
        if not cap.isOpened():
            print(f"[error] could not open camera {args.camera_index}", file=sys.stderr)
            return 1
        for _ in range(8):
            ok, frame = cap.read()
        cap.release()
        if not ok:
            print("[error] no frame from camera", file=sys.stderr)
            return 1
    preds = _run_workflow(client, args, args.image or frame)
    print(f"[once] {len(preds)} detections: " +
          ", ".join(f"{p.get('class')}({float(p.get('confidence',0)):.2f})" for p in preds))
    os.makedirs(SNAP_DIR, exist_ok=True)
    path = os.path.join(SNAP_DIR, f"workflow-{time.strftime('%Y%m%d-%H%M%S')}.jpg")
    cv2.imwrite(path, _annotate(frame, preds))
    print(f"[once] annotated -> {path}")
    return 0


def run_show(args):
    import cv2
    client = _client(args)
    cap = cv2.VideoCapture(args.camera_index)
    if not cap.isOpened():
        print(f"[error] could not open camera {args.camera_index}", file=sys.stderr)
        return 1
    print("[show] q=quit. Per-frame serverless inference — expect a few FPS.", file=sys.stderr)
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                continue
            try:
                preds = _run_workflow(client, args, frame)
            except Exception as e:
                print(f"[show] inference error: {e}", file=sys.stderr)
                preds = []
            cv2.imshow("Roboflow Workflow Output", _annotate(frame, preds))
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
    finally:
        cap.release()
        cv2.destroyAllWindows()
    return 0


def main():
    _load_dotenv()
    ap = argparse.ArgumentParser(description="Run a Roboflow Workflow on the webcam (per-frame).")
    ap.add_argument("--show", action="store_true", help="Live window, workflow per frame.")
    ap.add_argument("--once", action="store_true", help="One frame -> predictions + snapshot.")
    ap.add_argument("--image", help="Run on a still image instead of the camera.")
    ap.add_argument("--camera-index", type=int, default=0)
    ap.add_argument("--workspace", default=os.getenv("ROBOFLOW_WORKSPACE", DEFAULT_WORKSPACE))
    ap.add_argument("--workflow", default=os.getenv("ROBOFLOW_WORKFLOW_ID", DEFAULT_WORKFLOW))
    ap.add_argument("--api-url", default=os.getenv("ROBOFLOW_API_URL", DEFAULT_API_URL))
    args = ap.parse_args()
    try:
        return run_show(args) if args.show else run_once(args)
    except ImportError as e:
        print(f"[error] {e}\n[hint] pip install inference-sdk opencv-python", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
