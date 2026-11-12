# -*- coding: utf-8 -*-
"""单个房间：布局、实体容器、清房判定与渲染。

L3 纯逻辑模块，渲染全部经 painter 抽象，不 import pygame。
房间内容在首次进入时才生成（延迟生成），便于地牢测试只验证蓝图。
"""
from __future__ import annotations

import math
from typing import Any

from core.events import ROOM_CLEARED, ROOM_ENTERED, SPAWN_PARTICLES
from core.vec2 import Vec2
from entities.boss import Boss
from entities.door import Door
from entities.enemies import make_enemy, random_enemy_kinds
from entities.pickup import Pickup
from entities.prop import Prop
from items.effects import item_pool_for_room, price_of, roll_items
from settings import (ARENA_X, ARENA_Y, ARENA_W, ARENA_H, COL_FLOOR, COL_FLOOR_ALT,
                      COL_GRID, COL_WALL, COL_WALL_EDGE, COL_WALL_SHADE, DOOR_CELLS, DIRS,
                      LOGICAL_H, LOGICAL_W, PALETTE, PickupKind, RoomType, TILE)
from world.dungeon import RoomPlan
from world.room_templates import grid_to_cells, template_spawn_points


class Particle:
    """纯视觉粒子，使用房间独立的 visual_rng，不参与种子复现。"""
    __slots__ = ("pos", "vel", "life", "max_life", "color", "size")

    def __init__(self, pos: Vec2, vel: Vec2, life: float, color, size: float) -> None:
        self.pos = pos.copy()
        self.vel = vel.copy()
        self.life = life
        self.max_life = life
        self.color = color
        self.size = size

    def update(self, dt: float) -> None:
        self.life -= dt
        self.pos += self.vel * dt
        self.vel *= 0.90

    def render(self, painter: Any) -> None:
        if self.life > 0:
            size = max(1.0, self.size * (self.life / self.max_life))
            painter.circle(self.color, self.pos.x, self.pos.y, size)


