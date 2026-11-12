# -*- coding: utf-8 -*-
"""地牢生成：连通性、特殊房、门互补、种子复现。"""
import unittest

from core.rng import RNG
from settings import DIRS, MAX_FLOOR, OPPOSITE, RoomType
from world.dungeon import Dungeon, bfs_dist, build_adj, direction


class TestDungeon(unittest.TestCase):
    def test_600_dungeons_connected_and_reproducible(self):
        count = 0
        for i in range(100):
            seed = f"SEED-{i}"
            for floor in range(1, MAX_FLOOR + 1):
                a = Dungeon(floor, RNG(seed))
                b = Dungeon(floor, RNG(seed))
                self.assertEqual(a.signature(), b.signature(),
                                 f"种子 {seed} 第 {floor} 层不可复现")
                adj = build_adj(a.cells, a.links)
                dist = bfs_dist(adj, a.start_pos)
                self.assertEqual(len(dist), len(a.cells), "存在不可达房间")
                self.assertEqual(len(adj[a.boss_pos]), 1, "Boss 房度数必须为 1")
                self.assertGreaterEqual(dist[a.boss_pos], 3, "Boss 房离起点太近")
                count += 1
        self.assertEqual(count, 100 * MAX_FLOOR)

    def test_door_directions_are_complementary(self):
        for i in range(25):
            dungeon = Dungeon(3, RNG(f"DOOR-{i}"))
            for a, b in sorted(dungeon.links):
                name = direction(a, b)
                self.assertIn(name, dungeon.plan(a).doors)
                self.assertIn(OPPOSITE[name], dungeon.plan(b).doors)
                dx, dy = DIRS[name]
                self.assertEqual((a[0] + dx, a[1] + dy), b)

    def test_exactly_one_boss_and_at_most_one_treasure(self):
        for i in range(30):
            dungeon = Dungeon(4, RNG(f"TYPE-{i}"))
            types = [p.rtype for p in dungeon.plans.values()]
            self.assertEqual(types.count(RoomType.BOSS.value), 1)
            self.assertLessEqual(types.count(RoomType.TREASURE.value), 1)
            self.assertEqual(types.count(RoomType.START.value), 1)
            self.assertEqual(dungeon.plan(dungeon.start_pos).rtype, RoomType.START.value)

    def test_different_seeds_produce_different_layouts(self):
        sigs = {Dungeon(2, RNG(f"D-{i}")).signature() for i in range(20)}
        self.assertGreater(len(sigs), 15)

    def test_room_count_and_difficulty_grow_with_floor(self):
        counts = [len(Dungeon(f, RNG("SIZE")).plans) for f in range(1, MAX_FLOOR + 1)]
        self.assertEqual(counts, sorted(counts))
        self.assertEqual(counts[0], 12)
        self.assertEqual(counts[-1], 20)

    def test_templates_are_valid(self):
        from world.room_templates import TEMPLATES
        for name, rows in TEMPLATES.items():
            self.assertEqual(len(rows), 7, name)
            for row in rows:
                self.assertEqual(len(row), 13, name)


if __name__ == "__main__":
    unittest.main()
