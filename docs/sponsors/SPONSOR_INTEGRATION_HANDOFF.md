# Sponsor Integration Handoff — PPE & Future Services

This explains where external/sponsor APIs plug into the verification workflow and
how to swap or add providers **without touching frontend logic** and **without
moving the decision out of the backend**.

## Golden rule

> Sponsor-powered services return **evidence / predictions**. The **backend**
> remains the final decision-maker.

A model may say "goggles 0.91". It does **not** unlock anything. The backend's
`ppe_service.decide()` applies the policy (allowed labels + confidence threshold)
and `verification_session_service` combines it with the block sequence to compute
`can_open_work_order`. Keep it that way.

## Where the PPE model plugs in

```
backend/app/ppe_service.py
    get_config()        -> reads provider + keys from safety_config
    call_roboflow()     -> live provider call (returns raw predictions)
    _mock_predictions() -> labeled development fallback
    run_check()         -> picks provider, returns predictions + mode
    decide()            -> THE BACKEND DECISION (do not move into a provider)
```

`run_check()` selects the provider via `PPE_MODEL_PROVIDER`:

- `roboflow` → live call (needs `ROBOFLOW_API_KEY` + `ROBOFLOW_PPE_MODEL_ID`)
- `mock` → labeled dev predictions (`mode: "mock"`, reason prefixed `[MOCK]`)
- unset → auto: `roboflow` if a key+model exist, else `mock`

## How to replace the PPE provider

1. Add a function in `ppe_service.py`, e.g. `call_<provider>(image_bytes, cfg)`
   that returns a list of predictions in the normalized shape:
   ```json
   [ { "class": "safety_glasses", "confidence": 0.91, "x": 0, "y": 0, "width": 0, "height": 0 } ]
   ```
2. Branch on it in `run_check()`:
   ```python
   if cfg["provider"] == "myprovider":
       predictions = call_myprovider(image_bytes, cfg)
   ```
3. Add any keys to `safety_config.ppe_config()` and `.env.example`.
4. **Do not** change `decide()` semantics or any route/frontend code. The contract
   the frontend sees (`/api/verification-sessions/{id}/ppe-check`) stays identical.

Map your provider's labels onto the existing policy sets in `ppe_service.py`
(`POSITIVE_CLASSES`, `NEGATIVE_CLASSES`) — that's where "what counts as verified"
lives.

## How to add future sponsor integrations

Keep them **isolated** and **evidence-only**, mirroring the existing
`integrations/` scaffolds (Fetch, Sentry, Redis, Deepgram, Arize). For a new
verification-adjacent service:

1. Put provider code in `integrations/<sponsor>/` (isolated, optional).
2. Expose a thin `call_*()` that returns evidence/predictions.
3. Wire it behind an env-selected provider in the relevant `*_service.py`.
4. Persist evidence (predictions JSON, confidence, image/URL) like `ppe_checks`.
5. Let `verification_session_service` (or the relevant backend service) make the
   decision. Never return `can_open_work_order` from a sponsor service.

This keeps the demo working when a sponsor key is absent (auto-mock) and means
the frontend never needs to know which provider is active.

## Environment variables

See `docs/setup/ENVIRONMENT_VARIABLES.md`. PPE-relevant:

- `PPE_MODEL_PROVIDER` — `roboflow` | `mock` | (unset = auto)
- `ROBOFLOW_API_KEY`, `ROBOFLOW_PPE_MODEL_ID`, `ROBOFLOW_DETECT_URL`
- `PPE_MIN_CONFIDENCE` (default 0.72), `PPE_CHECK_EXPIRATION_SECONDS` (default 20)
- `PPE_MOCK_RESULT` — dev only: `pass` | `fail`

## Checklist for sponsor owners

- [ ] Provider returns predictions only (class, confidence, bbox, raw JSON).
- [ ] Keys read from env via `safety_config` — nothing hardcoded, nothing committed.
- [ ] Absent key → clean labeled mock, never a silent production "pass".
- [ ] Backend `decide()` unchanged; `can_open_work_order` still backend-only.
- [ ] Frontend contract unchanged.
