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
        # 1. Kalman Prediction
        self._kalman.predict()

        # 2. Preprocessing
        frame_adj = self._correct_lighting(frame)
        hsv = cv2.cvtColor(frame_adj, cv2.COLOR_BGR2HSV)

        # 3. HSV Masking
        mask = cv2.inRange(hsv, self.hsv_lower, self.hsv_upper)
        if self._field_mask is not None:
            if self._field_mask.shape != mask.shape:
                self._field_mask = cv2.resize(self._field_mask, (mask.shape[1], mask.shape[0]))
            mask = cv2.bitwise_and(mask, mask, mask=self._field_mask)

        # 4. Clean mask
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, self._kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, self._kernel)

        # 5. Find Contours and Filter by Circularity
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        best_measurement = None
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < 20: continue # Too small

            # CIRCULARITY CHECK: (4 * PI * Area) / Perimeter^2
            # A perfect circle has circularity = 1.0. A line is near 0.
            perimeter = cv2.arcLength(cnt, True)
            if perimeter > 0:
                circularity = (4 * np.pi * area) / (perimeter ** 2)
                if circularity > 0.6: # It's round enough to be a ball!
                    moments = cv2.moments(cnt)
                    if moments["m00"] > 0:
                        cx = moments["m10"] / moments["m00"]
                        cy = moments["m01"] / moments["m00"]
                        best_measurement = (float(cx), float(cy))
                        break

        # 6. Kalman Correction
        if best_measurement:
            meas = np.array([[np.float32(best_measurement[0])], [np.float32(best_measurement[1])]], dtype=np.float32)
            if not self._kalman_initialized:
                self._kalman.statePost = np.array([[best_measurement[0]], [best_measurement[1]], [0], [0]], dtype=np.float32)
                self._kalman_initialized = True
            else:
                self._kalman.correct(meas)

        # 7. Final State
        state = self._kalman.statePost
        self.last_velocity_px_s = np.sqrt(state[2, 0]**2 + state[3, 0]**2)

        return BallPosition(x=float(state[0, 0]), y=float(state[1, 0]), timestamp=time.time())

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