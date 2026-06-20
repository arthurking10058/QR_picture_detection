from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np


@dataclass(frozen=True)
class ImageVariant:
    name: str
    image: np.ndarray
    scale_x: float = 1.0
    scale_y: float = 1.0


def to_gray(image: np.ndarray) -> np.ndarray:
    if len(image.shape) == 2:
        return image
    return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)


def resize_for_detection(image: np.ndarray, max_side: int = 1600) -> tuple[np.ndarray, float, float]:
    """限制最大边长，提升批量处理速度并避免超大图耗时。"""
    height, width = image.shape[:2]
    largest = max(height, width)
    if largest <= max_side:
        return image, 1.0, 1.0
    scale = max_side / largest
    resized = cv2.resize(image, (int(width * scale), int(height * scale)), interpolation=cv2.INTER_AREA)
    return resized, width / resized.shape[1], height / resized.shape[0]


def clahe_enhance(gray: np.ndarray) -> np.ndarray:
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    return clahe.apply(gray)


def sharpen(image: np.ndarray) -> np.ndarray:
    kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]], dtype=np.float32)
    return cv2.filter2D(image, -1, kernel)


def adaptive_threshold(gray: np.ndarray) -> np.ndarray:
    return cv2.adaptiveThreshold(
        gray,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        35,
        5,
    )


def denoise(gray: np.ndarray) -> np.ndarray:
    return cv2.medianBlur(gray, 3)


def build_variants(image: np.ndarray) -> list[ImageVariant]:
    """生成多种预处理结果，增强低对比度、噪声和轻微模糊场景的识别能力。"""
    resized, scale_x, scale_y = resize_for_detection(image)
    gray = to_gray(resized)
    enhanced = clahe_enhance(gray)
    blurred = denoise(enhanced)

    return [
        ImageVariant("original", resized, scale_x, scale_y),
        ImageVariant("gray", gray, scale_x, scale_y),
        ImageVariant("clahe", enhanced, scale_x, scale_y),
        ImageVariant("denoise", blurred, scale_x, scale_y),
        ImageVariant("threshold", adaptive_threshold(blurred), scale_x, scale_y),
        ImageVariant("sharpen", sharpen(resized), scale_x, scale_y),
    ]
