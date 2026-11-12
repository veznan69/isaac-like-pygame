# -*- coding: utf-8 -*-
"""碰撞工具：分组配对表、圆/矩形相交、分轴移动与场地边界约束。

L1 纯逻辑模块，不 import pygame。所有实体通过 pos / radius 描述碰撞体。
"""
from __future__ import annotations

from settings import ARENA_X, ARENA_Y, ARENA_W, ARENA_H, Group
from core.vec2 import Vec2

# (A 组, B 组, 处理器名)；处理器由 core/game.py 绑定，避免实体互相知晓。
PAIRS = (
    (Group.TEAR_PLAYER, Group.ENEMY, "on_tear_hit_enemy"),
    (Group.TEAR_ENEMY, Group.PLAYER, "on_tear_hit_player"),
    (Group.PLAYER, Group.ENEMY, "on_player_touch_enemy"),
    (Group.PLAYER, Group.PICKUP, "on_player_touch_pickup"),
    (Group.PLAYER, Group.DOOR, "on_player_touch_door"),
    (Group.ENEMY, Group.ENEMY, "on_enemy_separate"),
)

ARENA_RIGHT = ARENA_X + ARENA_W
ARENA_BOTTOM = ARENA_Y + ARENA_H


def circles_hit(a, b, pad: float = 0.82) -> bool:
    """圆形相交。pad<1 让碰撞体内缩 18%，手感更宽容，减少"擦边就死"。"""
    radius = (a.radius + b.radius) * pad
    dx = a.pos.x - b.pos.x
    dy = a.pos.y - b.pos.y
    return dx * dx + dy * dy <= radius * radius


def circle_rect_hit(cx: float, cy: float, r: float, rect) -> bool:
    x, y, w, h = rect
    nx = max(x, min(cx, x + w))
    ny = max(y, min(cy, y + h))
    dx, dy = cx - nx, cy - ny
    return dx * dx + dy * dy < r * r


def clamp_arena(entity) -> None:
    """把实体中心限制在墙内可活动矩形。"""
    r = entity.radius
    entity.pos.x = max(ARENA_X + r, min(ARENA_RIGHT - r, entity.pos.x))
    entity.pos.y = max(ARENA_Y + r, min(ARENA_BOTTOM - r, entity.pos.y))


def move_with_props(entity, delta: Vec2, props) -> None:
    """分轴移动解阻挡：先 X 后 Y，某轴被实心障碍挡住只回退该轴，避免贴墙卡死。

    props 需提供 .solid 与 .rect(x, y, w, h)。
    """
    solid = [p for p in props if getattr(p, "solid", False) and p.alive]

    old_x = entity.pos.x
    entity.pos.x += delta.x
    clamp_arena(entity)
    if any(circle_rect_hit(entity.pos.x, entity.pos.y, entity.radius, p.rect) for p in solid):
        entity.pos.x = old_x

    old_y = entity.pos.y
    entity.pos.y += delta.y
    clamp_arena(entity)
    if any(circle_rect_hit(entity.pos.x, entity.pos.y, entity.radius, p.rect) for p in solid):
        entity.pos.y = old_y


def in_arena(pos: Vec2, radius: float = 0.0) -> bool:
    return (ARENA_X + radius <= pos.x <= ARENA_RIGHT - radius
            and ARENA_Y + radius <= pos.y <= ARENA_BOTTOM - radius)


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def rect_center(rect) -> Vec2:
    x, y, w, h = rect
    return Vec2(x + w / 2, y + h / 2)
