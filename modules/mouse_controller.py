import sys
import time
from typing import Optional, Tuple
import pyautogui
from pynput.mouse import Button, Controller as PynputMouse
from core.smoother import Point2DSmoother
from core.tracker import HandData, HandLandmarkIndex

# Fast Win32 imports for Windows zero-latency input
IS_WINDOWS = sys.platform == "win32"
if IS_WINDOWS:
    import ctypes
    user32 = ctypes.windll.user32

    class POINT(ctypes.Structure):
        _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


class MouseController:
    """Controls OS mouse cursor, clicks, drags, and scrolling with zero-latency smoothing and physical mouse auto-yield."""

    def __init__(self, active_padding: float = 0.12, click_cooldown: float = 0.20):
        self.mouse = PynputMouse()
        # High responsiveness: min_cutoff 2.5 (no lag), beta 0.035 (instant acceleration)
        self.smoother = Point2DSmoother(min_cutoff=2.5, beta=0.035)

        # Get primary display resolution
        self.screen_w, self.screen_h = pyautogui.size()

        self.active_padding = active_padding
        self.click_cooldown = click_cooldown

        self.last_click_time = 0.0
        self.is_dragging = False
        self.pinch_start_time: Optional[float] = None

        # Physical mouse auto-yield tracking
        self.last_set_cursor_pos: Optional[Tuple[int, int]] = None
        self.user_override_until: float = 0.0
        self.override_cooldown_sec: float = 1.2  # Pause gesture cursor for 1.2s if physical mouse is moved

        # Scroll tracking
        self.prev_scroll_y: Optional[float] = None

    def _get_current_pos(self) -> Tuple[int, int]:
        """Reads current hardware cursor position with microsecond Win32 call."""
        if IS_WINDOWS:
            pt = POINT()
            user32.GetCursorPos(ctypes.byref(pt))
            return int(pt.x), int(pt.y)
        else:
            pos = pyautogui.position()
            return int(pos[0]), int(pos[1])

    def _set_pos(self, x: int, y: int):
        if IS_WINDOWS:
            user32.SetCursorPos(x, y)
        else:
            self.mouse.position = (x, y)

    def _click_left(self):
        if IS_WINDOWS:
            user32.mouse_event(0x0002, 0, 0, 0, 0)  # MOUSEEVENTF_LEFTDOWN
            user32.mouse_event(0x0004, 0, 0, 0, 0)  # MOUSEEVENTF_LEFTUP
        else:
            self.mouse.click(Button.left)

    def _click_right(self):
        if IS_WINDOWS:
            user32.mouse_event(0x0008, 0, 0, 0, 0)  # MOUSEEVENTF_RIGHTDOWN
            user32.mouse_event(0x0010, 0, 0, 0, 0)  # MOUSEEVENTF_RIGHTUP
        else:
            self.mouse.click(Button.right)

    def update(
        self,
        hand: Optional[HandData],
        is_pinching_index: bool,
        is_pinching_middle: bool,
        is_scrolling: bool,
    ) -> dict:
        """
        Process hand landmarks and update mouse state with zero latency and physical mouse auto-yield.
        """
        status = {
            "cursor_pos": None,
            "clicked": False,
            "right_clicked": False,
            "dragging": self.is_dragging,
            "scrolling": False,
            "user_overriding": False,
        }

        if hand is None:
            self.last_set_cursor_pos = None
            if IS_WINDOWS:
                user32.mouse_event(0x0004, 0, 0, 0, 0)  # Always release Left button
                user32.mouse_event(0x0010, 0, 0, 0, 0)  # Always release Right button
            self.prev_scroll_y = None
            return status

        curr_time = time.time()

        # Physical Mouse Auto-Yield:
        # If the user touched or moved their physical mouse, yield control completely!
        if self.last_set_cursor_pos is not None:
            cur_x, cur_y = self._get_current_pos()
            dx = cur_x - self.last_set_cursor_pos[0]
            dy = cur_y - self.last_set_cursor_pos[1]
            dist = (dx**2 + dy**2) ** 0.5
            if dist > 18:
                self.user_override_until = curr_time + self.override_cooldown_sec

        if curr_time < self.user_override_until:
            self.smoother.prev_x = None
            self.smoother.prev_y = None
            self.last_set_cursor_pos = self._get_current_pos()
            status["user_overriding"] = True
            return status

        # In a fist or when index is not pointing, park cursor safely without accidental clicks
        is_fist = (hand.extended_count == 0) or (not hand.finger_states.get("index") and not hand.finger_states.get("middle"))
        if is_fist:
            self.prev_scroll_y = None
            return status

        # 1. Cursor Position Mapping (from Index Tip Landmark 8)
        norm_x, norm_y, _ = hand.points_norm[HandLandmarkIndex.INDEX_FINGER_TIP]

        # Map normalized camera coordinate within active bounding box to screen resolution
        pad = self.active_padding
        clamped_x = max(pad, min(1.0 - pad, norm_x))
        clamped_y = max(pad, min(1.0 - pad, norm_y))

        rel_x = (clamped_x - pad) / (1.0 - 2 * pad)
        rel_y = (clamped_y - pad) / (1.0 - 2 * pad)

        raw_screen_x = rel_x * self.screen_w
        raw_screen_y = rel_y * self.screen_h

        # Apply snappy One-Euro filter
        smooth_x, smooth_y = self.smoother.smooth(raw_screen_x, raw_screen_y)
        smooth_x = max(0, min(self.screen_w - 1, int(smooth_x)))
        smooth_y = max(0, min(self.screen_h - 1, int(smooth_y)))

        # Update cursor unless we are actively scrolling
        if not is_scrolling:
            self._set_pos(smooth_x, smooth_y)
            self.last_set_cursor_pos = (smooth_x, smooth_y)
            status["cursor_pos"] = (smooth_x, smooth_y)

        # 2. Right Click (Thumb + Middle finger pinch)
        if is_pinching_middle:
            if curr_time - self.last_click_time > self.click_cooldown:
                self._click_right()
                self.last_click_time = curr_time
                status["right_clicked"] = True
            return status

        # 3. Left Click (Thumb + Index finger pinch)
        # Clean atomic click: Press & Release immediately to avoid OS drag freezes!
        if is_pinching_index:
            if curr_time - self.last_click_time > self.click_cooldown:
                self._click_left()
                self.last_click_time = curr_time
                status["clicked"] = True

        # 4. Scrolling (Two-finger gesture)
        if is_scrolling:
            idx_y = hand.points_norm[HandLandmarkIndex.INDEX_FINGER_TIP][1]
            mid_y = hand.points_norm[HandLandmarkIndex.MIDDLE_FINGER_TIP][1]
            avg_y = (idx_y + mid_y) / 2.0

            if self.prev_scroll_y is not None:
                dy = avg_y - self.prev_scroll_y
                # Invert so moving hand up scrolls page up (positive ticks)
                if abs(dy) > 0.008:
                    scroll_ticks = int(-dy * 120)
                    if scroll_ticks != 0:
                        self.mouse.scroll(0, scroll_ticks)
                        status["scrolling"] = True
            self.prev_scroll_y = avg_y
        else:
            self.prev_scroll_y = None

        return status
