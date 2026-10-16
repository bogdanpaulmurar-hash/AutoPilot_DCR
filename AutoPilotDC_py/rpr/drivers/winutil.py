# -*- coding: utf-8 -*-
# ============================================================
# AutoPilot DC — RPR (Python)
# drivers/winutil.py — Ajutoare Windows comune driverelor SAP / Desktop:
#   - ComWorker: un fir dedicat cu COM initializat (obiectele COM nu se muta intre fire)
#   - Highlighter: chenar colorat pe ecran (4 ferestre subtiri, click-through, nu apar in capturi)
#   - taste (Ctrl+S, F5, Enter...), scriere text Unicode, starea tastelor (F2 / Esc la Spy)
# ============================================================

from __future__ import annotations

import concurrent.futures
import ctypes
import os
import queue
import threading
import time
from ctypes import wintypes
from typing import Callable, Optional, Tuple

from .base import RprStepException

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)


# ─────────────────────────────────────────────────────────────
# 1. Fir COM dedicat
# ─────────────────────────────────────────────────────────────
class ComWorker:
    """Toate apelurile unui driver COM ruleaza pe acelasi fir (STA). call() asteapta rezultatul."""

    def __init__(self, name: str, init: Optional[Callable[[], None]] = None):
        self._name = name
        self._init = init
        self._jobs: "queue.Queue" = queue.Queue()
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

    def call(self, fn: Callable, *args, **kwargs):
        if threading.current_thread() is self._thread:
            return fn(*args, **kwargs)
        with self._lock:
            if self._thread is None or not self._thread.is_alive():
                self._thread = threading.Thread(target=self._run, daemon=True, name=self._name)
                self._thread.start()
        fut: concurrent.futures.Future = concurrent.futures.Future()
        self._jobs.put((fn, args, kwargs, fut))
        return fut.result()

    def _run(self):
        try:
            import pythoncom
            pythoncom.CoInitialize()
        except ImportError:
            try:
                import comtypes
                comtypes.CoInitializeEx()
            except Exception:
                pass
        if self._init:
            try:
                self._init()
            except Exception:
                pass
        while True:
            job = self._jobs.get()
            if job is None:
                return
            fn, args, kwargs, fut = job
            try:
                fut.set_result(fn(*args, **kwargs))
            except BaseException as ex:  # noqa: BLE001
                fut.set_exception(ex)

    def stop(self):
        if self._thread is not None and self._thread.is_alive():
            self._jobs.put(None)


# ─────────────────────────────────────────────────────────────
# 2. Chenar pe ecran
# ─────────────────────────────────────────────────────────────
WNDPROC = ctypes.WINFUNCTYPE(ctypes.c_ssize_t, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)


class WNDCLASSW(ctypes.Structure):
    _fields_ = [("style", wintypes.UINT), ("lpfnWndProc", WNDPROC), ("cbClsExtra", ctypes.c_int),
                ("cbWndExtra", ctypes.c_int), ("hInstance", wintypes.HINSTANCE), ("hIcon", wintypes.HICON),
                ("hCursor", wintypes.HANDLE), ("hbrBackground", wintypes.HBRUSH), ("lpszMenuName", wintypes.LPCWSTR),
                ("lpszClassName", wintypes.LPCWSTR)]


class MSG(ctypes.Structure):
    _fields_ = [("hwnd", wintypes.HWND), ("message", wintypes.UINT), ("wParam", wintypes.WPARAM),
                ("lParam", wintypes.LPARAM), ("time", wintypes.DWORD), ("pt", wintypes.POINT)]


user32.DefWindowProcW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
user32.DefWindowProcW.restype = ctypes.c_ssize_t
user32.CreateWindowExW.argtypes = [wintypes.DWORD, wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.DWORD, ctypes.c_int,
                                   ctypes.c_int, ctypes.c_int, ctypes.c_int, wintypes.HWND, wintypes.HMENU,
                                   wintypes.HINSTANCE, wintypes.LPVOID]
user32.CreateWindowExW.restype = wintypes.HWND
user32.SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
                                wintypes.UINT]
