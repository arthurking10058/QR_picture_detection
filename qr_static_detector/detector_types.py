from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class QRCodeDetection:
    data: str
    points: list[tuple[int, int]]
    method: str
    variant: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class DetectionDiagnostic:
    category: str
    attempted_variants: list[str]
    attempted_methods: list[str]
    fallback_stages: list[str]
    final_status: str
    dominant_failure_reason: str
    elapsed_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
