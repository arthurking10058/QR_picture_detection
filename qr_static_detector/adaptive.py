from __future__ import annotations

import cv2
import numpy as np

from .config import PREPROCESS_CONFIG


def apply_clahe(gray: np.ndarray, clip_limit: float = 2.0, grid_size: tuple[int, int] = (8, 8)) -> np.ndarray:
    clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=grid_size)
    return clahe.apply(gray)


def apply_unsharp_mask(gray: np.ndarray, sigma: float = 1.5, strength: float = 1.5) -> np.ndarray:
    blurred = cv2.GaussianBlur(gray, (0, 0), sigma)
    return cv2.addWeighted(gray, 1 + strength, blurred, -strength, 0)


def apply_gamma(gray: np.ndarray, gamma: float) -> np.ndarray:
    table = np.array([((i / 255.0) ** gamma) * 255 for i in range(256)], dtype=np.uint8)
    return cv2.LUT(gray, table)


def apply_adaptive_threshold(gray: np.ndarray, block_size: int = 11, c: int = 2) -> np.ndarray:
    return cv2.adaptiveThreshold(
        gray,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        block_size,
        c,
    )


def apply_morphological_close(gray: np.ndarray, kernel_size: int = 3) -> np.ndarray:
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (kernel_size, kernel_size))
    return cv2.morphologyEx(gray, cv2.MORPH_CLOSE, kernel)


def apply_morphological_open(gray: np.ndarray, kernel_size: int = 3) -> np.ndarray:
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (kernel_size, kernel_size))
    return cv2.morphologyEx(gray, cv2.MORPH_OPEN, kernel)


def apply_sauvola(gray: np.ndarray, window_size: int = 25, k: float = 0.2) -> np.ndarray:
    gray_f = gray.astype(np.float64)
    mean = cv2.blur(gray_f, (window_size, window_size))
    sq_mean = cv2.blur(gray_f**2, (window_size, window_size))
    std = np.sqrt(np.maximum(sq_mean - mean**2, 0))
    threshold = mean * (1.0 + k * (std / 128.0 - 1.0))
    return ((gray_f > threshold) * 255).astype(np.uint8)


def apply_bilateral_filter(gray: np.ndarray, d: int = 9, sigma_color: int = 75, sigma_space: int = 75) -> np.ndarray:
    return cv2.bilateralFilter(gray, d, sigma_color, sigma_space)


def apply_otsu(gray: np.ndarray) -> np.ndarray:
    _, otsu = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return otsu


def apply_dilate(gray: np.ndarray, kernel_size: int = 2, iterations: int = 1) -> np.ndarray:
    kernel = np.ones((kernel_size, kernel_size), np.uint8)
    return cv2.dilate(gray, kernel, iterations=iterations)


def apply_erode(gray: np.ndarray, kernel_size: int = 2, iterations: int = 1) -> np.ndarray:
    kernel = np.ones((kernel_size, kernel_size), np.uint8)
    return cv2.erode(gray, kernel, iterations=iterations)


def _resize_gray(gray: np.ndarray, max_dim: int) -> np.ndarray:
    height, width = gray.shape[:2]
    cur_max = max(height, width)
    if cur_max <= max_dim:
        return gray
    scale = max_dim / cur_max
    return cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)


def _preprocess_nominal(image: np.ndarray) -> list[np.ndarray]:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    return [apply_clahe(gray), gray, apply_clahe(gray, clip_limit=3.0)]


def _preprocess_blurred(image: np.ndarray) -> list[np.ndarray]:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    sharp2 = apply_unsharp_mask(gray, sigma=2.0, strength=2.0)
    sharp1 = apply_unsharp_mask(gray, sigma=1.0, strength=1.5)
    sharp3 = apply_unsharp_mask(gray, sigma=3.0, strength=2.5)
    bilateral = apply_bilateral_filter(gray)
    return [
        apply_clahe(sharp2),
        apply_clahe(sharp1),
        apply_clahe(sharp3),
        apply_clahe(bilateral),
        apply_clahe(apply_unsharp_mask(bilateral, sigma=2.0, strength=2.0)),
        apply_sauvola(sharp2, 25, 0.2),
        apply_otsu(gray),
        apply_dilate(gray),
        apply_erode(gray),
    ]


def _preprocess_bright_spots(image: np.ndarray) -> list[np.ndarray]:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, PREPROCESS_CONFIG.bright_spots_kernel)
    blackhat = cv2.morphologyEx(gray, cv2.MORPH_BLACKHAT, kernel)
    corrected = cv2.subtract(gray, blackhat)
    return [
        apply_clahe(corrected),
        apply_clahe(gray),
        apply_clahe(corrected, clip_limit=3.0),
        apply_sauvola(apply_clahe(corrected), 25, 0.2),
        apply_otsu(gray),
        apply_dilate(gray),
        apply_erode(gray),
    ]


