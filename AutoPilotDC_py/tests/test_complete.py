# -*- coding: utf-8 -*-
# ============================================================
# AutoPilot DC — Teste: 🎯 Completeaza obiectele (v4.16.3)
#   Rulare:  py -m unittest tests.test_complete
# ============================================================

import os
import sys
import tempfile
import time
import unittest

APP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, APP)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import i18n  # noqa: E402
import ui_theme  # noqa: E402
from complete_ui import CompleteObjectsDialog, has_variables, merge_captured, objects_of_routine  # noqa: E402
from rpr.importer import StepImporter  # noqa: E402
from rpr.model import Locator, LocatorKind, ObjectRepository, UiObject  # noqa: E402
from rpr.storage import RprPaths  # noqa: E402


class MergeTests(unittest.TestCase):
    def test_merge_keeps_name_and_old_locators_as_fallback(self):
        obj = UiObject(name="Buton_Save", object_type="Buton", description="Creat de 📥 Import AI",
                       locators=[Locator(LocatorKind.Role, "button|Save"), Locator(LocatorKind.Text, "Save")])
        cap = UiObject(name="Spy_1", locators=[Locator(LocatorKind.Id, "btnSave"), Locator(LocatorKind.Text, "Save")],
                       frame_path=["iframe#main"], context="https://app/x")
        n = merge_captured(obj, cap)
        self.assertEqual(n, 2)
        self.assertEqual(obj.name, "Buton_Save")
        self.assertEqual([(str(l.kind), l.value) for l in obj.locators],
                         [("Id", "btnSave"), ("Text", "Save"), ("Role", "button|Save")])
        self.assertEqual(obj.frame_path, ["iframe#main"])
        self.assertEqual(obj.context, "https://app/x")
        self.assertEqual(obj.description, "Creat de 📥 Import AI")

    def test_objects_of_routine_in_order_once(self):
        repo = ObjectRepository()
        res = StepImporter(repo).parse('CLICK button "B"\nCLICK button "A"\nCLICK button "B"\n'
                                       'IF visible text "C"\n  LOG "x"\nEND')
        for o in res.new_objects:
            repo.add(o)
        self.assertEqual([o.name for o in objects_of_routine(res.routine, repo)], ["Buton_B", "Buton_A", "Text_C"])
        self.assertTrue(has_variables(UiObject(locators=[Locator(LocatorKind.Text, "{Rand.ID}")])))

    def test_state_text(self):
        i18n.load("ro")
        st = CompleteObjectsDialog._state_of
        self.assertTrue(st({"found": False}).startswith("✖"))
        self.assertTrue(st({"found": True, "counts": [(None, 2), (None, 3)]}).startswith("⚠ 2"))
        self.assertTrue(st({"found": True, "counts": [(None, 1), (None, 4)]}).startswith("✔"))


class _FakeWeb:
    is_open = True

    def __init__(self):
        self.page = {"Save"}

    def check_object(self, o):
        return {"found": o.captured_text in self.page, "counts": [(None, 1)]}

    def capture_object(self, hint, folder):
        return UiObject(name="x", locators=[Locator(LocatorKind.Css, "#lipsa")])

    def cancel_spy(self):
        pass


class DialogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            import tkinter as tk
            cls.root = tk.Tk()
            cls.root.geometry("1366x740")
        except Exception as ex:  # noqa: BLE001 — fara ecran (CI)
            raise unittest.SkipTest(f"fara afisaj: {ex}")
        from test_views import COLORS
        cls.d = tempfile.mkdtemp(prefix="apdc_complete_")
        cls.old_root, cls.old_aspect = RprPaths.root, ui_theme._SETTINGS
        RprPaths.root = os.path.join(cls.d, "Studio")
        ui_theme._SETTINGS = os.path.join(cls.d, "aspect.json")
        import studio_ui
        cls.studio_ui = studio_ui
        cls.p = studio_ui.StudioPanel(cls.root, COLORS)
        cls.p.pack(fill="both", expand=True)
        cls.root.update()

    @classmethod
    def tearDownClass(cls):
        RprPaths.root, ui_theme._SETTINGS = cls.old_root, cls.old_aspect
        cls.root.destroy()

    def _wait(self, w):
        t0 = time.time()
        while w._job is not None and time.time() - t0 < 10:
            self.root.update()
            time.sleep(0.02)
        self.root.update()

    def test_check_all_then_mark_missing(self):
        p = self.p
        res = StepImporter(p.repo).parse('CLICK button "Save"\nCLICK button "Lipsa"')
        orig = self.studio_ui.choice_dialog
        self.studio_ui.choice_dialog = lambda *a, **k: "Mai tarziu"
        try:
            self.assertTrue(p.open_imported(res.routine, res.new_objects))
            self.root.update()
            time.sleep(0.3)
            self.root.update()
        finally:
            self.studio_ui.choice_dialog = orig
        fake = _FakeWeb()
        p.web = lambda: fake
        p._ask_url_if_closed = lambda: None
        try:
            p.show_complete_objects()
            w = p._complete_win
            w.check_all()
            self._wait(w)
            self.assertTrue(w.state[0].startswith("✔"))
            self.assertTrue(w.state[1].startswith("✖"))
            self.assertEqual(w.tree.selection(), ("1",))   # merge singur la primul negasit
            w.mark()
            self._wait(w)
            obj = p.repo.find("Buton_Lipsa")
            self.assertEqual(obj.locators[0].value, "#lipsa")
            self.assertTrue(w.state[1].startswith("🎯"))
            self.assertFalse(p.busy)
            w.destroy()
        finally:
            del p.web
            del p._ask_url_if_closed


if __name__ == "__main__":
    unittest.main()
