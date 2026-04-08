import cv2
import os
import logging
from datetime import datetime
import numpy as np


class SnapshotManager:
    """Verwaltet das Speichern von Tor-Snapshots."""
    
    def __init__(self, snapshot_dir: str = "../snapshots"):
        """
        :param snapshot_dir: Verzeichnis für Tor-Snapshots
        """
        self.snapshot_dir = snapshot_dir
        os.makedirs(self.snapshot_dir, exist_ok=True)
        logging.info(f"[SnapshotManager] Snapshot-Verzeichnis: {self.snapshot_dir}")
    
    def save_snapshot(self, frame: np.ndarray, team: str, scoreboard) -> None:
        """
        Speichert einen Snapshot des aktuellen Frames.
        
        :param frame: Der zu speichernde Frame (bereits mit Trajektorie gezeichnet)
        :param team: Name des Teams, das getroffen hat
        :param scoreboard: ScoreBoard-Instanz für den aktuellen Spielstand
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        score = scoreboard.get_score_string().replace(" : ", "-")
        filename = f"goal_{team}_{score}_{timestamp}.png"
        filepath = os.path.join(self.snapshot_dir, filename)
        
        cv2.imwrite(filepath, frame)
        logging.info(f"[SnapshotManager] Snapshot gespeichert: {filepath}")
