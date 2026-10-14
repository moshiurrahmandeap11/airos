# 🥽 Vision Pro Style Hand Gesture Controller: Complete Guide & Tutorial

> **Cross-Platform PC Control via Computer Vision**  
> Supported Operating Systems: **Windows | macOS | Linux**

---

## 📌 1. Overview & Vision

This system transforms any standard webcam into a **Vision Pro style spatial computing controller**. By tracking both hands simultaneously in real-time 3D space, you can control your entire PC without touching a mouse or keyboard.

### Key Pillars:
1. **Dual-Hand Division of Labor:**
   * **Left Hand:** System Palette, App Launcher Dock, Mode Switcher, and Window Manager.
   * **Right Hand:** Precision Cursor Pointer, Spatial Clicker, and Context Actions.
   * **Both Hands Combined:** Virtual Air-Typing Keyboard & Spatial Navigation.
2. **Full Virtual Air Keyboard:** On-screen floating translucent keyboard layout enabling real character typing through index finger pinching or depth tapping.
3. **Complete App Lifecycle Control:** Open applications from a floating gesture dock, switch between active tasks, minimize, and close windows.
4. **Cross-Platform Compatibility:** Runs on Windows, macOS, and Linux using unified input abstractions (`pynput`, `pyautogui`, and native system subprocesses).

---

## 📐 2. How Hand Gesture Recognition Works Under the Hood

The system relies on **MediaPipe Hands** by Google Research, which uses a two-stage deep learning pipeline:
1. **Palm Detector:** Scans the full image frame and locates hands bounding boxes.
2. **Hand Landmark Model:** Predicts **21 3D landmarks** per hand with precise `(x, y, z)` spatial coordinates.

```
                  8 [Index Tip]
                  |
             7    |     12 [Middle Tip]
             |    |     |
             6    |     11    16 [Ring Tip]
        4    |    |     |     |
    [Thumb]  5    |     10    15    20 [Pinky Tip]
        \    |    |     |     |     |
         3   |    |      9    14    19
          \  \    |     /     |     |
           2  \   |    /      13    18
            \  \  |   /      /     /
             1  \ |  /      /     /
              \  \| /      /     /
                  0 [Wrist]
```

### Landmark Indices Table:
* **Wrist:** `0`
* **Thumb:** `1, 2, 3, 4` (Tip: `4`)
* **Index Finger:** `5, 6, 7, 8` (Tip: `8`)
* **Middle Finger:** `9, 10, 11, 12` (Tip: `12`)
* **Ring Finger:** `13, 14, 15, 16` (Tip: `16`)
* **Pinky Finger:** `17, 18, 19, 20` (Tip: `20`)

---

## 🔬 3. Mathematical Foundations

### A. Finger State Detection (Open vs. Closed)
For each finger except the thumb, we compare the vertical position ($y$-coordinate) of the fingertip to its corresponding Proximal Interphalangeal (PIP) joint:
$$\text{isOpen} = y_{\text{tip}} < y_{\text{pip}}$$
*(Note: In OpenCV image coordinates, $y=0$ is at the top of the frame, so smaller $y$ means higher up).*

For the thumb, we measure the horizontal distance ($x$-coordinate) relative to the MCP joint based on hand orientation (left vs. right).

---

### B. Pinch Detection (Euclidean Distance)
Clicking and keypresses are triggered by a pinch between the **Thumb Tip (4)** and **Index Tip (8)**:
$$d = \sqrt{(x_8 - x_4)^2 + (y_8 - y_4)^2 + (z_8 - z_4)^2}$$

When normalized against hand scale (distance between Wrist `0` and Middle MCP `9`), if $d_{\text{norm}} < \text{threshold}$ (typically $0.05$), a **Pinch Event** is registered.

---

### C. Jitter Reduction: The One-Euro Filter
Raw webcam coordinates fluctuate by a few pixels every frame due to sensor noise, causing cursor jitter. We use the **One-Euro Filter** (or Exponential Moving Average with dynamic cutoff):
* When your hand moves **slowly**, the cutoff frequency drops $\rightarrow$ heavy smoothing for millimeter-precision pointing.
* When your hand moves **quickly**, the cutoff frequency rises $\rightarrow$ zero-latency cursor tracking.

---