user32.DestroyWindow.argtypes = [wintypes.HWND]
user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
user32.SetLayeredWindowAttributes.argtypes = [wintypes.HWND, wintypes.COLORREF, wintypes.BYTE, wintypes.DWORD]
user32.PeekMessageW.argtypes = [ctypes.POINTER(MSG), wintypes.HWND, wintypes.UINT, wintypes.UINT, wintypes.UINT]
user32.TranslateMessage.argtypes = [ctypes.POINTER(MSG)]
user32.DispatchMessageW.argtypes = [ctypes.POINTER(MSG)]
user32.RegisterClassW.argtypes = [ctypes.POINTER(WNDCLASSW)]
user32.RegisterClassW.restype = wintypes.ATOM
gdi32.CreateSolidBrush.argtypes = [wintypes.COLORREF]
gdi32.CreateSolidBrush.restype = wintypes.HBRUSH
kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
kernel32.GetModuleHandleW.restype = wintypes.HMODULE

_WS_POPUP = 0x80000000
_WS_EX = 0x00000008 | 0x00000080 | 0x08000000 | 0x00000020 | 0x00080000   # TOPMOST|TOOLWINDOW|NOACTIVATE|TRANSPARENT|LAYERED
_SWP = 0x0010 | 0x0040                                                    # NOACTIVATE | SHOWWINDOW
_HWND_TOPMOST = wintypes.HWND(-1)
_wndproc = WNDPROC(lambda h, m, w, l: user32.DefWindowProcW(h, m, w, l))
_classes: dict = {}


def _rgb(color: Tuple[int, int, int]) -> int:
    r, g, b = color
    return r | (g << 8) | (b << 16)


def _class_for(color: Tuple[int, int, int]) -> str:
    name = "APDC_Highlight_%02X%02X%02X" % color
    if name not in _classes:
        wc = WNDCLASSW()
        wc.lpfnWndProc = _wndproc
        wc.hInstance = kernel32.GetModuleHandleW(None)
        wc.hbrBackground = gdi32.CreateSolidBrush(_rgb(color))
        wc.lpszClassName = name
        user32.RegisterClassW(ctypes.byref(wc))
        _classes[name] = wc
    return name


def pump_messages():
    msg = MSG()
    while user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, 1):   # PM_REMOVE
        user32.TranslateMessage(ctypes.byref(msg))
        user32.DispatchMessageW(ctypes.byref(msg))


class Highlighter:
    """Chenar colorat in jurul unui dreptunghi. Se foloseste pe UN singur fir (cel care l-a creat)."""

    def __init__(self, color: Tuple[int, int, int] = (255, 153, 0), thickness: int = 3):
        self.color, self.t = color, thickness
        self._hwnds = []

    def show(self, left: int, top: int, right: int, bottom: int):
        if right <= left or bottom <= top:
            return self.hide()
        if not self._hwnds:
            cls = _class_for(self.color)
            for _ in range(4):
                h = user32.CreateWindowExW(_WS_EX, cls, "", _WS_POPUP, 0, 0, 1, 1, None, None,
                                           kernel32.GetModuleHandleW(None), None)
                if h:
                    user32.SetLayeredWindowAttributes(h, 0, 230, 0x2)   # LWA_ALPHA
                    try:
                        user32.SetWindowDisplayAffinity(h, 0x11)         # nu apare in capturi
                    except Exception:
                        pass
                    self._hwnds.append(h)
        t = self.t
        rects = [(left - t, top - t, right - left + 2 * t, t), (left - t, bottom, right - left + 2 * t, t),
                 (left - t, top, t, bottom - top), (right, top, t, bottom - top)]
        for h, (x, y, w, hh) in zip(self._hwnds, rects):
            user32.SetWindowPos(h, _HWND_TOPMOST, x, y, w, hh, _SWP)
        pump_messages()

    def hide(self):
        for h in self._hwnds:
            user32.DestroyWindow(h)
        self._hwnds = []
        pump_messages()

    def flash(self, rect: Tuple[int, int, int, int], duration_ms: int, stop: Optional[threading.Event] = None):
        self.show(*rect)
        end = time.monotonic() + max(50, duration_ms) / 1000.0
        try:
            while time.monotonic() < end and not (stop is not None and stop.is_set()):
                pump_messages()
                time.sleep(0.03)
        finally:
            self.hide()


