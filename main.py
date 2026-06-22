import cv2
import numpy as np
import time
import math
import random
from hand_tracker import HandTracker

# ==========================================
# CONSTANTS & CONFIGURATION
# ==========================================
# Each panel is 640x480, stitched horizontally to make a 1280x480 window
PANEL_W = 640
PANEL_H = 480
WINDOW_NAME = "Gesture Maze Navigation Demo"

# BGR Neon Color Palette
COLOR_BG = (15, 10, 8)            # Very dark indigo/black
COLOR_GRID = (30, 20, 15)         # Faint blue-gray grid lines
COLOR_WALL_FILL = (35, 25, 20)    # Dark gray wall interior
COLOR_WALL_BORDER = (255, 220, 0) # Electric neon cyan border
COLOR_PLAYER_GLOW = (200, 0, 200) # Deep magenta glow
COLOR_PLAYER_CORE = (255, 150, 255)# Bright pink player center
COLOR_PLAYER_WHITE = (255, 255, 255)# Pure white core
COLOR_GOAL_GLOW = (0, 180, 0)     # Neon green glow
COLOR_GOAL_CORE = (0, 255, 0)     # Bright lime green core
COLOR_TEXT = (240, 240, 240)      # High-contrast white/gray for UI text
COLOR_HUD_BOX = (40, 25, 20)      # HUD panel background
COLOR_ACCENT = (0, 255, 255)      # Cyberpunk yellow/amber

