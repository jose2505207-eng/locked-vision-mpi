# Integrations — Sponsor Tracks (isolated & additive)

Every integration here is **optional** and **isolated**. The core demo runs with
all of them disabled. Each one must reinforce the manufacturing / MPI story —
nothing here is allowed to distract from the physical-AI demo.

| Folder | Sponsor track | Status | Ties to the story |
|---|---|---|---|
| `fetch_agent/` | Best Use of Fetch AI | Scaffold (runnable client) | Agent supervises the MPI via the gated API |
| `sentry/` | Best Use of Sentry | Placeholder + wiring note | Catches demo-killing errors live |
| `redis/` | Best Use of Redis | Placeholder | Real-time station memory + audit stream |
| `deepgram/` | Best Use of Deepgram | Placeholder | Hands-free operator voice commands |
| `arize/` | Best Use of Arize / Terac | Placeholder | Evaluate vision detections + label loop |

See `../SPONSOR_INTEGRATIONS.md` for the full prize strategy and how each
integration maps to the demo. Keep all API keys in environment variables / a
local `.env` — never commit secrets.
