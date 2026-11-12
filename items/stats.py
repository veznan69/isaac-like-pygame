# -*- coding: utf-8 -*-
"""角色属性计算。

L1 纯逻辑模块。道具修正按「base → 累加 add → 累乘 mul → clamp」计算，
加法与乘法各自满足交换律，因此最终数值与拾取顺序无关，便于种子复现测试。
"""
from __future__ import annotations

from collections import defaultdict

BASE = {
    "damage": 3.5,
    "tear_delay": 12,        # 射击间隔（固定步数，越小越快）
    "shot_speed": 230.0,     # 眼泪速度 px/s
    "range": 190.0,          # 眼泪射程 px
    "move_speed": 132.0,     # 移动速度 px/s
    "tear_size": 1.0,
    "luck": 0.0,
    "multi_shot": 1,
    "spread": 0.0,           # 多重射击扇形半角（弧度）
}

CLAMPS = {
    "damage": (0.5, 40.0),
    "tear_delay": (3, 60),
    "shot_speed": (90.0, 520.0),
    "range": (90.0, 460.0),
    "move_speed": (60.0, 260.0),
    "tear_size": (0.6, 3.0),
    "luck": (-10.0, 20.0),
    "multi_shot": (1, 7),
    "spread": (0.0, 0.9),
}

DEFAULT_FLAGS = {
    "piercing": False,       # 穿透
    "homing": False,         # 追踪
    "spectral": False,       # 眼泪穿墙
    "map_reveal": False,     # 全图显示
    "compass": False,        # 显示特殊房
    "explosive": False,      # 爆炸眼泪（预留）
}


class Stats:
    """只负责战斗数值与 flags；血量/金币/钥匙由 Player 单独持有。"""

    __slots__ = ("_adds", "_muls", "flags")

    def __init__(self) -> None:
        self._adds: dict[str, float] = defaultdict(float)
        self._muls: dict[str, float] = defaultdict(lambda: 1.0)
        self.flags: dict[str, bool] = dict(DEFAULT_FLAGS)

    def add(self, key: str, value: float) -> None:
        self._adds[key] += float(value)

    def multiply(self, key: str, factor: float) -> None:
        self._muls[key] *= float(factor)

    def set_flag(self, name: str, value: bool = True) -> None:
        self.flags[name] = bool(value)

    def get_flag(self, name: str) -> bool:
        return bool(self.flags.get(name, False))

    def value(self, key: str) -> float:
        base = float(BASE[key])
        result = (base + self._adds[key]) * self._muls[key]
        low, high = CLAMPS[key]
        return max(low, min(high, result))

    def int_value(self, key: str) -> int:
        return int(round(self.value(key)))

    def apply(self, mods: dict) -> None:
        """应用一个道具的修正表，结构见 items/item_defs.py。"""
        for key, value in (mods.get("add") or {}).items():
            if key in BASE:
                self.add(key, value)
        for key, value in (mods.get("mul") or {}).items():
            if key in BASE:
                self.multiply(key, value)
        for name, value in (mods.get("flags") or {}).items():
            self.set_flag(name, value)

    def snapshot(self) -> dict:
        return {
            "adds": dict(self._adds),
            "muls": dict(self._muls),
            "flags": dict(self.flags),
        }

    def restore(self, data: dict) -> None:
        self._adds = defaultdict(float, data.get("adds") or {})
        self._muls = defaultdict(lambda: 1.0, data.get("muls") or {})
        self.flags = dict(DEFAULT_FLAGS)
        self.flags.update(data.get("flags") or {})

    def as_dict(self) -> dict:
        return {key: self.value(key) for key in BASE}
