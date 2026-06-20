from __future__ import annotations

import contextlib
import os
import sys
from dataclasses import dataclass
from time import perf_counter

import cv2
import numpy as np

if sys.platform == "darwin":
    _homebrew_lib = "/opt/homebrew/lib"
    if os.path.isdir(_homebrew_lib):
        os.environ.setdefault("DYLD_LIBRARY_PATH", _homebrew_lib)

from .adaptive import preprocess_by_category
from .config import CATEGORY_CHOICES, DETECTOR_CONFIG
from .detector_types import DetectionDiagnostic, QRCodeDetection
from .preprocess import ImageVariant, build_variants


@dataclass
class QRStaticDetector:
    """基于OpenCV + pyzbar的QR码静态图片检测器。"""

    enable_pyzbar: bool = True

    def __post_init__(self) -> None:
        self._opencv_detector = cv2.QRCodeDetector()
        self._pyzbar_decode = None
        if self.enable_pyzbar:
            try:
                from pyzbar.pyzbar import decode

                self._pyzbar_decode = decode
            except Exception:
                self._pyzbar_decode = None

    def detect(self, image: np.ndarray) -> list[QRCodeDetection]:
        variants = build_variants(image)
        detections: list[QRCodeDetection] = []
        seen: set[tuple[str, tuple[tuple[int, int], ...]]] = set()

        for variant in variants:
            for detection in self._detect_with_opencv(variant):
                self._append_unique(detections, seen, detection)

            if self._pyzbar_decode is not None:
                for detection in self._detect_with_pyzbar(variant):
                    self._append_unique(detections, seen, detection)

        return detections

    def detect_adaptive(self, image: np.ndarray, category: str | None = None) -> list[QRCodeDetection]:
        if not category or category not in CATEGORY_CHOICES:
            return self.detect(image)

        detections: list[QRCodeDetection] = []
        seen: set[tuple[str, tuple[tuple[int, int], ...]]] = set()

        do_rotate = category in DETECTOR_CONFIG.rotation_categories
        cv2_first = category in DETECTOR_CONFIG.cv2_first_categories
        candidates = preprocess_by_category(image, category)
        original_height, original_width = image.shape[:2]

        def iter_candidate_variants() -> list[ImageVariant]:
            variants: list[ImageVariant] = []
            for index, candidate in enumerate(candidates, start=1):
                name = f"{category}_{index:02d}"
                scale_x, scale_y = _derive_variant_scale(candidate, original_width, original_height)
                if do_rotate:
                    for rotate_name, rotate_code in _rotation_variants():
                        rotated = cv2.rotate(candidate, rotate_code) if rotate_code is not None else candidate
                        rotate_scale_x, rotate_scale_y = _derive_variant_scale(rotated, original_width, original_height)
                        variants.append(ImageVariant(f"{name}_{rotate_name}", rotated, rotate_scale_x, rotate_scale_y))
                else:
                    variants.append(ImageVariant(name, candidate, scale_x, scale_y))
            return variants

        candidate_variants = iter_candidate_variants()
        primary = self._detect_with_opencv if cv2_first else self._detect_with_pyzbar
        secondary = self._detect_with_pyzbar if cv2_first else self._detect_with_opencv

        for variant in candidate_variants:
            for detection in primary(variant):
                self._append_unique(detections, seen, detection)
            if detections:
                return detections

        for variant in candidate_variants:
            for detection in secondary(variant):
                self._append_unique(detections, seen, detection)
            if detections:
                return detections

        if category in DETECTOR_CONFIG.warp_categories:
            for detection in self._try_warp_decode(image, category):
                self._append_unique(detections, seen, detection)
            if detections:
                return detections

        for variant in self._build_multi_variants(image, category):
            for detection in self._detect_with_opencv_multi(variant):
                self._append_unique(detections, seen, detection)
            if detections:
                return detections

        return detections

    def detect_frame(self, frame_bgr: np.ndarray) -> list[QRCodeDetection]:
        gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
        results = self._detect_with_pyzbar(ImageVariant(DETECTOR_CONFIG.frame_variant_name, gray))
        if results:
            return results
        return self._detect_with_opencv(ImageVariant(DETECTOR_CONFIG.frame_variant_name, gray))

    def diagnose_adaptive(self, image: np.ndarray, category: str | None = None) -> DetectionDiagnostic:
        started = perf_counter()
        if not category or category not in CATEGORY_CHOICES:
            detections = self.detect(image)
            status = "success" if detections else "miss"
            return DetectionDiagnostic(
                category=category or "",
                attempted_variants=["default_variants"],
                attempted_methods=["opencv", "pyzbar" if self._pyzbar_decode is not None else "opencv_only"],
                fallback_stages=["default_pipeline"],
                final_status=status,
                dominant_failure_reason="baseline_pipeline_miss" if not detections else "none",
                elapsed_ms=round((perf_counter() - started) * 1000, 2),
            )

        attempted_variants: list[str] = []
        attempted_methods: list[str] = []
        fallback_stages: list[str] = []

        do_rotate = category in DETECTOR_CONFIG.rotation_categories
        cv2_first = category in DETECTOR_CONFIG.cv2_first_categories
        candidates = preprocess_by_category(image, category)

        candidate_variants: list[ImageVariant] = []
        for index, candidate in enumerate(candidates, start=1):
            name = f"{category}_{index:02d}"
            if do_rotate:
                for rotate_name, rotate_code in _rotation_variants():
                    rotated = cv2.rotate(candidate, rotate_code) if rotate_code is not None else candidate
                    candidate_variants.append(ImageVariant(f"{name}_{rotate_name}", rotated))
            else:
                candidate_variants.append(ImageVariant(name, candidate))

        primary = ("opencv", self._detect_with_opencv) if cv2_first else ("pyzbar", self._detect_with_pyzbar)
        secondary = ("pyzbar", self._detect_with_pyzbar) if cv2_first else ("opencv", self._detect_with_opencv)

        for variant in candidate_variants:
            attempted_variants.append(variant.name)
            attempted_methods.append(primary[0])
            if primary[1](variant):
                return DetectionDiagnostic(
                    category=category,
                    attempted_variants=attempted_variants,
                    attempted_methods=attempted_methods,
                    fallback_stages=fallback_stages or ["adaptive_primary"],
                    final_status="success",
                    dominant_failure_reason="none",
                    elapsed_ms=round((perf_counter() - started) * 1000, 2),
                )

        fallback_stages.append("secondary_decoder")
        for variant in candidate_variants:
            attempted_methods.append(secondary[0])
            if secondary[1](variant):
                return DetectionDiagnostic(
                    category=category,
                    attempted_variants=attempted_variants,
                    attempted_methods=attempted_methods,
                    fallback_stages=fallback_stages,
                    final_status="success",
                    dominant_failure_reason="none",
                    elapsed_ms=round((perf_counter() - started) * 1000, 2),
                )

        if category in DETECTOR_CONFIG.warp_categories:
            fallback_stages.append("warp_fallback")
            if self._try_warp_decode(image, category):
                return DetectionDiagnostic(
                    category=category,
                    attempted_variants=attempted_variants,
                    attempted_methods=attempted_methods + ["warp_decode"],
                    fallback_stages=fallback_stages,
                    final_status="success",
                    dominant_failure_reason="none",
                    elapsed_ms=round((perf_counter() - started) * 1000, 2),
                )

        fallback_stages.append("multi_decode")
        for variant in self._build_multi_variants(image, category):
            attempted_variants.append(variant.name)
            attempted_methods.append("opencv_multi")
            if self._detect_with_opencv_multi(variant):
                return DetectionDiagnostic(
                    category=category,
                    attempted_variants=attempted_variants,
                    attempted_methods=attempted_methods,
                    fallback_stages=fallback_stages,
                    final_status="success",
                    dominant_failure_reason="none",
                    elapsed_ms=round((perf_counter() - started) * 1000, 2),
                )

        return DetectionDiagnostic(
            category=category,
            attempted_variants=attempted_variants,
            attempted_methods=attempted_methods,
            fallback_stages=fallback_stages,
            final_status="miss",
            dominant_failure_reason=infer_failure_reason(category, fallback_stages, attempted_methods),
            elapsed_ms=round((perf_counter() - started) * 1000, 2),
        )

    def _detect_with_opencv(self, variant: ImageVariant) -> list[QRCodeDetection]:
        image = variant.image
        detections: list[QRCodeDetection] = []

        try:
            ok, decoded_info, points, _ = self._opencv_detector.detectAndDecodeMulti(image)
            if ok and points is not None:
                for data, qr_points in zip(decoded_info, points):
                    normalized = _normalize_points(qr_points, variant.scale_x, variant.scale_y)
                    detections.append(
                        QRCodeDetection(
                            data=data,
                            points=normalized,
                            method="opencv-multi",
                            variant=variant.name,
                        )
                    )
        except cv2.error:
            pass

        try:
            data, points, _ = self._opencv_detector.detectAndDecode(image)
            if points is not None and len(points) > 0:
                detections.append(
                    QRCodeDetection(
                        data=data,
                        points=_normalize_points(points, variant.scale_x, variant.scale_y),
                        method="opencv-single",
                        variant=variant.name,
                    )
                )
        except cv2.error:
            pass

        return detections

    def _detect_with_opencv_multi(self, variant: ImageVariant) -> list[QRCodeDetection]:
        image = variant.image
        detections: list[QRCodeDetection] = []
        try:
            ok, decoded_info, points_multi, _ = self._opencv_detector.detectAndDecodeMulti(image)
            if not ok or points_multi is None:
                return detections
            for data, qr_points in zip(decoded_info, points_multi):
                if not data:
                    continue
                detections.append(
                    QRCodeDetection(
                        data=data,
                        points=_normalize_points(qr_points, variant.scale_x, variant.scale_y),
                        method="opencv-multi-adaptive",
                        variant=variant.name,
                    )
                )
        except cv2.error:
            pass
        return detections

    def _detect_with_pyzbar(self, variant: ImageVariant) -> list[QRCodeDetection]:
        if self._pyzbar_decode is None:
            return []
        detections: list[QRCodeDetection] = []
        try:
            with _suppress_c_stderr():
                decoded_items = self._pyzbar_decode(variant.image)
        except Exception:
            return detections

        for item in decoded_items:
            polygon = [(point.x, point.y) for point in item.polygon]
            if len(polygon) < 4:
                x, y, width, height = item.rect
                polygon = [(x, y), (x + width, y), (x + width, y + height), (x, y + height)]

            data = item.data.decode("utf-8", errors="replace")
            detections.append(
                QRCodeDetection(
                    data=data,
                    points=_normalize_points(np.array(polygon, dtype=np.float32), variant.scale_x, variant.scale_y),
                    method="pyzbar",
                    variant=variant.name,
                )
            )

        return detections

    def _try_warp_decode(self, image: np.ndarray, category: str) -> list[QRCodeDetection]:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        try:
            ok, points = self._opencv_detector.detect(gray)
        except cv2.error:
            return []
        if not ok or points is None:
            return []

        pts = points[0] if points.ndim == 3 else points
        if len(pts) < 4:
            return []

        detections = self._try_decode_with_points(gray, pts, category)
        if detections:
            return detections

        xs = pts[:, 0]
        ys = pts[:, 1]
        pad = DETECTOR_CONFIG.detected_padding
        x1 = max(0, int(xs.min()) - pad)
        y1 = max(0, int(ys.min()) - pad)
        x2 = min(gray.shape[1], int(xs.max()) + pad)
        y2 = min(gray.shape[0], int(ys.max()) + pad)
        cropped = gray[y1:y2, x1:x2]
        ch, cw = cropped.shape[:2]

        if ch >= DETECTOR_CONFIG.min_crop_side and cw >= DETECTOR_CONFIG.min_crop_side:
            for target in DETECTOR_CONFIG.warp_crop_targets:
                scale = target / max(ch, cw)
                if scale < DETECTOR_CONFIG.min_warp_scale:
                    continue
                resized = cv2.resize(cropped, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
                variant_base = f"{category}_crop_{target}"
                hits = self._decode_variant_pair(resized, variant_base)
                if hits:
                    return hits

        warped = _warp_from_points(gray, pts)
        if warped is None:
            return []

        hits = self._decode_variant_pair(warped, f"{category}_warp")
        if hits:
            return hits

        for scale in DETECTOR_CONFIG.warp_upscale_factors:
            upscaled = cv2.resize(warped, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
            hits = self._decode_variant_pair(upscaled, f"{category}_warp_x{scale:g}")
            if hits:
                return hits

        return []

    def _try_decode_with_points(self, gray: np.ndarray, points: np.ndarray, category: str) -> list[QRCodeDetection]:
        for image_variant, variant_name in (
            (gray, f"{category}_detected"),
            (cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8)).apply(gray), f"{category}_detected_clahe"),
        ):
            try:
                data, _, _ = self._opencv_detector.decode(image_variant, points)
            except Exception:
                data = ""
            if data:
                return [
                    QRCodeDetection(
                        data=data,
                        points=_normalize_points(points),
                        method="opencv-decode",
                        variant=variant_name,
                    )
                ]
        return []

    def _decode_variant_pair(
        self,
        gray: np.ndarray,
        variant_base: str,
    ) -> list[QRCodeDetection]:
        variants = [
            ImageVariant(variant_base, gray),
            ImageVariant(f"{variant_base}_clahe", cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8)).apply(gray)),
        ]
        for variant in variants:
            hits = self._detect_with_pyzbar(variant)
            if hits:
                return hits
            hits = self._detect_with_opencv(variant)
            if hits:
                return hits
        return []

    @staticmethod
    def _build_multi_variants(image: np.ndarray, category: str) -> list[ImageVariant]:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        variants = [
            ImageVariant(f"{category}_gray", gray),
            ImageVariant(f"{category}_clahe3", cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8)).apply(gray)),
        ]
        _, otsu = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        variants.append(ImageVariant(f"{category}_otsu", otsu))
        height, width = gray.shape[:2]
        for limit in DETECTOR_CONFIG.multi_variant_resize_limits:
            current = max(height, width)
            if current > limit:
                scale = limit / current
                resized = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
                variants.append(ImageVariant(f"{category}_gray_{limit}", resized, 1 / scale, 1 / scale))
        return variants

    @staticmethod
    def _append_unique(
        detections: list[QRCodeDetection],
        seen: set[tuple[str, tuple[tuple[int, int], ...]]],
        detection: QRCodeDetection,
    ) -> None:
        key = (detection.data, _point_signature(detection.points))
        if key not in seen:
            seen.add(key)
            detections.append(detection)


