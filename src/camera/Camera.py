from __future__ import annotations

import logging

import cv2
import numpy as np


class Camera:
    """
    Manages the camera feed and provides frames.
    """

    def __init__(self, source: int = 0):
        """
        :param source: Camera index (0 = default webcam) or video path
        """
        self.source = source
        self.cap: cv2.VideoCapture | None = None
        self.fps: float = 30.0
        self.frame_width: int = 0
        self.frame_height: int = 0

        #für Kalibrierung:
        self.camera_matrix = None
        self.dist_coeffs = None
        self.undistort_enabled = False


    def start(self) -> bool:
        """Opens the camera stream. Returns True if successful."""
        self.cap = cv2.VideoCapture(self.source)
        if not self.cap.isOpened():
            logging.error(f"[Camera] Fehler: Kamera {self.source} konnte nicht geöffnet werden.")
            return False

        self.fps = self.cap.get(cv2.CAP_PROP_FPS) or 30.0
        self.frame_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.frame_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        try:
            self.camera_matrix = np.load("camera_matrix.npy")
            self.dist_coeffs = np.load("dist_coeffs.npy")
            self.undistort_enabled = True
            print("[Camera] Kalibrierung geladen – Entzerrung aktiv.")
        except Exception:
            print("[Camera] Keine Kalibrierung gefunden – Entzerrung deaktiviert.")

        return True

    def read_frame(self):
        """
        Reads a frame from the stream.
        :return: (success: bool, frame: np.ndarray | None)
        """
        if self.cap is None:
             return False, None

        ok, frame = self.cap.read()
        if not ok:
            return False, None

        if self.undistort_enabled:
            frame = cv2.undistort(frame, self.camera_matrix, self.dist_coeffs)

        return True, frame


    def stop(self):
        """Releases the camera resource."""
        if self.cap:
            self.cap.release()
            self.cap = None
        print("[Camera] Gestoppt.")