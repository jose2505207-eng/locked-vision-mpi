"""Calibration / camera-lock placeholder.

The whole system assumes a FIXED camera and a GOLDEN VIEW. If the camera moves,
every zone definition becomes wrong and the evidence is untrustworthy — so the
backend should refuse to advance. This module provides the camera-lock check.

MVP: ArUco-marker based lock. Place 4 ArUco markers at the corners of the
working area. Calibration records their reference positions once ("golden
view"). On each frame, if a marker has drifted beyond a tolerance, the camera
has moved and the station is NOT ready.
"""

CALIBRATION_TOLERANCE_PX = 15  # max allowed drift per marker before "camera moved"


class CalibrationState:
    def __init__(self):
        self.golden_markers = None  # {marker_id: (cx, cy)} captured reference
        self.locked = False

    def capture_golden_view(self, markers):
        """Record the reference marker positions (call once, station empty)."""
        self.golden_markers = dict(markers)
        self.locked = True
        return self.golden_markers

    def check(self, markers) -> dict:
        """Compare current markers to the golden view.

        Returns {"calibrated": bool, "reason": str, "drift": {...}}.
        """
        if not self.locked or self.golden_markers is None:
            return {"calibrated": False, "reason": "No golden view captured yet.", "drift": {}}

        drift = {}
        ok = True
        for marker_id, (gx, gy) in self.golden_markers.items():
            if marker_id not in markers:
                ok = False
                drift[marker_id] = "missing"
                continue
            cx, cy = markers[marker_id]
            d = ((cx - gx) ** 2 + (cy - gy) ** 2) ** 0.5
            drift[marker_id] = round(d, 2)
            if d > CALIBRATION_TOLERANCE_PX:
                ok = False

        return {
            "calibrated": ok,
            "reason": "Station calibrated." if ok else "Camera moved — recalibrate.",
            "drift": drift,
        }


# TODO(vision): implement ArUco detection to feed this.
#   import cv2
#   aruco = cv2.aruco
#   detector = aruco.ArucoDetector(aruco.getPredefinedDictionary(aruco.DICT_4X4_50),
#                                  aruco.DetectorParameters())
#   corners, ids, _ = detector.detectMarkers(gray)
#   markers = {int(i): tuple(c[0].mean(axis=0)) for i, c in zip(ids.flatten(), corners)}
