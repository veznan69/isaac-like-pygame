# -*- coding: utf-8 -*-
"""小地图绘制（使用 painter 抽象，不 import pygame）。"""
from __future__ import annotations

from typing import Any

from settings import PALETTE, RoomType

CELL = 9
GAP = 2
PAD = 4

ROOM_COLOR = {
    RoomType.START.value: PALETTE["blue"],
    RoomType.NORMAL.value: PALETTE["light"],
    RoomType.BOSS.value: PALETTE["red"],
    RoomType.TREASURE.value: PALETTE["gold"],
    RoomType.SHOP.value: PALETTE["green"],
}


def draw(painter: Any, dungeon, rooms: dict, current_pos, stats) -> None:
    """右上角小地图。未访问房间默认不显示，蓝地图/罗盘道具会扩展可见范围。"""
    plans = dungeon.plans
    if not plans:
        return
    gx_values = [p[0] for p in plans]
    gy_values = [p[1] for p in plans]
    min_x, max_x = min(gx_values), max(gx_values)
    min_y, max_y = min(gy_values), max(gy_values)
    cols = max_x - min_x + 1
    rows = max_y - min_y + 1
    width = cols * CELL + (cols - 1) * GAP + PAD * 2
    height = rows * CELL + (rows - 1) * GAP + PAD * 2
    origin_x = 480 - width - 6
    origin_y = 6

    painter.alpha_rect((12, 10, 20), 205, origin_x, origin_y, width, height)

    reveal_all = stats.get_flag("map_reveal") if stats else False
    show_special = stats.get_flag("compass") if stats else False

    for pos in sorted(plans):
        plan = plans[pos]
        room = rooms.get(pos)
        visited = bool(room and room.visited)
        special = plan.rtype in (RoomType.BOSS.value, RoomType.TREASURE.value, RoomType.SHOP.value)
        if not visited and not reveal_all and not (show_special and special):
            continue
        x = origin_x + PAD + (pos[0] - min_x) * (CELL + GAP)
        y = origin_y + PAD + (pos[1] - min_y) * (CELL + GAP)
        color = ROOM_COLOR.get(plan.rtype, PALETTE["light"])
        if not visited:
            color = PALETTE["slate"]
        painter.rect(color, x, y, CELL, CELL)
        if pos == current_pos:
            painter.outline(PALETTE["white"], x - 1, y - 1, CELL + 2, CELL + 2, 1)
        elif visited and plan.doors:
            painter.rect(PALETTE["ink"], x + 3, y + 3, CELL - 6, CELL - 6)
    painter.outline(PALETTE["slate"], origin_x, origin_y, width, height, 1)
