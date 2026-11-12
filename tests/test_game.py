# -*- coding: utf-8 -*-
"""集成：开局、长稳推进、换房、层间推进、通关结算、道具三选一与占位渲染。"""
import unittest
from unittest.mock import patch

import pygame

from core.game import Game
from core.events import ROOM_TRANSITION
from core.rng import RNG
from core.vec2 import Vec2
from entities.pickup import Pickup
from settings import (LOGICAL_H, LOGICAL_W, MAX_FLOOR, PickupKind,
                      STEP, State, WINDOW_H, WINDOW_W)
from world.floor import Floor


def make_game(seed="GAME-1"):
    pygame.init()
    screen = pygame.display.set_mode((WINDOW_W, WINDOW_H))
    logical = pygame.Surface((LOGICAL_W, LOGICAL_H))
    game = Game(screen, logical, seed=seed, no_assets=True, autopilot=True)
    game.start_run(seed)
    return game


def key_event(key, unicode=""):
    return pygame.event.Event(pygame.KEYDOWN, key=key, unicode=unicode)


class TestGameFlow(unittest.TestCase):
    def test_start_run_state(self):
        game = make_game()
        self.assertEqual(game.state, State.PLAYING)
        self.assertEqual(game.floor_number, 1)
        self.assertIsNotNone(game.floor.current)
        self.assertIn(game.player, game.floor.current.players)
        self.assertTrue(game.floor.current.cleared, "起始房不应有敌人")

    def test_six_hundred_fixed_steps_do_not_crash(self):
        game = make_game("LONG-RUN")
        for frame in range(600):
            game.handle_events([], frame)
            game.fixed_update(STEP)
        self.assertEqual(game.frame, 600)
        self.assertLess(game.entity_count, 250, "实体数量应有界")
        self.assertGreater(game.player.age, 0)

    def test_room_transition_moves_player(self):
        game = make_game()
        start = game.floor.current_pos
        direction = game.floor.plan.doors[0]
        game.transition_cooldown = 0
        game.bus.emit(ROOM_TRANSITION, dir=direction)
        game.bus.drain()
        self.assertNotEqual(game.floor.current_pos, start)
        self.assertIn(game.player, game.floor.current.players)
        self.assertEqual(len(game.floor.current.players), 1)

    def test_advance_floor(self):
        game = make_game()
        game.player.collected.append("pencil")
        game.advance_floor()
        self.assertEqual(game.floor_number, 2)
        self.assertEqual(game.floor.number, 2)
        self.assertIn(game.player, game.floor.current.players)
        self.assertTrue(game.floor.current.cleared)

    def test_all_six_floors_generate(self):
        rng = RNG("FLOORS")
        for number in range(1, MAX_FLOOR + 1):
            floor = Floor(number, rng)
            self.assertGreater(len(floor.dungeon.plans), 0)
            self.assertTrue(floor.dungeon.has_room(floor.dungeon.boss_pos))

    def test_last_floor_boss_cleared_wins(self):
        game = make_game("WIN-RUN")
        game.floor_number = MAX_FLOOR
        game.floor = Floor(MAX_FLOOR, game.rng)
        game.floor.enter(game.floor.dungeon.start_pos, game.player, game.ctx)
        boss_pos = game.floor.dungeon.boss_pos
        room = game.floor.room_at(boss_pos)
        room.populate(game.player.collected)
        game.floor.current_pos = boss_pos
        game.ctx.room = room
        self.assertTrue(any(e.kind == "boss" for e in room.enemies))

        with patch("core.game.save_data_to_disk", return_value=True):
            for enemy in list(room.enemies):
                enemy.hurt(99999, game.ctx)
            room.enemies = []
            game.bus.drain()
            room.check_cleared(game.ctx)
            game.bus.drain()
        self.assertEqual(game.state, State.WIN)
        self.assertEqual(game.save_data["best"]["wins"], 1)

    def test_death_writes_record(self):
        game = make_game("DEAD-RUN")
        with patch("core.game.save_data_to_disk", return_value=True):
            game.player.hp = 1.0
            game.player.invuln = 0
            game.player.hurt(2.0, game.ctx)
            game.bus.drain()
        self.assertEqual(game.state, State.DEAD)

    def test_item_select_applies_chosen_item(self):
        game = make_game()
        game.input.autopilot = False
        game.item_choices = ["pencil", "cupid", "spoon_bender"]
        game.item_index = 0
        game.state = State.ITEM_SELECT
        game.handle_events([key_event(pygame.K_RIGHT)], 1)
        self.assertEqual(game.item_index, 1)
        game.handle_events([key_event(pygame.K_RETURN, "\r")], 2)
        self.assertEqual(game.state, State.PLAYING)
        self.assertIn("cupid", game.player.collected)
        self.assertTrue(game.player.stats.get_flag("piercing"))

    def test_render_in_no_assets_mode(self):
        game = make_game("RENDER")
        for frame in range(30):
            game.handle_events([], frame)
            game.fixed_update(STEP)
        game.render(game.logical)
        pixel = game.logical.get_at((240, 144))
        self.assertEqual(len(pixel), 4)

    def test_next_floor_pickup_advances(self):
        game = make_game()
        pickup = Pickup(Vec2(100, 100), PickupKind.ITEM,
                        item_id="__next_floor__")
        game._take_pickup(pickup)
        self.assertEqual(game.floor_number, 2)


if __name__ == "__main__":
    unittest.main()
