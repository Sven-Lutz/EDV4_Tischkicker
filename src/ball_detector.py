"""Ball detection with motion analysis and Kalman Filter prediction.

This module uses MOG2 for detection and a Kalman Filter for trajectory
smoothing and velocity estimation.
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
    """Detects and predicts ball movement using MOG2 and Kalman Filtering."""

    MIN_AREA = 30.0
    MAX_AREA = 800.0
    MIN_ASPECT_RATIO = 0.5
    MAX_ASPECT_RATIO = 2.5

    def __init__(self, fps: float = 30.0) -> None:
        """Initialize background subtraction and the Kalman Filter."""
        self._fps = fps

        # MOG2 Setup
        self._back_sub = cv2.createBackgroundSubtractorMOG2(
            history=500, varThreshold=50, detectShadows=False
        )
        self._kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        self._field_mask: Optional[np.ndarray] = None

        # Kalman Filter Setup: 4 state variables (x, y, vx, vy), 2 measurements (x, y)
        self._kalman = cv2.KalmanFilter(4, 2)
        dt = 1.0 / self._fps

        # Transition Matrix (Constant Velocity Model)
        # x_new = x + vx * dt
        # y_new = y + vy * dt
        self._kalman.transitionMatrix = np.array([
            [1, 0, dt, 0],
            [0, 1, 0, dt],
            [0, 0, 1, 0],
            [0, 0, 0, 1]
        ], np.float32)

        # Measurement Matrix (We only see x and y)
        self._kalman.measurementMatrix = np.array([
            [1, 0, 0, 0],
            [0, 1, 0, 0]
        ], np.float32)

        # Noise Covariance (Tuning these is key for "pro" feel)
        # Process Noise: How much we trust our physics model (lower = smoother)
        self._kalman.processNoiseCov = np.eye(4, dtype=np.float32) * 0.03
        # Measurement Noise: How much we trust the camera (higher = ignore jitter)
        self._kalman.measurementNoiseCov = np.eye(2, dtype=np.float32) * 0.5

        self._kalman_initialized = False
        self.last_velocity_px_s = 0.0

    def set_field_mask(self, mask: np.ndarray) -> None:
        """Restrict detection to the field area."""
        self._field_mask = mask.astype(np.uint8)

    def detect(self, frame: np.ndarray) -> Optional[BallPosition]:
        """Detect the ball and update the Kalman prediction."""
        # 1. Prediction Step (Always happen)
        prediction = self._kalman.predict()

        # 2. Visual Detection (MOG2)
        blurred = cv2.GaussianBlur(frame, (5, 5), 0)
        roi = blurred
        if self._field_mask is not None:
            if self._field_mask.shape != frame.shape[:2]:
                self._field_mask = cv2.resize(self._field_mask,
                                            (frame.shape[1], frame.shape[0]))
            roi = cv2.bitwise_and(blurred, blurred, mask=self._field_mask)

        fg_mask = self._back_sub.apply(roi)
        cleaned = cv2.morphologyEx(fg_mask, cv2.MORPH_CLOSE, self._kernel)
        cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_OPEN, self._kernel)

        contours, _ = cv2.findContours(cleaned, cv2.RETR_EXTERNAL,
                                      cv2.CHAIN_APPROX_SIMPLE)

        best_contour = self._pick_best_contour(contours)

        # 3. Correction Step
        if best_contour is not None:
            moments = cv2.moments(best_contour)
            if moments["m00"] > 0:
                cx = float(moments["m10"] / moments["m00"])
                cy = float(moments["m01"] / moments["m00"])

                measurement = np.array([[np.float32(cx)], [np.float32(cy)]])

                if not self._kalman_initialized:
                    self._kalman.statePost = np.array([[cx], [cy], [0], [0]],
                                                     dtype=np.float32)
                    self._kalman_initialized = True
                else:
                    self._kalman.correct(measurement)

        # 4. Extract Results from Kalman State
        state = self._kalman.statePost
        kx, ky = float(state[0, 0]), float(state[1, 0])
        vx, vy = float(state[2, 0]), float(state[3, 0])

        # Calculate speed in pixels per second
        self.last_velocity_px_s = np.sqrt(vx**2 + vy**2)

        # If we are totally lost (no detection for a while), we might return None
        # but usually, we return the Kalman prediction/filtered position.
        return BallPosition(x=kx, y=ky, timestamp=time.time())

    def _pick_best_contour(self, contours: tuple) -> Optional[np.ndarray]:
        """Filter contours based on heuristics."""
        best: Optional[np.ndarray] = None
        best_area = 0.0
        for c in contours:
            area = cv2.contourArea(c)
            if not (self.MIN_AREA <= area <= self.MAX_AREA):
                continue
            _, _, w, h = cv2.boundingRect(c)
            if h == 0 or not (self.MIN_ASPECT_RATIO <= (w/h) <= self.MAX_ASPECT_RATIO):
                continue
            if area > best_area:
                best_area = area
                best = c
        return best