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
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

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
    """Load zones plus the frame size they were defined against.

    Supports both formats: the calibrator's {"frame_width","frame_height",...}
    and the original {"golden_view": {"width","height"}}. Zones are then scaled
    from this reference size to the live frame, so a station calibrated with
    zone_calibrator.py lines up regardless of the run-time capture resolution.
    """
    with open(path) as f:
        data = json.load(f)
    if "frame_width" in data and "frame_height" in data:
        gv = {"width": data["frame_width"], "height": data["frame_height"]}
    else:
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
    """Wrap mapped detections in the backend-ready shape, incl. camera_locked.

    Each object is tagged with its source ("camera") so the backend can merge
    hybrid evidence (camera blocks + simulator tools) per object.
    """
    mapped = map_detections(detections, zones=zones, source=source)
    for o in mapped["objects"]:
        o["source"] = source
    return {"camera_locked": camera_locked, **mapped}


def _now_iso():
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


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


# --- UI feed server (Part A) -------------------------------------------------
# A tiny stdlib HTTP server so the React app can show the annotated feed WITHOUT
# the browser ever opening the webcam. Python/OpenCV stays the camera owner.

class _Shared:
    """Thread-safe holder for the latest annotated JPEG + vision state."""
    def __init__(self, camera_index):
        self.lock = threading.Lock()
        self.frame_jpeg = None
        self.state = {"source": "camera", "camera_locked": False, "objects": [], "updated_at": None}
        self.camera_index = camera_index
        self.camera_locked = False

    def update(self, frame_jpeg, state):
        with self.lock:
            self.frame_jpeg = frame_jpeg
            self.state = state
            self.camera_locked = bool(state.get("camera_locked"))

    def snapshot(self):
        with self.lock:
            return self.frame_jpeg, dict(self.state)


def _make_handler(shared):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):  # keep the terminal clean
            pass

        def _send(self, code, content_type, body):
            self.send_response(code)
            self.send_header("Content-Type", content_type)
            self.send_header("Access-Control-Allow-Origin", "*")  # allow :5173
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            path = self.path.split("?")[0]
            if path == "/health":
                body = json.dumps({
                    "status": "ok",
                    "camera_index": shared.camera_index,
                    "camera_locked": shared.camera_locked,
                }).encode()
                self._send(200, "application/json", body)
            elif path == "/latest-state":
                _, state = shared.snapshot()
                self._send(200, "application/json", json.dumps(state).encode())
            elif path == "/latest-frame.jpg":
                frame, _ = shared.snapshot()
                if frame is None:
                    self._send(503, "text/plain", b"no frame yet")
                else:
                    self._send(200, "image/jpeg", frame)
            elif path == "/video.mjpg":
                self.send_response(200)
                self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                try:
                    while True:
                        frame, _ = shared.snapshot()
                        if frame:
                            self.wfile.write(
                                b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + frame + b"\r\n"
                            )
                        time.sleep(0.1)
                except Exception:
                    return
            else:
                self._send(404, "text/plain", b"not found")
    return Handler


