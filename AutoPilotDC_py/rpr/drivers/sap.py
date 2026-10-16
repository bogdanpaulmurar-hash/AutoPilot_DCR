# -*- coding: utf-8 -*-
# ============================================================
# AutoPilot DC — RPR (Python)
# drivers/sap.py — SAP GUI prin SAP GUI Scripting (COM, pywin32)
#
# Cerinte pe PC: SAP GUI for Windows + scripting activat
#   (SAP GUI Options -> Accessibility & Scripting -> Enable scripting;
#    pe server: parametrul sapgui/user_scripting = TRUE).
# Se ataseaza la SAP GUI deschis (Running Object Table, "SAPGUI"), ca un script VBS inregistrat.
#
#  - Spy: elementul SAP de sub mouse e conturat cu rosu (Visualize); F2 = captureaza, Esc = anuleaza.
#    Daca pozitia nu poate fi determinata, se captureaza campul care are focusul.
#  - Locatori: Id SAP (wnd[0]/usr/ctxt...) + Nume|Tip ca rezerva (identici cu versiunea C#).
# ============================================================

from __future__ import annotations

import datetime as _dt
import os
import re
import threading
import time
from typing import Any, Dict, Optional

from ..model import Locator, LocatorKind, RprAction, UiObject, UiTechnology
from .base import ActionRequest, ElementNotFound, ElementState, NOT_FOUND, RprStepException, UiDriver
from .desktop import clean_name, _first_line
from . import winutil

_PREFIX = {"GuiButton": "Buton", "GuiTextField": "Camp", "GuiCTextField": "Camp", "GuiPasswordField": "Camp",
           "GuiComboBox": "Lista", "GuiCheckBox": "Bifa", "GuiRadioButton": "Optiune", "GuiTab": "Tab",
           "GuiGridView": "Tabel", "GuiTableControl": "Tabel", "GuiLabel": "Text", "GuiStatusbar": "BaraStare"}


def relative_id(full_id: str) -> str:
    return re.sub(r"^/app/con\[\d+\]/ses\[\d+\]/", "", full_id or "")


def sap_vkey(key: str) -> int:
    """Tastele SAP (SendVKey): Enter=0, F1=1 ... F12=12, Shift+F1=13 ..., Ctrl+S=11."""
    k = key.strip().upper().replace(" ", "")
    if k.isdigit():
        return int(k)
    fixed = {"ENTER": 0, "CTRL+S": 11, "BACK": 3, "EXIT": 15, "CANCEL": 12, "PAGEUP": 81, "PGUP": 81,
             "PAGEDOWN": 82, "PGDN": 82, "CTRL+F": 71, "CTRL+P": 86}
    if k in fixed:
        return fixed[k]
    for prefix, base in (("CTRL+SHIFT+F", 36), ("SHIFT+F", 12), ("CTRL+F", 24), ("F", 0)):
        if k.startswith(prefix) and k[len(prefix):].isdigit() and 1 <= int(k[len(prefix):]) <= 12:
            return base + int(k[len(prefix):])
    raise RprStepException(f"Tasta SAP necunoscuta: \"{key}\". Exemple: Enter, F3, F8, Shift+F4, Ctrl+S sau codul numeric.")


def _s(f, default: str = "") -> str:
    try:
        v = f()
        return "" if v is None else str(v)
    except Exception:
        return default


def _item(coll, i: int):
    """Elementul i dintr-o colectie SAP (GuiComponentCollection / GuiCollection)."""
    for get in (lambda: coll(i), lambda: coll.Item(i), lambda: coll.ElementAt(i)):
        try:
            return get()
        except Exception:
            continue
    raise RprStepException(f"Elementul {i} nu exista in colectia SAP.")


def _b(f, default: bool) -> bool:
    try:
        return bool(f())
    except Exception:
        return default


