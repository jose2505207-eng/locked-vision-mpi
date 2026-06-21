"""Redis live event bus (SHADOW). Publishes normalized events to channels for
any live dashboard/consumer. This is NOT the audit log — SQLite + the in-memory
state machine remain authoritative. If Redis is down or the SDK is missing, we
log once and the demo continues.

Channels:
  lockedvision.events                       (firehose)
  lockedvision.session.{session_id}         (if the event carries a session)
  lockedvision.workorder.{work_order_id}    (per work order)
"""
import json
import logging
import os

from . import sponsor_flags

log = logging.getLogger("sponsors")

_client = None
_warned = False  # so a down Redis logs once, not every event


def _get_client():
    global _client
    if _client is not None:
        return _client
    import redis  # lazy import — only when actually publishing
    url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    _client = redis.Redis.from_url(
        url, socket_connect_timeout=1, socket_timeout=1, decode_responses=True
    )
    return _client


def publish_event(data: dict) -> None:
    """Publish a normalized event to the bus. Never raises."""
    if not sponsor_flags.active("redis_events"):
        return
    global _warned
    try:
        client = _get_client()
        payload = json.dumps(data, default=str)
        client.publish("lockedvision.events", payload)
        if data.get("session_id"):
            client.publish(f"lockedvision.session.{data['session_id']}", payload)
        if data.get("work_order_id"):
            client.publish(f"lockedvision.workorder.{data['work_order_id']}", payload)
        if _warned:
            log.info("[redis] reconnected — publishing resumed")
            _warned = False
    except Exception as e:
        if not _warned:
            log.warning("[redis] publish failed (soft, demo continues): %s", e)
            _warned = True


def connection_status() -> dict:
    """Live ping for /api/sponsors/status. Never raises."""
    enabled = sponsor_flags.is_enabled("redis_events")
    if not sponsor_flags.active("redis_events"):
        return {"enabled": enabled, "connected": False,
                "reason": "inactive (flag off or REDIS_URL missing)"}
    try:
        _get_client().ping()
        return {"enabled": True, "connected": True, "url": os.getenv("REDIS_URL")}
    except Exception as e:
        return {"enabled": True, "connected": False, "error": str(e)}
