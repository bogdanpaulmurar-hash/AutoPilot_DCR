# -*- coding: utf-8 -*-
# ============================================================
# AutoPilot DC — Teste: 📱 Mobil (Android prin Appium), v4.29
#   Rulare:  py -m unittest tests.test_mobile
# Fara telefon si fara Appium: adb e simulat (runner), sesiunea Appium e un obiect fals.
# ============================================================

import os
import shutil
import sys
import tempfile
import threading
import unittest

APP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, APP)

from rpr import mobile as M  # noqa: E402
from rpr.drivers.base import ActionRequest, DriverProvider, RprStepException  # noqa: E402
from rpr.drivers.mobile import MobileDriver, appium_by, keycode  # noqa: E402
from rpr.engine import RprEngine  # noqa: E402
from rpr.model import (ActionNode, ErrorPolicy, Locator, LocatorKind, ObjectRepository, Routine,  # noqa: E402
                       RprAction, UiObject, UiTechnology, action_info)

from tests.test_rpr import FakeDriver, FakeHost  # noqa: E402

DEVICES = ("List of devices attached\n"
           "R58M12   device usb:1-1 product:x model:Galaxy_A52 device:a52\n"
           "emulator-5554   unauthorized\n")


def fake_adb(devices=DEVICES, locked=False, packages="package:com.firma.app\n", battery=80):
    calls = []

    def run(args, timeout):
        calls.append(args)
        if args[1:3] == ["devices", "-l"]:
            return 0, devices
        if "window" in args:
            return 0, f"  mDreamingLockscreen={'true' if locked else 'false'}\n"
        if "pm" in args:
            return 0, packages
        if "battery" in args:
            return 0, f"  level: {battery}\n"
        if "logcat" in args:
            return 0, "logcat text"
        return 1, ""
    run.calls = calls
    return run


def appium_ok(url):
    return True, "pornit"


class TargetAndDevicesTests(unittest.TestCase):
    def test_parse_target(self):
        t = M.parse_target("R58M12 | com.firma.app/.MainActivity")
        self.assertEqual(("R58M12", "com.firma.app", ".MainActivity"), (t.serial, t.package, t.activity))
        t = M.parse_target("com.firma.app")
        self.assertEqual(("", "com.firma.app", ""), (t.serial, t.package, t.activity))
        t = M.parse_target("emulator-5554")
        self.assertEqual(("emulator-5554", ""), (t.serial, t.package))
        t = M.parse_target(" | ")
        self.assertEqual(("", ""), (t.serial, t.package))

    def test_list_devices(self):
        devs = M.list_devices(fake_adb(), adb="adb")
        self.assertEqual(["R58M12", "emulator-5554"], [d.serial for d in devs])
        self.assertEqual("Galaxy A52", devs[0].model)
        self.assertEqual("unauthorized", devs[1].state)


