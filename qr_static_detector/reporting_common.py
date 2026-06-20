from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Iterable

from .config import REPORT_CONFIG
from .detector_types import QRCodeDetection


def configure_matplotlib_chinese(plt_module) -> bool:
    try:
        from matplotlib import font_manager
    except Exception:
        return False

    preferred_fonts = list(REPORT_CONFIG.preferred_fonts)
    available = {font.name for font in font_manager.fontManager.ttflist}
    chosen = next((font for font in preferred_fonts if font in available), None)
    if not chosen:
        return False

    plt_module.rcParams["font.sans-serif"] = [chosen, *preferred_fonts]
    plt_module.rcParams["axes.unicode_minus"] = False
    return True


def detection_to_legacy_dict(detection: QRCodeDetection) -> dict[str, object]:
    xs = [point[0] for point in detection.points]
    ys = [point[1] for point in detection.points]
    return {
        "data": detection.data,
        "type": "QRCODE",
        "method": detection.method,
        "variant": detection.variant,
        "rect": {
            "x": min(xs),
            "y": min(ys),
            "w": max(xs) - min(xs),
            "h": max(ys) - min(ys),
        },
        "polygon": detection.points,
    }


def detections_to_legacy_dicts(detections: Iterable[QRCodeDetection]) -> list[dict[str, object]]:
    return [detection_to_legacy_dict(detection) for detection in detections]


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding=REPORT_CONFIG.csv_encoding, newline="") as file:
        return list(csv.DictReader(file))


def read_optional_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    return read_csv_rows(path)


def write_csv_rows(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        return
    with path.open("w", encoding=REPORT_CONFIG.csv_encoding, newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def read_json_dict(path: Path) -> dict[str, object]:
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding=REPORT_CONFIG.json_encoding))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def read_optional_json_list(path: Path) -> list[dict[str, object]]:
    if not path.is_file():
        return []
    try:
        payload = json.loads(path.read_text(encoding=REPORT_CONFIG.json_encoding))
    except Exception:
        return []
    return payload if isinstance(payload, list) else []


def write_json_file(path: Path, payload: object) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding=REPORT_CONFIG.json_encoding,
    )


def read_summary_run_meta(path: Path) -> dict[str, object]:
    payload = read_json_dict(path)
    run_meta = payload.get("run_meta")
    if isinstance(run_meta, dict):
        return run_meta
    return payload


def safe_float(value: object) -> float:
    if value in ("", None):
        return 0.0
    return float(value)


def extract_meta_text(meta: dict[str, object], key: str) -> str:
    value = meta.get(key, "")
    return str(value) if value is not None else ""


def build_report_dir(output_dir: Path, name: str) -> Path:
    report_dir = output_dir / name
    if not report_dir.exists():
        try:
            report_dir.mkdir(parents=True, exist_ok=True)
        except PermissionError:
            return output_dir
    return report_dir


def ensure_output_dir(path: Path) -> Path | None:
    if path.exists():
        return path
    try:
        path.mkdir(parents=True, exist_ok=True)
    except PermissionError:
        return None
    return path
