# -*- coding: utf-8 -*-
# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  AUTOPILOT DC v4.1 — STUDIO RPR (Python / Tkinter)                           ║
# ║  Editorul vizual de rutine pe obiecte, integrat in fereastra aplicatiei.     ║
# ╚══════════════════════════════════════════════════════════════════════════════╝
#
#   Stanga : blocuri (pasi) + Object Repository
#   Centru : arborele rutinei (pasi, ramuri Atunci/Altfel, bucle)
#   Dreapta: proprietatile pasului selectat (fara cod)
#   Jos    : logul rularii + variabilele
#
# Fluxul tipic:
#   1. marchezi obiectele (Spy) o singura data
#   2. adaugi pasi din stanga si alegi obiectele din liste
#   3. ▶ Ruleaza (sau ⏭ Pas cu pas)
#
# Motorul (rpr/engine.py) ruleaza pe un fir separat; tot ce ajunge in interfata
# trece printr-o coada citita de firul Tk (Tkinter nu e sigur intre fire).

from __future__ import annotations

import copy
import ctypes
import os
import queue
import re
import subprocess
import sys
import threading
import uuid
from tkinter import filedialog, messagebox, ttk
import tkinter as tk
from typing import Any, Callable, Dict, List, Optional, Tuple

from rpr.drivers.base import DriverProvider
from rpr.engine import RprEngine
from rpr.host import AlertDecision, ErrorDecision, RunAlert, RunGuard, RunHost, RunLogEntry
from rpr.legacy import execute_legacy_step
from rpr.model import (ACTIONS, ActionNode, BreakNode, CellColor, CompareOperator, Condition, ConditionKind,
                       ErrorPolicy, ForEachRowNode, GroupNode, IfNode, LegacyStepNode, Locator, LocatorKind,
                       LogNode, LoopMode, LoopNode, ObjectRepository, QuestionNode, Routine, RprAction, RprLogLevel,
                       RprNode, SetVariableNode, StopNode, TryNode, UiObject, UiTechnology, VariableOperation,
                       WaitMode, WaitNode, WriteExcelNode, action_info, flatten, sanitize_name)
from rpr.storage import Examples, ExcelInfo, RepositoryStore, RoutineStore, RprPaths, RunLogExporter

try:
    import autopilot_safety as safety
except Exception:  # noqa: BLE001
    safety = None

HERE = os.path.dirname(os.path.abspath(__file__))
GUIDE_FILE = os.path.join(HERE, "docs", "GHID_STUDIO_RPR.md")

# ==============================================================================
# 1. ETICHETE IN ROMANA (identice cu Studio C#)
# ==============================================================================
ERROR_POLICIES = [
    (ErrorPolicy.Inherit, "Ca setarea rutinei"),
    (ErrorPolicy.Ask, "Intreaba-ma (Reincearca / Sari / Opreste)"),
    (ErrorPolicy.Stop, "Opreste rutina"),
    (ErrorPolicy.Continue, "Continua (doar logheaza)"),
    (ErrorPolicy.SkipRow, "Sari la urmatorul rand Excel"),
]
CONDITION_KINDS = [
    (ConditionKind.ElementExists, "Obiectul exista pe ecran"),
    (ConditionKind.ElementNotExists, "Obiectul NU exista / a disparut"),
    (ConditionKind.ElementVisible, "Obiectul e vizibil"),
    (ConditionKind.ElementEnabled, "Obiectul e activ (poate fi apasat)"),
    (ConditionKind.ElementText, "Textul obiectului ..."),
    (ConditionKind.Compare, "Compara doua valori / variabile"),
    (ConditionKind.AllOf, "Toate conditiile de mai jos (SI)"),
    (ConditionKind.AnyOf, "Oricare din conditiile de mai jos (SAU)"),
]
OPERATORS = [
    (CompareOperator.Equals, "este egal cu"),
    (CompareOperator.NotEquals, "este diferit de"),
    (CompareOperator.Contains, "contine"),
    (CompareOperator.NotContains, "nu contine"),
    (CompareOperator.StartsWith, "incepe cu"),
    (CompareOperator.EndsWith, "se termina cu"),
    (CompareOperator.IsEmpty, "este gol"),
    (CompareOperator.IsNotEmpty, "nu este gol"),
    (CompareOperator.GreaterThan, "este mai mare decat"),
    (CompareOperator.GreaterOrEqual, "este mai mare sau egal cu"),
    (CompareOperator.LessThan, "este mai mic decat"),
    (CompareOperator.LessOrEqual, "este mai mic sau egal cu"),
    (CompareOperator.MatchesRegex, "se potriveste cu expresia (regex)"),
]
TECHNOLOGIES = [
    (UiTechnology.Web, "Web (Playwright)"),
    (UiTechnology.WebSelenium, "Web (Selenium)"),
    (UiTechnology.Sap, "SAP GUI"),
    (UiTechnology.Desktop, "Aplicatie desktop"),
]
WAIT_MODES = [(WaitMode.Seconds, "Un numar de secunde"), (WaitMode.UntilTrue, "Pana cand o conditie e adevarata")]
LOOP_MODES = [
    (LoopMode.Times, "De un numar de ori"),
    (LoopMode.While, "Cat timp conditia e adevarata (verifica inainte)"),
    (LoopMode.Until, "Pana cand conditia devine adevarata (verifica dupa)"),
]
VARIABLE_OPS = [
    (VariableOperation.Set, "Seteaza valoarea"),
    (VariableOperation.Append, "Adauga la final"),
    (VariableOperation.Increment, "Creste cu (implicit 1)"),
    (VariableOperation.Decrement, "Scade cu (implicit 1)"),
    (VariableOperation.Trim, "Sterge spatiile de la capete"),
    (VariableOperation.ToUpper, "LITERE MARI"),
    (VariableOperation.ToLower, "litere mici"),
    (VariableOperation.Replace, "Inlocuieste text"),
]
CELL_COLORS = [
    (CellColor.None_, "Fara culoare"), (CellColor.Green, "Verde (OK)"), (CellColor.Red, "Rosu (eroare)"),
    (CellColor.Yellow, "Galben (atentie)"), (CellColor.Orange, "Portocaliu"), (CellColor.Blue, "Albastru"),
]
LOG_LEVELS = [(RprLogLevel.Info, "Informatie"), (RprLogLevel.Warning, "Atentionare"), (RprLogLevel.Error, "Eroare")]

_WEB_ACTIONS = {RprAction.OpenBrowser, RprAction.Navigate, RprAction.Back, RprAction.Refresh, RprAction.SwitchTab,
                RprAction.CloseBrowser, RprAction.HandleDialog, RprAction.ScreenshotPage}
_SAP_ACTIONS = {RprAction.SapConnect, RprAction.SapTransaction, RprAction.SapSendKey, RprAction.SapReadStatusBar,
                RprAction.SapGridReadCell, RprAction.SapGridRowCount}
_DESK_ACTIONS = {RprAction.LaunchApp, RprAction.AttachWindow, RprAction.CloseWindow}


def icon_for(node: RprNode) -> str:
    if isinstance(node, ActionNode):
        a = node.action
        if a in _WEB_ACTIONS:
            return "🌐"
        if a in _SAP_ACTIONS:
            return "🟦"
        if a in _DESK_ACTIONS:
            return "🖥"
        if a in (RprAction.TypeText, RprAction.AppendText, RprAction.Clear):
            return "⌨"
        if a in (RprAction.ReadText, RprAction.ReadValue, RprAction.ReadAttribute):
            return "👁"
        return "👆"
    return {WaitNode: "⏱", SetVariableNode: "✎", IfNode: "🔀", LoopNode: "🔁", ForEachRowNode: "📊",
            WriteExcelNode: "📝", QuestionNode: "💬", TryNode: "🛡", GroupNode: "📁", LogNode: "🗒",
            BreakNode: "⏏", StopNode: "⛔", LegacyStepNode: "🖱"}.get(type(node), "•")


# Blocurile din stanga: (grup, [(text, descriere, fabrica)])
TOOLBOX: List[Tuple[str, List[Tuple[str, str, Callable[[], RprNode]]]]] = [
    ("Actiuni", [
        ("👆  Click pe obiect", "Click / dublu click / click dreapta pe un element marcat",
         lambda: ActionNode(action=RprAction.Click)),
        ("⌨  Scrie text", "Completeaza un camp (accepta variabile din Excel)", lambda: ActionNode(action=RprAction.TypeText)),
        ("👁  Citeste valoare", "Citeste textul unui element intr-o variabila",
         lambda: ActionNode(action=RprAction.ReadText, output_variable="Valoare")),
        ("⌨  Apasa tasta", "Enter, Tab, F5, Ctrl+S ...", lambda: ActionNode(action=RprAction.PressKey, value="Enter")),
        ("🌐  Deschide browser", "Porneste browserul (Edge implicit) la o adresa",
         lambda: ActionNode(action=RprAction.OpenBrowser, technology=UiTechnology.Web, value="https://")),
        ("🌐  Mergi la adresa", "Navigheaza la un URL (poate contine variabile)",
         lambda: ActionNode(action=RprAction.Navigate, technology=UiTechnology.Web, value="https://")),
        ("🟦  SAP: conecteaza", "Se ataseaza la SAP GUI deschis",
         lambda: ActionNode(action=RprAction.SapConnect, technology=UiTechnology.Sap)),
        ("🟦  SAP: tranzactie", "Porneste o tranzactie (ex: /nVA03)",
         lambda: ActionNode(action=RprAction.SapTransaction, technology=UiTechnology.Sap, value="/n")),
        ("🟦  SAP: tasta (Enter/F8...)", "Trimite o tasta catre SAP",
         lambda: ActionNode(action=RprAction.SapSendKey, technology=UiTechnology.Sap, value="Enter")),
        ("🟦  SAP: bara de stare", "Citeste mesajul din bara de stare SAP",
         lambda: ActionNode(action=RprAction.SapReadStatusBar, technology=UiTechnology.Sap, output_variable="StareSAP")),
        ("🖥  Porneste aplicatie", "Porneste un program Windows",
         lambda: ActionNode(action=RprAction.LaunchApp, technology=UiTechnology.Desktop)),
        ("🖥  Ataseaza fereastra", "Lucreaza intr-o fereastra deja deschisa",
         lambda: ActionNode(action=RprAction.AttachWindow, technology=UiTechnology.Desktop, value="proces:")),
    ]),
    ("Flux (conditii si repetari)", [
        ("⏱  Asteapta", "Secunde sau pana apare / dispare ceva", WaitNode),
        ("🔀  Daca / Altfel", "Ramuri diferite dupa o conditie", IfNode),
        ("🔁  Repeta", "De N ori, cat timp sau pana cand", LoopNode),
        ("🛡  Incearca / La eroare", "Prinde erorile fara sa opreasca rutina", TryNode),
        ("💬  Intrebare", "Intreaba utilizatorul, cu butoane personalizate", QuestionNode),
        ("⏏  Iesi din bucla", "Opreste bucla curenta / sari la urmatoarea repetare", BreakNode),
        ("⛔  Opreste rutina", "Opreste rutina (cu sau fara eroare)", StopNode),
    ]),
    ("Date (Excel si variabile)", [
        ("📊  Pentru fiecare rand Excel", "Repeta pasii pentru fiecare rand dintr-un fisier Excel", ForEachRowNode),
        ("📝  Scrie in Excel", "Scrie in randul curent (in interiorul buclei Excel)", WriteExcelNode),
        ("✎  Variabila", "Seteaza / modifica o variabila", SetVariableNode),
    ]),
    ("Organizare", [
        ("📁  Grup", "Grupeaza pasi (doar pentru ordine)", GroupNode),
        ("🗒  Log", "Scrie un mesaj in log", LogNode),
    ]),
]