class Room:
    def __init__(self, plan: RoomPlan, floor: int, rng, difficulty: float = 1.0) -> None:
        self.plan = plan
        self.pos = plan.pos
        self.rtype = plan.rtype
        self.template = plan.template
        self.floor = floor
        self.difficulty = difficulty
        self.rng = rng.fork(f"room:{plan.gx},{plan.gy}")
        self.visual_rng = rng.fork(f"visual:{plan.gx},{plan.gy}")

        self.doors: dict[str, Door] = {}
        for d in plan.doors:
            door = Door(d, opened=False)
            dx, dy = DIRS[d]
            door.leads_to = (plan.gx + dx, plan.gy + dy)
            self.doors[d] = door

        self.props: list[Prop] = []
        self.solids: list[Prop] = []
        self.players: list = []
        self.enemies: list = []
        self.tears: list = []
        self.pickups: list = []
        self.particles: list[Particle] = []

        self.visited = False
        self.generated = False
        self.cleared = False
        self.pending_return = False

    # ---------- 内容生成 ----------

    def populate(self, owned: list[str] | None = None) -> None:
        """首次进入时按模板摆放障碍、敌人与道具。"""
        if self.generated:
            return
        self.generated = True
        owned = owned or []

        for col, row, kind in grid_to_cells(self.template):
            # 'spawn' 只是敌人生成点标记，不是可绘制的道具
            if kind == "spawn":
                continue
            prop = Prop(col, row, kind)
            self.props.append(prop)
            if prop.solid:
                self.solids.append(prop)
            if kind == "pedestal":
                self._setup_pedestal(prop, owned)

        pedestals = [p for p in self.props if p.kind == "pedestal"]
        if self.rtype == RoomType.TREASURE.value and pedestals:
            pedestals[0].item_choices = roll_items(self.rng.fork("treasure"), owned, 3,
                                                   item_pool_for_room(owned, self.floor))
        elif self.rtype == RoomType.SHOP.value:
            self._setup_shop(pedestals, owned)
        elif self.rtype == RoomType.BOSS.value:
            self.enemies.append(Boss(Vec2(LOGICAL_W / 2, 100), self.floor))
        elif self.rtype == RoomType.NORMAL.value:
            self._spawn_enemies()

        self.cleared = not self.enemies
        self.set_doors_open(self.cleared)

    def _setup_pedestal(self, prop: Prop, owned: list[str]) -> None:
        prop.used = False

    def _setup_shop(self, pedestals: list[Prop], owned: list[str]) -> None:
        choices = roll_items(self.rng.fork("shop"), owned, 3,
                             item_pool_for_room(owned, self.floor))
        for index, prop in enumerate(pedestals[:len(choices)]):
            item_id = choices[index]
            pickup = Pickup(Vec2(prop.pos.x, prop.pos.y - 6),
                            kind=PickupKind.ITEM, item_id=item_id,
                            price=price_of(item_id))
            self.pickups.append(pickup)

    def _spawn_enemies(self) -> None:
        points = template_spawn_points(self.template)
        if not points:
            points = [(7, 4), (4, 3), (10, 5)]
        count = min(len(points), max(2, int(2 + self.floor * 0.7)))
        kinds = random_enemy_kinds(self.rng.fork("enemy_kinds"), self.floor, count)
        spawn_rng = self.rng.fork("enemy_positions")
        chosen = sorted(points, key=lambda p: (p[1], p[0]))[:count]
        hp_scale = 1.0 + 0.20 * (self.floor - 1)
        speed_scale = 1.0 + 0.05 * (self.floor - 1)
        for (col, row), kind in zip(chosen, kinds):
            jitter = Vec2(spawn_rng.uniform(-5, 5), spawn_rng.uniform(-5, 5))
            pos = Vec2(col * TILE + TILE / 2, row * TILE + TILE / 2) + jitter
            self.enemies.append(make_enemy(kind, pos, hp_scale=hp_scale,
                                           speed_scale=speed_scale))

    # ---------- 状态 ----------

    def set_doors_open(self, value: bool) -> None:
        for door in self.doors.values():
            door.set_open(value)

    def add_particles(self, x: float, y: float, color, count: int = 4,
                      speed: float = 50.0) -> None:
        for _ in range(count):
            angle = self.visual_rng.angle()
            vec = Vec2(math.cos(angle), math.sin(angle)) * self.visual_rng.uniform(speed * 0.4, speed)
            self.particles.append(Particle(Vec2(x, y), vec,
                                           self.visual_rng.uniform(0.18, 0.45), color, 2.4))

    def all_entities(self):
        for entity in self.pickups:
            yield entity
        for entity in self.enemies:
            yield entity
        for entity in self.tears:
            yield entity
        for entity in self.players:
            yield entity
        for entity in self.props:
            if entity.kind != "decor":
                yield entity

    def check_cleared(self, ctx: Any) -> bool:
        """敌人清空时开门并发事件，奖励由 core/game.py 统一派发。"""
        if self.cleared or self.enemies:
            return False
        self.cleared = True
        self.set_doors_open(True)
        ctx.bus.emit(ROOM_CLEARED, room=self)
        return True

    def _sweep(self) -> None:
        self.enemies = [e for e in self.enemies if e.alive and not e.mark_remove]
        self.tears = [t for t in self.tears if t.alive and not t.mark_remove]
        self.pickups = [p for p in self.pickups if p.alive and not p.mark_remove]
        self.particles = [p for p in self.particles if p.life > 0]

    def update(self, dt: float, ctx: Any) -> None:
        for entity in list(self.all_entities()):
            entity.update(dt, ctx)
        for particle in self.particles:
            particle.update(dt)
        self._sweep()

    # ---------- 渲染 ----------

    def _draw_floor(self, painter: Any) -> None:
        painter.rect(COL_FLOOR, 0, 0, LOGICAL_W, LOGICAL_H)
        door_cells = set(DOOR_CELLS.values())
        for row in range(1, 8):
            for col in range(1, 14):
                if (col + row) % 2 == 0:
                    painter.rect(COL_FLOOR_ALT, col * TILE, row * TILE, TILE, TILE)
        for col in range(1, 14):
            painter.line(COL_GRID, col * TILE, TILE, col * TILE, LOGICAL_H - TILE, 1)
        for row in range(1, 8):
            painter.line(COL_GRID, TILE, row * TILE, LOGICAL_W - TILE, row * TILE, 1)

        # 内框亮线把"墙"和"地板"明确分开
        painter.outline(COL_WALL_EDGE, TILE, TILE, LOGICAL_W - 2 * TILE,
                        LOGICAL_H - 2 * TILE, 2)

        # 四面墙：逐格画砖块纹理，门格留空由 Door 实体接管
        for row in range(9):
            for col in range(15):
                if not (row in (0, 8) or col in (0, 14)) or (col, row) in door_cells:
                    continue
                x, y = col * TILE, row * TILE
                painter.rect(COL_WALL, x, y, TILE, TILE)
                painter.rect(COL_WALL_EDGE, x + 1, y + 1, TILE - 2, 3)
                painter.rect(COL_WALL_SHADE, x + 1, y + TILE - 4, TILE - 2, 3)
                painter.line(COL_WALL_SHADE, x, y + TILE // 2, x + TILE, y + TILE // 2, 1)
                painter.line(COL_WALL_SHADE, x + TILE // 2, y + TILE // 2,
                             x + TILE // 2, y + TILE, 1)
                if (row + col) % 4 == 0:
                    painter.rect(COL_WALL_EDGE, x + 5, y + 7, 3, 3)

    def render(self, painter: Any, ctx: Any) -> None:
        self._draw_floor(painter)
        for prop in self.props:
            if prop.kind == "decor":
                prop.render(painter, ctx)
        for door in self.doors.values():
            door.render(painter, ctx)
        for prop in self.props:
            if prop.kind in ("rock", "pedestal"):
                prop.render(painter, ctx)
        for prop in self.props:
            if prop.kind == "fire":
                prop.render(painter, ctx)
        for pickup in self.pickups:
            pickup.render(painter, ctx)
        for enemy in self.enemies:
            enemy.render(painter, ctx)
        for tear in self.tears:
            tear.render(painter, ctx)
        for player in self.players:
            player.render(painter, ctx)
        for particle in self.particles:
            particle.render(painter)