### D. Active Screen Mapping (Active Box)
You should not have to move your hand beyond your camera's field of view to reach the edges of your screen. We define an **Active Rectangular Region** (e.g., center 70% of the frame). Hand movement within this boundary scales linearly to $100\%$ of your monitor's display resolution ($W_{\text{screen}} \times H_{\text{screen}}$).

---

## 🎮 4. The Complete Gesture Cheat Sheet

### A. Right Hand: Cursor & Mouse Navigation

| Action | Hand Gesture | Mechanism |
| :--- | :--- | :--- |
| **Move Cursor** | 👉 Index finger pointing up, other fingers curled | Smooth mapping of Landmark 8 to screen resolution |
| **Left Click** | 👌 Index + Thumb Pinch & Release | Distance $(4 \leftrightarrow 8) < \text{threshold}$, duration $< 300\text{ms}$ |
| **Click & Drag** | 🤏 Index + Thumb Pinch & Hold | Distance $(4 \leftrightarrow 8) < \text{threshold}$, duration $> 400\text{ms}$ |
| **Right Click** | ✌️ Thumb + Middle Finger Pinch | Distance $(4 \leftrightarrow 12) < \text{threshold}$ |
| **Scroll Up/Down**| ✌️ Index + Middle finger extended together | Vertical delta of midpoint $\left(\frac{y_8 + y_{12}}{2}\right)$ |

---

### B. Left Hand: System Controller & App Launcher Dock

| Action | Hand Gesture | Mechanism |
| :--- | :--- | :--- |
| **Spawn App Dock** | 🖐️ Open Palm facing camera | Renders floating interactive dock with quick-launch icons |
| **Launch App** | 👉 Right Hand points to app icon + 👌 Pinch | Selects app under cursor and invokes system launch process |
| **Toggle Virtual Keyboard** | ✋ Open Palm + Thumb-to-Index Pinch | Shows/Hides translucent floating on-screen keyboard |
| **Sleep / Safety Pause** | ✊ Closed Fist held for 1.5s | Disables all inputs to prevent accidental triggers |

---

### C. Dual-Hand Synergy: Full Virtual Air Keyboard

When the virtual keyboard is activated:
1. A semi-transparent QWERTY keyboard overlay displays on-screen.
2. Both **Left Index Tip (8)** and **Right Index Tip (8)** display targeting crosshairs.
3. Keys highlight upon hover.
4. **Typing Methods:**
   * **Pinch-to-Type:** Pinch thumb + index over any key to type it.
   * **Air-Tap (Depth Sensing):** Push index finger forward ($Z$-axis drop $> \Delta z$) to simulate a physical mechanical keypress!
5. Special function keys included: `[SPACE]`, `[ENTER]`, `[BACKSPACE]`, `[CAPS]`, and `[ESC]`.

---

### D. Window & App Management (Multitasking)

| Action | Hand Gesture | Mechanism |
| :--- | :--- | :--- |
| **Close Active Window**| 🦅 Five-finger claw closing rapidly into a fist | Sends `Alt + F4` (Win/Linux) or `Cmd + Q` (macOS) |
| **Switch Apps (Alt+Tab)**| ✌️ Peace gesture with Right Hand | Triggers native task switcher (`Alt+Tab` / `Cmd+Tab`) |
| **Switch Virtual Desktop Left**| 🖐️ Right Hand 3 fingers (Index+Middle+Ring) Swipe Left | Sends `Ctrl + Win + Left` (Win) or `Ctrl + Left` (macOS) ⬅️ |
| **Switch Virtual Desktop Right**| 🖐️ Right Hand 3 fingers (Index+Middle+Ring) Swipe Right | Sends `Ctrl + Win + Right` (Win) or `Ctrl + Right` (macOS) ➡️ |
| **Show Desktop** | ⬇️ Both hands open, swiped downward | Sends `Win + D` (Win) or `Cmd + F3` (macOS) |

---

## 🏗️ 5. Project Architecture & Modular Design

