---
name: code-review
description: Use this skill before commits and before the demo to review Locked Vision MPI for rule violations and demo-killing bugs. It checks that the backend enforces can_advance, that the frontend cannot bypass validation, that hardcoded values are documented, that sponsor integrations are isolated, that the demo path is clear, and that setup instructions are complete. Output is a short list of blockers, risks, and quick fixes.
---

# Code Review

## Purpose

Catch rule violations and demo-killing bugs before they reach a commit or the stage. This review is focused and ruthless: protect the core rules and the demo path.

## When to use

- Before any commit.
- Before the demo and before the final submission.
- After a large change to the backend, frontend, or integrations.

## Inputs Claude should inspect

- `MAIN.md` sections 5 (rules), 9 (demo flow), 12 (DoD).
- Backend: `validation_engine.py`, `mpi_state_machine.py`, `audit_logger.py`, `main.py`.
- Frontend: `MPIStepPanel.jsx`, `api.js`, `Final6SCheckPanel.jsx`.
- `integrations/` for isolation.
- `README.md` for setup completeness.

## Step-by-step procedure

1. **Backend enforces `can_advance`?** Verify it is set only by the validation engine and only when evidence matches the expected step.
2. **Frontend bypass?** Verify the Next button is disabled unless `can_advance=true` and there is no client-side override; verify Close is blocked until final 6S.
3. **Audit log?** Verify every pass and failure is logged.
4. **Final 6S gate?** Verify closure is impossible until all parts/tools are home.
5. **Hardcoded values?** Verify magic numbers (zone coords, color thresholds, ports) are documented or in config/data files.
6. **Sponsor isolation?** Verify integrations are removable and don't touch flow/validation.
7. **Demo path?** Verify the four demo beats run end to end.
8. **Demo-killing errors?** Look for unhandled exceptions, missing endpoints, CORS issues, camera failures with no fallback.
9. **Setup complete?** Verify README commands work from a clean clone.

## Files this skill may edit

- None by default — this skill reports. With explicit user approval it may apply small, clearly-scoped quick fixes, then hand back to the owning skill.

## Files this skill should not touch

- It should not silently rewrite backend, vision, frontend, or integration logic. Findings go to the owning skill for implementation unless the user approves an inline quick fix.

## Expected output

A short review with three sections:
- **Blockers** — must fix before commit/demo (rule violations, demo-killers).
- **Risks** — could fail live; mitigate if time allows.
- **Quick fixes** — small, safe improvements with exact location.

## Definition of done

- All five core rules are explicitly checked.
- The four demo beats are confirmed or flagged.
- Each finding names the file/line and a concrete fix.
- Blockers are clearly separated from nice-to-haves.

## Common mistakes to avoid

- Generic style nitpicking instead of protecting the rules and the demo.
- Missing a frontend path that enables Next without `can_advance`.
- Overlooking missing audit entries on failures.
- Approving sponsor code that quietly couples to validation.
- Passing a build where README setup doesn't actually run.
