# -*- coding: utf-8 -*-
# ============================================================
# AutoPilot DC — RPR (Python)
# drivers/desktop.py — Aplicatii desktop Windows prin UI Automation (pachetul uiautomation)
#
#  - Spy: elementul de sub mouse e conturat; F2 = captureaza, Esc = anuleaza.
#  - Locatori (identici cu versiunea C#): AutomationId > Tip|Nume > Tip|ClassName > cale in arbore
#    ("Pane[0]/Button[name=OK]").
#  - Context: "proces:nume.exe" (stabil) sau titlul ferestrei (regex).
#  - Mod direct: actiuni prin pattern-uri UIA (Invoke, Value, Toggle), fara miscarea mouse-ului.
# ============================================================

from __future__ import annotations

import datetime as _dt
import os
import re
import shlex
import subprocess
import threading
import time
import unicodedata
from typing import Any, Dict, List, Optional, Tuple

from ..model import Locator, LocatorKind, RprAction, UiObject, UiTechnology
from .base import ActionRequest, ElementNotFound, ElementState, NOT_FOUND, RprStepException, UiDriver
from . import winutil

_SCOPE_CHILDREN, _SCOPE_DESCENDANTS = 2, 4


def _first_line(ex) -> str:
    return (str(ex).strip().splitlines() or [type(ex).__name__])[0][:300]


def clean_name(prefix: str, basis: str, limit: int = 30) -> str:
    s = unicodedata.normalize("NFD", basis or "")
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = re.sub(r"[^A-Za-z0-9]+", "_", s).strip("_")[:limit].strip("_")
    return f"{prefix}_{s}" if s else prefix


_PREFIX = {"Button": "Buton", "Edit": "Camp", "ComboBox": "Lista", "CheckBox": "Bifa", "RadioButton": "Optiune",
           "MenuItem": "Meniu", "TabItem": "Tab", "Hyperlink": "Link", "DataItem": "Rand", "ListItem": "Rand",
           "Text": "Text", "Window": "Fereastra", "Document": "Document"}


