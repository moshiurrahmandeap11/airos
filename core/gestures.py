from enum import Enum
from typing import Optional
from core.tracker import HandData, HandLandmarkIndex


class GestureType(Enum):
    IDLE = "Idle"
    POINTING = "1 Finger (Point)"
    TWO_FINGERS = "2 Fingers"
    THREE_FINGERS = "3 Fingers"
    FOUR_FINGERS = "4 Fingers"
    OPEN_PALM = "Open Palm (5)"
    FIST = "Fist (0)"
    PINCH_INDEX = "Pinch Index"
    PINCH_MIDDLE = "Pinch Middle"
    SCROLL = "Scroll"
    PEACE = "Peace"


class GestureRecognizer:
    """Classifies single-hand postures into clean, distinct high-level gestures without mistouches."""

    @staticmethod
    def classify(hand: Optional[HandData]) -> GestureType:
        if hand is None:
            return GestureType.IDLE

        states = hand.finger_states
        count = getattr(hand, "extended_count", sum(1 for v in states.values() if v))

        # 1. Closed Fist: Must take priority over pinch to prevent fist being mistaken for click!
        is_all_fingers_curled = not states.get("index") and not states.get("middle") and not states.get("ring") and not states.get("pinky")
        if count == 0 or is_all_fingers_curled:
            return GestureType.FIST

        # 2. Open Palm (4 or 5 fingers open)
        if count >= 4:
            return GestureType.OPEN_PALM

        # 3. Deliberate Pinch Detection (Threshold 0.26 to prevent accidental mistouches while pointing)
        if states.get("index") and hand.is_pinching(HandLandmarkIndex.INDEX_FINGER_TIP, threshold_ratio=0.26):
            return GestureType.PINCH_INDEX

        if states.get("middle") and hand.is_pinching(HandLandmarkIndex.MIDDLE_FINGER_TIP, threshold_ratio=0.26):
            return GestureType.PINCH_MIDDLE

        # 4. 3 Fingers (Index + Middle + Ring open, Pinky closed)
        if states.get("index") and states.get("middle") and states.get("ring") and not states.get("pinky"):
            return GestureType.THREE_FINGERS

        # 5. 2 Fingers / Scroll / Peace (Index + Middle open, Ring + Pinky closed)
        if states.get("index") and states.get("middle") and not states.get("ring") and not states.get("pinky"):
            dist_index_middle = hand.get_norm_dist(
                HandLandmarkIndex.INDEX_FINGER_TIP,
                HandLandmarkIndex.MIDDLE_FINGER_TIP,
            )
            if dist_index_middle < 0.38:
                return GestureType.SCROLL
            return GestureType.PEACE

        # 6. 1 Finger Pointing (Only index extended)
        if states.get("index"):
            return GestureType.POINTING

        return GestureType.IDLE


class WindowResizeTracker:
    """
    Tracks Thumb (bridda) + Index (torjoni) expansion and shrinking to resize windows:
    - Expand: Spreading thumb & index wide apart -> Maximize window (boro hobe)
    - Shrink: Bringing thumb & index close together -> Restore/shrink window (choto hobe)
    """

    def __init__(self, cooldown: float = 0.60):
        self.cooldown = cooldown
        self.last_action_time = 0.0
        self.prev_span: Optional[float] = None
        self.prev_time: float = 0.0

    def update(self, hand: Optional[HandData], current_time: float) -> Optional[str]:
        """Returns 'EXPAND', 'SHRINK', or None."""
        if hand is None:
            self.prev_span = None
            return None

        states = hand.finger_states
        # Only active when middle, ring, pinky are curled into palm
        if states.get("middle") or states.get("ring") or states.get("pinky"):
            self.prev_span = None
            return None

        # Calculate span between Thumb Tip (4) and Index Tip (8)
        span = hand.get_norm_dist(HandLandmarkIndex.THUMB_TIP, HandLandmarkIndex.INDEX_FINGER_TIP)

        if current_time - self.last_action_time < self.cooldown:
            self.prev_span = span
            self.prev_time = current_time
            return None

        action = None
        if self.prev_span is not None and (0.03 <= current_time - self.prev_time <= 0.40):
            d_span = span - self.prev_span
            # Deliberate expand gesture: distance increases and spans wide (>= 0.82)
            if d_span > 0.18 and span >= 0.80:
                action = "EXPAND"
                self.last_action_time = current_time
            # Deliberate shrink gesture: distance decreases and draws close (<= 0.35)
            elif d_span < -0.18 and span <= 0.35:
                action = "SHRINK"
                self.last_action_time = current_time

        self.prev_span = span
        self.prev_time = current_time
        return action


class SwipeTracker:
    """
    Detects natural horizontal hand flick/swipe (Left or Right) across the camera.
    Does NOT require a specific finger posture—works with any natural hand swipe.
    """

    def __init__(self, displacement_threshold: float = 0.08, time_window: float = 0.30, cooldown: float = 0.40):
        self.displacement_threshold = displacement_threshold
        self.time_window = time_window
        self.cooldown = cooldown
        self.history = []  # List of (timestamp, x_norm)
        self.last_swipe_time = 0.0

    def update(
        self,
        current_x: float,
        is_active: bool,
        current_time: float,
        is_mirrored: bool = True,
    ) -> Optional[str]:
        """
        Takes current normalized X coordinate of hand palm center.
        Returns: 'LEFT', 'RIGHT', or None based on physical hand flick direction.
        """
        if not is_active:
            self.history.clear()
            return None

        # Add current point and purge points outside time window
        self.history.append((current_time, current_x))
        self.history = [pt for pt in self.history if current_time - pt[0] <= self.time_window]

        if current_time - self.last_swipe_time < self.cooldown:
            return None

        if len(self.history) >= 2:
            oldest_time, oldest_x = self.history[0]
            dx = current_x - oldest_x
            dt = current_time - oldest_time

            # Check if hand moved fast enough across the screen (flick)
            if 0.04 <= dt <= self.time_window and abs(dx) >= self.displacement_threshold:
                speed = abs(dx) / dt
                if speed > 0.35:  # High speed flick
                    self.last_swipe_time = current_time
                    self.history.clear()
                    # Determine physical direction
                    if is_mirrored:
                        # Moving physically right increases X on screen
                        return "RIGHT" if dx > 0 else "LEFT"
                    else:
                        # In unmirrored camera, moving physically right decreases X in frame
                        return "RIGHT" if dx < 0 else "LEFT"

        return None
