# -*- coding: utf-8 -*-
# ============================================================
# AutoPilot DC v4.29 — drivers/mobile.py — 📱 telefon / tableta Android prin Appium
#
# Appium e un program separat (Node.js); AutoPilot doar vorbeste cu el. Pachetul Python
# "appium" se importa abia la pasul "Mobil: conecteaza telefonul", deci fara pasi pe
# telefon AutoPilot nu incarca nimic in plus.
# La conectare: verificarea telefonului (rpr/mobile.py), Appium pornit daca nu ruleaza,
# film al ecranului telefonului. La sfarsitul rularii, in folderul telefonului:
#   capturi\, ecran_telefon.mp4, logcat.txt, telefon.txt
# iOS: urmeaza (XCUITest are nevoie de un Mac sau de o ferma de telefoane in cloud).
# ============================================================

from __future__ import annotations

import base64
import datetime as _dt
import os
import shutil
import subprocess
import threading
import time
from typing import Dict, List, Optional, Tuple

from .. import mobile as M
from ..model import Locator, LocatorKind, RprAction, UiObject, UiTechnology
from .base import NOT_FOUND, ActionRequest, ElementNotFound, ElementState, RprStepException, UiDriver

# Tasta -> keycode Android
KEYCODES: Dict[str, int] = {
    "enter": 66, "tab": 61, "back": 4, "inapoi": 4, "home": 3, "acasa": 3, "backspace": 67, "delete": 67,
    "del": 112, "escape": 111, "esc": 111, "search": 84, "cauta": 84, "menu": 82, "space": 62, "spatiu": 62,
    "up": 19, "down": 20, "left": 21, "right": 22, "volumeup": 24, "volumedown": 25, "power": 26,
    "appswitch": 187,
}
SWIPES = {"sus": "up", "up": "up", "jos": "down", "down": "down", "stanga": "left", "left": "left",
          "dreapta": "right", "right": "right"}


def _q(text: str) -> str:
    return (text or "").replace("\\", "\\\\").replace('"', '\\"')


def appium_by(loc: Locator) -> Optional[Tuple[str, str]]:
    """Locatorul AutoPilot -> (strategie Appium, valoare). None = nu se poate folosi pe telefon."""
    k, v = loc.kind, loc.value.strip()
    if not v:
        return None
    if k in (LocatorKind.AccessibilityId, LocatorKind.Label, LocatorKind.Name):
        return "accessibility id", v
    if k in (LocatorKind.ResourceId, LocatorKind.Id, LocatorKind.TestId):
        return "id", v
    if k == LocatorKind.UiAutomator:
        return "-android uiautomator", v
    if k == LocatorKind.XPath:
        return "xpath", v
    if k == LocatorKind.Text:
        return "-android uiautomator", f'new UiSelector().text("{_q(v)}")'
    if k == LocatorKind.ClassName:
        return "class name", v
    return None


def keycode(name: str) -> int:
    n = (name or "").strip().lower().replace(" ", "")
    if n.isdigit():
        return int(n)
    if n in KEYCODES:
        return KEYCODES[n]
    raise RprStepException(f"Tasta \"{name}\" nu e cunoscuta pe telefon. Exemple: Enter, Back, Home, Tab, "
                           "Backspace, Search sau numarul keycode-ului Android.")


