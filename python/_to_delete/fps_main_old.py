"""
Simple Single-Player FPS (Raycasting style, ala Wolfenstein 3D)
Menggunakan Pygame - tanpa library 3D eksternal.

Kontrol:
  W/A/S/D  : gerak maju/mundur/geser kiri-kanan
  Mouse    : lihat kiri/kanan
  Klik kiri: tembak
  ESC      : keluar / lepas mouse

Tujuan: habiskan semua musuh (kotak merah) sebelum HP kamu habis.
"""

import pygame
import math
import random
import sys

# ---------------------------------------------------------------
# KONFIGURASI
# ---------------------------------------------------------------
WIDTH, HEIGHT = 800, 600
HALF_HEIGHT = HEIGHT // 2
FOV = math.pi / 3          # 60 derajat
NUM_RAYS = WIDTH // 2       # resolusi raycasting (tiap ray = 2px lebar)
MAX_DEPTH = 20
DELTA_ANGLE = FOV / NUM_RAYS
DIST = NUM_RAYS / (2 * math.tan(FOV / 2))
SCALE = WIDTH // NUM_RAYS

MOVE_SPEED = 3.0
ROT_SPEED = 0.0025          # sensitivitas mouse
FPS = 60

# Peta level: 1 = dinding, 0 = lorong kosong
MAP = [
    "1111111111111111",
    "1000000000000001",
    "1011110111101101",
    "1010000100001001",
    "1010111101011101",
    "1000100000010001",
    "1110100111010111",
    "1000100100010001",
    "1011101101110101",
    "1000001000000101",
    "1111111111111111",
]
MAP_W = len(MAP[0])
MAP_H = len(MAP)
TILE = 1.0  # ukuran satu petak dalam unit dunia

def is_wall(x, y):
    ix, iy = int(x), int(y)
    if 0 <= ix < MAP_W and 0 <= iy < MAP_H:
        return MAP[iy][ix] == "1"
    return True


# ---------------------------------------------------------------
# ENTITAS PEMAIN
# ---------------------------------------------------------------
class Player:
    def __init__(self):
        self.x, self.y = 2.5, 2.5
        self.angle = 0.0
        self.hp = 100
        self.ammo_cooldown = 0

    def move(self, keys, dt):
        speed = MOVE_SPEED * dt
        dx = dy = 0
        if keys[pygame.K_w]:
            dx += math.cos(self.angle) * speed
            dy += math.sin(self.angle) * speed
        if keys[pygame.K_s]:
            dx -= math.cos(self.angle) * speed
            dy -= math.sin(self.angle) * speed
        if keys[pygame.K_a]:
            dx += math.cos(self.angle - math.pi / 2) * speed
            dy += math.sin(self.angle - math.pi / 2) * speed
        if keys[pygame.K_d]:
            dx += math.cos(self.angle + math.pi / 2) * speed
            dy += math.sin(self.angle + math.pi / 2) * speed

        # collision sederhana per-sumbu dengan margin
        margin = 0.2
        if not is_wall(self.x + dx + math.copysign(margin, dx), self.y):
            self.x += dx
        if not is_wall(self.x, self.y + dy + math.copysign(margin, dy)):
            self.y += dy

    def rotate(self, rel_x):
        self.angle += rel_x * ROT_SPEED
        self.angle %= 2 * math.pi


# ---------------------------------------------------------------
# ENTITAS MUSUH
# ---------------------------------------------------------------
class Enemy:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.hp = 30
        self.alive = True
        self.speed = 1.0

    def update(self, player, dt):
        if not self.alive:
            return
        dx, dy = player.x - self.x, player.y - self.y
        dist = math.hypot(dx, dy)
        if dist < 0.6:
            return  # sudah nempel, jangan gerak lagi (nyerang lewat kontak)
        if dist > 0:
            dx, dy = dx / dist, dy / dist
        step = self.speed * dt
        nx, ny = self.x + dx * step, self.y + dy * step
        if not is_wall(nx, self.y):
            self.x = nx
        if not is_wall(self.x, ny):
            self.y = ny

    def take_damage(self, dmg):
        self.hp -= dmg
        if self.hp <= 0:
            self.alive = False


def spawn_enemies(n=6):
    enemies = []
    tries = 0
    while len(enemies) < n and tries < 500:
        tries += 1
        x = random.randint(1, MAP_W - 2) + 0.5
        y = random.randint(1, MAP_H - 2) + 0.5
        if not is_wall(x, y) and math.hypot(x - 2.5, y - 2.5) > 3:
            enemies.append(Enemy(x, y))
    return enemies


