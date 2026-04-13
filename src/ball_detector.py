"""Ball detection using HSV color filtering, Circularity checks, and Kalman Filtering.
This version combines color-based tracking with shape analysis and motion prediction.
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
    """Detects ball by color and shape, smoothed by a Kalman Filter."""

    MIN_AREA = 30.0
    MAX_AREA = 800.0
    MIN_ASPECT_RATIO = 0.5  # Allows for motion blur elongation
    MAX_ASPECT_RATIO = 2.5

    def __init__(self, fps: float = 30.0) -> None:
        self._fps = fps
        self._cm_per_pixel = 0.1 # Default, wird vom Controller überschrieben

        # 1. HSV Color Range (Initial values - can be tuned via calibration)
        self.hsv_lower = np.array([5, 150, 150])
        self.hsv_upper = np.array([25, 255, 255])

        # 2. Kalman Filter Setup
        self._kalman = cv2.KalmanFilter(4, 2)
        dt = 1.0 / self._fps
        self._kalman.transitionMatrix = np.array([
            [1, 0, dt, 0],
            [0, 1, 0, dt],
            [0, 0, 1, 0],
            [0, 0, 0, 1]
        ], np.float32)
        self._kalman.measurementMatrix = np.array([[1, 0, 0, 0], [0, 1, 0, 0]], np.float32)
        self._kalman.processNoiseCov = np.eye(4, dtype=np.float32) * 0.05
        self._kalman.measurementNoiseCov = np.eye(2, dtype=np.float32) * 2.0

        self._kalman_initialized = False
        self._field_mask: Optional[np.ndarray] = None
        self._kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))

        self.last_velocity_px_s = 0.0

    def set_field_mask(self, mask: np.ndarray) -> None:
        self._field_mask = mask.astype(np.uint8)

    def clear_field_mask(self) -> None:
        self._field_mask = None

    def _correct_lighting(self, frame: np.ndarray) -> np.ndarray:
        """Applies CLAHE to normalize lighting."""
        lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        l_corrected = clahe.apply(l)
        return cv2.cvtColor(cv2.merge((l_corrected, a, b)), cv2.COLOR_LAB2BGR)

    def detect(self, frame: np.ndarray) -> Optional[BallPosition]:
        """
        Detect the ball purely by yellow color segmentation.
        """

        # 1. HSV konvertieren
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        LOWER_YELLOW = np.array([20, 120, 120])
        UPPER_YELLOW = np.array([35, 255, 255])

        mask = cv2.inRange(hsv, LOWER_YELLOW, UPPER_YELLOW)

        # 2. Rauschen entfernen
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

        # 3. Konturen finden
        contours, _ = cv2.findContours(
            mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        best_contour = self._pick_best_contour(contours)
        if best_contour is None:
            return None

        # 4. Schwerpunkt berechnen
        moments = cv2.moments(best_contour)
        if moments["m00"] <= 0:
            return None

        cx = moments["m10"] / moments["m00"]
        cy = moments["m01"] / moments["m00"]

        return BallPosition(
            x=float(cx),
            y=float(cy),
            timestamp=time.time()
        )
    def calibrate_hsv_interactive(self, camera, roi_radius: int = 5) -> None:
        """
        Interactive calibration procedure.

        :param camera: camera object.
        """
        print("[BallTracker] HSV-Kalibrierung gestartet.Drücke 'c' zum Kalibrieren . Drücke 'q' zum Beenden.")

        # Trackbars
        self.hsv_trackbar()
        cv2.namedWindow("Original")
        cv2.waitKey(100)

        # ROI-Kreis in der Bildmitte platzieren
        ok, first_frame = camera.read_frame()
        h, w = first_frame.shape[:2] if ok else (480, 640)
        roi_center = (w // 2, h // 2)

        while True:
            # Frame lesen
            ok, frame = camera.read_frame()
            if not ok:
                print("[BallTracker] Kein Frame verfügbar.")
                break

            # Aktuelle Trackbar-Werte übernehmen
            frame = self.correct_lightning_clahe(frame)
            self.update_hsv_from_trackbar()

            # HSV konvertieren
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

            # Maske mit aktuellen Werten erstellen
            mask = cv2.inRange(hsv, self.hsv_lower, self.hsv_upper)
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))

            mask_cleaned = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
            mask_cleaned = cv2.morphologyEx(mask_cleaned, cv2.MORPH_OPEN, kernel)
            # Ergebnis auf Original anwenden
            result = cv2.bitwise_and(frame, frame, mask=mask_cleaned)

            # ROI-Kreis einzeichnen
            cv2.circle(frame, roi_center, roi_radius, (0, 255, 255), 2)

            cv2.imshow("Original", frame)
            cv2.imshow("Mask", mask_cleaned)
            cv2.imshow("Result", result)

            key = cv2.waitKey(1) & 0xFF

            if key == ord('c'):  # Kalibrierung
                self.hsv_lower, self.hsv_upper = self._auto_calibrate_from_roi(
                    camera, roi_center, roi_radius
                )
                self._sync_trackbars_to_hsv()

            elif key == ord('q'):
                print(f"[BallTracker] Finale HSV-Werte:")
                print(f"  hsv_lower = {self.hsv_lower}")
                print(f"  hsv_upper = {self.hsv_upper}")
                break

        cv2.destroyWindow("Original")
        cv2.destroyWindow("Mask")
        cv2.destroyWindow("Result")
        cv2.destroyWindow("HSV Settings")

    def _pick_best_contour(self, contours: tuple) -> Optional[np.ndarray]:
        """Filter contours based on size and aspect ratio to distinguish ball from players."""
        best: Optional[np.ndarray] = None
        best_area = 0.0

        for c in contours:
            area = cv2.contourArea(c)
            if not (self.MIN_AREA <= area <= self.MAX_AREA):
                continue
            x, y, w, h = cv2.boundingRect(c)
            if h == 0:
                continue
            aspect_ratio = float(w) / float(h)

            # Filter 2: Aspect Ratio (Players are tall/thin, ball is square-ish or blurred)
            if not (self.MIN_ASPECT_RATIO <= aspect_ratio <= self.MAX_ASPECT_RATIO):
                continue

            if area > best_area:
                best_area = area
                best = c
        return best