# -*- coding: utf-8 -*-
"""sprite sheet 解析与切帧。

sheets.json  : {"chars": {"file":"chars.png","cell":[32,32],"cols":4,"rows":4}}
manifest.json: {"player_idle": {"sheet":"chars","index":0,"flip":false}}

渲染层模块（import pygame）。文件缺失时返回空库，供占位模式正常运行。
"""
from __future__ import annotations

import json
from pathlib import Path

import pygame

from settings import SHEETS_FILE, MANIFEST_FILE, SPRITES_DIR


class Sheet:
    __slots__ = ("name", "path", "cell_w", "cell_h", "cols", "rows", "surface")

    def __init__(self, name: str, info: dict, base_dir: Path) -> None:
        self.name = name
        self.path = base_dir / info["file"]
        self.cell_w, self.cell_h = int(info["cell"][0]), int(info["cell"][1])
        self.cols, self.rows = int(info["cols"]), int(info["rows"])
        self.surface: pygame.Surface | None = None

    def load(self) -> bool:
        if self.surface is not None:
            return True
        if not self.path.is_file():
            return False
        try:
            self.surface = pygame.image.load(str(self.path)).convert_alpha()
            return True
        except (pygame.error, OSError) as exc:
            print(f"[sheet] 无法加载 {self.path.name}: {exc}")
            return False

    def get(self, index: int) -> pygame.Surface | None:
        if not self.load() or index < 0 or index >= self.cols * self.rows:
            return None
        col, row = index % self.cols, index // self.cols
        return self.surface.subsurface(pygame.Rect(col * self.cell_w, row * self.cell_h,
                                                  self.cell_w, self.cell_h))


class SheetLibrary:
    def __init__(self, sheets_file: Path | None = None,
                 manifest_file: Path | None = None,
                 sprites_dir: Path | None = None) -> None:
        self.sheets: dict[str, Sheet] = {}
        self.manifest: dict[str, dict] = {}
        self._cache: dict[str, pygame.Surface] = {}
        self._missing: set[str] = set()
        sheets_file = sheets_file or SHEETS_FILE
        manifest_file = manifest_file or MANIFEST_FILE
        sprites_dir = sprites_dir or SPRITES_DIR
        try:
            sheets_data = json.loads(sheets_file.read_text(encoding="utf-8"))
            manifest_data = json.loads(manifest_file.read_text(encoding="utf-8"))
            if not isinstance(sheets_data, dict) or not isinstance(manifest_data, dict):
                raise ValueError("metadata root must be object")
            for name, info in sorted(sheets_data.items()):
                self.sheets[name] = Sheet(name, info, sprites_dir)
            self.manifest = manifest_data
        except (OSError, ValueError, TypeError, json.JSONDecodeError, KeyError) as exc:
            print(f"[sheet] 素材元数据不可用，启用几何占位模式：{exc}")
            self.sheets = {}
            self.manifest = {}

    @property
    def available(self) -> bool:
        return bool(self.manifest)

    def get(self, key: str) -> pygame.Surface | None:
        if key in self._cache:
            return self._cache[key]
        if key in self._missing:
            return None
        entry = self.manifest.get(key)
        if not entry:
            self._missing.add(key)
            return None
        sheet = self.sheets.get(entry.get("sheet", ""))
        surface = sheet.get(int(entry.get("index", 0))) if sheet else None
        if surface is None:
            self._missing.add(key)
            return None
        if entry.get("flip"):
            surface = pygame.transform.flip(surface, True, False)
        self._cache[key] = surface
        return surface

    @property
    def missing_keys(self) -> tuple[str, ...]:
        return tuple(sorted(self._missing))
