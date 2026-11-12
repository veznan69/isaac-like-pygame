# -*- coding: utf-8 -*-
"""玩家角色。

血量以"半心"为单位（1 颗心 = 2.0），与以撒一致；战斗数值全部来自 Stats，
玩家只持有可变的资源与计时器。
"""
from __future__ import annotations

import math
from typing import Any

from core.events import PLAYER_DIED, PLAYER_HURT, SHAKE
from core.vec2 import Vec2
from entities.base import Entity
from entities.tear import Tear
from items.stats import Stats
from settings import PALETTE, PLAYER_RADIUS, INVULN_STEPS, Group


class Player(Entity):
    __slots__ = ("hp", "max_hp", "coins", "keys", "bombs", "stats", "invuln",
                 "fire_cooldown", "facing", "collected", "kills", "flash")

    def __init__(self, pos: Vec2 | None = None) -> None:
        super().__init__(pos or Vec2(240, 144), PLAYER_RADIUS, Group.PLAYER,
                         solid=False, sprite_key="player_idle", color=PALETTE["white"])
        self.max_hp = 6.0
        self.hp = 6.0
        self.coins = 0
        self.keys = 0
        self.bombs = 0
        self.stats = Stats()
        self.invuln = 0
        self.fire_cooldown = 0
        self.facing = Vec2(0, 1)
        self.collected: list[str] = []
        self.kills = 0
        self.flash = 0

    @property
    def alive_hearts(self) -> float:
        return max(0.0, self.hp)

    def heal(self, value: float) -> None:
        self.hp = min(self.max_hp, self.hp + value)

    def add_max_hp(self, half_hearts: float) -> None:
        self.max_hp += half_hearts
        self.heal(half_hearts)

    def hurt(self, amount: float, ctx: Any) -> bool:
        """返回是否真的造成伤害（无敌帧内会忽略）。"""
        if self.invuln > 0 or not self.alive:
            return False
        self.hp = max(0.0, self.hp - float(amount))
        self.invuln = INVULN_STEPS
        self.flash = 6
        ctx.bus.emit(PLAYER_HURT, amount=amount, source="unknown")
        ctx.bus.emit(SHAKE, strength=5.0)
        if self.hp <= 0:
            ctx.bus.emit(PLAYER_DIED)
        return True

    def can_fire(self) -> bool:
        return self.fire_cooldown <= 0

    def shoot(self, direction: Vec2, ctx: Any) -> list[Tear]:
        """按当前属性生成 1~N 发眼泪；扇形布局保证多重射击方向可复现。"""
        if direction.length_sq() < 1e-9 or not self.can_fire():
            return []
        self.fire_cooldown = self.stats.int_value("tear_delay")
        self.facing = direction.normalized()
        base = math.atan2(self.facing.y, self.facing.x)
        count = self.stats.int_value("multi_shot")
        spread = self.stats.value("spread")
        speed = self.stats.value("shot_speed")
        damage = self.stats.value("damage")
        rng = self.stats.value("range")
        size = self.stats.value("tear_size")
        piercing = self.stats.get_flag("piercing")
        homing = self.stats.get_flag("homing")
        spectral = self.stats.get_flag("spectral")

        if count == 1:
            angles = [base]
        else:
            angles = [base - spread + 2 * spread * i / (count - 1) for i in range(count)]

        tears = []
        for angle in angles:
            vel = Vec2(math.cos(angle), math.sin(angle)) * speed
            tears.append(Tear(self.pos.copy(), vel, damage,
                              owner=Group.TEAR_PLAYER, max_range=rng,
                              piercing=piercing, homing=homing,
                              spectral=spectral, size=size))
        return tears

    def update(self, dt: float, ctx: Any) -> None:
        super().update(dt, ctx)
        if self.fire_cooldown > 0:
            self.fire_cooldown -= 1
        if self.invuln > 0:
            self.invuln -= 1
        if self.flash > 0:
            self.flash -= 1

    def render(self, painter: Any, ctx: Any) -> None:
        # 无敌帧隔帧不画，用闪烁反馈受击；不改变逻辑
        if self.invuln > 0 and (self.invuln // 4) % 2 == 0:
            return
        dx, dy = self.facing.x, self.facing.y
        if abs(dy) > abs(dx):
            key = "player_down" if dy > 0 else "player_up"
        else:
            key = "player_side"
        painter.sprite(key, self.pos.x, self.pos.y, 26, 26, PALETTE["white"])
        # 眼睛朝向给出方向感
        ex = self.pos.x + dx * 4
        ey = self.pos.y + dy * 4 - 2
        painter.circle(PALETTE["ink"], ex, ey, 2.2)
