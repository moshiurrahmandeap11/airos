import sys
import time
import cv2
import numpy as np

from core.camera import CameraManager
from core.gestures import GestureRecognizer, GestureType, SwipeTracker, WindowResizeTracker
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
    tracker = DualHandTracker(max_num_hands=2, min_detection_confidence=0.58, min_tracking_confidence=0.50)
    mouse_ctrl = MouseController(active_padding=0.12, click_cooldown=0.20)
    app_mgr = AppManager()
    media_ctrl = MediaController()
    keyboard_mgr = VirtualKeyboardManager(frame_w, frame_h)
    hud = HUDOverlay(frame_w, frame_h)
    desktop_swipe_tracker = SwipeTracker(displacement_threshold=0.08, time_window=0.30, cooldown=0.40)
    resize_tracker = WindowResizeTracker(cooldown=0.60)

    # State Variables
    is_sleep_mode = False
    fist_minimize_start = None
    window_minimized_by_gesture = False
    peace_start_time = None
    prev_time = time.time()
    fps = 30.0

    # Keyboard toggle debounce
    last_kb_toggle_time = 0.0

    print("[Ready] Hand-OS is now live! Press 'Q' or 'ESC' in the camera window to quit.")
    print(f"[Camera] Initial Mirror Mode: {cam.mirror_camera} (Press 'M' to toggle live)")

    while True:
        ret, frame, is_green_inactive = cam.read()
        if not ret:
            break

        # Flip horizontally only if camera mirror is enabled (disabled for DroidCam by default)
        if cam.mirror_camera:
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

        # Process Hands with mirror-awareness and biomechanical cheek filtering
        hands = tracker.process(frame_rgb, frame, is_mirrored=cam.mirror_camera)
        left_hand = hands.get("Left")
        right_hand = hands.get("Right")

        # Classify Gestures
        left_gesture = GestureRecognizer.classify(left_hand)
        right_gesture = GestureRecognizer.classify(right_hand)

        # -------------------------------------------------------------
        # 1. Safety Sleep Mode Check (Manual toggle via 'S' key or deliberate hold)
        # -------------------------------------------------------------
        mode_name = "Sleep" if is_sleep_mode else ("Keyboard" if keyboard_mgr.is_active else "Mouse")

        # Draw hand skeletons for feedback
        if left_hand:
            tracker.draw_landmarks(frame, left_hand)
        if right_hand:
            tracker.draw_landmarks(frame, right_hand)

        # If asleep, draw clear wake-up prompt and skip processing
        if is_sleep_mode:
            hud.draw_top_bar(frame, fps, "SLEEP (PAUSED)", left_gesture.value, right_gesture.value)
            hud.draw_camera_alert(
                frame,
                "CONTROLLER IS PAUSED (SLEEP MODE)",
                [
                    "Press 'S' on your keyboard to resume active control.",
                    "Press 'M' to toggle Camera Mirroring (Flipped / Normal).",
                    "Press 'H' to swap Left and Right hand mapping.",
                    "Press 'Q' or ESC to quit.",
                ],
            )
            hud.draw_toasts(frame)
            cv2.imshow("Vision Pro Hand-OS Controller", frame)
            key = cv2.waitKey(1) & 0xFF
            if key in (27, ord("q")):
                break
            elif key == ord("s"):
                is_sleep_mode = False
                hud.show_toast("CONTROLLER ACTIVE")
            elif key == ord("h"):
                swapped = tracker.toggle_swap_hands()
                hud.show_toast(f"HANDS SWAPPED: {'INVERTED' if swapped else 'NORMAL'}")
            elif key == ord("m"):
                is_mir = cam.toggle_mirror()
                hud.show_toast(f"CAMERA MIRROR: {'ON (FLIPPED)' if is_mir else 'OFF (NORMAL)'}", duration=1.5)
            continue

        # -------------------------------------------------------------
        # 2. Virtual Keyboard Toggle (Left Hand Peace or 'K' key)
        # -------------------------------------------------------------
        if not keyboard_mgr.is_active and left_gesture == GestureType.PEACE:
            if curr_time - last_kb_toggle_time > 1.2:
                keyboard_mgr.toggle()
                last_kb_toggle_time = curr_time
                hud.show_toast("KEYBOARD OPENED ⌨️")

        # -------------------------------------------------------------
        # 3. Virtual Air Keyboard Mode
        # -------------------------------------------------------------
        if keyboard_mgr.is_active:
            # Effortless exit back to Mouse Mode:
            # 1) Show Peace sign ✌️, Fist ✊, or Open Palm 🖐️ with Left hand, OR
            # 2) Pinch the [✕ Close] key on the virtual keyboard, OR
            # 3) Press 'K' or 'ESC' on physical keyboard
            if (left_gesture in (GestureType.PEACE, GestureType.FIST, GestureType.OPEN_PALM)) and curr_time - last_kb_toggle_time > 1.0:
                keyboard_mgr.is_active = False
                last_kb_toggle_time = curr_time
                hud.show_toast("RETURNED TO MOUSE MODE 🖱️")
                continue

            kb_status = keyboard_mgr.update(left_hand, right_hand)
            hud.draw_virtual_keyboard(
                frame,
                keyboard_mgr.layout,
                kb_status["hovered_keys"],
                kb_status["pressed_key"],
                kb_status["fingers_px"],
            )
            if kb_status["pressed_key"]:
                if kb_status["pressed_key"].char == "CLOSE":
                    keyboard_mgr.is_active = False
                    last_kb_toggle_time = curr_time
                    hud.show_toast("RETURNED TO MOUSE MODE 🖱️")
                    continue
                else:
                    hud.show_toast(f"TYPED: {kb_status['pressed_key'].display_label}", duration=0.8)

            # Keep mouse cursor moving naturally when not directly hovering a virtual key!
            if right_hand and not kb_status["hovered_keys"]:
                is_pinching_idx = right_hand.is_pinching(HandLandmarkIndex.INDEX_FINGER_TIP, threshold_ratio=0.35)
                mouse_ctrl.update(right_hand, is_pinching_index=is_pinching_idx, is_pinching_middle=False, is_scrolling=False)

        # -------------------------------------------------------------
        # 4. Standard Navigation & App Launcher Mode
        # -------------------------------------------------------------
        else:
            # Active mouse tracking bounding box
            hud.draw_active_box(frame, padding=0.12)

            # Check if Left Hand Palm is Open -> Spawns App Menu!
            is_dock_open = (left_gesture == GestureType.OPEN_PALM) or (left_hand is not None and left_hand.extended_count >= 4)
            hovered_app = None

            # Get Right Hand Index Tip pixel position for pointing & aiming
            right_idx_px = None
            if right_hand:
                right_idx_px = (
                    right_hand.points_px[HandLandmarkIndex.INDEX_FINGER_TIP][0],
                    right_hand.points_px[HandLandmarkIndex.INDEX_FINGER_TIP][1],
                )

            # If Left Hand Palm is open, display Windows App Menu
            if is_dock_open:
                hovered_app = hud.draw_app_dock(frame, app_mgr.apps, right_idx_px)

                # Right Hand Point & Pinch -> Instant Launch!
                if hovered_app and right_hand and right_hand.is_pinching(HandLandmarkIndex.INDEX_FINGER_TIP, threshold_ratio=0.35):
                    if app_mgr.launch_app(hovered_app):
                        hud.show_toast(f"LAUNCHED: {hovered_app.upper()} 🚀", duration=1.5)

            # ---------------------------------------------------------
            # 1. Right Hand Fist to Minimize Active Window / Expand to Restore Window
            # ---------------------------------------------------------
            if right_hand is not None:
                is_fist_posture = (right_hand.extended_count == 0) or (
                    not right_hand.finger_states.get("index")
                    and not right_hand.finger_states.get("middle")
                    and not right_hand.finger_states.get("ring")
                    and not right_hand.finger_states.get("pinky")
                )
                if is_fist_posture:
                    if fist_minimize_start is None:
                        fist_minimize_start = curr_time
                    elif curr_time - fist_minimize_start >= 0.35:
                        if not window_minimized_by_gesture:
                            if app_mgr.minimize_active_window():
                                window_minimized_by_gesture = True
                                hud.show_toast("APP MINIMIZED 🗕", duration=1.2)
                else:
                    # Hand expanded from fist
                    if window_minimized_by_gesture and right_hand.extended_count >= 4:
                        if app_mgr.restore_last_minimized_window():
                            hud.show_toast("APP RESTORED 🗖", duration=1.2)
                        window_minimized_by_gesture = False
                    fist_minimize_start = None
            else:
                fist_minimize_start = None

            # ---------------------------------------------------------
            # 2. Window Resize (Thumb & Index Expand / Shrink)
            # ---------------------------------------------------------
            resize_action = None
            if right_hand and not is_dock_open:
                resize_action = resize_tracker.update(right_hand, curr_time)
                if resize_action == "EXPAND":
                    if app_mgr.maximize_active_window():
                        hud.show_toast("WINDOW MAXIMIZE / EXPAND 🗖", duration=1.2)
                elif resize_action == "SHRINK":
                    if app_mgr.shrink_active_window():
                        hud.show_toast("WINDOW RESTORE / SHRINK 🗗", duration=1.2)

            # ---------------------------------------------------------
            # 3. Virtual Desktop Switch (Requires AT LEAST 4 fingers open!)
            # ---------------------------------------------------------
            swipe_triggered = False
            is_open_hand_for_swipe = (
                right_hand is not None
                and right_hand.extended_count >= 4
                and not is_dock_open
            )

            if is_open_hand_for_swipe:
                right_palm_x = right_hand.points_norm[HandLandmarkIndex.MIDDLE_FINGER_MCP][0]
                swipe_dir = desktop_swipe_tracker.update(right_palm_x, True, curr_time, is_mirrored=cam.mirror_camera)

                if swipe_dir == "LEFT":
                    if app_mgr.switch_desktop_left():
                        hud.show_toast("DESKTOP: PREV (LEFT) ⬅️", duration=1.4)
                        swipe_triggered = True
                elif swipe_dir == "RIGHT":
                    if app_mgr.switch_desktop_right():
                        hud.show_toast("DESKTOP: NEXT (RIGHT) ➡️", duration=1.4)
                        swipe_triggered = True
            else:
                desktop_swipe_tracker.update(0.5, False, curr_time, is_mirrored=cam.mirror_camera)

            # ---------------------------------------------------------
            # 4. Mouse Cursor & Gesture Actions (Driven by Right Hand)
            # ---------------------------------------------------------
            # Tight 0.26 pinch threshold prevents mistouches when pointing with 1 finger
            is_pinching_idx = (
                right_hand.is_pinching(HandLandmarkIndex.INDEX_FINGER_TIP, threshold_ratio=0.26)
                if (right_hand and right_hand.finger_states.get("index") and right_hand.extended_count > 0)
                else False
            )
            is_pinching_mid = (
                right_hand.is_pinching(HandLandmarkIndex.MIDDLE_FINGER_TIP, threshold_ratio=0.26)
                if (right_hand and right_hand.finger_states.get("middle") and right_hand.extended_count > 0)
                else False
            )
            is_scrolling = right_gesture == GestureType.SCROLL

            # Move OS cursor only if not interacting with Menu and not during swipe or resize
            if not (is_dock_open and hovered_app) and not swipe_triggered and not resize_action:
                m_status = mouse_ctrl.update(
                    right_hand,
                    is_pinching_index=is_pinching_idx,
                    is_pinching_middle=is_pinching_mid,
                    is_scrolling=is_scrolling,
                )

                if m_status["clicked"]:
                    hud.show_toast("LEFT CLICK 👌")
                elif m_status["right_clicked"]:
                    hud.show_toast("RIGHT CLICK ✌️")

            # ---------------------------------------------------------
            # 5. Window Multitasking: Peace sign held for 0.4s = Alt+Tab
            # ---------------------------------------------------------
            if right_gesture == GestureType.PEACE and not is_dock_open and not is_open_hand_for_swipe:
                if peace_start_time is None:
                    peace_start_time = curr_time
                elif curr_time - peace_start_time >= 0.40:
                    if app_mgr.switch_app():
                        hud.show_toast("SWITCH APP (ALT+TAB)")
                    peace_start_time = curr_time + 0.35
            else:
                peace_start_time = None

        # Render Top Status Bar & Action Toasts
        hud.draw_top_bar(frame, fps, mode_name, left_gesture.value, right_gesture.value)
        hud.draw_toasts(frame)

        # Display Live Window
        cv2.imshow("Vision Pro Hand-OS Controller", frame)

        key = cv2.waitKey(1) & 0xFF
        if key == 27:  # ESC key
            if keyboard_mgr.is_active:
                keyboard_mgr.is_active = False
                hud.show_toast("RETURNED TO MOUSE MODE 🖱️")
            else:
                break
        elif key == ord("q"):
            break
        elif key == ord("k"):
            keyboard_mgr.toggle()
            hud.show_toast(f"KEYBOARD: {'ON' if keyboard_mgr.is_active else 'OFF'}")
        elif key == ord("s"):
            is_sleep_mode = not is_sleep_mode
            hud.show_toast(f"SAFETY: {'SLEEP' if is_sleep_mode else 'ACTIVE'}")
        elif key == ord("h"):
            swapped = tracker.toggle_swap_hands()
            hud.show_toast(f"HANDS SWAPPED: {'INVERTED' if swapped else 'NORMAL'}", duration=1.5)
        elif key == ord("m"):
            is_mir = cam.toggle_mirror()
            hud.show_toast(f"CAMERA MIRROR: {'ON (FLIPPED)' if is_mir else 'OFF (NORMAL)'}", duration=1.5)

    # Cleanup
    cam.release()
    cv2.destroyAllWindows()
    print("[Shutdown] Hand-OS stopped safely.")


if __name__ == "__main__":
    main()
