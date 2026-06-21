import pygame
import random
import math

class Particle:
    def __init__(self, x, y, color, size=None, vx=None, vy=None, gravity=0.1, decay=5, p_type="circle"):
        self.x = x
        self.y = y
        self.color = color
        self.size = size if size is not None else random.randint(4, 8)
        self.vx = vx if vx is not None else random.uniform(-3, 3)
        self.vy = vy if vy is not None else random.uniform(-4, 1)
        self.gravity = gravity
        self.decay = decay
        self.p_type = p_type  # circle, square, star
        self.alpha = 255
        self.angle = random.uniform(0, 360)
        self.spin = random.uniform(-5, 5)
        
    def update(self):
        self.vy += self.gravity
        self.x += self.vx
        self.y += self.vy
        self.angle += self.spin
        self.alpha = max(0, self.alpha - self.decay)
        
    def is_dead(self):
        return self.alpha <= 0 or self.size <= 0
        
    def draw(self, surface):
        if self.is_dead():
            return
            
        size_outer = int(self.size * 2)
        glow_surf = pygame.Surface((size_outer * 2, size_outer * 2), pygame.SRCALPHA)
        gc = size_outer
        
        c_glow = (self.color[0], self.color[1], self.color[2], int(self.alpha * 0.3))
        c_core = (255, 255, 255, self.alpha) if random.random() > 0.6 else (self.color[0], self.color[1], self.color[2], self.alpha)
        
        if self.p_type == "circle":
            pygame.draw.circle(glow_surf, c_glow, (gc, gc), size_outer)
            pygame.draw.circle(glow_surf, c_core, (gc, gc), self.size)
        elif self.p_type == "square":
            # Draw a rotated square on glow_surf
            r = self.size
            points = [
                (gc + int(r * math.cos(math.radians(self.angle))), gc + int(r * math.sin(math.radians(self.angle)))),
                (gc + int(r * math.cos(math.radians(self.angle + 90))), gc + int(r * math.sin(math.radians(self.angle + 90)))),
                (gc + int(r * math.cos(math.radians(self.angle + 180))), gc + int(r * math.sin(math.radians(self.angle + 180)))),
                (gc + int(r * math.cos(math.radians(self.angle + 270))), gc + int(r * math.sin(math.radians(self.angle + 270))))
            ]
            # Outer glow
            pygame.draw.polygon(glow_surf, c_glow, points, 4)
            # Inner core
            pygame.draw.polygon(glow_surf, c_core, points)
        elif self.p_type == "star":
            # Draw a 4-point star (cross)
            w = max(1, self.size // 3)
            # Glow cross
            pygame.draw.line(glow_surf, c_glow, (gc - size_outer, gc), (gc + size_outer, gc), w * 3)
            pygame.draw.line(glow_surf, c_glow, (gc, gc - size_outer), (gc, gc + size_outer), w * 3)
            # Core cross
            pygame.draw.line(glow_surf, c_core, (gc - self.size, gc), (gc + self.size, gc), w)
            pygame.draw.line(glow_surf, c_core, (gc, gc - self.size), (gc, gc + self.size), w)
            
        surface.blit(glow_surf, (int(self.x - gc), int(self.y - gc)))

class MagicMissile:
    def __init__(self, start_x, start_y, target, color, element_type):
        self.x = start_x
        self.y = start_y
        self.target = target  # Reference to target dict with {"x":, "y":}
        self.color = color
        self.element_type = element_type
        self.speed = 12.0
        self.active = True
        self.reached = False
        
    def update(self, particle_system):
        # Calculate distance to target
        tx, ty = self.target["x"], self.target["y"]
        dx = tx - self.x
        dy = ty - self.y
        dist = math.sqrt(dx**2 + dy**2)
        
        if dist < 18:
            self.reached = True
            self.active = False
            return
            
        # Move towards target
        self.x += (dx / dist) * self.speed
        self.y += (dy / dist) * self.speed
        
        # Emit colored cometary trail
        particle_system.emit_sparks(self.x, self.y, self.color, count=2)
        
    def draw(self, surface):
        size_outer = 16
        glow_surf = pygame.Surface((size_outer * 2, size_outer * 2), pygame.SRCALPHA)
        pygame.draw.circle(glow_surf, (self.color[0], self.color[1], self.color[2], 70), (size_outer, size_outer), size_outer)
        pygame.draw.circle(glow_surf, (255, 255, 255, 255), (size_outer, size_outer), 6)
        surface.blit(glow_surf, (int(self.x - size_outer), int(self.y - size_outer)))

class ParticleSystem:
    def __init__(self):
        self.particles = []
        
    def emit_explosion(self, x, y, color, count=25):
        for _ in range(count):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(2, 7)
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed
            size = random.randint(4, 9)
            decay = random.randint(4, 8)
            self.particles.append(Particle(x, y, color, size, vx, vy, gravity=0.1, decay=decay))
            
    def emit_sparks(self, x, y, color, count=3):
        for _ in range(count):
            vx = random.uniform(-1.5, 1.5)
            vy = random.uniform(-2, 1)
            self.particles.append(Particle(x, y, color, random.randint(2, 4), vx, vy, gravity=0.05, decay=12))

    def emit_elemental_burst(self, x, y, element_type, color, count=20):
        """Creates specialized physics and shapes based on magic element type."""
        for _ in range(count):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(1.5, 6)
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed
            
            if element_type == "fire":
                # Fire rises upwards wiggling
                self.particles.append(Particle(
                    x, y, color, 
                    size=random.randint(5, 10), 
                    vx=vx * 0.5, vy=-random.uniform(2, 6), 
                    gravity=-0.1, decay=random.randint(6, 12), 
                    p_type="circle"
                ))
            elif element_type == "water":
                # Water splashes outward and falls rapidly
                self.particles.append(Particle(
                    x, y, color, 
                    size=random.randint(4, 8), 
                    vx=vx, vy=vy - 2, 
                    gravity=0.25, decay=random.randint(5, 10), 
                    p_type="circle"
                ))
            elif element_type == "earth":
                # Earth falls like broken tumbling rock debris
                self.particles.append(Particle(
                    x, y, color, 
                    size=random.randint(6, 11), 
                    vx=vx * 0.8, vy=vy - 1, 
                    gravity=0.35, decay=random.randint(4, 8), 
                    p_type="square"
                ))
            elif element_type == "light":
                # Light explodes in starry sparks with low gravity
                self.particles.append(Particle(
                    x, y, color, 
                    size=random.randint(5, 9), 
                    vx=vx * 1.5, vy=vy * 1.5, 
                    gravity=0.02, decay=random.randint(8, 14), 
                    p_type="star"
                ))

    def emit_charging_ring(self, x, y, color, radius):
        """Creates particles collapsing into a ring to indicate charge progression."""
        angle = random.uniform(0, 2 * math.pi)
        px = x + math.cos(angle) * radius
        py = y + math.sin(angle) * radius
        # Velocity vector points inward to the center
        vx = -math.cos(angle) * 3
        vy = -math.sin(angle) * 3
        self.particles.append(Particle(
            px, py, color, 
            size=3, 
            vx=vx, vy=vy, 
            gravity=0, decay=20, 
            p_type="circle"
        ))
            
    def update(self):
        for p in self.particles:
            p.update()
        self.particles = [p for p in self.particles if not p.is_dead()]
        
    def draw(self, surface):
        for p in self.particles:
            p.draw(surface)
        
    def clear(self):
        self.particles.clear()
