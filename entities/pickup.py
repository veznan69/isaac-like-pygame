# -*- coding: utf-8 -*-
"""掉落物：心、硬币、钥匙、炸弹与道具。"""
from __future__ import annotations

import math
from typing import Any

from core.vec2 import Vec2
from entities.base import Entity
from settings import PALETTE, PICKUP_RADIUS, PickupKind, Group

PICKUP_STYLE = {
    PickupKind.HEART: ("pickup_heart", PALETTE["red"]),
    PickupKind.COIN: ("pickup_coin", PALETTE["gold"]),
    PickupKind.KEY: ("pickup_key", PALETTE["light"]),
    PickupKind.BOMB: ("pickup_bomb", PALETTE["slate"]),
    PickupKind.ITEM: ("item_unknown", PALETTE["cyan"]),
}


class Pickup(Entity):
    __slots__ = ("kind", "value", "item_id", "price", "bob_phase")

    def __init__(self, pos: Vec2, kind=PickupKind.COIN, value: float = 1.0,
                 item_id: str | None = None, price: int = 0) -> None:
        self.kind = PickupKind(kind)
        key, color = PICKUP_STYLE[self.kind]
        if self.kind == PickupKind.ITEM and item_id:
            key = f"item_{item_id}"
        super().__init__(pos, PICKUP_RADIUS, Group.PICKUP, solid=False,
                         sprite_key=key, color=color)
        self.value = float(value)
        self.item_id = item_id
        self.price = int(price)
        # 用 id 派生相位，不消耗随机数，避免影响种子复现
        self.bob_phase = (self.id % 17) * 0.37

    def render(self, painter: Any, ctx: Any) -> None:
        bob = math.sin(self.age * 4.0 + self.bob_phase) * 1.6
        painter.sprite(self.sprite_key, self.pos.x, self.pos.y + bob,
                       16, 16, self.color)
        if self.price > 0:
            painter.text(str(self.price), self.pos.x, self.pos.y + 12, 9,
                         PALETTE["gold"], anchor="midtop")
