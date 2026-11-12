# -*- coding: utf-8 -*-
"""游戏总控：状态机、事件编排、碰撞分发、掉落与层间推进。

实体与房间不反向引用 Game；所有跨层通信经 EventBus，依赖通过 Context 注入。
"""
from __future__ import annotations

import time
from collections import defaultdict
from typing import Any

import pygame

from core.assets import AssetBank
from core.collision import PAIRS, circle_rect_hit, circles_hit, move_with_props
from core.context import Context
from core.events import (BOSS_DIED, ENEMY_DIED, FLOOR_ADVANCE, ITEM_OFFER, ITEM_TAKEN,
                         PLAYER_DIED, ROOM_CLEARED, ROOM_ENTERED, ROOM_TRANSITION,
                         RUN_WON, SHAKE, SPAWN_ENEMY, SPAWN_PARTICLES, SPAWN_PICKUP,
                         SPAWN_TEAR, TOAST, EventBus)
from core.input import InputState
from core.rng import RNG
from core.save import clear_run, load as load_save, record_run, save as save_data_to_disk
from core.vec2 import Vec2
from entities.pickup import Pickup
from entities.player import Player
from items.effects import apply_item
from settings import (COL_BG, DOOR_SPAWN, INPUT_KEYBOARD, LOGICAL_H, LOGICAL_W,
                      MAX_FLOOR, OPPOSITE, PALETTE, PickupKind, RoomType, State,
                      Group)
from ui import hud, screens
from ui.painter import Painter
from world.floor import Floor
from world.minimap import draw as draw_minimap

NEXT_FLOOR = "__next_floor__"


