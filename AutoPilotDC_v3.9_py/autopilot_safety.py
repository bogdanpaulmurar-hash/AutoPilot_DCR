# -*- coding: utf-8 -*-
# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  AUTOPILOT DC v4.1 — Siguranta la rulare (echivalentul versiunii C#)         ║
# ║    - DoNotDisturb : "Nu deranja" (fara notificari Windows) cat timp ruleaza  ║
# ║    - RunFrame     : chenar rosu RUN / verde REC / portocaliu PAUZA           ║
# ║    - SafetyGuard  : sistemul de preventie (pauza + intrebare cand ceva       ║
# ║                     difera fata de inregistrare)                             ║
# ╚══════════════════════════════════════════════════════════════════════════════╝
#
# Compatibilitate cu C#: aceleasi chei JSON in pasi (window_title, window_process,
# screen_signature, guard_ignore), aceeasi amprenta, acelasi fisier de recuperare
# pentru "Nu deranja" (%LOCALAPPDATA%\AutoPilotDC\dnd_restore.json).

import base64
import ctypes
import json
import os
import re
import sys
import threading
import time
from ctypes import wintypes
from typing import Any, Dict, List, Optional, Set, Tuple

IS_WINDOWS = sys.platform == "win32"

# ==============================================================================
# 1. WIN32 (ctypes) — declaratii cu tipuri corecte (handle-urile sunt pe 64 de biti)
# ==============================================================================
if IS_WINDOWS:
    _user32 = ctypes.WinDLL("user32", use_last_error=True)
    _gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)
    _kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    _advapi32 = ctypes.WinDLL("advapi32", use_last_error=True)
    _ntdll = ctypes.WinDLL("ntdll")

    _WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    _MONITORENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HMONITOR, wintypes.HDC,
                                          ctypes.POINTER(wintypes.RECT), wintypes.LPARAM)
    _LONG_PTR = ctypes.c_ssize_t

    def _fn(dll, name, restype, *argtypes):
        f = getattr(dll, name)
        f.restype = restype
        f.argtypes = list(argtypes)
        return f

    WindowFromPoint = _fn(_user32, "WindowFromPoint", wintypes.HWND, wintypes.POINT)
    GetAncestor = _fn(_user32, "GetAncestor", wintypes.HWND, wintypes.HWND, wintypes.UINT)
    GetForegroundWindow = _fn(_user32, "GetForegroundWindow", wintypes.HWND)
    GetWindowTextW = _fn(_user32, "GetWindowTextW", ctypes.c_int, wintypes.HWND, wintypes.LPWSTR, ctypes.c_int)
    GetClassNameW = _fn(_user32, "GetClassNameW", ctypes.c_int, wintypes.HWND, wintypes.LPWSTR, ctypes.c_int)
    GetWindowThreadProcessId = _fn(_user32, "GetWindowThreadProcessId", wintypes.DWORD, wintypes.HWND, ctypes.POINTER(wintypes.DWORD))
    EnumWindows = _fn(_user32, "EnumWindows", wintypes.BOOL, _WNDENUMPROC, wintypes.LPARAM)
    EnumChildWindows = _fn(_user32, "EnumChildWindows", wintypes.BOOL, wintypes.HWND, _WNDENUMPROC, wintypes.LPARAM)
    IsWindowVisible = _fn(_user32, "IsWindowVisible", wintypes.BOOL, wintypes.HWND)
    IsHungAppWindow = _fn(_user32, "IsHungAppWindow", wintypes.BOOL, wintypes.HWND)
    GetCursorPos = _fn(_user32, "GetCursorPos", wintypes.BOOL, ctypes.POINTER(wintypes.POINT))
    SetCursorPos = _fn(_user32, "SetCursorPos", wintypes.BOOL, ctypes.c_int, ctypes.c_int)
    GetSystemMetrics = _fn(_user32, "GetSystemMetrics", ctypes.c_int, ctypes.c_int)
    GetWindowLongPtrW = _fn(_user32, "GetWindowLongPtrW", _LONG_PTR, wintypes.HWND, ctypes.c_int)
    SetWindowLongPtrW = _fn(_user32, "SetWindowLongPtrW", _LONG_PTR, wintypes.HWND, ctypes.c_int, _LONG_PTR)
    SetWindowDisplayAffinity = _fn(_user32, "SetWindowDisplayAffinity", wintypes.BOOL, wintypes.HWND, wintypes.DWORD)
    SetWindowPos = _fn(_user32, "SetWindowPos", wintypes.BOOL, wintypes.HWND, wintypes.HWND,
                       ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, wintypes.UINT)
    GetParent = _fn(_user32, "GetParent", wintypes.HWND, wintypes.HWND)
    EnumDisplayMonitors = _fn(_user32, "EnumDisplayMonitors", wintypes.BOOL, wintypes.HDC,
                              ctypes.c_void_p, _MONITORENUMPROC, wintypes.LPARAM)
    GetDC = _fn(_user32, "GetDC", wintypes.HDC, wintypes.HWND)
    ReleaseDC = _fn(_user32, "ReleaseDC", ctypes.c_int, wintypes.HWND, wintypes.HDC)

    CreateCompatibleDC = _fn(_gdi32, "CreateCompatibleDC", wintypes.HDC, wintypes.HDC)
    CreateCompatibleBitmap = _fn(_gdi32, "CreateCompatibleBitmap", wintypes.HBITMAP, wintypes.HDC, ctypes.c_int, ctypes.c_int)
    SelectObject = _fn(_gdi32, "SelectObject", wintypes.HGDIOBJ, wintypes.HDC, wintypes.HGDIOBJ)
    BitBlt = _fn(_gdi32, "BitBlt", wintypes.BOOL, wintypes.HDC, ctypes.c_int, ctypes.c_int, ctypes.c_int,
                 ctypes.c_int, wintypes.HDC, ctypes.c_int, ctypes.c_int, wintypes.DWORD)
    GetDIBits = _fn(_gdi32, "GetDIBits", ctypes.c_int, wintypes.HDC, wintypes.HBITMAP, wintypes.UINT,
                    wintypes.UINT, ctypes.c_void_p, ctypes.c_void_p, wintypes.UINT)
    DeleteObject = _fn(_gdi32, "DeleteObject", wintypes.BOOL, wintypes.HGDIOBJ)
    DeleteDC = _fn(_gdi32, "DeleteDC", wintypes.BOOL, wintypes.HDC)

    OpenProcess = _fn(_kernel32, "OpenProcess", wintypes.HANDLE, wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
    QueryFullProcessImageNameW = _fn(_kernel32, "QueryFullProcessImageNameW", wintypes.BOOL, wintypes.HANDLE,
                                     wintypes.DWORD, wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD))
    CloseHandle = _fn(_kernel32, "CloseHandle", wintypes.BOOL, wintypes.HANDLE)

    class _BITMAPINFOHEADER(ctypes.Structure):
        _fields_ = [("biSize", wintypes.DWORD), ("biWidth", wintypes.LONG), ("biHeight", wintypes.LONG),
                    ("biPlanes", wintypes.WORD), ("biBitCount", wintypes.WORD), ("biCompression", wintypes.DWORD),
                    ("biSizeImage", wintypes.DWORD), ("biXPelsPerMeter", wintypes.LONG),
                    ("biYPelsPerMeter", wintypes.LONG), ("biClrUsed", wintypes.DWORD), ("biClrImportant", wintypes.DWORD)]

    class _BITMAPINFO(ctypes.Structure):
        _fields_ = [("bmiHeader", _BITMAPINFOHEADER), ("bmiColors", wintypes.DWORD * 3)]

    class _SERVICE_STATUS(ctypes.Structure):
        _fields_ = [(n, wintypes.DWORD) for n in (
            "dwServiceType", "dwCurrentState", "dwControlsAccepted", "dwWin32ExitCode",
            "dwServiceSpecificExitCode", "dwCheckPoint", "dwWaitHint")]

    OpenSCManagerW = _fn(_advapi32, "OpenSCManagerW", wintypes.HANDLE, wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.DWORD)
    OpenServiceW = _fn(_advapi32, "OpenServiceW", wintypes.HANDLE, wintypes.HANDLE, wintypes.LPCWSTR, wintypes.DWORD)
    ControlService = _fn(_advapi32, "ControlService", wintypes.BOOL, wintypes.HANDLE, wintypes.DWORD, ctypes.POINTER(_SERVICE_STATUS))
    StartServiceW = _fn(_advapi32, "StartServiceW", wintypes.BOOL, wintypes.HANDLE, wintypes.DWORD, ctypes.c_void_p)
    QueryServiceStatus = _fn(_advapi32, "QueryServiceStatus", wintypes.BOOL, wintypes.HANDLE, ctypes.POINTER(_SERVICE_STATUS))
    CloseServiceHandle = _fn(_advapi32, "CloseServiceHandle", wintypes.BOOL, wintypes.HANDLE)

    NtQueryWnfStateData = _fn(_ntdll, "NtQueryWnfStateData", ctypes.c_long, ctypes.POINTER(ctypes.c_ulonglong),
                              ctypes.c_void_p, ctypes.c_void_p, ctypes.POINTER(ctypes.c_ulong),
                              ctypes.c_void_p, ctypes.POINTER(ctypes.c_ulong))

