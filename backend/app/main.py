"""Locked Vision MPI — backend API (FastAPI).

Architecture rules enforced here:
  * The fake MES is the source of truth.
  * The vision system provides evidence only.
  * The state machine validates the MPI sequence.
  * can_advance is set ONLY by the validation engine.
  * No work order closes until final 6S passes.
  * Every pass and every failure is logged.

Built with mocked vision first: POST a vision state (or a named mock
scenario) and the same endpoints work whether the evidence comes from
mock_vision_state.py or a real camera.
"""
import os
import sys

from fastapi import Body, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .audit_logger import AuditLogger
from .fake_mes_service import FakeMESService
from .models import StepResponse, ValidationResponse, WorkOrderSummary
from .mpi_state_machine import MPIStateMachine
from .ppe_routes import router as ppe_router
from .verification_routes import router as verification_router
from . import ppe_service, verification_session_service
from .validation_engine import validate_final_6s, validate_readiness, validate_step

# --- Optional mock vision scenarios (single source of truth in vision/) ------
# This lets the frontend post {"scenario": "step1_done"} instead of a full
# object list, which makes the camera-less demo trivial to drive.
_VISION_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "vision")
)
if _VISION_DIR not in sys.path:
    sys.path.insert(0, _VISION_DIR)
try:
    from mock_vision_state import build_state as build_mock_state  # type: ignore
except Exception:  # pragma: no cover - mock module is optional at runtime
    build_mock_state = None

# --- Optional Sentry monitoring (sponsor track, isolated) --------------------
if os.getenv("SENTRY_DSN"):
    try:
        import sentry_sdk

        sentry_sdk.init(dsn=os.getenv("SENTRY_DSN"), traces_sample_rate=0.2)
    except Exception:
        pass

app = FastAPI(title="Locked Vision MPI — Fake MES", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # demo only; lock down for production
    allow_methods=["*"],
    allow_headers=["*"],
)

mes = FakeMESService()
sm = MPIStateMachine(mes)
audit = AuditLogger()

# Safety-Glasses PPE check (/api/ppe/*) and the combined verification-session
# workflow (/api/verification-sessions/*, /api/work-orders/*/unlock).
app.include_router(ppe_router)
app.include_router(verification_router)


# --- helpers -----------------------------------------------------------------

def _require_rt(work_order_id):
    rt = sm.get(work_order_id)
    if rt is None:
        raise HTTPException(status_code=404, detail=f"Unknown work order {work_order_id}")
    return rt


def _resolve_vision(payload):
    """Turn a request body into a vision-state dict, or return None."""
    if not payload:
        return None
    if payload.get("scenario") and build_mock_state:
        return build_mock_state(payload["scenario"])
    if "objects" in payload:
        return {
            "objects": payload["objects"],
            "source": payload.get("source", "external"),
            "scenario": payload.get("scenario"),
        }
    return None


def _already_placed(rt):
    """Objects that earlier move-steps legitimately left in their target zone.

    Used so the out-of-sequence check doesn't flag a block that a previous step
    correctly placed (it stays in the assembly zone across later steps).
    """
    return {
        s["object"]
        for s in rt.steps
        if s.get("type") == "move" and s.get("step", 0) < rt.current_step
    }


def _display_source(vision):
    """Normalize the stored vision source for the frontend status label.

    -> "camera"    : posted by the Python OpenCV bridge (source=camera)
    -> "simulator" : posted by the dashboard's mock scenario buttons
    -> "none"      : no evidence received yet
    """
    raw = (vision or {}).get("source")
    if raw == "camera":
        return "camera"
    if vision and (vision.get("scenario") or raw == "mock"):
        return "simulator"
    if not vision or not vision.get("objects"):
        return "none"
    return raw or "external"


# --- endpoints ---------------------------------------------------------------

@app.get("/health")
def health():
    return {"status": "ok", "service": "locked-vision-mpi-backend"}


@app.post("/demo/reset")
def reset_demo():
    """Reset all work orders and clear the audit log for a clean re-demo."""
    sm.reset_all()
    audit.clear()
    return {"status": "ok", "message": "Demo reset. All work orders back to queued."}


