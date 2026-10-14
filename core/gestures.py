from enum import Enum
from typing import Optional
from core.tracker import HandData, HandLandmarkIndex


class GestureType(Enum):
    IDLE = "Idle"
    POINTING = "Pointing"
    PINCH_INDEX = "Pinch_Index"
    PINCH_MIDDLE = "Pinch_Middle"
    SCROLL = "Scroll"
    OPEN_PALM = "Open_Palm"
    FIST = "Fist"
    PEACE = "Peace"
    THREE_FINGERS = "Three_Fingers"


class GestureRecognizer:
    """Classifies single-hand postures into distinct high-level gestures."""

    @staticmethod
    def classify(hand: Optional[HandData]) -> GestureType:
        if hand is None:
            return GestureType.IDLE

        states = hand.finger_states
        thumb = states.get("thumb", False)
        index = states.get("index", False)
        middle = states.get("middle", False)
        ring = states.get("ring", False)
        pinky = states.get("pinky", False)

        # 1. Open Palm (All 5 fingers extended)
        if thumb and index and middle and ring and pinky:
            return GestureType.OPEN_PALM

        # 2. Fist (All fingers folded)
        if not index and not middle and not ring and not pinky:
            return GestureType.FIST

        # 3. 3 Fingers (Index, Middle, Ring extended, Pinky folded)
        if index and middle and ring and not pinky:
            return GestureType.THREE_FINGERS

        # 4. Pinching Detection (Thumb + Index or Thumb + Middle)
        # Check pinch first even if index is nominally extended
        if hand.is_pinching(HandLandmarkIndex.INDEX_FINGER_TIP, threshold_ratio=0.32):
            return GestureType.PINCH_INDEX

        if hand.is_pinching(HandLandmarkIndex.MIDDLE_FINGER_TIP, threshold_ratio=0.32):
            return GestureType.PINCH_MIDDLE

        # 5. Scroll (Index + Middle both extended, Ring & Pinky folded)
        if index and middle and not ring and not pinky:
            # Check distance between index tip and middle tip (must be close together)
            dist_index_middle = hand.get_norm_dist(
                HandLandmarkIndex.INDEX_FINGER_TIP,
                HandLandmarkIndex.MIDDLE_FINGER_TIP,
            )
            if dist_index_middle < 0.45:
                return GestureType.SCROLL
            else:
                return GestureType.PEACE

        # 6. Pointing (Index extended, others folded)
        if index and not middle and not ring and not pinky:
            return GestureType.POINTING

        return GestureType.IDLE


class SwipeTracker:
    """Tracks horizontal displacement over time to detect left and right swipes."""

    def __init__(self, displacement_threshold: float = 0.055, time_window: float = 0.45, cooldown: float = 0.45):
        self.displacement_threshold = displacement_threshold
        self.time_window = time_window
        self.cooldown = cooldown
        self.history = []  # List of (timestamp, x_norm)
        self.last_swipe_time = 0.0

    def update(self, current_x: float, is_active: bool, current_time: float) -> Optional[str]:
        """
        Takes current normalized X coordinate of hand and whether target posture is active.
        Returns: 'LEFT', 'RIGHT', or None.
        """
        if not is_active:
            self.history.clear()
            return None

        # Clean old points
        self.history.append((current_time, current_x))
        self.history = [pt for pt in self.history if current_time - pt[0] <= self.time_window]

        if current_time - self.last_swipe_time < self.cooldown:
            return None

        if len(self.history) >= 2:
            oldest_time, oldest_x = self.history[0]
            dx = current_x - oldest_x
            dt = current_time - oldest_time

            if dt >= 0.04 and abs(dx) >= self.displacement_threshold:
                self.last_swipe_time = current_time
                self.history.clear()
                # In mirrored view:
                # dx > 0 means hand moved right on screen -> Swipe Right
                # dx < 0 means hand moved left on screen -> Swipe Left
                return "RIGHT" if dx > 0 else "LEFT"

        return None
