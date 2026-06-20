---
name: project-orchestrator
description: Use this skill when planning or coordinating the whole Locked Vision MPI repo, deciding what to build next, resolving cross-team questions, or checking that a change aligns with the MVP. It keeps the project aligned with the MVP, enforces the non-negotiable architecture rules, and prevents scope creep.
---

# Project Orchestrator

## Purpose

Keep Locked Vision MPI aligned with its MVP and protect the non-negotiable architecture. Use this skill to plan work, sequence tasks across the four roles, arbitrate decisions, and stop scope creep before it costs demo time.

This skill is the guardian of the core rules:

- **Fake MES is the source of truth.**
- **Vision provides evidence only.**
- **State machine validates the sequence and decides `can_advance`.**
- **Frontend must never bypass the backend.**
- **Sponsor integrations must not break the core demo.**

## When to use

- Starting the project or a new work session and deciding what to do next.
- A teammate proposes a feature and you need to judge if it's in MVP scope.
- Two roles disagree about an interface (e.g., the shape of vision state).
- You suspect scope creep, gold-plating, or a sponsor feature taking over.
- Before sequencing a sprint or assigning tasks.

## Inputs Claude should inspect

- `MAIN.md` — the project brain (sections 5, 8, 10, 11, 12 especially).
- Current folder structure vs. the structure in MAIN.md section 7.
- The relevant skill SKILL.md for whichever area is in question.
- Existing data contracts: `backend/app/models.py`, `vision/mock_vision_state.py`.

## Step-by-step procedure

1. Re-read the non-negotiable rules (MAIN.md section 5). Restate the rule relevant to the current decision.
2. Locate the request in the build order (MAIN.md section 11). Is it the next thing, or is it jumping ahead?
3. Check it against MVP scope (MAIN.md section 8). If it's "out of scope," say so and propose deferring.
4. Confirm it does not violate any architecture rule. If it does, reject the approach and offer a compliant alternative.
5. For sponsor requests, confirm the feature reinforces the MPI/manufacturing story; if not, defer it.
6. Produce a short, ordered plan: what to build, who owns it (which skill), and the data contract at the boundary.
7. Note any risk to the demo flow (MAIN.md section 9) and a mitigation.

## Files this skill may edit

- `MAIN.md` (only to refine plan, build order, scope, or role notes).
- `TEAM_ROLES.md` (ownership clarifications).
- `ARCHITECTURE.md` (high-level decisions).

## Files this skill should not touch

- Any backend, vision, frontend, or integration source code. This skill plans and coordinates; it does not implement. Delegate implementation to the role-specific skill.

## Expected output

A concise plan containing: the decision, which rule(s) it respects, where it sits in the build order, who owns it (skill), the boundary data contract, and any demo risk + mitigation. Scope-creep items are explicitly listed as "deferred."

## Definition of done

- The next action is unambiguous and assigned to a specific skill/role.
- The decision is checked against all five core rules and MVP scope.
- Scope creep and sponsor distractions are flagged and deferred.
- The demo flow remains intact.

## Common mistakes to avoid

- Letting a "cool" feature jump the build order ahead of the gated Next button.
- Approving a sponsor integration that doesn't serve the MPI story.
- Allowing any design where the frontend could decide advancement.
- Implementing code from this skill instead of delegating.
- Forgetting that mock vision must work before real vision is required.
