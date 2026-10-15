#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
apply_patches_v4.py
═══════════════════════════════════════════════════════════════════
Aplica toate patch-urile v4.0 peste AutoPilot_DCv3.9.py (sau .txt)
si genereaza AutoPilot_DCv4.0.py

Utilizare:
    python apply_patches_v4.py

Asigura-te ca fisierul sursa (AutoPilot_DCv3.9.py sau .txt)
se afla in acelasi director cu acest script.
═══════════════════════════════════════════════════════════════════
"""

import os
import sys
import re
import shutil
from datetime import datetime

# ──────────────────────────────────────────────
# CONFIG
# ──────────────────────────────────────────────
POSSIBLE_SOURCES = [
    "AutoPilot_DCv3.9.py",
    "AutoPilot_DCv3.9.txt",
    "AutoPilot_DC.py",
]
OUTPUT_FILE = "AutoPilot_DCv4.0.py"
BACKUP_SUFFIX = f".bak_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

# ──────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────
ok_count   = 0
fail_count = 0
log_lines  = []

def log(msg: str):
    print(msg)
    log_lines.append(msg)

def apply(src: str, old: str, new: str, label: str,
          count: int = 1, regex: bool = False) -> str:
    global ok_count, fail_count
    if regex:
        result, n = re.subn(old, new, src, count=count, flags=re.DOTALL)
    else:
        n = src.count(old)
        if n == 0:
            result, n = src, 0
        else:
            result = src.replace(old, new, count)
            n = count if n >= count else n

    if n > 0:
        ok_count += 1
        log(f"  ✅  {label}")
    else:
        fail_count += 1
        log(f"  ❌  FAIL: {label}")
        log(f"       Cauta: {repr(old[:80])}")
    return result

# ══════════════════════════════════════════════════════════════════
# BLOC-URI DE COD NOU (inserate/inlocuite)
# ══════════════════════════════════════════════════════════════════

# ── P1: Optional imports ──────────────────────────────────────────
OPTIONAL_IMPORTS = '''
# ══════════════════════════════════════════════════════════════════
# [v4.0] Optional imports – graceful fallback if not installed
# ══════════════════════════════════════════════════════════════════
try:
    import win32gui
    import win32con
    _WIN32GUI_OK = True
except ImportError:
    _WIN32GUI_OK = False

try:
    import winreg
    _WINREG_OK = True
except ImportError:
    _WINREG_OK = False

try:
    import pywinauto
    from pywinauto import Desktop as _PWA_Desktop
    _PYWINAUTO_OK = True
except ImportError:
    _PYWINAUTO_OK = False

try:
    import screeninfo as _screeninfo_mod
    _SCREENINFO_OK = True
except ImportError:
    _SCREENINFO_OK = False

'''

# ── P2: FocusAssistManager ────────────────────────────────────────
FOCUS_ASSIST_CLASS = '''
# ══════════════════════════════════════════════════════════════════
# [v4.0 F10] FocusAssistManager – DND via winreg
# ══════════════════════════════════════════════════════════════════
class FocusAssistManager:
    """Activeaza/dezactiveaza Windows Focus Assist (DND) via registry."""

    _REG_PATH = (
        r"Software\\Microsoft\\Windows\\CurrentVersion"
        r"\\CloudStore\\Store\\Cache\\DefaultAccount"
        r"\\$$windows.data.notifications.quiethourssettings"
        r"\\Current"
    )
    _REG_KEY = "Data"

    def __init__(self):
        self._backup = None

    def enable(self) -> bool:
        if not _WINREG_OK:
            return False
        try:
            import winreg
            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER, self._REG_PATH,
                0, winreg.KEY_READ | winreg.KEY_WRITE
            ) as key:
                val, _ = winreg.QueryValueEx(key, self._REG_KEY)
                self._backup = bytes(val) if val else None
                data = bytearray(val) if val else bytearray(28)
                if len(data) > 24:
                    data[24] = 2
                winreg.SetValueEx(key, self._REG_KEY, 0,
                                  winreg.REG_BINARY, bytes(data))
            return True
        except Exception as e:
            import logging
            logging.warning(f"[v4.0 F10] FocusAssist enable failed: {e}")
            return False

    def disable(self):
        if not _WINREG_OK or self._backup is None:
            return
        try:
            import winreg
            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER, self._REG_PATH,
                0, winreg.KEY_WRITE
            ) as key:
                winreg.SetValueEx(key, self._REG_KEY, 0,
                                  winreg.REG_BINARY, self._backup)
        except Exception as e:
            import logging
            logging.warning(f"[v4.0 F10] FocusAssist restore failed: {e}")
        finally:
            self._backup = None

_focus_assist = FocusAssistManager()

'''

# ── P3: VerboseLogger ─────────────────────────────────────────────
VERBOSE_LOGGER_CLASS = '''
# ══════════════════════════════════════════════════════════════════
# [v4.0 F3] VerboseLogger – log detaliat per pas
# ══════════════════════════════════════════════════════════════════
class VerboseLogger:
    """Logheaza context detaliat la fiecare pas executat."""

    def __init__(self, logger=None):
        import logging as _logging
        self._log = logger or _logging.getLogger("VerboseLogger")

    def log_step(self, step, step_idx: int):
        from datetime import datetime as _dt
        ts  = _dt.now().isoformat(timespec="milliseconds")
        typ = getattr(step, "step_type", step.get("type", "?")) if hasattr(step, "step_type") else step.get("type", "?")
        x   = getattr(step, "x", step.get("x", "")) if hasattr(step, "x") else step.get("x", "")
        y   = getattr(step, "y", step.get("y", "")) if hasattr(step, "y") else step.get("y", "")
        txt = getattr(step, "text", step.get("text", "")) if hasattr(step, "text") else step.get("text", "")
        dly = getattr(step, "delay_before", step.get("delay", "")) if hasattr(step, "delay_before") else step.get("delay", "")

        win_title = self._get_window_title()
        url       = self._get_browser_url()
        field_val = self._get_focused_field()

        msg = (
            f"[VERBOSE] [{ts}] Pas #{step_idx+1} | Tip: {typ}"
            + (f" | X:{x} Y:{y}" if (x or y) else "")
            + (f" | Text: {txt!r}"  if txt else "")
            + (f" | Delay: {dly}s"  if dly else "")
            + f"\\n           Fereastra: {win_title}"
            + f" | URL: {url}"
            + f" | Camp activ: {field_val}"
        )
        self._log.info(msg)

    @staticmethod
    def _get_window_title() -> str:
        try:
            if _WIN32GUI_OK:
                import win32gui
                hwnd = win32gui.GetForegroundWindow()
                return win32gui.GetWindowText(hwnd) or "N/A"
        except Exception:
            pass
        return "N/A"

    @staticmethod
    def _get_browser_url() -> str:
        if not _PYWINAUTO_OK:
            return "N/A"
        try:
            import threading
            result = ["N/A"]
            def _fetch():
                try:
                    from pywinauto import Desktop
                    desk = Desktop(backend="uia")
                    for kw in ["Chrome", "Edge", "Firefox"]:
                        wins = desk.windows(title_re=f".*{kw}.*")
                        if wins:
                            addr = wins[0].child_window(
                                control_type="Edit", found_index=0)
                            result[0] = addr.get_value() or "N/A"
                            return
                except Exception:
                    pass
            t = threading.Thread(target=_fetch, daemon=True)
            t.start(); t.join(timeout=0.3)
            return result[0]
        except Exception:
            return "N/A"

    @staticmethod
    def _get_focused_field() -> str:
        if not _PYWINAUTO_OK:
            return "N/A"
        try:
            import threading
            result = ["N/A"]
            def _fetch():
                try:
                    from pywinauto import Desktop
                    desk = Desktop(backend="uia")
                    el = desk.get_focus()
                    if el:
                        try:
                            result[0] = el.get_value() or el.window_text() or "N/A"
                        except Exception:
                            result[0] = el.window_text() or "N/A"
                except Exception:
                    pass
            t = threading.Thread(target=_fetch, daemon=True)
            t.start(); t.join(timeout=0.3)
            return result[0]
        except Exception:
            return "N/A"

'''

# ── P4: HybridRoutineEngine ───────────────────────────────────────
HYBRID_ENGINE_CLASS = '''
# ══════════════════════════════════════════════════════════════════
# [v4.0 F5] HybridRoutineEngine – Click Map Recording
# ══════════════════════════════════════════════════════════════════
class HybridRoutineEngine:
    """
    Inregistreaza click-uri pe ecran cu overlay vizual (A, B, C...).
    Overlay-urile raman vizibile pana la oprirea inregistrarii.
    """

    def __init__(self, root):
        self._root      = root
        self._steps     = []
        self._overlays  = []
        self._listener  = None
        self._recording = False
        self.on_step_added = None  # callback(step_dict)

    @staticmethod
    def _label(idx: int) -> str:
        s = ""
        idx += 1
        while idx > 0:
            idx, r = divmod(idx - 1, 26)
            s = chr(65 + r) + s
        return s

    def start_recording(self):
        if self._recording:
            return
        self._recording = True
        self._steps.clear()
        self._clear_overlays()
        try:
            from pynput import mouse as _mouse
            self._listener = _mouse.Listener(on_click=self._on_click)
            self._listener.start()
        except Exception as e:
            import logging
            logging.error(f"[v4.0 F5] HybridEngine start failed: {e}")

    def stop_recording(self):
        self._recording = False
        if self._listener:
            try:
                self._listener.stop()
            except Exception:
                pass
            self._listener = None
        self._clear_overlays()

    def _on_click(self, x, y, button, pressed):
        if not pressed or not self._recording:
            return
        try:
            from pynput.mouse import Button
            if button != Button.left:
                return
        except Exception:
            pass
        idx   = len(self._steps)
        label = self._label(idx)
        step  = {"type": "HYBRID_CLICK", "x": x, "y": y,
                 "label": label, "index": idx, "delay": 0.3}
        self._steps.append(step)
        self._root.after(0, lambda s=step: self._draw_overlay(s))
        if callable(self.on_step_added):
            self._root.after(0, lambda s=step: self.on_step_added(s))

    def _draw_overlay(self, step: dict):
        x, y  = step["x"], step["y"]
        label = step["label"]
        idx   = step["index"] + 1
        win = tk.Toplevel(self._root)
        win.overrideredirect(True)
        win.attributes("-topmost", True)
        win.attributes("-alpha", 0.85)
        win.configure(bg="#CC0000")
        win.geometry(f"42x42+{x - 21}+{y - 21}")
        frm = tk.Frame(win, bg="#CC0000")
        frm.pack(expand=True, fill="both")
        tk.Label(frm, text=label, bg="#CC0000", fg="white",
                 font=("Segoe UI", 14, "bold")).place(
            relx=0.5, rely=0.6, anchor="center")
        tk.Label(frm, text=f"#{idx}", bg="#CC0000", fg="#FFFF99",
                 font=("Segoe UI", 5, "bold")).place(
            relx=0.5, rely=0.15, anchor="center")
        self._overlays.append(win)

    def _clear_overlays(self):
        for win in self._overlays:
            try:
                win.destroy()
            except Exception:
                pass
        self._overlays.clear()

    def get_steps(self):
        return list(self._steps)

    def export_as_standard(self):
        return [{"type": "CLICK", "x": s["x"], "y": s["y"],
                 "delay": s.get("delay", 0.3)} for s in self._steps]

    def clear(self):
        self._steps.clear()
        self._clear_overlays()

'''

# ── P5: RunIndicatorOverlay v4.0 (inlocuieste clasa existenta) ────
RUN_INDICATOR_NEW = '''class RunIndicatorOverlay:
    """[v4.0] Indicator RUN pulsant, multi-monitor, cu contor repetari."""

    W, H = 200, 26

    def __init__(self, root):
        self._root     = root
        self._windows  = []
        self._labels   = []
        self._running  = False
        self._alpha_hi = True
        self._after_id = None

    def show(self):
        self._destroy()
        try:
            if _SCREENINFO_OK:
                import screeninfo
                screens = [(m.x, m.y, m.width, m.height)
                           for m in screeninfo.get_monitors()]
            else:
                raise Exception("no screeninfo")
        except Exception:
            sw = self._root.winfo_screenwidth()
            sh = self._root.winfo_screenheight()
            screens = [(0, 0, sw, sh)]
        w, h = self.W, self.H
        for (mx, my, mw, mh) in screens:
            win = tk.Toplevel(self._root)
            win.overrideredirect(True)
            win.attributes("-topmost", True)
            win.attributes("-alpha", 0.60)
            win.configure(bg="#0A0A0A")
            x = mx + mw - w - 10 - 150
            y = my + 10
            win.geometry(f"{w}x{h}+{x}+{y}")
            lbl = tk.Label(win, text="\\u25b6  RUN",
                           bg="#0A0A0A", fg="#32CD32",
                           font=("Segoe UI", 7, "bold"))
            lbl.pack(expand=True, fill="both")
            self._windows.append(win)
            self._labels.append(lbl)
        self._running  = True
        self._alpha_hi = True
        self._pulse()

    def update_rep(self, cur: int, total: int):
        """[v4.0 F2] Actualizeaza contorul de repetari pe overlay."""
        text = f"\\u25b6  RUN  \\u2022  Rep: {cur} / {total}"
        for lbl in self._labels:
            try:
                lbl.config(text=text)
            except Exception:
                pass

    def hide(self):
        self._running = False
        if self._after_id:
            try:
                self._root.after_cancel(self._after_id)
            except Exception:
                pass
            self._after_id = None
        self._destroy()

    def _pulse(self):
        if not self._running:
            return
        alpha = 0.75 if self._alpha_hi else 0.40
        self._alpha_hi = not self._alpha_hi
        for win in self._windows:
            try:
                win.attributes("-alpha", alpha)
            except Exception:
                pass
        self._after_id = self._root.after(800, self._pulse)

    def _destroy(self):
        for win in self._windows:
            try:
                win.destroy()
            except Exception:
                pass
        self._windows.clear()
        self._labels.clear()
'''

# ── P6: Metode hibrid pentru MainWindow ───────────────────────────
HYBRID_METHODS = '''
    # ══════════════════════════════════════════════════════════════
    # [v4.0 F5] Metode Rutina Hibrida
    # ══════════════════════════════════════════════════════════════

    def _build_tab_hybrid(self):
        """[v4.0 F5] Construieste tab-ul Rutina Hibrida."""
        try:
            import tkinter.ttk as ttk_local
            tab_frame = tk.Frame(self._notebook, bg=C["bg_card"])
            self._notebook.add(tab_frame, text="\\U0001f5fa\\ufe0f Hibrid")
        except Exception:
            return

        btn_bar = tk.Frame(tab_frame, bg=C["bg_card"])
        btn_bar.pack(fill="x", padx=8, pady=6)

        def hbtn(text, cmd, bg=None):
            _bg = bg or C["bg_input"]
            _fg = "white" if _bg not in (C["bg_input"], C["bg_card"]) else C["text"]
            b = tk.Button(btn_bar, text=text, command=cmd,
                          bg=_bg, fg=_fg,
                          font=("Segoe UI", 10, "bold"),
                          relief="flat", padx=8, pady=4, cursor="hand2")
            b.pack(side="left", padx=3)
            return b

        self._hbtn_start = hbtn("\\u23fa Inregistreaza",
                                 self._hybrid_start_rec, C["danger"])
        self._hbtn_stop  = hbtn("\\u23f9 Stop",
                                 self._hybrid_stop_rec,  C["warning"])
        self._hbtn_run   = hbtn("\\u25b6 Ruleaza",
                                 self._hybrid_run,       C["success"])
        self._hbtn_clear = hbtn("\\U0001f5d1 Reseteaza",
                                 self._hybrid_clear)
        self._hbtn_exp   = hbtn("\\U0001f4e4 Export Standard",
                                 self._hybrid_export,    C["primary"])

        self._hybrid_status = tk.StringVar(value="Gata. Apasa Inregistreaza.")
        tk.Label(tab_frame, textvariable=self._hybrid_status,
                 bg=C["bg_card"], fg=C["accent"],
                 font=("Segoe UI", 10, "italic")).pack(anchor="w", padx=10)

        list_frame = tk.Frame(tab_frame, bg=C["bg_card"])
        list_frame.pack(fill="both", expand=True, padx=8, pady=4)

        import tkinter.ttk as _ttk
        cols = ("idx", "label", "x", "y", "delay")
        self._hybrid_tree = _ttk.Treeview(
            list_frame, columns=cols, show="headings", height=14)
        for col, hdr, w in [("idx","#",40),("label","Litera",60),
                             ("x","X",80),("y","Y",80),("delay","Delay",70)]:
            self._hybrid_tree.heading(col, text=hdr)
            self._hybrid_tree.column(col, width=w, anchor="center")
        sb = _ttk.Scrollbar(list_frame, orient="vertical",
                            command=self._hybrid_tree.yview)
        self._hybrid_tree.configure(yscrollcommand=sb.set)
        self._hybrid_tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        info = (
            "\\U0001f4d6 Instructiuni Rutina Hibrida:\\n"
            "1. Apasa \\u23fa Inregistreaza\\n"
            "2. Click pe fiecare punct de actiune din ecran\\n"
            "   \\u2192 Apare overlay rosu cu litera pasului (A, B, C...)\\n"
            "3. Apasa \\u23f9 Stop cand ai terminat\\n"
            "4. Apasa \\u25b6 Ruleaza pentru a executa rutina\\n"
            "5. Apasa \\U0001f4e4 Export Standard pentru a converti\\n"
            "   in format compatibil cu rutinele normale"
        )
        tk.Label(tab_frame, text=info,
                 bg=C["bg_card"], fg=C["text_dim"],
                 font=("Segoe UI", 9), justify="left", anchor="w").pack(
            fill="x", padx=10, pady=6)

        self._hybrid_engine.on_step_added = self._hybrid_on_step_added

    def _hybrid_start_rec(self):
        self._hybrid_engine.start_recording()
        self._hybrid_status.set("\\U0001f534 Inregistrare activa \\u2014 click pe ecran...")
        if getattr(self, "_var_dnd", None) and self._var_dnd.get():
            _focus_assist.enable()

    def _hybrid_stop_rec(self):
        self._hybrid_engine.stop_recording()
        n = len(self._hybrid_engine.get_steps())
        self._hybrid_status.set(f"\\u2705 Inregistrare oprita \\u2014 {n} pasi capturati")
        _focus_assist.disable()

    def _hybrid_run(self):
        steps = self._hybrid_engine.get_steps()
        if not steps:
            import tkinter.messagebox as _mb
            _mb.showinfo("Hibrid", "Nu exista pasi inregistrati.")
            return
        import threading, time
        def _run():
            try:
                from pynput.mouse import Controller, Button
                m = Controller()
                for s in steps:
                    m.position = (s["x"], s["y"])
                    time.sleep(0.1)
                    m.click(Button.left)
                    time.sleep(s.get("delay", 0.3))
            except Exception as e:
                import logging
                logging.error(f"[v4.0 F5] HybridRun error: {e}")
        threading.Thread(target=_run, daemon=True).start()
        self._hybrid_status.set("\\u25b6 Rulare hibrida in curs...")

    def _hybrid_clear(self):
        self._hybrid_engine.clear()
        if hasattr(self, "_hybrid_tree"):
            for row in self._hybrid_tree.get_children():
                self._hybrid_tree.delete(row)
        self._hybrid_status.set("\\U0001f5d1 Resetat.")

    def _hybrid_export(self):
        steps = self._hybrid_engine.export_as_standard()
        if not steps:
            import tkinter.messagebox as _mb
            _mb.showinfo("Export", "Nu exista pasi de exportat.")
            return
        from tkinter import filedialog
        path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON", "*.json")],
            title="Salveaza rutina hibrida"
        )
        if path:
            import json
            with open(path, "w", encoding="utf-8") as f:
                json.dump({"steps": steps, "source": "hybrid_v4.0"},
                          f, indent=2, ensure_ascii=False)
            self._hybrid_status.set(f"\\u2705 Exportat: {path}")

    def _hybrid_on_step_added(self, step: dict):
        if not hasattr(self, "_hybrid_tree"):
            return
        self._hybrid_tree.insert("", "end", values=(
            step["index"] + 1, step["label"],
            step["x"], step["y"], step.get("delay", 0.3),
        ))

    # ── Resize auto butoane [v4.0 F8] ────────────────────────────
    def _on_window_configure(self, event=None):
        if hasattr(self, "_resize_after_id") and self._resize_after_id:
            try:
                self.root.after_cancel(self._resize_after_id)
            except Exception:
                pass
        self._resize_after_id = self.root.after(
            150, self._apply_toolbar_resize)

    def _apply_toolbar_resize(self):
        try:
            w = self.root.winfo_width()
        except Exception:
            return
        _btn_map = [
            (getattr(self, "_btn_rec",   None),
             "\\u23fa  Inregistreaza", "\\u23fa REC",  "\\u23fa"),
            (getattr(self, "_btn_stopr", None),
             "\\u23f9  Stop Rec",      "\\u23f9 StpR", "\\u23f9"),
            (getattr(self, "_btn_play",  None),
             "\\u25b6  Ruleaza",       "\\u25b6 RUN",  "\\u25b6"),
            (getattr(self, "_btn_pause", None),
             "\\u23f8  Pauza",         "\\u23f8 PAU",  "\\u23f8"),
            (getattr(self, "_btn_stopp", None),
             "\\u23f9  Stop",          "\\u23f9 STP",  "\\u23f9"),
            (getattr(self, "_btn_save",  None),
             "\\U0001f4be  Salveaza",  "\\U0001f4be SAV", "\\U0001f4be"),
            (getattr(self, "_btn_reset", None),
             "\\U0001f5d1  Reseteaza", "\\U0001f5d1 RST", "\\U0001f5d1"),
            (getattr(self, "_btn_emg",   None),
             "\\U0001f6a8 STOP URGENTA","\\U0001f6a8 EMG","\\U0001f6a8"),
        ]
        for btn, full, short, icon in _btn_map:
            if btn is None:
                continue
            try:
                if w > 1200:
                    btn.config(text=full)
                elif w > 800:
                    btn.config(text=short)
                else:
                    btn.config(text=icon)
            except Exception:
                pass

'''

# ── P7: Setari v4.0 (Always on Top + DND + Scale) ────────────────
SETTINGS_V40_BLOCK = '''
        # ══════════════════════════════════════════════════════════
        # [v4.0] Sectiune setari noi: AOT, DND, Scale
        # ══════════════════════════════════════════════════════════

        # ── Always on Top [F9] ────────────────────────────────────
        try:
            _sep_v40 = tk.Frame(frm, bg=C["border"], height=1)
            _sep_v40.pack(fill="x", pady=10)
            tk.Label(frm, text="\\U0001f4cc Fereastra & Notificari [v4.0]",
                     bg=C["bg_card"], fg=C["accent"],
                     font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(0,4))

            self._var_aot = tk.BooleanVar(
                value=bool(self.settings.get("always_on_top", False)))
            def _toggle_aot():
                v = self._var_aot.get()
                self.root.attributes("-topmost", v)
                self.settings["always_on_top"] = v
                self._save_settings()
                self._status_var.set(
                    "\\U0001f4cc Always on Top: ON" if v
                    else "\\U0001f4cc Always on Top: OFF")
            tk.Checkbutton(
                frm,
                text="\\U0001f4cc Always on Top (fereastra ramane deasupra)",
                variable=self._var_aot, command=_toggle_aot,
                bg=C["bg_card"], fg=C["text"],
                selectcolor=C["bg_input"],
                activebackground=C["bg_card"],
                font=("Segoe UI", 11)
            ).pack(anchor="w", pady=4)

            # ── DND [F10] ─────────────────────────────────────────
            self._var_dnd = tk.BooleanVar(
                value=bool(self.settings.get("auto_dnd", False)))
            tk.Checkbutton(
                frm,
                text="\\U0001f515 Activeaza DND automat la rulare/inregistrare",
                variable=self._var_dnd,
                command=lambda: (
                    self.settings.update({"auto_dnd": self._var_dnd.get()}),
                    self._save_settings()
                ),
                bg=C["bg_card"], fg=C["text"],
                selectcolor=C["bg_input"],
                activebackground=C["bg_card"],
                font=("Segoe UI", 11)
            ).pack(anchor="w", pady=4)

            # ── Scalare UI [F7] ───────────────────────────────────
            tk.Label(frm, text="\\U0001f50d Scalare UI [v4.0]",
                     bg=C["bg_card"], fg=C["accent"],
                     font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(8,2))

            _sf = tk.Frame(frm, bg=C["bg_card"])
            _sf.pack(fill="x", pady=2)
            self._var_ui_scale = tk.DoubleVar(
                value=float(self.settings.get("ui_scale", 1.0)))
            _slbl = tk.Label(_sf, text=f"{int(self._var_ui_scale.get()*100)}%",
                             bg=C["bg_card"], fg=C["accent"],
                             font=("Segoe UI", 12, "bold"), width=5)
            _slbl.pack(side="right", padx=8)
            def _on_scale_move(val):
                pct = round(float(val) * 100 / 5) * 5
                self._var_ui_scale.set(pct / 100)
                _slbl.config(text=f"{pct}%")
            tk.Scale(_sf, from_=0.80, to=1.25, resolution=0.05,
                     orient="horizontal", variable=self._var_ui_scale,
                     command=_on_scale_move,
                     bg=C["bg_card"], fg=C["text"],
                     troughcolor=C["bg_input"],
                     highlightthickness=0, length=280
                     ).pack(side="left", padx=4)

            _pf = tk.Frame(frm, bg=C["bg_card"])
            _pf.pack(fill="x", pady=2)
            for _lbl, _val in [("80%",0.80),("90%",0.90),("100%",1.00),
                                ("110%",1.10),("125%",1.25)]:
                tk.Button(_pf, text=_lbl,
                          command=lambda v=_val: (
                              self._var_ui_scale.set(v),
                              _slbl.config(text=f"{int(v*100)}%")),
                          bg=C["bg_input"], fg=C["text"],
                          font=("Segoe UI", 9), relief="flat",
                          cursor="hand2", padx=6
                          ).pack(side="left", padx=3)

            def _apply_scale():
                scale = self._var_ui_scale.get()
                self.settings["ui_scale"] = scale
                self._save_settings()
                bw, bh = 1280, 750
                self.root.geometry(f"{int(bw*scale)}x{int(bh*scale)}")
                try:
                    import tkinter.font as _tkf
                    for nm in _tkf.names():
                        try:
                            f = _tkf.nametofont(nm)
                            orig = f.cget("size")
                            if orig > 0:
                                f.configure(size=max(7, int(orig*scale)))
                        except Exception:
                            pass
                except Exception:
                    pass
                self._status_var.set(f"\\u2705 Scalare aplicata: {int(scale*100)}%")

            tk.Button(frm, text="\\u2705 Aplica Scalare",
                      command=_apply_scale,
                      bg=C["success"], fg="white",
                      font=("Segoe UI", 11, "bold"),
                      relief="flat", cursor="hand2",
                      padx=12, pady=4
                      ).pack(anchor="w", pady=8)
        except Exception as _e40:
            import logging
            logging.warning(f"[v4.0] Settings block error: {_e40}")
'''

# ══════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════
def main():
    global ok_count, fail_count

    # ── Gaseste fisierul sursa ────────────────────────────────────
    src_path = None
    for candidate in POSSIBLE_SOURCES:
        if os.path.exists(candidate):
            src_path = candidate
            break
    if src_path is None:
        print(f"❌ Fisierul sursa nu a fost gasit!")
        print(f"   Cautat: {POSSIBLE_SOURCES}")
        print(f"   Asigura-te ca fisierul e in acelasi director.")
        sys.exit(1)

    log(f"\n{'═'*60}")
    log(f"  AutoPilot DC — Aplicare Patch-uri v4.0")
    log(f"{'═'*60}")
    log(f"  Sursa:  {src_path}")
    log(f"  Output: {OUTPUT_FILE}")
    log(f"{'═'*60}\n")

    # ── Citeste sursa ─────────────────────────────────────────────
    with open(src_path, "r", encoding="utf-8") as f:
        src = f.read()
    log(f"  Sursa incarcata: {len(src):,} chars | "
        f"{src.count(chr(10))+1} linii\n")

    # ══════════════════════════════════════════════════════════════
    # PATCH 1: Version bump
    # ══════════════════════════════════════════════════════════════
    log("── P1: Version bump ──────────────────────────────────────")
    src = apply(src,
        'APP_VERSION = "3.9"',
        'APP_VERSION = "4.0"',
        "APP_VERSION 3.9 → 4.0")

    # ══════════════════════════════════════════════════════════════
    # PATCH 2: Optional imports (dupa PYNPUT_AVAILABLE = False)
    # ══════════════════════════════════════════════════════════════
    log("── P2: Optional imports ──────────────────────────────────")
    # Cauta linia cu PYNPUT_AVAILABLE si insereaza dupa ea
    anchor_p2 = "PYNPUT_AVAILABLE = False"
    if anchor_p2 in src:
        # Gaseste sfarsitul liniei
        idx = src.index(anchor_p2) + len(anchor_p2)
        # Avanseaza pana la newline
        nl = src.find("\n", idx)
        if nl == -1:
            nl = len(src)
        src = src[:nl+1] + OPTIONAL_IMPORTS + src[nl+1:]
        ok_count += 1
        log("  ✅  Optional imports inserate dupa PYNPUT_AVAILABLE")
    else:
        # Fallback: insereaza dupa primul bloc de imports (dupa ultimul ^import)
        import_matches = list(re.finditer(r'^(?:import|from)\s+\S+',
                                          src, re.MULTILINE))
        if import_matches:
            last_imp = import_matches[-1]
            nl = src.find("\n", last_imp.end())
            src = src[:nl+1] + OPTIONAL_IMPORTS + src[nl+1:]
            ok_count += 1
            log("  ✅  Optional imports inserate dupa ultimul import (fallback)")
        else:
            fail_count += 1
            log("  ❌  FAIL: Optional imports – anchor negasit")

    # ══════════════════════════════════════════════════════════════
    # PATCH 3: FocusAssistManager (inainte de class RunIndicatorOverlay)
    # ══════════════════════════════════════════════════════════════
    log("── P3: FocusAssistManager ────────────────────────────────")
    anchor_p3 = "class RunIndicatorOverlay:"
    src = apply(src,
        anchor_p3,
        FOCUS_ASSIST_CLASS + anchor_p3,
        "FocusAssistManager inserata inainte de RunIndicatorOverlay")

    # ══════════════════════════════════════════════════════════════
    # PATCH 4: VerboseLogger (inainte de class RunIndicatorOverlay)
    # ══════════════════════════════════════════════════════════════
    log("── P4: VerboseLogger ─────────────────────────────────────")
    anchor_p4 = "class RunIndicatorOverlay:"
    src = apply(src,
        anchor_p4,
        VERBOSE_LOGGER_CLASS + anchor_p4,
        "VerboseLogger inserata inainte de RunIndicatorOverlay")

    # ══════════════════════════════════════════════════════════════
    # PATCH 5: HybridRoutineEngine (inainte de class RunIndicatorOverlay)
    # ══════════════════════════════════════════════════════════════
    log("── P5: HybridRoutineEngine ───────────────────────────────")
    anchor_p5 = "class RunIndicatorOverlay:"
    src = apply(src,
        anchor_p5,
        HYBRID_ENGINE_CLASS + anchor_p5,
        "HybridRoutineEngine inserata inainte de RunIndicatorOverlay")

    # ══════════════════════════════════════════════════════════════
    # PATCH 6: RunIndicatorOverlay – inlocuieste clasa existenta
    # ══════════════════════════════════════════════════════════════
    log("── P6: RunIndicatorOverlay v4.0 ──────────────────────────")
    # Cauta clasa existenta si inlocuieste pana la urmatoarea clasa
    src = apply(src,
        r'class RunIndicatorOverlay:.*?(?=\nclass |\Z)',
        RUN_INDICATOR_NEW,
        "RunIndicatorOverlay inlocuita cu v4.0",
        count=1, regex=True)

    # ══════════════════════════════════════════════════════════════
    # PATCH 7: Fix KEY vk→char in RecorderEngine._on_press
    # ══════════════════════════════════════════════════════════════
    log("── P7: Fix KEY vk→char ───────────────────────────────────")
    old_key = ('        try:\n'
               '            ks = key.char if (hasattr(key,"char") and key.char) '
               'else getattr(key,"name","?")\n'
               '        except Exception:\n'
               '            ks = str(key)')
    new_key = (
        '        try:\n'
        '            # [v4.0 F1] Fix vk→char (ex: Ctrl+vk65 → Ctrl+A)\n'
        '            ks = None\n'
        '            if hasattr(key, "char") and key.char and key.char.isprintable():\n'
        '                _mods = getattr(self, "_modifiers", set())\n'
        '                ks = key.char.upper() if any(\n'
        '                    m in _mods for m in ("ctrl_l", "ctrl_r")\n'
        '                ) else key.char\n'
        '            elif hasattr(key, "vk") and key.vk and 65 <= key.vk <= 90:\n'
        '                ks = chr(key.vk)\n'
        '            elif hasattr(key, "vk") and key.vk and 48 <= key.vk <= 57:\n'
        '                ks = chr(key.vk)\n'
        '            else:\n'
        '                ks = getattr(key, "name", str(key))\n'
        '            if not ks:\n'
        '                ks = "?"\n'
        '        except Exception:\n'
        '            ks = str(key)'
    )
    src = apply(src, old_key, new_key, "Fix KEY vk→char in RecorderEngine")

    # ══════════════════════════════════════════════════════════════
    # PATCH 8: on_verbose_logger in PlayerEngine.__init__
    # ══════════════════════════════════════════════════════════════
    log("── P8: VerboseLogger in PlayerEngine ─────────────────────")
    anchor_p8 = "self.on_iter_update:   Optional[Callable] = None  # (cur, total)"
    new_p8    = (anchor_p8 + "\n"
                 "        self.on_verbose_log:   Optional[Callable] = None  "
                 "# [v4.0 F3] verbose\n"
                 "        self._verbose_logger = None  # [v4.0 F3]")
    src = apply(src, anchor_p8, new_p8,
                "on_verbose_logger adaugat in PlayerEngine.__init__")

    # ══════════════════════════════════════════════════════════════
    # PATCH 9: Verbose logging in PlayerEngine._loop (dupa on_step_start)
    # ══════════════════════════════════════════════════════════════
    log("── P9: Verbose logging in _loop ──────────────────────────")
    anchor_p9 = ("                # Notifica UI\n"
                 "                if self.on_step_start:\n"
                 "                    self.on_step_start(idx, step)")
    new_p9    = (anchor_p9 + "\n"
                 "                # [v4.0 F3] Verbose log\n"
                 "                if self._verbose_logger is not None:\n"
                 "                    try:\n"
                 "                        self._verbose_logger.log_step(step, idx)\n"
                 "                    except Exception:\n"
                 "                        pass")
    src = apply(src, anchor_p9, new_p9,
                "Verbose logging in PlayerEngine._loop")

    # ══════════════════════════════════════════════════════════════
    # PATCH 10: Rep counter callback in _loop (dupa on_iter_update)
    # ══════════════════════════════════════════════════════════════
    log("── P10: Rep counter update_rep in _loop ──────────────────")
    anchor_p10 = ("            if self.on_iter_update:\n"
                  "                self.on_iter_update(it, repeat)")
    new_p10    = (anchor_p10 + "\n"
                  "            # [v4.0 F2] Overlay rep counter\n"
                  "            if hasattr(self, '_run_indicator') and "
                  "self._run_indicator:\n"
                  "                try:\n"
                  "                    self._run_indicator.update_rep(it, repeat)\n"
                  "                except Exception:\n"
                  "                    pass")
    src = apply(src, anchor_p10, new_p10,
                "Rep counter update_rep in _loop")

    # ══════════════════════════════════════════════════════════════
    # PATCH 11: Toolbar – Verbose checkbox inainte de _set_btn_state_idle
    # ══════════════════════════════════════════════════════════════
    log("── P11: Toolbar Verbose checkbox ─────────────────────────")
    anchor_p11 = "        # ── Stare initiala butoane ──"
    new_p11 = (
        "        # [v4.0 F3] Verbose Log checkbox\n"
        "        self._var_verbose = tk.BooleanVar(value=False)\n"
        "        tk.Checkbutton(\n"
        "            tb, text=\"\\U0001f4cb Verbose\",\n"
        "            variable=self._var_verbose,\n"
        "            bg=C[\"bg_card\"], fg=C[\"text\"],\n"
        "            selectcolor=C[\"bg_input\"],\n"
        "            activebackground=C[\"bg_card\"],\n"
        "            font=(\"Segoe UI\", 10), cursor=\"hand2\"\n"
        "        ).pack(side=\"left\", padx=(6, 2))\n\n"
        + anchor_p11
    )
    src = apply(src, anchor_p11, new_p11,
                "Verbose checkbox adaugat in toolbar")

    # ══════════════════════════════════════════════════════════════
    # PATCH 12: Report Bug in meniu Ajutor
    # ══════════════════════════════════════════════════════════════
    log("── P12: Report Bug in meniu ──────────────────────────────")
    # Cauta "Despre" in meniu si insereaza inainte
    anchor_p12 = 'label="Despre'
    if anchor_p12 in src:
        idx12 = src.index(anchor_p12)
        # Gaseste inceputul liniei (add_command)
        line_start = src.rfind("\n", 0, idx12) + 1
        insert_block = (
            "        hm.add_command(\n"
            "            label=\"\\U0001f41b  Raporteaza Bug\",\n"
            "            command=lambda: __import__(\"webbrowser\").open(\n"
            "                \"mailto:bogdan.murar@siemens.com\"\n"
            "                \"?subject=AutoPilot%20DC%20v4.0%20-%20Bug\"\n"
            "            )\n"
            "        )\n"
            "        hm.add_separator()\n"
        )
        src = src[:line_start] + insert_block + src[line_start:]
        ok_count += 1
        log("  ✅  Report Bug adaugat in meniu Ajutor")
    else:
        fail_count += 1
        log("  ❌  FAIL: Report Bug – anchor 'Despre' negasit in meniu")

    # ══════════════════════════════════════════════════════════════
    # PATCH 13: Setari v4.0 (AOT + DND + Scale) la sfarsitul
    #           metodei _build_tab_settings
    # ══════════════════════════════════════════════════════════════
    log("── P13: Setari v4.0 (AOT+DND+Scale) ─────────────────────")
    # Cauta sfarsitul metodei _build_tab_settings
    # Strategia: gaseste "def _build_tab_settings(" si apoi
    # urmatoarea metoda "    def " la nivel de clasa
    m13 = re.search(
        r'(def _build_tab_settings\(.*?)'
        r'(?=\n    def |\nclass |\Z)',
        src, re.DOTALL
    )
    if m13:
        old_block = m13.group(0)
        new_block = old_block.rstrip() + "\n" + SETTINGS_V40_BLOCK + "\n"
        src = src[:m13.start()] + new_block + src[m13.end():]
        ok_count += 1
        log("  ✅  Setari v4.0 adaugate la sfarsitul _build_tab_settings")
    else:
        fail_count += 1
        log("  ❌  FAIL: Setari v4.0 – _build_tab_settings negasita")

    # ══════════════════════════════════════════════════════════════
    # PATCH 14: HybridEngine init + metode in MainWindow.__init__
    # ══════════════════════════════════════════════════════════════
    log("── P14: HybridEngine init in MainWindow ──────────────────")
    # Cauta _build_toolbar(self) si insereaza inainte initializarea
    anchor_p14 = "        self._build_toolbar()"
    new_p14 = (
        "        # [v4.0 F5] Hybrid engine\n"
        "        self._hybrid_engine = HybridRoutineEngine(self.root)\n"
        "        # [v4.0 F8] Resize bind\n"
        "        self._resize_after_id = None\n"
        "        self.root.bind(\"<Configure>\", self._on_window_configure)\n"
        + anchor_p14
    )
    src = apply(src, anchor_p14, new_p14,
                "HybridEngine + resize bind in MainWindow.__init__")

    # ══════════════════════════════════════════════════════════════
    # PATCH 15: Metode hibrid + resize inserate in MainWindow
    #           (dupa _build_tab_settings)
    # ══════════════════════════════════════════════════════════════
    log("── P15: Metode hibrid + resize in MainWindow ─────────────")
    # Insereaza dupa _build_tab_settings (dupa blocul ei)
    anchor_p15_re = r'(def _build_tab_settings\(.*?)(\n    def |\nclass |\Z)'
    m15 = re.search(anchor_p15_re, src, re.DOTALL)
    if m15:
        insert_pos = m15.start(2)
        src = src[:insert_pos] + "\n" + HYBRID_METHODS + src[insert_pos:]
        ok_count += 1
        log("  ✅  Metode hibrid + resize inserate in MainWindow")
    else:
        fail_count += 1
        log("  ❌  FAIL: Metode hibrid – pozitie inserare negasita")

    # ══════════════════════════════════════════════════════════════
    # PATCH 16: DND la play started (dupa run_indicator.show())
    # ══════════════════════════════════════════════════════════════
    log("── P16: DND la play/rec started/stopped ──────────────────")
    # Cauta run_indicator.show() si adauga DND dupa
    anchor_p16 = "self.run_indicator.show()"
    if anchor_p16 in src:
        idx16 = src.index(anchor_p16) + len(anchor_p16)
        nl16  = src.find("\n", idx16)
        dnd_block = (
            "\n"
            "        # [v4.0 F10] DND automat\n"
            "        if getattr(self, '_var_dnd', None) and self._var_dnd.get():\n"
            "            _focus_assist.enable()\n"
            "        # [v4.0 F3] VerboseLogger\n"
            "        if getattr(self, '_var_verbose', None) and self._var_verbose.get():\n"
            "            if hasattr(self, 'player'):\n"
            "                self.player._verbose_logger = VerboseLogger()\n"
            "        # [v4.0 F2] Rep overlay ref\n"
            "        if hasattr(self, 'player') and hasattr(self, 'run_indicator'):\n"
            "            self.player._run_indicator = self.run_indicator"
        )
        src = src[:nl16] + dnd_block + src[nl16:]
        ok_count += 1
        log("  ✅  DND + VerboseLogger + rep_indicator la play started")
    else:
        fail_count += 1
        log("  ❌  FAIL: DND – 'run_indicator.show()' negasit")

    # DND disable la stop
    anchor_p16b = "self.run_indicator.hide()"
    if anchor_p16b in src:
        idx16b = src.index(anchor_p16b) + len(anchor_p16b)
        nl16b  = src.find("\n", idx16b)
        src = src[:nl16b] + (
            "\n"
            "        # [v4.0 F10] Restaurare DND\n"
            "        _focus_assist.disable()\n"
            "        # [v4.0 F3] Reset VerboseLogger\n"
            "        if hasattr(self, 'player'):\n"
            "            self.player._verbose_logger = None"
        ) + src[nl16b:]
        ok_count += 1
        log("  ✅  DND disable + VerboseLogger reset la play stopped")
    else:
        fail_count += 1
        log("  ❌  FAIL: DND disable – 'run_indicator.hide()' negasit")

    # ══════════════════════════════════════════════════════════════
    # PATCH 17: Always on Top aplicat la startup (in __init__)
    # ══════════════════════════════════════════════════════════════
    log("── P17: Always on Top la startup ─────────────────────────")
    anchor_p17 = "        self._build_toolbar()"
    new_p17_aot = (
        "        # [v4.0 F9] Always on Top la startup\n"
        "        if self.settings.get('always_on_top', False):\n"
        "            self.root.attributes('-topmost', True)\n"
        + anchor_p17
    )
    src = apply(src, anchor_p17, new_p17_aot,
                "Always on Top aplicat la startup")

    # ══════════════════════════════════════════════════════════════
    # RAPORT FINAL
    # ══════════════════════════════════════════════════════════════
    log(f"\n{'═'*60}")
    log(f"  REZULTAT: {ok_count} OK | {fail_count} FAIL")
    log(f"  Dimensiune finala: {len(src):,} chars | "
        f"{src.count(chr(10))+1} linii")
    log(f"{'═'*60}\n")

    if fail_count > 0:
        log(f"  ⚠️  {fail_count} patch-uri nu au putut fi aplicate.")
        log(f"     Verifica log-ul de mai sus si aplica-le manual.")
        log(f"     Fisierul OUTPUT va fi generat cu patch-urile reusit aplicate.\n")

    # ── Scrie output ──────────────────────────────────────────────
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(src)
    log(f"  ✅  Fisier generat: {OUTPUT_FILE}")

    # ── Scrie log ─────────────────────────────────────────────────
    log_path = f"patch_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    with open(log_path, "w", encoding="utf-8") as f:
        f.write("\n".join(log_lines))
    log(f"  📋  Log salvat: {log_path}\n")

    return fail_count == 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
