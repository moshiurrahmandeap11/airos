import sys
import time
import cv2
import numpy as np

from core.camera import CameraManager
from core.gestures import GestureRecognizer, GestureType
from core.tracker import DualHandTracker, HandLandmarkIndex
from modules.app_manager import AppManager
from modules.keyboard_virtual import VirtualKeyboardManager
from modules.media_controller import MediaController
from modules.mouse_controller import MouseController
from ui.hud_overlay import HUDOverlay


def main():
    print("=" * 60)
    print(" 🥽 Starting Vision Pro Style Hand Gesture OS Controller")
    print("=" * 60)

    # 1. Initialize Webcam / DroidCam
    cam = CameraManager()
    opened, frame_w, frame_h = cam.open(width=1280, height=720)

    if not opened:
        print("[ERROR] Cannot access camera source. Please check DroidCam or webcam connection.")
        sys.exit(1)

    print(f"[Camera] Stream initialized at {frame_w}x{frame_h}")

    # 2. Initialize Core Subsystems
    tracker = DualHandTracker(max_num_hands=2, min_detection_confidence=0.7, min_tracking_confidence=0.6)
    mouse_ctrl = MouseController(active_padding=0.15)
    app_mgr = AppManager()
    media_ctrl = MediaController()
    keyboard_mgr = VirtualKeyboardManager(frame_w, frame_h)
    hud = HUDOverlay(frame_w, frame_h)

    # State Variables
    is_sleep_mode = False
    fist_start_time = None
    prev_time = time.time()
    fps = 30.0

    # Keyboard toggle debounce
    last_kb_toggle_time = 0.0

    print("[Ready] Hand-OS is now live! Press 'Q' or 'ESC' in the camera window to quit.")

    while True:
        ret, frame, is_green_inactive = cam.read()
        if not ret:
            break

        # Flip horizontally for natural mirror UX
        frame = cv2.flip(frame, 1)

        # If DroidCam is sending an inactive green standby frame
        if is_green_inactive:
            hud.draw_top_bar(frame, fps, "DROIDCAM INACTIVE", "None", "None")
            hud.draw_camera_alert(
                frame,
                "DROIDCAM VIDEO IS INACTIVE",
                [
                    "1. Open DroidCam app on your phone & keep phone unlocked.",
                    "2. Make sure camera preview is live on your phone screen.",
                    "3. In PC DroidCam client, click STOP, check 'Video', then START.",
                ],
            )
            cv2.imshow("Vision Pro Hand-OS Controller", frame)
            key = cv2.waitKey(1) & 0xFF
            if key in (27, ord("q")):
                break
            continue

        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Calculate FPS
        curr_time = time.time()
        fps = 0.9 * fps + 0.1 * (1.0 / max(1e-5, curr_time - prev_time))
        prev_time = curr_time

        # Process Hands
        hands = tracker.process(frame_rgb, frame)
        left_hand = hands.get("Left")
        right_hand = hands.get("Right")

        # Classify Gestures
        left_gesture = GestureRecognizer.classify(left_hand)
        right_gesture = GestureRecognizer.classify(right_hand)

        # -------------------------------------------------------------
        # 1. Safety Sleep Toggle (Hold Left or Right Fist for >1.5s)
        # -------------------------------------------------------------
        either_fist = (left_gesture == GestureType.FIST) or (right_gesture == GestureType.FIST)
        if either_fist:
            if fist_start_time is None:
                fist_start_time = curr_time
            elif curr_time - fist_start_time > 1.5:
                is_sleep_mode = not is_sleep_mode
                fist_start_time = None
                hud.show_toast(f"SAFETY: {'SLEEP' if is_sleep_mode else 'ACTIVE'}")
        else:
            fist_start_time = None

        mode_name = "Sleep" if is_sleep_mode else ("Keyboard" if keyboard_mgr.is_active else "Mouse")

        # Draw hand skeletons for feedback
        if left_hand:
            tracker.draw_landmarks(frame, left_hand)
        if right_hand:
            tracker.draw_landmarks(frame, right_hand)

        # If asleep, draw banner and skip inputs
        if is_sleep_mode:
            hud.draw_top_bar(frame, fps, "SLEEP (PAUSED)", left_gesture.value, right_gesture.value)
            hud.draw_toasts(frame)
            cv2.imshow("Vision Pro Hand-OS Controller", frame)
            if cv2.waitKey(1) & 0xFF in (27, ord("q")):
                break
            continue

        # -------------------------------------------------------------
        # 2. Virtual Keyboard Toggle (Left Hand Peace or 'K' key)
        # -------------------------------------------------------------
        if left_gesture == GestureType.PEACE:
            if curr_time - last_kb_toggle_time > 1.2:
                keyboard_mgr.toggle()
                last_kb_toggle_time = curr_time
                hud.show_toast("KEYBOARD TOGGLED")

        # -------------------------------------------------------------
        # 3. Virtual Air Keyboard Mode
        # -------------------------------------------------------------
        if keyboard_mgr.is_active:
            kb_status = keyboard_mgr.update(left_hand, right_hand)
            hud.draw_virtual_keyboard(
                frame,
                keyboard_mgr.layout,
                kb_status["hovered_keys"],
                kb_status["pressed_key"],
                kb_status["fingers_px"],
            )
            if kb_status["pressed_key"]:
                hud.show_toast(f"TYPED: {kb_status['pressed_key'].display_label}", duration=0.8)

        # -------------------------------------------------------------
        # 4. Standard Navigation & App Launcher Mode
        # -------------------------------------------------------------
        else:
            # Active mouse tracking bounding box
            hud.draw_active_box(frame, padding=0.15)

            # Check if Left Hand Palm is Open -> Spawns App Dock!
            is_dock_open = left_gesture == GestureType.OPEN_PALM
            hovered_app = None

            # Get Right Hand Index Tip pixel position
            right_idx_px = None
            if right_hand:
                right_idx_px = (
                    right_hand.points_px[HandLandmarkIndex.INDEX_FINGER_TIP][0],
                    right_hand.points_px[HandLandmarkIndex.INDEX_FINGER_TIP][1],
                )

            if is_dock_open:
                hovered_app = hud.draw_app_dock(frame, app_mgr.apps, right_idx_px)

                # If pointing to an app tile and pinching with Right Hand -> Launch App!
                if hovered_app and right_gesture == GestureType.PINCH_INDEX:
                    if app_mgr.launch_app(hovered_app):
                        hud.show_toast(f"LAUNCHED: {hovered_app.upper()}", duration=1.5)

            # Mouse Cursor & Gesture Actions (Driven by Right Hand)
            is_pinching_idx = right_gesture == GestureType.PINCH_INDEX
            is_pinching_mid = right_gesture == GestureType.PINCH_MIDDLE
            is_scrolling = right_gesture == GestureType.SCROLL

            # Only move OS cursor if not currently interacting with the Dock
            if not (is_dock_open and hovered_app):
                m_status = mouse_ctrl.update(
                    right_hand,
                    is_pinching_index=is_pinching_idx,
                    is_pinching_middle=is_pinching_mid,
                    is_scrolling=is_scrolling,
                )

                if m_status["clicked"]:
                    hud.show_toast("LEFT CLICK")
                elif m_status["right_clicked"]:
                    hud.show_toast("RIGHT CLICK")

            # Window Multitasking Gestures:
            # Right Hand Peace gesture = Alt+Tab App Switcher
            if right_gesture == GestureType.PEACE:
                if app_mgr.switch_app():
                    hud.show_toast("SWITCH APP (ALT+TAB)")

        # Render Top Status Bar & Action Toasts
        hud.draw_top_bar(frame, fps, mode_name, left_gesture.value, right_gesture.value)
        hud.draw_toasts(frame)

        # Display Live Window
        cv2.imshow("Vision Pro Hand-OS Controller", frame)

        # Keyboard shortcuts on the PC window:
        # 'k' toggles virtual keyboard, 'q' or ESC exits
        key = cv2.waitKey(1) & 0xFF
        if key in (27, ord("q")):
            break
        elif key == ord("k"):
            keyboard_mgr.toggle()
            hud.show_toast("KEYBOARD TOGGLED")
        elif key == ord("s"):
            is_sleep_mode = not is_sleep_mode
            hud.show_toast(f"SAFETY: {'SLEEP' if is_sleep_mode else 'ACTIVE'}")

    # Cleanup
    cam.release()
    cv2.destroyAllWindows()
    print("[Shutdown] Hand-OS stopped safely.")


if __name__ == "__main__":
    main()
