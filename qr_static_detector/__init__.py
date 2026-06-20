"""QR码静态图片检测系统。"""

from .config import CATEGORY_CHOICES, CATEGORY_LABELS, REPORT_CONFIG
from .detector_types import DetectionDiagnostic
from .reporting import detection_to_legacy_dict, detections_to_legacy_dicts

__all__ = [
    "CATEGORY_CHOICES",
    "CATEGORY_LABELS",
    "REPORT_CONFIG",
    "DetectionDiagnostic",
    "QRCodeDetection",
    "QRStaticDetector",
    "detection_to_legacy_dict",
    "detections_to_legacy_dicts",
]


def __getattr__(name: str):
    if name in {"QRCodeDetection", "QRStaticDetector"}:
        from .detector import QRCodeDetection, QRStaticDetector

        exports = {
            "QRCodeDetection": QRCodeDetection,
            "QRStaticDetector": QRStaticDetector,
        }
        return exports[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
