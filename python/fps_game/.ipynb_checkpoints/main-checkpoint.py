"""
Simple Single-Player FPS (Raycasting style, ala Wolfenstein 3D)
Menggunakan Pygame - tanpa library 3D eksternal.

Kontrol:
  W/A/S/D           : gerak maju/mundur/geser kiri-kanan
  Mouse             : lihat kiri/kanan (saat sedang bermain)
  Panah Kiri/Kanan  : alternatif menoleh tanpa mouse
  Klik kiri         : tembak (saat bermain) / pilih tombol (di menu)
  ESC               : keluar / lepas mouse
  ENTER / klik      : lanjut di layar cerita

Alur permainan:
  Menu utama -> Cerita awal -> Bertarung melawan musuh biasa ->
  Cerita sebelum Boss -> Bertarung melawan Boss -> Cerita kemenangan.

  Kalau HP kamu habis, game TIDAK langsung berakhir -- muncul layar "Lanjutkan
  atau Keluar". Kalau pilih Lanjutkan, kamu hidup lagi dengan HP penuh dan
  melanjutkan dari posisi terakhir (musuh yang sudah kamu lukai/kalahkan tetap
  seperti itu, Boss yang sudah muncul juga tetap ada). Ini supaya siapapun
  pasti bisa menyelesaikan game ini cepat atau lambat.

--------------------------------------------------------
CARA MENGEDIT GAME INI TANPA MENYENTUH KODE PYTHON:
--------------------------------------------------------
Semua pengaturan ada di file data/config.json:

  "ui.main_menu"        -> gambar latar + judul + gambar tombol Mulai & Keluar di menu utama
  "ui.continue_screen"  -> gambar latar + judul + pesan + gambar tombol Lanjutkan & Keluar saat kamu mati

  "story.intro"         -> gambar + judul + teks cerita di awal permainan
  "story.before_boss"   -> gambar + judul + teks cerita sebelum Boss muncul
  "story.ending"        -> gambar + judul + teks cerita setelah Boss dikalahkan

  "combat.player_hp"                 -> HP pemain
  "combat.player_shoot_damage"       -> damage tiap tembakan
  "combat.player_shoot_cooldown"     -> jeda antar tembakan (frame)
  "combat.shots_to_kill_enemy"       -> berapa kali tembak sampai 1 musuh biasa mati
  "combat.shots_to_kill_boss"        -> berapa kali tembak sampai Boss mati
  "combat.enemy_hits_to_kill_player" -> berapa kali kena serang musuh biasa sampai pemain mati
  "combat.boss_hits_to_kill_player"  -> berapa kali kena serang Boss sampai pemain mati
  "combat.enemy_attack_interval" / "combat.boss_attack_interval" -> jeda antar serangan musuh/Boss (detik)

  "enemy.count" / "enemy.speed" / "enemy.image" -> jumlah, kecepatan, gambar musuh biasa
  "boss.speed" / "boss.image" / "boss.name" / "boss.spawn_message" -> statistik & gambar Boss

HP musuh dan damage serangan musuh/Boss DIHITUNG OTOMATIS dari variabel
"jumlah tembakan/serangan" di atas -- jadi kamu tidak perlu mengatur HP secara
manual, cukup atur berapa kali tembak/serang yang kamu inginkan.

Ganti file gambar di folder assets/images/ (nama file sama, atau ubah path-nya
di config.json). Jika gambar belum ada, game tetap jalan memakai kotak
placeholder berwarna sebagai pengganti.
"""

import os
import json
import math
import random
import sys

import pygame

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
KEY_ROT_SPEED = 2.6     # kecepatan menoleh pakai tombol panah kiri/kanan (radian per DETIK)
FPS = 60

WHITE = (245, 245, 245)
BLACK = (10, 10, 10)
YELLOW = (255, 225, 90)

