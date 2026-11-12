# -*- coding: utf-8 -*-
"""存档：中文往返、默认值、迁移、损坏恢复、原子写与成绩结算。"""
import json
import tempfile
import unittest
from pathlib import Path

from core import save


class TestSave(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "save.json"

    def tearDown(self):
        self.tmp.cleanup()

    def test_chinese_roundtrip(self):
        data = save.default_data()
        data["settings"]["input_mode"] = "mouse"
        data["run"] = {"seed": "中文种子测试", "note": "地牢·第六层"}
        self.assertTrue(save.save(data, self.path))
        loaded = save.load(self.path)
        self.assertEqual(loaded["run"]["seed"], "中文种子测试")
        self.assertEqual(loaded["run"]["note"], "地牢·第六层")
        self.assertEqual(loaded["settings"]["input_mode"], "mouse")
        self.assertTrue(self.path.read_text(encoding="utf-8").find("中文") >= 0)

    def test_missing_fields_are_filled(self):
        self.path.write_text(json.dumps({"best": {"floor": 4}}), encoding="utf-8")
        loaded = save.load(self.path)
        self.assertEqual(loaded["best"]["floor"], 4)
        self.assertEqual(loaded["best"]["kills"], 0)
        self.assertEqual(loaded["settings"]["scale"], 2)
        self.assertEqual(loaded["schema"], save.SCHEMA_VERSION)

    def test_v1_migration(self):
        legacy = {"version": 1, "schema": 1, "best_depth": 5,
                  "best_kills": 12, "settings": {"input_mode": "mouse"}}
        self.path.write_text(json.dumps(legacy), encoding="utf-8")
        loaded = save.load(self.path)
        self.assertEqual(loaded["schema"], 2)
        self.assertEqual(loaded["best"]["floor"], 5)
        self.assertEqual(loaded["best"]["kills"], 12)
        self.assertNotIn("best_depth", loaded)
        self.assertEqual(loaded["settings"]["show_fps"], False)

    def test_corrupt_file_is_backed_up_and_rebuilt(self):
        self.path.write_text("{ this is not json", encoding="utf-8")
        loaded = save.load(self.path)
        self.assertEqual(loaded, save.migrate(save.default_data()))
        self.assertTrue(self.path.with_name("save.json.bak").is_file())

    def test_non_object_root_is_rejected(self):
        self.path.write_text("[1, 2, 3]", encoding="utf-8")
        loaded = save.load(self.path)
        self.assertIsInstance(loaded, dict)
        self.assertEqual(loaded["schema"], save.SCHEMA_VERSION)

    def test_atomic_write_leaves_no_tmp(self):
        data = save.default_data()
        self.assertTrue(save.save(data, self.path))
        self.assertTrue(self.path.is_file())
        self.assertFalse(self.path.with_name("save.json.tmp").exists())

    def test_record_run_updates_best_and_clears_run(self):
        data = save.default_data()
        data["run"] = {"floor": 3}
        save.record_run(data, floor=4, kills=17, won=False, elapsed=123.4, seed="S1")
        self.assertEqual(data["best"]["floor"], 4)
        self.assertEqual(data["best"]["kills"], 17)
        self.assertIsNone(data["run"])
        self.assertIn(4, data["unlocks"]["floors_reached"])
        save.record_run(data, floor=6, kills=9, won=True, elapsed=200.0, seed="S2")
        self.assertEqual(data["best"]["floor"], 6)
        self.assertEqual(data["best"]["kills"], 17)
        self.assertEqual(data["best"]["wins"], 1)
        self.assertEqual(data["best"]["time"], 200.0)


if __name__ == "__main__":
    unittest.main()
