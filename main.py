import pygame
import random
import math
import cv2
import numpy as np
import os
import json
import time

from hand_tracker import HandTracker
from sound_generator import SoundGenerator
from particles import ParticleSystem, MagicMissile

# ======================
# CONSTANTS & CONFIG
# ======================
WIDTH = 800
HEIGHT = 600
FPS = 60

# Cyberpunk Palette
COLOR_BG = (8, 8, 15)
COLOR_CYAN = (0, 240, 255)      # Water
COLOR_MAGENTA = (255, 0, 180)   # Time Warp
COLOR_LIME = (50, 255, 50)      # Earth
COLOR_YELLOW = (255, 230, 0)    # Light
COLOR_RED = (255, 40, 40)       # Fire
COLOR_WHITE = (255, 255, 255)
COLOR_ORANGE = (255, 120, 0)

STATE_MENU = "menu"
STATE_CALIBRATE = "calibrate"
STATE_GAME = "game"
STATE_GAMEOVER = "gameover"

SCORE_FILE = "neon_spellweaver_scores.json"

GESTURE_TO_ELEMENT = {
    "FIST": {"element": "fire", "color": COLOR_RED, "name": "FIRE BLAST"},
    "PALM": {"element": "water", "color": COLOR_CYAN, "name": "WATER TORRENT"},
    "PEACE": {"element": "earth", "color": COLOR_LIME, "name": "EARTH SPIKE"},
    "THUMBS_UP": {"element": "light", "color": COLOR_YELLOW, "name": "LIGHT BEAM"}
}

# ======================
# SCORE UTILITIES
# ======================
def load_high_score():
    if os.path.exists(SCORE_FILE):
        try:
            with open(SCORE_FILE, "r") as f:
                return json.load(f).get("high_score", 0)
        except:
            pass
    return 0

def save_high_score(score):
    try:
        with open(SCORE_FILE, "w") as f:
            json.dump({"high_score": score}, f)
    except:
        pass

# ======================
# BUTTON CLASS
# ======================
class Button:
    def __init__(self, x, y, w, h, text, color, action_state):
        self.rect = pygame.Rect(x, y, w, h)
        self.text = text
        self.color = color
        self.action_state = action_state
        self.hover_time = 0.0  
        self.is_hovered = False
        
    def update(self, cursor_pos, dt):
        if cursor_pos and self.rect.collidepoint(cursor_pos):
            self.is_hovered = True
            self.hover_time = min(1.0, self.hover_time + dt / 1.2)  # 1.2s hover
        else:
            self.is_hovered = False
            self.hover_time = max(0.0, self.hover_time - dt * 2.0)  
            
        return self.hover_time >= 1.0

    def draw(self, surface, font):
        if self.hover_time > 0:
            glow_surf = pygame.Surface((self.rect.width + 20, self.rect.height + 20), pygame.SRCALPHA)
            alpha = int(self.hover_time * 80)
            glow_color = (self.color[0], self.color[1], self.color[2], alpha)
            pygame.draw.rect(glow_surf, glow_color, (0, 0, self.rect.width + 20, self.rect.height + 20), border_radius=12)
            surface.blit(glow_surf, (self.rect.x - 10, self.rect.y - 10))
            
        border_width = 3 if self.is_hovered else 1
        pygame.draw.rect(surface, self.color, self.rect, border_width, border_radius=8)
        
        if self.hover_time > 0:
            fill_w = int(self.rect.width * self.hover_time)
            fill_rect = pygame.Rect(self.rect.x, self.rect.y, fill_w, self.rect.height)
            fill_color = (self.color[0], self.color[1], self.color[2], 40)
            pygame.draw.rect(surface, fill_color, fill_rect, border_radius=8)
            
        text_color = COLOR_WHITE if self.is_hovered else (200, 200, 200)
        txt = font.render(self.text, True, text_color)
        txt_rect = txt.get_rect(center=self.rect.center)
        surface.blit(txt, txt_rect)

