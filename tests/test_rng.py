# -*- coding: utf-8 -*-
"""确定性与分层约束测试。"""
import re
import unittest

from core.rng import RNG, seed_to_u64, short_code
from settings import BASE_DIR

# 这些模块必须保持纯逻辑（不 import pygame、不用全局 random），
# 否则 headless 测试与种子复现都会失效。
PURE_MODULES = (
    "core/vec2.py", "core/rng.py", "core/events.py", "core/context.py",
    "core/collision.py", "core/save.py",
    "items/stats.py", "items/item_defs.py", "items/effects.py",
    "entities/base.py", "entities/prop.py", "entities/door.py",
    "entities/tear.py", "entities/pickup.py", "entities/player.py",
    "entities/enemies.py", "entities/boss.py",
    "world/room_templates.py", "world/dungeon.py", "world/room.py",
    "world/floor.py", "world/minimap.py",
)


class TestRNG(unittest.TestCase):
    def test_same_seed_same_sequence(self):
        a, b = RNG("ALPHA"), RNG("ALPHA")
        self.assertEqual([a.next_u32() for _ in range(1000)],
                         [b.next_u32() for _ in range(1000)])

    def test_different_seed_differs(self):
        a, b = RNG("ALPHA"), RNG("BETA")
        self.assertNotEqual([a.next_u32() for _ in range(20)],
                            [b.next_u32() for _ in range(20)])

    def test_seed_is_stable_integer(self):
        self.assertEqual(seed_to_u64("中文种子"), seed_to_u64("中文种子"))
        self.assertNotEqual(seed_to_u64("a"), seed_to_u64("b"))

    def test_fork_isolation(self):
        root = RNG("ROOT")
        a = root.fork("dungeon")
        b = root.fork("loot")
        baseline = [root.next_u32() for _ in range(10)]
        root2 = RNG("ROOT")
        root2.fork("dungeon").next_u32()
        root2.fork("loot").next_u32()
        self.assertEqual(baseline, [root2.next_u32() for _ in range(10)])
        self.assertNotEqual([a.next_u32() for _ in range(5)],
                            [b.next_u32() for _ in range(5)])

    def test_state_roundtrip(self):
        r = RNG("SNAP")
        for _ in range(17):
            r.next_u32()
        state = r.get_state()
        restored = RNG.from_state(state)
        self.assertEqual([r.next_u32() for _ in range(30)],
                         [restored.next_u32() for _ in range(30)])

    def test_weighted_and_shuffle_are_deterministic(self):
        a, b = RNG("W"), RNG("W")
        weights = {"a": 1, "b": 3, "c": 6}
        self.assertEqual([a.weighted(weights) for _ in range(50)],
                         [b.weighted(weights) for _ in range(50)])
        la, lb = list(range(30)), list(range(30))
        a.shuffle(la)
        b.shuffle(lb)
        self.assertEqual(la, lb)

    def test_short_code(self):
        self.assertEqual(short_code("X"), short_code("X"))
        self.assertEqual(len(short_code("X", 6)), 6)

    def test_pure_modules_have_no_pygame_or_global_random(self):
        pygame_pat = re.compile(r"^\s*(import pygame|from pygame\s+import)", re.M)
        random_pat = re.compile(r"^\s*(import random|from random\s+import)", re.M)
        for relative in PURE_MODULES:
            path = BASE_DIR / relative
            self.assertTrue(path.is_file(), f"缺少模块 {relative}")
            text = path.read_text(encoding="utf-8")
            self.assertIsNone(pygame_pat.search(text), f"{relative} 不应 import pygame")
            self.assertIsNone(random_pat.search(text), f"{relative} 不应使用全局 random")


if __name__ == "__main__":
    unittest.main()
