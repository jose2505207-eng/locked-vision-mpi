"""Sentry error monitoring for FastAPI — behind ENABLE_SENTRY + SENTRY_DSN.

Fail-soft: if the flag is off, the DSN is missing, or sentry-sdk is not
installed, this is a no-op and the app starts normally.
"""
import logging
import os

from . import sponsor_flags

log = logging.getLogger("sponsors")


def init_sentry() -> bool:
    """Initialize Sentry if active. Returns True if initialized."""
    if not sponsor_flags.is_enabled("sentry"):
        log.info("[sentry] disabled (flag off)")
        return False
    dsn = os.getenv("SENTRY_DSN")
    if not dsn:
        log.warning("[sentry] enabled but SENTRY_DSN missing — staying inactive")
        return False
    try:
        import sentry_sdk
        sentry_sdk.init(
            dsn=dsn,
            traces_sample_rate=float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.2")),
            environment=os.getenv("SENTRY_ENV", "demo"),
        )
        log.info("[sentry] initialized (FastAPI)")
        return True
    except ImportError:
        log.warning("[sentry] sentry-sdk not installed (`pip install sentry-sdk`) — inactive")
        return False
    except Exception as e:  # pragma: no cover - must never break startup
        log.warning("[sentry] init failed (soft, ignored): %s", e)
        return False
