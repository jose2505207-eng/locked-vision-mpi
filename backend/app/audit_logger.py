"""Append-only audit log.

Every pass and every failure is recorded here. The audit log is demo
evidence, not a certified compliance record (see MAIN.md safety notes).
"""
import json
import os
from datetime import datetime, timezone

AUDIT_PATH = os.path.join(os.path.dirname(__file__), "data", "audit_log.jsonl")


class AuditLogger:
    def __init__(self, path: str = AUDIT_PATH):
        self.path = path
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        # Ensure the file exists.
        open(self.path, "a").close()

    def log(self, work_order_id, event, step=None, status=None,
            message="", detected_objects=None):
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "work_order_id": work_order_id,
            "event": event,
            "step": step,
            "status": status,
            "message": message,
            "detected_objects": detected_objects or [],
        }
        with open(self.path, "a") as f:
            f.write(json.dumps(entry) + "\n")
        return entry

    def read(self, work_order_id=None):
        entries = []
        if not os.path.exists(self.path):
            return entries
        with open(self.path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                entry = json.loads(line)
                if work_order_id is None or entry.get("work_order_id") == work_order_id:
                    entries.append(entry)
        return entries
