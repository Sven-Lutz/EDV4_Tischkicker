"""Ball detection via HSV colour filtering.

Default profile: white ball on dark green (H 0–180, S 0–50, V 170–255).
Supply a field mask via set_field_mask() to restrict the search area.
"""

from __future__ import annotations

import logging
import time
from typing import Optional

import cv2
import numpy as np

from src.game_events import BallPosition

logger = logging.getLogger(__name__)


class BallDetector:
    DEFAULT_HSV_LOWER = np.array([0, 0, 170], dtype=np.uint8)
    DEFAULT_HSV_UPPER = np.array([180, 50, 255], dtype=np.uint8)

    MIN_RADIUS = 6
    MAX_RADIUS = 45
    MIN_CIRCULARITY = 0.65

    def __init__(self) -> None:
        self._hsv_lower = self.DEFAULT_HSV_LOWER.copy()
        self._hsv_upper = self.DEFAULT_HSV_UPPER.copy()
        self._kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        self._field_mask: Optional[np.ndarray] = None

    def set_field_mask(self, mask: np.ndarray) -> None:
        """Restrict detection to pixels where *mask* is non-zero."""
        self._field_mask = mask.astype(np.uint8)
        logger.debug("Field mask applied (%dx%d).", mask.shape[1], mask.shape[0])

    def clear_field_mask(self) -> None:
        """Remove the field mask; the full frame is searched."""
        self._field_mask = None
        logger.debug("Field mask cleared.")

    def update_hsv_range(self, lower: np.ndarray, upper: np.ndarray) -> None:
        """Override HSV thresholds used for colour filtering."""
        self._hsv_lower = lower.astype(np.uint8)
        self._hsv_upper = upper.astype(np.uint8)
        logger.debug("HSV range updated: lower=%s upper=%s", lower, upper)

    def detect(self, frame: np.ndarray) -> Optional[BallPosition]:
        """Return the ball position in *frame*, or None if not found."""
        blurred = cv2.GaussianBlur(frame, (7, 7), 0)
        hsv = cv2.cvtColor(blurred, cv2.COLOR_BGR2HSV)

        colour_mask = cv2.inRange(hsv, self._hsv_lower, self._hsv_upper)

        if self._field_mask is not None:
            if self._field_mask.shape != colour_mask.shape:
                self._field_mask = cv2.resize(
                    self._field_mask,
                    (colour_mask.shape[1], colour_mask.shape[0]),
                    interpolation=cv2.INTER_NEAREST,
                )
            colour_mask = cv2.bitwise_and(colour_mask, self._field_mask)

        # Close fills holes in the ball silhouette; open removes speckles.
        cleaned = cv2.morphologyEx(colour_mask, cv2.MORPH_CLOSE, self._kernel)
        cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_OPEN, self._kernel)

        contours, _ = cv2.findContours(
            cleaned, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        best = self._pick_best_contour(contours)
        if best is None:
            return None

        (cx, cy), _ = cv2.minEnclosingCircle(best)
        return BallPosition(x=float(cx), y=float(cy), timestamp=time.time())

    def _pick_best_contour(self, contours: tuple) -> Optional[np.ndarray]:
        best: Optional[np.ndarray] = None
        best_area = 0.0

        for c in contours:
            area = cv2.contourArea(c)
            if area < 1:
                continue

            _, radius = cv2.minEnclosingCircle(c)
            if not (self.MIN_RADIUS <= radius <= self.MAX_RADIUS):
                continue

            perimeter = cv2.arcLength(c, True)
            if perimeter == 0:
                continue

            circularity = 4 * np.pi * area / (perimeter ** 2)
            if circularity < self.MIN_CIRCULARITY:
                continue

            if area > best_area:
                best_area = area
                best = c

        return best
