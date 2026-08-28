import os

# ------------------------------------------------------------------
# Path dasar project (jangan diubah)
# ------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
SAVE_DIR = os.path.join(BASE_DIR, "saves")
ASSETS_DIR = os.path.join(BASE_DIR, "assets")

SAVE_FILE = os.path.join(SAVE_DIR, "save1.json")

# ------------------------------------------------------------------
# Pengaturan layar & warna. Silakan ubah sesuai selera.
# ------------------------------------------------------------------
SCREEN_WIDTH = 960
SCREEN_HEIGHT = 600
FPS = 60

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (200, 40, 40)
GREEN = (40, 180, 80)
BLUE = (50, 110, 200)
YELLOW = (230, 200, 40)
GRAY = (60, 60, 60)
DARK_GRAY = (30, 30, 30)
PANEL_BG = (20, 20, 30)

MAX_LEVEL = 10
ENEMIES_PER_LEVEL = 2  # jumlah musuh biasa sebelum bertemu boss di tiap level

FONT_NAME = None  # None = font default pygame. Ganti path .ttf di assets/fonts jika mau font custom.