GA_ROOT = 2
GWL_EXSTYLE = -20
WS_EX_TRANSPARENT = 0x00000020
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_LAYERED = 0x00080000
WS_EX_NOACTIVATE = 0x08000000
WDA_EXCLUDEFROMCAPTURE = 0x00000011
HWND_TOPMOST = -1
SWP_NOACTIVATE, SWP_SHOWWINDOW = 0x0010, 0x0040
SRCCOPY = 0x00CC0020

OWN_PID = os.getpid()


# ==============================================================================
# 2. CE E PE ECRAN (ferestre, cursor, amprente)
# ==============================================================================
class WindowInfo:
    """O fereastra de nivel superior."""

    __slots__ = ("hwnd", "title", "class_name", "process", "pid")

    def __init__(self, hwnd=0, title="", class_name="", process="", pid=0):
        self.hwnd, self.title, self.class_name, self.process, self.pid = hwnd or 0, title, class_name, process, pid

    @property
    def is_dialog(self) -> bool:
        return self.class_name == "#32770"

    @property
    def is_own(self) -> bool:
        return self.pid == OWN_PID

    def __str__(self):
        return f"[{self.process}]" if not self.title else f'"{self.title}" ({self.process})'


_proc_cache: Dict[int, str] = {}


def _process_name(pid: int) -> str:
    if pid in _proc_cache:
        return _proc_cache[pid]
    name = ""
    h = OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
    if h:
        try:
            buf = ctypes.create_unicode_buffer(1024)
            size = wintypes.DWORD(1024)
            if QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(size)):
                name = os.path.basename(buf.value).lower()
        finally:
            CloseHandle(h)
    if len(_proc_cache) > 500:
        _proc_cache.clear()
    _proc_cache[pid] = name
    return name


