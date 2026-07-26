from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class Check:
    check_id: str
    status: str  # PASS, WARNING, FAIL, INFO
    message: str
    value: Any = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ValidationResult:
    outcome: str
    checks: list[Check] = field(default_factory=list)
    summary: dict[str, Any] = field(default_factory=dict)
    provenance: dict[str, Any] = field(default_factory=dict)

    def add(self, check_id: str, status: str, message: str, value: Any = None) -> None:
        self.checks.append(Check(check_id, status, message, value))

    def to_dict(self) -> dict[str, Any]:
        return {
            "outcome": self.outcome,
            "checks": [c.to_dict() for c in self.checks],
            "summary": self.summary,
            "provenance": self.provenance,
        }
