# -*- coding: utf-8 -*-
"""战斗：眼泪射程、无敌帧、敌人死亡、清房开门、掉落与商店购买。"""
import unittest
from types import SimpleNamespace

import pygame

from core.events import ENEMY_DIED, EventBus
from core.rng import RNG
from core.vec2 import Vec2
from entities.enemies import make_enemy
from entities.pickup import Pickup
from entities.tear import Tear
from items.effects import apply_item
from settings import (LOGICAL_H, LOGICAL_W, PickupKind, RoomType,
                      STEP, WINDOW_H, WINDOW_W)
from core.game import Game


def logic_ctx():
    return SimpleNamespace(bus=EventBus(), rng=RNG("COMBAT"), room=None,
                           dt=STEP, floor=1, frame=0)


def make_game(seed="COMBAT-1"):
    pygame.init()
    screen = pygame.display.set_mode((WINDOW_W, WINDOW_H))
    logical = pygame.Surface((LOGICAL_W, LOGICAL_H))
    game = Game(screen, logical, seed=seed, no_assets=True, autopilot=True)
    game.start_run(seed)
    return game


class TestTear(unittest.TestCase):
    def test_tear_falls_and_is_destroyed_past_range(self):
        ctx = logic_ctx()
        tear = Tear(Vec2(100, 100), Vec2(200, 0), 3.0, max_range=60)
        seen_falling = False
        for _ in range(240):
            tear.update(STEP, ctx)
            seen_falling = seen_falling or tear.falling
            if not tear.alive:
                break
        self.assertTrue(seen_falling, "眼泪应进入坠落段")
        self.assertFalse(tear.alive, "超出射程后应销毁")

    def test_tear_leaves_arena(self):
        ctx = logic_ctx()
        tear = Tear(Vec2(40, 40), Vec2(-400, 0), 3.0, max_range=999)
        for _ in range(60):
            tear.update(STEP, ctx)
        self.assertFalse(tear.alive)

    def test_piercing_keeps_tear_alive_after_hit(self):
        game = make_game()
        tear = Tear(Vec2(100, 100), Vec2(0, 0), 3.0, piercing=True)
        enemy = make_enemy("fly", Vec2(100, 100))
        game.on_tear_hit_enemy(tear, enemy, game.ctx)
        self.assertTrue(tear.alive)
        self.assertLess(enemy.hp, enemy.max_hp)

    def test_non_piercing_tear_is_consumed(self):
        game = make_game()
        tear = Tear(Vec2(100, 100), Vec2(0, 0), 3.0)
        enemy = make_enemy("fly", Vec2(100, 100))
        game.on_tear_hit_enemy(tear, enemy, game.ctx)
        self.assertFalse(tear.alive)


class TestPlayer(unittest.TestCase):
    def test_invulnerability_frames(self):
        ctx = logic_ctx()
        from entities.player import Player
        player = Player()
        self.assertTrue(player.hurt(1.0, ctx))
        self.assertFalse(player.hurt(1.0, ctx), "无敌帧内不应重复受伤")
        self.assertEqual(player.hp, player.max_hp - 1.0)

    def test_death_emits_event(self):
        ctx = logic_ctx()
        from entities.player import Player
        player = Player()
        player.hp = 1.0
        seen = []
        ctx.bus.on("player_died", lambda **kw: seen.append(kw))
        player.hurt(2.0, ctx)
        self.assertEqual(player.hp, 0)
        ctx.bus.drain()
        self.assertEqual(len(seen), 1)

    def test_multi_shot(self):
        ctx = logic_ctx()
        from entities.player import Player
        player = Player()
        self.assertEqual(len(player.shoot(Vec2(1, 0), ctx)), 1)
        player.fire_cooldown = 0
        apply_item(player, "inner_eye", ctx)
        tears = player.shoot(Vec2(1, 0), ctx)
        self.assertEqual(len(tears), 3)


class TestRoomAndPickups(unittest.TestCase):
    def test_enemy_death_emits_and_clears_room(self):
        game = make_game()
        ctx = game.ctx
        seen = []
        ctx.bus.on(ENEMY_DIED, lambda **kw: seen.append(kw))
        enemy = make_enemy("fly", Vec2(120, 120))
        enemy.hurt(999, ctx)
        self.assertFalse(enemy.alive)
        ctx.bus.drain()
        self.assertEqual(len(seen), 1)

    def test_clearing_room_opens_all_doors(self):
        game = make_game()
        dungeon = game.floor.dungeon
        pos = next(p for p in sorted(dungeon.plans)
                   if dungeon.plan(p).rtype == RoomType.NORMAL.value)
        room = game.floor.room_at(pos)
        room.populate([])
        self.assertGreater(len(room.enemies), 0)
        room.set_doors_open(False)
        for enemy in list(room.enemies):
            enemy.kill()
        room.enemies = []
        game.ctx.room = room
        self.assertTrue(room.check_cleared(game.ctx))
        self.assertTrue(room.cleared)
        self.assertTrue(all(d.opened for d in room.doors.values()))
        game.bus.drain()

    def test_heart_pickup_heals_only_when_hurt(self):
        game = make_game()
        game.player.hp = 3.0
        pickup = Pickup(Vec2(100, 100), PickupKind.HEART, value=1.0)
        game._take_pickup(pickup)
        self.assertEqual(game.player.hp, 4.0)
        self.assertFalse(pickup.alive)

    def test_shop_pickup_requires_coins(self):
        game = make_game()
        pickup = Pickup(Vec2(100, 100), PickupKind.ITEM, item_id="pencil", price=9)
        game._take_pickup(pickup)
        self.assertTrue(pickup.alive, "钱不够时不该拿走商品")
        self.assertNotIn("pencil", game.player.collected)
        game.player.coins = 20
        game._take_pickup(pickup)
        self.assertFalse(pickup.alive)
        self.assertEqual(game.player.coins, 20 - 9)

    def test_buy_does_not_apply_when_poor(self):
        game = make_game()
        pickup = Pickup(Vec2(100, 100), PickupKind.ITEM, item_id="cupid", price=10)
        game._take_pickup(pickup)
        self.assertFalse(game.player.stats.get_flag("piercing"))


if __name__ == "__main__":
    unittest.main()
