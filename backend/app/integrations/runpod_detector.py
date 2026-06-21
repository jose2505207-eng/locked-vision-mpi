"""Optional RunPod GPU YOLO detector — a FALLBACK provider, used only if local /
color / Roboflow detection becomes fragile. It is NOT wired into the demo's
detection path by default; the vision bridge stays the detector. A caller can
opt in by calling detect(); if the flag is off, keys are missing, or the call
fails, it returns None so the caller falls back to its existing detector.

Uses the RunPod HTTP API (runsync) via `requests` — no extra SDK needed.
"""
import base64
import logging
import os

from . import sponsor_flags

log = logging.getLogger("sponsors")


def is_available() -> bool:
    return sponsor_flags.active("runpod_detector")


def _normalize(data: dict) -> list:
    """Best-effort flatten of a RunPod YOLO response into our detection shape."""
    output = (data or {}).get("output", data)
    raw = []
    if isinstance(output, dict):
        raw = output.get("detections") or output.get("predictions") or []
    elif isinstance(output, list):
        raw = output
    dets = []
    for d in raw:
        if not isinstance(d, dict):
            continue
        cls = d.get("class") or d.get("label") or d.get("name")
        if not cls:
            continue
        dets.append({
            "object": cls,
            "confidence": d.get("confidence") or d.get("score"),
            "bbox": d.get("bbox") or d.get("box"),
            "source": "runpod",
        })
    return dets


def detect(image_bytes: bytes, timeout: float = 20.0):
    """Run detection on RunPod. Returns a list of detections, or None to signal
    'fall back to the existing detector'. Never raises.
    """
    if not sponsor_flags.active("runpod_detector"):
        return None
    try:
        import requests  # core dep
        endpoint = os.getenv("RUNPOD_ENDPOINT_ID")
        url = f"https://api.runpod.ai/v2/{endpoint}/runsync"
        b64 = base64.b64encode(image_bytes).decode("ascii")
        resp = requests.post(
            url,
            headers={"Authorization": f"Bearer {os.getenv('RUNPOD_API_KEY')}"},
            json={"input": {"image": b64}},
            timeout=timeout,
        )
        resp.raise_for_status()
        dets = _normalize(resp.json())
        log.info("[runpod] detect returned %d detection(s)", len(dets))
        return dets
    except Exception as e:
        log.warning("[runpod] detect failed (soft, caller falls back): %s", e)
        return None
