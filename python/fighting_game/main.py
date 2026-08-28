"""
=========================================================
  FIGHTING GAME (pygame) - Pilih Tokoh & Kalahkan Semua Lawan
=========================================================

Cara jalankan:
    pip install pygame
    python main.py

Kontrol Player 1 (kamu):
    A / D  = Gerak kiri/kanan
    W      = Lompat
    F      = Pukul
    G      = Tendang
    ESC    = Keluar
    R      = Coba lagi (saat kalah)
    ENTER  = Lanjut (saat menang / di layar ending)

--------------------------------------------------------
CARA MENAMBAH TOKOH BARU (tidak perlu edit kode Python):
--------------------------------------------------------
1. Buka file data/characters.json
2. Tambahkan satu blok tokoh baru di dalam list "characters", contoh:
   {
     "id": "nama_unik_tanpa_spasi",
     "name": "Nama Tokoh",
     "color": [R, G, B],
     "images": {
       "standby": "assets/images/nama_unik/standby.png",
       "jump":    "assets/images/nama_unik/jump.png",
       "punch":   "assets/images/nama_unik/punch.png",
       "kick":    "assets/images/nama_unik/kick.png"
     },
     "stats": { "health": 100, "speed": 5, "punch_damage": 6, "kick_damage": 10 },
     "ending": {
       "image": "assets/images/nama_unik/ending.png",
       "text": "Teks ending saat tokoh ini menang mengalahkan semua lawan."
     }
   }
3. Taruh 5 gambar (standby, jump, punch, kick, ending) di folder
   assets/images/nama_unik/ dengan nama file yang sama seperti di JSON.
   Kalau gambar belum ada, game tetap jalan (memakai kotak placeholder).
4. Jumlah tokoh BEBAS, tidak dibatasi.

--------------------------------------------------------
CARA MENENTUKAN TOKOH YANG SELALU JADI LAWAN TERAKHIR (BOSS):
--------------------------------------------------------
Di paling atas data/characters.json ada field:
    "final_boss_id": "shadow_master"
Ubah nilainya ke id tokoh manapun di daftar "characters" -- tokoh itu akan SELALU
menjadi lawan terakhir yang dihadapi, siapapun tokoh yang kamu pilih untuk dimainkan.
Kalau kamu memilih tokoh yang jadi boss itu sendiri, dia otomatis dilewati dari
urutan lawan (karena tidak melawan diri sendiri).
"""

import os
import sys
import json
import random
import pygame

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "data", "characters.json")

pygame.init()

WIDTH, HEIGHT = 960, 540
FLOOR_Y = HEIGHT - 80

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Pygame Fighting Game - Pilih Tokoh")
clock = pygame.time.Clock()
FPS = 60

WHITE = (245, 245, 245)
BLACK = (20, 20, 20)
YELLOW = (240, 210, 60)
GRAY = (90, 90, 90)
SKY = (25, 25, 40)
GREEN = (60, 200, 90)
PANEL_BG = (20, 20, 30)

font_big = pygame.font.SysFont("arial", 56, bold=True)
font_med = pygame.font.SysFont("arial", 30, bold=True)
font_small = pygame.font.SysFont("arial", 20)
font_tiny = pygame.font.SysFont("arial", 16)

GRAVITY = 0.9
JUMP_SPEED = -16
MOVE_SPEED = 5

PUNCH_RANGE = 70
PUNCH_COOLDOWN = 18
KICK_RANGE = 95
KICK_COOLDOWN = 32
HITSTUN = 12

p1_controls = {
    "left": pygame.K_a, "right": pygame.K_d, "jump": pygame.K_w,
    "punch": pygame.K_f, "kick": pygame.K_g,
}


# ---------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------
def load_characters_data():
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data


_image_cache = {}


