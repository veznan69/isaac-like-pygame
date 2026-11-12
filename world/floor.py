# -*- coding: utf-8 -*-
"""一层的运行时容器：把 Dungeon 蓝图按需实例化为 Room，并追踪当前位置。"""
from __future__ import annotations

from typing import Any

from core.events import ROOM_ENTERED
from settings import DIRS, MAX_FLOOR
from world.dungeon import Dungeon
from world.room import Room


class Floor:
    def __init__(self, number: int, rng) -> None:
        self.number = int(number)
        self.rng = rng
        self.dungeon = Dungeon(self.number, rng)
        self._rooms: dict = {}
        self.current_pos = self.dungeon.start_pos

    @property
    def plan(self):
        return self.dungeon.plan(self.current_pos)

    @property
    def is_last(self) -> bool:
        return self.number >= MAX_FLOOR

    def room_at(self, pos) -> Room:
        if pos not in self._rooms:
            blueprint = self.dungeon.plan(pos)
            self._rooms[pos] = Room(blueprint, self.number, self.rng,
                                    self.dungeon.difficulty)
        return self._rooms[pos]

    @property
    def current(self) -> Room:
        return self.room_at(self.current_pos)

    @property
    def rooms(self) -> dict:
        """已实例化的房间，供小地图查询 visited 状态。"""
        return self._rooms

    def neighbor(self, direction: str):
        """返回目标格坐标；该方向没有门则返回 None。"""
        if direction not in self.plan.doors:
            return None
        dx, dy = DIRS[direction]
        pos = (self.current_pos[0] + dx, self.current_pos[1] + dy)
        return pos if self.dungeon.has_room(pos) else None

    def enter(self, pos, player, ctx: Any) -> Room:
        """切换到目标房间：摆放玩家、延迟生成内容、打上已访问标记。"""
        self.current_pos = pos
        room = self.room_at(pos)
        room.populate(player.collected if player else [])
        room.visited = True
        for p in room.players:
            if p is player:
                break
        else:
            room.players.append(player)
        ctx.bus.emit(ROOM_ENTERED, room=room)
        return room

    def all_cleared(self) -> bool:
        return all(room.cleared for room in self._rooms.values())

    def visited_count(self) -> int:
        return sum(1 for room in self._rooms.values() if room.visited)

    def describe(self) -> str:
        return self.dungeon.describe()