def _normalize_points(
    points: np.ndarray | list[tuple[int, int]],
    scale_x: float = 1.0,
    scale_y: float = 1.0,
) -> list[tuple[int, int]]:
    array = np.array(points, dtype=np.float32).reshape(-1, 2)
    if len(array) > 4:
        hull = cv2.convexHull(array).reshape(-1, 2)
        rectangle = cv2.minAreaRect(hull)
        array = cv2.boxPoints(rectangle)
    return [(int(round(x * scale_x)), int(round(y * scale_y))) for x, y in array[:4]]


def _derive_variant_scale(candidate: np.ndarray, original_width: int, original_height: int) -> tuple[float, float]:
    candidate_height, candidate_width = candidate.shape[:2]
    if candidate_width <= 0 or candidate_height <= 0:
        return 1.0, 1.0
    return original_width / candidate_width, original_height / candidate_height


def _point_signature(points: list[tuple[int, int]]) -> tuple[tuple[int, int], ...]:
    granularity = DETECTOR_CONFIG.pyzbar_signature_rounding
    return tuple(sorted((round(x / granularity) * granularity, round(y / granularity) * granularity) for x, y in points))


@contextlib.contextmanager
def _suppress_c_stderr():
    devnull = os.open(os.devnull, os.O_WRONLY)
    old_stderr_fd = os.dup(2)
    os.dup2(devnull, 2)
    os.close(devnull)
    try:
        yield
    finally:
        os.dup2(old_stderr_fd, 2)
        os.close(old_stderr_fd)


