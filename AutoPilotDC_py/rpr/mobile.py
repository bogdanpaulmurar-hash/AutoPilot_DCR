# -*- coding: utf-8 -*-
# ============================================================
# AutoPilot DC v4.29 — 📱 Mobil: verificarea telefonului si folderul rularii
#
# Fara Appium aici (se importa doar in drivers/mobile.py, la conectare):
#   - parse_target("R58M12 | com.firma.app/.MainActivity") -> telefon, pachet, activitate
#   - check_device(...) -> lista de verificari (adb, telefon conectat si autorizat,
#     ecran deblocat, aplicatia instalata, baterie, Appium pornit)
#   - run_folder(...) -> <rezultate>\mobil\<data_ora>_<rutina>\<telefon>\
# Android: adb (Android platform-tools). iOS: urmeaza (are nevoie de Mac sau ferma in cloud).
# ============================================================

from __future__ import annotations

import datetime as _dt
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.request
from dataclasses import dataclass, field
from typing import Callable, List, Optional, Tuple

DEFAULT_APPIUM_URL = "http://127.0.0.1:4723"
MOBILE_SUBFOLDER = "mobil"
MIN_BATTERY = 20

# runner(args, timeout) -> (cod iesire, text); inlocuit in teste
Runner = Callable[[List[str], float], Tuple[int, str]]


def _no_window() -> int:
    return 0x08000000 if sys.platform == "win32" else 0   # CREATE_NO_WINDOW: fara consola sub pythonw


def default_runner(args: List[str], timeout: float = 15.0) -> Tuple[int, str]:
    try:
        p = subprocess.run(args, capture_output=True, text=True, timeout=timeout, encoding="utf-8",
                           errors="replace", creationflags=_no_window())
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except FileNotFoundError:
        return 127, "programul nu exista"
    except subprocess.TimeoutExpired:
        return 124, "nu a raspuns la timp"
    except OSError as ex:
        return 126, str(ex)


def adb_path() -> str:
    """adb din PATH sau din ANDROID_HOME / ANDROID_SDK_ROOT / locul implicit al Android Studio."""
    found = shutil.which("adb")
    if found:
        return found
    exe = "adb.exe" if sys.platform == "win32" else "adb"
    roots = [os.environ.get("ANDROID_HOME", ""), os.environ.get("ANDROID_SDK_ROOT", "")]
    if os.environ.get("LOCALAPPDATA"):
        roots.append(os.path.join(os.environ["LOCALAPPDATA"], "Android", "Sdk"))
    for r in roots:
        p = os.path.join(r, "platform-tools", exe) if r else ""
        if p and os.path.isfile(p):
            return p
    return ""


@dataclass
class MobileTarget:
    serial: str = ""          # gol = primul telefon conectat
    package: str = ""         # ex. com.firma.app
    activity: str = ""        # ex. .MainActivity (gol = cea de pornire)

    def describe(self) -> str:
        app = self.package + ("/" + self.activity if self.activity else "")
        return f"{self.serial or 'primul telefon'} | {app or 'fara aplicatie'}"


def parse_target(value: str) -> MobileTarget:
    """'R58M12 | com.firma.app/.MainActivity' ; '| com.firma.app' ; 'R58M12' ; 'com.firma.app'."""
    v = (value or "").strip()
    if "|" in v:
        serial, app = (x.strip() for x in v.split("|", 1))
    elif re.match(r"^[A-Za-z][\w]*(\.[A-Za-z_][\w]*)+(/.*)?$", v) and ":" not in v:
        serial, app = "", v                   # arata a pachet (com.x.y), nu a numar de serie
    else:
        serial, app = v, ""
    package, _, activity = app.partition("/")
    return MobileTarget(serial, package.strip(), activity.strip())


@dataclass
class DeviceInfo:
    serial: str
    state: str                # device / unauthorized / offline
    model: str = ""


def list_devices(run: Runner = default_runner, adb: Optional[str] = None) -> List[DeviceInfo]:
    adb = adb if adb is not None else adb_path()
    if not adb:
        return []
    code, out = run([adb, "devices", "-l"], 15.0)
    if code != 0:
        return []
    devs = []
    for line in out.splitlines():
        line = line.strip()
        if not line or line.startswith("List of devices") or line.startswith("*"):
            continue
        parts = line.split()
        if len(parts) < 2:
            continue
        m = re.search(r"model:(\S+)", line)
        devs.append(DeviceInfo(parts[0], parts[1], m.group(1).replace("_", " ") if m else ""))
    return devs


@dataclass
class CheckItem:
    ok: bool
    label: str
    detail: str = ""
    blocking: bool = True     # False = doar atentionare (ex. baterie putina)

    def line(self) -> str:
        mark = "✅" if self.ok else ("❌" if self.blocking else "⚠")
        return f"{mark} {self.label}" + (f": {self.detail}" if self.detail else "")


@dataclass
class CheckResult:
    items: List[CheckItem] = field(default_factory=list)
    serial: str = ""
    model: str = ""

    @property
    def ok(self) -> bool:
        return all(i.ok or not i.blocking for i in self.items)

    def text(self) -> str:
        return "\n".join(i.line() for i in self.items)

    def add(self, ok: bool, label: str, detail: str = "", blocking: bool = True) -> bool:
        self.items.append(CheckItem(ok, label, detail, blocking))
        return ok


