"""Zone mapper — maps a detection's bounding-box center to a configured zone.

Zones come from the backend's source of truth (backend/app/data/zones.json),
defined as [x1, y1, x2, y2] in golden-view pixel coordinates. This module is
pure geometry: given detections (object + bbox), it returns the same structured
vision state shape that mock_vision_state.py produces.
"""
import json
import os

# Read the SAME zones file the backend uses, so there is one definition.
ZONES_PATH = os.path.join(
    os.path.dirname(__file__), "..", "backend", "app", "data", "zones.json"
)


def load_zones(path: str = ZONES_PATH) -> dict:
    with open(path) as f:
        return json.load(f)["zones"]


def bbox_center(bbox):
    x1, y1, x2, y2 = bbox
    return ((x1 + x2) / 2.0, (y1 + y2) / 2.0)


def point_in_zone(point, zone_box) -> bool:
    x, y = point
    x1, y1, x2, y2 = zone_box
    return x1 <= x <= x2 and y1 <= y <= y2


def map_point_to_zone(point, zones) -> str | None:
    for zone_name, box in zones.items():
        if point_in_zone(point, box):
            return zone_name
    return None


def map_detections(detections, zones=None, source: str = "camera") -> dict:
    """Turn raw detections into a backend-ready vision state.

    detections: list of {"object": str, "bbox": [x1,y1,x2,y2], "confidence": f}
    Returns the same shape as mock_vision_state.build_state().
    """
    if zones is None:
        zones = load_zones()

    objects = []
    for det in detections:
        zone = None
        if det.get("bbox"):
            zone = map_point_to_zone(bbox_center(det["bbox"]), zones)
        objects.append({
            "object": det["object"],
            "zone": zone,
            "bbox": det.get("bbox"),
            "confidence": det.get("confidence", 1.0),
        })
    return {"objects": objects, "source": source, "scenario": None}