class DesktopDriver(UiDriver):
    technology = UiTechnology.Desktop
    display_name = "Desktop (UI Automation)"

    def __init__(self):
        self._w = winutil.ComWorker("Desktop-UIA")
        self._auto = None
        self._iu = None
        self._window = None          # IUIAutomationElement atasat (LaunchApp / AttachWindow)
        self._pid = 0
        self._types: Dict[str, int] = {}
        self._type_names: Dict[int, str] = {}
        self._spy_cancel = threading.Event()

    # =========================================================
    # 0. Initializare (pe firul COM)
    # =========================================================
    def _ensure(self):
        if self._iu is None:
            try:
                import uiautomation as auto
            except ImportError as ex:
                raise RprStepException("Pachetul uiautomation lipseste. Ruleaza INSTALEAZA.bat.") from ex
            auto.InitializeUIAutomationInCurrentThread()
            self._auto = auto
            from uiautomation import uiautomation as _core   # modulul intern (are _AutomationClient)
            self._iu = _core._AutomationClient.instance().IUIAutomation
            for tid, name in auto.ControlTypeNames.items():
                short = name[:-7] if name.endswith("Control") else name
                self._types[short.lower()] = tid
                self._type_names[tid] = short
        return self._iu

    def _type_name(self, el) -> str:
        try:
            return self._type_names.get(el.CurrentControlType, str(el.CurrentControlType))
        except Exception:
            return ""

    def _control(self, el):
        return self._auto.Control.CreateControlFromElement(el)

    @staticmethod
    def _rect(el) -> Tuple[int, int, int, int]:
        r = el.CurrentBoundingRectangle
        return r.left, r.top, r.right, r.bottom

    @staticmethod
    def _arr(found) -> List[Any]:
        if not found:
            return []
        return [found.GetElement(i) for i in range(found.Length)]

    # =========================================================
    # 1. Ferestre / context
    # =========================================================
    def _windows(self, context: str) -> List[Any]:
        iu = self._ensure()
        root = iu.GetRootElement()
        context = (context or "").strip()
        if context.lower().startswith("proces:"):
            want = os.path.basename(context[7:].strip()).lower()
            if not want.endswith(".exe"):
                want += ".exe"
            out = []
            for w in self._arr(root.FindAll(_SCOPE_CHILDREN, iu.CreateTrueCondition())):
                try:
                    if winutil.process_name(w.CurrentProcessId).lower() == want:
                        out.append(w)
                except Exception:
                    pass
            return out
        if context:
            try:
                rx = re.compile(context, re.I)
            except re.error:
                rx = re.compile(re.escape(context), re.I)
            return [w for w in self._arr(root.FindAll(_SCOPE_CHILDREN, iu.CreateTrueCondition()))
                    if rx.search(w.CurrentName or "")]
        if self._pid:
            cond = iu.CreatePropertyCondition(30002, self._pid)   # ProcessId
            wins = self._arr(root.FindAll(_SCOPE_CHILDREN, cond))
            if wins:
                return wins
        return [self._window] if self._window is not None else []

    # =========================================================
    # 2. Gasire element
    # =========================================================
    def _find_all(self, root, loc: Locator) -> List[Any]:
        iu = self._iu
        k = LocatorKind.parse(loc.kind)
        if k == LocatorKind.AutomationId:
            return self._arr(root.FindAll(_SCOPE_DESCENDANTS, iu.CreatePropertyCondition(30011, loc.value)))
        if k in (LocatorKind.UiaName, LocatorKind.ClassName):
            typ, _, text = loc.value.partition("|") if "|" in loc.value else ("", "", loc.value)
            cond = iu.CreatePropertyCondition(30005 if k == LocatorKind.UiaName else 30012, text)
            tid = self._types.get(typ.strip().lower())
            if tid is not None:
                cond = iu.CreateAndCondition(cond, iu.CreatePropertyCondition(30003, tid))
            return self._arr(root.FindAll(_SCOPE_DESCENDANTS, cond))
        if k == LocatorKind.UiaPath:
            el = self._follow_path(root, loc.value)
            return [el] if el is not None else []
        return []

    def _resolve(self, obj: UiObject, timeout_ms: int, stop: Optional[threading.Event]):
        self._ensure()
        deadline = time.monotonic() + max(0, timeout_ms) / 1000.0
        while True:
            multi = None
            for win in self._windows(obj.context):
                for loc in obj.active_locators:
                    if stop is not None and stop.is_set():
                        return None, None
                    try:
                        found = self._find_all(win, loc)
                    except Exception:
                        continue   # fereastra s-a inchis intre timp
                    if len(found) == 1:
                        return found[0], loc
                    if found and multi is None:
                        multi = (found[0], loc)
            if multi is not None:
                return multi
            if time.monotonic() >= deadline or (stop is not None and stop.is_set()):
                return None, None
            time.sleep(0.3)

    def _require(self, obj: UiObject, timeout_ms: int, stop):
        el, _ = self._resolve(obj, timeout_ms, stop)
        if el is None:
            detail = f"nicio fereastra deschisa pentru contextul \"{obj.context}\"" if not self._windows(obj.context) else ""
            raise ElementNotFound(obj, timeout_ms, detail)
        return el

    # =========================================================
    # 3. UiDriver
    # =========================================================
    def get_state(self, obj, timeout_ms, stop):
        return self._w.call(self._get_state, obj, timeout_ms, stop)

    def _get_state(self, obj, timeout_ms, stop):
        el, used = self._resolve(obj, timeout_ms, stop)
        if el is None:
            return NOT_FOUND
        try:
            return ElementState(True, not el.CurrentIsOffscreen, bool(el.CurrentIsEnabled),
                                self._read_text(el), self._read_value(el), used)
        except Exception:
            return NOT_FOUND

    def highlight(self, obj, duration_ms, stop):
        try:
            self._w.call(self._highlight, obj, duration_ms, stop)
        except Exception:
            pass

    def _highlight(self, obj, duration_ms, stop, color=(255, 153, 0)):
        el, _ = self._resolve(obj, min(3000, duration_ms * 4), stop)
        if el is not None:
            winutil.Highlighter(color).flash(self._rect(el), duration_ms, stop)

    def capture_error_screenshot(self, folder, name):
        return winutil.screenshot(os.path.join(folder, name + ".png"))

    def execute(self, req: ActionRequest, stop):
        try:
            return self._w.call(self._execute, req, stop)
        except RprStepException:
            raise
        except Exception as ex:  # noqa: BLE001
            raise RprStepException(f"{type(ex).__name__}: {_first_line(ex)}") from ex

    def _execute(self, r: ActionRequest, stop):
        self._ensure()
        a = RprAction.parse(r.action)
        # ── Fara obiect ──
        if a == RprAction.LaunchApp:
            return self._launch(r.value, r.timeout_ms, stop)
        if a == RprAction.AttachWindow:
            return self._attach(r.value, r.timeout_ms, stop)
        if a == RprAction.CloseWindow:
            if self._window is not None:
                self._close_window(self._window)
            self._window, self._pid = None, 0
            return None
        if a == RprAction.PressKey and r.target is None:
            winutil.press_combo(r.value)
            return None

        obj = r.target
        if obj is None:
            raise RprStepException("Actiunea are nevoie de un obiect.")
        el = self._require(obj, r.timeout_ms, stop)
        c = self._control(el)
        P = self._auto.PatternId

        if a == RprAction.Click:
            if r.direct_mode and self._direct_click(c):
                return None
            c.Click(simulateMove=not r.direct_mode, waitTime=0.1)
        elif a == RprAction.DoubleClick:
            c.DoubleClick(waitTime=0.1)
        elif a == RprAction.RightClick:
            c.RightClick(waitTime=0.1)
        elif a == RprAction.Hover:
            c.MoveCursorToMyCenter()
        elif a == RprAction.TypeText:
            vp = c.GetPattern(P.ValuePattern)
            if vp is not None and not vp.IsReadOnly:
                vp.SetValue(r.value, waitTime=0.05)
            else:
                c.SetFocus()
                winutil.press_combo("Ctrl+A")
                winutil.type_text(r.value)
        elif a == RprAction.AppendText:
            c.SetFocus()
            winutil.press_combo("Ctrl+End")
            winutil.type_text(r.value)
        elif a == RprAction.Clear:
            vp = c.GetPattern(P.ValuePattern)
            if vp is not None and not vp.IsReadOnly:
                vp.SetValue("", waitTime=0.05)
            else:
                c.SetFocus()
                winutil.press_combo("Ctrl+A")
                winutil.press_combo("Delete")
        elif a == RprAction.PressKey:
            c.SetFocus()
            winutil.press_combo(r.value)
        elif a == RprAction.SelectOption:
            self._select(el, c, r.value)
        elif a in (RprAction.Check, RprAction.Uncheck):
            want = a == RprAction.Check
            tp = c.GetPattern(P.TogglePattern)
            if tp is not None:
                for _ in range(3):
                    if (tp.ToggleState == 1) == want:
                        break
                    tp.Toggle(waitTime=0.05)
            else:
                sp = c.GetPattern(P.SelectionItemPattern)
                if sp is not None and want:
                    sp.Select(waitTime=0.05)
                else:
                    c.Click(waitTime=0.1)
        elif a == RprAction.Focus:
            c.SetFocus()
        elif a == RprAction.ReadText:
            return self._read_text(el)
        elif a == RprAction.ReadValue:
            return self._read_value(el)
        elif a == RprAction.ReadAttribute:
            key = r.value.strip().lower()
            vals = {"name": lambda: el.CurrentName or "", "automationid": lambda: el.CurrentAutomationId or "",
                    "classname": lambda: el.CurrentClassName or "", "helptext": lambda: el.CurrentHelpText or "",
                    "isenabled": lambda: str(bool(el.CurrentIsEnabled)), "controltype": lambda: self._type_name(el),
                    "value": lambda: self._read_value(el)}
            if key not in vals:
                raise RprStepException("Atribute disponibile: Name, AutomationId, ClassName, HelpText, IsEnabled, "
                                       "ControlType, Value.")
            return vals[key]()
        elif a == RprAction.Highlight:
            winutil.Highlighter().flash(self._rect(el), 800, stop)
        elif a == RprAction.ScreenshotElement:
            path = r.value.strip() or os.path.join(
                r.output_folder, f"{obj.name}_{_dt.datetime.now():%Y%m%d_%H%M%S_%f}"[:-3] + ".png")
            if not winutil.screenshot(path, self._rect(el)):
                raise RprStepException("Captura elementului nu a reusit.")
            return path
        else:
            raise RprStepException(f"Actiunea {a} nu e disponibila pentru aplicatii desktop.")
        return None

    def _direct_click(self, c) -> bool:
        P = self._auto.PatternId
        for pid, call in ((P.InvokePattern, lambda p: p.Invoke(waitTime=0.05)),
                          (P.TogglePattern, lambda p: p.Toggle(waitTime=0.05)),
                          (P.SelectionItemPattern, lambda p: p.Select(waitTime=0.05)),
                          (P.ExpandCollapsePattern, lambda p: p.Expand(waitTime=0.05))):
            p = c.GetPattern(pid)
            if p is not None:
                call(p)
                return True
        return False

    def _select(self, el, c, value: str):
        iu = self._iu
        if self._type_name(el) == "ComboBox":
            try:
                if c.Select(value, simulateMove=False, waitTime=0.1):
                    return
            except Exception:
                pass
        items = self._arr(el.FindAll(_SCOPE_DESCENDANTS, iu.CreatePropertyCondition(30005, value)))
        if not items:
            raise RprStepException(f"Optiunea \"{value}\" nu exista in lista.")
        ic = self._control(items[0])
        sp = ic.GetPattern(self._auto.PatternId.SelectionItemPattern)
        if sp is not None:
            sp.Select(waitTime=0.05)
        else:
            ic.Click(waitTime=0.1)

    def _read_value(self, el) -> str:
        c = self._control(el)
        P = self._auto.PatternId
        try:
            vp = c.GetPattern(P.ValuePattern)
            if vp is not None:
                return vp.Value or ""
            lp = c.GetPattern(P.LegacyIAccessiblePattern)
            if lp is not None:
                return lp.Value or ""
        except Exception:
            pass
        return ""

    def _read_text(self, el) -> str:
        c = self._control(el)
        try:
            tp = c.GetPattern(self._auto.PatternId.TextPattern)
            if tp is not None:
                t = tp.DocumentRange.GetText(-1)
                if t and t.strip():
                    return t.strip()
        except Exception:
            pass   # unele controale raporteaza Text dar nu il ofera
        v = self._read_value(el)
        return v if v else (el.CurrentName or "")

    # ── Aplicatii / ferestre ──
    def _launch(self, value: str, timeout_ms: int, stop):
        value = value.strip()
        if value.startswith('"'):
            end = value.index('"', 1)
            exe, args = value[1:end], value[end + 1:].strip()
        else:
            m = re.search(r"\.exe\s", value, re.I)
            exe, args = (value[:m.start() + 4], value[m.end():]) if m else (value, "")
        try:
            proc = subprocess.Popen([exe] + (shlex.split(args, posix=False) if args else []))
        except OSError as ex:
            raise RprStepException(f"Aplicatia \"{exe}\" nu porneste: {_first_line(ex)}") from ex
        self._pid = proc.pid
        deadline = time.monotonic() + max(5000, timeout_ms) / 1000.0
        exe_name = os.path.basename(exe)
        while time.monotonic() < deadline and not (stop is not None and stop.is_set()):
            wins = self._windows("")   # ferestrele procesului pornit
            if not wins:   # Windows 11 / launcher: fereastra apare in alt proces cu acelasi nume
                wins = self._windows("proces:" + exe_name)
            wins = [w for w in wins if (w.CurrentName or "").strip()]
            if wins:
                self._window = wins[0]
                self._pid = wins[0].CurrentProcessId
                self._activate(wins[0])
                return wins[0].CurrentName or ""
            time.sleep(0.3)
        raise RprStepException(f"Aplicatia {exe_name} a pornit, dar fereastra nu a aparut.")

    def _attach(self, value: str, timeout_ms: int, stop):
        deadline = time.monotonic() + max(1000, timeout_ms) / 1000.0
        while True:
            wins = self._windows(value.strip())
            if wins:
                self._window, self._pid = wins[0], wins[0].CurrentProcessId
                self._activate(wins[0])
                return wins[0].CurrentName or ""
            if time.monotonic() >= deadline or (stop is not None and stop.is_set()):
                raise RprStepException(f"Nu gasesc fereastra \"{value}\". Foloseste titlul (regex) sau proces:nume.exe.")
            time.sleep(0.3)

    def _activate(self, win):
        try:
            h = win.CurrentNativeWindowHandle
            if h:
                self._auto.SetForegroundWindow(h)
        except Exception:
            pass

    def _close_window(self, win):
        try:
            wp = self._control(win).GetPattern(self._auto.PatternId.WindowPattern)
            if wp is not None:
                wp.Close(waitTime=0.1)
                return
        except Exception:
            pass
        try:
            winutil.user32.PostMessageW(win.CurrentNativeWindowHandle, 0x0010, 0, 0)   # WM_CLOSE
        except Exception:
            pass

    # =========================================================
    # 4. Test (Biblioteca 🧪) — numar de elemente per locator
    # =========================================================
    def test_object(self, obj: UiObject) -> Dict[str, Any]:
        return self._w.call(self._test_object, obj)

    def _test_object(self, obj: UiObject) -> Dict[str, Any]:
        self._ensure()
        wins = self._windows(obj.context)
        rows = []
        for loc in obj.locators:
            row = {"locator": loc, "in_container": None, "in_page": 0}
            try:
                row["in_page"] = sum(len(self._find_all(w, loc)) for w in wins)
            except Exception as ex:  # noqa: BLE001
                row["error"] = _first_line(ex)
            rows.append(row)
        el, used = self._resolve(obj, 1000, None)
        if el is not None:
            winutil.Highlighter().flash(self._rect(el), 1500)
        where = ", ".join((w.CurrentName or "?") for w in wins[:3]) or f"nicio fereastra pentru \"{obj.context}\""
        return {"url": where, "found": el is not None, "used": used, "rows": rows, "container": "",
                "container_found": None}

    def show_object(self, obj: UiObject, duration_ms: int = 1500):
        def f():
            el, used = self._resolve(obj, 3000, None)
            if el is None:
                return False, f"[{obj.name}] nu a fost gasit."
            winutil.Highlighter().flash(self._rect(el), duration_ms)
            return True, f"[{obj.name}] gasit prin {used}"
        return self._w.call(f)

    # =========================================================
    # 5. Spy — F2 captureaza elementul de sub mouse, Esc anuleaza
    # =========================================================
    def cancel_spy(self):
        self._spy_cancel.set()

    def capture_object(self, hint: str, screenshot_folder: str, cancel: Optional[threading.Event] = None,
                       timeout_s: float = 600) -> Optional[UiObject]:
        self._spy_cancel.clear()
        return self._w.call(self._spy, screenshot_folder, cancel, timeout_s)

    def _spy(self, folder, cancel, timeout_s):
        self._ensure()
        auto = self._auto
        hl = winutil.Highlighter((0, 215, 160))
        winutil.wait_release(winutil.VK_F2)
        end = time.monotonic() + timeout_s
        last = None
        try:
            while time.monotonic() < end:
                if self._spy_cancel.is_set() or (cancel is not None and cancel.is_set()) or winutil.is_down(winutil.VK_ESCAPE):
                    return None
                x, y = winutil.cursor_pos()
                el = None
                try:
                    c = auto.ControlFromPoint(x, y)
                    el = c.Element if c is not None else None
                except Exception:
                    pass
                if el is not None and winutil.is_down(winutil.VK_F2):
                    winutil.wait_release(winutil.VK_F2)
                    hl.hide()
                    obj = self._build_object(el)
                    self._save_screenshot(el, obj, folder)
                    winutil.Highlighter((50, 205, 50)).flash(self._rect(el), 600)
                    return obj
                if el is not None:
                    same = False
                    try:
                        same = last is not None and bool(self._iu.CompareElements(el, last))
                    except Exception:
                        pass
                    if not same:
                        try:
                            hl.show(*self._rect(el))
                        except Exception:
                            pass
                        last = el
                winutil.pump_messages()
                time.sleep(0.1)
            return None
        finally:
            hl.hide()

    def _top_window(self, el):
        walker = self._iu.ControlViewWalker
        root = self._iu.GetRootElement()
        cur = el
        try:
            while True:
                parent = walker.GetParentElement(cur)
                if not parent or self._iu.CompareElements(parent, root):
                    return cur
                cur = parent
        except Exception:
            return None

    def _build_object(self, el) -> UiObject:
        ctype = self._type_name(el)
        name = el.CurrentName or ""
        auto_id = el.CurrentAutomationId or ""
        cls = el.CurrentClassName or ""
        window = self._top_window(el)
        proc = winutil.process_name(el.CurrentProcessId)
        title = (window.CurrentName or "") if window is not None else ""
        obj = UiObject(name=clean_name(_PREFIX.get(ctype, ctype or "Element"), name or auto_id),
                       technology=UiTechnology.Desktop, element_type=ctype, captured_text=name,
                       context=("proces:" + proc) if proc else re.escape(title),
                       attributes={"Name": name, "AutomationId": auto_id, "ClassName": cls, "ControlType": ctype,
                                   "Fereastra": title, "Proces": proc})
        root = window if window is not None else self._iu.GetRootElement()

        def add_if_found(kind, value, score):
            if not value.strip():
                return
            try:
                n = len(self._find_all(root, Locator(kind, value)))
                if n >= 1:
                    obj.locators.append(Locator(kind, value, score if n == 1 else 20))
            except Exception:
                pass
        if auto_id and not auto_id.isdigit():
            add_if_found(LocatorKind.AutomationId, auto_id, 90)
        if name:
            add_if_found(LocatorKind.UiaName, f"{ctype}|{name}", 80)
        if cls:
            add_if_found(LocatorKind.ClassName, f"{ctype}|{cls}", 40)
        if window is not None:
            path = self._path_from(window, el)
            if path:
                obj.locators.append(Locator(LocatorKind.UiaPath, path, 30))
        obj.locators.sort(key=lambda l: -l.score)
        return obj

    def _save_screenshot(self, el, obj: UiObject, folder: str):
        if not folder:
            return
        file = f"{obj.name}_{_dt.datetime.now():%Y%m%d_%H%M%S}.png"
        if winutil.screenshot(os.path.join(folder, file), self._rect(el)):
            obj.screenshot = file

    # ── Cale in arbore: "Pane[1]/Button[name=OK]" (compatibila cu versiunea C#) ──
    def _path_from(self, window, el) -> str:
        iu = self._iu
        walker = iu.ControlViewWalker
        segs: List[str] = []
        cur = el
        try:
            while cur and not iu.CompareElements(cur, window):
                parent = walker.GetParentElement(cur)
                if not parent:
                    return ""
                ct, name = cur.CurrentControlType, cur.CurrentName or ""
                index = same_name = 0
                sib = walker.GetFirstChildElement(parent)
                while sib:
                    if iu.CompareElements(sib, cur):
                        break
                    if sib.CurrentControlType == ct:
                        index += 1
                        if (sib.CurrentName or "") == name:
                            same_name += 1
                    sib = walker.GetNextSiblingElement(sib)
                tname = self._type_names.get(ct, str(ct))
                segs.insert(0, f"{tname}[name={name}]" if name and same_name == 0 and "/" not in name and "]" not in name
                            else f"{tname}[{index}]")
                cur = parent
        except Exception:
            return ""
        return "/".join(segs)

    def _follow_path(self, root, path: str):
        walker = self._iu.ControlViewWalker
        cur = root
        for seg in [s for s in path.split("/") if s]:
            m = re.match(r"^(\w+)\[(?:name=(.*)|(\d+))\]$", seg)
            if not m:
                return None
            tid = self._types.get(m.group(1).lower())
            if tid is None:
                return None
            want_name = m.group(2)
            want_index = int(m.group(3)) if m.group(3) is not None else -1
            nxt, i = None, 0
            ch = walker.GetFirstChildElement(cur)
            while ch:
                if ch.CurrentControlType == tid:
                    if (want_name is not None and (ch.CurrentName or "") == want_name) or \
                            (want_name is None and i == want_index):
                        nxt = ch
                        break
                    i += 1
                ch = walker.GetNextSiblingElement(ch)
            if nxt is None:
                return None
            cur = nxt
        return cur

    def close(self):
        self._w.stop()
