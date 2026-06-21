#!/usr/bin/env python3
"""Zone calibrator — draw the real workstation zones on the live camera image.

Point the webcam at the taped table, draw each zone rectangle with the mouse,
and save the coordinates to the SAME zones.json the vision pipeline reads. After
calibrating, run_vision.py scales these zones to the live frame, so the on-screen
rectangles line up with the physical station.

No detection, no model — just mouse-drawn rectangles saved to disk.

Run:
    cd vision
    ../.venv/bin/python zone_calibrator.py --camera-index 2

Controls (in the window):
    draw  : hold left mouse button, drag a rectangle, release
    n     : accept the current rectangle, move to the next zone
    r     : redraw the current zone (clear the current rectangle)
    b     : go back to the previous zone
    s     : save zones.json
    q     : quit WITHOUT saving
"""
import argparse
import json
import os
import sys

# Reuse the SAME zones path the pipeline reads (single source of truth).
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
from zone_mapper import ZONES_PATH  # noqa: E402

# The exact order the operator is asked to define zones.
ZONE_ORDER = [
    "red_home",
    "blue_home",
    "yellow_home",
    "green_home",
    "tool_1_home",
    "tool_2_home",
    "assembly_zone",
    "complete_zone",
]


class _Draw:
    """Mouse-drag rectangle state for the active zone."""
    def __init__(self):
        self.start = None       # (x, y) on button down
        self.cur = None         # (x, y) while dragging
        self.rect = None        # finished [x1, y1, x2, y2]
        self.dragging = False

    def on_mouse(self, event, x, y, flags, _param):
        import cv2
        if event == cv2.EVENT_LBUTTONDOWN:
            self.start = (x, y)
            self.cur = (x, y)
            self.dragging = True
            self.rect = None
        elif event == cv2.EVENT_MOUSEMOVE and self.dragging:
            self.cur = (x, y)
        elif event == cv2.EVENT_LBUTTONUP and self.dragging:
            self.dragging = False
            self.cur = (x, y)
            self.rect = _norm(self.start, (x, y))

    def clear(self):
        self.start = self.cur = self.rect = None
        self.dragging = False


def _norm(p1, p2):
    """Return [x1, y1, x2, y2] with x1<x2, y1<y2."""
    x1, x2 = sorted((p1[0], p2[0]))
    y1, y2 = sorted((p1[1], p2[1]))
    return [int(x1), int(y1), int(x2), int(y2)]


def _open_camera(device):
    import cv2
    cap = cv2.VideoCapture(device)
    if not cap.isOpened():
        raise RuntimeError(
            f"Could not open camera index {device}. Try a different "
            f"--camera-index (1 or 2), or check test_camera.py."
        )
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    return cap


