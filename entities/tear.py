# -*- coding: utf-8 -*-
"""眼泪子弹。

以撒的标志性手感：眼泪并非匀速飞到屏幕外，而是飞满射程后逐渐"掉下来"，
受重力下坠并缩小消失，命中或落地时溅开一小簇粒子。
"""
from __future__ import annotations

import math
from typing import Any

from core.collision import circle_rect_hit, in_arena
from core.events import SPAWN_PARTICLES
from core.vec2 import Vec2
from entities.base import Entity
from settings import PALETTE, TEAR_RADIUS, Group


class Tear(Entity):
    __slots__ = ("damage", "owner", "travel", "max_range", "falling", "piercing",
                 "homing", "spectral", "hit_ids", "size", "_born_speed")

    def __init__(self, pos: Vec2, vel: Vec2, damage: float,
                 owner=Group.TEAR_PLAYER, max_range: float = 190.0,
                 piercing: bool = False, homing: bool = False,
                 spectral: bool = False, size: float = 1.0) -> None:
        radius = TEAR_RADIUS * size
        tint = PALETTE["cyan"] if owner == Group.TEAR_PLAYER else PALETTE["red"]
        super().__init__(pos, radius, owner, solid=False, color=tint)
        self.vel = vel.copy()
        self.damage = float(damage)
        self.owner = owner
        self.travel = 0.0
        self.max_range = float(max_range)
        self.falling = False
        self.piercing = piercing
        self.homing = homing
        self.spectral = spectral
        self.size = size
        self.hit_ids: set[int] = set()
        self._born_speed = vel.length()

    @property
    def friendly(self) -> bool:
        return self.owner == Group.TEAR_PLAYER

    def _splash(self, ctx: Any) -> None:
        ctx.bus.emit(SPAWN_PARTICLES, x=self.pos.x, y=self.pos.y,
                     color=self.color, count=4, speed=42)

    def _find_target(self, ctx: Any):
        room = ctx.room
        if room is None:
            return None
        pool = room.players if not self.friendly else room.enemies
        best, best_dist = None, 1e9
        for entity in pool:
            if entity.alive:
                d = self.pos.distance_to(entity.pos)
                if d < best_dist:
                    best, best_dist = entity, d
        return best if best_dist < 130 else None

    def update(self, dt: float, ctx: Any) -> None:
        super().update(dt, ctx)

        if self.homing:
            target = self._find_target(ctx)
            if target:
                wanted = (target.pos - self.pos).with_length(self._born_speed)
                self.vel = self.vel.lerp(wanted, min(1.0, 3.4 * dt))

        # 飞满射程后进入坠落段：加重力、缩小，制造眼泪抛物线尾段
        if self.travel > self.max_range and not self.falling:
            self.falling = True
        if self.falling:
            self.vel.y += 330.0 * dt
            self.size = max(0.35, self.size - 0.9 * dt)
            self.radius = TEAR_RADIUS * self.size

        step = self.vel * dt
        self.travel += step.length()
        self.pos += step

        if not self.spectral and ctx.room is not None:
            for prop in ctx.room.solids:
                if prop.alive and circle_rect_hit(self.pos.x, self.pos.y, self.radius, prop.rect):
                    self._splash(ctx)
                    self.kill()
                    return

        if self.travel > self.max_range * 1.3 or not in_arena(self.pos, -4) or self.age > 4.0:
            self._splash(ctx)
            self.kill()

    def render(self, painter: Any, ctx: Any) -> None:
        key = "tear_blue" if self.friendly else "tear_red"
        diameter = max(4.0, self.radius * 2)
        painter.sprite(key, self.pos.x, self.pos.y, diameter, diameter, self.color)
        if self.size > 0.8:
            painter.circle(PALETTE["white"], self.pos.x - self.radius * 0.25,
                           self.pos.y - self.radius * 0.3, max(1.0, self.radius * 0.22))
