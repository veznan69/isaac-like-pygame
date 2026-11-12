# -*- coding: utf-8 -*-
"""中文字体降级链与文字表面缓存。

Windows 优先使用系统内微软雅黑/黑体；找不到时退到 pygame 内置字体。
业务代码一律通过这里取文字，禁止直接调用 font.render，避免中文乱码散落各处。
"""
from __future__ import annotations

import os

import pygame

from settings import FONT_CANDIDATES

_SYSTEM_PATHS = (
    "C:/Windows/Fonts/msyh.ttc",
    "C:/Windows/Fonts/msyhbd.ttc",
    "C:/Windows/Fonts/simhei.ttf",
    "C:/Windows/Fonts/simsun.ttc",
)

_font_cache: dict[int, pygame.font.Font] = {}
_text_cache: dict[tuple, pygame.Surface] = {}
_font_path: str | None = None


def _resolve_font_path() -> str | None:
    global _font_path
    if _font_path is not None:
        return _font_path or None
    for path in _SYSTEM_PATHS:
        if os.path.isfile(path):
            _font_path = path
            return path
    for name in FONT_CANDIDATES:
        try:
            matched = pygame.font.match_font(name)
        except Exception:
            matched = None
        if matched:
            _font_path = matched
            return matched
    _font_path = ""
    return None


def font(size: int) -> pygame.font.Font:
    size = max(8, int(size))
    if size not in _font_cache:
        path = _resolve_font_path()
        try:
            _font_cache[size] = pygame.font.Font(path, size) if path else pygame.font.Font(None, size)
        except (OSError, ValueError):
            _font_cache[size] = pygame.font.Font(None, size)
    return _font_cache[size]


def render(text: str, size: int, color, alpha: int = 255) -> pygame.Surface:
    key = (str(text), int(size), tuple(color), int(alpha))
    hit = _text_cache.get(key)
    if hit is None:
        surface = font(size).render(str(text), True, tuple(color))
        if alpha < 255:
            surface.set_alpha(max(0, min(255, alpha)))
        # 缓存上限，避免道具名/提示语无限增长
        if len(_text_cache) > 600:
            _text_cache.clear()
        _text_cache[key] = surface
        hit = surface
    return hit


def measure(text: str, size: int) -> tuple[int, int]:
    return font(size).size(str(text))


def clear_cache() -> None:
    _text_cache.clear()
    _font_cache.clear()
