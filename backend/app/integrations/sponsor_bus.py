"""Event dispatcher — fans a normalized VisionEvent out to every ACTIVE sponsor
sink (Redis, Arize, Orkes shadow). Every sink call is independently wrapped so a
failure in one (or all) can never affect the caller or the demo.

This is called by the backend AFTER the authoritative validation has run.
"""
import importlib
import logging

from . import sponsor_flags

log = logging.getLogger("sponsors")

# feature flag -> (module, function) within this package.
_SINKS = [
    ("redis_events", "redis_event_bus", "publish_event"),
    ("arize_logging", "arize_logger", "log_event"),
    ("orkes_shadow", "orkes_workflow", "mirror_event"),
]


def emit(event) -> None:
    """Fan `event` out to active sinks. Never raises."""
    if not sponsor_flags.master_enabled():
        return
    data = event.to_dict() if hasattr(event, "to_dict") else dict(event)
    for feature, module_name, func_name in _SINKS:
        if not sponsor_flags.active(feature):
            continue
        try:
            mod = importlib.import_module(f"{__package__}.{module_name}")
            getattr(mod, func_name)(data)
        except Exception as e:  # pragma: no cover - defensive, demo must continue
            log.warning("[sponsors] %s sink failed (soft, ignored): %s", feature, e)
