"""Risk severity levels and scores."""
from __future__ import annotations

from enum import IntEnum


class Severity(IntEnum):
    LOW = 0
    MODERATE = 1
    HIGH = 2
    SEVERE = 3
    NO_TRAVEL = 4

    @property
    def label(self) -> str:
        return self.name

    @classmethod
    def parse(cls, name: str) -> Severity:
        return cls[name.upper()]