class CheckDeviceTests(unittest.TestCase):
    def check(self, value="| com.firma.app", **kw):
        client = kw.pop("client", True)
        appium = kw.pop("appium", appium_ok)
        return M.check_device(M.parse_target(value), run=fake_adb(**kw), adb="adb", appium=appium,
                              client_installed=client)

    def test_all_ok(self):
        r = self.check()
        self.assertTrue(r.ok, r.text())
        self.assertEqual("R58M12", r.serial)
        self.assertIn("✅ Aplicatia instalata", r.text())

    def test_no_adb(self):
        r = M.check_device(M.MobileTarget(), adb="")
        self.assertFalse(r.ok)
        self.assertEqual(1, len(r.items))

    def test_no_device_and_unauthorized(self):
        self.assertFalse(self.check(devices="List of devices attached\n").ok)
        r = self.check("emulator-5554 | com.firma.app")
        self.assertFalse(r.ok)
        self.assertIn("Permite depanarea USB", r.text())
        self.assertFalse(self.check("ALTUL | com.firma.app").ok)

    def test_locked_missing_app_low_battery_appium(self):
        self.assertFalse(self.check(locked=True).ok)
        r = self.check(packages="package:com.firma.app.beta\n")
        self.assertFalse(r.ok)
        self.assertIn("nu e instalata", r.text())
        r = self.check(battery=10)
        self.assertTrue(r.ok)                 # doar atentionare
        self.assertIn("⚠ Baterie", r.text())
        self.assertFalse(self.check(client=False).ok)
        self.assertFalse(self.check(appium=lambda u: (False, "nu raspunde")).ok)

    def test_run_folder(self):
        import datetime as dt
        root = M.run_root("R", "Login / test", dt.datetime(2026, 10, 31, 9, 5, 7))
        self.assertEqual(os.path.join("R", "mobil", "2026-10-31_090507_Login_test"), root)
        tmp = tempfile.mkdtemp()
        try:
            p = M.device_folder(os.path.join(tmp, "x"), "R58M12", "Galaxy A52")
            self.assertTrue(os.path.isdir(p))
            self.assertEqual("Galaxy_A52_R58M12", os.path.basename(p))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class FakeEl:
    def __init__(self, text="", checked="false"):
        self.text, self.id, self.checked, self.typed, self.clicks = text, "el1", checked, [], 0

    def click(self):
        self.clicks += 1
        self.checked = "false" if self.checked == "true" else "true"

    def clear(self):
        self.text = ""

    def send_keys(self, v):
        self.text = v
        self.typed.append(v)

    def get_attribute(self, name):
        return self.checked if name == "checked" else "attr-" + name

    def is_displayed(self):
        return True

    def is_enabled(self):
        return True


class FakeSession:
    def __init__(self):
        self.els = {}
        self.calls = []

    def find_elements(self, by, val):
        self.calls.append((by, val))
        return [self.els[(by, val)]] if (by, val) in self.els else []

    def back(self):
        self.calls.append("back")

    def press_keycode(self, k):
        self.calls.append(("key", k))

    def get_window_size(self):
        return {"width": 1000, "height": 2000}

    def execute_script(self, name, args):
        self.calls.append((name, args))

    def get_screenshot_as_file(self, path):
        open(path, "wb").close()
        return True

    def stop_recording_screen(self):
        return ""

    def quit(self):
        self.calls.append("quit")


def obj(name, kind=LocatorKind.AccessibilityId, value="login"):
    return UiObject(name=name, technology=UiTechnology.Mobile, locators=[Locator(kind, value)])


class DriverTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.d = MobileDriver(results_folder=self.tmp, runner=fake_adb())
        self.s = FakeSession()
        self.d._drv = self.s
        self.stop = threading.Event()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def ex(self, action, target=None, value=""):
        return self.d.execute(ActionRequest(action, target, value, 300, False, self.tmp), self.stop)

    def test_locators_and_keys(self):
        self.assertEqual(("accessibility id", "x"), appium_by(Locator(LocatorKind.AccessibilityId, "x")))
        self.assertEqual(("id", "com.a:id/b"), appium_by(Locator(LocatorKind.ResourceId, "com.a:id/b")))
        self.assertEqual(("-android uiautomator", 'new UiSelector().text("Intra \\"acum\\"")'),
                         appium_by(Locator(LocatorKind.Text, 'Intra "acum"')))
        self.assertIsNone(appium_by(Locator(LocatorKind.Css, "#x")))
        self.assertEqual(66, keycode("Enter"))
        self.assertEqual(4, keycode("inapoi"))
        self.assertEqual(187, keycode("187"))
        with self.assertRaises(RprStepException):
            keycode("Ctrl+S")

    def test_actions(self):
        el = FakeEl("vechi")
        self.s.els[("accessibility id", "login")] = el
        o = obj("Camp_Login")
        self.ex(RprAction.TypeText, o, "ana")
        self.assertEqual("ana", el.text)
        self.ex(RprAction.AppendText, o, "-1")
        self.assertEqual("ana-1", el.text)
        self.assertEqual("ana-1", self.ex(RprAction.ReadText, o))
        self.ex(RprAction.Check, o)
        self.ex(RprAction.Check, o)            # deja bifat: fara al doilea click
        self.assertEqual(1, el.clicks)
        self.ex(RprAction.Uncheck, o)
        self.assertEqual(2, el.clicks)
        self.ex(RprAction.RightClick, o)
        self.assertEqual("mobile: longClickGesture", self.s.calls[-1][0])
        self.ex(RprAction.MobileSwipe, value="jos")
        self.assertEqual("down", self.s.calls[-1][1]["direction"])
        self.ex(RprAction.MobileBack)
        self.ex(RprAction.PressKey, value="Enter")
        self.assertEqual(["back", ("key", 66)], self.s.calls[-2:])
        with self.assertRaises(RprStepException):
            self.ex(RprAction.Hover, o)
        with self.assertRaises(RprStepException):
            self.ex(RprAction.MobileSwipe, value="oblic")
        with self.assertRaises(RprStepException):     # obiect fara locatori de telefon
            self.ex(RprAction.Click, obj("Web", LocatorKind.Css, "#x"))

    def test_not_found_and_not_connected(self):
        with self.assertRaises(RprStepException):
            self.ex(RprAction.Click, obj("Lipsa", value="nimic"))
        self.d._drv = None
        with self.assertRaises(RprStepException) as cm:
            self.ex(RprAction.MobileBack)
        self.assertIn("conecteaza telefonul", str(cm.exception))

    def test_connect_refuses_when_device_not_ready(self):
        self.d._drv = None
        self.d._run = fake_adb(locked=True)
        orig = M.adb_path
        M.adb_path = lambda: "adb"
        try:
            with self.assertRaises(RprStepException) as cm:
                self.ex(RprAction.MobileConnect, value="| com.firma.app")
        finally:
            M.adb_path = orig
        self.assertIn("Telefonul nu e pregatit", str(cm.exception))
        self.assertIn("deblocheaza", str(cm.exception))

    def test_screenshot_and_end_run_files(self):
        self.d._serial = "R58M12"
        self.d._folder = M.device_folder(os.path.join(self.tmp, "run"), "R58M12")
        path = self.ex(RprAction.MobileScreenshot, value="dupa_login")
        self.assertTrue(path.endswith(os.path.join("capturi", "dupa_login.png")))
        self.assertTrue(os.path.isfile(path))
        folder = self.d.device_folder
        orig = M.adb_path
        M.adb_path = lambda: "adb"
        try:
            self.d.end_run()
        finally:
            M.adb_path = orig
        self.assertTrue(os.path.isfile(os.path.join(folder, "logcat.txt")))
        self.assertIn("quit", self.s.calls)
        self.assertIsNone(self.d._drv)


class MobileDriverStub(FakeDriver):
    technology = UiTechnology.Mobile

    def __init__(self):
        super().__init__()
        self.roots, self.ended = [], 0

    def begin_run(self, root):
        self.roots.append(root)

    def end_run(self):
        self.ended += 1


