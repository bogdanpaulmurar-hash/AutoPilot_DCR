# -*- coding: utf-8 -*-
# ============================================================
# AutoPilot DC — Teste: ▶ Ruleaza si marcheaza (v4.17)
#   Rulare:  py -m unittest tests.test_learn_run
# ============================================================

import os
import sys
import tempfile
import unittest
import uuid
from types import SimpleNamespace

APP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, APP)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from rpr.host import ErrorDecision  # noqa: E402
from rpr.model import (ActionNode, Condition, ConditionKind, ForEachRowNode, Locator, LocatorKind, RprAction,  # noqa: E402
                       SetVariableNode, TryNode, UiObject, UiTechnology, VariableOperation, WaitMode, WaitNode)
from test_rpr import create, new_routine  # noqa: E402


class EngineLearnTests(unittest.TestCase):
    def test_max_rows_runs_only_first_row(self):
        import openpyxl
        path = os.path.join(tempfile.gettempdir(), f"apdc_learn_{uuid.uuid4().hex}.xlsx")
        wb = openpyxl.Workbook()
        for r, v in enumerate(["Cod", "A1", "B2", "C3"], 1):
            wb.active.cell(row=r, column=1, value=v)
        wb.save(path)
        try:
            engine, *_ = create()
            engine.max_rows = 1
            each = ForEachRowNode(file_path=path, key_column="Cod")
            each.body.append(SetVariableNode(name="Nr", operation=VariableOperation.Increment))
            res = engine.run(new_routine(SetVariableNode(name="Nr", value="0"), each))
            self.assertTrue(res.success, res.message)
            self.assertEqual(1, res.rows_ok)
            self.assertEqual("1", res.final_variables["Nr"])
        finally:
            os.remove(path)

    def test_every_error_asks_even_with_stop_policy(self):
        engine, driver, host, _ = create()
        engine.ask_on_every_error = True
        asked = []

        def ask(node, error, inside):   # omul "marcheaza" obiectul: acum apare pe pagina
            asked.append(node.target)
            driver.screen["Lipsa"] = "x"
            return ErrorDecision.RETRY
        host.ask_on_error = ask
        res = engine.run(new_routine(ActionNode(action=RprAction.Click, target="Lipsa", timeout_ms=10),
                                     SetVariableNode(name="Ajuns", value="da")))
        self.assertTrue(res.success, res.message)
        self.assertEqual(["Lipsa"], asked)
        self.assertEqual("da", res.final_variables["Ajuns"])

    def test_without_flag_stop_policy_does_not_ask(self):
        engine, driver, host, _ = create()
        host.ask_on_error = lambda *a: self.fail("nu trebuia sa intrebe")
        res = engine.run(new_routine(ActionNode(action=RprAction.Click, target="Lipsa", timeout_ms=10)))
        self.assertFalse(res.success)

    def test_try_block_keeps_its_on_error_branch(self):
        engine, driver, host, _ = create()
        engine.ask_on_every_error = True
        host.ask_on_error = lambda *a: self.fail("in Incearca eroarea merge la La eroare")
        t = TryNode()
        t.body.append(ActionNode(action=RprAction.Click, target="Lipsa", timeout_ms=10))
        t.catch.append(SetVariableNode(name="Prins", value="da"))
        res = engine.run(new_routine(t))
        self.assertTrue(res.success, res.message)
        self.assertEqual("da", res.final_variables["Prins"])


class HostLearnTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            import studio_ui
        except ImportError as ex:  # fara tkinter
            raise unittest.SkipTest(str(ex))
        cls.studio_ui = studio_ui

    def _panel(self, answers, marks):
        obj = UiObject(name="Buton_Save", technology=UiTechnology.Web, locators=[Locator(LocatorKind.Text, "Save")])
        seen = []

        def dialog(title, text, buttons, detail):
            seen.append((buttons, detail))
            return answers.pop(0)
        p = SimpleNamespace(_learn_run=True, learn_object_of=lambda n: obj, call_ui=lambda fn: fn(),
                            paused_dialog=dialog, learn_mark=lambda o: marks.pop(0))
        return p, seen

    def test_mark_now_then_retry(self):
        p, seen = self._panel(["🎯 Marcheaza acum"], [True])
        host = self.studio_ui.StudioRunHost(p)
        node = ActionNode(action=RprAction.Click, target="Buton_Save")
        self.assertEqual(ErrorDecision.RETRY, host.ask_on_error(node, "negasit", False))
        self.assertEqual("🎯 Marcheaza acum", seen[0][0][0])
        self.assertIn("Buton_Save", seen[0][1])

    def test_cancelled_mark_asks_again(self):
        p, seen = self._panel(["🎯 Marcheaza acum", "Opreste"], [False])
        host = self.studio_ui.StudioRunHost(p)
        self.assertEqual(ErrorDecision.STOP, host.ask_on_error(ActionNode(target="Buton_Save"), "negasit", False))
        self.assertEqual(2, len(seen))

    def test_normal_run_has_no_mark_button(self):
        p, seen = self._panel(["Sari pasul"], [])
        p._learn_run = False
        host = self.studio_ui.StudioRunHost(p)
        self.assertEqual(ErrorDecision.SKIP, host.ask_on_error(ActionNode(target="Buton_Save"), "negasit", False))
        self.assertNotIn("🎯 Marcheaza acum", seen[0][0])
        self.assertEqual("negasit", seen[0][1])

    def test_object_of_node(self):
        from rpr.model import ObjectRepository
        repo = ObjectRepository()
        repo.add(UiObject(name="Camp_X", technology=UiTechnology.Web, locators=[Locator(LocatorKind.Text, "X")]))
        stub = SimpleNamespace(repo=repo)
        f = self.studio_ui.StudioPanel.learn_object_of
        self.assertEqual("Camp_X", f(stub, ActionNode(target="Camp_X")).name)
        w = WaitNode(mode=WaitMode.UntilTrue, condition=Condition(kind=ConditionKind.ElementExists, target="Camp_X"))
        self.assertEqual("Camp_X", f(stub, w).name)
        self.assertIsNone(f(stub, ActionNode(target="Nu_exista")))
        self.assertIsNone(f(stub, WaitNode(mode=WaitMode.Seconds)))

    def test_learn_mark_merges_and_saves(self):
        obj = UiObject(name="Buton_Save", technology=UiTechnology.Web, locators=[Locator(LocatorKind.Text, "Save")])
        cap = UiObject(name="Spy_1", locators=[Locator(LocatorKind.Id, "btnSave")])
        calls = []
        drv = SimpleNamespace(capture_object=lambda hint, folder: cap)
        stub = SimpleNamespace(
            web=lambda: drv, drivers=None, call_ui=lambda fn: fn(), _show_spy_hint=lambda t: calls.append("show"),
            _hide_spy_hint=lambda: calls.append("hide"), post=lambda *a: None, repo=SimpleNamespace(classify=lambda o: None),
            save_repository=lambda: calls.append("save"), refresh_objects=lambda: None,
            set_status=lambda m: calls.append(m), _complete_win=None)
        self.assertTrue(self.studio_ui.StudioPanel.learn_mark(stub, obj))
        self.assertEqual(["Id", "Text"], [str(l.kind) for l in obj.locators])
        self.assertEqual(["show", "hide", "save"], calls[:3])
        drv.capture_object = lambda hint, folder: None   # Esc
        self.assertFalse(self.studio_ui.StudioPanel.learn_mark(stub, obj))


if __name__ == "__main__":
    unittest.main()
