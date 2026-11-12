# -*- coding: utf-8 -*-
"""实体基类与占位绘制约定。

L2 纯逻辑模块：实体不 import pygame，渲染统一通过 painter 抽象接口完成，
因此 headless 测试可以传入 MockPainter 驱动完整房间逻辑。
"""
from __future__ import annotations

import itertools
from typing import Any

from core.vec2 import Vec2
from settings import Group, PALETTE

_ids = itertools.count(1)


class Entity:
    """所有房间内对象的公共基类。"""

    __slots__ = ("id", "pos", "vel", "radius", "group", "alive", "solid",
                 "sprite_key", "color", "age", "mark_remove")

    def __init__(self, pos=None, radius: float = 8.0, group=Group.PROP,
                 solid: bool = False, sprite_key: str | None = None,
                 color=None) -> None:
        self.id = next(_ids)
        self.pos = pos.copy() if isinstance(pos, Vec2) else Vec2(*(pos or (0, 0)))
        self.vel = Vec2()
        self.radius = float(radius)
        self.group = group
        self.alive = True
        self.solid = solid
        self.sprite_key = sprite_key
        self.color = color or PALETTE["gray"]
        self.age = 0.0
        self.mark_remove = False

    @property
    def rect(self) -> tuple[float, float, float, float]:
        d = self.radius * 2
        return (self.pos.x - self.radius, self.pos.y - self.radius, d, d)

    def kill(self) -> None:
        self.alive = False
        self.mark_remove = True

    def update(self, dt: float, ctx: Any) -> None:
        self.age += dt

    def render(self, painter: Any, ctx: Any) -> None:
        """默认外观：有 sprite key 走贴图（缺图时 painter 自动降级为色块）。"""
        diameter = self.radius * 2
        if self.sprite_key:
            painter.sprite(self.sprite_key, self.pos.x, self.pos.y,
                           diameter, diameter, self.color)
        else:
            painter.circle(self.color, self.pos.x, self.pos.y, self.radius)

    def on_collide(self, other: "Entity", ctx: Any) -> None:
        """默认无行为，具体交互由 core/game.py 的配对处理器分发。"""

    def distance_to(self, other: "Entity") -> float:
        return self.pos.distance_to(other.pos)

    def snapshot(self) -> dict:
        return {"id": self.id, "pos": [self.pos.x, self.pos.y],
                "radius": self.radius, "sprite_key": self.sprite_key}
