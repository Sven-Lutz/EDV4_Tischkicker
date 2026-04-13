from __future__ import annotations

import logging
import threading
import time
from typing import TYPE_CHECKING, Optional, Tuple

import cv2
import numpy as np

from camera.Camera import Camera
# 1. NEUER IMPORT: Den alten BallTracker durch unseren neuen BallDetector ersetzen
from src.ball_detector import BallDetector
from table.Field import GoalDetector
from statistics.Statistics import Statistics, ScoreBoard
from game_controller.EventHandler import EventHandler
from game_controller.HUDRenderer import HUDRenderer
from game_controller.SnapshotManager import SnapshotManager

if TYPE_CHECKING:
    from gui import KickerGUI

logger = logging.getLogger(__name__)

TARGET_FPS = 30.0
FRAME_INTERVAL = 1.0 / TARGET_FPS


class GameController:
    """Wires all backend components together."""

    STATE_IDLE = "IDLE"
    STATE_CALIBRATING = "CALIBRATING"
    STATE_RUNNING = "RUNNING"
    STATE_PAUSED = "PAUSED"
    STATE_FINISHED = "FINISHED"

    WINDOW_NAME = "Tischkicker Ball Tracker"

    def __init__(
            self,
            gui: Optional["KickerGUI"] = None,
            camera_source: int = 0,
            team_names: Tuple[str, str] = ("Left", "Right"),
            cm_per_pixel: float = 0.1,
            goals_to_win: int = 10,
            snapshot_dir: str = "../snapshots"
    ) -> None:

        self._gui = gui
        self.goals_to_win = goals_to_win
        self.state = self.STATE_IDLE

        # Core
        self.camera = Camera(source=camera_source)

        # 2. NEUE INSTANZ: BallDetector statt BallTracker
        self.ball_tracker = BallDetector()

        self.field = GoalDetector()
        self.scoreboard = ScoreBoard(team_names=team_names)
        self.statistics = Statistics()

        # Helper
        self.snapshot_manager = SnapshotManager(snapshot_dir=snapshot_dir)
        self.hud_renderer = HUDRenderer()
        self.event_handler = EventHandler(game_controller=self)

        # Threading mechanisms
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

        # Hilfsvariablen für rudimentäre Geschwindigkeitsmessung (Da der Kalman-Filter weg ist)
        self._last_ball_pos = None
        self._last_ball_time = 0.0
        self.cm_per_pixel = cm_per_pixel

    # -- Public API ------------------------------------------------------------

    def start_game(self) -> None:
        logger.info("Starting system...")
        self._stop_event.clear()

        if not self.camera.start():
            logger.error("Camera could not be opened. Aborting start.")
            return

        self._run_calibration()

        self.state = self.STATE_RUNNING

        if self._gui:
            self._gui.show_dashboard()

        self._thread = threading.Thread(
            target=self._game_loop,
            daemon=True,
            name="GameLoopThread"
        )
        self._thread.start()
        logger.info("Game loop thread started successfully.")

    def stop_game(self) -> None:
        logger.info("Stopping game...")
        self.state = self.STATE_FINISHED
        self._stop_event.set()

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)

        self._shutdown()

    def new_game(self) -> None:
        logger.info("Starting a new game session.")
        self.stop_game()

        self.scoreboard.reset()
        self.statistics.reset()
        self.state = self.STATE_IDLE

        if self._gui:
            self._gui.show_start_screen()

    def quit(self) -> None:
        logger.info("Application quit requested.")
        self.stop_game()

    # -- Core Logic ------------------------------------------------------------

    def _run_calibration(self) -> None:
        """Calibration phase: Goal zones and Field Mask."""
        self.state = self.STATE_CALIBRATING

        # 3. ÄNDERUNG: HSV-Kalibrierung fällt weg! Wir kalibrieren nur noch die Tore/Spielfeld.
        logger.info("Goal Calibration: Please mark the goals on the field.")
        ok, frame = self.camera.read_frame()
        if not ok:
            logger.error("No frame available for calibration.")
            return

        # Angenommen, self.field.calibrate_interactive liefert uns jetzt die Tore.
        # WICHTIG: Wenn dein Field/GoalDetector auch eine Maske für das gesamte Spielfeld erzeugt,
        # sollten wir sie hier an den BallDetector übergeben:
        # field_mask = self.field.get_field_mask()
        # if field_mask is not None:
        #     self.ball_tracker.set_field_mask(field_mask)

        self.field.calibrate_interactive(frame, window_name=self.WINDOW_NAME)
        logger.info("Calibration finished. Transitioning to RUNNING state.")

    def _game_loop(self) -> None:
        logger.info("Game loop is active. Awaiting frame processing.")

        while not self._stop_event.is_set():
            t_start = time.monotonic()

            if self.state not in (self.STATE_RUNNING, self.STATE_PAUSED):
                time.sleep(0.1)
                continue

            ok, frame = self.camera.read_frame()
            if not ok:
                logger.warning("Failed to read frame. Ending game loop.")
                break

            ball_pos = None

            if self.state == self.STATE_RUNNING:
                ball_pos = self._process_frame(frame)

            # 4. ÄNDERUNG: Für den HUDRenderer müssen wir ggf. aufpassen, da self.ball_tracker
            # jetzt andere Methoden hat. Erwartet der Renderer noch speed_cm_s oder draw()?
            # Das müssten wir im HUDRenderer anpassen.
            self.hud_renderer.render_hud(
                frame,
                self.scoreboard,
                self.statistics,
                self.ball_tracker,  # <- Achtung, das ist jetzt ein BallDetector Objekt!
                self.state
            )

            if self._gui and hasattr(self._gui, 'frame_signal'):
                score_l = self.scoreboard.get_score(self.scoreboard.team_names[0])
                score_r = self.scoreboard.get_score(self.scoreboard.team_names[1])
                self._gui.frame_signal.update.emit(
                    frame,
                    ball_pos,
                    self.statistics,
                    score_l,
                    score_r
                )
            else:
                cv2.imshow(self.WINDOW_NAME, frame)
                key = cv2.waitKey(1) & 0xFF
                self.event_handler.handle_key_press(key)

            elapsed = time.monotonic() - t_start
            sleep_time = FRAME_INTERVAL - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)

        logger.info("Game loop has terminated cleanly.")

    def _process_frame(self, frame: np.ndarray) -> Optional[Tuple[int, int]]:
        """
        Processes a single frame: detects ball, updates Kalman filter,
        calculates smoothed speed, and checks for game events.
        """
        # 1. Kalman-enhanced detection
        # The detect() method now internally handles prediction and correction
        ball_data = self.ball_tracker.detect(frame)

        # Initialize variables for this frame
        ball_pos_tuple = None
        current_speed_cm_s = 0.0

        if ball_data is not None:
            # Convert BallPosition object to (x, y) tuple for other components
            ball_pos_tuple = (int(ball_data.x), int(ball_data.y))

            # 2. Extract smoothed velocity from Kalman State
            # ball_tracker.last_velocity_px_s is calculated from the Kalman vx/vy vectors
            current_speed_cm_s = self.ball_tracker.last_velocity_px_s * self.cm_per_pixel

            # 3. Update Statistics & Trajectory
            self.statistics.record_speed(current_speed_cm_s)
            self.statistics.trajectory_add(ball_pos_tuple)

            # 4. Visualization (Feedback for the user)
            # Draw a solid circle for the filtered position
            cv2.circle(frame, ball_pos_tuple, 10, (0, 255, 0), 2)
            # Optional: draw a small dot at the exact center
            cv2.circle(frame, ball_pos_tuple, 2, (0, 0, 255), -1)
        else:
            # If the ball is lost, we record 0 speed to the live stats
            self.statistics.record_speed(0.0)

        # 5. Field & HUD Rendering
        self.field.draw(frame)
        trajectory_count = self.statistics.get_trajectory_count()
        self.hud_renderer.draw_trajectory_gradient(frame, trajectory_count)

        # 6. Goal Logic
        # We pass the filtered position to the goal detector
        scored_goals = self.field.check_goals(ball_pos_tuple)

        if scored_goals:
            for goal_name in scored_goals:
                # We use the smoothed speed at the moment of the goal
                self.scoreboard.register_goal(goal_name, current_speed_cm_s)
                self.event_handler.on_goal(goal_name, frame)

        # 7. Win Condition Check
        for team in self.scoreboard.team_names:
            if self.scoreboard.get_score(team) >= self.goals_to_win:
                self.event_handler.on_game_over(team)
                self.state = self.STATE_FINISHED

        return ball_pos_tuple

    def _shutdown(self) -> None:
        try:
            summary = self.statistics.summary(self.scoreboard)
            logger.info("\n" + summary)
        except Exception as e:
            logger.debug(f"Could not print summary during shutdown: {e}")

        if self.camera:
            self.camera.stop()

        cv2.destroyAllWindows()

        if self._gui:
            score_l = self.scoreboard.get_score(self.scoreboard.team_names[0])
            score_r = self.scoreboard.get_score(self.scoreboard.team_names[1])
            self._gui.show_summary(self.statistics, score_l, score_r)

        logger.info("System shutdown complete.")