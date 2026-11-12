# -*- coding: utf-8 -*-
"""全局常量与唯一路径来源。

本模块属于分层架构的 L0，禁止 import pygame，必须能被无显示环境的测试安全导入。
所有路径一律由 BASE_DIR 推导，不依赖当前工作目录。
"""
from enum import Enum, IntFlag
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
ASSETS_DIR = BASE_DIR / "assets"
SPRITES_DIR = ASSETS_DIR / "sprites"
RAW_DIR = ASSETS_DIR / "raw"
SAVE_DIR = BASE_DIR / "saves"
SHOT_DIR = BASE_DIR / "screenshots"
SAVE_FILE = SAVE_DIR / "save.json"
MANIFEST_FILE = ASSETS_DIR / "manifest.json"
SHEETS_FILE = ASSETS_DIR / "sheets.json"

TILE = 32
ROOM_COLS, ROOM_ROWS = 15, 9
LOGICAL_W, LOGICAL_H = ROOM_COLS * TILE, ROOM_ROWS * TILE   # 480 x 288
SCALE = 2
WINDOW_W, WINDOW_H = LOGICAL_W * SCALE, LOGICAL_H * SCALE   # 960 x 576

# 房间内墙包围的可活动矩形 (x, y, w, h)，实体中心不得越界
ARENA_X = TILE + 6
ARENA_Y = TILE + 6
ARENA_W = LOGICAL_W - 2 * (TILE + 6)
ARENA_H = LOGICAL_H - 2 * (TILE + 6)

STEP = 1.0 / 60.0
FPS = 60
MAX_FRAME_DT = 0.25
MAX_FLOOR = 6
MAX_STEPS_PER_FRAME = 8

DIRS = {"N": (0, -1), "E": (1, 0), "S": (0, 1), "W": (-1, 0)}
OPPOSITE = {"N": "S", "S": "N", "E": "W", "W": "E"}
DIR_ORDER = ("N", "E", "S", "W")
# 四扇门所在的格子坐标（墙上开口）
DOOR_CELLS = {"N": (7, 0), "E": (14, 4), "S": (7, 8), "W": (0, 4)}
# 玩家换房后的落点（门内侧）
DOOR_SPAWN = {"N": (240, 64), "E": (416, 144), "S": (240, 224), "W": (64, 144)}


class Group(IntFlag):
    """碰撞分组位掩码，配对规则集中在 core/collision.py。"""
    PLAYER = 1 << 0
    ENEMY = 1 << 1
    TEAR_PLAYER = 1 << 2
    TEAR_ENEMY = 1 << 3
    PICKUP = 1 << 4
    PROP = 1 << 5
    DOOR = 1 << 6


class RoomType(str, Enum):
    START = "start"
    NORMAL = "normal"
    BOSS = "boss"
    TREASURE = "treasure"
    SHOP = "shop"


class State(str, Enum):
    TITLE = "title"
    PLAYING = "playing"
    PAUSED = "paused"
    ITEM_SELECT = "item_select"
    DEAD = "dead"
    WIN = "win"


class PickupKind(str, Enum):
    HEART = "heart"
    COIN = "coin"
    KEY = "key"
    BOMB = "bomb"
    ITEM = "item"


INPUT_KEYBOARD = "keyboard"   # WASD 移动 + 方向键射击
INPUT_MOUSE = "mouse"         # WASD 移动 + 鼠标瞄准射击

# 16 色像素调色板，须与 tools/prompts.md 中给图像生成的色板一致
PALETTE = {
    "ink": (24, 20, 34),
    "dark": (45, 40, 62),
    "slate": (74, 68, 94),
    "gray": (118, 112, 138),
    "light": (186, 182, 204),
    "white": (240, 238, 248),
    "red": (208, 62, 78),
    "blood": (138, 32, 52),
    "orange": (232, 140, 58),
    "gold": (246, 202, 88),
    "green": (104, 184, 104),
    "teal": (64, 156, 168),
    "blue": (72, 116, 208),
    "cyan": (128, 216, 232),
    "purple": (138, 88, 190),
    "pink": (226, 122, 168),
}

COL_BG = PALETTE["ink"]
COL_WALL = (58, 52, 78)
COL_WALL_EDGE = (96, 86, 122)
COL_WALL_SHADE = (30, 26, 42)
COL_FLOOR = (40, 35, 54)
COL_FLOOR_ALT = (45, 40, 61)
COL_GRID = (53, 47, 70)
COL_TEXT = PALETTE["white"]
COL_TEXT_DIM = PALETTE["gray"]
COL_HP = PALETTE["red"]
COL_HUD_BG = (18, 15, 26)

# 中文渲染降级链，由 ui/fonts.py 依次尝试
FONT_CANDIDATES = ("msyh.ttc", "MicrosoftYaHei", "SimHei", "simsun.ttc", "NotoSansCJK")
FONT_FALLBACK = "freesansbold.ttf"

PLAYER_RADIUS = 9
TEAR_RADIUS = 5
PICKUP_RADIUS = 8
INVULN_STEPS = 45           # 受击后无敌帧（固定步）
MAGENTA = (255, 0, 255)     # 素材去背检测用的洋红色


def floor_difficulty(floor: int) -> float:
    """楼层难度系数：1 层 1.00，6 层 1.75。"""
    return 1.0 + 0.15 * (floor - 1)


def room_count(floor: int) -> int:
    """每层房间数量，随层数增长但设置上限。"""
    return min(10 + 2 * floor, 20)
