# -*- coding: utf-8 -*-
# ============================================================
# AutoPilot DC v4.14 — Teste: contrast, unde se salveaza fisierele,
# aplicatia pentru filme, drag and drop in arborele Studio.
#   Rulare:  py -m unittest tests.test_aspect
# ============================================================

import json
import os
import shutil
import sys
import tempfile
import unittest

APP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, APP)

import ui_theme  # noqa: E402
from rpr import locations  # noqa: E402
from rpr.storage import RprPaths  # noqa: E402


class ContrastTests(unittest.TestCase):
    def test_contrast_ratio(self):
        self.assertAlmostEqual(21.0, ui_theme.contrast("#000000", "#FFFFFF"), places=1)
        self.assertAlmostEqual(1.0, ui_theme.contrast("#FFFFFF", "white"), places=2)

    def test_text_on_picks_readable_color(self):
        self.assertEqual("white", ui_theme.text_on("#1E1E2E"))
        self.assertEqual(ui_theme.DARK_TEXT, ui_theme.text_on("#F0F4F8"))
        self.assertEqual(ui_theme.DARK_TEXT, ui_theme.text_on("#FF8800"))   # portocaliu: text inchis

    def test_readable_adjusts_only_when_needed(self):
        self.assertEqual("#FFFFFF", ui_theme.readable("#FFFFFF", "#1E1E2E"))
        fixed = ui_theme.readable("#3CCF6E", "#FFFFFF")      # verde deschis pe alb
        self.assertGreaterEqual(ui_theme.contrast(fixed, "#FFFFFF"), 4.5)

    def test_text_size_setting(self):
        old = ui_theme._SETTINGS
        ui_theme._SETTINGS = os.path.join(tempfile.mkdtemp(), "aspect.json")
        try:
            self.assertEqual("normal", ui_theme.text_size())
            ui_theme.save(text_size="large")
            self.assertEqual("large", ui_theme.text_size())
            self.assertAlmostEqual(1.15, ui_theme.text_factor())
            ui_theme.save(text_size="ceva")
            self.assertEqual("normal", ui_theme.text_size())
        finally:
            ui_theme._SETTINGS = old


class LocationsTests(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="apdc_loc_")
        self.old_root = RprPaths.root
        RprPaths.root = os.path.join(self.d, "Studio")
        os.makedirs(RprPaths.root)
        locations.reset()

    def tearDown(self):
        RprPaths.root = self.old_root
        locations.reset()
        shutil.rmtree(self.d, ignore_errors=True)

    def _write(self, **d):
        with open(locations.settings_file(), "w", encoding="utf-8") as f:
            json.dump(d, f)
        locations.reset()

    def test_nothing_set_keeps_old_folders(self):
        self.assertEqual(os.path.join(RprPaths.root, "rutine"), RprPaths.routines())
        self.assertEqual(os.path.join(RprPaths.root, "rezultate"), RprPaths.output())

    def test_common_folder_and_explicit_override(self):
        base = os.path.join(self.d, "Comun")
        own = os.path.join(self.d, "Rezultatele_mele")
        self._write(save_base_folder=base, save_folders={"results": own})
        self.assertEqual(os.path.join(base, "rutine"), RprPaths.routines())
        self.assertEqual(own, RprPaths.output())
        from rpr import scan
        self.assertEqual(os.path.join(base, "obiecte"), scan.libraries_root())
        self.assertTrue(os.path.isdir(os.path.join(base, "rutine")))

    def test_routines_folder_of_manager_wins(self):
        own = os.path.join(self.d, "R")
        self._write(save_base_folder=os.path.join(self.d, "Comun"), routines_folder=own)
        self.assertEqual(own, RprPaths.routines())

    def test_studio_settings_roundtrip_keeps_unknown_fields(self):
        from rpr.drivers.registry import StudioSettings
        self._write(campul_csharp=1)
        s = StudioSettings.load()
        s.save_base_folder = os.path.join(self.d, "Comun")
        s.save_folders = {"libraries": os.path.join(self.d, "L")}
        s.layout = {"left": 0.2, "right": 0.3, "bottom": 0.25}
        s.save()
        t = StudioSettings.load()
        self.assertEqual(s.save_base_folder, t.save_base_folder)
        self.assertEqual(s.save_folders, t.save_folders)
        self.assertEqual(0.3, t.layout["right"])
        with open(locations.settings_file(), encoding="utf-8") as f:
            self.assertEqual(1, json.load(f)["campul_csharp"])
        self.assertEqual(os.path.join(self.d, "L"), locations.folder("libraries"))

    def test_video_folder_follows_common_folder(self):
        try:
            import screen_recorder as sr
        except ImportError as ex:   # PIL.ImageGrab lipseste pe unele Linux
            self.skipTest(str(ex))
        old = sr._SETTINGS
        sr._SETTINGS = os.path.join(self.d, "video.json")
        try:
            v = sr.VideoSettings.load()
            self.assertEqual(sr._legacy_folder(), v.folder)
            v.save()                                   # folderul implicit nu se "ingheata"
            self._write(save_base_folder=os.path.join(self.d, "Comun"))
            self.assertEqual(os.path.join(self.d, "Comun", "filme"), sr.VideoSettings.load().folder)
            v = sr.VideoSettings.load()
            v.folder = os.path.join(self.d, "FilmeleMele")
            v.player = sr.PLAYER_SYSTEM
            v.save()
            w = sr.VideoSettings.load()
            self.assertEqual(os.path.join(self.d, "FilmeleMele"), w.folder)
            self.assertEqual(sr.PLAYER_SYSTEM, w.player)
        finally:
            sr._SETTINGS = old


