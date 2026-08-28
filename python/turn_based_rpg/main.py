"""
=========================================================
  TURN-BASED RPG (pygame) - dengan sistem level & save
=========================================================

Cara jalankan:
    pip install pygame
    python main.py

Struktur folder penting (silakan ubah isinya sesuai kebutuhanmu):
    data/characters.json   -> data tokoh utama (HP, attack, defense awal, gambar)
    data/enemies.json      -> daftar musuh biasa
    data/bosses.json       -> daftar 10 boss (satu per level)
    data/story.json        -> semua teks cerita/dialog
    assets/images/          -> semua gambar (tokoh, musuh, boss)
    saves/save1.json        -> file save otomatis (dibuat saat main)

Untuk mengganti gambar atau teks, kamu TIDAK perlu mengubah kode Python.
Cukup edit file JSON di folder data/, dan ganti file gambar di folder assets/images/
dengan nama file yang SAMA (atau ubah path "image" di JSON kalau mau nama lain).
"""
import sys
import random
import pygame

from game.constants import (
    SCREEN_WIDTH, SCREEN_HEIGHT, FPS, WHITE, BLACK, RED, GREEN, BLUE,
    YELLOW, GRAY, DARK_GRAY, PANEL_BG, MAX_LEVEL, ENEMIES_PER_LEVEL, FONT_NAME,
)
from game.data_loader import (
    load_characters, load_story, get_boss_for_level, get_random_enemy_for_level,
)
from game.save_system import has_save, save_game, load_game, delete_save, new_game_state
from game.combat import Combatant
from game.ui import load_image, draw_text, Button


