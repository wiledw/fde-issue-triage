"""Append-only audit trail: one JSONL file per run.

Every prompt, model response (including summarized thinking), tool call, tool
result, guardrail action, and error is written as it happens, so a run that
crashes halfway still leaves a readable record.
"""

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path


def dump(obj):
    """Best-effort JSON-able form of SDK objects, dataclasses, and plain data."""
    if hasattr(obj, "model_dump"):
        return obj.model_dump(mode="json")
    if isinstance(obj, (list, tuple)):
        return [dump(o) for o in obj]
    if isinstance(obj, dict):
        return {k: dump(v) for k, v in obj.items()}
    if hasattr(obj, "__dict__"):
        return {k: dump(v) for k, v in vars(obj).items()}
    return obj


class AuditLog:
    def __init__(self, log_dir: str | Path, run_id: str | None = None):
        self.run_id = run_id or f"{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}-{uuid.uuid4().hex[:6]}"
        self.path = Path(log_dir) / f"{self.run_id}.jsonl"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._seq = 0

    def write(self, event: str, **data) -> None:
        self._seq += 1
        record = {
            "ts": datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
            "run_id": self.run_id,
            "seq": self._seq,
            "event": event,
            **{k: dump(v) for k, v in data.items()},
        }
        with self.path.open("a") as f:
            f.write(json.dumps(record, default=str) + "\n")
