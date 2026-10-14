import time
from typing import Dict, List, Optional, Tuple
import cv2
import numpy as np
from core.tracker import HandData
from modules.app_manager import AppManager
from ui.keyboard_layout import KeyboardLayout, VirtualKey


class HUDOverlay:
    """Renders sleek Apple Vision Pro inspired spatial HUD on camera frames."""

    def __init__(self, frame_w: int, frame_h: int):
        self.frame_w = frame_w
        self.frame_h = frame_h

        # Notification / action toast
        self.toast_msg: Optional[str] = None
        self.toast_expiry: float = 0.0

        # Colors (BGR)
        self.COLOR_BG = (20, 20, 25)
        self.COLOR_PRIMARY = (255, 180, 0)       # Cyan-amber
        self.COLOR_ACCENT = (50, 220, 100)       # Bright Green
        self.COLOR_ALERT = (40, 40, 255)         # Red
        self.COLOR_TEXT = (245, 245, 245)        # Crisp White
        self.COLOR_HOVER = (0, 215, 255)         # Gold / Yellow
        self.COLOR_PRESSED = (0, 255, 128)       # Neon Green

    def show_toast(self, message: str, duration: float = 1.2):
        self.toast_msg = message
        self.toast_expiry = time.time() + duration

    def draw_top_bar(
        self,
        frame: np.ndarray,
        fps: float,
        mode_name: str,
        left_gesture: str,
        right_gesture: str,
    ):
        """Renders top info bar with glassmorphic aesthetic."""
        h, w, _ = frame.shape
        overlay = frame.copy()

        # Header bar background
        bar_h = 44
        cv2.rectangle(overlay, (0, 0), (w, bar_h), (15, 15, 20), -1)
        cv2.addWeighted(overlay, 0.65, frame, 0.35, 0, frame)

        # Mode Badge
        mode_text = f"MODE: {mode_name.upper()}"
        cv2.putText(frame, mode_text, (16, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 255), 2)

        # Hands Status
        l_text = f"L: {left_gesture}"
        r_text = f"R: {right_gesture}"
        cv2.putText(frame, l_text, (w // 2 - 120, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (200, 200, 200), 1)
        cv2.putText(frame, r_text, (w // 2 + 30, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (200, 200, 200), 1)

        # FPS
        fps_text = f"FPS: {int(fps)}"
        cv2.putText(frame, fps_text, (w - 110, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (100, 255, 100), 2)

    def draw_camera_alert(self, frame: np.ndarray, title: str, instructions: List[str]):
        """Renders an attention modal if camera feed is blank/green or inactive."""
        h, w, _ = frame.shape
        modal_w = 640
        modal_h = 240
        x1 = (w - modal_w) // 2
        y1 = (h - modal_h) // 2
        x2 = x1 + modal_w
        y2 = y1 + modal_h

        overlay = frame.copy()
        cv2.rectangle(overlay, (x1, y1), (x2, y2), (25, 25, 30), -1)
        cv2.addWeighted(overlay, 0.90, frame, 0.10, 0, frame)
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 165, 255), 2)  # Amber-orange border

        # Title
        cv2.putText(frame, f"[!] {title}", (x1 + 30, y1 + 45), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 215, 255), 2)

        # Instructions lines
        for i, text in enumerate(instructions):
            cv2.putText(
                frame,
                text,
                (x1 + 30, y1 + 90 + i * 35),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                (230, 230, 230),
                1,
            )

    def draw_active_box(self, frame: np.ndarray, padding: float):
        """Draws bounding box mapping camera coordinate space to monitor."""
        h, w, _ = frame.shape
        x1 = int(w * padding)
        y1 = int(h * padding)
        x2 = int(w * (1.0 - padding))
        y2 = int(h * (1.0 - padding))

        # Thin corner brackets
        corner_len = 24
        color = (180, 180, 180)
        thick = 2

        # Top-Left
        cv2.line(frame, (x1, y1), (x1 + corner_len, y1), color, thick)
        cv2.line(frame, (x1, y1), (x1, y1 + corner_len), color, thick)
        # Top-Right
        cv2.line(frame, (x2, y1), (x2 - corner_len, y1), color, thick)
        cv2.line(frame, (x2, y1), (x2, y1 + corner_len), color, thick)
        # Bottom-Left
        cv2.line(frame, (x1, y2), (x1 + corner_len, y2), color, thick)
        cv2.line(frame, (x1, y2), (x1, y2 - corner_len), color, thick)
        # Bottom-Right
        cv2.line(frame, (x2, y2), (x2 - corner_len, y2), color, thick)
        cv2.line(frame, (x2, y2), (x2, y2 - corner_len), color, thick)

    def draw_app_dock(
        self,
        frame: np.ndarray,
        apps: List[Dict],
        cursor_px: Optional[Tuple[int, int]],
    ) -> Optional[str]:
        """
        Renders Left-Hand App Launcher Dock.
        Returns app_key if hovered cursor is currently over it.
        """
        h, w, _ = frame.shape
        dock_w = 170
        dock_x = 20
        dock_y = 60
        tile_h = 48
        gap = 8

        hovered_app_key = None

        overlay = frame.copy()
        total_dock_h = len(apps) * (tile_h + gap) + 40
        cv2.rectangle(
            overlay,
            (dock_x - 10, dock_y - 30),
            (dock_x + dock_w + 10, dock_y + total_dock_h - 20),
            (25, 25, 30),
            -1,
        )
        cv2.addWeighted(overlay, 0.70, frame, 0.30, 0, frame)

        # Title
        cv2.putText(
            frame,
            "APP LAUNCHER",
            (dock_x, dock_y - 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.50,
            (0, 220, 255),
            2,
        )

        for i, app in enumerate(apps):
            y1 = dock_y + i * (tile_h + gap)
            y2 = y1 + tile_h
            x1 = dock_x
            x2 = dock_x + dock_w

            is_hovered = False
            if cursor_px:
                cx, cy = cursor_px
                if x1 <= cx <= x2 and y1 <= cy <= y2:
                    is_hovered = True
                    hovered_app_key = app["key"]

            # Background
            bg_color = (60, 140, 240) if is_hovered else (45, 45, 55)
            cv2.rectangle(frame, (x1, y1), (x2, y2), bg_color, -1)
            cv2.rectangle(frame, (x1, y1), (x2, y2), (100, 100, 120), 1)

            # Label
            label = f"{app['icon']} {app['name']}"
            cv2.putText(
                frame,
                label,
                (x1 + 12, y1 + 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                (255, 255, 255),
                2 if is_hovered else 1,
            )

        return hovered_app_key

    def draw_virtual_keyboard(
        self,
        frame: np.ndarray,
        layout: KeyboardLayout,
        hovered_keys: List[Tuple[VirtualKey, str]],
        pressed_key: Optional[VirtualKey],
        fingers_px: List[Tuple[int, int, str]],
    ):
        """Draws semi-transparent virtual keyboard overlay with dual fingertips."""
        overlay = frame.copy()

        # Keyboard backdrop
        if layout.keys:
            kb_x1 = min(k.x1 for k in layout.keys) - 14
            kb_y1 = min(k.y1 for k in layout.keys) - 14
            kb_x2 = max(k.x2 for k in layout.keys) + 14
            kb_y2 = max(k.y2 for k in layout.keys) + 14
            cv2.rectangle(overlay, (kb_x1, kb_y1), (kb_x2, kb_y2), (20, 20, 25), -1)

        # Draw individual keys on overlay
        hovered_set = {k.char for k, _ in hovered_keys}
        pressed_char = pressed_key.char if pressed_key else None

        for key in layout.keys:
            if key.char == pressed_char:
                key_color = self.COLOR_PRESSED
            elif key.char in hovered_set:
                key_color = self.COLOR_HOVER
            elif key.is_special:
                key_color = (65, 55, 75)
            else:
                key_color = (50, 50, 60)

            # Key block
            cv2.rectangle(overlay, (key.x1, key.y1), (key.x2, key.y2), key_color, -1)
            cv2.rectangle(overlay, (key.x1, key.y1), (key.x2, key.y2), (120, 120, 140), 1)

        # Blend keyboard overlay
        cv2.addWeighted(overlay, 0.72, frame, 0.28, 0, frame)

        # Render labels crisp on top
        for key in layout.keys:
            # Center text inside key
            font_scale = 0.50 if len(key.display_label) > 2 else 0.65
            thick = 2 if (key.char in hovered_set or key.char == pressed_char) else 1
            text_size = cv2.getTextSize(key.display_label, cv2.FONT_HERSHEY_SIMPLEX, font_scale, thick)[0]
            tx = key.x1 + (key.x2 - key.x1 - text_size[0]) // 2
            ty = key.y1 + (key.y2 - key.y1 + text_size[1]) // 2

            text_color = (0, 0, 0) if (key.char in hovered_set or key.char == pressed_char) else self.COLOR_TEXT
            cv2.putText(frame, key.display_label, (tx, ty), cv2.FONT_HERSHEY_SIMPLEX, font_scale, text_color, thick)

        # Draw dual-finger laser reticles
        for fx, fy, hand_label in fingers_px:
            ring_color = (255, 200, 0) if hand_label == "Left" else (0, 200, 255)
            cv2.circle(frame, (fx, fy), 12, ring_color, 2)
            cv2.circle(frame, (fx, fy), 3, (0, 255, 0), -1)

    def draw_toasts(self, frame: np.ndarray):
        """Displays transient status toasts in bottom-right corner."""
        if self.toast_msg and time.time() < self.toast_expiry:
            h, w, _ = frame.shape
            overlay = frame.copy()

            text = self.toast_msg
            text_size = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.65, 2)[0]
            box_w = text_size[0] + 30
            box_h = text_size[1] + 20

            x1 = w - box_w - 20
            y1 = h - box_h - 20
            x2 = w - 20
            y2 = h - 20

            cv2.rectangle(overlay, (x1, y1), (x2, y2), (20, 20, 20), -1)
            cv2.addWeighted(overlay, 0.8, frame, 0.2, 0, frame)
            cv2.rectangle(frame, (x1, y1), (x2, y2), self.COLOR_PRIMARY, 2)
            cv2.putText(frame, text, (x1 + 15, y1 + text_size[1] + 8), cv2.FONT_HERSHEY_SIMPLEX, 0.65, self.COLOR_PRIMARY, 2)
