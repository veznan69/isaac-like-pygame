# -*- coding: utf-8 -*-
"""道具数值：顺序无关、clamp、flags、资源效果与抽取复现。"""
import unittest
from types import SimpleNamespace

from core.events import EventBus
from core.rng import RNG
from entities.player import Player
from items.effects import apply_item, available, price_of, roll_items
from items.item_defs import ALL_ITEM_IDS, ITEMS
from items.stats import BASE, CLAMPS, Stats
from settings import INPUT_KEYBOARD


def make_ctx():
    return SimpleNamespace(bus=EventBus())


class TestStats(unittest.TestCase):
    def test_add_and_multiply_defaults(self):
        stats = Stats()
        for key in BASE:
            self.assertAlmostEqual(stats.value(key), BASE[key])

    def test_order_independent(self):
        a, b = Stats(), Stats()
        mods_a = {"add": {"damage": 2, "move_speed": 20}, "mul": {"damage": 1.5}}
        mods_b = {"add": {"tear_delay": -3}, "mul": {"shot_speed": 1.2}}
        a.apply(mods_a)
        a.apply(mods_b)
        b.apply(mods_b)
        b.apply(mods_a)
        self.assertEqual(a.as_dict(), b.as_dict())

    def test_clamps(self):
        stats = Stats()
        stats.add("damage", 9999)
        stats.add("tear_delay", -9999)
        self.assertEqual(stats.value("damage"), CLAMPS["damage"][1])
        self.assertEqual(stats.value("tear_delay"), CLAMPS["tear_delay"][0])

    def test_flags(self):
        stats = Stats()
        self.assertFalse(stats.get_flag("piercing"))
        stats.set_flag("piercing")
        self.assertTrue(stats.get_flag("piercing"))

    def test_snapshot_roundtrip(self):
        stats = Stats()
        stats.add("damage", 4)
        stats.set_flag("homing")
        restored = Stats()
        restored.restore(stats.snapshot())
        self.assertEqual(stats.as_dict(), restored.as_dict())
        self.assertTrue(restored.get_flag("homing"))


class TestItems(unittest.TestCase):
    def test_every_item_has_required_fields(self):
        for item_id, item in ITEMS.items():
            self.assertIn("name", item)
            self.assertIn("desc", item)
            self.assertIn("rarity", item)
            self.assertGreater(price_of(item_id), 0)

    def test_apply_item_changes_stats_and_resources(self):
        player, ctx = Player(), make_ctx()
        before = player.stats.value("damage")
        self.assertTrue(apply_item(player, "pencil", ctx))
        self.assertAlmostEqual(player.stats.value("damage"), before + 1.5)
        self.assertIn("pencil", player.collected)

        player2 = Player()
        apply_item(player2, "health_up", ctx)
        self.assertEqual(player2.max_hp, 8.0)
        apply_item(player2, "coin_bag", ctx)
        self.assertEqual(player2.coins, 8)

    def test_duplicate_item_is_rejected(self):
        player, ctx = Player(), make_ctx()
        self.assertTrue(apply_item(player, "cupid", ctx))
        self.assertFalse(apply_item(player, "cupid", ctx))
        self.assertEqual(player.collected.count("cupid"), 1)

    def test_flags_from_item(self):
        player, ctx = Player(), make_ctx()
        apply_item(player, "cupid", ctx)
        self.assertTrue(player.stats.get_flag("piercing"))

    def test_roll_is_reproducible_and_excludes_owned(self):
        owned = ["pencil", "cupid"]
        a = roll_items(RNG("ROLL").fork("x"), owned, 5)
        b = roll_items(RNG("ROLL").fork("x"), owned, 5)
        self.assertEqual(a, b)
        self.assertEqual(len(a), len(set(a)))
        self.assertFalse(set(a) & set(owned))
        self.assertTrue(set(a).issubset(set(ALL_ITEM_IDS)))

    def test_available_excludes_owned(self):
        self.assertNotIn("pencil", available(["pencil"]))


if __name__ == "__main__":
    unittest.main()
