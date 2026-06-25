---
name: demo-readiness
description: Use this skill when preparing the demo, pitch, README, or architecture doc. It creates/maintains DEMO_SCRIPT.md, README.md, and ARCHITECTURE.md, and keeps the pitch sharp and the four demo beats reliable.
---

# Demo Readiness

## Purpose

Make Locked Vision MPI demo-ready. Keep the pitch sharp, the run-of-show tight, and the four key demo beats reliable.

Pitch anchor:
> "This is not a camera watching a table. This is visual proof connected to manufacturing execution. The MPI only moves forward when the real world is correct."

## When to use

- Writing or updating the demo script, README, or architecture doc.
- Doing a demo dry run and hardening the flow.

## Inputs Claude should inspect

- `MAIN.md` sections 9 (demo flow), 11 (DoD), 12 (safety).
- Current backend endpoints and frontend state (to keep docs accurate).
- Any existing `README.md`, `ARCHITECTURE.md`.

## Step-by-step procedure

1. Confirm the four demo beats work end to end:
   1. Station readiness passes.
   2. Correct step passes (`can_advance=true`, Next enables).
   3. Wrong sequence is blocked (Next stays disabled, error fires, failure logged).
   4. Final 6S blocks close until the tool/part is returned.
2. Write/refresh `DEMO_SCRIPT.md`: exact run-of-show, who clicks/moves what, expected on-screen result, and recovery steps if something glitches.
3. Write/refresh `README.md`: what it is, setup, run commands (backend, vision, frontend), and the one-line pitch.
4. Write/refresh `ARCHITECTURE.md`: the data flow (MES truth → state machine → can_advance; vision = evidence; audit log) and key files.
5. Time the demo; trim anything that doesn't land in the first 10 seconds.
6. List known limitations and a fallback path (e.g., snapshot mode if the live camera fails).

## Files this skill may edit

- `DEMO_SCRIPT.md`
- `README.md`
- `ARCHITECTURE.md`

## Files this skill should not touch

- Backend, vision, and frontend source code. This skill documents and rehearses; it does not implement. Route code fixes to the owning skill.

## Expected output

A complete, accurate set of demo docs: a tight `DEMO_SCRIPT.md` covering the four beats with recovery steps, a clean `README.md` with working run commands, and an accurate `ARCHITECTURE.md`.

## Definition of done

- All four demo beats are scripted and verified to work.
- README run commands work from a clean clone.
- The pitch anchor is present and the story lands in 10 seconds.
- A fallback path exists for live-camera failure.
- Known limitations are documented honestly.

## Common mistakes to avoid

- Documenting features that don't actually work yet.
- A demo script with no recovery/fallback for camera or backend hiccups.
- Burying the pitch; the "visual proof connected to MES" line must lead.
- Letting docs drift from the real endpoints and commands.
- Over-running on time — the four beats must fit the slot.
