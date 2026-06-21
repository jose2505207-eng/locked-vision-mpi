"""Sponsor-stack safety smoke tests.

Proves the sacred rule: with sponsors off (or failing) the demo behaves exactly
as before, and no sponsor adapter can break a request.

Run:  cd backend && ../.venv/bin/python tests/test_sponsor_stack.py
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Start from a clean, all-OFF flag state.
for _k in ("ENABLE_SPONSOR_STACK", "ENABLE_SENTRY", "ENABLE_REDIS_EVENTS",
           "ENABLE_ORKES_SHADOW", "ENABLE_CLAUDE_ASSIST", "ENABLE_ARIZE_LOGGING",
           "ENABLE_DEEPGRAM_VOICE", "ENABLE_RUNPOD_DETECTOR"):
    os.environ[_k] = "false"

from app import ppe_store  # noqa: E402
ppe_store.DB_PATH = tempfile.mktemp(suffix="-sponsor-test.db")

from starlette.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402

client = TestClient(app, raise_server_exceptions=True)
_fails = []


def check(name, cond, extra=""):
    if not cond:
        _fails.append(name)
    print(f"[{'PASS' if cond else 'FAIL'}] {name}{(' -> ' + extra) if extra else ''}")


def _drive_to_step5():
    client.post("/demo/reset")
    client.post("/work-orders/WO-1001/start")
    for sc in ["step1_done", "step2_done", "step3_done", "step4_done"]:
        client.post("/work-orders/WO-1001/vision-state", json={"scenario": sc})
        client.post("/work-orders/WO-1001/advance")


# 1. App starts with all flags false; status reports everything inactive.
s = client.get("/api/sponsors/status").json()
check("1. starts with all flags false", s["sponsor_stack_enabled"] is False
      and not any(s["badges"].values()))

# 2. Existing validation still blocks wrong / out-of-zone blocks.
client.post("/demo/reset")
client.post("/work-orders/WO-1001/start")
r = client.post("/work-orders/WO-1001/validate-step", json={"scenario": "wrong_sequence"}).json()
check("2. wrong/early block still BLOCKED", r["can_advance"] is False, r["message"])
r = client.post("/work-orders/WO-1001/validate-step", json={"scenario": "step1_done"}).json()
check("2b. correct block still PASSES", r["can_advance"] is True)

# 3. Final completion still requires ALL four blocks in complete_zone.
_drive_to_step5()
three = {"objects": [
    {"object": "green_block", "zone": "complete_zone"},
    {"object": "blue_block", "zone": "complete_zone"},
    {"object": "red_block", "zone": "complete_zone"},
    {"object": "yellow_block", "zone": "yellow_home"}], "source": "camera"}
r = client.post("/work-orders/WO-1001/validate-step", json=three).json()
check("3. final BLOCKED with only 3 in complete", r["can_advance"] is False, r["message"])
r = client.post("/work-orders/WO-1001/validate-step", json={"scenario": "step5_done"}).json()
check("3b. final PASSES with all 4 in complete", r["can_advance"] is True)

# 4. Sponsor adapter failure (Redis down) does NOT block the demo.
os.environ["ENABLE_SPONSOR_STACK"] = "true"
os.environ["ENABLE_REDIS_EVENTS"] = "true"
os.environ["REDIS_URL"] = "redis://localhost:6399/0"  # nothing listening
client.post("/demo/reset")
client.post("/work-orders/WO-1001/start")
r = client.post("/work-orders/WO-1001/validate-step", json={"scenario": "step1_done"}).json()
check("4. redis DOWN does not break validate-step", r["status"] == "passed")
os.environ["ENABLE_REDIS_EVENTS"] = "false"
os.environ["ENABLE_SPONSOR_STACK"] = "false"

# 5. Claude fallback works with no key.
r = client.post("/api/assistant/operator-instruction",
                json={"message": "Step blocked: move the green block into the assembly zone.",
                      "validation_status": "blocked", "expected_block": "green_block"}).json()
check("5. claude fallback with missing key", r["source"] == "fallback" and "green" in r["instruction"])

# 6. A failing sponsor sink never propagates out of emit().
os.environ["ENABLE_SPONSOR_STACK"] = "true"
os.environ["ENABLE_ARIZE_LOGGING"] = "true"
os.environ["ARIZE_SPACE_KEY"] = "x"
os.environ["ARIZE_API_KEY"] = "y"  # arize SDK not installed -> sink raises internally
from app.integrations import sponsor_bus               # noqa: E402
from app.integrations.events import VisionEvent          # noqa: E402
raised = False
try:
    sponsor_bus.emit(VisionEvent(work_order_id="WO-1001", event_type="smoke-test"))
except Exception:
    raised = True
check("6. failing sponsor sink does not raise", raised is False)
os.environ["ENABLE_ARIZE_LOGGING"] = "false"
os.environ["ENABLE_SPONSOR_STACK"] = "false"

# 7. Voice intent recognition is local and never needs Deepgram.
r = client.post("/api/voice/command", json={"text": "verify step"}).json()
check("7. voice intent local (no deepgram)", r["intent"] == "verify_step")

print()
if _fails:
    print(f"SPONSOR SMOKE TESTS FAILED: {_fails}")
    sys.exit(1)
print("ALL SPONSOR SMOKE TESTS PASSED")
