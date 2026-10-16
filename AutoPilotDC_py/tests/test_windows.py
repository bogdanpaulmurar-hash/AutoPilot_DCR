# -*- coding: utf-8 -*-
# ============================================================
# AutoPilot DC — Teste drivere SAP / Desktop.
#  - SAP: doar partile care nu cer SAP GUI (taste, Id-uri, nume).
#  - Desktop: Notepad real (pornit si inchis de test); scrierea se face prin UI Automation
#    (ValuePattern), fara tastatura. Se sare daca uiautomation lipseste.
#   Rulare:  py -m unittest tests.test_windows
# ============================================================

import os
import subprocess
import sys
import tempfile
import threading
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rpr import (ActionNode, DriverProvider, ErrorPolicy, Locator, LocatorKind, ObjectRepository,  # noqa: E402
                 Routine, RprAction, RprEngine, RunHost, UiObject, UiTechnology)
from rpr.drivers.base import ActionRequest, RprStepException  # noqa: E402
from rpr.drivers.desktop import clean_name  # noqa: E402
from rpr.drivers.sap import relative_id, sap_vkey  # noqa: E402
from rpr.drivers.winutil import to_vk  # noqa: E402


class SapHelperTests(unittest.TestCase):
    def test_vkeys(self):
        self.assertEqual(0, sap_vkey("Enter"))
        self.assertEqual(3, sap_vkey("F3"))
        self.assertEqual(8, sap_vkey("f8"))
        self.assertEqual(16, sap_vkey("Shift+F4"))
        self.assertEqual(11, sap_vkey("Ctrl+S"))
        self.assertEqual(26, sap_vkey("Ctrl+F2"))
        self.assertEqual(37, sap_vkey("Ctrl+Shift+F1"))
        self.assertEqual(71, sap_vkey("71"))
        with self.assertRaises(RprStepException):
            sap_vkey("Ctrl+Q")

    def test_ids_and_names(self):
        self.assertEqual("wnd[0]/usr/ctxtVBAK-VBELN", relative_id("/app/con[0]/ses[1]/wnd[0]/usr/ctxtVBAK-VBELN"))
        self.assertEqual("Camp_Comanda_vanzari", clean_name("Camp", "Comandă vânzări (F4)".replace("(F4)", "")))
        self.assertEqual("Buton", clean_name("Buton", "  "))

    def test_keys(self):
        self.assertEqual(0x0D, to_vk("enter"))
        self.assertEqual(0x74, to_vk("F5"))
        self.assertEqual(ord("S"), to_vk("s"))
        with self.assertRaises(RprStepException):
            to_vk("Nimic")


class Host(RunHost):
    def __init__(self):
        self.lines = []

    def log(self, e):
        self.lines.append(str(e))


def _uia():
    try:
        import uiautomation  # noqa: F401
        return os.path.exists(os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "notepad.exe"))
    except ImportError:
        return False


@unittest.skipUnless(_uia(), "uiautomation / notepad indisponibil")
class DesktopNotepadTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from rpr.drivers.desktop import DesktopDriver
        cls.tmp = tempfile.mkdtemp(prefix="apdc_desk_")
        cls.driver = DesktopDriver()
        cls.repo = ObjectRepository()
        # Notepad clasic (Windows 10) si cel nou (Windows 11) — aceleasi obiecte ca exemplul 05
        cls.repo.add(UiObject(name="Editor", technology=UiTechnology.Desktop, context="proces:notepad.exe",
                              locators=[Locator(LocatorKind.ClassName, "Document|RichEditD2DPT", 70),
                                        Locator(LocatorKind.ClassName, "Edit|Edit", 60)]))

    @classmethod
    def tearDownClass(cls):
        pid = getattr(cls, "pid", 0)
        if pid:
            subprocess.run(["taskkill", "/PID", str(pid), "/F"], capture_output=True)
        cls.driver.close()

    def _req(self, action, target=None, value="", direct=True):
        return ActionRequest(RprAction.parse(action), target, value, 8000, direct, self.tmp)

    def test_1_notepad_roundtrip(self):
        stop = threading.Event()
        title = self.driver.execute(self._req(RprAction.LaunchApp, value="notepad.exe"), stop)
        type(self).pid = self.driver._w.call(lambda: self.driver._pid)
        self.assertTrue(title)
        ed = self.repo.find("Editor")
        st = self.driver.get_state(ed, 5000, stop)
        self.assertTrue(st.exists, "editorul Notepad nu a fost gasit")
        self.driver.execute(self._req(RprAction.TypeText, ed, "Salut AutoPilot ăîșț"), stop)
        self.assertEqual("Salut AutoPilot ăîșț", self.driver.execute(self._req(RprAction.ReadValue, ed), stop))
        self.assertIn("Salut", self.driver.execute(self._req(RprAction.ReadText, ed), stop))
        self.assertEqual("Edit" if st.used_locator.value == "Edit|Edit" else "Document",
                         self.driver.execute(self._req(RprAction.ReadAttribute, ed, "ControlType"), stop))
        res = self.driver.test_object(ed)
        self.assertTrue(res["found"])
        self.assertTrue(any(r["in_page"] == 1 for r in res["rows"]))

    def test_2_spy_builder_and_path(self):
        """Obiectul construit de Spy (fara mouse) are locatori care il regasesc, inclusiv calea in arbore."""
        d = self.driver

        def build():
            win = d._windows("proces:notepad.exe")[0]
            found = d._find_all(win, Locator(LocatorKind.ClassName, "Edit|Edit")) or \
                d._find_all(win, Locator(LocatorKind.ClassName, "Document|RichEditD2DPT"))
            return d._build_object(found[0])
        obj = d._w.call(build)
        self.assertEqual("proces:notepad.exe", obj.context.lower())
        self.assertTrue(any(l.kind == LocatorKind.UiaPath for l in obj.locators), obj.locators)
        only_path = UiObject(name="P", technology=UiTechnology.Desktop, context=obj.context,
                             locators=[l for l in obj.locators if l.kind == LocatorKind.UiaPath])
        self.assertTrue(d.get_state(only_path, 2000, threading.Event()).exists)

    def test_3_engine_attach_and_type(self):
        r = Routine(name="Desktop")
        r.settings.default_error_policy = ErrorPolicy.Stop
        r.settings.guard_enabled = False
        r.settings.do_not_disturb = False
        r.settings.highlight_before_action = True
        r.settings.highlight_ms = 150
        r.steps.extend([ActionNode(action=RprAction.AttachWindow, value="proces:notepad.exe", technology=UiTechnology.Desktop),
                        ActionNode(action=RprAction.TypeText, target="Editor", value="din motor", direct_mode=True),
                        ActionNode(action=RprAction.ReadValue, target="Editor", output_variable="Text")])
        host = Host()
        res = RprEngine(self.repo, DriverProvider({UiTechnology.Desktop: lambda: self.driver}), host, self.tmp).run(r)
        self.assertTrue(res.success, res.message + "\n" + "\n".join(host.lines[-6:]))
        self.assertEqual("din motor", res.final_variables["Text"])


if __name__ == "__main__":
    unittest.main()
