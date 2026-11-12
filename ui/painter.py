# -*- coding: utf-8 -*-
"""绘制抽象层。

实体与房间只认识 painter 的方法，不直接碰 pygame；这样同一套逻辑既能画到窗口，
也能在 headless 测试里用 MockPainter 驱动。缺素材时 painter 自动画几何占位。
"""
from __future__ import annotations

import pygame

from settings import PALETTE
from ui import fonts


class Painter:
    __slots__ = ("surface", "bank", "no_assets", "debug")

    def __init__(self, surface, bank=None, no_assets: bool = False) -> None:
        self.surface = surface
        self.bank = bank
        self.no_assets = bool(no_assets)
        self.debug = False

    def rect(self, color, x, y, w, h) -> None:
        pygame.draw.rect(self.surface, tuple(color),
                         (int(x), int(y), max(1, int(w)), max(1, int(h))))

    def outline(self, color, x, y, w, h, width: int = 1) -> None:
        pygame.draw.rect(self.surface, tuple(color),
                         (int(x), int(y), max(1, int(w)), max(1, int(h))), max(1, int(width)))

    def circle(self, color, cx, cy, r) -> None:
        pygame.draw.circle(self.surface, tuple(color),
                           (int(round(cx)), int(round(cy))), max(1, int(round(r))))

    def line(self, color, x1, y1, x2, y2, width: int = 1) -> None:
        pygame.draw.line(self.surface, tuple(color),
                         (int(x1), int(y1)), (int(x2), int(y2)), max(1, int(width)))

    def alpha_rect(self, color, alpha: int, x, y, w, h) -> None:
        w, h = max(1, int(w)), max(1, int(h))
        layer = pygame.Surface((w, h), pygame.SRCALPHA)
        layer.fill((color[0], color[1], color[2], max(0, min(255, int(alpha)))))
        self.surface.blit(layer, (int(x), int(y)))

    def text(self, text, x, y, size: int = 12, color=None,
             anchor: str = "topleft", alpha: int = 255) -> None:
        color = color or PALETTE["white"]
        surface = fonts.render(str(text), size, color, alpha)
        w, h = surface.get_size()
        px = {"topleft": x, "center": x - w / 2, "midtop": x - w / 2,
              "topright": x - w}.get(anchor, x)
        py = {"topleft": y, "center": y - h / 2, "midtop": y,
              "topright": y}.get(anchor, y)
        self.surface.blit(surface, (int(px), int(py)))

    def sprite(self, key, cx, cy, w, h, fallback_color=None) -> None:
        w, h = max(2.0, float(w)), max(2.0, float(h))
        surface = None if self.no_assets or self.bank is None else self.bank.get(key, w, h)
        if surface is not None:
            self.surface.blit(surface, (int(round(cx - w / 2)), int(round(cy - h / 2))))
            return
        self._fallback(key, cx, cy, w, h, fallback_color or PALETTE["gray"])

    def _fallback(self, key, cx, cy, w, h, color) -> None:
        """无素材时的几何替身，形状按用途区分，保证占位模式也能看懂画面。"""
        left, top = cx - w / 2, cy - h / 2
        if key and key.startswith("prop_"):
            self.rect(color, left, top, w, h)
            self.outline(PALETTE["ink"], left, top, w, h, 2)
            self.rect(PALETTE["light"], left + 3, top + 3, max(2, w * 0.3), 3)
        elif key and (key.startswith("pickup_") or key.startswith("item_")):
            self.rect(PALETTE["ink"], left - 1, top - 1, w + 2, h + 2)
            self.rect(color, left, top, w, h)
            self.circle(PALETTE["white"], cx - w * 0.18, cy - h * 0.18, max(1, w * 0.13))
        else:
            radius = min(w, h) / 2
            self.circle(PALETTE["ink"], cx, cy, radius + 1)
            self.circle(color, cx, cy, radius)
            self.circle(PALETTE["white"], cx - radius * 0.3, cy - radius * 0.3,
                        max(1, radius * 0.22))
