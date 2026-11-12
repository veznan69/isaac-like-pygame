# -*- coding: utf-8 -*-
"""道具数值表（纯数据）。

新增道具只需在这里加一条，战斗逻辑无需改动。
mods 只影响 Stats；hearts/coins/keys/bombs 是可变资源，由 items/effects.py 处理。
"""
from __future__ import annotations

ITEMS: dict[str, dict] = {
    "sad_onion": {
        "name": "悲伤洋葱", "desc": "射速大幅提升", "rarity": "common", "price": 5,
        "mods": {"add": {"tear_delay": -3}},
    },
    "inner_eye": {
        "name": "三只眼", "desc": "一次射出三发眼泪，单发伤害略降", "rarity": "rare", "price": 12,
        "mods": {"add": {"multi_shot": 2, "spread": 0.26}, "mul": {"damage": 0.78}},
    },
    "cupid": {
        "name": "丘比特之箭", "desc": "眼泪可以穿透敌人", "rarity": "rare", "price": 10,
        "mods": {"flags": {"piercing": True}},
    },
    "spoon_bender": {
        "name": "弯勺", "desc": "眼泪会追踪敌人", "rarity": "rare", "price": 10,
        "mods": {"flags": {"homing": True}},
    },
    "ghost_shot": {
        "name": "幽灵之泪", "desc": "眼泪可以穿过障碍", "rarity": "rare", "price": 9,
        "mods": {"flags": {"spectral": True}},
    },
    "pencil": {
        "name": "铅笔", "desc": "伤害 +1.5", "rarity": "common", "price": 5,
        "mods": {"add": {"damage": 1.5}},
    },
    "magic_mushroom": {
        "name": "魔法蘑菇", "desc": "伤害、移速与生命上限全面提升", "rarity": "rare", "price": 15,
        "mods": {"add": {"damage": 2.0, "move_speed": 16.0}, "mul": {"damage": 1.2}},
        "hearts": 2.0,
    },
    "speed_ball": {
        "name": "速度球", "desc": "移动速度与弹速提升", "rarity": "common", "price": 6,
        "mods": {"add": {"move_speed": 24.0, "shot_speed": 34.0}},
    },
    "polyphemus": {
        "name": "独眼巨人", "desc": "单发伤害翻倍，但射速下降", "rarity": "rare", "price": 14,
        "mods": {"mul": {"damage": 2.0}, "add": {"tear_delay": 5, "tear_size": 0.35}},
    },
    "number_one": {
        "name": "一号", "desc": "射速极快，但射程缩短", "rarity": "common", "price": 5,
        "mods": {"add": {"tear_delay": -4}, "mul": {"range": 0.68}},
    },
    "the_compass": {
        "name": "罗盘", "desc": "小地图显示特殊房间", "rarity": "common", "price": 7,
        "mods": {"flags": {"compass": True}},
    },
    "blue_map": {
        "name": "蓝地图", "desc": "小地图显示全部房间", "rarity": "common", "price": 7,
        "mods": {"flags": {"map_reveal": True}},
    },
    "lucky_foot": {
        "name": "幸运脚", "desc": "幸运 +3，掉落更好", "rarity": "common", "price": 6,
        "mods": {"add": {"luck": 3.0}},
    },
    "big_tears": {
        "name": "大眼泪", "desc": "眼泪变大，伤害小幅提升", "rarity": "common", "price": 6,
        "mods": {"add": {"tear_size": 0.5, "damage": 0.8}},
    },
    "long_range": {
        "name": "长射程", "desc": "射程 +70", "rarity": "common", "price": 5,
        "mods": {"add": {"range": 70.0}},
    },
    "health_up": {
        "name": "心之容器", "desc": "生命上限 +1 颗心并回满", "rarity": "common", "price": 8,
        "hearts": 2.0,
    },
    "coin_bag": {
        "name": "钱袋", "desc": "获得 8 枚硬币", "rarity": "common", "price": 4,
        "coins": 8,
    },
    "key_ring": {
        "name": "钥匙串", "desc": "获得 2 把钥匙", "rarity": "common", "price": 4,
        "keys": 2,
    },
    "bomb_bag": {
        "name": "炸弹袋", "desc": "获得 3 颗炸弹", "rarity": "common", "price": 4,
        "bombs": 3,
    },
    "brimstone": {
        "name": "硫磺火", "desc": "伤害大幅提升，射速下降", "rarity": "rare", "price": 18,
        "mods": {"mul": {"damage": 1.9, "tear_size": 1.3}, "add": {"tear_delay": 6}},
    },
}

ALL_ITEM_IDS = tuple(sorted(ITEMS))


def get(item_id: str) -> dict:
    return ITEMS[item_id]


def sprite_key(item_id: str) -> str:
    return f"item_{item_id}"
