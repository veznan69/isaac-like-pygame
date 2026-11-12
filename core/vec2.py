# -*- coding: utf-8 -*-
"""二维向量。

L0 模块：纯 Python 实现，不依赖 pygame，使 L0~L3 全部逻辑可在无显示环境下测试。
"""
from __future__ import annotations

import math

from settings import DIRS


class Vec2:
    __slots__ = ("x", "y")

    def __init__(self, x: float = 0.0, y: float = 0.0) -> None:
        self.x = float(x)
        self.y = float(y)

    @classmethod
    def from_dir(cls, name: str) -> "Vec2":
        dx, dy = DIRS[name]
        return cls(dx, dy)

    @classmethod
    def from_tuple(cls, pair) -> "Vec2":
        return cls(pair[0], pair[1])

    def copy(self) -> "Vec2":
        return Vec2(self.x, self.y)

    def __add__(self, other: "Vec2") -> "Vec2":
        return Vec2(self.x + other.x, self.y + other.y)

    def __sub__(self, other: "Vec2") -> "Vec2":
        return Vec2(self.x - other.x, self.y - other.y)

    def __mul__(self, k: float) -> "Vec2":
        return Vec2(self.x * k, self.y * k)

    __rmul__ = __mul__

    def __truediv__(self, k: float) -> "Vec2":
        return Vec2(self.x / k, self.y / k)

    def __neg__(self) -> "Vec2":
        return Vec2(-self.x, -self.y)

    def __iadd__(self, other: "Vec2") -> "Vec2":
        self.x += other.x
        self.y += other.y
        return self

    def __isub__(self, other: "Vec2") -> "Vec2":
        self.x -= other.x
        self.y -= other.y
        return self

    def __imul__(self, k: float) -> "Vec2":
        self.x *= k
        self.y *= k
        return self

    def __iter__(self):
        yield self.x
        yield self.y

    def __eq__(self, other) -> bool:
        return isinstance(other, Vec2) and self.x == other.x and self.y == other.y

    def __hash__(self) -> int:
        return hash((self.x, self.y))

    def __repr__(self) -> str:
        return f"Vec2({self.x:.2f}, {self.y:.2f})"

    def as_tuple(self) -> tuple[float, float]:
        return (self.x, self.y)

    def length_sq(self) -> float:
        return self.x * self.x + self.y * self.y

    def length(self) -> float:
        return math.hypot(self.x, self.y)

    def normalized(self) -> "Vec2":
        length = self.length()
        if length < 1e-9:
            return Vec2(0.0, 0.0)
        return Vec2(self.x / length, self.y / length)

    def with_length(self, length: float) -> "Vec2":
        return self.normalized() * length

    def clamp_magnitude(self, max_length: float) -> "Vec2":
        length = self.length()
        if length > max_length and length > 1e-9:
            return self * (max_length / length)
        return self.copy()

    def rotated(self, radians: float) -> "Vec2":
        c, s = math.cos(radians), math.sin(radians)
        return Vec2(self.x * c - self.y * s, self.x * s + self.y * c)

    def distance_to(self, other: "Vec2") -> float:
        return math.hypot(self.x - other.x, self.y - other.y)

    def lerp(self, other: "Vec2", t: float) -> "Vec2":
        return Vec2(self.x + (other.x - self.x) * t, self.y + (other.y - self.y) * t)