# 12x8 Maze Layout: 1 = Wall, 0 = Path
# Designed with multiple paths, corridors, and dead ends
MAZE = [
    [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
    [1, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 1],
    [1, 0, 1, 0, 1, 0, 1, 1, 1, 1, 0, 1],
    [1, 0, 1, 0, 0, 0, 1, 0, 0, 1, 0, 1],
    [1, 0, 1, 1, 1, 1, 1, 0, 1, 1, 0, 1],
    [1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 1],
    [1, 1, 1, 1, 0, 1, 1, 0, 1, 0, 1, 1],
    [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]
]

# Maze offset & sizing inside the 640x480 right panel
CELL_SIZE = 50
OFFSET_X = (PANEL_W - len(MAZE[0]) * CELL_SIZE) // 2  # Centered horizontally: 20px padding
OFFSET_Y = (PANEL_H - len(MAZE) * CELL_SIZE) // 2 - 20 # Offset upwards to leave 60px for the guide: 20px padding

# Start and goal coordinates (grid coordinates)
START_CELL = (1, 1)
GOAL_CELL = (10, 5)

# Calculate pixel centers for start and goal
PLAYER_START_X = OFFSET_X + START_CELL[0] * CELL_SIZE + CELL_SIZE // 2
PLAYER_START_Y = OFFSET_Y + START_CELL[1] * CELL_SIZE + CELL_SIZE // 2
GOAL_X = OFFSET_X + GOAL_CELL[0] * CELL_SIZE + CELL_SIZE // 2
GOAL_Y = OFFSET_Y + GOAL_CELL[1] * CELL_SIZE + CELL_SIZE // 2

# ==========================================
# GAME STATE VARIABLES
# ==========================================
player_x = float(PLAYER_START_X)
player_y = float(PLAYER_START_Y)
player_radius = 12
player_speed = 3.5

# Particle system list
# Particles have format: {"x", "y", "vx", "vy", "color", "size", "life", "max_life"}
particles = []

# Victory status
victory_active = False
victory_timer = 0  # Frame countdown for resetting after victory

# ==========================================
# COLLISION & MOVEMENT UTILITIES
# ==========================================
def check_collision(px, py, radius):
    """
    Checks if a circle at (px, py) with the given radius intersects with any wall.
    Uses closest-point bounding box intersection for smooth collision sliding.
    """
    col_min = max(0, int((px - OFFSET_X - radius) // CELL_SIZE))
    col_max = min(len(MAZE[0]) - 1, int((px - OFFSET_X + radius) // CELL_SIZE))
    row_min = max(0, int((py - OFFSET_Y - radius) // CELL_SIZE))
    row_max = min(len(MAZE) - 1, int((py - OFFSET_Y + radius) // CELL_SIZE))
    
    for r in range(row_min, row_max + 1):
        for c in range(col_min, col_max + 1):
            if MAZE[r][c] == 1:
                # Bounding box of this wall block
                x1 = OFFSET_X + c * CELL_SIZE
                x2 = x1 + CELL_SIZE
                y1 = OFFSET_Y + r * CELL_SIZE
                y2 = y1 + CELL_SIZE
                
                # Find the point on the block closest to the player's center
                cx = max(x1, min(px, x2))
                cy = max(y1, min(py, y2))
                
                # Check distance to that closest point
                dx = px - cx
                dy = py - cy
                if dx*dx + dy*dy < radius*radius:
                    return True
    return False

def reset_game():
    """Resets the player position and clears game animations."""
    global player_x, player_y, victory_active, victory_timer, particles
    player_x = float(PLAYER_START_X)
    player_y = float(PLAYER_START_Y)
    victory_active = False
    victory_timer = 0
    particles.clear()

# ==========================================
# MAIN EXECUTION LOOP
# ==========================================
def main():
    global player_x, player_y, victory_active, victory_timer, particles
    
    # Initialize background hand tracking thread
    tracker = HandTracker()
    tracker.start()
    
    # Initialize OpenCV window
    cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_AUTOSIZE)
    
    # Frame rate limiter variables (Target: 30 FPS)
    target_frame_time = 1.0 / 30.0
    
    print("[INFO] Project initialized. Open webcam active.")
    print("[INFO] Backup controls: Use W, A, S, D on keyboard to navigate.")
    print("[INFO] Press ESC on window to exit.")
    
    while True:
        frame_start = time.time()
        
        # 1. Fetch data and frame from hand tracker
        tracker_data = tracker.get_data()
        raw_gesture = tracker_data["gesture"]
        tracker_fps = tracker_data["fps"]
        hand_detected = tracker_data["hand_detected"]
        
        cam_frame = tracker.get_frame()
        
        # Poll keyboard keys
        key = cv2.waitKey(1) & 0xFF
        
        # ESC key pressed or window closed -> exit
        if key == 27:
            break
        if cv2.getWindowProperty(WINDOW_NAME, cv2.WND_PROP_VISIBLE) < 1:
            break
            
        # 2. Process active input (Gesture or Keyboard fallback)
        active_direction = "NONE"
        if raw_gesture != "NONE":
            active_direction = raw_gesture
            
        # Keyboard backup overrides
        if key in [ord('w'), ord('W')]:
            active_direction = "UP"
        elif key in [ord('s'), ord('S')]:
            active_direction = "DOWN"
        elif key in [ord('a'), ord('A')]:
            active_direction = "LEFT"
        elif key in [ord('d'), ord('D')]:
            active_direction = "RIGHT"
            
        # 3. Update Game Logic
        dx, dy = 0.0, 0.0
        if not victory_active:
            if active_direction == "UP":
                dy = -player_speed
            elif active_direction == "DOWN":
                dy = player_speed
            elif active_direction == "LEFT":
                dx = -player_speed
            elif active_direction == "RIGHT":
                dx = player_speed
                
            # Perform axis-separated movement to allow sliding along walls
            if dx != 0:
                new_x = player_x + dx
                if not check_collision(new_x, player_y, player_radius):
                    player_x = new_x
            if dy != 0:
                new_y = player_y + dy
                if not check_collision(player_x, new_y, player_radius):
                    player_y = new_y
                    
            # Emit trail particles behind the player during movement
            if dx != 0 or dy != 0:
                particles.append({
                    "x": player_x + random.uniform(-3, 3),
                    "y": player_y + random.uniform(-3, 3),
                    "vx": -dx * 0.15 + random.uniform(-0.4, 0.4),
                    "vy": -dy * 0.15 + random.uniform(-0.4, 0.4),
                    "color": (255, 0, 200),  # Magenta
                    "size": random.randint(3, 5),
                    "life": 15,
                    "max_life": 15
                })
                
            # Check victory condition (goal collision)
            dist_to_goal = math.sqrt((player_x - GOAL_X)**2 + (player_y - GOAL_Y)**2)
            if dist_to_goal < (player_radius + 14):
                victory_active = True
                victory_timer = 60  # 2 seconds at 30 FPS
                
                # Emit massive fireworks/explosion particles
                for _ in range(80):
                    angle = random.uniform(0, 2 * math.pi)
                    speed = random.uniform(2.0, 6.0)
                    particles.append({
                        "x": float(GOAL_X),
                        "y": float(GOAL_Y),
                        "vx": math.cos(angle) * speed,
                        "vy": math.sin(angle) * speed,
                        "color": random.choice([(0, 255, 0), (0, 255, 255), (255, 255, 255)]), # lime, yellow/cyan, white
                        "size": random.randint(4, 7),
                        "life": random.randint(25, 45),
                        "max_life": 45
                    })
        else:
            # Handle victory reset countdown
            victory_timer -= 1
            if victory_timer <= 0:
                reset_game()
                
        # Update particles (age and movement)
        for p in particles[:]:
            p["x"] += p["vx"]
            p["y"] += p["vy"]
            p["life"] -= 1
            if p["life"] <= 0:
                particles.remove(p)
                
        # 4. Render Left Panel (System View)
        if cam_frame is not None:
            left_panel = cam_frame
        else:
            # Show a nice loading canvas if the frame isn't ready
            left_panel = np.zeros((PANEL_H, PANEL_W, 3), dtype=np.uint8)
            left_panel[:] = COLOR_BG
            cv2.putText(left_panel, "CAMERA CONNECTING...", (160, 240), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 2, cv2.LINE_AA)
                        
        # Draw system HUD boxes on Left Panel
        cv2.rectangle(left_panel, (15, 15), (280, 115), COLOR_HUD_BOX, -1)
        cv2.rectangle(left_panel, (15, 15), (280, 115), COLOR_WALL_BORDER, 1)
        
        status_text = "TRACKING ACTIVE" if hand_detected else "SCANNING..."
        status_color = (0, 255, 0) if hand_detected else (0, 165, 255) # Green / Amber
        
        cv2.putText(left_panel, f"SYS STATE: {status_text}", (25, 40), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, status_color, 1, cv2.LINE_AA)
        cv2.putText(left_panel, f"GESTURE: {active_direction}", (25, 65), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, COLOR_TEXT, 1, cv2.LINE_AA)
        cv2.putText(left_panel, f"TRACKER RATE: {tracker_fps} FPS", (25, 90), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (180, 180, 180), 1, cv2.LINE_AA)
                    
        # Small pulsating scanning indicator dot
        ind_pulse = int(5 + math.sin(time.time() * 8) * 2)
        cv2.circle(left_panel, (250, 40), ind_pulse, status_color, -1, cv2.LINE_AA)
        
        # Outer panel border
        cv2.rectangle(left_panel, (4, 4), (PANEL_W - 4, PANEL_H - 4), COLOR_WALL_BORDER, 2, cv2.LINE_AA)
        
        # 5. Render Right Panel (Game View)
        game_panel = np.zeros((PANEL_H, PANEL_W, 3), dtype=np.uint8)
        game_panel[:] = COLOR_BG
        
        # Draw background grids
        for r in range(0, PANEL_H, 25):
            cv2.line(game_panel, (0, r), (PANEL_W, r), COLOR_GRID, 1)
        for c in range(0, PANEL_W, 25):
            cv2.line(game_panel, (c, 0), (c, PANEL_H), COLOR_GRID, 1)
            
        # Draw Maze Walls
        for r in range(len(MAZE)):
            for c in range(len(MAZE[0])):
                if MAZE[r][c] == 1:
                    x1 = OFFSET_X + c * CELL_SIZE
                    y1 = OFFSET_Y + r * CELL_SIZE
                    x2 = x1 + CELL_SIZE
                    y2 = y1 + CELL_SIZE
                    # Fill
                    cv2.rectangle(game_panel, (x1, y1), (x2, y2), COLOR_WALL_FILL, -1)
                    # Border
                    cv2.rectangle(game_panel, (x1, y1), (x2, y2), COLOR_WALL_BORDER, 1, cv2.LINE_AA)
                    
        # Draw Start cell indicator
        cv2.putText(game_panel, "START", (OFFSET_X + START_CELL[0]*CELL_SIZE + 5, OFFSET_Y + START_CELL[1]*CELL_SIZE + 30), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (100, 100, 100), 1, cv2.LINE_AA)
                    
        # Draw Pulsating Goal Portal (Lime Green)
        goal_pulse = 16 + int(math.sin(time.time() * 10) * 3)
        cv2.circle(game_panel, (GOAL_X, GOAL_Y), goal_pulse + 5, (0, 100, 0), 2, cv2.LINE_AA) # Outer rings
        cv2.circle(game_panel, (GOAL_X, GOAL_Y), goal_pulse, COLOR_GOAL_GLOW, 2, cv2.LINE_AA)
        cv2.circle(game_panel, (GOAL_X, GOAL_Y), goal_pulse - 5, COLOR_GOAL_CORE, -1, cv2.LINE_AA)
        cv2.circle(game_panel, (GOAL_X, GOAL_Y), 4, COLOR_PLAYER_WHITE, -1, cv2.LINE_AA)
        cv2.putText(game_panel, "GOAL", (GOAL_X - 16, GOAL_Y - 24), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, COLOR_GOAL_CORE, 1, cv2.LINE_AA)
                    
        # Draw Particles
        for p in particles:
            sz = int(p["size"] * (p["life"] / p["max_life"]))
            sz = max(1, sz)
            cv2.circle(game_panel, (int(p["x"]), int(p["y"])), sz, p["color"], -1, cv2.LINE_AA)
            
        # Draw Glowing Player character (Magenta core and outline)
        cv2.circle(game_panel, (int(player_x), int(player_y)), player_radius + 4, COLOR_PLAYER_GLOW, 3, cv2.LINE_AA)
        cv2.circle(game_panel, (int(player_x), int(player_y)), player_radius, COLOR_PLAYER_CORE, -1, cv2.LINE_AA)
        cv2.circle(game_panel, (int(player_x), int(player_y)), 4, COLOR_PLAYER_WHITE, -1, cv2.LINE_AA)
        
        # Draw Victory HUD overlay overlaying the game scene
        if victory_active:
            overlay = game_panel.copy()
            cv2.rectangle(overlay, (50, 150), (PANEL_W - 50, 310), (20, 20, 20), -1)
            cv2.rectangle(overlay, (50, 150), (PANEL_W - 50, 310), COLOR_GOAL_CORE, 2, cv2.LINE_AA)
            cv2.addWeighted(overlay, 0.85, game_panel, 0.15, 0, game_panel)
            
            cv2.putText(game_panel, "MAZE COMPLETED!", (120, 215), 
                        cv2.FONT_HERSHEY_SIMPLEX, 1.2, COLOR_GOAL_CORE, 3, cv2.LINE_AA)
            cv2.putText(game_panel, "Smooth gesture navigation successful!", (165, 250), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, COLOR_TEXT, 1, cv2.LINE_AA)
            cv2.putText(game_panel, f"Resetting start in {int(victory_timer / 15) + 1}s...", (230, 285), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, (160, 160, 160), 1, cv2.LINE_AA)
                        
        # Draw Visual Guide Dashboard at the bottom (y=420 to y=480)
        dash_y = 420
        dash_h = 60
        panel_w = PANEL_W // 4
        
        directions = ["UP", "DOWN", "LEFT", "RIGHT"]
        gestures = ["OPEN HAND", "CLOSED FIST", "POINT LEFT", "POINT RIGHT"]
        
        for i in range(4):
            d_name = directions[i]
            g_name = gestures[i]
            px_l = i * panel_w
            px_r = px_l + panel_w
            
            is_hl = (active_direction == d_name)
            box_bg = (40, 25, 20) if is_hl else (20, 15, 12)
            box_border = COLOR_ACCENT if is_hl else (70, 50, 45)
            box_thick = 2 if is_hl else 1
            
            # Panel box
            cv2.rectangle(game_panel, (px_l + 4, dash_y + 4), (px_r - 4, dash_y + dash_h - 4), box_bg, -1)
            cv2.rectangle(game_panel, (px_l + 4, dash_y + 4), (px_r - 4, dash_y + dash_h - 4), box_border, box_thick, cv2.LINE_AA)
            
            # Icon location
            ic_x = px_l + 28
            ic_y = dash_y + dash_h // 2
            ic_color = COLOR_ACCENT if is_hl else (140, 120, 115)
            
            # Draw tiny vector directions arrows
            if d_name == "UP":
                cv2.line(game_panel, (ic_x, ic_y + 9), (ic_x, ic_y - 9), ic_color, 2, cv2.LINE_AA)
                cv2.line(game_panel, (ic_x - 5, ic_y - 4), (ic_x, ic_y - 9), ic_color, 2, cv2.LINE_AA)
                cv2.line(game_panel, (ic_x + 5, ic_y - 4), (ic_x, ic_y - 9), ic_color, 2, cv2.LINE_AA)
            elif d_name == "DOWN":
                cv2.line(game_panel, (ic_x, ic_y - 9), (ic_x, ic_y + 9), ic_color, 2, cv2.LINE_AA)
                cv2.line(game_panel, (ic_x - 5, ic_y + 4), (ic_x, ic_y + 9), ic_color, 2, cv2.LINE_AA)
                cv2.line(game_panel, (ic_x + 5, ic_y + 4), (ic_x, ic_y + 9), ic_color, 2, cv2.LINE_AA)
            elif d_name == "LEFT":
                cv2.line(game_panel, (ic_x + 9, ic_y), (ic_x - 9, ic_y), ic_color, 2, cv2.LINE_AA)
                cv2.line(game_panel, (ic_x - 4, ic_y - 5), (ic_x - 9, ic_y), ic_color, 2, cv2.LINE_AA)
                cv2.line(game_panel, (ic_x - 4, ic_y + 5), (ic_x - 9, ic_y), ic_color, 2, cv2.LINE_AA)
            elif d_name == "RIGHT":
                cv2.line(game_panel, (ic_x - 9, ic_y), (ic_x + 9, ic_y), ic_color, 2, cv2.LINE_AA)
                cv2.line(game_panel, (ic_x + 4, ic_y - 5), (ic_x + 9, ic_y), ic_color, 2, cv2.LINE_AA)
                cv2.line(game_panel, (ic_x + 4, ic_y + 5), (ic_x + 9, ic_y), ic_color, 2, cv2.LINE_AA)
                
            # Panel text
            txt_color = COLOR_PLAYER_WHITE if is_hl else COLOR_TEXT
            cv2.putText(game_panel, d_name, (px_l + 50, dash_y + 22), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, txt_color, 1, cv2.LINE_AA)
            cv2.putText(game_panel, g_name, (px_l + 50, dash_y + 40), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.32, (120, 100, 95), 1, cv2.LINE_AA)
                        
        # Outer panel border
        cv2.rectangle(game_panel, (4, 4), (PANEL_W - 4, PANEL_H - 4), COLOR_WALL_BORDER, 2, cv2.LINE_AA)
        
        # 6. Compose Combined Dual-Panel View
        combined_view = cv2.hconcat([left_panel, game_panel])
        
        # Draw central divider line (neon yellow accent)
        cv2.line(combined_view, (PANEL_W, 0), (PANEL_W, PANEL_H), COLOR_WALL_BORDER, 2)
        
        # Render stitched frame to window
        cv2.imshow(WINDOW_NAME, combined_view)
        
        # Frame rate controller delay: ensures smooth loop timing
        elapsed = time.time() - frame_start
        if elapsed < target_frame_time:
            time.sleep(target_frame_time - elapsed)
            
    # Cleanup background thread and close window
    print("[INFO] Shutting down tracker thread...")
    tracker.stop()
    cv2.destroyAllWindows()
    print("[INFO] Terminated successfully.")

if __name__ == "__main__":
    main()