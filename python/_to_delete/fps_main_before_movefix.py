"""
Simple Single-Player FPS (Raycasting style, ala Wolfenstein 3D)
Menggunakan Pygame - tanpa library 3D eksternal.

Kontrol:
  W/A/S/D  : gerak maju/mundur/geser kiri-kanan
  Mouse    : lihat kiri/kanan
  Klik kiri: tembak
  ESC      : keluar / lepas mouse

Tujuan: habiskan semua musuh biasa, lalu kalahkan Boss yang muncul setelahnya,
sebelum HP kamu habis. HP pemain jauh lebih besar daripada musuh biasa supaya
tidak cepat mati.

--------------------------------------------------------
CARA MENGEDIT GAME INI TANPA MENYENTUH KODE PYTHON:
--------------------------------------------------------
Semua pengaturan ada di file data/config.json:
  - "player.hp"                    -> jumlah HP pemain (dibuat jauh lebih besar dari musuh)
  - "enemy.count"                  -> jumlah musuh biasa yang muncul
  - "enemy.hp" / "enemy.speed" / "enemy.contact_damage_per_frame" -> statistik musuh biasa
  - "enemy.image"                  -> path gambar musuh biasa
  - "boss.hp" / "boss.speed" / "boss.contact_damage_per_frame"    -> statistik Boss
  - "boss.image"                   -> path gambar Boss
  - "boss.spawn_message"           -> teks yang muncul saat Boss pertama kali muncul
  - "ending.image"                 -> gambar yang tampil di layar kemenangan
  - "ending.title" / "ending.text" -> judul & teks di layar kemenangan

Ganti file gambar di folder assets/images/ (nama file sama, atau ubah path-nya
di config.json). Jika gambar belum ada, game tetap jalan memakai kotak
placeholder berwarna sebagai pengganti.
"""

import os
import json
import pygame
import math
import random
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "data", "config.json")

# ---------------------------------------------------------------
# KONFIGURASI LAYAR / RAYCASTING (tidak perlu diubah)
# ---------------------------------------------------------------
WIDTH, HEIGHT = 800, 600
HALF_HEIGHT = HEIGHT // 2
FOV = math.pi / 3
NUM_RAYS = WIDTH // 2
MAX_DEPTH = 20
DELTA_ANGLE = FOV / NUM_RAYS
DIST = NUM_RAYS / (2 * math.tan(FOV / 2))
SCALE = WIDTH // NUM_RAYS

ROT_SPEED = 0.0025
FPS = 60

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


def is_wall(x, y):
    ix, iy = int(x), int(y)
    if 0 <= ix < MAP_W and 0 <= iy < MAP_H:
        return MAP[iy][ix] == "1"
    return True


def load_config():
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------
# Loader gambar dengan fallback placeholder (aman jika file belum ada)
# ---------------------------------------------------------------
_image_cache = {}