def describe(hwnd) -> WindowInfo:
    if not IS_WINDOWS or not hwnd:
        return WindowInfo()
    t = ctypes.create_unicode_buffer(512)
    GetWindowTextW(hwnd, t, 512)
    c = ctypes.create_unicode_buffer(256)
    GetClassNameW(hwnd, c, 256)
    pid = wintypes.DWORD(0)
    GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    return WindowInfo(hwnd, t.value, c.value, _process_name(pid.value), pid.value)


def window_at(x: int, y: int) -> WindowInfo:
    """Fereastra principala (radacina) aflata sub punctul (x, y)."""
    if not IS_WINDOWS:
        return WindowInfo()
    h = WindowFromPoint(wintypes.POINT(int(x), int(y)))
    if not h:
        return WindowInfo()
    root = GetAncestor(h, GA_ROOT)
    return describe(root or h)


def foreground() -> WindowInfo:
    """Fereastra activa (in care ajung tastele)."""
    return describe(GetForegroundWindow()) if IS_WINDOWS else WindowInfo()


def top_level_windows() -> List[WindowInfo]:
    """Ferestrele vizibile de nivel superior (cu titlu sau dialoguri)."""
    out: List[WindowInfo] = []
    if not IS_WINDOWS:
        return out

    def cb(h, _):
        if IsWindowVisible(h) and not (GetWindowLongPtrW(h, GWL_EXSTYLE) & WS_EX_TOOLWINDOW):
            w = describe(h)
            if w.title or w.is_dialog:
                out.append(w)
        return True

    EnumWindows(_WNDENUMPROC(cb), 0)
    return out


def dialog_text(hwnd) -> str:
    """Mesajul dintr-un dialog standard Windows (controalele Static)."""
    parts: List[str] = []
    if not IS_WINDOWS:
        return ""

    def cb(h, _):
        c = ctypes.create_unicode_buffer(64)
        GetClassNameW(h, c, 64)
        if c.value in ("Static", "DirectUIHWND") and IsWindowVisible(h):
            t = ctypes.create_unicode_buffer(1024)
            GetWindowTextW(h, t, 1024)
            if t.value.strip():
                parts.append(t.value.strip())
        return sum(len(p) for p in parts) < 1500

    EnumChildWindows(hwnd, _WNDENUMPROC(cb), 0)
    return "\n".join(parts)


def is_hung(hwnd) -> bool:
    return bool(IS_WINDOWS and hwnd and IsHungAppWindow(hwnd))


ERROR_WORDS = (
    "error", "eroare", "erori", "fehler", "exception", "exceptie", "excepție",
    "warning", "avertisment", "atentie", "atenție", "failed", "esuat", "eșuat",
    "not responding", "nu raspunde", "nu răspunde", "problem", "problema", "problemă",
    "fatal", "crash", "access denied", "acces refuzat",
)


def looks_like_error(text: str) -> bool:
    low = (text or "").lower()
    return any(w in low for w in ERROR_WORDS)


def cursor_pos() -> Tuple[int, int]:
    if not IS_WINDOWS:
        return (0, 0)
    p = wintypes.POINT()
    GetCursorPos(ctypes.byref(p))
    return (p.x, p.y)


def move_cursor(x: int, y: int) -> None:
    if IS_WINDOWS:
        SetCursorPos(int(x), int(y))


# ── Amprenta zonei din jurul unui punct (identica cu C# ScreenProbe) ──
PATCH = 40
SIG = 20


