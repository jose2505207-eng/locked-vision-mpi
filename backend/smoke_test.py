"""End-to-end smoke test of the WO-1001 flow using FastAPI TestClient.

Run from repo root:  backend/.venv/bin/python -m backend.smoke_test
or:                  cd backend && .venv/bin/python smoke_test.py
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from backend.app.main import app

c = TestClient(app)
WO = "WO-1001"
fails = []


def check(label, cond, extra=""):
    status = "PASS" if cond else "FAIL"
    print(f"[{status}] {label} {extra}")
    if not cond:
        fails.append(label)


# health
r = c.get("/health").json()
check("health ok", r["status"] == "ok")

# list
r = c.get("/work-orders").json()
check("WO-1001 listed queued", r[0]["work_order_id"] == WO and r[0]["status"] == "queued")

# start
r = c.post(f"/work-orders/{WO}/start").json()
check("started on step 1", r["current_step"] == 1 and r["status"] == "in_progress")

# wrong sequence is blocked
r = c.post(f"/work-orders/{WO}/validate-step", json={"scenario": "wrong_sequence"}).json()
check("wrong sequence blocked", r["status"] == "blocked" and r["can_advance"] is False, f"-> {r['message']}")

# advance attempt while blocked must NOT move
r = c.post(f"/work-orders/{WO}/advance").json()
check("advance blocked when not satisfied", r["can_advance"] is False and r["current_step"] == 1)

# correct step 1
r = c.post(f"/work-orders/{WO}/validate-step", json={"scenario": "step1_done"}).json()
check("step 1 passes", r["status"] == "passed" and r["can_advance"] is True)
r = c.post(f"/work-orders/{WO}/advance").json()
check("advanced to step 2", r["current_step"] == 2)

# step 2
c.post(f"/work-orders/{WO}/vision-state", json={"scenario": "step2_done"})
r = c.post(f"/work-orders/{WO}/validate-step").json()
check("step 2 passes (vision posted separately)", r["can_advance"] is True)
c.post(f"/work-orders/{WO}/advance")

# step 3 red: blocked until red joins green+blue in assembly, then passes
r = c.post(f"/work-orders/{WO}/validate-step", json={"scenario": "step2_done"}).json()
check("step 3 blocked without red", r["can_advance"] is False, f"-> {r['message']}")
r = c.post(f"/work-orders/{WO}/validate-step", json={"scenario": "step3_done"}).json()
check("step 3 passes (green+blue+red in assembly)", r["can_advance"] is True, f"-> {r['message']}")
# cumulative regression: move GREEN back out -> step 3 must now FAIL
r = c.post(f"/work-orders/{WO}/validate-step",
           json={"objects": [{"object": "green_block", "zone": "green_home"}], "source": "camera"}).json()
check("step 3 fails when green moved back out (cumulative)", r["can_advance"] is False, f"-> {r['message']}")
# restore and advance
c.post(f"/work-orders/{WO}/validate-step", json={"scenario": "step3_done"})
c.post(f"/work-orders/{WO}/advance")

# step 4: all four in assembly passes; moving one out fails (cumulative)
r = c.post(f"/work-orders/{WO}/validate-step", json={"scenario": "step4_done"}).json()
check("step 4 passes (all four in assembly)", r["can_advance"] is True)
r = c.post(f"/work-orders/{WO}/validate-step",
           json={"objects": [{"object": "blue_block", "zone": "blue_home"}], "source": "camera"}).json()
check("step 4 fails when blue moved back out (cumulative)", r["can_advance"] is False, f"-> {r['message']}")
c.post(f"/work-orders/{WO}/validate-step", json={"scenario": "step4_done"})
c.post(f"/work-orders/{WO}/advance")

# step 5: all four blocks in complete_zone passes (no finished_assembly object)
r = c.post(f"/work-orders/{WO}/validate-step", json={"scenario": "step5_done"}).json()
check("step 5 passes (all four in complete_zone)", r["can_advance"] is True, f"-> {r['message']}")
r = c.post(f"/work-orders/{WO}/advance").json()
check("awaiting final 6S after step 5", "6S" in r["message"])

# final 6S: a block left in the assembly zone blocks close (blocks-only check)
r = c.post(f"/work-orders/{WO}/final-6s-check", json={"scenario": "step1_done"}).json()
check("final 6S blocked when assembly not clear", r["can_advance"] is False, f"-> {r['message']}")

# final 6S pass closes
r = c.post(f"/work-orders/{WO}/final-6s-check", json={"scenario": "final_6s_pass"}).json()
check("final 6S passes and closes", r["can_advance"] is True)
r = c.get("/work-orders").json()
check("WO status completed", r[0]["status"] == "completed")

# audit log captured passes and failures
entries = c.get(f"/work-orders/{WO}/audit-log").json()["entries"]
has_blocked = any(e["status"] == "blocked" for e in entries)
has_passed = any(e["status"] == "passed" for e in entries)
check("audit log has blocked + passed entries", has_blocked and has_passed,
      f"({len(entries)} entries)")

print()
if fails:
    print(f"SMOKE TEST FAILED: {len(fails)} check(s) failed: {fails}")
    sys.exit(1)
print("SMOKE TEST PASSED — full WO-1001 flow works on mock vision.")
