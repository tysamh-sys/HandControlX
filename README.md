# HandControlX — Neon Spellweaver: Cyber Mage

An interactive, gesture-controlled cyberpunk arcade game built using **Pygame** and **MediaPipe**. Players act as elemental cyber-mages, using static hand postures facing their webcams to charge and fire homing spells at incoming magical runes, defending their central core.

Unlike typical tracking games, **Neon Spellweaver** is optimized for low-framerate and low-quality webcams. It uses static hand postures instead of high-speed swiping movements, eliminating tracking failures caused by motion blur.

---

## Key Features

- **Asynchronous Computer Vision Threading**: Frame capture and MediaPipe joint classification run in a background daemon thread, allowing the main game graphics loop to render at a smooth 60 FPS.
- **Robust Static Gesture Classifier**: Analyzes hand coordinates in real-time, detecting 5 distinct postures:
  - ✊ **Fist**
  - 🖐️ **Open Palm**
  - ✌️ **Peace Sign**
  - 👍 **Thumbs Up**
  - 🤟 **Rock On / Spider-Man**
- **Chrono-Dilation (Time Warp)**: Active posture checks detect when the player makes the "Rock On" gesture, slowing down incoming enemy runes to 20% speed while rendering a retro blue vignette.
- **Procedural Sound Engine**: Audio effects (spell casts, portal impacts, score chimes, errors) are synthesized programmatically on launch using NumPy math wave formulas, meaning the game is completely self-contained with no external audio file dependencies.
- **High-Tech Cyberpunk HUD**: Features glowing neon vector drawing layers, particle emitters (fire sparks, water ripples, rock debris, light stars), screen shake feedback, and a diagnostic Picture-in-Picture webcam overlay.

---

## Spellcasting Controls

Hold your hand upright in view of your webcam. Perform and hold one of the following postures to target the nearest rune of that element:

| Gesture | Spell Name | Targeted Rune Color |
| :--- | :--- | :--- |
| ✊ **Fist** | Fire Blast | **Red (Fire)** |
| 🖐️ **Open Palm** | Water Torrent | **Cyan (Water)** |
| ✌️ **Peace Sign** | Earth Spike | **Green (Earth)** |
| 👍 **Thumbs Up** | Light Beam | **Yellow (Light)** |
| 🤟 **Rock On** | Time Warp | *Slows down time (consumes Chrono-Charge bar)* |

*Hold an elemental gesture for **0.4 seconds** to charge and cast the homing missile. Press `ESC` to go back to the menu or exit.*

---

## Installation & Setup

### Prerequisites
- Python 3.8 or higher
- A working webcam

### 1. Install Dependencies
Install the required packages using `pip`:
```bash
pip install pygame opencv-python mediapipe numpy
```

### 2. Run the Game
Execute the main script to play:
```bash
python main.py
```

---

## Code Architecture

- `main.py`: Drives the primary orchestrator state machine (Menus, Calibration view, Gameplay loops, HUD meters).
- `hand_tracker.py`: Threaded computer vision wrapper using OpenCV and MediaPipe to calculate coordinates and postures.
- `sound_generator.py`: Generates chimes, combustion booms, and clangs programmatically.
- `particles.py`: Animates trailing sparks, shockwaves, and homing comets.
