"""
Fighting Game sederhana berbasis Pygame - 2 Pemain
Kontrol:
  Pemain 1 (Kiri, biru):
    A / D  = Gerak kiri/kanan
    W      = Lompat
    F      = Pukul (jarak dekat)
    G      = Tendang (jangkauan lebih jauh, damage lebih besar)
  Pemain 2 (Kanan, merah):
    Panah Kiri/Kanan = Gerak
    Panah Atas       = Lompat
    Numpad 1 / K     = Pukul
    Numpad 2 / L     = Tendang

R = restart setelah game selesai
C = ganti Player 2 antara manusia <-> CPU (gerakan acak sederhana)
ESC = keluar
"""

import pygame
import sys
import random

pygame.init()

WIDTH, HEIGHT = 960, 540
FLOOR_Y = HEIGHT - 80

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Pygame Fighting Game")
clock = pygame.time.Clock()
FPS = 60

# Warna
WHITE = (245, 245, 245)
BLACK = (20, 20, 20)
BLUE = (60, 120, 220)
RED = (210, 60, 60)
DARK_BLUE = (30, 60, 120)
DARK_RED = (120, 30, 30)
GREEN = (60, 200, 90)
YELLOW = (240, 210, 60)
GRAY = (90, 90, 90)
SKY = (25, 25, 40)

font_big = pygame.font.SysFont("arial", 64, bold=True)
font_med = pygame.font.SysFont("arial", 32, bold=True)
font_small = pygame.font.SysFont("arial", 20)

GRAVITY = 0.9
JUMP_SPEED = -16
MOVE_SPEED = 5
MAX_HEALTH = 100

PUNCH_RANGE = 70
PUNCH_DAMAGE = 6
PUNCH_COOLDOWN = 18   # frame

KICK_RANGE = 95
KICK_DAMAGE = 10
KICK_COOLDOWN = 32

HITSTUN = 12  # frame kena knockback saat dipukul