class EngineAndModelTests(unittest.TestCase):
    def setUp(self):
        self.out = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.out, ignore_errors=True)

    def run_routine(self, *steps):
        repo = ObjectRepository()
        repo.add(obj("Buton_Login"))
        web, mob = FakeDriver(), MobileDriverStub()
        mob.screen["Buton_Login"] = "Login"
        provider = DriverProvider({t: (lambda d=web: d) for t in UiTechnology})
        provider.register(UiTechnology.Mobile, lambda: mob)
        engine = RprEngine(repo, provider, FakeHost(), self.out)
        r = Routine(name="Login telefon")
        r.settings.highlight_before_action = False
        r.settings.auto_retries = 0
        r.settings.screenshot_on_error = False
        r.settings.default_error_policy = ErrorPolicy.Stop
        r.steps.extend(steps)
        return engine.run(r), mob, repo, r

    def test_engine_prepares_and_closes_mobile_run(self):
        res, mob, repo, r = self.run_routine(
            ActionNode(action=RprAction.MobileConnect, technology=UiTechnology.Mobile, value="| com.firma.app"),
            ActionNode(action=RprAction.Click, target="Buton_Login"))
        self.assertTrue(res.success, res.message)
        self.assertEqual(1, len(mob.roots))
        self.assertTrue(mob.roots[0].startswith(os.path.join(self.out, "mobil")))
        self.assertTrue(mob.roots[0].endswith("_Login_telefon"))
        self.assertEqual(1, mob.ended)
        self.assertIn("MobileConnect::| com.firma.app", mob.actions)
        self.assertIn("Click:Buton_Login:", mob.actions)

    def test_step_on_mobile_object_is_enough(self):
        res, mob, repo, r = self.run_routine(ActionNode(action=RprAction.Click, target="Buton_Login"))
        self.assertTrue(res.success, res.message)
        self.assertTrue(M.uses_mobile(r, repo.find))
        self.assertFalse(M.uses_mobile(r))           # fara biblioteca nu stie tehnologia obiectului
        self.assertEqual(1, mob.ended)

    def test_web_routine_does_not_touch_mobile(self):
        res, mob, repo, r = self.run_routine(ActionNode(action=RprAction.PressKey, value="Enter"))
        self.assertEqual([], mob.roots)
        self.assertEqual(0, mob.ended)

    def test_model_roundtrip_and_catalog(self):
        o = obj("Camp", LocatorKind.ResourceId, "com.a:id/user")
        back = UiObject.from_dict(o.to_dict())
        self.assertEqual(UiTechnology.Mobile, back.technology)
        self.assertEqual(LocatorKind.ResourceId, back.locators[0].kind)
        self.assertIn(UiTechnology.Mobile, action_info(RprAction.Click).technologies)
        self.assertEqual((UiTechnology.Mobile,), action_info(RprAction.MobileSwipe).technologies)
        a = ActionNode.from_dict(ActionNode(action=RprAction.MobileConnect, technology=UiTechnology.Mobile).to_dict())
        self.assertEqual(RprAction.MobileConnect, a.action)


class StudioMobileTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            import tkinter as tk
            cls.root = tk.Tk()
            cls.root.withdraw()
        except Exception as ex:  # noqa: BLE001
            raise unittest.SkipTest(f"fara afisaj: {ex}")
        from rpr.storage import RprPaths
        cls.RprPaths = RprPaths
        cls.d = tempfile.mkdtemp(prefix="apdc_mobil_")
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
        cls.RprPaths.root = cls.old_root
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

    def test_connect_step_has_check_button_and_icon(self):
        su = self.studio_ui
        node = ActionNode(action=RprAction.MobileConnect, technology=UiTechnology.Mobile, value="| com.firma.app")
        self.assertEqual("📱", su.icon_for(node))
        self.assertIn((UiTechnology.Mobile, "Mobil (Android)"), su.TECHNOLOGIES)
        tools = [t for _, items in su.TOOLBOX for t, _, _ in items]
        self.assertTrue(any("Mobil: conecteaza" in t for t in tools))
        self.p.routine.steps.append(node)
        self.p.editor.show(node)
        self.root.update_idletasks()
        labels = self._labels(self.p.editor._host)
        self.assertTrue(any("Verifica telefonul" in t for t in labels), labels)
        # Click pe un obiect de telefon: pasul se poate construi (fara erori)
        self.p.repo.add(obj("Buton_Telefon"))
        click = ActionNode(action=RprAction.Click, target="Buton_Telefon")
        self.p.routine.steps.append(click)
        self.p.editor.show(click)
        self.root.update_idletasks()


if __name__ == "__main__":
    unittest.main()
