#!/usr/bin/env python3
"""Camera health check — find a working webcam before running the vision bridge.

Probes camera indexes 0..4, reports which open, prints the captured frame shape,
and saves one test image from the first working camera to
vision/snapshots/camera_test.jpg.

Run:
    cd vision
    ../.venv/bin/python test_camera.py

No LEGO blocks needed — this just confirms the OS hands us a webcam.
"""
import os
import sys

MAX_INDEX = 4  # probe 0..4 inclusive
SNAPSHOT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "snapshots")
TEST_IMAGE = os.path.join(SNAPSHOT_DIR, "camera_test.jpg")


def main():
    try:
        import cv2
    except ImportError:
        print("[error] OpenCV is not installed.")
        print("        Install it with: ../.venv/bin/pip install -r requirements.txt")
        return 1

    os.makedirs(SNAPSHOT_DIR, exist_ok=True)

    print(f"Probing camera indexes 0..{MAX_INDEX} ...\n")
    first_working = None
    first_frame = None

    for idx in range(MAX_INDEX + 1):
        cap = cv2.VideoCapture(idx)
        if not cap.isOpened():
            print(f"  index {idx}: NOT available (did not open)")
            cap.release()
            continue

        ok, frame = cap.read()
        if not ok or frame is None:
            print(f"  index {idx}: opened, but could NOT capture a frame")
            cap.release()
            continue

        h, w = frame.shape[:2]
        ch = frame.shape[2] if frame.ndim == 3 else 1
        print(f"  index {idx}: OK  ->  frame shape {w}x{h} ({ch} channels)")
        if first_working is None:
            first_working = idx
            first_frame = frame
        cap.release()

    print()
    if first_working is None:
        print("[error] No working camera found on indexes 0..4.")
        print("  - Is a webcam connected / enabled?")
        print("  - Close any app using the camera (Zoom, Discord, browser tabs).")
        print("  - On Linux, check permissions: ls -l /dev/video*")
        print("  - You can still run the pipeline without a camera:")
        print("      ../.venv/bin/python run_vision.py --once --mock step1_done")
        return 1

    import cv2  # already imported above; kept local for clarity
    cv2.imwrite(TEST_IMAGE, first_frame)
    print(f"[ok] First working camera: index {first_working}")
    print(f"[ok] Saved a test image -> {TEST_IMAGE}")
    print()
    print("Next:")
    print(f"  ../.venv/bin/python run_vision.py --show --camera-index {first_working}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
