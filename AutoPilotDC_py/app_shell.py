# -*- coding: utf-8 -*-
# ============================================================
# AutoPilot DC — integrarea cu Windows:
#   - iconita aplicatiei (fereastra, bara de activitati, scurtaturi)
#   - pornire automata cu Windows (HKCU\...\Run, fara drepturi de admin)
#   - pictograma in zona de notificari (tray), langa ceas
# ============================================================

from __future__ import annotations

import os
import sys
import threading
from typing import Callable, List, Optional, Tuple

HERE = os.path.dirname(os.path.abspath(__file__))
ICON_ICO = os.path.join(HERE, "assets", "autopilot.ico")
ICON_PNG = os.path.join(HERE, "assets", "autopilot.png")
LAUNCHER = os.path.join(HERE, "AutoPilot_DC.pyw")
APP_ID = "Siemens.AutoPilotDC.4"
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
RUN_VALUE = "AutoPilot DC"


# ── Iconita ───────────────────────────────────────────────────
def set_app_id() -> None:
    """Windows grupeaza fereastra sub iconita AutoPilot (nu sub cea a lui Python) in bara de activitati.
    Trebuie apelat inainte de crearea ferestrei."""
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_ID)
    except Exception:
        pass


def apply_icon(root) -> None:
    """Iconita pentru fereastra principala si pentru toate ferestrele deschise din ea."""
    try:
        if os.path.isfile(ICON_ICO):
            root.iconbitmap(default=ICON_ICO)
    except Exception:
        pass


# ── Pornire cu Windows ────────────────────────────────────────
def _pythonw() -> str:
    exe = sys.executable
    if os.path.basename(exe).lower() == "python.exe":
        candidate = os.path.join(os.path.dirname(exe), "pythonw.exe")
        if os.path.isfile(candidate):
            exe = candidate
    return exe


def autostart_command(minimized: bool) -> str:
    cmd = f'"{_pythonw()}" "{LAUNCHER}"'
    return cmd + " --tray" if minimized else cmd


def is_autostart_enabled() -> bool:
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as k:
            winreg.QueryValueEx(k, RUN_VALUE)
        return True
    except OSError:
        return False


def set_autostart(enabled: bool, minimized: bool = True) -> Tuple[bool, str]:
    """Activeaza / dezactiveaza pornirea cu Windows. Returneaza (succes, mesaj)."""
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as k:
            if enabled:
                winreg.SetValueEx(k, RUN_VALUE, 0, winreg.REG_SZ, autostart_command(minimized))
            else:
                try:
                    winreg.DeleteValue(k, RUN_VALUE)
                except FileNotFoundError:
                    pass
        return True, ("AutoPilot DC porneste automat cu Windows" + (" (in tray)." if minimized else ".")
                      if enabled else "Pornirea automata cu Windows a fost oprita.")
    except OSError as ex:
        return False, f"Nu am putut schimba pornirea automata: {ex}"


# ── Scurtatura fara consola ───────────────────────────────────
def create_shortcut(folder: Optional[str] = None, name: str = "AutoPilot DC") -> Tuple[bool, str]:
    """Scurtatura care porneste DIRECT pythonw.exe (niciodata fereastra CMD, indiferent cum e asociat
    .pyw in Windows), cu iconita aplicatiei. Implicit pe Desktop."""
    import subprocess
    if folder is None:
        folder = os.path.join(os.environ.get("USERPROFILE", os.path.expanduser("~")), "Desktop")
        try:  # Desktop-ul real (poate fi mutat in OneDrive)
            import ctypes
            from ctypes import wintypes
            buf = ctypes.create_unicode_buffer(wintypes.MAX_PATH)
            if ctypes.windll.shell32.SHGetFolderPathW(None, 0x0010, None, 0, buf) == 0:  # CSIDL_DESKTOPDIRECTORY
                folder = buf.value
        except Exception:
            pass
    lnk = os.path.join(folder, name + ".lnk")
    q = lambda s: "'" + s.replace("'", "''") + "'"  # noqa: E731  (ghilimele PowerShell)
    ps = ("$s=(New-Object -ComObject WScript.Shell).CreateShortcut(" + q(lnk) + ");"
          "$s.TargetPath=" + q(_pythonw()) + ";"
          "$s.Arguments=" + q('"' + LAUNCHER + '"') + ";"
          "$s.WorkingDirectory=" + q(HERE) + ";"
          "$s.IconLocation=" + q(ICON_ICO + ",0") + ";"
          "$s.Description='AutoPilot DC';$s.Save()")
    try:
        r = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps],
                           capture_output=True, text=True, timeout=30,
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        if r.returncode == 0 and os.path.isfile(lnk):
            return True, f"Scurtatura \"{name}\" a fost creata: {lnk}"
        return False, "Scurtatura nu a putut fi creata: " + (r.stderr or r.stdout).strip()[:300]
    except Exception as ex:  # noqa: BLE001
        return False, f"Scurtatura nu a putut fi creata: {ex}"


# ── Pictograma din tray ───────────────────────────────────────
def tray_available() -> bool:
    try:
        import pystray  # noqa: F401
        from PIL import Image  # noqa: F401
        return True
    except Exception:
        return False


class Tray:
    """Pictograma langa ceas. Meniul ruleaza pe firul pystray; actiunile se trimit inapoi
    in firul Tk prin `ui_call` (Tkinter nu e sigur intre fire)."""

    def __init__(self, ui_call: Callable[[Callable[[], None]], None],
                 items: List[Tuple[str, Callable[[], None], bool]], on_open: Callable[[], None]):
        self._ui_call, self._items, self._on_open = ui_call, items, on_open
        self._icon = None
        self._lock = threading.Lock()

    @property
    def visible(self) -> bool:
        return self._icon is not None

    def show(self, tooltip: str = "AutoPilot DC") -> bool:
        with self._lock:
            if self._icon is not None:
                return True
            try:
                import pystray
                from PIL import Image
            except ImportError:
                return False
            img = Image.open(ICON_PNG) if os.path.isfile(ICON_PNG) else Image.new("RGB", (64, 64), (0, 153, 153))
            entries = [pystray.MenuItem("Deschide AutoPilot DC", lambda: self._ui_call(self._on_open), default=True)]
            for text, fn, separator_before in self._items:
                if separator_before:
                    entries.append(pystray.Menu.SEPARATOR)
                entries.append(pystray.MenuItem(text, (lambda f=fn: (lambda: self._ui_call(f)))()))
            self._icon = pystray.Icon("AutoPilotDC", img, tooltip, pystray.Menu(*entries))
            self._icon.run_detached()
            return True

    def notify(self, text: str, title: str = "AutoPilot DC") -> None:
        try:
            if self._icon is not None:
                self._icon.notify(text, title)
        except Exception:
            pass

    def set_tooltip(self, text: str) -> None:
        try:
            if self._icon is not None:
                self._icon.title = text
        except Exception:
            pass

    def hide(self) -> None:
        with self._lock:
            icon, self._icon = self._icon, None
        if icon is not None:
            try:
                icon.stop()
            except Exception:
                pass


if __name__ == "__main__":
    # folosit de INSTALEAZA.bat:  py app_shell.py scurtatura
    if len(sys.argv) > 1 and sys.argv[1] == "scurtatura":
        ok, msg = create_shortcut()
        print("  " + msg)
        sys.exit(0 if ok else 1)
