<img width="900" alt="Capture d&#39;écran 2026-06-25 101725" src="https://github.com/user-attachments/assets/6d5a3a89-42f8-4d54-8fb6-f6985814714f" />
<img width="900" alt="Capture d&#39;écran 2026-06-25 101651" src="https://github.com/user-attachments/assets/e7c5628f-fdd0-4ca7-8308-e65cd44435a3" />
# HandControlX — Gesture Controlled Maze Navigation Demo

An interactive, gesture-controlled 2D maze navigation application built using **OpenCV** and **MediaPipe Hands**. The application runs completely inside a single dual-panel window showing real-time hand-joint tracking on the left and a retro-cyberpunk maze navigation game on the right.

This project is designed to showcase clean, high-performance computer vision implementation, custom neon vector rendering, and scale-invariant gesture classification.

---

## Key Features

- **Asynchronous Computer Vision Threading**: Frame capture, MediaPipe inference, and gesture classification execute in a background daemon thread, allowing the rendering loop to remain lightweight and performant.
- **Twin Diagnostic Panels**:
  - **LEFT PANEL (System View)**: Visualizes the tracking system, rendering a custom cyberpunk hand skeleton (neon cyan bones and glowing magenta nodes) along with diagnostic stats (Active Gesture, Tracking State, and Camera FPS).
  - **RIGHT PANEL (Game View)**: Displays the 2D maze game, featuring a grid background, neon walls, a pulsating lime-green goal portal, particle trail emitters, and an interactive gesture guide at the bottom.
- **Robust Scale-Invariant Classifier**: Detects finger extension ratios rather than absolute coordinate ranges. This makes gesture recognition robust to different hand sizes, hand orientation, and distance from the camera.
- **Axis-Separated Collision Checking**: Smooth movement with bounding box math that allows the player to slide along walls, resulting in a premium and responsive controls feel.
- **Zero Heavy Game Engines**: Renders everything (game scene, guide dashboard, and particles) entirely inside **OpenCV** canvas drawing layers (`numpy` arrays).

---

## Gesture Controls & Dashboard Guide

To control the player character (magenta circle), stand in front of your webcam and present one of the following postures:

| Gesture | Movement Action | Description |
| :--- | :--- | :--- |
| 🖐️ **Open Hand** | **UP** | Extend all four fingers upwards. |
| ✊ **Closed Fist** | **DOWN** | Fold all four fingers. |
| 👈 **Pointing Left** | **LEFT** | Extend index finger pointing to the visual left of the screen; fold others. |
| 👉 **Pointing Right** | **RIGHT** | Extend index finger pointing to the visual right of the screen; fold others. |

*Note: The active dashboard guide at the bottom of the game panel will glow in bright amber/cyan whenever the corresponding gesture is successfully detected.*

### Fallback Keyboard Controls
If you don't have a webcam connected or want to test the game mechanics, you can use the following keys on your keyboard:
- `W` / `A` / `S` / `D` to navigate Up, Left, Down, and Right.

---

## Installation & Setup

### Prerequisites
- Python 3.8 or higher
- A working webcam

### 1. Install Dependencies
Install the required packages using `pip`:
```bash
pip install opencv-python mediapipe numpy
```

### 2. Run the Demo
Run the main script:
```bash
python main.py
```

*Press `ESC` or click the window's close button to exit the application cleanly.*

---

## Code Architecture

- [main.py](file:///c:/Users/otays/Desktop/handDitctor/main.py): Drives the primary execution loop, game canvas rendering, collision sliding math, particle systems, dashboard panels, and stitched side-by-side visual output.
- [hand_tracker.py](file:///c:/Users/otays/Desktop/handDitctor/hand_tracker.py): Houses the background worker thread running MediaPipe Hands to process camera frames and return thread-safe tracking data.
