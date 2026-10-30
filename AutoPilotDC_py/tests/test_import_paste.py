# -*- coding: utf-8 -*-
# ============================================================
# AutoPilot DC — Teste: 📥 Import AI, lipirea in chenar (v4.16.4)
#   Rulare:  py -m unittest tests.test_import_paste
# ============================================================

import os
import sys
import tempfile
import unittest
from unittest import mock

APP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, APP)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import import_ui  # noqa: E402
import ui_theme  # noqa: E402
from rpr.storage import RprPaths  # noqa: E402


class PasteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            import tkinter as tk
            cls.root = tk.Tk()
            cls.root.geometry("1366x740")
        except Exception as ex:  # noqa: BLE001 — fara ecran (CI)
            raise unittest.SkipTest(f"fara afisaj: {ex}")
        from test_views import COLORS
        cls.d = tempfile.mkdtemp(prefix="apdc_paste_")
        cls.old_root, cls.old_aspect = RprPaths.root, ui_theme._SETTINGS
        RprPaths.root = os.path.join(cls.d, "Studio")
        ui_theme._SETTINGS = os.path.join(cls.d, "aspect.json")
        import studio_ui
        cls.p = studio_ui.StudioPanel(cls.root, COLORS)
        cls.p.pack(fill="both", expand=True)
        cls.root.update()

    @classmethod
    def tearDownClass(cls):
        RprPaths.root, ui_theme._SETTINGS = cls.old_root, cls.old_aspect
        cls.root.destroy()

    def setUp(self):
        self.dlg = import_ui.ImportDialog(self.p)
        self.root.update()

    def tearDown(self):
        self.dlg.destroy()

    def _text(self):
        return self.dlg.text.get("1.0", "end-1c")

    def test_paste_takes_system_clipboard_not_the_prompt(self):
        # Tk inca tine promptul, dar in Windows s-a copiat intre timp raspunsul AI-ului
        self.dlg.clipboard_clear()
        self.dlg.clipboard_append("PROMPTUL")
        with mock.patch.object(import_ui, "win_clipboard_get", return_value='CLICK button "Save"'):
            self.dlg.text.event_generate("<<Paste>>")
        self.assertEqual(self._text(), 'CLICK button "Save"')

    def test_paste_replaces_selection(self):
        self.dlg.text.insert("1.0", "ROUTINE: X\nVECHI\n")
        self.dlg.text.tag_add("sel", "2.0", "2.5")
        self.dlg.text.mark_set("insert", "2.5")
        with mock.patch.object(import_ui, "win_clipboard_get", return_value="NOU"):
            self.dlg.text.event_generate("<<Paste>>")
        self.assertEqual(self._text(), "ROUTINE: X\nNOU\n")

    def test_paste_falls_back_to_tk_clipboard(self):
        self.dlg.clipboard_clear()
        self.dlg.clipboard_append("DIN TK")
        with mock.patch.object(import_ui, "win_clipboard_get", return_value=None):
            self.dlg.text.event_generate("<<Paste>>")
        self.assertEqual(self._text(), "DIN TK")

    def test_copy_prompt_uses_windows_clipboard_when_possible(self):
        got = []
        with mock.patch.object(import_ui, "win_clipboard_set", side_effect=lambda t: got.append(t) or True), \
                mock.patch.object(import_ui.messagebox, "showinfo"):
            self.dlg.clipboard_clear()
            self.dlg.clipboard_append("NESCHIMBAT")
            self.dlg.copy_prompt()
        self.assertEqual(len(got), 1)
        self.assertIn("AutoPilot", got[0])
        self.assertEqual(self.dlg.clipboard_get(), "NESCHIMBAT")   # Tk nu a mai preluat clipboard-ul

    def test_not_windows_helpers_say_so(self):
        if sys.platform == "win32":
            self.skipTest("doar pe alte sisteme")
        self.assertIsNone(import_ui.win_clipboard_get())
        self.assertFalse(import_ui.win_clipboard_set("x"))


if __name__ == "__main__":
    unittest.main()
