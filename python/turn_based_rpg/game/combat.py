"""
Logika pertarungan turn-based yang sederhana.
"""
import random


class Combatant:
    def __init__(self, name, hp, attack, defense, image_path=None):
        self.name = name
        self.max_hp = hp
        self.hp = hp
        self.attack = attack
        self.defense = defense
        self.image_path = image_path

    @property
    def is_alive(self):
        return self.hp > 0

    def take_damage(self, raw_damage):
        dmg = max(1, raw_damage - self.defense)
        # sedikit variasi acak supaya pertarungan tidak monoton
        dmg = max(1, dmg + random.randint(-1, 1))
        self.hp = max(0, self.hp - dmg)
        return dmg

    def basic_attack(self, target: "Combatant"):
        return target.take_damage(self.attack)