# ======================
# GAME ORCHESTRATOR
# ======================
class NeonSpellweaver:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Neon Spellweaver: Cyber Mage")
        self.clock = pygame.time.Clock()
        
        # Fonts
        self.font_title = pygame.font.SysFont("Impact", 68)
        self.font_header = pygame.font.SysFont("Consolas", 32, bold=True)
        self.font_ui = pygame.font.SysFont("Consolas", 20, bold=True)
        self.font_score = pygame.font.SysFont("Consolas", 24, bold=True)
        
        # Synthesizer
        self.synth = SoundGenerator()
        self.synth.init_mixer()
        
        # Asynchronous Tracker
        self.tracker = HandTracker()
        self.tracker.start()
        
        # Particle System
        self.particles = ParticleSystem()
        
        # State variables
        self.state = STATE_MENU
        self.high_score = load_high_score()
        
        # Screen Shake
        self.shake_magnitude = 0.0
        self.shake_decay = 0.85
        
        # Menu Navigation
        self.buttons = []
        self._init_menu()
        
        # Gameplay variables
        self.score = 0
        self.lives = 5
        self.runes = []
        self.missiles = []
        self.last_spawn_time = 0
        self.floating_texts = []
        
        # Targeting & Charging
        self.targeted_rune = None
        self.charge_time = 0.0
        self.charge_required = 0.4  # 400ms steady hold to cast
        
        # Time Warp variables
        self.time_warp_active = False
        self.warp_energy = 100.0
        self.warp_cooldown = False
        self.last_warp_sound_time = 0
        
    def _init_menu(self):
        self.buttons = [
            Button(250, 250, 300, 50, "START CHRONICLES", COLOR_CYAN, STATE_GAME),
            Button(250, 320, 300, 50, "CALIBRATION", COLOR_LIME, STATE_CALIBRATE)
        ]
        
    def trigger_shake(self, magnitude):
        self.shake_magnitude = magnitude
        
    def get_shaked_pos(self):
        if self.shake_magnitude > 0.5:
            dx = random.uniform(-self.shake_magnitude, self.shake_magnitude)
            dy = random.uniform(-self.shake_magnitude, self.shake_magnitude)
            return int(dx), int(dy)
        return 0, 0
        
    def draw_neon_circle(self, surface, center, radius, color, width=3):
        r_glow = radius + 6
        glow = pygame.Surface((r_glow * 2, r_glow * 2), pygame.SRCALPHA)
        pygame.draw.circle(glow, (color[0], color[1], color[2], 40), (r_glow, r_glow), r_glow, width + 4)
        pygame.draw.circle(glow, (color[0], color[1], color[2], 100), (r_glow, r_glow), radius + 2, width + 2)
        pygame.draw.circle(glow, COLOR_WHITE, (r_glow, r_glow), radius, width)
        surface.blit(glow, (center[0] - r_glow, center[1] - r_glow))
        
    def draw_neon_rect(self, surface, rect, color, width=3):
        pad = 8
        glow = pygame.Surface((rect.width + pad * 2, rect.height + pad * 2), pygame.SRCALPHA)
        glow_rect = pygame.Rect(pad, pad, rect.width, rect.height)
        pygame.draw.rect(glow, (color[0], color[1], color[2], 40), glow_rect.inflate(8, 8), width + 4, border_radius=4)
        pygame.draw.rect(glow, (color[0], color[1], color[2], 100), glow_rect.inflate(4, 4), width + 2, border_radius=4)
        pygame.draw.rect(glow, COLOR_WHITE, glow_rect, width, border_radius=4)
        surface.blit(glow, (rect.x - pad, rect.y - pad))
        
    def draw_neon_triangle(self, surface, center, size, color, width=3):
        cx, cy = center
        h = int(size * math.sqrt(3) / 2)
        poly_surf = pygame.Surface((size + 20, h + 20), pygame.SRCALPHA)
        offset_x = size // 2 + 10
        offset_y = h // 2 + 10
        
        lp1 = (offset_x, offset_y - h // 2)
        lp2 = (offset_x - size // 2, offset_y + h // 2)
        lp3 = (offset_x + size // 2, offset_y + h // 2)
        
        pygame.draw.polygon(poly_surf, (color[0], color[1], color[2], 40), [lp1, lp2, lp3], width + 4)
        pygame.draw.polygon(poly_surf, (color[0], color[1], color[2], 100), [lp1, lp2, lp3], width + 2)
        pygame.draw.polygon(poly_surf, COLOR_WHITE, [lp1, lp2, lp3], width)
        surface.blit(poly_surf, (cx - offset_x, cy - offset_y))

    def run(self):
        dt = 0.0
        while self.state != "quit":
            start_time = time.time()
            self._handle_events()
            
            raw_data = self.tracker.get_data()
            cursor_pos = None
            active_gesture = raw_data["gesture"]
            
            if raw_data["index"]:
                cx, cy = raw_data["index"]
                gx = int((cx / raw_data["dims"][0]) * WIDTH)
                gy = int((cy / raw_data["dims"][1]) * HEIGHT)
                cursor_pos = (gx, gy)
            
            self.shake_magnitude = max(0.0, self.shake_magnitude * self.shake_decay)
            
            # State Updates
            if self.state == STATE_MENU:
                self._update_menu(cursor_pos, dt)
            elif self.state == STATE_CALIBRATE:
                self._update_calibrate(cursor_pos, active_gesture, dt)
            elif self.state == STATE_GAME:
                self._update_game(cursor_pos, active_gesture, dt)
            elif self.state == STATE_GAMEOVER:
                self._update_gameover(cursor_pos, dt)
                
            # Rendering phase
            sh_x, sh_y = self.get_shaked_pos()
            draw_surf = pygame.Surface((WIDTH, HEIGHT))
            draw_surf.fill(COLOR_BG)
            
            if self.state == STATE_MENU:
                self._draw_menu(draw_surf)
            elif self.state == STATE_CALIBRATE:
                self._draw_calibrate(draw_surf)
            elif self.state == STATE_GAME:
                self._draw_game(draw_surf, cursor_pos, active_gesture)
            elif self.state == STATE_GAMEOVER:
                self._draw_gameover(draw_surf)
                
            # Draw Hand Cursor
            if cursor_pos:
                cursor_color = COLOR_WHITE
                # Color match cursor to element if gesture matches
                if self.state == STATE_GAME and active_gesture in GESTURE_TO_ELEMENT:
                    cursor_color = GESTURE_TO_ELEMENT[active_gesture]["color"]
                    
                pygame.draw.circle(draw_surf, cursor_color, cursor_pos, 7)
                pygame.draw.circle(draw_surf, (cursor_color[0], cursor_color[1], cursor_color[2], 90), cursor_pos, 13, 2)
                
                # Render radial loader for menus
                if self.state in [STATE_MENU, STATE_GAMEOVER]:
                    for btn in self.buttons:
                        if btn.is_hovered:
                            pygame.draw.arc(draw_surf, COLOR_YELLOW, 
                                            (cursor_pos[0]-16, cursor_pos[1]-16, 32, 32), 
                                            0, btn.hover_time * 2 * math.pi, 3)
            
            self.screen.blit(draw_surf, (sh_x, sh_y))
            pygame.display.flip()
            
            self.clock.tick(FPS)
            dt = time.time() - start_time
            
        self.tracker.stop()
        pygame.quit()

    def _handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.state = "quit"
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if self.state in [STATE_GAME, STATE_CALIBRATE]:
                        self.state = STATE_MENU
                        self.particles.clear()
                        self._init_menu()
                    else:
                        self.state = "quit"

    # ======================
    # MENU SCREEN
    # ======================
    def _update_menu(self, cursor_pos, dt):
        for btn in self.buttons:
            if btn.update(cursor_pos, dt):
                self.synth.play("score")
                self.state = btn.action_state
                self.particles.clear()
                
                if self.state == STATE_GAME:
                    # Reset game stats
                    self.score = 0
                    self.lives = 5
                    self.runes = []
                    self.missiles = []
                    self.floating_texts = []
                    self.targeted_rune = None
                    self.charge_time = 0.0
                    self.warp_energy = 100.0
                    self.time_warp_active = False
                elif self.state == STATE_CALIBRATE:
                    self.buttons = [Button(250, 480, 300, 50, "BACK TO MENU", COLOR_CYAN, STATE_MENU)]
                break
                
    def _draw_menu(self, surf):
        # Draw tech matrix background
        for i in range(0, WIDTH, 80):
            pygame.draw.line(surf, (15, 15, 28), (i, 0), (i, HEIGHT))
        for j in range(0, HEIGHT, 80):
            pygame.draw.line(surf, (15, 15, 28), (0, j), (WIDTH, j))
            
        # Draw glowing Title
        title_txt = self.font_title.render("NEON SPELLWEAVER", True, COLOR_CYAN)
        t_glow = self.font_title.render("NEON SPELLWEAVER", True, (0, 100, 255))
        surf.blit(t_glow, (113, 93))
        surf.blit(title_txt, (110, 90))
        
        sub_txt = self.font_ui.render("GESTURE-DRIVEN CYBERMAGE SIMULATOR", True, COLOR_MAGENTA)
        surf.blit(sub_txt, (200, 175))
        
        # Buttons
        for btn in self.buttons:
            btn.draw(surf, self.font_header)
            
        # High Score
        hs_txt = self.font_score.render(f"GRAND HIGH SCORE: {self.high_score}", True, COLOR_YELLOW)
        surf.blit(hs_txt, (WIDTH // 2 - hs_txt.get_width() // 2, 410))

    # ======================
    # CALIBRATION CONSOLE
    # ======================
    def _update_calibrate(self, cursor_pos, active_gesture, dt):
        for btn in self.buttons:
            if btn.update(cursor_pos, dt):
                self.synth.play("score")
                self.state = btn.action_state
                self._init_menu()
                break
                
        # Spawn test sparks matching gesture
        if active_gesture in GESTURE_TO_ELEMENT and cursor_pos:
            color = GESTURE_TO_ELEMENT[active_gesture]["color"]
            element = GESTURE_TO_ELEMENT[active_gesture]["element"]
            self.particles.emit_elemental_burst(cursor_pos[0], cursor_pos[1], element, color, count=1)
        self.particles.update()

    def _draw_calibrate(self, surf):
        title = self.font_header.render("GESTURE CALIBRATION SCREEN", True, COLOR_LIME)
        surf.blit(title, (180, 25))
        
        frame = self.tracker.get_frame()
        raw_data = self.tracker.get_data()
        active_gesture = raw_data["gesture"]
        
        # Map element borders to classified gesture
        outline_color = COLOR_WHITE
        if active_gesture in GESTURE_TO_ELEMENT:
            outline_color = GESTURE_TO_ELEMENT[active_gesture]["color"]
        elif active_gesture == "ROCK_ON":
            outline_color = COLOR_MAGENTA
            
        if frame is not None:
            frame = cv2.resize(frame, (400, 300))
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frame_rgb = np.transpose(frame_rgb, (1, 0, 2))
            frame_surf = pygame.surfarray.make_surface(frame_rgb)
            
            x = (WIDTH - 400) // 2
            y = 100
            surf.blit(frame_surf, (x, y))
            # Glowing border mapping active gesture
            pygame.draw.rect(surf, outline_color, (x - 3, y - 3, 406, 306), 3, border_radius=4)
        else:
            pygame.draw.rect(surf, COLOR_RED, (200, 100, 400, 300), 2)
            error_txt = self.font_header.render("CAMERA LOADING...", True, COLOR_RED)
            surf.blit(error_txt, (280, 230))
            
        # Displays detected values
        fps_txt = self.font_ui.render(f"CAMERA INFERENCE RATE: {raw_data['fps']} FPS", True, COLOR_WHITE)
        gest_lbl = "ACTIVE GESTURE: " + (active_gesture if active_gesture != "NONE" else "NO POSTURE DETECTED")
        gest_txt = self.font_ui.render(gest_lbl, True, outline_color)
        
        # Legend guide for user
        surf.blit(fps_txt, (200, 415))
        surf.blit(gest_txt, (200, 440))
        
        legend = self.font_ui.render("Fist=Fire | Palm=Water | Peace=Earth | ThumbsUp=Light | RockOn=SlowTime", True, (150, 150, 160))
        surf.blit(legend, (WIDTH // 2 - legend.get_width() // 2, 545))
        
        self.particles.draw(surf)
        
        for btn in self.buttons:
            btn.draw(surf, self.font_header)

    # ======================
    # GAMEPLAY STATE
    # ======================
    def _update_game(self, cursor_pos, active_gesture, dt):
        curr_time = time.time()
        
        # ======================
        # TIME WARP MECHANIC
        # ======================
        self.time_warp_active = False
        if active_gesture == "ROCK_ON" and not self.warp_cooldown:
            self.time_warp_active = True
            # Drain energy
            self.warp_energy = max(0.0, self.warp_energy - dt * 28.0)
            if self.warp_energy <= 0.0:
                self.warp_cooldown = True  # Lock warp
                self.synth.play("error")
                
            # Play warp slow sound periodically
            if curr_time - self.last_warp_sound_time > 0.8:
                self.synth.play("warp")
                self.last_warp_sound_time = curr_time
        else:
            # Regenerate energy
            self.warp_energy = min(100.0, self.warp_energy + dt * 14.0)
            if self.warp_cooldown and self.warp_energy >= 30.0:
                self.warp_cooldown = False  # Recharge lock released
                
        time_scale = 0.20 if self.time_warp_active else 1.0
        
        # ======================
        # SPAWN RUNES
        # ======================
        spawn_rate = max(0.8, 2.2 - (self.score * 0.015))
        if curr_time - self.last_spawn_time > (spawn_rate / time_scale):
            self.last_spawn_time = curr_time
            self.runes.append(self._spawn_rune())
            
        # ======================
        # RUNES UPDATE (PHYSICS)
        # ======================
        cx, cy = WIDTH // 2, HEIGHT // 2
        for r in self.runes:
            r["x"] += r["vx"] * time_scale
            r["y"] += r["vy"] * time_scale
            r["angle"] += r["spin"] * time_scale
            
            # Check core collision
            dist = math.sqrt((r["x"] - cx)**2 + (r["y"] - cy)**2)
            if dist < 50:
                r["destroyed"] = True
                self.lives -= 1
                self.synth.play("shield")
                self.trigger_shake(15.0)
                self.particles.emit_explosion(cx, cy, COLOR_RED, count=15)
                # Force reset targeting if hit
                if self.targeted_rune and self.targeted_rune["id"] == r["id"]:
                    self.targeted_rune = None
                    self.charge_time = 0.0
                    
        # Filter dead runes
        self.runes = [r for r in self.runes if not r["destroyed"]]
        
        # ======================
        # TARGETING & SPELLCASTING
        # ======================
        if cursor_pos and active_gesture in GESTURE_TO_ELEMENT:
            target_elem = GESTURE_TO_ELEMENT[active_gesture]["element"]
            target_color = GESTURE_TO_ELEMENT[active_gesture]["color"]
            
            # Find closest matching rune that is not already targeted or heading for missile
            best_rune = None
            min_dist = 99999.0
            
            for r in self.runes:
                if r["element"] == target_elem and not r["targeted"]:
                    d_core = math.sqrt((r["x"] - cx)**2 + (r["y"] - cy)**2)
                    if d_core < min_dist:
                        min_dist = d_core
                        best_rune = r
                        
            # If target changes, reset charge
            if best_rune:
                if not self.targeted_rune or self.targeted_rune["id"] != best_rune["id"]:
                    self.targeted_rune = best_rune
                    self.charge_time = 0.0
            else:
                self.targeted_rune = None
                self.charge_time = 0.0
                
            # If target exists, charge the spell
            if self.targeted_rune:
                self.charge_time += dt
                # Emit collapsing particles around hand cursor showing it is charging
                self.particles.emit_charging_ring(cursor_pos[0], cursor_pos[1], target_color, radius=35)
                
                # Check casting completion
                if self.charge_time >= self.charge_required:
                    # Fire homing projectile!
                    self.targeted_rune["targeted"] = True
                    self.missiles.append(MagicMissile(cx, cy, self.targeted_rune, target_color, target_elem))
                    self.synth.play(target_elem)
                    
                    # Reset target search
                    self.targeted_rune = None
                    self.charge_time = 0.0
        else:
            # Gesture released/changed
            self.targeted_rune = None
            self.charge_time = 0.0
            
        # ======================
        # HOMING MISSILES UPDATE
        # ======================
        for m in self.missiles:
            m.update(self.particles)
            if m.reached:
                # Missile hit! Mark target rune as destroyed
                m_target_id = m.target["id"]
                for r in self.runes:
                    if r["id"] == m_target_id:
                        r["destroyed"] = True
                        self.score += 10
                        self.synth.play("score")
                        self.particles.emit_elemental_burst(r["x"], r["y"], m.element_type, m.color, count=25)
                        
        self.missiles = [m for m in self.missiles if m.active]
        
        # Clean destroyed runes
        self.runes = [r for r in self.runes if not r["destroyed"]]
        
        # Particles
        self.particles.update()
        
        # Game Over Check
        if self.lives <= 0:
            self.state = STATE_GAMEOVER
            if self.score > self.high_score:
                self.high_score = self.score
                save_high_score(self.high_score)
            self.buttons = [
                Button(250, 360, 300, 50, "PLAY AGAIN", COLOR_CYAN, STATE_GAME),
                Button(250, 430, 300, 50, "MAIN MENU", COLOR_MAGENTA, STATE_MENU)
            ]
            self.targeted_rune = None
            self.charge_time = 0.0
            
    def _spawn_rune(self):
        side = random.choice(["top", "bottom", "left", "right"])
        if side == "top":
            rx = random.randint(50, WIDTH - 50)
            ry = -30
        elif side == "bottom":
            rx = random.randint(50, WIDTH - 50)
            ry = HEIGHT + 30
        elif side == "left":
            rx = -30
            ry = random.randint(50, HEIGHT - 50)
        else:
            rx = WIDTH + 30
            ry = random.randint(50, HEIGHT - 50)
            
        element = random.choice(["fire", "water", "earth", "light"])
        color = GESTURE_TO_ELEMENT[random.choice(list(GESTURE_TO_ELEMENT.keys()))]["color"] # defaults
        for k, v in GESTURE_TO_ELEMENT.items():
            if v["element"] == element:
                color = v["color"]
                break
                
        # Calculate velocity pointing at center core (400, 300)
        cx, cy = WIDTH // 2, HEIGHT // 2
        dx = cx - rx
        dy = cy - ry
        dist = math.sqrt(dx**2 + dy**2)
        
        # Scale speed based on score difficulty
        speed = random.uniform(1.2, 2.0) + (self.score * 0.003)
        speed = min(speed, 4.5)  # Cap speed
        
        vx = (dx / dist) * speed
        vy = (dy / dist) * speed
        
        return {
            "id": random.randint(100000, 999999),
            "x": rx,
            "y": ry,
            "vx": vx,
            "vy": vy,
            "element": element,
            "color": color,
            "targeted": False,
            "destroyed": False,
            "angle": random.uniform(0, 360),
            "spin": random.uniform(-3, 3)
        }

    # ======================
    # GAMEPLAY RENDERING
    # ======================
    def _draw_game(self, surf, cursor_pos, active_gesture):
        # 1. Background grid
        for i in range(0, WIDTH, 100):
            pygame.draw.line(surf, (12, 12, 22), (i, 0), (i, HEIGHT))
        for j in range(0, HEIGHT, 100):
            pygame.draw.line(surf, (12, 12, 22), (0, j), (WIDTH, j))
            
        # 2. Draw Center Defense Shield Core
        cx, cy = WIDTH // 2, HEIGHT // 2
        core_color = COLOR_WHITE
        if active_gesture in GESTURE_TO_ELEMENT:
            core_color = GESTURE_TO_ELEMENT[active_gesture]["color"]
            
        # Draw glowing core boundaries
        self.draw_neon_circle(surf, (cx, cy), 40, core_color, width=4)
        pygame.draw.circle(surf, (15, 15, 30), (cx, cy), 36)
        # Inner glowing core
        inner_pulse = int(12 + math.sin(time.time() * 8) * 3)
        pygame.draw.circle(surf, core_color, (cx, cy), inner_pulse)
        
        # 3. Draw targeting laser vector if active
        if self.targeted_rune and cursor_pos:
            r = self.targeted_rune
            t_color = r["color"]
            # Draw laser targeting beam
            pygame.draw.line(surf, (255, 255, 255, 180), (cx, cy), (int(r["x"]), int(r["y"])), 1)
            pygame.draw.line(surf, (t_color[0], t_color[1], t_color[2], 60), (cx, cy), (int(r["x"]), int(r["y"])), 6)
            # Draw lock-on reticle around rune
            pygame.draw.circle(surf, t_color, (int(r["x"]), int(r["y"])), 30, 2)
            
        # 4. Draw Runes
        for r in self.runes:
            pos = (int(r["x"]), int(r["y"]))
            color = r["color"]
            size = 20
            
            if r["element"] == "fire":
                # Red flame circle
                self.draw_neon_circle(surf, pos, size, color)
            elif r["element"] == "water":
                # Blue water square
                rect = pygame.Rect(pos[0]-size, pos[1]-size, size*2, size*2)
                self.draw_neon_rect(surf, rect, color)
            elif r["element"] == "earth":
                # Green earth triangle
                self.draw_neon_triangle(surf, pos, size*2, color)
            elif r["element"] == "light":
                # Yellow light cross star
                # Let's draw custom neon star
                glow_surf = pygame.Surface((size*3, size*3), pygame.SRCALPHA)
                gc = size * 1.5
                pygame.draw.line(glow_surf, (color[0], color[1], color[2], 50), (gc-size*1.5, gc), (gc+size*1.5, gc), 6)
                pygame.draw.line(glow_surf, (color[0], color[1], color[2], 50), (gc, gc-size*1.5), (gc, gc+size*1.5), 6)
                pygame.draw.line(glow_surf, COLOR_WHITE, (gc-size, gc), (gc+size, gc), 2)
                pygame.draw.line(glow_surf, COLOR_WHITE, (gc, gc-size), (gc, gc+size), 2)
                surf.blit(glow_surf, (pos[0]-gc, pos[1]-gc))
                
        # 5. Draw Projectiles & Particles
        for m in self.missiles:
            m.draw(surf)
        self.particles.draw(surf)
        
        # 6. Draw Charging Progress Arc on Hand
        if self.targeted_rune and cursor_pos:
            target_color = self.targeted_rune["color"]
            progress = self.charge_time / self.charge_required
            pygame.draw.arc(surf, target_color, 
                            (cursor_pos[0]-25, cursor_pos[1]-25, 50, 50), 
                            0, progress * 2 * math.pi, 4)
            # Text casting warning
            cast_name = GESTURE_TO_ELEMENT[active_gesture]["name"]
            txt_cast = self.font_ui.render(f"CHARGING {cast_name}...", True, target_color)
            surf.blit(txt_cast, (cursor_pos[0] - txt_cast.get_width() // 2, cursor_pos[1] - 45))
            
        # 7. Draw Time Warp Vignette Overlay
        if self.time_warp_active:
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            # Blue cyber tint
            overlay.fill((0, 20, 60, 60))
            # Pulse vignette borders
            pulse_thick = int(25 + math.sin(time.time() * 12) * 5)
            pygame.draw.rect(overlay, (0, 120, 255, 45), (0, 0, WIDTH, HEIGHT), pulse_thick)
            surf.blit(overlay, (0, 0))
            
            # Warning text
            txt_warp = self.font_header.render("TIME WARP DILATION ACTIVE", True, COLOR_MAGENTA)
            surf.blit(txt_warp, (WIDTH // 2 - txt_warp.get_width() // 2, 85))
            
        # 8. HUD & UI Elements
        # Score & Shield bars
        score_txt = self.font_header.render(f"SCORE: {self.score}", True, COLOR_CYAN)
        surf.blit(score_txt, (25, 20))
        
        # Draw Lives (Shield integrity cells)
        cell_w, cell_h = 24, 12
        cell_gap = 6
        x_start = WIDTH - 200
        y_pos = 32
        # Label
        lbl_shield = self.font_ui.render("SHIELD INTEGRITY: ", True, COLOR_WHITE)
        surf.blit(lbl_shield, (x_start - lbl_shield.get_width() - 5, y_pos - 4))
        for i in range(5):
            cell_rect = pygame.Rect(x_start + i * (cell_w + cell_gap), y_pos, cell_w, cell_h)
            if i < self.lives:
                # Active cell
                pygame.draw.rect(surf, COLOR_RED, cell_rect, border_radius=2)
                pygame.draw.rect(surf, COLOR_WHITE, cell_rect, 1, border_radius=2)
            else:
                # Inactive cell
                pygame.draw.rect(surf, (40, 10, 10), cell_rect, border_radius=2)
                pygame.draw.rect(surf, (70, 20, 20), cell_rect, 1, border_radius=2)
                
        # Time Warp Energy Meter (Bottom of the screen)
        bar_w = 400
        bar_h = 10
        bar_x = WIDTH // 2 - bar_w // 2
        bar_y = HEIGHT - 30
        
        # Draw energy bar box
        pygame.draw.rect(surf, (20, 20, 35), (bar_x, bar_y, bar_w, bar_h), border_radius=4)
        energy_color = COLOR_MAGENTA if not self.warp_cooldown else COLOR_RED
        # Calculate width based on energy percentage
        fill_w = int(bar_w * (self.warp_energy / 100.0))
        pygame.draw.rect(surf, energy_color, (bar_x, bar_y, fill_w, bar_h), border_radius=4)
        pygame.draw.rect(surf, COLOR_WHITE, (bar_x, bar_y, bar_w, bar_h), 1, border_radius=4)
        
        # Label Time Warp energy
        lbl_energy = self.font_ui.render(f"WARP CHRONO-CHARGE: {int(self.warp_energy)}%", True, energy_color)
        surf.blit(lbl_energy, (WIDTH // 2 - lbl_energy.get_width() // 2, bar_y - 22))
        
        # PIP Camera Window
        self._draw_pip(surf)

    # ======================
    # GAMEOVER SCREEN
    # ======================
    def _update_gameover(self, cursor_pos, dt):
        for btn in self.buttons:
            if btn.update(cursor_pos, dt):
                self.synth.play("score")
                self.state = btn.action_state
                self.particles.clear()
                
                if self.state == STATE_GAME:
                    # Reset game stats
                    self.score = 0
                    self.lives = 5
                    self.runes = []
                    self.missiles = []
                    self.floating_texts = []
                    self.targeted_rune = None
                    self.charge_time = 0.0
                    self.warp_energy = 100.0
                    self.time_warp_active = False
                elif self.state == STATE_MENU:
                    self._init_menu()
                break

    def _draw_gameover(self, surf):
        go_txt = self.font_title.render("SHIELD COLLAPSED", True, COLOR_RED)
        surf.blit(go_txt, (WIDTH // 2 - go_txt.get_width() // 2, 110))
        
        score_txt = self.font_header.render(f"SPELLS CAST SCORE: {self.score}", True, COLOR_CYAN)
        surf.blit(score_txt, (WIDTH // 2 - score_txt.get_width() // 2, 210))
        
        # High Score comparison
        if self.score >= self.high_score and self.score > 0:
            hs_txt = self.font_header.render("NEW GRAND HIGH SCORE!", True, COLOR_YELLOW)
            surf.blit(hs_txt, (WIDTH // 2 - hs_txt.get_width() // 2, 270))
            
        for btn in self.buttons:
            btn.draw(surf, self.font_header)

    # ======================
    # GRAPHICS HELPER: PIP OVERLAY
    # ======================
    def _draw_pip(self, surf):
        frame = self.tracker.get_frame()
        if frame is not None:
            # Scaled webcam window
            frame = cv2.resize(frame, (160, 120))
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frame_rgb = np.transpose(frame_rgb, (1, 0, 2))
            frame_surf = pygame.surfarray.make_surface(frame_rgb)
            
            x = WIDTH - 185
            y = 65
            surf.blit(frame_surf, (x, y))
            pygame.draw.rect(surf, COLOR_CYAN, (x-1, y-1, 162, 122), 1)

# ======================
# ENTRY POINT
# ======================
if __name__ == "__main__":
    game = NeonSpellweaver()
    game.run()