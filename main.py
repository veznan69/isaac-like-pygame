# -*- coding: utf-8 -*-
"""游戏入口。

常用命令：
    python main.py                          正常游玩（标题界面可输入种子）
    python main.py --seed DEMO-1            用指定种子直接开局
    python main.py --no-assets              强制几何占位模式
    python main.py --smoke --seconds 3      弹窗 3 秒自动截图并退出
    python main.py --headless --smoke       无窗口冒烟（CI 用）
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# 音频驱动设为 dummy：本期不做音效，避免无音频设备时初始化卡顿
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from settings import INPUT_KEYBOARD, INPUT_MOUSE, LOGICAL_H, LOGICAL_W, SHOT_DIR, WINDOW_H, WINDOW_W


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="泪之地牢 —— Python + pygame 俯视角 roguelike")
    parser.add_argument("--seed", default=None, help="指定随机种子（可复现同一局地牢）")
    parser.add_argument("--mode", choices=(INPUT_KEYBOARD, INPUT_MOUSE), default=None,
                        help="输入模式，默认读取存档设置")
    parser.add_argument("--no-assets", action="store_true", help="不使用图片素材，全部几何占位")
    parser.add_argument("--headless", action="store_true", help="不弹真实窗口（SDL dummy 驱动）")
    parser.add_argument("--smoke", action="store_true", help="冒烟测试：自动驾驶 + 定时退出 + 截图")
    parser.add_argument("--seconds", type=float, default=3.0, help="冒烟测试运行时长（秒）")
    parser.add_argument("--shot", default=None, help="冒烟截图路径")
    parser.add_argument("--stats", action="store_true", help="打印 FPS 统计")
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    if args.headless:
        os.environ["SDL_VIDEODRIVER"] = "dummy"

    pygame.init()
    pygame.display.set_caption("泪之地牢 · TEARS OF THE DUNGEON")
    screen = pygame.display.set_mode((WINDOW_W, WINDOW_H), pygame.DOUBLEBUF)
    logical = pygame.Surface((LOGICAL_W, LOGICAL_H))

    # AssetBank 在 set_mode 之后创建，确保 convert_alpha 可用
    from core.game import Game
    from core.loop import Loop

    game = Game(screen, logical, seed=args.seed, input_mode=args.mode,
                no_assets=args.no_assets, autopilot=args.smoke)
    if args.smoke or args.seed:
        game.start_run(args.seed or "SMOKE-1")

    shot = args.shot
    if args.smoke and shot is None:
        shot = str(SHOT_DIR / "smoke.png")
    seconds = args.seconds if args.smoke else None

    loop = Loop(game, screen, logical)
    result = loop.run(seconds=seconds, shot=shot, collect_stats=args.stats)
    if args.stats or args.smoke:
        print(f"[run] frames={result['frames']} steps={result['steps']} "
              f"elapsed={result['elapsed']}s avg_fps={result['avg_fps']} "
              f"min_fps={result['min_fps']}")
        if result["shot"]:
            print(f"[run] screenshot={result['shot']}")
    pygame.quit()
    return 0


if __name__ == "__main__":
    sys.exit(main())
