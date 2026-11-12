# -*- coding: utf-8 -*-
"""像素素材后处理管线：AI 原图 -> 去背 -> 统一色板 -> 切格 -> sprite sheet + manifest。

设计要点：
  * 即使 assets/raw/ 里一张 AI 图都没有，也会用程序化几何图生成完整 manifest，
    游戏永远能加载素材，不会因为缺图崩溃或阻塞开发。
  * AI 图生成后放进 assets/raw/<名字>.png，重跑本脚本即可增量升级对应 sprite。
  * 所有图统一吸附到 16 色板，缓解多张 AI 图风格不一致的问题。

用法：
    python tools/make_sprites.py                 # 构建
    python tools/make_sprites.py --validate     # 只校验现有产物
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw

TOOLS_DIR = Path(__file__).resolve().parent
ROOT = TOOLS_DIR.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from settings import ASSETS_DIR, PALETTE, RAW_DIR, SPRITES_DIR, SHEETS_FILE, MANIFEST_FILE  # noqa: E402
from items.item_defs import ALL_ITEM_IDS  # noqa: E402

PALETTE_COLORS = list(PALETTE.values())
CELL = 32
BOSS_CELL = 64
COLS = 8

PLAYER_KEYS = ("player_idle", "player_down", "player_up", "player_side")
ENEMY_KEYS = ("enemy_fly", "enemy_chaser", "enemy_hopper",
              "enemy_shooter", "enemy_splitter", "enemy_orbiter")
BOSS_KEYS = ("boss_idle", "boss_angry")
TEAR_KEYS = ("tear_blue", "tear_red")
PICKUP_KEYS = ("pickup_heart", "pickup_coin", "pickup_key", "pickup_bomb")
PROP_KEYS = ("prop_rock", "prop_fire", "prop_pedestal")
MISC_KEYS = ("item_unknown", "decor_tile", "door_ornament")
ITEM_KEYS = tuple(f"item_{item_id}" for item_id in ALL_ITEM_IDS)

ALL_SPRITE_KEYS = (PLAYER_KEYS + ENEMY_KEYS + BOSS_KEYS + TEAR_KEYS
                   + PICKUP_KEYS + PROP_KEYS + MISC_KEYS + ITEM_KEYS)

# (raw 文件名, 处理方式, 产出的 sprite keys)
# single : 一图一 sprite；pose : 一图派生 4 个朝向；grid4 : 2x2 图标网格切 4 个
RAW_SPECS = [
    ("player.png", "pose", PLAYER_KEYS),
    ("enemy_fly.png", "single", ("enemy_fly",)),
    ("enemy_chaser.png", "single", ("enemy_chaser",)),
    ("enemy_hopper.png", "single", ("enemy_hopper",)),
    ("enemy_shooter.png", "single", ("enemy_shooter",)),
    ("enemy_splitter.png", "single", ("enemy_splitter",)),
    ("enemy_orbiter.png", "single", ("enemy_orbiter",)),
    ("boss_idle.png", "single", ("boss_idle",)),
    ("boss_angry.png", "single", ("boss_angry",)),
    ("tear_blue.png", "single", ("tear_blue",)),
    ("tear_red.png", "single", ("tear_red",)),
    ("pickup_heart.png", "single", ("pickup_heart",)),
    ("pickup_coin.png", "single", ("pickup_coin",)),
    ("pickup_key.png", "single", ("pickup_key",)),
    ("pickup_bomb.png", "single", ("pickup_bomb",)),
    ("prop_rock.png", "single", ("prop_rock",)),
    ("prop_fire.png", "single", ("prop_fire",)),
    ("prop_pedestal.png", "single", ("prop_pedestal",)),
    ("misc.png", "single", MISC_KEYS),
    ("items_1.png", "grid4", ITEM_KEYS[0:4]),
    ("items_2.png", "grid4", ITEM_KEYS[4:8]),
    ("items_3.png", "grid4", ITEM_KEYS[8:12]),
    ("items_4.png", "grid4", ITEM_KEYS[12:16]),
    ("items_5.png", "grid4", ITEM_KEYS[16:20]),
    ("floor_decor.png", "single", ("door_ornament",)),
    ("decor.png", "single", ("decor_tile",)),
]

SHEET_GROUPS = {
    "chars": {"cell": CELL, "keys": PLAYER_KEYS + ENEMY_KEYS},
    "bosses": {"cell": BOSS_CELL, "keys": BOSS_KEYS},
    "fx": {"cell": CELL, "keys": TEAR_KEYS + PICKUP_KEYS + ("item_unknown",)},
    "props": {"cell": CELL, "keys": PROP_KEYS + ("decor_tile", "door_ornament")},
    "items": {"cell": CELL, "keys": ITEM_KEYS},
}


# ---------- 图像处理 ----------

def _color_distance(a, b) -> float:
    return (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2


def clean_background(img: Image.Image) -> Image.Image:
    """透明底校验 + 洋红/纯色底兜底去背 + 边缘半透明清理。"""
    img = img.convert("RGBA")
    img.thumbnail((256, 256), Image.Resampling.LANCZOS)
    pixels = img.load()
    w, h = img.size

    corners = [pixels[0, 0], pixels[w - 1, 0], pixels[0, h - 1], pixels[w - 1, h - 1]]
    opaque_bg = all(c[3] > 200 for c in corners)
    bg = tuple(sum(c[i] for c in corners) // 4 for i in range(3)) if opaque_bg else None

    for y in range(h):
        for x in range(w):
            r, g, b, a = pixels[x, y]
            if a < 16:
                pixels[x, y] = (0, 0, 0, 0)
                continue
            magenta = r > 190 and g < 90 and b > 190
            solid_bg = bool(bg) and _color_distance((r, g, b), bg) < 2200
            if magenta or solid_bg:
                pixels[x, y] = (0, 0, 0, 0)
            elif a < 200:
                # 边缘羽化像素直接压成不透明，避免缩放后出现灰边
                pixels[x, y] = (r, g, b, 255)
    return img


def snap_to_palette(img: Image.Image) -> Image.Image:
    """把每个不透明像素吸附到最近的 16 色调色板颜色，统一多张 AI 图的色调。"""
    pixels = img.load()
    for y in range(img.height):
        for x in range(img.width):
            r, g, b, a = pixels[x, y]
            if a < 16:
                continue
            best = min(PALETTE_COLORS, key=lambda c: _color_distance((r, g, b), c))
            pixels[x, y] = (best[0], best[1], best[2], 255)
    return img


def normalize(img: Image.Image, size: int) -> Image.Image:
    """裁剪透明边 -> 补成正方形 -> 两阶段缩放得到硬像素边缘。"""
    alpha = img.getchannel("A")
    bbox = alpha.getbbox()
    if bbox:
        img = img.crop(bbox)
    side = max(img.width, img.height)
    square = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    square.paste(img, ((side - img.width) // 2, (side - img.height) // 2))
    large = square.resize((size * 4, size * 4), Image.Resampling.LANCZOS)
    return large.resize((size, size), Image.Resampling.NEAREST)


def make_placeholder(key: str, size: int) -> Image.Image:
    """没有任何 AI 原图时的程序化像素替身，风格与色板完全一致。"""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    ink = PALETTE["ink"]
    if key.startswith("player"):
        color = PALETTE["white"]
    elif key.startswith("boss"):
        color = PALETTE["blood"]
    elif key.startswith("enemy"):
        color = PALETTE["purple"]
    elif "tear" in key:
        color = PALETTE["cyan"] if "blue" in key else PALETTE["red"]
    elif "heart" in key:
        color = PALETTE["red"]
    elif "coin" in key or "gold" in key:
        color = PALETTE["gold"]
    elif key.startswith("item_"):
        color = PALETTE["cyan"]
    elif "fire" in key:
        color = PALETTE["orange"]
    else:
        color = PALETTE["slate"]

    pad = max(2, size // 8)
    if key.startswith("prop_") or "tile" in key or "ornament" in key:
        draw.rectangle((pad, pad, size - pad - 1, size - pad - 1), fill=color, outline=ink, width=2)
        draw.rectangle((pad + 3, pad + 3, pad + 7, pad + 5), fill=PALETTE["light"])
    elif key.startswith("item_"):
        draw.polygon([(size // 2, pad), (size - pad, size // 2),
                      (size // 2, size - pad), (pad, size // 2)], fill=color, outline=ink)
        draw.ellipse((size // 2 - 3, size // 2 - 3, size // 2 + 2, size // 2 + 2),
                     fill=PALETTE["white"])
    else:
        draw.ellipse((pad, pad, size - pad - 1, size - pad - 1), fill=color, outline=ink, width=2)
        r = max(2, size // 8)
        draw.ellipse((pad + 4, pad + 4, pad + 4 + r, pad + 4 + r), fill=PALETTE["white"])
    return img


def _load_single(path: Path, size: int) -> Image.Image:
    raw = Image.open(path)
    return normalize(snap_to_palette(clean_background(raw)), size)


def _derive_poses(base: Image.Image) -> list[Image.Image]:
    """一张正面立绘派生四个朝向：正面 / 正面 / 背影(垂直翻转) / 侧面(水平翻转)。"""
    return [
        base,
        base,
        base.transpose(Image.Transpose.FLIP_TOP_BOTTOM),
        base.transpose(Image.Transpose.FLIP_LEFT_RIGHT),
    ]


def _split_grid4(img: Image.Image, size: int) -> list[Image.Image]:
    """把 2x2 图标网格切成 4 个独立 sprite；每格单独去背裁剪，容忍对不齐。"""
    w, h = img.size
    result = []
    for row in range(2):
        for col in range(2):
            cell = img.crop((col * w // 2, row * h // 2,
                             (col + 1) * w // 2, (row + 1) * h // 2))
            result.append(normalize(snap_to_palette(cell), size))
    return result


def build_sprites(raw_dir: Path = RAW_DIR, sprites_dir: Path = SPRITES_DIR) -> dict:
    """返回 {sprite_key: PIL.Image}；缺图自动用程序化替身补齐。"""
    result: dict[str, Image.Image] = {}
    size_by_key = {key: BOSS_CELL for key in BOSS_KEYS}
    for key in ALL_SPRITE_KEYS:
        result[key] = make_placeholder(key, size_by_key.get(key, CELL))

    found = 0
    for filename, mode, keys in RAW_SPECS:
        path = raw_dir / filename
        if not path.is_file():
            continue
        try:
            size = BOSS_CELL if keys[0] in BOSS_KEYS else CELL
            if mode == "grid4":
                raw = clean_background(Image.open(path))
                pieces = _split_grid4(raw, size)
                for key, piece in zip(keys, pieces):
                    result[key] = piece
            elif mode == "pose":
                base = _load_single(path, size)
                for key, piece in zip(keys, _derive_poses(base)):
                    result[key] = piece
            else:
                base = _load_single(path, size)
                for key in keys:
                    result[key] = base
            found += 1
        except (OSError, ValueError) as exc:
            print(f"[sprites] 跳过无法处理的 {filename}: {exc}")
    print(f"[sprites] 已读取 {found}/{len(RAW_SPECS)} 张 AI 原图，其余使用程序化替身")
    return result


def write_sheets(sprites: dict, sprites_dir: Path = SPRITES_DIR) -> tuple[dict, dict]:
    sprites_dir.mkdir(parents=True, exist_ok=True)
    sheets: dict[str, dict] = {}
    manifest: dict[str, dict] = {}

    for name, group in SHEET_GROUPS.items():
        cell = group["cell"]
        keys = list(group["keys"])
        cols = min(COLS, len(keys)) or 1
        rows = max(1, math.ceil(len(keys) / cols))
        sheet = Image.new("RGBA", (cols * cell, rows * cell), (0, 0, 0, 0))
        for index, key in enumerate(keys):
            image = sprites[key]
            if image.size != (cell, cell):
                image = image.resize((cell, cell), Image.Resampling.NEAREST)
            sheet.alpha_composite(image, ((index % cols) * cell, (index // cols) * cell))
            manifest[key] = {"sheet": name, "index": index, "flip": False}
        filename = f"{name}.png"
        sheet.save(sprites_dir / filename)
        sheets[name] = {"file": filename, "cell": [cell, cell],
                        "cols": cols, "rows": rows}
    return sheets, manifest


def validate(sprites_dir: Path = SPRITES_DIR, sheets_file: Path = SHEETS_FILE,
             manifest_file: Path = MANIFEST_FILE) -> list[str]:
    """返回问题列表；空列表表示校验通过。"""
    problems: list[str] = []
    if not sheets_file.is_file() or not manifest_file.is_file():
        return ["缺少 sheets.json 或 manifest.json"]
    try:
        sheets = json.loads(sheets_file.read_text(encoding="utf-8"))
        manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return [f"元数据无法解析：{exc}"]

    for name, info in sheets.items():
        path = sprites_dir / info["file"]
        if not path.is_file():
            problems.append(f"{name}: 缺少图片 {info['file']}")
            continue
        with Image.open(path) as img:
            if img.mode != "RGBA":
                problems.append(f"{name}: 图片模式应为 RGBA，实际 {img.mode}")
            expected = (info["cols"] * info["cell"][0], info["rows"] * info["cell"][1])
            if img.size != expected:
                problems.append(f"{name}: 尺寸 {img.size} != {expected}")
    for key in ALL_SPRITE_KEYS:
        if key not in manifest:
            problems.append(f"manifest 缺少 {key}")
    for item_id in ALL_ITEM_IDS:
        if f"item_{item_id}" not in manifest:
            problems.append(f"道具 {item_id} 没有对应 sprite")
    for key, entry in manifest.items():
        info = sheets.get(entry.get("sheet", ""))
        if not info:
            problems.append(f"{key}: 引用了不存在的 sheet")
            continue
        if not (0 <= int(entry.get("index", -1)) < info["cols"] * info["rows"]):
            problems.append(f"{key}: index 越界")
    return problems


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="构建像素 sprite sheet")
    parser.add_argument("--raw", default=str(RAW_DIR))
    parser.add_argument("--out", default=str(SPRITES_DIR))
    parser.add_argument("--validate", action="store_true", help="只校验现有产物")
    args = parser.parse_args(argv)

    if args.validate:
        problems = validate(Path(args.out))
        for problem in problems:
            print("  [FAIL]", problem)
        print(f"[validate] {'通过' if not problems else f'{len(problems)} 个问题'}")
        return 0 if not problems else 1

    sprites = build_sprites(Path(args.raw))
    sheets, manifest = write_sheets(sprites, Path(args.out))
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    SHEETS_FILE.write_text(json.dumps(sheets, ensure_ascii=False, indent=2), encoding="utf-8")
    MANIFEST_FILE.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[sprites] 生成 {len(sheets)} 张 sheet / {len(manifest)} 个 sprite")
    problems = validate(Path(args.out))
    for problem in problems:
        print("  [FAIL]", problem)
    return 0 if not problems else 1


if __name__ == "__main__":
    sys.exit(main())