def appium_status(url: str = DEFAULT_APPIUM_URL, timeout: float = 3.0) -> Tuple[bool, str]:
    try:
        with urllib.request.urlopen(url.rstrip("/") + "/status", timeout=timeout) as r:
            data = json.loads(r.read().decode("utf-8", "replace") or "{}")
        ver = ((data.get("value") or {}).get("build") or {}).get("version", "")
        return True, f"pornit{(' (versiunea ' + ver + ')') if ver else ''}"
    except Exception as ex:  # noqa: BLE001
        return False, f"nu raspunde la {url} ({type(ex).__name__})"


def appium_client_installed() -> bool:
    try:
        import importlib.util
        return importlib.util.find_spec("appium") is not None
    except Exception:  # noqa: BLE001
        return False


def _screen_locked(dumpsys_window: str) -> Optional[bool]:
    for rx in (r"mDreamingLockscreen=(true|false)", r"isStatusBarKeyguard=(true|false)",
               r"mShowingLockscreen=(true|false)", r"KeyguardShowing=(true|false)"):
        m = re.search(rx, dumpsys_window)
        if m:
            return m.group(1) == "true"
    return None


def check_device(target: MobileTarget, appium_url: str = DEFAULT_APPIUM_URL, run: Runner = default_runner,
                 adb: Optional[str] = None, appium: Optional[Callable[[str], Tuple[bool, str]]] = None,
                 client_installed: Optional[bool] = None, need_appium: bool = True) -> CheckResult:
    """Verificarile dinainte de rulare. Se opreste la prima problema care le face pe celelalte inutile."""
    res = CheckResult()
    adb = adb if adb is not None else adb_path()
    if not res.add(bool(adb), "Android platform-tools (adb)", adb or
                   "nu e instalat; pune folderul platform-tools in PATH sau seteaza ANDROID_HOME"):
        return res
    devs = list_devices(run, adb)
    ready = [d for d in devs if d.state == "device"]
    if target.serial:
        dev = next((d for d in devs if d.serial == target.serial), None)
    else:
        dev = ready[0] if ready else (devs[0] if devs else None)
    if dev is None:
        res.add(False, "Telefon conectat", (f"{target.serial} nu apare in adb devices" if target.serial else
                                            "niciun telefon; conecteaza-l prin USB si activeaza Depanare USB"))
        return res
    res.serial, res.model = dev.serial, dev.model
    if not res.add(dev.state == "device", "Telefon conectat", f"{dev.model or dev.serial} ({dev.serial})" +
                   ("" if dev.state == "device" else
                    " — accepta pe telefon „Permite depanarea USB”" if dev.state == "unauthorized"
                    else f" — stare {dev.state}")):
        return res
    if len(ready) > 1 and not target.serial:
        res.add(False, "Mai multe telefoane", "conectate: " + ", ".join(d.serial for d in ready) +
                f"; folosesc {dev.serial}. Scrie telefonul in pas ca sa fie sigur.", blocking=False)
    sh = [adb, "-s", dev.serial, "shell"]
    code, out = run(sh + ["dumpsys", "window"], 15.0)
    locked = _screen_locked(out) if code == 0 else None
    if locked is None:
        res.add(False, "Ecran deblocat", "nu pot afla; verifica pe telefon", blocking=False)
    else:
        res.add(not locked, "Ecran deblocat", "" if not locked else "deblocheaza telefonul")
    if target.package:
        code, out = run(sh + ["pm", "list", "packages", target.package], 15.0)
        installed = code == 0 and any(l.strip() == "package:" + target.package for l in out.splitlines())
        res.add(installed, "Aplicatia instalata", target.package if installed else f"{target.package} nu e instalata")
    code, out = run(sh + ["dumpsys", "battery"], 15.0)
    m = re.search(r"level:\s*(\d+)", out) if code == 0 else None
    if m:
        lvl = int(m.group(1))
        res.add(lvl >= MIN_BATTERY, "Baterie", f"{lvl}%" + ("" if lvl >= MIN_BATTERY else " — pune-l la incarcat"),
                blocking=False)
    if need_appium:
        inst = appium_client_installed() if client_installed is None else client_installed
        if not res.add(inst, "Pachetul Python Appium", "instalat" if inst else
                       "lipseste: py -m pip install --user Appium-Python-Client"):
            return res
        ok, detail = (appium or appium_status)(appium_url)
        res.add(ok, "Serverul Appium", detail + ("" if ok else "; porneste-l cu: appium"))
    return res


# ── Folderul rularii pe telefon ──────────────────────────────
def _safe(name: str) -> str:
    return re.sub(r'[\\/:*?"<>|\s]+', "_", (name or "").strip()).strip("_.") or "telefon"


def run_root(results_folder: str, routine_name: str, when: Optional[_dt.datetime] = None) -> str:
    """<rezultate>\\mobil\\<AAAA-LL-ZZ_HHMMSS>_<rutina> (nu se creeaza aici)."""
    when = when or _dt.datetime.now()
    return os.path.join(results_folder, MOBILE_SUBFOLDER, f"{when:%Y-%m-%d_%H%M%S}_{_safe(routine_name)}")


def device_folder(root: str, serial: str, model: str = "") -> str:
    name = _safe(f"{model}_{serial}" if model else serial)
    path = os.path.join(root, name)
    os.makedirs(path, exist_ok=True)
    return path


def uses_mobile(routine, find=None) -> bool:
    """Rutina are pasi pe telefon? (actiuni Mobile sau, cu find = repo.find, pasi pe obiecte Mobile)."""
    from .model import ActionNode, UiTechnology
    for n in routine.all_nodes():
        if not isinstance(n, ActionNode):
            continue
        if n.technology == UiTechnology.Mobile:
            return True
        obj = find(n.target) if find and n.target.strip() else None
        if obj is not None and obj.technology == UiTechnology.Mobile:
            return True
    return False
