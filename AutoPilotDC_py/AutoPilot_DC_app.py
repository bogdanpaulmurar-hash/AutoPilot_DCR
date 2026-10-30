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
import i18n       # v4.7: romana / engleza / germana (limba din Setari)
import ui_theme   # v4.14: marimea textului, contrast automat
i18n.install()
import video_ui   # v4.8: 🎥 inregistrare video a ecranului + editor
from autopilot_safety import DoNotDisturb, RunFrame, SafetyGuard
from rpr.legacy import recorded_to_nodes   # v4.16: ⏺ Ecran -> pasi Studio

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
APP_AUTHOR  = "Bogdan Murar"

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
    "accent":         "#3DA9E0",
    "success":        "#1F8F4E",
    "success_hover":  "#17733E",
    "warning":        "#FF8800",
    "danger":         "#CC0000",
    "danger_hover":   "#AA0000",
    "emergency":      "#8B0000",
    "text":           "#FFFFFF",
    "text_dim":       "#B4B4D0",
    "text_muted":     "#8A8AAA",
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
    "success":        "#1F8F4E",
    "success_hover":  "#17733E",
    "warning":        "#FF8800",
    "danger":         "#CC0000",
    "danger_hover":   "#AA0000",
    "emergency":      "#8B0000",
    "text":           "#1B1B2E",
    "text_dim":       "#444466",
    "text_muted":     "#6E6E80",
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
        self.ignore: Optional[Callable] = None   # v4.16: pas -> True = nu se inregistreaza

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
        if self.ignore is not None and self.ignore(step):
            return   # v4.16: ex. click pe fereastra AutoPilot DC (⏹ Stop)
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


