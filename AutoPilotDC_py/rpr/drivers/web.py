# -*- coding: utf-8 -*-
# ============================================================
# AutoPilot DC — RPR (Python)
# drivers/web.py — Web prin Playwright (Edge / Chrome instalat, fara descarcari)
#
#  1. Browser cu profil persistent (login-ul SSO ramane intre rulari).
#  2. Scriptul Spy (apdc-spy.js, acelasi ca in C#) injectat in fiecare pagina si iframe.
#  3. Gasire element cu fallback pe toti locatorii (self-healing):
#     primul locator care gaseste exact UN element castiga.
#  4. Spy (marcare obiect) si Recorder (actiuni din browser -> pasi).
#  5. Tab-uri noi deschise de aplicatie devin automat pagina curenta.
#
# Fire de executie: Playwright (API sincron) cere ca TOATE comenzile sa vina din
# acelasi fir. Motorul, Spy si Recorder-ul sunt pe fire diferite, deci driverul are
# firul lui ("lucratorul"): primeste comenzile la rand, iar intre ele proceseaza
# evenimentele browserului (click-uri capturate, popup-uri, tab-uri noi).
# ============================================================

from __future__ import annotations

import concurrent.futures
import datetime as _dt
import json
import os
import queue
import re
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple
from urllib.parse import urlsplit, urlunsplit

from ..model import Locator, LocatorKind, RprAction, UiObject, UiTechnology
from .base import ActionRequest, ElementNotFound, ElementState, NOT_FOUND, RprStepException, UiDriver

SPY_SCRIPT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "apdc-spy.js")

BROWSERS = [("Edge", "Microsoft Edge (recomandat)"), ("Chrome", "Google Chrome"),
            ("Chromium", "Chromium (descarcat de Playwright)"), ("Firefox", "Firefox (descarcat de Playwright)")]


@dataclass
class WebSettings:
    browser: str = "Edge"            # Edge / Chrome / Chromium / Firefox
    headless: bool = False
    profile_folder: str = ""         # gol = profil temporar
    navigation_timeout_ms: int = 60000


@dataclass
class RecordedAction:
    action: RprAction
    target: UiObject
    value: str


_ROLES = {
    "alert", "alertdialog", "application", "article", "banner", "blockquote", "button", "caption", "cell",
    "checkbox", "code", "columnheader", "combobox", "complementary", "contentinfo", "definition", "deletion",
    "dialog", "directory", "document", "emphasis", "feed", "figure", "form", "generic", "grid", "gridcell",
    "group", "heading", "img", "insertion", "link", "list", "listbox", "listitem", "log", "main", "marquee",
    "math", "meter", "menu", "menubar", "menuitem", "menuitemcheckbox", "menuitemradio", "navigation", "none",
    "note", "option", "paragraph", "presentation", "progressbar", "radio", "radiogroup", "region", "row",
    "rowgroup", "rowheader", "scrollbar", "search", "searchbox", "separator", "slider", "spinbutton", "status",
    "strong", "subscript", "superscript", "switch", "tab", "table", "tablist", "tabpanel", "term", "textbox",
    "time", "timer", "toolbar", "tooltip", "tree", "treegrid", "treeitem",
}

_KEY_NAMES = {
    "ctrl": "Control", "control": "Control", "shift": "Shift", "alt": "Alt", "win": "Meta", "meta": "Meta",
    "cmd": "Meta", "esc": "Escape", "escape": "Escape", "del": "Delete", "delete": "Delete", "ins": "Insert",
    "insert": "Insert", "enter": "Enter", "return": "Enter", "tab": "Tab", "space": "Space",
    "backspace": "Backspace", "pgup": "PageUp", "pageup": "PageUp", "pgdn": "PageDown", "pagedown": "PageDown",
    "home": "Home", "end": "End", "up": "ArrowUp", "down": "ArrowDown", "left": "ArrowLeft", "right": "ArrowRight",
}


def key_to_playwright(key: str) -> str:
    """"Ctrl+Shift+a" -> "Control+Shift+a" (formatul Playwright)."""
    parts = [p.strip() for p in (key or "").split("+") if p.strip()]
    out = []
    for p in parts:
        low = p.lower()
        if low in _KEY_NAMES:
            out.append(_KEY_NAMES[low])
        elif re.fullmatch(r"f\d{1,2}", low):
            out.append(low.upper())
        else:
            out.append(p)
    return "+".join(out)


def _first_line(s: str) -> str:
    s = str(s or "").strip()
    return s.splitlines()[0] if s else s


def _trim_url(url: str) -> str:
    """Pastram doar adresa + calea (fara parametri care se schimba)."""
    try:
        u = urlsplit(url)
        if u.scheme and u.netloc:
            return urlunsplit((u.scheme, u.netloc, u.path, "", ""))
    except Exception:
        pass
    return url or ""


