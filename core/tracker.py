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
        self.extended_count = sum(1 for v in self.finger_states.values() if v)

    def _dist3d(self, idx1: int, idx2: int) -> float:
        p1 = self.points_norm[idx1]
        p2 = self.points_norm[idx2]
        return math.sqrt((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2 + (p1[2] - p2[2]) ** 2)

    def _calc_scale(self) -> float:
        w = self.points_norm[HandLandmarkIndex.WRIST]
        m = self.points_norm[HandLandmarkIndex.MIDDLE_FINGER_MCP]
        return math.sqrt((w[0] - m[0]) ** 2 + (w[1] - m[1]) ** 2) + 1e-6

    def _calc_finger_states(self) -> Dict[str, bool]:
        """
        3D Rotation-Invariant Finger Extension Classifier.
        Accurately identifies open vs curled fingers in ANY hand orientation (tilted, sideways, upside down).
        """
        states = {}
        wrist_idx = HandLandmarkIndex.WRIST

        # 4 Fingers: Open if tip is farther from wrist than PIP joint
        fingers = [
            ("index", HandLandmarkIndex.INDEX_FINGER_TIP, HandLandmarkIndex.INDEX_FINGER_PIP),
            ("middle", HandLandmarkIndex.MIDDLE_FINGER_TIP, HandLandmarkIndex.MIDDLE_FINGER_PIP),
            ("ring", HandLandmarkIndex.RING_FINGER_TIP, HandLandmarkIndex.RING_FINGER_PIP),
            ("pinky", HandLandmarkIndex.PINKY_TIP, HandLandmarkIndex.PINKY_PIP),
        ]

        for name, tip_idx, pip_idx in fingers:
            d_tip_wrist = self._dist3d(tip_idx, wrist_idx)
            d_pip_wrist = self._dist3d(pip_idx, wrist_idx)
            states[name] = d_tip_wrist > (d_pip_wrist * 1.05)

        # Thumb: Open if thumb tip is extended away from pinky base
        d_thumb_tip_pinky = self._dist3d(HandLandmarkIndex.THUMB_TIP, HandLandmarkIndex.PINKY_MCP)
        d_thumb_ip_pinky = self._dist3d(HandLandmarkIndex.THUMB_IP, HandLandmarkIndex.PINKY_MCP)
        states["thumb"] = d_thumb_tip_pinky > (d_thumb_ip_pinky * 1.08)

        return states

    def get_norm_dist(self, idx1: int, idx2: int) -> float:
        p1 = self.points_norm[idx1]
        p2 = self.points_norm[idx2]
        euclidean = math.sqrt((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2)
        return euclidean / self.scale

    def is_pinching(self, finger_idx: int = HandLandmarkIndex.INDEX_FINGER_TIP, threshold_ratio: float = 0.35) -> bool:
        return self.get_norm_dist(HandLandmarkIndex.THUMB_TIP, finger_idx) < threshold_ratio


class DualHandTracker:
    """Modern MediaPipe Tasks HandLandmarker wrapper for simultaneous dual-hand tracking."""

    MODEL_URL = "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"

    def __init__(
        self,
        model_path: str = "models/hand_landmarker.task",
        max_num_hands: int = 2,
        min_detection_confidence: float = 0.58,
        min_tracking_confidence: float = 0.50,
        swap_hands: bool = False,
    ):
        self.swap_hands = swap_hands
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

    def toggle_swap_hands(self) -> bool:
        self.swap_hands = not self.swap_hands
        print(f"[DualHandTracker] Swapped hands mode: {self.swap_hands}")
        return self.swap_hands

    def _ensure_model_exists(self):
        if not os.path.exists(self.model_path):
            os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
            print(f"[DualHandTracker] Downloading MediaPipe hand model to {self.model_path}...")
            urllib.request.urlretrieve(self.MODEL_URL, self.model_path)
            print("[DualHandTracker] Model downloaded successfully.")

    def _is_valid_hand(self, lms, category) -> bool:
        """
        Biomechanical filter to reject facial contours (cheeks, nose, neck) and background noise,
        while reliably accepting real hands at any tilt, fist, or pinch angle.
        """
        # 1. MediaPipe handedness confidence score
        score = getattr(category, "score", 1.0)
        if score < 0.58:
            return False

        # 2. Palm Length: Landmark 0 (Wrist) to Landmark 9 (Middle MCP)
        w_pt = (lms[0].x, lms[0].y)
        m_pt = (lms[9].x, lms[9].y)
        palm_len = math.hypot(w_pt[0] - m_pt[0], w_pt[1] - m_pt[1])
        if not (0.070 <= palm_len <= 0.70):
            return False

        # 3. Palm Width: Landmark 5 (Index MCP) to Landmark 17 (Pinky MCP)
        idx_mcp = (lms[5].x, lms[5].y)
        pky_mcp = (lms[17].x, lms[17].y)
        palm_width = math.hypot(idx_mcp[0] - pky_mcp[0], idx_mcp[1] - pky_mcp[1])
        if palm_width < 0.030:
            return False

        # 4. Aspect Ratio of Palm: width / length (tilted fists can be ~0.18, open hand ~0.8-1.1)
        aspect_ratio = palm_width / palm_len
        if not (0.16 <= aspect_ratio <= 1.50):
            return False

        # 5. Triangle Area: Wrist(0), Index MCP(5), Pinky MCP(17)
        # Real palm base forms a 2D planar triangle; facial artifacts are collinear
        v1x = idx_mcp[0] - w_pt[0]
        v1y = idx_mcp[1] - w_pt[1]
        v2x = pky_mcp[0] - w_pt[0]
        v2y = pky_mcp[1] - w_pt[1]
        area2 = abs(v1x * v2y - v1y * v2x)
        if area2 < 0.0010:
            return False

        return True

    def process(
        self,
        frame_rgb: np.ndarray,
        frame_bgr: np.ndarray,
        is_mirrored: bool = False,
    ) -> Dict[str, Optional[HandData]]:
        h, w, _ = frame_bgr.shape
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)
        result = self.landmarker.detect(mp_image)

        detected_hands: Dict[str, Optional[HandData]] = {"Left": None, "Right": None}

        if not result.hand_landmarks or not result.handedness:
            return detected_hands

        # Biomechanical filter: discard cheeks, nose, and background false positives
        valid_entries = []
        for lms, cats in zip(result.hand_landmarks, result.handedness):
            cat = cats[0]
            if self._is_valid_hand(lms, cat):
                valid_entries.append((lms, cat))

        if not valid_entries:
            return detected_hands

        # Determine Handedness:
        # MediaPipe Rule:
        # - When image is MIRRORED: category_name 'Right' == User's Right hand, 'Left' == User's Left hand.
        # - When image is NOT MIRRORED: category_name 'Left' == User's Right hand, 'Right' == User's Left hand.
        def resolve_side(category):
            mp_label = category.category_name
            if is_mirrored:
                side = "Right" if mp_label == "Right" else "Left"
            else:
                side = "Right" if mp_label == "Left" else "Left"

            if self.swap_hands:
                side = "Right" if side == "Left" else "Left"
            return side

        if len(valid_entries) == 1:
            lms, cat = valid_entries[0]
            side = resolve_side(cat)
            detected_hands[side] = HandData(
                label=side,
                landmarks_list=lms,
                frame_width=w,
                frame_height=h,
            )
        else:
            # Two hands detected
            assigned = []
            for lms, cat in valid_entries[:2]:
                side = resolve_side(cat)
                assigned.append((side, lms, cat))

            # Disambiguate if both received the same label
            if assigned[0][0] == assigned[1][0]:
                x0 = sum(p.x for p in assigned[0][1]) / len(assigned[0][1])
                x1 = sum(p.x for p in assigned[1][1]) / len(assigned[1][1])
                if is_mirrored:
                    left_entry = assigned[0] if x0 < x1 else assigned[1]
                    right_entry = assigned[1] if x0 < x1 else assigned[0]
                else:
                    right_entry = assigned[0] if x0 < x1 else assigned[1]
                    left_entry = assigned[1] if x0 < x1 else assigned[0]

                if self.swap_hands:
                    left_entry, right_entry = right_entry, left_entry

                detected_hands["Left"] = HandData("Left", left_entry[1], w, h)
                detected_hands["Right"] = HandData("Right", right_entry[1], w, h)
            else:
                for side, lms, _ in assigned:
                    detected_hands[side] = HandData(side, lms, w, h)

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
