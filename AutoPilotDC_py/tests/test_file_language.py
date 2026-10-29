# -*- coding: utf-8 -*-
# ============================================================
# AutoPilot DC v4.8.5 — Limba fisierelor (Excel, rapoarte, loguri), separata de interfata.
#   Rulare:  py -m unittest tests.test_file_language
# ============================================================

import os
import sys
import tempfile
import unittest

APP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, APP)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import i18n  # noqa: E402
from rpr import ForEachRowNode, SetVariableNode, VariableOperation  # noqa: E402
from rpr.excel import ExcelTable  # noqa: E402
from rpr.lang import ft, is_in_progress, is_ok  # noqa: E402
import test_rpr  # noqa: E402
from test_rpr import create, new_routine  # noqa: E402


class _TempSettings(unittest.TestCase):
    def setUp(self):
        self._old = i18n._SETTINGS
        i18n._SETTINGS = os.path.join(tempfile.mkdtemp(), "limba.json")

    def tearDown(self):
        i18n._SETTINGS = self._old


class FileLanguageSetting(_TempSettings):
    def test_default_follows_interface_and_can_differ(self):
        self.assertEqual("", i18n.saved_file_language())
        self.assertEqual("ro", i18n.file_language())
        i18n.save_language("de")
        self.assertEqual("de", i18n.file_language())          # "ca interfata"
        i18n.save_file_language("en")
        self.assertEqual("de", i18n.saved_language())          # interfata nu se schimba
        self.assertEqual("en", i18n.file_language())
        i18n.save_file_language("")
        self.assertEqual("de", i18n.file_language())

    def test_translation_independent_of_interface(self):
        i18n.save_file_language("en")
        self.assertEqual("ro", i18n.LANG)                      # interfata ramane in romana
        self.assertEqual("Salveaza", i18n.tr("Salveaza"))
        self.assertEqual("ERROR: x", ft("EROARE: x"))
        self.assertEqual("IN PROGRESS 29.10 10:00", ft("IN LUCRU 29.10 10:00"))
        i18n.save_file_language("de")
        self.assertEqual("IN BEARBEITUNG (gestoppt 10:00:00)", ft("IN LUCRU (oprit 10:00:00)"))
        i18n.save_file_language("ro")
        self.assertEqual("EROARE: x", ft("EROARE: x"))

    def test_statuses_recognised_in_any_language(self):
        for s in ("IN LUCRU 29.10 10:00", "IN PROGRESS (stopped 10:00:00)", "in bearbeitung 29.10"):
            self.assertTrue(is_in_progress(s), s)
        for s in ("OK", "OK (checked manually)", "OK (verificat manual)"):
            self.assertTrue(is_ok(s), s)
        self.assertFalse(is_ok("ERROR: x"))
        self.assertFalse(is_in_progress("OK"))


class FileLanguageExcel(_TempSettings):
    _make_file = test_rpr.Excel._make_file

    def test_statuses_written_in_english_and_resumed(self):
        i18n.save_file_language("en")
        path = self._make_file()
        try:
            with ExcelTable.open(path, None, 1) as t:   # inceput in romana, reluat in engleza
                t.write(2, "Status", "OK")
                t.write(3, "Status", "IN LUCRU 29.10 10:00")
                t.save()
            engine, _, host, _ = create()
            from rpr.engine import UNFINISHED_BUTTONS
            host.answers = [UNFINISHED_BUTTONS[1]]
            each = ForEachRowNode(file_path=path, key_column="Cod", status_column="Status")
            each.body.append(SetVariableNode(name="Nr", operation=VariableOperation.Increment))
            r = engine.run(new_routine(SetVariableNode(name="Nr", value="1"), each))
            self.assertEqual("2", r.final_variables["Nr"])       # doar randul 4 a rulat
            with ExcelTable.open(path, None, 1) as check:
                self.assertEqual("OK (checked manually)", check.get_cell(3, "Status"))
                self.assertEqual("OK", check.get_cell(4, "Status"))
        finally:
            os.remove(path)

    def test_error_status_in_german(self):
        i18n.save_file_language("de")
        path = self._make_file()
        try:
            from rpr import ActionNode, RprAction
            engine, *_ = create()
            each = ForEachRowNode(file_path=path, key_column="Cod", status_column="Status")
            each.body.append(ActionNode(action=RprAction.ReadText, target="Lipsa", output_variable="X"))
            engine.run(new_routine(each))
            with ExcelTable.open(path, None, 1) as check:
                self.assertTrue(check.get_cell(2, "Status").startswith("FEHLER"), check.get_cell(2, "Status"))
        finally:
            os.remove(path)


if __name__ == "__main__":
    unittest.main()
