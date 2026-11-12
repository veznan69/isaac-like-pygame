# -*- coding: utf-8 -*-
"""地牢蓝图生成：生长式扩展、显式连接、特殊房分配与硬断言。

L3 纯逻辑模块，不 import pygame，也不依赖实体类，可直接做 headless 测试。

复现要点：
  1. 所有集合/字典迭代一律先 sorted，不依赖 set 的哈希迭代顺序；
  2. 全部随机取自显式 fork 出的 RNG，不调用全局 random；
  3. links 显式存储"哪两个相邻房间之间真的有门"，不用空间相邻隐式推导。
"""
from __future__ import annotations

import hashlib
from collections import deque
from dataclasses import dataclass

from settings import DIRS, DIR_ORDER, OPPOSITE, RoomType, floor_difficulty, room_count
from world.room_templates import NORMAL_TEMPLATES, SPECIAL_TEMPLATE


def edge(a, b) -> tuple:
    return tuple(sorted((a, b)))


def direction(a, b) -> str:
    dx, dy = b[0] - a[0], b[1] - a[1]
    for name, (ddx, ddy) in DIRS.items():
        if (dx, dy) == (ddx, ddy):
            return name
    raise ValueError(f"rooms are not adjacent: {a} -> {b}")


def build_adj(cells, links) -> dict:
    adj = {pos: set() for pos in cells}
    for a, b in sorted(links):
        adj[a].add(b)
        adj[b].add(a)
    return adj


def bfs_dist(adj, start) -> dict:
    dist = {start: 0}
    queue = deque([start])
    while queue:
        node = queue.popleft()
        for nxt in sorted(adj[node]):
            if nxt not in dist:
                dist[nxt] = dist[node] + 1
                queue.append(nxt)
    return dist


@dataclass(frozen=True)
class RoomPlan:
    gx: int
    gy: int
    rtype: str
    doors: tuple[str, ...]
    template: str
    dist: int

    @property
    def pos(self) -> tuple[int, int]:
        return (self.gx, self.gy)

    def signature(self) -> str:
        return f"{self.gx},{self.gy}:{self.rtype}:{''.join(sorted(self.doors))}:{self.template}:{self.dist}"


