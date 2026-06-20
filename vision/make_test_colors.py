#!/usr/bin/env python3
"""Generate printable / on-screen color targets for testing detection.

No LEGO blocks? Generate solid color images, open them on your phone or a second
screen (or print them), and point the webcam at them. The colors are chosen to
sit squarely inside the HSV ranges in color_detector.py, so each maps to the
matching *_block object.

Run:
    cd vision
    ../.venv/bin/python make_test_colors.py

Outputs -> vision/snapshots/test_targets/
    red_test.png  blue_test.png  yellow_test.png  green_test.png
    all_colors_grid.png
"""
import os

OUT_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "snapshots", "test_targets"
)

# Strong BGR colors that land well inside color_detector.COLOR_RANGES.
# object_name: (BGR, human label)
COLORS = {
    "red_block": ((0, 0, 255), "RED"),
    "blue_block": ((255, 0, 0), "BLUE"),
    "yellow_block": ((0, 255, 255), "YELLOW"),
    "green_block": ((0, 200, 0), "GREEN"),
}

SIZE = 800  # single-target image is SIZE x SIZE


def _text(cv2, img, txt, org, scale, color, thick=2):
    cv2.putText(img, txt, org, cv2.FONT_HERSHEY_SIMPLEX, scale, color, thick, cv2.LINE_AA)


def make_single(cv2, np, bgr, label, path):
    img = np.full((SIZE, SIZE, 3), 255, np.uint8)  # white background
    cv2.rectangle(img, (70, 150), (SIZE - 70, SIZE - 70), bgr, -1)
    cv2.rectangle(img, (70, 150), (SIZE - 70, SIZE - 70), (40, 40, 40), 3)
    _text(cv2, img, f"{label} test target", (70, 100), 1.4, (20, 20, 20), 3)
    cv2.imwrite(path, img)
    return path


def make_grid(cv2, np, path):
    cell = 400
    img = np.full((cell * 2, cell * 2, 3), 255, np.uint8)
    positions = list(COLORS.items())
    for i, (_, (bgr, label)) in enumerate(positions):
        r, c = divmod(i, 2)
        y0, x0 = r * cell, c * cell
        cv2.rectangle(img, (x0 + 30, y0 + 70), (x0 + cell - 30, y0 + cell - 30), bgr, -1)
        cv2.rectangle(img, (x0 + 30, y0 + 70), (x0 + cell - 30, y0 + cell - 30), (40, 40, 40), 2)
        _text(cv2, img, label, (x0 + 40, y0 + 55), 1.0, (20, 20, 20), 2)
    cv2.imwrite(path, img)
    return path


def main():
    try:
        import cv2
        import numpy as np
    except ImportError:
        print("[error] OpenCV/NumPy not installed.")
        print("        Install with: ../.venv/bin/pip install -r requirements.txt")
        return 1

    os.makedirs(OUT_DIR, exist_ok=True)

    written = []
    for obj, (bgr, label) in COLORS.items():
        name = obj.replace("_block", "_test") + ".png"
        written.append(make_single(cv2, np, bgr, label, os.path.join(OUT_DIR, name)))
    written.append(make_grid(cv2, np, os.path.join(OUT_DIR, "all_colors_grid.png")))

    print(f"[ok] Wrote {len(written)} color targets to:\n     {OUT_DIR}\n")
    for p in written:
        print("  -", os.path.basename(p))
    print()
    print("Open these on your phone/second screen and point the webcam at one,")
    print("then run:  ../.venv/bin/python run_vision.py --show --camera-index 0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