class StudioDragDropTests(unittest.TestCase):
    """Mutarea pasilor cu mouse-ul: logica din StudioPanel (fara evenimente reale)."""

    @classmethod
    def setUpClass(cls):
        try:
            import tkinter as tk
            cls.root = tk.Tk()
            cls.root.withdraw()
        except Exception as ex:  # noqa: BLE001 — fara ecran (CI)
            raise unittest.SkipTest(f"fara afisaj: {ex}")
        cls.d = tempfile.mkdtemp(prefix="apdc_dnd_")
        cls.old_root = RprPaths.root
        RprPaths.root = os.path.join(cls.d, "Studio")
        import studio_ui
        colors = {"bg_main": "#1E1E2E", "bg_panel": "#252535", "bg_card": "#2A2A3E", "bg_input": "#32324A",
                  "border": "#444466", "primary": "#009999", "accent": "#3DA9E0", "text": "#FFFFFF",
                  "text_dim": "#B4B4D0", "text_muted": "#8A8AAA", "success": "#1F8F4E", "warning": "#FF8800",
                  "danger": "#CC0000", "row_active": "#1A4A4A"}
        cls.p = studio_ui.StudioPanel(cls.root, colors)
        cls.p.pack(fill="both", expand=True)

    @classmethod
    def tearDownClass(cls):
        try:
            cls.p.shutdown()
            cls.root.destroy()
        except Exception:  # noqa: BLE001
            pass
        RprPaths.root = cls.old_root
        shutil.rmtree(cls.d, ignore_errors=True)

    def _routine(self):
        from rpr.model import IfNode, LogNode, LoopNode, Routine
        r = Routine()
        a, b = LogNode(message="A"), LogNode(message="B")
        cond = IfNode()
        loop = LoopNode()
        r.steps = [a, b, cond, loop]
        self.p.routine = r
        self.p.rebuild_tree()
        return r, a, b, cond, loop

    def test_move_down_up_and_into_branch(self):
        r, a, b, cond, loop = self._routine()
        self.p._move_node_to(a, r.steps, 2)          # dupa B
        self.assertEqual([b, a, cond, loop], r.steps)
        self.p._move_node_to(a, r.steps, 0)          # inapoi primul
        self.assertEqual([a, b, cond, loop], r.steps)
        then = cond.branches()[0][1]
        self.p._move_node_to(b, then, 0)             # in "Atunci"
        self.assertIs(then[0], b)
        self.assertNotIn(b, r.steps)
        body = loop.branches()[0][1]
        self.p._move_node_to(b, body, len(body))     # in bucla
        self.assertIs(body[-1], b)
        self.assertNotIn(b, then)
        self.assertTrue(self.p.dirty)

    def test_cannot_move_into_itself(self):
        r, a, b, cond, loop = self._routine()
        body = loop.branches()[0][1]
        body.append(a)
        r.steps.remove(a)
        self.p.rebuild_tree()
        self.p._move_node_to(loop, body, 0)
        self.assertIn(loop, r.steps)
        self.assertNotIn(loop, body)

    def test_insert_at_drop_place(self):
        from rpr.model import LogNode
        r, a, b, cond, loop = self._routine()
        n = LogNode(message="nou")
        self.p._insert_at = (r.steps, 1)
        self.p.insert_node(n)
        self.assertIs(r.steps[1], n)
        self.assertIsNone(self.p._insert_at)


if __name__ == "__main__":
    unittest.main()
