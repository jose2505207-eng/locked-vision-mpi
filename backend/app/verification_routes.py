"""Verification session API routes (mounted under /api).

    POST /api/verification-sessions/start
    POST /api/verification-sessions/{session_id}/ppe-check       (multipart image)
    POST /api/verification-sessions/{session_id}/blocks/submit
    GET  /api/verification-sessions/{session_id}/status
    POST /api/work-orders/{work_order_id}/unlock                 (authoritative gate)

The backend owns truth: routes call the verification service, which is the only
place can_open_work_order is computed. A client-supplied can_open_work_order is
never read.
"""
import asyncio
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Body, File, Form, HTTPException, UploadFile

from . import ppe_service, ppe_store, verification_session_service as sessions
from .ppe_routes import _save_evidence

router = APIRouter(prefix="/api", tags=["verification"])


@router.post("/verification-sessions/start")
def start_session(payload: dict = Body(default={})):
    work_order_id = (payload or {}).get("work_order_id")
    if not work_order_id:
        raise HTTPException(status_code=400, detail="work_order_id is required.")
    worker_id = (payload or {}).get("worker_id")
    return sessions.start_session(work_order_id, worker_id)


@router.post("/verification-sessions/{session_id}/ppe-check")
async def ppe_check(
    session_id: str,
    image: UploadFile = File(...),
    work_order_id: str = Form(None),
    worker_id: str = Form(None),
):
    session = sessions.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail=f"Unknown session {session_id}.")

    image_bytes = await image.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="Empty image upload.")
    image_path = _save_evidence(image_bytes)

    cfg = ppe_service.get_config()
    try:
        # Bound the provider call so a slow/unreachable model can't hang the request.
        result = await asyncio.wait_for(
            asyncio.to_thread(ppe_service.run_check, image_bytes),
            timeout=cfg["provider_timeout"],
        )
    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=504,
            detail=f"PPE provider timed out after {cfg['provider_timeout']:.0f}s.",
        )
    except ppe_service.PPEServiceError as e:
        raise HTTPException(status_code=502, detail=str(e))
    created = datetime.now(timezone.utc)
    expires = created + timedelta(seconds=cfg["expiration_seconds"])
    created_iso, expires_iso = created.isoformat(), expires.isoformat()

    ppe_store.insert_check(
        session_id=session_id,
        work_order_id=session["work_order_id"],
        worker_id=session["worker_id"],
        verified=result["safety_glasses_verified"],
        confidence=result["confidence"],
        reason=result["reason"],
        predictions=result["predictions"],
        image_path=image_path,
        created_at=created_iso,
        expires_at=expires_iso,
    )

    pub = sessions.apply_ppe_result(session_id, result, expires_iso)
    return {
        "session_id": session_id,
        "ppe_verified": result["safety_glasses_verified"],
        "confidence": result["confidence"],
        "reason": result["reason"],
        "mode": result.get("mode"),
        "expires_at": expires_iso if result["safety_glasses_verified"] else None,
        "predictions": result["predictions"],
        "sequence_passed": pub["sequence_passed"],
        "expected_next_color": pub["expected_next_color"],
        "can_open_work_order": pub["can_open_work_order"],
    }


@router.post("/verification-sessions/{session_id}/blocks/submit")
def submit_block(session_id: str, payload: dict = Body(default={})):
    # NOTE: only submitted_color is read. Any client-sent can_open_work_order,
    # accepted, or sequence_passed is ignored — the backend decides.
    submitted_color = (payload or {}).get("submitted_color")
    if submitted_color is None:
        raise HTTPException(status_code=400, detail="submitted_color is required.")
    resp = sessions.submit_block(session_id, submitted_color)
    if resp is None:
        raise HTTPException(status_code=404, detail=f"Unknown session {session_id}.")
    return resp


@router.get("/verification-sessions/{session_id}/status")
def session_status(session_id: str):
    st = sessions.status(session_id)
    if st is None:
        raise HTTPException(status_code=404, detail=f"Unknown session {session_id}.")
    return st


@router.post("/work-orders/{work_order_id}/unlock")
def unlock_work_order(work_order_id: str, payload: dict = Body(default={})):
    """Authoritative gate: unlocked only if the latest session passed PPE + sequence.

    Returns 200 with the flat contract body in BOTH cases — the frontend gates on
    `can_open_work_order` / `unlocked`, never on the HTTP status code.
    """
    return sessions.evaluate_unlock(work_order_id)
