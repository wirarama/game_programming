"""
Modul untuk memuat semua data game (karakter, musuh, boss, story) dari file JSON
di folder data/. Untuk mengubah teks atau statistik, cukup edit file JSON,
tidak perlu menyentuh kode Python ini.
"""
import json
import os
from .constants import DATA_DIR


def _load_json(filename):
    path = os.path.join(DATA_DIR, filename)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_characters():
    return _load_json("characters.json")


def load_enemies():
    return _load_json("enemies.json")["enemies"]


def load_bosses():
    return _load_json("bosses.json")["bosses"]


def load_story():
    return _load_json("story.json")


def get_boss_for_level(level):
    for boss in load_bosses():
        if boss["level"] == level:
            return boss
    return None


def get_random_enemy_for_level(level):
    import random
    candidates = [e for e in load_enemies() if e["min_level"] <= level <= e["max_level"]]
    if not candidates:
        candidates = load_enemies()
    return random.choice(candidates)
