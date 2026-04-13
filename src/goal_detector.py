"""Goal zone detection with edge-triggered scoring and optional 2-D bounds.

A goal fires only when the ball enters a zone (edge-triggered), not for every
frame it stays inside. Cooldown provides secondary double-count protection.
Call configure_from_corners() after field calibration to add y-axis bounds.
"""

from __future__ import annotations

import logging
from typing import Optional

import cv2

from src.game_events import BallPosition, EventType, GameEvent, Team

logger = logging.getLogger(__name__)

_GOAL_DEPTH_RATIO = 0.04   # goal depth as fraction of field width
_GOAL_HEIGHT_RATIO = 0.28  # goal opening height as fraction of field height


class _GoalZone:
    """Rectangular zone that triggers a goal when the ball enters it."""

    def __init__(
        self,
        name: str,
        x: int,
        y: int,
        w: int,
        h: int,
        scoring_team: Team,
        use_y_bounds: bool = True,
    ) -> None:
        self.name = name
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.scoring_team = scoring_team
        self._use_y_bounds = use_y_bounds

    def contains(self, px: float, py: float) -> bool:
        if not (self.x <= px <= self.x + self.w):
            return False
        if self._use_y_bounds:
            return self.y <= py <= self.y + self.h
        return True


class GoalDetector:
    """Detects when the ball enters the left or right goal zone.

    Constructor parameters (unchanged for backward compatibility):
        field_x1, field_x2  — horizontal field boundaries in pixels
        goal_zone_width     — depth of each goal zone in pixels
        cooldown_frames     — minimum frames between two goal events

    Call configure_from_corners() to enable proper 2-D detection.
    """

    DEFAULT_GOAL_ZONE_WIDTH = 40
    DEFAULT_COOLDOWN_FRAMES = 45  # 1.5 s at 30 fps

    def __init__(
        self,
        field_x1: int = 0,
        field_x2: int = 640,
        goal_zone_width: int = DEFAULT_GOAL_ZONE_WIDTH,
        cooldown_frames: int = DEFAULT_COOLDOWN_FRAMES,
    ) -> None:
        self._field_x1 = field_x1
        self._field_x2 = field_x2
        self._goal_zone_width = goal_zone_width
        self._cooldown_frames = cooldown_frames

        self._score_left = 0
        self._score_right = 0
        self._frames_since_goal = cooldown_frames  # start ready to detect

        # Was the ball in each zone on the previous frame?
        self._prev_in_left = False
        self._prev_in_right = False

        # Populated by configure_from_corners() or update_field_bounds()
        self._zone_left: Optional[_GoalZone] = None
        self._zone_right: Optional[_GoalZone] = None

        self._rebuild_default_zones()

    @property
    def score_left(self) -> int:
        return self._score_left

    @property
    def score_right(self) -> int:
        return self._score_right

    def configure_from_corners(
        self,
        corners: list[tuple[int, int]],
    ) -> None:
        """Derive 2-D goal zones from field corners [TL, TR, BR, BL]."""
        if len(corners) < 4:
            logger.warning(
                "configure_from_corners: expected 4 corners, got %d.",
                len(corners),
            )
            return

        tl, tr, br, bl = corners

        field_width = int(((tr[0] - tl[0]) + (br[0] - bl[0])) / 2)
        field_height = int(((bl[1] - tl[1]) + (br[1] - tr[1])) / 2)

        goal_depth = max(8, int(field_width * _GOAL_DEPTH_RATIO))
        goal_height = max(20, int(field_height * _GOAL_HEIGHT_RATIO))

        left_mid_x = int((tl[0] + bl[0]) / 2)
        left_mid_y = int((tl[1] + bl[1]) / 2)
        right_mid_x = int((tr[0] + br[0]) / 2)
        right_mid_y = int((tr[1] + br[1]) / 2)

        # Ball enters from the right — RIGHT team scores.
        self._zone_left = _GoalZone(
            name="Left",
            x=left_mid_x - goal_depth,
            y=left_mid_y - goal_height // 2,
            w=goal_depth,
            h=goal_height,
            scoring_team=Team.RIGHT,
            use_y_bounds=True,
        )

        # Ball enters from the left — LEFT team scores.
        self._zone_right = _GoalZone(
            name="Right",
            x=right_mid_x,
            y=right_mid_y - goal_height // 2,
            w=goal_depth,
            h=goal_height,
            scoring_team=Team.LEFT,
            use_y_bounds=True,
        )

        self._field_x1 = tl[0]
        self._field_x2 = tr[0]

        logger.info(
            "2-D goal zones set: left x=%d–%d y=%d–%d | right x=%d–%d y=%d–%d",
            self._zone_left.x,
            self._zone_left.x + self._zone_left.w,
            self._zone_left.y,
            self._zone_left.y + self._zone_left.h,
            self._zone_right.x,
            self._zone_right.x + self._zone_right.w,
            self._zone_right.y,
            self._zone_right.y + self._zone_right.h,
        )

    def update_field_bounds(
        self,
        field_x1: int,
        field_x2: int,
        field_y1: int = 0,
        field_y2: int = 480,
    ) -> None:
        """Update goal zones from a simple axis-aligned bounding box."""
        self._field_x1 = field_x1
        self._field_x2 = field_x2
        self._rebuild_default_zones(field_y1, field_y2)
        logger.debug(
            "Goal zones updated: x=%d–%d y=%d–%d",
            field_x1, field_x2, field_y1, field_y2,
        )

    def update(self, position: Optional[BallPosition]) -> Optional[GameEvent]:
        """Call once per frame. Returns a GameEvent if a goal was scored."""
        self._frames_since_goal += 1

        if position is None or not position.detected:
            # Ball lost — clear edge state so re-entry can trigger a goal.
            self._prev_in_left = False
            self._prev_in_right = False
            return None

        x, y = position.x, position.y

        in_left = (
            self._zone_left.contains(x, y)
            if self._zone_left
            else x <= self._field_x1 + self._goal_zone_width
        )
        in_right = (
            self._zone_right.contains(x, y)
            if self._zone_right
            else x >= self._field_x2 - self._goal_zone_width
        )

        event: Optional[GameEvent] = None
        cooldown_ok = self._frames_since_goal >= self._cooldown_frames

        # Left zone — RIGHT team scores
        if in_left and not self._prev_in_left and cooldown_ok:
            self._score_right += 1
            self._frames_since_goal = 0
            event = GameEvent(
                event_type=EventType.GOAL,
                timestamp=position.timestamp,
                team=Team.RIGHT,
                score_left=self._score_left,
                score_right=self._score_right,
                description=f"Tor Rechts · {self._score_left}:{self._score_right}",
            )
            logger.info(
                "Goal RIGHT — score %d:%d", self._score_left, self._score_right
            )

        # Right zone — LEFT team scores
        elif in_right and not self._prev_in_right and cooldown_ok:
            self._score_left += 1
            self._frames_since_goal = 0
            event = GameEvent(
                event_type=EventType.GOAL,
                timestamp=position.timestamp,
                team=Team.LEFT,
                score_left=self._score_left,
                score_right=self._score_right,
                description=f"Tor Links · {self._score_left}:{self._score_right}",
            )
            logger.info(
                "Goal LEFT — score %d:%d", self._score_left, self._score_right
            )

        self._prev_in_left = in_left
        self._prev_in_right = in_right
        return event

    def reset(self) -> None:
        self._score_left = 0
        self._score_right = 0
        self._frames_since_goal = self._cooldown_frames
        self._prev_in_left = False
        self._prev_in_right = False
        logger.debug("GoalDetector reset.")

    def draw(self, frame: np.ndarray) -> None:
        """Draw goal zone outlines onto *frame* for HUD overlay."""
        for zone in (self._zone_left, self._zone_right):
            if zone is None:
                continue
            cv2.rectangle(
                frame,
                (zone.x, zone.y),
                (zone.x + zone.w, zone.y + zone.h),
                (0, 60, 220),
                2,
            )
            cv2.putText(
                frame,
                f"Tor {zone.name}",
                (zone.x, zone.y - 6),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.45,
                (0, 60, 220),
                1,
            )

    def _rebuild_default_zones(
            self,
            field_y1: int = 0,
            field_y2: int = 480,
    ) -> None:
        field_height = field_y2 - field_y1
        goal_height = max(20, int(field_height * _GOAL_HEIGHT_RATIO))
        goal_y = field_y1 + (field_height - goal_height) // 2

        self._zone_left = _GoalZone(
            name="Left",
            x=self._field_x1,
            y=goal_y,
            w=self._goal_zone_width,
            h=goal_height,
            scoring_team=Team.RIGHT,
            use_y_bounds=True,  # ✅ y wird berücksichtigt
        )

        self._zone_right = _GoalZone(
            name="Right",
            x=self._field_x2 - self._goal_zone_width,
            y=goal_y,
            w=self._goal_zone_width,
            h=goal_height,
            scoring_team=Team.LEFT,
            use_y_bounds=True,
        )

