# -*- coding: utf-8 -*-
"""六种敌人 AI + 敌方子弹发射。

所有 AI 都基于固定步长 dt 更新，随机取自 ctx.rng.fork(f"ai:{self.id}")，
保证同一帧序列下行为可复现，且不污染地牢/掉落的随机流。
"""
from __future__ import annotations

import math
from typing import Any

from core.collision import move_with_props
from core.events import ENEMY_DIED, SPAWN_ENEMY, SPAWN_PARTICLES, SPAWN_TEAR
from core.vec2 import Vec2
from entities.base import Entity
from entities.tear import Tear
from settings import ARENA_X, ARENA_Y, ARENA_W, ARENA_H, PALETTE, Group

CENTER = Vec2(ARENA_X + ARENA_W / 2, ARENA_Y + ARENA_H / 2)


class Enemy(Entity):
    __slots__ = ("kind", "hp", "max_hp", "speed", "touch_damage", "hit_flash",
                 "score", "split_level")

    def __init__(self, pos, kind: str, hp: float, speed: float, radius: float,
                 color, sprite_key: str, touch_damage: float = 2.0,
                 split_level: int = 0) -> None:
        super().__init__(pos, radius, Group.ENEMY, solid=False,
                         sprite_key=sprite_key, color=color)
        self.kind = kind
        self.hp = float(hp)
        self.max_hp = float(hp)
        self.speed = float(speed)
        self.touch_damage = float(touch_damage)
        self.hit_flash = 0
        self.score = 1
        self.split_level = split_level

    def hurt(self, amount: float, ctx: Any) -> bool:
        """返回是否致死。"""
        if not self.alive:
            return False
        self.hp -= float(amount)
        self.hit_flash = 5
        ctx.bus.emit(SPAWN_PARTICLES, x=self.pos.x, y=self.pos.y,
                     color=self.color, count=3, speed=55)
        if self.hp > 0:
            return False
        self.kill()
        ctx.bus.emit(ENEMY_DIED, pos=self.pos.copy(), kind=self.kind, enemy=self)
        if self.kind == "splitter" and self.split_level > 0:
            for sign in (-1, 1):
                child = make_enemy("splitter", Vec2(self.pos.x + sign * 12, self.pos.y),
                                   split_level=self.split_level - 1)
                child.hp = child.max_hp = max(2.0, self.max_hp * 0.5)
                child.radius *= 0.78
                child.speed *= 1.2
                ctx.bus.emit(SPAWN_ENEMY, enemy=child)
        return True

    def player(self, ctx: Any):
        room = ctx.room
        if room and room.players:
            for p in room.players:
                if p.alive:
                    return p
        return None

    def _steer(self, target: Vec2, dt: float, ctx: Any, speed_scale: float = 1.0,
               ignore_props: bool = False) -> None:
        delta = target - self.pos
        if delta.length_sq() < 1e-6:
            return
        step = delta.normalized() * self.speed * speed_scale * dt
        if ignore_props:
            self.pos += step
            from core.collision import clamp_arena
            clamp_arena(self)
        else:
            move_with_props(self, step, ctx.room.solids if ctx.room else [])

    def _fire_at(self, target: Vec2, ctx: Any, speed: float = 120.0,
                 damage: float = 2.0) -> None:
        direction = (target - self.pos)
        if direction.length_sq() < 1e-6:
            return
        vel = direction.with_length(speed)
        tear = Tear(self.pos.copy(), vel, damage, owner=Group.TEAR_ENEMY,
                    max_range=320.0, size=0.9)
        ctx.bus.emit(SPAWN_TEAR, tear=tear)

    def _ai(self, dt: float, ctx: Any, player) -> None:
        self._steer(player.pos, dt, ctx)

    def update(self, dt: float, ctx: Any) -> None:
        super().update(dt, ctx)
        if self.hit_flash > 0:
            self.hit_flash -= 1
        player = self.player(ctx)
        if player:
            self._ai(dt, ctx, player)

    def render(self, painter: Any, ctx: Any) -> None:
        color = PALETTE["white"] if self.hit_flash > 0 else self.color
        painter.sprite(self.sprite_key, self.pos.x, self.pos.y,
                       self.radius * 2.2, self.radius * 2.2, color)
        if self.max_hp >= 8 and self.hp < self.max_hp:
            w = self.radius * 2
            painter.rect(PALETTE["ink"], self.pos.x - w / 2, self.pos.y - self.radius - 6, w, 3)
            painter.rect(PALETTE["red"], self.pos.x - w / 2, self.pos.y - self.radius - 6,
                         w * max(0.0, self.hp / self.max_hp), 3)


class FlyEnemy(Enemy):
    """苍蝇：无视障碍直扑玩家，速度快但脆弱。"""
    __slots__ = ("wobble",)

    def __init__(self, pos, hp=4.0, speed=88.0) -> None:
        super().__init__(pos, "fly", hp, speed, 9, PALETTE["purple"], "enemy_fly")
        self.wobble = self.id * 0.7

    def _ai(self, dt, ctx, player) -> None:
        self.wobble += dt * 7
        offset = Vec2(math.sin(self.wobble) * 10, math.cos(self.wobble * 1.3) * 10)
        self._steer(player.pos + offset, dt, ctx, ignore_props=True)


