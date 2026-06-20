from __future__ import annotations

from typing import Iterable

import cv2
import numpy as np

from .detector_types import QRCodeDetection


def draw_detections(image: np.ndarray, detections: Iterable[QRCodeDetection]) -> np.ndarray:
    canvas = image.copy()
    for index, detection in enumerate(detections, start=1):
        points = np.array(detection.points, dtype=np.int32)
        cv2.polylines(canvas, [points], isClosed=True, color=(0, 200, 0), thickness=3)

        x, y = points[:, 0].min(), points[:, 1].min()
        label = f"{index}: {detection.data[:32] or '<empty>'}"
        cv2.putText(
            canvas,
            label,
            (int(x), max(25, int(y) - 10)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            (0, 0, 255),
            2,
            cv2.LINE_AA,
        )
    return canvas
