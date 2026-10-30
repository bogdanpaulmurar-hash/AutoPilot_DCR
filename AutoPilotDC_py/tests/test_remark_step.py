# -*- coding: utf-8 -*-
# ============================================================
# AutoPilot DC — Teste: 🎯 Remarcheaza din pas (v4.18)
#   Rulare:  py -m unittest tests.test_remark_step
# ============================================================

import os
import sys
import unittest
from types import SimpleNamespace

APP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, APP)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from rpr.model import (ActionNode, Condition, ConditionKind, Locator, LocatorKind, ObjectRepository,  # noqa: E402
                       RprAction, UiObject, UiTechnology, WaitMode, WaitNode)


class RemarkStepTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            import studio_ui
        except ImportError as ex:  # fara tkinter
            raise unittest.SkipTest(str(ex))
        cls.S = studio_ui.StudioPanel

    def _stub(self, *steps):
        repo = ObjectRepository()
        old = repo.add(UiObject(name="Bifa_Systems", technology=UiTechnology.Web, folder="Search",
                                locators=[Locator(LocatorKind.Text, "Systems")]))
        calls = []
        S = self.S
        stub = SimpleNamespace(
            repo=repo, routine=SimpleNamespace(steps=list(steps)), busy=True, calls=calls,
            _hide_spy_hint=lambda: calls.append("hide"), save_repository=lambda: calls.append("save"),
            refresh_objects=lambda: None, mark_dirty=lambda: calls.append("dirty"),
            refresh_node=lambda n: calls.append("refresh"), set_status=lambda m: calls.append(m),
            editor=SimpleNamespace(_target=None, show=lambda n: None),
            step_object_name=S.step_object_name, set_step_object=S.set_step_object)
        stub.steps_using = lambda name: S.steps_using(stub, name)
        return stub, old

    @staticmethod
    def _captured():
        return UiObject(name="Checkbox_Systems", technology=UiTechnology.Web,
                        locators=[Locator(LocatorKind.Id, "chkSystems"), Locator(LocatorKind.Css, "#chkSystems")])

    def test_object_name_of_steps(self):
        S = self.S
        self.assertEqual("Bifa_Systems", S.step_object_name(ActionNode(action=RprAction.Check, target=" Bifa_Systems ")))
        w = WaitNode(mode=WaitMode.UntilTrue, condition=Condition(kind=ConditionKind.ElementExists, target="X"))
        self.assertEqual("X", S.step_object_name(w))
        self.assertEqual("", S.step_object_name(WaitNode(mode=WaitMode.Seconds)))
        S.set_step_object(w, "Y")
        self.assertEqual("Y", w.condition.target)

    def test_steps_using_counts_every_step(self):
        a = ActionNode(action=RprAction.Check, target="Bifa_Systems")
        b = ActionNode(action=RprAction.Click, target="bifa_systems")
        c = ActionNode(action=RprAction.Click, target="Alt")
        stub, _ = self._stub(a, b, c)
        self.assertEqual(2, stub.steps_using("Bifa_Systems"))

    def test_replace_keeps_name_and_drops_wrong_locators(self):
        node = ActionNode(action=RprAction.Check, target="Bifa_Systems")
        stub, old = self._stub(node)
        self.S._remark_done(stub, node, old, "replace", self._captured(), None)
        self.assertEqual("Bifa_Systems", node.target)
        self.assertEqual(["Id", "Css"], [str(l.kind) for l in old.locators])   # locatorul gresit nu mai ramane
        self.assertEqual(1, len(stub.repo.objects))
        self.assertIn("save", stub.calls)
        self.assertNotIn("dirty", stub.calls)   # rutina nu se schimba, doar biblioteca
        self.assertFalse(stub.busy)

    def test_new_object_only_for_this_step(self):
        node = ActionNode(action=RprAction.Check, target="Bifa_Systems")
        other = ActionNode(action=RprAction.Click, target="Bifa_Systems")
        stub, old = self._stub(node, other)
        stub.repo.classify = lambda o: None
        self.S._remark_done(stub, node, old, "new", self._captured(), None, ask_name=False)
        self.assertEqual("Bifa_Systems_2", node.target)
        self.assertEqual("Bifa_Systems", other.target)
        new = stub.repo.find("Bifa_Systems_2")
        self.assertEqual("Search", new.folder)
        self.assertEqual(["Text"], [str(l.kind) for l in old.locators])   # obiectul vechi neschimbat
        self.assertIn("dirty", stub.calls)
        self.assertIn("save", stub.calls)

    def test_step_without_object_gets_new_object(self):
        node = ActionNode(action=RprAction.Click, target="")
        stub, _ = self._stub(node)
        stub.repo.classify = lambda o: None
        self.S._remark_done(stub, node, None, "new", self._captured(), None, ask_name=False)
        self.assertEqual("Checkbox_Systems", node.target)
        self.assertIsNotNone(stub.repo.find("Checkbox_Systems"))

    def test_cancel_changes_nothing(self):
        node = ActionNode(action=RprAction.Check, target="Bifa_Systems")
        stub, old = self._stub(node)
        self.S._remark_done(stub, node, old, "replace", None, None)
        self.assertEqual(["Text"], [str(l.kind) for l in old.locators])
        self.assertNotIn("save", stub.calls)
        self.assertFalse(stub.busy)


