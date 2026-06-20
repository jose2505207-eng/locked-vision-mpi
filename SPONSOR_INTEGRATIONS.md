# Sponsor Integrations & Prize Strategy

**Guiding rule:** every integration must support the manufacturing / MPI story,
and **no integration may break or become a dependency of the core demo.** The
locked camera + fake MES + visual gating runs with all integrations disabled.

---

## Primary — Best Physical AI Hack

This *is* the project. A physical, locked camera supervises a real workstation
of LEGO blocks and tools. The MPI literally cannot advance unless the physical
world matches the instruction, and the work order cannot close until the station
is physically reset (6S). Visual proof is wired directly into manufacturing
execution. **This is the headline.**

---

## Best Use of Fetch AI — MES Supervisor Agent

`integrations/fetch_agent/mes_supervisor_agent.py`

An agent that operates the workstation through the gated backend API:

- start a work order
- check the current step
- validate the current step against vision evidence
- run the final 6S check
- summarize the audit log

It acts as a digital line supervisor and **never bypasses validation** — its own
actions are audit-logged. Runnable today as a plain client; a `TODO(fetch)` block
shows the Agentverse / ASI:One `uagents` wrapper.

---

## Best Use of Anthropic — built with Claude Code

This entire repo — the project "brain" (`MAIN.md`), the `.claude/skills/` system,
the backend, vision, frontend, and integrations — was scaffolded with **Claude
Code**. Eight project skills (`/backend-mes`, `/vision-camera`, `/frontend-ui`,
`/sponsor-integrations`, `/demo-readiness`, `/code-review`, `/github-handoff`,
`/project-orchestrator`) encode and enforce the architecture rules.

**Runtime use:** `MESSupervisor.summarize_audit_log()` has a `TODO(anthropic)`
hook to send audit entries to Claude for natural-language root-cause explanations
of blocked steps ("Step 3 blocked because tool_1 never returned home").

---

## Best Use of Sentry — live error monitoring

`integrations/sentry/`. The backend initializes Sentry **only if** `SENTRY_DSN`
is set (`backend/app/main.py`), so it is fully isolated. Monitors backend,
frontend, and vision so a demo-killing exception is caught and explained in real
time — the reliability an MES demands.

---

## Best Use of Deepgram — hands-free operator voice (optional)

`integrations/deepgram/`. An operator's hands are on the parts, not the keyboard.
Speech-to-text maps "verify" / "next" / "reset" to the same API calls as the
buttons. Voice is a way to *request* advancement — never to bypass the gate.

---

## Best Use of Redis — real-time station memory (optional)

`integrations/redis/`. Station state (current step, latest vision) in Redis
hashes, the audit log as a Redis Stream other services/agents can tail, and an
MPI lookup cache. JSON files stay the source of truth, so the demo never depends
on Redis being up.

---

## Best Use of Arize / Terac — vision evaluation & labeling (optional)

`integrations/arize/`. Log every detection (object, zone, confidence) vs.
operator-confirmed outcome to measure precision/recall, zone-mapping accuracy,
and drift; route low-confidence snapshots for labeling. Trust-but-verify for the
evidence layer.

---

## Isolation checklist

- [ ] Core demo runs with **all** integrations disabled.
- [ ] No integration sets `can_advance` or bypasses validation.
- [ ] All API keys come from `.env` (see `.env.example`); none committed.
- [ ] Each integration maps to a prize **and** to the MPI story above.
