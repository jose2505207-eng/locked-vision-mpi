"""MES Supervisor Agent — Fetch AI scaffold.

A supervisory agent that drives the Locked Vision MPI backend the same way an
operator (or another agent) would. It calls the backend HTTP API only — it
never bypasses validation, and it does not decide can_advance itself. The
backend remains the source of truth.

Capabilities (Fetch "Best Use of Fetch AI" track):
  * start a work order
  * check the current step
  * validate the current step against the latest vision evidence
  * run the final 6S check
  * summarize the audit log

Run as a plain client (works today):
    pip install requests
    python mes_supervisor_agent.py

Deploy to Agentverse / expose on ASI:One: wrap the methods below in a uAgents
protocol (see the TODO block at the bottom). The business logic does not change.
"""
import os

try:
    import requests
except ImportError:  # pragma: no cover
    requests = None

BACKEND_URL = os.getenv("MES_BACKEND_URL", "http://localhost:8000")


class MESSupervisor:
    def __init__(self, backend_url: str = BACKEND_URL):
        self.backend_url = backend_url.rstrip("/")
        if requests is None:
            raise RuntimeError("Install requests: pip install requests")

    def _post(self, path, body=None):
        r = requests.post(f"{self.backend_url}{path}", json=body or {})
        r.raise_for_status()
        return r.json()

    def _get(self, path):
        r = requests.get(f"{self.backend_url}{path}")
        r.raise_for_status()
        return r.json()

    # --- capabilities --------------------------------------------------------

    def start_work_order(self, work_order_id: str):
        return self._post(f"/work-orders/{work_order_id}/start")

    def check_current_step(self, work_order_id: str):
        return self._get(f"/work-orders/{work_order_id}/current-step")

    def validate_step(self, work_order_id: str, vision=None):
        """Validate the current step. vision may be {'scenario': ...} or
        {'objects': [...]}; if omitted, the backend uses its latest evidence."""
        return self._post(f"/work-orders/{work_order_id}/validate-step", vision)

    def run_final_6s(self, work_order_id: str, vision=None):
        return self._post(f"/work-orders/{work_order_id}/final-6s-check", vision)

    def summarize_audit_log(self, work_order_id: str) -> str:
        entries = self._get(f"/work-orders/{work_order_id}/audit-log")["entries"]
        passed = sum(1 for e in entries if e["status"] == "passed")
        blocked = sum(1 for e in entries if e["status"] == "blocked")
        lines = [
            f"Audit summary for {work_order_id}: "
            f"{len(entries)} events, {passed} passed, {blocked} blocked.",
        ]
        for e in entries[-5:]:
            lines.append(f"  - [{e['status']}] step {e['step']}: {e['message']}")
        summary = "\n".join(lines)
        # TODO(anthropic): for the Anthropic track, send `entries` to Claude for a
        # natural-language root-cause explanation of any blocked steps.
        return summary


def _demo():
    sup = MESSupervisor()
    wo = "WO-1001"
    print(sup.start_work_order(wo)["instruction"])
    print(sup.validate_step(wo, {"scenario": "step1_done"})["message"])
    print(sup.summarize_audit_log(wo))


if __name__ == "__main__":
    _demo()


# -----------------------------------------------------------------------------
# TODO(fetch): Agentverse / ASI:One deployment.
#
# from uagents import Agent, Context, Model
#
# class StepRequest(Model):
#     work_order_id: str
#     scenario: str | None = None
#
# agent = Agent(name="mes_supervisor", seed=os.getenv("AGENT_SEED", "mes-seed"))
# sup = MESSupervisor()
#
# @agent.on_message(model=StepRequest)
# async def on_validate(ctx: Context, sender: str, msg: StepRequest):
#     result = sup.validate_step(msg.work_order_id,
#                                {"scenario": msg.scenario} if msg.scenario else None)
#     await ctx.send(sender, ... )
#
# if __name__ == "__main__":
#     agent.run()
# -----------------------------------------------------------------------------