class Dungeon:
    """一层的房间图。"""

    def __init__(self, floor: int, rng, room_total: int | None = None) -> None:
        self.floor = int(floor)
        self.rng = rng.fork(f"dungeon:floor{self.floor}")
        self.target = int(room_total or room_count(self.floor))
        self.cells: set = set()
        self.links: set = set()
        self.plans: dict = {}
        self.start_pos = (0, 0)
        self.boss_pos = (0, 0)
        self.treasure_pos: tuple | None = None
        self.shop_pos: tuple | None = None
        self.difficulty = floor_difficulty(self.floor)
        self.generate()

    def _grow(self) -> None:
        """随机前沿扩展；限制新格与已有格最多相邻 1 个，确保初始连接是一棵生成树。"""
        self.cells = {(0, 0)}
        self.links = set()
        guard = 0
        while len(self.cells) < self.target and guard < 4000:
            guard += 1
            candidates = []
            for pos in sorted(self.cells):
                for d in DIR_ORDER:
                    dx, dy = DIRS[d]
                    nxt = (pos[0] + dx, pos[1] + dy)
                    if nxt in self.cells or abs(nxt[0]) > 7 or abs(nxt[1]) > 7:
                        continue
                    adjacent = sum(
                        1 for d2 in DIR_ORDER
                        if (nxt[0] + DIRS[d2][0], nxt[1] + DIRS[d2][1]) in self.cells
                    )
                    if adjacent > 1:
                        continue
                    candidates.append((pos, nxt))
            if not candidates:
                break
            parent, nxt = self.rng.choice(candidates)
            self.cells.add(nxt)
            self.links.add(edge(parent, nxt))

    def _ensure_depth(self) -> None:
        """保证存在距离 >= 3 的远端房间，供 Boss 房使用。"""
        adj = build_adj(self.cells, self.links)
        dist = bfs_dist(adj, self.start_pos)
        guard = 0
        while max(dist.values()) < 3 and len(self.cells) < self.target + 6 and guard < 40:
            guard += 1
            tip = max(sorted(self.cells), key=lambda p: (dist[p], p))
            options = []
            for d in DIR_ORDER:
                dx, dy = DIRS[d]
                nxt = (tip[0] + dx, tip[1] + dy)
                if nxt in self.cells or abs(nxt[0]) > 7 or abs(nxt[1]) > 7:
                    continue
                adjacent = sum(
                    1 for d2 in DIR_ORDER
                    if (nxt[0] + DIRS[d2][0], nxt[1] + DIRS[d2][1]) in self.cells
                )
                if adjacent == 1:
                    options.append(nxt)
            if not options:
                break
            nxt = self.rng.choice(sorted(options))
            self.cells.add(nxt)
            self.links.add(edge(tip, nxt))
            adj = build_adj(self.cells, self.links)
            dist = bfs_dist(adj, self.start_pos)

    def _pick_boss(self, adj, dist) -> tuple:
        leaves = [p for p in sorted(self.cells)
                  if p != self.start_pos and len(adj[p]) == 1 and dist.get(p, 0) >= 3]
        if not leaves:
            leaves = [p for p in sorted(self.cells)
                      if p != self.start_pos and dist.get(p, 0) >= 3]
        return max(leaves, key=lambda p: (dist[p], p))

    def _add_loops(self, adj, boss_pos) -> None:
        """补 1~3 条回边形成环路，但绝不连到 Boss 房，保证 Boss 房度数为 1。"""
        candidates = []
        for a in sorted(self.cells):
            for d in ("E", "S"):
                dx, dy = DIRS[d]
                b = (a[0] + dx, a[1] + dy)
                if b not in self.cells or boss_pos in (a, b):
                    continue
                if edge(a, b) not in self.links:
                    candidates.append((a, b))
        if not candidates:
            return
        pool = list(candidates)
        self.rng.fork("loops").shuffle(pool)
        for a, b in pool[:min(3, self.rng.fork("loop_count").randint(1, 3), len(pool))]:
            self.links.add(edge(a, b))

    def generate(self) -> None:
        self._grow()
        self._ensure_depth()

        adj = build_adj(self.cells, self.links)
        dist = bfs_dist(adj, self.start_pos)
        self.boss_pos = self._pick_boss(adj, dist)
        self._add_loops(adj, self.boss_pos)

        adj = build_adj(self.cells, self.links)
        dist = bfs_dist(adj, self.start_pos)

        # 宝箱房：次远的叶子，且离起点至少 2 步
        far = [p for p in sorted(self.cells)
               if p not in (self.start_pos, self.boss_pos) and dist.get(p, 0) >= 2]
        leaves = [p for p in far if len(adj[p]) == 1]
        pool = leaves or far
        self.treasure_pos = max(pool, key=lambda p: (dist[p], p)) if pool else None

        # 商店：剩余普通房中随机一间，概率 0.75
        shop_rng = self.rng.fork("shop")
        shop_pool = [p for p in far if p != self.treasure_pos and dist.get(p, 0) >= 2]
        if shop_pool and shop_rng.chance(0.75):
            self.shop_pos = shop_rng.choice(sorted(shop_pool))

        doors = {pos: set() for pos in self.cells}
        for a, b in sorted(self.links):
            d = direction(a, b)
            doors[a].add(d)
            doors[b].add(OPPOSITE[d])

        types = {}
        for pos in sorted(self.cells):
            if pos == self.start_pos:
                types[pos] = RoomType.START.value
            elif pos == self.boss_pos:
                types[pos] = RoomType.BOSS.value
            elif pos == self.treasure_pos:
                types[pos] = RoomType.TREASURE.value
            elif pos == self.shop_pos:
                types[pos] = RoomType.SHOP.value
            else:
                types[pos] = RoomType.NORMAL.value

        for pos in sorted(self.cells):
            rtype = types[pos]
            template = SPECIAL_TEMPLATE[rtype]
            if template is None:
                template = self.rng.fork(f"template:{pos[0]},{pos[1]}").choice(NORMAL_TEMPLATES)
            self.plans[pos] = RoomPlan(
                gx=pos[0], gy=pos[1], rtype=rtype,
                doors=tuple(sorted(doors[pos])),
                template=template, dist=dist[pos],
            )

        self._assert_valid(adj, dist, doors)

    def _assert_valid(self, adj, dist, doors) -> None:
        assert len(dist) == len(self.cells), "存在从起点不可达的房间"
        assert len(adj[self.boss_pos]) == 1, "Boss 房必须只有一扇门"
        assert dist[self.boss_pos] >= 3, "Boss 房离起点太近"
        assert self.treasure_pos is None or dist[self.treasure_pos] >= 2, "宝箱房离起点太近"
        boss_count = sum(1 for p in self.plans.values() if p.rtype == RoomType.BOSS.value)
        treasure_count = sum(1 for p in self.plans.values() if p.rtype == RoomType.TREASURE.value)
        assert boss_count == 1, "Boss 房必须恰好一间"
        assert treasure_count <= 1, "宝箱房最多一间"
        for a, b in sorted(self.links):
            d = direction(a, b)
            assert d in doors[a] and OPPOSITE[d] in doors[b], "相邻房间门方向不互补"
        for pos in sorted(self.cells):
            assert doors[pos], f"房间 {pos} 没有门"

    def neighbors(self, pos) -> list[tuple[str, tuple]]:
        result = []
        for d in self.plan(pos).doors:
            dx, dy = DIRS[d]
            result.append((d, (pos[0] + dx, pos[1] + dy)))
        return result

    def plan(self, pos) -> RoomPlan:
        return self.plans[pos]

    def has_room(self, pos) -> bool:
        return pos in self.plans

    def signature(self) -> str:
        """用于同种子复现断言的稳定指纹。"""
        lines = [self.plans[pos].signature() for pos in sorted(self.plans)]
        return hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()

    def describe(self) -> str:
        return (f"Floor {self.floor}: {len(self.plans)} rooms, "
                f"boss={self.boss_pos}, treasure={self.treasure_pos}, "
                f"shop={self.shop_pos}, difficulty={self.difficulty:.2f}")
