"""PPE detection service — calls a hosted PPE model and DECIDES locally.

The model is only evidence. This module sends an image to the Roboflow hosted
inference API, parses the predictions, and then *the backend* decides whether
safety glasses are verified based on configured class names and a confidence
threshold. The model never decides; we do.

Providers (PPE_MODEL_PROVIDER, or auto-resolved):
    roboflow_workflow  a Roboflow Workflow (workspace + workflow id) via inference-sdk
    roboflow           a single Roboflow detect model
    mock               clearly-labeled development fallback (no key)

Config (environment variables):
    ROBOFLOW_API_KEY            required to call the real model
    ROBOFLOW_WORKSPACE          workflow workspace, e.g. "joses-workspace-zokda"
    ROBOFLOW_WORKFLOW_ID        e.g. "find-object-and-safety-glasses"
    ROBOFLOW_API_URL            default https://serverless.roboflow.com
    ROBOFLOW_PPE_MODEL_ID       single-model fallback, e.g. "ppe-detection/3"
    ROBOFLOW_DETECT_URL         default https://detect.roboflow.com
    PPE_MIN_CONFIDENCE          default 0.72
    PPE_CHECK_EXPIRATION_SECONDS  default 20
    PPE_REQUIRED               "true"/"false" — enforce on work-order start
"""
import base64
import logging
import random
import time

from .safety_config import ppe_config as _ppe_config

log = logging.getLogger("ppe")


def _force_ipv4_http():
    """Force outbound HTTP to use IPv4.

    Some demo networks black-hole IPv6 egress. curl survives via Happy-Eyeballs
    (parallel IPv4/IPv6), but requests/urllib3 tries each IPv6 address first and
    blocks ~5s per address before falling back to IPv4 — enough to blow the PPE
    timeout even though the Roboflow endpoint itself answers in ~2s. Pinning the
    address family to AF_INET makes the call fast and reliable.
    """
    try:
        import socket
        import urllib3.util.connection as _conn
        _conn.allowed_gai_family = lambda: socket.AF_INET
        log.info("[PPE] forced IPv4 for outbound HTTP (IPv6 egress unreliable)")
    except Exception as e:  # pragma: no cover
        log.warning("[PPE] could not force IPv4: %s", e)


_force_ipv4_http()

# Class names (normalized) that COUNT AS verified eye protection.
POSITIVE_CLASSES = {
    "goggles", "safety_glasses", "glasses", "eye_protection", "eyewear",
    "protective_eyewear", "safety_goggles",
}
# Class names (normalized) that explicitly mean NO eye protection.
NEGATIVE_CLASSES = {
    "no_goggles", "missing_goggles", "no_safety_glasses", "missing_eye_protection",
    "no_glasses", "no_eye_protection", "no_eyewear",
}


class PPEServiceError(RuntimeError):
    """Raised when the model cannot be reached or is misconfigured."""


def _norm(name: str) -> str:
    return (name or "").strip().lower().replace("-", "_").replace(" ", "_")


def get_config() -> dict:
    """PPE config (delegates to safety_config — single source of truth)."""
    return _ppe_config()


def model_configured() -> bool:
    """True when PPE verification can actually run (real model OR explicit mock).

    Drives the frontend gate: when False the modal stays locked with an honest
    "PPE unavailable" reason rather than auto-opening or faking a pass.
    """
    return get_config()["provider"] in ("roboflow_workflow", "roboflow", "mock")


