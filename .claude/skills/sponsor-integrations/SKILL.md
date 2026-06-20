---
name: sponsor-integrations
description: Use this skill when adding sponsor-related features (Fetch AI, Sentry, Redis, Deepgram, Arize) without corrupting the main product. It scaffolds isolated integrations under integrations/, documents them in SPONSOR_INTEGRATIONS.md, and enforces that every sponsor feature supports the manufacturing/MPI story and never breaks the core demo.
---

# Sponsor Integrations

## Purpose

Add sponsor integrations that strengthen the prize story **without** touching or destabilizing the core MPI demo. Every integration lives in its own folder under `integrations/`, is optional, and can be removed with zero impact on the core flow.

## When to use

- Scaffolding or editing a sponsor integration (Fetch agent, Sentry, Redis, Deepgram, Arize).
- Deciding whether a sponsor feature is worth adding.
- Documenting the sponsor/prize mapping.

## Inputs Claude should inspect

- `MAIN.md` sections 5 (rules) and 10 (prize strategy).
- `SPONSOR_INTEGRATIONS.md` (if present).
- The backend API surface (integrations consume it; they do not bypass it).

## Step-by-step procedure

1. Confirm the integration reinforces the manufacturing/MPI story. If not, defer it (escalate to `/project-orchestrator`).
2. Create an isolated folder under `integrations/<sponsor>/` with its own README and config.
3. Keep all keys in environment variables / `.env`; never commit secrets.
4. Scaffold each integration as additive and removable:
   - `integrations/fetch_agent/` — Fetch AI supervisor agent scaffold that observes MES/audit state and narrates/supervises the MPI.
   - `integrations/sentry/` — error monitoring wrapper for backend/frontend.
   - `integrations/redis/` — station memory placeholder (e.g., last-known station state).
   - `integrations/deepgram/` — voice placeholder for operator prompts.
   - `integrations/arize/` — optional observability of validation decisions.
5. Ensure each integration consumes the backend API; none of them decides `can_advance` or bypasses validation.
6. Update `SPONSOR_INTEGRATIONS.md`: what each integration does, which prize it targets, how it ties to the MPI story, and how to disable it.
7. Verify the core demo still runs with every integration turned off.

## Files this skill may edit

- `integrations/fetch_agent/` (and contents)
- `integrations/sentry/` (and contents)
- `integrations/redis/` (and contents)
- `integrations/deepgram/` (and contents)
- `integrations/arize/` (and contents)
- `SPONSOR_INTEGRATIONS.md`

## Files this skill should not touch

- Core backend logic (`mpi_state_machine.py`, `validation_engine.py`, `audit_logger.py`), `vision/` detection logic, and core frontend flow components.
- It may add thin, optional hooks but must never make the core demo depend on a sponsor.

## Expected output

Isolated, documented, removable sponsor integration scaffolds that each reinforce the MPI story, plus an up-to-date `SPONSOR_INTEGRATIONS.md` mapping integrations to prizes.

## Definition of done

- Each integration lives in its own `integrations/<sponsor>/` folder.
- The core demo runs unchanged with all integrations disabled.
- No integration decides flow or bypasses validation.
- No secrets are committed; all keys come from env vars.
- `SPONSOR_INTEGRATIONS.md` maps each integration to a prize and to the MPI story.

## Common mistakes to avoid

- Letting a sponsor feature become a hard dependency of the core demo.
- Adding a flashy feature that doesn't serve the manufacturing story.
- Committing API keys or `.env` files.
- Wiring a sponsor integration into validation or `can_advance`.
- Spending build time here before the core demo (sections 11) is solid.
