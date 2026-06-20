# Frontend — Fake MES Dashboard

Vite + React dashboard. High-contrast, manufacturing-themed, readable from 6
feet. The Next Step button is **disabled unless the backend returns
`can_advance=true`** — there is no client-side override.

## Run

```bash
cd frontend
npm install
npm run dev        # http://localhost:5173
```

The backend must be running on `http://localhost:8000` (override with
`VITE_API_URL`).

## Layout

- **Left:** Work Order Queue + Start button · Station Readiness.
- **Center:** Status banner (loud red/green) · Current MPI Step + gated Next
  button · Final 6S panel · Detected Objects.
- **Right:** Locked Camera / Vision Simulator · Audit Log.

## Vision Simulator (camera-less demo)

Since the camera is optional for the dashboard demo, the camera panel includes
buttons that POST mock vision evidence (`vision/mock_vision_state.py` scenarios)
to the backend. Typical demo run:

1. `Station ready (all home)` → readiness goes green.
2. Start WO-1001. Try `Wrong move (blue first)` → **Verify Step** → blocked, red banner, Next stays locked.
3. `Red → assembly` → **Verify Step** → green → **Next Step**.
4. Continue: Blue, Tool removed (blocked) → Tool returned (pass), Yellow, Finished.
5. Final 6S: `6S: tool missing` → blocked. `6S: all home` → **Work Order Closed**.

## Non-negotiables enforced here

- Next is `disabled` whenever `validation.can_advance !== true`.
- Advancing clears the verification — the new step must be re-verified.
- Close is impossible until the backend confirms final 6S.
- Validation is never computed in the browser; the backend decides.
