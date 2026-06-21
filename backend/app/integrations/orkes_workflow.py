"""Orkes Conductor SHADOW workflow mirror.

Mirrors the backend's authoritative MPI state into a Conductor workflow so the
flow is observable in Orkes. The backend ALWAYS remains the source of truth —
this never gates a step. The shadow stage map is maintained in-memory and always
works; pushing to a real Conductor server is best-effort and fully optional.

Workflow stages:
  start_work_order -> verify_ppe -> step_green -> step_blue -> step_red
  -> step_yellow -> final_zone_check -> complete_work_order
"""
import logging
import os
import uuid

from . import sponsor_flags

log = logging.getLogger("sponsors")

# Per work-order shadow state: run_id, ordered stages reached, orkes connectivity.
_runs = {}

# Cumulative step (green,blue,red,yellow) -> workflow stage name.
_STEP_STAGE = {1: "step_green", 2: "step_blue", 3: "step_red", 4: "step_yellow"}


def _stage_for(data: dict):
    et = data.get("event_type")
    status = data.get("validation_status")
    step = data.get("current_step")
    if et == "ppe-check":
        return "verify_ppe"
    if et == "advance" and status == "passed":
        return _STEP_STAGE.get(step)
    if et == "final-6s":
        return "complete_work_order" if status == "passed" else "final_zone_check"
    return None


def _push_to_conductor(run: dict, stage: str, data: dict) -> None:
    """Best-effort real Orkes update. Guarded; failure just marks not-connected."""
    try:
        from conductor.client.configuration.configuration import Configuration  # lazy
        from conductor.client.orkes_clients import OrkesClients
        conf = Configuration(
            server_api_url=os.getenv("ORKES_SERVER_URL"),
            authentication_settings=None,
        )
        conf.update_token(os.getenv("ORKES_KEY_ID"), os.getenv("ORKES_KEY_SECRET"))
        clients = OrkesClients(configuration=conf)
        wf_client = clients.get_workflow_client()
        if run.get("orkes_run_id") is None:
            run["orkes_run_id"] = wf_client.start_workflow_by_name(
                "locked_vision_mpi", {"work_order_id": data.get("work_order_id")}
            )
        run["orkes_connected"] = True
    except Exception as e:
        run["orkes_connected"] = False
        log.warning("[orkes] conductor push failed (soft, shadow only): %s", e)


def mirror_event(data: dict) -> None:
    """Advance the shadow workflow from a normalized event. Never raises."""
    if not sponsor_flags.active("orkes_shadow"):
        return
    try:
        wo = data.get("work_order_id")
        if not wo:
            return
        run = _runs.setdefault(wo, {
            "run_id": f"shadow-{uuid.uuid4().hex[:12]}",
            "orkes_run_id": None,
            "orkes_connected": False,
            "stages": ["start_work_order"],
        })
        stage = _stage_for(data)
        if stage and stage not in run["stages"]:
            run["stages"].append(stage)
            log.info("[orkes] shadow %s -> %s", wo, stage)
            _push_to_conductor(run, stage, data)
    except Exception as e:  # pragma: no cover
        log.warning("[orkes] mirror_event failed (soft): %s", e)


def get_status(work_order_id: str = None) -> dict:
    """Shadow status for /api/sponsors/status (or a single work order)."""
    if work_order_id:
        return _runs.get(work_order_id, {"stages": [], "run_id": None})
    return {"enabled": sponsor_flags.is_enabled("orkes_shadow"),
            "active": sponsor_flags.active("orkes_shadow"),
            "tracked_work_orders": list(_runs.keys())}
