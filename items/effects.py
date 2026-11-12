# -*- coding: utf-8 -*-
"""道具抽取与应用。"""
from __future__ import annotations

from typing import Any

from core.events import ITEM_TAKEN, TOAST
from items.item_defs import ALL_ITEM_IDS, ITEMS, get


def available(owned: list[str]) -> list[str]:
    """排除已持有的唯一道具，避免重复叠加同一件。"""
    return [item_id for item_id in ALL_ITEM_IDS if item_id not in owned]


def roll_items(rng, owned: list[str], count: int = 1,
               pool: tuple[str, ...] | None = None) -> list[str]:
    """确定性抽取不重复道具；候选不足时允许回落为空列表。"""
    candidates = list(pool) if pool else available(owned)
    rng.shuffle(candidates)
    return candidates[:count]


def price_of(item_id: str) -> int:
    return int(get(item_id).get("price", 5))


def describe(item_id: str) -> str:
    item = get(item_id)
    return f"{item['name']} — {item['desc']}"


def apply_item(player, item_id: str, ctx: Any) -> bool:
    """把一个道具永久作用到玩家身上。返回是否成功（已持有返回 False）。"""
    if item_id not in ITEMS or item_id in player.collected:
        return False
    item = ITEMS[item_id]
    player.stats.apply(item.get("mods") or {})

    # 生命上限走 Player 的资源逻辑，不进 Stats 的乘加体系
    if item.get("hearts"):
        player.add_max_hp(float(item["hearts"]))
    player.coins += int(item.get("coins", 0))
    player.keys += int(item.get("keys", 0))
    player.bombs += int(item.get("bombs", 0))
    player.collected.append(item_id)

    ctx.bus.emit(ITEM_TAKEN, item_id=item_id)
    ctx.bus.emit(TOAST, text=describe(item_id))
    return True


def item_pool_for_room(owned: list[str], floor: int) -> tuple[str, ...]:
    """深层更容易出现稀有道具；这里只调整候选池，抽取仍由传入的 rng 决定。"""
    ids = available(owned)
    if floor >= 3:
        return tuple(ids)
    return tuple(i for i in ids if ITEMS[i]["rarity"] == "common") or tuple(ids)
