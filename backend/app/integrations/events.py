"""Normalized event schema for all vision / work-order events.

One shape, emitted to every enabled sponsor adapter (Redis, Arize, Orkes) AFTER
the authoritative validation has already run. Adapters consume this; they never
produce the validation decision.
"""
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from typing import Optional


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class VisionEvent:
    work_order_id: str
    event_type: str                      # e.g. "validate-step", "advance", "final-6s", "ppe-check"
    session_id: Optional[str] = None
    current_step: Optional[int] = None
    expected_block: Optional[str] = None
    detected_block: Optional[str] = None
    detected_ppe: Optional[bool] = None
    in_assembly_zone: Optional[bool] = None
    confidence: Optional[float] = None
    validation_status: Optional[str] = None   # "passed" | "blocked" | ...
    message: Optional[str] = None
    timestamp: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict:
        return asdict(self)


def build_validation_event(work_order_id, step, result, vision_state, event_type):
    """Build a normalized event from an existing validation result.

    `result` is the dict returned by the validation engine (status/message/
    detected_objects). We only READ it — the decision is already made.
    """
    objects = (vision_state or {}).get("objects", [])
    expected = None
    if step:
        expected = step.get("object") or (step.get("objects") or [None])[0]

    detected_block = None
    in_assembly = None
    confidence = None
    if expected:
        for o in objects:
            if o.get("object") == expected:
                detected_block = o.get("object")
                in_assembly = o.get("zone") == (step.get("to_zone") if step else None)
                confidence = o.get("confidence")
                break

    return VisionEvent(
        work_order_id=work_order_id,
        event_type=event_type,
        current_step=step.get("step") if step else None,
        expected_block=expected,
        detected_block=detected_block,
        in_assembly_zone=in_assembly,
        confidence=confidence,
        validation_status=result.get("status"),
        message=result.get("message"),
    )
