"""
Fungsi bantu untuk UI: memuat gambar dengan aman (fallback jika file belum ada),
menggambar teks dengan word-wrap, dan menggambar tombol sederhana.
"""
import os
import pygame
from .constants import BASE_DIR, GRAY, WHITE, BLACK

_image_cache = {}


def load_image(relative_path, size=None):
    """Muat gambar relatif terhadap folder project. Jika file tidak ditemukan,
    kembalikan placeholder abu-abu berlabel nama file supaya game tetap jalan."""
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
        w, h = size if size else (160, 160)
        surface = pygame.Surface((w, h), pygame.SRCALPHA)
        surface.fill((70, 70, 90, 255))
        pygame.draw.rect(surface, (120, 120, 140), surface.get_rect(), 3)
        font = pygame.font.SysFont(None, 20)
        label = os.path.basename(relative_path)
        text = font.render(label, True, WHITE)
        surface.blit(text, text.get_rect(center=(w // 2, h // 2)))

    if size:
        surface = pygame.transform.smoothscale(surface, size)

    _image_cache[key] = surface
    return surface


def draw_text(screen, text, pos, font, color=WHITE, max_width=None):
    if not max_width:
        surf = font.render(text, True, color)
        screen.blit(surf, pos)
        return surf.get_height()

    words = text.split(" ")
    lines = []
    current = ""
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
    line_height = font.get_linesize()
    for i, line in enumerate(lines):
        surf = font.render(line, True, color)
        screen.blit(surf, (x, y + i * line_height))
    return line_height * len(lines)


class Button:
    def __init__(self, rect, text, font, bg=GRAY, fg=WHITE, enabled=True):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.font = font
        self.bg = bg
        self.fg = fg
        self.enabled = enabled

    def draw(self, screen):
        color = self.bg if self.enabled else (40, 40, 40)
        pygame.draw.rect(screen, color, self.rect, border_radius=8)
        pygame.draw.rect(screen, WHITE, self.rect, 2, border_radius=8)
        text_surf = self.font.render(self.text, True, self.fg if self.enabled else (110, 110, 110))
        screen.blit(text_surf, text_surf.get_rect(center=self.rect.center))

    def is_clicked(self, event):
        if not self.enabled:
            return False
        return event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.rect.collidepoint(event.pos)
