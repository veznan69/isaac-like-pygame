# -*- coding: utf-8 -*-
"""房间之间的门。

门只负责表现与开合状态，换房由 core/game.py 消费 ROOM_TRANSITION 事件完成，
实体层不需要知道 Floor / Dungeon 的存在。
"""
from __future__ import annotations

from typing import Any

from core.vec2 import Vec2
from entities.base import Entity
from settings import DOOR_CELLS, PALETTE, TILE, Group


class Door(Entity):
    __slots__ = ("dir", "opened", "locked", "_box", "leads_to")

    def __init__(self, direction: str, opened: bool = False, locked: bool = False) -> None:
        col, row = DOOR_CELLS[direction]
        cx, cy = col * TILE + TILE / 2, row * TILE + TILE / 2
        super().__init__(Vec2(cx, cy), 14, Group.DOOR, solid=False)
        self.dir = direction
        self.opened = opened
        self.locked = locked
        self.leads_to: tuple[int, int] | None = None
        if direction in ("N", "S"):
            self._box = (cx - 24, cy - 12, 48, 24)
        else:
            self._box = (cx - 12, cy - 24, 24, 48)

    @property
    def rect(self):
        return self._box

    def set_open(self, value: bool) -> None:
        self.opened = bool(value)

    def render(self, painter: Any, ctx: Any) -> None:
        x, y, w, h = self._box
        if self.opened:
            painter.rect(PALETTE["ink"], x, y, w, h)
            painter.rect(PALETTE["gold"], x + 3, y + 3, w - 6, h - 6)
            painter.rect(PALETTE["ink"], x + 6, y + 6, w - 12, h - 12)
        else:
            painter.rect(PALETTE["dark"], x, y, w, h)
            painter.outline(PALETTE["slate"], x, y, w, h, 2)
            if self.locked:
                painter.circle(PALETTE["gold"], self.pos.x, self.pos.y, 5)
            else:
                painter.circle(PALETTE["gray"], self.pos.x, self.pos.y, 4)