def captured_to_object(el: Dict[str, Any], frame_path: List[str]) -> UiObject:
    """Elementul capturat de apdc-spy.js -> obiect pentru Object Repository."""
    obj = UiObject(
        name=el.get("suggestedName") or "Element",
        technology=UiTechnology.Web,
        element_type=(f"{el.get('tag', '')} ({el['role']})" if el.get("role") else el.get("tag", "")),
        captured_text=el.get("text", "") or "",
        context=_trim_url(el.get("url", "")),
        frame_path=list(frame_path),
        attributes={str(k): str(v) for k, v in (el.get("attributes") or {}).items()},
    )
    for l in el.get("locators") or []:
        try:
            obj.locators.append(Locator(LocatorKind.parse(l.get("kind", "")), str(l.get("value", "")), int(l.get("score", 50))))
        except ValueError:
            pass
    return obj


_RECORD_ACTIONS = {"Click": RprAction.Click, "DoubleClick": RprAction.DoubleClick, "TypeText": RprAction.TypeText,
                   "SelectOption": RprAction.SelectOption, "Check": RprAction.Check, "Uncheck": RprAction.Uncheck,
                   "PressKey": RprAction.PressKey}


class PlaywrightDriver(UiDriver):
    technology = UiTechnology.Web

    def __init__(self, settings: Optional[WebSettings] = None, technology: UiTechnology = UiTechnology.Web):
        self.settings = settings or WebSettings()
        self.technology = technology
        self.display_name = f"Web (Playwright, {self.settings.browser})"
        self.on_info: Optional[Callable[[str], None]] = None   # mesaje pentru Studio (pot veni de pe alt fir)

        self._jobs: "queue.Queue[tuple]" = queue.Queue()
        self._thread: Optional[threading.Thread] = None
        self._closing = False

        # starea Playwright — folosita DOAR pe firul lucratorului
        self._pw = None
        self._browser = None
        self._context = None
        self._page = None
        self._binding = False
        self._dialog_policy = "accept"
        self.last_dialog_message = ""
        self._spy_mode: Optional[str] = None      # "spy" / "record" / None
        self._spy_hint = ""
        self._spy_event: Optional[Dict[str, Any]] = None
        self._spy_frame = None
        self._spy_done = threading.Event()
        self._record_cb: Optional[Callable[[RecordedAction], None]] = None
        self._restart_frames: List[Any] = []
        self._pending_records: List[Tuple[Dict[str, Any], Any]] = []
        self._spy_source: Optional[str] = None
        self._hover_cb: Optional[Callable[[UiObject], None]] = None   # v4.9: captura cu cursorul tinut 3 s
        self._pending_hover: List[Tuple[Dict[str, Any], Any]] = []
        self._hover_folder = ""

    # =========================================================
    # Lucratorul (firul Playwright)
    # =========================================================
    def _call(self, fn: Callable, *args, **kwargs):
        if self._closing:
            raise RprStepException("Driverul web se inchide.")
        if self._thread is None or not self._thread.is_alive():
            self._thread = threading.Thread(target=self._run, daemon=True, name="PlaywrightWorker")
            self._thread.start()
        if threading.current_thread() is self._thread:   # apel din interiorul lucratorului
            return fn(*args, **kwargs)
        fut: concurrent.futures.Future = concurrent.futures.Future()
        self._jobs.put((fn, args, kwargs, fut))
        return fut.result()

    def _run(self):
        while True:
            try:
                job = self._jobs.get(timeout=0.05)
            except queue.Empty:
                self._pump()
                if self._closing and self._jobs.empty():
                    return
                continue
            if job is None:
                return
            fn, args, kwargs, fut = job
            try:
                fut.set_result(fn(*args, **kwargs))
            except BaseException as ex:  # noqa: BLE001
                fut.set_exception(ex)

    def _pump(self):
        """Intre comenzi: lasam Playwright sa livreze evenimentele (click-uri Spy, popup-uri, tab-uri noi)."""
        if self._context is None:
            return
        try:
            page = self._page if self._page is not None and not self._page.is_closed() else None
            if page is not None:
                page.wait_for_timeout(15)
        except Exception:
            pass
        self._process_pending()

    def _process_pending(self):
        # frame-uri navigate cat timp Spy / Recorder e activ: repornim scriptul in ele
        while self._restart_frames:
            f = self._restart_frames.pop(0)
            if self._spy_mode:
                self._start_spy_in_frame(f)
        # obiectele capturate cu cursorul tinut 3 s (v4.9)
        while self._pending_hover:
            ev, frame = self._pending_hover.pop(0)
            cb = self._hover_cb
            if cb is None:
                continue
            if ev is None:
                self._hover_cb = None
                self._stop_spy()
                try:
                    cb(None)
                except Exception:
                    pass
                continue
            if not ev.get("element"):
                continue
            try:
                obj = captured_to_object(ev["element"], self._frame_path(frame))
                self._verify_and_screenshot(obj, self._hover_folder)
                cb(obj)
            except Exception as ex:  # noqa: BLE001
                self._info("Eroare la captura: " + _first_line(ex))
        # actiunile inregistrate (calculul FramePath cere apeluri Playwright -> nu din handler)
        while self._pending_records:
            ev, frame = self._pending_records.pop(0)
            cb = self._record_cb
            action = _RECORD_ACTIONS.get(ev.get("action", ""))
            if cb is None or action is None or not ev.get("element"):
                continue
            try:
                obj = captured_to_object(ev["element"], self._frame_path(frame))
                cb(RecordedAction(action, obj, ev.get("value", "") or ""))
            except Exception as ex:  # noqa: BLE001
                self._info("Eroare la inregistrare: " + _first_line(ex))

    def _info(self, msg: str):
        cb = self.on_info
        if cb:
            try:
                cb(msg)
            except Exception:
                pass

    # =========================================================
    # 1. Pornire browser
    # =========================================================
    @property
    def is_open(self) -> bool:
        return self._call(self._is_open)

    def _is_open(self) -> bool:
        return self._page is not None and not self._page.is_closed()

    def open(self, url: Optional[str] = None) -> None:
        self._call(self._open, url)

    def _spy_js(self) -> str:
        if self._spy_source is None:
            with open(SPY_SCRIPT_PATH, encoding="utf-8") as f:
                self._spy_source = f.read()
        return self._spy_source

    def _open(self, url: Optional[str]):
        if self._context is None:
            try:
                from playwright.sync_api import sync_playwright
            except ImportError:
                raise RprStepException("Lipseste pachetul playwright. Ruleaza INSTALEAZA.bat din folderul aplicatiei.")
            if self._pw is None:
                self._pw = sync_playwright().start()
            self._context = self._launch()
            self._context.on("page", lambda p: self._on_new_page(p, from_popup=True))
            self._context.on("close", lambda *_: self._reset_state())
            self._context.add_init_script(self._spy_js())
            self._ensure_binding()
            for p in self._context.pages:
                self._on_new_page(p, from_popup=False)
            self._page = self._context.pages[0] if self._context.pages else self._context.new_page()
            self._inject_all_frames(self._page)
        elif not self._is_open():
            alive = [p for p in self._context.pages if not p.is_closed()]
            self._page = alive[-1] if alive else self._context.new_page()
        if url and url.strip():
            self._navigate(url)

    def _launch(self):
        """Porneste browserul. Ordinea incercarilor:
        1. profilul pastrat (login-ul ramane intre rulari) — fiecare browser are profilul lui;
        2. inca o data, dupa o pauza (profilul poate fi ocupat cateva secunde de o fereastra care se inchide);
        3. profil temporar: merge sigur, dar login-ul nu se pastreaza (anuntam utilizatorul)."""
        b = (self.settings.browser or "Edge").lower()
        channel = {"edge": "msedge", "chrome": "chrome"}.get(b)
        btype = self._pw.firefox if b == "firefox" else self._pw.chromium
        opts: Dict[str, Any] = dict(channel=channel, headless=self.settings.headless)
        if b != "firefox":
            opts["args"] = ["--start-maximized"]
            # sandbox-ul normal al browserului: fara steagul --no-sandbox (si fara bara galbena de avertizare)
            opts["chromium_sandbox"] = True
        errors: List[str] = []

        if self.settings.profile_folder:
            os.makedirs(self.settings.profile_folder, exist_ok=True)
            for attempt in range(2):
                try:
                    return btype.launch_persistent_context(self.settings.profile_folder, no_viewport=True,
                                                           accept_downloads=True, **opts)
                except Exception as ex:  # noqa: BLE001
                    errors.append(_first_line(ex))
                    time.sleep(1.5)

        try:
            self._browser = btype.launch(**opts)
            ctx = self._browser.new_context(no_viewport=True, accept_downloads=True)
            if errors:
                self._info("Profilul browserului nu a putut fi folosit (o fereastra AutoPilot ramasa deschisa il "
                           "blocheaza?). Am pornit cu un profil temporar: login-ul nu se pastreaza. Inchide ferestrele "
                           "de browser ramase de la AutoPilot si reporneste. Detalii: " + errors[-1])
            return ctx
        except Exception as ex:  # noqa: BLE001
            errors.append(_first_line(ex))
        hint = {"edge": "Verifica daca Microsoft Edge e instalat; inchide ferestrele Edge ramase deschise de AutoPilot. "
                        "Sau alege Google Chrome in 🌐 Setari Studio.",
                "chrome": "Verifica daca Google Chrome e instalat."}.get(
            b, "Ruleaza o data in PowerShell:  py -m playwright install " + b)
        raise RprStepException(f"Nu pot porni browserul ({self.settings.browser}). {hint} Detalii: {errors[-1]}")

    def _reset_state(self):
        self._context = self._page = self._browser = None
        self._binding = False

    def _on_new_page(self, page, from_popup: bool):
        def on_dialog(dialog):
            self.last_dialog_message = dialog.message
            self._info(f"Popup {dialog.type}: {dialog.message} → {self._dialog_policy}")
            try:
                dialog.dismiss() if self._dialog_policy == "dismiss" else dialog.accept()
            except Exception:
                pass

        def on_nav(frame):
            if self._spy_mode:
                self._restart_frames.append(frame)

        def on_close(*_):
            if self._page is page and self._context is not None:
                alive = [p for p in self._context.pages if not p.is_closed()]
                self._page = alive[-1] if alive else None

        page.on("dialog", on_dialog)
        page.on("framenavigated", on_nav)
        page.on("close", on_close)
        if from_popup:
            self._page = page
            self._info("Tab nou deschis de aplicatie — devine pagina curenta.")

    def _ensure_binding(self):
        if not self._binding and self._context is not None:
            self._context.expose_binding("__apdcEmit", self._on_emit)
            self._binding = True

    def _inject_all_frames(self, page):
        for f in page.frames:
            try:
                f.evaluate(self._spy_js())
            except Exception:
                pass

    def _require_page(self):
        if self._is_open():
            return self._page
        if self._context is not None:
            self._open(None)
            if self._is_open():
                return self._page
        raise RprStepException("Browserul nu este deschis. Adauga la inceputul rutinei pasul \"Deschide browser\".")

    # =========================================================
    # 2. Gasirea elementului (fallback pe toti locatorii)
    # =========================================================
    def _build(self, page, obj: UiObject, loc: Locator, scope=None):
        """Locatorul Playwright. scope = locatorul containerului (cautare doar in interiorul lui)."""
        if scope is not None:
            root = scope
        else:
            root = page
            for sel in obj.frame_path:
                root = root.frame_locator(sel)
        k, v = loc.kind, loc.value
        if k == LocatorKind.Role:
            role, _, name = v.partition("|")
            if role.strip().lower() in _ROLES:
                return root.get_by_role(role.strip().lower(), name=name or None, exact=bool(name)) if name                     else root.get_by_role(role.strip().lower())
            return root.locator(v)
        if k == LocatorKind.Label:
            return root.get_by_label(v, exact=True)
        if k == LocatorKind.Placeholder:
            return root.get_by_placeholder(v, exact=True)
        if k == LocatorKind.Text:
            return root.get_by_text(v, exact=True)
        if k == LocatorKind.XPath:
            x = v[6:] if v.lower().startswith("xpath=") else v
            if scope is not None and x.startswith("/"):
                x = "." + x   # in container: XPath relativ la container
            return root.locator("xpath=" + x)
        if k == LocatorKind.Id:
            return root.locator('[id="' + v.replace("\\", "\\\\").replace('"', '\\"') + '"]')
        if k == LocatorKind.Name:
            return root.locator('[name="' + v.replace("\\", "\\\\").replace('"', '\\"') + '"]')
        return root.locator(v)   # Css, TestId (selector de atribut)

    def _scope_of(self, obj: UiObject):
        """Containerul obiectului (din biblioteca), gasit pe pagina; None = toata pagina."""
        parent = getattr(obj, "parent_ref", None)
        if parent is None:
            return None
        pl, _ = self._resolve(parent, 2000, None)
        return pl

    def _resolve(self, obj: UiObject, timeout_ms: int, stop: Optional[threading.Event]):
        """Primul locator care gaseste exact UN element. Cu container: intai in container
        (acolo e acceptat si primul din mai multe), apoi in toata pagina (doar daca e unic)."""
        page = self._require_page()
        deadline = time.monotonic() + max(0, timeout_ms) / 1000.0
        while True:
            scope = self._scope_of(obj)
            multi = None
            for sc in ([scope, None] if scope is not None else [None]):
                for loc in obj.active_locators:
                    if stop is not None and stop.is_set():
                        return None, None
                    try:
                        l = self._build(page, obj, loc, sc)
                        count = l.count()
                    except Exception:
                        continue   # locator invalid / frame in navigare
                    if count == 1:
                        return l, loc
                    if count > 1 and multi is None and (sc is not None or scope is None):
                        multi = (l.first, loc)
                if multi is not None:
                    return multi
            if time.monotonic() >= deadline or (stop is not None and stop.is_set()):
                return None, None
            try:
                page.wait_for_timeout(250)
            except Exception:
                pass
            page = self._require_page()

    def _require(self, obj: UiObject, timeout_ms: int, stop):
        l, _ = self._resolve(obj, timeout_ms, stop)
        if l is None:
            detail = f"pagina curenta: {self._page.url}" if self._is_open() else ""
            raise ElementNotFound(obj, timeout_ms, detail)
        return l

    # =========================================================
    # 3. UiDriver
    # =========================================================
    def get_state(self, obj, timeout_ms, stop):
        return self._call(self._get_state, obj, timeout_ms, stop)

    def _get_state(self, obj, timeout_ms, stop):
        if not self._is_open():
            return NOT_FOUND
        l, used = self._resolve(obj, timeout_ms, stop)
        if l is None:
            return NOT_FOUND
        try:
            visible, enabled = l.is_visible(), l.is_enabled()
            text = value = ""
            try:
                text = l.inner_text(timeout=2000).strip()
            except Exception:
                pass
            try:
                value = l.input_value(timeout=1000)
            except Exception:
                pass
            return ElementState(True, visible, enabled, text, value, used)
        except Exception:
            return NOT_FOUND   # elementul a disparut intre timp

    def highlight(self, obj, duration_ms, stop):
        try:
            self._call(self._highlight, obj, duration_ms, stop)
        except Exception:
            pass   # marcarea e optionala

    def _highlight(self, obj, duration_ms, stop):
        l, _ = self._resolve(obj, min(3000, duration_ms * 4), stop)
        if l is not None:
            l.evaluate("""(e, ms) => {
                if (window.__apdc) return window.__apdc.highlight(e, ms);
                const o = e.style.outline; e.style.outline = '3px solid #FF9900';
                setTimeout(() => e.style.outline = o, ms); return true; }""", duration_ms)

    def show_object(self, obj: UiObject, duration_ms: int = 1500) -> Tuple[bool, str]:
        """Pentru "👁 Arata" din Studio: gaseste + marcheaza; returneaza (gasit, mesaj)."""
        return self._call(self._show_object, obj, duration_ms)

    def _show_object(self, obj, duration_ms):
        if not self._is_open():
            return False, "Browserul nu e deschis."
        l, used = self._resolve(obj, 3000, None)
        if l is None:
            return False, f"[{obj.name}] nu a fost gasit pe pagina curenta ({self._page.url})."
        try:
            l.scroll_into_view_if_needed(timeout=2000)
        except Exception:
            pass
        self._highlight(obj, duration_ms, None)
        text = ""
        try:
            text = l.inner_text(timeout=1000).strip()[:80]
        except Exception:
            pass
        return True, f"[{obj.name}] gasit prin {used}" + (f" — text: \"{text}\"" if text else "")

    def current_url(self) -> str:
        try:
            return self._call(lambda: self._page.url if self._is_open() else "")
        except Exception:
            return ""

    def test_object(self, obj: UiObject) -> Dict[str, Any]:
        """🧪 Testeaza: cate elemente gaseste fiecare locator (in container si in pagina) + marcheaza elementul."""
        return self._call(self._test_object, obj)

    def _test_object(self, obj: UiObject) -> Dict[str, Any]:
        if not self._is_open():
            raise RprStepException("Browserul nu e deschis. Deschide pagina pe care vrei sa testezi obiectul.")
        page = self._page
        scope = self._scope_of(obj)
        parent = getattr(obj, "parent_ref", None)
        rows = []
        for loc in obj.locators:
            row = {"locator": loc, "in_container": None, "in_page": None}
            try:
                if scope is not None:
                    row["in_container"] = self._build(page, obj, loc, scope).count()
                row["in_page"] = self._build(page, obj, loc, None).count()
            except Exception as ex:  # noqa: BLE001
                row["error"] = _first_line(ex)
            rows.append(row)
        l, used = self._resolve(obj, 1500, None)
        if l is not None:
            try:
                l.scroll_into_view_if_needed(timeout=2000)
            except Exception:
                pass
            self._highlight(obj, 2000, None)
        return {"url": page.url, "found": l is not None, "used": used, "rows": rows,
                "container": parent.name if parent is not None else "",
                "container_found": scope is not None if parent is not None else None}

    def element_inside(self, container: UiObject, child: UiObject) -> bool:
        """Elementul capturat se afla in interiorul containerului (pe pagina curenta)?"""
        try:
            return bool(self._call(self._element_inside, container, child))
        except Exception:
            return False

    def _element_inside(self, container, child):
        cl, _ = self._resolve(container, 0, None)
        el, _ = self._resolve(child, 0, None)
        if cl is None or el is None:
            return False
        return cl.evaluate("(c, e) => c !== e && c.contains(e)", el.element_handle(timeout=1000))

    def capture_error_screenshot(self, folder, name):
        try:
            return self._call(self._shot, folder, name)
        except Exception:
            return None

    def _shot(self, folder, name):
        if not self._is_open():
            return None
        path = os.path.join(folder, name + ".png")
        self._page.screenshot(path=path)
        return path

    def execute(self, req, stop):
        return self._call(self._execute, req, stop)

    def _execute(self, r: ActionRequest, stop):
        try:
            return self._execute_core(r, stop)
        except RprStepException:
            raise
        except Exception as ex:  # noqa: BLE001  — erorile Playwright (inclusiv depasirile de timp)
            raise RprStepException(_first_line(ex))

    def _execute_core(self, r: ActionRequest, stop):
        t = r.timeout_ms
        a = r.action
        # ── Browser ──
        if a == RprAction.OpenBrowser:
            self._open(r.value)
            return None
        if a == RprAction.Navigate:
            self._require_page()
            self._navigate(r.value)
            return None
        if a == RprAction.Back:
            self._require_page().go_back(timeout=self.settings.navigation_timeout_ms)
            return None
        if a == RprAction.Refresh:
            self._require_page().reload(timeout=self.settings.navigation_timeout_ms)
            return None
        if a == RprAction.SwitchTab:
            return self._switch_tab(r.value)
        if a == RprAction.HandleDialog:
            self._dialog_policy = "dismiss" if r.value.strip().lower().startswith("d") else "accept"
            return self.last_dialog_message
        if a == RprAction.ScreenshotPage:
            page = self._require_page()
            path = self._output_path(r, "pagina")
            page.screenshot(path=path, full_page=True)
            return path
        if a == RprAction.CloseBrowser:
            self._close_browser()
            return None
        if a == RprAction.PressKey and r.target is None:
            self._require_page().keyboard.press(key_to_playwright(r.value))
            return None

        # ── Pe obiect ──
        if r.target is None:
            raise RprStepException("Actiunea are nevoie de un obiect.")
        obj = r.target
        l = self._require(obj, t, stop)
        if a == RprAction.Click:
            l.evaluate("e => e.click()") if r.direct_mode else l.click(timeout=t)
        elif a == RprAction.DoubleClick:
            l.dblclick(timeout=t)
        elif a == RprAction.RightClick:
            l.click(timeout=t, button="right")
        elif a == RprAction.Hover:
            l.hover(timeout=t)
        elif a == RprAction.TypeText:
            try:
                l.fill(r.value, timeout=t)
            except Exception:
                # elemente "custom" care nu accepta fill: click + selectare + tastare
                l.click(timeout=t)
                l.press("Control+A")
                l.press_sequentially(r.value, delay=15)
        elif a == RprAction.AppendText:
            l.press_sequentially(r.value, delay=25, timeout=t)
        elif a == RprAction.Clear:
            l.clear(timeout=t)
        elif a == RprAction.PressKey:
            l.press(key_to_playwright(r.value), timeout=t)
        elif a == RprAction.SelectOption:
            self._select_option(l, r.value, t)
        elif a == RprAction.Check:
            l.check(timeout=t)
        elif a == RprAction.Uncheck:
            l.uncheck(timeout=t)
        elif a == RprAction.Focus:
            l.focus(timeout=t)
        elif a == RprAction.ReadText:
            return l.inner_text(timeout=t).strip()
        elif a == RprAction.ReadValue:
            try:
                return l.input_value(timeout=t)
            except Exception:
                return (l.text_content(timeout=t) or "").strip()
        elif a == RprAction.ReadAttribute:
            return l.get_attribute(r.value, timeout=t) or ""
        elif a == RprAction.Highlight:
            self._highlight(obj, 800, stop)
        elif a == RprAction.ScreenshotElement:
            path = self._output_path(r, obj.name)
            l.screenshot(path=path, timeout=t)
            return path
        else:
            raise RprStepException(f"Actiunea {a} nu e disponibila pentru web.")
        return None

    def _navigate(self, url: str):
        url = url.strip()
        if "://" not in url and not url.lower().startswith(("about:", "file:", "data:")):
            url = "https://" + url
        self._page.goto(url, timeout=self.settings.navigation_timeout_ms, wait_until="domcontentloaded")

    def _switch_tab(self, value: str) -> str:
        self._require_page()
        pages = [p for p in self._context.pages if not p.is_closed()]
        target = None
        v = value.strip()
        if re.fullmatch(r"-?\d+", v):
            idx = int(v)
            if idx < 0:
                idx += len(pages)   # -1 = ultimul tab
            if 0 <= idx < len(pages):
                target = pages[idx]
        else:
            for p in pages:
                if v.lower() in (p.title() or "").lower() or v.lower() in (p.url or "").lower():
                    target = p
                    break
        if target is None:
            raise RprStepException(f"Nu exista tab-ul \"{value}\". Tab-uri deschise: {len(pages)}.")
        self._page = target
        target.bring_to_front()
        return target.title()

    @staticmethod
    def _select_option(l, value: str, timeout: int):
        tag = l.evaluate("e => e.tagName.toLowerCase()")
        if tag == "select":
            try:
                l.select_option(label=value, timeout=timeout)
            except Exception:
                l.select_option(value=value, timeout=timeout)
            return
        # dropdown "custom" (div-uri): deschidem lista si alegem optiunea dupa text
        l.click(timeout=timeout)
        page = l.page
        option = page.get_by_role("option", name=value, exact=True)
        if option.count() == 0:
            option = page.get_by_text(value, exact=True)
        option.first.click(timeout=timeout)

    @staticmethod
    def _output_path(r: ActionRequest, base: str) -> str:
        if r.value.strip() and r.action in (RprAction.ScreenshotElement, RprAction.ScreenshotPage):
            os.makedirs(os.path.dirname(os.path.abspath(r.value)), exist_ok=True)
            return r.value
        os.makedirs(r.output_folder, exist_ok=True)
        safe = re.sub(r'[\\/:*?"<>|]', "_", base)
        return os.path.join(r.output_folder, f"{safe}_{_dt.datetime.now():%Y%m%d_%H%M%S_%f}"[:-3] + ".png")

    # =========================================================
    # 4. Spy — marcarea interactiva a unui obiect
    # =========================================================
    def capture_object(self, hint: str, screenshot_folder: str, cancel: Optional[threading.Event] = None,
                       timeout_s: float = 600) -> Optional[UiObject]:
        """Blocheaza firul apelantului (NU firul interfetei!) pana cand utilizatorul da click
        pe un element in browser (sau Esc / anulare)."""
        self._spy_done.clear()
        self._call(self._start_spy, "spy", hint)
        try:
            end = time.monotonic() + timeout_s
            while not self._spy_done.wait(0.1):
                if (cancel is not None and cancel.is_set()) or time.monotonic() > end:
                    return None
            return self._call(self._finish_capture, screenshot_folder)
        finally:
            try:
                self._call(self._stop_spy)
            except Exception:
                pass

    def cancel_spy(self):
        self._spy_event = {"type": "cancel"}
        self._spy_done.set()

    def _start_spy(self, mode: str, hint: str):
        page = self._require_page()
        try:
            page.bring_to_front()
        except Exception:
            pass
        self._spy_mode, self._spy_hint, self._spy_event = mode, hint, None
        self._ensure_binding()
        for p in [p for p in self._context.pages if not p.is_closed()]:
            for f in p.frames:
                self._start_spy_in_frame(f)

    def _start_spy_in_frame(self, frame):
        try:
            frame.evaluate(self._spy_js())
            frame.evaluate("([m, h]) => window.__apdc.startSpy(m, h)", [self._spy_mode or "spy", self._spy_hint])
        except Exception:
            pass   # frame in navigare / detasat

    def _stop_spy(self):
        self._spy_mode = None
        if self._context is None:
            return
        for p in [p for p in self._context.pages if not p.is_closed()]:
            for f in p.frames:
                try:
                    f.evaluate("() => window.__apdc && window.__apdc.stopSpy()")
                except Exception:
                    pass

    def _on_emit(self, source, payload):
        """Apelat de Playwright (pe firul lucratorului) cand scriptul trimite un eveniment."""
        try:
            ev = json.loads(payload)
        except Exception:
            return
        frame = source.get("frame") if isinstance(source, dict) else None
        typ = ev.get("type")
        if self._spy_mode == "spy" and typ in ("captured", "cancel"):
            page = source.get("page") if isinstance(source, dict) else None
            if page is not None and not page.is_closed():
                self._page = page
            self._spy_event, self._spy_frame = ev, frame
            self._spy_done.set()
            return
        if self._spy_mode == "hover":
            if typ == "stop":
                self._spy_mode = None
                self._pending_hover.append((None, None))   # on_object(None) = oprit din browser (Esc)
            elif typ == "captured":
                self._pending_hover.append((ev, frame))
            return
        if self._spy_mode == "record":
            if typ == "stop":
                self._record_cb = None
                self._spy_mode = None
                self._info("Inregistrare oprita (Esc).")
            elif typ == "action":
                self._pending_records.append((ev, frame))

    def _finish_capture(self, screenshot_folder: str) -> Optional[UiObject]:
        ev = self._spy_event or {}
        if ev.get("type") != "captured" or not ev.get("element"):
            return None
        obj = captured_to_object(ev["element"], self._frame_path(self._spy_frame))
        self._verify_and_screenshot(obj, screenshot_folder)
        return obj

    def _frame_path(self, frame) -> List[str]:
        """Lantul de selectori de iframe de la pagina principala pana la frame-ul dat."""
        path: List[str] = []
        f = frame
        while f is not None and f.parent_frame is not None:
            try:
                el = f.frame_element()
                sel = el.evaluate("e => window.__apdc ? window.__apdc.frameSelector(e) : "
                                  "(e.id ? '#' + e.id : (e.name ? `iframe[name=\"${e.name}\"]` : 'iframe'))")
            except Exception:
                sel = "iframe"
            path.insert(0, sel or "iframe")
            f = f.parent_frame
        return path

    def _verify_and_screenshot(self, obj: UiObject, folder: str):
        """Fiecare locator e testat: cei care nu gasesc nimic sunt dezactivati (dar pastrati),
        cei ambigui raman doar ca rezerva. Se salveaza si o captura a elementului."""
        page = self._require_page()
        for loc in obj.locators:
            try:
                n = self._build(page, obj, loc).count()
                if n == 0:
                    loc.enabled = False
                elif n > 1:
                    loc.score = min(loc.score, 20)
            except Exception:
                loc.enabled = False
        obj.locators.sort(key=lambda l: (not l.enabled, -l.score))
        if not folder:
            return
        try:
            l, _ = self._resolve(obj, 1500, None)
            if l is not None:
                os.makedirs(folder, exist_ok=True)
                file = f"{obj.name}_{_dt.datetime.now():%Y%m%d_%H%M%S}.png"
                l.screenshot(path=os.path.join(folder, file), timeout=3000)
                obj.screenshot = file
        except Exception:
            pass   # captura e optionala

    # =========================================================
    # 4b. Captura cu cursorul tinut 3 s si scanarea paginii (v4.9)
    # =========================================================
    @property
    def is_hover_capturing(self) -> bool:
        return self._hover_cb is not None

    def start_hover_capture(self, on_object: Callable[[Optional[UiObject]], None], hint: str = "",
                            screenshot_folder: str = "") -> None:
        """Fiecare element pe care utilizatorul tine cursorul 3 s ajunge la on_object (pe firul lucratorului).
        Click-urile trec normal in pagina. Esc in browser = on_object(None); stop_hover_capture() opreste."""
        self._call(self._start_hover, on_object, hint, screenshot_folder)

    def _start_hover(self, on_object, hint, folder):
        self._require_page()
        self._hover_folder = folder or ""
        self._hover_cb = on_object
        self._pending_hover.clear()
        self._start_spy("hover", hint)

    def stop_hover_capture(self) -> None:
        self._hover_cb = None
        try:
            self._call(self._stop_spy)
        except Exception:
            pass

    def scan_page(self, max_items: int = 500, batch: int = 25,
                  cancel: Optional[threading.Event] = None) -> List[UiObject]:
        """Butoanele, campurile, listele, bifele si link-urile vizibile pe pagina curenta (si in iframe-uri).
        Doar citeste pagina: nu da click si nu trimite nimic la server. Lucrul se face in loturi mici,
        cu pauze intre ele, ca aplicatia din browser sa ramana fluida."""
        return self._call(self._scan_page, max_items, batch, cancel)

    def _scan_page(self, max_items, batch, cancel):
        page = self._require_page()
        out: List[UiObject] = []
        for frame in list(page.frames):
            left = max_items - len(out)
            if left <= 0 or (cancel is not None and cancel.is_set()):
                break
            try:
                frame.evaluate(self._spy_js())
                info = frame.evaluate("(m) => window.__apdc.scanStart(m)", left)
                found = int((info or {}).get("found", 0))
            except Exception:
                continue   # frame in navigare / detasat / alt domeniu blocat
            if not found:
                continue
            path = self._frame_path(frame)
            for start in range(0, found, batch):
                if cancel is not None and cancel.is_set():
                    break
                try:
                    items = frame.evaluate("([s, n]) => window.__apdc.scanBatch(s, n)", [start, batch]) or []
                except Exception:
                    break
                for el in items:
                    out.append(captured_to_object(el, path))
                page.wait_for_timeout(20)   # pauza: pagina isi face treaba intre loturi
        return out

    # =========================================================
    # 5. Recorder — click-uri / scriere din browser -> pasi
    # =========================================================
    @property
    def is_recording(self) -> bool:
        return self._record_cb is not None

    def start_recording(self, on_action: Callable[[RecordedAction], None], hint: str = "") -> None:
        self._call(self._start_recording, on_action, hint)

    def _start_recording(self, on_action, hint):
        self._require_page()
        self._record_cb = on_action
        self._start_spy("record", hint)

    def stop_recording(self) -> None:
        self._record_cb = None
        try:
            self._call(self._stop_spy)
        except Exception:
            pass

    # =========================================================
    # 6. Inchidere
    # =========================================================
    def close_browser(self) -> None:
        self._call(self._close_browser)

    def _close_browser(self):
        try:
            if self._context is not None:
                self._context.close()
            if self._browser is not None:
                self._browser.close()
        except Exception:
            pass
        self._reset_state()

    def close(self) -> None:
        if self._thread is None or not self._thread.is_alive():
            return
        try:
            self._call(self._shutdown)
        except Exception:
            pass
        self._closing = True
        self._jobs.put(None)

    def _shutdown(self):
        self._close_browser()
        try:
            if self._pw is not None:
                self._pw.stop()
        except Exception:
            pass
        self._pw = None