# ==============================================================================
# 2. UTILITARE DE INTERFATA
# ==============================================================================
class ToolTip:
    def __init__(self, widget, text: str):
        self._w, self._text, self._tip = widget, text, None
        widget.bind("<Enter>", self._show, add="+")
        widget.bind("<Leave>", self._hide, add="+")

    def _show(self, _e=None):
        if self._tip or not self._text:
            return
        x, y = self._w.winfo_rootx() + 12, self._w.winfo_rooty() + self._w.winfo_height() + 4
        self._tip = tk.Toplevel(self._w)
        self._tip.overrideredirect(True)
        self._tip.attributes("-topmost", True)
        tk.Label(self._tip, text=self._text, bg="#FFFFE0", fg="#222", font=("Segoe UI", 9),
                 relief="solid", bd=1, padx=6, pady=3, wraplength=360, justify="left").pack()
        self._tip.geometry(f"+{x}+{y}")

    def _hide(self, _e=None):
        if self._tip:
            self._tip.destroy()
            self._tip = None


class ScrollFrame(tk.Frame):
    """Cadru cu bara de derulare verticala; continutul se pune in .inner."""

    def __init__(self, master, bg: str):
        super().__init__(master, bg=bg)
        self.canvas = tk.Canvas(self, bg=bg, highlightthickness=0)
        self.vsb = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.inner = tk.Frame(self.canvas, bg=bg)
        self._win = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.canvas.configure(yscrollcommand=self.vsb.set)
        self.vsb.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        self.inner.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfigure(self._win, width=e.width))
        for w in (self.canvas, self.inner):
            w.bind("<Enter>", lambda e: self.canvas.bind_all("<MouseWheel>", self._wheel))
            w.bind("<Leave>", lambda e: self.canvas.unbind_all("<MouseWheel>"))

    def _wheel(self, e):
        if self.canvas.winfo_height() < self.inner.winfo_height():
            self.canvas.yview_scroll(int(-e.delta / 120), "units")

    def clear(self):
        for w in self.inner.winfo_children():
            w.destroy()
        self.canvas.yview_moveto(0)


