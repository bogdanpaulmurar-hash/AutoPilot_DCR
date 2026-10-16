#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║          AUTOPILOT DC — Tool de Automatizare RPA & Data Cleansing (version.py) ║
# ║          Autor: Bogdan Murar | Realizat cu ajutorul unui asistent AI         ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

# ==============================================================================
# SECTIUNEA 1: IMPORTURI NECESARE
# ==============================================================================
# 1.1 — Librarii standard Python
import os
import sys
import json
import time
import queue
import logging
import threading
import datetime
import re
import csv
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any, Callable, Tuple

# 1.2 — Tkinter (GUI de baza)
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog, colorchooser

# 1.3 — CustomTkinter (GUI modern)
try:
    import customtkinter as ctk
    CTK_AVAILABLE = True
except ImportError:
    CTK_AVAILABLE = False
    print("[EROARE] customtkinter nu este instalat. Rulati: pip install customtkinter")
    sys.exit(1)

# 1.4 — pynput (inregistrare mouse/tastatura)
try:
    import pynput.mouse    as pynput_mouse
    import pynput.keyboard as pynput_keyboard
    from pynput.keyboard import Key as PynputKey
    PYNPUT_AVAILABLE = True
except ImportError:
    import types as _t_pynput
    pynput_mouse    = _t_pynput.ModuleType("pynput.mouse")    # type: ignore[assignment]
    pynput_keyboard = _t_pynput.ModuleType("pynput.keyboard") # type: ignore[assignment]
    PynputKey       = None  # type: ignore[assignment]
    PYNPUT_AVAILABLE = False
    print("[WARN] pynput nu este instalat. Rulati: pip install pynput")

# 1.5 — pyautogui (redare automata)
try:
    import pyautogui  # type: ignore[import]
    pyautogui.FAILSAFE = False
    pyautogui.PAUSE = 0.0
    PYAUTOGUI_AVAILABLE = True
except ImportError:
    import types as _t_pyag
    pyautogui = _t_pyag.ModuleType("pyautogui")  # type: ignore[assignment]
    PYAUTOGUI_AVAILABLE = False
    print("[WARN] pyautogui nu este instalat. Rulati: pip install pyautogui")

# 1.6 — openpyxl (Excel)
try:
    import openpyxl  # type: ignore[import]
    import openpyxl.utils  # type: ignore[import]
    from openpyxl.styles import PatternFill, Font, Alignment  # type: ignore[import]
    OPENPYXL_AVAILABLE = True
except ImportError:
    import types as _t_oxl
    openpyxl = _t_oxl.ModuleType("openpyxl")              # type: ignore[assignment]
    openpyxl.utils = _t_oxl.ModuleType("openpyxl.utils")  # type: ignore[attr-defined]
    PatternFill = None  # type: ignore[assignment,misc]
    Font        = None  # type: ignore[assignment,misc]
    Alignment   = None  # type: ignore[assignment,misc]
    OPENPYXL_AVAILABLE = False
    print("[WARN] openpyxl nu este instalat. Rulati: pip install openpyxl")

# 1.7 — Pillow (screenshot, imagini)
try:
    from PIL import Image, ImageTk, ImageGrab
    PILLOW_AVAILABLE = True
except ImportError:
    PILLOW_AVAILABLE = False

# 1.8b — Siguranta la rulare v4.1 (Nu deranja, chenar RUN/REC, sistem de preventie)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import app_shell  # v4.1: iconita, pornire cu Windows, tray
from autopilot_safety import (DoNotDisturb, RunFrame, SafetyGuard, GuardAlert,
                              CONTINUE, IGNORE_STEP, RETRY, SKIP_STEP, STOP)

# 1.8 — OpenCV (recunoastere vizuala)
try:
    import cv2
    import numpy as np
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False

# ==============================================================================
# SECTIUNEA 2: CONFIGURARE INITIALA — CONSTANTE SI SETARI
# ==============================================================================

# 2.1 — Informatii aplicatie
APP_NAME    = "AutoPilot DC"
from version import __version__ as APP_VERSION  # singura sursa: version.py
APP_AUTHOR  = "Bogdan Murar (Z003FU5C)"

# 2.2 — Directoare de lucru (in acelasi folder cu scriptul)
BASE_DIR      = Path(__file__).parent.resolve()
ROUTINES_DIR  = BASE_DIR / "rutine_salvate"
LOGS_DIR      = BASE_DIR / "loguri"
NOTES_DIR     = BASE_DIR / "notite"
LOCATORS_DIR  = BASE_DIR / "locatori"
CONFIG_FILE   = BASE_DIR / "config.json"

# 2.3 — Creare directoare la pornire
for _d in [ROUTINES_DIR, LOGS_DIR, NOTES_DIR, LOCATORS_DIR]:
    _d.mkdir(parents=True, exist_ok=True)

# 2.4 — Paleta de culori Siemens (tema dark)
COLORS_DARK = {
    "bg_main":        "#1E1E2E",
    "bg_panel":       "#252535",
    "bg_card":        "#2A2A3E",
    "bg_input":       "#32324A",
    "border":         "#444466",
    "primary":        "#009999",
    "primary_hover":  "#007777",
    "primary_light":  "#00BBBB",
    "accent":         "#0288D1",
    "success":        "#00AA44",
    "success_hover":  "#008833",
    "warning":        "#FF8800",
    "danger":         "#CC0000",
    "danger_hover":   "#AA0000",
    "emergency":      "#8B0000",
    "text":           "#FFFFFF",
    "text_dim":       "#AAAACC",
    "text_muted":     "#666688",
    "row_even":       "#252535",
    "row_odd":        "#2E2E45",
    "row_active":     "#1A4A4A",
    "row_error":      "#4A1A1A",
    "row_skip":       "#3A3A3A",
    "separator":      "#009999",
    "btn_neutral_fg": "#FFFFFF",
}

# 2.5 — Paleta de culori Siemens (tema light)
COLORS_LIGHT = {
    "bg_main":        "#F0F4F8",
    "bg_panel":       "#FFFFFF",
    "bg_card":        "#E8EEF5",
    "bg_input":       "#FFFFFF",
    "border":         "#CCDDEE",
    "primary":        "#009999",
    "primary_hover":  "#007777",
    "primary_light":  "#00BBBB",
    "accent":         "#006666",
    "success":        "#00AA44",
    "success_hover":  "#008833",
    "warning":        "#FF8800",
    "danger":         "#CC0000",
    "danger_hover":   "#AA0000",
    "emergency":      "#8B0000",
    "text":           "#1B1B2E",
    "text_dim":       "#444466",
    "text_muted":     "#888899",
    "row_even":       "#F5F8FC",
    "row_odd":        "#EBF0F7",
    "row_active":     "#CCF0F0",
    "row_error":      "#FFDDDD",
    "row_skip":       "#DDDDDD",
    "separator":      "#009999",
    "btn_neutral_fg": "#1B1B2E"
}

# 2.6 — Tema activa (va fi setata la pornire)
C = COLORS_DARK  # referinta globala la culorile active
def _btn_fg(bg_hex: str) -> str:
    """
    Returneaza 'white' sau '#1B1B2E' in functie de luminozitatea
    culorii de fundal — asigura contrast optim pe orice tema.
    """
    try:
        bg_hex = bg_hex.lstrip("#")
        r, g, b = int(bg_hex[0:2], 16), int(bg_hex[2:4], 16), int(bg_hex[4:6], 16)
        # Formula luminozitate relativa (WCAG)
        luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
        return "#1B1B2E" if luminance > 0.55 else "white"
    except Exception:
        return "white"

# 2.7 — Setari implicite redare
DEFAULT_STEP_DELAY     = 0.8
DEFAULT_MOUSE_DELAY    = 0.05
MIN_STEP_DELAY         = 0.05
MAX_STEP_DELAY         = 10.0
MAX_STEPS_WARNING      = 50
DEFAULT_COUNTDOWN      = 3
DEFAULT_REPEAT         = 1

# 2.8 — Tipuri de pasi disponibili
STEP_TYPES = {
    "CLICK":       "Click Mouse",
    "DBLCLICK":    "Dublu Click",
    "RIGHTCLICK":  "Click Dreapta",
    "KEY":         "Apasare Tasta",
    "TYPE":        "Scriere Text",
    "SCROLL":      "Scroll",
    "MOVE":        "Miscare Mouse",
    "DELAY":       "Pauza / Delay",
    "SCREENSHOT":  "Captura Ecran",
    "QUESTION":    "Intrebare User",
}

# 2.9 — Shortcut-uri implicite (taste functionale)
DEFAULT_SHORTCUTS = {
    "start_rec":      "F5",
    "stop_rec":       "F6",
    "resume_play":    "F3",
    "play":           "F7",
    "pause":          "F8",
    "resume":         "F8",
    "stop_play":      "F9",
    "emergency":      "F12",
    "save":           "Ctrl+S",
    "new":            "Ctrl+N",
    "open":           "Ctrl+O",
    "add_delay":      "Ctrl+D",
    "add_step":       "Ctrl+M",
    "delete_step":    "Delete",
    "skip_step":      "Ctrl+K",
    "debug_step":     "Ctrl+B",
    "toggle_debug":   "Ctrl+Shift+B",
    "move_step_up":   "Ctrl+up",
    "move_step_down": "Ctrl+down",
    "edit_step":      "Ctrl+E",
    "show_shortcuts": "Ctrl+H",
}

# ==============================================================================
# SECTIUNEA 3: MODELE DE DATE (STRUCTURI)
# ==============================================================================

@dataclass
class StepModel:
    """
    [MODEL] Reprezinta un pas atomic dintr-o rutina RPA.
    Fiecare pas este serializabil in JSON pentru persistenta.
    """
    # 3.1 — Identificare
    step_id:         int   = 0
    step_type:       str   = "CLICK"      # din STEP_TYPES
    description:     str   = ""
    # 3.2 — Coordonate si mouse
    x:               int   = 0
    y:               int   = 0
    button:          str   = "left"       # left / right / middle
    click_type:      str   = "single"     # single / double / triple / right
    # 3.3 — Tastatura
    key_combo:       str   = ""
    text_input:      str   = ""
    # 3.4 — Scroll
    scroll_dx:       int   = 0
    scroll_dy:       int   = 0
    # 3.5 — Timing
    delay_before:    float = 0.0
    delay_after:     float = 0.0
    # 3.6 — Control flux
    skip:            bool  = False
    monitor_id:      int   = 0
    # 3.7 — Locator vizual
    locator_image:   str   = ""
    # 3.8 — Date extrase/asteptate
    expected_value:  str   = ""
    extracted_value: str   = ""
    # 3.9 — Intrebare user
    question_text:   str   = ""
    question_buttons: str  = "Continua,Opreste,Sari"
    # 3.10 — Stare executie
    has_error:       bool  = False
    error_message:   str   = ""
    comment:         str   = ""
    timestamp:       str   = ""
    # 3.11 — Context la inregistrare (v4.1, sistemul de preventie; identic cu C#)
    window_title:     str  = ""     # fereastra in care s-a dat click / s-a tastat
    window_process:   str  = ""     # ex: excel.exe
    screen_signature: str  = ""     # amprenta zonei 40x40 din jurul click-ului
    guard_ignore:     bool = False  # True = pasul nu mai e verificat

    def to_dict(self) -> dict:
        """Serializeaza pasul in dictionar."""
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "StepModel":
        """Deserializeaza un pas din dictionar."""
        known = {f for f in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in d.items() if k in known})

    def get_display_type(self) -> str:
        """Returneaza tipul formatat pentru afisare."""
        return STEP_TYPES.get(self.step_type, self.step_type)


@dataclass
class LogEntry:
    """[MODEL] O intrare in jurnalul de executie."""
    entry_id:    int   = 0
    timestamp:   str   = ""
    step_id:     int   = 0
    action:      str   = ""
    result:      str   = "OK"
    has_error:   bool  = False
    error_msg:   str   = ""
    comment:     str   = ""
    duration_ms: float = 0.0
    iteration:   int   = 1

# ==============================================================================
# SECTIUNEA 4: MANAGER SETARI
# ==============================================================================