def _preprocess_brightness(image: np.ndarray) -> list[np.ndarray]:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    dark = apply_gamma(gray, PREPROCESS_CONFIG.gamma_values[0])
    bright = apply_gamma(gray, PREPROCESS_CONFIG.gamma_values[1])
    return [apply_clahe(dark), apply_clahe(bright), apply_clahe(gray)]


def _preprocess_close(image: np.ndarray) -> list[np.ndarray]:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    candidates: list[np.ndarray] = []
    for dim in PREPROCESS_CONFIG.close_resize_dims:
        resized = _resize_gray(gray, dim)
        candidates.append(resized)
        candidates.append(apply_clahe(resized))
    return candidates


def _preprocess_curved(image: np.ndarray) -> list[np.ndarray]:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    clahe = apply_clahe(gray, clip_limit=3.0)
    clahe4 = apply_clahe(gray, clip_limit=4.0)
    sharp = apply_unsharp_mask(gray, sigma=1.5, strength=2.0)
    return [
        clahe,
        *[apply_adaptive_threshold(clahe, block_size, c) for block_size, c in PREPROCESS_CONFIG.curved_threshold_params],
        apply_clahe(sharp),
        apply_adaptive_threshold(clahe4, *PREPROCESS_CONFIG.curved_threshold_params[0]),
        apply_sauvola(clahe, *PREPROCESS_CONFIG.sauvola_default),
        apply_sauvola(clahe, *PREPROCESS_CONFIG.sauvola_curved_alt),
        apply_otsu(clahe),
        apply_otsu(gray),
        apply_dilate(gray),
        apply_erode(gray),
    ]


def _preprocess_damaged(image: np.ndarray) -> list[np.ndarray]:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    clahe = apply_clahe(gray)
    candidates: list[np.ndarray] = []
    for dim in PREPROCESS_CONFIG.damaged_resize_dims:
        candidates.append(_resize_gray(clahe, dim))
    for dim in PREPROCESS_CONFIG.damaged_threshold_dims:
        resized = _resize_gray(clahe, dim)
        candidates.append(apply_adaptive_threshold(resized, 21, 3))
    for dim in PREPROCESS_CONFIG.damaged_extra_threshold_dims:
        resized = _resize_gray(clahe, dim)
        candidates.append(apply_adaptive_threshold(resized, 31, 5))
    closed = apply_morphological_close(clahe, 3)
    candidates.append(closed)
    candidates.append(apply_adaptive_threshold(closed, 21, 3))
    opened = apply_morphological_open(clahe, 3)
    candidates.append(apply_adaptive_threshold(opened, 21, 3))
    candidates.append(apply_sauvola(clahe, *PREPROCESS_CONFIG.sauvola_default))
    for dim in PREPROCESS_CONFIG.damaged_extra_threshold_dims:
        candidates.append(apply_sauvola(_resize_gray(clahe, dim), *PREPROCESS_CONFIG.sauvola_default))
    sharp = apply_unsharp_mask(gray, sigma=1.5, strength=2.0)
    candidates.append(apply_clahe(sharp))
    candidates.append(apply_otsu(clahe))
    candidates.append(apply_otsu(gray))
    candidates.append(apply_dilate(gray))
    candidates.append(apply_erode(gray))
    return candidates


def _preprocess_glare(image: np.ndarray) -> list[np.ndarray]:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    _, mask = cv2.threshold(gray, PREPROCESS_CONFIG.glare_inpaint_threshold, 255, cv2.THRESH_BINARY)
    mask = cv2.dilate(
        mask,
        cv2.getStructuringElement(cv2.MORPH_ELLIPSE, PREPROCESS_CONFIG.glare_dilate_kernel),
        iterations=2,
    )
    inpainted = cv2.inpaint(gray, mask, PREPROCESS_CONFIG.glare_inpaint_radius, cv2.INPAINT_TELEA)
    cl_inpaint = apply_clahe(inpainted)
    cl_raw = apply_clahe(gray)
    candidates: list[np.ndarray] = []
    for dim in PREPROCESS_CONFIG.glare_resize_dims:
        candidates.append(_resize_gray(gray, dim))
    for dim in PREPROCESS_CONFIG.glare_clahe_dims:
        candidates.append(_resize_gray(cl_raw, dim))
        candidates.append(_resize_gray(cl_inpaint, dim))
    candidates.append(apply_sauvola(cl_inpaint, *PREPROCESS_CONFIG.sauvola_default))
    return candidates


