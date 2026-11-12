# -*- coding: utf-8 -*-
"""房间布局模板。

L2 纯数据模块。每个模板是内部 13x7 的字符网格（外圈墙由 world/room.py 统一绘制），
坐标 (col, row) 对应房间格 (col+1, row+1)。

字符含义：
    .  空地            o  石头（实心障碍）
    x  火堆（接触伤害） e  敌人生成点
    d  装饰地砖        p  道具台（实心，宝箱/商店/Boss 房使用）
"""
from __future__ import annotations

TEMPLATES: dict[str, tuple[str, ...]] = {
    "empty": (
        ".............",
        ".............",
        "....e...e....",
        ".............",
        "....e...e....",
        ".............",
        ".............",
    ),
    "pillars": (
        ".............",
        "..o.......o..",
        ".............",
        "....e.e.e....",
        ".............",
        "..o.......o..",
        ".............",
    ),
    "cross": (
        ".............",
        ".....ooo.....",
        ".....e.e.....",
        "..e..d.d..e..",
        ".....e.e.....",
        ".....ooo.....",
        ".............",
    ),
    "rocks": (
        "..d.......d..",
        "....o...o....",
        "..e..o.o..e..",
        "......e......",
        "..e..o.o..e..",
        "....o...o....",
        "..d.......d..",
    ),
    "spikes": (
        ".............",
        "..x.......x..",
        ".....eee.....",
        "..d.......d..",
        ".....eee.....",
        "..x.......x..",
        ".............",
    ),
    "arena": (
        ".............",
        "...e.....e...",
        "..o.......o..",
        ".....ooo.....",
        "..o.......o..",
        "...e.....e...",
        ".............",
    ),
    "corridor": (
        "..ooo...ooo..",
        ".............",
        "..e.......e..",
        "......e......",
        "..e.......e..",
        ".............",
        "..ooo...ooo..",
    ),
    "gap": (
        "..d..........",
        "....oo.oo....",
        "..e.......e..",
        "......e......",
        "..e.......e..",
        "....oo.oo....",
        "..........d..",
    ),
    "treasure": (
        ".............",
        ".............",
        "....ddddd....",
        "......p......",
        "....ddddd....",
        ".............",
        ".............",
    ),
    "shop": (
        ".............",
        ".............",
        "...p.p.p.p...",
        "....ddddd....",
        ".............",
        "......d......",
        ".............",
    ),
    "boss": (
        ".............",
        "..d.......d..",
        ".............",
        "......p......",
        ".............",
        "..d.......d..",
        ".............",
    ),
    "start": (
        ".............",
        ".............",
        ".....ddd.....",
        ".....d.d.....",
        ".....ddd.....",
        ".............",
        ".............",
    ),
}

NORMAL_TEMPLATES = ("empty", "pillars", "cross", "rocks", "spikes", "arena", "corridor", "gap")

SPECIAL_TEMPLATE = {
    "start": "start",
    "boss": "boss",
    "treasure": "treasure",
    "shop": "shop",
    "normal": None,
}

CHAR_KIND = {
    "o": "rock",
    "x": "fire",
    "e": "spawn",
    "d": "decor",
    "p": "pedestal",
}


def grid_to_cells(template: str):
    """产出 (col, row, kind) 列表，col/row 为房间格坐标（已 +1 偏移）。"""
    rows = TEMPLATES[template]
    for row, line in enumerate(rows):
        for col, char in enumerate(line):
            kind = CHAR_KIND.get(char)
            if kind:
                yield col + 1, row + 1, kind


def template_spawn_points(template: str):
    return [(c, r) for c, r, kind in grid_to_cells(template) if kind == "spawn"]