class ChaserEnemy(Enemy):
    """追踪者：被障碍阻挡时贴墙滑动，速度中等。"""
    def __init__(self, pos, hp=6.0, speed=64.0) -> None:
        super().__init__(pos, "chaser", hp, speed, 10, PALETTE["red"], "enemy_chaser")

    def _ai(self, dt, ctx, player) -> None:
        self._steer(player.pos, dt, ctx)


class HopperEnemy(Enemy):
    """跳跳怪：蓄力 → 腾空直冲 → 落地硬直，三态循环。"""
    __slots__ = ("phase", "timer", "jump_dir")

    def __init__(self, pos, hp=7.0, speed=52.0) -> None:
        super().__init__(pos, "hopper", hp, speed, 11, PALETTE["green"], "enemy_hopper")
        self.phase = "idle"
        self.timer = 0.6
        self.jump_dir = Vec2()

    def _ai(self, dt, ctx, player) -> None:
        self.timer -= dt
        if self.phase == "idle":
            if self.timer <= 0:
                self.phase = "jump"
                self.timer = 0.45
                self.jump_dir = (player.pos - self.pos).normalized()
        elif self.phase == "jump":
            self._steer(self.pos + self.jump_dir * 40, dt, ctx, speed_scale=3.0,
                        ignore_props=True)
            if self.timer <= 0:
                self.phase = "rest"
                self.timer = 0.5
        else:
            if self.timer <= 0:
                self.phase = "idle"
                self.timer = 0.35

    def render(self, painter, ctx) -> None:
        lift = 6 if self.phase == "jump" else 0
        color = PALETTE["white"] if self.hit_flash > 0 else self.color
        painter.sprite(self.sprite_key, self.pos.x, self.pos.y - lift,
                       self.radius * 2.2, self.radius * 2.2, color)


class ShooterEnemy(Enemy):
    """射手：保持中距离，定期朝玩家放一发敌方眼泪。"""
    __slots__ = ("cooldown",)

    def __init__(self, pos, hp=6.0, speed=46.0) -> None:
        super().__init__(pos, "shooter", hp, speed, 10, PALETTE["blue"], "enemy_shooter")
        self.cooldown = 1.0

    def _ai(self, dt, ctx, player) -> None:
        distance = self.pos.distance_to(player.pos)
        if distance > 130:
            self._steer(player.pos, dt, ctx)
        elif distance < 84:
            self._steer(self.pos * 2 - player.pos, dt, ctx)
        self.cooldown -= dt
        if self.cooldown <= 0:
            self.cooldown = 1.7
            self._fire_at(player.pos, ctx, speed=126.0)


class SplitterEnemy(Enemy):
    """分裂怪：死亡后分裂出两只更小的自己（level 递减防止无限分裂）。"""
    def __init__(self, pos, hp=9.0, speed=56.0, split_level: int = 1) -> None:
        super().__init__(pos, "splitter", hp, speed, 12, PALETTE["pink"], "enemy_splitter",
                         split_level=split_level)


class OrbiterEnemy(Enemy):
    """环绕者：绕房间中心公转，同时缓慢向玩家靠拢。"""
    __slots__ = ("angle", "radius_orbit")

    def __init__(self, pos, hp=5.0, speed=62.0) -> None:
        super().__init__(pos, "orbiter", hp, speed, 9, PALETTE["teal"], "enemy_orbiter")
        delta = pos - CENTER
        self.angle = math.atan2(delta.y, delta.x)
        self.radius_orbit = max(38.0, delta.length())

    def _ai(self, dt, ctx, player) -> None:
        self.angle += dt * 1.5
        self.radius_orbit = max(28.0, self.radius_orbit - dt * 5)
        target = CENTER + Vec2(math.cos(self.angle), math.sin(self.angle)) * self.radius_orbit
        target = target.lerp(player.pos, 0.25)
        self._steer(target, dt, ctx, ignore_props=True)


ENEMY_CLASSES = {
    "fly": FlyEnemy,
    "chaser": ChaserEnemy,
    "hopper": HopperEnemy,
    "shooter": ShooterEnemy,
    "splitter": SplitterEnemy,
    "orbiter": OrbiterEnemy,
}


def make_enemy(kind: str, pos, *, hp_scale: float = 1.0,
               speed_scale: float = 1.0, split_level: int = 1):
    """工厂：统一按楼层难度缩放 HP 与速度。"""
    pos = pos.copy() if isinstance(pos, Vec2) else Vec2(*pos)
    cls = ENEMY_CLASSES[kind]
    if kind == "splitter":
        enemy = cls(pos, split_level=split_level)
    else:
        enemy = cls(pos)
    enemy.hp = enemy.max_hp = enemy.max_hp * hp_scale
    enemy.speed *= speed_scale
    return enemy


def random_enemy_kinds(rng, floor: int, count: int) -> list[str]:
    """按楼层解锁敌人种类：2 层起加入射手，3 层起加入跳跳怪与分裂怪。"""
    pool = ["fly", "chaser", "orbiter"]
    if floor >= 2:
        pool.append("shooter")
    if floor >= 3:
        pool += ["hopper", "splitter"]
    return [rng.choice(pool) for _ in range(count)]
