# Environment Variables

Copy `.env.example` to `.env` and fill in only what you use. The core demo and the
verification workflow run with **none** of these set (PPE falls back to a clearly
labeled mock).

## PPE / Safety-Glasses verification

| Variable | Default | Purpose |
|---|---|---|
| `PPE_MODEL_PROVIDER` | _(auto)_ | `roboflow` (live) or `mock` (dev). Unset → `roboflow` if a key+model exist, else `mock`. |
| `ROBOFLOW_API_KEY` | _(empty)_ | Roboflow hosted inference key. Required for live PPE. |
| `ROBOFLOW_PPE_MODEL_ID` | _(empty)_ | e.g. `ppe-detection/3`. Required for live PPE. |
| `ROBOFLOW_DETECT_URL` | `https://detect.roboflow.com` | Inference base URL (override for self-host/proxy). |
| `PPE_MIN_CONFIDENCE` | `0.72` | Backend confidence threshold to accept a positive PPE label. |
| `PPE_CHECK_EXPIRATION_SECONDS` | `20` | How long a passed PPE check stays valid. |
| `PPE_REQUIRED` | `false` | `true` = block `/work-orders/{id}/start` until PPE + sequence pass. |
| `PPE_MOCK_RESULT` | `pass` | **Dev only.** What the mock provider returns: `pass` or `fail`. |

### Live vs mock

- **Live:** set `ROBOFLOW_API_KEY` + `ROBOFLOW_PPE_MODEL_ID` (and optionally
  `PPE_MODEL_PROVIDER=roboflow`). Responses carry `mode: "live"`.
- **Mock (dev):** leave the key unset or set `PPE_MODEL_PROVIDER=mock`. Every
  response carries `mode: "mock"` and a `[MOCK]` reason — never confused with
  production. If the provider resolves to `roboflow` but the key is missing,
  `/ppe-check` returns **HTTP 502** (it never fakes a pass).

## Existing app variables (already in the project)

| Variable | Default | Purpose |
|---|---|---|
| `VITE_API_URL` | `http://localhost:8000` | Frontend → backend base URL. |
| `VITE_VISION_URL` | `http://localhost:8010` | Frontend → vision bridge feed (camera UI). |

## How `.env` is loaded

`backend/app/main.py` auto-loads the repo-root `.env` at startup (a small,
dependency-free loader), so `uvicorn app.main:app` picks up secrets like
`ROBOFLOW_API_KEY` **without** needing an `--env-file` flag. Real environment
variables always win over the file (the loader uses `setdefault`). Edit `.env`,
restart the backend, and the new values apply.

```bash
cp .env.example .env          # then fill in your keys
cd backend && uvicorn app.main:app --reload --port 8000
```

## Going live with Roboflow

Live PPE requires **both** values:

```env
ROBOFLOW_API_KEY=...            # your Roboflow private API key
ROBOFLOW_PPE_MODEL_ID=...       # e.g. workspace/ppe-detection/3
```

With only the key set, the provider auto-resolves to **mock** (graceful) instead
of erroring. Set the model id to flip to live (`mode: "live"` in responses).

## Where they're read

- PPE/sequence config: `backend/app/safety_config.py` (`ppe_config()` and
  `REQUIRED_BLOCK_SEQUENCE`). This is the single source — re-read per request, so
  editing `.env` and restarting is enough.
- Secrets live in `.env` (gitignored). **Never commit real keys.**