class MobileDriver(UiDriver):
    technology = UiTechnology.Mobile
    display_name = "Mobil (Android)"

    def __init__(self, appium_url: str = M.DEFAULT_APPIUM_URL, results_folder: str = "", runner=None):
        self.appium_url = appium_url or M.DEFAULT_APPIUM_URL
        self.results_folder = results_folder
        self._run = runner or M.default_runner
        self._drv = None                       # sesiunea Appium
        self._server: Optional[subprocess.Popen] = None
        self._target = M.MobileTarget()
        self._serial = ""
        self._model = ""
        self._run_root = ""
        self._folder = ""                      # folderul telefonului in rularea curenta
        self._recording = False
        self.last_check: Optional[M.CheckResult] = None

    # ── rularea (apelat de motor) ──
    def begin_run(self, run_root: str) -> None:
        self._run_root = run_root

    @property
    def device_folder(self) -> str:
        return self._folder

    def end_run(self) -> None:
        """Salveaza filmul, logcat-ul si datele telefonului; inchide sesiunea (telefonul ramane cum e)."""
        if self._drv is not None and self._folder:
            if self._recording:
                try:
                    data = self._drv.stop_recording_screen()
                    if data:
                        with open(os.path.join(self._folder, "ecran_telefon.mp4"), "wb") as f:
                            f.write(base64.b64decode(data))
                except Exception:  # noqa: BLE001 — filmul nu are voie sa strice rularea
                    pass
                self._recording = False
            self._save_logcat()
        self._quit()
        self._run_root = ""
        self._folder = ""

    def _save_logcat(self) -> None:
        adb = M.adb_path()
        if not adb or not self._serial:
            return
        try:
            code, out = self._run([adb, "-s", self._serial, "logcat", "-d", "-t", "3000"], 30.0)
            if code == 0:
                with open(os.path.join(self._folder, "logcat.txt"), "w", encoding="utf-8") as f:
                    f.write(out)
        except Exception:  # noqa: BLE001
            pass

    def _quit(self) -> None:
        if self._drv is not None:
            try:
                self._drv.quit()
            except Exception:  # noqa: BLE001
                pass
        self._drv = None

    # ── conectare ──
    def _session(self):
        if self._drv is None:
            raise RprStepException("Telefonul nu e conectat. Pune la inceputul rutinei pasul "
                                   "\"Mobil: conecteaza telefonul\".")
        return self._drv

    def _ensure_server(self, stop: threading.Event) -> None:
        ok, _ = M.appium_status(self.appium_url)
        if ok:
            return
        exe = shutil.which("appium") or shutil.which("appium.cmd")
        if not exe:
            return          # verificarea de mai jos explica ce lipseste
        log = open(os.path.join(self._folder or self.results_folder or ".", "appium.log"), "a", encoding="utf-8")
        self._server = subprocess.Popen([exe, "--address", "127.0.0.1", "--port", self.appium_url.rsplit(":", 1)[-1]
                                         .strip("/") or "4723"], stdout=log, stderr=subprocess.STDOUT,
                                        creationflags=M._no_window())
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline and not stop.is_set():
            if M.appium_status(self.appium_url, 1.5)[0]:
                return
            time.sleep(0.5)

    def connect(self, value: str, stop: threading.Event) -> str:
        self._target = M.parse_target(value)
        self._quit()
        pre = M.check_device(self._target, self.appium_url, self._run, need_appium=False)
        if pre.ok and pre.serial:
            self._serial, self._model = pre.serial, pre.model
            root = self._run_root or M.run_root(self.results_folder, "test")
            self._folder = M.device_folder(root, pre.serial, pre.model)
            self._ensure_server(stop)
        check = M.check_device(self._target, self.appium_url, self._run)
        self.last_check = check
        if not check.ok:
            raise RprStepException("Telefonul nu e pregatit:\n" + check.text())
        self._serial, self._model = check.serial, check.model
        if not self._folder:
            self._folder = M.device_folder(self._run_root or M.run_root(self.results_folder, "test"),
                                           check.serial, check.model)
        try:
            from appium import webdriver
            from appium.options.android import UiAutomator2Options
        except ImportError as ex:
            raise RprStepException("Lipseste pachetul Python Appium: py -m pip install --user "
                                   f"Appium-Python-Client ({ex})")
        opts = UiAutomator2Options()
        opts.udid = check.serial
        opts.no_reset = True                  # nu sterge datele aplicatiei (login etc.)
        opts.new_command_timeout = 300
        if self._target.package:
            opts.app_package = self._target.package
            if self._target.activity:
                opts.app_activity = self._target.activity
        try:
            self._drv = webdriver.Remote(self.appium_url, options=opts)
        except Exception as ex:  # noqa: BLE001
            raise RprStepException(f"Appium nu a putut porni sesiunea pe {check.serial}: {ex}")
        try:
            self._drv.start_recording_screen(timeLimit="1800", bitRate="4000000")
            self._recording = True
        except Exception:  # noqa: BLE001 — unele telefoane nu permit filmarea
            self._recording = False
        try:
            with open(os.path.join(self._folder, "telefon.txt"), "w", encoding="utf-8") as f:
                f.write(f"Telefon: {check.model} ({check.serial})\nAplicatie: {self._target.describe()}\n"
                        f"Conectat: {_dt.datetime.now():%Y-%m-%d %H:%M:%S}\n\n{check.text()}\n")
        except OSError:
            pass
        return check.text()

    # ── cautare ──
    def _find(self, obj: UiObject, timeout_ms: int, stop: threading.Event):
        drv = self._session()
        locs = [(l, appium_by(l)) for l in obj.active_locators]
        locs = [(l, b) for l, b in locs if b]
        if not locs:
            raise RprStepException(f"Obiectul [{obj.name}] nu are locatori pentru telefon "
                                   "(AccessibilityId, ResourceId, UiAutomator, XPath sau Text).")
        deadline = time.monotonic() + max(0, timeout_ms) / 1000.0
        while True:
            for loc, (by, val) in locs:
                try:
                    found = drv.find_elements(by, val)
                except Exception:  # noqa: BLE001
                    found = []
                if found:
                    return found[0], loc
            if stop.is_set() or time.monotonic() >= deadline:
                return None, None
            time.sleep(0.3)

    def get_state(self, obj, timeout_ms, stop):
        el, loc = self._find(obj, timeout_ms, stop)
        if el is None:
            return NOT_FOUND
        try:
            return ElementState(True, el.is_displayed(), el.is_enabled(), el.text or "", el.text or "", loc)
        except Exception:  # noqa: BLE001
            return ElementState(True, used_locator=loc)

    def _el(self, req: ActionRequest, stop):
        el, _ = self._find(req.target, req.timeout_ms, stop)
        if el is None:
            raise ElementNotFound(req.target, req.timeout_ms)
        return el

    # ── actiuni ──
    def execute(self, req: ActionRequest, stop):
        a = req.action
        if a == RprAction.MobileConnect:
            self.connect(req.value, stop)
            return None
        drv = self._session()
        if a == RprAction.MobileBack:
            drv.back()
            return None
        if a == RprAction.MobileSwipe:
            d = SWIPES.get((req.value or "sus").strip().lower())
            if d is None:
                raise RprStepException(f"Directia \"{req.value}\" nu e cunoscuta: sus, jos, stanga sau dreapta.")
            size = drv.get_window_size()
            w, h = int(size["width"]), int(size["height"])
            drv.execute_script("mobile: swipeGesture", {"left": w // 10, "top": h // 5, "width": w * 8 // 10,
                                                        "height": h * 3 // 5, "direction": d, "percent": 0.75})
            return None
        if a in (RprAction.MobileScreenshot, RprAction.ScreenshotPage):
            path = self._shot_path(req.value, "ecran")
            drv.get_screenshot_as_file(path)
            return path
        if a == RprAction.MobileCloseApp:
            if not self._target.package:
                raise RprStepException("Nu stiu ce aplicatie sa inchid: scrie pachetul in pasul de conectare.")
            drv.terminate_app(self._target.package)
            return None
        if a == RprAction.PressKey and req.target is None:
            drv.press_keycode(keycode(req.value or "Enter"))
            return None
        if req.target is None:
            raise RprStepException(f"Pasul \"{a}\" nu se poate face pe telefon.")
        el = self._el(req, stop)
        if a in (RprAction.Click, RprAction.Focus):
            el.click()
        elif a == RprAction.DoubleClick:
            drv.execute_script("mobile: doubleClickGesture", {"elementId": el.id})
        elif a == RprAction.RightClick:
            drv.execute_script("mobile: longClickGesture", {"elementId": el.id, "duration": 1000})
        elif a == RprAction.TypeText:
            el.clear()
            el.send_keys(req.value)
        elif a == RprAction.AppendText:
            el.send_keys((el.text or "") + req.value)
        elif a == RprAction.Clear:
            el.clear()
        elif a == RprAction.PressKey:
            el.click()
            drv.press_keycode(keycode(req.value or "Enter"))
        elif a == RprAction.SelectOption:
            el.click()
            sel = (f'new UiScrollable(new UiSelector().scrollable(true)).scrollIntoView('
                   f'new UiSelector().text("{_q(req.value)}"))')
            opts = drv.find_elements("-android uiautomator", sel) or \
                drv.find_elements("-android uiautomator", f'new UiSelector().text("{_q(req.value)}")')
            if not opts:
                raise RprStepException(f"Optiunea \"{req.value}\" nu apare in lista.")
            opts[0].click()
        elif a in (RprAction.Check, RprAction.Uncheck):
            on = (el.get_attribute("checked") or "").lower() == "true"
            if on != (a == RprAction.Check):
                el.click()
        elif a in (RprAction.ReadText, RprAction.ReadValue):
            return el.text or ""
        elif a == RprAction.ReadAttribute:
            return el.get_attribute(req.value) or ""
        elif a == RprAction.ScreenshotElement:
            path = self._shot_path(req.value, req.target.name)
            el.screenshot(path)
            return path
        elif a == RprAction.Hover:
            raise RprStepException("Pe telefon nu exista „mouse deasupra”. Foloseste Click sau Click dreapta "
                                   "(apasare lunga).")
        else:
            raise RprStepException(f"Pasul \"{a}\" nu se poate face pe telefon.")
        return None

    def _shot_path(self, value: str, name: str) -> str:
        folder = os.path.join(self._folder, "capturi") if self._folder else os.path.join(self.results_folder, "capturi")
        os.makedirs(folder, exist_ok=True)
        v = (value or "").strip().strip('"')
        if v:
            return v if os.path.isabs(v) else os.path.join(folder, v if v.lower().endswith(".png") else v + ".png")
        return os.path.join(folder, f"{M._safe(name)}_{_dt.datetime.now():%H%M%S_%f}.png")

    def capture_error_screenshot(self, folder: str, name: str) -> Optional[str]:
        if self._drv is None:
            return None
        try:
            target = os.path.join(self._folder, "capturi") if self._folder else folder
            os.makedirs(target, exist_ok=True)
            path = os.path.join(target, f"EROARE_{M._safe(name)}_{_dt.datetime.now():%H%M%S}.png")
            self._drv.get_screenshot_as_file(path)
            return path
        except Exception:  # noqa: BLE001
            return None

    def close(self) -> None:
        try:
            self.end_run()
        finally:
            if self._server is not None:
                try:
                    self._server.terminate()
                except Exception:  # noqa: BLE001
                    pass
                self._server = None
