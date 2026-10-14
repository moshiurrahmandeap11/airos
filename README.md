# 🥽 Vision Pro Style Hand Gesture OS Controller

Control your entire PC (Mouse, Full Virtual Keyboard, App Launcher, and Window Multitasking) using only your webcam and hand gestures. Inspired by the spatial computing paradigm of Apple Vision Pro.

---

## 🌟 Key Features

* **Dual-Hand Tracking:** Left and Right hands are tracked simultaneously in 3D space with 21 skeletal landmarks per hand.
* **Apple Vision Pro Style Interactions:**
  * **Left Hand:** Open palm spawns the **Floating App Launcher Dock** (Browser, Terminal, Files, Notes, Calculator).
  * **Right Hand:** Precision mouse cursor pointer with **One-Euro Filter** for zero-jitter cursor tracking.
  * **Both Hands:** Interactive **Virtual Air-Typing Keyboard** with dual-index targeting and pinch/tap triggers.
* **Cross-Platform:** Out of the box support for **Windows, macOS, and Linux**.
* **Safety Sleep Switch:** Hold a fist for 1.5 seconds to freeze tracking and prevent accidental gestures.

---

## 🚀 Quick Start

### 1. Install Dependencies
```bash
python -m pip install -r requirements.txt
```

### 2. Run the Controller
```bash
python main.py
```

---

## 🎮 Gesture Cheat Sheet

| Hand | Gesture | Action |
| :--- | :--- | :--- |
| **Right Hand** | 👉 Point Index Finger (1 finger) | Move Mouse Cursor (Super smooth, zero mistouch) |
| **Right Hand** | 👌 Index + Thumb Pinch (deliberate) | Instant Left Click |
| **Right Hand** | ✌️ Middle + Thumb Pinch | Right Click |
| **Right Hand** | ✌️ Index + Middle Together | Scroll Up / Down |
| **Right Hand** | ✊ Closed Fist (Hold 0.35s) | **Minimize Active App** 🗕 |
| **Right Hand** | 🖐️ Expand Hand (from Fist) | **Restore Last Minimized App** 🗖 |
| **Right Hand** | 🤏 $\rightarrow$ 👈 Thumb + Index Expand | **Maximize Window (Boro hobe)** 🗖 |
| **Right Hand** | 👈 $\rightarrow$ 🤏 Thumb + Index Shrink | **Restore / Shrink Window (Choto hobe)** 🗗 |
| **Right Hand** | 🖐️ 4 or 5 Fingers Swipe Left | **Switch Desktop Left** (`Ctrl+Win+Left`) ⬅️ |
| **Right Hand** | 🖐️ 4 or 5 Fingers Swipe Right| **Switch Desktop Right** (`Ctrl+Win+Right`) ➡️ |
| **Right Hand** | ✌️ Peace Sign (Hold 0.4s) | Switch Applications (`Alt+Tab` / `Cmd+Tab`) |
| **Left Hand** | 🖐️ Open Palm facing camera | Show Windows App Launcher Menu |
| **Left + Right**| 🖐️ Menu Open + 👉 Point & 👌 Pinch | Launch Hovered App |
| **Left Hand** | ✌️ Peace Sign | Toggle Virtual Air Keyboard |

---

## ⌨️ Hotkeys in Camera Window

* `M` — Toggle Camera Horizontal Mirror (Normal / Flipped) — *Fixes backwards DroidCam*
* `H` — Swap Left and Right hand assignment
* `K` — Toggle Virtual Air Keyboard on/off
* `S` — Toggle Safety Sleep mode on/off
* `ESC` — Exit keyboard mode (if open) or quit application
* `Q` — Safely exit the application

---

## 🛡️ Built-in Protections

* **Physical Mouse Auto-Yield:** Whenever you touch or move your real mouse or keyboard, gesture control immediately yields for 1.2 seconds so you are never locked out.
* **Cheek & Face False-Positive Filter:** Biomechanical palm aspect and knuckle validation completely prevents faces, cheeks, or background textures from triggering phantom clicks.
* **Rotation-Invariant 3D Tracking:** Detects 1, 2, 3, 4, 5 fingers accurately at any hand tilt.

---

## ⚙️ Configuration (`config/settings.json`)

You can customize camera resolution, smoothing sensitivity, and your favorite apps in `config/settings.json`.
For extensive architectural and mathematical details, check **[tutorial.md](tutorial.md)**.