# ─────────────────────────────────────────────────────────────
# 3. Taste
# ─────────────────────────────────────────────────────────────
VK_F2, VK_ESCAPE = 0x71, 0x1B
_KEYS = {"CTRL": 0x11, "CONTROL": 0x11, "SHIFT": 0x10, "ALT": 0x12, "WIN": 0x5B, "ENTER": 0x0D, "RETURN": 0x0D,
         "TAB": 0x09, "ESC": 0x1B, "ESCAPE": 0x1B, "DEL": 0x2E, "DELETE": 0x2E, "INS": 0x2D, "INSERT": 0x2D,
         "BACKSPACE": 0x08, "SPACE": 0x20, "HOME": 0x24, "END": 0x23, "PGUP": 0x21, "PAGEUP": 0x21, "PGDN": 0x22,
         "PAGEDOWN": 0x22, "LEFT": 0x25, "UP": 0x26, "RIGHT": 0x27, "DOWN": 0x28}
_EXTENDED = {0x2E, 0x2D, 0x24, 0x23, 0x21, 0x22, 0x25, 0x26, 0x27, 0x28, 0x5B}


def to_vk(raw: str) -> int:
    s = raw.strip().upper()
    if s in _KEYS:
        return _KEYS[s]
    if len(s) == 1 and s.isalnum():
        return ord(s)
    if len(s) >= 2 and s[0] == "F" and s[1:].isdigit() and 1 <= int(s[1:]) <= 24:
        return 0x6F + int(s[1:])
    raise RprStepException(f"Tasta necunoscuta: \"{raw}\". Exemple: Enter, Tab, F5, Ctrl+S, Alt+F4.")


def is_down(vk: int) -> bool:
    return bool(user32.GetAsyncKeyState(vk) & 0x8000)


def wait_release(vk: int, stop: Optional[threading.Event] = None):
    while is_down(vk) and not (stop is not None and stop.is_set()):
        time.sleep(0.03)


def cursor_pos() -> Tuple[int, int]:
    pt = wintypes.POINT()
    user32.GetCursorPos(ctypes.byref(pt))
    return pt.x, pt.y


class _KEYBDINPUT(ctypes.Structure):
    _fields_ = [("wVk", wintypes.WORD), ("wScan", wintypes.WORD), ("dwFlags", wintypes.DWORD),
                ("time", wintypes.DWORD), ("dwExtraInfo", ctypes.c_size_t)]


class _MOUSEINPUT(ctypes.Structure):
    _fields_ = [("dx", wintypes.LONG), ("dy", wintypes.LONG), ("mouseData", wintypes.DWORD),
                ("dwFlags", wintypes.DWORD), ("time", wintypes.DWORD), ("dwExtraInfo", ctypes.c_size_t)]


class _INPUTUNION(ctypes.Union):
    _fields_ = [("ki", _KEYBDINPUT), ("mi", _MOUSEINPUT)]


class _INPUT(ctypes.Structure):
    _fields_ = [("type", wintypes.DWORD), ("u", _INPUTUNION)]


def _send(inputs):
    arr = (_INPUT * len(inputs))(*inputs)
    user32.SendInput(len(inputs), arr, ctypes.sizeof(_INPUT))


def _key(vk: int, up: bool) -> _INPUT:
    flags = (0x0002 if up else 0) | (0x0001 if vk in _EXTENDED else 0)
    return _INPUT(type=1, u=_INPUTUNION(ki=_KEYBDINPUT(wVk=vk, wScan=0, dwFlags=flags, time=0, dwExtraInfo=0)))


def press_combo(combo: str):
    """"Ctrl+Shift+S", "Enter", "F5", "Alt+F4"."""
    keys = [to_vk(k) for k in combo.split("+") if k.strip()]
    if not keys:
        return
    _send([_key(k, False) for k in keys] + [_key(k, True) for k in reversed(keys)])
    time.sleep(0.05)


