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
        rt = self.get(work_order_id)
        rt.latest_vision = vision
        return rt

    def advance(self, work_order_id):
        """Move to the next step. Caller MUST have confirmed can_advance first."""
        rt = self.get(work_order_id)
        rt.current_step += 1
        if rt.current_step > rt.total_steps:
            rt.current_step = rt.total_steps + 1
            rt.status = "awaiting_final_6s"
        return rt
