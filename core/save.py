# -*- coding: utf-8 -*-
"""本地存档：JSON 读写、默认值补全、版本迁移、损坏恢复、原子写入。

L1 纯逻辑模块。存档损坏时只警告 + 备份，绝不抛异常打断游戏。
"""
from __future__ import annotations

import json
import os
import shutil
import time
from pathlib import Path

from settings import INPUT_KEYBOARD, SAVE_FILE

SCHEMA_VERSION = 2


def default_data() -> dict:
    return {
        "version": SCHEMA_VERSION,
        "schema": SCHEMA_VERSION,
        "updated_at": "",
        "best": {
            "floor": 0,
            "kills": 0,
            "wins": 0,
            "time": 0.0,
            "seed": "",
        },
        "unlocks": {
            "items": [],
            "floors_reached": [],
        },
        "settings": {
            "input_mode": INPUT_KEYBOARD,
            "scale": 2,
            "show_fps": False,
        },
        "run": None,
    }


def _deep_merge(data: dict, defaults: dict) -> dict:
    """递归补齐缺失字段，保留已有值；类型明显不符时回退默认值。"""
    out = dict(defaults)
    for key, value in data.items():
        if key in defaults and isinstance(defaults[key], dict):
            out[key] = _deep_merge(value if isinstance(value, dict) else {}, defaults[key])
        elif key in defaults:
            expected = defaults[key]
            if expected is None or isinstance(value, type(expected)):
                out[key] = value
        else:
            out[key] = value
    return out


def _v1_to_v2(data: dict) -> dict:
    """历史版本迁移示例：v1 把成绩放在顶层，v2 收拢进 best。"""
    best = dict(data.get("best") or {})
    if "best_depth" in data:
        best["floor"] = max(best.get("floor", 0), int(data.pop("best_depth", 0)))
    if "best_kills" in data:
        best["kills"] = max(best.get("kills", 0), int(data.pop("best_kills", 0)))
    for legacy in ("best_depth", "best_kills", "best_wins"):
        data.pop(legacy, None)
    data["best"] = best
    data["schema"] = 2
    data["version"] = 2
    return data


MIGRATIONS = {1: _v1_to_v2}


def migrate(data: dict) -> dict:
    version = int(data.get("schema", SCHEMA_VERSION))
    while version < SCHEMA_VERSION:
        step = MIGRATIONS.get(version)
        if step is None:
            data["schema"] = SCHEMA_VERSION
            data["version"] = SCHEMA_VERSION
            break
        data = step(data)
        version = int(data.get("schema", version + 1))
    return _deep_merge(data, default_data())


def load(path=None) -> dict:
    """读取存档；文件不存在 / 损坏 / 权限异常时返回默认档，损坏文件留 .bak 备份。"""
    path = Path(path) if path else Path(SAVE_FILE)
    if not path.exists():
        return migrate(default_data())
    try:
        raw = path.read_text(encoding="utf-8")
        data = json.loads(raw)
        if not isinstance(data, dict):
            raise ValueError("save root is not an object")
        return migrate(data)
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        try:
            shutil.copy2(path, path.with_name(path.name + ".bak"))
        except OSError:
            pass
        print(f"[save] 存档读取失败，已备份并重建：{exc}")
        return migrate(default_data())


def save(data: dict, path=None) -> bool:
    """原子写入：先写 .tmp 再 os.replace，避免中途退出写坏存档。"""
    path = Path(path) if path else Path(SAVE_FILE)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = dict(data)
        payload["schema"] = SCHEMA_VERSION
        payload["version"] = SCHEMA_VERSION
        payload["updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
        tmp = path.with_name(path.name + ".tmp")
        tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(tmp, path)
        return True
    except (OSError, TypeError, ValueError) as exc:
        print(f"[save] 存档写入失败：{exc}")
        return False


def clear_run(data: dict) -> dict:
    data["run"] = None
    return data


def record_run(data: dict, *, floor: int, kills: int, won: bool,
               elapsed: float, seed: str) -> dict:
    """结算：更新历史最佳，并清空断点。返回被修改的同一 dict。"""
    best = data.setdefault("best", default_data()["best"])
    best["floor"] = max(int(best.get("floor", 0)), int(floor))
    best["kills"] = max(int(best.get("kills", 0)), int(kills))
    best["wins"] = int(best.get("wins", 0)) + (1 if won else 0)
    previous = float(best.get("time", 0.0))
    if won and (previous <= 0 or elapsed < previous):
        best["time"] = round(float(elapsed), 2)
    best["seed"] = str(seed)
    reached = data.setdefault("unlocks", {}).setdefault("floors_reached", [])
    if floor not in reached:
        reached.append(floor)
    return clear_run(data)