# ---------------------------------------------------------------
# RAYCASTING
# ---------------------------------------------------------------
def cast_rays(player, screen):
    screen.fill((40, 40, 40))
    # langit & lantai
    pygame.draw.rect(screen, (60, 60, 90), (0, 0, WIDTH, HALF_HEIGHT))
    pygame.draw.rect(screen, (70, 70, 70), (0, HALF_HEIGHT, WIDTH, HALF_HEIGHT))

    depth_buffer = [MAX_DEPTH] * NUM_RAYS

    start_angle = player.angle - FOV / 2
    for ray in range(NUM_RAYS):
        angle = start_angle + ray * DELTA_ANGLE
        sin_a = math.sin(angle)
        cos_a = math.cos(angle)

        depth = 0.0
        step = 0.02
        hit = False
        while depth < MAX_DEPTH:
            depth += step
            tx = player.x + cos_a * depth
            ty = player.y + sin_a * depth
            if is_wall(tx, ty):
                hit = True
                break

        if hit:
            # koreksi fisheye
            depth *= math.cos(player.angle - angle)
            depth = max(depth, 0.0001)
            depth_buffer[ray] = depth

            wall_h = min(HEIGHT, DIST / depth)
            shade = max(30, 255 - int(depth * 20))
            color = (shade, int(shade * 0.5), int(shade * 0.5))

            x = ray * SCALE
            pygame.draw.rect(
                screen, color,
                (x, HALF_HEIGHT - wall_h // 2, SCALE + 1, int(wall_h))
            )
    return depth_buffer


def draw_sprites(screen, player, enemies, depth_buffer):
    # urutkan dari jauh ke dekat
    visible = [e for e in enemies if e.alive]
    visible.sort(key=lambda e: -((e.x - player.x) ** 2 + (e.y - player.y) ** 2))

    for e in visible:
        dx, dy = e.x - player.x, e.y - player.y
        dist = math.hypot(dx, dy)
        if dist < 0.3:
            continue
        angle_to = math.atan2(dy, dx) - player.angle
        angle_to = (angle_to + math.pi) % (2 * math.pi) - math.pi

        if abs(angle_to) > FOV / 2 + 0.3:
            continue

        proj_dist = dist * math.cos(angle_to)
        if proj_dist < 0.1:
            continue

        screen_x = (0.5 + angle_to / FOV) * WIDTH
        size = min(HEIGHT, DIST / proj_dist * 0.6)

        ray_idx = int(screen_x / SCALE)
        if 0 <= ray_idx < NUM_RAYS and proj_dist > depth_buffer[ray_idx] + 0.2:
            continue  # ketutup dinding

        rect = pygame.Rect(0, 0, size, size)
        rect.center = (screen_x, HALF_HEIGHT)
        pygame.draw.rect(screen, (200, 30, 30), rect)
        pygame.draw.rect(screen, (100, 0, 0), rect, 3)

        # health bar musuh
        hp_ratio = max(0, e.hp / 30)
        bar_w = size
        pygame.draw.rect(screen, (0, 0, 0), (rect.left, rect.top - 10, bar_w, 5))
        pygame.draw.rect(screen, (0, 220, 0), (rect.left, rect.top - 10, bar_w * hp_ratio, 5))


def draw_gun(screen, shooting_timer):
    gun_w, gun_h = 160, 160
    x = WIDTH // 2 - gun_w // 2
    y = HEIGHT - gun_h + (10 if shooting_timer > 0 else 0)
    pygame.draw.rect(screen, (50, 50, 50), (x, y, gun_w, gun_h), border_radius=10)
    pygame.draw.rect(screen, (20, 20, 20), (x + 55, y - 20, 50, 40), border_radius=6)
    if shooting_timer > 0:
        pygame.draw.circle(screen, (255, 230, 100), (WIDTH // 2, y - 15), 25)


def draw_hud(screen, font, player, enemies_left):
    pygame.draw.rect(screen, (0, 0, 0), (10, HEIGHT - 30, 210, 20))
    hp_ratio = max(0, player.hp / 100)
    pygame.draw.rect(screen, (220, 30, 30), (10, HEIGHT - 30, 210 * hp_ratio, 20))
    hp_text = font.render(f"HP: {max(0, player.hp)}", True, (255, 255, 255))
    screen.blit(hp_text, (15, HEIGHT - 28))

    enemy_text = font.render(f"Musuh tersisa: {enemies_left}", True, (255, 255, 0))
    screen.blit(enemy_text, (WIDTH - 220, 10))

    # crosshair
    cx, cy = WIDTH // 2, HEIGHT // 2
    pygame.draw.line(screen, (255, 255, 255), (cx - 8, cy), (cx + 8, cy), 2)
    pygame.draw.line(screen, (255, 255, 255), (cx, cy - 8), (cx, cy + 8), 2)


def draw_minimap(screen, player, enemies):
    scale = 8
    ox, oy = WIDTH - MAP_W * scale - 10, HEIGHT - MAP_H * scale - 40
    for row in range(MAP_H):
        for col in range(MAP_W):
            color = (150, 150, 150) if MAP[row][col] == "1" else (20, 20, 20)
            pygame.draw.rect(screen, color, (ox + col * scale, oy + row * scale, scale, scale))
    for e in enemies:
        if e.alive:
            pygame.draw.circle(screen, (255, 0, 0), (int(ox + e.x * scale), int(oy + e.y * scale)), 3)
    pygame.draw.circle(screen, (0, 255, 0), (int(ox + player.x * scale), int(oy + player.y * scale)), 3)
    ex = player.x + math.cos(player.angle) * 0.5
    ey = player.y + math.sin(player.angle) * 0.5
    pygame.draw.line(screen, (0, 255, 0), (ox + player.x * scale, oy + player.y * scale), (ox + ex * scale, oy + ey * scale), 1)


def shoot(player, enemies):
    """Tembak lurus ke depan, kena musuh pertama dalam jangkauan sempit."""
    best_target, best_dist = None, MAX_DEPTH
    for e in enemies:
        if not e.alive:
            continue
        dx, dy = e.x - player.x, e.y - player.y
        dist = math.hypot(dx, dy)
        angle_to = math.atan2(dy, dx) - player.angle
        angle_to = (angle_to + math.pi) % (2 * math.pi) - math.pi
        if abs(angle_to) < 0.08 and dist < best_dist:
            # cek tidak ketutup tembok
            steps = int(dist / 0.05)
            blocked = False
            for s in range(1, steps):
                t = s * 0.05
                if is_wall(player.x + math.cos(player.angle) * t, player.y + math.sin(player.angle) * t):
                    blocked = True
                    break
            if not blocked:
                best_target, best_dist = e, dist
    if best_target:
        best_target.take_damage(15)


# ---------------------------------------------------------------
# MAIN LOOP
# ---------------------------------------------------------------
def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Simple FPS - Pygame Raycaster")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("consolas", 22)
    big_font = pygame.font.SysFont("consolas", 48)

    pygame.mouse.set_visible(False)
    pygame.event.set_grab(True)

    player = Player()
    enemies = spawn_enemies(6)

    shooting_timer = 0
    game_over = False
    win = False

    running = True
    while running:
        dt_ms = clock.tick(FPS)
        dt = dt_ms / 16.6667  # normalisasi ke ~1.0 pada 60fps

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
            elif event.type == pygame.MOUSEBUTTONDOWN and not game_over:
                if event.button == 1 and player.ammo_cooldown <= 0:
                    shoot(player, enemies)
                    shooting_timer = 6
                    player.ammo_cooldown = 15

        if not game_over:
            keys = pygame.key.get_pressed()
            player.move(keys, dt)
            rel_x, _ = pygame.mouse.get_rel()
            player.rotate(rel_x)

            if player.ammo_cooldown > 0:
                player.ammo_cooldown -= 1
            if shooting_timer > 0:
                shooting_timer -= 1

            for e in enemies:
                e.update(player, dt)
                if e.alive:
                    dist = math.hypot(e.x - player.x, e.y - player.y)
                    if dist < 0.6:
                        player.hp -= 0.4 * dt

            if player.hp <= 0:
                player.hp = 0
                game_over = True
                win = False

            if all(not e.alive for e in enemies):
                game_over = True
                win = True
        else:
            pygame.mouse.get_rel()  # buang delta biar ga meloncat kalau lanjut

        depth_buffer = cast_rays(player, screen)
        draw_sprites(screen, player, enemies, depth_buffer)
        draw_gun(screen, shooting_timer)
        draw_hud(screen, font, player, sum(1 for e in enemies if e.alive))
        draw_minimap(screen, player, enemies)

        if game_over:
            msg = "KAMU MENANG!" if win else "KAMU KALAH"
            color = (80, 255, 80) if win else (255, 80, 80)
            text = big_font.render(msg, True, color)
            screen.blit(text, (WIDTH // 2 - text.get_width() // 2, HEIGHT // 2 - 40))
            sub = font.render("Tekan ESC untuk keluar", True, (255, 255, 255))
            screen.blit(sub, (WIDTH // 2 - sub.get_width() // 2, HEIGHT // 2 + 20))

        pygame.display.flip()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
