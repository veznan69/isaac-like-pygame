# -*- coding: utf-8 -*-
"""更新上下文。

L1 纯逻辑模块。实体通过 ctx 拿到所需依赖，不持有 Game 实例，
既避免循环 import，也让 headless 测试可以用假 ctx 驱动实体逻辑。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from settings import STEP


@dataclass
class Context:
    bus: Any
    rng: Any
    room: Any = None
    game: Any = None
    painter: Any = None
    stats: Any = None
    dt: float = STEP
    floor: int = 1
    seed: str = ""
    frame: int = 0
    input: Any = None
    no_assets: bool = False