def _render(cv2, frame, zones, idx, draw):
    """Draw accepted zones, the in-progress rectangle, and the HUD."""
    out = frame.copy()

    # Accepted zones: green boxes + labels.
    for name, box in zones.items():
        x1, y1, x2, y2 = box
        cv2.rectangle(out, (x1, y1), (x2, y2), (60, 200, 60), 2)
        cv2.putText(out, name, (x1 + 4, y1 + 18),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (60, 200, 60), 1, cv2.LINE_AA)

    # In-progress rectangle (current drag or accepted-but-not-confirmed).
    box = draw.rect
    if box is None and draw.dragging and draw.start and draw.cur:
        box = _norm(draw.start, draw.cur)
    if box is not None:
        x1, y1, x2, y2 = box
        cv2.rectangle(out, (x1, y1), (x2, y2), (40, 210, 230), 2)

    # HUD.
    done = idx >= len(ZONE_ORDER)
    h = out.shape[0]
    cv2.rectangle(out, (0, 0), (out.shape[1], 60), (0, 0, 0), -1)
    if done:
        line1 = "ALL ZONES DEFINED. Press 's' to save, 'q' to quit, 'b' to edit."
    else:
        line1 = f"Draw zone {idx + 1}/{len(ZONE_ORDER)}:  {ZONE_ORDER[idx]}"
    cv2.putText(out, line1, (10, 24),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2, cv2.LINE_AA)
    cv2.putText(out, "drag=draw  n=next  r=redraw  b=back  s=save  q=quit",
                (10, 48), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (180, 180, 180), 1, cv2.LINE_AA)

    # Footer: how many defined.
    cv2.putText(out, f"defined: {len(zones)}/{len(ZONE_ORDER)}",
                (10, h - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (160, 160, 160), 1, cv2.LINE_AA)
    return out


def save_zones(path, frame_w, frame_h, zones):
    """Write zones.json with frame-size metadata (and golden_view for compat)."""
    data = {
        "frame_width": int(frame_w),
        "frame_height": int(frame_h),
        # Keep golden_view mirrored so older readers stay compatible.
        "golden_view": {"width": int(frame_w), "height": int(frame_h)},
        "description": (
            "Calibrated against the live camera frame. Zone boxes are "
            "[x1, y1, x2, y2] in pixels at frame_width x frame_height."
        ),
        "zones": {name: zones[name] for name in ZONE_ORDER if name in zones},
    }
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    return path


def main():
    ap = argparse.ArgumentParser(description="Draw and save workstation zones from the webcam.")
    ap.add_argument("--camera-index", "--device", type=int, default=0, dest="device",
                    help="Webcam index (default 0).")
    ap.add_argument("--output", default=ZONES_PATH,
                    help=f"Where to save zones.json (default: {ZONES_PATH}).")
    args = ap.parse_args()

    try:
        import cv2
    except ImportError:
        print("[error] OpenCV not installed. ../.venv/bin/pip install -r requirements.txt")
        return 1

    try:
        cap = _open_camera(args.device)
    except RuntimeError as e:
        print(f"[error] {e}")
        return 1

    win = "Zone Calibrator"
    cv2.namedWindow(win)
    draw = _Draw()
    cv2.setMouseCallback(win, draw.on_mouse)

    zones = {}
    idx = 0
    frame_w = frame_h = None
    print("[calibrator] draw each zone, press 'n' to accept. 's' saves, 'q' quits.")

    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                continue
            frame_h, frame_w = frame.shape[:2]
            cv2.imshow(win, _render(cv2, frame, zones, idx, draw))
            key = cv2.waitKey(1) & 0xFF

            if key == ord("q"):
                print("[calibrator] quit without saving.")
                break
            elif key == ord("r"):
                draw.clear()
            elif key == ord("b"):
                if idx > 0:
                    idx -= 1
                    zones.pop(ZONE_ORDER[idx], None)
                    draw.clear()
                    print(f"[calibrator] back to {ZONE_ORDER[idx]}")
            elif key == ord("n"):
                if idx >= len(ZONE_ORDER):
                    continue
                if draw.rect is None:
                    print("[calibrator] draw a rectangle first (drag the mouse).")
                    continue
                name = ZONE_ORDER[idx]
                zones[name] = draw.rect
                print(f"[calibrator] {name} = {draw.rect}")
                draw.clear()
                idx += 1
                if idx < len(ZONE_ORDER):
                    print(f"[calibrator] now draw: {ZONE_ORDER[idx]}")
                else:
                    print("[calibrator] all zones defined — press 's' to save.")
            elif key == ord("s"):
                if not zones:
                    print("[calibrator] nothing to save yet.")
                    continue
                path = save_zones(args.output, frame_w, frame_h, zones)
                missing = [z for z in ZONE_ORDER if z not in zones]
                print(f"[calibrator] saved {len(zones)} zones -> {path}")
                if missing:
                    print(f"[calibrator] WARNING: still undefined: {', '.join(missing)}")
                else:
                    print("[calibrator] all 8 zones saved. Restart run_vision.py to use them.")
                break
    finally:
        cap.release()
        cv2.destroyAllWindows()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
