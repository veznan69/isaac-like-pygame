# -*- coding: utf-8 -*-
"""Boss：三阶段行为（追击 → 环形弹幕 → 召唤 + 高速弹幕）。"""
from __future__ import annotations

import math
from typing import Any

from core.events import BOSS_DIED, ENEMY_DIED, SPAWN_ENEMY, SPAWN_PARTICLES, SPAWN_TEAR
from core.vec2 import Vec2
from entities.enemies import Enemy, make_enemy
from entities.tear import Tear
from settings import PALETTE, Group


class Boss(Enemy):
    __slots__ = ("phase", "cooldown", "summon_cooldown", "floor")

    def __init__(self, pos, floor: int = 1) -> None:
        hp = 56.0 + 18.0 * (floor - 1)
        super().__init__(pos, "boss", hp, 44.0 + 2.0 * floor, 20,
                         PALETTE["blood"], "boss_idle", touch_damage=2.0)
        self.floor = floor
        self.phase = 1
        self.cooldown = 1.2
        self.summon_cooldown = 4.0
        self.score = 10

    def hurt(self, amount: float, ctx: Any) -> bool:
        died = super().hurt(amount, ctx)
        if died:
            ctx.bus.emit(BOSS_DIED, pos=self.pos.copy(), floor=self.floor)
        return died

    def _ring(self, ctx: Any, count: int, speed: float) -> None:
        for i in range(count):
            angle = math.tau * i / count + self.age * 0.35
            vel = Vec2(math.cos(angle), math.sin(angle)) * speed
            tear = Tear(self.pos.copy(), vel, 2.0, owner=Group.TEAR_ENEMY,
                        max_range=300.0, size=1.05)
            ctx.bus.emit(SPAWN_TEAR, tear=tear)

    def _ai(self, dt: float, ctx: Any, player) -> None:
        ratio = self.hp / self.max_hp
        new_phase = 3 if ratio <= 0.33 else (2 if ratio <= 0.66 else 1)
        if new_phase != self.phase:
            self.phase = new_phase
            self.cooldown = 0.45
            ctx.bus.emit(SPAWN_PARTICLES, x=self.pos.x, y=self.pos.y,
                         color=PALETTE["gold"], count=14, speed=90)

        if self.phase == 1:
            self._steer(player.pos, dt, ctx, speed_scale=1.0)
        else:
            # 弹幕阶段改为缓慢游走，给玩家留出走位空间
            target = player.pos.lerp(Vec2(240, 144), 0.65)
            self._steer(target, dt, ctx, speed_scale=0.65)

        self.cooldown -= dt
        if self.phase >= 2 and self.cooldown <= 0:
            self.cooldown = 1.45 if self.phase == 2 else 0.95
            self._ring(ctx, 8 if self.phase == 2 else 12,
                       112.0 if self.phase == 2 else 138.0)

        if self.phase == 3:
            self.summon_cooldown -= dt
            if self.summon_cooldown <= 0:
                self.summon_cooldown = 4.5
                for sign in (-1, 1):
                    spawn = Vec2(self.pos.x + sign * 34, self.pos.y + 22)
                    ctx.bus.emit(SPAWN_ENEMY, enemy=make_enemy("fly", spawn, hp_scale=0.7))

    def render(self, painter: Any, ctx: Any) -> None:
        color = PALETTE["white"] if self.hit_flash > 0 else self.color
        key = "boss_angry" if self.phase >= 2 else "boss_idle"
        painter.sprite(key, self.pos.x, self.pos.y, 48, 48, color)
        w = 44
        painter.rect(PALETTE["ink"], self.pos.x - w / 2, self.pos.y - 30, w, 4)
        painter.rect(PALETTE["red"], self.pos.x - w / 2, self.pos.y - 30,
                     w * max(0.0, self.hp / self.max_hp), 4)