class Game:
    STATE_MENU = "menu"
    STATE_STORY = "story"
    STATE_OVERWORLD = "overworld"
    STATE_BATTLE = "battle"
    STATE_LEVELUP = "levelup"
    STATE_ENDING = "ending"
    STATE_GAMEOVER = "gameover"

    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Petualangan Eldoria - Turn Based RPG")
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.clock = pygame.time.Clock()

        self.font_small = pygame.font.Font(FONT_NAME, 20)
        self.font_medium = pygame.font.Font(FONT_NAME, 28)
        self.font_large = pygame.font.Font(FONT_NAME, 42)

        self.characters = load_characters()
        self.story = load_story()

        self.state = self.STATE_MENU
        self.player_state = None
        self.battle = None
        self.message_log = []
        self.pending_level_after_boss = False
        self.story_lines = []
        self.story_index = 0

        self.buttons = {}
        self._build_menu_buttons()

    # ---------------------------------------------------------------
    # Setup tombol per layar
    # ---------------------------------------------------------------
    def _build_menu_buttons(self):
        cx = SCREEN_WIDTH // 2
        self.buttons["menu"] = [
            Button((cx - 120, 260, 240, 55), "Mulai Baru", self.font_medium),
            Button((cx - 120, 330, 240, 55), "Lanjutkan", self.font_medium, enabled=has_save()),
            Button((cx - 120, 400, 240, 55), "Keluar", self.font_medium),
        ]

    def _build_overworld_buttons(self):
        cx = SCREEN_WIDTH // 2
        self.buttons["overworld"] = [
            Button((cx - 130, 480, 260, 55), "Lanjutkan Petualangan", self.font_medium),
        ]

    def _build_battle_buttons(self):
        self.buttons["battle"] = [
            Button((60, 500, 200, 55), "Serang", self.font_medium, bg=RED),
            Button((280, 500, 200, 55), "Bertahan", self.font_medium, bg=BLUE),
        ]

    def _build_levelup_buttons(self):
        cx = SCREEN_WIDTH // 2
        self.buttons["levelup"] = [
            Button((cx - 320, 320, 190, 70), "+ Health Point", self.font_small),
            Button((cx - 95, 320, 190, 70), "+ Offense", self.font_small),
            Button((cx + 130, 320, 190, 70), "+ Defense", self.font_small),
        ]

    # ---------------------------------------------------------------
    # Alur New Game / Load Game
    # ---------------------------------------------------------------
    def start_new_game(self):
        self.player_state = new_game_state(self.characters)
        save_game(self.player_state)
        self.story_lines = list(self.story.get("intro", []))
        self.story_index = 0
        self.state = self.STATE_STORY

    def continue_game(self):
        self.player_state = load_game()
        self._enter_overworld()

    def _enter_overworld(self):
        self._build_overworld_buttons()
        self.state = self.STATE_OVERWORLD

    # ---------------------------------------------------------------
    # Pertarungan
    # ---------------------------------------------------------------
    def _make_player_combatant(self):
        p = self.characters["player"]
        c = Combatant(
            p["name"],
            self.player_state["max_hp"],
            self.player_state["attack"],
            self.player_state["defense"],
            p["image"],
        )
        c.hp = self.player_state["hp"]
        return c

    def start_battle(self, is_boss):
        self.is_boss_battle = is_boss
        level = self.player_state["level"]
        if is_boss:
            data = get_boss_for_level(level)
        else:
            data = get_random_enemy_for_level(level)

        self.player_combatant = self._make_player_combatant()
        self.enemy_combatant = Combatant(data["name"], data["hp"], data["attack"], data["defense"], data["image"])
        self.enemy_is_boss = is_boss
        self.turn = "player"
        self.message_log = []
        if is_boss:
            self.message_log.append(self.story.get("boss_intro", {}).get(str(level), f"{data['name']} muncul!"))
        else:
            self.message_log.append(f"{data['name']} liar muncul menghadangmu!")
        self._build_battle_buttons()
        self.state = self.STATE_BATTLE

    def _log(self, text):
        self.message_log.append(text)
        self.message_log = self.message_log[-5:]

    def player_action(self, action):
        if not self.player_combatant.is_alive or not self.enemy_combatant.is_alive:
            return
        if action == "attack":
            dmg = self.player_combatant.basic_attack(self.enemy_combatant)
            self._log(f"{self.player_combatant.name} menyerang, {dmg} damage!")
        elif action == "defend":
            self._defending = True
            self._log(f"{self.player_combatant.name} bersiap bertahan.")

        if not self.enemy_combatant.is_alive:
            self._log(f"{self.enemy_combatant.name} dikalahkan!")
            self._end_battle(victory=True)
            return

        # giliran musuh
        dmg = self.enemy_combatant.attack
        if getattr(self, "_defending", False):
            dmg = max(1, dmg // 2)
            self._defending = False
        actual = self.player_combatant.take_damage(dmg)
        self._log(f"{self.enemy_combatant.name} menyerang balik, {actual} damage!")

        # sinkronkan hp ke player_state
        self.player_state["hp"] = self.player_combatant.hp
        save_game(self.player_state)

        if not self.player_combatant.is_alive:
            self._log(f"{self.player_combatant.name} kalah...")
            self.state = self.STATE_GAMEOVER

    def _end_battle(self, victory):
        if not victory:
            self.state = self.STATE_GAMEOVER
            return

        self.player_state["hp"] = self.player_combatant.hp

        if self.enemy_is_boss:
            level = self.player_state["level"]
            if level >= MAX_LEVEL:
                self.player_state["game_won"] = True
                save_game(self.player_state)
                self.state = self.STATE_ENDING
                return
            self.player_state["boss_defeated_this_level"] = True
            save_game(self.player_state)
            self._build_levelup_buttons()
            self.state = self.STATE_LEVELUP
        else:
            self.player_state["enemies_defeated_this_level"] += 1
            save_game(self.player_state)
            self._enter_overworld()

    def apply_level_up(self, stat):
        p = self.characters["player"]
        if stat == "hp":
            self.player_state["max_hp"] += p["hp_per_point"]
            self.player_state["hp"] = self.player_state["max_hp"]
        elif stat == "attack":
            self.player_state["attack"] += p["attack_per_point"]
        elif stat == "defense":
            self.player_state["defense"] += p["defense_per_point"]

        self.player_state["level"] += 1
        self.player_state["enemies_defeated_this_level"] = 0
        self.player_state["boss_defeated_this_level"] = False
        self.player_state["hp"] = self.player_state["max_hp"]
        save_game(self.player_state)
        self._enter_overworld()

    # ---------------------------------------------------------------
    # Event handling
    # ---------------------------------------------------------------
    def handle_event(self, event):
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

        if self.state == self.STATE_MENU:
            for i, btn in enumerate(self.buttons["menu"]):
                if btn.is_clicked(event):
                    if i == 0:
                        self.start_new_game()
                    elif i == 1 and has_save():
                        self.continue_game()
                    elif i == 2:
                        pygame.quit()
                        sys.exit()

        elif self.state == self.STATE_STORY:
            if event.type == pygame.MOUSEBUTTONDOWN or (event.type == pygame.KEYDOWN and event.key in (pygame.K_SPACE, pygame.K_RETURN)):
                self.story_index += 1
                if self.story_index >= len(self.story_lines):
                    self._enter_overworld()

        elif self.state == self.STATE_OVERWORLD:
            for btn in self.buttons["overworld"]:
                if btn.is_clicked(event):
                    level = self.player_state["level"]
                    if self.player_state["enemies_defeated_this_level"] < ENEMIES_PER_LEVEL:
                        self.start_battle(is_boss=False)
                    else:
                        self.start_battle(is_boss=True)

        elif self.state == self.STATE_BATTLE:
            for i, btn in enumerate(self.buttons["battle"]):
                if btn.is_clicked(event):
                    self.player_action("attack" if i == 0 else "defend")

        elif self.state == self.STATE_LEVELUP:
            for i, btn in enumerate(self.buttons["levelup"]):
                if btn.is_clicked(event):
                    stat = ["hp", "attack", "defense"][i]
                    self.apply_level_up(stat)

        elif self.state in (self.STATE_ENDING, self.STATE_GAMEOVER):
            if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
                if self.state == self.STATE_GAMEOVER:
                    # reset hp full dan kembali ke overworld level saat ini (retry)
                    self.player_state["hp"] = self.player_state["max_hp"]
                    save_game(self.player_state)
                    self._enter_overworld()
                else:
                    delete_save()
                    self._build_menu_buttons()
                    self.state = self.STATE_MENU

    # ---------------------------------------------------------------
    # Rendering
    # ---------------------------------------------------------------
    def draw(self):
        self.screen.fill(DARK_GRAY)

        if self.state == self.STATE_MENU:
            self._draw_menu()
        elif self.state == self.STATE_STORY:
            self._draw_story()
        elif self.state == self.STATE_OVERWORLD:
            self._draw_overworld()
        elif self.state == self.STATE_BATTLE:
            self._draw_battle()
        elif self.state == self.STATE_LEVELUP:
            self._draw_levelup()
        elif self.state == self.STATE_ENDING:
            self._draw_ending()
        elif self.state == self.STATE_GAMEOVER:
            self._draw_gameover()

        pygame.display.flip()

    def _draw_menu(self):
        draw_text(self.screen, "PETUALANGAN ELDORIA", (SCREEN_WIDTH // 2 - 260, 120), self.font_large, YELLOW)
        draw_text(self.screen, "Turn-Based RPG", (SCREEN_WIDTH // 2 - 90, 190), self.font_medium, WHITE)
        for btn in self.buttons["menu"]:
            btn.draw(self.screen)

    def _draw_story(self):
        img = load_image("assets/images/player.png", (200, 200))
        self.screen.blit(img, (SCREEN_WIDTH // 2 - 100, 80))
        panel = pygame.Rect(60, 320, SCREEN_WIDTH - 120, 220)
        pygame.draw.rect(self.screen, PANEL_BG, panel, border_radius=10)
        pygame.draw.rect(self.screen, WHITE, panel, 2, border_radius=10)
        text = self.story_lines[min(self.story_index, len(self.story_lines) - 1)]
        draw_text(self.screen, text, (80, 350), self.font_medium, WHITE, max_width=panel.width - 40)
        draw_text(self.screen, "(klik atau tekan ENTER untuk lanjut)", (80, 490), self.font_small, GRAY)

    def _draw_overworld(self):
        level = self.player_state["level"]
        draw_text(self.screen, f"Level {level} / {MAX_LEVEL}", (40, 30), self.font_large, YELLOW)

        img = load_image(self.characters["player"]["image"], (220, 220))
        self.screen.blit(img, (SCREEN_WIDTH // 2 - 110, 90))

        stats_y = 340
        draw_text(self.screen, f"HP: {self.player_state['hp']}/{self.player_state['max_hp']}", (40, stats_y), self.font_medium, GREEN)
        draw_text(self.screen, f"Offense: {self.player_state['attack']}", (40, stats_y + 35), self.font_medium, RED)
        draw_text(self.screen, f"Defense: {self.player_state['defense']}", (40, stats_y + 70), self.font_medium, BLUE)

        remaining = max(0, ENEMIES_PER_LEVEL - self.player_state["enemies_defeated_this_level"])
        if remaining > 0:
            info = f"Kalahkan {remaining} musuh biasa lagi sebelum bertemu Boss level {level}."
        else:
            info = f"Musuh biasa sudah dikalahkan. Selanjutnya: Boss level {level}!"
        draw_text(self.screen, info, (SCREEN_WIDTH - 420, stats_y, ), self.font_small, WHITE, max_width=380)

        for btn in self.buttons["overworld"]:
            btn.draw(self.screen)

    def _draw_hp_bar(self, x, y, w, h, current, maximum, color):
        pygame.draw.rect(self.screen, (50, 50, 50), (x, y, w, h), border_radius=4)
        ratio = max(0, current) / maximum if maximum else 0
        pygame.draw.rect(self.screen, color, (x, y, int(w * ratio), h), border_radius=4)
        pygame.draw.rect(self.screen, WHITE, (x, y, w, h), 2, border_radius=4)

    def _draw_battle(self):
        title = "PERTARUNGAN BOSS!" if self.enemy_is_boss else "Pertarungan"
        draw_text(self.screen, title, (SCREEN_WIDTH // 2 - 100, 20), self.font_medium, YELLOW)

        p_img = load_image(self.player_combatant.image_path, (180, 180))
        e_img = load_image(self.enemy_combatant.image_path, (180, 180))
        self.screen.blit(p_img, (100, 120))
        self.screen.blit(e_img, (SCREEN_WIDTH - 280, 120))

        draw_text(self.screen, self.player_combatant.name, (100, 90), self.font_small, WHITE)
        self._draw_hp_bar(100, 305, 200, 22, self.player_combatant.hp, self.player_combatant.max_hp, GREEN)
        draw_text(self.screen, f"{self.player_combatant.hp}/{self.player_combatant.max_hp}", (100, 330), self.font_small, WHITE)

        draw_text(self.screen, self.enemy_combatant.name, (SCREEN_WIDTH - 280, 90), self.font_small, WHITE)
        self._draw_hp_bar(SCREEN_WIDTH - 280, 305, 200, 22, self.enemy_combatant.hp, self.enemy_combatant.max_hp, RED)
        draw_text(self.screen, f"{self.enemy_combatant.hp}/{self.enemy_combatant.max_hp}", (SCREEN_WIDTH - 280, 330), self.font_small, WHITE)

        panel = pygame.Rect(40, 380, SCREEN_WIDTH - 80, 100)
        pygame.draw.rect(self.screen, PANEL_BG, panel, border_radius=8)
        pygame.draw.rect(self.screen, WHITE, panel, 2, border_radius=8)
        y = 390
        for line in self.message_log[-3:]:
            draw_text(self.screen, line, (55, y), self.font_small, WHITE, max_width=panel.width - 30)
            y += 26

        for btn in self.buttons["battle"]:
            btn.draw(self.screen)

    def _draw_levelup(self):
        draw_text(self.screen, "NAIK LEVEL!", (SCREEN_WIDTH // 2 - 120, 120), self.font_large, YELLOW)
        draw_text(self.screen, self.story.get("level_up", "Pilih atribut untuk ditingkatkan."), (SCREEN_WIDTH // 2 - 300, 200), self.font_medium, WHITE, max_width=600)
        for btn in self.buttons["levelup"]:
            btn.draw(self.screen)

    def _draw_ending(self):
        draw_text(self.screen, "SELAMAT!", (SCREEN_WIDTH // 2 - 100, 150), self.font_large, YELLOW)
        draw_text(self.screen, self.story.get("ending", "Kamu menang!"), (SCREEN_WIDTH // 2 - 320, 240), self.font_medium, WHITE, max_width=640)
        draw_text(self.screen, "Tekan ENTER untuk kembali ke menu utama.", (SCREEN_WIDTH // 2 - 260, 460), self.font_small, GRAY)

    def _draw_gameover(self):
        draw_text(self.screen, "GAME OVER", (SCREEN_WIDTH // 2 - 130, 200), self.font_large, RED)
        draw_text(self.screen, "Kamu kalah dalam pertarungan.", (SCREEN_WIDTH // 2 - 180, 280), self.font_medium, WHITE)
        draw_text(self.screen, "Tekan ENTER untuk mencoba lagi (HP dipulihkan).", (SCREEN_WIDTH // 2 - 280, 340), self.font_small, GRAY)

    # ---------------------------------------------------------------
    def run(self):
        while True:
            for event in pygame.event.get():
                self.handle_event(event)
            self.draw()
            self.clock.tick(FPS)


if __name__ == "__main__":
    Game().run()
