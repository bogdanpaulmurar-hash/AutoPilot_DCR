# -*- coding: utf-8 -*-
# ============================================================
# AutoPilot DC — reluare după o închidere neașteptată
#
# Cât timp rulează o rutină sau o pregătire, în Studio\in-curs\ stă un fișier mic
# rulare_<pid>_<n>.json: ce rulează, de unde și cât s-a terminat. La final se șterge.
# Dacă la pornirea aplicației găsim un astfel de fișier al unui proces care nu mai
# există, înseamnă că aplicația (sau PC-ul) s-a închis în mijlocul rulării și
# oferim reluarea. Rândurile Excel terminate au deja „OK” și sunt sărite, iar
# rândul rămas „IN LUCRU” e întrebat (vezi engine.py).
# ============================================================

from __future__ import annotations

import datetime as _dt
import glob
import json
import os
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

from .storage import RprPaths

KIND_ROUTINE = "routine"
KIND_PREP = "prep"
FOLDER = "in-curs"
_counter = 0          # mai multe rulări în același proces (ex. Studio + programare) → fișiere separate


@dataclass
class RunState:
    kind: str = KIND_ROUTINE
    path: str = ""                 # fișierul rutinei / pregătirii ("" = rutină nesalvată, vezi routine)
    name: str = ""
    started: str = ""
    pid: int = 0
    done_items: int = 0            # pregătire: câte rutine s-au terminat
    variables: Dict[str, str] = field(default_factory=dict)
    routine: Optional[Dict[str, Any]] = None   # copia rutinei, doar dacă are modificări nesalvate
    file: str = ""                 # fișierul de stare (nu se salvează)

    @property
    def started_text(self) -> str:
        try:
            return _dt.datetime.fromisoformat(self.started).strftime("%d.%m.%Y %H:%M")
        except ValueError:
            return self.started


def _folder() -> str:
    return os.path.join(RprPaths.root, FOLDER)


def _write(state: RunState) -> None:
    data = asdict(state)
    data.pop("file", None)
    tmp = state.file + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    os.replace(tmp, state.file)


def begin(kind: str, path: str = "", name: str = "", routine: Optional[Dict[str, Any]] = None,
          variables: Optional[Dict[str, str]] = None) -> Optional[RunState]:
    """Notează pornirea unei rulări. Întoarce None dacă nu se poate scrie (rularea continuă oricum)."""
    global _counter
    try:
        os.makedirs(_folder(), exist_ok=True)
        pid = os.getpid()
        _counter += 1
        state = RunState(kind=kind, path=os.path.abspath(path) if path else "", name=name,
                         started=_dt.datetime.now().isoformat(timespec="seconds"), pid=pid,
                         variables=dict(variables or {}), routine=routine,
                         file=os.path.join(_folder(), f"rulare_{pid}_{_counter}.json"))
        _write(state)
        return state
    except (OSError, TypeError, ValueError):
        return None


def update(state: Optional[RunState], done_items: int) -> None:
    if not state:
        return
    state.done_items = done_items
    try:
        _write(state)
    except OSError:
        pass


def end(state: Optional[RunState]) -> None:
    """Rularea s-a terminat normal (OK, eroare sau STOP): nu mai e nimic de reluat."""
    if state:
        discard(state)


def discard(state: RunState) -> None:
    for p in (state.file, state.file + ".tmp"):
        try:
            os.remove(p)
        except OSError:
            pass


def pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    if pid == os.getpid():
        return True
    if os.name == "nt":
        try:
            import ctypes
            k32 = ctypes.windll.kernel32
            handle = k32.OpenProcess(0x1000, False, pid)   # PROCESS_QUERY_LIMITED_INFORMATION
            if not handle:
                return False
            try:
                code = ctypes.c_ulong()
                ok = k32.GetExitCodeProcess(handle, ctypes.byref(code))
                return bool(ok) and code.value == 259       # STILL_ACTIVE
            finally:
                k32.CloseHandle(handle)
        except Exception:  # noqa: BLE001
            return False
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False


def load(path: str) -> Optional[RunState]:
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return None
    state = RunState(file=path)
    for k, v in data.items():
        if hasattr(state, k) and k != "file":
            setattr(state, k, v)
    return state


def pending() -> List[RunState]:
    """Rulările întrerupte: fișier de stare rămas, iar procesul care l-a scris nu mai există."""
    out = []
    for p in sorted(glob.glob(os.path.join(_folder(), "rulare_*.json"))):
        st = load(p)
        if st is None:
            try:
                os.remove(p)   # fișier stricat: nu avem ce relua din el
            except OSError:
                pass
            continue
        if not pid_alive(int(st.pid or 0)):
            out.append(st)
    out.sort(key=lambda s: s.started, reverse=True)
    return out
