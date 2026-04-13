"""Controller — orchestrates the game loop and auto-calibration on startup.

On start_game(), the camera is opened, CALIBRATION_FRAMES are sampled for
field detection, and all detectors are configured before the loop starts.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import TYPE_CHECKING, Optional

from src.ball_detector import BallDetector
from src.field_detector import FieldBounds, FieldDetector
from src.game_events import GameConfig, GameEvent
from src.goal_detector import GoalDetector
from src.statistics import Statistics
from src.video_source import VideoSource

if TYPE_CHECKING:
    from src.gui import KickerGUI

logger = logging.getLogger(__name__)

TARGET_FPS = 30.0
FRAME_INTERVAL = 1.0 / TARGET_FPS
CALIBRATION_FRAMES = 20


class Controller:
    """Wires all backend components together and drives the game loop."""

    def __init__(self, gui: "KickerGUI") -> None:
        self._gui = gui
        self._video: Optional[VideoSource] = None
        self._detector: Optional[BallDetector] = None
        self._goal_detector: Optional[GoalDetector] = None
        self._stats: Optional[Statistics] = None
        self._config: Optional[GameConfig] = None
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._field_detector = FieldDetector()

    def start_game(self, config: GameConfig) -> None:
        """Initialise all components, auto-calibrate, and start the game loop."""
        self._config = config
        self._stop_event.clear()

        field_w = config.field_x2 - config.field_x1
        field_h = config.field_y2 - config.field_y1
        req_w = field_w if field_w > 0 else 640
        req_h = field_h if field_h > 0 else 480

        self._video = VideoSource(
            camera_index=config.camera_index,
            width=req_w,
            height=req_h,
            fps=config.fps,
        )
        camera_opened = self._video.open()
        if not camera_opened:
            logger.warning(
                "Camera %d not available — running without video feed.",
                config.camera_index,
            )

        if camera_opened:
            config.field_x1 = 0
            config.field_y1 = 0
            config.field_x2 = self._video.frame_width
            config.field_y2 = self._video.frame_height

        field_corners: Optional[list[tuple[int, int]]] = None
        if camera_opened:
            logger.info(
                "Auto-calibration: sampling %d frames for field detection.",
                CALIBRATION_FRAMES,
            )
            bounds = self._field_detector.detect_from_frames(
                self._video, num_frames=CALIBRATION_FRAMES
            )
            if bounds is not None:
                config.field_x1 = bounds.x1
                config.field_y1 = bounds.y1
                config.field_x2 = bounds.x2
                config.field_y2 = bounds.y2
                field_corners = bounds.corners
                logger.info(
                    "Field detected: x=%d–%d y=%d–%d",
                    bounds.x1, bounds.x2, bounds.y1, bounds.y2,
                )
            else:
                logger.warning(
                    "Field auto-detection failed — using full frame (%dx%d).",
                    config.field_x2,
                    config.field_y2,
                )

        self._detector = BallDetector()

        if camera_opened and field_corners is not None:
            bounds_obj = FieldBounds(
                corners=field_corners,
                x1=config.field_x1,
                y1=config.field_y1,
                x2=config.field_x2,
                y2=config.field_y2,
            )
            self._detector.set_field_mask(
                bounds_obj.create_mask((config.field_y2, config.field_x2))
            )

        self._goal_detector = GoalDetector(
            field_x1=config.field_x1,
            field_x2=config.field_x2,
        )
        if field_corners is not None:
            self._goal_detector.configure_from_corners(field_corners)
        else:
            self._goal_detector.update_field_bounds(
                config.field_x1,
                config.field_x2,
                config.field_y1,
                config.field_y2,
            )

        self._stats = Statistics(config)
        self._stats.start_timer()

        self._gui.show_dashboard()

        self._thread = threading.Thread(
            target=self._game_loop, daemon=True, name="game-loop"
        )
        self._thread.start()
        logger.info("Game started: %s", config)

    def end_game(self) -> None:
        """Stop the loop and show the summary screen."""
        self._stop_event.set()
        if self._stats:
            self._stats.stop_timer()
        score_left = self._goal_detector.score_left if self._goal_detector else 0
        score_right = self._goal_detector.score_right if self._goal_detector else 0
        if self._video:
            self._video.release()
        self._gui.show_summary(self._stats, self._config, score_left, score_right)
        logger.info("Game ended. Score: %d:%d", score_left, score_right)

    def new_game(self) -> None:
        """Stop the current game and return to the start screen."""
        self._stop_event.set()
        if self._video:
            self._video.release()
            self._video = None
        self._stats = None
        self._goal_detector = None
        self._detector = None
        self._config = None
        self._gui.show_start_screen()
        logger.info("New game — returning to start screen.")

    def quit(self) -> None:
        """Clean shutdown."""
        self._stop_event.set()
        if self._video:
            self._video.release()
        logger.info("Application quit.")

    def _game_loop(self) -> None:
        signal = self._gui.frame_signal
        last_read_ok = True
        logger.debug("Game loop started.")

        while not self._stop_event.is_set():
            t_start = time.monotonic()

            frame = None
            position = None

            if self._video and self._video.is_opened():
                ok, frame = self._video.read()
                if not ok:
                    if last_read_ok:
                        logger.warning(
                            "Frame read failed — camera may have disconnected."
                        )
                    last_read_ok = False
                    frame = None
                else:
                    last_read_ok = True

            if frame is not None and self._detector:
                position = self._detector.detect(frame)

            goal_event: Optional[GameEvent] = None
            if self._goal_detector:
                goal_event = self._goal_detector.update(position)

            if self._stats:
                self._stats.update(position, goal_event)

            score_left = self._goal_detector.score_left if self._goal_detector else 0
            score_right = self._goal_detector.score_right if self._goal_detector else 0

            signal.update.emit(frame, position, self._stats, score_left, score_right)

            elapsed = time.monotonic() - t_start
            sleep_time = FRAME_INTERVAL - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)

        logger.debug("Game loop stopped.")
