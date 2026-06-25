---
name: github-handoff
description: Use this skill when preparing commits, repo structure, handoff docs, or contributor instructions for Locked Vision MPI. It maintains README.md, ARCHITECTURE.md, MAIN.md, and DEMO_SCRIPT.md, and produces a clear folder structure, setup/build/demo commands, known limitations, and next steps so the repo is public-ready and easy to pick up.
---

# GitHub Handoff

## Purpose

Make the repo public-ready and trivially easy for a contributor to clone, understand, run, and demo. Keep structure and instructions current and honest.

## When to use

- Preparing commits or organizing repo structure.
- Writing or updating handoff/onboarding docs.
- Producing contributor instructions before a handoff or end of a session.

## Inputs Claude should inspect

- `MAIN.md` (all sections — it is the source for these docs).
- Current folder structure vs. MAIN.md section 7.
- Existing `README.md`, `ARCHITECTURE.md`, `DEMO_SCRIPT.md`.
- Actual run/build commands used by backend, vision, and frontend.

## Step-by-step procedure

1. Verify the real folder structure matches MAIN.md section 7; fix drift or note it.
2. `README.md`: project summary, one-line pitch, prerequisites, setup commands, run commands (backend/vision/frontend), demo command, known limitations, next steps.
4. `ARCHITECTURE.md`: data flow and key files (coordinate with `/demo-readiness`).
5. Keep `MAIN.md` and `DEMO_SCRIPT.md` consistent with the above.
6. Document setup, build, and demo commands explicitly and test them mentally against a clean clone.
7. List known limitations honestly and concrete next steps.
8. Ensure no secrets/`.env` are committed; include `.gitignore` guidance.

## Files this skill may edit

- `README.md`
- `ARCHITECTURE.md`
- `MAIN.md`
- `DEMO_SCRIPT.md`

## Files this skill should not touch

- Backend, vision, and frontend source code. This skill handles docs, structure, and handoff — not implementation.

## Expected output

A public-ready repo with accurate docs: a clean folder structure, a `README.md` with working setup/build/demo commands, an aligned `ARCHITECTURE.md`, and clearly listed known limitations and next steps.

## Definition of done

- Folder structure matches MAIN.md (or drift is documented).
- README setup/build/demo commands work from a clean clone.
- No secrets are committed; `.gitignore` covers `.env` and snapshots if needed.
- Known limitations and next steps are listed.

## Common mistakes to avoid

- Docs that describe an idealized repo instead of the real one.
- Setup commands that were never actually run.
- Committing API keys, `.env`, or large snapshot files.
- Forgetting to list known limitations before a public push.