def capture_signature(x: int, y: int) -> Optional[str]:
    """Zona 40x40 centrata pe (x, y) -> gri -> medie 2x2 -> 20x20 octeti -> base64."""
    if not IS_WINDOWS:
        return None
    hdc = mdc = bmp = old = None
    try:
        vx, vy = GetSystemMetrics(76), GetSystemMetrics(77)
        vw, vh = GetSystemMetrics(78), GetSystemMetrics(79)
        left = min(max(int(x) - PATCH // 2, vx), max(vx, vx + vw - PATCH))
        top = min(max(int(y) - PATCH // 2, vy), max(vy, vy + vh - PATCH))

        hdc = GetDC(None)
        mdc = CreateCompatibleDC(hdc)
        bmp = CreateCompatibleBitmap(hdc, PATCH, PATCH)
        old = SelectObject(mdc, bmp)
        if not BitBlt(mdc, 0, 0, PATCH, PATCH, hdc, left, top, SRCCOPY):
            return None

        # 32 bpp, de sus in jos (inaltime negativa)
        bmi = _BITMAPINFO()
        bmi.bmiHeader.biSize = ctypes.sizeof(_BITMAPINFOHEADER)
        bmi.bmiHeader.biWidth = PATCH
        bmi.bmiHeader.biHeight = -PATCH
        bmi.bmiHeader.biPlanes = 1
        bmi.bmiHeader.biBitCount = 32
        buf = (ctypes.c_ubyte * (PATCH * PATCH * 4))()
        if not GetDIBits(mdc, bmp, 0, PATCH, ctypes.cast(buf, ctypes.c_void_p), ctypes.byref(bmi), 0):
            return None

        raw = bytes(buf)  # BGRA
        gray = [(raw[i + 2] * 299 + raw[i + 1] * 587 + raw[i] * 114) // 1000
                for i in range(0, len(raw), 4)]
        sig = bytearray(SIG * SIG)
        for sy in range(SIG):
            r0, r1 = (sy * 2) * PATCH, (sy * 2 + 1) * PATCH
            for sx in range(SIG):
                c0 = sx * 2
                sig[sy * SIG + sx] = (gray[r0 + c0] + gray[r0 + c0 + 1] +
                                      gray[r1 + c0] + gray[r1 + c0 + 1] + 2) // 4
        return base64.b64encode(bytes(sig)).decode("ascii")
    except Exception:
        return None
    finally:
        try:
            if old:
                SelectObject(mdc, old)
            if bmp:
                DeleteObject(bmp)
            if mdc:
                DeleteDC(mdc)
            if hdc:
                ReleaseDC(None, hdc)
        except Exception:
            pass


def compare_signatures(a: Optional[str], b: Optional[str]) -> Optional[float]:
    """0 = identice, 100 = complet diferite. None = nu se pot compara."""
    if not a or not b:
        return None
    try:
        x, y = base64.b64decode(a), base64.b64decode(b)
    except Exception:
        return None
    if len(x) != len(y) or not x:
        return None
    return sum(abs(p - q) for p, q in zip(x, y)) * 100.0 / (len(x) * 255.0)


def monitors() -> List[Tuple[int, int, int, int]]:
    """(x, y, latime, inaltime) pentru fiecare monitor."""
    out: List[Tuple[int, int, int, int]] = []
    if not IS_WINDOWS:
        return out

    def cb(_h, _dc, rc, _p):
        r = rc.contents
        out.append((r.left, r.top, r.right - r.left, r.bottom - r.top))
        return True

    EnumDisplayMonitors(None, None, _MONITORENUMPROC(cb), 0)
    return out


def make_overlay_window(hwnd) -> None:
    """Fereastra lasa click-urile sa treaca, nu ia focus, nu apare in capturi / Alt+Tab."""
    if not IS_WINDOWS or not hwnd:
        return
    ex = GetWindowLongPtrW(hwnd, GWL_EXSTYLE)
    SetWindowLongPtrW(hwnd, GWL_EXSTYLE, ex | WS_EX_TRANSPARENT | WS_EX_LAYERED | WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW)
    SetWindowDisplayAffinity(hwnd, WDA_EXCLUDEFROMCAPTURE)


# ==============================================================================
# 3. "NU DERANJA" (Focus Assist / Do not disturb)
# ==============================================================================
class DoNotDisturb:
    """
    Windows nu are API public pentru "Nu deranja". Scrierea directa a starii WNF NU
    blocheaza notificarile (testat pe Windows 10 22H2). Metoda care functioneaza:
      1. profilul "Microsoft.QuietHoursProfile.PriorityOnly" in
         HKCU\\...\\CloudStore\\...\\quiethourssettings\\Current -> Data
      2. repornirea serviciului de notificari al utilizatorului (WpnUserService_xxxx).
         Nu cere drepturi de administrator.
    Daca aplicatia e inchisa fortat, recover_if_needed() la urmatoarea pornire
    readuce notificarile (fisier comun cu versiunea C#).
    """

    BASE = r"Software\Microsoft\Windows\CurrentVersion\CloudStore\Store\DefaultAccount\Current"
    PREFIX = "Microsoft.QuietHoursProfile."
    ON = PREFIX + "PriorityOnly"
    OFF = PREFIX + "Unrestricted"

    _lock = threading.RLock()
    _users = 0
    _changed: Optional[List[str]] = None
    last_message = ""

    RECOVERY_FILE = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")),
                                 "AutoPilotDC", "dnd_restore.json")

    # ── API ──────────────────────────────────────────────────────
    @classmethod
    def enable(cls) -> bool:
        """Activeaza "Nu deranja" (cateva secunde — apeleaz-o pe un fir separat)."""
        if not IS_WINDOWS:
            return False
        with cls._lock:
            cls._users += 1
            if cls._users > 1:
                return cls.is_active() is not False
            try:
                targets = cls._discover()
                if not targets:
                    cls.last_message = "Nu deranja: setarea Windows nu a fost gasita."
                    return False
                if all(cls.read_profile(d) != cls.OFF for _, d in targets):
                    cls._changed = None
                    cls.last_message = "Nu deranja era deja activ."
                    return True
                cls._save_recovery([p for p, _ in targets])
                changed = []
                for path, data in targets:
                    blob = cls.write_profile(data, cls.ON)
                    if blob is not None and cls._write_blob(path, blob):
                        changed.append(path)
                if not changed:
                    cls._delete_recovery()
                    cls.last_message = "Nu deranja: setarea Windows nu a putut fi scrisa."
                    return False
                cls._changed = changed
                cls._save_recovery(changed)
                cls._restart_service()
                ok = cls._wait_state(True)
                cls.last_message = ("🌙 Nu deranja activ — notificarile sunt oprite pe durata rularii."
                                    if ok else "Nu deranja a fost setat, dar Windows nu a confirmat inca.")
                return ok
            except Exception as e:
                cls.last_message = f"Nu deranja nu a putut fi activat: {e}"
                return False

    @classmethod
    def restore(cls) -> None:
        """Reda notificarile (doar daca noi le-am oprit)."""
        with cls._lock:
            if cls._users == 0:
                return
            cls._users -= 1
            if cls._users > 0:
                return
            changed, cls._changed = cls._changed, None
            if changed:
                cls._restore_keys(changed)

    @classmethod
    def restore_all(cls) -> None:
        """La inchiderea aplicatiei."""
        with cls._lock:
            if cls._users:
                cls._users = 1
                cls.restore()

    @classmethod
    def recover_if_needed(cls) -> None:
        """La pornire: o rulare anterioara a ramas cu "Nu deranja" pornit -> il oprim."""
        try:
            if os.path.exists(cls.RECOVERY_FILE):
                with open(cls.RECOVERY_FILE, "r", encoding="utf-8") as f:
                    keys = json.load(f)
                with cls._lock:
                    cls._restore_keys(list(keys))
        except Exception:
            cls._delete_recovery()

    @staticmethod
    def is_active() -> Optional[bool]:
        """Starea efectiva: True = notificari blocate, False = libere, None = necunoscut."""
        if not IS_WINDOWS:
            return None
        try:
            name = ctypes.c_ulonglong(0x0D83063EA3BF1C75)  # WNF_SHEL_QUIETHOURS_ACTIVE_PROFILE_CHANGED
            stamp = ctypes.c_ulong(0)
            buf = (ctypes.c_ubyte * 16)()
            size = ctypes.c_ulong(16)
            st = NtQueryWnfStateData(ctypes.byref(name), None, None, ctypes.byref(stamp), buf, ctypes.byref(size))
            if st != 0 or size.value < 4:
                return None
            return int.from_bytes(bytes(buf[:4]), "little") != 0
        except Exception:
            return None

    # ── Blob-ul profilului (sir UTF-16 precedat de numarul de caractere) ──
    @classmethod
    def _find(cls, blob: bytes) -> int:
        return blob.find(cls.PREFIX.encode("utf-16-le"))

    @classmethod
    def read_profile(cls, blob: bytes) -> Optional[str]:
        i = cls._find(blob)
        if i < 1:
            return None
        n = blob[i - 1]
        if i + n * 2 > len(blob):
            return None
        return blob[i:i + n * 2].decode("utf-16-le", errors="replace")

    @classmethod
    def write_profile(cls, blob: bytes, profile: str) -> Optional[bytes]:
        """Doar profile cu aceeasi lungime (Unrestricted / PriorityOnly = 40 caractere)."""
        i = cls._find(blob)
        if i < 1:
            return None
        n = blob[i - 1]
        if n != len(profile) or i + n * 2 > len(blob):
            return None
        out = bytearray(blob)
        out[i:i + n * 2] = profile.encode("utf-16-le")
        # marca de timp: tag 2a 06 la offset 8, 5 octeti LEB128 (secunde Unix) de la offset 10
        if len(out) > 15 and out[8] == 0x2A and out[9] == 0x06:
            t = int(time.time())
            for k in range(5):
                b = t & 0x7F
                t >>= 7
                if k < 4:
                    b |= 0x80
                out[10 + k] = b
        return bytes(out)

    # ── Registry ─────────────────────────────────────────────────
    @classmethod
    def _discover(cls) -> List[Tuple[str, bytes]]:
        import winreg
        found = []
        try:
            root = winreg.OpenKey(winreg.HKEY_CURRENT_USER, cls.BASE)
        except OSError:
            return found
        with root:
            i = 0
            while True:
                try:
                    name = winreg.EnumKey(root, i)
                except OSError:
                    break
                i += 1
                if "quiethourssettings" not in name.lower():
                    continue
                try:
                    with winreg.OpenKey(root, name) as cont:
                        j = 0
                        while True:
                            try:
                                child = winreg.EnumKey(cont, j)
                            except OSError:
                                break
                            j += 1
                            path = f"{cls.BASE}\\{name}\\{child}"
                            try:
                                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, path) as k:
                                    data, _ = winreg.QueryValueEx(k, "Data")
                                if isinstance(data, bytes) and cls.read_profile(data):
                                    found.append((path, data))
                            except OSError:
                                pass
                except OSError:
                    pass
        return found

    @staticmethod
    def _write_blob(path: str, data: bytes) -> bool:
        import winreg
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, path, 0, winreg.KEY_SET_VALUE) as k:
                winreg.SetValueEx(k, "Data", 0, winreg.REG_BINARY, data)
            return True
        except OSError:
            return False

    @classmethod
    def _restore_keys(cls, keys: List[str]) -> None:
        import winreg
        for path in keys:
            try:
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, path) as k:
                    data, _ = winreg.QueryValueEx(k, "Data")
                # doar daca e inca profilul pus de noi
                if cls.read_profile(data) == cls.ON:
                    blob = cls.write_profile(data, cls.OFF)
                    if blob:
                        cls._write_blob(path, blob)
            except OSError:
                pass
        cls._restart_service()
        cls._wait_state(False)
        cls._delete_recovery()
        cls.last_message = "Notificarile Windows au fost repornite."

    @classmethod
    def _wait_state(cls, on: bool) -> bool:
        for _ in range(25):
            if cls.is_active() == on:
                return True
            time.sleep(0.2)
        return False

    @classmethod
    def _save_recovery(cls, keys: List[str]) -> None:
        try:
            os.makedirs(os.path.dirname(cls.RECOVERY_FILE), exist_ok=True)
            with open(cls.RECOVERY_FILE, "w", encoding="utf-8") as f:
                json.dump(keys, f)
        except OSError:
            pass

    @classmethod
    def _delete_recovery(cls) -> None:
        try:
            os.remove(cls.RECOVERY_FILE)
        except OSError:
            pass

    # ── Serviciul de notificari al utilizatorului ────────────────
    @staticmethod
    def _restart_service() -> None:
        import winreg
        names = []
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Services") as k:
                i = 0
                while True:
                    try:
                        n = winreg.EnumKey(k, i)
                    except OSError:
                        break
                    i += 1
                    if n.lower().startswith("wpnuserservice_"):
                        names.append(n)
        except OSError:
            return

        scm = OpenSCManagerW(None, None, 0x0001)  # SC_MANAGER_CONNECT
        if not scm:
            return
        try:
            for n in names:
                svc = OpenServiceW(scm, n, 0x0010 | 0x0020 | 0x0004)  # START | STOP | QUERY_STATUS
                if not svc:
                    continue  # instantele altor sesiuni
                try:
                    st = _SERVICE_STATUS()
                    if not QueryServiceStatus(svc, ctypes.byref(st)) or st.dwCurrentState != 4:
                        continue
                    ControlService(svc, 1, ctypes.byref(st))  # SERVICE_CONTROL_STOP
                    DoNotDisturb._wait_service(svc, 1)
                    # pornim mereu la loc: un serviciu de notificari oprit e mai rau decat un DND neaplicat
                    for _ in range(20):
                        if StartServiceW(svc, 0, None):
                            break
                        time.sleep(0.1)
                    DoNotDisturb._wait_service(svc, 4)
                finally:
                    CloseServiceHandle(svc)
        finally:
            CloseServiceHandle(scm)

    @staticmethod
    def _wait_service(svc, state: int) -> None:
        st = _SERVICE_STATUS()
        for _ in range(50):
            if QueryServiceStatus(svc, ctypes.byref(st)) and st.dwCurrentState == state:
                return
            time.sleep(0.1)