def start_ui_server(shared, port):
    httpd = ThreadingHTTPServer(("0.0.0.0", port), _make_handler(shared))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd


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

    # Optional UI feed server (Part A) + auto-post (Part C).
    shared = _Shared(args.device)
    httpd = None
    if args.serve_ui:
        httpd = start_ui_server(shared, args.vision_port)
        print(f"[ui] serving feed on http://localhost:{args.vision_port} "
              f"(/health /latest-state /latest-frame.jpg /video.mjpg)", file=sys.stderr)
    auto = args.auto_post_interval or 0.0
    if args.show:
        print("[live] q=quit  s=snapshot  p=post-to-backend", file=sys.stderr)
    if auto > 0 and args.post:
        print(f"[live] auto-posting every {auto:.1f}s -> {args.post} ({args.wo})", file=sys.stderr)

    last_summary = None
    last_post_summary = None
    last_post = 0.0
    printed_zones = False
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
            annotated = annotate(frame, state, zones)

            # Print the zone rectangles actually in use ONCE (scaled to this frame
            # size), so a calibration/coordinate mismatch is visible immediately.
            if not printed_zones:
                print(f"[zones] frame={w}x{h} golden={golden_view}", file=sys.stderr)
                for name, rect in zones.items():
                    print(f"        {name:14s} {rect}", file=sys.stderr)
                printed_zones = True

            # Print only when the detection set changes (keeps the log readable).
            summary = objects_summary(state)
            if summary != last_summary:
                print(f"[live] {summary}", file=sys.stderr)
                last_summary = summary

            # Publish the annotated frame + state to the UI server.
            if args.serve_ui:
                ok_jpg, buf = cv2.imencode(".jpg", annotated)
                ui_state = {
                    "source": "camera",
                    "camera_locked": True,
                    "objects": state["objects"],
                    "updated_at": _now_iso(),
                }
                if ok_jpg:
                    shared.update(buf.tobytes(), ui_state)

            # Auto-post on the interval.
            now = time.time()
            if auto > 0 and args.post and (now - last_post) >= auto:
                try:
                    body = {"objects": state["objects"], "source": state.get("source", "camera")}
                    resp = post_state(args.post, args.wo, state)
                    last_post = now
                    if args.debug_post:
                        # Full truth, every post cycle.
                        print(f"[post] POST {args.post}/work-orders/{args.wo}/vision-state",
                              file=sys.stderr)
                        for o in state["objects"]:
                            x1, y1, x2, y2 = o["bbox"]
                            cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
                            print(f"        {o['object']:13s} zone={o.get('zone')} "
                                  f"center=({cx:.0f},{cy:.0f}) conf={o.get('confidence')}",
                                  file=sys.stderr)
                        print(f"        payload={json.dumps(body)}", file=sys.stderr)
                        print(f"        backend<= accepted={resp.get('accepted')} "
                              f"source={resp.get('source')} stored={len(resp.get('objects', []))}",
                              file=sys.stderr)
                    elif summary != last_post_summary:
                        # Concise: confirm posting + what landed, only when it changes.
                        print(f"[post] -> {args.wo}: accepted={resp.get('accepted')} "
                              f"objects={len(resp.get('objects', []))} ({summary})", file=sys.stderr)
                        last_post_summary = summary
                except Exception as e:
                    print(f"[live] auto-post FAILED: {e}", file=sys.stderr)
                    last_post = now  # back off one interval

            if args.show:
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
            else:
                # Headless (--serve-ui only): ~30 fps, Ctrl+C to quit.
                time.sleep(0.03)
    except KeyboardInterrupt:
        pass
    finally:
        cap.release()
        if args.show:
            cv2.destroyAllWindows()
        if httpd is not None:
            httpd.shutdown()
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
    ap.add_argument("--serve-ui", action="store_true",
                    help="Serve the annotated feed over HTTP for the React UI.")
    ap.add_argument("--vision-port", type=int, default=8010,
                    help="Port for the UI feed server (default 8010).")
    ap.add_argument("--auto-post-interval", type=float, default=None,
                    help="Seconds between automatic posts to --post "
                         "(default: 1.0 when --post is set, else off). Use 0 to force off.")
    ap.add_argument("--debug-post", action="store_true",
                    help="Print every post cycle: objects (label/zone/center/conf), the exact "
                         "JSON payload, and the backend response. Makes the evidence flow explicit.")
    args = ap.parse_args()

    # Auto-post defaults ON (1.0s) whenever a --post target is given for a live
    # run. Without this, the bridge serves the UI feed and computes state but
    # NEVER posts evidence to the backend unless you press "p" — which looks
    # exactly like "bridge live but backend sees no objects". Pass
    # --auto-post-interval 0 to opt out (manual "p" only).
    if args.auto_post_interval is None:
        args.auto_post_interval = 1.0 if (args.post and not args.once and not args.mock) else 0.0
        if args.auto_post_interval and (args.show or args.serve_ui):
            print(f"[live] --post set; auto-posting every {args.auto_post_interval:.1f}s "
                  f"(pass --auto-post-interval 0 to disable).", file=sys.stderr)

    # Mock fallback: explicit, or graceful if OpenCV/camera is unavailable.
    if args.mock:
        return run_mock(args)

    try:
        zones_gv, golden_view = load_zones_and_view()
        if args.show or args.serve_ui:
            return run_live(args, zones_gv, golden_view)
        # Default to one-shot if neither --show/--serve-ui nor --once given.
        return run_once(args, zones_gv, golden_view)
    except Exception as e:  # camera/OpenCV problems -> point at the mock path
        print(f"[error] {e}", file=sys.stderr)
        print("[hint] No camera? Try: python run_vision.py --once --mock step1_done",
              file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
