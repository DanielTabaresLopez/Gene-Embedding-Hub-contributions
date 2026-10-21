"""Bounded retries keyed by both the submitted data and trusted validator code."""
from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


def validator_fingerprint(root: str | Path = ".") -> str:
    root = Path(root)
    paths = []
    for folder, pattern in (("gene_registry", "*.py"), ("schemas", "*.json"),
                            ("config", "*.yaml"), ("scripts", "*.py"),
                            (".github/workflows", "*.yml")):
        paths.extend((root / folder).glob(pattern))
    digest = hashlib.sha256()
    for path in sorted(paths):
        digest.update(path.relative_to(root).as_posix().encode() + b"\0")
        digest.update(path.read_bytes() + b"\0")
    return digest.hexdigest()[:20]


def marker(kind: str, head: str, version: str, outcome: str = "") -> str:
    suffix = f":{outcome}" if outcome else ""
    return f"<!-- geh-{kind}:v2:{version}:{head}{suffix} -->"


def retry_decision(events: list[dict[str, Any]], head: str, version: str,
                   now: datetime | None = None) -> tuple[bool, str]:
    now = now or datetime.now(timezone.utc)
    for event in events:
        content = event["content"]
        if any(marker("processed", head, version, outcome) in content
               for outcome in ("PUBLISHED", "REJECTED")):
            return False, "this revision has a final result from the current validator"
    attempts = [e for e in events if marker("dispatched", head, version) in e["content"]]
    if len(attempts) >= 3:
        return False, "three attempts reached; inspect the run logs and retry manually"
    if attempts:
        timestamp = attempts[-1].get("created_at")
        if isinstance(timestamp, str):
            try:
                timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            except ValueError:
                timestamp = None
        if not isinstance(timestamp, datetime):
            return False, "pending dispatch has no readable timestamp; inspect manually"
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)
        # The publish job has a five-hour timeout. Do not queue a second writer
        # while that job could still be running.
        if now - timestamp < timedelta(hours=6):
            return False, "a dispatch is still within its six-hour retry window"
    return True, "new revision/validator or retryable interrupted attempt"
