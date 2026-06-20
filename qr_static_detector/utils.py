from __future__ import annotations

from pathlib import Path
from typing import Iterable

import cv2
import numpy as np


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp"}


def read_image(path: str | Path) -> np.ndarray:
    """读取图片，兼容中文路径。"""
    image_path = Path(path)
    if not image_path.exists():
        raise FileNotFoundError(f"图片不存在: {image_path}")

    buffer = np.fromfile(str(image_path), dtype=np.uint8)
    image = cv2.imdecode(buffer, cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError(f"无法读取图片文件: {image_path}")
    return image


def write_image(path: str | Path, image: np.ndarray) -> None:
    """写入图片，兼容中文路径。"""
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    suffix = output_path.suffix or ".png"
    ok, encoded = cv2.imencode(suffix, image)
    if not ok:
        raise ValueError(f"图片编码失败: {output_path}")
    encoded.tofile(str(output_path))


def iter_image_files(path: str | Path) -> Iterable[Path]:
    """遍历单张图片或目录中的图片文件。"""
    source = Path(path)
    if source.is_file() and source.suffix.lower() in IMAGE_EXTENSIONS:
        yield source
        return

    if not source.is_dir():
        raise FileNotFoundError(f"输入路径不是图片或目录: {source}")

    for item in sorted(source.rglob("*")):
        if item.is_file() and item.suffix.lower() in IMAGE_EXTENSIONS:
            yield item


def safe_stem(path: str | Path) -> str:
    stem = Path(path).stem.strip() or "image"
    return "".join(ch if ch.isalnum() or ch in "-_." else "_" for ch in stem)