def type_text(text: str, delay: float = 0.005):
    """Scrie text Unicode (diacritice incluse) in campul cu focus. \\n = Enter, \\t = Tab."""
    for ch in text:
        if ch == "\n":
            press_combo("Enter")
            continue
        if ch == "\t":
            press_combo("Tab")
            continue
        code = ord(ch)
        units = [code] if code <= 0xFFFF else [0xD800 + ((code - 0x10000) >> 10), 0xDC00 + ((code - 0x10000) & 0x3FF)]
        seq = []
        for u in units:
            seq.append(_INPUT(type=1, u=_INPUTUNION(ki=_KEYBDINPUT(wVk=0, wScan=u, dwFlags=0x0004, time=0, dwExtraInfo=0))))
            seq.append(_INPUT(type=1, u=_INPUTUNION(ki=_KEYBDINPUT(wVk=0, wScan=u, dwFlags=0x0004 | 0x0002, time=0,
                                                                   dwExtraInfo=0))))
        _send(seq)
        if delay:
            time.sleep(delay)


# ─────────────────────────────────────────────────────────────
# 4. Ferestre: aducere in fata (Windows blocheaza SetForegroundWindow simplu din fundal)
# ─────────────────────────────────────────────────────────────
user32.GetForegroundWindow.restype = wintypes.HWND
user32.WindowFromPoint.argtypes = [wintypes.POINT]
user32.WindowFromPoint.restype = wintypes.HWND
user32.GetAncestor.argtypes = [wintypes.HWND, wintypes.UINT]
user32.GetAncestor.restype = wintypes.HWND
user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
user32.SetForegroundWindow.argtypes = [wintypes.HWND]
user32.BringWindowToTop.argtypes = [wintypes.HWND]
user32.IsIconic.argtypes = [wintypes.HWND]


def root_window(hwnd) -> int:
    return int(user32.GetAncestor(hwnd, 2) or 0) if hwnd else 0   # GA_ROOT


def force_foreground(hwnd: int) -> bool:
    """Aduce fereastra in fata chiar daca procesul nostru nu e in prim-plan
    (AttachThreadInput la firul ferestrei active; la nevoie, apasarea unei taste neutre)."""
    if not hwnd:
        return False
    hwnd = wintypes.HWND(hwnd)
    if user32.IsIconic(hwnd):
        user32.ShowWindow(hwnd, 9)   # SW_RESTORE
    if root_window(user32.GetForegroundWindow()) == root_window(hwnd):
        return True
    fg = user32.GetForegroundWindow()
    fg_thread = user32.GetWindowThreadProcessId(fg, None) if fg else 0
    me = kernel32.GetCurrentThreadId()
    attached = bool(fg_thread and fg_thread != me and user32.AttachThreadInput(me, fg_thread, True))
    try:
        user32.BringWindowToTop(hwnd)
        user32.SetForegroundWindow(hwnd)
    finally:
        if attached:
            user32.AttachThreadInput(me, fg_thread, False)
    time.sleep(0.1)
    if root_window(user32.GetForegroundWindow()) != root_window(hwnd):
        # ultima varianta: o tasta neutra (F24) deblocheaza schimbarea ferestrei active
        _send([_key(0x87, False), _key(0x87, True)])
        user32.SetForegroundWindow(hwnd)
        time.sleep(0.1)
    return root_window(user32.GetForegroundWindow()) == root_window(hwnd)


def point_in_window(x: int, y: int, hwnd: int) -> bool:
    """Click-ul in (x, y) ajunge in fereastra hwnd (nu e acoperita de alta fereastra)?"""
    return root_window(user32.WindowFromPoint(wintypes.POINT(x, y))) == root_window(hwnd)


# ─────────────────────────────────────────────────────────────
# 5. Procese / ecran
# ─────────────────────────────────────────────────────────────
def process_name(pid: int) -> str:
    """"notepad.exe" pentru un PID (gol daca nu se poate citi)."""
    h = kernel32.OpenProcess(0x1000, False, pid)   # PROCESS_QUERY_LIMITED_INFORMATION
    if not h:
        return ""
    try:
        buf = ctypes.create_unicode_buffer(1024)
        size = wintypes.DWORD(1024)
        if kernel32.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(size)):
            return os.path.basename(buf.value)
        return ""
    finally:
        kernel32.CloseHandle(h)


def screenshot(path: str, rect: Optional[Tuple[int, int, int, int]] = None) -> Optional[str]:
    try:
        from PIL import ImageGrab
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        img = ImageGrab.grab(bbox=rect, all_screens=rect is None)
        img.save(path)
        return path
    except Exception:
        return None
