#!/usr/bin/env python3
"""Real vision bridge — webcam -> HSV color detection -> zones -> vision state.

This is the runnable entry point that turns a live webcam into the SAME
structured vision state the backend already consumes from mock_vision_state.py.
No model training: just OpenCV HSV color thresholding for the four colored
LEGO blocks (red / blue / yellow / green).

Pipeline (reusing the existing modules):
    frame  -> color_detector.detect_blocks()   (HSV threshold -> bboxes)
           -> zone_mapper.map_detections()      (bbox center  -> zone)
           -> {"camera_locked": true, "objects": [...]}

Examples
--------
    # One-shot: grab a frame, annotate + save a snapshot, print the state.
    python run_vision.py --once

    # Live debug window with zone overlay (q quit, s snapshot, p post).
    python run_vision.py --show

    # Live + push every frame to the backend for a work order.
    python run_vision.py --show --post http://localhost:8000 --wo WO-1001

    # No camera? Fall back to a mock scenario (same shape).
    python run_vision.py --once --mock step1_done

The webcam may capture at a different resolution than the golden view that
zones.json was defined against, so zones are SCALED to the live frame size
before mapping. That is what makes "place a red block in the assembly zone and
see red_block @ assembly_zone" actually work on a laptop webcam.
"""
import argparse
import json
import os
import sys
import time

# Make sibling modules importable whether run from repo root or vision/.
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from color_detector import detect_blocks  # noqa: E402
from zone_mapper import ZONES_PATH, load_zones, map_detections  # noqa: E402

SNAPSHOT_DIR = os.path.join(_HERE, "snapshots")

# BGR draw colors per object (OpenCV is BGR, not RGB).
DRAW_BGR = {
    "red_block": (60, 60, 230),
    "blue_block": (230, 120, 40),
    "yellow_block": (40, 210, 230),
    "green_block": (60, 200, 60),
}


# --- zone helpers ------------------------------------------------------------

def load_zones_and_view(path=ZONES_PATH):
    """Load zones plus the golden-view dimensions they were defined against."""
    with open(path) as f:
        data = json.load(f)
    gv = data.get("golden_view", {"width": 1280, "height": 720})
    return data["zones"], gv


def scale_zones(zones, golden_view, frame_w, frame_h):
    """Scale golden-view zone boxes to the live frame resolution."""
    sx = frame_w / float(golden_view["width"])
    sy = frame_h / float(golden_view["height"])
    return {
        name: [b[0] * sx, b[1] * sy, b[2] * sx, b[3] * sy]
        for name, b in zones.items()
    }


# --- state ------------------------------------------------------------------

def build_vision_state(detections, zones, source="camera", camera_locked=True):
    """Wrap mapped detections in the backend-ready shape, incl. camera_locked."""
    mapped = map_detections(detections, zones=zones, source=source)
    return {"camera_locked": camera_locked, **mapped}


def objects_summary(state):
    parts = [
        f"{o['object']}@{o['zone'] or 'none'}({o['confidence']:.2f})"
        for o in state["objects"]
    ]
    return ", ".join(parts) if parts else "(nothing detected)"


# --- drawing -----------------------------------------------------------------

