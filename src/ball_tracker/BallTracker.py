from __future__ import annotations

import logging
import time
from typing import Optional, Tuple

import cv2
import numpy as np

from GameEvents import BallPosition

logger = logging.getLogger(__name__)


def nothing(x: int) -> None:
    """Dummy callback for OpenCV trackbars."""
    pass

class BallTracker:
    """
    Detects and tracks the ball based on a combined HSV color space (White, Orange, Blue)
    and handles edge-distortions by relaxing circularity constraints.
    """

    MIN_RADIUS = 6
    MAX_RADIUS = 40
    MIN_CIRCULARITY = 0.50

    def __init__(self, fps: float = 30.0, cm_per_pixel: float = 0.1) -> None:
        self.fps = fps
        self.cm_per_pixel = cm_per_pixel

        self._kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))

        self.position: Optional[BallPosition] = None
        self.radius: int = 0
        self.speed_cm_s: float = 0.0

        self._prev_position: Optional[BallPosition] = None
        self._speed_history: list[float] = []

    # --Tracking & Detection---------------------------------------------

    def update(self, frame: np.ndarray) -> Optional[BallPosition]:
        """
        Processes a frame, detects the ball using multi-color masking,
        and updates position and velocity.
        """
        self._prev_position = self.position

        blurred = cv2.GaussianBlur(frame, (7, 7), 0)
        hsv = cv2.cvtColor(blurred, cv2.COLOR_BGR2HSV)

        mask = self._create_multi_color_mask(hsv)

        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, self._kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, self._kernel)

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        best_contour = self._pick_best_contour(contours)

        if best_contour is None:
            self.position = None
            self.radius = 0
            self.speed_cm_s = 0.0
            return None

        (cx, cy), radius = cv2.minEnclosingCircle(best_contour)

        self.position = BallPosition(x=float(cx), y=float(cy), timestamp=time.time())
        self.radius = int(radius)

        self._update_speed()
        return self.position

    def _create_multi_color_mask(self, hsv: np.ndarray) -> np.ndarray:
        mask_white = cv2.inRange(hsv, np.array([0, 0, 130]), np.array([180, 50, 255]))
        mask_orange = cv2.inRange(hsv, np.array([5, 80, 130]), np.array([25, 255, 255]))
        mask_blue = cv2.inRange(hsv, np.array([90, 60, 130]), np.array([130, 255, 255]))
        combined_mask = cv2.bitwise_or(mask_white, mask_orange)
        combined_mask = cv2.bitwise_or(combined_mask, mask_blue)

        return combined_mask

    def _pick_best_contour(self, contours: tuple) -> Optional[np.ndarray]:
        best = None
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

    def _update_speed(self) -> None:
        """Calculates velocity based on the pixel distance between frames."""
        if self._prev_position is None or self.position is None:
            self.speed_cm_s = 0.0
            return

        dx = self.position.x - self._prev_position.x
        dy = self.position.y - self._prev_position.y
        pixel_dist = (dx ** 2 + dy ** 2) ** 0.5

        self.speed_cm_s = pixel_dist * self.cm_per_pixel * self.fps

        self._speed_history.append(self.speed_cm_s)
        if len(self._speed_history) > 100:
            self._speed_history.pop(0)

    def draw(self, frame: np.ndarray) -> None:
        """Draws the ball's bounding circle and velocity label onto the frame."""
        if self.position is None:
            return

        center = (int(self.position.x), int(self.position.y))

        cv2.circle(frame, center, self.radius, (0, 255, 0), 2)
        cv2.circle(frame, center, 3, (0, 255, 0), -1)

        cv2.putText(
            frame,
            f"{self.speed_cm_s:.1f} cm/s",
            (center[0] + self.radius + 5, center[1]),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (0, 255, 0),
            1
        )