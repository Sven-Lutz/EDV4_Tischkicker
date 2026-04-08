import cv2
import numpy as np


class HUDRenderer:
    """Rendert das Head-Up-Display (HUD) mit Spielstand, Geschwindigkeit und Status."""
    
    def __init__(self):
        """Initialisiert den HUD-Renderer."""
        pass
    
    def render_hud(
        self,
        frame: np.ndarray,
        scoreboard,
        statistics,
        ball_tracker,
        state: str
    ) -> None:
        """
        Rendert Spielstand, Geschwindigkeit und Status ins Bild.
        
        :param frame: Das Bild, in das gerendert werden soll
        :param scoreboard: ScoreBoard-Instanz
        :param statistics: Statistics-Instanz
        :param ball_tracker: BallTracker-Instanz
        :param state: Aktueller Spielzustand (z.B. "RUNNING", "PAUSED")
        """
        h, w = frame.shape[:2]

        # Schwarzer Balken oben
        cv2.rectangle(frame, (0, 0), (w, 50), (0, 0, 0), -1)

        # Spielstand in der Mitte
        score_text = f"  {scoreboard.get_score_string()}  "
        cv2.putText(frame, score_text, (w // 2 - 60, 35),
                    cv2.FONT_HERSHEY_DUPLEX, 1.0, (255, 255, 255), 2)

        # Team-Namen links und rechts
        cv2.putText(frame, scoreboard.team_names[0], (10, 35),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (100, 200, 255), 2)
        cv2.putText(frame, scoreboard.team_names[1], (w - 100, 35),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (100, 200, 255), 2)

        # Geschwindigkeit unten
        avg_speed = statistics.average_speed()
        cv2.putText(frame, f"Akt: {ball_tracker.speed_cm_s:.1f} cm/s  |  Ø {avg_speed:.1f} cm/s",
                    (10, h - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)

        # Pause-Anzeige
        if state == "PAUSED":
            cv2.putText(frame, "⏸ PAUSE", (w // 2 - 60, h // 2),
                        cv2.FONT_HERSHEY_DUPLEX, 1.5, (0, 255, 255), 3)
    
    def draw_trajectory(self, frame: np.ndarray, trajectory: list) -> None:
        """
        Zeichnet die Trajektorie der letzten Sekunden.
        
        :param frame: Das Bild, in das gezeichnet werden soll
        :param trajectory: Liste von Positionen [(x, y, timestamp), ...]
        """
        if len(trajectory) < 2:
            return
        
        for i in range(1, len(trajectory)):
            # Extrahiere nur x,y Position
            p1 = (int(trajectory[i-1][0]), int(trajectory[i-1][1]))
            p2 = (int(trajectory[i][0]), int(trajectory[i][1]))
            cv2.line(frame, p1, p2, (255, 0, 0), 2)
