# Demo Script — Locked Vision MPI

**Total time:** ~3 minutes. **Anchor line (say it first):**

> "This is not a camera watching a table. This is **visual proof connected to
> manufacturing execution.** The MPI only moves forward when the real world is
> correct."

---

## Setup (before judges arrive)

```bash
# Terminal 1
cd backend && source .venv/bin/activate && uvicorn app.main:app --port 8000
# Terminal 2
cd frontend && npm run dev
```

Open http://localhost:5173. Confirm "backend online" (green dot). The camera-less
demo is driven by the **Vision Simulator** buttons in the camera panel (each posts
mock vision evidence). For a physical demo, replace those with real camera pushes
(`vision/` README) — the backend behaves identically.

---

## The 4 key moments

### 1. Station readiness passes
- Click **Station ready (all home)**.
- The **Station Readiness** panel goes all-green: backend online, camera locked,
  calibration in tolerance, zones clear → **✓ STATION READY**.
- *Say:* "The station is calibrated and the camera is locked to a golden view.
  If the camera moved, we'd refuse to start."

### 2. Correct step passes
- Click **▶ Start Work Order** on WO-1001. Step 1 shows: *Move the RED block to
  the ASSEMBLY ZONE.* Next is **🔒 LOCKED**.
- Click **Red → assembly**, then **Verify Step (check vision)**.
- Banner turns green, gate reads **✓ Verified**, **NEXT STEP →** unlocks.
- Click **NEXT STEP →**. Now on step 2.
- *Say:* "The button was physically locked until the camera proved the red block
  was actually in the assembly zone."

### 3. Wrong sequence is blocked
- On step 2 (or restart at step 1 to make it crisp), click **Wrong move (blue
  first)**, then **Verify Step**.
- Loud red banner: *"Out of sequence: blue_block is in assembly_zone, but step N
  requires …"*. Next stays **🔒 LOCKED**. The failure appears in the **Audit Log**.
- *Say:* "Wrong part, wrong order — the system blocks it and logs it as evidence.
  No skipping, no faking the click."
- Recover: post the correct scenario, Verify, advance.

### 4. Final 6S blocks close until tools are returned
- Drive to the end (Blue → assembly; **Tool 1 removed** → blocked → **Tool 1
  returned** → pass; Yellow → assembly; **Finished → complete**; Next).
- The Final 6S panel appears. Click **6S: tool missing** → **Run Final 6S Check**
  → blocked: *"tool_1 must be returned to tool_1_home."*
- Click **6S: all home** → **Run Final 6S Check** → **✅ WORK ORDER CLOSED**.
- *Say:* "The work order cannot close until the station is reset — tools home,
  parts home, assembly clear. 6S enforced by vision."

---

## If something glitches (recovery)

- **Frontend error banner / backend offline:** restart Terminal 1; the dot goes
  green; state is in-memory so just re-Start the work order.
- **Wrong state shown:** click the matching Vision Simulator button to re-post
  evidence, then **Verify Step** — the backend is stateless about the *button*,
  it only trusts the last posted evidence.
- **Total fallback:** run `backend/smoke_test.py` live — it walks the entire
  flow (start → block → pass → tool → 6S → closed) and prints PASS/FAIL for each
  of the four moments.

---

## One-line close

> "MES is the source of truth, the camera is the evidence, and the work order
> only moves when the real world is correct. That's Locked Vision MPI."
