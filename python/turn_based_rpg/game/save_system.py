"""
Sistem penyimpanan (save/load) progres permainan menggunakan file JSON.
Data yang disimpan: level saat ini, HP, attack, defense, poin stat yang sudah
dipakai, jumlah musuh biasa yang sudah dikalahkan di level tsb, dan status
apakah boss level tsb sudah dikalahkan.
"""
import json
import os
from .constants import SAVE_FILE, SAVE_DIR


def has_save():
    return os.path.isfile(SAVE_FILE)


def save_game(state: dict):
    os.makedirs(SAVE_DIR, exist_ok=True)
    with open(SAVE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)


def load_game():
    with open(SAVE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def delete_save():
    if has_save():
        os.remove(SAVE_FILE)


def new_game_state(characters_data):
    p = characters_data["player"]
    return {
        "level": 1,
        "hp": p["base_hp"],
        "max_hp": p["base_hp"],
        "attack": p["base_attack"],
        "defense": p["base_defense"],
        "enemies_defeated_this_level": 0,
        "boss_defeated_this_level": False,
        "game_won": False,
    }