# ==============================================================================
# 4. SISTEMUL DE PREVENTIE
# ==============================================================================
class GuardAlert:
    """Ce a gasit sistemul de preventie."""

    def __init__(self, title: str, details: str, key: str, can_ignore_step: bool = True):
        self.title, self.details, self.key, self.can_ignore_step = title, details, key, can_ignore_step


# Raspunsurile utilizatorului
CONTINUE, IGNORE_STEP, RETRY, SKIP_STEP, STOP = "continue", "ignore_step", "retry", "skip_step", "stop"


class WindowWatcher:
    """Ferestre noi aparute in timpul rularii care arata a eroare."""

    def __init__(self):
        self._known: Set[int] = set()

    def reset(self):
        self._known.clear()
        self.accept_current()

    def accept_current(self):
        for w in top_level_windows():
            self._known.add(w.hwnd)

    def check_new_windows(self, expected_titles: Optional[Set[str]] = None,
                          report_all_dialogs: bool = False) -> Optional[GuardAlert]:
        expected = {t.lower() for t in (expected_titles or set())}
        for w in top_level_windows():
            if w.hwnd in self._known:
                continue
            self._known.add(w.hwnd)
            if w.is_own or w.title.lower() in expected:
                continue
            text = dialog_text(w.hwnd) if w.is_dialog else ""
            error = looks_like_error(w.title) or looks_like_error(text)
            if not error and not (report_all_dialogs and w.is_dialog):
                continue
            return GuardAlert(
                "A aparut o fereastra de eroare" if error else "A aparut o fereastra neasteptata",
                f"Fereastra: {w}" + (f"\n\nMesaj:\n{text}" if text else "") +
                "\n\nRezolv-o (citeste mesajul, inchide fereastra daca e cazul), apoi apasa Continua.",
                "window:" + w.title, can_ignore_step=False)
        return None


