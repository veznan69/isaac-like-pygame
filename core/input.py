# -*- coding: utf-8 -*-
"""输入抽象：键盘双摇杆 / 鼠标瞄准双模式 + 冒烟测试的确定性自动驾驶。"""
from __future__ import annotations

import math

import pygame

from core.vec2 import Vec2
from settings import INPUT_KEYBOARD, INPUT_MOUSE, SCALE

MOVE_KEYS = {
    pygame.K_a: ("x", -1), pygame.K_d: ("x", 1),
    pygame.K_w: ("y", -1), pygame.K_s: ("y", 1),
}

FIRE_KEYS = {
    pygame.K_UP: Vec2(0, -1), pygame.K_DOWN: Vec2(0, 1),
    pygame.K_LEFT: Vec2(-1, 0), pygame.K_RIGHT: Vec2(1, 0),
}

EDGE_KEYS = {
    pygame.K_e: "interact", pygame.K_SPACE: "interact",
    pygame.K_ESCAPE: "pause", pygame.K_p: "pause",
    pygame.K_RETURN: "confirm",
    pygame.K_r: "restart", pygame.K_t: "title",
    pygame.K_F1: "debug", pygame.K_q: "bomb",
    pygame.K_TAB: "toggle_input",
    pygame.K_LEFT: "left", pygame.K_RIGHT: "right",
    pygame.K_BACKSPACE: "backspace",
}


class InputState:
    __slots__ = ("mode", "autopilot", "move", "fire_dir", "firing", "edges",
                 "mouse_pos", "typed", "held_mouse")

    def __init__(self, mode: str = INPUT_KEYBOARD, autopilot: bool = False) -> None:
        self.mode = mode if mode in (INPUT_KEYBOARD, INPUT_MOUSE) else INPUT_KEYBOARD
        self.autopilot = bool(autopilot)
        self.move = Vec2()
        self.fire_dir = Vec2(0, 1)
        self.firing = False
        self.edges: set[str] = set()
        self.mouse_pos = (0, 0)
        self.typed: list[str] = []
        self.held_mouse = False

    def toggle_mode(self) -> str:
        self.mode = INPUT_MOUSE if self.mode == INPUT_KEYBOARD else INPUT_KEYBOARD
        return self.mode

    def consume(self, name: str) -> bool:
        if name in self.edges:
            self.edges.discard(name)
            return True
        return False

    def poll(self, events, player_pos=None, frame: int = 0, scale: int = SCALE) -> None:
        self.edges.clear()
        self.typed = []
        self.move = Vec2()
        self.fire_dir = Vec2()
        self.firing = False

        if self.autopilot:
            self._autopilot(frame)
            return

        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key in EDGE_KEYS:
                    self.edges.add(EDGE_KEYS[event.key])
                if event.unicode and event.unicode.isprintable():
                    self.typed.append(event.unicode)
            elif event.type in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
                self.mouse_pos = event.pos
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self.held_mouse = True
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                self.held_mouse = False

        keys = pygame.key.get_pressed()
        for key, (axis, value) in MOVE_KEYS.items():
            if keys[key]:
                self.move += Vec2(value, 0) if axis == "x" else Vec2(0, value)
        if self.move.length_sq() > 1:
            self.move = self.move.normalized()

        if self.mode == INPUT_KEYBOARD:
            for key, direction in FIRE_KEYS.items():
                if keys[key]:
                    self.fire_dir += direction
            if self.fire_dir.length_sq() > 1e-6:
                self.fire_dir = self.fire_dir.normalized()
                self.firing = True
        else:
            if self.held_mouse and player_pos is not None:
                mx, my = self.mouse_pos[0] / scale, self.mouse_pos[1] / scale
                delta = Vec2(mx - player_pos.x, my - player_pos.y)
                if delta.length_sq() > 1e-6:
                    self.fire_dir = delta.normalized()
                    self.firing = True

    def _autopilot(self, frame: int) -> None:
        """不依赖窗口焦点的确定性输入，用于冒烟测试与长稳测试。"""
        phase = (frame // 45) % 4
        self.move = (Vec2(1, 0), Vec2(0, 1), Vec2(-1, 0), Vec2(0, -1))[phase]
        angle = (frame // 30) % 8 * (math.tau / 8)
        self.fire_dir = Vec2(math.cos(angle), math.sin(angle))
        self.firing = True
        if frame % 180 == 90:
            self.edges.add("interact")
