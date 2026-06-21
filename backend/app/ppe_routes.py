"""PPE / Safety-Glasses API routes.

Endpoints (mounted under /api):
    GET  /api/ppe/config                         -> client config (thresholds, etc.)
    POST /api/ppe/check                           -> run a PPE check, store evidence
    POST /api/work-orders/{id}/unlock             -> gated unlock (403 if not verified)

The model is evidence only. The decision is made in ppe_service.decide(), the
gate in safety_gate, and every check is written to the audit log + ppe_checks DB.
"""
import os
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from .audit_logger import AuditLogger
from . import ppe_service, ppe_store

router = APIRouter(prefix="/api", tags=["ppe"])

EVIDENCE_DIR = os.path.join(os.path.dirname(__file__), "data", "ppe_evidence")
_audit = AuditLogger()  # appends to the same audit_log.jsonl as the rest of the app

# Run the migration once at import.
ppe_store.init_db()


@router.get("/ppe/config")
def ppe_config():
    """Config the frontend needs to render the safety-glasses modal."""
    cfg = ppe_service.get_config()
    return {
        "model_configured": ppe_service.model_configured(),
        "required": cfg["required"],
        "min_confidence": cfg["min_confidence"],
        "expiration_seconds": cfg["expiration_seconds"],
        "positive_classes": sorted(ppe_service.POSITIVE_CLASSES),
        "negative_classes": sorted(ppe_service.NEGATIVE_CLASSES),
    }


def _save_evidence(image_bytes: bytes) -> str:
    os.makedirs(EVIDENCE_DIR, exist_ok=True)
    name = f"ppe-{datetime.now(timezone.utc):%Y%m%d-%H%M%S}-{uuid.uuid4().hex[:8]}.jpg"
    path = os.path.join(EVIDENCE_DIR, name)
    with open(path, "wb") as f:
        f.write(image_bytes)
    return path


@router.post("/ppe/check")
async def ppe_check(
    image: UploadFile = File(...),
    work_order_id: str = Form(...),
    worker_id: str = Form(...),
):
    """Run a safety-glasses check on a camera snapshot and store the evidence."""
    image_bytes = await image.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="Empty image upload.")

    image_path = _save_evidence(image_bytes)

    try:
        result = ppe_service.run_check(image_bytes)
    except ppe_service.PPEServiceError as e:
        # Model unreachable/misconfigured — record a failed (not verified) check.
        _audit.log(
            work_order_id, event="ppe-check", status="blocked",
            message=f"PPE check error: {e}",
        )
        raise HTTPException(status_code=502, detail=str(e))

    cfg = ppe_service.get_config()
    created = datetime.now(timezone.utc)
    expires = created + timedelta(seconds=cfg["expiration_seconds"])
    created_iso, expires_iso = created.isoformat(), expires.isoformat()

    ppe_store.insert_check(
        work_order_id=work_order_id,
        worker_id=worker_id,
        verified=result["safety_glasses_verified"],
        confidence=result["confidence"],
        reason=result["reason"],
        predictions=result["predictions"],
        image_path=image_path,
        created_at=created_iso,
        expires_at=expires_iso,
    )

    _audit.log(
        work_order_id,
        event="ppe-check",
        status="passed" if result["safety_glasses_verified"] else "blocked",
        message=f"[{worker_id}] {result['reason']}",
    )

    return {
        "work_order_id": work_order_id,
        "worker_id": worker_id,
        "safety_glasses_verified": result["safety_glasses_verified"],
        "confidence": result["confidence"],
        "reason": result["reason"],
        "expires_at": expires_iso,
        "created_at": created_iso,
        "predictions": result["predictions"],
    }


# NOTE: the authoritative POST /api/work-orders/{id}/unlock now lives in
# verification_routes.py — it requires BOTH PPE verification and the block
# sequence (see verification_session_service). This standalone PPE check
# endpoint remains for direct/legacy PPE-only checks.