# Peta arena terbuka: sebagian besar lantai kosong dengan beberapa pilar 1x1
# yang tersebar sebagai penghalang & tempat sembunyi.
# '1' = dinding, '0' = lantai kosong. Silakan ubah peta ini sesuka hati.
MAP = [
    "111111111111111111111",
    "100000000000000000001",
    "100000000000000000001",
    "100010000010000010001",
    "100000000000000000001",
    "100000010000010000001",
    "100000000000000000001",
    "100010000010000010001",
    "100000000000000000001",
    "100000010000010000001",
    "100000000000000000001",
    "100010000010000010001",
    "100000000000000000001",
    "100000000000000000001",
    "111111111111111111111",
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


def derive_combat(cfg):
    """Hitung HP musuh/Boss dan damage serangan musuh/Boss dari variabel
    'jumlah tembakan/serangan yang menyebabkan mati' di config.json, supaya
    yang perlu diedit orang lain cukup angka jumlah tembakan itu saja."""
    c = cfg["combat"]
    shoot_damage = c["player_shoot_damage"]
    player_hp = c["player_hp"]

    enemy_hp = max(1, shoot_damage * c["shots_to_kill_enemy"])
    boss_hp = max(1, shoot_damage * c["shots_to_kill_boss"])

    enemy_attack_damage = max(1, math.ceil(player_hp / c["enemy_hits_to_kill_player"]))
    boss_attack_damage = max(1, math.ceil(player_hp / c["boss_hits_to_kill_player"]))

    return {
        "player_hp": player_hp,
        "shoot_damage": shoot_damage,
        "shoot_cooldown": c["player_shoot_cooldown"],
        "enemy_hp": enemy_hp,
        "enemy_attack_damage": enemy_attack_damage,
        "enemy_attack_interval": c["enemy_attack_interval"],
        "boss_hp": boss_hp,
        "boss_attack_damage": boss_attack_damage,
        "boss_attack_interval": c["boss_attack_interval"],
    }


# ---------------------------------------------------------------
# Loader gambar dengan fallback placeholder (aman jika file belum ada)
# ---------------------------------------------------------------
_image_cache = {}


def load_sprite(relative_path, size, fallback_color, label=""):
    """Untuk sprite di dunia game (musuh/boss) -- selalu persegi, di-bucket
    untuk cache murah karena ukurannya berubah-ubah tiap frame (jarak)."""
    size = max(4, int(size))
    bucket = (size // 8) * 8
    key = (relative_path, bucket)
    if key in _image_cache:
        base = _image_cache[key]
    else:
        base = _load_raw(relative_path, (bucket, bucket), fallback_color, label)
        _image_cache[key] = base
    if base.get_width() != size:
        return pygame.transform.smoothscale(base, (size, size))
    return base


_ui_image_cache = {}


def load_ui_image(relative_path, size, fallback_color=(60, 60, 90), label=""):
    """Untuk gambar UI (background, tombol, gambar cerita) -- ukuran tetap
    (bukan persegi), di-cache langsung per (path, size) karena jarang berubah."""
    key = (relative_path, size)
    if key not in _ui_image_cache:
        _ui_image_cache[key] = _load_raw(relative_path, size, fallback_color, label)
    return _ui_image_cache[key]


def _load_raw(relative_path, size, fallback_color, label):
    full_path = os.path.join(BASE_DIR, relative_path)
    surf = None
    if os.path.isfile(full_path):
        try:
            surf = pygame.image.load(full_path).convert_alpha()
        except Exception:
            surf = None
    if surf is None:
        w, h = size
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        surf.fill(fallback_color + (255,))
        pygame.draw.rect(surf, (255, 255, 255), surf.get_rect(), 3)
        if label:
            f = pygame.font.SysFont("consolas", max(12, min(w, h) // 8))
            text_lines = label.split("\n")
            lh = f.get_linesize()
            total_h = lh * len(text_lines)
            for i, line in enumerate(text_lines):
                t = f.render(line, True, (255, 255, 255))
                surf.blit(t, t.get_rect(center=(w // 2, h // 2 - total_h // 2 + i * lh + lh // 2)))
    else:
        surf = pygame.transform.smoothscale(surf, size)
    return surf


# ---------------------------------------------------------------
# ENTITAS PEMAIN
# ---------------------------------------------------------------
PLAYER_RADIUS = 0.2    # jari-jari tabrakan pemain, dipakai supaya bisa "menggeser" di sepanjang dinding
ACCEL_BLEND = 16.0      # seberapa cepat kecepatan menyesuaikan target, per DETIK (lebih besar = lebih responsif/gesit)
# Titik spawn HARUS berada di petak lantai yang benar-benar kosong (bukan di
# pinggir/sudut dinding atau pilar) -- disesuaikan dengan peta arena terbuka.
PLAYER_SPAWN = (3.5, 2.5)


class Player:
    def __init__(self, cfg, combat):
        self.x, self.y = PLAYER_SPAWN
        self.angle = 0.0
        self.max_hp = combat["player_hp"]
        self.hp = self.max_hp
        self.move_speed = cfg["player"]["move_speed"]
        self.ammo_cooldown = 0
        # kecepatan aktual saat ini (di-lerp menuju kecepatan target tiap frame
        # supaya gerakan mulai/berhenti terasa halus, bukan langsung penuh/nol)
        self.vx = 0.0
        self.vy = 0.0

    def respawn(self):
        """Dipanggil saat pemain memilih Lanjutkan setelah mati -- hidup lagi
        dengan HP penuh di titik spawn, tapi progres musuh/boss lain tidak direset."""
        self.x, self.y = PLAYER_SPAWN
        self.hp = self.max_hp
        self.vx = self.vy = 0.0

    def _can_move_to(self, x, y):
        """Cek tabrakan berbasis lingkaran kecil di sekeliling pemain supaya bisa
        meluncur mulus menyusuri dinding, bukan mentok kaku di satu sumbu saja."""
        r = PLAYER_RADIUS
        for ox, oy in ((r, 0), (-r, 0), (0, r), (0, -r), (r, r), (-r, -r), (r, -r), (-r, r)):
            if is_wall(x + ox, y + oy):
                return False
        return True

    def move(self, keys, dt):
        move_x = move_y = 0.0
        if keys[pygame.K_w]:
            move_x += math.cos(self.angle)
            move_y += math.sin(self.angle)
        if keys[pygame.K_s]:
            move_x -= math.cos(self.angle)
            move_y -= math.sin(self.angle)
        if keys[pygame.K_a]:
            move_x += math.cos(self.angle - math.pi / 2)
            move_y += math.sin(self.angle - math.pi / 2)
        if keys[pygame.K_d]:
            move_x += math.cos(self.angle + math.pi / 2)
            move_y += math.sin(self.angle + math.pi / 2)

        length = math.hypot(move_x, move_y)
        if length > 0.0001:
            move_x /= length
            move_y /= length

        target_vx = move_x * self.move_speed
        target_vy = move_y * self.move_speed

        blend = 1.0 - math.exp(-ACCEL_BLEND * dt)
        self.vx += (target_vx - self.vx) * blend
        self.vy += (target_vy - self.vy) * blend

        step_x = self.vx * dt
        step_y = self.vy * dt

        if self._can_move_to(self.x + step_x, self.y):
            self.x += step_x
        else:
            self.vx = 0.0
        if self._can_move_to(self.x, self.y + step_y):
            self.y += step_y
        else:
            self.vy = 0.0

    def rotate(self, rel_x):
        rel_x = max(-60, min(60, rel_x))
        self.angle += rel_x * ROT_SPEED
        self.angle %= 2 * math.pi

    def rotate_keys(self, keys, dt):
        if keys[pygame.K_LEFT]:
            self.angle -= KEY_ROT_SPEED * dt
        if keys[pygame.K_RIGHT]:
            self.angle += KEY_ROT_SPEED * dt
        self.angle %= 2 * math.pi


# ---------------------------------------------------------------
# ENTITAS MUSUH (dipakai juga untuk Boss dengan stat lebih besar)
# ---------------------------------------------------------------
class Enemy:
    def __init__(self, x, y, hp, speed, attack_damage, attack_interval, image_path, is_boss=False, name="Musuh"):
        self.x = x
        self.y = y
        self.max_hp = hp
        self.hp = hp
        self.alive = True
        self.speed = speed
        self.attack_damage = attack_damage
        self.attack_interval = attack_interval
        self.attack_cooldown = 0.0
        self.image_path = image_path
        self.is_boss = is_boss
        self.name = name

    def update(self, player, dt):
        if not self.alive:
            return None
        if self.attack_cooldown > 0:
            self.attack_cooldown -= dt

        dx, dy = player.x - self.x, player.y - self.y
        dist = math.hypot(dx, dy)
        if dist >= 0.6:
            if dist > 0:
                dx, dy = dx / dist, dy / dist
            step = self.speed * dt
            nx, ny = self.x + dx * step, self.y + dy * step
            if not is_wall(nx, self.y):
                self.x = nx
            if not is_wall(self.x, ny):
                self.y = ny
            return None

        # cukup dekat untuk menyerang -- serangan diskrit per interval waktu,
        # bukan drain HP terus-menerus tiap frame, supaya jelas berapa kali
        # kena serang sampai pemain mati (sesuai jumlah di config.json).
        if self.attack_cooldown <= 0:
            self.attack_cooldown = self.attack_interval
            return self.attack_damage
        return None

    def take_damage(self, dmg):
        self.hp -= dmg
        if self.hp <= 0:
            self.hp = 0
            self.alive = False


def spawn_enemies(cfg, combat):
    ecfg = cfg["enemy"]
    n = ecfg["count"]
    enemies = []
    tries = 0
    while len(enemies) < n and tries < 500:
        tries += 1
        x = random.randint(1, MAP_W - 2) + 0.5
        y = random.randint(1, MAP_H - 2) + 0.5
        if not is_wall(x, y) and math.hypot(x - PLAYER_SPAWN[0], y - PLAYER_SPAWN[1]) > 3:
            enemies.append(Enemy(
                x, y,
                hp=combat["enemy_hp"], speed=ecfg["speed"],
                attack_damage=combat["enemy_attack_damage"],
                attack_interval=combat["enemy_attack_interval"],
                image_path=ecfg["image"], is_boss=False, name="Musuh",
            ))
    return enemies


def spawn_boss(cfg, combat):
    bcfg = cfg["boss"]
    tries = 0
    while tries < 500:
        tries += 1
        x = random.randint(1, MAP_W - 2) + 0.5
        y = random.randint(1, MAP_H - 2) + 0.5
        if not is_wall(x, y) and math.hypot(x - PLAYER_SPAWN[0], y - PLAYER_SPAWN[1]) > 4:
            return Enemy(
                x, y,
                hp=combat["boss_hp"], speed=bcfg["speed"],
                attack_damage=combat["boss_attack_damage"],
                attack_interval=combat["boss_attack_interval"],
                image_path=bcfg["image"], is_boss=True, name=bcfg.get("name", "Boss"),
            )
    return Enemy(PLAYER_SPAWN[0], PLAYER_SPAWN[1], combat["boss_hp"], bcfg["speed"],
                 combat["boss_attack_damage"], combat["boss_attack_interval"],
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


def draw_hit_indicator(screen, hit_flash_timer, hit_flash_dir):
    """Tanda panah + kilatan merah di tepi layar menunjukkan arah datangnya
    serangan, supaya pemain sadar diserang dari sisi/belakang yang tidak
    kelihatan di layar (bukan cuma HP berkurang tiba-tiba)."""
    if hit_flash_timer <= 0:
        return
    alpha = max(0, min(160, int(160 * (hit_flash_timer / FPS))))
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((220, 30, 30, alpha // 3))
    screen.blit(overlay, (0, 0))

    cx, cy = WIDTH // 2, HEIGHT // 2
    radius = 250
    ax = cx + math.sin(hit_flash_dir) * radius
    ay = cy - math.cos(hit_flash_dir) * radius * 0.55
    ay = max(40, min(HEIGHT - 40, ay))
    ax = max(40, min(WIDTH - 40, ax))

    tip_angle = math.atan2(ay - cy, ax - cx)
    size = 16
    p1 = (ax, ay)
    p2 = (ax - size * math.cos(tip_angle - 0.5), ay - size * math.sin(tip_angle - 0.5))
    p3 = (ax - size * math.cos(tip_angle + 0.5), ay - size * math.sin(tip_angle + 0.5))
    pygame.draw.polygon(screen, (255, 60, 60), [p1, p2, p3])


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
    return lh * len(lines)


# ---------------------------------------------------------------
# TOMBOL BERGAMBAR (dipakai di menu & layar cerita)
# ---------------------------------------------------------------
class ImageButton:
    def __init__(self, image, center):
        self.image = image
        self.rect = image.get_rect(center=center)

    def draw(self, screen):
        screen.blit(self.image, self.rect)

    def is_clicked(self, event):
        return (
            event.type == pygame.MOUSEBUTTONDOWN
            and event.button == 1
            and self.rect.collidepoint(event.pos)
        )


def draw_story_screen(screen, font, big_font, story_cfg, hint_text):
    screen.fill((10, 10, 18))
    img = load_ui_image(story_cfg.get("image", ""), (300, 340), (70, 60, 110), label=story_cfg.get("title", "CERITA"))
    screen.blit(img, img.get_rect(center=(WIDTH // 2, 200)))

    title = big_font.render(story_cfg.get("title", ""), True, YELLOW)
    screen.blit(title, (WIDTH // 2 - title.get_width() // 2, 25))

    panel = pygame.Rect(60, 390, WIDTH - 120, 150)
    pygame.draw.rect(screen, (25, 25, 35), panel, border_radius=10)
    pygame.draw.rect(screen, WHITE, panel, 2, border_radius=10)
    draw_text_wrapped(screen, story_cfg.get("text", ""), (panel.x + 20, panel.y + 18), font, WHITE, panel.width - 40)

    hint = font.render(hint_text, True, (200, 200, 200))
    screen.blit(hint, (WIDTH // 2 - hint.get_width() // 2, HEIGHT - 34))


def draw_menu_background(screen, menu_cfg, big_font, small_font):
    bg = load_ui_image(menu_cfg.get("background", ""), (WIDTH, HEIGHT), (25, 25, 45), label="MENU")
    screen.blit(bg, (0, 0))
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 90))
    screen.blit(overlay, (0, 0))

    title = big_font.render(menu_cfg.get("title", ""), True, YELLOW)
    screen.blit(title, (WIDTH // 2 - title.get_width() // 2, 80))
    if menu_cfg.get("subtitle"):
        sub = small_font.render(menu_cfg["subtitle"], True, WHITE)
        screen.blit(sub, (WIDTH // 2 - sub.get_width() // 2, 150))


# ---------------------------------------------------------------
# MAIN LOOP
# ---------------------------------------------------------------
def _has_relative_mode():
    return hasattr(pygame.mouse, "set_relative_mode")


def set_menu_mouse_mode():
    """Kursor normal & terlihat -- dipakai di menu/cerita/layar lanjutkan supaya bisa klik tombol."""
    if _has_relative_mode():
        pygame.mouse.set_relative_mode(False)
    else:
        pygame.event.set_grab(False)
    pygame.mouse.set_visible(True)


def set_gameplay_mouse_mode():
    """Kursor tersembunyi & mode relative -- dipakai saat benar-benar bermain (mouse-look).
    set_relative_mode ada di pygame 2 / pygame-ce; kalau versi pygame yang terpasang tidak
    punya method ini, jatuh kembali ke cara lama (grab + hide) supaya tetap jalan."""
    pygame.mouse.set_visible(False)
    if _has_relative_mode():
        pygame.mouse.set_relative_mode(True)
    else:
        pygame.event.set_grab(True)
    pygame.mouse.get_rel()  # buang delta pertama yang biasanya melonjak besar


def main():
    cfg = load_config()
    combat = derive_combat(cfg)

    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Simple FPS - Pygame Raycaster")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("consolas", 22)
    big_font = pygame.font.SysFont("consolas", 44)

    STATE_MENU = "menu"
    STATE_STORY_INTRO = "story_intro"
    STATE_PLAYING = "playing"
    STATE_STORY_BEFORE_BOSS = "story_before_boss"
    STATE_STORY_ENDING = "story_ending"
    STATE_CONTINUE = "continue_screen"

    state = STATE_MENU
    set_menu_mouse_mode()

    menu_cfg = cfg["ui"]["main_menu"]
    continue_cfg = cfg["ui"]["continue_screen"]
    start_btn = ImageButton(load_ui_image(menu_cfg["start_button"], (260, 70), (40, 120, 60), "MULAI"), (WIDTH // 2, 330))
    quit_btn_menu = ImageButton(load_ui_image(menu_cfg["quit_button"], (260, 70), (120, 40, 40), "KELUAR"), (WIDTH // 2, 420))
    continue_btn = ImageButton(load_ui_image(continue_cfg["continue_button"], (260, 70), (40, 120, 60), "LANJUTKAN"), (WIDTH // 2, 380))
    quit_btn_continue = ImageButton(load_ui_image(continue_cfg["quit_button"], (260, 70), (120, 40, 40), "KELUAR"), (WIDTH // 2, 460))

    player = None
    enemies = []
    boss = None
    boss_message_timer = 0
    shooting_timer = 0
    hit_flash_timer = 0
    hit_flash_dir = 0.0

    def start_new_run():
        nonlocal player, enemies, boss, boss_message_timer
        player = Player(cfg, combat)
        enemies = spawn_enemies(cfg, combat)
        boss = None
        boss_message_timer = 0

    running = True
    while running:
        dt_ms = min(clock.tick(FPS), 50)
        dt = dt_ms / 16.6667          # "frame-equivalent" @60fps, dipakai untuk timer per-frame
        dt_seconds = dt_ms / 1000.0   # waktu nyata dalam detik, dipakai untuk pergerakan & serangan

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False

            if state == STATE_MENU:
                if start_btn.is_clicked(event):
                    start_new_run()
                    state = STATE_STORY_INTRO
                elif quit_btn_menu.is_clicked(event):
                    running = False

            elif state == STATE_STORY_INTRO:
                if event.type == pygame.MOUSEBUTTONDOWN or (event.type == pygame.KEYDOWN and event.key in (pygame.K_RETURN, pygame.K_SPACE)):
                    state = STATE_PLAYING
                    set_gameplay_mouse_mode()

            elif state == STATE_STORY_BEFORE_BOSS:
                if event.type == pygame.MOUSEBUTTONDOWN or (event.type == pygame.KEYDOWN and event.key in (pygame.K_RETURN, pygame.K_SPACE)):
                    boss = spawn_boss(cfg, combat)
                    boss_message_timer = FPS * 2
                    state = STATE_PLAYING
                    set_gameplay_mouse_mode()

            elif state == STATE_PLAYING:
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and player.ammo_cooldown <= 0:
                    targets = enemies + ([boss] if boss else [])
                    shoot(player, targets, combat["shoot_damage"])
                    shooting_timer = 6
                    player.ammo_cooldown = combat["shoot_cooldown"]

            elif state == STATE_CONTINUE:
                if continue_btn.is_clicked(event):
                    player.respawn()
                    state = STATE_PLAYING
                    set_gameplay_mouse_mode()
                elif quit_btn_continue.is_clicked(event):
                    running = False

            elif state == STATE_STORY_ENDING:
                if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
                    state = STATE_MENU
                    set_menu_mouse_mode()

        # -------------------------------------------------------
        # UPDATE
        # -------------------------------------------------------
        if state == STATE_PLAYING:
            keys = pygame.key.get_pressed()
            player.move(keys, dt_seconds)
            rel_x, _ = pygame.mouse.get_rel()
            player.rotate(rel_x)
            player.rotate_keys(keys, dt_seconds)

            if player.ammo_cooldown > 0:
                player.ammo_cooldown -= 1
            if shooting_timer > 0:
                shooting_timer -= 1
            if boss_message_timer > 0:
                boss_message_timer -= 1
            if hit_flash_timer > 0:
                hit_flash_timer -= 1

            all_targets = enemies + ([boss] if boss else [])
            for e in all_targets:
                dmg = e.update(player, dt_seconds)
                if dmg:
                    player.hp -= dmg
                    angle_to_enemy = math.atan2(e.y - player.y, e.x - player.x) - player.angle
                    angle_to_enemy = (angle_to_enemy + math.pi) % (2 * math.pi) - math.pi
                    hit_flash_dir = angle_to_enemy
                    hit_flash_timer = FPS

            if player.hp <= 0:
                player.hp = 0
                state = STATE_CONTINUE
                set_menu_mouse_mode()

            elif boss is None and all(not e.alive for e in enemies):
                # semua musuh biasa habis -> tampilkan cerita sebelum boss,
                # boss sendiri baru muncul setelah cerita ini dilanjutkan
                state = STATE_STORY_BEFORE_BOSS
                set_menu_mouse_mode()

            elif boss is not None and not boss.alive:
                state = STATE_STORY_ENDING
                set_menu_mouse_mode()

        # -------------------------------------------------------
        # DRAW
        # -------------------------------------------------------
        if state == STATE_MENU:
            draw_menu_background(screen, menu_cfg, big_font, font)
            start_btn.draw(screen)
            quit_btn_menu.draw(screen)

        elif state == STATE_STORY_INTRO:
            draw_story_screen(screen, font, big_font, cfg["story"]["intro"], "Klik atau tekan ENTER untuk lanjut")

        elif state == STATE_STORY_BEFORE_BOSS:
            draw_story_screen(screen, font, big_font, cfg["story"]["before_boss"], "Klik atau tekan ENTER untuk melawan Boss")

        elif state == STATE_STORY_ENDING:
            draw_story_screen(screen, font, big_font, cfg["story"]["ending"], "Tekan ENTER untuk kembali ke menu utama")

        elif state == STATE_CONTINUE:
            bg = load_ui_image(continue_cfg.get("background", ""), (WIDTH, HEIGHT), (35, 15, 15), label="KALAH")
            screen.blit(bg, (0, 0))
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 130))
            screen.blit(overlay, (0, 0))
            title = big_font.render(continue_cfg.get("title", "KAMU KALAH"), True, (255, 90, 90))
            screen.blit(title, (WIDTH // 2 - title.get_width() // 2, 150))
            draw_text_wrapped(screen, continue_cfg.get("message", ""), (WIDTH // 2 - 260, 220), font, WHITE, 520)
            continue_btn.draw(screen)
            quit_btn_continue.draw(screen)

        elif state == STATE_PLAYING:
            depth_buffer = cast_rays(player, screen)
            draw_sprites(screen, player, enemies + ([boss] if boss else []), depth_buffer)
            draw_gun(screen, shooting_timer)
            draw_hud(screen, font, player, sum(1 for e in enemies if e.alive), boss)
            draw_minimap(screen, player, enemies, boss)
            draw_hit_indicator(screen, hit_flash_timer, hit_flash_dir)
            if boss_message_timer > 0:
                msg = font.render(cfg["boss"].get("spawn_message", "BOSS MUNCUL!"), True, (255, 80, 220))
                screen.blit(msg, (WIDTH // 2 - msg.get_width() // 2, 60))

        pygame.display.flip()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