def _warp_from_points(gray: np.ndarray, points: np.ndarray) -> np.ndarray | None:
    pts = np.array(points, dtype=np.float32).reshape(-1, 2)
    if len(pts) < 4:
        return None
    sums = pts.sum(axis=1)
    diffs = np.diff(pts, axis=1).flatten()
    ordered = np.zeros((4, 2), dtype=np.float32)
    ordered[0] = pts[np.argmin(sums)]
    ordered[2] = pts[np.argmax(sums)]
    ordered[1] = pts[np.argmin(diffs)]
    ordered[3] = pts[np.argmax(diffs)]

    w1 = np.linalg.norm(ordered[1] - ordered[0])
    w2 = np.linalg.norm(ordered[2] - ordered[3])
    h1 = np.linalg.norm(ordered[3] - ordered[0])
    h2 = np.linalg.norm(ordered[2] - ordered[1])
    out_w = int(max(w1, w2))
    out_h = int(max(h1, h2))
    if out_w < 50 or out_h < 50:
        return None

    dst = np.array([[0, 0], [out_w - 1, 0], [out_w - 1, out_h - 1], [0, out_h - 1]], dtype=np.float32)
    matrix = cv2.getPerspectiveTransform(ordered, dst)
    return cv2.warpPerspective(gray, matrix, (out_w, out_h))


def _rotation_variants() -> tuple[tuple[str, int | None], ...]:
    mapped_codes = {
        0: cv2.ROTATE_90_CLOCKWISE,
        1: cv2.ROTATE_180,
        2: cv2.ROTATE_90_COUNTERCLOCKWISE,
    }
    return tuple((name, mapped_codes.get(code) if code is not None else None) for name, code in DETECTOR_CONFIG.rotation_variant_names)


def infer_failure_reason(category: str, fallback_stages: list[str], attempted_methods: list[str]) -> str:
    if "warp_fallback" in fallback_stages and "multi_decode" in fallback_stages:
        return "warp_and_multi_fallback_exhausted"
    if "warp_fallback" in fallback_stages:
        return "warp_fallback_exhausted"
    if "multi_decode" in fallback_stages:
        return "multi_decode_exhausted"
    if category in DETECTOR_CONFIG.cv2_first_categories and "pyzbar" in attempted_methods:
        return "cv2_and_pyzbar_exhausted"
    if "pyzbar" in attempted_methods and "opencv" in attempted_methods:
        return "dual_decoder_exhausted"
    return "adaptive_variants_exhausted"
