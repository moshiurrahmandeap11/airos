import time
from typing import Optional, Tuple
import pyautogui
from pynput.mouse import Button, Controller as PynputMouse
from core.smoother import Point2DSmoother
from core.tracker import HandData, HandLandmarkIndex


class MouseController:
    """Controls OS mouse cursor, clicks, drags, and scrolling with jitter smoothing."""

    def __init__(self, active_padding: float = 0.15, click_cooldown: float = 0.28):
        self.mouse = PynputMouse()
        self.smoother = Point2DSmoother(min_cutoff=1.5, beta=0.007)

        # Get primary display resolution
        self.screen_w, self.screen_h = pyautogui.size()

        self.active_padding = active_padding
        self.click_cooldown = click_cooldown

        self.last_click_time = 0.0
        self.is_dragging = False
        self.pinch_start_time: Optional[float] = None

        # Scroll tracking
        self.prev_scroll_y: Optional[float] = None

    def update(
        self,
        hand: Optional[HandData],
        is_pinching_index: bool,
        is_pinching_middle: bool,
        is_scrolling: bool,
    ) -> dict:
        """
        Process hand landmarks and update mouse state.
        Returns dict of actions performed for HUD feedback.
        """
        status = {
            "cursor_pos": None,
            "clicked": False,
            "right_clicked": False,
            "dragging": self.is_dragging,
            "scrolling": False,
        }

        if hand is None:
            if self.is_dragging:
                self.mouse.release(Button.left)
                self.is_dragging = False
            self.pinch_start_time = None
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

        # Apply One-Euro filter
        smooth_x, smooth_y = self.smoother.smooth(raw_screen_x, raw_screen_y)
        smooth_x = max(0, min(self.screen_w - 1, int(smooth_x)))
        smooth_y = max(0, min(self.screen_h - 1, int(smooth_y)))

        # Update cursor unless we are actively scrolling
        if not is_scrolling:
            self.mouse.position = (smooth_x, smooth_y)
            status["cursor_pos"] = (smooth_x, smooth_y)

        curr_time = time.time()

        # 2. Right Click (Thumb + Middle finger pinch)
        if is_pinching_middle:
            if curr_time - self.last_click_time > self.click_cooldown:
                self.mouse.click(Button.right)
                self.last_click_time = curr_time
                status["right_clicked"] = True
            return status

        # 3. Left Click & Drag (Thumb + Index finger pinch)
        if is_pinching_index:
            if self.pinch_start_time is None:
                self.pinch_start_time = curr_time

            duration = curr_time - self.pinch_start_time
            # Pinch held > 0.35s = start Dragging
            if duration > 0.35 and not self.is_dragging:
                self.mouse.press(Button.left)
                self.is_dragging = True
                status["dragging"] = True
        else:
            if self.is_dragging:
                # Release drag
                self.mouse.release(Button.left)
                self.is_dragging = False
                status["dragging"] = False
            elif self.pinch_start_time is not None:
                duration = curr_time - self.pinch_start_time
                # Quick pinch release = Single Left Click
                if duration < 0.35 and (curr_time - self.last_click_time > self.click_cooldown):
                    self.mouse.click(Button.left)
                    self.last_click_time = curr_time
                    status["clicked"] = True
            self.pinch_start_time = None

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