def similar_titles(a: str, b: str) -> bool:
    """La fel daca, fara cifre, unul il contine pe celalalt sau au un cuvant lung comun."""
    def norm(s):
        return re.sub(r"[\d\W_]+", " ", (s or "").lower()).strip()
    x, y = norm(a), norm(b)
    if not x or not y or x in y or y in x:
        return True
    wx = {w for w in x.split() if len(w) >= 4}
    return any(len(w) >= 4 and w in wx for w in y.split())


class SafetyGuard:
    """
    Inainte de fiecare pas verifica daca ecranul arata ca la inregistrare:
      1. mouse miscat de altcineva intre pasi
      2. ferestre noi de eroare / avertisment
      3. aplicatia activa nu raspunde
      4. click-ul ar ajunge in alta aplicatie decat la inregistrare
      5. zona din jurul click-ului arata diferit
      6. tastele ar ajunge in alta aplicatie
    Pasii inregistrati inainte de v4.1 nu au context: se verifica doar 1-3.
    """

    THRESHOLDS = {"relaxed": 35.0, "normal": 22.0, "strict": 12.0}

    def __init__(self):
        self.enabled = True
        self.sensitivity = "normal"
        self._windows = WindowWatcher()
        self._cursor_after_last: Optional[Tuple[int, int]] = None

    @property
    def screen_threshold(self) -> float:
        return self.THRESHOLDS.get(self.sensitivity, 22.0)

    def begin_run(self):
        self._windows.reset()
        self._cursor_after_last = cursor_pos()

    def acknowledge(self):
        self._windows.accept_current()
        self._cursor_after_last = cursor_pos()

    def after_step(self):
        self._cursor_after_last = cursor_pos()

    @staticmethod
    def record_context(step) -> None:
        """La inregistrare: fereastra + amprenta zonei (apelat imediat la click)."""
        try:
            t = step.step_type
            if t in ("CLICK", "DBLCLICK", "RIGHTCLICK"):
                w = window_at(step.x, step.y)
                step.window_title, step.window_process = w.title, w.process
                step.screen_signature = capture_signature(step.x, step.y) or ""
            elif t in ("TYPE", "KEY", "SCROLL"):
                w = window_at(step.x, step.y) if t == "SCROLL" else foreground()
                step.window_title, step.window_process = w.title, w.process
        except Exception:
            pass

    def check_before_step(self, step, upcoming: List[Any]) -> Optional[GuardAlert]:
        if not self.enabled or not IS_WINDOWS:
            return None

        # 1. mouse miscat de utilizator
        if self._cursor_after_last:
            lx, ly = self._cursor_after_last
            nx, ny = cursor_pos()
            if abs(nx - lx) + abs(ny - ly) > 40:
                self._cursor_after_last = (nx, ny)
                return GuardAlert(
                    "Mouse-ul a fost miscat in timpul rularii",
                    f"Mouse-ul era la ({lx}, {ly}) si acum e la ({nx}, {ny}).\n"
                    "Daca lucrezi in paralel, rutina poate da click unde nu trebuie.\n"
                    "Ia mana de pe mouse si apasa Continua cand esti gata.",
                    "mouse", can_ignore_step=False)

        # 2. ferestre noi de eroare (cele asteptate de pasii urmatori nu conteaza)
        nxt = upcoming[:4]
        expected = {getattr(s, "window_title", "") for s in nxt if getattr(s, "window_title", "")}
        has_ctx = any(getattr(s, "window_process", "") for s in nxt)
        alert = self._windows.check_new_windows(expected, report_all_dialogs=has_ctx)
        if alert:
            return alert

        # 3. aplicatia activa nu raspunde
        fg = foreground()
        if not fg.is_own and is_hung(fg.hwnd):
            return GuardAlert("Aplicatia nu raspunde",
                              f"Fereastra {fg} nu raspunde (\"Not Responding\").\n"
                              "Asteapta sa-si revina, apoi apasa Continua.",
                              "hung:" + fg.process, can_ignore_step=False)

        if getattr(step, "guard_ignore", False):
            return None

        # 4-5. click
        if step.step_type in ("CLICK", "DBLCLICK", "RIGHTCLICK"):
            return self._check_click(step)

        # 6. taste
        proc = getattr(step, "window_process", "")
        if step.step_type in ("TYPE", "KEY") and proc:
            if not fg.is_own and fg.process and fg.process.lower() != proc.lower():
                return GuardAlert("Tastele ar ajunge in alta aplicatie",
                                  f"La inregistrare scriai in: {self._desc(step)}\n"
                                  f"Acum fereastra activa este: {fg}\n"
                                  "Activeaza fereastra corecta, apoi apasa Continua.",
                                  f"keys:{step.step_id}")
        return None

    def _check_click(self, step) -> Optional[GuardAlert]:
        proc = getattr(step, "window_process", "")
        sig = getattr(step, "screen_signature", "")
        if not proc and not sig:
            return None

        # mouse pe tinta (hover ca la inregistrare), apoi comparam
        move_cursor(step.x, step.y)
        time.sleep(0.15)
        self._cursor_after_last = (step.x, step.y)

        here = window_at(step.x, step.y)
        recorded_own = proc.lower() in ("python.exe", "pythonw.exe", "autopilotdc.ui.exe")
        if not here.is_own and not recorded_own and proc and here.process:
            if here.process.lower() != proc.lower():
                return GuardAlert("Click-ul ar ajunge in alta aplicatie",
                                  f"La inregistrare, la ({step.x}, {step.y}) era: {self._desc(step)}\n"
                                  f"Acum acolo este: {here}\n"
                                  "Adu fereastra corecta in fata (sau inchide ce o acopera), apoi apasa Continua.",
                                  f"click:{step.step_id}")
            if self.sensitivity == "strict" and not similar_titles(getattr(step, "window_title", ""), here.title):
                return GuardAlert("Alta fereastra decat la inregistrare",
                                  f"La inregistrare: \"{step.window_title}\"\nAcum: \"{here.title}\"",
                                  f"title:{step.step_id}")

        if sig and not here.is_own:
            diff = compare_signatures(sig, capture_signature(step.x, step.y))
            if diff is not None and diff > self.screen_threshold:
                return GuardAlert("Ecranul arata diferit fata de inregistrare",
                                  f"Zona din jurul click-ului ({step.x}, {step.y}) difera cu {diff:.0f}% "
                                  f"(limita: {self.screen_threshold:.0f}%).\n"
                                  "Posibil: alt ecran deschis, un popup / o notificare peste buton, "
                                  "date diferite, fereastra mutata.\n"
                                  "Verifica ecranul. Daca e in regula, apasa Continua.",
                                  f"screen:{step.step_id}")
        return None

    @staticmethod
    def _desc(step) -> str:
        t, p = getattr(step, "window_title", ""), getattr(step, "window_process", "")
        return f"[{p}]" if not t else f"\"{t}\" ({p})"


