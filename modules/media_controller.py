import time
import pyautogui


class MediaController:
    """Controls system volume and media playback."""

    def __init__(self, step_cooldown: float = 0.15):
        self.step_cooldown = step_cooldown
        self.last_action_time = 0.0

    def volume_up(self):
        curr_time = time.time()
        if curr_time - self.last_action_time > self.step_cooldown:
            pyautogui.press("volumeup")
            self.last_action_time = curr_time

    def volume_down(self):
        curr_time = time.time()
        if curr_time - self.last_action_time > self.step_cooldown:
            pyautogui.press("volumedown")
            self.last_action_time = curr_time

    def toggle_mute(self):
        curr_time = time.time()
        if curr_time - self.last_action_time > 0.5:
            pyautogui.press("volumemute")
            self.last_action_time = curr_time

    def play_pause(self):
        curr_time = time.time()
        if curr_time - self.last_action_time > 0.5:
            pyautogui.press("playpause")
            self.last_action_time = curr_time