def call_roboflow(image_bytes: bytes, cfg: dict) -> list:
    """Send the image to Roboflow hosted inference and return raw predictions.

    Raises PPEServiceError if the model is not configured or the call fails.
    """
    if not cfg["api_key"] or not cfg["model_id"]:
        raise PPEServiceError(
            "PPE model not configured. Set ROBOFLOW_API_KEY and ROBOFLOW_PPE_MODEL_ID."
        )
    try:
        import requests
    except ImportError as e:  # pragma: no cover
        raise PPEServiceError("The 'requests' package is required for PPE checks.") from e

    # Roboflow serverless detect: base64 body, model id in the path.
    url = f"{cfg['detect_url'].rstrip('/')}/{cfg['model_id']}"
    b64 = base64.b64encode(image_bytes).decode("ascii")
    try:
        resp = requests.post(
            url,
            params={"api_key": cfg["api_key"], "confidence": 20, "overlap": 30},
            data=b64,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        raise PPEServiceError(f"PPE model request failed: {e}") from e

    return data.get("predictions", []) or []


def _extract_predictions(workflow_result) -> list:
    """Flatten a Roboflow Workflow result into a list of detection dicts.

    A workflow returns a list (one entry per input image); each entry is a dict
    of named output blocks. An object-detection block is itself a dict with a
    nested "predictions" list. We collect every detection that has a class +
    confidence, regardless of how the output block is named.
    """
    out = workflow_result[0] if isinstance(workflow_result, list) else workflow_result
    preds = []

    def _harvest(value):
        if isinstance(value, dict):
            if "class" in value and "confidence" in value:
                preds.append(value)
            elif isinstance(value.get("predictions"), list):
                for d in value["predictions"]:
                    if isinstance(d, dict) and "class" in d and "confidence" in d:
                        preds.append(d)
        elif isinstance(value, list):
            for d in value:
                if isinstance(d, dict) and "class" in d and "confidence" in d:
                    preds.append(d)

    if isinstance(out, dict):
        for v in out.values():
            _harvest(v)
    return preds


def call_roboflow_workflow(image_path: str, cfg: dict) -> list:
    """Run a Roboflow Workflow on an image and return raw predictions.

    Calls the hosted workflow endpoint directly over HTTP
    (POST {api_url}/infer/workflows/{workspace}/{workflow_id}) with a hard
    timeout. We deliberately do NOT use inference_sdk.run_workflow(): that method
    makes an extra blocking call that hangs indefinitely against serverless even
    though the inference endpoint itself responds in ~2s. Raises PPEServiceError
    if misconfigured or the call fails.
    """
    if not (cfg["api_key"] and cfg["workspace"] and cfg["workflow_id"]):
        raise PPEServiceError(
            "Roboflow workflow not configured. Set ROBOFLOW_API_KEY, "
            "ROBOFLOW_WORKSPACE and ROBOFLOW_WORKFLOW_ID."
        )
    try:
        import requests
    except ImportError as e:  # pragma: no cover
        raise PPEServiceError("The 'requests' package is required for PPE checks.") from e

    with open(image_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("ascii")
    url = f"{cfg['api_url'].rstrip('/')}/infer/workflows/{cfg['workspace']}/{cfg['workflow_id']}"
    body = {"api_key": cfg["api_key"], "inputs": {"image": {"type": "base64", "value": b64}}}
    # (connect, read) — keep read slightly under the route cap so a slow call
    # surfaces here as a clean error instead of being cancelled by the route.
    read_to = max(5.0, cfg.get("provider_timeout", 12.0) - 1.0)
    try:
        resp = requests.post(url, json=body, timeout=(3.05, read_to))
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        raise PPEServiceError(f"Roboflow workflow request failed: {e}") from e

    # The HTTP endpoint wraps results in {"outputs": [...]}; the SDK returned the
    # bare outputs list. Hand the outputs list to the existing flattener.
    outputs = data.get("outputs", data) if isinstance(data, dict) else data
    preds = _extract_predictions(outputs)
    # Debug: parsed class names + confidence so the integration is traceable.
    # (Raw masks are dropped — they bloat the log; flip to DEBUG for the full body.)
    log.info("[PPE][parsed] %s", [(p.get("class"), round(float(p.get("confidence", 0)), 3)) for p in preds])
    if log.isEnabledFor(logging.DEBUG):
        import json
        log.debug("[PPE][raw] %s", json.dumps(data, default=str)[:2000])
    return preds


def decide(predictions: list, min_confidence: float) -> dict:
    """Backend decision: are safety glasses verified?

    Returns {safety_glasses_verified, confidence, reason, matched_class}.
    A strong NEGATIVE detection blocks; otherwise a POSITIVE detection at or
    above the threshold verifies; anything else is not verified.
    """
    positives, negatives = [], []
    for p in predictions:
        conf = float(p.get("confidence", 0.0))
        cls = _norm(p.get("class", ""))
        if cls in POSITIVE_CLASSES and conf >= min_confidence:
            positives.append((conf, cls))
        elif cls in NEGATIVE_CLASSES and conf >= min_confidence:
            negatives.append((conf, cls))

    best_pos = max(positives) if positives else None
    best_neg = max(negatives) if negatives else None
    pct = lambda c: round(c * 100, 1)

    if best_neg and (best_pos is None or best_neg[0] >= best_pos[0]):
        return {
            "safety_glasses_verified": False,
            "confidence": best_neg[0],
            "reason": f"Detected '{best_neg[1]}' ({pct(best_neg[0])}%) — no safety glasses.",
            "matched_class": best_neg[1],
        }
    if best_pos:
        return {
            "safety_glasses_verified": True,
            "confidence": best_pos[0],
            "reason": f"Safety glasses verified: '{best_pos[1]}' at {pct(best_pos[0])}%.",
            "matched_class": best_pos[1],
        }

    # Nothing qualifying — report the strongest raw signal for context.
    best_any = max((float(p.get("confidence", 0.0)) for p in predictions), default=0.0)
    return {
        "safety_glasses_verified": False,
        "confidence": best_any,
        "reason": (
            f"No eye protection detected above {pct(min_confidence)}% confidence."
            if predictions else "No PPE detected in the frame."
        ),
        "matched_class": None,
    }


def _mock_predictions(cfg: dict) -> list:
    """Clearly-labeled development predictions (NOT production).

    Simulates a little provider latency (0.5–1.0s) so the UI exercises its real
    "verifying" state, and logs loudly so mock mode is never mistaken for a real
    model call.
    """
    why = "DEMO_MOCK_PPE" if cfg.get("mock_mode") else "provider=mock"
    log.warning("[PPE][MOCK] mock verification active (%s) — NOT a real model call", why)
    time.sleep(random.uniform(0.5, 1.0))
    if cfg.get("mock_result") == "fail":
        return [{"class": "no_goggles", "confidence": 0.9}]
    return [{"class": "safety_glasses", "confidence": 0.86}]


def run_check(image_bytes: bytes) -> dict:
    """Full check: get predictions from the configured provider, then DECIDE
    locally. Returns the decision plus raw predictions, threshold, and mode.

    mode is "live" for a real model call and "mock" for development. Mock is
    always labeled and never silently presented as production.
    """
    cfg = get_config()
    log.info("[PPE] run_check provider=%s (%d bytes)", cfg["provider"], len(image_bytes))
    if cfg["provider"] == "unconfigured":
        raise PPEServiceError(
            "PPE model not configured. Set ROBOFLOW_API_KEY (+ workspace/workflow) "
            "for real verification, or DEMO_MOCK_PPE=true for the emergency fallback."
        )
    if cfg["provider"] == "mock":
        predictions = _mock_predictions(cfg)
        mode = "mock"
    elif cfg["provider"] == "roboflow_workflow":
        import os as _os
        import tempfile
        # run_workflow takes an image path; write the snapshot to a temp file.
        fd, path = tempfile.mkstemp(suffix=".jpg")
        try:
            with _os.fdopen(fd, "wb") as f:
                f.write(image_bytes)
            log.info("[PPE] calling Roboflow workflow %s/%s", cfg["workspace"], cfg["workflow_id"])
            predictions = call_roboflow_workflow(path, cfg)
            log.info("[PPE] Roboflow returned %d prediction(s)", len(predictions))
        finally:
            _os.unlink(path)
        mode = "live"
    else:
        log.info("[PPE] calling Roboflow detect model %s", cfg["model_id"])
        predictions = call_roboflow(image_bytes, cfg)
        log.info("[PPE] Roboflow returned %d prediction(s)", len(predictions))
        mode = "live"

    result = decide(predictions, cfg["min_confidence"])
    if mode == "mock":
        # Make the mock verdict unambiguous in logs, audit, and the UI.
        result["reason"] = (
            "Mock PPE verification passed"
            if result["safety_glasses_verified"]
            else "[MOCK] " + result["reason"]
        )
    result["mode"] = mode
    result["provider"] = cfg["provider"]
    result["predictions"] = predictions
    result["min_confidence"] = cfg["min_confidence"]
    result["expiration_seconds"] = cfg["expiration_seconds"]
    return result
