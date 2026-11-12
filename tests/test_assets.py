# -*- coding: utf-8 -*-
"""素材管线：sheet 元数据、切帧、缩放缓存、缺图降级与几何占位。"""
import json
import tempfile
import unittest
from pathlib import Path

import pygame

from core.assets import AssetBank
from core.sprite_sheet import SheetLibrary
from settings import MANIFEST_FILE, SHEETS_FILE, SPRITES_DIR
from tools.make_sprites import ALL_SPRITE_KEYS, build_sprites, validate, write_sheets
from ui.painter import Painter


class TestAssetPipeline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        cls.display = pygame.display.set_mode((64, 64))

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def test_repository_sheets_pass_validation(self):
        self.assertEqual(validate(), [], "仓库内 sprite 产物应通过校验")

    def test_manifest_covers_every_sprite_key(self):
        manifest = json.loads(MANIFEST_FILE.read_text(encoding="utf-8"))
        for key in ALL_SPRITE_KEYS:
            self.assertIn(key, manifest)

    def test_sheet_rects_are_within_bounds(self):
        sheets = json.loads(SHEETS_FILE.read_text(encoding="utf-8"))
        manifest = json.loads(MANIFEST_FILE.read_text(encoding="utf-8"))
        for key, entry in manifest.items():
            info = sheets[entry["sheet"]]
            self.assertLess(entry["index"], info["cols"] * info["rows"], key)

    def test_library_returns_surface_and_handles_missing_key(self):
        library = SheetLibrary()
        self.assertTrue(library.available)
        surface = library.get("player_idle")
        self.assertIsNotNone(surface)
        self.assertEqual(surface.get_size(), (32, 32))
        self.assertIsNone(library.get("__does_not_exist__"))
        self.assertIn("__does_not_exist__", library.missing_keys)

    def test_asset_bank_caches_scaled_surface(self):
        bank = AssetBank()
        first = bank.get("player_idle", 32, 32)
        second = bank.get("player_idle", 32, 32)
        self.assertIs(first, second, "同尺寸取图应命中缓存")
        scaled = bank.get("player_idle", 24, 24)
        self.assertEqual(scaled.get_size(), (24, 24))

    def test_no_assets_mode_returns_none(self):
        bank = AssetBank(no_assets=True)
        self.assertIsNone(bank.get("player_idle", 32, 32))
        self.assertFalse(bank.available)

    def test_painter_draws_geometry_when_sprite_missing(self):
        surface = pygame.Surface((64, 64))
        surface.fill((0, 0, 0))
        painter = Painter(surface, None, no_assets=True)
        painter.sprite("player_idle", 32, 32, 24, 24, (255, 255, 255))
        self.assertNotEqual(tuple(surface.get_at((32, 32))[:3]), (0, 0, 0))

    def test_build_without_any_raw_image_still_produces_valid_sheets(self):
        """零 AI 素材时也要能构建出完整可加载的 sheet（关键降级路径）。"""
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            sprites = build_sprites(raw_dir=out / "empty_raw")
            sheets, manifest = write_sheets(sprites, out)
            sheets_file = out / "sheets.json"
            manifest_file = out / "manifest.json"
            sheets_file.write_text(json.dumps(sheets), encoding="utf-8")
            manifest_file.write_text(json.dumps(manifest), encoding="utf-8")
            self.assertEqual(validate(out, sheets_file, manifest_file), [])
            self.assertEqual(len(manifest), len(ALL_SPRITE_KEYS))


if __name__ == "__main__":
    unittest.main()