# ==============================================================================
# 5. CHENARUL RUN / REC / PAUZA (Tkinter)
# ==============================================================================
class RunFrame:
    """
    Chenar pe toate monitoarele:
      run   -> ROSU + "▶ RUN"     rec -> VERDE + "● REC"     pause -> PORTOCALIU + "❚❚ PAUZA"
    Lasa click-urile sa treaca, nu ia focusul, nu apare in capturi.
    Toate metodele se apeleaza de pe firul Tk (folositi root.after).
    """

    KEY = "#FF00FE"  # culoarea "transparenta" (nefolosita in rest)
    COLORS = {"run": ("#E51C23", "▶ RUN"), "rec": ("#00C853", "● REC"), "pause": ("#FF8F00", "❚❚ PAUZA")}
    THICK = 5

    def __init__(self, root):
        self._root = root
        self._wins: List[Any] = []
        self._after = None
        self.enabled = True
        self.mode = "off"

    def show(self, mode: str):
        import tkinter as tk
        self.mode = mode
        if mode == "off" or not self.enabled:
            self.hide()
            return
        mons = monitors() or [(0, 0, self._root.winfo_screenwidth(), self._root.winfo_screenheight())]
        if len(self._wins) != len(mons):
            self._destroy()
            for (x, y, w, h) in mons:
                win = tk.Toplevel(self._root)
                win.overrideredirect(True)
                win.attributes("-topmost", True)
                win.configure(bg=self.KEY)
                try:
                    win.attributes("-transparentcolor", self.KEY)
                except tk.TclError:
                    pass
                win.geometry(f"{w}x{h}+{x}+{y}")
                cv = tk.Canvas(win, bg=self.KEY, highlightthickness=0, width=w, height=h)
                cv.pack(fill="both", expand=True)
                win.update_idletasks()
                try:
                    make_overlay_window(GetParent(win.winfo_id()) or win.winfo_id())
                except Exception:
                    pass
                self._wins.append((win, cv, w, h))
        color, text = self.COLORS.get(mode, self.COLORS["run"])
        for (_win, cv, w, h) in self._wins:
            cv.delete("all")
            t = self.THICK
            cv.create_rectangle(t // 2, t // 2, w - t // 2 - 1, h - t // 2 - 1, outline=color, width=t)
            bw = 76 if mode != "pause" else 96
            cv.create_rectangle(w - bw, 0, w, 20, fill=color, outline=color)
            cv.create_text(w - bw // 2, 10, text=text, fill="white", font=("Segoe UI", 9, "bold"))
        if self._after is None:
            self._keep_on_top()

    def hide(self):
        self.mode = "off"
        self._destroy()

    def _destroy(self):
        if self._after is not None:
            try:
                self._root.after_cancel(self._after)
            except Exception:
                pass
            self._after = None
        for (win, *_rest) in self._wins:
            try:
                win.destroy()
            except Exception:
                pass
        self._wins = []

    def _keep_on_top(self):
        # alte ferestre "mereu deasupra" pot acoperi chenarul -> il readucem periodic
        for (win, *_rest) in self._wins:
            try:
                if IS_WINDOWS:
                    hwnd = GetParent(win.winfo_id()) or win.winfo_id()
                    SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0, 0x0001 | 0x0002 | SWP_NOACTIVATE)  # NOSIZE|NOMOVE
                else:
                    win.attributes("-topmost", True)
            except Exception:
                pass
        self._after = self._root.after(2000, self._keep_on_top)
