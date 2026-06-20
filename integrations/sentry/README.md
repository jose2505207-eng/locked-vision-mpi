# Sentry — Error Monitoring

**Track:** Best Use of Sentry API.

## Why it fits

A live demo dies on an unhandled exception. Sentry watches the backend, vision,
and frontend so we catch (and explain) failures in real time — exactly the kind
of reliability a manufacturing execution system needs.

## Backend wiring (already present, opt-in)

`backend/app/main.py` initializes Sentry **only if** `SENTRY_DSN` is set:

```bash
pip install sentry-sdk
export SENTRY_DSN="https://...@sentry.io/..."
uvicorn app.main:app --port 8000
```

With no DSN set, the backend runs normally — the integration is fully isolated.

## Frontend wiring (optional)

```bash
npm install @sentry/react
# in src/main.jsx:
# import * as Sentry from "@sentry/react";
# Sentry.init({ dsn: import.meta.env.VITE_SENTRY_DSN });
```

## Vision wiring (optional)

Wrap the capture/detection loop and report exceptions with
`sentry_sdk.capture_exception(e)` so camera/calibration failures are visible.
