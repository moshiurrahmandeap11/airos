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

        # 3. Pinching Detection (Thumb + Index or Thumb + Middle)
        # Check pinch first even if index is nominally extended
        if hand.is_pinching(HandLandmarkIndex.INDEX_FINGER_TIP, threshold_ratio=0.32):
            return GestureType.PINCH_INDEX

        if hand.is_pinching(HandLandmarkIndex.MIDDLE_FINGER_TIP, threshold_ratio=0.32):
            return GestureType.PINCH_MIDDLE

        # 4. Scroll (Index + Middle both extended, Ring & Pinky folded)
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

        # 5. Pointing (Index extended, others folded)
        if index and not middle and not ring and not pinky:
            return GestureType.POINTING

        return GestureType.IDLE
