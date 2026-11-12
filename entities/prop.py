# -*- coding: utf-8 -*-
"""房间障碍物：石头、火堆、道具台、地面装饰。"""
from __future__ import annotations

from typing import Any

from core.vec2 import Vec2
from entities.base import Entity
from settings import PALETTE, TILE, Group

PROP_STYLE = {
    "rock": {"sprite": "prop_rock", "color": PALETTE["slate"], "solid": True, "harm": False, "radius": 12},
    "fire": {"sprite": "prop_fire", "color": PALETTE["orange"], "solid": False, "harm": True, "radius": 11},
    "pedestal": {"sprite": "prop_pedestal", "color": PALETTE["gold"], "solid": True, "harm": False, "radius": 11},
    "decor": {"sprite": None, "color": PALETTE["dark"], "solid": False, "harm": False, "radius": 6},
}


class Prop(Entity):
    """占据一个格子的静态物体；碰撞盒与格子对齐，避免贴图边缘与判定不一致。"""

    __slots__ = ("kind", "harm", "cell", "_box", "item_choices", "price", "used")

    def __init__(self, col: int, row: int, kind: str) -> None:
        style = PROP_STYLE[kind]
        cx = col * TILE + TILE / 2
        cy = row * TILE + TILE / 2
        super().__init__(Vec2(cx, cy), style["radius"], Group.PROP,
                         solid=style["solid"], sprite_key=style["sprite"],
                         color=style["color"])
        self.kind = kind
        self.harm = style["harm"]
        self.cell = (col, row)
        inset = 5 if kind in ("rock", "pedestal") else 8
        self._box = (col * TILE + inset, row * TILE + inset,
                     TILE - 2 * inset, TILE - 2 * inset)
        self.item_choices: list[str] = []
        self.price = 0
        self.used = False

    @property
    def rect(self):
        return self._box

    def render(self, painter: Any, ctx: Any) -> None:
        if self.kind == "decor":
            x, y, w, h = self._box
            painter.rect((56, 50, 74), x, y, w, h)
            painter.outline((70, 62, 92), x, y, w, h, 1)
            painter.rect((62, 55, 82), x + 5, y + 5, 3, 3)
            return
        if self.kind == "fire":
            # 火堆用两层圆做出跳动感，纯几何不依赖素材帧
            pulse = 1.0 + 0.12 * (1 if int(self.age * 8) % 2 else 0)
            painter.circle(PALETTE["blood"], self.pos.x, self.pos.y, self.radius * pulse)
            painter.circle(PALETTE["orange"], self.pos.x, self.pos.y, self.radius * 0.62 * pulse)
            painter.circle(PALETTE["gold"], self.pos.x, self.pos.y, self.radius * 0.3 * pulse)
            return
        if self.kind == "rock":
            painter.sprite("prop_rock", self.pos.x, self.pos.y,
                           TILE - 8, TILE - 8, PALETTE["slate"])
            return
        if self.kind == "pedestal":
            painter.sprite("prop_pedestal", self.pos.x, self.pos.y,
                           TILE - 6, TILE - 6, PALETTE["gold"])
            if self.item_choices and not self.used:
                key = f"item_{self.item_choices[0]}"
                painter.sprite(key, self.pos.x, self.pos.y - 12, 18, 18, PALETTE["cyan"])
            return
        super().render(painter, ctx)