def load_sprite(relative_path, size, fallback_color, label=""):
    size = max(4, int(size))
    bucket = (size // 8) * 8  # bucket ukuran biar cache tidak membengkak
    key = (relative_path, bucket)
    if key in _image_cache:
        base = _image_cache[key]
    else:
        full_path = os.path.join(BASE_DIR, relative_path)
        base = None
        if os.path.isfile(full_path):
            try:
                base = pygame.image.load(full_path).convert_alpha()
            except Exception:
                base = None
        if base is None:
            base = pygame.Surface((bucket, bucket), pygame.SRCALPHA)
            base.fill(fallback_color + (255,))
            pygame.draw.rect(base, (255, 255, 255), base.get_rect(), 2)
            if label:
                f = pygame.font.SysFont("consolas", max(10, bucket // 8))
                t = f.render(label, True, (255, 255, 255))
                base.blit(t, t.get_rect(center=(bucket // 2, bucket // 2)))
        else:
            base = pygame.transform.smoothscale(base, (bucket, bucket))
        _image_cache[key] = base
    if base.get_width() != size:
        return pygame.transform.smoothscale(base, (size, size))
    return base


# ---------------------------------------------------------------
# ENTITAS PEMAIN
# ---------------------------------------------------------------
class Player:
    def __init__(self, cfg):
        self.x, self.y = 2.5, 2.5
        self.angle = 0.0
        self.max_hp = cfg["player"]["hp"]
        self.hp = self.max_hp
        self.move_speed = cfg["player"]["move_speed"]
        self.ammo_cooldown = 0

    def move(self, keys, dt):
        speed = self.move_speed * dt
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

        margin = 0.2
        if not is_wall(self.x + dx + math.copysign(margin, dx), self.y):
            self.x += dx
        if not is_wall(self.x, self.y + dy + math.copysign(margin, dy)):
            self.y += dy

    def rotate(self, rel_x):
        self.angle += rel_x * ROT_SPEED
        self.angle %= 2 * math.pi


# ---------------------------------------------------------------
# ENTITAS MUSUH (dipakai juga untuk Boss dengan stat lebih besar)
# ---------------------------------------------------------------
class Enemy:
    def __init__(self, x, y, hp, speed, contact_damage, image_path, is_boss=False, name="Musuh"):
        self.x = x
        self.y = y
        self.max_hp = hp
        self.hp = hp
        self.alive = True
        self.speed = speed
        self.contact_damage = contact_damage
        self.image_path = image_path
        self.is_boss = is_boss
        self.name = name

    def update(self, player, dt):
        if not self.alive:
            return
        dx, dy = player.x - self.x, player.y - self.y
        dist = math.hypot(dx, dy)
        if dist < 0.6:
            return
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
            self.hp = 0
            self.alive = False


def spawn_enemies(cfg):
    ecfg = cfg["enemy"]
    n = ecfg["count"]
    enemies = []
    tries = 0
    while len(enemies) < n and tries < 500:
        tries += 1
        x = random.randint(1, MAP_W - 2) + 0.5
        y = random.randint(1, MAP_H - 2) + 0.5
        if not is_wall(x, y) and math.hypot(x - 2.5, y - 2.5) > 3:
            enemies.append(Enemy(
                x, y,
                hp=ecfg["hp"], speed=ecfg["speed"],
                contact_damage=ecfg["contact_damage_per_frame"],
                image_path=ecfg["image"], is_boss=False, name="Musuh",
            ))
    return enemies


def spawn_boss(cfg):
    bcfg = cfg["boss"]
    tries = 0
    while tries < 500:
        tries += 1
        x = random.randint(1, MAP_W - 2) + 0.5
        y = random.randint(1, MAP_H - 2) + 0.5
        if not is_wall(x, y) and math.hypot(x - 2.5, y - 2.5) > 4:
            return Enemy(
                x, y,
                hp=bcfg["hp"], speed=bcfg["speed"],
                contact_damage=bcfg["contact_damage_per_frame"],
                image_path=bcfg["image"], is_boss=True, name=bcfg.get("name", "Boss"),
            )
    # fallback kalau tidak ketemu titik kosong (harusnya tidak pernah terjadi)
    return Enemy(2.5, 2.5, bcfg["hp"], bcfg["speed"], bcfg["contact_damage_per_frame"],
                 bcfg["image"], is_boss=True, name=bcfg.get("name", "Boss"))


# ---------------------------------------------------------------
# RAYCASTING
# ---------------------------------------------------------------
def cast_rays(player, screen):
    screen.fill((40, 40, 40))
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
        base_scale = 0.9 if e.is_boss else 0.6
        size = min(HEIGHT, DIST / proj_dist * base_scale)

        ray_idx = int(screen_x / SCALE)
        if 0 <= ray_idx < NUM_RAYS and proj_dist > depth_buffer[ray_idx] + 0.2:
            continue

        rect = pygame.Rect(0, 0, size, size)
        rect.center = (screen_x, HALF_HEIGHT + (size * 0.15 if e.is_boss else 0))

        fallback_color = (140, 30, 160) if e.is_boss else (200, 30, 30)
        img = load_sprite(e.image_path, size, fallback_color, label=e.name)
        screen.blit(img, rect)

        hp_ratio = max(0, e.hp / e.max_hp)
        bar_w = size
        pygame.draw.rect(screen, (0, 0, 0), (rect.left, rect.top - 10, bar_w, 5))
        bar_color = (220, 60, 220) if e.is_boss else (0, 220, 0)
        pygame.draw.rect(screen, bar_color, (rect.left, rect.top - 10, bar_w * hp_ratio, 5))


def draw_gun(screen, shooting_timer):
    gun_w, gun_h = 160, 160
    x = WIDTH // 2 - gun_w // 2
    y = HEIGHT - gun_h + (10 if shooting_timer > 0 else 0)
    pygame.draw.rect(screen, (50, 50, 50), (x, y, gun_w, gun_h), border_radius=10)
    pygame.draw.rect(screen, (20, 20, 20), (x + 55, y - 20, 50, 40), border_radius=6)
    if shooting_timer > 0:
        pygame.draw.circle(screen, (255, 230, 100), (WIDTH // 2, y - 15), 25)


def draw_hud(screen, font, player, enemies_left, boss):
    pygame.draw.rect(screen, (0, 0, 0), (10, HEIGHT - 30, 260, 20))
    hp_ratio = max(0, player.hp / player.max_hp)
    pygame.draw.rect(screen, (220, 30, 30), (10, HEIGHT - 30, 260 * hp_ratio, 20))
    hp_text = font.render(f"HP: {max(0, int(player.hp))}/{player.max_hp}", True, (255, 255, 255))
    screen.blit(hp_text, (15, HEIGHT - 28))

    if boss is not None and boss.alive:
        pygame.draw.rect(screen, (0, 0, 0), (WIDTH // 2 - 200, 10, 400, 18))
        br = max(0, boss.hp / boss.max_hp)
        pygame.draw.rect(screen, (220, 60, 220), (WIDTH // 2 - 200, 10, 400 * br, 18))
        bt = font.render(f"{boss.name}: {max(0, int(boss.hp))}/{boss.max_hp}", True, (255, 255, 255))
        screen.blit(bt, (WIDTH // 2 - bt.get_width() // 2, 30))
    else:
        enemy_text = font.render(f"Musuh tersisa: {enemies_left}", True, (255, 255, 0))
        screen.blit(enemy_text, (WIDTH - 220, 10))

    cx, cy = WIDTH // 2, HEIGHT // 2
    pygame.draw.line(screen, (255, 255, 255), (cx - 8, cy), (cx + 8, cy), 2)
    pygame.draw.line(screen, (255, 255, 255), (cx, cy - 8), (cx, cy + 8), 2)


def draw_minimap(screen, player, enemies, boss):
    scale = 8
    ox, oy = WIDTH - MAP_W * scale - 10, HEIGHT - MAP_H * scale - 40
    for row in range(MAP_H):
        for col in range(MAP_W):
            color = (150, 150, 150) if MAP[row][col] == "1" else (20, 20, 20)
            pygame.draw.rect(screen, color, (ox + col * scale, oy + row * scale, scale, scale))
    for e in enemies:
        if e.alive:
            pygame.draw.circle(screen, (255, 0, 0), (int(ox + e.x * scale), int(oy + e.y * scale)), 3)
    if boss is not None and boss.alive:
        pygame.draw.circle(screen, (220, 60, 220), (int(ox + boss.x * scale), int(oy + boss.y * scale)), 5)
    pygame.draw.circle(screen, (0, 255, 0), (int(ox + player.x * scale), int(oy + player.y * scale)), 3)
    ex = player.x + math.cos(player.angle) * 0.5
    ey = player.y + math.sin(player.angle) * 0.5
    pygame.draw.line(screen, (0, 255, 0), (ox + player.x * scale, oy + player.y * scale), (ox + ex * scale, oy + ey * scale), 1)


def shoot(player, targets, damage):
    """Tembak lurus ke depan, kena target pertama (musuh/boss) dalam jangkauan sempit."""
    best_target, best_dist = None, MAX_DEPTH
    for e in targets:
        if not e.alive:
            continue
        dx, dy = e.x - player.x, e.y - player.y
        dist = math.hypot(dx, dy)
        angle_to = math.atan2(dy, dx) - player.angle
        angle_to = (angle_to + math.pi) % (2 * math.pi) - math.pi
        if abs(angle_to) < 0.08 and dist < best_dist:
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
        best_target.take_damage(damage)


def draw_text_wrapped(screen, text, pos, font, color, max_width):
    words = text.split(" ")
    lines, current = [], ""
    for word in words:
        trial = (current + " " + word).strip()
        if font.size(trial)[0] > max_width and current:
            lines.append(current)
            current = word
        else:
            current = trial
    if current:
        lines.append(current)
    x, y = pos
    lh = font.get_linesize()
    for i, line in enumerate(lines):
        s = font.render(line, True, color)
        screen.blit(s, (x, y + i * lh))


def draw_ending_screen(screen, cfg, font, big_font):
    ending = cfg["ending"]
    screen.fill((10, 10, 18))
    img = load_sprite(ending["image"], 260, (90, 60, 150), label="ENDING")
    screen.blit(img, img.get_rect(center=(WIDTH // 2, 190)))

    title = big_font.render(ending.get("title", "KAMU MENANG!"), True, (255, 230, 80))
    screen.blit(title, (WIDTH // 2 - title.get_width() // 2, 30))

    panel = pygame.Rect(60, 360, WIDTH - 120, 170)
    pygame.draw.rect(screen, (25, 25, 35), panel, border_radius=10)
    pygame.draw.rect(screen, (255, 255, 255), panel, 2, border_radius=10)
    draw_text_wrapped(screen, ending.get("text", ""), (panel.x + 20, panel.y + 20), font, (255, 255, 255), panel.width - 40)

    sub = font.render("Tekan ESC untuk keluar", True, (200, 200, 200))
    screen.blit(sub, (WIDTH // 2 - sub.get_width() // 2, HEIGHT - 40))


# ---------------------------------------------------------------
# MAIN LOOP
# ---------------------------------------------------------------
def main():
    cfg = load_config()

    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Simple FPS - Pygame Raycaster")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("consolas", 22)
    big_font = pygame.font.SysFont("consolas", 48)

    pygame.mouse.set_visible(False)
    pygame.event.set_grab(True)

    player = Player(cfg)
    enemies = spawn_enemies(cfg)
    boss = None
    boss_message_timer = 0

    shooting_timer = 0
    game_over = False
    win = False

    running = True
    while running:
        dt_ms = clock.tick(FPS)
        dt = dt_ms / 16.6667

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
            elif event.type == pygame.MOUSEBUTTONDOWN and not game_over:
                if event.button == 1 and player.ammo_cooldown <= 0:
                    targets = enemies + ([boss] if boss else [])
                    shoot(player, targets, cfg["player"]["shoot_damage"])
                    shooting_timer = 6
                    player.ammo_cooldown = cfg["player"]["shoot_cooldown"]

        if not game_over:
            keys = pygame.key.get_pressed()
            player.move(keys, dt)
            rel_x, _ = pygame.mouse.get_rel()
            player.rotate(rel_x)

            if player.ammo_cooldown > 0:
                player.ammo_cooldown -= 1
            if shooting_timer > 0:
                shooting_timer -= 1
            if boss_message_timer > 0:
                boss_message_timer -= 1

            all_targets = enemies + ([boss] if boss else [])
            for e in all_targets:
                e.update(player, dt)
                if e.alive:
                    dist = math.hypot(e.x - player.x, e.y - player.y)
                    if dist < 0.6:
                        player.hp -= e.contact_damage * dt

            if player.hp <= 0:
                player.hp = 0
                game_over = True
                win = False

            # semua musuh biasa habis -> spawn boss (sekali saja)
            if boss is None and all(not e.alive for e in enemies):
                boss = spawn_boss(cfg)
                boss_message_timer = FPS * 3

            # boss sudah muncul dan mati -> menang
            if boss is not None and not boss.alive:
                game_over = True
                win = True
        else:
            pygame.mouse.get_rel()

        depth_buffer = cast_rays(player, screen)
        draw_sprites(screen, player, enemies + ([boss] if boss else []), depth_buffer)
        draw_gun(screen, shooting_timer)
        draw_hud(screen, font, player, sum(1 for e in enemies if e.alive), boss)
        draw_minimap(screen, player, enemies, boss)

        if boss_message_timer > 0 and not game_over:
            msg = font.render(cfg["boss"].get("spawn_message", "BOSS MUNCUL!"), True, (255, 80, 220))
            screen.blit(msg, (WIDTH // 2 - msg.get_width() // 2, 60))

        if game_over:
            if win:
                draw_ending_screen(screen, cfg, font, big_font)
            else:
                text = big_font.render("KAMU KALAH", True, (255, 80, 80))
                screen.blit(text, (WIDTH // 2 - text.get_width() // 2, HEIGHT // 2 - 40))
                sub = font.render("Tekan ESC untuk keluar", True, (255, 255, 255))
                screen.blit(sub, (WIDTH // 2 - sub.get_width() // 2, HEIGHT // 2 + 20))

        pygame.display.flip()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
