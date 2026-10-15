#!/usr/bin/env python3
"""Aquamarine Avalanche — full-colour Python 3 neon gem-catch arcade for ElbowOS.
Catch falling aqua gems with the paddle. Avoid magenta mines.
https://x.com/ElbowOS
"""
import os
import sys
import random
import subprocess
import pygame

# Constants
W, H = 1080, 1920
FPS = 30
DURATION = 15
TITLE = "AQUAMARINE AVALANCHE"
BRAND = "x.com/ElbowOS"

# Colours
BG = (8, 12, 28)
AQUA = (0, 255, 220)
CYAN = (0, 200, 255)
MAGENTA = (255, 0, 180)
GOLD = (255, 220, 0)
WHITE = (240, 245, 255)
NEON_PURPLE = (180, 0, 255)

class Gem:
    def __init__(self):
        self.x = random.randint(40, W - 40)
        self.y = -40
        self.r = random.randint(18, 32)
        self.speed = random.uniform(6, 12)
        self.good = random.random() > 0.22  # mostly good
        self.color = AQUA if self.good else MAGENTA

    def update(self):
        self.y += self.speed
        return self.y < H + 40

    def draw(self, surf):
        pygame.draw.circle(surf, self.color, (int(self.x), int(self.y)), self.r)
        pygame.draw.circle(surf, WHITE, (int(self.x), int(self.y)), self.r, 2)
        if not self.good:
            pygame.draw.line(surf, WHITE, (self.x - 10, self.y - 10), (self.x + 10, self.y + 10), 3)
            pygame.draw.line(surf, WHITE, (self.x + 10, self.y - 10), (self.x - 10, self.y + 10), 3)

class Game:
    def __init__(self):
        pygame.init()
        pygame.font.init()
        self.font_lg = pygame.font.SysFont("monospace", 72, bold=True)
        self.font_sm = pygame.font.SysFont("monospace", 36, bold=True)
        self.reset()

    def reset(self):
        self.paddle_x = W // 2
        self.paddle_w = 180
        self.score = 0
        self.gems = []
        self.spawn_t = 0
        self.time = 0
        self.combo = 0

    def spawn(self):
        if self.spawn_t <= 0:
            self.gems.append(Gem())
            self.spawn_t = max(8, 28 - self.score // 10)
        else:
            self.spawn_t -= 1

    def update(self, dx=0):
        self.time += 1
        self.paddle_x = max(self.paddle_w // 2, min(W - self.paddle_w // 2, self.paddle_x + dx))
        self.spawn()
        hit_paddle = False
        new_gems = []
        for g in self.gems:
            if g.update():
                # collision with paddle
                if abs(g.x - self.paddle_x) < self.paddle_w // 2 + g.r and H - 120 < g.y < H - 80:
                    if g.good:
                        self.score += 10 + self.combo
                        self.combo = min(9, self.combo + 1)
                    else:
                        self.score = max(0, self.score - 25)
                        self.combo = 0
                    hit_paddle = True
                else:
                    new_gems.append(g)
            else:
                if g.good:
                    self.combo = 0  # missed good
        self.gems = new_gems
        return hit_paddle

    def draw(self, surf):
        surf.fill(BG)
        # subtle grid
        for i in range(0, W, 60):
            pygame.draw.line(surf, (20, 30, 50), (i, 0), (i, H), 1)
        for j in range(0, H, 60):
            pygame.draw.line(surf, (20, 30, 50), (0, j), (W, j), 1)
        # gems
        for g in self.gems:
            g.draw(surf)
        # paddle
        py = H - 100
        pygame.draw.rect(surf, CYAN, (self.paddle_x - self.paddle_w // 2, py, self.paddle_w, 28), border_radius=14)
        pygame.draw.rect(surf, AQUA, (self.paddle_x - self.paddle_w // 2, py, self.paddle_w, 28), 4, border_radius=14)
        # overlays
        title = self.font_lg.render(TITLE, True, AQUA)
        surf.blit(title, title.get_rect(center=(W // 2, 80)))
        sc = self.font_sm.render(f"SCORE {self.score}  COMBO x{self.combo}", True, GOLD)
        surf.blit(sc, sc.get_rect(center=(W // 2, 160)))
        brand = self.font_sm.render(BRAND, True, NEON_PURPLE)
        surf.blit(brand, brand.get_rect(center=(W // 2, H - 40)))

    def auto_dx(self):
        # simple AI: move toward nearest good gem near bottom
        target = None
        best_d = 9999
        for g in self.gems:
            if g.good and g.y > H * 0.4:
                d = abs(g.x - self.paddle_x)
                if d < best_d:
                    best_d = d
                    target = g.x
        if target is None:
            return random.choice([-8, 0, 8])
        if target > self.paddle_x + 10:
            return 12
        if target < self.paddle_x - 10:
            return -12
        return 0

    def record(self, out_path):
        os.environ["SDL_VIDEODRIVER"] = "dummy"
        pygame.display.set_mode((1, 1))  # minimal
        surf = pygame.Surface((W, H))
        frames = DURATION * FPS
        cmd = [
            "ffmpeg", "-y",
            "-f", "rawvideo", "-vcodec", "rawvideo",
            "-s", f"{W}x{H}", "-pix_fmt", "rgb24",
            "-r", str(FPS), "-i", "-",
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-crf", "20", "-preset", "fast",
            "-movflags", "+faststart",
            out_path
        ]
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
        self.reset()
        for i in range(frames):
            dx = self.auto_dx()
            self.update(dx)
            self.draw(surf)
            # pipe RGB
            raw = pygame.image.tostring(surf, "RGB")
            try:
                proc.stdin.write(raw)
            except BrokenPipeError:
                break
        proc.stdin.close()
        err = proc.stderr.read().decode(errors="ignore")
        rc = proc.wait()
        if rc != 0:
            print("ffmpeg failed:", err[-800:], file=sys.stderr)
            sys.exit(1)
        print("wrote", out_path)
        pygame.quit()

    def play(self):
        screen = pygame.display.set_mode((W // 2, H // 2))
        clock = pygame.time.Clock()
        surf = pygame.Surface((W, H))
        running = True
        while running:
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT or (ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE):
                    running = False
            keys = pygame.key.get_pressed()
            dx = 0
            if keys[pygame.K_LEFT] or keys[pygame.K_a]:
                dx = -14
            if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
                dx = 14
            self.update(dx)
            self.draw(surf)
            scaled = pygame.transform.smoothscale(surf, (W // 2, H // 2))
            screen.blit(scaled, (0, 0))
            pygame.display.flip()
            clock.tick(FPS)
        pygame.quit()

def main():
    g = Game()
    if "--record" in sys.argv:
        out = "/workspace/artifacts/AquamarineAvalanche_ElbowOS.mp4"
        g.record(out)
    else:
        g.play()

if __name__ == "__main__":
    main()