class SapDriver(UiDriver):
    technology = UiTechnology.Sap
    display_name = "SAP GUI (Scripting)"

    def __init__(self):
        self._w = winutil.ComWorker("SAP-GUI-Scripting")
        self._session = None
        self._spy_cancel = threading.Event()

    # =========================================================
    # 1. Conectare la SAP GUI deschis
    # =========================================================
    def _connect(self, which: str = ""):
        try:
            import win32com.client
        except ImportError as ex:
            raise RprStepException("Pachetul pywin32 lipseste. Ruleaza INSTALEAZA.bat.") from ex
        try:
            rot = win32com.client.GetObject("SAPGUI")
        except Exception as ex:  # noqa: BLE001
            raise RprStepException("SAP GUI nu este deschis (sau scripting-ul este dezactivat). "
                                   "Deschide SAP Logon si autentifica-te.") from ex
        try:
            app = rot.GetScriptingEngine
        except Exception as ex:  # noqa: BLE001
            raise RprStepException("SAP GUI Scripting nu raspunde. Verifica daca scripting-ul este activat "
                                   "(Optiuni SAP GUI → Accesibilitate si Scripting).") from ex
        con = ses = 0
        which = (which or "").strip()
        if "/" in which:
            a, _, b = which.partition("/")
            con, ses = int(a or 0), int(b or 0)
        elif which.isdigit():
            ses = int(which)
        if int(app.Children.Count) == 0:
            raise RprStepException("Nu exista nicio conexiune SAP deschisa. Autentifica-te in SAP Logon.")
        connection = _item(app.Children, con)
        if int(connection.Children.Count) <= ses:
            raise RprStepException(f"Sesiunea SAP {ses} nu exista (deschise: {int(connection.Children.Count)}).")
        self._session = _item(connection.Children, ses)

    @property
    def session(self):
        if self._session is None:
            self._connect("")
        try:
            _ = self._session.Id   # sesiune inca vie?
        except Exception:
            self._connect("")
        return self._session

    def _wait_busy(self, timeout_ms: int):
        deadline = time.monotonic() + max(1000, timeout_ms) / 1000.0
        while bool(self.session.Busy):
            if time.monotonic() > deadline:
                raise RprStepException("SAP este ocupat (Busy) prea mult timp.")
            time.sleep(0.1)

    # =========================================================
    # 2. Gasire element
    # =========================================================
    def _find_once(self, obj: UiObject):
        for loc in obj.active_locators:
            try:
                el = None
                k = LocatorKind.parse(loc.kind)
                if k == LocatorKind.SapId:
                    el = self.session.FindById(loc.value, False)
                elif k == LocatorKind.SapName:
                    name, _, typ = loc.value.partition("|")
                    found = self.session.ActiveWindow.FindAllByName(name, typ)
                    if int(found.Count) >= 1:
                        el = _item(found, 0)
                if el is not None:
                    return el, loc
            except RprStepException:
                raise
            except Exception:
                pass   # locatorul nu se potriveste pe ecranul curent
        return None, None

    def _require(self, obj: UiObject, timeout_ms: int, stop):
        deadline = time.monotonic() + max(0, timeout_ms) / 1000.0
        while True:
            if stop is not None and stop.is_set():
                raise RprStepException("Oprit.")
            self._wait_busy(timeout_ms)
            el, _ = self._find_once(obj)
            if el is not None:
                return el
            if time.monotonic() >= deadline:
                screen = _s(lambda: f"ecran curent: {self.session.Info.Transaction} / {self.session.ActiveWindow.Text}")
                raise ElementNotFound(obj, timeout_ms, screen)
            time.sleep(0.25)

    # =========================================================
    # 3. UiDriver
    # =========================================================
    def get_state(self, obj, timeout_ms, stop):
        return self._w.call(self._get_state, obj, timeout_ms, stop)

    def _get_state(self, obj, timeout_ms, stop):
        deadline = time.monotonic() + max(0, timeout_ms) / 1000.0
        while True:
            try:
                el, used = self._find_once(obj)
            except RprStepException:
                return NOT_FOUND
            if el is not None:
                text = _s(lambda: el.Text)
                return ElementState(True, True, _b(lambda: el.Changeable, True), text, text, used)
            if time.monotonic() >= deadline or (stop is not None and stop.is_set()):
                return NOT_FOUND
            time.sleep(0.25)

    def highlight(self, obj, duration_ms, stop):
        try:
            self._w.call(self._visualize, obj, duration_ms)
        except Exception:
            pass

    def _visualize(self, obj, duration_ms):
        el, _ = self._find_once(obj)
        if el is None:
            return False
        el.Visualize(True)
        time.sleep(min(2.0, max(0.1, duration_ms / 1000.0)))
        el.Visualize(False)
        return True

    def capture_error_screenshot(self, folder, name):
        def f():
            try:
                path = os.path.join(folder, name + ".png")
                self.session.ActiveWindow.HardCopy(path, 2)   # 2 = PNG
                return path
            except Exception:
                return winutil.screenshot(os.path.join(folder, name + ".png"))
        try:
            return self._w.call(f)
        except Exception:
            return None

    def execute(self, req: ActionRequest, stop):
        try:
            return self._w.call(self._execute, req, stop)
        except RprStepException:
            raise
        except Exception as ex:  # noqa: BLE001
            msg = _first_line(ex)
            if "com_error" in type(ex).__name__ or "COM" in msg or "-2147" in msg:
                raise RprStepException(f"SAP: {msg}") from ex
            raise RprStepException(f"Actiunea {req.action} nu e suportata de acest element SAP ({msg}).") from ex

    def _execute(self, r: ActionRequest, stop):
        a = RprAction.parse(r.action)
        s = None
        # ── Fara obiect ──
        if a == RprAction.SapConnect:
            self._connect(r.value)
            s = self._session
            return f"{_s(lambda: s.Info.SystemName)} / client {_s(lambda: s.Info.Client)}"
        if a == RprAction.SapTransaction:
            tcode = r.value.strip()
            if not tcode:
                raise RprStepException("Codul tranzactiei lipseste.")
            s = self.session
            if tcode.lower().startswith(("/n", "/o")):
                s.FindById("wnd[0]/tbar[0]/okcd").Text = tcode
                s.FindById("wnd[0]").SendVKey(0)
            else:
                s.StartTransaction(tcode)
            self._wait_busy(r.timeout_ms)
            return None
        if a == RprAction.SapSendKey or (a == RprAction.PressKey and r.target is None):
            self.session.ActiveWindow.SendVKey(sap_vkey(r.value))
            self._wait_busy(r.timeout_ms)
            return None
        if a == RprAction.SapReadStatusBar:
            self._wait_busy(r.timeout_ms)
            sbar = self.session.FindById("wnd[0]/sbar")
            typ, text = _s(lambda: sbar.MessageType), _s(lambda: sbar.Text)   # S, E, W, I, A
            return f"{typ}: {text}" if typ else text

        # ── Pe obiect ──
        obj = r.target
        if obj is None:
            raise RprStepException("Actiunea are nevoie de un obiect.")
        el = self._require(obj, r.timeout_ms, stop)
        typ = _s(lambda: el.Type)

        if a == RprAction.Click:
            if typ == "GuiCheckBox":
                el.Selected = not bool(el.Selected)
            elif typ in ("GuiRadioButton", "GuiTab"):
                el.Select()
            elif typ in ("GuiTextField", "GuiCTextField", "GuiPasswordField"):
                el.SetFocus()
            else:
                el.Press()
        elif a == RprAction.DoubleClick:
            if typ == "GuiGridView":
                el.DoubleClickCurrentCell()
            else:
                el.SetFocus()
                self.session.ActiveWindow.SendVKey(2)   # F2 = dublu click / alegere
        elif a == RprAction.RightClick:
            el.ShowContextMenu()
        elif a == RprAction.TypeText:
            el.Text = r.value
        elif a == RprAction.AppendText:
            el.Text = str(el.Text) + r.value
        elif a == RprAction.Clear:
            el.Text = ""
        elif a in (RprAction.Focus, RprAction.Hover):
            el.SetFocus()
        elif a == RprAction.PressKey:
            el.SetFocus()
            self.session.ActiveWindow.SendVKey(sap_vkey(r.value))
        elif a == RprAction.SelectOption:
            self._select(el, r.value)
        elif a == RprAction.Check:
            el.Selected = True
        elif a == RprAction.Uncheck:
            el.Selected = False
        elif a in (RprAction.ReadText, RprAction.ReadValue):
            return _s(lambda: el.Text)
        elif a == RprAction.ReadAttribute:
            key = r.value.strip()
            simple = {"id": lambda: relative_id(str(el.Id)), "name": lambda: el.Name, "type": lambda: typ,
                      "tooltip": lambda: el.Tooltip, "changeable": lambda: str(_b(lambda: el.Changeable, False))}
            f = simple.get(key.lower())
            return _s(f) if f else _s(lambda: getattr(el, key))
        elif a == RprAction.SapGridReadCell:
            row, _, col = r.value.partition("|")
            if not row.strip().isdigit() or not col.strip():
                raise RprStepException("Valoarea trebuie sa fie \"rand|coloana\" (ex: 0|MATNR sau 0|2).")
            row_i = int(row)
            if typ == "GuiTableControl":
                # randurile sunt relative la zona vizibila: derulam tabelul pana la rand (scroll)
                visible = int(_s(lambda: el.VisibleRowCount) or 0)
                first = int(_s(lambda: el.VerticalScrollbar.Position) or 0)
                if visible and not first <= row_i < first + visible:
                    table_id = str(el.Id)
                    el.VerticalScrollbar.Position = row_i
                    self._wait_busy(r.timeout_ms)
                    el = self.session.FindById(table_id)   # dupa scroll obiectul tabelului se reincarca
                    first = int(_s(lambda: el.VerticalScrollbar.Position) or 0)
                return str(el.GetCell(row_i - first, int(col.strip())).Text)
            # GuiGridView (ALV): randurile nevazute se incarca doar dupa derulare
            visible = int(_s(lambda: el.VisibleRowCount) or 0)
            first = int(_s(lambda: el.FirstVisibleRow) or 0)
            if visible and not first <= row_i < first + visible:
                el.FirstVisibleRow = row_i
                self._wait_busy(r.timeout_ms)
            return str(el.GetCellValue(row_i, col.strip()))
        elif a == RprAction.SapGridRowCount:
            return str(int(el.RowCount))
        elif a == RprAction.Highlight:
            el.Visualize(True)
            time.sleep(0.8)
            el.Visualize(False)
            return None
        elif a == RprAction.ScreenshotElement:
            path = r.value.strip() or os.path.join(
                r.output_folder, f"{obj.name}_{_dt.datetime.now():%Y%m%d_%H%M%S_%f}"[:-3] + ".png")
            os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
            self.session.ActiveWindow.HardCopy(path, 2)
            return path
        else:
            raise RprStepException(f"Actiunea {a} nu e disponibila pentru SAP.")
        self._wait_busy(r.timeout_ms)
        return None

    @staticmethod
    def _select(el, value: str):
        entries = el.Entries
        want = value.strip().lower()
        for i in range(int(entries.Count)):
            e = _item(entries, i)
            if str(e.Value).strip().lower() == want or str(e.Key).strip().lower() == want:
                el.Key = str(e.Key)
                return
        raise RprStepException(f"Optiunea \"{value}\" nu exista in lista SAP.")

    # =========================================================
    # 4. Test (Biblioteca 🧪)
    # =========================================================
    def test_object(self, obj: UiObject) -> Dict[str, Any]:
        return self._w.call(self._test_object, obj)

    def _test_object(self, obj: UiObject) -> Dict[str, Any]:
        rows = []
        for loc in obj.locators:
            row = {"locator": loc, "in_container": None, "in_page": 0}
            try:
                if LocatorKind.parse(loc.kind) == LocatorKind.SapId:
                    row["in_page"] = 1 if self.session.FindById(loc.value, False) is not None else 0
                else:
                    name, _, typ = loc.value.partition("|")
                    row["in_page"] = int(self.session.ActiveWindow.FindAllByName(name, typ).Count)
            except RprStepException:
                raise
            except Exception as ex:  # noqa: BLE001
                row["error"] = _first_line(ex)
            rows.append(row)
        el, used = self._find_once(obj)
        if el is not None:
            self._visualize(obj, 1500)
        where = _s(lambda: f"SAP {self.session.Info.SystemName} · {self.session.Info.Transaction} · "
                           f"{self.session.ActiveWindow.Text}")
        return {"url": where, "found": el is not None, "used": used, "rows": rows, "container": "",
                "container_found": None}

    def show_object(self, obj: UiObject, duration_ms: int = 1500):
        def f():
            ok = self._visualize(obj, duration_ms)
            return ok, f"[{obj.name}] " + ("gasit" if ok else "nu a fost gasit pe ecranul SAP curent.")
        return self._w.call(f)

    # =========================================================
    # 5. Spy — elementul SAP de sub mouse; F2 captureaza, Esc anuleaza
    # =========================================================
    def cancel_spy(self):
        self._spy_cancel.set()

    def capture_object(self, hint: str, screenshot_folder: str, cancel: Optional[threading.Event] = None,
                       timeout_s: float = 600) -> Optional[UiObject]:
        self._spy_cancel.clear()
        return self._w.call(self._spy, cancel, timeout_s)

    def _spy(self, cancel, timeout_s):
        _ = self.session   # verifica conexiunea inainte
        winutil.wait_release(winutil.VK_F2)
        last = None
        end = time.monotonic() + timeout_s
        try:
            while time.monotonic() < end:
                if self._spy_cancel.is_set() or (cancel is not None and cancel.is_set()) or winutil.is_down(winutil.VK_ESCAPE):
                    return None
                x, y = winutil.cursor_pos()
                capture = winutil.is_down(winutil.VK_F2)
                id_ = self._id_at(x, y)
                if capture:
                    winutil.wait_release(winutil.VK_F2)
                    id_ = id_ or relative_id(_s(lambda: self.session.ActiveWindow.GuiFocus.Id))
                    if id_:
                        return self._build_object(self.session.FindById(id_))
                elif id_ and id_ != last:
                    self._try_visualize(last, False)
                    self._try_visualize(id_, True)
                    last = id_
                time.sleep(0.15)
            return None
        finally:
            self._try_visualize(last, False)

    def _id_at(self, x: int, y: int) -> Optional[str]:
        try:
            hits = self.session.FindByPosition(x, y, False)
            for i in range(int(hits.Count)):
                item = str(_item(hits, i))
                if item.startswith("/app/"):
                    return relative_id(item)
        except Exception:
            pass   # mouse-ul nu e deasupra unei ferestre SAP
        return None

    def _try_visualize(self, id_: Optional[str], on: bool):
        if not id_:
            return
        try:
            el = self.session.FindById(id_, False)
            if el is not None:
                el.Visualize(on)
        except Exception:
            pass

    @staticmethod
    def _build_object(el) -> UiObject:
        id_ = relative_id(str(el.Id))
        typ, name, text, tooltip = _s(lambda: el.Type), _s(lambda: el.Name), _s(lambda: el.Text), _s(lambda: el.Tooltip)
        # tooltip-ul SAP contine de obicei eticheta campului ("Material (F4)")
        basis = re.sub(r"\(.*?\)", "", tooltip) if tooltip.strip() else \
            (text if typ == "GuiButton" and text.strip() else name)
        obj = UiObject(name=clean_name(_PREFIX.get(typ, "SAP"), basis), technology=UiTechnology.Sap,
                       element_type=typ, captured_text=text, context=id_.split("/")[0],
                       locators=[Locator(LocatorKind.SapId, id_, 90)],
                       attributes={"Id": id_, "Name": name, "Type": typ, "Tooltip": tooltip})
        if name.strip() and typ.strip():
            obj.locators.append(Locator(LocatorKind.SapName, f"{name}|{typ}", 60))
        return obj

    def close(self):
        self._session = None
        self._w.stop()
