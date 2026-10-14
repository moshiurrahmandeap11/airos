import json
import os
import subprocess
import sys
import time
from typing import Dict, List
import pyautogui
from pynput.keyboard import Controller as KeyboardController, Key


class AppManager:
    """Handles cross-platform application launching, switching, and window lifecycle."""

    def __init__(self, config_path: str = "config/settings.json"):
        self.keyboard = KeyboardController()
        self.os_type = self._detect_os()
        self.apps = self._load_apps(config_path)
        self.last_action_time = 0.0
        self.action_cooldown = 0.7  # Prevent accidental double-firing

    def _detect_os(self) -> str:
        if sys.platform == "darwin":
            return "mac"
        elif sys.platform.startswith("linux"):
            return "linux"
        return "win"

    def _load_apps(self, config_path: str) -> List[Dict]:
        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    apps_dict = data.get("apps", {})
                    app_list = []
                    for key, val in apps_dict.items():
                        app_list.append({
                            "key": key,
                            "name": val.get("name", key),
                            "icon": val.get("icon", "📦"),
                            "cmd": val.get(self.os_type, ""),
                        })
                    return app_list
            except Exception as e:
                print(f"[AppManager] Error loading apps config: {e}")
        return []

    def launch_app(self, app_key_or_cmd: str) -> bool:
        """Launches an application in the background."""
        curr_time = time.time()
        if curr_time - self.last_action_time < self.action_cooldown:
            return False

        cmd = app_key_or_cmd
        # Look up if key was passed
        for app in self.apps:
            if app["key"] == app_key_or_cmd or app["name"].lower() == app_key_or_cmd.lower():
                cmd = app["cmd"]
                break

        if not cmd:
            return False

        try:
            if self.os_type == "win":
                subprocess.Popen(cmd, shell=True)
            elif self.os_type == "mac":
                subprocess.Popen(["open", "-a", cmd])
            else:  # Linux
                subprocess.Popen([cmd], shell=True)

            self.last_action_time = curr_time
            print(f"[AppManager] Launched: {cmd}")
            return True
        except Exception as e:
            print(f"[AppManager] Failed to launch {cmd}: {e}")
            return False

    def close_active_window(self) -> bool:
        """Sends native shortcut to close the active foreground window."""
        curr_time = time.time()
        if curr_time - self.last_action_time < self.action_cooldown:
            return False

        try:
            if self.os_type == "mac":
                self.keyboard.press(Key.cmd)
                self.keyboard.press("w")
                self.keyboard.release("w")
                self.keyboard.release(Key.cmd)
            else:
                # Windows & Linux: Alt + F4
                self.keyboard.press(Key.alt)
                self.keyboard.press(Key.f4)
                self.keyboard.release(Key.f4)
                self.keyboard.release(Key.alt)

            self.last_action_time = curr_time
            print("[AppManager] Closed active window")
            return True
        except Exception as e:
            print(f"[AppManager] Error closing window: {e}")
            return False

    def switch_app(self) -> bool:
        """Triggers native Alt+Tab / Cmd+Tab to switch active applications."""
        curr_time = time.time()
        if curr_time - self.last_action_time < self.action_cooldown:
            return False

        try:
            if self.os_type == "mac":
                pyautogui.hotkey("command", "tab")
            else:
                pyautogui.hotkey("alt", "tab")

            self.last_action_time = curr_time
            print("[AppManager] Switched app")
            return True
        except Exception as e:
            print(f"[AppManager] Error switching app: {e}")
            return False

    def show_desktop(self) -> bool:
        """Minimizes all windows to display the desktop."""
        curr_time = time.time()
        if curr_time - self.last_action_time < self.action_cooldown:
            return False

        try:
            if self.os_type == "mac":
                pyautogui.hotkey("command", "f3")
            else:
                pyautogui.hotkey("win", "d")

            self.last_action_time = curr_time
            print("[AppManager] Toggled desktop")
            return True
        except Exception as e:
            print(f"[AppManager] Error showing desktop: {e}")
            return False
