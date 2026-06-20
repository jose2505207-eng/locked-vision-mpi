# Redis — Real-time Station Memory

**Track:** Best Use of Redis.

## Why it fits

The workstation has live state: current step, latest vision evidence, and a
stream of audit events. Redis gives us fast shared memory and a real-time event
stream that other services (the Fetch agent, a wallboard, a second station) can
subscribe to.

## Planned usage (placeholder)

- **Station memory:** `HSET station:WO-1001 current_step 3 status in_progress`
- **Latest vision:** `SET vision:WO-1001 <json>` with a short TTL.
- **Audit stream:** `XADD audit:WO-1001 * event validate-step status passed ...`
  so dashboards/agents tail the log via `XREAD`.
- **MPI retrieval cache:** cache `mpi_steps.json` lookups.

## Wiring sketch

```bash
pip install redis
export REDIS_URL="redis://localhost:6379/0"
```

Add a thin `redis_store.py` that the backend's `audit_logger` and state machine
*also* write to. Keep it optional: if `REDIS_URL` is unset, skip it. The JSON
files remain the source of truth so the demo never depends on Redis being up.
