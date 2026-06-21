"""Cumulative step-validation tests (block-only demo).

Runs the pure validation engine against the REAL mpi_steps.json sequence, so it
verifies the actual rules the app uses. Every step must validate the full
required state up to itself (not just the current block), and step 5 checks all
four blocks in complete_zone — no synthetic finished_assembly object.

Run:  cd backend && ../.venv/bin/python tests/test_step_validation.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.validation_engine import validate_step  # noqa: E402

_STEPS = json.load(open(os.path.join(
    os.path.dirname(__file__), "..", "app", "data", "mpi_steps.json"
)))["MPI-LEGO-001"]["steps"]

HOMES = {
    "green_block": "green_home", "blue_block": "blue_home",
    "red_block": "red_home", "yellow_block": "yellow_home",
}

_fails = []


def _vision(**placed):
    """Vision state for all four blocks; kwargs override a block's zone."""
    objs = []
    for name, home in HOMES.items():
        objs.append({"object": name, "zone": placed.get(name, home),
                     "bbox": None, "confidence": 1.0})
    return {"objects": objs, "source": "camera"}


def _step(n):
    return _STEPS[n - 1]


def check(name, got_pass, want_pass):
    ok = bool(got_pass) == want_pass
    if not ok:
        _fails.append(name)
    print(f"[{'PASS' if ok else 'FAIL'}] {name} (want {'PASS' if want_pass else 'FAIL'}, "
          f"got {'PASS' if got_pass else 'FAIL'})")


def run(step_no, vision):
    r = validate_step(_step(step_no), vision, {}, all_steps=_STEPS)
    return r["can_advance"], r["message"]


# --- the cases from the spec -------------------------------------------------
A = "assembly_zone"
C = "complete_zone"

# Step 3: green+blue in assembly but red outside => FAIL
p, m = run(3, _vision(green_block=A, blue_block=A))
check("step3 green+blue only (red home) => FAIL", p, False)

# Step 3: green+blue+red in assembly => PASS
p, m = run(3, _vision(green_block=A, blue_block=A, red_block=A))
check("step3 green+blue+red => PASS", p, True)

# Step 3 core bug: all three placed but GREEN moved back out => FAIL
p, m = run(3, _vision(green_block="green_home", blue_block=A, red_block=A))
check("step3 with green moved back out => FAIL", p, False)

# Step 3: yellow placed too early => FAIL
p, m = run(3, _vision(green_block=A, blue_block=A, red_block=A, yellow_block=A))
check("step3 yellow placed too early => FAIL", p, False)

# Step 4: all four in assembly => PASS
p, m = run(4, _vision(green_block=A, blue_block=A, red_block=A, yellow_block=A))
check("step4 all four in assembly => PASS", p, True)

# Step 4: one (blue) moved out => FAIL (cumulative)
p, m = run(4, _vision(green_block=A, blue_block="blue_home", red_block=A, yellow_block=A))
check("step4 blue moved out => FAIL", p, False)

# Step 5: all four in complete_zone => PASS
p, m = run(5, _vision(green_block=C, blue_block=C, red_block=C, yellow_block=C))
check("step5 all four in complete => PASS", p, True)

# Step 5: three in complete, one (yellow) outside => FAIL
p, m = run(5, _vision(green_block=C, blue_block=C, red_block=C, yellow_block="yellow_home"))
check("step5 three in complete, yellow out => FAIL", p, False)

# Step 1: blue placed first (green expected) => FAIL (too early)
p, m = run(1, _vision(blue_block=A))
check("step1 blue placed first => FAIL", p, False)

print()
if _fails:
    print(f"STEP VALIDATION FAILED: {_fails}")
    sys.exit(1)
print("ALL STEP-VALIDATION TESTS PASSED")