class RemarkStepUiTests(unittest.TestCase):
    """Studio real (Tk): butonul 🎯 Remarcheaza din panoul pasului, cu un browser fals."""
    @classmethod
    def setUpClass(cls):
        try:
            import tkinter as tk
            cls.root = tk.Tk()
            cls.root.geometry("1366x740")
        except Exception as ex:  # noqa: BLE001 — fara ecran (CI)
            raise unittest.SkipTest(f"fara afisaj: {ex}")
        import tempfile
        import ui_theme
        from rpr.storage import RprPaths
        from test_views import COLORS
        cls.d = tempfile.mkdtemp(prefix="apdc_remark_")
        cls.RprPaths, cls.ui_theme = RprPaths, ui_theme
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
        cls.RprPaths.root, cls.ui_theme._SETTINGS = cls.old_root, cls.old_aspect
        cls.root.destroy()

    def _buttons(self, w, out):
        for ch in w.winfo_children():
            try:
                out.append((ch.cget("text"), ch))
            except Exception:  # noqa: BLE001
                pass
            self._buttons(ch, out)
        return out

    def test_button_replaces_locators(self):
        import time
        p = self.p
        obj = p.repo.add(UiObject(name="Bifa_Systems", technology=UiTechnology.Web,
                                  locators=[Locator(LocatorKind.Text, "Systems")]))
        node = ActionNode(action=RprAction.Check, target="Bifa_Systems", technology=UiTechnology.Web)
        p.insert_node(node)
        p.editor.show(node)
        self.root.update()
        btn = dict(self._buttons(p.props.inner, [])).get("🎯 Remarcheaza")
        self.assertIsNotNone(btn, "butonul lipseste langa ▶ Testeaza pasul")
        cap = UiObject(name="Spy", technology=UiTechnology.Web, locators=[Locator(LocatorKind.Id, "chkSystems")])
        fake = SimpleNamespace(is_open=True, capture_object=lambda hint, folder: cap, cancel_spy=lambda: None)
        orig_dlg, orig_web = self.studio_ui.choice_dialog, p.web
        self.studio_ui.choice_dialog = lambda *a, **k: "Inlocuieste locatoarele"
        p.web = lambda: fake
        try:
            btn.invoke()
            t0 = time.time()
            while p.busy and time.time() - t0 < 5:
                self.root.update()
                time.sleep(0.02)
        finally:
            self.studio_ui.choice_dialog, p.web = orig_dlg, orig_web
        self.assertFalse(p.busy)
        self.assertEqual(["Id"], [str(l.kind) for l in obj.locators])
        self.assertEqual("Bifa_Systems", node.target)


if __name__ == "__main__":
    unittest.main()