class FlowFrame(tk.Frame):
    """[v4.1] Bara de actiuni: grupurile de butoane trec pe randul urmator cand nu incap."""

    def __init__(self, master, **kw):
        super().__init__(master, **kw)
        self._items = []
        self._last = None
        self._compact = False
        self._full_w = {}          # latimea grupurilor cu textul intreg (masurata in modul normal)
        self._labels = []          # (buton, text intreg, text scurt)
        self.bind("<Configure>", lambda e: self._relayout())

    def compactable(self, button, full: str, short: str):
        """v4.14: pe ecrane inguste butonul arata doar textul scurt (iconita)."""
        if short and short != full:
            self._labels.append((button, full, short))

    def _set_compact(self, on: bool):
        self._compact = on
        for b, full, short in self._labels:
            try:
                b.configure(text=short if on else full)
            except tk.TclError:
                pass
        self.update_idletasks()

    def set_items(self, items):
        for w in self._items:
            w.place_forget()
        if self._compact:          # masuram din nou cu textul intreg (alt mod = alte butoane)
            self._set_compact(False)
        self._items = list(items)
        self._last = None
        self.after_idle(self._relayout)

    def _relayout(self):
        width = self.winfo_width()
        if width <= 1:
            width = self.master.winfo_width()
        if width > 1 and self._items:
            if not self._compact:
                self._full_w = {id(w): w.winfo_reqwidth() for w in self._items}
            need = sum(self._full_w.get(id(w), w.winfo_reqwidth()) + 6 for w in self._items)
            if not self._compact and need > width:
                self._set_compact(True)
            elif self._compact and need + 12 <= width:
                self._set_compact(False)
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
    [GUI] Fereastra principala a aplicatiei AutoPilot DC (v4.16).
    Un singur loc de lucru: Studio RPR. Fostul tab Recorder a intrat in Studio (⏺ Ecran: mouse si tastatura
    inregistrate ca pasi pe ecran). Setarile aplicatiei si 📖 Instructiunile se deschid in ferestre proprii,
    din butoanele mici din dreapta barei de sus.
    """

    def __init__(self):
        """Initializeaza fereastra principala si toate componentele."""

        # ── Managers ──────────────────────────────────────────────
        self.settings     = SettingsManager()
        self.recorder     = RecorderEngine(self.settings)
        self.hotkey_mgr   = HotkeyManager()

        # ── Tema ──────────────────────────────────────────────────
        global C
        theme = self.settings.get("theme", "dark")
        C = COLORS_DARK if theme == "dark" else COLORS_LIGHT
        if theme == "light":
            C.update(COLORS_LIGHT)

        # ── Fereastra CTk ─────────────────────────────────────────
        ctk.set_appearance_mode("dark" if theme == "dark" else "light")
        ctk.set_default_color_theme("blue")
        app_shell.set_app_id()          # iconita AutoPilot in bara de activitati (nu cea a lui Python)
        self.root = ctk.CTk()
        # v4.14: marimea textului (Setari Studio → Aspect) si contrast automat in orice fereastra
        ui_theme.apply_scaling(self.root)
        ui_theme.install_contrast_guard(self.root)
        app_shell.apply_icon(self.root)
        self._start_in_tray = "--tray" in sys.argv
        self._really_quit = False
        self._tray_hint_shown = False
        # v4.8: 🎥 filme (manual sau la rularea rutinelor)
        self.video = video_ui.VideoController(self.root, C, on_status=lambda m: self._status_var.set(m))
        try:   # 🎬 dublu-click pe un film .apvid (sau linkul din Excel) il deschide in player
            video_ui.register_file_type()
        except Exception:  # noqa: BLE001
            pass
        try:   # 📂 rutinele din folderul setat se citesc in fundal la pornire (Managerul de rutine le are gata)
            from rpr.batch import preload
            from rpr.drivers.registry import StudioSettings
            preload(StudioSettings.load().effective_routines_folder())
        except Exception:  # noqa: BLE001 — nu oprim pornirea aplicatiei
            pass
        self.tray = app_shell.Tray(
            ui_call=lambda fn: self.root.after(0, fn),
            items=[("🧩 Studio RPR", self._show_from_tray, False),
                   ("⏺ Inregistrare pe ecran (start / stop)", self._toggle_recording, True),
                   ("🎥 Inregistrare video (start / stop)", lambda: self.video.toggle_manual(), False),
                   ("🚨 STOP URGENTA", self._emergency_stop, True),
                   ("Iesire", self._quit_app, True)],
            on_open=self._show_from_tray)
        self.root.title(f"{APP_NAME} v{APP_VERSION}")
        # v4.14: pe ecrane mici (laptop 1366x768) fereastra porneste maximizata, iar minimul e mai mic
        sw, sh = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        self.root.geometry(f"{min(1400, int(sw * 0.92))}x{min(880, int(sh * 0.88))}")
        self.root.minsize(min(900, sw - 40), min(560, sh - 80))
        if sw <= 1440 or sh <= 900:
            try:
                self.root.state("zoomed")
            except tk.TclError:
                pass
        # v4.1: chenar RUN/REC
        self.run_frame = RunFrame(self.root)
        self.run_frame.enabled = bool(self.settings.get("show_run_frame", True))
        self.root.configure(fg_color=C["bg_main"])

        # ── Stare ─────────────────────────────────────────────────
        self._is_recording = False
        self._rec_bar = None
        self._rec_dnd = False
        self._studio = None
        self._help_win = None
        self._settings_win = None
        self._status_var = i18n.TrVar(value="Gata")      # texte afisate: se traduc la set()

        # ── Interfata ─────────────────────────────────────────────
        self._build_styles()
        self._build_toolbar()
        self._build_statusbar()
        self._workspace = tk.Frame(self.root, bg=C["bg_main"])
        self._workspace.pack(fill="both", expand=True)
        self._connect_callbacks()
        self._show_studio()
        self.root.after(600, lambda: ui_theme.fix_contrast(self.root))   # v4.14: niciun text greu de citit

        # ── Taste ─────────────────────────────────────────────────
        self._register_hotkeys()
        st = self._studio_call
        self.root.bind("<Control-n>", lambda e: st("new_routine"))
        self.root.bind("<Control-o>", lambda e: st("open_routine"))
        self.root.bind("<Control-s>", lambda e: st("save_routine"))
        self.root.bind("<F1>", lambda e: self._show_help())
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
        # pictograma langa ceas: mereu, cat timp aplicatia ruleaza
        tray_ok = self.tray.show()
        if self._start_in_tray and tray_ok:
            self.root.withdraw()   # pornit cu Windows: fara fereastra, doar pictograma
        else:
            if self._start_in_tray:
                print("[tray] pornire in tray imposibila, deschid fereastra: " + self.tray.last_error)
            self.root.after(300, _bring_to_front)
        self.root.after(1500, self._offer_resume)   # v4.8.4: rulare intrerupta de o inchidere neasteptata?
        self.root.mainloop()

    # ==========================================================================
    # BARA DE SUS (un singur rand: titlu, comenzile Studio, butoanele mici din dreapta)
    # ==========================================================================
    def _build_styles(self):
        style = ttk.Style()
        style.theme_use("clam")
        # v4.14: toate listele (si cele "readonly") cu culorile temei: fara text alb pe fundal alb
        ui_theme.style_combobox(style, "TCombobox", C)
        ui_theme.style_popdown(self.root, C)

    def _studio_call(self, name: str, *args):
        if self._studio is not None:
            return getattr(self._studio, name)(*args)
        return None

    def _build_toolbar(self):
        """[v4.16] Bara de sus pe un rand: 'AutoPilot DC' · comenzile Studio (trec pe randul urmator / devin
        iconite cand nu incap) · in dreapta butoane mici: 🎥 🎬 📖 ⚙ ✕ si STOP URGENTA."""
        hdr = tk.Frame(self.root, bg=C["bg_card"])
        hdr.pack(fill="x", side="top")
        self._toolbar = hdr

        tk.Label(hdr, text="AutoPilot DC", bg=C["bg_card"], fg=C["primary"],
                 font=("Segoe UI", 13, "bold")).pack(side="left", padx=(12, 8), pady=6)

        def hbtn(text, cmd, bg=None, fg=None, tip=""):
            b = tk.Button(hdr, text=text, command=cmd, bg=bg or C["bg_input"], fg=fg or C["text"],
                          activebackground=C["primary"], activeforeground="white", relief="flat", bd=0,
                          font=("Segoe UI", 10), padx=8, pady=4, cursor="hand2")
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
        ToolTip(self._btn_emg, "Opreste imediat rularea si inregistrarea", "F12")
        self._btn_exit = hbtn("✕", self._on_close, bg=C["bg_main"], fg=C["text_dim"], tip="Inchide aplicatia")
        hbtn("⚙", self._open_settings_window, tip="Setari aplicatie: siguranta, scurtaturi, pornire, tema, video, "
                                                  "limba, backup")
        hbtn("📖", self._show_help, tip="📖 Instructiuni: toate procedurile, pe scurt, cu exemple (RO / EN / DE) — F1")
        hbtn("🎬", lambda: self.video.open_file(), tip="Deschide un film inregistrat (redare, editare, export GIF / MP4)")
        self._btn_video = hbtn("🎥", lambda: self.video.toggle_manual(),
                               tip="Inregistreaza ecranul acum (fara rutina); apasa din nou ca sa opresti. "
                                   "Filmele: ⚙ Setari → Video")
        tk.Frame(hdr, bg=C["border"], width=1).pack(side="right", fill="y", padx=6, pady=8)

        # ── comenzile Studio (in mijlocul randului) ──
        self._actions = FlowFrame(hdr, bg=C["bg_card"], height=40)
        self._actions.pack(side="left", fill="x", expand=True)
        groups = []

        def group(title):
            # grupurile se despart printr-o linie subtire; titlul grupului apare in tooltip-ul fiecarui buton
            g = tk.Frame(self._actions, bg=C["bg_card"])
            if groups:
                tk.Frame(g, bg=C["border"], width=1).pack(side="left", fill="y", padx=(0, 6), pady=4)
            row = tk.Frame(g, bg=C["bg_card"])
            row.pack(side="left")
            setattr(row, "_title", title)
            groups.append(g)
            return row

        def abtn(row, text, cmd, bg=None, tip="", sc="", short=None):
            bg = bg or C["bg_input"]
            b = tk.Button(row, text=text, command=cmd, bg=bg, fg=_btn_fg(bg), activebackground=C["primary"],
                          activeforeground="white", relief="flat", bd=0, font=("Segoe UI", 10),
                          padx=9, pady=4, cursor="hand2", highlightthickness=0)
            b.pack(side="left", padx=2, pady=2)
            setattr(b, "_orig_bg", bg)
            setattr(b, "_orig_fg", _btn_fg(bg))
            # pe ecrane inguste butonul ramane doar cu iconita (textul intreg e in tooltip)
            self._actions.compactable(b, text, short if short is not None else text.split(" ")[0])
            title = getattr(row, "_title", "")
            tr = i18n.tr
            full_tip = (f"{tr(text).strip()} — {tr(tip)}" if tip else tr(text).strip())
            ToolTip(b, (f"[{tr(title)}] " if title else "") + full_tip, sc)
            return b

        def more_btn(row, items):
            """⋯ : comenzile folosite mai rar, intr-un meniu (bara ramane aerisita)."""
            mb = tk.Menubutton(row, text="⋯", bg=C["bg_input"], fg=C["text"], relief="flat", bd=0,
                               font=("Segoe UI", 11, "bold"), padx=10, pady=2, cursor="hand2",
                               activebackground=C["primary"], activeforeground="white")
            menu = tk.Menu(mb, tearoff=0, bg=C["bg_card"], fg=C["text"], activebackground=C["primary"],
                           activeforeground="white", font=("Segoe UI", 10))
            for label, cmd in items:
                if label == "-":
                    menu.add_separator()
                else:
                    menu.add_command(label=label, command=cmd)
            mb.configure(menu=menu)
            mb.pack(side="left", padx=2, pady=2)
            ToolTip(mb, "Mai multe comenzi", "")
            return mb

        sc = self.settings.get("shortcuts", DEFAULT_SHORTCUTS)
        st = lambda name, *a: (lambda: self._studio_call(name, *a))  # noqa: E731
        r = group("RUTINA")
        abtn(r, "📄 Nou", st("new_routine"), None, "Rutina noua (Ctrl+N)")
        abtn(r, "📂 Deschide", st("open_routine"), None, "Deschide o rutina .rpr.json (sau una veche, se converteste)",
             "Ctrl+O")
        abtn(r, "💾 Salveaza", st("save_routine"), C["primary"], "Salveaza rutina", "Ctrl+S", short="💾 Salveaza")
        abtn(r, "🗂 Manager rutine", st("show_routine_manager"), None,
             "Rutinele din folderul setat (citite la pornire) si pregatirile: mai multe rutine rulate una dupa alta, "
             "cu film, raport Excel si documentatie", short="🗂 Manager")
        more_btn(r, [("Salveaza ca…", st("save_routine", True)),
                     ("📥 Importa pasi (text / JSON de la AI)…", st("show_import")),
                     ("🎯 Completeaza obiectele rutinei…", st("show_complete_objects")),
                     ("📚 Exemple", st("show_examples")),
                     ("-", None),
                     ("🕒 Programeaza", st("show_schedule"))])
        r = group("RULARE")
        abtn(r, "▶ Ruleaza", st("run"), C["success"], "Ruleaza rutina", sc.get("play", "F7"), short="▶ Ruleaza")
        abtn(r, "⏭ Pas cu pas", st("run", True), None, "Fiecare apasare executa un singur pas")
        abtn(r, "⏸ Pauza", st("toggle_pause"), C["warning"], "Pauza / reluare", sc.get("pause", "F8"))
        abtn(r, "⏹ Stop", st("stop"), C["danger"], "Opreste rutina", sc.get("stop_play", "F9"), short="⏹ Stop")
        r = group("OBIECTE (SPY) SI INREGISTRARE")
        abtn(r, "🎯 Web", lambda: self._studio_call("spy", "Web"), None, "Marcheaza un element din browser",
             short="🎯 Web")
        abtn(r, "🎯 SAP", lambda: self._studio_call("spy", "SAP"), None, "Marcheaza un camp / buton SAP",
             short="🎯 SAP")
        abtn(r, "🎯 Desktop", lambda: self._studio_call("spy", "Desktop"), None,
             "Marcheaza un element dintr-o aplicatie Windows", short="🎯 Desktop")
        abtn(r, "⏺ Inregistreaza Web", st("record_web"), C["danger"],
             "Lucrezi normal in browser; fiecare click / text / optiune devine un pas pe obiect. Apasa din nou (sau "
             "Esc in browser) ca sa opresti.", short="⏺ Web")
        self._btn_rec = abtn(r, "⏺ Ecran", self._toggle_recording, C["danger"],
                             "Inregistreaza mouse-ul si tastatura in orice aplicatie (pe coordonate de ecran, ca "
                             "fostul Recorder). Pasii intra in rutina, intr-un grup, dupa pasul selectat. "
                             "Opresti cu F6 sau din bara mica de sus.", sc.get("start_rec", "F5"), short="⏺ Ecran")
        r = group("RUTINA CURENTA")
        abtn(r, "⚙ Rutina", st("show_routine_settings"), None, "Setarile rutinei si variabilele", short="⚙ Rutina")
        abtn(r, "🌐 Setari Studio", st("show_settings"), None,
             "Browserul, marimea textului, unde se salveaza fisierele, aplicatia pentru filme", short="🌐 Studio")
        self._actions.set_items(groups)

    def _build_statusbar(self):
        """Bara de jos: inregistrare, mesajul curent, versiunea."""
        sb = tk.Frame(self.root, bg=C["bg_card"], height=28)
        sb.pack(fill="x", side="bottom")
        sb.pack_propagate(False)
        self._rec_indicator = tk.Label(sb, text="⬤ STANDBY", bg=C["bg_card"], fg=C["text_muted"],
                                       font=("Segoe UI", 10, "bold"))
        self._rec_indicator.pack(side="left", padx=10)
        tk.Frame(sb, bg=C["border"], width=1).pack(side="left", fill="y", pady=4)
        tk.Label(sb, textvariable=self._status_var, bg=C["bg_card"], fg=C["text"],
                 font=("Segoe UI", 10)).pack(side="left", padx=10)
        tk.Label(sb, text=f"{APP_NAME} v{APP_VERSION}", bg=C["bg_card"], fg=C["text_muted"],
                 font=("Segoe UI", 9)).pack(side="right", padx=10)

    # ==========================================================================
    # ZONA DE LUCRU: Studio + ferestrele 📖 Instructiuni si ⚙ Setari
    # ==========================================================================
    def _show_studio(self):
        if self._studio is None:
            try:
                from studio_ui import StudioPanel
                self._studio = StudioPanel(self._workspace, C, run_frame=self.run_frame,
                                           on_status=self._status_var.set,
                                           dnd_allowed=lambda: bool(self.settings.get("dnd_during_run", True)),
                                           video=self.video, on_help=self._show_help)
            except Exception as ex:
                import traceback
                traceback.print_exc()
                messagebox.showerror("Studio RPR", f"Studio nu a putut porni:\n{ex}")
                return
            self._studio.pack(fill="both", expand=True)

    def _set_mode(self, mode: str):
        """Compatibilitate (tray, filmele din Instructiuni): exista o singura zona de lucru, Studio."""
        if mode == "help":
            self._show_help()
        else:
            self._show_studio()

    def _show_help(self):
        """📖 Instructiuni intr-o fereastra proprie (Studio ramane deschis langa ea)."""
        if self._help_win is not None and self._help_win.winfo_exists():
            self._help_win.deiconify()
            self._help_win.lift()
            return
        from instructions_ui import InstructionsPanel
        win = tk.Toplevel(self.root)
        win.title("📖 Instructiuni")
        win.configure(bg=C["bg_main"])
        app_shell.apply_icon(win)
        ui_theme.fit_window(win, 1150, 780)
        InstructionsPanel(win, C).pack(fill="both", expand=True)
        win.bind("<Escape>", lambda e: win.destroy())
        self._help_win = win

    def _open_settings_window(self):
        """⚙ Setarile aplicatiei, intr-o fereastra proprie."""
        if self._settings_win is not None and self._settings_win.winfo_exists():
            self._settings_win.deiconify()
            self._settings_win.lift()
            return
        win = tk.Toplevel(self.root)
        win.title("⚙ Setari aplicatie")
        win.configure(bg=C["bg_main"])
        app_shell.apply_icon(win)
        ui_theme.fit_window(win, 860, 780)
        self._settings_win = win
        self._build_settings(win)
        ui_theme.fix_contrast(win)

    # ==========================================================================
    # SETARI APLICATIE
    # ==========================================================================
    def _build_settings(self, parent):
        """Setarile aplicatiei (fostul tab ⚙ Setari al Recorderului)."""
        canvas = tk.Canvas(parent, bg=C["bg_main"], highlightthickness=0)
        vsb    = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        canvas.pack(fill="both", expand=True)
        bind_scroll(canvas, canvas)

        inner = tk.Frame(canvas, bg=C["bg_main"])
        cw = canvas.create_window((0, 0), window=inner, anchor="nw")
        inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: (canvas.itemconfigure(cw, width=e.width),
                                              canvas.configure(scrollregion=canvas.bbox("all"))))
        inner.bind("<Enter>", lambda e: bind_scroll(inner, canvas), add="+")

        tk.Label(inner, text="⚙  Setari aplicatie", bg=C["bg_main"], fg=C["primary"],
                 font=("Segoe UI", 14, "bold")).pack(pady=(12, 4))

        def section(title):
            tk.Label(inner, text=title, bg=C["bg_main"], fg=C["primary"],
                     font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=12, pady=(10, 2))
            f = tk.Frame(inner, bg=C["bg_card"])
            f.pack(fill="x", padx=8, pady=2)
            return f

        def row(f, label, widget_fn):
            r = tk.Frame(f, bg=C["bg_card"])
            r.pack(fill="x", padx=12, pady=4)
            tk.Label(r, text=label, bg=C["bg_card"], fg=C["text_dim"],
                     font=("Segoe UI", 11), width=28, anchor="w").pack(side="left")
            widget_fn(r)

        def note(f, text):
            tk.Label(f, text=text, bg=C["bg_card"], fg=C["text_dim"], font=("Segoe UI", 9), wraplength=720,
                     justify="left").pack(anchor="w", padx=12, pady=(2, 8))

        # ── ⏺ Inregistrare pe ecran ──
        f_rec = section("⏺  Inregistrare pe ecran (⏺ Ecran)")
        self._var_rec_move = tk.BooleanVar(value=bool(self.settings.get("record_mouse_move", False)))
        self._var_move_thr = tk.IntVar(value=int(self.settings.get("mouse_move_threshold", 5) or 5))
        row(f_rec, "Inregistreaza miscari mouse:", lambda p: tk.Checkbutton(
            p, variable=self._var_rec_move, bg=C["bg_card"], selectcolor=C["bg_input"],
            activebackground=C["bg_card"]).pack(side="left"))
        row(f_rec, "Prag miscare mouse (px):", lambda p: tk.Spinbox(
            p, from_=1, to=50, width=8, textvariable=self._var_move_thr,
            bg=C["bg_input"], fg=C["text"], font=("Segoe UI", 11),
            relief="flat", buttonbackground=C["bg_card"], insertbackground=C["text"]).pack(side="left"))
        note(f_rec, "Click-urile, scroll-ul si tastele din orice aplicatie devin pasi pe ecran in rutina din Studio. "
                    "Literele scrise una dupa alta devin un singur pas \"Scrie\". Click-urile pe AutoPilot DC nu se "
                    "inregistreaza.")

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

        def _diagnose_dnd():
            real = messagebox.askyesno(
                "Nu deranja", "Fac si un test real? \"Nu deranja\" porneste si se opreste o data "
                              "(cateva secunde).\n\nNu = doar citesc setarile.")
            self._status_var.set("Verific \"Nu deranja\"...")

            def work():
                from autopilot_safety import diagnose_dnd
                try:
                    text = diagnose_dnd(real)
                except Exception as ex:  # noqa: BLE001
                    text = f"Diagnosticul a esuat: {ex}"
                path = LOGS_DIR / "nu_deranja_diagnostic.txt"
                try:
                    LOGS_DIR.mkdir(parents=True, exist_ok=True)
                    path.write_text(text, encoding="utf-8")
                except OSError:
                    pass
                self.root.after(0, lambda: self._show_text_dialog("Nu deranja — diagnostic", text, str(path)))
            threading.Thread(target=work, daemon=True).start()
        row(f_safe, "Nu deranja nu merge?", lambda p: tk.Button(
            p, text="🔍 Verifica Nu deranja", command=_diagnose_dnd,
            bg=C["bg_input"], fg=C["text"], relief="flat", font=("Segoe UI", 10), padx=8,
            cursor="hand2").pack(side="left"))
        row(f_safe, "Sensibilitate preventie:", lambda p: ttk.Combobox(
            p, textvariable=self._var_guard_sens, values=["relaxed", "normal", "strict"],
            state="readonly", width=12).pack(side="left"))
        note(f_safe, "Verifica inainte de fiecare pas: mouse miscat de tine, ferestre de eroare, "
                     "aplicatie care nu raspunde, click in alta aplicatie, zona click-ului diferita "
                     "(relaxed 35% · normal 22% · strict 12%), taste trimise in alta fereastra. "
                     "Un pas esuat nu mai e sarit in tacere: rutina se opreste si te intreaba. "
                     "Verificarea ecranului functioneaza pentru pasii inregistrati cu versiunea 4.1+.")

        # ── Scurtaturi (taste globale) ──
        f_sc = section("⌨  Shortcut-uri")
        sc = self.settings.get("shortcuts", DEFAULT_SHORTCUTS)
        self._sc_vars: Dict[str, tk.StringVar] = {}
        sc_labels = {
            "start_rec":  "⏺ Ecran (start / stop):",
            "stop_rec":   "Stop inregistrare:",
            "play":       "Ruleaza Rutina:",
            "pause":      "Pauza:",
            "stop_play":  "Stop rutina:",
            "emergency":  "Stop Urgenta:",
        }
        for key, label in sc_labels.items():
            var = tk.StringVar(value=sc.get(key, DEFAULT_SHORTCUTS.get(key, "")))
            self._sc_vars[key] = var
            row(f_sc, label, lambda p, v=var: tk.Entry(
                p, textvariable=v, width=14, bg=C["bg_input"], fg=C["text"], font=("Segoe UI", 11),
                relief="flat", insertbackground=C["text"]).pack(side="left"))
        note(f_sc, "Merg si cand AutoPilot DC nu e fereastra activa. In plus: Ctrl+N / Ctrl+O / Ctrl+S in Studio, "
                   "F1 = Instructiuni.")

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
        tray_state = ("Pictograma din tray: ✔ activa (pe Windows 10/11 poate fi ascunsa sub sageata ^ de langa ceas — "
                      "o poti trage pe bara)." if self.tray.visible else
                      "Pictograma din tray: ✖ " + (self.tray.last_error or "nu e afisata."))
        tk.Label(f_start, text=(i18n.tr(tray_state) + "\n" +
                                i18n.tr("Setarile se aplica imediat. Pornirea cu Windows foloseste contul tau (fara "
                                        "drepturi de administrator). Din tray: click = deschide; click dreapta = "
                                        "Studio, ⏺ Ecran, film, STOP URGENTA, Iesire.") if tray_ok else
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
            tk.Radiobutton(p, text="Dark", variable=self._var_theme, value="dark", bg=C["bg_card"], fg=C["text"],
                           selectcolor=C["bg_input"], activebackground=C["bg_card"],
                           font=("Segoe UI", 11)).pack(side="left", padx=4),
            tk.Radiobutton(p, text="Light", variable=self._var_theme, value="light", bg=C["bg_card"], fg=C["text"],
                           selectcolor=C["bg_input"], activebackground=C["bg_card"],
                           font=("Segoe UI", 11)).pack(side="left", padx=4),
        ))

        # ── Video ──
        f_vid = section("🎥  Video (inregistrarea ecranului)")
        self._video_save = video_ui.build_settings_section(f_vid, C)

        # ── Limba ──
        f_lang = section("🌐  Limba / Language / Sprache")
        self._var_lang = tk.StringVar(value=dict(i18n.LANGUAGES).get(i18n.saved_language(), "Română"))
        row(f_lang, "Limba interfetei:", lambda p: (
            ttk.Combobox(p, textvariable=self._var_lang, values=[n for _, n in i18n.LANGUAGES],
                         state="readonly", width=14, font=("Segoe UI", 10)).pack(side="left", padx=4),
        ))
        tk.Label(f_lang, text="Se aplica dupa repornirea aplicatiei (se cere confirmarea la Salveaza Setarile).",
                 bg=C["bg_card"], fg=C["text_dim"], font=("Segoe UI", 9)).pack(anchor="w", padx=12, pady=(0, 2))
        note(f_lang, "Aceeasi limba pentru toata aplicatia: interfata, logurile, statusurile din Excel, "
                     "rapoartele si documentatia pregatirilor.")

        # ── Locatie fisiere ──
        f_loc = section("📁  Locatie Fisiere")
        r = tk.Frame(f_loc, bg=C["bg_card"])
        r.pack(fill="x", padx=12, pady=3)
        tk.Label(r, text="Loguri:", bg=C["bg_card"], fg=C["text_dim"], font=("Segoe UI", 11), width=10,
                 anchor="w").pack(side="left")
        tk.Label(r, text=str(LOGS_DIR), bg=C["bg_card"], fg=C["accent"], font=("Segoe UI", 10)).pack(side="left")
        note(f_loc, "Rutinele, biblioteca, rezultatele si filmele: 🌐 Setari Studio → Unde se salveaza.")
        tk.Button(f_loc, text="📂 Deschide Folder", command=lambda: _open_path(str(BASE_DIR)),
                  bg=C["primary"], fg="white", relief="flat", font=("Segoe UI", 10), padx=8, pady=3,
                  cursor="hand2").pack(anchor="w", padx=12, pady=(0, 8))

        # ── 💾 Backup setari + context (backup.py) ──
        f_bak = section("💾  Backup si restaurare")
        self._var_bak_results = tk.BooleanVar(value=False)
        note(f_bak, "Un fisier .zip, salvat unde alegi: setarile, rutinele, biblioteca de obiecte, programarile si "
                    "folderul rutinelor din 📂 Manager. Fara profilul browserului si fara filme. La restaurare, "
                    "starea curenta se salveaza intai automat.")
        tk.Checkbutton(f_bak, text="Include si rezultatele (rapoarte, loguri Studio, capturi de eroare)",
                       variable=self._var_bak_results, bg=C["bg_card"], fg=C["text"], selectcolor=C["bg_input"],
                       activebackground=C["bg_card"], activeforeground=C["text"], font=("Segoe UI", 10),
                       anchor="w").pack(fill="x", padx=12)
        bak_row = tk.Frame(f_bak, bg=C["bg_card"])
        bak_row.pack(anchor="w", padx=12, pady=(4, 8))
        tk.Button(bak_row, text="💾 Creeaza backup...", command=self._create_backup, bg=C["primary"], fg="white",
                  relief="flat", font=("Segoe UI", 10), padx=8, pady=3, cursor="hand2").pack(side="left", padx=(0, 6))
        tk.Button(bak_row, text="♻ Restaureaza din backup...", command=self._restore_backup, bg=C["bg_input"],
                  fg=C["text"], relief="flat", font=("Segoe UI", 10), padx=8, pady=3,
                  cursor="hand2").pack(side="left")

        # ── Despre ──
        f_about = section("ℹ  Despre")
        note(f_about, f"{APP_NAME} v{APP_VERSION} · {i18n.tr('Autor')}: {APP_AUTHOR}\n" +
             i18n.tr("Tool RPA: rutine pe obiecte (Web / SAP / Desktop + Excel) si pasi pe ecran (mouse / "
                     "tastatura), fara cod."))

        # ── Buton Salveaza ──
        tk.Frame(inner, bg=C["separator"], height=1).pack(fill="x", padx=8, pady=8)
        tk.Button(inner, text="💾  Salveaza Setarile", command=self._save_settings,
                  bg=C["primary"], fg="white", relief="flat", font=("Segoe UI", 13, "bold"), padx=20, pady=8,
                  cursor="hand2").pack(pady=12)

    def _save_settings(self):
        """Salveaza toate setarile."""
        try:
            self.settings.set("record_mouse_move",    bool(self._var_rec_move.get()))
            self.settings.set("mouse_move_threshold", max(1, int(self._var_move_thr.get())))
            # v4.1: siguranta la rulare
            self.settings.set("dnd_during_run",       bool(self._var_dnd.get()))
            self.settings.set("show_run_frame",       bool(self._var_frame.get()))
            self.settings.set("guard_enabled",        bool(self._var_guard.get()))
            self.settings.set("guard_sensitivity",    self._var_guard_sens.get())
            self.run_frame.enabled = bool(self._var_frame.get())
            # shortcut-urile (pastram si cheile vechi pe care nu le mai arata fereastra)
            sc = dict(self.settings.get("shortcuts", DEFAULT_SHORTCUTS))
            sc.update({k: v.get() for k, v in self._sc_vars.items()})
            self.settings.set("shortcuts", sc)
            # Video (folder, la rulare, per rand Excel, calitate)
            if getattr(self, "_video_save", None):
                self._video_save()
            # Salveaza limba + tema (repornire doar daca s-a schimbat ceva)
            lang = next((c for c, n in i18n.LANGUAGES if n == self._var_lang.get()), "ro")
            lang_changed = lang != i18n.saved_language()
            if lang_changed:
                i18n.save_language(lang)
            self._set_theme(self._var_theme.get(), force_restart=lang_changed)
            # Reporneste hotkeys cu noile setari
            self.hotkey_mgr.stop()
            self._register_hotkeys()
            messagebox.showinfo("Setari", "Setarile au fost salvate cu succes!", parent=self._settings_win)
            self._status_var.set("Setari salvate")
        except Exception as e:
            messagebox.showerror("Eroare", f"Nu s-au putut salva setarile:\n{e}", parent=self._settings_win)

    def _set_theme(self, theme: str, force_restart: bool = False):
        """Schimba tema (si/sau limba) si reporneste aplicatia automat."""
        changed = theme != self.settings.get("theme", "dark")
        self.settings.set("theme", theme)
        if not changed and not force_restart:
            return
        question = (f"Tema '{theme}' va fi aplicata.\nAplicatia se va reporni acum. Continui?" if changed else
                    "Limba noua se aplica dupa repornire.\nAplicatia se va reporni acum. Continui?")
        if messagebox.askyesno("Tema" if changed else "Limba", question):
            if self._studio is not None and not self._studio.confirm_discard():
                return
            self.root.destroy()
            os.execv(sys.executable, [sys.executable] + sys.argv)

    def _create_backup(self):
        import backup
        path = filedialog.asksaveasfilename(title="Salveaza backup-ul", initialfile=backup.default_name(),
                                            defaultextension=".zip", filetypes=[("Backup AutoPilot DC", "*.zip")])
        if not path:
            return
        include = bool(self._var_bak_results.get())
        self._status_var.set("Creez backup-ul...")

        def work():
            try:
                info = backup.create_backup(path, include_results=include)
                msg = (True, f"Backup creat: {path}\n{info.files} fisiere.")
            except Exception as ex:  # noqa: BLE001
                msg = (False, f"Backup-ul nu a putut fi creat:\n{ex}")
            self.root.after(0, lambda: (messagebox.showinfo if msg[0] else messagebox.showerror)("Backup", msg[1]))
        threading.Thread(target=work, daemon=True).start()

    def _restore_backup(self):
        import backup
        path = filedialog.askopenfilename(title="Alege backup-ul", filetypes=[("Backup AutoPilot DC", "*.zip")])
        if not path:
            return
        try:
            info = backup.read_info(path)
        except Exception as ex:  # noqa: BLE001
            messagebox.showerror("Backup", f"Fisierul nu e un backup AutoPilot DC:\n{ex}")
            return
        if not messagebox.askyesno("Restaurare", f"Restaurez backup-ul din {info.created[:16].replace('T', ' ')} "
                                                 f"(versiunea {info.version}, {info.files} fisiere)?\n\n"
                                                 "Setarile si rutinele de acum se inlocuiesc; inainte se face "
                                                 "automat un backup al starii curente."):
            return
        try:
            res = backup.restore_backup(path)
        except Exception as ex:  # noqa: BLE001
            messagebox.showerror("Restaurare", f"Restaurarea a esuat:\n{ex}")
            return
        notes = ("\n" + "\n".join(res.notes)) if res.notes else ""
        messagebox.showinfo("Restaurare", f"Restaurat: {res.files} fisiere.{notes}\n\nBackup-ul starii anterioare: "
                                          f"{res.safety_backup}\n\nReporneste AutoPilot DC ca setarile sa se aplice.")

    def _show_text_dialog(self, title: str, text: str, saved_path: str = ""):
        """Text de citit si de copiat (ex. diagnosticul "Nu deranja")."""
        dlg = tk.Toplevel(self.root)
        dlg.title(title)
        dlg.configure(bg=C["bg_main"])
        dlg.transient(self.root)
        box = tk.Text(dlg, width=90, height=18, wrap="word", bg=C["bg_input"], fg=C["text"],
                      font=("Consolas", 10), relief="flat")
        box.insert("1.0", text)
        box.pack(fill="both", expand=True, padx=10, pady=(10, 4))
        if saved_path:
            tk.Label(dlg, text="Salvat si in: " + saved_path, bg=C["bg_main"], fg=C["text_dim"],
                     font=("Segoe UI", 9)).pack(anchor="w", padx=10)
        bar = tk.Frame(dlg, bg=C["bg_main"])
        bar.pack(anchor="e", padx=10, pady=8)

        def copy():
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
            self._status_var.set("Textul a fost copiat.")
        tk.Button(bar, text="📋 Copiaza", command=copy, bg=C["primary"], fg="white", relief="flat",
                  font=("Segoe UI", 10, "bold"), padx=10).pack(side="left", padx=3)
        tk.Button(bar, text="Inchide", command=dlg.destroy, bg=C["bg_input"], fg=C["text"], relief="flat",
                  font=("Segoe UI", 10), padx=10).pack(side="left", padx=3)

    # ==========================================================================
    # TASTE GLOBALE
    # ==========================================================================
    def _register_hotkeys(self):
        """F5 = ⏺ Ecran, F6 = stop inregistrare, F7 / F8 / F9 = Studio ruleaza / pauza / stop, F12 = urgenta."""
        sc = self.settings.get("shortcuts", DEFAULT_SHORTCUTS)
        acts = [("start_rec", "F5", self._toggle_recording),
                ("stop_rec", "F6", self._stop_recording),
                ("play", "F7", lambda: self._studio_call("run")),
                ("pause", "F8", self._toggle_pause),
                ("stop_play", "F9", lambda: self._studio_call("stop")),
                ("emergency", "F12", self._emergency_stop)]
        used = set()
        for key, default, fn in acts:   # aceeasi tasta pe doua comenzi: ramane prima (ex. pauza = F7 ca rularea)
            combo = (sc.get(key, default) or "").strip()
            if combo and combo.lower() not in used:
                used.add(combo.lower())
                self.hotkey_mgr.register(combo, lambda f=fn: self.root.after(0, f))
        self.hotkey_mgr.start()
        if not PYNPUT_AVAILABLE:   # fara pynput: tastele merg macar cand fereastra e activa
            for key, default, fn in acts:
                combo = sc.get(key, default)
                if re.fullmatch(r"F\d{1,2}", combo or ""):
                    self.root.bind(f"<{combo}>", lambda e, f=fn: f())

    def _toggle_pause(self):
        if self._studio is not None and self._studio.busy:
            self._studio.toggle_pause()

    # ==========================================================================
    # ⏺ ECRAN: inregistrarea mouse / tastatura (fostul Recorder) -> pasi Studio
    # ==========================================================================
    def _connect_callbacks(self):
        self.recorder.on_recording_started = lambda: self.root.after(0, lambda: self._on_rec_ui(True))
        self.recorder.on_recording_stopped = lambda: self.root.after(0, lambda: self._on_rec_ui(False))
        self.recorder.on_step_recorded = lambda s: self.root.after(0, self._update_rec_count)
        self.recorder.ignore = _is_own_window_step   # click-urile / tastele pe AutoPilot DC nu devin pasi

    def _toggle_recording(self):
        if self._is_recording:
            self._stop_recording()
        else:
            self._start_recording()

    def _start_recording(self):
        if self._is_recording or self._studio is None:
            return
        if self._studio.busy:
            self._status_var.set("Rutina ruleaza: opreste-o inainte de inregistrare.")
            return
        if not PYNPUT_AVAILABLE:
            messagebox.showwarning("⏺ Ecran", "Lipseste pachetul pynput. Ruleaza INSTALEAZA.bat din folderul "
                                             "aplicatiei.")
            return
        self.recorder.clear()
        if not self.recorder.start():
            return
        self._is_recording = True
        self.root.iconify()   # lucrezi in aplicatia tinta; bara mica de sus ramane la vedere

    def _stop_recording(self):
        if not self._is_recording:
            return
        steps = self.recorder.stop()
        self._is_recording = False
        self._show_from_tray()
        nodes = recorded_to_nodes([s.to_dict() for s in steps])
        if not nodes:
            self._status_var.set("Inregistrare oprita: niciun pas.")
            return
        title = i18n.tr_template("Inregistrare pe ecran {0}").format(datetime.datetime.now().strftime("%H:%M"))
        self._studio.insert_recorded(nodes, title)
        self._status_var.set(i18n.tr_template("⏺ {0} pasi pe ecran adaugati in rutina (grupul \"{1}\").").format(
            len(nodes), title))

    def _on_rec_ui(self, on: bool):
        """Chenarul verde REC, Nu deranja, butonul ⏺ Ecran si bara mica de sus."""
        if on:
            self._btn_rec.configure(text="⏹ Stop ecran", bg="#FF0000", fg="white")
            self._rec_indicator.configure(text="⏺ REC", fg=C["danger"])
            if self.run_frame.enabled:
                self.run_frame.show("rec")
            if self.settings.get("dnd_during_run", True):
                self._rec_dnd = True
                DoNotDisturb.enable(wait=False)
            self._show_rec_bar()
            self._status_var.set("⏺ Inregistrare pe ecran: lucreaza normal; F6 sau ⏹ = stop.")
        else:
            self._btn_rec.configure(text="⏺ Ecran", bg=getattr(self._btn_rec, "_orig_bg", C["danger"]),
                                    fg=getattr(self._btn_rec, "_orig_fg", "white"))
            self._rec_indicator.configure(text="⬤ STANDBY", fg=C["text_muted"])
            if self.run_frame.mode == "rec":
                self.run_frame.hide()
            if self._rec_dnd:
                self._rec_dnd = False
                DoNotDisturb.restore()
            if self._rec_bar is not None:
                try:
                    self._rec_bar.destroy()
                except tk.TclError:
                    pass
                self._rec_bar = None

    def _show_rec_bar(self):
        """Bara mica, mereu deasupra: cati pasi s-au inregistrat + ⏹ Stop."""
        bar = tk.Toplevel(self.root)
        bar.overrideredirect(True)
        bar.attributes("-topmost", True)
        bar.configure(bg="#B00020")
        sw = self.root.winfo_screenwidth()
        bar.geometry(f"+{max(0, sw // 2 - 170)}+6")
        tk.Label(bar, text="⏺ REC", bg="#B00020", fg="white", font=("Segoe UI", 10, "bold")).pack(
            side="left", padx=(10, 6), pady=4)
        self._rec_count = tk.Label(bar, text=i18n.tr_template("{0} pasi").format(0), bg="#B00020", fg="white",
                                   font=("Segoe UI", 10))
        self._rec_count.pack(side="left", padx=6)
        tk.Button(bar, text="⏹ Stop (F6)", command=self._stop_recording, bg="white", fg="#B00020", relief="flat",
                  font=("Segoe UI", 10, "bold"), padx=10, cursor="hand2").pack(side="left", padx=6, pady=4)
        self._rec_bar = bar

    def _update_rec_count(self):
        if self._rec_bar is not None:
            try:
                self._rec_count.configure(text=i18n.tr_template("{0} pasi").format(len(self.recorder.get_steps())))
            except tk.TclError:
                pass

    def _emergency_stop(self):
        """Oprire de urgenta: rutina, inregistrarea pe ecran, chenarul."""
        if self._studio is not None and self._studio.busy:
            self._studio.stop()
        if self._is_recording:
            self._stop_recording()
        self.run_frame.hide()
        self._status_var.set("🚨 STOP URGENTA ACTIVAT")

    # ==========================================================================
    # TRAY, RELUARE, INCHIDERE
    # ==========================================================================
    def _hide_to_tray(self) -> bool:
        if not app_shell.tray_available() or not self.tray.show():
            return False
        self.root.withdraw()
        if not self._tray_hint_shown:
            self._tray_hint_shown = True
            self.tray.notify("AutoPilot DC ruleaza in continuare aici. Click pe pictograma ca sa-l deschizi; "
                             "Iesire din meniul pictogramei il inchide.")
        return True

    def _offer_resume(self):
        """v4.8.4: daca aplicatia (sau PC-ul) s-a inchis in mijlocul unei rulari, oferim reluarea ei."""
        try:
            from rpr import resume
            states = resume.pending()
        except Exception:  # noqa: BLE001
            return
        if not states:
            return
        st = states[0]
        for old in states[1:]:   # oferim doar ultima rulare intrerupta
            resume.discard(old)
        prep = st.kind == resume.KIND_PREP
        if self._start_in_tray:
            self._show_from_tray()
        from studio_ui import choice_dialog
        text = (f"AutoPilot DC s-a inchis neasteptat in timpul pregatirii \"{st.name}\" (pornita la {st.started_text})."
                if prep else
                f"AutoPilot DC s-a inchis neasteptat in timpul rutinei \"{st.name}\" (pornita la {st.started_text}).")
        detail = i18n.tr("La reluare, randurile Excel terminate (OK) sunt sarite. Pentru randul ramas IN LUCRU "
                         "esti intrebat daca il refaci, il marchezi facut sau opresti.")
        if prep:
            detail += "\n" + i18n.tr(f"Rutinele terminate ale pregatirii ({st.done_items}) sunt sarite.")
        buttons = ["Reiau rularea", "Doar deschid", "Nu, renunt"]
        ans = choice_dialog(self.root, "Reluare dupa inchidere", text, buttons, detail, C=C)
        if ans == buttons[2]:
            resume.discard(st)
            return
        if self._studio is None:
            return
        self._studio.resume_interrupted(st, run=ans == buttons[0])

    def _show_from_tray(self):
        self.root.deiconify()
        self.root.lift()
        self.root.attributes("-topmost", True)
        self.root.after(300, lambda: self.root.attributes("-topmost", False))
        self.root.focus_force()

    def _quit_app(self):
        """Inchidere reala (din meniul tray)."""
        self._show_from_tray()
        self._really_quit = True
        self._on_close()
        self._really_quit = False

    def _on_close(self):
        """Inchiderea aplicatiei (Studio intreaba de rutinele nesalvate)."""
        if self.settings.get("close_to_tray", False) and not self._really_quit and self._hide_to_tray():
            return  # ✕ ascunde aplicatia langa ceas (rularile si scurtaturile F7/F12 merg in continuare)
        if self._is_recording:
            self._stop_recording()   # pasii inregistrati intra in rutina, apoi Studio intreaba de salvare
        if self.video.active:
            self.video.stop(open_editor=False)   # filmul inceput se salveaza
        if self._studio is not None:
            if self._studio.busy:
                self._studio.stop()
                self._studio.forget_resume()   # inchidere ceruta de utilizator: nu e o inchidere neasteptata
            if not self._studio.confirm_discard():
                return
            self._studio.shutdown()   # opreste inregistrarea, inchide browserul
        self.run_frame.hide()
        DoNotDisturb.restore_all()  # v4.1: notificarile revin chiar daca o rulare nu s-a terminat
        self.hotkey_mgr.stop()
        self.tray.hide()
        self.root.destroy()


def _open_path(path: str) -> None:
    try:
        os.startfile(path)  # type: ignore[attr-defined]
    except AttributeError:
        import subprocess
        subprocess.Popen(["xdg-open", path])
    except OSError as ex:
        messagebox.showerror("AutoPilot DC", str(ex))


def _is_own_window_step(step) -> bool:
    """Pasul s-a facut pe o fereastra AutoPilot DC (ex. click pe ⏹ Stop)? Atunci nu se inregistreaza."""
    try:
        import autopilot_safety as _s
        if not _s.IS_WINDOWS:
            return False
        if step.step_type in ("CLICK", "DBLCLICK", "RIGHTCLICK", "SCROLL", "MOVE"):
            return _s.window_at(step.x, step.y).is_own
        return _s.foreground().is_own
    except Exception:  # noqa: BLE001
        return False

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
