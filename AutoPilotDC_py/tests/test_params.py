# -*- coding: utf-8 -*-
# ============================================================
# AutoPilot DC — Teste: 🧩 obiecte cu parametru si 📌 parti comune (v4.28)
#   Rulare:  py -m unittest tests.test_params
# ============================================================

import os
import shutil
import sys
import tempfile
import threading
import unittest
from unittest import mock

APP = os.path.dirname(os.path.abspath(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, APP)

from rpr import libsearch  # noqa: E402
from rpr.conditions import ConditionEvaluator  # noqa: E402
from rpr.importer import StepImporter, ai_prompt  # noqa: E402
from rpr.model import (ActionNode, Condition, ConditionKind, IfNode, Locator, LocatorKind,  # noqa: E402
                       ObjectRepository, Routine, RprAction, UiObject, UiTechnology, param_names_in, with_params)
from rpr.storage import RprPaths  # noqa: E402
from rpr.variables import VariableStore  # noqa: E402


def _button():
    return UiObject(name="Buton_Salveaza", technology=UiTechnology.Web, site="Portal", page="Comenzi",
                    object_type="Buton", captured_text="Salveaza",
                    locators=[Locator(LocatorKind.Text, "Salveaza"), Locator(LocatorKind.Id, "btnSave"),
                              Locator(LocatorKind.XPath, "//button[text()='Salveaza']")])


class ModelTests(unittest.TestCase):
    def test_params_roundtrip_and_old_files(self):
        o = _button()
        o.params = ["Text"]
        self.assertEqual(["Text"], UiObject.from_dict(o.to_dict()).params)
        self.assertEqual([], UiObject.from_dict({"name": "Vechi"}).params)       # fisier vechi
        a = ActionNode(action=RprAction.Click, target="B", params={"Text": "Anuleaza"})
        back = ActionNode.from_dict(a.to_dict())
        self.assertEqual({"Text": "Anuleaza"}, back.params)
        self.assertIn("Text=Anuleaza", back.auto_title() if hasattr(back, "auto_title") else back.title)
        c = Condition(kind=ConditionKind.ElementExists, target="B", params={"Text": "Ok"})
        self.assertEqual({"Text": "Ok"}, Condition.from_dict(c.to_dict()).params)
        self.assertEqual({}, ActionNode.from_dict({"type": "action", "action": "Click", "target": "B"}).params)

    def test_with_params_then_variables(self):
        o = UiObject(name="B", locators=[Locator(LocatorKind.Text, "{Text}"),
                                         Locator(LocatorKind.Css, "#r{Rand.Id} .b")], params=["Text"])
        self.assertEqual(["Text"], param_names_in(o))                        # {Rand.Id} nu e parametru
        v = VariableStore()
        v.set("Rand.Nume", "Ion")
        v.set("Rand.Id", "7")
        real = with_params(o, {"Text": "Salut {Rand.Nume}"}, v.resolve)
        self.assertEqual("Salut Ion", real.locators[0].value)
        self.assertEqual("#r7 .b", real.locators[1].value)
        self.assertEqual("{Text}", o.locators[0].value)                      # biblioteca nu se schimba


class ParametrizeTests(unittest.TestCase):
    def test_label_becomes_param_and_specific_disabled(self):
        twin, n = libsearch.parametrize(_button(), "Text")
        self.assertEqual(2, n)
        self.assertEqual("{Text}", twin.locators[0].value)
        self.assertEqual("//button[text()='{Text}']", twin.locators[2].value)
        self.assertFalse(twin.locators[1].enabled)                           # id fara text: ar gasi acelasi buton
        self.assertEqual(["Text"], twin.params)
        self.assertIn("parametru", twin.tags)
        self.assertEqual("Salveaza", _button().locators[0].value)


class _State:
    def __init__(self, exists):
        self.exists = self.visible = self.enabled = exists
        self.text = self.value = ""


class EngineTests(unittest.TestCase):
    def test_condition_resolves_params(self):
        repo = ObjectRepository()
        o = UiObject(name="B", technology=UiTechnology.Desktop, locators=[Locator(LocatorKind.Name, "{Text}")],
                     params=["Text"])
        repo.add(o)
        seen = []
        driver = mock.Mock()
        driver.get_state.side_effect = lambda obj, ms, stop: (seen.append(obj.locators[0].value), _State(True))[1]
        drivers = mock.Mock()
        drivers.get.return_value = driver
        ev = ConditionEvaluator(repo, drivers, VariableStore(), threading.Event())
        self.assertTrue(ev.evaluate(Condition(kind=ConditionKind.ElementExists, target="B", params={"Text": "Ok"})))
        self.assertEqual(["Ok"], seen)


class ImporterTests(unittest.TestCase):
    def setUp(self):
        self.repo = ObjectRepository()
        o = UiObject(name="Buton_cu_Text", technology=UiTechnology.Web, locators=[Locator(LocatorKind.Text, "{Text}")],
                     params=["Text"])
        self.repo.add(o)
        self.repo.add(UiObject(name="Camp", technology=UiTechnology.Web, locators=[Locator(LocatorKind.Name, "{Eticheta}")],
                               params=["Eticheta"]))

    def test_action_and_condition_params(self):
        res = StepImporter(self.repo).parse("CLICK [Buton_cu_Text](Text=Salveaza)\n"
                                            "SCRIE [Camp](Eticheta=\"Nume, prenume\") = abc\n"
                                            "CLICK [Buton_cu_Text]\n")
        acts = [n for n in res.routine.steps if isinstance(n, ActionNode)]
        self.assertEqual({"Text": "Salveaza"}, acts[0].params)
        self.assertEqual({"Eticheta": "Nume, prenume"}, acts[1].params)
        self.assertEqual("abc", acts[1].value)
        self.assertEqual({}, acts[2].params)                                 # nu se mosteneste de la pasul anterior

    def test_prompt_lists_params(self):
        text = ai_prompt("ro", self.repo.objects)
        self.assertIn("[Buton_cu_Text](Text=...)", text)


class StudioParamTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            import tkinter as tk
            cls.root = tk.Tk()
            cls.root.withdraw()
        except Exception as ex:  # noqa: BLE001
            raise unittest.SkipTest(f"fara afisaj: {ex}")
        cls.d = tempfile.mkdtemp(prefix="apdc_params_")
        cls.old_root = RprPaths.root
        RprPaths.root = os.path.join(cls.d, "Studio")
        import studio_ui
        cls.studio_ui = studio_ui
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

    def _labels(self, w):
        out = []
        for ch in w.winfo_children():
            try:
                out.append(str(ch.cget("text")))
            except Exception:  # noqa: BLE001
                pass
            out.extend(self._labels(ch))
        return out

    def test_make_param_common_and_editor_fields(self):
        p = self.p
        b = _button()
        p.repo.add(b)
        answers = iter(["Text", "Buton_cu_Text"])
        with mock.patch.object(self.studio_ui, "input_dialog", lambda *a, **k: next(answers)):
            p.make_param_object(b)
        twin = p.repo.find("Buton_cu_Text")
        self.assertIsNotNone(twin)
        self.assertEqual(["Text"], twin.params)
        self.assertEqual("{Text}", twin.locators[0].value)
        # 📌 comun: fara ecran si fara adrese
        b.url_patterns = ["*/comenzi*"]
        p.make_common_object(b)
        self.assertEqual("", b.page)
        self.assertEqual([], b.url_patterns)
        p.refresh_objects()
        groups = [p.objects.item(i, "text") for i in p.objects.get_children()]
        self.assertTrue(any("Portal" in g for g in groups))
        # editorul pasului: campul "Parametru: Text" sub obiect
        node = ActionNode(action=RprAction.Click, target="Buton_cu_Text", params={"Text": "Anuleaza"})
        p.routine.steps.append(node)
        p.editor.show(node)
        self.root.update_idletasks()
        self.assertTrue(any("Parametru: Text" in t for t in self._labels(p.editor._host)))
        cond = IfNode(condition=Condition(kind=ConditionKind.ElementExists, target="Buton_cu_Text"))
        p.routine.steps.append(cond)
        p.editor.show(cond)
        self.root.update_idletasks()
        self.assertTrue(any("Parametru: Text" in t for t in self._labels(p.editor._host)))

    def test_test_object_asks_param_value(self):
        p = self.p
        o = UiObject(name="Sap_Buton", technology=UiTechnology.Sap, locators=[Locator(LocatorKind.SapName, "{Text}")],
                     params=["Text"])
        p.repo.add(o)
        driver = mock.Mock()
        driver.test_object.return_value = {"found": True}
        with mock.patch.object(p.drivers, "get", return_value=driver), \
                mock.patch.object(self.studio_ui, "input_dialog", return_value="Salveaza"), \
                mock.patch.object(p, "post"), mock.patch("threading.Thread") as th:
            p.test_object(o)
            th.call_args.kwargs["target"]()
        tested = driver.test_object.call_args.args[0]
        self.assertEqual("Salveaza", tested.locators[0].value)
        self.assertEqual("{Text}", o.locators[0].value)
        # Anuleaza la intrebare = nu se testeaza nimic
        driver.reset_mock()
        with mock.patch.object(self.studio_ui, "input_dialog", return_value=None), \
                mock.patch("threading.Thread") as th:
            p.test_object(o)
            th.assert_not_called()


if __name__ == "__main__":
    unittest.main()