def load_image(relative_path, size=None, label=""):
    key = (relative_path, size)
    if key in _image_cache:
        return _image_cache[key]

    full_path = os.path.join(BASE_DIR, relative_path)
    surface = None
    if os.path.isfile(full_path):
        try:
            surface = pygame.image.load(full_path).convert_alpha()
        except Exception:
            surface = None

    if surface is None:
        w, h = size if size else (140, 220)
        surface = pygame.Surface((w, h), pygame.SRCALPHA)
        surface.fill((80, 80, 100, 255))
        pygame.draw.rect(surface, (150, 150, 170), surface.get_rect(), 3)
        txt = font_tiny.render(label or os.path.basename(relative_path), True, WHITE)
        surface.blit(txt, txt.get_rect(center=(w // 2, h // 2)))

    if size:
        surface = pygame.transform.smoothscale(surface, size)

    _image_cache[key] = surface
    return surface


# ---------------------------------------------------------------
# Fighter
# ---------------------------------------------------------------
class Fighter:
    def __init__(self, char_def, x, facing, controls=None, is_cpu=False):
        self.char_id = char_def["id"]
        self.name = char_def["name"]
        self.color = tuple(char_def.get("color", (150, 150, 150)))
        self.images = char_def["images"]
        stats = char_def["stats"]
        self.max_health = stats.get("health", 100)
        self.speed = stats.get("speed", 5)
        self.punch_damage = stats.get("punch_damage", 6)
        self.kick_damage = stats.get("kick_damage", 10)

        self.x = x
        self.y = FLOOR_Y
        self.w = 70
        self.h = 130
        self.vel_y = 0
        self.on_ground = True
        self.facing = facing
        self.health = self.max_health
        self.controls = controls
        self.is_cpu = is_cpu

        self.ai_timer = 0
        self.ai_move = 0
        self.ai_want_jump = False
        self.ai_want_punch = False
        self.ai_want_kick = False

        self.attack_type = None
        self.attack_timer = 0
        self.attack_active_frame = 0
        self.punch_cd = 0
        self.kick_cd = 0
        self.hit_landed = False

        self.hurt_timer = 0
        self.knockback = 0
        self.win = False

    def rect(self):
        return pygame.Rect(int(self.x - self.w // 2), int(self.y - self.h), self.w, self.h)

    def attack_hitbox(self):
        if self.attack_type is None:
            return None
        range_ = PUNCH_RANGE if self.attack_type == "punch" else KICK_RANGE
        if self.facing == 1:
            return pygame.Rect(int(self.x + self.w // 2), int(self.y - self.h * 0.65), range_, 30)
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

        if self.is_cpu:
            self.ai_think(opponent)

        if self.hurt_timer <= 0:
            if self.is_cpu:
                if self.ai_move == -1:
                    self.x -= self.speed
                    self.facing = -1
                elif self.ai_move == 1:
                    self.x += self.speed
                    self.facing = 1
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
                c = self.controls
                if keys[c["left"]]:
                    self.x -= self.speed
                    self.facing = -1
                if keys[c["right"]]:
                    self.x += self.speed
                    self.facing = 1
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

        self.vel_y += GRAVITY
        self.y += self.vel_y
        if self.y >= FLOOR_Y:
            self.y = FLOOR_Y
            self.vel_y = 0
            self.on_ground = True

        self.x = max(self.w // 2 + 5, min(WIDTH - self.w // 2 - 5, self.x))

        if self.attack_type is None:
            self.facing = 1 if opponent.x > self.x else -1

        if self.attack_type is not None:
            self.attack_active_frame -= 1
            self.attack_timer -= 1
            if 0 <= self.attack_active_frame <= 4 and not self.hit_landed:
                hb = self.attack_hitbox()
                if hb and hb.colliderect(opponent.rect()):
                    dmg = self.punch_damage if self.attack_type == "punch" else self.kick_damage
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

    def current_pose(self):
        if self.attack_type == "punch":
            return "punch"
        if self.attack_type == "kick":
            return "kick"
        if not self.on_ground:
            return "jump"
        return "standby"

    def draw(self, surf):
        pose = self.current_pose()
        img_path = self.images.get(pose, self.images.get("standby"))
        img = load_image(img_path, (self.w + 40, self.h + 20), label=f"{self.name}\n{pose}")
        if self.facing == -1:
            img = pygame.transform.flip(img, True, False)
        rect = img.get_rect(midbottom=(int(self.x), int(self.y)))
        if self.hurt_timer > 0 and (self.hurt_timer // 2) % 2 == 0:
            tint = img.copy()
            tint.fill((255, 120, 120, 90), special_flags=pygame.BLEND_RGBA_MULT)
            surf.blit(tint, rect)
        else:
            surf.blit(img, rect)

    def health_ratio(self):
        return self.health / self.max_health


# ---------------------------------------------------------------
# Helpers UI
# ---------------------------------------------------------------
def draw_text(surf, text, pos, font, color=WHITE, max_width=None, center=False):
    if not max_width:
        s = font.render(text, True, color)
        r = s.get_rect()
        if center:
            r.center = pos
        else:
            r.topleft = pos
        surf.blit(s, r)
        return s.get_height()

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
        r = s.get_rect()
        if center:
            r.centerx = x
            r.y = y + i * lh
        else:
            r.topleft = (x, y + i * lh)
        surf.blit(s, r)
    return lh * len(lines)


class Button:
    def __init__(self, rect, text, font, bg=GRAY, fg=WHITE):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.font = font
        self.bg = bg
        self.fg = fg

    def draw(self, surf):
        pygame.draw.rect(surf, self.bg, self.rect, border_radius=8)
        pygame.draw.rect(surf, WHITE, self.rect, 2, border_radius=8)
        t = self.font.render(self.text, True, self.fg)
        surf.blit(t, t.get_rect(center=self.rect.center))

    def is_clicked(self, event):
        return event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.rect.collidepoint(event.pos)


def draw_health_bar(surf, x, y, w, h, ratio, color, flip=False):
    pygame.draw.rect(surf, GRAY, (x, y, w, h), border_radius=6)
    fill_w = int(w * ratio)
    rect = (x + w - fill_w, y, fill_w, h) if flip else (x, y, fill_w, h)
    bar_color = GREEN if ratio > 0.35 else (230, 150, 40) if ratio > 0.15 else (220, 50, 50)
    pygame.draw.rect(surf, bar_color, rect, border_radius=6)
    pygame.draw.rect(surf, BLACK, (x, y, w, h), 3, border_radius=6)


def draw_arena(surf):
    surf.fill(SKY)
    pygame.draw.rect(surf, (50, 40, 60), (0, FLOOR_Y, WIDTH, HEIGHT - FLOOR_Y))
    pygame.draw.line(surf, (80, 70, 90), (0, FLOOR_Y), (WIDTH, FLOOR_Y), 3)
    for i in range(0, WIDTH, 40):
        pygame.draw.line(surf, (35, 30, 45), (i, FLOOR_Y), (i, HEIGHT), 1)


# ---------------------------------------------------------------
# Game (state machine)
# ---------------------------------------------------------------
class Game:
    SELECT = "select"
    FIGHT = "fight"
    ROUND_WIN = "round_win"
    GAMEOVER = "gameover"
    ENDING = "ending"

    def __init__(self):
        self.data = load_characters_data()
        self.characters = self.data["characters"]
        self.final_boss_id = self.data.get("final_boss_id")

        self.state = self.SELECT
        self.selected_index = 0
        self.player_char_def = None
        self.opponent_queue = []
        self.opponent_index = 0
        self.p1 = None
        self.p2 = None
        self.round_winner_text = ""

        self._build_select_buttons()

    def _build_select_buttons(self):
        self.select_buttons = []
        cols = 4
        cell_w, cell_h = 190, 170
        start_x = (WIDTH - cols * cell_w) // 2
        start_y = 130
        for i, c in enumerate(self.characters):
            col = i % cols
            row = i // cols
            x = start_x + col * cell_w
            y = start_y + row * cell_h
            self.select_buttons.append((pygame.Rect(x, y, cell_w - 20, cell_h - 20), c))
        self.start_button = Button((WIDTH // 2 - 110, HEIGHT - 70, 220, 50), "Mulai Bertarung", font_small)

    def build_opponent_queue(self, chosen_id):
        others = [c for c in self.characters if c["id"] != chosen_id]
        boss = None
        if self.final_boss_id:
            boss = next((c for c in others if c["id"] == self.final_boss_id), None)
        rest = [c for c in others if boss is None or c["id"] != boss["id"]]
        random.shuffle(rest)
        queue = rest + ([boss] if boss else [])
        return queue

    def choose_character(self, char_def):
        self.player_char_def = char_def
        self.opponent_queue = self.build_opponent_queue(char_def["id"])
        self.opponent_index = 0
        self.start_next_fight()

    def start_next_fight(self):
        opp_def = self.opponent_queue[self.opponent_index]
        self.p1 = Fighter(self.player_char_def, WIDTH * 0.25, 1, controls=p1_controls, is_cpu=False)
        self.p2 = Fighter(opp_def, WIDTH * 0.75, -1, is_cpu=True)
        self.state = self.FIGHT

    def handle_event(self, event):
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            pygame.quit()
            sys.exit()

        if self.state == self.SELECT:
            for rect, c in self.select_buttons:
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and rect.collidepoint(event.pos):
                    self.selected_index = self.characters.index(c)
            if self.start_button.is_clicked(event):
                self.choose_character(self.characters[self.selected_index])

        elif self.state == self.FIGHT:
            pass  # ditangani lewat keys realtime di update

        elif self.state == self.ROUND_WIN:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
                self.opponent_index += 1
                if self.opponent_index >= len(self.opponent_queue):
                    self.state = self.ENDING
                else:
                    self.start_next_fight()

        elif self.state == self.GAMEOVER:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_r:
                self.start_next_fight()
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_m:
                self.state = self.SELECT

        elif self.state == self.ENDING:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
                self.__init__()

    def update(self):
        if self.state == self.FIGHT:
            keys = pygame.key.get_pressed()
            self.p1.update(keys, self.p2)
            self.p2.update(keys, self.p1)
            if self.p1.health <= 0:
                self.state = self.GAMEOVER
            elif self.p2.health <= 0:
                self.round_winner_text = f"{self.player_char_def['name']} MENGALAHKAN {self.p2.name}!"
                self.state = self.ROUND_WIN

    def draw(self):
        if self.state == self.SELECT:
            self._draw_select()
        elif self.state == self.FIGHT:
            self._draw_fight()
        elif self.state == self.ROUND_WIN:
            self._draw_fight()
            self._draw_overlay(self.round_winner_text, "Tekan ENTER untuk lanjut ke lawan berikutnya")
        elif self.state == self.GAMEOVER:
            self._draw_fight()
            self._draw_overlay("KAMU KALAH!", "Tekan R untuk coba lagi, M untuk pilih tokoh lain", color=(230, 70, 70))
        elif self.state == self.ENDING:
            self._draw_ending()
        pygame.display.flip()

    def _draw_select(self):
        screen.fill((15, 15, 25))
        draw_text(screen, "PILIH TOKOHMU", (WIDTH // 2, 50), font_big, YELLOW, center=True)
        for i, (rect, c) in enumerate(self.select_buttons):
            selected = i == self.selected_index
            bg = pygame.Rect(rect)
            pygame.draw.rect(screen, (40, 40, 60) if not selected else (70, 70, 110), bg, border_radius=10)
            pygame.draw.rect(screen, YELLOW if selected else WHITE, bg, 3 if selected else 1, border_radius=10)
            img = load_image(c["images"]["standby"], (100, 130), label=c["name"])
            screen.blit(img, img.get_rect(center=(bg.centerx, bg.y + 70)))
            draw_text(screen, c["name"], (bg.centerx, bg.bottom - 22), font_small, WHITE, center=True)
            if c["id"] == self.final_boss_id:
                draw_text(screen, "(BOSS TERAKHIR)", (bg.centerx, bg.bottom - 6), font_tiny, (255, 160, 160), center=True)
        self.start_button.draw(screen)

    def _draw_fight(self):
        draw_arena(screen)
        for f in sorted([self.p1, self.p2], key=lambda f: f.y):
            f.draw(screen)

        draw_health_bar(screen, 30, 25, 380, 28, self.p1.health_ratio(), self.p1.color, flip=False)
        draw_health_bar(screen, WIDTH - 30 - 380, 25, 380, 28, self.p2.health_ratio(), self.p2.color, flip=True)

        draw_text(screen, self.p1.name, (30, 55), font_small, WHITE)
        p2_label = f"{self.p2.name} ({self.opponent_index + 1}/{len(self.opponent_queue)})"
        w = font_small.size(p2_label)[0]
        draw_text(screen, p2_label, (WIDTH - 30 - w, 55), font_small, WHITE)

        draw_text(screen, "VS", (WIDTH // 2, 35), font_med, YELLOW, center=True)

    def _draw_overlay(self, title, subtitle, color=YELLOW):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 170))
        screen.blit(overlay, (0, 0))
        draw_text(screen, title, (WIDTH // 2, HEIGHT // 2 - 40), font_big, color, center=True)
        draw_text(screen, subtitle, (WIDTH // 2, HEIGHT // 2 + 30), font_small, WHITE, center=True)

    def _draw_ending(self):
        screen.fill((10, 10, 18))
        ending = self.player_char_def.get("ending", {})
        img_path = ending.get("image", self.player_char_def["images"]["standby"])
        img = load_image(img_path, (280, 340), label=f"{self.player_char_def['name']}\nending")
        screen.blit(img, img.get_rect(center=(WIDTH // 2, 210)))

        draw_text(screen, "JUARA SEJATI!", (WIDTH // 2, 30), font_big, YELLOW, center=True)
        panel = pygame.Rect(80, 400, WIDTH - 160, 110)
        pygame.draw.rect(screen, PANEL_BG, panel, border_radius=10)
        pygame.draw.rect(screen, WHITE, panel, 2, border_radius=10)
        text = ending.get("text", f"{self.player_char_def['name']} berhasil mengalahkan semua lawan!")
        draw_text(screen, text, (panel.x + 20, panel.y + 15), font_small, WHITE, max_width=panel.width - 40)
        draw_text(screen, "Tekan ENTER untuk kembali ke pilihan tokoh", (WIDTH // 2, HEIGHT - 20), font_tiny, GRAY, center=True)

    def run(self):
        while True:
            for event in pygame.event.get():
                self.handle_event(event)
            self.update()
            self.draw()
            clock.tick(FPS)


if __name__ == "__main__":
    Game().run()
