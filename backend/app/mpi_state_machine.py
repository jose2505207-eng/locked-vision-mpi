"""MPI state machine.

Holds the runtime state of each work order (current step, status, temporal
progress flags, and the latest vision evidence) and controls transitions.
Advancement is only ever performed by the API after the validation engine
returns can_advance=true.

Status values:
  queued            -> not started
  in_progress       -> running MPI steps
  awaiting_final_6s -> all steps passed, 6S reset not yet verified
  completed         -> final 6S passed, work order closed
"""
from datetime import datetime, timezone


class WorkOrderRuntime:
    def __init__(self, work_order, steps):
        self.work_order_id = work_order["work_order_id"]
        self.product = work_order["product"]
        self.mpi_id = work_order["mpi_id"]
        self.steps = steps
        self.total_steps = len(steps)
        self.current_step = 0  # 0 = not started
        self.status = "queued"
        self.progress = {}  # temporal flags, e.g. tool removed/returned
        self.latest_vision = {"objects": [], "source": "none"}
        self.vision_updated_at = None  # ISO timestamp of the last evidence post
        # Hybrid evidence: per-object state keyed by object name, so a camera
        # post (blocks) and a simulator post (tools/finished) don't erase each
        # other — each only updates the objects it actually carries.
        self.object_state = {}
        self.last_post_source = "none"
        self.camera_locked = False


class MPIStateMachine:
    def __init__(self, mes):
        self.mes = mes
        self.runtimes = {}
        for work_order in mes.list_work_orders():
            steps = mes.get_steps(work_order["mpi_id"])
            self.runtimes[work_order["work_order_id"]] = WorkOrderRuntime(
                work_order, steps
            )

    def get(self, work_order_id):
        return self.runtimes.get(work_order_id)

    def reset_all(self):
        """Return every work order to its initial queued state (demo reset)."""
        for work_order in self.mes.list_work_orders():
            steps = self.mes.get_steps(work_order["mpi_id"])
            self.runtimes[work_order["work_order_id"]] = WorkOrderRuntime(
                work_order, steps
            )

    def start(self, work_order_id):
        rt = self.get(work_order_id)
        rt.current_step = 1
        rt.status = "in_progress"
        rt.progress = {}
        return rt

    def current_step_def(self, work_order_id):
        rt = self.get(work_order_id)
        if rt is None or rt.current_step < 1 or rt.current_step > rt.total_steps:
            return None
        return rt.steps[rt.current_step - 1]

    def set_vision(self, work_order_id, vision):
        """Merge incoming evidence by object name (hybrid camera + simulator).

        Objects present in the post are updated; objects absent are preserved.
        This is what lets the camera stream blocks while the simulator owns
        tools/finished-assembly without either side wiping the other.
        """
        rt = self.get(work_order_id)
        now = datetime.now(timezone.utc).isoformat()
        src = vision.get("source", "external")

        for o in vision.get("objects", []):
            name = o.get("object")
            if not name:
                continue
            merged = dict(o)
            merged.setdefault("source", "simulator" if src == "mock" else src)
            merged["updated_at"] = now
            rt.object_state[name] = merged

        rt.last_post_source = src
        rt.vision_updated_at = now
        if src == "camera":
            rt.camera_locked = True

        rt.latest_vision = {
            "objects": list(rt.object_state.values()),
            "source": src,
            "scenario": vision.get("scenario"),
        }
        return rt

    def advance(self, work_order_id):
        """Move to the next step. Caller MUST have confirmed can_advance first."""
        rt = self.get(work_order_id)
        rt.current_step += 1
        if rt.current_step > rt.total_steps:
            rt.current_step = rt.total_steps + 1
            rt.status = "awaiting_final_6s"
        return rt
