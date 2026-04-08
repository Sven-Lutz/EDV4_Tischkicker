import cv2
import numpy as np
import logging
logging.basicConfig(level=logging.INFO)
from camera.Camera import Camera
from ball_tracker.BallTracker import BallTracker
from table.Field import Field
from statistics.Statistics import Statistics, ScoreBoard
from game_controller.EventHandler import EventHandler
from game_controller.HUDRenderer import HUDRenderer
from game_controller.SnapshotManager import SnapshotManager


class GameController:
    # Spielzustände
    STATE_IDLE = "IDLE"
    STATE_CALIBRATING = "CALIBRATING"
    STATE_RUNNING = "RUNNING"
    STATE_PAUSED = "PAUSED"
    STATE_FINISHED = "FINISHED"

    WINDOW_NAME = "Tischkicker ball_tracker"

    def __init__(
            self,
            camera_source: int = 0,
            team_names: tuple[str, str] = ("Links", "Rechts"),
            cm_per_pixel: float = 0.1,
            goals_to_win: int = 10,
            snapshot_dir: str = "../snapshots"

    ):
        """
        :param camera_source: Kamera-Index oder Videopfad
        :param team_names:    Namen der beiden Teams
        :param cm_per_pixel:  Pixel→cm Umrechnungsfaktor
        :param goals_to_win:  Tore bis zum Spielende
        :param snapshot_dir:  Verzeichnis für Tor-Snapshots
        """
        self.goals_to_win = goals_to_win
        self.state = self.STATE_IDLE

        # Komponenten
        self.camera = Camera(source=camera_source)
        self.ball_tracker = BallTracker(cm_per_pixel=cm_per_pixel)
        self.field = Field()
        self.scoreboard = ScoreBoard(team_names=team_names)
        self.statistics = Statistics()
        
        # Ausgelagerte Komponenten
        self.snapshot_manager = SnapshotManager(snapshot_dir=snapshot_dir)
        self.hud_renderer = HUDRenderer()
        self.event_handler = EventHandler(game_controller=self)

    def start(self) -> None:
        """Startet das System: Kamera öffnen → kalibrieren → Spiel-Loop."""
        logging.info("[game_controller] Starte System …")

        if not self.camera.start():
            logging.error("[game_controller] Abbruch: Kamera nicht verfügbar.")
            return

        self.ball_tracker.fps = self.camera.fps

        self._run_calibration()

        self._run_game_loop()

        self._shutdown()

    def stop(self) -> None:
        """Beendet den Spiel-Loop von außen ."""
        self.state = self.STATE_FINISHED

    def _run_calibration(self) -> None:
        """Kalibrierungsphase: HSV-Werte und Tor-Zonen interaktiv festlegen."""
        self.state = self.STATE_CALIBRATING

        # 1. HSV-Kalibrierung
        logging.info(
            "[game_controller] HSV-Kalibrierung – Passe die Trackbars an, bis nur der Ball sichtbar ist. Drücke 'q' zum Fortfahren.")
        self.ball_tracker.calibrate_hsv_interactive(self.camera)

        # 2. Tor-Kalibrierung
        logging.info("[game_controller] Tor-Kalibrierung – Bitte Tore markieren.")
        ok, frame = self.camera.read_frame()
        if not ok:
            logging.error("[game_controller] Kein Frame für Kalibrierung.")
            return

        self.field.calibrate_interactive(frame, window_name=self.WINDOW_NAME)
        # 3. Wand-Kalibrierung

        self.state = self.STATE_RUNNING
        logging.info("[game_controller] Kalibrierung fertig – Spiel startet!")

    def _run_game_loop(self) -> None:
        """Haupt-Loop: Frame lesen → tracken → prüfen → anzeigen."""
        print(f"[game_controller] Spiel läuft. Tasten: [p] Pause  [r] Reset  [q] Beenden")

        while self.state in (self.STATE_RUNNING, self.STATE_PAUSED):
            ok, frame = self.camera.read_frame()
            if not ok:
                logging.error("[game_controller] Kein Frame mehr – Loop beendet.")
                break

            if self.state == self.STATE_RUNNING:
                self._process_frame(frame)

            self.hud_renderer.render_hud(frame, self.scoreboard, self.statistics, self.ball_tracker, self.state)
            cv2.imshow(self.WINDOW_NAME, frame)

            self.event_handler.handle_key_press(cv2.waitKey(1) & 0xFF)

    def _process_frame(self, frame: np.ndarray) -> None:
        """Führt Tracking, Tor-Check und Statistik für einen einzelnen Frame durch."""
        # 1. Ball tracken
        ball_pos = self.ball_tracker.update(frame)
        self.ball_tracker.draw(frame)

        # 2. Geschwindigkeit aufzeichnen
        self.statistics.record_speed(self.ball_tracker.speed_cm_s)

        # 3. Trajektorie aufzeichnen
        if ball_pos is not None:
            self.statistics.trajectory_add(ball_pos)
        
        # 4. Torzonen zeichnen
        self.field.draw(frame)
        
        # 5. Trajektorie zeichnen
        trajectory = self.statistics.get_trajectory_count()
        self.hud_renderer.draw_trajectory(frame, trajectory)

        # 6. Tor-Check
        scored_goals = self.field.check_goals(ball_pos)
        for goal_name in scored_goals:
            self.scoreboard.register_goal(goal_name, self.ball_tracker.speed_cm_s)
            self.event_handler.on_goal(goal_name, frame)

        # 7. Spielende prüfen
        for team in self.scoreboard.team_names:
            if self.scoreboard.get_score(team) >= self.goals_to_win:
                self.event_handler.on_game_over(team)
                return

    def _shutdown(self) -> None:
        """Gibt alle Ressourcen frei und zeigt die Zusammenfassung."""
        print("\n" + self.statistics.summary(self.scoreboard))
        self.camera.stop()
        cv2.destroyAllWindows()
        print("[game_controller] System beendet.")
