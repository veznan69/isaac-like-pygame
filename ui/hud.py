# -*- coding: utf-8 -*-
"""游戏内 HUD：心容器、资源、层号、道具、Boss 血条、提示与调试信息。"""
from __future__ import annotations

from typing import Any

from core.rng import short_code
from items.item_defs import ITEMS
from settings import PALETTE, COL_HUD_BG, MAX_FLOOR


def _heart(painter, x: float, y: float, fill: float) -> None:
    """fill: 0 空 / 0.5 半心 / 1.0 全心。"""
    painter.circle(PALETTE["ink"], x - 3, y - 2, 5)
    painter.circle(PALETTE["ink"], x + 3, y - 2, 5)
    painter.rect(PALETTE["ink"], x - 7, y - 2, 14, 8)
    if fill <= 0:
        color = PALETTE["slate"]
    else:
        color = PALETTE["red"]
    if fill >= 1.0:
        painter.circle(color, x - 3, y - 2, 3.6)
        painter.circle(color, x + 3, y - 2, 3.6)
        painter.rect(color, x - 6, y - 2, 12, 6)
        painter.circle(PALETTE["white"], x - 3, y - 3, 1.2)
    elif fill > 0:
        painter.circle(color, x - 3, y - 2, 3.6)
        painter.rect(color, x - 6, y - 2, 6, 6)


def _resource(painter, x: float, y: float, color, value: int, label: str) -> None:
    painter.circle(color, x, y, 4)
    painter.outline(PALETTE["ink"], x - 5, y - 5, 10, 10, 1)
    painter.text(f"{label}{value}", x + 8, y - 6, 10, PALETTE["white"])


def draw(painter: Any, game) -> None:
    player = game.player
    if player is None:
        return

    # 左上信息板：半透明底，不与房间地板抢对比度
    painter.alpha_rect(COL_HUD_BG, 190, 4, 4, 168, 62)
    containers = int((player.max_hp + 1) // 2)
    for i in range(min(containers, 8)):
        fill = max(0.0, min(1.0, (player.hp - i * 2.0) / 2.0))
        _heart(painter, 16 + i * 17, 16, fill)
    if containers > 8:
        painter.text(f"+{containers - 8}", 16 + 8 * 17, 10, 10, PALETTE["white"])

    y = 32
    _resource(painter, 16, y + 4, PALETTE["gold"], player.coins, "")
    _resource(painter, 70, y + 4, PALETTE["light"], player.keys, "")
    _resource(painter, 124, y + 4, PALETTE["slate"], player.bombs, "")

    painter.text(f"第 {game.floor_number} / {MAX_FLOOR} 层", 8, 52, 11, PALETTE["gold"])
    painter.text(f"种子 {short_code(game.seed, 6)}", 8, 68, 9, PALETTE["gray"])
    if player.collected:
        painter.text(f"道具 {len(player.collected)}", 148, 52, 10, PALETTE["cyan"])
        names = " ".join(ITEMS[i]["name"] for i in player.collected[:3] if i in ITEMS)
        painter.text(names[:16], 148, 64, 8, PALETTE["light"])

    # Boss 血条置顶居中
    boss = game.current_boss
    if boss and boss.alive:
        width = 220
        x, y = (480 - width) / 2, 12
        painter.alpha_rect(COL_HUD_BG, 210, x - 4, y - 4, width + 8, 18)
        painter.rect(PALETTE["ink"], x, y, width, 8)
        painter.rect(PALETTE["red"], x, y, width * max(0.0, boss.hp / boss.max_hp), 8)
        painter.text(f"BOSS  阶段 {boss.phase}", 240, y + 10, 9,
                     PALETTE["white"], anchor="midtop")

    # 短提示（拾取道具、硬币不足等）
    for index, (text, life) in enumerate(game.toasts[:3]):
        alpha = int(255 * min(1.0, life / 0.35))
        painter.text(text, 240, 218 + index * 14, 12,
                     PALETTE["gold"], anchor="center", alpha=alpha)

    if game.debug:
        painter.alpha_rect(COL_HUD_BG, 200, 4, 250, 220, 34)
        painter.text(f"FPS {game.display_fps:.0f} | 实体 {game.entity_count} | 帧 {game.frame}",
                     8, 254, 9, PALETTE["cyan"])
        painter.text(f"房间 {game.floor.current_pos if game.floor else '-'} | {game.input.mode}",
                     8, 268, 9, PALETTE["cyan"])
