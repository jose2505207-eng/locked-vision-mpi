# Fetch AI — MES Supervisor Agent

**Track:** Best Use of Fetch AI.

A supervisory agent that operates the Locked Vision MPI workstation through the
backend API. It can:

- **start** a work order
- **check** the current MPI step
- **validate** the current step against vision evidence
- run the **final 6S** check
- **summarize** the audit log

## Why it fits the project

The agent is a digital line supervisor. It never overrides the rules — it calls
the same gated API a human uses, so the MES stays the source of truth and the
agent's actions are themselves audit-logged. This shows physical-AI supervision
without weakening the core demo.

## Run (plain client, works now)

```bash
pip install requests
MES_BACKEND_URL=http://localhost:8000 python mes_supervisor_agent.py
```

## Deploy to Agentverse / ASI:One

See the `TODO(fetch)` block at the bottom of `mes_supervisor_agent.py`: wrap the
`MESSupervisor` methods in a `uagents` protocol and publish. The logic is
unchanged; only the transport differs.

## Isolation

This integration is additive. If it is removed, the core demo is unaffected.
