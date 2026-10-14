import math
import os
import urllib.request
from typing import Dict, List, Optional, Tuple
import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import numpy as np


class HandLandmarkIndex:
    WRIST = 0
    THUMB_CMC = 1
    THUMB_MCP = 2
    THUMB_IP = 3
    THUMB_TIP = 4
    INDEX_FINGER_MCP = 5
    INDEX_FINGER_PIP = 6
    INDEX_FINGER_DIP = 7
    INDEX_FINGER_TIP = 8
    MIDDLE_FINGER_MCP = 9
    MIDDLE_FINGER_PIP = 10
    MIDDLE_FINGER_DIP = 11
    MIDDLE_FINGER_TIP = 12
    RING_FINGER_MCP = 13
    RING_FINGER_PIP = 14
    RING_FINGER_DIP = 15
    RING_FINGER_TIP = 16
    PINKY_MCP = 17
    PINKY_PIP = 18
    PINKY_DIP = 19
    PINKY_TIP = 20


# Skeletal connections between the 21 landmarks
HAND_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4),           # Thumb
    (0, 5), (5, 6), (6, 7), (7, 8),           # Index
    (5, 9), (9, 10), (10, 11), (11, 12),      # Middle
    (9, 13), (13, 14), (14, 15), (15, 16),    # Ring
    (13, 17), (0, 17), (17, 18), (18, 19), (19, 20),  # Pinky
]


class HandData:
    """Holds parsed coordinates and calculated states for a single detected hand."""

    def __init__(
        self,
        label: str,  # 'Left' or 'Right'
        landmarks_list,  # List of normalized landmark objects with .x, .y, .z
        frame_width: int,
        frame_height: int,
    ):
        self.label = label
        self.frame_width = frame_width
        self.frame_height = frame_height

        self.points_px: List[Tuple[int, int, float]] = []
        self.points_norm: List[Tuple[float, float, float]] = []

        for lm in landmarks_list:
            px = int(lm.x * frame_width)
            py = int(lm.y * frame_height)
            self.points_px.append((px, py, lm.z))
            self.points_norm.append((lm.x, lm.y, lm.z))

        self.scale = self._calc_scale()
        self.finger_states = self._calc_finger_states()

    def _calc_scale(self) -> float:
        w = self.points_norm[HandLandmarkIndex.WRIST]
        m = self.points_norm[HandLandmarkIndex.MIDDLE_FINGER_MCP]
        return math.sqrt((w[0] - m[0]) ** 2 + (w[1] - m[1]) ** 2) + 1e-6

    def _calc_finger_states(self) -> Dict[str, bool]:
        states = {}

        # Thumb extension check
        thumb_tip = self.points_norm[HandLandmarkIndex.THUMB_TIP]
        thumb_ip = self.points_norm[HandLandmarkIndex.THUMB_IP]

        if self.label == "Right":
            states["thumb"] = thumb_tip[0] < thumb_ip[0]
        else:
            states["thumb"] = thumb_tip[0] > thumb_ip[0]

        # 4 Fingers: Open if tip is higher (smaller y) than PIP joint
        fingers = [
            ("index", HandLandmarkIndex.INDEX_FINGER_TIP, HandLandmarkIndex.INDEX_FINGER_PIP),
            ("middle", HandLandmarkIndex.MIDDLE_FINGER_TIP, HandLandmarkIndex.MIDDLE_FINGER_PIP),
            ("ring", HandLandmarkIndex.RING_FINGER_TIP, HandLandmarkIndex.RING_FINGER_PIP),
            ("pinky", HandLandmarkIndex.PINKY_TIP, HandLandmarkIndex.PINKY_PIP),
        ]

        for name, tip_idx, pip_idx in fingers:
            tip_y = self.points_norm[tip_idx][1]
            pip_y = self.points_norm[pip_idx][1]
            states[name] = tip_y < (pip_y - 0.01)

        return states

    def get_norm_dist(self, idx1: int, idx2: int) -> float:
        p1 = self.points_norm[idx1]
        p2 = self.points_norm[idx2]
        euclidean = math.sqrt((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2)
        return euclidean / self.scale

    def is_pinching(self, finger_idx: int = HandLandmarkIndex.INDEX_FINGER_TIP, threshold_ratio: float = 0.28) -> bool:
        return self.get_norm_dist(HandLandmarkIndex.THUMB_TIP, finger_idx) < threshold_ratio


class DualHandTracker:
    """Modern MediaPipe Tasks HandLandmarker wrapper for simultaneous dual-hand tracking."""

    MODEL_URL = "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"

    def __init__(
        self,
        model_path: str = "models/hand_landmarker.task",
        max_num_hands: int = 2,
        min_detection_confidence: float = 0.7,
        min_tracking_confidence: float = 0.6,
        mirrored_camera: bool = True,
    ):
        self.mirrored_camera = mirrored_camera
        self.model_path = model_path
        self._ensure_model_exists()

        base_options = python.BaseOptions(model_asset_path=self.model_path)
        options = vision.HandLandmarkerOptions(
            base_options=base_options,
            running_mode=vision.RunningMode.IMAGE,
            num_hands=max_num_hands,
            min_hand_detection_confidence=min_detection_confidence,
            min_hand_presence_confidence=min_tracking_confidence,
            min_tracking_confidence=min_tracking_confidence,
        )
        self.landmarker = vision.HandLandmarker.create_from_options(options)

    def _ensure_model_exists(self):
        if not os.path.exists(self.model_path):
            os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
            print(f"[DualHandTracker] Downloading MediaPipe hand model to {self.model_path}...")
            urllib.request.urlretrieve(self.MODEL_URL, self.model_path)
            print("[DualHandTracker] Model downloaded successfully.")

    def process(self, frame_rgb: np.ndarray, frame_bgr: np.ndarray) -> Dict[str, Optional[HandData]]:
        h, w, _ = frame_bgr.shape
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)
        result = self.landmarker.detect(mp_image)

        detected_hands: Dict[str, Optional[HandData]] = {"Left": None, "Right": None}

        if result.hand_landmarks and result.handedness:
            for lms, handedness_list in zip(result.hand_landmarks, result.handedness):
                raw_label = handedness_list[0].category_name

                # In mirrored camera view, invert label so user's physical right hand is "Right"
                if self.mirrored_camera:
                    actual_label = "Right" if raw_label == "Left" else "Left"
                else:
                    actual_label = raw_label

                detected_hands[actual_label] = HandData(
                    label=actual_label,
                    landmarks_list=lms,
                    frame_width=w,
                    frame_height=h,
                )

        return detected_hands

    def draw_landmarks(self, frame: np.ndarray, hand_data: HandData):
        """Draws skeletal lines and joint dots directly on the frame."""
        line_color = (0, 220, 100) if hand_data.label == "Right" else (240, 180, 0)
        joint_color = (255, 255, 255)

        # Draw bone connections
        for start_idx, end_idx in HAND_CONNECTIONS:
            p1 = hand_data.points_px[start_idx][:2]
            p2 = hand_data.points_px[end_idx][:2]
            cv2.line(frame, p1, p2, line_color, 2)

        # Draw joint circles
        for pt in hand_data.points_px:
            cv2.circle(frame, (pt[0], pt[1]), 3, joint_color, -1)