def annotate(frame, state, zones, camera_locked=True):
    """Draw zone boxes + detection boxes with object/zone labels."""
    import cv2

    out = frame.copy()

    # Zones: thin gray boxes with a name tag.
    for name, (x1, y1, x2, y2) in zones.items():
        p1, p2 = (int(x1), int(y1)), (int(x2), int(y2))
        cv2.rectangle(out, p1, p2, (90, 90, 90), 1)
        cv2.putText(out, name, (p1[0] + 4, p1[1] + 16),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (160, 160, 160), 1, cv2.LINE_AA)

    # Detections: colored box + "object @ zone".
    for o in state["objects"]:
        if not o.get("bbox"):
            continue
        x1, y1, x2, y2 = (int(v) for v in o["bbox"])
        color = DRAW_BGR.get(o["object"], (255, 255, 255))
        cv2.rectangle(out, (x1, y1), (x2, y2), color, 2)
        label = f"{o['object']} @ {o['zone'] or 'no-zone'}"
        cv2.putText(out, label, (x1, max(0, y1 - 8)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2, cv2.LINE_AA)

    # Header: lock state.
    lock_txt = "CAMERA LOCKED" if camera_locked else "CAMERA UNLOCKED"
    lock_col = (60, 200, 60) if camera_locked else (60, 60, 230)
    cv2.putText(out, lock_txt, (10, frame.shape[0] - 12),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, lock_col, 2, cv2.LINE_AA)
    return out


def save_snapshot(frame, label="vision"):
    import cv2
    os.makedirs(SNAPSHOT_DIR, exist_ok=True)
    path = os.path.join(SNAPSHOT_DIR, f"{label}-{time.strftime('%Y%m%d-%H%M%S')}.jpg")
    cv2.imwrite(path, frame)
    return path


# --- backend posting ---------------------------------------------------------

def post_state(base_url, work_order_id, state):
    """POST the vision state to the backend's vision-state endpoint."""
    import requests
    url = f"{base_url.rstrip('/')}/work-orders/{work_order_id}/vision-state"
    body = {"objects": state["objects"], "source": state.get("source", "camera")}
    resp = requests.post(url, json=body, timeout=5)
    resp.raise_for_status()
    return resp.json()


# --- mock fallback -----------------------------------------------------------

def mock_state(scenario):
    """Produce the same shape from a canned scenario (no camera needed)."""
    from mock_vision_state import build_state
    mapped = build_state(scenario)
    return {"camera_locked": False, **mapped}


# --- run modes ---------------------------------------------------------------

def run_mock(args):
    state = mock_state(args.mock)
    print(json.dumps(state, indent=2))
    print(f"[mock] {objects_summary(state)}", file=sys.stderr)
    if args.post:
        print(f"[mock] posted -> {post_state(args.post, args.wo, state)}", file=sys.stderr)
    return 0


def _open_camera(device):
    import cv2
    cap = cv2.VideoCapture(device)
    if not cap.isOpened():
        raise RuntimeError(
            f"Could not open camera index {device}. "
            f"Try a different --device, or use --mock <scenario>."
        )
    # Request the golden-view resolution; the driver may pick the nearest.
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    return cap


def run_once(args, zones_gv, golden_view):
    import cv2
    cap = _open_camera(args.device)
    # Warm up so auto-exposure / white balance settle before we detect.
    frame = None
    for _ in range(8):
        ok, frame = cap.read()
        if not ok:
            frame = None
    cap.release()
    if frame is None:
        raise RuntimeError("Camera opened but returned no frame.")

    h, w = frame.shape[:2]
    zones = scale_zones(zones_gv, golden_view, w, h)
    detections = detect_blocks(frame)
    state = build_vision_state(detections, zones, camera_locked=True)

    annotated = annotate(frame, state, zones)
    path = save_snapshot(annotated, label="vision-once")
    print(json.dumps(state, indent=2))
    print(f"[once] {objects_summary(state)}", file=sys.stderr)
    print(f"[once] annotated snapshot -> {path}", file=sys.stderr)
    if args.post:
        print(f"[once] posted -> {post_state(args.post, args.wo, state)}", file=sys.stderr)
    return 0


def run_live(args, zones_gv, golden_view):
    import cv2
    cap = _open_camera(args.device)
    print("[live] q=quit  s=snapshot  p=post-to-backend", file=sys.stderr)
    last_summary = None
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                print("[live] dropped frame", file=sys.stderr)
                continue
            h, w = frame.shape[:2]
            zones = scale_zones(zones_gv, golden_view, w, h)
            detections = detect_blocks(frame)
            state = build_vision_state(detections, zones, camera_locked=True)

            # Print only when the detection set changes (keeps the log readable).
            summary = objects_summary(state)
            if summary != last_summary:
                print(f"[live] {summary}", file=sys.stderr)
                last_summary = summary

            annotated = annotate(frame, state, zones)
            cv2.imshow("Locked Vision MPI - vision debug", annotated)

            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                break
            if key == ord("s"):
                print(f"[live] saved -> {save_snapshot(annotated)}", file=sys.stderr)
            if key == ord("p"):
                if args.post:
                    print(f"[live] posted -> {post_state(args.post, args.wo, state)}",
                          file=sys.stderr)
                else:
                    print("[live] no --post URL set", file=sys.stderr)
    finally:
        cap.release()
        cv2.destroyAllWindows()
    return 0


def main():
    ap = argparse.ArgumentParser(description="Real webcam vision bridge for Locked Vision MPI.")
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--once", action="store_true",
                      help="Grab one frame, save an annotated snapshot, print state, exit.")
    mode.add_argument("--show", action="store_true",
                      help="Live debug window with zone overlay.")
    ap.add_argument("--camera-index", "--device", type=int, default=0, dest="device",
                    help="Webcam index (default 0). Try 1 or 2 if 0 doesn't open.")
    ap.add_argument("--mock", metavar="SCENARIO",
                    help="Skip the camera and emit a mock scenario (e.g. step1_done).")
    ap.add_argument("--post", metavar="URL",
                    help="Backend base URL to POST vision state to (e.g. http://localhost:8000).")
    ap.add_argument("--wo", default="WO-1001", help="Work order id for --post (default WO-1001).")
    args = ap.parse_args()

    # Mock fallback: explicit, or graceful if OpenCV/camera is unavailable.
    if args.mock:
        return run_mock(args)

    try:
        zones_gv, golden_view = load_zones_and_view()
        if args.show:
            return run_live(args, zones_gv, golden_view)
        # Default to one-shot if neither --show nor --once given.
        return run_once(args, zones_gv, golden_view)
    except Exception as e:  # camera/OpenCV problems -> point at the mock path
        print(f"[error] {e}", file=sys.stderr)
        print("[hint] No camera? Try: python run_vision.py --once --mock step1_done",
              file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
