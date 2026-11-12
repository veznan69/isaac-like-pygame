# -*- coding: utf-8 -*-
"""确定性随机数。

L0 模块。全工程唯一的随机来源，禁止任何模块调用全局 random。
使用 splitmix64 自实现，避免依赖平台随机实现，保证同种子跨进程、跨版本完全一致。
种子派生用 sha256 而非内置 hash()（后者跨进程随机化，会破坏复现）。
"""
from __future__ import annotations

import hashlib

MASK64 = (1 << 64) - 1
GAMMA = 0x9E3779B97F4A7C15


def seed_to_u64(seed) -> int:
    """把任意可打印种子稳定映射为 64 位整数。"""
    raw = str(seed).encode("utf-8")
    return int.from_bytes(hashlib.sha256(raw).digest()[:8], "big")


class RNG:
    """可派生、可快照的伪随机数发生器。"""

    __slots__ = ("_label", "_state", "_initial")

    def __init__(self, seed="", *, _state: int | None = None) -> None:
        self._label = str(seed)
        self._initial = seed_to_u64(seed)
        self._state = self._initial if _state is None else _state & MASK64

    @property
    def label(self) -> str:
        return self._label

    @property
    def state(self) -> int:
        return self._state

    def get_state(self) -> dict:
        """供存档快照使用。"""
        return {"label": self._label, "initial": self._initial, "state": self._state}

    @classmethod
    def from_state(cls, data: dict) -> "RNG":
        obj = cls(data.get("label", ""), _state=int(data.get("state", 0)))
        obj._initial = int(data.get("initial", obj._initial))
        return obj

    def fork(self, namespace: str) -> "RNG":
        """派生独立子随机器，不影响自身序列，也不受调用顺序影响。

        地牢/房间/掉落/AI 各用独立命名空间，避免"多打一只怪就改变地图"的串扰。
        """
        return RNG(f"{self._label}/{namespace}")

    def _next_u64(self) -> int:
        self._state = (self._state + GAMMA) & MASK64
        z = self._state
        z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & MASK64
        z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & MASK64
        return (z ^ (z >> 31)) & MASK64

    def next_u32(self) -> int:
        return self._next_u64() >> 32

    def random(self) -> float:
        """[0, 1) 浮点。"""
        return (self._next_u64() >> 11) * (1.0 / (1 << 53))

    def uniform(self, a: float, b: float) -> float:
        return a + (b - a) * self.random()

    def randint(self, a: int, b: int) -> int:
        """闭区间 [a, b]。"""
        if b < a:
            raise ValueError("randint: b < a")
        return a + (self._next_u64() % (b - a + 1))

    def chance(self, p: float) -> bool:
        return self.random() < p

    def choice(self, seq):
        if not seq:
            raise IndexError("choice from empty sequence")
        return seq[self._next_u64() % len(seq)]

    def sample(self, seq, k: int) -> list:
        """不重复抽样，返回新列表，不改变输入。"""
        pool = list(seq)
        if k > len(pool):
            k = len(pool)
        for i in range(k):
            j = i + (self._next_u64() % (len(pool) - i))
            pool[i], pool[j] = pool[j], pool[i]
        return pool[:k]

    def shuffle(self, seq: list) -> None:
        """原地 Fisher-Yates。"""
        for i in range(len(seq) - 1, 0, -1):
            j = self._next_u64() % (i + 1)
            seq[i], seq[j] = seq[j], seq[i]

    def weighted(self, weights: dict):
        """按权重抽取一个 key，权重必须为非负数。"""
        items = [(k, float(v)) for k, v in weights.items() if v > 0]
        total = sum(w for _, w in items)
        if total <= 0:
            raise ValueError("weighted: all weights are zero")
        roll = self.random() * total
        acc = 0.0
        for key, weight in items:
            acc += weight
            if roll < acc:
                return key
        return items[-1][0]

    def sign(self) -> int:
        return 1 if self._next_u64() & 1 else -1

    def angle(self) -> float:
        import math
        return self.random() * math.tau


def short_code(seed: str, length: int = 8) -> str:
    """HUD 上显示的种子短码。"""
    return hashlib.sha256(str(seed).encode("utf-8")).hexdigest()[:length].upper()