class Fighter:
    def __init__(self, x, color_main, color_dark, facing, controls, name, is_cpu=False):
        self.x = x
        self.y = FLOOR_Y
        self.w = 60
        self.h = 120
        self.vel_y = 0
        self.on_ground = True
        self.facing = facing  # 1 = hadap kanan, -1 = hadap kiri
        self.color_main = color_main
        self.color_dark = color_dark
        self.health = MAX_HEALTH
        self.controls = controls
        self.name = name

        self.is_cpu = is_cpu
        self.ai_timer = 0
        self.ai_move = 0        # -1 kiri, 0 diam, 1 kanan
        self.ai_want_jump = False
        self.ai_want_punch = False
        self.ai_want_kick = False

        self.attack_type = None   # "punch" / "kick"
        self.attack_timer = 0
        self.attack_active_frame = 0
        self.punch_cd = 0
        self.kick_cd = 0
        self.hit_landed = False

        self.hurt_timer = 0
        self.knockback = 0

        self.win = False

    def rect(self):
        return pygame.Rect(self.x - self.w // 2, self.y - self.h, self.w, self.h)

    def attack_hitbox(self):
        if self.attack_type is None:
            return None
        range_ = PUNCH_RANGE if self.attack_type == "punch" else KICK_RANGE
        if self.facing == 1:
            return pygame.Rect(int(self.x + self.w // 2), int(self.y - self.h * 0.65), range_, 30)
        else:
            return pygame.Rect(int(self.x - self.w // 2 - range_), int(self.y - self.h * 0.65), range_, 30)

    def start_attack(self, kind):
        if self.attack_type is not None:
            return
        if kind == "punch" and self.punch_cd <= 0:
            self.attack_type = "punch"
            self.attack_timer = PUNCH_COOLDOWN
            self.attack_active_frame = 6
            self.punch_cd = PUNCH_COOLDOWN
            self.hit_landed = False
        elif kind == "kick" and self.kick_cd <= 0:
            self.attack_type = "kick"
            self.attack_timer = KICK_COOLDOWN
            self.attack_active_frame = 10
            self.kick_cd = KICK_COOLDOWN
            self.hit_landed = False

    def ai_think(self, opponent):
        """AI acak sederhana: ganti keputusan tiap beberapa frame."""
        self.ai_timer -= 1
        if self.ai_timer <= 0:
            self.ai_timer = random.randint(10, 40)
            self.ai_move = random.choice([-1, 0, 0, 1])
            self.ai_want_jump = random.random() < 0.15
            self.ai_want_punch = random.random() < 0.25
            self.ai_want_kick = random.random() < 0.15

        dist = abs(opponent.x - self.x)
        if dist < PUNCH_RANGE + self.w and random.random() < 0.06:
            self.ai_want_punch = True
        if dist < KICK_RANGE + self.w and random.random() < 0.03:
            self.ai_want_kick = True

    def update(self, keys, opponent):
        if self.win:
            return

        c = self.controls
        moving = False

        if self.is_cpu:
            self.ai_think(opponent)

        if self.hurt_timer <= 0:
            if self.is_cpu:
                if self.ai_move == -1:
                    self.x -= MOVE_SPEED
                    self.facing = -1
                    moving = True
                elif self.ai_move == 1:
                    self.x += MOVE_SPEED
                    self.facing = 1
                    moving = True
                if self.ai_want_jump and self.on_ground:
                    self.vel_y = JUMP_SPEED
                    self.on_ground = False
                if self.ai_want_punch:
                    self.start_attack("punch")
                    self.ai_want_punch = False
                if self.ai_want_kick:
                    self.start_attack("kick")
                    self.ai_want_kick = False
            else:
                if keys[c["left"]]:
                    self.x -= MOVE_SPEED
                    self.facing = -1
                    moving = True
                if keys[c["right"]]:
                    self.x += MOVE_SPEED
                    self.facing = 1
                    moving = True
                if keys[c["jump"]] and self.on_ground:
                    self.vel_y = JUMP_SPEED
                    self.on_ground = False

                if keys[c["punch"]]:
                    self.start_attack("punch")
                if keys[c["kick"]]:
                    self.start_attack("kick")
        else:
            self.hurt_timer -= 1
            self.x += self.knockback

        # gravitasi
        self.vel_y += GRAVITY
        self.y += self.vel_y
        if self.y >= FLOOR_Y:
            self.y = FLOOR_Y
            self.vel_y = 0
            self.on_ground = True

        # batas layar
        self.x = max(self.w // 2 + 5, min(WIDTH - self.w // 2 - 5, self.x))

        # auto-facing kalau tidak sedang serang
        if self.attack_type is None:
            if opponent.x > self.x:
                self.facing = 1
            else:
                self.facing = -1

        # update attack
        if self.attack_type is not None:
            self.attack_active_frame -= 1
            self.attack_timer -= 1

            if 0 <= self.attack_active_frame <= 4 and not self.hit_landed:
                hb = self.attack_hitbox()
                if hb and hb.colliderect(opponent.rect()):
                    dmg = PUNCH_DAMAGE if self.attack_type == "punch" else KICK_DAMAGE
                    opponent.take_hit(dmg, self.facing)
                    self.hit_landed = True

            if self.attack_timer <= 0:
                self.attack_type = None

        if self.punch_cd > 0:
            self.punch_cd -= 1
        if self.kick_cd > 0:
            self.kick_cd -= 1

    def take_hit(self, dmg, attacker_facing):
        self.health = max(0, self.health - dmg)
        self.hurt_timer = HITSTUN
        self.knockback = attacker_facing * 4

    def draw(self, surf):
        r = self.rect()
        color = self.color_dark if self.hurt_timer > 0 else self.color_main

        # badan
        pygame.draw.rect(surf, color, r, border_radius=10)
        # kepala
        head_r = 18
        head_c = (int(self.x), int(self.y - self.h - head_r + 4))
        pygame.draw.circle(surf, color, head_c, head_r)

        # mata (arah hadap)
        eye_x = head_c[0] + self.facing * 8
        pygame.draw.circle(surf, WHITE, (eye_x, head_c[1] - 3), 4)

        # lengan serang
        if self.attack_type is not None and self.attack_active_frame > -6:
            hb = self.attack_hitbox()
            arm_color = YELLOW if self.attack_type == "kick" else (255, 255, 255)
            if hb:
                pygame.draw.rect(surf, arm_color, hb, border_radius=6)

    def health_ratio(self):
        return self.health / MAX_HEALTH


p1_controls = {
    "left": pygame.K_a, "right": pygame.K_d, "jump": pygame.K_w,
    "punch": pygame.K_f, "kick": pygame.K_g,
}
p2_controls = {
    "left": pygame.K_LEFT, "right": pygame.K_RIGHT, "jump": pygame.K_UP,
    "punch": pygame.K_k, "kick": pygame.K_l,
}


def new_fighters(p2_is_cpu=True):
    p1 = Fighter(WIDTH * 0.25, BLUE, DARK_BLUE, 1, p1_controls, "PLAYER 1")
    p2 = Fighter(WIDTH * 0.75, RED, DARK_RED, -1, p2_controls, "PLAYER 2", is_cpu=p2_is_cpu)
    return p1, p2


def draw_health_bar(surf, x, y, w, h, ratio, color, flip=False):
    pygame.draw.rect(surf, GRAY, (x, y, w, h), border_radius=6)
    fill_w = int(w * ratio)
    if flip:
        rect = (x + w - fill_w, y, fill_w, h)
    else:
        rect = (x, y, fill_w, h)
    bar_color = GREEN if ratio > 0.35 else (230, 150, 40) if ratio > 0.15 else (220, 50, 50)
    pygame.draw.rect(surf, bar_color, rect, border_radius=6)
    pygame.draw.rect(surf, BLACK, (x, y, w, h), 3, border_radius=6)


def draw_arena(surf):
    surf.fill(SKY)
    pygame.draw.rect(surf, (50, 40, 60), (0, FLOOR_Y, WIDTH, HEIGHT - FLOOR_Y))
    pygame.draw.line(surf, (80, 70, 90), (0, FLOOR_Y), (WIDTH, FLOOR_Y), 3)
    for i in range(0, WIDTH, 40):
        pygame.draw.line(surf, (35, 30, 45), (i, FLOOR_Y), (i, HEIGHT), 1)


def main():
    p2_is_cpu = True
    p1, p2 = new_fighters(p2_is_cpu)
    game_over = False
    winner_text = ""

    running = True
    while running:
        clock.tick(FPS)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                if event.key == pygame.K_r and game_over:
                    p1, p2 = new_fighters(p2_is_cpu)
                    game_over = False
                    winner_text = ""
                if event.key == pygame.K_c:
                    p2_is_cpu = not p2_is_cpu
                    p1, p2 = new_fighters(p2_is_cpu)
                    game_over = False
                    winner_text = ""

        keys = pygame.key.get_pressed()

        if not game_over:
            p1.update(keys, p2)
            p2.update(keys, p1)

            if p1.health <= 0 or p2.health <= 0:
                game_over = True
                if p1.health <= 0 and p2.health <= 0:
                    winner_text = "SERI!"
                elif p1.health <= 0:
                    winner_text = "PLAYER 2 MENANG!"
                else:
                    winner_text = "PLAYER 1 MENANG!"

        draw_arena(screen)

        # gambar fighters (yang di belakang sesuai posisi x biar ada depth sederhana)
        for f in sorted([p1, p2], key=lambda f: f.y):
            f.draw(screen)

        # health bars
        draw_health_bar(screen, 30, 25, 380, 28, p1.health_ratio(), BLUE, flip=False)
        draw_health_bar(screen, WIDTH - 30 - 380, 25, 380, 28, p2.health_ratio(), RED, flip=True)

        name1 = font_small.render("PLAYER 1", True, WHITE)
        p2_label = "PLAYER 2 (CPU)" if p2_is_cpu else "PLAYER 2"
        name2 = font_small.render(p2_label, True, WHITE)
        screen.blit(name1, (30, 55))
        screen.blit(name2, (WIDTH - 30 - name2.get_width(), 55))

        vs = font_med.render("VS", True, YELLOW)
        screen.blit(vs, (WIDTH // 2 - vs.get_width() // 2, 20))

        mode_hint = font_small.render("C = ganti Player 2 manusia/CPU", True, (180, 180, 180))
        screen.blit(mode_hint, (WIDTH // 2 - mode_hint.get_width() // 2, HEIGHT - 24))

        if game_over:
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 160))
            screen.blit(overlay, (0, 0))

            text = font_big.render(winner_text, True, YELLOW)
            screen.blit(text, (WIDTH // 2 - text.get_width() // 2, HEIGHT // 2 - 60))

            hint = font_small.render("Tekan R untuk main lagi, ESC untuk keluar", True, WHITE)
            screen.blit(hint, (WIDTH // 2 - hint.get_width() // 2, HEIGHT // 2 + 20))

        pygame.display.flip()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
