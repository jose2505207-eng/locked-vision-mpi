"""Camera capture — fixed overhead camera, single golden view.

Thin wrapper over an OpenCV VideoCapture. The camera does not move; framing is
the golden view that zones.json was defined against. Falls back cleanly when
OpenCV or a physical camera is unavailable so the rest of the repo keeps
working on mock vision.
"""
import os
import time

SNAPSHOT_DIR = os.path.join(os.path.dirname(__file__), "snapshots")


class Camera:
    def __init__(self, device_index: int = 0):
        self.device_index = device_index
        self._cap = None

    def open(self):
        import cv2  # imported lazily so mock-only runs don't need OpenCV
        self._cap = cv2.VideoCapture(self.device_index)
        if not self._cap.isOpened():
            raise RuntimeError(f"Could not open camera index {self.device_index}")
        return self

    def read(self):
        """Grab a single frame (BGR ndarray)."""
        if self._cap is None:
            raise RuntimeError("Camera not opened. Call open() first.")
        ok, frame = self._cap.read()
        if not ok:
            raise RuntimeError("Failed to read frame from camera.")
        return frame

    def snapshot(self, label: str = "snapshot") -> str:
        """Capture a frame and save it as evidence in snapshots/."""
        import cv2
        os.makedirs(SNAPSHOT_DIR, exist_ok=True)
        frame = self.read()
        ts = time.strftime("%Y%m%d-%H%M%S")
        path = os.path.join(SNAPSHOT_DIR, f"{label}-{ts}.jpg")
        cv2.imwrite(path, frame)
        return path

    def release(self):
        if self._cap is not None:
            self._cap.release()
            self._cap = None


def get_vision_state(camera: "Camera"):
    """End-to-end: frame -> color detection -> zone mapping -> vision state.

    This is the real-vision equivalent of mock_vision_state.build_state().
    """
    from color_detector import detect_blocks
    from zone_mapper import map_detections

    frame = camera.read()
    detections = detect_blocks(frame)
    return map_detections(detections, source="camera")