def _preprocess_high_version(image: np.ndarray) -> list[np.ndarray]:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    candidates: list[np.ndarray] = []
    for dim in PREPROCESS_CONFIG.high_version_resize_dims:
        candidates.append(_resize_gray(gray, dim))
    candidates.append(apply_clahe(gray))
    for dim in PREPROCESS_CONFIG.high_version_clahe_dims:
        candidates.append(apply_clahe(_resize_gray(gray, dim)))
    candidates.append(apply_sauvola(apply_clahe(gray), *PREPROCESS_CONFIG.sauvola_default))
    blurred = cv2.GaussianBlur(gray, (3, 3), 0)
    for dim in PREPROCESS_CONFIG.high_version_blur_dims:
        candidates.append(_resize_gray(blurred, dim))
    candidates.append(apply_clahe(blurred, clip_limit=3.0))
    for dim in PREPROCESS_CONFIG.high_version_threshold_dims:
        candidates.append(apply_adaptive_threshold(_resize_gray(gray, dim), 21, 3))
    candidates.append(apply_otsu(gray))
    candidates.append(apply_dilate(gray))
    candidates.append(apply_erode(gray))
    return candidates


def _preprocess_lots(image: np.ndarray) -> list[np.ndarray]:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    return [apply_clahe(gray), gray]


def _preprocess_monitor(image: np.ndarray) -> list[np.ndarray]:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    candidates: list[np.ndarray] = []
    for dim in PREPROCESS_CONFIG.monitor_resize_dims:
        resized = _resize_gray(gray, dim)
        candidates.append(resized)
        candidates.append(apply_clahe(resized, clip_limit=3.0))
    return candidates


def _preprocess_noncompliant(image: np.ndarray) -> list[np.ndarray]:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    clahe = apply_clahe(gray)
    return [
        clahe,
        *[apply_adaptive_threshold(clahe, block_size, c) for block_size, c in PREPROCESS_CONFIG.noncompliant_threshold_params],
        apply_sauvola(clahe, *PREPROCESS_CONFIG.sauvola_default),
        apply_clahe(gray, clip_limit=3.0),
    ]


def _preprocess_pathological(image: np.ndarray) -> list[np.ndarray]:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    clahe = apply_clahe(gray, clip_limit=3.0)
    sharp = apply_unsharp_mask(gray, sigma=1.5, strength=2.0)
    bilateral = apply_bilateral_filter(gray)
    return [
        gray,
        clahe,
        apply_clahe(sharp),
        *[apply_adaptive_threshold(clahe, block_size, c) for block_size, c in PREPROCESS_CONFIG.pathological_threshold_params],
        apply_clahe(bilateral),
        apply_sauvola(clahe, *PREPROCESS_CONFIG.sauvola_default),
    ]


def _preprocess_perspective(image: np.ndarray) -> list[np.ndarray]:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    clahe = apply_clahe(gray)
    clahe3 = apply_clahe(gray, clip_limit=3.0)
    sharp = apply_unsharp_mask(gray, sigma=1.5, strength=2.0)
    return [
        clahe,
        *[apply_adaptive_threshold(clahe, block_size, c) for block_size, c in PREPROCESS_CONFIG.perspective_threshold_params],
        *[apply_adaptive_threshold(clahe3, block_size, c) for block_size, c in PREPROCESS_CONFIG.perspective_threshold_params],
        apply_clahe(sharp),
        apply_sauvola(clahe, *PREPROCESS_CONFIG.sauvola_default),
        apply_otsu(clahe),
        apply_dilate(gray),
        apply_erode(gray),
    ]


def _preprocess_rotations(image: np.ndarray) -> list[np.ndarray]:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    return [
        apply_clahe(gray),
        apply_clahe(gray, clip_limit=3.0),
        gray,
        apply_unsharp_mask(gray, sigma=1.5, strength=1.5),
    ]


def _preprocess_shadows(image: np.ndarray) -> list[np.ndarray]:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    clahe3 = apply_clahe(gray, clip_limit=3.0)
    return [
        clahe3,
        apply_clahe(gray),
        apply_sauvola(clahe3, *PREPROCESS_CONFIG.sauvola_default),
    ]


_PREPROCESSORS = {
    "nominal": _preprocess_nominal,
    "blurred": _preprocess_blurred,
    "bright_spots": _preprocess_bright_spots,
    "brightness": _preprocess_brightness,
    "close": _preprocess_close,
    "curved": _preprocess_curved,
    "damaged": _preprocess_damaged,
    "glare": _preprocess_glare,
    "high_version": _preprocess_high_version,
    "lots": _preprocess_lots,
    "monitor": _preprocess_monitor,
    "noncompliant": _preprocess_noncompliant,
    "pathological": _preprocess_pathological,
    "perspective": _preprocess_perspective,
    "rotations": _preprocess_rotations,
    "shadows": _preprocess_shadows,
}


def preprocess_by_category(image: np.ndarray, category: str) -> list[np.ndarray]:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    fn = _PREPROCESSORS.get(category)
    if fn is None:
        return [gray]

    candidates = fn(image)
    candidates.append(gray)

    deduped: list[np.ndarray] = []
    for candidate in candidates:
        if not any(candidate.shape == existing.shape and np.array_equal(candidate, existing) for existing in deduped):
            deduped.append(candidate)
    return deduped
