"""Central feature-flag + key-presence registry for the sponsor stack.

ENABLE_SPONSOR_STACK is a master kill-switch: when false, EVERY sponsor feature
is off regardless of its individual flag. This guarantees a single, reliable way
to run the pure demo. Individual flags then enable specific adapters.

Nothing here imports a sponsor SDK or touches the network — it only reads env.
"""
import logging
import os

log = logging.getLogger("sponsors")

_TRUTHY = ("1", "true", "yes", "on")


def _bool(name: str, default: str = "false") -> bool:
    return os.getenv(name, default).strip().lower() in _TRUTHY


def master_enabled() -> bool:
    return _bool("ENABLE_SPONSOR_STACK")


# Individual feature flags. A feature is active only if the master switch AND its
# own flag are on (so ENABLE_SPONSOR_STACK=false reliably disables everything).
_FEATURE_FLAGS = {
    "sentry": "ENABLE_SENTRY",
    "redis_events": "ENABLE_REDIS_EVENTS",
    "orkes_shadow": "ENABLE_ORKES_SHADOW",
    "claude_assist": "ENABLE_CLAUDE_ASSIST",
    "arize_logging": "ENABLE_ARIZE_LOGGING",
    "deepgram_voice": "ENABLE_DEEPGRAM_VOICE",
    "runpod_detector": "ENABLE_RUNPOD_DETECTOR",
}

# Env keys each feature needs to actually function (for "configured" reporting).
_FEATURE_KEYS = {
    "sentry": ["SENTRY_DSN"],
    "redis_events": ["REDIS_URL"],
    "orkes_shadow": ["ORKES_SERVER_URL", "ORKES_KEY_ID", "ORKES_KEY_SECRET"],
    "claude_assist": ["ANTHROPIC_API_KEY"],
    "arize_logging": ["ARIZE_SPACE_KEY", "ARIZE_API_KEY"],
    "deepgram_voice": ["DEEPGRAM_API_KEY"],
    "runpod_detector": ["RUNPOD_API_KEY", "RUNPOD_ENDPOINT_ID"],
}


def is_enabled(feature: str) -> bool:
    """True only if the master switch and the feature's own flag are both on."""
    flag = _FEATURE_FLAGS.get(feature)
    return bool(flag) and master_enabled() and _bool(flag)


def keys_configured(feature: str) -> bool:
    """True if every env key the feature needs is present and non-empty."""
    return all(os.getenv(k) for k in _FEATURE_KEYS.get(feature, []))


def missing_keys(feature: str) -> list:
    return [k for k in _FEATURE_KEYS.get(feature, []) if not os.getenv(k)]


def active(feature: str) -> bool:
    """The honest state used everywhere: enabled by flags AND keys present.

    If a flag is on but keys are missing, the feature reports INACTIVE rather
    than crashing — exactly the 'show inactive, never crash' rule.
    """
    return is_enabled(feature) and keys_configured(feature)


def snapshot() -> dict:
    """Full state for /api/sponsors/status — flags, keys, and effective active."""
    features = {}
    for feature, flag in _FEATURE_FLAGS.items():
        features[feature] = {
            "flag": flag,
            "flag_enabled": _bool(flag),
            "keys_configured": keys_configured(feature),
            "missing_keys": missing_keys(feature),
            "active": active(feature),
        }
    return {
        "sponsor_stack_enabled": master_enabled(),
        "features": features,
    }