@app.get("/work-orders", response_model=list[WorkOrderSummary])
def list_work_orders():
    out = []
    for wo in mes.list_work_orders():
        rt = sm.get(wo["work_order_id"])
        out.append(
            WorkOrderSummary(
                work_order_id=wo["work_order_id"],
                product=wo["product"],
                mpi_id=wo["mpi_id"],
                status=rt.status,
                current_step=rt.current_step,
                total_steps=rt.total_steps,
            )
        )
    return out


@app.post("/work-orders/{work_order_id}/start", response_model=StepResponse)
def start_work_order(work_order_id: str):
    _require_rt(work_order_id)
    # Safety gate: when PPE enforcement is enabled, the latest verification
    # session for this work order must pass BOTH PPE and the block sequence
    # before it can start. Off by default so the camera-less mock demo is
    # unaffected.
    if ppe_service.get_config()["required"]:
        if not verification_session_service.latest_session_can_open(work_order_id):
            raise HTTPException(
                status_code=403,
                detail="Work Order locked: complete PPE + block-sequence verification first.",
            )
    rt = sm.start(work_order_id)
    step = sm.current_step_def(work_order_id)
    audit.log(
        work_order_id, event="start", step=rt.current_step,
        status="in_progress", message="Work order started.",
    )
    return StepResponse(
        work_order_id=work_order_id,
        current_step=rt.current_step,
        total_steps=rt.total_steps,
        status=rt.status,
        instruction=step["instruction"] if step else "",
        step=step,
    )


@app.get("/work-orders/{work_order_id}/current-step", response_model=StepResponse)
def current_step(work_order_id: str):
    rt = _require_rt(work_order_id)
    step = sm.current_step_def(work_order_id)
    if step is None and rt.status == "awaiting_final_6s":
        instruction = "All MPI steps complete. Run the final 6S check to close the work order."
    elif step is None and rt.status == "completed":
        instruction = "Work order closed. Final 6S passed."
    elif step is None:
        instruction = "Work order not started."
    else:
        instruction = step["instruction"]
    return StepResponse(
        work_order_id=work_order_id,
        current_step=rt.current_step,
        total_steps=rt.total_steps,
        status=rt.status,
        instruction=instruction,
        step=step,
    )


@app.post("/work-orders/{work_order_id}/vision-state")
def post_vision_state(work_order_id: str, payload: dict = Body(...)):
    _require_rt(work_order_id)
    vision = _resolve_vision(payload)
    if vision is None:
        raise HTTPException(
            status_code=400,
            detail="Provide either {'objects': [...]} or {'scenario': '<name>'}.",
        )
    sm.set_vision(work_order_id, vision)
    return {
        "work_order_id": work_order_id,
        "accepted": True,
        "source": vision.get("source"),
        "scenario": vision.get("scenario"),
        "objects": vision["objects"],
    }


@app.get("/work-orders/{work_order_id}/vision-state")
def get_vision_state(work_order_id: str):
    """Latest vision evidence for the work order (polled by the frontend).

    Exposes which source last posted evidence — the Python camera bridge
    ("camera") or the dashboard's mock buttons ("simulator") — so the UI can
    show that real camera evidence arrives through the external OpenCV bridge.
    """
    rt = _require_rt(work_order_id)
    vision = rt.latest_vision or {}
    source = _display_source(vision)
    return {
        "work_order_id": work_order_id,
        "source": source,
        "camera_locked": bool(rt.camera_locked) or source == "camera",
        "objects": vision.get("objects", []),
        "scenario": vision.get("scenario"),
        "updated_at": rt.vision_updated_at,
    }


@app.post("/work-orders/{work_order_id}/validate-readiness")
def validate_readiness_endpoint(work_order_id: str, payload: dict = Body(default={})):
    """Pre-start station-readiness gate (not audit-logged; safe to poll)."""
    rt = _require_rt(work_order_id)
    vision = _resolve_vision(payload)
    if vision is not None:
        sm.set_vision(work_order_id, vision)
    result = validate_readiness(rt.latest_vision)
    return {"work_order_id": work_order_id, **result}


