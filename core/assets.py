# -*- coding: utf-8 -*-
"""贴图仓库：按 key 取图并按尺寸缓存缩放结果。

关键性能约束：所有翻转/缩放只在首次取图时做一次并缓存，主循环内禁止 transform。
"""
from __future__ import annotations

import pygame

from core.sprite_sheet import SheetLibrary


class AssetBank:
    __slots__ = ("library", "_scaled", "no_assets")

    def __init__(self, no_assets: bool = False, library: SheetLibrary | None = None) -> None:
        self.no_assets = bool(no_assets)
        self.library = library if library is not None else (SheetLibrary() if not no_assets else None)
        self._scaled: dict[tuple, pygame.Surface | None] = {}

    @property
    def available(self) -> bool:
        return bool(self.library and self.library.available)

    def get(self, key: str, width: float, height: float) -> pygame.Surface | None:
        if self.no_assets or not self.library or not key:
            return None
        w, h = max(2, int(round(width))), max(2, int(round(height)))
        cache_key = (key, w, h)
        if cache_key in self._scaled:
            return self._scaled[cache_key]
        source = self.library.get(key)
        if source is None:
            self._scaled[cache_key] = None
            return None
        if source.get_size() == (w, h):
            result = source
        else:
            # 像素素材用最近邻缩放，避免平滑导致边缘发灰
            result = pygame.transform.scale(source, (w, h))
        self._scaled[cache_key] = result
        return result

    @property
    def missing_keys(self) -> tuple[str, ...]:
        return self.library.missing_keys if self.library else ()
