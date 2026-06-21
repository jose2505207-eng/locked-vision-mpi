"""Arize detection observability (SHADOW). Logs detection/validation records so
drift and confidence can be monitored. NO raw camera images are uploaded — only
labels, confidence, zone status, expected class, and the validation outcome.

No-op when ENABLE_ARIZE_LOGGING is off or keys are missing. Any SDK/API error is
swallowed (warn once) — the demo never depends on Arize.
"""
import logging
import os
import uuid

from . import sponsor_flags

log = logging.getLogger("sponsors")

_client = None
_warned = False


def _get_client():
    global _client
    if _client is not None:
        return _client
    from arize.api import Client  # lazy import
    _client = Client(
        space_key=os.getenv("ARIZE_SPACE_KEY"),
        api_key=os.getenv("ARIZE_API_KEY"),
    )
    return _client


def _record(data: dict) -> dict:
    """The structured, image-free record we send to Arize."""
    return {
        "model_id": os.getenv("ARIZE_MODEL_ID", "locked-vision-mpi"),
        "model_version": os.getenv("ARIZE_MODEL_VERSION", "v1"),
        "prediction_id": str(uuid.uuid4()),
        "prediction_label": data.get("detected_block") or "none",
        "actual_label": data.get("expected_block") or "none",
        "prediction_score": data.get("confidence"),
        "features": {
            "work_order_id": data.get("work_order_id"),
            "event_type": data.get("event_type"),
            "current_step": data.get("current_step"),
            "expected_block": data.get("expected_block"),
            "detected_block": data.get("detected_block"),
            "in_assembly_zone": data.get("in_assembly_zone"),
            "validation_status": data.get("validation_status"),
        },
        "timestamp": data.get("timestamp"),
    }


def log_event(data: dict) -> None:
    """Log one detection/validation record to Arize. Never raises."""
    if not sponsor_flags.active("arize_logging"):
        return
    global _warned
    rec = _record(data)
    try:
        from arize.utils.types import Environments, ModelTypes  # lazy
        client = _get_client()
        client.log(
            model_id=rec["model_id"],
            model_version=rec["model_version"],
            model_type=ModelTypes.SCORE_CATEGORICAL,
            environment=Environments.PRODUCTION,
            prediction_id=rec["prediction_id"],
            prediction_label=(rec["prediction_label"], rec["prediction_score"] or 0.0),
            actual_label=rec["actual_label"],
            features=rec["features"],
        )
        if _warned:
            log.info("[arize] logging resumed")
            _warned = False
    except Exception as e:
        if not _warned:
            log.warning("[arize] log failed (soft, demo continues): %s", e)
            _warned = True