@app.post("/work-orders/{work_order_id}/validate-step", response_model=ValidationResponse)
def validate_current_step(work_order_id: str, payload: dict = Body(default={})):
    rt = _require_rt(work_order_id)

    # Allow vision evidence to be passed inline for convenience.
    vision = _resolve_vision(payload)
    if vision is not None:
        sm.set_vision(work_order_id, vision)

    if rt.current_step < 1:
        raise HTTPException(status_code=409, detail="Work order not started.")

    step = sm.current_step_def(work_order_id)
    if step is None:
        return ValidationResponse(
            work_order_id=work_order_id,
            current_step=rt.current_step,
            status="blocked",
            can_advance=False,
            message="All steps complete. Run the final 6S check.",
            detected_objects=rt.latest_vision.get("objects", []),
        )

    result = validate_step(step, rt.latest_vision, rt.progress, _already_placed(rt))
    audit.log(
        work_order_id, event="validate-step", step=rt.current_step,
        status=result["status"], message=result["message"],
        detected_objects=result["detected_objects"],
    )
    return ValidationResponse(
        work_order_id=work_order_id,
        current_step=rt.current_step,
        **result,
    )


@app.post("/work-orders/{work_order_id}/advance", response_model=ValidationResponse)
def advance(work_order_id: str, payload: dict = Body(default={})):
    rt = _require_rt(work_order_id)

    vision = _resolve_vision(payload)
    if vision is not None:
        sm.set_vision(work_order_id, vision)

    if rt.current_step < 1:
        raise HTTPException(status_code=409, detail="Work order not started.")

    step = sm.current_step_def(work_order_id)
    if step is None:
        return ValidationResponse(
            work_order_id=work_order_id,
            current_step=rt.current_step,
            status="blocked",
            can_advance=False,
            message="All steps complete. Run the final 6S check to close.",
            detected_objects=rt.latest_vision.get("objects", []),
        )

    # Re-validate before advancing. This is the hard gate.
    result = validate_step(step, rt.latest_vision, rt.progress, _already_placed(rt))
    if not result["can_advance"]:
        audit.log(
            work_order_id, event="advance-blocked", step=rt.current_step,
            status="blocked", message=result["message"],
            detected_objects=result["detected_objects"],
        )
        return ValidationResponse(
            work_order_id=work_order_id,
            current_step=rt.current_step,
            **result,
        )

    completed_step = rt.current_step
    audit.log(
        work_order_id, event="advance", step=completed_step,
        status="passed", message=result["message"],
        detected_objects=result["detected_objects"],
    )
    sm.advance(work_order_id)

    if rt.status == "awaiting_final_6s":
        message = (
            f"Step {completed_step} passed. All steps complete — run the final "
            f"6S check to close the work order."
        )
    else:
        next_step = sm.current_step_def(work_order_id)
        message = f"Step {completed_step} passed. Now on step {rt.current_step}: {next_step['instruction']}"

    return ValidationResponse(
        work_order_id=work_order_id,
        current_step=rt.current_step,
        status="passed",
        can_advance=False,  # must re-validate the new step
        message=message,
        detected_objects=result["detected_objects"],
    )


@app.post("/work-orders/{work_order_id}/final-6s-check", response_model=ValidationResponse)
def final_6s_check(work_order_id: str, payload: dict = Body(default={})):
    rt = _require_rt(work_order_id)

    vision = _resolve_vision(payload)
    if vision is not None:
        sm.set_vision(work_order_id, vision)

    final_cfg = mes.get_final_6s(rt.mpi_id)
    result = validate_final_6s(final_cfg, rt.latest_vision)

    if result["can_advance"]:
        rt.status = "completed"

    audit.log(
        work_order_id, event="final-6s-check", step=rt.current_step,
        status=result["status"], message=result["message"],
        detected_objects=result["detected_objects"],
    )
    return ValidationResponse(
        work_order_id=work_order_id,
        current_step=rt.current_step,
        **result,
    )


@app.get("/work-orders/{work_order_id}/audit-log")
def get_audit_log(work_order_id: str):
    _require_rt(work_order_id)
    return {"work_order_id": work_order_id, "entries": audit.read(work_order_id)}