class SettingsManager:
    """
    [MANAGER] Gestioneaza configuratia persistenta a aplicatiei.
    Citeste/scrie din config.json in directorul aplicatiei.
    """

    # 4.1 — Valori implicite complete
    DEFAULTS: Dict[str, Any] = {
        "theme":                  "dark",
        "step_delay":             DEFAULT_STEP_DELAY,
        "mouse_move_delay":       DEFAULT_MOUSE_DELAY,
        "record_mouse_move":      False,
        "mouse_move_threshold":   5,
        "shortcuts":              DEFAULT_SHORTCUTS.copy(),
        "max_steps_warning":      MAX_STEPS_WARNING,
        "auto_save":              True,
        "font_size":              12,
        "playback_speed":         1.0,
        "countdown_before_play":  DEFAULT_COUNTDOWN,
        "repeat_count":           DEFAULT_REPEAT,
        "show_floating_controls": True,
        "show_emergency_btn":     True,
        "active_monitor":         0,
        # v4.1 — Siguranta la rulare
        "dnd_during_run":         True,      # "Nu deranja" cat timp ruleaza / inregistreaza
        "show_run_frame":         True,      # chenar rosu RUN / verde REC
        "guard_enabled":          True,      # sistemul de preventie
        "guard_sensitivity":      "normal",  # relaxed / normal / strict
    }

    def __init__(self):
        """Initializeaza si incarca setarile."""
        self._data: Dict[str, Any] = {}
        self.load()

    def load(self) -> None:
        """Incarca setarile din fisier, cu fallback la valori implicite."""
        self._data = self.DEFAULTS.copy()
        try:
            if CONFIG_FILE.exists():
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                self._data.update(saved)
        except Exception as e:
            logging.warning(f"[Settings] Nu s-au putut incarca setarile: {e}")

    def save(self) -> None:
        """Salveaza setarile curente in fisier."""
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logging.error(f"[Settings] Nu s-au putut salva setarile: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        """Returneaza valoarea unei setari."""
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Seteaza o valoare si salveaza automat."""
        self._data[key] = value
        self.save()

    def get_shortcut(self, action: str) -> str:
        """Returneaza shortcut-ul pentru o actiune."""
        shortcuts = self._data.get("shortcuts", DEFAULT_SHORTCUTS)
        return shortcuts.get(action, DEFAULT_SHORTCUTS.get(action, ""))

    def set_shortcut(self, action: str, combo: str) -> None:
        """Seteaza un shortcut pentru o actiune."""
        shortcuts = self._data.get("shortcuts", DEFAULT_SHORTCUTS.copy())
        shortcuts[action] = combo
        self._data["shortcuts"] = shortcuts
        self.save()

# ==============================================================================
# SECTIUNEA 5: MANAGER LOG
# ==============================================================================

class LogManager:
    """
    [MANAGER] Gestioneaza jurnalul de executie al rutinelor.
    Thread-safe. Suporta export in XLSX, CSV, JSON.
    """

    def __init__(self):
        """Initializeaza managerul de log."""
        # 5.1 — Lista de intrari
        self._entries: List[LogEntry] = []
        # 5.2 — Counter ID
        self._counter: int = 0
        # 5.3 — Lock thread-safe
        self._lock = threading.Lock()
        # 5.4 — Callback UI
        self.on_entry_added: Optional[Callable[[LogEntry], None]] = None

    def add(self, step_id: int, action: str, result: str = "OK",
            has_error: bool = False, error_msg: str = "",
            comment: str = "", duration_ms: float = 0.0,
            iteration: int = 1) -> LogEntry:
        """Adauga o intrare noua in log."""
        with self._lock:
            self._counter += 1
            entry = LogEntry(
                entry_id=self._counter,
                timestamp=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
                step_id=step_id,
                action=action,
                result=result,
                has_error=has_error,
                error_msg=error_msg,
                comment=comment,
                duration_ms=duration_ms,
                iteration=iteration,
            )
            self._entries.append(entry)
        # Notifica UI in afara lock-ului
        if self.on_entry_added:
            self.on_entry_added(entry)
        return entry

    def get_all(self) -> List[LogEntry]:
        """Returneaza toate intrarile."""
        with self._lock:
            return list(self._entries)

    def clear(self) -> None:
        """Sterge toate intrarile."""
        with self._lock:
            self._entries.clear()
            self._counter = 0

    def add_comment(self, entry_id: int, comment: str) -> None:
        """Adauga comentariu la o intrare."""
        with self._lock:
            for e in self._entries:
                if e.entry_id == entry_id:
                    e.comment = comment
                    break

    def export_xlsx(self, path: str) -> bool:
        """Exporta log-ul in format XLSX cu stilizare."""
        if not OPENPYXL_AVAILABLE:
            return False
        try:
            wb = openpyxl.Workbook()
            ws = wb.active
            if ws is None: raise RuntimeError("Nu s-a putut obtine active worksheet")
            ws.title = "Log AutoPilot DC"
            # Header
            hdr_fill = PatternFill("solid", fgColor="009999")  # type: ignore[call-arg]
            hdr_font = Font(bold=True, color="FFFFFF", size=11)  # type: ignore[call-arg]
            err_fill = PatternFill("solid", fgColor="CC0000")  # type: ignore[call-arg]
            alt_fill = PatternFill("solid", fgColor="E8F5F5")  # type: ignore[call-arg]
            headers = ["#","Timestamp","Pas","Actiune","Rezultat",
                       "Eroare","Mesaj Eroare","Comentariu","Durata(ms)","Iteratie"]
            for c, h in enumerate(headers, 1):
                cell = ws.cell(row=1, column=c, value=h)  # type: ignore[union-attr]
                cell.fill = hdr_fill
                cell.font = hdr_font
                cell.alignment = Alignment(horizontal="center")
            with self._lock:
                rows = list(self._entries)
            for ri, e in enumerate(rows, 2):
                vals = [e.entry_id, e.timestamp, e.step_id, e.action,
                        e.result, "DA" if e.has_error else "NU",
                        e.error_msg, e.comment, round(e.duration_ms,2), e.iteration]
                for ci, v in enumerate(vals, 1):
                    cell = ws.cell(row=ri, column=ci, value=v)  # type: ignore[union-attr]
                    if e.has_error:
                        cell.fill = err_fill
                        cell.font = Font(color="FFFFFF")  # type: ignore[call-arg]
                    elif ri % 2 == 0:
                        cell.fill = alt_fill
            widths = [6,22,6,45,10,8,35,30,12,10]
            for ci, w in enumerate(widths, 1):
                ws.column_dimensions[openpyxl.utils.get_column_letter(ci)].width = w
            ws.freeze_panes = "A2"
            wb.save(path)
            return True
        except Exception as ex:
            logging.error(f"[Log] Export XLSX esuat: {ex}")
            return False

    def export_csv(self, path: str) -> bool:
        """Exporta log-ul in format CSV."""
        try:
            with open(path, "w", newline="", encoding="utf-8-sig") as f:
                w = csv.writer(f, delimiter=";")
                w.writerow(["#","Timestamp","Pas","Actiune","Rezultat",
                             "Eroare","Mesaj","Comentariu","Durata(ms)","Iteratie"])
                with self._lock:
                    for e in self._entries:
                        w.writerow([e.entry_id, e.timestamp, e.step_id, e.action,
                                    e.result, e.has_error, e.error_msg,
                                    e.comment, e.duration_ms, e.iteration])
            return True
        except Exception as ex:
            logging.error(f"[Log] Export CSV esuat: {ex}")
            return False

    def export_json(self, path: str) -> bool:
        """Exporta log-ul in format JSON."""
        try:
            with self._lock:
                data = [asdict(e) for e in self._entries]
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as ex:
            logging.error(f"[Log] Export JSON esuat: {ex}")
            return False

# ==============================================================================
# SECTIUNEA 6: MANAGER RUTINE
# ==============================================================================

class RoutineManager:
    """
    [MANAGER] Gestioneaza salvarea, incarcarea si stergerea rutinelor.
    Rutinele sunt stocate ca fisiere JSON in ROUTINES_DIR.
    """

    def __init__(self):
        """Initializeaza managerul de rutine."""
        self._dir = ROUTINES_DIR

    def save(self, name: str, steps: List[StepModel],
             description: str = "") -> bool:
        """Salveaza o rutina in fisier JSON."""
        try:
            safe = self._safe_name(name)
            data = {
                "name": name,
                "description": description,
                "version": APP_VERSION,
                "created_at": datetime.datetime.now().isoformat(),
                "step_count": len(steps),
                "steps": [s.to_dict() for s in steps],
            }
            with open(self._dir / f"{safe}.json", "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            logging.error(f"[Routine] Salvare esuata: {e}")
            return False

    def load(self, name: str) -> Optional[List[StepModel]]:
        """Incarca o rutina dupa nume."""
        try:
            fp = self._find(name)
            if not fp:
                return None
            with open(fp, "r", encoding="utf-8") as f:
                data = json.load(f)
            return [StepModel.from_dict(s) for s in data.get("steps", [])]
        except Exception as e:
            logging.error(f"[Routine] Incarcare esuata: {e}")
            return None

    def list_all(self) -> List[Dict[str, Any]]:
        """Returneaza lista tuturor rutinelor cu metadate."""
        result = []
        for fp in sorted(self._dir.glob("*.json")):
            try:
                with open(fp, "r", encoding="utf-8") as f:
                    d = json.load(f)
                result.append({
                    "name":        d.get("name", fp.stem),
                    "description": d.get("description", ""),
                    "step_count":  d.get("step_count", 0),
                    "created_at":  d.get("created_at", ""),
                    "file":        str(fp),
                })
            except Exception:
                pass
        return result

    def delete(self, name: str) -> bool:
        """Sterge o rutina."""
        fp = self._find(name)
        if fp and fp.exists():
            fp.unlink()
            return True
        return False

    def rename(self, old: str, new: str) -> bool:
        """Redenumeste o rutina."""
        fp = self._find(old)
        if not fp:
            return False
        try:
            with open(fp, "r", encoding="utf-8") as f:
                data = json.load(f)
            data["name"] = new
            new_fp = self._dir / f"{self._safe_name(new)}.json"
            with open(new_fp, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            if new_fp != fp:
                fp.unlink()
            return True
        except Exception as e:
            logging.error(f"[Routine] Redenumire esuata: {e}")
            return False

    def _safe_name(self, name: str) -> str:
        """Sanitizeaza numele pentru filesystem."""
        return re.sub(r'[^\w\s-]', '', name).strip().replace(' ', '_') or "rutina"

    def _find(self, name: str) -> Optional[Path]:
        """Gaseste fisierul JSON al unei rutine."""
        candidate = self._dir / f"{self._safe_name(name)}.json"
        if candidate.exists():
            return candidate
        for fp in self._dir.glob("*.json"):
            try:
                with open(fp, "r", encoding="utf-8") as f:
                    if json.load(f).get("name") == name:
                        return fp
            except Exception:
                pass
        return None

# ==============================================================================
# SECTIUNEA 7: MOTOR DE INREGISTRARE (RECORDER)
# ==============================================================================

class RecorderEngine:
    """
    [ENGINE] Inregistreaza gesturile mouse si tastatura folosind pynput.
    Ruleaza in thread separat, nu blocheaza UI-ul.
    """

    def __init__(self, settings: SettingsManager):
        """Initializeaza motorul de inregistrare."""
        # 7.1 — Referinte
        self._settings = settings
        # 7.2 — Stare
        self._recording:  bool = False
        self._paused:     bool = False
        # 7.3 — Pasi inregistrati
        self._steps: List[StepModel] = []
        self._counter: int = 0
        # 7.4 — Lock
        self._lock = threading.Lock()
        # 7.5 — Listeners pynput
        self._mouse_listener    = None
        self._keyboard_listener = None
        # 7.6 — Stare mouse/tastatura
        self._last_pos:       Tuple[int, int] = (0, 0)
        self._last_time:      float = 0.0
        self._modifiers:      set   = set()
        # 7.7 — Taste de control (nu le inregistram)
        self._ctrl_keys: set = set()
        if PYNPUT_AVAILABLE and PynputKey is not None:
            try:
                _k = PynputKey
                self._ctrl_keys = {
                    k for k in [
                        getattr(_k, "f5",  None),
                        getattr(_k, "f6",  None),
                        getattr(_k, "f7",  None),
                        getattr(_k, "f8",  None),
                        getattr(_k, "f9",  None),
                        getattr(_k, "f12", None),
                    ] if k is not None
                }
            except Exception:
                pass
        # 7.8 — Callbacks UI
        self.on_step_recorded:    Optional[Callable] = None
        self.on_recording_started: Optional[Callable] = None
        self.on_recording_stopped: Optional[Callable] = None

    # ── Proprietati publice ──────────────────────────────────────
    @property
    def is_recording(self) -> bool:
        return self._recording

    @property
    def is_paused(self) -> bool:
        return self._paused

    # ── Control ─────────────────────────────────────────────────
    def start(self) -> bool:
        """Porneste inregistrarea."""
        if not PYNPUT_AVAILABLE or self._recording:
            return False
        with self._lock:
            self._recording = True
            self._paused    = False
            self._last_time = time.time()
        # Porneste listeners
        self._mouse_listener = pynput_mouse.Listener(
            on_move=self._on_move,
            on_click=self._on_click,
            on_scroll=self._on_scroll,
        )
        self._keyboard_listener = pynput_keyboard.Listener(
            on_press=self._on_key_press,
            on_release=self._on_key_release,
        )
        self._mouse_listener.start()
        self._keyboard_listener.start()
        if self.on_recording_started:
            self.on_recording_started()
        return True

    def stop(self) -> List[StepModel]:
        """Opreste inregistrarea si returneaza pasii."""
        if not self._recording:
            return list(self._steps)
        with self._lock:
            self._recording = False
        for lst in [self._mouse_listener, self._keyboard_listener]:
            if lst:
                try:
                    lst.stop()
                except Exception:
                    pass
        self._mouse_listener    = None
        self._keyboard_listener = None
        if self.on_recording_stopped:
            self.on_recording_stopped()
        return list(self._steps)

    def pause(self) -> None:
        """Pune inregistrarea pe pauza."""
        with self._lock:
            self._paused = True

    def resume(self) -> None:
        """Reia inregistrarea."""
        with self._lock:
            self._paused    = False
            self._last_time = time.time()

    def clear(self) -> None:
        """Sterge toti pasii inregistrati."""
        with self._lock:
            self._steps.clear()
            self._counter = 0

    def get_steps(self) -> List[StepModel]:
        """Returneaza pasii inregistrati."""
        with self._lock:
            return list(self._steps)

    def set_steps(self, steps: List[StepModel]) -> None:
        """Seteaza pasii (la incarcare rutina)."""
        with self._lock:
            self._steps   = list(steps)
            self._counter = len(steps)

    def add_step_manual(self, step: StepModel) -> None:
        """Adauga un pas manual (din Step Builder)."""
        with self._lock:
            self._counter += 1
            step.step_id   = self._counter
            if not step.timestamp:
                step.timestamp = datetime.datetime.now().strftime("%H:%M:%S")
            self._steps.append(step)
        if self.on_step_recorded:
            self.on_step_recorded(step)

    # ── Callbacks interne ────────────────────────────────────────
    def _add(self, step: StepModel) -> None:
        """Adauga un pas inregistrat automat."""
        with self._lock:
            if not self._recording or self._paused:
                return
            self._counter += 1
            step.step_id   = self._counter
            step.timestamp = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
            self._steps.append(step)
        if self.on_step_recorded:
            self.on_step_recorded(step)

    def _elapsed(self) -> float:
        """Calculeaza timpul scurs de la ultimul eveniment."""
        now = time.time()
        dt  = min(round(now - self._last_time, 3), 10.0)
        self._last_time = now
        return dt

    def _on_move(self, x: int, y: int) -> None:
        """Callback miscare mouse."""
        if not self._recording or self._paused:
            return
        if not self._settings.get("record_mouse_move", False):
            return
        thr = self._settings.get("mouse_move_threshold", 5)
        lx, ly = self._last_pos
        if ((x - lx)**2 + (y - ly)**2)**0.5 < thr:
            return
        self._last_pos = (x, y)
        self._add(StepModel(
            step_type="MOVE", x=x, y=y,
            delay_before=self._elapsed(),
            description=f"Miscare mouse la ({x}, {y})",
        ))

    def _on_click(self, x: int, y: int, button, pressed: bool) -> None:
        """Callback click mouse."""
        if not self._recording or self._paused or not pressed:
            return
        btn = getattr(button, "name", "left")
        stype = "RIGHTCLICK" if btn == "right" else "CLICK"
        self._last_pos = (x, y)
        step = StepModel(
            step_type=stype, x=x, y=y, button=btn,
            click_type="right" if btn == "right" else "single",
            delay_before=self._elapsed(),
            description=f"Click {btn} la ({x}, {y})",
        )
        SafetyGuard.record_context(step)  # v4.1: fereastra + amprenta, inainte ca aplicatia sa reactioneze
        self._add(step)

    def _on_scroll(self, x: int, y: int, dx: int, dy: int) -> None:
        """Callback scroll mouse."""
        if not self._recording or self._paused:
            return
        step = StepModel(
            step_type="SCROLL", x=x, y=y,
            scroll_dx=dx, scroll_dy=dy,
            delay_before=self._elapsed(),
            description=f"Scroll ({dx},{dy}) la ({x},{y})",
        )
        SafetyGuard.record_context(step)
        self._add(step)

    def _on_key_press(self, key) -> None:
        """Callback apasare tasta."""
        if not self._recording or self._paused:
            return
        if key in self._ctrl_keys:
            return
        # Detecteaza modificatori
        try:
            nm = getattr(key, "name", "")
            if nm in ("ctrl_l","ctrl_r","shift","shift_r","alt_l","alt_r","cmd"):
                self._modifiers.add(nm)
                return
        except Exception:
            pass
        # Construieste reprezentarea tastei [v3.9 fix]
        try:
            raw_char = getattr(key, "char", None)
            raw_name = getattr(key, "name", None)
            if raw_char and raw_char.isprintable() and len(raw_char) == 1:
                ks = raw_char
            elif raw_name:
                ks = raw_name
            else:
                vk = getattr(key, "vk", None)
                ks = f"vk{vk}" if vk is not None else str(key).replace("Key.", "").replace("'", "")
        except Exception:
            ks = str(key).replace("Key.", "").replace("'", "")
        mods = []
        if any(m in self._modifiers for m in ("ctrl_l","ctrl_r")):
            mods.append("Ctrl")
        if any(m in self._modifiers for m in ("shift","shift_r")):
            mods.append("Shift")
        if any(m in self._modifiers for m in ("alt_l","alt_r")):
            mods.append("Alt")
        combo = "+".join(mods + [ks]) if mods else ks
        step = StepModel(
            step_type="KEY", key_combo=combo,
            delay_before=self._elapsed(),
            description=f"Tasta: {combo}",
        )
        SafetyGuard.record_context(step)  # v4.1: in ce fereastra se tasteaza
        self._add(step)

    def _on_key_release(self, key) -> None:
        """Callback eliberare tasta — curata modificatorii."""
        try:
            nm = getattr(key, "name", "")
            self._modifiers.discard(nm)
        except Exception:
            pass

# ==============================================================================
# SECTIUNEA 8: MOTOR DE REDARE (PLAYER)
# ==============================================================================

class PlayerEngine:
    """
    [ENGINE] Ruleaza rutinele inregistrate.
    Ruleaza in thread separat. Suporta: countdown, repetari,
    delay configurabil, pause/resume, emergency stop.
    """

    def __init__(self, settings: SettingsManager, log: LogManager):
        """Initializeaza motorul de redare."""
        # 8.1 — Referinte
        self._settings = settings
        self._log      = log
        # 8.2 — Stare
        self._running:  bool = False
        self._paused:   bool = False
        self._stop_req: bool = False
        # 8.3 — Thread si sincronizare
        self._thread:      Optional[threading.Thread] = None
        self._pause_event: threading.Event = threading.Event()
        self._pause_event.set()
        # 8.4 — Callbacks UI
        self.on_step_start:    Optional[Callable] = None  # (idx, step)
        self.on_step_done:     Optional[Callable] = None  # (idx, step, ok)
        self.on_started:       Optional[Callable] = None
        self.on_stopped:       Optional[Callable] = None
        self.on_paused:        Optional[Callable] = None
        self.on_resumed:       Optional[Callable] = None
        self.on_countdown:     Optional[Callable] = None  # (sec)
        self.on_iter_update:   Optional[Callable] = None  # (cur, total)
        self.on_error:         Optional[Callable] = None  # (step, msg)
        self.on_question:      Optional[Callable] = None  # (step) -> str
        # 8.5 — v4.1: siguranta la rulare
        self.guard: Optional[SafetyGuard] = None
        self.suppress_notifications: bool = True
        # (step, GuardAlert, poate_reincerca) -> CONTINUE / IGNORE_STEP / RETRY / SKIP_STEP / STOP
        self.on_guard_question: Optional[Callable] = None

    # ── Proprietati ──────────────────────────────────────────────
    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def is_paused(self) -> bool:
        return self._paused

    # ── Control ─────────────────────────────────────────────────
    def play(self, steps: List[StepModel], repeat: int = 1) -> bool:
        """Porneste redarea rutinei."""
        if self._running or not steps or not PYAUTOGUI_AVAILABLE:
            return False
        self._running  = True
        self._paused   = False
        self._stop_req = False
        self._pause_event.set()
        self._thread = threading.Thread(
            target=self._loop, args=(steps, repeat),
            daemon=True, name="PlayerThread"
        )
        self._thread.start()
        return True

    def pause(self) -> None:
        """Pauza redare."""
        if self._running and not self._paused:
            self._paused = True
            self._pause_event.clear()
            if self.on_paused:
                self.on_paused()

    def resume(self) -> None:
        """Reia redarea."""
        if self._running and self._paused:
            self._paused = False
            self._pause_event.set()
            if self.on_resumed:
                self.on_resumed()

    def stop(self) -> None:
        """Opreste redarea normal."""
        self._stop_req = True
        self._pause_event.set()

    def emergency_stop(self) -> None:
        """Oprire de urgenta imediata."""
        self._stop_req = True
        self._running  = False
        self._pause_event.set()
        if self.on_stopped:
            self.on_stopped()

    # ── Bucla principala ─────────────────────────────────────────
    def _loop(self, steps: List[StepModel], repeat: int) -> None:
        """Bucla de redare in thread separat (+ "Nu deranja" pe durata ei)."""
        dnd = bool(self.suppress_notifications)
        if dnd:
            # cererea se inregistreaza imediat; aplicarea (cateva secunde) merge in paralel cu countdown-ul
            DoNotDisturb.enable(wait=False)
        try:
            self._loop_inner(steps, repeat, dnd)
        finally:
            if dnd:
                DoNotDisturb.restore()   # nu blocheaza; lucratorul reporneste notificarile

    def _ask_guard(self, step: StepModel, alert: GuardAlert, can_retry: bool) -> str:
        """v4.1: pauza + intrebare. Rutina asteapta raspunsul utilizatorului."""
        if not self.on_guard_question:
            return CONTINUE
        self._paused = True
        self._pause_event.clear()
        if self.on_paused:
            self.on_paused()
        try:
            decision = self.on_guard_question(step, alert, can_retry)
        finally:
            self._paused = False
            self._pause_event.set()
            if self.on_resumed:
                self.on_resumed()
        self._log.add(step.step_id, f"[PREVENTIE] {alert.title} -> {decision}",
                      "ATENTIE", has_error=True, error_msg=alert.details[:300])
        if self.guard:
            self.guard.acknowledge()
        return decision

    def _loop_inner(self, steps: List[StepModel], repeat: int, dnd) -> None:
        # 1. Countdown
        cd = int(self._settings.get("countdown_before_play", DEFAULT_COUNTDOWN))
        for i in range(cd, 0, -1):
            if self._stop_req:
                self._running = False
                if self.on_stopped:
                    self.on_stopped()
                return
            if self.on_countdown:
                self.on_countdown(i)
            time.sleep(1.0)

        if dnd:
            DoNotDisturb.wait_settled(timeout=15)

        # 2. Notifica start
        if self.on_started:
            self.on_started()
        if self.guard:
            self.guard.begin_run()

        # 3. Calculeaza delay efectiv
        base_delay  = float(self._settings.get("step_delay", DEFAULT_STEP_DELAY))
        speed       = float(self._settings.get("playback_speed", 1.0))
        eff_delay   = base_delay / max(speed, 0.01)

        # 4. Bucla repetari
        for it in range(1, repeat + 1):
            if self._stop_req:
                break
            if self.on_iter_update:
                self.on_iter_update(it, repeat)

            # 5. Bucla pasi
            for idx, step in enumerate(steps):
                if self._stop_req:
                    break
                # Asteapta daca e pauza
                self._pause_event.wait()
                if self._stop_req:
                    break
                # Sari pasul
                if step.skip:
                    self._log.add(step.step_id,
                                  f"[SARIT] {step.description}",
                                  "SARIT", iteration=it)
                    continue
                # Notifica UI
                if self.on_step_start:
                    self.on_step_start(idx, step)
                # Delay inainte
                if step.delay_before > 0:
                    time.sleep(step.delay_before)
                # v4.1: sistemul de preventie — ecranul arata ca la inregistrare?
                if self.guard is not None and self.guard.enabled:
                    upcoming = [s for s in steps[idx:] if not s.skip]
                    alert = self.guard.check_before_step(step, upcoming)
                    if alert:
                        d = self._ask_guard(step, alert, can_retry=False)
                        if d == STOP:
                            self._stop_req = True
                            break
                        if d == SKIP_STEP:
                            continue
                        if d == IGNORE_STEP:
                            step.guard_ignore = True
                if self._stop_req:
                    break
                # Executa (la eroare: pauza + intrebare, nu mai mergem mai departe in tacere)
                while True:
                    t0 = time.time()
                    ok, err = self._exec(step)
                    dur = (time.time() - t0) * 1000
                    if ok or not self.on_guard_question or self._stop_req:
                        break
                    if self.on_error:
                        self.on_error(step, err)
                    d = self._ask_guard(step, GuardAlert(
                        f"Pasul {step.step_id} ({step.get_display_type()}) a esuat", err,
                        f"error:{step.step_id}", can_ignore_step=False), can_retry=True)
                    if d == RETRY:
                        continue
                    if d == STOP:
                        self._stop_req = True
                    break
                if self.guard:
                    self.guard.after_step()
                # Logheaza
                self._log.add(
                    step.step_id,
                    step.description or f"Pas {step.step_id}: {step.step_type}",
                    "OK" if ok else "EROARE",
                    has_error=not ok, error_msg=err,
                    duration_ms=dur, iteration=it,
                )
                # Notifica UI
                if self.on_step_done:
                    self.on_step_done(idx, step, ok)
                if not ok and self.on_error and not self.on_guard_question:
                    self.on_error(step, err)
                # Delay global
                time.sleep(eff_delay)
                # Delay dupa pas
                if step.delay_after > 0:
                    time.sleep(step.delay_after)

        # 6. Finalizeaza
        self._running = False
        self._paused  = False
        if self.on_stopped:
            self.on_stopped()

    def _exec(self, step: StepModel) -> Tuple[bool, str]:
        """Executa un pas individual. Returneaza (succes, mesaj_eroare)."""
        try:
            t = step.step_type
            if t in ("CLICK", "DBLCLICK", "RIGHTCLICK"):
                btn = step.button if step.button in ("left","right","middle") else "left"
                if t == "DBLCLICK" or step.click_type == "double":
                    pyautogui.doubleClick(step.x, step.y, button=btn)
                elif t == "RIGHTCLICK" or step.click_type == "right":
                    pyautogui.rightClick(step.x, step.y)
                else:
                    pyautogui.click(step.x, step.y, button=btn)
            elif t == "MOVE":
                pyautogui.moveTo(step.x, step.y, duration=0.15)
            elif t == "SCROLL":
                pyautogui.scroll(step.scroll_dy, x=step.x, y=step.y)
            elif t == "KEY":
                combo = step.key_combo
                _KEY_MAP = {
                    "Ctrl":"ctrl","Shift":"shift","Alt":"alt",
                    "ctrl":"ctrl","shift":"shift","alt":"alt",
                    "enter":"enter","return":"enter","tab":"tab",
                    "space":"space","backspace":"backspace","delete":"delete",
                    "esc":"escape","escape":"escape",
                    "up":"up","down":"down","left":"left","right":"right",
                    "home":"home","end":"end","pageup":"pageup","pagedown":"pagedown",
                    "f1":"f1","f2":"f2","f3":"f3","f4":"f4","f5":"f5",
                    "f6":"f6","f7":"f7","f8":"f8","f9":"f9","f10":"f10",
                    "f11":"f11","f12":"f12",
                    "insert":"insert","capslock":"capslock","numlock":"numlock",
                    "win":"win","winleft":"winleft","winright":"winright",
                }
                def _pynput_combo(mods_list, final_key):
                    try:
                        import pynput.keyboard as _pk
                        _kbc = _pk.Controller()
                        _MOD = {"ctrl":_pk.Key.ctrl,"shift":_pk.Key.shift,
                                "alt":_pk.Key.alt,"win":_pk.Key.cmd}
                        mod_objs = [_MOD[m] for m in mods_list if m in _MOD]
                        for mo in mod_objs: _kbc.press(mo)
                        if len(str(final_key)) == 1:
                            _kbc.press(final_key); _kbc.release(final_key)
                        else:
                            try:
                                _kbc.press(getattr(_pk.Key, final_key))
                                _kbc.release(getattr(_pk.Key, final_key))
                            except AttributeError:
                                _kbc.press(final_key); _kbc.release(final_key)
                        for mo in reversed(mod_objs): _kbc.release(mo)
                        return True
                    except Exception:
                        return False
                if "+" in combo:
                    parts = combo.split("+")
                    mods  = [_KEY_MAP.get(p.lower(), p.lower()) for p in parts[:-1]]
                    key   = parts[-1]
                    is_sp = len(key) == 1 and ord(key) > 127
                    if is_sp:
                        _pynput_combo(mods, key)
                    else:
                        mapped = mods + [_KEY_MAP.get(key.lower(), key.lower())]
                        try:
                            pyautogui.hotkey(*mapped)
                        except Exception:
                            _pynput_combo(mods, _KEY_MAP.get(key.lower(), key.lower()))
                else:
                    is_sp = len(combo) == 1 and ord(combo) > 127
                    if is_sp:
                        _pynput_combo([], combo)
                    else:
                        mapped = _KEY_MAP.get(combo.lower(), combo.lower())
                        try:
                            pyautogui.press(mapped)
                        except Exception:
                            _pynput_combo([], mapped)
            elif t == "TYPE":
                txt = step.text_input or ""
                if any(ord(c) > 127 for c in txt):
                    try:
                        import pynput.keyboard as _pk
                        _kbc = _pk.Controller()
                        for ch in txt:
                            _kbc.press(ch); _kbc.release(ch)
                            time.sleep(0.04)
                    except Exception:
                        pyautogui.typewrite(txt, interval=0.04)
                else:
                    pyautogui.typewrite(txt, interval=0.04)
            elif t == "DELAY":
                time.sleep(max(step.delay_before, 0.1))
            elif t == "QUESTION":
                # Intrebare user — raspuns prin callback
                if self.on_question:
                    ans = self.on_question(step)
                    if ans == "Opreste":
                        self._stop_req = True
                        return True, ""
            return True, ""
        except Exception as ex:
            return False, str(ex)

# ==============================================================================
# SECTIUNEA 9: MOTOR EXCEL
# ==============================================================================

class ExcelEngine:
    """
    [ENGINE] Operatii Excel: citire date, scriere rezultate, export log.
    """

    def load_data(self, path: str, sheet: str, rng: str) -> List[Any]:
        """Incarca date dintr-un interval Excel."""
        if not OPENPYXL_AVAILABLE:
            return []
        try:
            wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
            ws = wb[sheet] if sheet in wb.sheetnames else wb.active
            if ws is None: raise RuntimeError("Nu s-a putut obtine worksheet")
            vals = [c.value for row in ws[rng] for c in row if c.value is not None]
            wb.close()
            return vals
        except Exception as e:
            logging.error(f"[Excel] Incarcare esuata: {e}")
            return []

    def get_sheets(self, path: str) -> List[str]:
        """Returneaza lista de sheet-uri."""
        if not OPENPYXL_AVAILABLE:
            return []
        try:
            wb = openpyxl.load_workbook(path, read_only=True)
            names = wb.sheetnames
            wb.close()
            return names
        except Exception:
            return []

    def write_results(self, path: str, results: List[Any],
                      start_cell: str, sheet: str = "") -> bool:
        """Scrie rezultate intr-un fisier Excel."""
        if not OPENPYXL_AVAILABLE:
            return False
        try:
            wb = openpyxl.load_workbook(path) if Path(path).exists() else openpyxl.Workbook()
            ws = wb[sheet] if sheet and sheet in wb.sheetnames else wb.active
            _m1 = re.match(r"([A-Za-z]+)", start_cell)
            _m2 = re.match(r"[A-Za-z]+([0-9]+)", start_cell)
            col_str = _m1.group(1).upper() if _m1 else "A"
            row_s   = int(_m2.group(1)) if _m2 else 1
            col_i   = openpyxl.utils.column_index_from_string(col_str)
            for i, v in enumerate(results):
                ws.cell(row=row_s + i, column=col_i, value=v)
            wb.save(path)
            return True
        except Exception as e:
            logging.error(f"[Excel] Scriere esuata: {e}")
            return False

# ==============================================================================
# SECTIUNEA 10: MANAGER HOTKEYS GLOBALE
# ==============================================================================

class HotkeyManager:
    """
    [MANAGER] Gestioneaza hotkey-urile globale cu pynput.GlobalHotKeys.
    Permite inregistrarea, stergerea si repornirea hotkeys.
    """

    def __init__(self):
        """Initializeaza managerul de hotkeys."""
        # 10.1 — Dictionar {combo_pynput: callback}
        self._map:      Dict[str, Callable] = {}
        self._listener = None
        self._active:   bool = False

    def register(self, combo: str, cb: Callable) -> None:
        """Inregistreaza un hotkey."""
        pnc = self._to_pynput(combo)
        if pnc:
            self._map[pnc] = cb

    def unregister(self, combo: str) -> None:
        """Dezinregistreaza un hotkey."""
        pnc = self._to_pynput(combo)
        if pnc is not None:
            self._map.pop(pnc, None)

    def start(self) -> bool:
        """Porneste listener-ul de hotkeys."""
        if not PYNPUT_AVAILABLE or not self._map:
            return False
        try:
            self._listener = pynput_keyboard.GlobalHotKeys(self._map)  # type: ignore[attr-defined]
            self._listener.start()
            self._active = True
            return True
        except Exception as e:
            logging.error(f"[Hotkeys] Pornire esuata: {e}")
            return False

    def stop(self) -> None:
        """Opreste listener-ul."""
        if self._listener:
            try:
                self._listener.stop()
            except Exception:
                pass
            self._listener = None
        self._active = False

    def restart(self) -> None:
        """Reporneste listener-ul."""
        self.stop()
        self.start()

    def _to_pynput(self, combo: str) -> Optional[str]:
        """[v3.9] Converteste combo in format pynput GlobalHotKeys."""
        try:
            parts  = [pt.strip() for pt in combo.split("+")]
            result = []
            for pt in parts:
                pl = pt.lower()
                if pl == "ctrl":
                    result.append("<ctrl>")
                elif pl == "shift":
                    result.append("<shift>")
                elif pl == "alt":
                    result.append("<alt>")
                elif pl in ("win", "super", "cmd"):
                    result.append("<cmd>")
                elif pl.startswith("f") and pl[1:].isdigit():
                    result.append(f"<{pl}>")
                elif pl in ("delete","del"):
                    result.append("<delete>")
                elif pl in ("insert","ins"):
                    result.append("<insert>")
                elif pl in ("home","end","pageup","pagedown","pgup","pgdn",
                            "up","down","left","right",
                            "tab","enter","return","esc","escape",
                            "space","backspace","caps_lock","num_lock"):
                    result.append(f"<{pl}>")
                elif len(pl) == 1:
                    result.append(pl)
                else:
                    result.append(pl)
            return "+".join(result)
        except Exception:
            return None

# ==============================================================================
# SECTIUNEA 11: WIDGET-URI HELPER (SCROLL, TREEVIEW, ETC.)
# ==============================================================================

def bind_scroll(widget, target=None):
    """
    Leaga scroll-ul mouse-ului pe un widget, toti copiii sai
    si orice copii adaugati in viitor (prin trace pe <Enter>).
    """
    def _scroll(event, tgt=target or widget):
        delta = 0
        if hasattr(event, "delta") and event.delta:
            delta = -1 * (event.delta // 120)
        elif event.num == 4:
            delta = -1
        elif event.num == 5:
            delta = 1
        try:
            tgt.yview_scroll(delta, "units")
        except Exception:
            pass

    def _bind_recursive(w):
        w.bind("<MouseWheel>", _scroll, add="+")
        w.bind("<Button-4>",   _scroll, add="+")
        w.bind("<Button-5>",   _scroll, add="+")
        for child in w.winfo_children():
            _bind_recursive(child)

    # Leaga imediat pe ce exista
    _bind_recursive(widget)

    # Leaga si pe orice widget nou adaugat in viitor
    tgt = target or widget
    def _on_map(event):
        _bind_recursive(event.widget)
    widget.bind("<Map>", _on_map, add="+")


def make_treeview(parent, columns: List[Tuple], style_name: str,
                  row_height: int = 26, font_size: int = 11,
                  multi_select: bool = False) -> ttk.Treeview:
    """
    [HELPER] Creeaza un Treeview stilizat cu tema Siemens.
    Args:
        parent: Widget parinte
        columns: Lista de (id, heading, width, anchor, stretch)
        style_name: Numele stilului ttk
        row_height: Inaltimea unui rand
        font_size: Marimea fontului
        multi_select: Permite selectie multipla
    Returns: Treeview configurat
    """
    style = ttk.Style()
    style.theme_use("clam")
    style.configure(f"{style_name}.Treeview",
                    background=C["bg_card"],
                    foreground=C["text"],
                    fieldbackground=C["bg_card"],
                    rowheight=row_height,
                    font=("Segoe UI", font_size))
    style.configure(f"{style_name}.Treeview.Heading",
                    background=C["primary"],
                    foreground="white",
                    font=("Segoe UI", font_size, "bold"),
                    relief="flat")
    style.map(f"{style_name}.Treeview",
                background=[("selected", "#2563EB")],   # <-- culoare fixa
                foreground=[("selected", "#FFFFFF")])    # text alb garantat

    col_ids = [c[0] for c in columns]
    tv = ttk.Treeview(
        parent,
        style=f"{style_name}.Treeview",
        columns=col_ids,
        show="headings",
        selectmode="extended" if multi_select else "browse",
    )
    for col_id, heading, width, anchor, stretch in columns:
        tv.heading(col_id, text=heading, anchor=anchor)
        tv.column(col_id, width=width, anchor=anchor, stretch=stretch)

    # Tag-uri culori standard
    tv.tag_configure("even",    background=C["row_even"],   foreground=C["text"])
    tv.tag_configure("odd",     background=C["row_odd"],    foreground=C["text"])
    tv.tag_configure("active",  background=C["row_active"], foreground="white")
    tv.tag_configure("error",   background=C["row_error"],  foreground="#FF8888")
    tv.tag_configure("skipped", background=C["row_skip"],   foreground="#888888")
    tv.tag_configure("playing", background=C["primary"],    foreground="white")

    # Scroll mouse nativ
    bind_scroll(tv)
    return tv


def ctk_btn(parent, text: str, cmd: Callable,
            color: Optional[str] = None, hover: Optional[str] = None,
            width: int = 120, height: int = 34,
            font_size: int = 12, bold: bool = False,
            **kwargs) -> ctk.CTkButton:
    """[HELPER] Creeaza un buton CTk cu stil uniform."""
    return ctk.CTkButton(
        parent, text=text, command=cmd,
        fg_color=color or C["primary"],
        hover_color=hover or C["primary_hover"],
        width=width, height=height,
        font=ctk.CTkFont(size=font_size, weight="bold" if bold else "normal"),
        corner_radius=8,
        **kwargs,
    )


def ctk_label(parent, text: str, size: int = 12,
              bold: bool = False, color: Optional[str] = None, **kwargs) -> ctk.CTkLabel:
    """[HELPER] Creeaza un label CTk cu stil uniform."""
    return ctk.CTkLabel(
        parent, text=text,
        font=ctk.CTkFont(size=size, weight="bold" if bold else "normal"),
        text_color=color or C["text"],
        **kwargs,
    )

# ==============================================================================
# SECTIUNEA 12: DIALOG STEP BUILDER (CREARE PAS MANUAL)
# ==============================================================================

class StepBuilderDialog(tk.Toplevel):
    """
    [DIALOG] Dialog pentru crearea sau editarea manuala a unui pas.
    Permite configurarea tuturor proprietatilor unui StepModel.
    """

    def __init__(self, parent, step: Optional[StepModel] = None,
                 title: str = "Adauga Pas"):
        """
        Initializeaza dialogul.
        Args:
            parent: Fereastra parinte
            step: Pasul de editat (None pentru pas nou)
            title: Titlul dialogului
        """
        super().__init__(parent)
        self.title(title)
        self.geometry("560x620")
        self.resizable(False, False)
        self.grab_set()
        self.transient(parent)
        self.configure(bg=C["bg_main"])

        # 12.1 — Rezultatul dialogului
        self.result: Optional[StepModel] = None
        # 12.2 — Pasul de editat (sau nou)
        self._step = step or StepModel()

        # 12.3 — Variabile UI
        self._var_type    = tk.StringVar(value=self._step.step_type)
        self._var_desc    = tk.StringVar(value=self._step.description)
        self._var_x       = tk.IntVar(value=self._step.x)
        self._var_y       = tk.IntVar(value=self._step.y)
        self._var_btn     = tk.StringVar(value=self._step.button)
        self._var_click   = tk.StringVar(value=self._step.click_type)
        self._var_key     = tk.StringVar(value=self._step.key_combo)
        self._var_text    = tk.StringVar(value=self._step.text_input)
        self._var_scroll_dy = tk.IntVar(value=self._step.scroll_dy)
        self._var_delay_b = tk.DoubleVar(value=self._step.delay_before)
        self._var_delay_a = tk.DoubleVar(value=self._step.delay_after)
        self._var_skip    = tk.BooleanVar(value=self._step.skip)
        self._var_comment = tk.StringVar(value=self._step.comment)
        self._var_question= tk.StringVar(value=self._step.question_text)

        self._build()
        self._on_type_change()
        self.wait_window()

    def _build(self):
        """Construieste interfata dialogului."""
        # ── Titlu ──
        tk.Label(self, text="⚙  Configurare Pas",
                 bg=C["bg_main"], fg=C["primary"],
                 font=("Segoe UI", 14, "bold")).pack(pady=(12, 4))

        # ── Frame principal scrollabil ──
        canvas = tk.Canvas(self, bg=C["bg_main"], highlightthickness=0)
        vsb    = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        canvas.pack(fill="both", expand=True, padx=8)
        bind_scroll(canvas, canvas)

        self._inner = tk.Frame(canvas, bg=C["bg_main"])
        canvas_win  = canvas.create_window((0, 0), window=self._inner, anchor="nw")

        def _resize(e):
            canvas.configure(scrollregion=canvas.bbox("all"))
        self._inner.bind("<Configure>", _resize)
        canvas.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

        f = self._inner

        def row(label, widget_fn):
            r = tk.Frame(f, bg=C["bg_main"])
            r.pack(fill="x", padx=16, pady=3)
            tk.Label(r, text=label, bg=C["bg_main"], fg=C["text_dim"],
                     font=("Segoe UI", 11), width=22, anchor="w").pack(side="left")
            widget_fn(r)

        # Tip pas
        row("Tip Pas:", lambda p: ttk.Combobox(
            p, textvariable=self._var_type,
            values=list(STEP_TYPES.keys()),
            state="readonly", width=18,
            font=("Segoe UI", 11)
        ).pack(side="left"))
        self._var_type.trace_add("write", lambda *_: self._on_type_change())

        # Descriere
        row("Descriere:", lambda p: tk.Entry(
            p, textvariable=self._var_desc, width=32,
            bg=C["bg_input"], fg=C["text"],
            font=("Segoe UI", 11), relief="flat",
            insertbackground=C["text"]
        ).pack(side="left"))

        # Separator
        tk.Frame(f, bg=C["separator"], height=1).pack(fill="x", padx=16, pady=6)

        # ── Sectiune Mouse ──
        self._lbl_mouse = tk.Label(f, text="🖱  Optiuni Mouse",
                                   bg=C["bg_main"], fg=C["primary"],
                                   font=("Segoe UI", 11, "bold"))
        self._lbl_mouse.pack(anchor="w", padx=16, pady=(2, 0))

        self._frame_mouse = tk.Frame(f, bg=C["bg_main"])
        self._frame_mouse.pack(fill="x")

        def mouse_row(label, widget_fn):
            r = tk.Frame(self._frame_mouse, bg=C["bg_main"])
            r.pack(fill="x", padx=16, pady=2)
            tk.Label(r, text=label, bg=C["bg_main"], fg=C["text_dim"],
                     font=("Segoe UI", 11), width=22, anchor="w").pack(side="left")
            widget_fn(r)

        mouse_row("Coordonata X:", lambda p: tk.Entry(
            p, textvariable=self._var_x, width=10,
            bg=C["bg_input"], fg=C["text"], font=("Segoe UI", 11),
            relief="flat", insertbackground=C["text"]
        ).pack(side="left"))

        mouse_row("Coordonata Y:", lambda p: tk.Entry(
            p, textvariable=self._var_y, width=10,
            bg=C["bg_input"], fg=C["text"], font=("Segoe UI", 11),
            relief="flat", insertbackground=C["text"]
        ).pack(side="left"))

        mouse_row("Buton Mouse:", lambda p: ttk.Combobox(
            p, textvariable=self._var_btn,
            values=["left", "right", "middle"],
            state="readonly", width=10, font=("Segoe UI", 11)
        ).pack(side="left"))

        mouse_row("Tip Click:", lambda p: ttk.Combobox(
            p, textvariable=self._var_click,
            values=["single", "double", "triple", "right"],
            state="readonly", width=10, font=("Segoe UI", 11)
        ).pack(side="left"))

        # Buton captura pozitie
        r_cap = tk.Frame(self._frame_mouse, bg=C["bg_main"])
        r_cap.pack(fill="x", padx=16, pady=2)
        tk.Button(r_cap, text="📍 Captureaza Pozitia Mouse-ului (3s)",
                  bg=C["primary"], fg="white",
                  font=("Segoe UI", 10), relief="flat",
                  command=self._capture_pos).pack(side="left")

        # Scroll amount
        mouse_row("Scroll (dy):", lambda p: tk.Entry(
            p, textvariable=self._var_scroll_dy, width=10,
            bg=C["bg_input"], fg=C["text"], font=("Segoe UI", 11),
            relief="flat", insertbackground=C["text"]
        ).pack(side="left"))

        # ── Sectiune Tastatura ──
        tk.Frame(f, bg=C["separator"], height=1).pack(fill="x", padx=16, pady=6)
        self._lbl_key = tk.Label(f, text="⌨  Optiuni Tastatura",
                                 bg=C["bg_main"], fg=C["primary"],
                                 font=("Segoe UI", 11, "bold"))
        self._lbl_key.pack(anchor="w", padx=16, pady=(2, 0))

        self._frame_key = tk.Frame(f, bg=C["bg_main"])
        self._frame_key.pack(fill="x")

        def key_row(label, widget_fn):
            r = tk.Frame(self._frame_key, bg=C["bg_main"])
            r.pack(fill="x", padx=16, pady=2)
            tk.Label(r, text=label, bg=C["bg_main"], fg=C["text_dim"],
                     font=("Segoe UI", 11), width=22, anchor="w").pack(side="left")
            widget_fn(r)

        key_row("Combinatie Taste:", lambda p: tk.Entry(
            p, textvariable=self._var_key, width=20,
            bg=C["bg_input"], fg=C["text"], font=("Segoe UI", 11),
            relief="flat", insertbackground=C["text"]
        ).pack(side="left"))

        key_row("Text de Scris:", lambda p: tk.Entry(
            p, textvariable=self._var_text, width=28,
            bg=C["bg_input"], fg=C["text"], font=("Segoe UI", 11),
            relief="flat", insertbackground=C["text"]
        ).pack(side="left"))

        # ── Sectiune Timing ──
        tk.Frame(f, bg=C["separator"], height=1).pack(fill="x", padx=16, pady=6)
        tk.Label(f, text="⏱  Timing",
                 bg=C["bg_main"], fg=C["primary"],
                 font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=16, pady=(2, 0))

        def time_row(label, widget_fn):
            r = tk.Frame(f, bg=C["bg_main"])
            r.pack(fill="x", padx=16, pady=2)
            tk.Label(r, text=label, bg=C["bg_main"], fg=C["text_dim"],
                     font=("Segoe UI", 11), width=22, anchor="w").pack(side="left")
            widget_fn(r)

        time_row("Delay inainte (sec):", lambda p: tk.Entry(
            p, textvariable=self._var_delay_b, width=10,
            bg=C["bg_input"], fg=C["text"], font=("Segoe UI", 11),
            relief="flat", insertbackground=C["text"]
        ).pack(side="left"))

        time_row("Delay dupa (sec):", lambda p: tk.Entry(
            p, textvariable=self._var_delay_a, width=10,
            bg=C["bg_input"], fg=C["text"], font=("Segoe UI", 11),
            relief="flat", insertbackground=C["text"]
        ).pack(side="left"))

        # ── Sectiune Intrebare ──
        tk.Frame(f, bg=C["separator"], height=1).pack(fill="x", padx=16, pady=6)
        self._lbl_q = tk.Label(f, text="❓  Intrebare User",
                               bg=C["bg_main"], fg=C["primary"],
                               font=("Segoe UI", 11, "bold"))
        self._lbl_q.pack(anchor="w", padx=16, pady=(2, 0))

        self._frame_q = tk.Frame(f, bg=C["bg_main"])
        self._frame_q.pack(fill="x")

        rq = tk.Frame(self._frame_q, bg=C["bg_main"])
        rq.pack(fill="x", padx=16, pady=2)
        tk.Label(rq, text="Text Intrebare:", bg=C["bg_main"], fg=C["text_dim"],
                 font=("Segoe UI", 11), width=22, anchor="w").pack(side="left")
        tk.Entry(rq, textvariable=self._var_question, width=28,
                 bg=C["bg_input"], fg=C["text"], font=("Segoe UI", 11),
                 relief="flat", insertbackground=C["text"]).pack(side="left")

        # ── Optiuni generale ──
        tk.Frame(f, bg=C["separator"], height=1).pack(fill="x", padx=16, pady=6)
        r_skip = tk.Frame(f, bg=C["bg_main"])
        r_skip.pack(fill="x", padx=16, pady=2)
        tk.Checkbutton(r_skip, text="Sari peste acest pas la executie",
                       variable=self._var_skip,
                       bg=C["bg_main"], fg=C["text"],
                       selectcolor=C["bg_input"],
                       font=("Segoe UI", 11), activebackground=C["bg_main"],
                       activeforeground=C["text"]).pack(side="left")

        r_com = tk.Frame(f, bg=C["bg_main"])
        r_com.pack(fill="x", padx=16, pady=2)
        tk.Label(r_com, text="Comentariu:", bg=C["bg_main"], fg=C["text_dim"],
                 font=("Segoe UI", 11), width=22, anchor="w").pack(side="left")
        tk.Entry(r_com, textvariable=self._var_comment, width=28,
                 bg=C["bg_input"], fg=C["text"], font=("Segoe UI", 11),
                 relief="flat", insertbackground=C["text"]).pack(side="left")

        # ── Butoane OK/Cancel ──
        tk.Frame(f, bg=C["separator"], height=1).pack(fill="x", padx=16, pady=8)
        btn_row = tk.Frame(f, bg=C["bg_main"])
        btn_row.pack(pady=(0, 12))
        tk.Button(btn_row, text="✔  Salveaza Pasul",
                  bg=C["success"], fg="white",
                  font=("Segoe UI", 12, "bold"), relief="flat",
                  padx=20, pady=6,
                  command=self._ok).pack(side="left", padx=8)
        tk.Button(btn_row, text="✖  Anuleaza",
                  bg=C["danger"], fg="white",
                  font=("Segoe UI", 12), relief="flat",
                  padx=20, pady=6,
                  command=self.destroy).pack(side="left", padx=8)

    def _on_type_change(self):
        """Afiseaza/ascunde sectiunile relevante in functie de tipul pasului."""
        t = self._var_type.get()
        # Mouse: CLICK, DBLCLICK, RIGHTCLICK, MOVE, SCROLL
        show_mouse = t in ("CLICK","DBLCLICK","RIGHTCLICK","MOVE","SCROLL")
        # Tastatura: KEY, TYPE
        show_key   = t in ("KEY","TYPE")
        # Intrebare: QUESTION
        show_q     = t == "QUESTION"

        for w in [self._lbl_mouse, self._frame_mouse]:
            w.pack_configure() if show_mouse else w.pack_forget()
        for w in [self._lbl_key, self._frame_key]:
            w.pack_configure() if show_key else w.pack_forget()
        for w in [self._lbl_q, self._frame_q]:
            w.pack_configure() if show_q else w.pack_forget()

        # Auto-descriere
        if not self._var_desc.get():
            desc_map = {
                "CLICK":      "Click stanga",
                "DBLCLICK":   "Dublu click",
                "RIGHTCLICK": "Click dreapta",
                "KEY":        "Apasare tasta",
                "TYPE":       "Scriere text",
                "SCROLL":     "Scroll",
                "MOVE":       "Miscare mouse",
                "DELAY":      "Pauza",
                "SCREENSHOT": "Captura ecran",
                "QUESTION":   "Intrebare utilizator",
            }
            self._var_desc.set(desc_map.get(t, ""))

    def _capture_pos(self):
        """Captureaza pozitia mouse-ului dupa 3 secunde."""
        self.withdraw()
        for i in range(3, 0, -1):
            time.sleep(1.0)
        if PYAUTOGUI_AVAILABLE:
            x, y = pyautogui.position()
            self._var_x.set(x)
            self._var_y.set(y)
        self.deiconify()
        self.lift()

    def _ok(self):
        """Salveaza pasul si inchide dialogul."""
        s = self._step
        s.step_type    = self._var_type.get()
        s.description  = self._var_desc.get() or STEP_TYPES.get(s.step_type, s.step_type)
        s.x            = self._var_x.get()
        s.y            = self._var_y.get()
        s.button       = self._var_btn.get()
        s.click_type   = self._var_click.get()
        s.key_combo    = self._var_key.get()
        s.text_input   = self._var_text.get()
        s.scroll_dy    = self._var_scroll_dy.get()
        s.delay_before = self._var_delay_b.get()
        s.delay_after  = self._var_delay_a.get()
        s.skip         = self._var_skip.get()
        s.comment      = self._var_comment.get()
        s.question_text= self._var_question.get()
        self.result    = s
        self.destroy()

# ==============================================================================
# SECTIUNEA 13: FEREASTRA FLOATING SHORTCUTS
# ==============================================================================


# ==============================================================================
# SECTIUNEA 12e — MODE INDICATOR OVERLAY (v3.9)
# ==============================================================================

class ModeIndicatorOverlay:
    """[v3.9] Indicator mod activ: SIMULATION (violet) sau DEBUG (portocaliu).
    
    Pozitii overlay (dreapta ecran, y=10):
      RUN        @ sw - 130  (verde,      W=120)
      SIMULATION @ sw - 270  (violet,     W=130)
      DEBUG      @ sw - 420  (portocaliu, W=140)
    """

    W, H = 130, 22

    def __init__(self, root):
        self._root     = root
        self._win      = None
        self._running  = False
        self._after_id = None
        self._alpha_hi = True

    def show(self, mode: str = "simulation"):
        self.hide()
        if mode == "simulation":
            text     = "🔍  SIMULATION"
            bg_color = "#3D0070"
            fg_color = "#D8B4FE"
            x_offset = 270
        else:
            text     = "🐛  DEBUG"
            bg_color = "#7C2D00"
            fg_color = "#FED7AA"
            x_offset = 420
        try:
            sw = self._root.winfo_screenwidth()
        except Exception:
            sw = 1920
        win = tk.Toplevel(self._root)
        win.overrideredirect(True)
        win.attributes("-topmost", True)
        win.attributes("-alpha", 0.92)
        win.configure(bg=bg_color)
        win.geometry(f"{self.W}x{self.H}+{sw - self.W - x_offset}+10")
        tk.Label(win, text=text,
                 bg=bg_color, fg=fg_color,
                 font=("Segoe UI", 7, "bold")).pack(expand=True, fill="both")
        self._win      = win
        self._running  = True
        self._alpha_hi = True
        self._pulse()

    def hide(self):
        self._running = False
        if self._after_id:
            try:
                self._root.after_cancel(self._after_id)
            except Exception:
                pass
            self._after_id = None
        if self._win:
            try:
                self._win.destroy()
            except Exception:
                pass
            self._win = None

    def _pulse(self):
        if not self._running or not self._win:
            return
        alpha = 0.95 if self._alpha_hi else 0.50
        self._alpha_hi = not self._alpha_hi
        try:
            self._win.attributes("-alpha", alpha)
        except Exception:
            return
        self._after_id = self._root.after(700, self._pulse)

class FloatingShortcutsWindow:
    """
    [WIDGET] Fereastra floating always-on-top cu shortcut-urile active.
    Afisata in timpul inregistrarii/redarii.
    """

    def __init__(self, parent, settings: SettingsManager):
        """Initializeaza fereastra floating."""
        self._parent   = parent
        self._settings = settings
        self._win:     Optional[tk.Toplevel] = None

    def show(self):
        """Afiseaza fereastra floating."""
        if self._win and self._win.winfo_exists():
            self._win.lift()
            return
        self._win = tk.Toplevel(self._parent)
        self._win.title("Shortcut-uri Active")
        pos = self._settings.get("shortcuts_panel_position", "top-right")
        sw = self._win.winfo_screenwidth()
        sh = self._win.winfo_screenheight()
        w_win, h_win = 220, 180

        positions = {
            "top-right":    (sw - w_win - 10, 10),
            "top-left":     (10, 10),
            "bottom-right": (sw - w_win - 10, sh - h_win - 40),
            "bottom-left":  (10, sh - h_win - 40),
        }
        px, py = positions.get(pos, (sw - w_win - 10, 10))
        self._win.geometry(f"{w_win}x{h_win}+{px}+{py}")
        self._win.resizable(True, True)
        self._win.minsize(260, 400)
        self._build()

    def hide(self):
        """Ascunde fereastra floating."""
        if self._win and self._win.winfo_exists():
            self._win.destroy()
            self._win = None

    def _build(self):
        """Construieste continutul ferestrei."""
        w = self._win
        tk.Label(w, text="⌨  Shortcut-uri Active",
                 bg=C["bg_card"], fg=C["primary"],
                 font=("Segoe UI", 11, "bold")).pack(pady=(8, 4))
        tk.Frame(w, bg=C["separator"], height=1).pack(fill="x", padx=8)

        sc = self._settings.get("shortcuts", DEFAULT_SHORTCUTS)
        shortcuts_display = [
            ("Start Rec",   sc.get("start_rec", "F5")),
            ("Stop Rec",    sc.get("stop_rec",  "F6")),
            ("Ruleaza",     sc.get("play",      "F7")),
            ("Pauza/Reia",  sc.get("pause",     "F8")),
            ("Stop Play",   sc.get("stop_play", "F9")),
            ("Stop Urgenta",sc.get("emergency", "F12")),
        ]
        for action, key in shortcuts_display:
            r = tk.Frame(w, bg=C["bg_card"])
            r.pack(fill="x", padx=10, pady=1)
            tk.Label(r, text=action, bg=C["bg_card"], fg=C["text_dim"],
                     font=("Segoe UI", 10), width=14, anchor="w").pack(side="left")
            tk.Label(r, text=key, bg=C["primary"], fg="white",
                     font=("Segoe UI", 10, "bold"),
                     padx=6, pady=1, relief="flat").pack(side="left")

        tk.Button(w, text="Inchide", bg=C["bg_input"], fg=C["text"],
                  font=("Segoe UI", 9), relief="flat",
                  command=self.hide).pack(pady=6)

# ==============================================================================
# SECTIUNEA 14: FEREASTRA PRINCIPALA — MAIN WINDOW
# ==============================================================================

# ==============================================================================
# SECTIUNEA 10.5: BARA LATERALA SHORTCUTURI (ShortcutSidebar)
# ==============================================================================

class ShortcutSidebar:
    """
    Bara laterala compacta care afiseaza toate shortcut-urile active.
    Apare automat cand inregistrarea sau redarea sunt active.
    Se plaseaza in dreapta zonei de continut principale.
    """
    _LABELS = [
        ("start_rec",   "▶ Start Rec",   "#C62828"),
        ("stop_rec",    "■ Stop Rec",    "#B71C1C"),
        ("resume_play", "↺ Reia Play",   "#00695C"),
        ("play",        "▶ Ruleaza",     "#2E7D32"),
        ("pause",       "⏸ Pauza/Reia", "#E65100"),
        ("stop_play",   "■ Stop Play",   "#C62828"),
        ("emergency",   "⚡ URGENTA",    "#880E4F"),
        ("save",        "💾 Salveaza",   "#1565C0"),
        ("new",         "✚ Nou",         "#4527A0"),
        ("open",        "📂 Deschide",   "#00695C"),
        ("add_delay",   "⏱ Add Delay",  "#558B2F"),
        ("add_step",    "✚ Add Pas",    "#0277BD"),
        ("delete_step", "🗑 Sterge",    "#D84315"),
        ("skip_step",   "↷ Skip",       "#6A1B9A"),
        ("debug_step",  "🐛 Debug",     "#37474F"),
    ]

    def __init__(self, parent_frame, settings):
        self._parent   = parent_frame
        self._settings = settings
        self._frame    = None
        self._visible  = False

    def show(self):
        if self._visible:
            self._refresh(); return
        sc = self._settings._data.get("shortcuts", DEFAULT_SHORTCUTS)
        self._frame = tk.Frame(self._parent, bg="#0D1B2A",
                               relief="flat", bd=0, width=150)
        self._frame.pack(side="right", fill="y", padx=(2, 0))
        self._frame.pack_propagate(False)
        tk.Label(self._frame, text="⌨  Shortcuts",
                 bg="#0D1B2A", fg="#00BCD4",
                 font=("Segoe UI", 9, "bold"),
                 pady=4, anchor="center").pack(fill="x")
        tk.Frame(self._frame, bg="#00BCD4", height=1).pack(fill="x", pady=(0, 2))
        for action, label, color in self._LABELS:
            key = sc.get(action, DEFAULT_SHORTCUTS.get(action, "—"))
            row = tk.Frame(self._frame, bg="#0D1B2A")
            row.pack(fill="x", padx=3, pady=1)
            tk.Label(row, text=label, bg="#0D1B2A", fg="#CFD8DC",
                     font=("Segoe UI", 8), anchor="w",
                     width=10, wraplength=82).pack(side="left")
            tk.Label(row, text=key, bg=color, fg="white",
                     font=("Segoe UI", 8, "bold"),
                     padx=3, pady=1, relief="flat",
                     anchor="center").pack(side="right", padx=(2, 0))
        self._visible = True

    def hide(self):
        if self._frame:
            try: self._frame.destroy()
            except Exception: pass
            self._frame = None
        self._visible = False

    def _refresh(self):
        self.hide(); self.show()



# ==============================================================================

# ==============================================================================
# SECTIUNEA 12a.1 - TOOLTIP HELPER (v3.9)
# ==============================================================================

class ToolTip:
    """[v3.9] Tooltip cu descriere si shortcut pentru orice widget Tkinter."""

    def __init__(self, widget, text, shortcut=""):
        self._widget   = widget
        self._text     = text
        self._shortcut = shortcut
        self._tip_win  = None
        widget.bind("<Enter>",       self._show)
        widget.bind("<Leave>",       self._hide)
        widget.bind("<ButtonPress>", self._hide)

    def _show(self, event=None):
        if self._tip_win:
            return
        x = self._widget.winfo_rootx() + 10
        y = self._widget.winfo_rooty() + self._widget.winfo_height() + 4
        self._tip_win = tw = tk.Toplevel(self._widget)
        tw.overrideredirect(True)
        tw.attributes("-topmost", True)
        tw.geometry("+%d+%d" % (x, y))
        content = self._text
        if self._shortcut:
            content += "\n\u2328  " + self._shortcut
        bg_col = C.get("bg_card", "#2A2A3E")
        tk.Label(
            tw, text=content,
            bg=bg_col, fg=C.get("text", "#FFFFFF"),
            font=("Segoe UI", 9),
            relief="flat", padx=8, pady=4,
            justify="left"
        ).pack()

    def _hide(self, event=None):
        if self._tip_win:
            try:
                self._tip_win.destroy()
            except Exception:
                pass
            self._tip_win = None


# SECTIUNEA 12b — DEBUG GHOST OVERLAY (v3.7)
# ==============================================================================

class DebugGhostOverlay:
    """[v3.9] Indicator vizual cursor in modul debug."""
    COLOR_MAP = {
        "CLICK": "#FF4444", "RCLICK": "#FF8800", "DCLICK": "#FF6600",
        "TYPE": "#4488FF", "KEY": "#4488FF", "SCROLL": "#AA44FF", "WAIT": "#888888",
    }
    DEFAULT_COLOR = "#FF4444"
    SIZE = 60; RADIUS = 18

    def __init__(self, root):
        self._root = root; self._win = None; self._canvas = None
        self._active = False; self._after_id = None; self._lbl_text = ""

    def enable(self): self._active = True
    def disable(self): self._active = False; self._hide()
    def is_active(self): return self._active

    def show_at(self, x, y, label="", color=None, duration_ms=600):
        if not self._active: return
        self._lbl_text = label
        col = color or self.COLOR_MAP.get(label, self.DEFAULT_COLOR)
        self._build_window(x, y, col)
        if self._after_id:
            try: self._root.after_cancel(self._after_id)
            except Exception: pass
        self._after_id = self._root.after(duration_ms, self._hide)

    def _build_window(self, x, y, color):
        S = self.SIZE; R = self.RADIUS
        sw = self._root.winfo_screenwidth(); sh = self._root.winfo_screenheight()
        wx = max(0, min(x - S // 2, sw - S)); wy = max(0, min(y - S // 2, sh - S))
        if self._win is None:
            self._win = tk.Toplevel(self._root)
            self._win.overrideredirect(True)
            self._win.attributes("-topmost", True)
            self._win.attributes("-alpha", 0.82)
            try:
                self._win.attributes("-transparentcolor", "#010101")
                self._win.configure(bg="#010101")
            except Exception:
                self._win.configure(bg="black")
            self._canvas = tk.Canvas(self._win, width=S, height=S, bg="#010101", highlightthickness=0)
            self._canvas.pack()
        self._win.geometry(f"{S}x{S}+{wx}+{wy}")
        self._win.deiconify()
        cv = self._canvas
        if cv is None: return
        cv.delete("all")
        cx, cy = S // 2, S // 2
        cv.create_oval(cx-R-4, cy-R-4, cx+R+4, cy+R+4, outline=color, width=2, fill="")
        cv.create_oval(cx-R, cy-R, cx+R, cy+R, outline="white", width=2, fill=color)
        cv.create_line(cx-6, cy, cx+6, cy, fill="white", width=2)
        cv.create_line(cx, cy-6, cx, cy+6, fill="white", width=2)
        if self._lbl_text:
            ty = cy - R - 8 if wy > 30 else cy + R + 8
            cv.create_text(cx, ty, text=self._lbl_text, fill="white", font=("Segoe UI", 7, "bold"), anchor="center")

    def _hide(self):
        if self._win:
            try: self._win.withdraw()
            except Exception: pass

    def destroy(self):
        if self._win:
            try: self._win.destroy()
            except Exception: pass
            self._win = None


# ==============================================================================
# SECTIUNEA 12c — STOPWATCH OVERLAY (v3.7)
# ==============================================================================

class StopwatchOverlay:
    """[v3.9] Countdown vizual inainte de pornirea redarii."""
    W, H = 202, 32

    def __init__(self, root):
        self._root = root; self._windows = []; self._after_id = None

    def show_countdown(self, seconds=3, on_done=None):
        self._destroy_all(); self._tick(seconds, on_done)

    def _tick(self, n, on_done):
        if n <= 0:
            self._show_text("▶  START!", "#32CD32")
            self._after_id = self._root.after(
                600, lambda: (self._destroy_all(), on_done() if callable(on_done) else None)
            )
            return
        self._show_text(f"▶  {n}...", "#FF9500")
        self._after_id = self._root.after(1000, lambda: self._tick(n - 1, on_done))

    def _show_text(self, text, color):
        self._destroy_all()
        sw = self._root.winfo_screenwidth(); sh = self._root.winfo_screenheight()
        x = (sw - self.W) // 2; y = sh - 80
        win = tk.Toplevel(self._root)
        win.overrideredirect(True); win.attributes("-topmost", True)
        win.attributes("-alpha", 0.92); win.geometry(f"{self.W}x{self.H}+{x}+{y}")
        win.configure(bg="#1A1A2E")
        frame = tk.Frame(win, bg="#1A1A2E", bd=2)
        frame.pack(fill="both", expand=True, padx=2, pady=2)
        lbl = tk.Label(frame, text=text, bg="#1A1A2E", fg=color,
                       font=("Segoe UI", 13, "bold"), anchor="center")
        lbl.pack(fill="both", expand=True)
        self._windows.append(win)

    def _destroy_all(self):
        for w in self._windows:
            try: w.destroy()
            except Exception: pass
        self._windows.clear()
        if self._after_id:
            try: self._root.after_cancel(self._after_id)
            except Exception: pass
            self._after_id = None

    def destroy(self): self._destroy_all()


# ==============================================================================
# SECTIUNEA 12d — RUN INDICATOR OVERLAY (v3.7)
# ==============================================================================

class RunIndicatorOverlay:
    """[v3.9] Indicator RUN pulsant."""

    W, H = 120, 22

    def __init__(self, root):
        self._root     = root
        self._win      = None
        self._running  = False
        self._alpha_hi = True
        self._after_id = None

    def show(self):
        self.hide()
        try:
            sw = self._root.winfo_screenwidth()
        except Exception:
            sw = 1920
        win = tk.Toplevel(self._root)
        win.overrideredirect(True)
        win.attributes("-topmost", True)
        win.attributes("-alpha", 0.92)
        win.configure(bg="#0A0A0A")
        win.geometry(f"{self.W}x{self.H}+{sw - self.W - 10}+10")
        tk.Label(win, text="▶  RUN",
                 bg="#0A0A0A", fg="#32CD32",
                 font=("Segoe UI", 7, "bold")).pack(expand=True, fill="both")
        self._win      = win
        self._running  = True
        self._alpha_hi = True
        self._pulse()

    def hide(self):
        self._running = False
        if self._after_id:
            try:
                self._root.after_cancel(self._after_id)
            except Exception:
                pass
            self._after_id = None
        if self._win:
            try:
                self._win.destroy()
            except Exception:
                pass
            self._win = None

    def _pulse(self):
        if not self._running or not self._win:
            return
        alpha = 0.95 if self._alpha_hi else 0.40
        self._alpha_hi = not self._alpha_hi
        try:
            self._win.attributes("-alpha", alpha)
        except Exception:
            return
        self._after_id = self._root.after(800, self._pulse)


class FlowFrame(tk.Frame):
    """[v4.1] Bara de actiuni: grupurile de butoane trec pe randul urmator cand nu incap."""

    def __init__(self, master, **kw):
        super().__init__(master, **kw)
        self._items = []
        self._last = None
        self.bind("<Configure>", lambda e: self._relayout())

    def set_items(self, items):
        for w in self._items:
            w.place_forget()
        self._items = list(items)
        self._last = None
        self.after_idle(self._relayout)

    def _relayout(self):
        width = self.winfo_width()
        if width <= 1:
            width = self.master.winfo_width()
        x = y = row_h = 0
        pad = 6
        for w in self._items:
            rw, rh = w.winfo_reqwidth(), w.winfo_reqheight()
            if x > 0 and x + rw > width:
                x, y, row_h = 0, y + row_h + 2, 0
            w.place(x=x + pad, y=y + 3)
            x += rw + pad
            row_h = max(row_h, rh)
        height = y + row_h + 6
        if height != self._last:
            self._last = height
            self.configure(height=height)


class MainWindow:
    """
    [GUI] Fereastra principala a aplicatiei AutoPilot DC.
    Contine: MenuBar, Toolbar, TabView (Recorder, Step Builder, Log,
    Rutine, Excel, Notite, Setari, Ajutor), StatusBar.
    """

    def __init__(self):
        """Initializeaza fereastra principala si toate componentele."""

        # ── 14.1 Initializare managers ────────────────────────────
        self.settings     = SettingsManager()
        self.log_mgr      = LogManager()
        self.routine_mgr  = RoutineManager()
        self.recorder     = RecorderEngine(self.settings)
        self.player       = PlayerEngine(self.settings, self.log_mgr)
        self.excel_eng    = ExcelEngine()
        self.hotkey_mgr   = HotkeyManager()

        # ── 14.2 Tema ─────────────────────────────────────────────
        global C
        theme = self.settings.get("theme", "dark")
        C = COLORS_DARK if theme == "dark" else COLORS_LIGHT
        COLORS_DARK.update(COLORS_DARK)  # no-op pentru dark
        if theme == "light":
            C.update(COLORS_LIGHT)

        # ── 14.3 Fereastra CTk ────────────────────────────────────
        ctk.set_appearance_mode("dark" if theme == "dark" else "light")
        ctk.set_default_color_theme("blue")
        app_shell.set_app_id()          # iconita AutoPilot in bara de activitati (nu cea a lui Python)
        self.root = ctk.CTk()
        app_shell.apply_icon(self.root)
        self._start_in_tray = "--tray" in sys.argv
        self._really_quit = False
        self._tray_hint_shown = False
        self.tray = app_shell.Tray(
            ui_call=lambda fn: self.root.after(0, fn),
            items=[("🎬 Recorder", lambda: (self._show_from_tray(), self._set_mode("recorder")), False),
                   ("🧩 Studio RPR", lambda: (self._show_from_tray(), self._set_mode("studio")), False),
                   ("🚨 STOP URGENTA", self._emergency_stop, True),
                   ("Iesire", self._quit_app, True)],
            on_open=self._show_from_tray)
        self.root.title(f"{APP_NAME} v{APP_VERSION}")
        self.root.geometry("1280x800")
        self.root.minsize(1024, 600)
        # v3.7: debug var + overlay engines
        self._debug_var  = tk.BooleanVar(value=self.settings.get("debug_visual", False))
        self._debug_mode = bool(self._debug_var.get())
        self.debug_overlay = DebugGhostOverlay(self.root)
        self.stopwatch_ovl = StopwatchOverlay(self.root)
        self.run_indicator  = RunIndicatorOverlay(self.root)
        self.mode_indicator = ModeIndicatorOverlay(self.root)
        # v4.1: chenar RUN/REC + sistemul de preventie
        self.run_frame = RunFrame(self.root)
        self.run_frame.enabled = bool(self.settings.get("show_run_frame", True))
        self.guard = SafetyGuard()
        self.player.guard = self.guard
        if self._debug_mode:
            self.debug_overlay.enable()

        self.root.configure(fg_color=C["bg_main"])

        # ── 14.4 Variabile de stare ───────────────────────────────
        self._is_recording:  bool = False
        self._is_playing:    bool = False
        self._current_steps: List[StepModel] = []

        # ── 14.5 Variabile UI ─────────────────────────────────────
        self._status_var    = tk.StringVar(value="Gata")
        self._step_count_var= tk.StringVar(value="Pasi: 0")
        self._countdown_var = tk.StringVar(value="")
        self._iter_var      = tk.StringVar(value="")
        self._repeat_var    = tk.IntVar(value=self.settings.get("repeat_count", 1))

        # ── 14.6 Floating windows ─────────────────────────────────
        self._floating_sc = FloatingShortcutsWindow(self.root, self.settings)

        # ── 14.7 Construire UI ────────────────────────────────────
        self._build_menu()
        self._build_toolbar()
        self._build_tabs()
        self._build_statusbar()

        # ── 14.8 Conectare callbacks ──────────────────────────────
        self._connect_callbacks()

        # v4.1: ultima zona de lucru folosita
        if self.settings.get("ui_mode", "recorder") == "studio":
            self.root.after(100, lambda: self._set_mode("studio"))
        else:
            self._set_mode("recorder")

        # ── 14.9 Hotkeys ──────────────────────────────────────────
        self._register_hotkeys()

        # ── 14.10 Bindings tastatura pe fereastra ─────────────────
        self.root.bind("<Control-n>", lambda e: self._new_routine())
        self.root.bind("<Control-o>", lambda e: self._open_routine_dialog())
        self.root.bind("<Control-s>", lambda e: self._save_routine_dialog())
        self.root.bind("<F5>",        lambda e: self._toggle_recording())
        self.root.bind("<F6>",        lambda e: self._stop_all())
        self.root.bind("<F7>",        lambda e: self._start_playback())
        self.root.bind("<F8>",        lambda e: self._toggle_pause())
        self.root.bind("<F9>",        lambda e: self._stop_playback())
        self.root.bind("<F12>",       lambda e: self._emergency_stop())
        self.root.bind("<Delete>",    lambda e: self._delete_selected_steps())

        # ── 14.11 Protocol inchidere ──────────────────────────────
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def run(self):
        """Porneste bucla principala a aplicatiei."""
        # v4.1: pornita fara consola (.pyw), fereastra poate ramane in spatele altora -> o aducem in fata
        def _bring_to_front():
            try:
                self.root.deiconify()
                self.root.lift()
                self.root.attributes("-topmost", True)
                self.root.after(400, lambda: self.root.attributes("-topmost", False))
                self.root.focus_force()
            except Exception:
                pass
        if app_shell.is_autostart_enabled():
            app_shell.set_autostart(True, bool(self.settings.get("start_minimized_tray", True)))
        if self._start_in_tray and app_shell.tray_available():
            # pornit cu Windows: fara fereastra, doar pictograma langa ceas
            self.root.withdraw()
            self.root.after(500, self.tray.show)
        else:
            self.root.after(300, _bring_to_front)
        self.root.mainloop()

    # ==========================================================================
    # SECTIUNEA 14.A: MENIU
    # ==========================================================================

    def _build_menu(self):
        """Construieste bara de meniu completa."""
        mb_cfg = dict(
            bg=C["bg_card"], fg=C["text"],
            activebackground=C["primary"], activeforeground="white",
            relief="flat"
        )
        menubar = tk.Menu(self.root, **mb_cfg)  # type: ignore[call-arg]
        self.root.config(menu=menubar)

        def sub(label):
            m = tk.Menu(menubar, tearoff=0, **mb_cfg)  # type: ignore[call-arg]
            menubar.add_cascade(label=label, menu=m)
            return m

        # ── Fisier ──
        fm = sub("Fisier")
        fm.add_command(label="Rutina Noua        Ctrl+N", command=self._new_routine)
        fm.add_command(label="Deschide Rutina    Ctrl+O", command=self._open_routine_dialog)
        fm.add_command(label="Salveaza Rutina    Ctrl+S", command=self._save_routine_dialog)
        fm.add_separator()
        fm.add_command(label="Export Log XLSX",  command=self._export_log_xlsx)
        fm.add_command(label="Export Log CSV",   command=self._export_log_csv)
        fm.add_command(label="Export Log JSON",  command=self._export_log_json)
        fm.add_separator()
        fm.add_command(label="Iesire",           command=self._quit_app)

        # ── Editare ──
        em = sub("Editare")
        em.add_command(label="Sterge Toti Pasii",    command=self._clear_all_steps)
        em.add_command(label="Sterge Pasii Selectati Delete", command=self._delete_selected_steps)
        em.add_command(label="Sterge Log",            command=self._clear_log)
        em.add_separator()
        em.add_command(label="Adauga Pas Manual",     command=self._add_step_manual)
        em.add_command(label="Adauga Delay",          command=self._add_delay_step)

        # ── Vizualizare ──
        vm = sub("Vizualizare")
        vm.add_command(label="Tema Dark",   command=lambda: self._set_theme("dark"))
        vm.add_command(label="Tema Light",  command=lambda: self._set_theme("light"))
        vm.add_separator()
        vm.add_command(label="Arata Shortcut-uri Floating",
                       command=self._floating_sc.show)
        vm.add_command(label="Ascunde Shortcut-uri Floating",
                       command=self._floating_sc.hide)

        # ── Rutine ──
        rm = sub("Rutine")
        rm.add_command(label="Rutina Noua",           command=self._new_routine)
        rm.add_command(label="Salveaza Rutina",       command=self._save_routine_dialog)
        rm.add_command(label="Incarca Rutina",        command=self._open_routine_dialog)
        rm.add_command(label="Reseteaza Rutina",      command=self._clear_all_steps)

        # ── Setari ──
        sm = sub("Setari")
        sm.add_command(label="Setari Aplicatie",      command=self._open_settings_tab)
        sm.add_command(label="Configureaza Shortcut-uri",
                       command=self._open_shortcuts_dialog)

        # ── Ajutor ──
        hm = sub("Ajutor")
        hm.add_command(label="Ghid Rapid",            command=self._show_quick_guide)
        hm.add_command(label="Shortcut-uri",          command=self._floating_sc.show)
        hm.add_separator()
        hm.add_command(label="Despre AutoPilot DC",   command=self._show_about)

    # ==========================================================================
    # SECTIUNEA 14.B: TOOLBAR
    # ==========================================================================

    def _build_toolbar(self):
        """[v4.1] Bara de sus pe doua randuri:
        1. antet: comutator Recorder / Studio, stare, setari, STOP URGENTA (mereu vizibile)
        2. actiuni mici, grupate, specifice zonei de lucru; trec pe randul urmator daca nu incap."""
        hdr = tk.Frame(self.root, bg=C["bg_card"])
        hdr.pack(fill="x", side="top")
        self._toolbar = hdr

        tk.Label(hdr, text="AutoPilot DC", bg=C["bg_card"], fg=C["primary"],
                 font=("Segoe UI", 13, "bold")).pack(side="left", padx=(12, 14), pady=6)

        # ── Comutator zone de lucru ──
        self._mode = "recorder"
        self._studio = None
        self._mode_btns = {}
        sw = tk.Frame(hdr, bg=C["bg_main"])
        sw.pack(side="left", pady=6)
        for key, text, tip in [("recorder", "🎬  Recorder", "Inregistrare si redare pe coordonate (mouse / tastatura)"),
                               ("studio", "🧩  Studio RPR", "Rutine pe obiecte: Web / SAP / Desktop + Excel, fara cod")]:
            b = tk.Button(sw, text=text, command=lambda k=key: self._set_mode(k), relief="flat", bd=0,
                          font=("Segoe UI", 10, "bold"), padx=14, pady=4, cursor="hand2")
            b.pack(side="left", padx=1, pady=1)
            self._mode_btns[key] = b
            ToolTip(b, tip, "")

        def hbtn(text, cmd, bg=None, fg=None, tip=""):
            b = tk.Button(hdr, text=text, command=cmd, bg=bg or C["bg_input"], fg=fg or C["text"],
                          activebackground=C["primary"], activeforeground="white", relief="flat", bd=0,
                          font=("Segoe UI", 9, "bold"), padx=9, pady=4, cursor="hand2")
            b.pack(side="right", padx=2, pady=6)
            if tip:
                ToolTip(b, tip, "")
            return b

        # dreapta -> stanga
        self._btn_emg = tk.Button(hdr, text="🚨 STOP URGENTA", command=self._emergency_stop,
                                  bg=C["emergency"], fg="white", activebackground="#5A0000",
                                  activeforeground="white", font=("Segoe UI", 10, "bold"),
                                  relief="flat", padx=10, pady=4, cursor="hand2")
        self._btn_emg.pack(side="right", padx=(4, 10), pady=6)
        self._btn_exit = hbtn("✕", self._on_close, bg=C["bg_main"], fg=C["text_dim"], tip="Inchide aplicatia")
        hbtn("❓", self._help_for_mode, tip="Ghid (Recorder sau Studio, dupa zona deschisa)")
        hbtn("⚙", lambda: (self._set_mode("recorder"), self._open_settings_tab()), tip="Setari aplicatie")
        self._btn_sc = hbtn("⌨", self._toggle_shortcuts_panel, tip="Afiseaza / ascunde panoul de shortcut-uri")
        self._lbl_cd = tk.Label(hdr, textvariable=self._countdown_var, bg=C["bg_card"], fg=C["warning"],
                                font=("Segoe UI", 18, "bold"), width=4)
        self._lbl_cd.pack(side="right", padx=4)
        self._lbl_iter = tk.Label(hdr, textvariable=self._iter_var, bg=C["bg_card"], fg=C["accent"],
                                  font=("Segoe UI", 10, "bold"))
        self._lbl_iter.pack(side="right", padx=6)

        # ── Randul 2: actiunile zonei de lucru ──
        self._actions = FlowFrame(self.root, bg=C["bg_main"], height=40)
        self._actions.pack(fill="x", side="top")
        self._groups = {"recorder": [], "studio": []}

        def group(mode, title):
            g = tk.Frame(self._actions, bg=C["bg_main"])
            tk.Label(g, text=title, bg=C["bg_main"], fg=C["text_muted"],
                     font=("Segoe UI", 7, "bold")).pack(anchor="w", padx=2)
            row = tk.Frame(g, bg=C["bg_main"])
            row.pack(anchor="w")
            self._groups[mode].append(g)
            return row

        def abtn(row, text, cmd, bg=None, tip="", sc=""):
            bg = bg or C["bg_input"]
            b = tk.Button(row, text=text, command=cmd, bg=bg, fg=_btn_fg(bg), activebackground=C["primary"],
                          activeforeground="white", relief="flat", bd=0, font=("Segoe UI", 9, "bold"),
                          padx=8, pady=3, cursor="hand2", highlightthickness=1, highlightbackground=bg)
            b.pack(side="left", padx=2)
            setattr(b, "_orig_bg", bg)
            setattr(b, "_orig_fg", _btn_fg(bg))
            if tip:
                ToolTip(b, tip, sc)
            return b

        _sc = self.settings.get("shortcuts", DEFAULT_SHORTCUTS)
        # Recorder
        r = group("recorder", "INREGISTRARE")
        self._btn_rec = abtn(r, "⏺ Inregistreaza", self._toggle_recording, C["danger"],
                             "Incepe inregistrarea actiunilor", _sc.get("start_rec", "F5"))
        self._btn_stopr = abtn(r, "⏹ Stop Rec", self._stop_recording, None, "Opreste inregistrarea",
                               _sc.get("stop_rec", "F6"))
        r = group("recorder", "REDARE")
        self._btn_play = abtn(r, "▶ Ruleaza", self._start_playback, C["success"], "Ruleaza rutina inregistrata",
                              _sc.get("play", "F7"))
        self._btn_pause = abtn(r, "⏸ Pauza", self._toggle_pause, C["warning"], "Pauza / Reia redarea",
                               _sc.get("pause", "F8"))
        self._btn_stopp = abtn(r, "⏹ Stop", self._stop_playback, C["danger"], "Opreste redarea",
                               _sc.get("stop_play", "F9"))
        tk.Label(r, text=" Repetari", bg=C["bg_main"], fg=C["text_dim"], font=("Segoe UI", 9)).pack(side="left")
        self._entry_repeat = tk.Entry(r, textvariable=self._repeat_var, width=4, bg=C["bg_input"], fg=C["text"],
                                      font=("Segoe UI", 10, "bold"), justify="center", relief="flat",
                                      insertbackground=C["text"])
        self._entry_repeat.pack(side="left", padx=(3, 2), ipady=2)
        r = group("recorder", "RUTINA")
        abtn(r, "📂 Deschide", self._open_routine_dialog, None, "Deschide o rutina salvata", _sc.get("open", "Ctrl+O"))
        self._btn_save = abtn(r, "💾 Salveaza", self._save_routine_dialog, C["primary"], "Salveaza rutina curenta",
                              _sc.get("save", "Ctrl+S"))
        self._btn_reset = abtn(r, "🗑 Reseteaza", self._clear_all_steps, None, "Sterge toti pasii din rutina curenta")

        # Studio (comenzile ajung la panoul Studio, creat la prima deschidere)
        st = lambda name, *a: (lambda: getattr(self._studio, name)(*a) if self._studio else None)  # noqa: E731
        r = group("studio", "RUTINA")
        abtn(r, "📄 Nou", st("new_routine"), None, "Rutina noua (Ctrl+N)")
        abtn(r, "📂 Deschide", st("open_routine"), None, "Deschide o rutina .rpr.json (sau una veche, se converteste)")
        abtn(r, "💾 Salveaza", st("save_routine"), C["primary"], "Salveaza rutina")
        abtn(r, "Salveaza ca…", st("save_routine", True), None, "Salveaza intr-un fisier nou")
        abtn(r, "📚 Exemple", st("show_examples"), None, "Rutinele exemplu (incepe cu 01 Invatare)")
        r = group("studio", "RULARE")
        abtn(r, "▶ Ruleaza", st("run"), C["success"], "Ruleaza rutina", "F7")
        abtn(r, "⏭ Pas cu pas", st("run", True), None, "Fiecare apasare executa un singur pas")
        abtn(r, "⏸ Pauza", st("toggle_pause"), C["warning"], "Pauza / reluare", "Ctrl+F11")
        abtn(r, "⏹ Stop", st("stop"), C["danger"], "Opreste rutina", "Ctrl+F12")
        r = group("studio", "OBIECTE (SPY)")
        abtn(r, "🎯 Web", lambda: self._studio and self._studio.spy("Web"), None, "Marcheaza un element din browser")
        abtn(r, "🎯 SAP", lambda: self._studio and self._studio.spy("SAP"), None, "Marcheaza un camp / buton SAP")
        abtn(r, "🎯 Desktop", lambda: self._studio and self._studio.spy("Desktop"), None,
             "Marcheaza un element dintr-o aplicatie Windows")
        r = group("studio", "RUTINA CURENTA")
        abtn(r, "⚙ Setari rutina", st("show_routine_settings"), None, "Setarile rutinei si variabilele")
        abtn(r, "❓ Ghid", st("show_guide"), None, "Ghidul pas cu pas al Studio")

        self._set_btn_state_idle()

    def _set_mode(self, mode: str):
        """[v4.1] Comuta zona de lucru: Recorder (coordonate) sau Studio RPR (obiecte)."""
        if mode == "studio" and self._studio is None:
            try:
                from studio_ui import StudioPanel
                self._studio = StudioPanel(self._workspace, C, run_frame=self.run_frame,
                                           on_status=self._status_var.set,
                                           dnd_allowed=lambda: bool(self.settings.get("dnd_during_run", True)))
            except Exception as ex:
                import traceback
                traceback.print_exc()
                messagebox.showerror("Studio RPR", f"Studio nu a putut porni:\n{ex}")
                return
        self._mode = mode
        for key, b in self._mode_btns.items():
            on = key == mode
            b.configure(bg=C["primary"] if on else C["bg_card"], fg="white" if on else C["text_dim"],
                        activebackground=C["primary"], activeforeground="white")
        if mode == "studio":
            self._nb.pack_forget()
            self._studio.pack(fill="both", expand=True)
        else:
            if self._studio is not None:
                self._studio.pack_forget()
            self._nb.pack(fill="both", expand=True, padx=6, pady=(4, 0))
        self._actions.set_items(self._groups[mode])
        self.settings.set("ui_mode", mode)

    def _help_for_mode(self):
        if self._mode == "studio" and self._studio is not None:
            self._studio.show_guide()
        else:
            self._show_quick_guide()

    # ==========================================================================
    # SECTIUNEA 14.C: TABS
    # ==========================================================================

    def _build_tabs(self):
        """Construieste sistemul de tab-uri principal."""
        # Notebook ttk stilizat
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Main.TNotebook",
                        background=C["bg_main"],
                        tabmargins=[4, 4, 0, 0])
        style.configure("Main.TNotebook.Tab",
                        background=C["bg_card"],
                        foreground=C["text_dim"],
                        padding=[14, 6],
                        font=("Segoe UI", 11))
        style.map("Main.TNotebook.Tab",
                  background=[("selected", C["primary"])],
                  foreground=[("selected", "white")])

        # v4.1: zona de lucru comuna (Recorder = tab-urile de mai jos, Studio = panoul Studio)
        self._workspace = tk.Frame(self.root, bg=C["bg_main"])
        self._workspace.pack(fill="both", expand=True)
        self._nb = ttk.Notebook(self._workspace, style="Main.TNotebook")
        self._nb.pack(fill="both", expand=True, padx=6, pady=(4, 0))

        # ── Creeaza frame-urile tab-urilor ──
        self._tab_recorder = tk.Frame(self._nb, bg=C["bg_main"])
        self._tab_builder  = tk.Frame(self._nb, bg=C["bg_main"])
        self._tab_log      = tk.Frame(self._nb, bg=C["bg_main"])
        self._tab_routines = tk.Frame(self._nb, bg=C["bg_main"])
        self._tab_excel    = tk.Frame(self._nb, bg=C["bg_main"])
        self._tab_notes    = tk.Frame(self._nb, bg=C["bg_main"])
        self._tab_settings = tk.Frame(self._nb, bg=C["bg_main"])
        self._tab_help     = tk.Frame(self._nb, bg=C["bg_main"])

        # ── Adauga tab-urile ──
        self._nb.add(self._tab_recorder, text="🎬 Recorder")
        self._nb.add(self._tab_builder,  text="🔧 Step Builder")
        self._nb.add(self._tab_log,      text="📋 Log")
        self._nb.add(self._tab_routines, text="📁 Rutine")
        self._nb.add(self._tab_excel,    text="📊 Excel")
        self._nb.add(self._tab_notes,    text="📝 Notite")
        self._nb.add(self._tab_settings, text="⚙ Setari")
        self._nb.add(self._tab_help,     text="❓ Ajutor")

        # ── Construieste continutul ──
        self._build_tab_recorder()
        self._build_tab_builder()
        self._build_tab_log()
        self._build_tab_routines()
        self._build_tab_excel()
        self._build_tab_notes()
        self._build_tab_settings()
        self._build_tab_help()

    # ==========================================================================
    # SECTIUNEA 14.D: TAB RECORDER
    # ==========================================================================

    def _build_tab_recorder(self):
        """Construieste tab-ul de inregistrare cu treeview si optiuni."""
        parent = self._tab_recorder

        # ── Panou stanga: Optiuni ─────────────────────────────────
        left = tk.Frame(parent, bg=C["bg_card"], width=240)
        left.pack(side="left", fill="y", padx=(6, 3), pady=6)
        left.pack_propagate(False)

        tk.Label(left, text="⚙  Optiuni Inregistrare",
                 bg=C["bg_card"], fg=C["primary"],
                 font=("Segoe UI", 12, "bold")).pack(pady=(10, 4), padx=8)
        tk.Frame(left, bg=C["separator"], height=1).pack(fill="x", padx=8, pady=2)

        # Checkbox miscare mouse
        self._var_rec_move = tk.BooleanVar(
            value=self.settings.get("record_mouse_move", False))
        tk.Checkbutton(left,
                       text="Inregistreaza miscari mouse",
                       variable=self._var_rec_move,
                       bg=C["bg_card"], fg=C["text"],
                       selectcolor=C["bg_input"],
                       activebackground=C["bg_card"],
                       activeforeground=C["text"],
                       font=("Segoe UI", 10),
                       command=lambda: self.settings.set(
                           "record_mouse_move", self._var_rec_move.get())
                       ).pack(anchor="w", padx=12, pady=4)

        tk.Label(left, text="⚠ Miscarile genereaza multi pasi",
                 bg=C["bg_card"], fg=C["warning"],
                 font=("Segoe UI", 9)).pack(anchor="w", padx=14)

        tk.Frame(left, bg=C["separator"], height=1).pack(fill="x", padx=8, pady=6)

        # Delay intre pasi
        tk.Label(left, text="Delay intre pasi (sec):",
                 bg=C["bg_card"], fg=C["text_dim"],
                 font=("Segoe UI", 10)).pack(anchor="w", padx=12)
        self._var_delay = tk.DoubleVar(
            value=self.settings.get("step_delay", DEFAULT_STEP_DELAY))
        delay_sl = tk.Scale(left, from_=MIN_STEP_DELAY, to=MAX_STEP_DELAY,
                            resolution=0.05, orient="horizontal",
                            variable=self._var_delay,
                            bg=C["bg_card"], fg=C["text"],
                            troughcolor=C["bg_input"],
                            activebackground=C["primary"],
                            highlightthickness=0, length=200,
                            command=self._on_delay_change)
        delay_sl.pack(padx=12, pady=2)
        self._lbl_delay = tk.Label(left,
                                   text=f"{self._var_delay.get():.1f}s",
                                   bg=C["bg_card"], fg=C["accent"],
                                   font=("Segoe UI", 11, "bold"))
        self._lbl_delay.pack()

        # Viteza redare
        tk.Label(left, text="Viteza redare (x):",
                 bg=C["bg_card"], fg=C["text_dim"],
                 font=("Segoe UI", 10)).pack(anchor="w", padx=12, pady=(6, 0))
        self._var_speed = tk.DoubleVar(
            value=self.settings.get("playback_speed", 1.0))
        speed_sl = tk.Scale(left, from_=0.1, to=5.0,
                            resolution=0.1, orient="horizontal",
                            variable=self._var_speed,
                            bg=C["bg_card"], fg=C["text"],
                            troughcolor=C["bg_input"],
                            activebackground=C["primary"],
                            highlightthickness=0, length=200,
                            command=self._on_speed_change)
        speed_sl.pack(padx=12, pady=2)
        self._lbl_speed = tk.Label(left,
                                   text=f"{self._var_speed.get():.1f}x",
                                   bg=C["bg_card"], fg=C["accent"],
                                   font=("Segoe UI", 11, "bold"))
        self._lbl_speed.pack()

        # Countdown
        tk.Label(left, text="Countdown start (sec):",
                 bg=C["bg_card"], fg=C["text_dim"],
                 font=("Segoe UI", 10)).pack(anchor="w", padx=12, pady=(6, 0))
        self._var_cd = tk.IntVar(
            value=self.settings.get("countdown_before_play", DEFAULT_COUNTDOWN))
        tk.Spinbox(left, from_=0, to=10, textvariable=self._var_cd,
                   width=6, bg=C["bg_input"], fg=C["text"],
                   font=("Segoe UI", 11), relief="flat",
                   buttonbackground=C["bg_card"],
                   insertbackground=C["text"]).pack(anchor="w", padx=12, pady=2)

        tk.Frame(left, bg=C["separator"], height=1).pack(fill="x", padx=8, pady=6)

        # Actiuni rapide
        tk.Label(left, text="Actiuni Rapide:",
                 bg=C["bg_card"], fg=C["text"],
                 font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=12)

        for text, cmd, bg in [
            ("+ Adauga Delay",      self._add_delay_step,      C["bg_input"]),
            ("+ Adauga Pas Manual", self._add_step_manual,     C["bg_input"]),
            ("💾 Salveaza Rutina",  self._save_routine_dialog, C["primary"]),
            ("🗑 Sterge Toti Pasii", self._clear_all_steps,    C["danger"]),
        ]:
            _fg = _btn_fg(bg)
            tk.Button(left, text=text, command=cmd,
                    bg=bg, fg=_fg, activebackground=bg,
                    activeforeground=_fg,
                    font=("Segoe UI", 10), relief="flat",
                    padx=6, pady=4, cursor="hand2"
                    ).pack(fill="x", padx=8, pady=2)

        # ── Panou dreapta: Pasi ───────────────────────────────────
        right = tk.Frame(parent, bg=C["bg_main"])
        right.pack(side="left", fill="both", expand=True,
                   padx=(3, 6), pady=6)

        # Header
        hdr = tk.Frame(right, bg=C["bg_card"], height=38)
        hdr.pack(fill="x", pady=(0, 4))
        hdr.pack_propagate(False)
        tk.Label(hdr, text="📋  Pasi Inregistrati",
                 bg=C["bg_card"], fg=C["primary"],
                 font=("Segoe UI", 12, "bold")).pack(side="left", padx=10, pady=8)
        self._lbl_step_count = tk.Label(hdr,
                                        textvariable=self._step_count_var,
                                        bg=C["bg_card"], fg=C["accent"],
                                        font=("Segoe UI", 11))
        self._lbl_step_count.pack(side="right", padx=10)

        # Avertizare prea multi pasi
        self._lbl_warn = tk.Label(right,
                                  text=f"⚠ Rutina are prea multi pasi (>{MAX_STEPS_WARNING}). Considera simplificarea!",
                                  bg=C["bg_main"], fg=C["warning"],
                                  font=("Segoe UI", 10))

        # Bara de actiuni pe pasi (deasupra treeview)
        act_bar = tk.Frame(right, bg=C["bg_main"])
        act_bar.pack(fill="x", pady=(0, 2))

        for text, cmd, bg in [
            ("▲ Sus",         self._move_step_up,          C["bg_input"]),
            ("▼ Jos",         self._move_step_down,        C["bg_input"]),
            ("✏ Editeaza",    self._edit_selected_step,    C["primary"]),
            ("⊘ Skip/Unskip",     self._toggle_skip_selected,  C["warning"]),
            ("🐛 Debug Pas",   self._rec_debug_step,        C["accent"]),
            ("🔍 Simuleaza",   self._rec_simulate_step,     "#6A5ACD"),
            ("🗑 Sterge",      self._delete_selected_steps, C["danger"]),
        ]:
            _fg = _btn_fg(bg)
            tk.Button(act_bar, text=text, command=cmd,
                    bg=bg, fg=_fg, activebackground=bg,
                    activeforeground=_fg,
                    font=("Segoe UI", 10), relief="flat",
                    padx=8, pady=3, cursor="hand2"
                    ).pack(side="left", padx=2)

        # Treeview pasi cu selectie multipla
        tree_frame = tk.Frame(right, bg=C["bg_card"])
        tree_frame.pack(fill="both", expand=True)

        vsb = ttk.Scrollbar(tree_frame, orient="vertical")
        vsb.pack(side="right", fill="y")

        cols = [
            ("id",    "#",         50,  "center", False),
            ("tip",   "Tip",       90,  "center", False),
            ("desc",  "Descriere", 400, "w",      True),
            ("delay", "Delay (s)", 80,  "center", False),
            ("skip",  "Sarit",     60,  "center", False),
            ("ts",    "Timestamp", 90,  "center", False),
        ]
        self._steps_tv = make_treeview(tree_frame, cols, "Steps",
                                       row_height=28, font_size=11,
                                       multi_select=True)
        self._steps_tv.configure(yscrollcommand=vsb.set)
        vsb.configure(command=self._steps_tv.yview)
        self._steps_tv.pack(fill="both", expand=True, padx=2, pady=2)

        # Bindings treeview
        self._steps_tv.bind("<Button-3>",        self._on_step_rclick)
        self._steps_tv.bind("<Double-Button-1>",  self._on_step_dclick)
        self._steps_tv.bind("<Delete>",           lambda e: self._delete_selected_steps())
        

    def _rec_simulate_step(self):
        """[v3.9] Simuleaza un pas: muta mouse-ul la pozitie si afiseaza
        un chenar mic pe ecran cu ce ar face, fara executie reala.
        Chenarul dispare dupa delay-ul inregistrat al pasului.
        """
        sel = self._steps_tv.selection()
        if not sel or len(sel) != 1:
            messagebox.showwarning("Simulare", "Selecteaza exact UN pas pentru simulare.")
            return
        step_id = int(sel[0])
        step    = next((s for s in self.recorder.get_steps()
                        if s.step_id == step_id), None)
        if not step:
            return

        # ── Eticheta scurta pentru chenar ────────────────────────────
        label_map = {
            "CLICK":       "CLICK",
            "RCLICK":      "RIGHT CLICK",
            "RIGHTCLICK":  "RIGHT CLICK",
            "DCLICK":      "DOUBLE CLICK",
            "TYPE":        "TYPE: %s" % (step.text_input or "")[:30],
            "KEY":         "KEY: %s" % (step.key_combo or ""),
            "HOTKEY":      "HOTKEY: %s" % (step.key_combo or ""),
            "SCROLL":      "SCROLL",
            "WAIT":        "WAIT %.2fs" % step.delay_before,
            "DRAG":        "DRAG -> (%d, %d)" % (
                            getattr(step, "drag_x", 0),
                            getattr(step, "drag_y", 0)),
        }
        label_text = label_map.get(step.step_type.upper(), step.step_type)

        # ── Delay de afisare: cel putin 1s, maxim 5s ─────────────────
        delay_ms = max(1000, min(int(step.delay_before * 1000), 5000))

        # ── Muta mouse-ul la pozitia inregistrata (fara click) ───────
        target_x = step.x or 0
        target_y = step.y or 0
        has_pos  = step.step_type.upper() not in ("TYPE", "KEY", "HOTKEY", "WAIT")

        if has_pos and (target_x > 0 or target_y > 0):
            try:
                import pyautogui
                pyautogui.moveTo(target_x, target_y, duration=0.3)
            except Exception:
                pass

        # ── Chenar mic pe ecran langa pozitia mouse-ului ─────────────
        overlay = tk.Toplevel(self.root)
        overlay.overrideredirect(True)
        overlay.attributes("-topmost", True)
        overlay.attributes("-alpha", 0.92)
        overlay.configure(bg="#1A1A2E")

        # Padding si font
        lbl = tk.Label(
            overlay,
            text=label_text,
            bg="#1A1A2E", fg="#FFFFFF",
            font=("Segoe UI", 11, "bold"),
            padx=14, pady=8,
            relief="flat"
        )
        lbl.pack()

        # Chenar colorat in functie de tip
        border_color = {
            "CLICK":       "#00BFFF",
            "RCLICK":      "#FF6B35",
            "RIGHTCLICK":  "#FF6B35",
            "DCLICK":      "#FFD700",
            "TYPE":        "#32CD32",
            "KEY":         "#32CD32",
            "HOTKEY":      "#32CD32",
            "SCROLL":      "#DA70D6",
            "WAIT":        "#808080",
            "DRAG":        "#FF8C00",
        }.get(step.step_type.upper(), "#6A5ACD")
        overlay.configure(highlightbackground=border_color,
                          highlightthickness=2,
                          highlightcolor=border_color)

        # Pozitionare: langa mouse, usor offset
        overlay.update_idletasks()
        w = overlay.winfo_reqwidth()
        h = overlay.winfo_reqheight()
        if has_pos and (target_x > 0 or target_y > 0):
            px = target_x + 18
            py = target_y - h - 8
            # Asigura ca nu iese din ecran
            sw = overlay.winfo_screenwidth()
            sh = overlay.winfo_screenheight()
            if px + w > sw:
                px = target_x - w - 18
            if py < 0:
                py = target_y + 18
        else:
            # Fara pozitie mouse - centru ecran
            sw = overlay.winfo_screenwidth()
            sh = overlay.winfo_screenheight()
            px = (sw - w) // 2
            py = (sh - h) // 2
        overlay.geometry("+%d+%d" % (px, py))

        # Dispare automat dupa delay
        overlay.after(delay_ms, overlay.destroy)
        # [v3.9] SIMULATION indicator
        try:
            self.mode_indicator.show("simulation")
            self.root.after(delay_ms, lambda: self.mode_indicator.hide())
        except Exception:
            pass

    # ==========================================================================
    # SECTIUNEA 14.E: TAB STEP BUILDER
    # ==========================================================================

    def _build_tab_builder(self):
        """
        Construieste tab-ul Step Builder — creare manuala a rutinei pas cu pas.
        Fiecare pas are optiuni complete: tip, coordonate, taste, delay, etc.
        """
        parent = self._tab_builder

        # ── Header ──
        hdr = tk.Frame(parent, bg=C["bg_card"], height=44)
        hdr.pack(fill="x", padx=6, pady=(6, 0))
        hdr.pack_propagate(False)
        tk.Label(hdr, text="🔧  Step Builder — Creare Rutina Manuala",
                 bg=C["bg_card"], fg=C["primary"],
                 font=("Segoe UI", 13, "bold")).pack(side="left", padx=12, pady=10)
        tk.Label(hdr,
                 text="Adauga pasi individuali cu optiuni complete | Dublu-click pentru editare",
                 bg=C["bg_card"], fg=C["text_dim"],
                 font=("Segoe UI", 10)).pack(side="right", padx=12)

        # ── Bara de actiuni ──
        act = tk.Frame(parent, bg=C["bg_main"])
        act.pack(fill="x", padx=6, pady=4)

        for text, cmd, bg in [
            ("➕ Adauga Pas",       self._builder_add_step,      C["success"]),
            ("✏ Editeaza Selectat", self._builder_edit_step,     C["primary"]),
            ("▲ Muta Sus",          self._builder_move_up,       C["bg_input"]),
            ("▼ Muta Jos",          self._builder_move_down,     C["bg_input"]),
            ("⊘ Skip/Unskip",       self._builder_toggle_skip,   C["warning"]),
            ("🐛 Debug Pas",         self._builder_debug_step,    C["accent"]),
            ("🗑 Sterge Selectat",   self._builder_delete_step,   C["danger"]),
            ("🗑🗑 Sterge Tot",       self._builder_clear_all,     C["danger"]),
            ("💾 Salveaza Rutina",   self._save_routine_dialog,   C["primary"]),
            ("▶ Ruleaza Rutina",    self._start_playback,         C["success"]),
        ]:
            _fg = _btn_fg(bg)
            tk.Button(act, text=text, command=cmd,
                    bg=bg, fg=_fg, activebackground=bg,
                    activeforeground=_fg,
                    font=("Segoe UI", 10), relief="flat",
                    padx=8, pady=4, cursor="hand2"
                    ).pack(side="left", padx=2)

        # ── Treeview pasi builder ──
        tree_f = tk.Frame(parent, bg=C["bg_card"])
        tree_f.pack(fill="both", expand=True, padx=6, pady=(0, 6))

        vsb = ttk.Scrollbar(tree_f, orient="vertical")
        vsb.pack(side="right", fill="y")

        cols = [
            ("id",    "#",            50,  "center", False),
            ("tip",   "Tip",          100, "center", False),
            ("desc",  "Descriere",    320, "w",      True),
            ("x",     "X",            60,  "center", False),
            ("y",     "Y",            60,  "center", False),
            ("key",   "Tasta/Text",   120, "w",      False),
            ("delay", "Delay (s)",    80,  "center", False),
            ("skip",  "Sarit",        60,  "center", False),
            ("com",   "Comentariu",   140, "w",      False),
        ]
        self._builder_tv = make_treeview(tree_f, cols, "Builder",
                                         row_height=30, font_size=11,
                                         multi_select=True)
        self._builder_tv.configure(yscrollcommand=vsb.set)
        vsb.configure(command=self._builder_tv.yview)
        self._builder_tv.pack(fill="both", expand=True, padx=2, pady=2)

        self._builder_tv.bind("<Double-Button-1>", lambda e: self._builder_edit_step())
        self._builder_tv.bind("<Delete>",          lambda e: self._builder_delete_step())
        self._builder_tv.bind("<Button-3>",        self._builder_rclick)

        # ── Bara de status builder ──
        self._lbl_builder_count = tk.Label(parent,
                                           text="Pasi in builder: 0",
                                           bg=C["bg_main"], fg=C["accent"],
                                           font=("Segoe UI", 10))
        self._lbl_builder_count.pack(anchor="w", padx=8, pady=2)

    # ==========================================================================
    # SECTIUNEA 14.F: TAB LOG
    # ==========================================================================

    def _build_tab_log(self):
        """Construieste tab-ul de log cu filtre si export."""
        parent = self._tab_log

        # ── Bara filtre + export ──
        top = tk.Frame(parent, bg=C["bg_card"], height=48)
        top.pack(fill="x", padx=6, pady=(6, 3))
        top.pack_propagate(False)

        tk.Label(top, text="Filtru:", bg=C["bg_card"], fg=C["text"],
                font=("Segoe UI", 11)).pack(side="left", padx=8, pady=12)
        self._log_filter = tk.StringVar()
        tk.Entry(top, textvariable=self._log_filter,
                bg=C["bg_input"], fg=C["text"],
                font=("Segoe UI", 11), relief="flat",
                insertbackground=C["text"],
                width=22).pack(side="left", padx=4)

        tk.Button(top, text="Filtreaza", command=self._filter_log,
                bg=C["primary"], fg=_btn_fg(C["primary"]), relief="flat",
                font=("Segoe UI", 10), padx=8, pady=3,
                cursor="hand2").pack(side="left", padx=2)

        tk.Button(top, text="Reset", command=self._reset_log_filter,
                bg=C["bg_input"], fg=_btn_fg(C["bg_input"]), relief="flat",
                font=("Segoe UI", 10), padx=8, pady=3,
                cursor="hand2").pack(side="left", padx=2)

        # Butoane export (dreapta)
        for text, cmd, bg in [
            ("📥 XLSX",   self._export_log_xlsx, C["success"]),
            ("📥 CSV",    self._export_log_csv,  C["bg_input"]),
            ("📥 JSON",   self._export_log_json, C["bg_input"]),
            ("🗑 Sterge", self._clear_log,       C["danger"]),
        ]:
            _fg = _btn_fg(bg)
            tk.Button(top, text=text, command=cmd,
                    bg=bg, fg=_fg, relief="flat",
                    font=("Segoe UI", 10), padx=8, pady=3,
                    cursor="hand2").pack(side="right", padx=2)

        # ── Treeview log ──
        log_f = tk.Frame(parent, bg=C["bg_card"])
        log_f.pack(fill="both", expand=True, padx=6, pady=(0, 6))

        vsb = ttk.Scrollbar(log_f, orient="vertical")
        vsb.pack(side="right", fill="y")
        hsb = ttk.Scrollbar(log_f, orient="horizontal")
        hsb.pack(side="bottom", fill="x")

        cols = [
            ("id",    "#",           50,  "center", False),
            ("ts",    "Timestamp",   160, "center", False),
            ("step",  "Pas",         50,  "center", False),
            ("act",   "Actiune",     300, "w",      True),
            ("res",   "Rezultat",    80,  "center", False),
            ("err",   "Eroare",      60,  "center", False),
            ("emsg",  "Mesaj Eroare",200, "w",      False),
            ("com",   "Comentariu",  150, "w",      False),
            ("dur",   "Durata(ms)",  90,  "center", False),
            ("iter",  "Iteratie",    70,  "center", False),
        ]
        self._log_tv = make_treeview(log_f, cols, "Log",
                                     row_height=24, font_size=10)
        self._log_tv.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        vsb.configure(command=self._log_tv.yview)
        hsb.configure(command=self._log_tv.xview)
        self._log_tv.pack(fill="both", expand=True, padx=2, pady=2)

        self._log_tv.bind("<Button-3>", self._log_rclick)

    # ==========================================================================
    # SECTIUNEA 14.G: TAB RUTINE
    # ==========================================================================

    def _build_tab_routines(self):
        """Construieste tab-ul de rutine salvate."""
        parent = self._tab_routines

        # ── Bara actiuni ──
        act = tk.Frame(parent, bg=C["bg_card"], height=48)
        act.pack(fill="x", padx=6, pady=(6, 3))
        act.pack_propagate(False)

        for text, cmd, bg in [
            ("🔄 Reincarca",   self._refresh_routines,      C["primary"]),
            ("📂 Incarca",     self._load_selected_routine, C["success"]),
            ("✏ Redenumeste", self._rename_routine,         C["bg_input"]),
            ("🗑 Sterge",      self._delete_routine,        C["danger"]),
        ]:
            _fg = _btn_fg(bg)
            tk.Button(act, text=text, command=cmd,
                    bg=bg, fg=_fg, relief="flat",
                    font=("Segoe UI", 11), padx=10, pady=6,
                    cursor="hand2").pack(side="left", padx=4, pady=8)

        # Cautare
        tk.Label(act, text="Cauta:", bg=C["bg_card"], fg=C["text"],
                 font=("Segoe UI", 11)).pack(side="right", padx=(0, 4))
        self._routine_search = tk.StringVar()
        self._routine_search.trace_add("write", lambda *_: self._refresh_routines())
        tk.Entry(act, textvariable=self._routine_search,
                 bg=C["bg_input"], fg=C["text"],
                 font=("Segoe UI", 11), relief="flat",
                 insertbackground=C["text"],
                 width=20).pack(side="right", padx=4)

        # ── Treeview rutine ──
        rt_f = tk.Frame(parent, bg=C["bg_card"])
        rt_f.pack(fill="both", expand=True, padx=6, pady=(0, 6))

        vsb = ttk.Scrollbar(rt_f, orient="vertical")
        vsb.pack(side="right", fill="y")

        cols = [
            ("name",  "Nume Rutina",  220, "w",      True),
            ("steps", "Nr. Pasi",     80,  "center", False),
            ("date",  "Data Creare",  160, "center", False),
            ("desc",  "Descriere",    300, "w",      True),
        ]
        self._routines_tv = make_treeview(rt_f, cols, "Routines",
                                          row_height=30, font_size=11)
        self._routines_tv.configure(yscrollcommand=vsb.set)
        vsb.configure(command=self._routines_tv.yview)
        self._routines_tv.pack(fill="both", expand=True, padx=2, pady=2)

        self._routines_tv.bind("<Double-Button-1>",
                               lambda e: self._load_selected_routine())

        self.root.after(200, self._refresh_routines)

    # ==========================================================================
    # SECTIUNEA 14.H: TAB EXCEL
    # ==========================================================================

    def _build_tab_excel(self):
        """Construieste tab-ul de executie data-driven din Excel."""
        parent = self._tab_excel

        # Scroll canvas
        canvas = tk.Canvas(parent, bg=C["bg_main"], highlightthickness=0)
        vsb    = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        canvas.pack(fill="both", expand=True)
        bind_scroll(canvas, canvas)

        inner = tk.Frame(canvas, bg=C["bg_main"])
        cw = canvas.create_window((0, 0), window=inner, anchor="nw")
        inner.bind("<Configure>", lambda e: canvas.configure(
            scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

        def section(title):
            tk.Label(inner, text=title, bg=C["bg_main"], fg=C["primary"],
                     font=("Segoe UI", 12, "bold")).pack(
                         anchor="w", padx=12, pady=(12, 2))
            f = tk.Frame(inner, bg=C["bg_card"], relief="flat")
            f.pack(fill="x", padx=8, pady=2)
            return f

        def row(f, label, widget_fn):
            r = tk.Frame(f, bg=C["bg_card"])
            r.pack(fill="x", padx=12, pady=4)
            tk.Label(r, text=label, bg=C["bg_card"], fg=C["text_dim"],
                     font=("Segoe UI", 11), width=24, anchor="w").pack(side="left")
            widget_fn(r)

        tk.Label(inner, text="📊  Executie Data-Driven din Excel",
                 bg=C["bg_main"], fg=C["primary"],
                 font=("Segoe UI", 14, "bold")).pack(pady=(12, 4))

        # Fisier Excel
        f1 = section("Fisier Excel")
        self._excel_path = tk.StringVar()
        row(f1, "Fisier Excel:", lambda p: (
            tk.Entry(p, textvariable=self._excel_path,
                     bg=C["bg_input"], fg=C["text"],
                     font=("Segoe UI", 11), relief="flat",
                     insertbackground=C["text"],
                     width=35).pack(side="left", padx=(0, 6)),
            tk.Button(p, text="Browse", command=self._browse_excel,
                      bg=C["primary"], fg="white", relief="flat",
                      font=("Segoe UI", 10), padx=8, pady=2,
                      cursor="hand2").pack(side="left")
        ))

        # Sheet si interval
        f2 = section("Date")
        self._excel_sheet = tk.StringVar()
        self._excel_sheet_cb = None
        row(f2, "Sheet:", lambda p: self._make_excel_sheet_cb(p))
        self._excel_range = tk.StringVar(value="A1:A100")
        row(f2, "Interval (ex: A1:A100):", lambda p: tk.Entry(
            p, textvariable=self._excel_range,
            bg=C["bg_input"], fg=C["text"],
            font=("Segoe UI", 11), relief="flat",
            insertbackground=C["text"], width=16).pack(side="left"))

        # Buton rulare
        tk.Button(inner, text="▶  Ruleaza Rutina pe Date Excel",
                  command=self._run_excel_driven,
                  bg=C["success"], fg="white", relief="flat",
                  font=("Segoe UI", 13, "bold"), padx=20, pady=8,
                  cursor="hand2").pack(fill="x", padx=8, pady=12)

        # Progress
        self._excel_prog_var = tk.DoubleVar(value=0)
        self._excel_prog = ttk.Progressbar(inner, variable=self._excel_prog_var,
                                           maximum=100, length=400)
        self._excel_prog.pack(fill="x", padx=8, pady=4)
        self._lbl_excel_st = tk.Label(inner, text="",
                                      bg=C["bg_main"], fg=C["accent"],
                                      font=("Segoe UI", 11))
        self._lbl_excel_st.pack(pady=4)

    def _make_excel_sheet_cb(self, parent):
        """Creeaza combobox pentru selectia sheet-ului Excel."""
        self._excel_sheet_cb = ttk.Combobox(parent,
                                             textvariable=self._excel_sheet,
                                             values=[], state="readonly",
                                             width=20, font=("Segoe UI", 11))
        self._excel_sheet_cb.pack(side="left")

    # ==========================================================================
    # SECTIUNEA 14.I: TAB NOTITE
    # ==========================================================================

    def _build_tab_notes(self):
        """Construieste tab-ul de notite cu editor text."""
        parent = self._tab_notes

        # Toolbar
        tb = tk.Frame(parent, bg=C["bg_card"], height=44)
        tb.pack(fill="x", padx=6, pady=(6, 3))
        tb.pack_propagate(False)

        for text, cmd, bg in [
            ("• Bullet",     self._note_bullet,     C["bg_input"]),
            ("1. Lista",     self._note_numbered,   C["bg_input"]),
            ("─ Linie",      self._note_separator,  C["bg_input"]),
            ("💾 Salveaza",  self._save_notes,       C["primary"]),
            ("📂 Incarca",   self._load_notes,       C["bg_input"]),
            ("🗑 Sterge",    self._clear_notes,      C["danger"]),
        ]:
            _fg = _btn_fg(bg)
            tk.Button(tb, text=text, command=cmd,
                    bg=bg, fg=_fg, relief="flat",
                    font=("Segoe UI", 10), padx=8, pady=4,
                    cursor="hand2").pack(side="left", padx=3, pady=8)

        # Text area
        txt_f = tk.Frame(parent, bg=C["bg_card"])
        txt_f.pack(fill="both", expand=True, padx=6, pady=(0, 6))

        vsb = ttk.Scrollbar(txt_f, orient="vertical")
        vsb.pack(side="right", fill="y")

        self._notes_txt = tk.Text(txt_f,
                                  bg=C["bg_card"], fg=C["text"],
                                  font=("Segoe UI", 12),
                                  insertbackground=C["text"],
                                  relief="flat", wrap="word",
                                  yscrollcommand=vsb.set,
                                  padx=8, pady=8)
        vsb.configure(command=self._notes_txt.yview)
        self._notes_txt.pack(fill="both", expand=True)
        bind_scroll(self._notes_txt)

        self._load_notes()

    # ==========================================================================
    # SECTIUNEA 14.J: TAB SETARI
    # ==========================================================================

    def _build_tab_settings(self):
        """Construieste tab-ul de setari cu toate optiunile."""
        parent = self._tab_settings

        canvas = tk.Canvas(parent, bg=C["bg_main"], highlightthickness=0)
        vsb    = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        canvas.pack(fill="both", expand=True)
        bind_scroll(canvas, canvas)

        inner = tk.Frame(canvas, bg=C["bg_main"]) # 1. Creare inner
        cw = canvas.create_window((0, 0), window=inner, anchor="nw")
        inner.bind("<Configure>", lambda e: canvas.configure(
            scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

        # Scroll cu rotita cand mouse-ul e deasupra continutului interior
        inner.bind("<Enter>", lambda e: bind_scroll(inner, canvas), add="+") # 2. Binding DUPĂ inner

        tk.Label(inner, text="⚙  Setari Aplicatie",
                 bg=C["bg_main"], fg=C["primary"],
                 font=("Segoe UI", 14, "bold")).pack(pady=(12, 4))

        def section(title):
            tk.Label(inner, text=title, bg=C["bg_main"], fg=C["primary"],
                     font=("Segoe UI", 12, "bold")).pack(
                         anchor="w", padx=12, pady=(10, 2))
            f = tk.Frame(inner, bg=C["bg_card"])
            f.pack(fill="x", padx=8, pady=2)
            return f

        def row(f, label, widget_fn):
            r = tk.Frame(f, bg=C["bg_card"])
            r.pack(fill="x", padx=12, pady=4)
            tk.Label(r, text=label, bg=C["bg_card"], fg=C["text_dim"],
                     font=("Segoe UI", 11), width=28, anchor="w").pack(side="left")
            widget_fn(r)

        # ── Redare ──
        f_play = section("▶  Redare")
        row(f_play, "Delay intre pasi (sec):", lambda p: tk.Entry(
            p, textvariable=self._var_delay, width=10,
            bg=C["bg_input"], fg=C["text"], font=("Segoe UI", 11),
            relief="flat", insertbackground=C["text"]).pack(side="left"))
        row(f_play, "Viteza redare (x):", lambda p: tk.Entry(
            p, textvariable=self._var_speed, width=10,
            bg=C["bg_input"], fg=C["text"], font=("Segoe UI", 11),
            relief="flat", insertbackground=C["text"]).pack(side="left"))
        row(f_play, "Countdown inainte de start (sec):", lambda p: tk.Spinbox(
            p, from_=0, to=10, textvariable=self._var_cd, width=8,
            bg=C["bg_input"], fg=C["text"], font=("Segoe UI", 11),
            relief="flat", buttonbackground=C["bg_card"],
            insertbackground=C["text"]).pack(side="left"))
        row(f_play, "Numar repetari implicit:", lambda p: tk.Spinbox(
            p, from_=1, to=9999, textvariable=self._repeat_var, width=8,
            bg=C["bg_input"], fg=C["text"], font=("Segoe UI", 11),
            relief="flat", buttonbackground=C["bg_card"],
            insertbackground=C["text"]).pack(side="left"))

        # ── Inregistrare ──
        f_rec = section("⏺  Inregistrare")
        row(f_rec, "Inregistreaza miscari mouse:", lambda p: tk.Checkbutton(
            p, variable=self._var_rec_move,
            bg=C["bg_card"], selectcolor=C["bg_input"],
            activebackground=C["bg_card"]).pack(side="left"))
        row(f_rec, "Threshold miscare mouse (px):", lambda p: tk.Spinbox(
            p, from_=1, to=50, width=8,
            bg=C["bg_input"], fg=C["text"], font=("Segoe UI", 11),
            relief="flat", buttonbackground=C["bg_card"],
            insertbackground=C["text"]).pack(side="left"))

        # ── v4.1: Siguranta la rulare ──
        f_safe = section("🛡  Siguranta la rulare")
        self._var_dnd = tk.BooleanVar(value=bool(self.settings.get("dnd_during_run", True)))
        self._var_frame = tk.BooleanVar(value=bool(self.settings.get("show_run_frame", True)))
        self._var_guard = tk.BooleanVar(value=bool(self.settings.get("guard_enabled", True)))
        self._var_guard_sens = tk.StringVar(value=str(self.settings.get("guard_sensitivity", "normal")))
        for text, var in [
            ("🌙 Nu deranja (fara notificari Windows) cat timp ruleaza / inregistreaza", self._var_dnd),
            ("🟥 Chenar pe ecran: rosu + RUN la rulare, verde + REC la inregistrare", self._var_frame),
            ("🛡 Sistem de preventie: pauza + intrebare cand ecranul difera", self._var_guard),
        ]:
            tk.Checkbutton(f_safe, text=text, variable=var, bg=C["bg_card"], fg=C["text"],
                           selectcolor=C["bg_input"], activebackground=C["bg_card"],
                           activeforeground=C["text"], font=("Segoe UI", 11),
                           anchor="w").pack(fill="x", padx=12, pady=2)
        def _force_notifications_on():
            self._status_var.set("Repornesc notificarile Windows...")
            def work():
                DoNotDisturb.force_off()
                self.root.after(0, lambda: messagebox.showinfo("Nu deranja", DoNotDisturb.last_message))
            threading.Thread(target=work, daemon=True).start()
        row(f_safe, "Notificari ramase oprite?", lambda p: tk.Button(
            p, text="🔔 Reporneste notificarile acum", command=_force_notifications_on,
            bg=C["bg_input"], fg=C["text"], relief="flat", font=("Segoe UI", 10), padx=8,
            cursor="hand2").pack(side="left"))
        row(f_safe, "Sensibilitate preventie:", lambda p: ttk.Combobox(
            p, textvariable=self._var_guard_sens, values=["relaxed", "normal", "strict"],
            state="readonly", width=12).pack(side="left"))
        tk.Label(f_safe, text=("Verifica inainte de fiecare pas: mouse miscat de tine, ferestre de eroare, "
                               "aplicatie care nu raspunde, click in alta aplicatie, zona click-ului diferita "
                               "(relaxed 35% · normal 22% · strict 12%), taste trimise in alta fereastra. "
                               "Un pas esuat nu mai e sarit in tacere: rutina se opreste si te intreaba. "
                               "Verificarea ecranului functioneaza pentru pasii inregistrati cu versiunea 4.1+."),
                 bg=C["bg_card"], fg=C["text_dim"], font=("Segoe UI", 9), wraplength=720,
                 justify="left").pack(anchor="w", padx=12, pady=(2, 8))

        # ── Shortcut-uri ──
        f_sc = section("⌨  Shortcut-uri")
        sc = self.settings.get("shortcuts", DEFAULT_SHORTCUTS)
        self._sc_vars: Dict[str, tk.StringVar] = {}
        sc_labels = {
            "start_rec":  "Start Inregistrare:",
            "stop_rec":   "Stop Inregistrare:",
            "play":       "Ruleaza Rutina:",
            "pause":      "Pauza:",
            "stop_play":  "Stop Redare:",
            "emergency":  "Stop Urgenta:",
            "save":       "Salveaza Rutina:",
        }
        for key, label in sc_labels.items():
            var = tk.StringVar(value=sc.get(key, DEFAULT_SHORTCUTS.get(key, "")))
            self._sc_vars[key] = var
            row(f_sc, label, lambda p, v=var: tk.Entry(
                p, textvariable=v, width=14,
                bg=C["bg_input"], fg=C["text"], font=("Segoe UI", 11),
                relief="flat", insertbackground=C["text"]).pack(side="left"))

        # ── v4.1: Pornire si tray ──
        f_start = section("🪟  Pornire si zona de notificari (tray)")
        tray_ok = app_shell.tray_available()
        self._var_autostart = tk.BooleanVar(value=app_shell.is_autostart_enabled())
        self._var_start_tray = tk.BooleanVar(value=bool(self.settings.get("start_minimized_tray", True)))
        self._var_close_tray = tk.BooleanVar(value=bool(self.settings.get("close_to_tray", False)))

        def _apply_autostart():
            self.settings.set("start_minimized_tray", bool(self._var_start_tray.get()))
            ok, msg = app_shell.set_autostart(bool(self._var_autostart.get()), bool(self._var_start_tray.get()))
            self._status_var.set(msg)
            if not ok:
                messagebox.showwarning("Pornire cu Windows", msg)
                self._var_autostart.set(app_shell.is_autostart_enabled())

        def _apply_close_tray():
            self.settings.set("close_to_tray", bool(self._var_close_tray.get()))
            self._status_var.set("Butonul ✕ ascunde aplicatia langa ceas." if self._var_close_tray.get()
                                 else "Butonul ✕ inchide aplicatia.")

        for text, var, cmd, needs_tray in [
            ("Porneste AutoPilot DC automat cu Windows", self._var_autostart, _apply_autostart, False),
            ("   ... si porneste ascuns in tray (fara fereastra, doar pictograma langa ceas)",
             self._var_start_tray, _apply_autostart, True),
            ("Butonul ✕ ascunde aplicatia in tray (nu o inchide); Iesire din meniul pictogramei",
             self._var_close_tray, _apply_close_tray, True),
        ]:
            tk.Checkbutton(f_start, text=text, variable=var, command=cmd, bg=C["bg_card"], fg=C["text"],
                           selectcolor=C["bg_input"], activebackground=C["bg_card"], activeforeground=C["text"],
                           font=("Segoe UI", 11), anchor="w",
                           state="normal" if (tray_ok or not needs_tray) else "disabled").pack(fill="x", padx=12, pady=2)
        tk.Label(f_start, text=("Setarile se aplica imediat. Pornirea cu Windows foloseste contul tau (fara drepturi de "
                                "administrator). Din tray: click = deschide; click dreapta = Recorder, Studio, "
                                "STOP URGENTA, Iesire." if tray_ok else
                                "Pentru tray lipseste pachetul pystray: ruleaza INSTALEAZA.bat."),
                 bg=C["bg_card"], fg=C["text_dim"] if tray_ok else C["warning"], font=("Segoe UI", 9),
                 wraplength=720, justify="left").pack(anchor="w", padx=12, pady=(2, 8))
        def _make_shortcut():
            ok, msg = app_shell.create_shortcut()
            (messagebox.showinfo if ok else messagebox.showwarning)("Scurtatura", msg)
        tk.Button(f_start, text="🖥  Creeaza scurtatura pe Desktop (porneste fara fereastra CMD)",
                  command=_make_shortcut, bg=C["bg_input"], fg=C["text"], relief="flat", font=("Segoe UI", 10),
                  padx=8, pady=3, cursor="hand2").pack(anchor="w", padx=12, pady=(0, 8))

        # ── Tema ──
        f_theme = section("🎨  Tema")
        self._var_theme = tk.StringVar(value=self.settings.get("theme", "dark"))
        row(f_theme, "Tema interfata:", lambda p: (
            tk.Radiobutton(p, text="Dark", variable=self._var_theme,
                           value="dark", bg=C["bg_card"], fg=C["text"],
                           selectcolor=C["bg_input"],
                           activebackground=C["bg_card"],
                           font=("Segoe UI", 11)).pack(side="left", padx=4),
            tk.Radiobutton(p, text="Light", variable=self._var_theme,
                           value="light", bg=C["bg_card"], fg=C["text"],
                           selectcolor=C["bg_input"],
                           activebackground=C["bg_card"],
                           font=("Segoe UI", 11)).pack(side="left", padx=4),
        ))

        # ── Locatie fisiere ──
        f_loc = section("📁  Locatie Fisiere")
        for label, path in [
            ("Rutine:", ROUTINES_DIR),
            ("Loguri:", LOGS_DIR),
            ("Notite:", NOTES_DIR),
        ]:
            r = tk.Frame(f_loc, bg=C["bg_card"])
            r.pack(fill="x", padx=12, pady=3)
            tk.Label(r, text=label, bg=C["bg_card"], fg=C["text_dim"],
                     font=("Segoe UI", 11), width=10, anchor="w").pack(side="left")
            tk.Label(r, text=str(path), bg=C["bg_card"], fg=C["accent"],
                     font=("Segoe UI", 10)).pack(side="left")
        tk.Button(f_loc, text="📂 Deschide Folder",
                  command=lambda: os.startfile(str(BASE_DIR)),
                  bg=C["primary"], fg="white", relief="flat",
                  font=("Segoe UI", 10), padx=8, pady=3,
                  cursor="hand2").pack(anchor="w", padx=12, pady=(4, 8))

        # ── Buton Salveaza ──
        tk.Frame(inner, bg=C["separator"], height=1).pack(fill="x", padx=8, pady=8)
        tk.Button(inner, text="💾  Salveaza Setarile",
                  command=self._save_settings,
                  bg=C["primary"], fg="white", relief="flat",
                  font=("Segoe UI", 13, "bold"), padx=20, pady=8,
                  cursor="hand2").pack(pady=12)

    # ==========================================================================
    # SECTIUNEA 14.K: TAB AJUTOR
    # ==========================================================================

    def _build_tab_help(self):
        """Construieste tab-ul de ajutor."""
        parent = self._tab_help

        txt_f = tk.Frame(parent, bg=C["bg_card"])
        txt_f.pack(fill="both", expand=True, padx=6, pady=6)

        vsb = ttk.Scrollbar(txt_f, orient="vertical")
        vsb.pack(side="right", fill="y")

        help_txt = tk.Text(txt_f, bg=C["bg_card"], fg=C["text"],
                           font=("Consolas", 11), relief="flat",
                           wrap="word", padx=12, pady=12,
                           yscrollcommand=vsb.set)
        vsb.configure(command=help_txt.yview)
        help_txt.pack(fill="both", expand=True)
        bind_scroll(help_txt)

        sc = self.settings.get("shortcuts", DEFAULT_SHORTCUTS)
        content = f"""
{APP_NAME} v{APP_VERSION} — Ghid de Utilizare
{'='*65}

AUTOR: {APP_AUTHOR}
Realizat cu ajutorul unui asistent AI (SiemensGPT - Claude Sonnet 4.6)

{'─'*65}
DESCRIERE:
AutoPilot DC este un tool RPA (Robotic Process Automation) care permite
automatizarea task-urilor repetitive prin inregistrarea si redarea
gesturilor mouse si tastatura.

{'─'*65}
SHORTCUT-URI:
  {sc.get('start_rec','F5'):<12} — Start Inregistrare
  {sc.get('stop_rec','F6'):<12} — Stop Inregistrare
  {sc.get('play','F7'):<12} — Ruleaza Rutina
  {sc.get('pause','F8'):<12} — Pauza / Reia
  {sc.get('stop_play','F9'):<12} — Stop Redare
  {sc.get('emergency','F12'):<12} — STOP URGENTA
  Ctrl+S      — Salveaza Rutina
  Ctrl+N      — Rutina Noua
  Ctrl+O      — Deschide Rutina
  Delete      — Sterge Pasii Selectati

{'─'*65}
CUM SE FOLOSESTE:

1. INREGISTRARE AUTOMATA (Tab Recorder):
   • Apasa "Inregistreaza" sau {sc.get('start_rec','F5')}
   • Efectueaza actiunile dorite pe ecran
   • Apasa "Stop Rec" sau {sc.get('stop_rec','F6')} pentru a opri
   • Pasii apar automat in lista

2. CREARE MANUALA (Tab Step Builder):
   • Mergi la tab-ul "Step Builder"
   • Apasa "Adauga Pas" pentru fiecare actiune
   • Configureaza tipul, coordonatele, tastele, delay-ul
   • Poti edita, muta, sterge pasi individuali
   • Apasa "Ruleaza Rutina" cand esti gata

3. REDARE:
   • Seteaza numarul de repetari in campul "Repetari"
   • Apasa "Ruleaza" sau {sc.get('play','F7')}
   • Urmareste countdown-ul si numarul de iteratii ramase
   • Apasa "Pauza" ({sc.get('pause','F8')}) sau "Stop" ({sc.get('stop_play','F9')}) dupa nevoie

4. SALVARE RUTINA:
   • Apasa "Salveaza" din toolbar sau Ctrl+S
   • Introdu un nume si o descriere optionala
   • Rutina se salveaza in: {ROUTINES_DIR}

5. INCARCARE RUTINA:
   • Mergi la tab-ul "Rutine"
   • Selecteaza rutina din lista
   • Apasa "Incarca" sau dublu-click

6. SELECTIE MULTIPLA PASI:
   • Tine Ctrl apasat si click pe mai multi pasi
   • Sau tine Shift pentru selectie interval
   • Apasa Delete pentru a sterge pasii selectati

7. DELAY SI VITEZA:
   • Seteaza "Delay intre pasi" din panoul stanga (0.8s recomandat)
   • Seteaza "Viteza redare" (1.0 = normal, 0.5 = mai lent)
   • Delay recomandat pentru vizibilitate: 0.8 - 2.0 secunde

8. STOP URGENTA:
   • Apasa butonul rosu "STOP URGENTA" din toolbar
   • Sau apasa {sc.get('emergency','F12')} oricand

{'─'*65}
LOCATIE FISIERE:
  Rutine:  {ROUTINES_DIR}
  Loguri:  {LOGS_DIR}
  Notite:  {NOTES_DIR}
  Config:  {CONFIG_FILE}

{'─'*65}
CONTACT: {APP_AUTHOR}
"""
        help_txt.insert("1.0", content)
        help_txt.configure(state="disabled")

    # ==========================================================================
    # SECTIUNEA 14.L: STATUSBAR
    # ==========================================================================

    def _build_statusbar(self):
        """Construieste bara de status de jos."""
        sb = tk.Frame(self.root, bg=C["bg_card"], height=28)
        sb.pack(fill="x", side="bottom")
        sb.pack_propagate(False)

        # Indicator inregistrare
        self._rec_indicator = tk.Label(sb, text="⬤ STANDBY",
                                       bg=C["bg_card"], fg=C["text_muted"],
                                       font=("Segoe UI", 10, "bold"))
        self._rec_indicator.pack(side="left", padx=10)

        tk.Frame(sb, bg=C["border"], width=1).pack(
            side="left", fill="y", pady=4)

        # Status text
        tk.Label(sb, textvariable=self._status_var,
                 bg=C["bg_card"], fg=C["text"],
                 font=("Segoe UI", 10)).pack(side="left", padx=10)

        tk.Frame(sb, bg=C["border"], width=1).pack(
            side="left", fill="y", pady=4)

        # Numar pasi
        tk.Label(sb, textvariable=self._step_count_var,
                 bg=C["bg_card"], fg=C["accent"],
                 font=("Segoe UI", 10)).pack(side="left", padx=10)

        # Iteratie (dreapta)
        tk.Label(sb, textvariable=self._iter_var,
                 bg=C["bg_card"], fg=C["warning"],
                 font=("Segoe UI", 10, "bold")).pack(side="right", padx=10)

        # Versiune
        tk.Label(sb, text=f"{APP_NAME} v{APP_VERSION}",
                 bg=C["bg_card"], fg=C["text_muted"],
                 font=("Segoe UI", 9)).pack(side="right", padx=10)

    # ==========================================================================
    # SECTIUNEA 15: CALLBACKS SI LOGICA PRINCIPALA
    # ==========================================================================

    def _connect_callbacks(self):
        """Conecteaza callback-urile intre componente."""
        # 15.1 — Recorder
        self.recorder.on_step_recorded     = self._on_step_recorded
        self.recorder.on_recording_started = self._on_rec_started
        self.recorder.on_recording_stopped = self._on_rec_stopped
        # 15.2 — Player
        self.player.on_step_start   = self._on_player_step_start
        self.player.on_step_done    = self._on_player_step_done
        self.player.on_started      = self._on_play_started
        self.player.on_stopped      = self._on_play_stopped
        self.player.on_paused       = self._on_play_paused
        self.player.on_resumed      = self._on_play_resumed
        self.player.on_countdown    = self._on_countdown
        self.player.on_iter_update  = self._on_iter_update
        self.player.on_error        = self._on_player_error
        self.player.on_question     = self._on_player_question
        self.player.on_guard_question = self._on_guard_question
        # 15.3 — Log
        self.log_mgr.on_entry_added = self._on_log_entry

    def _register_hotkeys(self):
        """Inregistreaza hotkey-urile globale."""
        sc = self.settings.get("shortcuts", DEFAULT_SHORTCUTS)
        self.hotkey_mgr.register(sc.get("start_rec", "F5"),
                                 lambda: self.root.after(0, self._toggle_recording))
        self.hotkey_mgr.register(sc.get("stop_rec",  "F6"),
                                 lambda: self.root.after(0, self._stop_all))
        self.hotkey_mgr.register(sc.get("play",         "F7"),
                                 lambda: self.root.after(0, self._start_playback))
        self.hotkey_mgr.register(sc.get("resume_play",  "F3"),
                                 lambda: self.root.after(0, self._start_playback))
        self.hotkey_mgr.register(sc.get("pause",        "F8"),
                                 lambda: self.root.after(0, self._toggle_pause))
        self.hotkey_mgr.register(sc.get("stop_play", "F9"),
                                 lambda: self.root.after(0, self._stop_playback))
        self.hotkey_mgr.register(sc.get("emergency", "F12"),
                                 lambda: self.root.after(0, self._emergency_stop))
        self.hotkey_mgr.start()
        # [v3.9] Bindings directe pe fereastra
        self.root.bind("<F5>",  lambda e: self._toggle_recording())
        self.root.bind("<F6>",  lambda e: self._stop_all())
        self.root.bind("<F7>",  lambda e: self._start_playback())
        self.root.bind("<F3>",  lambda e: self._start_playback())
        self.root.bind("<F8>",  lambda e: self._toggle_pause())
        self.root.bind("<F9>",  lambda e: self._stop_playback())
        self.root.bind("<F12>", lambda e: self._emergency_stop())

    # ── Stare butoane ────────────────────────────────────────────
    def _set_btn_state_idle(self):
        """Seteaza starea butoanelor in modul idle."""
        self._btn_rec.configure(text="⏺  Inregistreaza", bg=C["danger"],
                                fg="white", state="normal", relief="flat",
                                bd=0, highlightthickness=2,
                                highlightbackground=C["danger"])
        self._btn_stopr.configure(state="disabled", bg=C["bg_input"],
                                  relief="flat", bd=0, highlightthickness=0)
        self._btn_play.configure(state="normal", bg=C["success"], fg="white",
                                 relief="flat", bd=0, highlightthickness=2,
                                 highlightbackground=C["success"])
        self._btn_pause.configure(state="disabled", bg=C["warning"],
                                  text="⏸  Pauza", relief="flat", bd=0,
                                  highlightthickness=0)
        self._btn_stopp.configure(state="disabled", bg=C["danger"],
                                  relief="flat", bd=0, highlightthickness=0)

    def _set_btn_state_recording(self):
        """Seteaza starea butoanelor in modul inregistrare."""
        self._btn_rec.configure(text="⏺ INREG...", bg="#FF0000", fg="white",
                                state="normal", relief="solid", bd=3,
                                highlightthickness=3, highlightbackground="white")
        self._btn_stopr.configure(state="normal", bg=C["danger"], fg="white",
                                  relief="solid", bd=2, highlightthickness=2,
                                  highlightbackground="white")
        self._btn_play.configure(state="disabled", bg=C["bg_input"],
                                 relief="flat", bd=0, highlightthickness=0)
        self._btn_pause.configure(state="disabled", bg=C["bg_input"],
                                  relief="flat", bd=0, highlightthickness=0)
        self._btn_stopp.configure(state="disabled", bg=C["bg_input"],
                                  relief="flat", bd=0, highlightthickness=0)

    def _set_btn_state_playing(self):
        """Seteaza starea butoanelor in modul redare."""
        self._btn_play.configure(state="disabled", bg="#007A3D", fg="white",
                                 relief="solid", bd=3, highlightthickness=3,
                                 highlightbackground="white")
        self._btn_pause.configure(state="normal", bg=C["warning"], fg="white",
                                  relief="solid", bd=2, highlightthickness=2,
                                  highlightbackground="white")
        self._btn_stopp.configure(state="normal", bg=C["danger"], fg="white",
                                  relief="solid", bd=2, highlightthickness=2,
                                  highlightbackground="white")
        self._btn_rec.configure(state="disabled", bg=C["bg_input"],
                                relief="flat", bd=0, highlightthickness=0)
        self._btn_stopr.configure(state="disabled", bg=C["bg_input"],
                                  relief="flat", bd=0, highlightthickness=0)

    # ── Recorder actions ─────────────────────────────────────────
    def _toggle_recording(self):
        """Porneste sau opreste inregistrarea."""
        if getattr(self, "_mode", "recorder") == "studio" and not self._is_recording:
            return  # in Studio, F5 nu porneste recorderul pe coordonate
        if not self._is_recording:
            self._start_recording()
        else:
            self._stop_recording()

    def _start_recording(self):
        """Porneste inregistrarea."""
        if self.recorder.start():
            self._is_recording = True

    def _stop_recording(self):
        """Opreste inregistrarea."""
        if self._is_recording:
            self.recorder.stop()
            self._is_recording = False
        
    def _rec_debug_step(self):
        """
        [DEBUG] Executa un singur pas selectat in tab Recorder si afiseaza
        rezultatul intr-un popup de debug. Identic cu _builder_debug_step.
        """
        sel = self._steps_tv.selection()
        if not sel or len(sel) != 1:
            messagebox.showwarning("Debug", "Selecteaza exact UN pas pentru debug.")
            return

        step_id = int(sel[0])
        step    = next((s for s in self.recorder.get_steps()
                        if s.step_id == step_id), None)
        if not step:
            return

        # ── Construieste fereastra de debug ──────────────────────────────
        dlg = tk.Toplevel(self.root)
        dlg.title(f"🐛 Debug — Pas #{step.step_id}")
        dlg.geometry("520x420")
        dlg.resizable(False, False)
        dlg.configure(bg=C["bg_main"])
        dlg.grab_set()
        # [v3.9] DEBUG indicator
        try:
            self.mode_indicator.show("debug")
            _orig_close = dlg.protocol
            dlg.protocol("WM_DELETE_WINDOW", lambda: [
                self.mode_indicator.hide(), dlg.destroy()])
        except Exception:
            pass
        dlg.attributes("-topmost", True)

        # Header
        tk.Label(dlg,
                text=f"🐛  Debug Pas #{step.step_id}",
                bg=C["bg_main"], fg=C["primary"],
                font=("Segoe UI", 13, "bold")).pack(pady=(14, 4))

        # ── Tabel cu proprietatile pasului ───────────────────────────────
        info_f = tk.Frame(dlg, bg=C["bg_card"], relief="flat", bd=0)
        info_f.pack(fill="x", padx=16, pady=6)

        def row(label, value, color=None):
            fr = tk.Frame(info_f, bg=C["bg_card"])
            fr.pack(fill="x", padx=8, pady=2)
            tk.Label(fr, text=f"{label}:",
                    bg=C["bg_card"], fg=C["text_dim"],
                    font=("Consolas", 10), width=16, anchor="e"
                    ).pack(side="left")
            tk.Label(fr, text=str(value) if value != "" else "—",
                    bg=C["bg_card"], fg=color or C["text"],
                    font=("Consolas", 10, "bold"), anchor="w"
                    ).pack(side="left", padx=(6, 0))

        row("Tip",         step.step_type,   C["accent"])
        row("Descriere",   step.description[:55])
        row("X / Y",       f"{step.x}  /  {step.y}")
        row("Click Type",  step.click_type)
        row("Tasta/Combo", step.key_combo   or "—")
        row("Text Input",  step.text_input  or "—")
        row("Delay Before",f"{step.delay_before:.2f}s")
        row("Delay After", f"{step.delay_after:.2f}s")
        row("Skip",        "DA" if step.skip else "NU",
                           C["warning"] if step.skip else C["success"])
        row("Comentariu",  step.comment[:50] or "—")

        # ── Zona rezultat ─────────────────────────────────────────────────
        tk.Frame(dlg, bg=C["separator"], height=1).pack(fill="x", padx=16, pady=8)

        res_var = tk.StringVar(value="⏳ Apasa 'Executa Acum' pentru a testa pasul...")
        lbl_res = tk.Label(dlg,
                        textvariable=res_var,
                        bg=C["bg_main"], fg=C["text_dim"],
                        font=("Segoe UI", 11, "bold"),
                        wraplength=480)
        lbl_res.pack(pady=(0, 10))

        def _do_exec():
            if self.player.is_running:
                messagebox.showwarning("Debug",
                    "Playerul ruleaza deja. Opreste redarea inainte de debug.",
                    parent=dlg)
                return
            btn_exec.configure(state="disabled", text="⏳ Se executa...")
            dlg.update()
            import time
            time.sleep(0.5)
            t0 = time.time()
            ok, err = self.player._exec(step)
            dur = (time.time() - t0) * 1000
            if ok:
                res_var.set(f"✅  OK  —  Executat in {dur:.1f} ms")
                lbl_res.configure(fg=C["success"])
            else:
                res_var.set(f"❌  EROARE  —  {err}")
                lbl_res.configure(fg=C["danger"])
            btn_exec.configure(state="normal", text="▶ Executa Din Nou")
            self.log_mgr.add(
                step.step_id,
                f"[DEBUG] {step.description or step.step_type}",
                "OK" if ok else "EROARE",
                has_error=not ok, error_msg=err,
                duration_ms=round(dur, 2), iteration=0,
            )

        # ── Butoane ───────────────────────────────────────────────────────
        btn_f = tk.Frame(dlg, bg=C["bg_main"])
        btn_f.pack(pady=6)

        btn_exec = tk.Button(btn_f,
                            text="▶  Executa Acum",
                            command=_do_exec,
                            bg=C["success"], fg="white",
                            activebackground=C["success_hover"],
                            activeforeground="white",
                            font=("Segoe UI", 11, "bold"),
                            relief="flat", padx=16, pady=6,
                            cursor="hand2")
        btn_exec.pack(side="left", padx=6)

        tk.Button(btn_f,
                  text="✖  Inchide",
                  command=dlg.destroy,
                  bg=C["danger"], fg="white",
                  activebackground=C["danger_hover"],
                  activeforeground="white",
                  font=("Segoe UI", 11, "bold"),
                  relief="flat", padx=16, pady=6,
                  cursor="hand2").pack(side="left", padx=6)
    
    def _stop_all(self):
        """Opreste orice operatie activa."""
        self._stop_recording()
        self._stop_playback()

    def _on_rec_started(self):
        """Callback apelat cand inregistrarea porneste."""
        self.root.after(0, self._on_rec_started_ui)

    def _on_rec_started_ui(self):
        """Actualizeaza UI-ul pe thread-ul principal."""
        self._set_btn_state_recording()
        self._show_recording_indicator()
        if self.settings.get("dnd_during_run", True):
            self._rec_dnd = True
            DoNotDisturb.enable(wait=False)

    def _show_recording_indicator(self):
        """Afiseaza overlay REC pe TOATE monitoarele."""
        self._hide_recording_indicator()
        self._rec_indicators = []
        if self.run_frame.enabled:
            self.run_frame.show("rec")  # v4.1: chenar verde + REC
            return

        try:
            sw = self.root.winfo_screenwidth()
            sh = self.root.winfo_screenheight()
            screens = [(0, 0, sw, sh)]
        except Exception:
            screens = [(0, 0, 1920, 1080)]

        w, h = 140, 22

        for (mx, my, mw, mh) in screens:
            ind = tk.Toplevel(self.root)
            ind.overrideredirect(True)
            ind.attributes("-topmost", True)
            ind.attributes("-alpha", 0.82)
            ind.configure(bg="#FF0000")
            ind.geometry(f"{w}x{h}+{mx + mw - w - 10}+{my + 10}")
            tk.Label(
                ind,
                text="⏺ REC  ACTIV",
                bg="#FF0000",
                fg="white",
                font=("Segoe UI", 7, "bold")
            ).pack(expand=True, fill="both")
            self._rec_indicators.append(ind)

    def _hide_recording_indicator(self):
        """Ascunde overlay-urile REC de pe toate monitoarele."""
        if self.run_frame.mode == "rec":
            self.run_frame.hide()
        if hasattr(self, "_rec_indicators"):
            for ind in self._rec_indicators:
                try:
                    ind.destroy()
                except Exception:
                    pass
            self._rec_indicators = []
        # self._rec_indicator (label statusbar) NU se atinge — ramane intact!

    def _on_rec_stopped(self):
        """Callback: inregistrarea s-a oprit."""
        if getattr(self, "_rec_dnd", False):
            self._rec_dnd = False
            DoNotDisturb.restore()
        self.root.after(0, lambda: [
            self._hide_recording_indicator(),
            self._set_btn_state_idle(),
            self._status_var.set("Inregistrare oprita"),
            self._rec_indicator.configure(text="⬤ STANDBY",
                                          fg=C["text_muted"]),
        ])

    def _on_step_recorded(self, step: StepModel):
        # v3.7: Debug ghost
        try:
            if self._debug_mode and hasattr(step, "x") and step.x and step.y:
                _cm = {"CLICK": "#FF4444", "RCLICK": "#FF8800", "TYPE": "#4488FF", "KEY": "#4488FF", "SCROLL": "#AA44FF"}
                _col = _cm.get(getattr(step, "action", ""), "#FF4444")
                _lbl = getattr(step, "action", "")
                self.root.after(0, lambda sx=step.x, sy=step.y, c=_col, lb=_lbl: self.debug_overlay.show_at(sx, sy, lb, c))
        except Exception:
            pass

        """Callback: un pas nou a fost inregistrat."""
        self.root.after(0, lambda s=step: self._add_step_to_tv(s))

    def _add_step_to_tv(self, step: StepModel, tv=None):
        """Adauga un pas in treeview-ul de pasi."""
        target = tv or self._steps_tv
        tag    = "even" if step.step_id % 2 == 0 else "odd"
        if step.skip:
            tag = "skipped"
        target.insert("", "end",
                      iid=str(step.step_id),
                      values=(
                          step.step_id,
                          step.step_type,
                          step.description[:80],
                          f"{step.delay_before:.2f}",
                          "DA" if step.skip else "",
                          step.timestamp,
                      ),
                      tags=(tag,))
        target.see(str(step.step_id))
        self._update_step_count()

    def _update_step_count(self):
        """Actualizeaza contorul de pasi."""
        n = len(self.recorder.get_steps())
        self._step_count_var.set(f"Pasi: {n}")
        # Avertizare
        if n > MAX_STEPS_WARNING:
            self._lbl_warn.pack(fill="x", padx=6, pady=2)
        else:
            try:
                self._lbl_warn.pack_forget()
            except Exception:
                pass

    # ── Player actions ────────────────────────────────────────────
    def _start_playback(self):
        """Porneste redarea rutinei."""
        if getattr(self, "_mode", "recorder") == "studio" and self._studio is not None:
            self._studio.run()
            return
        steps = self.recorder.get_steps()
        if not steps:
            messagebox.showwarning("Fara pasi",
                                   "Nu exista pasi de redat.\n"
                                   "Inregistreaza o rutina sau creeaza pasi in Step Builder.")
            return
        try:
            repeat = max(1, int(self._repeat_var.get()))
        except ValueError:
            repeat = 1
        # Salveaza setarile curente
        self.settings.set("step_delay",          float(self._var_delay.get()))
        self.settings.set("playback_speed",       float(self._var_speed.get()))
        self.settings.set("countdown_before_play",int(self._var_cd.get()))
        self.settings.set("repeat_count",         repeat)
        # v4.1: siguranta la rulare
        self.player.suppress_notifications = bool(self.settings.get("dnd_during_run", True))
        self.guard.enabled = bool(self.settings.get("guard_enabled", True))
        self.guard.sensitivity = str(self.settings.get("guard_sensitivity", "normal"))
        if self.player.play(steps, repeat=repeat):
            self.run_frame.show("run")

    def _toggle_pause(self):
        """Comuta pauza/reluare."""
        if getattr(self, "_mode", "recorder") == "studio" and self._studio is not None and self._studio.busy:
            self._studio.toggle_pause()
            return
        if self.player.is_paused:
            self.player.resume()
        else:
            self.player.pause()

    def _stop_playback(self):
        """Opreste redarea."""
        if self._studio is not None and self._studio.busy:
            self._studio.stop()
        self.player.stop()

    def _emergency_stop(self):
        """Oprire de urgenta."""
        if self._studio is not None and self._studio.busy:
            self._studio.stop()
        self.player.emergency_stop()
        if self._is_recording:
            self.recorder.stop()
            self._is_recording = False
        self.root.after(0, self.run_frame.hide)
        self.root.after(0, lambda: [
            self._set_btn_state_idle(),
            self._status_var.set("🚨 STOP URGENTA ACTIVAT"),
            self._rec_indicator.configure(text="⬤ STANDBY", fg=C["text_muted"]),
            self._countdown_var.set(""),
            self._iter_var.set(""),
        ])

    def _on_play_started(self):
        # [v3.9] Ascunde mode_indicator inainte de RUN
        try:
            self.mode_indicator.hide()
        except Exception:
            pass
        # v3.7: Countdown + RUN indicator (v4.1: inlocuit de chenarul RUN, daca e activ)
        try:
            cd = int(self.settings.get("countdown", 3))
            if self.run_frame.enabled:
                pass
            elif cd > 0:
                self.stopwatch_ovl.show_countdown(seconds=cd, on_done=lambda: self.run_indicator.show())
            else:
                self.run_indicator.show()
        except Exception:
            pass

        """Callback: redarea a pornit."""
        self.root.after(0, lambda: [
            self._set_btn_state_playing(),
            self._status_var.set("▶ REDARE ACTIVA"),
            self._rec_indicator.configure(text="⬤ REDARE", fg=C["success"]),
        ])

    def _on_play_stopped(self):
        # [v3.9] Hide RUN + mode indicators
        self.root.after(0, self.run_frame.hide)
        try:
            self.run_indicator.hide()
            self.mode_indicator.hide()
            self.stopwatch_ovl.destroy()
        except Exception:
            pass

        """Callback: redarea s-a oprit."""
        self.root.after(0, lambda: [
            self._set_btn_state_idle(),
            self._status_var.set("Redare finalizata"),
            self._rec_indicator.configure(text="⬤ STANDBY", fg=C["text_muted"]),
            self._countdown_var.set(""),
            self._iter_var.set(""),
            self._floating_sc.hide(),
        ])

    def _on_play_paused(self):
        """Callback: redarea e pe pauza."""
        self.root.after(0, lambda: self.run_frame.show("pause") if self.run_frame.mode != "off" else None)
        self.root.after(0, lambda: [
            self._btn_pause.configure(text="▶  Reia"),
            self._status_var.set("⏸ PAUZA"),
        ])

    def _on_play_resumed(self):
        """Callback: redarea a reluat."""
        self.root.after(0, lambda: self.run_frame.show("run") if self.run_frame.mode != "off" else None)
        self.root.after(0, lambda: [
            self._btn_pause.configure(text="⏸  Pauza"),
            self._status_var.set("▶ REDARE ACTIVA"),
        ])

    def _on_countdown(self, sec: int):
        """Callback: afiseaza countdown-ul."""
        self.root.after(0, lambda s=sec: [
            self._countdown_var.set(f"⏱{s}"),
            self._status_var.set(f"Start in {s}s..."),
        ])

    def _on_iter_update(self, cur: int, total: int):
        """Callback: actualizeaza afisarea iteratiei."""
        remaining = total - cur + 1
        self.root.after(0, lambda: self._iter_var.set(
            f"Repetare {cur}/{total}  |  Ramase: {remaining}"))

    def _on_player_step_start(self, idx: int, step: StepModel):
        """Callback: un pas a inceput executia — evidentiaza in treeview."""
        def _hl():
            try:
                for iid in self._steps_tv.get_children():
                    tags = list(self._steps_tv.item(iid, "tags"))
                    if "playing" in tags:
                        tags.remove("playing")
                        n = int(iid)
                        tags.append("even" if n % 2 == 0 else "odd")
                        self._steps_tv.item(iid, tags=tags)
                iid = str(step.step_id)
                if self._steps_tv.exists(iid):
                    self._steps_tv.item(iid, tags=("playing",))
                    self._steps_tv.see(iid)
            except Exception:
                pass
        self.root.after(0, _hl)

    def _on_player_step_done(self, idx: int, step: StepModel, ok: bool):
        """Callback: un pas s-a terminat."""
        if not ok:
            def _err():
                iid = str(step.step_id)
                if self._steps_tv.exists(iid):
                    self._steps_tv.item(iid, tags=("error",))
            self.root.after(0, _err)

    def _on_player_error(self, step: StepModel, msg: str):
        """Callback: eroare la executia unui pas."""
        self.root.after(0, lambda: self._status_var.set(
            f"⚠ Eroare pas {step.step_id}: {msg[:50]}"))

    def _on_player_question(self, step: StepModel) -> str:
        """Callback: intrebare pentru user in timpul redarii."""
        result = {"ans": "Continua"}
        def _ask():
            buttons = step.question_buttons.split(",")
            dlg = tk.Toplevel(self.root)
            dlg.title("Intrebare Rutina")
            dlg.geometry("400x200")
            dlg.grab_set()
            dlg.attributes("-topmost", True)
            dlg.configure(bg=C["bg_main"])
            tk.Label(dlg, text=step.question_text or "Continui rutina?",
                     bg=C["bg_main"], fg=C["text"],
                     font=("Segoe UI", 12), wraplength=360).pack(pady=20)
            btn_f = tk.Frame(dlg, bg=C["bg_main"])
            btn_f.pack()
            for btn_text in buttons:
                btn_text = btn_text.strip()
                def _click(t=btn_text):
                    result["ans"] = t
                    dlg.destroy()
                bg = C["danger"] if "Opre" in btn_text else C["success"]
                tk.Button(btn_f, text=btn_text, command=_click,
                          bg=bg, fg="white", relief="flat",
                          font=("Segoe UI", 11), padx=12, pady=6,
                          cursor="hand2").pack(side="left", padx=6)
            dlg.wait_window()
        done = threading.Event()

        def _ask_and_signal():
            try:
                _ask()
            finally:
                done.set()
        self.root.after(0, _ask_and_signal)
        done.wait()  # v4.1: asteapta raspunsul (inainte returna "Continua" dupa 0.2 s)
        return result["ans"]

    # ── v4.1: Sistemul de preventie — pauza + intrebare ───────────
    def _on_guard_question(self, step: StepModel, alert: GuardAlert, can_retry: bool) -> str:
        """Apelat din firul playerului: afiseaza intrebarea si asteapta raspunsul."""
        result = {"d": STOP}
        done = threading.Event()

        def _show():
            try:
                result["d"] = self._guard_dialog(step, alert, can_retry)
            finally:
                done.set()
        self.root.after(0, _show)
        done.wait()
        return result["d"]

    def _guard_dialog(self, step: StepModel, alert: GuardAlert, can_retry: bool) -> str:
        options = []
        if can_retry:
            options.append(("Reincearca pasul", RETRY, C["success"]))
        options.append(("Continua", CONTINUE, C["success"]))
        if alert.can_ignore_step:
            options.append(("Continua si nu mai verifica pasul", IGNORE_STEP, C["primary"]))
        options.append(("Sari pasul", SKIP_STEP, C["bg_input"]))
        options.append(("Opreste rutina", STOP, C["danger"]))

        self._status_var.set(f"⚠ {alert.title} — rutina e pe pauza")
        dlg = tk.Toplevel(self.root)
        dlg.title("AutoPilot DC — ceva difera")
        dlg.configure(bg=C["bg_main"])
        dlg.attributes("-topmost", True)
        dlg.resizable(False, False)
        chosen = {"d": STOP}  # inchiderea ferestrei = oprire (cel mai sigur)

        tk.Label(dlg, text=f"⚠  {alert.title}", bg=C["bg_main"], fg=C["warning"],
                 font=("Segoe UI", 13, "bold"), wraplength=560, justify="left").pack(anchor="w", padx=18, pady=(16, 6))
        where = step.description or step.get_display_type()
        txt = tk.Text(dlg, height=8, width=70, wrap="word", bg=C["bg_card"], fg=C["text"],
                      font=("Segoe UI", 10), relief="flat", padx=8, pady=6)
        txt.insert("1.0", f"Pasul #{step.step_id}: {where}\n\n{alert.details}")
        txt.configure(state="disabled")
        txt.pack(fill="both", padx=18)

        bf = tk.Frame(dlg, bg=C["bg_main"])
        bf.pack(anchor="e", padx=18, pady=14)
        for label, value, bg in options:
            def _pick(v=value):
                chosen["d"] = v
                dlg.destroy()
            tk.Button(bf, text=label, command=_pick, bg=bg, fg=_btn_fg(bg), relief="flat",
                      font=("Segoe UI", 10, "bold"), padx=10, pady=5,
                      cursor="hand2").pack(side="left", padx=4)

        dlg.update_idletasks()
        w, h = dlg.winfo_reqwidth(), dlg.winfo_reqheight()
        dlg.geometry(f"+{(dlg.winfo_screenwidth() - w) // 2}+{(dlg.winfo_screenheight() - h) // 3}")
        dlg.grab_set()
        dlg.focus_force()
        dlg.wait_window()
        return chosen["d"]

    # ── Log callbacks ─────────────────────────────────────────────
    def _on_log_entry(self, entry: LogEntry):
        """Callback: adauga o intrare in tabelul de log."""
        self.root.after(0, lambda e=entry: self._add_log_row(e))

    def _add_log_row(self, entry: LogEntry):
        """Adauga o linie in tabelul de log."""
        tag = "error" if entry.has_error else (
            "even" if entry.entry_id % 2 == 0 else "odd")
        self._log_tv.insert("", "end",
                             values=(
                                 entry.entry_id, entry.timestamp,
                                 entry.step_id, entry.action[:60],
                                 entry.result,
                                 "DA" if entry.has_error else "",
                                 entry.error_msg[:40],
                                 entry.comment[:30],
                                 f"{entry.duration_ms:.1f}",
                                 entry.iteration,
                             ),
                             tags=(tag,))
        children = self._log_tv.get_children()
        if children:
            self._log_tv.see(children[-1])

    # ── Pasi actions ──────────────────────────────────────────────
    def _new_routine(self):
        """Creeaza o rutina noua (sterge pasii curenti)."""
        if self.recorder.get_steps():
            if not messagebox.askyesno("Confirmare",
                                       "Stergi pasii curenti si incepi o rutina noua?"):
                return
        self.recorder.clear()
        self._refresh_steps_tv()
        self._status_var.set("Rutina noua creata")

    def _refresh_steps_tv(self):
        """Reincarca treeview-ul de pasi din recorder."""
        for iid in self._steps_tv.get_children():
            self._steps_tv.delete(iid)
        for step in self.recorder.get_steps():
            self._add_step_to_tv(step)
        self._update_step_count()

    def _clear_all_steps(self):
        """Sterge toti pasii cu confirmare."""
        if not self.recorder.get_steps():
            return
        if messagebox.askyesno("Confirmare",
                               "Stergi toti pasii? Rutina nesalvata se pierde."):
            self.recorder.clear()
            self._refresh_steps_tv()
            # Curata si builder-ul
            for iid in self._builder_tv.get_children():
                self._builder_tv.delete(iid)
            self._lbl_builder_count.configure(text="Pasi in builder: 0")
            self._status_var.set("Toti pasii au fost stearsi")

    def _delete_selected_steps(self):
        """Sterge pasii selectati din treeview (suporta selectie multipla)."""
        sel = self._steps_tv.selection()
        if not sel:
            return
        ids_to_del = {int(iid) for iid in sel}
        # Sterge din recorder
        steps = [s for s in self.recorder.get_steps()
                 if s.step_id not in ids_to_del]
        self.recorder.set_steps(steps)
        # Sterge din treeview
        for iid in sel:
            self._steps_tv.delete(iid)
        self._update_step_count()

    def _move_step_up(self):
        """Muta pasul selectat in sus."""
        sel = self._steps_tv.selection()
        if not sel or len(sel) != 1:
            return
        iid  = sel[0]
        prev = self._steps_tv.prev(iid)
        if not prev:
            return
        self._steps_tv.move(iid, "", self._steps_tv.index(prev))
        self._sync_steps_from_tv()

    def _move_step_down(self):
        """Muta pasul selectat in jos."""
        sel = self._steps_tv.selection()
        if not sel or len(sel) != 1:
            return
        iid  = sel[0]
        nxt  = self._steps_tv.next(iid)
        if not nxt:
            return
        self._steps_tv.move(nxt, "", self._steps_tv.index(iid))
        self._sync_steps_from_tv()

    def _sync_steps_from_tv(self):
        """Sincronizeaza ordinea pasilor din treeview cu recorder-ul."""
        order = [int(iid) for iid in self._steps_tv.get_children()]
        steps_map = {s.step_id: s for s in self.recorder.get_steps()}
        new_steps = [steps_map[sid] for sid in order if sid in steps_map]
        self.recorder.set_steps(new_steps)

    def _toggle_skip_selected(self):
        """Comuta starea skip a pasilor selectati."""
        sel = self._steps_tv.selection()
        if not sel:
            return
        ids = {int(iid) for iid in sel}
        for step in self.recorder.get_steps():
            if step.step_id in ids:
                step.skip = not step.skip
                iid  = str(step.step_id)
                vals = list(self._steps_tv.item(iid, "values"))
                vals[4] = "DA" if step.skip else ""
                tag  = "skipped" if step.skip else (
                    "even" if step.step_id % 2 == 0 else "odd")
                self._steps_tv.item(iid, values=vals, tags=(tag,))

    def _edit_selected_step(self):
        """Editeaza pasul selectat."""
        sel = self._steps_tv.selection()
        if not sel or len(sel) != 1:
            return
        step_id = int(sel[0])
        steps   = self.recorder.get_steps()
        step    = next((s for s in steps if s.step_id == step_id), None)
        if not step:
            return
        dlg = StepBuilderDialog(self.root, step, title="Editeaza Pas")
        if dlg.result:
            # Actualizeaza in recorder
            for i, s in enumerate(steps):
                if s.step_id == step_id:
                    steps[i] = dlg.result
                    break
            self.recorder.set_steps(steps)
            self._refresh_steps_tv()

    def _add_step_manual(self):
        """Adauga un pas manual prin dialog."""
        dlg = StepBuilderDialog(self.root, title="Adauga Pas Manual")
        if dlg.result:
            self.recorder.add_step_manual(dlg.result)

    def _add_delay_step(self):
        """Adauga un pas de delay."""
        val = simpledialog.askfloat(
            "Adauga Delay", "Durata delay-ului (secunde):",
            initialvalue=1.0, minvalue=0.1, maxvalue=60.0,
            parent=self.root)
        if val:
            step = StepModel(step_type="DELAY", delay_before=val,
                             description=f"Pauza: {val:.1f}s")
            self.recorder.add_step_manual(step)

    def _on_step_rclick(self, event):
        """Meniu contextual click dreapta pe pas."""
        iid = self._steps_tv.identify_row(event.y)
        if not iid:
            return
        if iid not in self._steps_tv.selection():
            self._steps_tv.selection_set(iid)
        menu = tk.Menu(self.root, tearoff=0,
                       bg=C["bg_card"], fg=C["text"],
                       activebackground=C["primary"],
                       activeforeground="white")
        menu.add_command(label="✏ Editeaza Pasul",
                         command=self._edit_selected_step)
        menu.add_command(label="⊘ Skip / Unskip",
                         command=self._toggle_skip_selected)
        menu.add_command(label="▲ Muta Sus",
                         command=self._move_step_up)
        menu.add_command(label="▼ Muta Jos",
                         command=self._move_step_down)
        menu.add_separator()
        menu.add_command(label="🗑 Sterge Selectat(ii)",
                         command=self._delete_selected_steps)
        menu.tk_popup(event.x_root, event.y_root)

    def _on_step_dclick(self, event):
        """Dublu-click pe pas: editeaza."""
        self._edit_selected_step()

    # ── Step Builder actions ──────────────────────────────────────
    def _builder_add_step(self):
        """Adauga un pas nou in Step Builder."""
        dlg = StepBuilderDialog(self.root, title="Adauga Pas Nou")
        if dlg.result:
            self.recorder.add_step_manual(dlg.result)
            # Adauga si in builder_tv
            step = dlg.result
            tag  = "even" if step.step_id % 2 == 0 else "odd"
            self._builder_tv.insert("", "end",
                                    iid=str(step.step_id),
                                    values=(
                                        step.step_id,
                                        step.step_type,
                                        step.description[:60],
                                        step.x, step.y,
                                        step.key_combo or step.text_input,
                                        f"{step.delay_before:.2f}",
                                        "DA" if step.skip else "",
                                        step.comment[:30],
                                    ),
                                    tags=(tag,))
            self._builder_tv.see(str(step.step_id))
            n = len(self._builder_tv.get_children())
            self._lbl_builder_count.configure(text=f"Pasi in builder: {n}")
            # Sync si in steps_tv
            self._add_step_to_tv(step)

    def _builder_edit_step(self):
        """Editeaza pasul selectat in builder."""
        sel = self._builder_tv.selection()
        if not sel or len(sel) != 1:
            return
        step_id = int(sel[0])
        steps   = self.recorder.get_steps()
        step    = next((s for s in steps if s.step_id == step_id), None)
        if not step:
            return
        dlg = StepBuilderDialog(self.root, step, title="Editeaza Pas")
        if dlg.result:
            for i, s in enumerate(steps):
                if s.step_id == step_id:
                    steps[i] = dlg.result
                    break
            self.recorder.set_steps(steps)
            # Actualizeaza ambele treeview-uri
            self._refresh_steps_tv()
            self._refresh_builder_tv()

    def _refresh_builder_tv(self):
        """Reincarca builder treeview."""
        for iid in self._builder_tv.get_children():
            self._builder_tv.delete(iid)
        for step in self.recorder.get_steps():
            tag = "even" if step.step_id % 2 == 0 else "odd"
            if step.skip:
                tag = "skipped"
            self._builder_tv.insert("", "end",
                                    iid=str(step.step_id),
                                    values=(
                                        step.step_id,
                                        step.step_type,
                                        step.description[:60],
                                        step.x, step.y,
                                        step.key_combo or step.text_input,
                                        f"{step.delay_before:.2f}",
                                        "DA" if step.skip else "",
                                        step.comment[:30],
                                    ),
                                    tags=(tag,))
        n = len(self._builder_tv.get_children())
        self._lbl_builder_count.configure(text=f"Pasi in builder: {n}")

    def _builder_move_up(self):
        """Muta pasul selectat in sus in builder."""
        sel = self._builder_tv.selection()
        if not sel or len(sel) != 1:
            return
        iid  = sel[0]
        prev = self._builder_tv.prev(iid)
        if not prev:
            return
        self._builder_tv.move(iid, "", self._builder_tv.index(prev))
        self._sync_builder_from_tv()

    def _builder_move_down(self):
        """Muta pasul selectat in jos in builder."""
        sel = self._builder_tv.selection()
        if not sel or len(sel) != 1:
            return
        iid = sel[0]
        nxt = self._builder_tv.next(iid)
        if not nxt:
            return
        self._builder_tv.move(nxt, "", self._builder_tv.index(iid))
        self._sync_builder_from_tv()

    def _sync_builder_from_tv(self):
        """Sincronizeaza ordinea din builder cu recorder-ul."""
        order     = [int(iid) for iid in self._builder_tv.get_children()]
        steps_map = {s.step_id: s for s in self.recorder.get_steps()}
        new_steps = [steps_map[sid] for sid in order if sid in steps_map]
        self.recorder.set_steps(new_steps)
        self._refresh_steps_tv()

    def _builder_toggle_skip(self):
        """Comuta skip pe pasul selectat in builder."""
        sel = self._builder_tv.selection()
        if not sel:
            return
        ids = {int(iid) for iid in sel}
        for step in self.recorder.get_steps():
            if step.step_id in ids:
                step.skip = not step.skip
                iid  = str(step.step_id)
                vals = list(self._builder_tv.item(iid, "values"))
                vals[7] = "DA" if step.skip else ""
                tag  = "skipped" if step.skip else (
                    "even" if step.step_id % 2 == 0 else "odd")
                self._builder_tv.item(iid, values=vals, tags=(tag,))
        self._refresh_steps_tv()

    def _builder_delete_step(self):
        """Sterge pasul selectat din builder."""
        sel = self._builder_tv.selection()
        if not sel:
            return
        ids = {int(iid) for iid in sel}
        steps = [s for s in self.recorder.get_steps() if s.step_id not in ids]
        self.recorder.set_steps(steps)
        for iid in sel:
            self._builder_tv.delete(iid)
        n = len(self._builder_tv.get_children())
        self._lbl_builder_count.configure(text=f"Pasi in builder: {n}")
        self._refresh_steps_tv()

    def _builder_clear_all(self):
        """Sterge toti pasii din builder."""
        if messagebox.askyesno("Confirmare", "Stergi toti pasii din builder?"):
            self.recorder.clear()
            for iid in self._builder_tv.get_children():
                self._builder_tv.delete(iid)
            self._lbl_builder_count.configure(text="Pasi in builder: 0")
            self._refresh_steps_tv()

    def _builder_rclick(self, event):
        """Meniu contextual in builder."""
        iid = self._builder_tv.identify_row(event.y)
        if not iid:
            return
        self._builder_tv.selection_set(iid)
        menu = tk.Menu(self.root, tearoff=0,
                       bg=C["bg_card"], fg=C["text"],
                       activebackground=C["primary"],
                       activeforeground="white")
        menu.add_command(label="✏ Editeaza", command=self._builder_edit_step)
        menu.add_command(label="⊘ Skip/Unskip", command=self._builder_toggle_skip)
        menu.add_command(label="▲ Muta Sus",    command=self._builder_move_up)
        menu.add_command(label="▼ Muta Jos",    command=self._builder_move_down)
        menu.add_separator()
        menu.add_command(label="🐛 Debug Pas",  command=self._builder_debug_step)
        menu.add_separator()
        menu.add_command(label="🗑 Sterge",      command=self._builder_delete_step)
        menu.tk_popup(event.x_root, event.y_root)
        
    def _builder_debug_step(self):
        """
        [DEBUG] Executa un singur pas selectat in Step Builder si afiseaza
        rezultatul intr-un popup de debug. Nu necesita countdown sau loop.
        Foloseste direct self.player._exec(step) — motorul existent.
        """
        sel = self._builder_tv.selection()
        if not sel or len(sel) != 1:
            messagebox.showwarning("Debug", "Selecteaza exact UN pas pentru debug.")
            return

        step_id = int(sel[0])
        step    = next((s for s in self.recorder.get_steps()
                        if s.step_id == step_id), None)
        if not step:
            return

        # ── Construieste fereastra de debug ──────────────────────
        dlg = tk.Toplevel(self.root)
        dlg.title(f"🐛 Debug — Pas #{step.step_id}")
        dlg.geometry("520x420")
        dlg.resizable(False, False)
        dlg.configure(bg=C["bg_main"])
        dlg.grab_set()
        # [v3.9] DEBUG indicator
        try:
            self.mode_indicator.show("debug")
            _orig_close = dlg.protocol
            dlg.protocol("WM_DELETE_WINDOW", lambda: [
                self.mode_indicator.hide(), dlg.destroy()])
        except Exception:
            pass
        dlg.attributes("-topmost", True)

        # Header
        tk.Label(dlg,
                text=f"🐛  Debug Pas #{step.step_id}",
                bg=C["bg_main"], fg=C["primary"],
                font=("Segoe UI", 13, "bold")).pack(pady=(14, 4))

        # ── Tabel cu proprietatile pasului ───────────────────────
        info_f = tk.Frame(dlg, bg=C["bg_card"], relief="flat", bd=0)
        info_f.pack(fill="x", padx=16, pady=6)

        def row(label, value, color=None):
            fr = tk.Frame(info_f, bg=C["bg_card"])
            fr.pack(fill="x", padx=8, pady=2)
            tk.Label(fr, text=f"{label}:",
                    bg=C["bg_card"], fg=C["text_dim"],
                    font=("Consolas", 10), width=16, anchor="e"
                    ).pack(side="left")
            tk.Label(fr, text=str(value) if value != "" else "—",
                    bg=C["bg_card"], fg=color or C["text"],
                    font=("Consolas", 10, "bold"), anchor="w"
                    ).pack(side="left", padx=(6, 0))

        row("Tip",        step.step_type,   C["accent"])
        row("Descriere",  step.description[:55])
        row("X / Y",      f"{step.x}  /  {step.y}")
        row("Click Type", step.click_type)
        row("Tasta/Combo",step.key_combo   or "—")
        row("Text Input", step.text_input  or "—")
        row("Delay Before",f"{step.delay_before:.2f}s")
        row("Delay After", f"{step.delay_after:.2f}s")
        row("Skip",       "DA" if step.skip else "NU",
                        C["warning"] if step.skip else C["success"])
        row("Comentariu", step.comment[:50] or "—")

        # ── Zona rezultat ─────────────────────────────────────────
        sep = tk.Frame(dlg, bg=C["separator"], height=1)
        sep.pack(fill="x", padx=16, pady=8)

        res_var  = tk.StringVar(value="⏳ Apasa 'Executa Acum' pentru a testa pasul...")
        res_color = tk.StringVar(value=C["text_dim"])

        lbl_res = tk.Label(dlg,
                        textvariable=res_var,
                        bg=C["bg_main"], fg=C["text_dim"],
                        font=("Segoe UI", 11, "bold"),
                        wraplength=480)
        lbl_res.pack(pady=(0, 10))

        def _do_exec():
            """Executa pasul si afiseaza rezultatul."""
            if self.player.is_running:
                messagebox.showwarning("Debug",
                    "Playerul ruleaza deja. Opreste redarea inainte de debug.",
                    parent=dlg)
                return

            btn_exec.configure(state="disabled", text="⏳ Se executa...")
            dlg.update()

            import time
            time.sleep(0.5)  # mic delay ca userul sa mute mouse-ul daca e MOVE/CLICK

            t0 = time.time()
            ok, err = self.player._exec(step)
            dur = (time.time() - t0) * 1000

            if ok:
                res_var.set(f"✅  OK  —  Executat in {dur:.1f} ms")
                lbl_res.configure(fg=C["success"])
            else:
                res_var.set(f"❌  EROARE  —  {err}")
                lbl_res.configure(fg=C["danger"])

            btn_exec.configure(state="normal", text="▶ Executa Din Nou")

            # Logheza si in LogManager
            self.log_mgr.add(
                step.step_id,
                f"[DEBUG] {step.description or step.step_type}",
                "OK" if ok else "EROARE",
                has_error=not ok, error_msg=err,
                duration_ms=round(dur, 2), iteration=0,
            )

        # ── Butoane ───────────────────────────────────────────────
        btn_f = tk.Frame(dlg, bg=C["bg_main"])
        btn_f.pack(pady=6)

        btn_exec = tk.Button(btn_f,
                            text="▶  Executa Acum",
                            command=_do_exec,
                            bg=C["success"], fg="white",
                            activebackground=C["success_hover"],
                            activeforeground="white",
                            font=("Segoe UI", 11, "bold"),
                            relief="flat", padx=16, pady=6,
                            cursor="hand2")
        btn_exec.pack(side="left", padx=8)

        tk.Button(btn_f,
                text="✖  Inchide",
                command=dlg.destroy,
                bg=C["bg_input"], fg="white",
                activebackground=C["danger"],
                activeforeground="white",
                font=("Segoe UI", 11),
                relief="flat", padx=16, pady=6,
                cursor="hand2").pack(side="left", padx=8)

    # ── Rutine actions ────────────────────────────────────────────
    def _save_routine_dialog(self):
        """Salveaza rutina curenta."""
        steps = self.recorder.get_steps()
        if not steps:
            messagebox.showwarning("Fara pasi", "Nu exista pasi de salvat.")
            return
        name = simpledialog.askstring("Salveaza Rutina",
                                      "Numele rutinei:",
                                      parent=self.root)
        if not name:
            return
        desc = simpledialog.askstring("Descriere (optional)",
                                      "Descriere scurta:",
                                      parent=self.root) or ""
        if self.routine_mgr.save(name, steps, desc):
            messagebox.showinfo("Succes",
                                f"Rutina '{name}' salvata!\n"
                                f"Locatie: {ROUTINES_DIR}")
            self._refresh_routines()
            self._status_var.set(f"Rutina '{name}' salvata")
        else:
            messagebox.showerror("Eroare", "Nu s-a putut salva rutina.")

    def _open_routine_dialog(self):
        """Deschide dialog de incarcare rutina din fisier."""
        path = filedialog.askopenfilename(
            title="Incarca Rutina",
            initialdir=str(ROUTINES_DIR),
            filetypes=[("JSON", "*.json"), ("Toate", "*.*")],
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            steps = [StepModel.from_dict(s) for s in data.get("steps", [])]
            self._load_steps_to_ui(steps)
            self._status_var.set(f"Rutina incarcata: {Path(path).stem}")
        except Exception as e:
            messagebox.showerror("Eroare", f"Nu s-a putut incarca rutina:\n{e}")

    def _refresh_routines(self):
        """Reincarca lista de rutine."""
        for iid in self._routines_tv.get_children():
            self._routines_tv.delete(iid)
        query = self._routine_search.get().lower() if hasattr(self, "_routine_search") else ""
        for r in self.routine_mgr.list_all():
            if query and query not in r["name"].lower():
                continue
            self._routines_tv.insert("", "end", values=(
                r["name"],
                r["step_count"],
                r["created_at"][:19] if r["created_at"] else "",
                r["description"],
            ))

    def _load_selected_routine(self):
        """Incarca rutina selectata din lista."""
        sel = self._routines_tv.selection()
        if not sel:
            messagebox.showwarning("Selectie", "Selecteaza o rutina din lista.")
            return
        name  = self._routines_tv.item(sel[0], "values")[0]
        steps = self.routine_mgr.load(name)
        if steps is None:
            messagebox.showerror("Eroare", f"Nu s-a putut incarca rutina '{name}'.")
            return
        self._load_steps_to_ui(steps)
        self._nb.select(self._tab_recorder)
        self._status_var.set(f"Rutina '{name}' incarcata ({len(steps)} pasi)")

    def _load_steps_to_ui(self, steps: List[StepModel]):
        """Incarca pasii in UI (recorder + ambele treeview-uri)."""
        self.recorder.set_steps(steps)
        self._refresh_steps_tv()
        self._refresh_builder_tv()

    def _rename_routine(self):
        """Redenumeste rutina selectata."""
        sel = self._routines_tv.selection()
        if not sel:
            return
        old = self._routines_tv.item(sel[0], "values")[0]
        new = simpledialog.askstring("Redenumeste",
                                     f"Noul nume pentru '{old}':",
                                     parent=self.root)
        if new and self.routine_mgr.rename(old, new):
            self._refresh_routines()

    def _delete_routine(self):
        """Sterge rutina selectata."""
        sel = self._routines_tv.selection()
        if not sel:
            return
        name = self._routines_tv.item(sel[0], "values")[0]
        if messagebox.askyesno("Confirmare",
                               f"Stergi rutina '{name}'? Actiunea e ireversibila."):
            if self.routine_mgr.delete(name):
                self._refresh_routines()

    # ── Log actions ───────────────────────────────────────────────
    def _filter_log(self):
        """Filtreaza log-ul."""
        q = self._log_filter.get().lower()
        for iid in self._log_tv.get_children():
            vals = " ".join(str(v) for v in self._log_tv.item(iid, "values")).lower()
            if q in vals:
                self._log_tv.reattach(iid, "", "end")
            else:
                self._log_tv.detach(iid)

    def _reset_log_filter(self):
        """Reseteaza filtrul log-ului."""
        self._log_filter.set("")
        for iid in self._log_tv.get_children():
            self._log_tv.delete(iid)
        for entry in self.log_mgr.get_all():
            self._add_log_row(entry)

    def _clear_log(self):
        """Sterge tot log-ul."""
        if messagebox.askyesno("Confirmare", "Stergi tot log-ul?"):
            self.log_mgr.clear()
            for iid in self._log_tv.get_children():
                self._log_tv.delete(iid)

    def _log_rclick(self, event):
        """Meniu contextual in log."""
        iid = self._log_tv.identify_row(event.y)
        if not iid:
            return
        self._log_tv.selection_set(iid)
        menu = tk.Menu(self.root, tearoff=0,
                       bg=C["bg_card"], fg=C["text"],
                       activebackground=C["primary"],
                       activeforeground="white")
        menu.add_command(label="💬 Adauga Comentariu",
                         command=lambda: self._add_log_comment(iid))
        menu.add_command(label="⚠ Marcheaza ca Problema",
                         command=lambda: self._mark_log_error(iid))
        menu.tk_popup(event.x_root, event.y_root)

    def _add_log_comment(self, iid: str):
        """Adauga comentariu la o intrare din log."""
        vals    = self._log_tv.item(iid, "values")
        entry_id = int(vals[0])
        comment  = simpledialog.askstring("Comentariu",
                                          "Introdu comentariul:",
                                          parent=self.root)
        if comment:
            self.log_mgr.add_comment(entry_id, comment)
            new_vals = list(vals)
            new_vals[7] = comment[:30]
            self._log_tv.item(iid, values=new_vals)

    def _mark_log_error(self, iid: str):
        """Marcheaza o intrare din log ca eroare."""
        self._log_tv.item(iid, tags=("error",))

    def _export_log_xlsx(self):
        """Exporta log-ul in XLSX."""
        path = filedialog.asksaveasfilename(
            title="Export Log XLSX",
            initialdir=str(LOGS_DIR),
            defaultextension=".xlsx",
            filetypes=[("Excel", "*.xlsx")],
        )
        if path:
            if self.log_mgr.export_xlsx(path):
                messagebox.showinfo("Export", f"Log exportat:\n{path}")
            else:
                messagebox.showerror("Eroare", "Export XLSX esuat.")

    def _export_log_csv(self):
        """Exporta log-ul in CSV."""
        path = filedialog.asksaveasfilename(
            title="Export Log CSV",
            initialdir=str(LOGS_DIR),
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv")],
        )
        if path:
            self.log_mgr.export_csv(path)

    def _export_log_json(self):
        """Exporta log-ul in JSON."""
        path = filedialog.asksaveasfilename(
            title="Export Log JSON",
            initialdir=str(LOGS_DIR),
            defaultextension=".json",
            filetypes=[("JSON", "*.json")],
        )
        if path:
            self.log_mgr.export_json(path)

    # ── Excel actions ─────────────────────────────────────────────
    def _browse_excel(self):
        """Selecteaza fisierul Excel."""
        path = filedialog.askopenfilename(
            title="Selecteaza fisier Excel",
            filetypes=[("Excel", "*.xlsx *.xls"), ("Toate", "*.*")],
        )
        if path:
            self._excel_path.set(path)
            sheets = self.excel_eng.get_sheets(path)
            if self._excel_sheet_cb:
                self._excel_sheet_cb.configure(values=sheets)
            if sheets:
                self._excel_sheet.set(sheets[0])

    def _run_excel_driven(self):
        """Ruleaza rutina pe datele din Excel."""
        path = self._excel_path.get()
        if not path or not Path(path).exists():
            messagebox.showerror("Eroare", "Selecteaza un fisier Excel valid.")
            return
        steps = self.recorder.get_steps()
        if not steps:
            messagebox.showerror("Eroare", "Nu exista pasi de redat.")
            return
        data = self.excel_eng.load_data(path, self._excel_sheet.get(),
                                        self._excel_range.get())
        if not data:
            messagebox.showwarning("Date", "Nu s-au gasit date in intervalul specificat.")
            return
        self._lbl_excel_st.configure(text=f"Rulare pe {len(data)} valori...")
        self.player.play(steps, repeat=len(data))

    # ── Notes actions ─────────────────────────────────────────────
    def _note_bullet(self):
        self._notes_txt.insert("insert", "\n• ")
        self._notes_txt.focus()

    def _note_numbered(self):
        content = self._notes_txt.get("1.0", "end")
        n = sum(1 for l in content.split("\n")
                if l.strip() and l.strip()[0].isdigit()) + 1
        self._notes_txt.insert("insert", f"\n{n}. ")
        self._notes_txt.focus()

    def _note_separator(self):
        self._notes_txt.insert("insert", "\n" + "─" * 55 + "\n")

    def _save_notes(self):
        """Salveaza notitele."""
        content = self._notes_txt.get("1.0", "end-1c")
        try:
            with open(NOTES_DIR / "notite.txt", "w", encoding="utf-8") as f:
                f.write(content)
            self._status_var.set("Notite salvate")
        except Exception as e:
            messagebox.showerror("Eroare", f"Nu s-au putut salva notitele:\n{e}")

    def _load_notes(self):
        """Incarca notitele."""
        fp = NOTES_DIR / "notite.txt"
        if fp.exists():
            try:
                with open(fp, "r", encoding="utf-8") as f:
                    content = f.read()
                self._notes_txt.delete("1.0", "end")
                self._notes_txt.insert("1.0", content)
            except Exception:
                pass

    def _clear_notes(self):
        """Sterge notitele."""
        if messagebox.askyesno("Confirmare", "Stergi toate notitele?"):
            self._notes_txt.delete("1.0", "end")

    # ── Settings actions ──────────────────────────────────────────
    def _save_settings(self):
        """Salveaza toate setarile."""
        try:
            self.settings.set("step_delay",          float(self._var_delay.get()))
            self.settings.set("playback_speed",       float(self._var_speed.get()))
            self.settings.set("countdown_before_play",int(self._var_cd.get()))
            self.settings.set("repeat_count",         int(self._repeat_var.get()))
            self.settings.set("record_mouse_move",    self._var_rec_move.get())
            # v4.1: siguranta la rulare
            self.settings.set("dnd_during_run",       bool(self._var_dnd.get()))
            self.settings.set("show_run_frame",       bool(self._var_frame.get()))
            self.settings.set("guard_enabled",        bool(self._var_guard.get()))
            self.settings.set("guard_sensitivity",    self._var_guard_sens.get())
            self.run_frame.enabled = bool(self._var_frame.get())
            # Salveaza shortcut-urile
            sc = {k: v.get() for k, v in self._sc_vars.items()}
            self.settings.set("shortcuts", sc)
            # Salveaza tema
            self._set_theme(self._var_theme.get())
            # Reporneste hotkeys cu noile setari
            self.hotkey_mgr.stop()
            self._register_hotkeys()
            messagebox.showinfo("Setari", "Setarile au fost salvate cu succes!")
            self._status_var.set("Setari salvate")
        except Exception as e:
            messagebox.showerror("Eroare", f"Nu s-au putut salva setarile:\n{e}")

    def _on_delay_change(self, val):
        """Actualizeaza label-ul de delay."""
        self._lbl_delay.configure(text=f"{float(val):.1f}s")
        self.settings.set("step_delay", float(val))

    def _on_speed_change(self, val):
        """Actualizeaza label-ul de viteza."""
        self._lbl_speed.configure(text=f"{float(val):.1f}x")
        self.settings.set("playback_speed", float(val))

    def _set_theme(self, theme: str):
        """Schimba tema si reporneste aplicatia automat."""
        self.settings.set("theme", theme)
        if messagebox.askyesno("Tema",
                f"Tema '{theme}' va fi aplicata.\nAplicatia se va reporni acum. Continui?"):
            import sys, os
            self.root.destroy()
            os.execv(sys.executable, [sys.executable] + sys.argv)

    def _open_settings_tab(self):
        """Deschide tab-ul de setari."""
        self._nb.select(self._tab_settings)

    def _open_shortcuts_dialog(self):
        """Deschide fereastra floating cu shortcut-urile."""
        self._floating_sc.show()

    def _show_quick_guide(self):
        """Afiseaza ghidul rapid."""
        self._nb.select(self._tab_help)

    def _show_about(self):
        """Afiseaza informatii despre aplicatie."""
        messagebox.showinfo(
            f"Despre {APP_NAME}",
            f"{APP_NAME} v{APP_VERSION}\n\n"
            f"Autor: {APP_AUTHOR}\n"
            f"Realizat cu ajutorul unui asistent AI\n\n"
            f"Tool RPA pentru automatizarea task-urilor repetitive.\n"
            f"Inregistreaza, salveaza si ruleaza rutine mouse/tastatura.\n\n"
            f"Fisiere salvate in:\n{BASE_DIR}"
        )

    # ── Inchidere ─────────────────────────────────────────────────
    def _toggle_debug_visual(self):
        """[v3.9] Activeaza/dezactiveaza debug visual overlay."""
        try:
            val = bool(self._debug_var.get())
        except Exception:
            return
        self.settings.set("debug_visual", val)
        self._debug_mode = val
        if val:
            self.debug_overlay.enable()
        else:
            self.debug_overlay.disable()


    def _toggle_shortcuts_panel(self):
        """[v3.9] Afiseaza/ascunde panoul lateral cu shortcut-urile."""
        if hasattr(self, "_sc_side_panel"):
            try:
                if self._sc_side_panel.winfo_exists():
                    self._sc_side_panel.destroy()
                    self._btn_sc.configure(bg=C["bg_input"], fg=C["text"])
                    return
            except Exception:
                pass

        sc = self.settings.get("shortcuts", DEFAULT_SHORTCUTS)
        panel = tk.Toplevel(self.root)
        panel.title("Shortcut-uri")
        panel.attributes("-topmost", True)
        panel.configure(bg=C["bg_card"])
        panel.resizable(False, True)
        self.root.update_idletasks()
        rx = self.root.winfo_x() + self.root.winfo_width()
        ry = self.root.winfo_y()
        panel.geometry("260x540+%d+%d" % (rx, ry))
        self._sc_side_panel = panel

        tk.Label(panel, text="\u2328  Shortcut-uri AutoPilot DC",
                 bg=C["primary"], fg="white",
                 font=("Segoe UI", 11, "bold")).pack(fill="x", ipady=8)

        sc_list = [
            ("Inregistrare",    sc.get("start_rec",      "Ctrl+Alt+Shift+0")),
            ("Stop Inreg.",     sc.get("stop_rec",       "F6")),
            ("Ruleaza",         sc.get("play",           "F7")),
            ("Pauza / Reia",    sc.get("pause",          "F8")),
            ("Stop Redare",     sc.get("stop_play",      "F9")),
            ("Stop Urgenta",    sc.get("emergency",      "F12")),
            ("Salveaza",        sc.get("save",           "Ctrl+S")),
            ("Rutina Noua",     sc.get("new",            "Ctrl+N")),
            ("Deschide",        sc.get("open",           "Ctrl+O")),
            ("Adauga Delay",    sc.get("add_delay",      "Ctrl+D")),
            ("Adauga Pas",      sc.get("add_step",       "Ctrl+M")),
            ("Sterge Pas",      sc.get("delete_step",    "Delete")),
            ("Skip Pas",        sc.get("skip_step",      "Ctrl+K")),
            ("Debug Pas",       sc.get("debug_step",     "Ctrl+Shift+B")),
            ("Editeaza Pas",    sc.get("edit_step",      "Ctrl+E")),
            ("Muta Sus",        sc.get("move_step_up",   "Ctrl+Up")),
            ("Muta Jos",        sc.get("move_step_down", "Ctrl+Down")),
            ("Shortcut-uri",    sc.get("show_shortcuts", "Ctrl+H")),
            ("Iesire",          "Alt+F4"),
        ]

        for i, (label, combo) in enumerate(sc_list):
            row_bg = C["bg_main"] if i % 2 == 0 else C["bg_card"]
            fr = tk.Frame(panel, bg=row_bg)
            fr.pack(fill="x", pady=1)
            tk.Label(fr, text=label,
                     bg=row_bg, fg=C["text"],
                     font=("Segoe UI", 9), anchor="w",
                     width=18).pack(side="left", padx=(8, 4), pady=4)
            tk.Label(fr, text=combo,
                     bg=row_bg, fg=C["accent"],
                     font=("Consolas", 9, "bold"), anchor="e").pack(side="right", padx=8)

        tk.Button(panel, text="Inchide", command=panel.destroy,
                  bg=C["bg_input"], fg=C["text"],
                  font=("Segoe UI", 9), relief="flat",
                  padx=8, pady=4, cursor="hand2").pack(fill="x", padx=8, pady=6)

        self._btn_sc.configure(bg=C["primary"], fg="white")
        panel.protocol("WM_DELETE_WINDOW", lambda: (
            panel.destroy(),
            self._btn_sc.configure(bg=C["bg_input"], fg=C["text"])
        ))

    # ── v4.1: tray ────────────────────────────────────────────────
    def _hide_to_tray(self) -> bool:
        if not app_shell.tray_available() or not self.tray.show():
            return False
        self.root.withdraw()
        if not self._tray_hint_shown:
            self._tray_hint_shown = True
            self.tray.notify("AutoPilot DC ruleaza in continuare aici. Click pe pictograma ca sa-l deschizi; "
                             "Iesire din meniul pictogramei il inchide.")
        return True

    def _show_from_tray(self):
        self.root.deiconify()
        self.root.lift()
        self.root.attributes("-topmost", True)
        self.root.after(300, lambda: self.root.attributes("-topmost", False))
        self.root.focus_force()
        if not self.settings.get("close_to_tray", False):
            self.tray.hide()

    def _quit_app(self):
        """Inchidere reala (din meniul tray / Fisier → Iesire)."""
        self._show_from_tray()
        self._really_quit = True
        self._on_close()
        self._really_quit = False

    def _on_close(self):
        """Gestioneaza inchiderea aplicatiei cu dialog de salvare."""
        if self.settings.get("close_to_tray", False) and not self._really_quit and self._hide_to_tray():
            return  # ✕ ascunde aplicatia langa ceas (rularile si scurtaturile F7/F12 merg in continuare)
        if self._studio is not None:
            if self._studio.busy:
                self._studio.stop()
            if not self._studio.confirm_discard():
                return

        steps = self.recorder.get_steps()

        # Daca e inregistrare activa SAU exista pasi nesalvati
        if self._is_recording or steps:
            # Dialog custom mai frumos decat messagebox simplu
            dlg = tk.Toplevel(self.root)
            dlg.title("Inchidere AutoPilot DC")
            dlg.geometry("420x200")
            dlg.resizable(False, False)
            dlg.grab_set()
            dlg.attributes("-topmost", True)
            dlg.configure(bg=C["bg_main"])

            # Centreaza dialogul pe ecran
            dlg.update_idletasks()
            sw = self.root.winfo_screenwidth()
            sh = self.root.winfo_screenheight()
            x = (sw - 420) // 2
            y = (sh - 200) // 2
            dlg.geometry(f"420x200+{x}+{y}")

            msg = "Inregistrarea este ACTIVA!\n" if self._is_recording else ""
            msg += f"Ai {len(steps)} pasi inregistrati nesalvati.\nVrei sa salvezi rutina inainte de iesire?"

            tk.Label(dlg,
                    text="⚠  Atentie!",
                    bg=C["bg_main"], fg=C["warning"],
                    font=("Segoe UI", 13, "bold")).pack(pady=(18, 4))

            tk.Label(dlg,
                    text=msg,
                    bg=C["bg_main"], fg=C["text"],
                    font=("Segoe UI", 10),
                    wraplength=380, justify="center").pack(pady=(0, 14))

            btn_f = tk.Frame(dlg, bg=C["bg_main"])
            btn_f.pack()

            result: dict = {"action": None}

            def _save_and_close():
                result["action"] = "save"
                dlg.destroy()

            def _close_without_save():
                result["action"] = "close"
                dlg.destroy()

            def _cancel():
                result["action"] = "cancel"
                dlg.destroy()

            tk.Button(btn_f,
                    text="💾  Salveaza si Iesi",
                    command=_save_and_close,
                    bg=C["primary"], fg="white",
                    activebackground=C["primary"],
                    activeforeground="white",
                    font=("Segoe UI", 10, "bold"),
                    relief="flat", padx=12, pady=6,
                    cursor="hand2").pack(side="left", padx=6)

            tk.Button(btn_f,
                    text="🚪  Iesi fara Salvare",
                    command=_close_without_save,
                    bg=C["danger"], fg="white",
                    activebackground=C["danger_hover"],
                    activeforeground="white",
                    font=("Segoe UI", 10),
                    relief="flat", padx=12, pady=6,
                    cursor="hand2").pack(side="left", padx=6)

            tk.Button(btn_f,
                    text="  ✖  Anuleaza   ",
                    command=_cancel,
                    bg=C["bg_input"], fg=C["text"],
                    activebackground=C["bg_card"],
                    activeforeground=C["text"],
                    font=("Segoe UI", 10, "bold"),
                    relief="flat", padx=12, pady=6,
                    width=20,           # <-- Latime buton
                    cursor="hand2").pack(side="left", padx=6)

            dlg.wait_window()

            if result["action"] == "cancel" or result["action"] is None:
                return  # Nu inchide aplicatia

            if result["action"] == "save":
                # Opreste inregistrarea daca e activa
                if self._is_recording:
                    self.recorder.stop()
                    self._is_recording = False
                # Deschide dialogul de salvare
                self._save_routine_dialog()

        # Curatare si inchidere
        if self._is_recording:
            self.recorder.stop()
        if self.player.is_running:
            self.player.emergency_stop()
        self._hide_recording_indicator()
        self.run_frame.hide()
        DoNotDisturb.restore_all()  # v4.1: notificarile revin chiar daca o rulare nu s-a terminat
        self.hotkey_mgr.stop()
        self._floating_sc.hide()
        self._save_notes()
        self.tray.hide()
        self.root.destroy()

# ==============================================================================
# SECTIUNEA 16: PUNCT DE INTRARE (ENTRY POINT)
# ==============================================================================

def main():
    """
    [ENTRY POINT] Porneste aplicatia AutoPilot DC.
    Initializeaza logging, CustomTkinter si fereastra principala.
    """
    # 16.1 — Configureaza logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[logging.StreamHandler()],
    )
    logging.info(f"Pornire {APP_NAME} v{APP_VERSION}")
    logging.info(f"Director de lucru: {BASE_DIR}")

    # 16.1b — v4.1: daca o rulare anterioara a ramas cu "Nu deranja" pornit, readucem notificarile
    DoNotDisturb.recover_if_needed()   # nu blocheaza: lucratorul se ocupa in fundal

    # 16.2 — Creeaza si porneste aplicatia
    app = MainWindow()
    app.run()


if __name__ == "__main__":
    main()