```
hand_gestures_controll/
│
├── core/
│   ├── __init__.py
│   ├── camera.py             # OpenCV webcam capture & downscaling thread
│   ├── tracker.py            # MediaPipe Dual-Hand landmark extractor
│   ├── gestures.py           # Gesture recognition & state machine
│   └── smoother.py           # One-Euro filter for jitter-free tracking
│
├── modules/
│   ├── __init__.py
│   ├── mouse_controller.py   # Cursor movement, left/right click, drag, scroll
│   ├── keyboard_virtual.py   # Dual-hand air typing engine & layout logic
│   ├── app_manager.py        # Cross-platform app launcher, switcher, and closer
│   └── media_controller.py   # Volume and media hotkeys
│
├── ui/
│   ├── __init__.py
│   ├── hud_overlay.py        # On-screen camera HUD & state status
│   └── keyboard_layout.py    # Geometric coordinates for virtual QWERTY keys
│
├── config/
│   └── settings.json         # User settings: sensitivity, hotkeys, apps
│
├── main.py                   # Master entrypoint & event loop
├── requirements.txt          # Python dependencies
└── tutorial.md               # Complete architecture & usage documentation
```

---

## 💻 6. Cross-Platform Abstraction Implementation Details

### A. Cross-Platform Mouse & Keyboard Events
Using `pynput`, mouse and keyboard events work seamlessly on all three major OS environments:
```python
from pynput.mouse import Button, Controller as MouseController
from pynput.keyboard import Key, Controller as KeyboardController

mouse = MouseController()
keyboard = KeyboardController()

# Cross-platform click
mouse.click(Button.left)

# Cross-platform typing
keyboard.type("Hello Vision Pro!")
```

### B. Cross-Platform App Launcher & Window Closer
```python
import sys
import subprocess

def launch_application(app_name):
    os_name = sys.platform
    if os_name == "win32":
        subprocess.Popen(["start", app_name], shell=True)
    elif os_name == "darwin":  # macOS
        subprocess.Popen(["open", "-a", app_name])
    elif os_name.startswith("linux"):
        subprocess.Popen([app_name])

def close_active_window():
    os_name = sys.platform
    if os_name == "win32" or os_name.startswith("linux"):
        # Alt + F4
        keyboard.press(Key.alt)
        keyboard.press(Key.f4)
        keyboard.release(Key.f4)
        keyboard.release(Key.alt)
    elif os_name == "darwin":
        # Cmd + W or Cmd + Q
        keyboard.press(Key.cmd)
        keyboard.press('w')
        keyboard.release('w')
        keyboard.release(Key.cmd)
```

---

## 🛠️ 7. Installation & Environment Setup

### 1. Requirements
* **Python:** 3.10 – 3.12 recommended for widest MediaPipe binary wheel support.
* **Camera:** Standard 720p or 1080p webcam (30+ FPS).

### 2. Dependencies (`requirements.txt`)
```text
opencv-python>=4.8.0
mediapipe>=0.10.0
pynput>=1.7.6
pyautogui>=0.9.54
numpy>=1.24.0
```

### 3. macOS Specific Setup
On macOS, grant **Accessibility Permissions** to your terminal/IDE:
`System Settings > Privacy & Security > Accessibility > Enable Terminal / Python / VS Code`.

### 4. Linux Specific Setup
For Linux (Ubuntu/Debian):
```bash
sudo apt-get install python3-tk libx11-dev
```

---

## 🚀 8. Five-Phase Implementation Roadmap

| Phase | Title | Key Objective |
| :--- | :--- | :--- |
| **Phase 1** | **Core Engine & Dual-Hand Tracker** | Set up camera loop, dual-hand MediaPipe tracking, landmark normalization, and FPS counter. |
| **Phase 2** | **Smooth Spatial Mouse Controller** | Implement active screen box, One-Euro jitter filter, pinch-to-click, and two-finger scroll. |
| **Phase 3** | **Left-Hand App Launcher & Dock** | Build floating palm menu, app launching system, and gesture-driven window closing (`Alt+F4` / `Cmd+W`). |
| **Phase 4** | **Virtual Air Keyboard Overlay** | Translucent QWERTY layout with hover tracking and dual-index pinch/depth tap typing. |
| **Phase 5** | **Polish, Configuration & Testing** | `settings.json` for sensitivity customization, safety sleep lock, and multi-OS verification. |

---

## 💡 9. Tips for the Best Experience

1. **Camera Placement:** Position your camera at eye level, roughly 1.5 to 2.5 feet (45–75 cm) away from your chest.
2. **Lighting:** Avoid strong backlight directly behind you; soft front lighting makes landmark detection rock-solid.
3. **Rest Position:** Keep your hands slightly above desk level; when resting, make a light fist or lower your hands to activate idle state.