class Game:
    def __init__(self, screen, logical_surface, seed: str | None = None,
                 input_mode: str | None = None, no_assets: bool = False,
                 autopilot: bool = False) -> None:
        self.screen = screen
        self.logical = logical_surface
        self.save_data = load_save()
        self.seed = seed or f"RUN-{time.time_ns():x}"
        self.seed_text = seed or ""
        self.bus = EventBus()
        self.rng = RNG(self.seed)
        self.visual_rng = RNG(self.seed + "|visual")

        mode = input_mode or self.save_data.get("settings", {}).get("input_mode", INPUT_KEYBOARD)
        self.input = InputState(mode, autopilot)
        self.bank = AssetBank(no_assets=no_assets)
        self.painter = Painter(logical_surface, self.bank, no_assets)
        self.ctx = Context(bus=self.bus, rng=self.rng, painter=self.painter)

        self.state = State.TITLE
        self.floor: Floor | None = None
        self.player = None
        self.floor_number = 1
        self.frame = 0
        self.elapsed = 0.0
        self.quit_requested = False
        self.debug = False
        self.display_fps = 60.0
        self.shake = 0.0
        self.transition_cooldown = 0
        self.offer_cooldown = 0
        self.toast_cooldown = 0
        self.toasts: list[tuple[str, float]] = []
        self.item_choices: list[str] = []
        self.item_index = 0
        self._item_pedestal = None
        self._register_handlers()

    # ---------- 事件注册 ----------

    def _register_handlers(self) -> None:
        self.bus.on(SPAWN_TEAR, self._on_spawn_tear)
        self.bus.on(SPAWN_ENEMY, self._on_spawn_enemy)
        self.bus.on(SPAWN_PICKUP, self._on_spawn_pickup)
        self.bus.on(SPAWN_PARTICLES, self._on_spawn_particles)
        self.bus.on(ENEMY_DIED, self._on_enemy_died)
        self.bus.on(PLAYER_DIED, self._on_player_died)
        self.bus.on(ROOM_CLEARED, self._on_room_cleared)
        self.bus.on(ROOM_TRANSITION, self._on_room_transition)
        self.bus.on(TOAST, self._on_toast)
        self.bus.on(SHAKE, self._on_shake)
        self.bus.on(ITEM_TAKEN, self._on_item_taken)

    def _room(self):
        return self.floor.current if self.floor else None

    def _on_spawn_tear(self, tear) -> None:
        room = self._room()
        if room:
            room.tears.append(tear)

    def _on_spawn_enemy(self, enemy) -> None:
        room = self._room()
        if room:
            room.enemies.append(enemy)

    def _on_spawn_pickup(self, pickup) -> None:
        room = self._room()
        if room:
            room.pickups.append(pickup)

    def _on_spawn_particles(self, x, y, color, count=4, speed=50.0) -> None:
        room = self._room()
        if room:
            room.add_particles(x, y, color, count, speed)

    def _on_enemy_died(self, pos, kind, enemy=None) -> None:
        if self.player:
            self.player.kills += 1

    def _on_player_died(self) -> None:
        self._finish(won=False)

    def _on_toast(self, text: str) -> None:
        self.toasts.insert(0, (str(text), 2.4))
        self.toasts = self.toasts[:3]

    def _on_shake(self, strength: float) -> None:
        self.shake = max(self.shake, float(strength))

    def _on_item_taken(self, item_id: str) -> None:
        if self.floor:
            self.floor.current.add_particles(self.player.pos.x, self.player.pos.y,
                                            PALETTE["gold"], 12, 80)

    # ---------- 一局游戏 ----------

    def start_run(self, seed: str | None = None) -> None:
        self.seed = seed or self.seed_text.strip() or f"RUN-{time.time_ns():x}"
        self.rng = RNG(self.seed)
        self.visual_rng = RNG(self.seed + "|visual")
        self.ctx.rng = self.rng
        self.ctx.seed = self.seed
        self.player = Player()
        self.floor_number = 1
        self.floor = Floor(1, self.rng)
        self.floor.enter(self.floor.dungeon.start_pos, self.player, self.ctx)
        self.player.pos = Vec2(LOGICAL_W / 2, LOGICAL_H / 2)
        self.state = State.PLAYING
        self.elapsed = 0.0
        self.toasts.clear()
        self.item_choices = []
        self.transition_cooldown = 20
        self.offer_cooldown = 0
        self.shake = 0.0
        self.toast(f"种子 {self.seed[:16]} · 第 1 层")

    def toast(self, text: str) -> None:
        self._on_toast(text)

    def advance_floor(self) -> None:
        self.floor_number += 1
        self.floor = Floor(self.floor_number, self.rng)
        self.floor.enter(self.floor.dungeon.start_pos, self.player, self.ctx)
        self.player.pos = Vec2(LOGICAL_W / 2, LOGICAL_H / 2)
        self.transition_cooldown = 20
        self.bus.emit(FLOOR_ADVANCE, floor=self.floor_number)
        self.toast(f"进入第 {self.floor_number} 层")
        self.shake = 4.0

    def _finish(self, won: bool) -> None:
        if self.state in (State.DEAD, State.WIN):
            return
        self.state = State.WIN if won else State.DEAD
        record_run(self.save_data, floor=self.floor_number,
                   kills=self.player.kills if self.player else 0,
                   won=won, elapsed=self.elapsed, seed=self.seed)
        save_data_to_disk(self.save_data)
        self.toast("通关！" if won else "你死了")

    # ---------- 输入 ----------

    def on_focus_lost(self) -> None:
        if self.state == State.PLAYING:
            self.state = State.PAUSED

    def _switch_mode(self) -> None:
        mode = self.input.toggle_mode()
        self.save_data.setdefault("settings", {})["input_mode"] = mode
        save_data_to_disk(self.save_data)
        self.toast("操作模式：WASD + 方向键" if mode == INPUT_KEYBOARD
                   else "操作模式：WASD + 鼠标瞄准")

    def handle_events(self, events, frame: int = 0) -> None:
        for event in events:
            if event.type == pygame.QUIT:
                self.quit_requested = True

        self.input.poll(events, self.player.pos if self.player else None, frame)

        if self.input.consume("debug"):
            self.debug = not self.debug

        if self.state == State.TITLE:
            self._handle_title_events()
        elif self.state == State.PLAYING:
            self._handle_playing_events()
        elif self.state == State.PAUSED:
            self._handle_paused_events()
        elif self.state == State.ITEM_SELECT:
            self._handle_item_events()
        else:
            self._handle_end_events()

    def _handle_title_events(self) -> None:
        for char in self.input.typed:
            if char.isalnum() or char in "-_":
                self.seed_text = (self.seed_text + char)[:24]
        if self.input.consume("backspace"):
            self.seed_text = self.seed_text[:-1]
        if self.input.consume("toggle_input"):
            self._switch_mode()
        if self.input.consume("confirm") or self.input.consume("interact"):
            self.start_run()

    def _handle_playing_events(self) -> None:
        if self.input.consume("pause"):
            self.state = State.PAUSED
        if self.input.consume("toggle_input"):
            self._switch_mode()
        if self.input.consume("restart"):
            self.start_run(self.seed)
        if self.input.consume("title"):
            self.state = State.TITLE
        if self.input.consume("bomb"):
            self._use_bomb()
        if self.input.consume("interact"):
            self._try_interact()

    def _handle_paused_events(self) -> None:
        if self.input.consume("pause") or self.input.consume("confirm"):
            self.state = State.PLAYING
        if self.input.consume("toggle_input"):
            self._switch_mode()
        if self.input.consume("restart"):
            self.start_run(self.seed)
        if self.input.consume("title"):
            self.state = State.TITLE

    def _handle_item_events(self) -> None:
        if self.input.consume("left"):
            self.item_index = (self.item_index - 1) % max(1, len(self.item_choices))
        if self.input.consume("right"):
            self.item_index = (self.item_index + 1) % max(1, len(self.item_choices))
        if self.input.consume("confirm") or self.input.consume("interact"):
            if self.item_choices:
                chosen = self.item_choices[self.item_index]
                apply_item(self.player, chosen, self.ctx)
                if self._item_pedestal:
                    self._item_pedestal.used = True
                    self._item_pedestal.item_choices = []
            self.item_choices = []
            self.state = State.PLAYING
        elif self.input.consume("pause"):
            self.item_choices = []
            self.offer_cooldown = 45
            self.state = State.PLAYING

    def _handle_end_events(self) -> None:
        if self.input.consume("restart") or self.input.consume("confirm"):
            self.start_run(self.seed)
        if self.input.consume("title"):
            self.state = State.TITLE

    def _use_bomb(self) -> None:
        room = self._room()
        if not room or not self.player or self.player.bombs <= 0:
            self.toast("没有炸弹了")
            return
        self.player.bombs -= 1
        for enemy in list(room.enemies):
            enemy.hurt(12.0, self.ctx)
        room.add_particles(self.player.pos.x, self.player.pos.y, PALETTE["orange"], 20, 130)
        self.shake = 8.0

    def _try_interact(self) -> None:
        """E 键：靠近宝箱台可主动开启，靠近商店道具可购买。"""
        room = self._room()
        if not room or not self.player:
            return
        for prop in room.props:
            if prop.kind == "pedestal" and prop.item_choices and not prop.used:
                if self.player.pos.distance_to(prop.pos) < 34:
                    self._offer(prop)
                    return
        for pickup in room.pickups:
            if pickup.price and self.player.pos.distance_to(pickup.pos) < 24:
                self._take_pickup(pickup)
                return

    def _offer(self, prop) -> None:
        self.item_choices = list(prop.item_choices)
        self.item_index = 0
        self._item_pedestal = prop
        self.state = State.ITEM_SELECT
        self.bus.emit(ITEM_OFFER, item_id=self.item_choices[0] if self.item_choices else "",
                      choices=self.item_choices)

    # ---------- 固定步更新 ----------

    def fixed_update(self, dt: float) -> None:
        self.frame += 1
        self.ctx.dt = dt
        self.ctx.frame = self.frame
        self.ctx.floor = self.floor_number
        self.ctx.seed = self.seed
        self.ctx.rng = self.rng
        self.ctx.game = self
        self.ctx.input = self.input
        if self.player:
            self.ctx.stats = self.player.stats

        self.toasts = [(text, life - dt) for text, life in self.toasts if life - dt > 0]
        self.shake = max(0.0, self.shake - dt * 18.0)
        if self.transition_cooldown > 0:
            self.transition_cooldown -= 1
        if self.offer_cooldown > 0:
            self.offer_cooldown -= 1
        if self.toast_cooldown > 0:
            self.toast_cooldown -= 1

        if self.state == State.PLAYING:
            self.elapsed += dt
            self._update_playing(dt)

        self.bus.drain()

    def _update_playing(self, dt: float) -> None:
        room = self._room()
        player = self.player
        if not room or not player:
            return
        self.ctx.room = room

        if self.input.move.length_sq() > 1e-6:
            delta = self.input.move * player.stats.value("move_speed") * dt
            move_with_props(player, delta, room.solids)

        if self.input.firing and player.can_fire():
            for tear in player.shoot(self.input.fire_dir, self.ctx):
                room.tears.append(tear)

        room.update(dt, self.ctx)
        self._hazard_check(room)
        self._collisions(room)
        self._door_check(room)
        room.check_cleared(self.ctx)
        if self.offer_cooldown == 0:
            self._pedestal_check(room)

    def _hazard_check(self, room) -> None:
        """火堆等接触伤害；伤害判定统一走 Player.hurt 以复用无敌帧。"""
        for prop in room.props:
            if prop.harm and prop.alive and circles_hit(self.player, prop, 0.7):
                self.player.hurt(1.0, self.ctx)

    def _collisions(self, room) -> None:
        buckets: dict[Group, list] = defaultdict(list)
        for entity in room.all_entities():
            if entity.alive and not entity.mark_remove:
                buckets[entity.group].append(entity)
        for door in room.doors.values():
            buckets[Group.DOOR].append(door)

        for group_a, group_b, handler_name in PAIRS:
            list_a, list_b = buckets.get(group_a), buckets.get(group_b)
            if not list_a or not list_b:
                continue
            handler = getattr(self, handler_name)
            for a in list_a:
                if not a.alive:
                    continue
                for b in list_b:
                    if a is b or not b.alive:
                        continue
                    if circles_hit(a, b):
                        handler(a, b, self.ctx)

    def _door_check(self, room) -> None:
        if self.transition_cooldown > 0 or not self.player.alive:
            return
        for door in room.doors.values():
            if not door.opened:
                continue
            # 玩家受 arena 约束走不到墙上的门格中心，因此用"靠近门口"的距离判定，
            # 矩形相交作为兜底；36px 约为一个半格子，不会在房间中段误触发。
            near = self.player.pos.distance_to(door.pos) < 36
            inside = circle_rect_hit(self.player.pos.x, self.player.pos.y,
                                     self.player.radius, door.rect)
            if near or inside:
                self.bus.emit(ROOM_TRANSITION, dir=door.dir)
                self.transition_cooldown = 24
                return

    def _pedestal_check(self, room) -> None:
        for prop in room.props:
            if prop.kind == "pedestal" and prop.item_choices and not prop.used:
                if self.player.pos.distance_to(prop.pos) < 28:
                    self._offer(prop)
                    return

    # ---------- 配对处理器 ----------

    def on_tear_hit_enemy(self, tear, enemy, ctx) -> None:
        if not tear.alive or not enemy.alive:
            return
        if enemy.id in tear.hit_ids:
            return
        tear.hit_ids.add(enemy.id)
        enemy.hurt(tear.damage, ctx)
        if not tear.piercing:
            tear._splash(ctx)
            tear.kill()

    def on_tear_hit_player(self, tear, player, ctx) -> None:
        if tear.alive:
            player.hurt(2.0, ctx)
            tear._splash(ctx)
            tear.kill()

    def on_player_touch_enemy(self, player, enemy, ctx) -> None:
        player.hurt(enemy.touch_damage, ctx)

    def on_player_touch_pickup(self, player, pickup, ctx) -> None:
        self._take_pickup(pickup)

    def on_player_touch_door(self, player, door, ctx) -> None:
        # 门的实际换房判定在 _door_check 用矩形做，这里只作为兜底
        if door.opened and self.transition_cooldown == 0:
            self.bus.emit(ROOM_TRANSITION, dir=door.dir)
            self.transition_cooldown = 24

    def on_enemy_separate(self, a, b, ctx) -> None:
        if a is b or a.pos == b.pos:
            return
        push = (a.pos - b.pos).normalized() * 0.35
        a.pos += push
        b.pos -= push

    def _take_pickup(self, pickup) -> None:
        if not pickup.alive:
            return
        player = self.player
        if pickup.item_id == NEXT_FLOOR:
            pickup.kill()
            if self.floor and self.floor.is_last:
                self._finish(won=True)
            else:
                self.advance_floor()
            return
        if pickup.price > 0:
            if player.coins < pickup.price:
                if self.toast_cooldown == 0:
                    self.toast(f"硬币不足（需要 {pickup.price}）")
                    self.toast_cooldown = 60
                return
            player.coins -= pickup.price
        if pickup.item_id:
            if not apply_item(player, pickup.item_id, self.ctx):
                return
        elif pickup.kind == PickupKind.HEART:
            if player.hp >= player.max_hp:
                return
            player.heal(pickup.value)
        elif pickup.kind == PickupKind.COIN:
            player.coins += int(pickup.value)
        elif pickup.kind == PickupKind.KEY:
            player.keys += int(pickup.value)
        elif pickup.kind == PickupKind.BOMB:
            player.bombs += int(pickup.value)
        pickup.kill()

    # ---------- 房间事件 ----------

    def _on_room_transition(self, dir: str) -> None:
        if not self.floor or not self.player or self.state != State.PLAYING:
            return
        target = self.floor.neighbor(dir)
        if target is None:
            return
        old = self.floor.current
        if self.player in old.players:
            old.players.remove(self.player)
        spawn = DOOR_SPAWN[OPPOSITE[dir]]
        self.player.pos = Vec2(*spawn)
        self.floor.enter(target, self.player, self.ctx)
        self.transition_cooldown = 24

    def _on_room_cleared(self, room) -> None:
        loot = self.rng.fork(f"loot:{self.floor_number}:{room.pos[0]},{room.pos[1]}")
        if room.rtype == RoomType.BOSS.value:
            if self.floor.is_last:
                self._finish(won=True)
            else:
                room.pickups.append(Pickup(Vec2(LOGICAL_W / 2, LOGICAL_H / 2),
                                           kind=PickupKind.ITEM,
                                           item_id=NEXT_FLOOR))
                self.toast("通往下一层的活板门出现了")
            room.add_particles(LOGICAL_W / 2, LOGICAL_H / 2, PALETTE["gold"], 24, 120)
            return
        if room.rtype == RoomType.TREASURE.value:
            return
        count = 1 + (1 if loot.chance(0.45) else 0) + (1 if loot.chance(0.18) else 0)
        weights = {"coin": 34, "heart": 20, "key": 16, "bomb": 14, "item": 6}
        if self.player:
            weights["heart"] += max(0, 10 - self.player.hp) * 1.5
            weights["item"] += self.player.stats.value("luck")
        kind_map = {
            "coin": PickupKind.COIN, "heart": PickupKind.HEART,
            "key": PickupKind.KEY, "bomb": PickupKind.BOMB,
            "item": PickupKind.ITEM,
        }
        for _ in range(count):
            kind = kind_map[loot.weighted(weights)]
            pos = Vec2(loot.uniform(96, LOGICAL_W - 96), loot.uniform(80, LOGICAL_H - 80))
            if kind == PickupKind.HEART:
                room.pickups.append(Pickup(pos, kind, value=1.0))
            elif kind == PickupKind.ITEM:
                from items.effects import item_pool_for_room, roll_items
                choices = roll_items(loot, self.player.collected, 1,
                                     item_pool_for_room(self.player.collected, self.floor_number))
                if choices:
                    room.pickups.append(Pickup(pos, kind, item_id=choices[0]))
            else:
                room.pickups.append(Pickup(pos, kind))

    # ---------- 渲染 ----------

    @property
    def current_boss(self):
        room = self._room()
        if room:
            for enemy in room.enemies:
                if enemy.kind == "boss" and enemy.alive:
                    return enemy
        return None

    @property
    def entity_count(self) -> int:
        room = self._room()
        return sum(1 for _ in room.all_entities()) if room else 0

    @property
    def shake_offset(self) -> tuple[int, int]:
        if self.shake <= 0.2:
            return (0, 0)
        return (int(self.visual_rng.uniform(-self.shake, self.shake) * 2),
                int(self.visual_rng.uniform(-self.shake, self.shake) * 2))

    def render(self, surface) -> None:
        self.painter.surface = surface
        surface.fill(COL_BG)
        if self.floor and self.player and self.state != State.TITLE:
            room = self.floor.current
            self.ctx.room = room
            room.render(self.painter, self.ctx)
            draw_minimap(self.painter, self.floor.dungeon, self.floor.rooms,
                         self.floor.current_pos, self.player.stats)
            hud.draw(self.painter, self)

        if self.state == State.TITLE:
            screens.draw_title(self.painter, self)
        elif self.state == State.PAUSED:
            screens.draw_paused(self.painter, self)
        elif self.state == State.ITEM_SELECT:
            screens.draw_item_select(self.painter, self)
        elif self.state == State.DEAD:
            screens.draw_end(self.painter, self, won=False)
        elif self.state == State.WIN:
            screens.draw_end(self.painter, self, won=True)