def choice_dialog(parent, title: str, text: str, buttons: List[str], detail: str = "", C=None) -> str:
    """Intrebare cu butoane. Inchiderea ferestrei = ultimul buton (de obicei Opreste)."""
    C = C or {}
    bg, card, fg = C.get("bg_main", "#1E1E2E"), C.get("bg_card", "#2A2A3E"), C.get("text", "#FFFFFF")
    dlg = tk.Toplevel(parent)
    dlg.title(title)
    dlg.configure(bg=bg)
    dlg.attributes("-topmost", True)
    dlg.resizable(False, False)
    answer = {"v": buttons[-1] if buttons else ""}
    tk.Label(dlg, text=text, bg=bg, fg=C.get("warning", "#FF8800") if text.startswith("⚠") else fg,
             font=("Segoe UI", 12, "bold"), wraplength=560, justify="left").pack(anchor="w", padx=18, pady=(16, 8))
    if detail:
        rows = sum(max(1, -(-len(l) // 72)) for l in detail.split("\n"))
        t = tk.Text(dlg, height=min(14, rows + 1), width=74, wrap="word", bg=card, fg=fg, relief="flat",
                    font=("Segoe UI", 10), padx=8, pady=6)
        t.insert("1.0", detail)
        t.configure(state="disabled")
        t.pack(padx=18, fill="x")
    row = tk.Frame(dlg, bg=bg)
    row.pack(anchor="e", padx=18, pady=14)
    for b in buttons:
        low = b.lower()
        color = C.get("danger", "#CC0000") if low.startswith(("opr", "stop")) else \
            C.get("bg_input", "#3A3A5A") if low.startswith("sari") else C.get("success", "#00AA44")

        def pick(v=b):
            answer["v"] = v
            dlg.destroy()
        tk.Button(row, text=b, command=pick, bg=color, fg="white", relief="flat", font=("Segoe UI", 10, "bold"),
                  padx=12, pady=5, cursor="hand2", activebackground=color).pack(side="left", padx=4)
    dlg.update_idletasks()
    w, h = dlg.winfo_reqwidth(), dlg.winfo_reqheight()
    dlg.geometry(f"+{(dlg.winfo_screenwidth() - w) // 2}+{(dlg.winfo_screenheight() - h) // 3}")
    dlg.grab_set()
    dlg.focus_force()
    dlg.wait_window()
    return answer["v"]


def _new_ids(node: RprNode) -> None:
    node.id = uuid.uuid4().hex[:10]
    for _, lst in node.branches():
        for ch in lst:
            _new_ids(ch)


# ==============================================================================
# 3. LEGATURA MOTOR -> INTERFATA
# ==============================================================================
class StudioGuard(RunGuard):
    """Ferestre noi de eroare + aplicatie blocata, inainte de fiecare actiune."""

    def __init__(self):
        self._w = safety.WindowWatcher() if safety else None

    def begin_run(self):
        if self._w:
            self._w.reset()

    def acknowledge(self):
        if self._w:
            self._w.accept_current()

    def check_before_action(self, node):
        if not self._w:
            return None
        a = self._w.check_new_windows(report_all_dialogs=False)
        if a:
            return RunAlert(a.title, a.details, a.key)
        fg = safety.foreground()
        if not fg.is_own and safety.is_hung(fg.hwnd):
            return RunAlert("Aplicatia nu raspunde",
                            f"Fereastra {fg} nu raspunde (\"Not Responding\").\nAsteapta sa-si revina, apoi apasa Continua.",
                            "hung:" + fg.process)
        return None


class StudioRunHost(RunHost):
    """Motorul ruleaza pe alt fir: totul trece prin coada panoului."""

    def __init__(self, panel: "StudioPanel"):
        self._p = panel
        self.legacy_executor = execute_legacy_step

    def log(self, entry):
        self._p.post("log", entry)

    def node_started(self, node):
        self._p.post("started", node)

    def node_finished(self, node, success):
        self._p.post("finished", (node, success))

    def ask(self, title, text, buttons):
        return self._p.call_ui(lambda: choice_dialog(self._p, title, text, list(buttons), C=self._p.C))

    def ask_on_error(self, node, error, inside_excel_loop):
        btns = ["Reincearca", "Sari pasul"] + (["Sari randul"] if inside_excel_loop else []) + ["Opreste"]
        ans = self._p.call_ui(lambda: self._p.paused_dialog(
            "Pasul a esuat", f"Pasul \"{node.title}\" a esuat.", btns, error))
        return {"Reincearca": ErrorDecision.RETRY, "Sari pasul": ErrorDecision.SKIP,
                "Sari randul": ErrorDecision.SKIP_ROW}.get(ans, ErrorDecision.STOP)

    def ask_alert(self, node, alert, inside_excel_loop):
        cont, ign, skip, stop = "Continua", "Continua si nu mai intreba pentru asta", "Sari randul", "Opreste"
        btns = [cont, ign] + ([skip] if inside_excel_loop else []) + [stop]
        ans = self._p.call_ui(lambda: self._p.paused_dialog(
            "AutoPilot DC — ceva difera", f"⚠ {alert.title}", btns, f"Pasul: {node.title}\n\n{alert.details}"))
        return {cont: AlertDecision.CONTINUE, ign: AlertDecision.IGNORE_SIMILAR,
                skip: AlertDecision.SKIP_ROW}.get(ans, AlertDecision.STOP)


class RunControlWindow(tk.Toplevel):
    """Bara plutitoare in timpul rularii: Pauza / Pas / STOP + Ctrl+F11 / Ctrl+F12 oriunde."""

    def __init__(self, panel: "StudioPanel"):
        super().__init__(panel)
        self._p = panel
        C = panel.C
        self.title("AutoPilot DC — rulare")
        self.attributes("-topmost", True)
        self.attributes("-toolwindow", True)
        self.resizable(False, False)
        self.configure(bg=C["bg_card"])
        self.protocol("WM_DELETE_WINDOW", lambda: None)
        self._status = tk.Label(self, text="Pornire...", bg=C["bg_card"], fg=C["text"], font=("Segoe UI", 10, "bold"),
                                width=46, anchor="w")
        self._status.pack(padx=8, pady=(6, 2), anchor="w")
        row = tk.Frame(self, bg=C["bg_card"])
        row.pack(padx=8, pady=4, anchor="w")
        self._pause = tk.Button(row, text="⏸ Pauza", command=panel.toggle_pause, bg=C["warning"], fg="white",
                                relief="flat", font=("Segoe UI", 9, "bold"), padx=8, cursor="hand2")
        self._pause.pack(side="left", padx=2)
        tk.Button(row, text="⏭ Pas", command=panel.step_once, bg=C["bg_input"], fg=C["text"], relief="flat",
                  font=("Segoe UI", 9, "bold"), padx=8, cursor="hand2").pack(side="left", padx=2)
        tk.Button(row, text="⏹ STOP", command=panel.stop, bg=C["danger"], fg="white", relief="flat",
                  font=("Segoe UI", 9, "bold"), padx=8, cursor="hand2").pack(side="left", padx=2)
        tk.Label(self, text="Ctrl+F11 pauza/reluare  ·  Ctrl+F12 stop", bg=C["bg_card"], fg=C["text_dim"],
                 font=("Segoe UI", 8)).pack(padx=8, pady=(0, 6), anchor="w")
        self.update_idletasks()
        self.geometry(f"+{self.winfo_screenwidth() - self.winfo_reqwidth() - 24}+"
                      f"{self.winfo_screenheight() - self.winfo_reqheight() - 90}")
        self._was = (False, False)
        self._poll_keys()

    def set_status(self, text: str):
        self._status.configure(text=text[:70])

    def set_paused(self, paused: bool):
        self._pause.configure(text="▶ Reluare" if paused else "⏸ Pauza")

    def _poll_keys(self):
        try:
            gk = ctypes.windll.user32.GetAsyncKeyState
            down = lambda vk: bool(gk(vk) & 0x8000)  # noqa: E731
            ctrl = down(0x11)
            p, s = ctrl and down(0x7A), ctrl and down(0x7B)   # F11, F12
            if p and not self._was[0]:
                self._p.toggle_pause()
            if s and not self._was[1]:
                self._p.stop()
            self._was = (p, s)
        except Exception:
            pass
        self.after(100, self._poll_keys)


# ==============================================================================
# 4. PANOUL STUDIO
# ==============================================================================
class StudioPanel(tk.Frame):
    def __init__(self, master, colors: Dict[str, str], run_frame=None,
                 on_status: Optional[Callable[[str], None]] = None):
        super().__init__(master, bg=colors["bg_main"])
        self.C = colors
        self._run_frame = run_frame
        self._on_status = on_status or (lambda s: None)

        self.repo = ObjectRepository()
        self.repo_path = RprPaths.default_repository()
        self.routine = Routine()
        self.routine_path: Optional[str] = None
        self.dirty = False

        self.engine: Optional[RprEngine] = None
        self.drivers = self._build_drivers()
        self.busy = False
        self._run_control: Optional[RunControlWindow] = None
        self._queue: "queue.Queue[tuple]" = queue.Queue()
        self._items: Dict[str, Tuple[str, Optional[RprNode], List[RprNode]]] = {}
        self._running_iid: Optional[str] = None
        self._log_entries: List[RunLogEntry] = []

        self._styles()
        self._build()
        self.load_repository(RprPaths.default_repository())
        self.new_routine(ask=False)
        self.after(50, self._poll)

    # ── drivere (se completeaza in etapele 2-3) ─────────────────────────────
    @staticmethod
    def _build_drivers() -> DriverProvider:
        provider = DriverProvider()
        try:
            from rpr.drivers.registry import register_all
            register_all(provider)
        except ImportError:
            pass
        return provider

    # =========================================================================
    # Constructia interfetei
    # =========================================================================
    def _styles(self):
        C = self.C
        st = ttk.Style()
        st.configure("Studio.Treeview", background=C["bg_input"], fieldbackground=C["bg_input"],
                     foreground=C["text"], rowheight=24, font=("Segoe UI", 10), borderwidth=0)
        st.map("Studio.Treeview", background=[("selected", C["primary"])], foreground=[("selected", "white")])
        st.configure("Studio.Treeview.Heading", background=C["bg_card"], foreground=C["text_dim"],
                     font=("Segoe UI", 9, "bold"), relief="flat")
        st.configure("Studio.TNotebook", background=C["bg_main"], borderwidth=0)
        st.configure("Studio.TNotebook.Tab", background=C["bg_card"], foreground=C["text_dim"], padding=[10, 4],
                     font=("Segoe UI", 9, "bold"))
        st.map("Studio.TNotebook.Tab", background=[("selected", C["primary"])], foreground=[("selected", "white")])
        st.configure("Studio.TPanedwindow", background=C["border"])
        st.configure("Studio.TCombobox", fieldbackground=C["bg_input"], background=C["bg_card"],
                     foreground=C["text"], arrowcolor=C["text"])
        self.option_add("*TCombobox*Listbox.background", C["bg_input"])
        self.option_add("*TCombobox*Listbox.foreground", C["text"])
        self.option_add("*TCombobox*Listbox.selectBackground", C["primary"])

    def _label(self, parent, text, size=9, bold=False, color=None, **kw):
        return tk.Label(parent, text=text, bg=kw.pop("bg", parent["bg"]), fg=color or self.C["text"],
                        font=("Segoe UI", size, "bold" if bold else "normal"), **kw)

    def _btn(self, parent, text, cmd, color=None, tip="", **kw):
        bg = color or self.C["bg_input"]
        fg = "white" if color else self.C["text"]
        b = tk.Button(parent, text=text, command=cmd, bg=bg, fg=fg, activebackground=self.C["primary"],
                      activeforeground="white", relief="flat", font=("Segoe UI", 9, "bold"), padx=8, pady=2,
                      cursor="hand2", bd=0, **kw)
        if tip:
            ToolTip(b, tip)
        return b

    def _build(self):
        C = self.C
        vpaned = ttk.PanedWindow(self, orient="vertical", style="Studio.TPanedwindow")
        vpaned.pack(fill="both", expand=True, padx=4, pady=4)
        hpaned = ttk.PanedWindow(vpaned, orient="horizontal", style="Studio.TPanedwindow")
        vpaned.add(hpaned, weight=4)

        # ── Stanga: blocuri + obiecte ──
        left = tk.Frame(hpaned, bg=C["bg_main"], width=250)
        hpaned.add(left, weight=0)
        nb = ttk.Notebook(left, style="Studio.TNotebook")
        nb.pack(fill="both", expand=True)
        tb = ScrollFrame(nb, C["bg_main"])
        nb.add(tb, text="🧱 Pasi")
        self._build_toolbox(tb.inner)
        ob = tk.Frame(nb, bg=C["bg_main"])
        nb.add(ob, text="🎯 Obiecte")
        self._build_objects(ob)

        # ── Centru: arborele rutinei ──
        center = tk.Frame(hpaned, bg=C["bg_main"])
        hpaned.add(center, weight=3)
        head = tk.Frame(center, bg=C["bg_main"])
        head.pack(fill="x", pady=(0, 4))
        self._title = self._label(head, "Rutina noua", 12, True, C["primary"], anchor="w")
        self._title.pack(side="top", fill="x", padx=4)
        # butoanele pe rand separat: un nume lung de rutina nu le mai impinge in afara ecranului
        bar = tk.Frame(head, bg=C["bg_main"])
        bar.pack(side="top", fill="x", pady=(2, 0))
        for text, cmd, tip in [("▲", lambda: self.move(-1), "Muta sus (Ctrl+Sus)"),
                               ("▼", lambda: self.move(1), "Muta jos (Ctrl+Jos)"),
                               ("Duplica", self.duplicate, "Duplica pasul cu tot ce contine (Ctrl+D)"),
                               ("Activ / Omis", self.toggle_enabled, "Activeaza / omite pasul (Spatiu)"),
                               ("Sterge", self.delete_selected, "Sterge pasul (Delete)"),
                               ("⚙ Rutina", self.show_routine_settings, "Setarile rutinei si variabilele")]:
            self._btn(bar, text, cmd, tip=tip).pack(side="left", padx=1)

        tree_box = tk.Frame(center, bg=C["bg_main"])
        tree_box.pack(fill="both", expand=True)
        self.tree = ttk.Treeview(tree_box, show="tree", style="Studio.Treeview", selectmode="browse")
        vsb = ttk.Scrollbar(tree_box, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        self.tree.pack(side="left", fill="both", expand=True)
        self.tree.tag_configure("disabled", foreground=C["text_muted"])
        self.tree.tag_configure("branch", foreground=C["accent"], font=("Segoe UI", 9, "italic"))
        self.tree.tag_configure("running", background="#B36B00", foreground="white")
        self.tree.tag_configure("ok", foreground="#3CCF6E")
        self.tree.tag_configure("error", foreground="#FF5C5C")
        self.tree.bind("<<TreeviewSelect>>", self._on_select)
        self.tree.bind("<Delete>", lambda e: self.delete_selected())
        self.tree.bind("<space>", lambda e: (self.toggle_enabled(), "break")[1])
        self.tree.bind("<Control-Up>", lambda e: (self.move(-1), "break")[1])
        self.tree.bind("<Control-Down>", lambda e: (self.move(1), "break")[1])
        self.tree.bind("<Control-d>", lambda e: (self.duplicate(), "break")[1])

        # ── Dreapta: proprietati ──
        right = tk.Frame(hpaned, bg=C["bg_card"], width=380)
        hpaned.add(right, weight=2)
        self.props = ScrollFrame(right, C["bg_card"])
        self.props.pack(fill="both", expand=True, padx=2, pady=2)
        self.editor = PropertyEditor(self)

        # ── Jos: log + variabile ──
        bottom = ttk.Notebook(vpaned, style="Studio.TNotebook")
        vpaned.add(bottom, weight=1)
        logf = tk.Frame(bottom, bg=C["bg_main"])
        bottom.add(logf, text="📋 Log rulare")
        lbar = tk.Frame(logf, bg=C["bg_main"])
        lbar.pack(fill="x")
        self._btn(lbar, "📤 Export Excel", self.export_log, tip="Salveaza logul ca fisier Excel").pack(side="left", padx=2, pady=2)
        self._btn(lbar, "📂 Rezultate", lambda: os.startfile(RprPaths.output()), tip="Deschide folderul cu capturi si loguri").pack(side="left", padx=2)
        self._btn(lbar, "🧹 Goleste", self.clear_log).pack(side="left", padx=2)
        cols = ("ora", "nivel", "rand", "pas", "mesaj")
        self.log = ttk.Treeview(logf, columns=cols, show="headings", style="Studio.Treeview", height=6)
        for c, title, w, stretch in [("ora", "Ora", 70, False), ("nivel", "Nivel", 80, False), ("rand", "Rand", 50, False),
                                     ("pas", "Pas", 240, False), ("mesaj", "Mesaj", 500, True)]:
            self.log.heading(c, text=title, anchor="w")
            self.log.column(c, width=w, stretch=stretch, anchor="w")
        self.log.tag_configure("Error", foreground="#FF6B6B")
        self.log.tag_configure("Warning", foreground="#FFC24B")
        lsb = ttk.Scrollbar(logf, orient="vertical", command=self.log.yview)
        self.log.configure(yscrollcommand=lsb.set)
        lsb.pack(side="right", fill="y")
        self.log.pack(fill="both", expand=True)
        varf = tk.Frame(bottom, bg=C["bg_main"])
        bottom.add(varf, text="🔤 Variabile")
        self.vars = ttk.Treeview(varf, columns=("nume", "valoare"), show="headings", style="Studio.Treeview", height=6)
        self.vars.heading("nume", text="Variabila", anchor="w")
        self.vars.heading("valoare", text="Valoare (dupa ultima rulare)", anchor="w")
        self.vars.column("nume", width=220, stretch=False)
        self.vars.column("valoare", width=600, stretch=True)
        self.vars.pack(fill="both", expand=True)

    def _build_toolbox(self, host):
        C = self.C
        tk.Label(host, text="Click pe un bloc = il adaugi dupa pasul selectat. Ca sa adaugi IN interiorul unui "
                            "\"Daca\" sau al unei bucle, selecteaza mai intai ramura (ex: ▸ Atunci).",
                 bg=C["bg_main"], fg=C["text_dim"], font=("Segoe UI", 8), wraplength=220, justify="left").pack(
            anchor="w", padx=6, pady=(6, 2))
        for group, items in TOOLBOX:
            tk.Label(host, text=group.upper(), bg=C["bg_main"], fg=C["primary"], font=("Segoe UI", 8, "bold")).pack(
                anchor="w", padx=6, pady=(10, 2))
            for text, tip, factory in items:
                b = tk.Button(host, text=text, anchor="w", command=lambda f=factory: self.insert_node(f()),
                              bg=C["bg_card"], fg=C["text"], activebackground=C["primary"], activeforeground="white",
                              relief="flat", font=("Segoe UI", 9), padx=8, pady=3, cursor="hand2", bd=0)
                b.pack(fill="x", padx=6, pady=1)
                ToolTip(b, tip)

    def _build_objects(self, host):
        C = self.C
        top = tk.Frame(host, bg=C["bg_main"])
        top.pack(fill="x", padx=4, pady=4)
        self._obj_filter = tk.StringVar()
        e = tk.Entry(top, textvariable=self._obj_filter, bg=C["bg_input"], fg=C["text"], relief="flat",
                     insertbackground=C["text"], font=("Segoe UI", 9))
        e.pack(fill="x")
        ToolTip(e, "Cauta un obiect dupa nume")
        self._obj_filter.trace_add("write", lambda *a: self.refresh_objects())
        self.objects = ttk.Treeview(host, columns=("tip",), show="tree headings", style="Studio.Treeview")
        self.objects.heading("#0", text="Obiect", anchor="w")
        self.objects.heading("tip", text="Tehnologie", anchor="w")
        self.objects.column("#0", width=150)
        self.objects.column("tip", width=70, stretch=False)
        self.objects.pack(fill="both", expand=True, padx=4)
        self.objects.bind("<Double-1>", lambda e: self.edit_object())
        row = tk.Frame(host, bg=C["bg_main"])
        row.pack(fill="x", padx=4, pady=4)
        for text, cmd, tip in [("＋ Nou", self.new_object, "Obiect nou, cu locatori scrisi de mana"),
                               ("✎", self.edit_object, "Editeaza numele si locatorii (dublu click)"),
                               ("➕ Pas", self.object_to_step, "Adauga un pas Click pe acest obiect"),
                               ("🗑", self.delete_object, "Sterge obiectul din repository")]:
            self._btn(row, text, cmd, tip=tip).pack(side="left", padx=1)
        tk.Label(host, text="Spy (marcarea obiectelor cu mouse-ul) vine cu driverele Web / SAP / Desktop.",
                 bg=C["bg_main"], fg=C["text_dim"], font=("Segoe UI", 8), wraplength=220, justify="left").pack(
            anchor="w", padx=6, pady=(0, 6))

    # =========================================================================
    # Rutina: nou / deschide / salveaza
    # =========================================================================
    def set_status(self, text: str):
        self._on_status(text)

    def mark_dirty(self):
        self.dirty = True
        self._update_title()

    def _update_title(self):
        name = self.routine.name or "Rutina noua"
        self._title.configure(text=f"{name}{'  •  nesalvat' if self.dirty else ''}")

    def confirm_discard(self) -> bool:
        if not self.dirty:
            return True
        ans = messagebox.askyesnocancel("Studio RPR", f"Rutina \"{self.routine.name}\" are modificari nesalvate.\n"
                                                       "Le salvezi?", parent=self)
        if ans is None:
            return False
        return self.save_routine() if ans else True

    def new_routine(self, ask=True):
        if ask and not self.confirm_discard():
            return
        self.routine = Routine(name="Rutina noua")
        self.routine_path = None
        self.dirty = False
        self.rebuild_tree()
        self.show_routine_settings()
        self._update_title()

    def open_routine(self, path: Optional[str] = None):
        if not self.confirm_discard():
            return
        path = path or filedialog.askopenfilename(
            parent=self, title="Deschide rutina", initialdir=RprPaths.routines(),
            filetypes=[("Rutine AutoPilot", "*.rpr.json *.json"), ("Toate fisierele", "*.*")])
        if not path:
            return
        try:
            r = RoutineStore.load(path, self.repo)
        except Exception as ex:  # noqa: BLE001
            messagebox.showerror("Studio RPR", f"Rutina nu poate fi deschisa:\n{ex}", parent=self)
            return
        self.routine = r
        if r.repository_path.strip():
            self.load_repository(r.repository_path)
        converted = not path.lower().endswith(".rpr.json")
        self.routine_path = None if converted else path
        self.dirty = converted
        if converted:
            self.save_repository()
            messagebox.showinfo("Studio RPR", "Rutina veche a fost convertita: pasii de browser au devenit obiecte, "
                                              "click-urile pe coordonate au ramas pasi 🖱.\n"
                                              "Salveaz-o (💾) ca rutina noua; fisierul vechi ramane neschimbat.",
                                parent=self)
        self.rebuild_tree()
        self.show_routine_settings()
        self._update_title()
        self.set_status(f"Rutina \"{r.name}\" deschisa ({sum(1 for _ in r.all_nodes())} pasi).")

    def save_routine(self, ask_path: bool = False) -> bool:
        path = self.routine_path
        if ask_path or not path:
            path = filedialog.asksaveasfilename(
                parent=self, title="Salveaza rutina", initialdir=RprPaths.routines(),
                initialfile=(sanitize_name(self.routine.name) or "Rutina") + ".rpr.json",
                defaultextension=".rpr.json", filetypes=[("Rutina AutoPilot", "*.rpr.json")])
            if not path:
                return False
            if not path.lower().endswith(".rpr.json"):
                path = re.sub(r"(\.json)?$", ".rpr.json", path, flags=re.I)
        try:
            RoutineStore.save(self.routine, path)
            self.save_repository()
        except Exception as ex:  # noqa: BLE001
            messagebox.showerror("Studio RPR", f"Nu am putut salva:\n{ex}", parent=self)
            return False
        self.routine_path = path
        self.dirty = False
        self._update_title()
        self.set_status(f"Salvat: {path}")
        return True

    def load_repository(self, path: str):
        try:
            self.repo = RepositoryStore.load(path)
            self.repo_path = path
        except Exception as ex:  # noqa: BLE001
            messagebox.showerror("Studio RPR", f"Object Repository nu poate fi citit:\n{ex}", parent=self)
        self.refresh_objects()

    def save_repository(self):
        RepositoryStore.save(self.repo, self.repo_path)

    def show_examples(self):
        try:
            examples = Examples.install(self.repo)
            self.save_repository()
            self.refresh_objects()
        except Exception as ex:  # noqa: BLE001
            messagebox.showerror("Studio RPR", f"Exemplele nu au putut fi instalate:\n{ex}", parent=self)
            return
        C = self.C
        dlg = tk.Toplevel(self)
        dlg.title("Rutine exemplu")
        dlg.configure(bg=C["bg_main"])
        dlg.transient(self.winfo_toplevel())
        tk.Label(dlg, text="📚  Rutine exemplu", bg=C["bg_main"], fg=C["primary"], font=("Segoe UI", 13, "bold")).pack(
            anchor="w", padx=16, pady=(14, 2))
        tk.Label(dlg, text="Incepe cu 01 Invatare: apasa ⏭ Pas cu pas de mai multe ori si urmareste fiecare bloc.\n"
                           "Exemplele Web / SAP / Desktop au nevoie de driverele din etapele urmatoare.",
                 bg=C["bg_main"], fg=C["text_dim"], font=("Segoe UI", 9), justify="left").pack(anchor="w", padx=16)
        for ex in examples:
            card = tk.Frame(dlg, bg=C["bg_card"])
            card.pack(fill="x", padx=16, pady=4)
            tk.Label(card, text=ex["name"], bg=C["bg_card"], fg=C["text"], font=("Segoe UI", 10, "bold")).pack(
                anchor="w", padx=10, pady=(6, 0))
            tk.Label(card, text=ex["description"], bg=C["bg_card"], fg=C["text_dim"], font=("Segoe UI", 9),
                     wraplength=520, justify="left").pack(anchor="w", padx=10)
            self._btn(card, "Deschide", lambda p=ex["path"]: (dlg.destroy(), self.open_routine(p)),
                      color=C["primary"]).pack(anchor="e", padx=10, pady=6)
        self._btn(dlg, "📂 Folderul cu exemple", lambda: os.startfile(RprPaths.examples())).pack(anchor="w", padx=16, pady=10)

    def show_guide(self):
        C = self.C
        dlg = tk.Toplevel(self)
        dlg.title("Ghid Studio RPR")
        dlg.geometry("900x700")
        dlg.configure(bg=C["bg_main"])
        t = tk.Text(dlg, wrap="word", bg=C["bg_card"], fg=C["text"], font=("Segoe UI", 10), relief="flat",
                    padx=16, pady=12, spacing1=2, spacing3=2)
        sb = ttk.Scrollbar(dlg, orient="vertical", command=t.yview)
        t.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        t.pack(fill="both", expand=True)
        t.tag_configure("h1", font=("Segoe UI", 16, "bold"), foreground=C["primary"], spacing1=10)
        t.tag_configure("h2", font=("Segoe UI", 13, "bold"), foreground=C["primary"], spacing1=12)
        t.tag_configure("h3", font=("Segoe UI", 11, "bold"), foreground=C["accent"], spacing1=8)
        t.tag_configure("b", font=("Segoe UI", 10, "bold"))
        t.tag_configure("code", font=("Consolas", 10), foreground="#FFD479")
        try:
            text = open(GUIDE_FILE, encoding="utf-8").read()
        except OSError:
            text = "# Ghidul lipseste\nFisierul docs/GHID_STUDIO_RPR.md nu a fost gasit."
        for line in text.split("\n"):
            tag = None
            for prefix, tg in (("### ", "h3"), ("## ", "h2"), ("# ", "h1")):
                if line.startswith(prefix):
                    line, tag = line[len(prefix):], tg
                    break
            if tag:
                t.insert("end", line + "\n", tag)
                continue
            # **bold** si `cod`
            for part in re.split(r"(\*\*[^*]+\*\*|`[^`]+`)", line):
                if part.startswith("**"):
                    t.insert("end", part[2:-2], "b")
                elif part.startswith("`"):
                    t.insert("end", part[1:-1], "code")
                else:
                    t.insert("end", part)
            t.insert("end", "\n")
        t.configure(state="disabled")

    # =========================================================================
    # Arborele
    # =========================================================================
    def rebuild_tree(self, select: Optional[RprNode] = None):
        collapsed = {iid for iid in self._items if self.tree.exists(iid) and not self.tree.item(iid, "open")}
        self.tree.delete(*self.tree.get_children())
        self._items.clear()
        for n in self.routine.steps:
            self._add_tree_node(n, self.routine.steps, "", collapsed)
        if select is not None and self.tree.exists(select.id):
            self.tree.see(select.id)
            self.tree.selection_set(select.id)
            self.tree.focus(select.id)
        self._update_title()

    def _node_text(self, node: RprNode) -> str:
        return f"{icon_for(node)}  {node.title}{'   💬' if node.comment.strip() else ''}"

    def _add_tree_node(self, node: RprNode, owner: List[RprNode], parent: str, collapsed: set):
        iid = node.id
        self.tree.insert(parent, "end", iid=iid, text=self._node_text(node), open=iid not in collapsed,
                         tags=() if node.enabled else ("disabled",))
        self._items[iid] = ("node", node, owner)
        branches = node.branches()
        if not branches:
            return
        if len(branches) > 1:
            for name, lst in branches:
                biid = f"{iid}#{name}"
                self.tree.insert(iid, "end", iid=biid, text=f"▸ {name}", open=biid not in collapsed, tags=("branch",))
                self._items[biid] = ("branch", None, lst)
                for ch in lst:
                    self._add_tree_node(ch, lst, biid, collapsed)
        else:
            name, lst = branches[0]
            if not lst:  # ramura goala ramane selectabila
                biid = f"{iid}#{name}"
                self.tree.insert(iid, "end", iid=biid, text=f"▸ {name} (gol)", tags=("branch",))
                self._items[biid] = ("branch", None, lst)
            for ch in lst:
                self._add_tree_node(ch, lst, iid, collapsed)

    def _selected(self) -> Tuple[Optional[str], Optional[Tuple]]:
        sel = self.tree.selection()
        if not sel:
            return None, None
        return sel[0], self._items.get(sel[0])

    def _on_select(self, _e=None):
        iid, info = self._selected()
        if not info:
            return
        kind, node, _ = info
        if kind == "node":
            self.editor.show(node)
        else:
            self.editor.show_branch(self.tree.item(iid, "text"))

    def refresh_node(self, node: RprNode):
        if self.tree.exists(node.id):
            tags = [t for t in self.tree.item(node.id, "tags") if t != "disabled"]
            if not node.enabled:
                tags.append("disabled")
            self.tree.item(node.id, text=self._node_text(node), tags=tags)

    def insert_node(self, node: RprNode):
        iid, info = self._selected()
        if info and info[0] == "branch":
            target, index = info[2], len(info[2])
        elif info and info[0] == "node":
            target = info[2]
            index = next(i for i, x in enumerate(target) if x is info[1]) + 1
        else:
            target, index = self.routine.steps, len(self.routine.steps)
        target.insert(index, node)
        self.mark_dirty()
        self.rebuild_tree(node)

    def _sel_node(self) -> Tuple[Optional[RprNode], Optional[List[RprNode]]]:
        _, info = self._selected()
        if info and info[0] == "node":
            return info[1], info[2]
        return None, None

    def move(self, delta: int):
        node, owner = self._sel_node()
        if node is None:
            return
        i = next(k for k, x in enumerate(owner) if x is node)
        j = i + delta
        if 0 <= j < len(owner):
            owner[i], owner[j] = owner[j], owner[i]
            self.mark_dirty()
            self.rebuild_tree(node)

    def duplicate(self):
        node, owner = self._sel_node()
        if node is None:
            return
        twin = copy.deepcopy(node)
        _new_ids(twin)
        owner.insert(next(k for k, x in enumerate(owner) if x is node) + 1, twin)
        self.mark_dirty()
        self.rebuild_tree(twin)

    def toggle_enabled(self):
        node, _ = self._sel_node()
        if node is None:
            return
        node.enabled = not node.enabled
        self.mark_dirty()
        self.refresh_node(node)
        self.editor.show(node)

    def delete_selected(self):
        node, owner = self._sel_node()
        if node is None:
            return
        n = sum(1 for _ in flatten([node]))
        if n > 1 and not messagebox.askyesno("Studio RPR", f"Stergi pasul \"{node.title}\" si cei {n - 1} pasi din el?",
                                             parent=self):
            return
        i = next(k for k, x in enumerate(owner) if x is node)
        owner.pop(i)
        self.mark_dirty()
        nxt = owner[min(i, len(owner) - 1)] if owner else None
        self.rebuild_tree(nxt)
        if nxt is None:
            self.show_routine_settings()

    def show_routine_settings(self):
        self.tree.selection_remove(*self.tree.selection())
        self.editor.show_routine(self.routine)

    def known_variables(self, at: Optional[RprNode]) -> List[str]:
        out: List[str] = list(self.routine.variables.keys())
        for n in self.routine.all_nodes():
            if isinstance(n, ActionNode) and n.output_variable.strip():
                out.append(n.output_variable)
            elif isinstance(n, SetVariableNode) and n.name.strip():
                out.append(n.name)
            elif isinstance(n, LoopNode) and n.counter_variable.strip():
                out.append(n.counter_variable)
            elif isinstance(n, QuestionNode) and n.output_variable.strip():
                out.append(n.output_variable)
            elif isinstance(n, TryNode) and n.error_variable.strip():
                out.append(n.error_variable)
        for f in self.routine.all_nodes():
            if not isinstance(f, ForEachRowNode):
                continue
            if at is not None and at is not f and not any(x is at for x in flatten(f.body)):
                continue
            out.append(f"{f.row_variable}.#")
            out.extend(f"{f.row_variable}.{h}" for h in self.excel_info(f).headers)
        out += ["Azi", "Acum", "Acum:yyyyMMdd_HHmm", "NewLine"]
        seen, res = set(), []
        for v in out:
            if v.strip() and v.lower() not in seen:
                seen.add(v.lower())
                res.append(v)
        return res

    def excel_info(self, f: ForEachRowNode) -> ExcelInfo:
        from rpr.variables import VariableStore
        vs = VariableStore()
        for k, v in self.routine.variables.items():
            vs.set(k, v)
        return ExcelInfo.read(vs.resolve(f.file_path), vs.resolve(f.sheet), f.header_row)

    def parent_for_each(self, node: RprNode) -> Optional[ForEachRowNode]:
        for f in self.routine.all_nodes():
            if isinstance(f, ForEachRowNode) and any(x is node for x in flatten(f.body)):
                return f
        return None

    # =========================================================================
    # Object Repository
    # =========================================================================
    def refresh_objects(self):
        if not hasattr(self, "objects"):
            return
        flt = self._obj_filter.get().strip().lower()
        self.objects.delete(*self.objects.get_children())
        for o in sorted(self.repo.objects, key=lambda x: x.name.lower()):
            if flt and flt not in o.name.lower():
                continue
            self.objects.insert("", "end", iid="obj:" + o.name, text=o.name, values=(str(o.technology),))

    def _sel_object(self) -> Optional[UiObject]:
        sel = self.objects.selection()
        return self.repo.find(sel[0][4:]) if sel else None

    def new_object(self):
        obj = UiObject(name=self.repo.make_unique_name("Obiect"), locators=[Locator(LocatorKind.Css, "")])
        if ObjectDialog(self, obj, is_new=True).result:
            self.repo.add(obj)
            self.save_repository()
            self.refresh_objects()

    def edit_object(self):
        obj = self._sel_object()
        if obj is None:
            return
        old = obj.name
        if ObjectDialog(self, obj).result:
            if obj.name != old:
                self._rename_references(old, obj.name)
            self.save_repository()
            self.refresh_objects()
            self.rebuild_tree()

    def _rename_references(self, old: str, new: str):
        def fix_cond(c: Condition):
            if c.target.lower() == old.lower():
                c.target = new
            for ch in c.children:
                fix_cond(ch)
        for n in self.routine.all_nodes():
            if isinstance(n, ActionNode) and n.target.lower() == old.lower():
                n.target = new
            cond = getattr(n, "condition", None)
            if isinstance(cond, Condition):
                fix_cond(cond)
        self.mark_dirty()

    def delete_object(self):
        obj = self._sel_object()
        if obj is None:
            return
        used = sum(1 for n in self.routine.referenced_objects() if n.lower() == obj.name.lower())
        msg = f"Stergi obiectul \"{obj.name}\" din Object Repository?"
        if used:
            msg += f"\n\nAtentie: rutina curenta il foloseste in {used} pasi."
        if messagebox.askyesno("Studio RPR", msg, parent=self):
            self.repo.remove(obj)
            self.save_repository()
            self.refresh_objects()

    def object_to_step(self):
        obj = self._sel_object()
        if obj is None:
            return
        self.insert_node(ActionNode(action=RprAction.Click, target=obj.name, technology=obj.technology))

    def spy(self, technology: UiTechnology):
        messagebox.showinfo("Spy", f"Spy pentru {technology} (marcarea obiectelor cu mouse-ul) vine cu driverul "
                                   "acestei tehnologii, in etapele urmatoare.\n\nPana atunci poti adauga obiecte manual: "
                                   "tab-ul 🎯 Obiecte → ＋ Nou.", parent=self)

    # =========================================================================
    # Rulare
    # =========================================================================
    def post(self, kind: str, payload: Any = None):
        self._queue.put((kind, payload))

    def call_ui(self, fn: Callable[[], Any]) -> Any:
        """Din firul motorului: executa fn pe firul Tk si asteapta rezultatul."""
        ev, box = threading.Event(), {}
        self._queue.put(("call", (fn, ev, box)))
        ev.wait()
        return box.get("r")

    def paused_dialog(self, title, text, buttons, detail) -> str:
        if self._run_frame:
            self._run_frame.show("pause")
        if self._run_control:
            self._run_control.set_status("⚠ " + text.lstrip("⚠ "))
        ans = choice_dialog(self, title, text, buttons, detail, C=self.C)
        if self._run_frame and self.busy:
            self._run_frame.show("run")
        return ans

    def _poll(self):
        self.after(50, self._poll)  # reprogramat primul: dialogurile modale nu opresc coada
        for _ in range(200):
            try:
                kind, p = self._queue.get_nowait()
            except queue.Empty:
                return
            if kind == "log":
                self._add_log(p)
            elif kind == "started":
                self._mark_running(p)
            elif kind == "finished":
                node, ok = p
                if self.tree.exists(node.id):
                    tags = [t for t in self.tree.item(node.id, "tags") if t not in ("running", "ok", "error")]
                    self.tree.item(node.id, tags=tags + ["ok" if ok else "error"])
            elif kind == "status":
                self.set_status(p)
            elif kind == "call":
                fn, ev, box = p
                try:
                    box["r"] = fn()
                finally:
                    ev.set()
            elif kind == "done":
                self._run_finished(*p)

    def _add_log(self, e: RunLogEntry):
        self._log_entries.append(e)
        iid = self.log.insert("", "end", values=(e.time.strftime("%H:%M:%S"), str(e.level),
                                                 e.excel_row or "", e.node_title[:60], e.message.replace("\n", " ")),
                              tags=(str(e.level),))
        kids = self.log.get_children()
        if len(kids) > 3000:
            self.log.delete(kids[0])
        self.log.see(iid)

    def _mark_running(self, node: RprNode):
        if self._running_iid and self.tree.exists(self._running_iid):
            tags = [t for t in self.tree.item(self._running_iid, "tags") if t != "running"]
            self.tree.item(self._running_iid, tags=tags)
        if self.tree.exists(node.id):
            tags = [t for t in self.tree.item(node.id, "tags") if t not in ("ok", "error")]
            self.tree.item(node.id, tags=tags + ["running"])
            self.tree.see(node.id)
            self._running_iid = node.id
        if self._run_control:
            self._run_control.set_status(node.title)
        self.set_status("▶ " + node.title)

    def clear_log(self):
        self.log.delete(*self.log.get_children())
        self._log_entries.clear()

    def export_log(self):
        if not self._log_entries:
            messagebox.showinfo("Studio RPR", "Logul e gol.", parent=self)
            return
        path = filedialog.asksaveasfilename(parent=self, title="Export log", initialdir=RprPaths.output(),
                                            initialfile=f"Log_{sanitize_name(self.routine.name)}.xlsx",
                                            defaultextension=".xlsx", filetypes=[("Excel", "*.xlsx")])
        if path:
            try:
                RunLogExporter.export_xlsx(self._log_entries, path)
                self.set_status(f"Log exportat: {path}")
            except Exception as ex:  # noqa: BLE001
                messagebox.showerror("Studio RPR", str(ex), parent=self)

    def run(self, step_mode: bool = False):
        if self.busy:
            if step_mode:
                self.step_once()
            return
        if not self.routine.steps:
            messagebox.showinfo("Rutina goala", "Rutina nu are pasi. Adauga pasi din stanga sau deschide un exemplu "
                                                "(📚 Exemple).", parent=self)
            return
        self.busy = True
        for iid in self._items:
            if self.tree.exists(iid):
                self.tree.item(iid, tags=[t for t in self.tree.item(iid, "tags") if t not in ("running", "ok", "error")])
        self.clear_log()
        self.engine = RprEngine(self.repo, self.drivers, StudioRunHost(self), RprPaths.output())
        self.engine.step_mode = step_mode
        self.engine.guard = StudioGuard() if safety else None
        self._run_control = RunControlWindow(self)
        if self._run_frame:
            self._run_frame.show("pause" if step_mode else "run")
        self.set_status("PAS CU PAS: apasa ⏭ Pas pentru fiecare pas." if step_mode else "Rulez...")
        engine, routine = self.engine, self.routine
        dnd = bool(routine.settings.do_not_disturb and safety)

        def work():
            result = None
            try:
                if dnd:
                    self.post("status", "🌙 Activez \"Nu deranja\" (cateva secunde)...")
                    safety.DoNotDisturb.enable()
                    self.post("status", safety.DoNotDisturb.last_message)
                result = engine.run(routine)
            except Exception as ex:  # noqa: BLE001
                from rpr.host import RunResult
                result = RunResult(success=False, message=str(ex))
            finally:
                if dnd:
                    threading.Thread(target=safety.DoNotDisturb.restore, daemon=True).start()
                self.post("done", (result,))

        threading.Thread(target=work, daemon=True, name="StudioRun").start()

    def _run_finished(self, result):
        self.busy = False
        if self._run_control:
            self._run_control.destroy()
            self._run_control = None
        if self._run_frame:
            self._run_frame.hide()
        if self._running_iid and self.tree.exists(self._running_iid):
            self.tree.item(self._running_iid, tags=[t for t in self.tree.item(self._running_iid, "tags") if t != "running"])
        self._running_iid = None
        self.vars.delete(*self.vars.get_children())
        for k, v in sorted((self.engine.last_variables if self.engine else {}).items(), key=lambda kv: kv[0].lower()):
            self.vars.insert("", "end", values=(k, v))
        mark = "✔ " if result.success else "⏹ " if result.cancelled else "✖ "
        self.set_status(mark + result.message)
        self.winfo_toplevel().deiconify()
        if not result.success and not result.cancelled:
            choice_dialog(self, "Rutina oprita", result.message, ["OK"],
                          "Detaliile sunt in Log (randurile rosii). Capturile erorilor: " +
                          os.path.join(RprPaths.output(), "erori"), C=self.C)

    def toggle_pause(self):
        if not self.busy or self.engine is None:
            return
        if self.engine.is_paused:
            self.engine.step_mode = False
            self.engine.resume()
        else:
            self.engine.pause()
        paused = self.engine.is_paused
        if self._run_control:
            self._run_control.set_paused(paused)
        if self._run_frame:
            self._run_frame.show("pause" if paused else "run")
        self.set_status("PAUZA — Reluare sau Pas cu pas." if paused else "Rulare reluata.")

    def step_once(self):
        if self.busy and self.engine:
            self.engine.step_mode = True
            self.engine.step_once()

    def stop(self):
        if self.engine:
            self.engine.stop()

    def test_node(self, node: RprNode):
        if self.busy:
            return
        self.busy = True
        engine = RprEngine(self.repo, self.drivers, StudioRunHost(self), RprPaths.output())
        if self.engine:
            engine.last_variables = dict(self.engine.last_variables)
        self.engine = engine
        routine = self.routine

        def work():
            r = engine.run_single(routine, node)
            self.post("done", (r,))
        self.set_status(f"Testez pasul \"{node.title}\"...")
        threading.Thread(target=work, daemon=True).start()


# ==============================================================================
# 5. EDITORUL DE PROPRIETATI (fara cod)
# ==============================================================================
class PropertyEditor:
    def __init__(self, panel: StudioPanel):
        self.p = panel
        self.C = panel.C
        self._target: Any = None
        self._host: tk.Frame = panel.props.inner

    # ── intrare ──
    def show(self, node: RprNode):
        self._target = node
        self._rebuild()

    def show_routine(self, routine: Routine):
        self._target = routine
        self._rebuild()

    def show_branch(self, text: str):
        self._target = None
        self.p.props.clear()
        self._host = self.p.props.inner
        self._title(text)
        self._hint("Click pe un bloc din stanga ca sa adaugi un pas IN aceasta ramura.")

    def _rebuild(self):
        self.p.props.clear()
        self._host = self.p.props.inner
        t = self._target
        if isinstance(t, RprNode):
            self._build_node(t)
        elif isinstance(t, Routine):
            self._build_routine(t)

    def _later_rebuild(self):
        self.p.after_idle(self._rebuild)

    def _changed(self, node: Optional[RprNode], structural=False):
        self.p.mark_dirty()
        if node is not None:
            self.p.refresh_node(node)
        else:
            self.p._update_title()
        if structural:
            self._later_rebuild()

    # ── elemente vizuale ──
    def _title(self, text):
        tk.Label(self._host, text=text, bg=self.C["bg_card"], fg=self.C["primary"], font=("Segoe UI", 13, "bold"),
                 anchor="w").pack(fill="x", padx=10, pady=(10, 4))

    def _caption(self, text, host=None):
        tk.Label(host or self._host, text=text, bg=(host or self._host)["bg"], fg=self.C["text_dim"],
                 font=("Segoe UI", 9, "bold"), anchor="w", justify="left", wraplength=330).pack(
            fill="x", padx=10, pady=(8, 1))

    def _hint(self, text, host=None, color=None):
        tk.Label(host or self._host, text=text, bg=(host or self._host)["bg"], fg=color or self.C["text_dim"],
                 font=("Segoe UI", 8), anchor="w", justify="left", wraplength=330).pack(fill="x", padx=10, pady=(2, 2))

    def _card(self, host=None, title="") -> tk.Frame:
        f = tk.Frame(host or self._host, bg=self.C["bg_main"], highlightthickness=1,
                     highlightbackground=self.C["border"])
        f.pack(fill="x", padx=8, pady=6)
        if title:
            tk.Label(f, text=title, bg=self.C["bg_main"], fg=self.C["accent"], font=("Segoe UI", 10, "bold"),
                     anchor="w").pack(fill="x", padx=8, pady=(6, 0))
        return f

    def _entry_style(self):
        return dict(bg=self.C["bg_input"], fg=self.C["text"], insertbackground=self.C["text"], relief="flat",
                    font=("Segoe UI", 10))

    # ── campuri ──
    def text(self, node, label, get, set_, vars_=True, multiline=False, host=None):
        host = host or self._host
        self._caption(label, host)
        row = tk.Frame(host, bg=host["bg"])
        row.pack(fill="x", padx=10)
        if multiline:
            w = tk.Text(row, height=3, wrap="word", **self._entry_style())
            w.insert("1.0", get() or "")

            def on_mod(_e=None):
                if w.edit_modified():
                    set_(w.get("1.0", "end-1c"))
                    self._changed(node)
                    w.edit_modified(False)
            w.edit_modified(False)
            w.bind("<<Modified>>", on_mod)
        else:
            var = tk.StringVar(value=get() or "")
            w = tk.Entry(row, textvariable=var, **self._entry_style())
            var.trace_add("write", lambda *a: (set_(var.get()), self._changed(node)))
        w.pack(side="left", fill="x", expand=True, ipady=3)
        if vars_:
            self._var_inserter(row, w, node if isinstance(node, RprNode) else None).pack(side="left", padx=(4, 0))
        return w

    def _var_inserter(self, parent, widget, node):
        mb = tk.Menubutton(parent, text="＋{x}", bg=self.C["bg_input"], fg=self.C["accent"], relief="flat",
                           font=("Segoe UI", 9, "bold"), cursor="hand2", activebackground=self.C["primary"])
        menu = tk.Menu(mb, tearoff=0, bg=self.C["bg_card"], fg=self.C["text"], activebackground=self.C["primary"])
        mb.configure(menu=menu)

        def fill():
            menu.delete(0, "end")
            names = self.p.known_variables(node)
            if not names:
                menu.add_command(label="(nicio variabila inca)", state="disabled")
            for v in names:
                def ins(v=v):
                    token = "{" + v + "}"
                    if isinstance(widget, tk.Text):
                        widget.insert("insert", token)
                    else:
                        widget.insert(widget.index("insert"), token)
                    widget.focus_set()
                menu.add_command(label="{" + v + "}", command=ins)
        menu.configure(postcommand=fill)
        ToolTip(mb, "Insereaza o variabila la pozitia cursorului")
        return mb

    def number(self, node, label, get, set_, host=None, is_float=False, structural=False):
        host = host or self._host
        self._caption(label, host)
        var = tk.StringVar(value=(f"{get():g}" if is_float else str(get())))
        e = tk.Entry(host, textvariable=var, width=12, **self._entry_style())
        e.pack(anchor="w", padx=10, ipady=3)

        def on_write(*_a):
            s = var.get().strip().replace(",", ".")
            try:
                v = float(s) if is_float else int(s)
            except ValueError:
                e.configure(bg="#5A2A2A")
                return
            e.configure(bg=self.C["bg_input"])
            set_(v)
            self._changed(node, structural)
        var.trace_add("write", on_write)
        return e

    def check(self, node, label, get, set_, host=None, structural=False):
        host = host or self._host
        var = tk.BooleanVar(value=bool(get()))
        cb = tk.Checkbutton(host, text=label, variable=var, bg=host["bg"], fg=self.C["text"], anchor="w",
                            justify="left", wraplength=320, selectcolor=self.C["bg_input"],
                            activebackground=host["bg"], activeforeground=self.C["text"], font=("Segoe UI", 9),
                            command=lambda: (set_(var.get()), self._changed(node, structural)))
        cb.pack(fill="x", padx=8, pady=2)
        return cb

    def combo(self, node, label, options, get, set_, host=None, structural=False):
        host = host or self._host
        if label:
            self._caption(label, host)
        labels = [l for _, l in options]
        current = get()
        idx = next((i for i, (v, _) in enumerate(options) if v == current), 0)
        cb = ttk.Combobox(host, values=labels, state="readonly", style="Studio.TCombobox", font=("Segoe UI", 9))
        cb.current(idx)
        cb.pack(fill="x", padx=10, pady=1)

        def on_sel(_e=None):
            set_(options[cb.current()][0])
            self._changed(node, structural)
        cb.bind("<<ComboboxSelected>>", on_sel)
        return cb

    def editable_choice(self, node, label, values, get, set_, host=None, structural=False):
        host = host or self._host
        self._caption(label, host)
        var = tk.StringVar(value=get() or "")
        cb = ttk.Combobox(host, textvariable=var, values=list(values), style="Studio.TCombobox", font=("Segoe UI", 9))
        cb.pack(fill="x", padx=10, pady=1)
        var.trace_add("write", lambda *a: (set_(var.get()), self._changed(node)))
        if structural:
            cb.bind("<<ComboboxSelected>>", lambda e: self._later_rebuild())
            cb.bind("<FocusOut>", lambda e: self._later_rebuild())
        return cb

    def object_picker(self, node, label, get, set_, technologies=None, host=None):
        names = [o.name for o in sorted(self.p.repo.objects, key=lambda x: x.name.lower())
                 if not technologies or o.technology in technologies]
        cb = self.editable_choice(node, label, names, get, set_, host=host, structural=True)
        if get() and self.p.repo.find(get()) is None:
            self._hint(f"⚠ Obiectul [{get()}] nu exista in Object Repository.", host, self.C["warning"])
        return cb

    def file_picker(self, node, label, get, set_, structural=True):
        self._caption(label)
        row = tk.Frame(self._host, bg=self._host["bg"])
        row.pack(fill="x", padx=10)
        var = tk.StringVar(value=get() or "")
        tk.Entry(row, textvariable=var, **self._entry_style()).pack(side="left", fill="x", expand=True, ipady=3)
        var.trace_add("write", lambda *a: (set_(var.get()), self._changed(node)))

        def browse():
            p = filedialog.askopenfilename(parent=self.p, title=label, filetypes=[("Excel", "*.xlsx *.xlsm")])
            if p:
                var.set(os.path.normpath(p))
                if structural:
                    self._later_rebuild()
        self.p._btn(row, "📂", browse, tip="Alege fisierul").pack(side="left", padx=(4, 0))

    def button_row(self, buttons):
        row = tk.Frame(self._host, bg=self._host["bg"])
        row.pack(fill="x", padx=10, pady=(10, 4))
        for text, cmd, color, tip in buttons:
            self.p._btn(row, text, cmd, color=color, tip=tip).pack(side="left", padx=2)

    # ── pas ──
    def _build_node(self, node: RprNode):
        self._title(f"{icon_for(node)}  {node.KIND_LABEL}")
        if isinstance(node, ActionNode):
            self._build_action(node)
        elif isinstance(node, WaitNode):
            self.combo(node, "Cat asteapta", WAIT_MODES, lambda: node.mode, lambda v: setattr(node, "mode", v), structural=True)
            if node.mode == WaitMode.Seconds:
                self.number(node, "Secunde", lambda: node.seconds, lambda v: setattr(node, "seconds", v), is_float=True)
            else:
                self.condition(node.condition, node)
                self.number(node, "Timp maxim (ms)", lambda: node.timeout_ms, lambda v: setattr(node, "timeout_ms", v))
                self.check(node, "Daca nu se indeplineste in timp: eroare (debifat = continua)",
                           lambda: node.fail_on_timeout, lambda v: setattr(node, "fail_on_timeout", v))
        elif isinstance(node, SetVariableNode):
            self.text(node, "Numele variabilei", lambda: node.name, lambda v: setattr(node, "name", v.strip("{} ")), vars_=False)
            self.combo(node, "Operatie", VARIABLE_OPS, lambda: node.operation, lambda v: setattr(node, "operation", v), structural=True)
            op = node.operation
            if op == VariableOperation.Replace:
                self.text(node, "Cauta textul", lambda: node.find, lambda v: setattr(node, "find", v))
            if op in (VariableOperation.Set, VariableOperation.Append, VariableOperation.Replace,
                      VariableOperation.Increment, VariableOperation.Decrement):
                self.text(node, "Inlocuieste cu" if op == VariableOperation.Replace else "Valoare",
                          lambda: node.value, lambda v: setattr(node, "value", v))
        elif isinstance(node, IfNode):
            self._hint("Pasii din ramura \"Atunci\" ruleaza cand conditia e adevarata, cei din \"Altfel\" cand e falsa.")
            self.condition(node.condition, node)
        elif isinstance(node, LoopNode):
            self.combo(node, "Cum repeta", LOOP_MODES, lambda: node.mode, lambda v: setattr(node, "mode", v), structural=True)
            if node.mode == LoopMode.Times:
                self.text(node, "De cate ori", lambda: node.count, lambda v: setattr(node, "count", v))
            else:
                self.condition(node.condition, node)
                self.number(node, "Maxim repetari (protectie)", lambda: node.max_iterations,
                            lambda v: setattr(node, "max_iterations", v))
            self.text(node, "Variabila cu numarul repetarii", lambda: node.counter_variable,
                      lambda v: setattr(node, "counter_variable", v), vars_=False)
            self._hint(f"In pasii din bucla folosesti {{{node.counter_variable}}} = 1, 2, 3...")
        elif isinstance(node, ForEachRowNode):
            self._build_for_each(node)
        elif isinstance(node, WriteExcelNode):
            loop = self.p.parent_for_each(node)
            if loop is None:
                self._hint("Pune acest pas IN INTERIORUL unui bloc \"Pentru fiecare rand Excel\".", color=self.C["warning"])
            headers = self.p.excel_info(loop).headers if loop else []
            self.editable_choice(node, "Coloana (titlu sau litera; coloana noua se creeaza automat)", headers,
                                 lambda: node.column, lambda v: setattr(node, "column", v))
            self.text(node, "Valoare", lambda: node.value, lambda v: setattr(node, "value", v))
            self.combo(node, "Culoare celula", CELL_COLORS, lambda: node.color, lambda v: setattr(node, "color", v))
        elif isinstance(node, QuestionNode):
            self.text(node, "Intrebarea", lambda: node.text, lambda v: setattr(node, "text", v), multiline=True)
            self.text(node, "Butoane (separate prin virgula)", lambda: node.buttons, lambda v: setattr(node, "buttons", v), vars_=False)
            self.text(node, "Raspunsul se salveaza in variabila", lambda: node.output_variable,
                      lambda v: setattr(node, "output_variable", v), vars_=False)
            self.text(node, "Butonul care OPRESTE rutina", lambda: node.stop_button, lambda v: setattr(node, "stop_button", v), vars_=False)
            self.text(node, "Butonul care SARE randul Excel curent", lambda: node.skip_button,
                      lambda v: setattr(node, "skip_button", v), vars_=False)
        elif isinstance(node, TryNode):
            self._hint("Daca un pas din \"Incearca\" esueaza, rutina NU se opreste: ruleaza ramura \"La eroare\". "
                       "Mesajul erorii e in variabila de mai jos.")
            self.text(node, "Variabila cu mesajul erorii", lambda: node.error_variable,
                      lambda v: setattr(node, "error_variable", v), vars_=False)
        elif isinstance(node, GroupNode):
            self._hint("Grupul doar organizeaza pasii (il poti dezactiva cu totul sau redenumi).")
        elif isinstance(node, LogNode):
            self.text(node, "Mesaj", lambda: node.message, lambda v: setattr(node, "message", v), multiline=True)
            self.combo(node, "Nivel", LOG_LEVELS, lambda: node.level, lambda v: setattr(node, "level", v))
        elif isinstance(node, BreakNode):
            self.check(node, "Doar treci la urmatoarea repetare / urmatorul rand (nu iesi din bucla)",
                       lambda: node.next_iteration, lambda v: setattr(node, "next_iteration", v))
        elif isinstance(node, StopNode):
            self.text(node, "Mesaj", lambda: node.message, lambda v: setattr(node, "message", v))
            self.check(node, "Opreste ca EROARE (randul Excel curent va fi marcat cu rosu)",
                       lambda: node.as_error, lambda v: setattr(node, "as_error", v))
        elif isinstance(node, LegacyStepNode):
            self._hint("Pas pe coordonate de ecran (din recorder). Functioneaza, dar e fragil: daca fereastra se muta "
                       "sau rezolutia se schimba, click-ul nimereste altundeva. Recomandat: un pas \"Actiune\" pe un obiect.")
            s = node.step
            self.text(node, "Descriere", lambda: s.get("description", ""), lambda v: s.__setitem__("description", v), vars_=False)
            self.number(node, "X", lambda: int(s.get("x", 0) or 0), lambda v: s.__setitem__("x", v))
            self.number(node, "Y", lambda: int(s.get("y", 0) or 0), lambda v: s.__setitem__("y", v))
            if s.get("key_combo") or s.get("step_type") == "KEY":
                self.text(node, "Taste", lambda: s.get("key_combo", ""), lambda v: s.__setitem__("key_combo", v), vars_=False)
            if s.get("text_input") or s.get("step_type") == "TYPE":
                self.text(node, "Text", lambda: s.get("text_input", ""), lambda v: s.__setitem__("text_input", v), vars_=False)

        # ── comun ──
        card = self._card(title="General")
        self.text(node, "Titlu personalizat (gol = automat)", lambda: node.label, lambda v: setattr(node, "label", v),
                  vars_=False, host=card)
        self.check(node, "Pas activ (debifat = omis la rulare)", lambda: node.enabled,
                   lambda v: setattr(node, "enabled", v), host=card)
        self.number(node, "Asteapta inainte (ms)", lambda: node.delay_before_ms, lambda v: setattr(node, "delay_before_ms", v), host=card)
        self.number(node, "Asteapta dupa (ms)", lambda: node.delay_after_ms, lambda v: setattr(node, "delay_after_ms", v), host=card)
        self.combo(node, "La eroare", ERROR_POLICIES, lambda: node.on_error, lambda v: setattr(node, "on_error", v), host=card)
        self.text(node, "Comentariu / notita", lambda: node.comment, lambda v: setattr(node, "comment", v),
                  vars_=False, multiline=True, host=card)
        tk.Frame(card, bg=card["bg"], height=6).pack()

    def _build_action(self, a: ActionNode):
        info = action_info(a.action)
        # 1. actiunea (grupata pe tehnologii)
        options = []
        for ai in ACTIONS:
            grp = "Pe obiect" if len(ai.technologies) == 4 else "SAP" if UiTechnology.Sap in ai.technologies else \
                "Desktop" if UiTechnology.Desktop in ai.technologies else "Browser"
            options.append((ai.action, f"{grp}  ·  {ai.label}"))

        def set_action(v):
            a.action = v
            ni = action_info(v)
            if a.technology not in ni.technologies:
                a.technology = ni.technologies[0]
            if not ni.needs_target and not ni.target_optional:
                a.target = ""
        self.combo(a, "Ce face pasul", options, lambda: a.action, set_action, structural=True)

        # 2. obiectul
        if info.needs_target or info.target_optional:
            lbl = "Obiect (optional — gol = tasta se trimite ferestrei active)" if info.target_optional else "Pe ce obiect"
            self.object_picker(a, lbl, lambda: a.target, lambda v: setattr(a, "target", v), info.technologies)

        # 3. tehnologia (doar fara obiect)
        if not a.target.strip() and len(info.technologies) > 1 and not info.needs_target:
            opts = [(v, l) for v, l in TECHNOLOGIES if v in info.technologies]
            self.combo(a, "Tehnologie", opts, lambda: a.technology, lambda v: setattr(a, "technology", v))

        # 4. valoarea
        if info.value_label:
            self.text(a, info.value_label, lambda: a.value, lambda v: setattr(a, "value", v),
                      multiline=a.action in (RprAction.TypeText, RprAction.AppendText))
            hint = {
                RprAction.TypeText: "Poti folosi variabile, ex: {Rand.IBase} sau {Azi}.",
                RprAction.AppendText: "Poti folosi variabile, ex: {Rand.IBase} sau {Azi}.",
                RprAction.PressKey: "Exemple: Enter, Tab, Escape, F5, Ctrl+A, Ctrl+Shift+S, Alt+F4.",
                RprAction.SapSendKey: "Exemple: Enter, F3 (Inapoi), F8 (Executa), Ctrl+S (Salvare), Shift+F4.",
                RprAction.SapTransaction: "Ex: VA03. Cu /n in fata (/nVA03) se inchide tranzactia curenta.",
                RprAction.SapGridReadCell: "Ex: 0|MATNR (rand 0, coloana tehnica MATNR) sau 0|2 pentru tabele clasice.",
                RprAction.SwitchTab: "0 = primul tab, -1 = ultimul tab, sau un text din titlu / adresa.",
                RprAction.AttachWindow: "Ex: proces:notepad.exe  sau  ^Calculator$ (titlu, expresie regulata).",
                RprAction.LaunchApp: "Ex: notepad.exe  sau  \"C:\\Program Files\\App\\app.exe\" /param",
                RprAction.SapConnect: "Gol = prima sesiune. \"1\" = a doua sesiune. \"1/0\" = conexiunea 2, sesiunea 1.",
            }.get(a.action)
            if hint:
                self._hint(hint)

        # 5. rezultat + valoarea asteptata
        if info.produces_output:
            self.text(a, "Salveaza rezultatul in variabila", lambda: a.output_variable,
                      lambda v: setattr(a, "output_variable", v), vars_=False)
            self._hint("Ex: Status. Apoi folosesti {Status} in pasii urmatori, in conditii sau in Excel.")
            self.text(a, "Valoarea asteptata (optional)", lambda: a.expected_value, lambda v: setattr(a, "expected_value", v))
            self._hint("Daca valoarea citita e diferita, rutina se opreste si te intreaba. * = orice text. "
                       "Ex: S:*  (orice mesaj de succes SAP),  {Rand.Status},  Salvat*")

        # 6. optiuni
        if info.needs_target or a.target.strip():
            self.number(a, "Asteapta obiectul maxim (ms)", lambda: a.timeout_ms, lambda v: setattr(a, "timeout_ms", v))
            self.check(a, "Mod direct (fara miscarea vizibila a mouse-ului, unde e posibil)",
                       lambda: a.direct_mode, lambda v: setattr(a, "direct_mode", v))
        self.button_row([("▶ Testeaza pasul", lambda: self.p.test_node(a), self.C["success"],
                          "Executa doar acest pas acum (cu variabilele ultimei rulari)")])

    def _build_for_each(self, f: ForEachRowNode):
        self._hint("Pasii din interior ruleaza o data pentru fiecare rand. Valorile randului sunt variabile: "
                   f"{{{f.row_variable}.TitluColoana}}, {{{f.row_variable}.A}} (dupa litera), "
                   f"{{{f.row_variable}.#}} (numarul randului).")
        self.file_picker(f, "Fisier Excel", lambda: f.file_path, lambda v: setattr(f, "file_path", v))
        info = self.p.excel_info(f)
        if info.sheets:
            self.editable_choice(f, "Foaia (gol = prima)", info.sheets, lambda: f.sheet, lambda v: setattr(f, "sheet", v),
                                 structural=True)
        else:
            self.text(f, "Foaia (gol = prima)", lambda: f.sheet, lambda v: setattr(f, "sheet", v), vars_=False)
        self.number(f, "Randul cu titlurile coloanelor (0 = fara titluri)", lambda: f.header_row,
                    lambda v: setattr(f, "header_row", v))
        self.number(f, "Primul rand cu date (0 = imediat sub titluri)", lambda: f.start_row, lambda v: setattr(f, "start_row", v))
        self.number(f, "Ultimul rand (0 = pana la primul rand gol)", lambda: f.end_row, lambda v: setattr(f, "end_row", v))
        self.editable_choice(f, "Coloana cheie (rand gol aici = sfarsitul listei)", info.headers,
                             lambda: f.key_column, lambda v: setattr(f, "key_column", v))
        self.text(f, "Prefixul variabilelor de rand", lambda: f.row_variable, lambda v: setattr(f, "row_variable", v.strip()),
                  vars_=False)
        self.editable_choice(f, "Coloana de status (gol = nu scrie status)", info.headers + ["Status"],
                             lambda: f.status_column, lambda v: setattr(f, "status_column", v))
        self.check(f, "Coloreaza randurile (verde OK, rosu eroare)", lambda: f.color_rows, lambda v: setattr(f, "color_rows", v))
        self.check(f, "Salveaza Excel dupa fiecare rand (sigur la intreruperi)", lambda: f.save_after_each_row,
                   lambda v: setattr(f, "save_after_each_row", v))
        self.check(f, "La reluare, sari randurile deja marcate OK", lambda: f.skip_completed_rows,
                   lambda v: setattr(f, "skip_completed_rows", v))
        if info.error:
            self._hint(info.error, color=self.C["warning"])
        elif info.headers:
            self._hint(f"Coloane gasite ({info.data_rows} randuri cu date): " +
                       ", ".join("{" + f.row_variable + "." + h + "}" for h in info.headers))

    # ── conditie (recursiv pentru SI / SAU) ──
    def condition(self, c: Condition, node: RprNode, host=None, depth=0):
        card = self._card(host, "Conditia" if depth == 0 else "Conditie")

        def set_kind(v):
            c.kind = v
            if v in (ConditionKind.AllOf, ConditionKind.AnyOf) and not c.children:
                c.children.append(Condition(kind=ConditionKind.ElementExists))
        self.combo(node, "", CONDITION_KINDS, lambda: c.kind, set_kind, host=card, structural=True)

        if c.kind in (ConditionKind.AllOf, ConditionKind.AnyOf):
            for child in list(c.children):
                sub = tk.Frame(card, bg=card["bg"])
                sub.pack(fill="x", padx=(14, 0))
                self.condition(child, node, sub, depth + 1)
                self.p._btn(sub, "✕ Scoate conditia",
                            lambda ch=child: (c.children.remove(ch), self._changed(node, True))).pack(anchor="w", padx=10)
            self.p._btn(card, "＋ Adauga conditie",
                        lambda: (c.children.append(Condition()), self._changed(node, True))).pack(anchor="w", padx=10, pady=4)
        elif c.kind == ConditionKind.Compare:
            self.text(node, "Valoarea (stanga)", lambda: c.left, lambda v: setattr(c, "left", v), host=card)
            self.combo(node, "", OPERATORS, lambda: c.operator, lambda v: setattr(c, "operator", v), host=card, structural=True)
            if c.operator not in (CompareOperator.IsEmpty, CompareOperator.IsNotEmpty):
                self.text(node, "Comparata cu (dreapta)", lambda: c.right, lambda v: setattr(c, "right", v), host=card)
            self.check(node, "Ignora literele mari/mici", lambda: c.ignore_case, lambda v: setattr(c, "ignore_case", v), host=card)
        else:
            self.object_picker(node, "Obiectul", lambda: c.target, lambda v: setattr(c, "target", v), host=card)
            if c.kind == ConditionKind.ElementText:
                self.combo(node, "", OPERATORS, lambda: c.operator, lambda v: setattr(c, "operator", v), host=card, structural=True)
                if c.operator not in (CompareOperator.IsEmpty, CompareOperator.IsNotEmpty):
                    self.text(node, "Valoarea", lambda: c.right, lambda v: setattr(c, "right", v), host=card)
                self.check(node, "Ignora literele mari/mici", lambda: c.ignore_case, lambda v: setattr(c, "ignore_case", v), host=card)
            self.number(node, "Asteapta sa dispara maxim (ms)" if c.kind == ConditionKind.ElementNotExists
                        else "Asteapta obiectul maxim (ms, 0 = verificare imediata)",
                        lambda: c.timeout_ms, lambda v: setattr(c, "timeout_ms", v), host=card)
        self.check(node, "NU (inverseaza rezultatul)", lambda: c.negate, lambda v: setattr(c, "negate", v), host=card)
        tk.Frame(card, bg=card["bg"], height=4).pack()

    # ── rutina (nimic selectat) ──
    def _build_routine(self, r: Routine):
        self._title("⚙  Setarile rutinei")
        self.text(None, "Nume", lambda: r.name, lambda v: setattr(r, "name", v), vars_=False)
        self.text(None, "Descriere", lambda: r.description, lambda v: setattr(r, "description", v), vars_=False, multiline=True)
        s = r.settings
        self.combo(None, "La eroare (implicit pentru toti pasii)", [o for o in ERROR_POLICIES if o[0] != ErrorPolicy.Inherit],
                   lambda: s.default_error_policy, lambda v: setattr(s, "default_error_policy", v))
        self.check(None, "Marcheaza obiectul pe ecran inainte de fiecare actiune", lambda: s.highlight_before_action,
                   lambda v: setattr(s, "highlight_before_action", v))
        self.number(None, "Durata marcarii (ms)", lambda: s.highlight_ms, lambda v: setattr(s, "highlight_ms", v))
        self.number(None, "Timeout implicit pentru obiecte (ms)", lambda: s.default_timeout_ms, lambda v: setattr(s, "default_timeout_ms", v))
        self.number(None, "Pauza intre pasi (ms) — util la verificare", lambda: s.step_delay_ms, lambda v: setattr(s, "step_delay_ms", v))
        self.number(None, "Reincercari automate la eroare", lambda: s.auto_retries, lambda v: setattr(s, "auto_retries", v))
        self.check(None, "Captura de ecran automata la eroare", lambda: s.screenshot_on_error, lambda v: setattr(s, "screenshot_on_error", v))

        card = self._card(title="Siguranta la rulare")
        self.check(None, "🌙 Nu deranja (fara notificari Windows) cat timp ruleaza", lambda: s.do_not_disturb,
                   lambda v: setattr(s, "do_not_disturb", v), host=card)
        self.check(None, "🛡 Sistem de preventie (pauza + intrebare cand ceva difera)", lambda: s.guard_enabled,
                   lambda v: setattr(s, "guard_enabled", v), host=card)
        self._hint("Te intreaba inainte sa continue cand: apare o fereastra de eroare, aplicatia nu raspunde, SAP arata "
                   "o eroare in bara de stare sau o valoare citita difera de \"Valoarea asteptata\" a pasului.", host=card)

        # ── variabile ──
        card = self._card(title="Variabile (valori de start, folosite ca {Nume})")
        box = tk.Frame(card, bg=card["bg"])
        box.pack(fill="x", padx=6)

        def refill():
            for w in box.winfo_children():
                w.destroy()
            for key in list(r.variables.keys()):
                row = tk.Frame(box, bg=card["bg"])
                row.pack(fill="x", pady=1)
                nv, vv = tk.StringVar(value=key), tk.StringVar(value=r.variables[key])
                ne = tk.Entry(row, textvariable=nv, width=14, **self._entry_style())
                ne.pack(side="left", padx=(0, 4), ipady=2)
                tk.Entry(row, textvariable=vv, **self._entry_style()).pack(side="left", fill="x", expand=True, ipady=2)
                state = {"k": key}

                def rename(_e=None, nv=nv, state=state):
                    nk = nv.get().strip().strip("{}")
                    old = state["k"]
                    if nk == old or not nk or nk in r.variables:
                        nv.set(old)
                        return
                    r.variables = {(nk if k == old else k): v for k, v in r.variables.items()}
                    state["k"] = nk
                    self._changed(None)
                ne.bind("<FocusOut>", rename)
                ne.bind("<Return>", rename)
                vv.trace_add("write", lambda *a, vv=vv, state=state: (r.variables.__setitem__(state["k"], vv.get()),
                                                                     self._changed(None)))
                self.p._btn(row, "✕", lambda state=state: (r.variables.pop(state["k"], None), self._changed(None),
                                                           refill()), tip="Sterge variabila").pack(side="left", padx=2)
        refill()

        def add_var():
            i = 1
            while f"Var{i}" in r.variables:
                i += 1
            r.variables[f"Var{i}"] = ""
            self._changed(None)
            refill()
        self.p._btn(card, "＋ Variabila noua", add_var).pack(anchor="w", padx=8, pady=6)
        self._hint("Variabile speciale mereu disponibile: {Azi}, {Acum}, {Acum:yyyyMMdd_HHmm}, {NewLine}.", host=card)


# ==============================================================================
# 6. DIALOG OBIECT (nume, tehnologie, context, locatori)
# ==============================================================================
class ObjectDialog(tk.Toplevel):
    def __init__(self, panel: StudioPanel, obj: UiObject, is_new: bool = False):
        super().__init__(panel)
        self.p, self.obj, self.result = panel, obj, False
        C = panel.C
        self.title("Obiect nou" if is_new else f"Obiect: {obj.name}")
        self.configure(bg=C["bg_main"])
        self.transient(panel.winfo_toplevel())
        self.attributes("-topmost", True)
        es = dict(bg=C["bg_input"], fg=C["text"], insertbackground=C["text"], relief="flat", font=("Segoe UI", 10))

        def cap(text):
            tk.Label(self, text=text, bg=C["bg_main"], fg=C["text_dim"], font=("Segoe UI", 9, "bold")).pack(
                anchor="w", padx=14, pady=(8, 1))
        cap("Nume (cum il alegi in pasi)")
        self.name = tk.StringVar(value=obj.name)
        tk.Entry(self, textvariable=self.name, **es).pack(fill="x", padx=14, ipady=3)
        cap("Tehnologie")
        self.tech = ttk.Combobox(self, values=[l for _, l in TECHNOLOGIES], state="readonly")
        self.tech.current(next((i for i, (v, _) in enumerate(TECHNOLOGIES) if v == obj.technology), 0))
        self.tech.pack(fill="x", padx=14)
        cap("Context (Web: fragment URL · Desktop: proces:nume.exe sau titlu · SAP: wnd[0])")
        self.context = tk.StringVar(value=obj.context)
        tk.Entry(self, textvariable=self.context, **es).pack(fill="x", padx=14, ipady=3)
        cap("Locatori (in ordinea de incercare; primul care gaseste exact UN element castiga)")
        self.loc_box = tk.Frame(self, bg=C["bg_main"])
        self.loc_box.pack(fill="x", padx=14)
        self.rows: List[Tuple[ttk.Combobox, tk.StringVar, tk.BooleanVar]] = []
        for l in obj.locators:
            self._add_row(l)
        panel._btn(self, "＋ Locator", lambda: self._add_row(Locator(LocatorKind.Css, ""))).pack(anchor="w", padx=14, pady=4)
        tk.Label(self, text="Web: TestId, Id, Role (button|Salveaza), Label, Name, Placeholder, Text, Css, XPath · "
                            "Desktop: AutomationId, UiaName (Button|OK), ClassName, UiaPath · SAP: SapId (wnd[0]/usr/...), SapName",
                 bg=C["bg_main"], fg=C["text_dim"], font=("Segoe UI", 8), wraplength=560, justify="left").pack(
            anchor="w", padx=14)
        row = tk.Frame(self, bg=C["bg_main"])
        row.pack(anchor="e", padx=14, pady=12)
        panel._btn(row, "💾 Salveaza", self._ok, color=C["success"]).pack(side="left", padx=3)
        panel._btn(row, "Anuleaza", self.destroy).pack(side="left", padx=3)
        self.geometry("620x" + str(min(720, 360 + 34 * max(1, len(obj.locators)))))
        self.grab_set()
        self.wait_window()

    def _add_row(self, loc: Locator):
        C = self.p.C
        r = tk.Frame(self.loc_box, bg=C["bg_main"])
        r.pack(fill="x", pady=1)
        kinds = [k.value for k in LocatorKind]
        kind = ttk.Combobox(r, values=kinds, width=13, state="readonly")
        kind.set(loc.kind.value)
        kind.pack(side="left")
        val = tk.StringVar(value=loc.value)
        tk.Entry(r, textvariable=val, bg=C["bg_input"], fg=C["text"], insertbackground=C["text"], relief="flat",
                 font=("Consolas", 10)).pack(side="left", fill="x", expand=True, padx=4, ipady=2)
        en = tk.BooleanVar(value=loc.enabled)
        tk.Checkbutton(r, text="activ", variable=en, bg=C["bg_main"], fg=C["text"], selectcolor=C["bg_input"],
                       activebackground=C["bg_main"]).pack(side="left")
        entry = (kind, val, en)
        self.rows.append(entry)
        self.p._btn(r, "✕", lambda: (r.destroy(), self.rows.remove(entry))).pack(side="left", padx=2)

    def _ok(self):
        name = sanitize_name(self.name.get())
        if not name:
            messagebox.showwarning("Obiect", "Numele nu poate fi gol.", parent=self)
            return
        other = self.p.repo.find(name)
        if other is not None and other is not self.obj:
            messagebox.showwarning("Obiect", f"Exista deja un obiect numit \"{name}\".", parent=self)
            return
        self.obj.name = name
        self.obj.technology = TECHNOLOGIES[self.tech.current()][0]
        self.obj.context = self.context.get().strip()
        self.obj.locators = [Locator(LocatorKind.parse(k.get()), v.get().strip(), 50, e.get())
                             for k, v, e in self.rows if v.get().strip()]
        self.result = True
        self.destroy()
