import json
import os
import time
from typing import Optional, Tuple, Union
import cv2
import numpy as np


class CameraManager:
    """Manages webcam capture, supports DroidCam virtual device and IP stream."""

    def __init__(self, config_path: str = "config/settings.json"):
        self.config_path = config_path
        self.source = 0
        self.mirror_camera = False
        self.target_width = 1280
        self.target_height = 720
        self._load_settings()
        self.cap: Optional[cv2.VideoCapture] = None
        self.is_green_placeholder = False

    def _load_settings(self):
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    cfg = data.get("camera", {})
                    src = cfg.get("source", 0)
                    if isinstance(src, str) and src.isdigit():
                        src = int(src)
                    self.source = src
                    self.mirror_camera = cfg.get("mirror_camera", False)
                    self.target_width = cfg.get("width", 1280)
                    self.target_height = cfg.get("height", 720)
            except Exception as e:
                print(f"[CameraManager] Error reading config: {e}")

    def toggle_mirror(self) -> bool:
        self.mirror_camera = not self.mirror_camera
        print(f"[CameraManager] Mirror camera toggled to: {self.mirror_camera}")
        return self.mirror_camera

    def open(self, width: int = 1280, height: int = 720) -> Tuple[bool, int, int]:
        """Attempts to open the configured camera source."""
        print(f"[CameraManager] Attempting to open camera source: {self.source}")

        if isinstance(self.source, int):
            # Try DirectShow first on Windows, fallback to default
            self.cap = cv2.VideoCapture(self.source)
        else:
            # IP stream or video path
            self.cap = cv2.VideoCapture(self.source)

        if not self.cap.isOpened():
            return False, 0, 0

        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)

        ret, test_frame = self.cap.read()
        if not ret or test_frame is None:
            return False, 0, 0

        h, w, _ = test_frame.shape
        return True, w, h

    def read(self) -> Tuple[bool, Optional[np.ndarray], bool]:
        """
        Reads a frame and checks if it's an inactive DroidCam green placeholder.
        Returns: (ret, frame, is_inactive_green_screen)
        """
        if self.cap is None:
            return False, None, False

        ret, frame = self.cap.read()
        if not ret or frame is None:
            return False, None, False

        # Detect DroidCam solid green placeholder
        # Typical DroidCam inactive green: G in [45, 120], B < 30, R < 30, low variance
        mean_b = np.mean(frame[:, :, 0])
        mean_g = np.mean(frame[:, :, 1])
        mean_r = np.mean(frame[:, :, 2])
        std_g = np.std(frame[:, :, 1])

        # Solid green screen detection
        if mean_g > 35 and mean_r < 30 and mean_b < 30 and std_g < 25:
            self.is_green_placeholder = True
        else:
            self.is_green_placeholder = False

        return True, frame, self.is_green_placeholder

    def release(self):
        if self.cap:
            self.cap.release()
            self.cap = None
