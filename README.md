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
| **Right Hand** | 👉 Point Index Finger | Move Mouse Cursor |
| **Right Hand** | 👌 Index + Thumb Pinch | Left Click |
| **Right Hand** | 🤏 Pinch & Hold (>0.35s) | Click & Drag |
| **Right Hand** | ✌️ Middle + Thumb Pinch | Right Click |
| **Right Hand** | ✌️ Index + Middle Together | Scroll Up / Down |
| **Right Hand** | ✌️ Peace Sign | Switch Applications (`Alt+Tab` / `Cmd+Tab`) |
| **Left Hand** | 🖐️ Open Palm facing camera | Show Floating App Launcher Dock |
| **Left + Right**| 🖐️ Dock Open + 👉 Point & 👌 Pinch | Launch Hovered App |
| **Left Hand** | ✌️ Peace Sign | Toggle Virtual Air Keyboard |
| **Either Hand** | ✊ Hold Fist for 1.5s | Toggle Safety Sleep / Active Mode |

---

## ⌨️ Hotkeys in Camera Window

* `K` — Toggle Virtual Air Keyboard on/off
* `S` — Toggle Safety Sleep mode on/off
* `Q` or `ESC` — Safely exit the application

---

## ⚙️ Configuration (`config/settings.json`)

You can customize camera resolution, smoothing sensitivity, and your favorite apps in `config/settings.json`.
For extensive architectural and mathematical details, check **[tutorial.md](tutorial.md)**.
