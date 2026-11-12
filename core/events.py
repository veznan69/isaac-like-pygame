# -*- coding: utf-8 -*-
"""事件总线与事件名常量。

L0 模块。实体只发事件、不认识 Game / 地牢，跨层通信全部经此队列，
这样 L2 的实体和 L3 的房间之间不会产生循环 import。
"""
from __future__ import annotations

from collections import defaultdict, deque
from typing import Callable

ROOM_TRANSITION = "room_transition"     # dir: str
ROOM_ENTERED = "room_entered"           # room
ROOM_CLEARED = "room_cleared"           # room
PLAYER_HURT = "player_hurt"             # amount: float, source
PLAYER_DIED = "player_died"
ENEMY_DIED = "enemy_died"               # pos, kind
BOSS_DIED = "boss_died"
PICKUP_GAINED = "pickup_gained"         # kind, value
ITEM_OFFER = "item_offer"               # item_id, choices
ITEM_TAKEN = "item_taken"               # item_id
FLOOR_ADVANCE = "floor_advance"         # floor: int
RUN_WON = "run_won"
SPAWN_TEAR = "spawn_tear"               # tear
SPAWN_PICKUP = "spawn_pickup"           # pickup
SPAWN_ENEMY = "spawn_enemy"             # enemy
SPAWN_PARTICLES = "spawn_particles"     # x, y, color, count
SHAKE = "shake"                         # strength
SFX = "sfx"                             # name（本期不发声，预留接口）
STATE_CHANGE = "state_change"           # state
TOAST = "toast"                         # text


class EventBus:
    """默认入队、每固定步末尾统一 drain，保证一帧内事件处理顺序与逻辑解耦。"""

    __slots__ = ("_handlers", "_queue", "_depth")

    def __init__(self) -> None:
        self._handlers: dict[str, list[Callable]] = defaultdict(list)
        self._queue: deque[tuple[str, dict]] = deque()
        self._depth = 0

    def on(self, name: str, handler: Callable) -> None:
        if handler not in self._handlers[name]:
            self._handlers[name].append(handler)

    def off(self, name: str, handler: Callable) -> None:
        if name in self._handlers and handler in self._handlers[name]:
            self._handlers[name].remove(handler)

    def clear(self) -> None:
        self._handlers.clear()
        self._queue.clear()
        self._depth = 0

    def emit(self, name: str, **payload) -> None:
        """入队，等待 drain 时按产生顺序处理。"""
        self._queue.append((name, payload))

    def fire(self, name: str, **payload) -> None:
        """立即派发，仅用于必须同步生效的场景（如状态切换）。"""
        self._dispatch(name, payload)

    def _dispatch(self, name: str, payload: dict) -> None:
        for handler in list(self._handlers.get(name, ())):
            handler(**payload)

    def drain(self, max_events: int = 2048) -> int:
        """处理当前队列；处理过程中新产生的事件留到下一次，避免无限递归。"""
        count = 0
        while self._queue and count < max_events:
            name, payload = self._queue.popleft()
            self._dispatch(name, payload)
            count += 1
        return count

    @property
    def pending(self) -> int:
        return len(self._queue)
