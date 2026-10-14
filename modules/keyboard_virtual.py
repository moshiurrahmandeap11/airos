import time
from typing import Dict, Optional, Tuple
from pynput.keyboard import Controller as KeyboardController, Key
from core.tracker import HandData, HandLandmarkIndex
from ui.keyboard_layout import KeyboardLayout, VirtualKey


class VirtualKeyboardManager:
    """Manages Vision Pro style dual-hand virtual air typing."""

    def __init__(self, frame_w: int, frame_h: int, cooldown_sec: float = 0.30):
        self.layout = KeyboardLayout(frame_w, frame_h)
        self.keyboard = KeyboardController()
        self.cooldown_sec = cooldown_sec

        self.is_active = False
        self.last_press_time = 0.0
        self.last_pressed_char: Optional[str] = None

    def toggle(self):
        self.is_active = not self.is_active
        print(f"[VirtualKeyboard] Active state: {self.is_active}")

    def update(
        self,
        left_hand: Optional[HandData],
        right_hand: Optional[HandData],
    ) -> Dict:
        """
        Processes index fingertips from both hands against virtual keys.
        Supports pinching or air-tap depth trigger.
        """
        status = {
            "active": self.is_active,
            "hovered_keys": [],  # List of VirtualKey
            "pressed_key": None,
            "fingers_px": [],
        }

        if not self.is_active:
            return status

        curr_time = time.time()
        hands = [("Left", left_hand), ("Right", right_hand)]

        for label, hand in hands:
            if hand is None:
                continue

            # Index fingertip pixel location
            idx_px = hand.points_px[HandLandmarkIndex.INDEX_FINGER_TIP]
            px_x, px_y, pz = idx_px[0], idx_px[1], idx_px[2]
            status["fingers_px"].append((px_x, px_y, label))

            # Hit-test key
            key = self.layout.find_key(px_x, px_y)
            if key:
                status["hovered_keys"].append((key, label))

                # Check trigger: Pinching index+thumb while hovering over key
                # Or air-tap (depth z < threshold)
                is_pinching = hand.is_pinching(HandLandmarkIndex.INDEX_FINGER_TIP, threshold_ratio=0.30)

                if is_pinching:
                    if curr_time - self.last_press_time > self.cooldown_sec:
                        self._trigger_key(key)
                        self.last_press_time = curr_time
                        status["pressed_key"] = key
                        break  # Prevent dual-trigger in same frame

        return status

    def _trigger_key(self, key: VirtualKey):
        """Dispatches actual keypress event to the operating system."""
        char = key.char
        self.last_pressed_char = key.display_label
        print(f"[VirtualKeyboard] Typed: {key.display_label}")

        if char == "SPACE":
            self.keyboard.press(Key.space)
            self.keyboard.release(Key.space)
        elif char == "BACKSPACE":
            self.keyboard.press(Key.backspace)
            self.keyboard.release(Key.backspace)
        elif char == "ENTER":
            self.keyboard.press(Key.enter)
            self.keyboard.release(Key.enter)
        elif char == "CLOSE":
            self.is_active = False
        else:
            # Normal alphabetical character (lowercase)
            self.keyboard.type(char.lower())
