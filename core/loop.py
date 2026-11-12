# -*- coding: utf-8 -*-
"""固定步长主循环。

逻辑以 1/60 秒确定性推进，渲染每帧只做一次整数倍缩放 + flip；
双缓冲与全量重绘保证不出现局部刷新导致的闪烁。
"""
from __future__ import annotations

import time
from pathlib import Path

import pygame

from settings import (FPS, LOGICAL_H, LOGICAL_W, MAX_FRAME_DT,
                      MAX_STEPS_PER_FRAME, STEP, WINDOW_H, WINDOW_W)


class Loop:
    def __init__(self, game, screen, logical_surface) -> None:
        self.game = game
        self.screen = screen
        self.logical = logical_surface
        self.scaled = pygame.Surface((WINDOW_W, WINDOW_H))
        self.clock = pygame.time.Clock()
        self.accumulator = 0.0
        self.frame_durations: list[float] = []

    def run(self, seconds: float | None = None, shot=None, collect_stats: bool = False) -> dict:
        start = time.perf_counter()
        last = start
        frames = 0
        steps = 0
        deadline = (start + seconds) if seconds else None
        running = True

        while running:
            now = time.perf_counter()
            frame_dt = now - last
            last = now
            if frame_dt > 0:
                self.game.display_fps = min(999.0, 1.0 / frame_dt)
            if frame_dt > 0 and collect_stats:
                self.frame_durations.append(frame_dt)

            events = pygame.event.get()
            for event in events:
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.WINDOWFOCUSLOST:
                    self.game.on_focus_lost()
            if self.game.quit_requested:
                running = False

            self.game.handle_events(events, self.game.frame)

            # 失焦回来时 dt 可能很大，钳制后按固定步补齐，避免"死亡螺旋"
            self.accumulator += min(frame_dt, MAX_FRAME_DT)
            step_count = 0
            while self.accumulator >= STEP and step_count < MAX_STEPS_PER_FRAME:
                self.game.fixed_update(STEP)
                self.accumulator -= STEP
                steps += 1
                step_count += 1
            if step_count >= MAX_STEPS_PER_FRAME:
                self.accumulator = 0.0

            self.game.render(self.logical)
            offset = self.game.shake_offset
            pygame.transform.scale(self.logical, (WINDOW_W, WINDOW_H), self.scaled)
            self.screen.fill((0, 0, 0))
            # 抖动通过整帧平移实现，不改动任何逻辑坐标
            self.screen.blit(self.scaled, (int(offset[0]), int(offset[1])))
            pygame.display.flip()
            self.clock.tick(FPS)
            frames += 1

            if deadline is not None and now - start >= seconds:
                if shot:
                    path = Path(shot)
                    path.parent.mkdir(parents=True, exist_ok=True)
                    pygame.image.save(self.screen, str(path))
                    print(f"[smoke] 截图已保存：{path}")
                running = False

        elapsed = time.perf_counter() - start
        durations = [d for d in self.frame_durations if d > 0] or [1 / FPS]
        result = {
            "frames": frames,
            "steps": steps,
            "elapsed": round(elapsed, 2),
            "avg_fps": round(1.0 / (sum(durations) / len(durations)), 1),
            "min_fps": round(1.0 / max(durations), 1),
            "shot": str(shot) if shot else None,
        }
        return result
