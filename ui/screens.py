# -*- coding: utf-8 -*-
"""标题、暂停、道具三选一、死亡与通关界面。"""
from __future__ import annotations

from typing import Any

from items.item_defs import ITEMS
from settings import INPUT_KEYBOARD, LOGICAL_H, LOGICAL_W, MAX_FLOOR, PALETTE

TITLE = "泪之地牢"
SUBTITLE = "TEARS OF THE DUNGEON"


def _panel(painter: Any, x: int, y: int, w: int, h: int) -> None:
    painter.alpha_rect((16, 13, 26), 235, x, y, w, h)
    painter.outline(PALETTE["slate"], x, y, w, h, 2)
    painter.outline(PALETTE["dark"], x + 3, y + 3, w - 6, h - 6, 1)


def draw_title(painter: Any, game) -> None:
    painter.rect((14, 12, 22), 0, 0, LOGICAL_W, LOGICAL_H)
    for i in range(0, LOGICAL_W, 32):
        painter.rect((20, 17, 30), i, 0, 16, 16)
        painter.rect((20, 17, 30), i + 16, LOGICAL_H - 16, 16, 16)

    painter.text(TITLE, 240, 46, 34, PALETTE["gold"], anchor="center")
    painter.text(SUBTITLE, 240, 74, 11, PALETTE["gray"], anchor="center")

    _panel(painter, 90, 96, 300, 118)
    painter.text("输入种子（留空则随机）", 240, 104, 11, PALETTE["light"], anchor="midtop")
    box_x, box_y, box_w, box_h = 130, 122, 220, 24
    painter.rect(PALETTE["ink"], box_x, box_y, box_w, box_h)
    painter.outline(PALETTE["gold"], box_x, box_y, box_w, box_h, 1)
    shown = game.seed_text or ""
    cursor = "|" if (game.frame // 30) % 2 == 0 else ""
    painter.text(shown[-22:] + cursor, box_x + 6, box_y + 5, 13, PALETTE["white"])

    mode = game.input.mode
    mode_name = "WASD + 方向键" if mode == INPUT_KEYBOARD else "WASD + 鼠标瞄准"
    painter.text(f"操作模式：{mode_name}   [Tab] 切换", 240, 152, 11,
                 PALETTE["cyan"], anchor="center")
    painter.text("[Enter] 开始冒险        [F1] 显示调试信息", 240, 170, 11,
                 PALETTE["white"], anchor="center")

    best = game.save_data.get("best", {})
    painter.text(f"历史最佳：第 {best.get('floor', 0)} 层 · 击杀 {best.get('kills', 0)} · "
                 f"通关 {best.get('wins', 0)} 次", 240, 190, 10,
                 PALETTE["gray"], anchor="center")

    painter.text("WASD 移动 · 方向键/鼠标 射击 · E 交互 · Q 炸弹", 240, 236, 10,
                 PALETTE["light"], anchor="center")
    painter.text(f"ESC 暂停 · 打穿 {MAX_FLOOR} 层 Boss 即通关", 240, 252, 10,
                 PALETTE["gray"], anchor="center")
    painter.text("Python + pygame · 确定性种子地牢", 240, 274, 9,
                 PALETTE["slate"], anchor="center")


def draw_paused(painter: Any, game) -> None:
    painter.alpha_rect((8, 6, 14), 200, 0, 0, LOGICAL_W, LOGICAL_H)
    _panel(painter, 120, 76, 240, 136)
    painter.text("暂停", 240, 88, 26, PALETTE["gold"], anchor="midtop")
    lines = (
        "[ESC / P] 继续游戏",
        f"[Tab] 切换操作模式（当前：{game.input.mode}）",
        "[R] 用同一种子重开",
        "[T] 返回标题",
    )
    for index, line in enumerate(lines):
        painter.text(line, 240, 132 + index * 18, 12, PALETTE["white"], anchor="center")
    painter.text(f"种子：{game.seed}", 240, 194, 9, PALETTE["gray"], anchor="center")


def draw_item_select(painter: Any, game) -> None:
    painter.alpha_rect((8, 6, 14), 205, 0, 0, LOGICAL_W, LOGICAL_H)
    _panel(painter, 40, 54, 400, 186)
    painter.text("宝箱开启！选择一件道具", 240, 64, 16, PALETTE["gold"], anchor="midtop")
    choices = game.item_choices
    if not choices:
        painter.text("（没有可选道具）", 240, 130, 12, PALETTE["gray"], anchor="center")
    for index, item_id in enumerate(choices):
        x = 56 + index * 132
        active = index == game.item_index
        painter.rect(PALETTE["ink"], x, 96, 116, 104)
        painter.outline(PALETTE["gold"] if active else PALETTE["slate"],
                        x, 96, 116, 104, 2 if active else 1)
        painter.sprite(f"item_{item_id}", x + 58, 128, 36, 36, PALETTE["cyan"])
        info = ITEMS.get(item_id, {"name": item_id, "desc": ""})
        painter.text(info["name"], x + 58, 154, 12,
                     PALETTE["gold"] if active else PALETTE["white"], anchor="center")
        desc = info["desc"]
        painter.text(desc[:10], x + 58, 174, 9, PALETTE["light"], anchor="center")
        if len(desc) > 10:
            painter.text(desc[10:20], x + 58, 186, 9, PALETTE["light"], anchor="center")
    painter.text("[← →] 选择    [E / Enter] 确认    [ESC] 稍后再说", 240, 218, 11,
                 PALETTE["white"], anchor="center")


def draw_end(painter: Any, game, won: bool) -> None:
    painter.alpha_rect((8, 6, 14), 215, 0, 0, LOGICAL_W, LOGICAL_H)
    _panel(painter, 96, 58, 288, 178)
    title = "通关！" if won else "你死了"
    color = PALETTE["gold"] if won else PALETTE["red"]
    painter.text(title, 240, 72, 30, color, anchor="midtop")
    subtitle = "地牢的尽头，眼泪终于停了。" if won else "地牢又多了一个名字。"
    painter.text(subtitle, 240, 110, 11, PALETTE["light"], anchor="center")

    best = game.save_data.get("best", {})
    rows = (
        f"到达层数   第 {game.floor_number} / {MAX_FLOOR} 层",
        f"击杀敌人   {game.player.kills if game.player else 0}",
        f"收集道具   {len(game.player.collected) if game.player else 0}",
        f"用时       {game.elapsed:.1f} 秒",
        f"种子       {game.seed[:16]}",
        f"历史最深   第 {best.get('floor', 0)} 层 · 通关 {best.get('wins', 0)} 次",
    )
    for index, row in enumerate(rows):
        painter.text(row, 132, 132 + index * 15, 11, PALETTE["white"])

    painter.text("[R] 用同种子重开    [T] 返回标题", 240, 216, 11,
                 PALETTE["cyan"], anchor="center")
