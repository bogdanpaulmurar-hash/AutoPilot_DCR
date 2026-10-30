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
import time
import uuid
from types import SimpleNamespace
from tkinter import filedialog, messagebox, ttk
import tkinter as tk
import tkinter.font as tkfont
from typing import Any, Callable, Dict, List, Optional, Tuple

from rpr.drivers.base import DriverProvider
from rpr.engine import RprEngine
from rpr.host import AlertDecision, ErrorDecision, RunAlert, RunGuard, RunHost, RunLogEntry
from rpr.lang import level_label
from rpr.legacy import execute_legacy_step
from rpr.model import (ACTIONS, ActionNode, BreakNode, CellColor, CompareOperator, Condition, ConditionKind,
                       ErrorPolicy, ForEachRowNode, GroupNode, IfNode, LegacyStepNode, Locator, LocatorKind,
                       LogNode, LoopMode, LoopNode, ObjectRepository, QuestionNode, Routine, RprAction, RprLogLevel, RunRoutineNode,
                       RprNode, RuleAfter, RuleNode, SetVariableNode, StopNode, TryNode, UiObject, UiTechnology, VariableOperation,
                       WaitMode, WaitNode, WriteExcelNode, action_info, flatten, sanitize_name,
                       OBJECT_TYPES, CONTAINER_TYPES, SiteGroup)
from rpr import report as rpr_report
from rpr import resume as rpr_resume
from rpr import scan as rpr_scan
from rpr import subroutine as rpr_sub
from rpr.storage import Examples, ExcelInfo, RepositoryStore, RoutineStore, RprPaths, RunLogExporter
import ui_theme   # v4.14: contrast automat, texte care se rup dupa latime
import studio_views   # v4.15: bara de activitati, tab-uri, cronologie, ecranul Excel, fluxul

try:
    from i18n import tr, tr_template   # limba interfetei (listele de mai jos se traduc doar la afisare)
except ImportError:       # pragma: no cover
    def tr(text):
        return text
    tr_template = tr

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
RULE_AFTER = [
    (RuleAfter.Retry, "Reia pasul care a esuat"),
    (RuleAfter.Skip, "Considera pasul rezolvat si continua"),
    (RuleAfter.Error, "Eroarea merge mai departe (politica normala)"),
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
    if isinstance(node, IfNode) and node.optional:
        return "👁"
    return {WaitNode: "⏱", SetVariableNode: "✎", IfNode: "🔀", LoopNode: "🔁", ForEachRowNode: "📊",
            WriteExcelNode: "📝", QuestionNode: "💬", TryNode: "🛡", GroupNode: "📁", LogNode: "🗒", RunRoutineNode: "📋", RuleNode: "🧯",
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
        ("👁  Daca apare (optional)", "Asteapta scurt un mesaj / element; daca nu apare, rutina merge mai departe",
         lambda: IfNode(optional=True, condition=Condition(kind=ConditionKind.ElementVisible, timeout_ms=1500))),
        ("🧯  Regula la mesaj / eroare", "Pasi care ruleaza doar daca un pas esueaza cu un anumit mesaj (arma regula inainte)",
         RuleNode),
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
        ("📋  Ruleaza rutina", "Ruleaza o rutina salvata ca pas (mai simplu: tab-ul 📋 Rutine)", RunRoutineNode),
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
        tk.Label(self._tip, text=self._text, bg="#FFFFE0", fg="#222", font=("Segoe UI", 10),
                 relief="solid", bd=1, padx=6, pady=3, wraplength=360, justify="left").pack()
        self._tip.geometry(f"+{x}+{y}")

    def _hide(self, _e=None):
        if self._tip:
            self._tip.destroy()
            self._tip = None


_wheel_installed = False


def _install_wheel(widget):
    """O singura legare pe toata aplicatia: roata mouse-ului deruleaza cadrul de sub cursor, oriunde ar fi
    cursorul in el (v4.13.1: inainte mergea doar deasupra barei, pentru ca Enter/Leave se pierdeau pe widgeturile din cadru)."""
    global _wheel_installed
    if _wheel_installed:
        return
    _wheel_installed = True

    def handler(e):
        try:
            w = widget.winfo_containing(e.x_root, e.y_root)
        except Exception:  # noqa: BLE001  (ex. lista deschisa a unui combobox)
            return
        while w is not None:
            if isinstance(w, (ttk.Treeview, tk.Text, tk.Listbox, ttk.Combobox)):
                return   # acestea se deruleaza singure
            if isinstance(w, ScrollFrame):
                w._wheel(e)
                return
            w = getattr(w, "master", None)
    widget.winfo_toplevel().bind_all("<MouseWheel>", handler, add="+")


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
        _install_wheel(self)

    def _wheel(self, e):
        if self.canvas.winfo_height() < self.inner.winfo_height():
            self.canvas.yview_scroll(int(-e.delta / 120) or (-1 if e.delta > 0 else 1), "units")

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


def input_dialog(parent, title: str, prompt: str, initial: str = "", C=None) -> Optional[str]:
    C = C or {}
    bg, fg = C.get("bg_main", "#1E1E2E"), C.get("text", "#FFFFFF")
    dlg = tk.Toplevel(parent)
    dlg.title(title)
    dlg.configure(bg=bg)
    dlg.attributes("-topmost", True)
    dlg.resizable(False, False)
    res = {"v": None}
    tk.Label(dlg, text=prompt, bg=bg, fg=fg, font=("Segoe UI", 10), wraplength=480, justify="left").pack(
        anchor="w", padx=16, pady=(14, 6))
    var = tk.StringVar(value=initial)
    e = tk.Entry(dlg, textvariable=var, width=60, bg=C.get("bg_input", "#32324A"), fg=fg, insertbackground=fg,
                 relief="flat", font=("Segoe UI", 10))
    e.pack(padx=16, ipady=4)
    e.icursor("end")
    e.focus_set()

    def ok(_e=None):
        res["v"] = var.get()
        dlg.destroy()
    e.bind("<Return>", ok)
    row = tk.Frame(dlg, bg=bg)
    row.pack(anchor="e", padx=16, pady=12)
    tk.Button(row, text="OK", command=ok, bg=C.get("success", "#00AA44"), fg="white", relief="flat",
              font=("Segoe UI", 10, "bold"), padx=14).pack(side="left", padx=3)
    tk.Button(row, text="Anuleaza", command=dlg.destroy, bg=C.get("bg_input", "#3A3A5A"), fg=fg, relief="flat",
              font=("Segoe UI", 10), padx=10).pack(side="left", padx=3)
    dlg.update_idletasks()
    dlg.geometry(f"+{(dlg.winfo_screenwidth() - dlg.winfo_reqwidth()) // 2}+{dlg.winfo_screenheight() // 3}")
    dlg.grab_set()
    dlg.wait_window()
    return res["v"]


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

    def check_before_legacy(self, node):
        """v4.16: pasii pe ecran (coordonate): ca la actiuni + click / taste in aplicatia de la inregistrare."""
        a = self.check_before_action(node)
        if a or not safety:
            return a
        if getattr(self, "_sg", None) is None:
            self._sg = safety.SafetyGuard()
        s = dict(getattr(node, "step", {}) or {})
        step = SimpleNamespace(step_type=str(s.get("step_type", "")).upper(), x=int(s.get("x", 0) or 0),
                               y=int(s.get("y", 0) or 0), window_title=s.get("window_title", "") or "",
                               window_process=s.get("window_process", "") or "",
                               screen_signature=s.get("screen_signature", "") or "",
                               guard_ignore=bool(s.get("guard_ignore", False)), step_id=node.id)
        g = self._sg.check_recorded(step)
        return RunAlert(g.title, g.details, g.key) if g else None

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
        v = self._p.video
        if v is not None and isinstance(node, ActionNode):
            v.marker(node.title)   # capitolele filmului = pasii rutinei

    def row_started(self, row, sheet):
        if self._p.video is not None:
            self._p.video.row_started(row, sheet)   # fara Tk: poate rula pe firul motorului
        film, sec = self.video_position()           # v4.15: minutul randului, pentru ecranul Excel
        self._p.post("row_started", (row, sheet, film, sec))

    def row_finished(self, row, status):
        if self._p.video is not None:
            self._p.video.row_finished(row, status)
        self._p.post("row_finished", (row, status))

    @property
    def video_recorder(self):
        v = self._p.video   # filmul curent, pentru linkurile din raportul Excel
        return v.rec if v is not None and v.mode == "run" else None

    def node_finished(self, node, success):
        self._p.post("finished", (node, success))

    def ask(self, title, text, buttons):
        return self._p.call_ui(lambda: choice_dialog(self._p, title, text, list(buttons), C=self._p.C))

    def ask_value(self, title, text, initial=""):
        return self._p.call_ui(lambda: input_dialog(self._p, title, text, initial, C=self._p.C))

    def ask_on_error(self, node, error, inside_excel_loop):
        btns = ["Reincearca", "Sari pasul"] + (["Sari randul"] if inside_excel_loop else []) + ["Opreste"]
        # v4.17 ▶ Ruleaza si marcheaza: obiectul pasului se poate marca pe loc, apoi pasul se reia
        obj = self._p.learn_object_of(node) if getattr(self._p, "_learn_run", False) else None
        mark = "🎯 Marcheaza acum"
        detail = error
        if obj is not None:
            btns = [mark] + btns
            detail = tr_template("🎯 Marcheaza acum [{0}] pe pagina, apoi pasul se reia.").format(obj.name) + \
                "\n\n" + error
        while True:
            ans = self._p.call_ui(lambda: self._p.paused_dialog(
                "Pasul a esuat", f"Pasul \"{node.title}\" a esuat.", btns, detail))
            if ans != mark:
                break
            if self._p.learn_mark(obj):
                return ErrorDecision.RETRY
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
                                relief="flat", font=("Segoe UI", 10, "bold"), padx=8, cursor="hand2")
        self._pause.pack(side="left", padx=2)
        tk.Button(row, text="⏭ Pas", command=panel.step_once, bg=C["bg_input"], fg=C["text"], relief="flat",
                  font=("Segoe UI", 10, "bold"), padx=8, cursor="hand2").pack(side="left", padx=2)
        tk.Button(row, text="⏹ STOP", command=panel.stop, bg=C["danger"], fg="white", relief="flat",
                  font=("Segoe UI", 10, "bold"), padx=8, cursor="hand2").pack(side="left", padx=2)
        tk.Label(self, text="Ctrl+F11 pauza/reluare  ·  Ctrl+F12 stop", bg=C["bg_card"], fg=C["text_dim"],
                 font=("Segoe UI", 9)).pack(padx=8, pady=(0, 6), anchor="w")
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
                 on_status: Optional[Callable[[str], None]] = None,
                 dnd_allowed: Optional[Callable[[], bool]] = None, video=None,
                 on_help: Optional[Callable[[], None]] = None):
        super().__init__(master, bg=colors["bg_main"])
        self.C = colors
        self._on_help = on_help     # v4.16: ❓ deschide 📖 Instructiuni (RO / EN / DE)
        self.video = video          # VideoController (🎥 film la rulare) sau None
        self._dnd_allowed = dnd_allowed or (lambda: True)
        self._run_frame = run_frame
        self._on_status = on_status or (lambda s: None)

        self.repo = ObjectRepository()
        self.repo_path = RprPaths.default_repository()
        self.routine = Routine()
        self.routine_path: Optional[str] = None
        self.dirty = False

        self.engine: Optional[RprEngine] = None
        from rpr.drivers.registry import StudioSettings
        self.studio_settings = StudioSettings.load()
        self.drivers = self._build_drivers()
        self._recording = False
        self._spy_hint: Optional[tk.Toplevel] = None
        self.busy = False
        self._run_control: Optional[RunControlWindow] = None
        self._queue: "queue.Queue[tuple]" = queue.Queue()
        self._items: Dict[str, Tuple[str, Optional[RprNode], List[RprNode]]] = {}
        self._running_iid: Optional[str] = None
        self._log_entries: List[RunLogEntry] = []
        self._step_t0: Dict[str, float] = {}                # v4.15: cronologia rularii
        self._step_errors: Dict[str, Tuple[str, str]] = {}
        self._cur_row = 0

        self._last_folder = ("", "")   # v4.11: ultimul folder ales la scanare; il folosesc si capturile 3 s
        self._prep_runner = None    # pregatirea care ruleaza (📂 Manager de rutine)
        self._resume_state = None   # rpr/resume.py: starea rularii, pentru reluare dupa o inchidere neasteptata

        self._styles()
        self._build()
        self.load_repository(self.studio_settings.library_path or RprPaths.default_repository())
        self.new_routine(ask=False)
        self._restore_side()
        self.after(50, self._poll)
        self.after(400, lambda: ui_theme.fix_contrast(self))   # v4.14: niciun text greu de citit
        # 📂 rutinele din folderul setat se citesc in fundal (Managerul de rutine le are gata)
        from rpr.batch import preload, shared_library
        if shared_library().scanned_at is None:
            preload(self.studio_settings.effective_routines_folder(),
                    on_done=lambda lib: self.post("routines_ready", None))

    # ── drivere (se completeaza in etapele 2-3) ─────────────────────────────
    def _build_drivers(self) -> DriverProvider:
        provider = DriverProvider()
        try:
            from rpr.drivers.registry import register_all
            register_all(provider, self.studio_settings)
        except ImportError:
            pass
        return provider

    # ── v4.17 ▶ Ruleaza si marcheaza ──
    def learn_object_of(self, node) -> Optional[UiObject]:
        """Obiectul din biblioteca folosit de pas (Click, Scrie, Citeste... sau Asteapta obiectul), daca se poate marca."""
        name = ""
        if isinstance(node, ActionNode):
            name = node.target
        elif isinstance(node, WaitNode) and node.mode != WaitMode.Seconds:
            name = node.condition.target
        obj = self.repo.find(name.strip()) if name and name.strip() else None
        if obj is None or obj.technology not in (UiTechnology.Web, UiTechnology.WebSelenium, UiTechnology.Sap,
                                                 UiTechnology.Desktop):
            return None
        return obj

    def learn_mark(self, obj: UiObject) -> bool:
        """Pe firul rularii: Spy pentru obiect, locatoarele capturate intra in obiect, biblioteca se salveaza."""
        from complete_ui import merge_captured
        web = obj.technology in (UiTechnology.Web, UiTechnology.WebSelenium)
        driver = self.web() if web else self.drivers.get(obj.technology)

        def show():
            self._spy_driver = None if web else driver
            self._show_spy_hint(tr_template("🎯 [{0}]: du mouse-ul peste element si da CLICK (SAP / Desktop: F2). "
                                            "Esc = anuleaza.").format(obj.name))
        self.call_ui(show)
        try:
            hint = "Click = captureaza · Esc = anuleaza" if web else "F2 = captureaza · Esc = anuleaza"
            captured = driver.capture_object(hint, RprPaths.object_images())
        except Exception as ex:  # noqa: BLE001
            self.post("status", f"🎯 {ex}")
            captured = None
        finally:
            self.call_ui(self._hide_spy_hint)
        if captured is None:
            return False

        def apply():
            n = merge_captured(obj, captured)
            if obj.context:
                self.repo.classify(obj)
            self.save_repository()
            self.refresh_objects()
            win = getattr(self, "_complete_win", None)
            if win is not None and win.winfo_exists():
                win.object_marked(obj, n)
            self.set_status(tr_template("🎯 [{0}] are acum {1} locatoare.").format(obj.name, len(obj.locators)))
        self.call_ui(apply)
        return True

    # ── v4.19 🎯 Remarcheaza din pas: dupa ▶ Testeaza pasul, obiectul gresit se corecteaza pe loc ──
    @staticmethod
    def step_object_name(node) -> str:
        """Numele obiectului folosit de pas (Click, Scrie, Citeste... sau Asteapta obiectul)."""
        if isinstance(node, ActionNode):
            return node.target.strip()
        if isinstance(node, WaitNode) and node.mode != WaitMode.Seconds:
            return node.condition.target.strip()
        return ""

    @staticmethod
    def set_step_object(node, name: str) -> None:
        if isinstance(node, ActionNode):
            node.target = name
        elif isinstance(node, WaitNode):
            node.condition.target = name

    def step_technology(self, node) -> UiTechnology:
        obj = self.repo.find(self.step_object_name(node))
        if obj is not None:
            return obj.technology
        if isinstance(node, ActionNode):
            info = action_info(node.action)
            return node.technology if node.technology in info.technologies else info.technologies[0]
        return UiTechnology.Web

    def steps_using(self, name: str) -> int:
        low = name.lower()
        return sum(1 for n in flatten(self.routine.steps) if self.step_object_name(n).lower() == low)

    def remark_step(self, node):
        """🎯 Remarcheaza: Spy pe element; obiectul pasului primeste locatoarele noi
        (sau pasul primeste un obiect nou, doar pentru el). Biblioteca se salveaza."""
        if self.busy:
            self.set_status(tr("Asteapta sa se termine operatia curenta."))
            return
        name = self.step_object_name(node)
        obj = self.repo.find(name) if name else None
        mode = "new"
        if obj is not None:
            used = self.steps_using(obj.name)
            detail = tr_template("Inlocuieste locatoarele: obiectul [{0}] pastreaza numele, deci toti cei {1} pasi "
                                 "care il folosesc vor cauta elementul nou.\n"
                                 "Obiect nou doar pentru acest pas: [{0}] ramane neschimbat pentru ceilalti pasi.").format(
                obj.name, used)
            a = choice_dialog(self, "🎯 Remarcheaza obiectul",
                              tr_template("Ce faci cu [{0}]?").format(obj.name),
                              ["Inlocuieste locatoarele", "Obiect nou doar pentru acest pas", "Anuleaza"], detail,
                              C=self.C)
            if a == "Anuleaza" or not a:
                return
            mode = "replace" if a == "Inlocuieste locatoarele" else "new"
        tech = obj.technology if obj is not None else self.step_technology(node)
        web = tech in (UiTechnology.Web, UiTechnology.WebSelenium)
        url = None
        if web:
            url = self._ask_url_if_closed()
            if url is False:
                return
        driver = self.web() if web else self.drivers.get(tech)
        self.busy = True
        self._spy_driver = None if web else driver
        label = obj.name if obj is not None else tr("obiect nou")
        self._show_spy_hint(tr_template("🎯 [{0}]: du mouse-ul peste element si da CLICK (SAP / Desktop: F2). "
                                        "Esc = anuleaza.").format(label))

        def work():
            try:
                if url:
                    driver.open(url)
                hint = "Click = captureaza · Esc = anuleaza" if web else "F2 = captureaza · Esc = anuleaza"
                captured = driver.capture_object(hint, RprPaths.object_images())
                self.post("ui", lambda: self._remark_done(node, obj, mode, captured, None))
            except Exception as ex:  # noqa: BLE001
                err = str(ex)
                self.post("ui", lambda: self._remark_done(node, obj, mode, None, err))
        self.set_status(tr("🎯 Click pe element (SAP / Desktop: F2). Esc = anulare."))
        threading.Thread(target=work, daemon=True, name="Remark").start()

    def _remark_done(self, node, obj: Optional[UiObject], mode: str, captured: Optional[UiObject],
                     error: Optional[str], ask_name: bool = True):
        self.busy = False
        self._hide_spy_hint()
        if error:
            messagebox.showerror("🎯", error, parent=self)
            return
        if captured is None:
            self.set_status(tr("Marcare anulata."))
            return
        if mode == "replace" and obj is not None:
            rpr_scan.apply_recapture(obj, captured)
            if obj.context:
                self.repo.classify(obj)
            final = obj
        else:
            self.repo.classify(captured)
            if obj is not None:   # acelasi folder ca obiectul vechi; numele pornesc de la el
                captured.folder = obj.folder
                base = obj.name
            else:
                base = captured.name
            suggestion = self.repo.make_unique_name(base)
            name = input_dialog(self, "🎯 Obiect nou", tr("Numele obiectului nou:"), suggestion, C=self.C) \
                if ask_name else suggestion
            if name is None or not name.strip():
                self.set_status(tr("Obiect nesalvat."))
                return
            captured.name = name.strip()
            final = self.repo.add(captured)
            self.set_step_object(node, final.name)
            self.mark_dirty()
            self.refresh_node(node)
        self.save_repository()
        self.refresh_objects()
        try:
            if self.editor._target is node:
                self.editor.show(node)
        except Exception:  # noqa: BLE001
            pass
        self.set_status(tr_template("🎯 [{0}] are acum {1} locatoare. Apasa ▶ Testeaza pasul ca sa verifici.").format(
            final.name, len(final.locators)))

    def web(self):
        """Driverul Web (acelasi browser pentru Spy, inregistrare si rulare)."""
        d = self.drivers.get(UiTechnology.Web)
        if getattr(d, "on_info", "absent") is None:
            d.on_info = lambda m: self.post("status", m)
        return d

    def shutdown(self):
        """La inchiderea aplicatiei: oprim inregistrarea si inchidem browserul."""
        try:
            if self._recording:
                self.web().stop_recording()
        except Exception:
            pass
        self.drivers.close()

    # =========================================================================
    # Constructia interfetei
    # =========================================================================
    def _styles(self):
        C = self.C
        st = ttk.Style()
        # v4.14: inaltimea randului urmeaza fontul (cu "Marime text" mare, randurile nu se mai taie)
        line = tkfont.Font(self, font=("Segoe UI", 10)).metrics("linespace")
        self._row_h = max(24, line + 10)
        on_primary = ui_theme.text_on(C["primary"], self)
        st.configure("Studio.Treeview", background=C["bg_input"], fieldbackground=C["bg_input"],
                     foreground=C["text"], rowheight=self._row_h, font=("Segoe UI", 10), borderwidth=0)
        st.map("Studio.Treeview", background=[("selected", C["primary"])], foreground=[("selected", on_primary)])
        st.configure("Studio.Treeview.Heading", background=C["bg_card"], foreground=C["text_dim"],
                     font=("Segoe UI", 10, "bold"), relief="flat", padding=[6, 4])
        st.map("Studio.Treeview.Heading", background=[("active", C["bg_card"])])
        st.configure("Studio.TNotebook", background=C["bg_main"], borderwidth=0, tabmargins=[2, 4, 2, 0])
        st.configure("Studio.TNotebook.Tab", background=C["bg_card"], foreground=C["text_dim"], padding=[14, 6],
                     font=("Segoe UI", 10, "bold"), borderwidth=0)
        st.map("Studio.TNotebook.Tab", background=[("selected", C["primary"])], foreground=[("selected", on_primary)],
               padding=[("selected", [14, 6])])
        st.configure("Studio.TPanedwindow", background=C["bg_main"])
        st.configure("Sash", sashthickness=6, gripcount=0)
        ui_theme.style_combobox(st, "Studio.TCombobox", C)
        ui_theme.style_popdown(self, C)

    def _label(self, parent, text, size=9, bold=False, color=None, **kw):
        return tk.Label(parent, text=text, bg=kw.pop("bg", parent["bg"]), fg=color or self.C["text"],
                        font=("Segoe UI", size, "bold" if bold else "normal"), **kw)

    def _btn(self, parent, text, cmd, color=None, tip="", **kw):
        bg = color or self.C["bg_input"]
        fg = ui_theme.text_on(bg, self) if color else self.C["text"]   # v4.14: textul se alege dupa fundal
        b = tk.Button(parent, text=text, command=cmd, bg=bg, fg=fg, activebackground=self.C["primary"],
                      activeforeground=ui_theme.text_on(self.C["primary"], self), relief="flat",
                      font=("Segoe UI", 10), padx=10, pady=4, cursor="hand2", bd=0, highlightthickness=0, **kw)
        if tip:
            ToolTip(b, tip)
        return b

    def _build(self):
        C = self.C
        # v4.15: bara de activitati in stanga; fiecare iconita schimba doar panoul lateral
        self._rail = studio_views.ActivityBar(self, C, [
            ("steps", "🧱", "Pasi", "panel"), ("library", "📚", "Biblioteca", "panel"),
            ("routines", "📋", "Rutine", "panel"), ("films", "🎬", "Filme", "panel"),
            ("import", "📥", "Import AI", "action"), None,
            ("settings", "🌐", "Setari", "action"), ("guide", "❓", "Ghid", "action")],
            on_panel=self._on_rail, on_action=self._on_rail_action)
        self._rail.pack(side="left", fill="y")
        vpaned = ttk.PanedWindow(self, orient="vertical", style="Studio.TPanedwindow")
        vpaned.pack(fill="both", expand=True, padx=6, pady=6)
        hpaned = ttk.PanedWindow(vpaned, orient="horizontal", style="Studio.TPanedwindow")
        vpaned.add(hpaned, weight=4)
        self._vpaned, self._hpaned = vpaned, hpaned

        # ── Stanga: panoul activitatii alese (blocuri, obiecte, rutine, filme) ──
        left = tk.Frame(hpaned, bg=C["bg_main"], width=260)
        hpaned.add(left, weight=1)
        self._side, self._side_shown = left, True
        tb = ScrollFrame(left, C["bg_main"])
        self._build_toolbox(tb.inner)
        ob = tk.Frame(left, bg=C["bg_main"])
        self._build_objects(ob)
        rt = tk.Frame(left, bg=C["bg_main"])
        self._build_routines_tab(rt)
        self._films = studio_views.FilmsPanel(left, self)
        self._side_pages = {"steps": tb, "library": ob, "routines": rt, "films": self._films}

        # ── Centru: tab-urile rutinelor + pasii / fluxul / ecranul Excel ──
        center = tk.Frame(hpaned, bg=C["bg_main"])
        hpaned.add(center, weight=3)
        top = tk.Frame(center, bg=C["bg_main"])
        top.pack(fill="x", pady=(0, 2))
        views = tk.Frame(top, bg=C["bg_main"])
        views.pack(side="right")
        self._view_btns: Dict[str, tk.Button] = {}
        for key, text, tip in [("steps", "✎ Pasi", "Pasii rutinei, ca lista (editare)"),
                               ("flow", "🔀 Flux", "Rutina ca flux de carduri: ramurile una langa alta (doar citire)"),
                               ("excel", "📊 Excel", "Randurile Excel ale rutinei: status, film, reia randul")]:
            b = self._btn(views, text, lambda k=key: self.show_center(k), tip=tip)
            b.configure(padx=8)
            b.pack(side="left", padx=1)
            self._view_btns[key] = b
        self._doc_tabs = studio_views.DocTabs(top, C, on_switch=self.switch_doc, on_close=self.close_doc,
                                              on_new=lambda: self.new_routine())
        self._doc_tabs.pack(side="left", fill="x", expand=True)
        self._doc_tabs.bind("<Configure>", lambda e: self._render_tabs(), add="+")
        self._docs: List[Dict[str, Any]] = []
        self._doc_i = 0
        self._tabs_sig = None
        # butoanele pe rand separat: un nume lung de rutina nu le mai impinge in afara ecranului
        bar = tk.Frame(center, bg=C["bg_main"])
        bar.pack(side="top", fill="x", pady=(2, 4))
        self._edit_bar = bar
        for text, cmd, tip in [("▲", lambda: self.move(-1), "Muta sus (Ctrl+Sus)"),
                               ("▼", lambda: self.move(1), "Muta jos (Ctrl+Jos)"),
                               ("Duplica", self.duplicate, "Duplica pasul cu tot ce contine (Ctrl+D)"),
                               ("Activ / Omis", self.toggle_enabled, "Activeaza / omite pasul (Spatiu)"),
                               ("Sterge", self.delete_selected, "Sterge pasul (Delete)"),
                               ("⚙ Rutina", self.show_routine_settings, "Setarile rutinei si variabilele")]:
            self._btn(bar, text, cmd, tip=tip).pack(side="left", padx=1)

        stack = tk.Frame(center, bg=C["bg_main"])
        stack.pack(fill="both", expand=True)
        tree_box = tk.Frame(stack, bg=C["bg_main"])
        self._flow = studio_views.FlowView(stack, self)
        self._excel = studio_views.ExcelRunView(stack, self)
        self._center_views = {"steps": tree_box, "flow": self._flow, "excel": self._excel}
        self._view = "steps"
        tree_box.pack(fill="both", expand=True)
        self._paint_view_btns()
        self.tree = ttk.Treeview(tree_box, show="tree", style="Studio.Treeview", selectmode="browse")
        vsb = ttk.Scrollbar(tree_box, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        self.tree.pack(side="left", fill="both", expand=True)
        rd = lambda c: ui_theme.readable(c, C["bg_input"], widget=self)   # noqa: E731 — culori lizibile pe ambele teme
        self.tree.tag_configure("disabled", foreground=ui_theme.readable(C["text_muted"], C["bg_input"], 3.0, self))
        self.tree.tag_configure("branch", foreground=rd(C["accent"]), font=("Segoe UI", 10, "italic"))
        self.tree.tag_configure("running", background="#B36B00", foreground="white")
        self.tree.tag_configure("ok", foreground=rd("#3CCF6E"))
        self.tree.tag_configure("error", foreground=rd("#FF5C5C"))
        self.tree.tag_configure("drop_into", background=C["row_active"] if "row_active" in C else C["bg_card"])
        self._drop_line = tk.Frame(self.tree, bg=C["primary"], height=3)
        self._drop_into = None
        self._drag_source(self.tree, self._tree_drag_payload, "↕ Muta pasul")
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
        # v4.14: latimea panourilor se tine minte ca procent din fereastra (merge si pe ecrane mici)
        for pw in (hpaned, vpaned):
            pw.bind("<ButtonRelease-1>", lambda e: self.after(50, self._save_layout), add="+")
        hpaned.bind("<Configure>", lambda e: self._layout_later(), add="+")
        self.after(150, self._apply_layout)
        self._bottom = bottom
        self._timeline = studio_views.RunTimeline(bottom, C, on_pick=self._timeline_pick, on_open=self.open_path)
        bottom.add(self._timeline, text="⏱ Cronologie")
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
        self.log.tag_configure("Error", foreground=ui_theme.readable("#FF6B6B", C["bg_input"], widget=self))
        self.log.tag_configure("Warning", foreground=ui_theme.readable("#FFC24B", C["bg_input"], widget=self))
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

    # =========================================================================
    # v4.14: aspect — latimea panourilor (procent din fereastra, tinut minte)
    # =========================================================================
    def _apply_layout(self):
        hp, vp = self._hpaned, self._vpaned
        W, H = hp.winfo_width(), vp.winfo_height()
        if W < 200 or H < 200:
            self.after(150, self._apply_layout)
            return
        lay = getattr(self.studio_settings, "layout", None) or {}
        left, right, bottom = (float(lay.get(k, d)) for k, d in (("left", 0.22), ("right", 0.30), ("bottom", 0.24)))
        lw, rw = max(230, int(W * left)), max(300, int(W * right))
        avail = W - 280                       # arborele rutinei pastreaza cel putin ~280 px
        if lw + rw > avail:
            lw = max(180, int(avail * left / (left + right)))
            rw = max(220, avail - lw)
        try:
            if self._side_shown:
                hp.sashpos(0, lw)
                hp.sashpos(1, W - rw)
            else:                             # v4.15: panoul lateral strans din bara de activitati
                hp.sashpos(0, W - min(rw, W - 280))
            vp.sashpos(0, max(200, int(H * (1 - min(0.5, max(0.1, bottom))))))
        except tk.TclError:
            pass
        self._layout_w = W

    def _layout_later(self):
        W = self._hpaned.winfo_width()
        if abs(W - getattr(self, "_layout_w", 0)) < 40:
            return
        if getattr(self, "_layout_job", None):
            self.after_cancel(self._layout_job)
        self._layout_job = self.after(150, self._apply_layout)

    def _save_layout(self):
        hp, vp = self._hpaned, self._vpaned
        W, H = hp.winfo_width(), vp.winfo_height()
        if W < 200 or H < 200:
            return
        lay = dict(getattr(self.studio_settings, "layout", None) or {})
        try:
            if self._side_shown:
                lay.update(left=round(hp.sashpos(0) / W, 3), right=round((W - hp.sashpos(1)) / W, 3))
            else:
                lay.update(right=round((W - hp.sashpos(0)) / W, 3))
            lay["bottom"] = round((H - vp.sashpos(0)) / H, 3)
        except tk.TclError:
            return
        self._layout_w = W
        if lay != getattr(self.studio_settings, "layout", None):
            self.studio_settings.layout = lay
            self.studio_settings.save()

    # =========================================================================
    # v4.14: drag and drop — pasi in arbore, blocuri, obiecte si rutine trase in rutina
    # =========================================================================
    def _drag_source(self, widget, payload_fn: Callable[[], Optional[Tuple[str, Any]]], label: str = ""):
        widget.bind("<ButtonPress-1>", lambda e: self._drag_press(e, payload_fn, label), add="+")
        widget.bind("<B1-Motion>", self._drag_motion, add="+")
        widget.bind("<ButtonRelease-1>", self._drag_release, add="+")

    def _drag_press(self, e, payload_fn, label):
        self._drag = {"x": e.x_root, "y": e.y_root, "fn": payload_fn, "label": label, "on": False,
                      "payload": None, "ghost": None, "src": e.widget}

    def _drag_motion(self, e):
        d = getattr(self, "_drag", None)
        if not d:
            return
        if not d["on"]:
            if abs(e.x_root - d["x"]) + abs(e.y_root - d["y"]) < 10:
                return
            payload = d["fn"]()
            if not payload or payload[1] is None:
                self._drag = None
                return
            d["on"], d["payload"] = True, payload
            g = tk.Toplevel(self)
            g.overrideredirect(True)
            try:
                g.attributes("-topmost", True)
                g.attributes("-alpha", 0.9)
            except tk.TclError:
                pass
            tk.Label(g, text=d["label"] or "…", bg=self.C["primary"], fg=ui_theme.text_on(self.C["primary"], self),
                     font=("Segoe UI", 10, "bold"), padx=10, pady=4).pack()
            d["ghost"] = g
        d["ghost"].geometry(f"+{e.x_root + 14}+{e.y_root + 10}")
        self._show_drop(e.x_root, e.y_root)

    def _drag_release(self, e):
        d, self._drag = getattr(self, "_drag", None), None
        self._hide_drop()
        if not d or not d["on"]:
            return
        if d["ghost"] is not None:
            d["ghost"].destroy()
        target = self._drop_target(e.x_root, e.y_root)
        if target is None:
            return "break"
        owner, index, _y, _into = target
        kind, obj = d["payload"]
        if kind == "move":
            self._move_node_to(obj, owner, index)
        elif kind == "node":
            self._insert_at = (owner, index)
            self.insert_node(obj)
        elif kind == "object":
            self._drop_object_menu(obj, owner, index, e.x_root, e.y_root)
        elif kind == "routine":
            self.add_routine_step(entry=obj, at=(owner, index))
        return "break"

    def _drop_target(self, x_root: int, y_root: int):
        """Unde ajunge pasul lasat la (x_root, y_root): (lista, pozitie, y linie, rand "in interior")."""
        tree = self.tree
        w = tree.winfo_containing(x_root, y_root)
        if w is not tree:
            return None
        y = y_root - tree.winfo_rooty()
        row = tree.identify_row(y)
        if not row or row not in self._items:
            kids = tree.get_children()
            last_y = 0
            if kids:
                vis = [i for i in self._visible_rows() if tree.bbox(i)]
                if vis:
                    bx = tree.bbox(vis[-1])
                    last_y = bx[1] + bx[3]
            return self.routine.steps, len(self.routine.steps), last_y, None
        kind, node, owner = self._items[row]
        bbox = tree.bbox(row) or (0, y, 0, self._row_h)
        rel = (y - bbox[1]) / max(1, bbox[3])
        if kind == "branch":
            return owner, len(owner), None, row
        branches = node.branches()
        if len(branches) == 1 and 0.3 <= rel <= 0.75:
            return branches[0][1], len(branches[0][1]), None, row
        idx = next(i for i, x in enumerate(owner) if x is node)
        if rel < 0.5:
            return owner, idx, bbox[1], None
        return owner, idx + 1, bbox[1] + bbox[3], None

    def _visible_rows(self):
        out, stack = [], list(reversed(self.tree.get_children()))
        while stack:
            iid = stack.pop()
            out.append(iid)
            if self.tree.item(iid, "open"):
                stack.extend(reversed(self.tree.get_children(iid)))
        return out

    def _show_drop(self, x_root: int, y_root: int):
        tree = self.tree
        y = y_root - tree.winfo_rooty()     # derulare automata langa margini
        if 0 <= y < 24:
            tree.yview_scroll(-1, "units")
        elif tree.winfo_height() - 24 < y <= tree.winfo_height():
            tree.yview_scroll(1, "units")
        t = self._drop_target(x_root, y_root)
        if getattr(self, "_drop_into", None) and self.tree.exists(self._drop_into):
            tags = [x for x in self.tree.item(self._drop_into, "tags") if x != "drop_into"]
            self.tree.item(self._drop_into, tags=tags)
        self._drop_into = None
        if t is None:
            self._drop_line.place_forget()
            return
        _o, _i, line_y, into = t
        if into:
            self._drop_line.place_forget()
            self.tree.item(into, tags=list(self.tree.item(into, "tags")) + ["drop_into"])
            self._drop_into = into
        else:
            self._drop_line.place(in_=tree, x=0, y=max(0, line_y - 1), relwidth=1, height=3)
            self._drop_line.lift()

    def _hide_drop(self):
        try:
            self._drop_line.place_forget()
            if getattr(self, "_drop_into", None) and self.tree.exists(self._drop_into):
                tags = [x for x in self.tree.item(self._drop_into, "tags") if x != "drop_into"]
                self.tree.item(self._drop_into, tags=tags)
        except tk.TclError:
            pass
        self._drop_into = None

    def _tree_drag_payload(self):
        node, _owner = self._sel_node()
        return ("move", node) if node is not None else None

    def _move_node_to(self, node: RprNode, target: List[RprNode], index: int):
        # nu se poate muta un pas in interiorul lui insusi
        for n in flatten([node]):
            if any(lst is target for _, lst in n.branches()):
                self.set_status("Un pas nu poate fi mutat in interiorul lui.")
                return
        owner = next((info[2] for info in self._items.values() if info[0] == "node" and info[1] is node), None)
        if owner is None:
            return
        i = next(k for k, x in enumerate(owner) if x is node)
        if owner is target and index in (i, i + 1):
            return                              # acelasi loc
        owner.pop(i)
        if owner is target and index > i:
            index -= 1
        target.insert(max(0, min(index, len(target))), node)
        self.mark_dirty()
        self.rebuild_tree(node)

    def _drop_object_menu(self, obj: UiObject, owner, index, x_root, y_root):
        """Obiect tras in rutina: alegi ce face pasul."""
        C = self.C
        m = tk.Menu(self, tearoff=0, bg=C["bg_card"], fg=C["text"], activebackground=C["primary"],
                    activeforeground=ui_theme.text_on(C["primary"], self), font=("Segoe UI", 10))

        def put(fn):
            self._insert_at = (owner, index)
            fn()
            self._insert_at = None
        m.add_command(label="Click", command=lambda: put(lambda: self._obj_step(RprAction.Click, obj)))
        m.add_command(label="Scrie text", command=lambda: put(lambda: self._obj_step(RprAction.TypeText, obj)))
        m.add_command(label="Citeste valoare", command=lambda: put(lambda: self._obj_step(RprAction.ReadText, obj)))
        m.add_command(label="Alege din lista", command=lambda: put(lambda: self._obj_step(RprAction.SelectOption, obj)))
        m.add_separator()
        m.add_command(label="Daca obiectul exista", command=lambda: put(lambda: self.insert_node(
            IfNode(condition=Condition(kind=ConditionKind.ElementExists, target=obj.name, timeout_ms=2000)))))
        try:
            m.tk_popup(x_root, y_root)
        finally:
            m.grab_release()

    def _build_toolbox(self, host):
        C = self.C
        ui_theme.autowrap(tk.Label(host, text="Click pe un bloc = il adaugi dupa pasul selectat. Sau trage-l cu mouse-ul "
                                              "exact unde vrei in rutina (si in interiorul unui \"Daca\" sau al unei bucle).",
                                   bg=C["bg_main"], fg=C["text_dim"], font=("Segoe UI", 9), justify="left", anchor="w"),
                          margin=12).pack(fill="x", padx=8, pady=(8, 2))
        for group, items in TOOLBOX:
            tk.Label(host, text=tr(group).upper(), bg=C["bg_main"], fg=C["primary"], font=("Segoe UI", 9, "bold")).pack(
                anchor="w", padx=8, pady=(12, 3))
            for text, tip, factory in items:
                b = tk.Button(host, text=text, anchor="w", command=lambda f=factory: self.insert_node(f()),
                              bg=C["bg_card"], fg=C["text"], activebackground=C["primary"],
                              activeforeground=ui_theme.text_on(C["primary"], self),
                              relief="flat", font=("Segoe UI", 10), padx=10, pady=5, cursor="hand2", bd=0,
                              highlightthickness=0)
                b.pack(fill="x", padx=8, pady=2)
                ToolTip(b, tip)
                self._drag_source(b, lambda f=factory: ("node", f()), text)

    def _build_objects(self, host):
        """📚 Biblioteca de obiecte (ca in SilkTest): Site -> Pagina -> Container -> obiecte,
        comuna tuturor rutinelor. Fiecare obiect poate fi testat inainte de a-l folosi."""
        C = self.C
        # v4.9: biblioteca e un fisier ales de tine (de ex. una pe aplicatie, in OneDrive)
        lib = tk.Frame(host, bg=C["bg_card"])
        lib.pack(fill="x", padx=4, pady=(4, 2))
        self._lib_label = tk.Label(lib, text="", bg=C["bg_card"], fg=C["text"], font=("Segoe UI", 10, "bold"),
                                   anchor="w")
        self._lib_label.pack(fill="x", padx=6, pady=(3, 1))
        lrow = tk.Frame(lib, bg=C["bg_card"])
        lrow.pack(fill="x", padx=2, pady=(0, 3))
        for text, cmd, tip in [("📂 Deschide", self.open_library, "Deschide alta biblioteca de obiecte (fisier .json)"),
                               ("＋ Noua", lambda: self.new_library(), "Biblioteca noua pentru o aplicatie "
                                                                      "(propune un folder in OneDrive)"),
                               ("📁", self.open_library_folder, "Deschide folderul bibliotecii")]:
            self._btn(lrow, text, cmd, tip=tip).pack(side="left", padx=1)
        srow = tk.Frame(host, bg=C["bg_main"])
        srow.pack(fill="x", padx=4, pady=(0, 2))
        self._btn(srow, "🔍 Scaneaza site", self.scan_site,
                  tip="Deschide adresa si adauga butoanele si campurile gasite pe pagina (doar citeste pagina)").pack(
            side="left", padx=1)
        self._btn(srow, "🖐 Captura 3 s", self.hover_capture,
                  tip="Tii cursorul 3 secunde pe un camp / buton si se salveaza singur; apoi treci la urmatorul").pack(
            side="left", padx=1)
        self._btn(srow, "🩺 Verifica", lambda: self.check_saved(),
                  tip="Verifica daca butoanele salvate mai merg pe pagina din browser: simulare fara click").pack(
            side="left", padx=1)
        self._btn(srow, "🎯 Completeaza", lambda: self.show_complete_objects(),
                  tip="Obiectele rutinei deschise, pe rand, pe pagina reala: verifici si marchezi cu click "
                      "(dupa 📥 Import AI)").pack(side="left", padx=1)
        top = tk.Frame(host, bg=C["bg_main"])
        top.pack(fill="x", padx=4, pady=(4, 2))
        self._obj_filter = tk.StringVar()
        e = tk.Entry(top, textvariable=self._obj_filter, bg=C["bg_input"], fg=C["text"], relief="flat",
                     insertbackground=C["text"], font=("Segoe UI", 10))
        e.pack(fill="x", ipady=2)
        ToolTip(e, "Cauta dupa nume, tip, site, pagina sau eticheta")
        self._obj_filter.trace_add("write", lambda *a: self.refresh_objects())
        self._obj_only_page = tk.BooleanVar(value=False)
        tk.Checkbutton(top, text="Doar ce merge pe pagina din browser", variable=self._obj_only_page,
                       command=self.refresh_objects, bg=C["bg_main"], fg=C["text_dim"], selectcolor=C["bg_input"],
                       activebackground=C["bg_main"], font=("Segoe UI", 9)).pack(anchor="w")
        box = tk.Frame(host, bg=C["bg_main"])
        box.pack(fill="both", expand=True, padx=4)
        self.objects = ttk.Treeview(box, columns=("tip",), show="tree headings", style="Studio.Treeview")
        self.objects.heading("#0", text="Site · Pagina · Folder · Obiect", anchor="w")
        self.objects.heading("tip", text="Tip", anchor="w")
        self.objects.column("#0", width=170)
        self.objects.column("tip", width=78, stretch=False)
        vsb = ttk.Scrollbar(box, orient="vertical", command=self.objects.yview)
        self.objects.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        self.objects.pack(fill="both", expand=True)
        self.objects.tag_configure("site", foreground=ui_theme.readable(C["primary"], C["bg_input"], widget=self),
                                   font=("Segoe UI", 10, "bold"))
        self.objects.tag_configure("page", foreground=ui_theme.readable(C["accent"], C["bg_input"], widget=self),
                                   font=("Segoe UI", 10, "italic"))
        self.objects.tag_configure("container", font=("Segoe UI", 10, "bold"))
        self.objects.tag_configure("folder", foreground=C["text"], font=("Segoe UI", 10, "bold"))
        self.objects.bind("<Double-1>", lambda e: self.edit_object())
        self._drag_source(self.objects, lambda: ("object", self._sel_object()), "➕ Obiect in rutina")
        self.objects.bind("<Button-3>", self._object_menu)
        row = tk.Frame(host, bg=C["bg_main"])
        row.pack(fill="x", padx=4, pady=4)
        for text, cmd, tip in [("Test", self.test_object, "Testeaza obiectul pe pagina din browser: cate elemente gaseste "
                                                       "fiecare locator; il marcheaza pe ecran"),
                               ("➕ Pas", self.object_to_step, "Adauga obiectul in rutina curenta (pas Click)"),
                               ("Editeaza", self.edit_object, "Editeaza: nume, tip, site, pagina, container, locatori"),
                               ("＋ Nou", self.new_object, "Obiect nou, cu locatori scrisi de mana"),
                               ("🗑", self.delete_object, "Sterge obiectul din biblioteca"),
                               ("🌐 Site-uri", self.edit_sites, "Site-uri si link-urile lor (sisteme similare: test / productie)")]:
            self._btn(row, text, cmd, tip=tip).pack(side="left", padx=1)
        hint = tk.Label(host, text="Obiecte noi: Scaneaza site, Captura 3 s, Spy (Web) sau Inregistreaza Web. "
                                   "Click dreapta pe obiect: testeaza, adauga in rutina, muta in container, copiaza pentru alt site.",
                        bg=C["bg_main"], fg=C["text_dim"], font=("Segoe UI", 9), justify="left", wraplength=220)
        hint.pack(anchor="w", padx=6, pady=(0, 6))
        host.bind("<Configure>", lambda e: hint.configure(wraplength=max(120, e.width - 20)), add="+")

    # =========================================================================
    # v4.12: 📋 tab-ul Rutine — rutinele salvate, de adaugat ca pas sau ca pasi
    # =========================================================================
    def _build_routines_tab(self, host):
        C = self.C
        head = tk.Frame(host, bg=C["bg_card"])
        head.pack(fill="x", padx=4, pady=(4, 2))
        self._rt_folder = tk.Label(head, text="", bg=C["bg_card"], fg=C["text"], font=("Segoe UI", 10, "bold"),
                                   anchor="w", justify="left", wraplength=230)
        self._rt_folder.pack(fill="x", padx=6, pady=(3, 1))
        ui_theme.autowrap(self._rt_folder, margin=12)
        hr = tk.Frame(head, bg=C["bg_card"])
        hr.pack(fill="x", padx=2, pady=(0, 3))
        self._btn(hr, "📁 Folder", self.choose_routines_folder,
                  tip="Alege folderul cu rutinele (ca in 📂 Manager rutine)").pack(side="left", padx=1)
        self._btn(hr, "↻", self.refresh_routines, tip="Citeste din nou folderul").pack(side="left", padx=1)
        self._rt_filter = tk.StringVar()
        e = tk.Entry(host, textvariable=self._rt_filter, bg=C["bg_input"], fg=C["text"], relief="flat",
                     insertbackground=C["text"], font=("Segoe UI", 10))
        e.pack(fill="x", padx=4, pady=(2, 2), ipady=2)
        ToolTip(e, "Cauta dupa nume, descriere sau folder")
        self._rt_filter.trace_add("write", lambda *a: self.refresh_routines_view())
        box = tk.Frame(host, bg=C["bg_main"])
        box.pack(fill="both", expand=True, padx=4)
        self.routines_tree = ttk.Treeview(box, columns=("pasi",), show="tree headings", style="Studio.Treeview",
                                          selectmode="browse")
        self.routines_tree.heading("#0", text="Rutina", anchor="w")
        self.routines_tree.heading("pasi", text="Pasi", anchor="w")
        self.routines_tree.column("#0", width=190)
        self.routines_tree.column("pasi", width=48, stretch=False)
        vsb = ttk.Scrollbar(box, orient="vertical", command=self.routines_tree.yview)
        self.routines_tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        self.routines_tree.pack(fill="both", expand=True)
        self.routines_tree.tag_configure("dir", foreground=ui_theme.readable(C["accent"], C["bg_input"], widget=self),
                                         font=("Segoe UI", 10, "bold"))
        self.routines_tree.tag_configure("bad", foreground=C["danger"] if "danger" in C else "#FF6B6B")
        self.routines_tree.bind("<Double-1>", lambda e: self.add_routine_step())
        self._drag_source(self.routines_tree, lambda: ("routine", self._sel_routine_entry()), "➕ Rutina ca pas")
        self.routines_tree.bind("<<TreeviewSelect>>", lambda e: self._routine_detail())
        self.routines_tree.bind("<Button-3>", self._routine_menu)
        sbox = tk.Frame(host, bg=C["bg_main"])
        sbox.pack(fill="x", padx=4, pady=(2, 0))
        tk.Label(sbox, text="Pasii rutinei alese (doar citire)", bg=C["bg_main"], fg=C["text_dim"],
                 font=("Segoe UI", 9, "bold"), anchor="w").pack(fill="x", padx=2)
        self.routine_steps_tree = self._steps_preview(sbox, 7)
        self._rt_info = tk.Label(host, text="", bg=C["bg_main"], fg=C["text_dim"], font=("Segoe UI", 9), anchor="w",
                                 justify="left", wraplength=230)
        self._rt_info.pack(fill="x", padx=6)
        row = tk.Frame(host, bg=C["bg_main"])
        row.pack(fill="x", padx=4, pady=4)
        for text, cmd, tip in [("➕ Ca pas", self.add_routine_step,
                                "Adauga un pas „Ruleaza rutina”: ruleaza rutina salvata, cu variabilele si Excel-ul comune "
                                "(dublu-click)"),
                               ("📥 Ca pasi", self.insert_routine_steps,
                                "Copiaza pasii rutinei in rutina curenta (ii poti edita; nu mai urmaresc originalul)"),
                               ("✎ Nume", self.rename_routine_entry, "Schimba numele rutinei alese"),
                               ("📂 Deschide", self.open_selected_routine, "Deschide rutina pentru editare")]:
            self._btn(row, text, cmd, tip=tip).pack(side="left", padx=1)
        hint = tk.Label(host, text="Ai deja o rutina de cativa pasi? Adaug-o aici ca pas si pune intre ele doar pasii "
                                   "tai. „Ca pas” urmareste fisierul (o schimbi o data, merge peste tot); „Ca pasi” face o copie.",
                        bg=C["bg_main"], fg=C["text_dim"], font=("Segoe UI", 9), justify="left", wraplength=220)
        hint.pack(anchor="w", padx=6, pady=(0, 6))
        host.bind("<Configure>", lambda e: (hint.configure(wraplength=max(120, e.width - 20)),
                                            self._rt_info.configure(wraplength=max(120, e.width - 20))), add="+")
        self._rt_loaded_at = 0.0
        self._update_routines_label()

    # =========================================================================
    # v4.15: bara de activitati + panoul lateral
    # =========================================================================
    def _on_rail(self, key: Optional[str]):
        """key=None: panoul lateral se strange (click pe iconita activa); altfel se arata pagina aleasa."""
        hp = self._hpaned
        if key is None:
            if self._side_shown:
                self._save_layout()
                hp.forget(self._side)
                self._side_shown = False
                self.after(30, self._apply_layout)
            ui_theme.save(side_collapsed=True)
            return
        for k, page in self._side_pages.items():
            if k != key:
                page.pack_forget()
        self._side_pages[key].pack(fill="both", expand=True)
        if not self._side_shown:
            hp.insert(0, self._side, weight=1)
            self._side_shown = True
            self.after(30, self._apply_layout)
        if key == "routines" and time.time() - self._rt_loaded_at > 30:
            self.refresh_routines()
        elif key == "films" and time.time() - self._films.loaded_at > 30:
            self._films.refresh()
        ui_theme.save(side_panel=key, side_collapsed=False)

    def _on_rail_action(self, key: str):
        if key == "settings":
            self.show_settings()
        elif key == "guide":
            self.show_guide()
        elif key == "import":
            self.show_import()

    # =========================================================================
    # v4.16: 📥 Import AI — pasi scrisi de un AI (dintr-un document Word) -> rutina
    # =========================================================================
    def show_import(self):
        w = getattr(self, "_import_win", None)
        if w is not None and w.winfo_exists():
            w.deiconify()
            w.lift()
            return
        from import_ui import ImportDialog
        self._import_win = ImportDialog(self)

    def open_imported(self, routine: Routine, new_objects: List[UiObject]) -> bool:
        """Rutina importata intr-un tab nou (nesalvata); obiectele noi intra in biblioteca curenta."""
        if self._busy_block():
            return False
        added = 0
        for o in new_objects:
            if any(x is o for x in self.repo.objects) or self.repo.find(o.name) is not None:
                continue
            if o.context:
                self.repo.classify(o)
            self.repo.objects.append(o)
            added += 1
        if added:
            self.save_repository()
            self.refresh_objects()
        self._new_doc_slot()
        routine.repository_path = "" if self._is_default_library() else self.repo_path
        self.routine = routine
        self.routine_path = None
        self.dirty = True
        self.rebuild_tree()
        self.show_routine_settings()
        self._update_title()
        self.set_status(tr_template("📥 Rutina \"{0}\" importata: {1} pasi, {2} obiecte noi. Verifica obiectele cu 🧪 Test, "
                           "apoi salveaz-o (💾).").format(routine.name, sum(1 for _ in routine.all_nodes()), added))
        if added:
            self.after(200, self._offer_complete)
        return True

    # v4.16.3: 🎯 Completeaza obiectele — dupa import, obiectele se verifica / marcheaza pe pagina reala
    def _offer_complete(self):
        a = choice_dialog(self, "🎯 Completeaza obiectele",
                          "Obiectele noi au doar locatoare deduse din text. Le verifici acum pe pagina reala "
                          "(si le marchezi cu click pe cele negasite)?",
                          ["🎯 Acum", "Mai tarziu"], C=self.C)
        if a.startswith("🎯"):
            self.show_complete_objects()

    def show_complete_objects(self, objects: Optional[List[UiObject]] = None):
        from complete_ui import CompleteObjectsDialog, objects_of_routine
        objs = objects if objects is not None else objects_of_routine(self.routine, self.repo)
        if not objs:
            messagebox.showinfo("🎯 Completeaza obiectele", "Rutina deschisa nu foloseste niciun obiect din biblioteca.",
                                parent=self)
            return
        w = getattr(self, "_complete_win", None)
        if w is not None and w.winfo_exists():
            w.destroy()
        self._complete_win = CompleteObjectsDialog(self, objs)

    def show_side(self, key: str):
        """Deschide o pagina din panoul lateral (si din cod: ex. Biblioteca dupa o captura)."""
        self._rail.select(key)

    def _restore_side(self):
        a = ui_theme.load()
        key = str(a.get("side_panel") or "steps")
        if key not in self._side_pages:
            key = "steps"
        self._rail.select(key)
        if a.get("side_collapsed"):
            self._rail.collapsed = True
            self._rail._paint()
            self._on_rail(None)

    def open_path(self, path: str):
        """Deschide un fisier / folder cu aplicatia din Windows."""
        try:
            os.startfile(path)  # type: ignore[attr-defined]
        except AttributeError:
            subprocess.Popen(["xdg-open", path])
        except OSError as ex:
            messagebox.showerror("Studio RPR", str(ex), parent=self)

    # =========================================================================
    # v4.15: centrul — pasi (lista) / flux / ecranul Excel
    # =========================================================================
    def _paint_view_btns(self):
        C = self.C
        for k, b in self._view_btns.items():
            on = k == self._view
            bg = C["primary"] if on else C["bg_input"]
            b.configure(bg=bg, fg=ui_theme.text_on(bg, self) if on else C["text"])

    def show_center(self, view: str, select: Optional[str] = None):
        if view not in self._center_views:
            return
        if view != self._view:
            self._center_views[self._view].pack_forget()
            self._view = view
            self._center_views[view].pack(fill="both", expand=True)
            self._paint_view_btns()
        if view == "steps":
            if not self._edit_bar.winfo_ismapped():
                self._edit_bar.pack(side="top", fill="x", pady=(2, 4), before=self._center_views["steps"].master)
        else:
            self._edit_bar.pack_forget()
        self._refresh_center()
        if select:
            self.select_node(select)

    def _flows(self) -> list:
        """Fluxurile vizibile: cel din centru (daca e ales) si fereastra separata (v4.21), daca e deschisa."""
        out = [self._flow] if getattr(self, "_view", "steps") == "flow" else []
        win = getattr(self, "_flow_win", None)
        if win is not None and win.winfo_exists():
            out.append(win.view)
        return out

    def _refresh_center(self):
        view = getattr(self, "_view", "steps")
        if view == "excel":
            self._bind_excel()
        sel = self.tree.selection()
        for fv in self._flows():
            fv.refresh()
            if sel and sel[0] in fv.cards:
                fv.select(sel[0])

    def first_for_each(self, routine: Optional[Routine] = None) -> Optional[ForEachRowNode]:
        for n in (routine or self.routine).all_nodes():
            if isinstance(n, ForEachRowNode) and n.enabled:
                return n
        return None

    def _bind_excel(self):
        f = self.first_for_each()
        path = ""
        if f is not None:
            from rpr.variables import VariableStore
            vs = VariableStore()
            for k, v in self.routine.variables.items():
                vs.set(k, v)
            path = vs.resolve(f.file_path).strip().strip('"')
        self._excel.bind_node(f, path)

    def select_node(self, node_id: str):
        if self.tree.exists(node_id):
            self.tree.see(node_id)
            self.tree.selection_set(node_id)
            self.tree.focus(node_id)

    def _timeline_pick(self, node_id: str):
        self.select_node(node_id)
        for fv in self._flows():
            fv.select(node_id)

    def rerun_excel_row(self, f: ForEachRowNode, row: int):
        """Ruleaza din nou doar randul ales: o copie a rutinei, cu bucla Excel limitata la acel rand."""
        if self.busy:
            return
        r = copy.deepcopy(self.routine)
        target = next((n for n in r.all_nodes() if n.id == f.id), None)
        if target is None:
            return
        if not messagebox.askyesno("Reia randul", f"Rulez din nou randul {row}?\n"
                                                  "Pasii de dinaintea buclei Excel (ex. deschiderea browserului) "
                                                  "ruleaza si ei.", parent=self):
            return
        target.start_row = target.end_row = row
        target.skip_completed_rows = False
        self.run(routine=r)

    # =========================================================================
    # v4.15: mai multe rutine deschise (tab-uri)
    # =========================================================================
    def _store_doc(self):
        d = {"routine": self.routine, "path": self.routine_path, "dirty": self.dirty}
        if not self._docs:
            self._docs.append(d)
            self._doc_i = 0
        else:
            self._docs[self._doc_i] = d

    def _render_tabs(self):
        docs = [(d["routine"].name, d["dirty"], d["path"] or "") for d in self._docs]
        sig = (tuple(docs), self._doc_i, self._doc_tabs.winfo_width() // 80)
        if sig == self._tabs_sig:
            return
        self._tabs_sig = sig
        self._doc_tabs.render(docs, self._doc_i)

    def _pristine(self) -> bool:
        return not self.dirty and not self.routine_path and not self.routine.steps

    def _new_doc_slot(self):
        """Tab-ul in care intra o rutina noua / deschisa: cel curent daca e gol, altfel unul nou."""
        if self._docs and self._pristine():
            return
        if self._docs:
            self._store_doc()
        self._docs.append({"routine": Routine(), "path": None, "dirty": False})
        self._doc_i = len(self._docs) - 1

    def _busy_block(self) -> bool:
        if self.busy:
            messagebox.showinfo("Studio RPR", "Rutina ruleaza. Asteapta sa se termine (sau apasa ⏹ Stop), apoi "
                                              "schimba rutina.", parent=self)
            return True
        return False

    def _activate_doc(self, i: int):
        d = self._docs[i]
        self._doc_i = i
        self.routine, self.routine_path, self.dirty = d["routine"], d["path"], d["dirty"]
        self._load_routine_library(self.routine)
        self.rebuild_tree()
        self.show_routine_settings()
        self._update_title()

    def switch_doc(self, i: int):
        if i == self._doc_i or not 0 <= i < len(self._docs) or self._busy_block():
            return
        self._store_doc()
        self._activate_doc(i)

    def close_doc(self, i: int):
        if not 0 <= i < len(self._docs) or self._busy_block():
            return
        if i != self._doc_i:
            self.switch_doc(i)
        if not self._confirm_current():
            return
        del self._docs[self._doc_i]
        if not self._docs:
            self.new_routine(ask=False)
            return
        self._activate_doc(min(self._doc_i, len(self._docs) - 1))

    def next_doc(self, step: int = 1):
        if len(self._docs) > 1:
            self.switch_doc((self._doc_i + step) % len(self._docs))

    def _update_routines_label(self):
        folder = self.studio_settings.effective_routines_folder()
        self._rt_folder.configure(text=f"📋 {os.path.basename(folder.rstrip(chr(92) + '/')) or folder}")
        ToolTip(self._rt_folder, folder)

    def choose_routines_folder(self):
        d = filedialog.askdirectory(parent=self, title="Folderul cu rutinele",
                                    initialdir=self.studio_settings.effective_routines_folder())
        if not d:
            return
        self.studio_settings.routines_folder = os.path.normpath(d)
        self.studio_settings.save()
        self._update_routines_label()
        self.refresh_routines()

    def refresh_routines(self):
        """Citeste folderul rutinelor pe un fir separat (aplicatia ramane fluida), apoi reface lista."""
        from rpr.batch import shared_library
        folder = self.studio_settings.effective_routines_folder()
        self._update_routines_label()

        def work():
            try:
                shared_library().scan(folder)
            except Exception:  # noqa: BLE001
                pass
            self._rt_loaded_at = time.time()
            self.post("routines_ready", None)
        threading.Thread(target=work, daemon=True, name="RoutinesScan").start()

    def refresh_routines_view(self):
        if not hasattr(self, "routines_tree"):
            return
        from rpr.batch import shared_library
        lib = shared_library()
        flt = self._rt_filter.get().strip().lower()
        tree = self.routines_tree
        open_state = {i: tree.item(i, "open") for i in self._all_tree_iids(tree)}
        sel = tree.selection()
        tree.delete(*tree.get_children())
        base = (lib.folder or "").rstrip("\\/")
        n = 0
        for r in sorted(lib.routines, key=lambda x: (os.path.dirname(x.path).lower(), x.name.lower())):
            rel = os.path.relpath(os.path.dirname(r.path), base) if base else ""
            rel = "" if rel in (".", "") else rel.replace("\\", "/")
            if flt and flt not in f"{r.name} {r.description} {rel}".lower():
                continue
            parent = ""
            path_so_far = ""
            for part in [x for x in rel.split("/") if x]:
                path_so_far += "/" + part
                did = "d:" + path_so_far
                if not tree.exists(did):
                    tree.insert(parent, "end", iid=did, text=f"📁 {part}", open=open_state.get(did, True), tags=("dir",))
                parent = did
            tree.insert(parent, "end", iid="r:" + r.path, text=("⚠ " if r.error else "📋 ") + r.name,
                        values=("" if r.error else str(r.steps),), tags=("bad",) if r.error else ())
            n += 1
        for i in sel:
            if tree.exists(i):
                tree.selection_set(i)
        if not n:
            tree.insert("", "end", iid="none", text="(nicio rutina in acest folder)" if not flt else "(nimic gasit)")
        self._routine_detail()

    @staticmethod
    def _all_tree_iids(tree):
        out, stack = [], list(tree.get_children())
        while stack:
            i = stack.pop()
            out.append(i)
            stack.extend(tree.get_children(i))
        return out

    def _sel_routine_entry(self):
        sel = self.routines_tree.selection()
        if not sel or not sel[0].startswith("r:"):
            return None
        from rpr.batch import shared_library
        return shared_library().find(sel[0][2:])

    def _steps_preview(self, host, height):
        """Arbore de citire cu pasii unei rutine (structura Daca / bucle pastrata)."""
        box = tk.Frame(host, bg=self.C["bg_main"])
        box.pack(fill="x")
        tv = ttk.Treeview(box, show="tree", style="Studio.Treeview", selectmode="none", height=height)
        vsb = ttk.Scrollbar(box, orient="vertical", command=tv.yview)
        tv.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        tv.pack(fill="x", expand=True)
        tv.tag_configure("disabled", foreground=self.C["text_dim"])
        tv.tag_configure("branch", foreground=ui_theme.readable(self.C["accent"], self.C["bg_input"], widget=self))
        return tv

    def _fill_steps_preview(self, tv, path: str):
        tv.delete(*tv.get_children())
        if not path or not os.path.isfile(path):
            return
        try:
            sub = RoutineStore.load(path, self.repo)
        except Exception as ex:  # noqa: BLE001
            tv.insert("", "end", text=f"⚠ {ex}")
            return

        def add(node, parent):
            iid = tv.insert(parent, "end", text=f"{icon_for(node)}  {node.title}", open=True,
                            tags=() if node.enabled else ("disabled",))
            br = node.branches()
            for name, lst in br:
                par = iid
                if len(br) > 1:
                    par = tv.insert(iid, "end", text=f"▸ {tr(name)}", open=True, tags=("branch",))
                for ch in lst:
                    add(ch, par)
        for n in sub.steps:
            add(n, "")
        if not sub.steps:
            tv.insert("", "end", text="(fara pasi)")

    def _routine_detail(self):
        e = self._sel_routine_entry()
        if hasattr(self, "routine_steps_tree"):
            self._fill_steps_preview(self.routine_steps_tree, e.path if e is not None and not e.error else "")
        if e is None:
            self._rt_info.configure(text="")
            return
        t = e.error and f"⚠ {e.error}" or (f"{e.steps} pasi · {e.modified:%d.%m.%Y %H:%M}"
                                          + (f"\n{e.description}" if e.description else ""))
        self._rt_info.configure(text=t)

    def _routine_menu(self, ev):
        iid = self.routines_tree.identify_row(ev.y)
        if not iid or not iid.startswith("r:"):
            return
        self.routines_tree.selection_set(iid)
        C = self.C
        m = tk.Menu(self, tearoff=0, bg=C["bg_card"], fg=C["text"], activebackground=C["primary"])
        m.add_command(label="➕ Adauga ca pas („Ruleaza rutina”)", command=self.add_routine_step)
        m.add_command(label="📥 Insereaza ca pasi (copie)", command=self.insert_routine_steps)
        m.add_command(label="✎ Redenumeste...", command=self.rename_routine_entry)
        m.add_separator()
        m.add_command(label="📂 Deschide pentru editare", command=self.open_selected_routine)
        m.tk_popup(ev.x_root, ev.y_root)

    def _is_current_routine(self, path: str) -> bool:
        try:
            return bool(self.routine_path) and os.path.samefile(self.routine_path, path)
        except OSError:
            return False

    def add_routine_step(self, entry=None, at=None):
        e = entry or self._sel_routine_entry()
        if e is None:
            self.set_status("Alege o rutina din lista.")
            return
        if e.error:
            messagebox.showerror("Rutine", f"Rutina nu poate fi citita:\n{e.error}", parent=self)
            return
        if self._is_current_routine(e.path):
            messagebox.showwarning("Rutine", "Aceasta e rutina deschisa acum: nu se poate apela pe ea insasi.", parent=self)
            return
        self._insert_at = at
        self.insert_node(RunRoutineNode(path=e.path, name=e.name))
        self.set_status(f"Pas adaugat: ruleaza rutina [{e.name}] ({e.steps} pasi).")

    def _load_for_copy(self, path: str):
        try:
            return RoutineStore.load(path, self.repo)
        except Exception as ex:  # noqa: BLE001
            messagebox.showerror("Rutine", f"Rutina nu poate fi citita:\n{ex}", parent=self)
            return None

    def _missing_objects(self, r: Routine) -> List[str]:
        return sorted({n for n in r.referenced_objects() if self.repo.find(n) is None}, key=str.lower)

    def insert_routine_steps(self):
        e = self._sel_routine_entry()
        if e is None:
            self.set_status("Alege o rutina din lista.")
            return
        sub = self._load_for_copy(e.path)
        if sub is None:
            return
        steps = rpr_sub.steps_copy(sub)
        if not steps:
            self.set_status(f"Rutina [{e.name}] nu are pasi.")
            return
        for node in steps:
            self.insert_node(node)
        added = rpr_sub.merge_variables(self.routine, sub)
        miss = self._missing_objects(sub)
        msg = f"Am copiat {len(steps)} pasi din [{e.name}]" + (f" si {added} variabile" if added else "") + "."
        if miss:
            msg += f" ⚠ Obiecte lipsa din biblioteca curenta: {', '.join(miss[:5])}."
        self.set_status(msg)

    def expand_run_routine(self, node: RunRoutineNode):
        """Transforma un pas „Ruleaza rutina” in pasii rutinei (copie)."""
        path = rpr_sub.resolve_path(node.path)
        if not path or not os.path.isfile(path):
            messagebox.showwarning("Rutine", "Fisierul rutinei nu exista.", parent=self)
            return
        sub = self._load_for_copy(path)
        owner = self.routine.find_parent_list(node)
        if sub is None or owner is None:
            return
        steps = rpr_sub.steps_copy(sub)
        i = next(k for k, x in enumerate(owner) if x is node)
        owner[i:i + 1] = steps
        rpr_sub.merge_variables(self.routine, sub)
        self.mark_dirty()
        self.rebuild_tree(steps[0] if steps else None)
        self.set_status(f"Pasul a fost inlocuit cu cei {len(steps)} pasi ai rutinei [{sub.name}].")

    def rename_routine_entry(self):
        """Schimba numele afisat al rutinei alese direct in fisier (fara s-o deschizi)."""
        e = self._sel_routine_entry()
        if e is None:
            self.set_status("Alege o rutina din lista.")
            return
        if self._is_current_routine(e.path):
            messagebox.showinfo("Rutine", "Rutina e deschisa acum: schimba numele din ⚙ Rutina (campul Nume) si salveaz-o.",
                                parent=self)
            return
        sub = self._load_for_copy(e.path)
        if sub is None:
            return
        new = input_dialog(self, "✎ Redenumeste rutina", "Numele rutinei:", sub.name, self.C)
        new = (new or "").strip()
        if not new or new == sub.name:
            return
        sub.name = new
        try:
            RoutineStore.save(sub, e.path)
        except Exception as ex:  # noqa: BLE001
            messagebox.showerror("Rutine", f"Nu am putut salva:\n{ex}", parent=self)
            return
        self.set_status(f"Rutina a fost redenumita: [{new}].")
        self.refresh_routines()

    def open_selected_routine(self):
        e = self._sel_routine_entry()
        if e is not None:
            self.open_routine(e.path)

    # =========================================================================
    # Rutina: nou / deschide / salveaza
    # =========================================================================
    def set_status(self, text: str):
        self._on_status(text)

    def mark_dirty(self):
        self.dirty = True
        self._update_title()

    def _update_title(self):
        if not hasattr(self, "_doc_tabs"):
            return
        self._store_doc()      # v4.15: numele si "nesalvat" apar pe tab-ul rutinei
        self._render_tabs()

    def _confirm_current(self) -> bool:
        if not self.dirty:
            return True
        ans = messagebox.askyesnocancel("Studio RPR", f"Rutina \"{self.routine.name}\" are modificari nesalvate.\n"
                                                       "Le salvezi?", parent=self)
        if ans is None:
            return False
        return self.save_routine() if ans else True

    def confirm_discard(self) -> bool:
        """La inchiderea aplicatiei: fiecare tab cu modificari nesalvate e intrebat."""
        self._store_doc()
        for i in range(len(self._docs)):
            if not self._docs[i]["dirty"]:
                continue
            if i != self._doc_i:
                self._store_doc()
                self._activate_doc(i)
            if not self._confirm_current():
                return False
        return True

    def new_routine(self, ask=True):
        """v4.15: rutina noua intr-un tab nou (tab-ul curent ramane deschis cu rutina lui)."""
        if ask and self._busy_block():
            return
        self._new_doc_slot()
        self.routine = Routine(name="Rutina noua")
        self.routine.repository_path = "" if self._is_default_library() else self.repo_path
        self.routine_path = None
        self.dirty = False
        self.rebuild_tree()
        self.show_routine_settings()
        self._update_title()

    def _find_doc(self, path: str) -> int:
        key = os.path.normcase(os.path.abspath(path))
        self._store_doc()
        for i, d in enumerate(self._docs):
            if d["path"] and os.path.normcase(os.path.abspath(d["path"])) == key:
                return i
        return -1

    def open_routine(self, path: Optional[str] = None):
        if self._busy_block():
            return
        path = path or filedialog.askopenfilename(
            parent=self, title="Deschide rutina", initialdir=RprPaths.routines(),
            filetypes=[("Rutine AutoPilot", "*.rpr.json *.json"), ("Toate fisierele", "*.*")])
        if not path:
            return
        i = self._find_doc(path)
        if i >= 0:                 # v4.15: rutina e deja deschisa intr-un tab: doar il aratam
            self.switch_doc(i)
            return
        try:
            r = RoutineStore.load(path, self.repo)
        except Exception as ex:  # noqa: BLE001
            messagebox.showerror("Studio RPR", f"Rutina nu poate fi deschisa:\n{ex}", parent=self)
            return
        self._new_doc_slot()
        self.routine = r
        self._load_routine_library(r)
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
            # biblioteca folosita de rutina (gol = cea implicita, ca pana acum)
            self.routine.repository_path = "" if self._is_default_library() else self.repo_path
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
            real = RepositoryStore.resolve(path)
            self.repo = RepositoryStore.load(real)
            self.repo_path = real
        except Exception as ex:  # noqa: BLE001
            messagebox.showerror("Studio RPR", f"Object Repository nu poate fi citit:\n{ex}", parent=self)
        self.refresh_objects()
        self._update_library_label()

    def save_repository(self):
        RepositoryStore.save(self.repo, self.repo_path)

    # ── v4.9: biblioteca pe aplicatie, intr-un fisier ales de tine ──
    def _is_default_library(self) -> bool:
        return os.path.normcase(os.path.abspath(self.repo_path)) == \
            os.path.normcase(os.path.abspath(RprPaths.default_repository()))

    def _load_routine_library(self, r: Routine):
        """Rutina isi aduce biblioteca; o rutina fara cale foloseste biblioteca implicita (ca inainte de 4.9)."""
        if r.repository_path.strip():
            self.load_repository(r.repository_path)
        elif not self._is_default_library():
            self.load_repository(RprPaths.default_repository())

    def _update_library_label(self):
        lbl = getattr(self, "_lib_label", None)
        if lbl is None:
            return
        if self._is_default_library():
            text = "📚 obiecte.json (implicita)"
        else:
            text = f"📚 {os.path.basename(os.path.dirname(self.repo_path))} / {os.path.basename(self.repo_path)}"
        lbl.configure(text=f"{text}  ·  {len(self.repo.objects)}")

    def _remember_library(self):
        self.studio_settings.library_path = "" if self._is_default_library() else self.repo_path
        self.studio_settings.save()
        want = "" if self._is_default_library() else self.repo_path
        if self.routine.repository_path != want:
            self.routine.repository_path = want   # rutina deschisa foloseste de acum biblioteca aleasa
            if any(True for _ in self.routine.all_nodes()):
                self.mark_dirty()

    def open_library(self):
        start = os.path.dirname(self.repo_path) if not self._is_default_library() else rpr_scan.libraries_root()
        path = filedialog.askopenfilename(parent=self, title="Deschide biblioteca de obiecte",
                                          initialdir=start if os.path.isdir(start) else RprPaths.root,
                                          filetypes=[("Biblioteca de obiecte", "*.json"), ("Toate fisierele", "*.*")])
        if not path:
            return
        try:
            self.save_repository()
        except Exception:
            pass
        self.load_repository(path)
        self._remember_library()
        self.set_status(f"Biblioteca deschisa: {self.repo_path} ({len(self.repo.objects)} obiecte)")

    def new_library(self, app_name: str = "") -> bool:
        """Biblioteca noua pentru o aplicatie: OneDrive\\AutoPilotDC\\obiecte\\<Aplicatie>\\obiecte.json."""
        name = input_dialog(self, "Biblioteca noua", "Numele aplicatiei (devine numele folderului bibliotecii):",
                            app_name, C=self.C)
        if not name or not name.strip():
            return False
        suggested = rpr_scan.suggest_library_path(name.strip())
        try:
            os.makedirs(os.path.dirname(suggested), exist_ok=True)
        except OSError:
            pass
        path = filedialog.asksaveasfilename(parent=self, title="Unde salvez biblioteca?",
                                            initialdir=os.path.dirname(suggested), initialfile=os.path.basename(suggested),
                                            defaultextension=".json", filetypes=[("Biblioteca de obiecte", "*.json")])
        if not path:
            return False
        try:
            self.save_repository()
        except Exception:
            pass
        if os.path.isfile(path):
            self.load_repository(path)
        else:
            self.repo = ObjectRepository()
            self.repo_path = path
            try:
                self.save_repository()
            except Exception as ex:  # noqa: BLE001
                messagebox.showerror("Studio RPR", f"Nu am putut salva:\n{ex}", parent=self)
                return False
            self.refresh_objects()
            self._update_library_label()
        self._remember_library()
        self.set_status(f"Biblioteca: {self.repo_path}")
        return True

    def open_library_folder(self):
        try:
            os.startfile(os.path.dirname(os.path.abspath(self.repo_path)))
        except Exception as ex:  # noqa: BLE001
            self.set_status(str(ex))

    def _ensure_app_library(self, url: str) -> bool:
        """Inainte de scanare: daca lucram in biblioteca implicita, propunem una separata pentru aplicatie."""
        if not self._is_default_library():
            return True
        app = rpr_scan.app_name_from_url(url)
        a = choice_dialog(self, "Biblioteca aplicatiei",
                          f"Obiectele s-ar salva in biblioteca implicita (obiecte.json din AppData). "
                          f"Recomandat: o biblioteca separata pentru {app}, intr-un folder ales de tine (ex. OneDrive).",
                          ["Biblioteca noua", "Biblioteca curenta", "Anuleaza"], C=self.C)
        if a == "Biblioteca noua":
            return self.new_library(app)
        return a == "Biblioteca curenta"

    # ── v4.9: scanarea site-ului si captura cu cursorul tinut 3 s ──
    def _browser_url(self) -> str:
        try:
            web = self.web()
            return web.current_url() if web.is_open else ""
        except Exception:
            return ""

    def scan_site(self):
        if self.busy:
            self.set_status("Asteapta sa se termine operatia curenta.")
            return
        if self._recording:
            self.record_web()
        cur = self._browser_url()
        url = input_dialog(self, "🔍 Scaneaza site",
                           "Adresa aplicatiei (se deschide in browserul AutoPilot). Daca browserul e deja pe pagina "
                           "dorita, lasa adresa asa cum e.", cur or "https://", C=self.C)
        if not url or not url.strip() or url.strip() == "https://":
            return
        url = url.strip()
        if not self._ensure_app_library(url):
            return
        self._open_then(url if url != cur else None, "scan")

    def hover_capture(self):
        if self.busy:
            self.set_status("Asteapta sa se termine operatia curenta.")
            return
        if self._recording:
            self.record_web()
        cur = self._browser_url()
        url = None
        if not cur:
            url = input_dialog(self, "🖐 Captura 3 s", "Browserul nu e deschis. La ce adresa sa-l deschid?",
                               "https://", C=self.C)
            if not url or not url.strip() or url.strip() == "https://":
                return
            url = url.strip()
        if not self._ensure_app_library(url or cur):
            return
        self._open_then(url, "hover")

    def _open_then(self, url: Optional[str], what: str):
        """Deschide adresa (pe un fir separat), apoi intreaba daca pagina e gata."""
        self.busy = True
        web = self.web()

        def work():
            try:
                if url:
                    web.open(url)
                self.post("scan_ready", (what, bool(url), None))
            except Exception as ex:  # noqa: BLE001
                self.post("scan_ready", (what, bool(url), str(ex)))
        self.set_status("Deschid browserul..." if url else "")
        threading.Thread(target=work, daemon=True, name="ScanOpen").start()

    def _scan_ready(self, what: str, opened: bool, error: Optional[str]):
        self.busy = False
        if error:
            messagebox.showerror("Browser", f"Browserul nu a putut deschide pagina:\n{error}", parent=self)
            return
        if opened or what == "scan":
            a = choice_dialog(self, "Pagina e gata?",
                              "Browserul e deschis. Autentifica-te si deschide pagina dorita (meniu, tab, formular), "
                              "apoi alege:",
                              ["🔍 Scaneaza automat", "🖐 Captura 3 s", "🩺 Verifica butoanele salvate", "Anuleaza"],
                              C=self.C)
            if a == "🔍 Scaneaza automat":
                what = "scan"
            elif a == "🖐 Captura 3 s":
                what = "hover"
            elif a == "🩺 Verifica butoanele salvate":
                what = "check"
            else:
                return
        if what == "scan":
            self._scan_now()
        elif what == "check":
            self._check_start(None)
        else:
            self._hover_start()

    def _scan_now(self):
        self.busy = True
        cancel = threading.Event()
        self._scan_cancel = cancel
        self._show_spy_hint("🔍 Scanez pagina: doar citesc butoanele si campurile, nu dau click.",
                            on_cancel=cancel.set)
        web = self.web()

        def work():
            try:
                self.post("scan_done", (web.scan_page(500, cancel=cancel), None))
            except Exception as ex:  # noqa: BLE001
                self.post("scan_done", ([], str(ex)))
        self.set_status("Scanez pagina...")
        threading.Thread(target=work, daemon=True, name="Scan").start()

    def _scan_done(self, objs: List[UiObject], error: Optional[str]):
        self.busy = False
        self._hide_spy_hint()
        if error:
            messagebox.showerror("Scanare", f"Scanarea nu a reusit:\n{error}", parent=self)
            return
        fresh, existing = rpr_scan.new_objects(self.repo, objs)
        if not fresh:
            msg = f"Nu am gasit obiecte noi pe pagina ({len(objs)} gasite, {existing} deja in biblioteca)."
        else:
            chosen = ScanReviewDialog(self, fresh, existing).result
            if chosen is None:
                self.set_status("Scanare anulata: nimic adaugat.")
                return
            n = rpr_scan.add_objects(self.repo, chosen)
            self.save_repository()
            self.refresh_objects()
            self._update_library_label()
            msg = f"Am adaugat {n} obiecte in biblioteca ({existing} erau deja)."
        self.set_status(msg)
        a = choice_dialog(self, "Scanare", msg + " Deschide alt meniu / alta pagina in browser si continua:",
                          ["🔍 Scaneaza din nou", "🖐 Captura 3 s", "Am terminat"], C=self.C)
        if a == "🔍 Scaneaza din nou":
            self._scan_now()
        elif a == "🖐 Captura 3 s":
            self._hover_start()

    # ── v4.10: 🩺 verificarea butoanelor salvate, fara click ──
    def check_saved(self, objs: Optional[List[UiObject]] = None):
        """Obiectele salvate mai merg pe pagina din browser? Simulare: verificarile unui click, fara click."""
        if self.busy:
            self.set_status("Asteapta sa se termine operatia curenta.")
            return
        if self._recording:
            self.record_web()
        if not self._browser_url():
            url = self._ask_url_if_closed()
            if url is False:
                return
            self._check_objs = objs
            self._open_then(url, "check")
            return
        self._check_start(objs)

    def _check_start(self, objs: Optional[List[UiObject]]):
        objs = objs if objs is not None else getattr(self, "_check_objs", None)
        self._check_objs = None
        url = self._browser_url()
        if objs is None:
            here = rpr_scan.objects_to_check(self.repo, url)
            site = rpr_scan.objects_to_check(self.repo, url, whole_site=True)
            if not site:
                messagebox.showinfo("🩺 Verifica", "Nu ai obiecte salvate pentru site-ul deschis in browser.",
                                    parent=self)
                return
            objs = here
            if len(site) > len(here):
                a = choice_dialog(self, "🩺 Verifica",
                                  f"Pe pagina deschisa ({rpr_scan.page_of_url(url)}) ai {len(here)} obiecte salvate, "
                                  f"pe tot site-ul {len(site)}. Ce verific?",
                                  [f"Pagina curenta ({len(here)})", f"Tot site-ul ({len(site)})", "Anuleaza"], C=self.C)
                if a.startswith("Tot"):
                    objs = site
                elif not a.startswith("Pagina") or not here:
                    return
        for o in objs:
            self.repo.link_parents(o)
        self.busy = True
        cancel = threading.Event()
        self._show_spy_hint("🩺 Verific butoanele salvate: simulez click-ul, fara sa apas nimic.",
                            on_cancel=cancel.set)
        web = self.web()

        def work():
            results = []
            try:
                for i, o in enumerate(objs, 1):
                    if cancel.is_set():
                        break
                    self.post("check_progress", f"🩺 Verific {i}/{len(objs)}: [{o.name}]")
                    try:
                        res = web.check_object(o)
                    except Exception as ex:  # noqa: BLE001
                        res = {"found": False, "counts": [], "error": str(ex)}
                    results.append((o, res))
                self.post("check_done", (results, url, None))
            except Exception as ex:  # noqa: BLE001
                self.post("check_done", (results, url, str(ex)))
        threading.Thread(target=work, daemon=True, name="Check").start()

    def _check_done(self, results, url: str, error: Optional[str]):
        self.busy = False
        self._hide_spy_hint()
        if error and not results:
            messagebox.showerror("🩺 Verifica", f"Verificarea nu a reusit:\n{error}", parent=self)
            return
        rows = [(o, res) + rpr_scan.diagnose(o, res, url) for o, res in results]
        n = {k: sum(1 for r in rows if r[2] == k) for k in (rpr_scan.OK, rpr_scan.WARN, rpr_scan.REMAP)}
        self.set_status(f"🩺 Verificare: {n['ok']} merg, {n['warn']} cu impedimente, {n['remap']} de recaptat.")
        dlg = getattr(self, "_check_dlg", None)
        if dlg is not None and dlg.winfo_exists():
            dlg.update_rows(rows)
        else:
            self._check_dlg = CheckResultDialog(self, rows, url)

    def recheck(self, objs: List[UiObject]):
        if objs:
            self._check_start(list(objs))

    def fix_object_locators(self, obj: UiObject, used) -> bool:
        if rpr_scan.fix_locators(obj, used):
            self.save_repository()
            self.refresh_objects()
            self.set_status(f"[{obj.name}]: locatorul care merge e acum primul.")
            return True
        return False

    def recapture(self, obj: UiObject):
        """Recapteaza elementul: click pe el in browser; numele ramane, deci rutinele merg mai departe."""
        if self.busy:
            self.set_status("Asteapta sa se termine operatia curenta.")
            return
        self.busy = True
        self._show_spy_hint(f"🎯 Recaptare [{obj.name}]: du mouse-ul peste element in browser si da CLICK.  "
                            "Esc in browser = anuleaza.")
        web = self.web()

        def work():
            try:
                new = web.capture_object("Click = captureaza · Esc = anuleaza", RprPaths.object_images())
                self.post("recapture_done", (obj, new, None))
            except Exception as ex:  # noqa: BLE001
                self.post("recapture_done", (obj, None, str(ex)))
        self.set_status(f"Recaptare [{obj.name}]: click pe element in browser. Esc = anulare.")
        threading.Thread(target=work, daemon=True, name="Recapture").start()

    def _recapture_done(self, obj: UiObject, new: Optional[UiObject], error: Optional[str]):
        self.busy = False
        self._hide_spy_hint()
        if error:
            messagebox.showerror("Recaptare", error, parent=self)
            return
        if new is None:
            self.set_status("Recaptare anulata.")
            return
        rpr_scan.apply_recapture(obj, new)
        self.save_repository()
        self.refresh_objects()
        self.set_status(f"[{obj.name}] recaptat: am pastrat numele, verific din nou...")
        self._check_start([obj])

    def _hover_start(self):
        self.busy = True
        self._hover_count = 0
        self._hover_on = True
        self._show_spy_hint("🖐 Tine cursorul 3 s pe camp / buton (contur albastru): se salveaza singur. "
                            "Click-urile merg normal. Esc in browser = gata.",
                            on_cancel=self._hover_stop, cancel_text="Am terminat")
        web = self.web()

        def work():
            try:
                web.start_hover_capture(lambda o: self.post("hover_obj", o), tr("3 s = salveaza · Esc = gata"),
                                        RprPaths.object_images())
            except Exception as ex:  # noqa: BLE001
                self.post("hover_failed", str(ex))
        self.set_status("Captura 3 s: tine cursorul pe fiecare camp / buton din browser.")
        threading.Thread(target=work, daemon=True, name="Hover").start()

    def _hover_object(self, obj: Optional[UiObject]):
        if not getattr(self, "_hover_on", False):
            return
        if obj is None:
            self._hover_finished()
            return
        self.repo.classify(obj)
        same = rpr_scan.find_existing(self.repo, obj)
        if same is not None:
            self.set_status(f"Deja in biblioteca: [{same.name}]")
            return
        if self._last_folder[1]:
            obj.folder = self._last_folder[1]   # folderul ales la ultima scanare
        self.repo.add(obj)
        self.save_repository()
        self.refresh_objects()
        self._update_library_label()
        self._hover_count += 1
        self.set_status(f"Salvat [{obj.name}] ({self._hover_count} obiecte noi).")

    def _hover_stop(self):
        web = self.web()
        threading.Thread(target=web.stop_hover_capture, daemon=True, name="HoverStop").start()
        self._hover_finished()

    def _hover_finished(self, error: Optional[str] = None):
        if not getattr(self, "_hover_on", False):
            return
        self._hover_on = False
        self.busy = False
        self._hide_spy_hint()
        if error:
            messagebox.showerror("Captura 3 s", f"Captura nu a putut porni:\n{error}", parent=self)
            return
        self.set_status(f"Captura 3 s oprita: {self._hover_count} obiecte noi in biblioteca.")

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
                           "Exemplele Web / SAP / Desktop au nevoie de aplicatia respectiva (browser, SAP GUI, Notepad).",
                 bg=C["bg_main"], fg=C["text_dim"], font=("Segoe UI", 10), justify="left").pack(anchor="w", padx=16)
        for ex in examples:
            card = tk.Frame(dlg, bg=C["bg_card"])
            card.pack(fill="x", padx=16, pady=4)
            tk.Label(card, text=ex["name"], bg=C["bg_card"], fg=C["text"], font=("Segoe UI", 10, "bold")).pack(
                anchor="w", padx=10, pady=(6, 0))
            tk.Label(card, text=ex["description"], bg=C["bg_card"], fg=C["text_dim"], font=("Segoe UI", 10),
                     wraplength=520, justify="left").pack(anchor="w", padx=10)
            self._btn(card, "Deschide", lambda p=ex["path"]: (dlg.destroy(), self.open_routine(p)),
                      color=C["primary"]).pack(anchor="e", padx=10, pady=6)
        self._btn(dlg, "📂 Folderul cu exemple", lambda: os.startfile(RprPaths.examples())).pack(anchor="w", padx=16, pady=10)

    def show_guide(self):
        if self._on_help is not None:   # v4.16: ghidul vechi era doar in romana; Instructiunile au toate limbile
            self._on_help()
            return
        C = self.C
        dlg = tk.Toplevel(self)
        dlg.title("Ghid Studio RPR")
        ui_theme.fit_window(dlg, 900, 700)
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
        if getattr(self, "_view", "steps") != "steps":
            self._refresh_center()

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
                self.tree.insert(iid, "end", iid=biid, text=f"▸ {tr(name)}", open=biid not in collapsed, tags=("branch",))
                self._items[biid] = ("branch", None, lst)
                for ch in lst:
                    self._add_tree_node(ch, lst, biid, collapsed)
        else:
            name, lst = branches[0]
            if not lst:  # ramura goala ramane selectabila
                biid = f"{iid}#{name}"
                self.tree.insert(iid, "end", iid=biid, text=f"▸ {tr(name)} " + tr("(gol)"), tags=("branch",))
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

    def insert_recorded(self, nodes: List[RprNode], title: str) -> Optional[GroupNode]:
        """v4.16: pasii inregistrati pe ecran (mouse / tastatura) intra intr-un grup, dupa pasul selectat."""
        if not nodes:
            return None
        group = GroupNode(label=title, body=list(nodes))
        self.insert_node(group)
        self.editor.show(group)
        return group

    def insert_node(self, node: RprNode):
        at, self._insert_at = getattr(self, "_insert_at", None), None
        if at is not None:          # v4.14: locul ales prin drag and drop
            target, index = at
            target.insert(max(0, min(index, len(target))), node)
            self.mark_dirty()
            self.rebuild_tree(node)
            return
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
        repo = self.repo
        changed = False
        for o in repo.objects:   # obiectele vechi (fara site / pagina / tip) se clasifica din link-ul capturarii
            if (o.context and (not o.site or not o.page)) or not o.object_type:
                before = (o.site, o.page, o.object_type)
                repo.classify(o)
                changed |= before != (o.site, o.page, o.object_type)
        if changed:
            self.save_repository()

        flt = self._obj_filter.get().strip().lower()
        url = ""
        if self._obj_only_page.get():
            try:
                url = self.web().current_url() if self.web().is_open else ""
            except Exception:
                url = ""

        def matches(o: UiObject) -> bool:
            if url and not repo.valid_on(o, url):
                return False
            if not flt:
                return True
            hay = " ".join([o.name, o.object_type, o.site, o.page, o.folder, o.description, " ".join(o.tags)]).lower()
            return flt in hay

        # vizibile = potrivirile + containerele lor (ca arborele sa ramana intreg)
        visible = set()
        for o in repo.objects:
            if matches(o):
                visible.add(o.name.lower())
                for p in repo.parent_chain(o):
                    visible.add(p.name.lower())

        open_state = {iid: self.objects.item(iid, "open") for iid in self._all_object_iids()}
        sel = self.objects.selection()
        self.objects.delete(*self.objects.get_children())

        site_of = self._site_of

        tree: Dict[str, Dict[str, List[UiObject]]] = {}
        names = {o.name.lower() for o in repo.objects}
        for o in sorted(repo.objects, key=lambda x: x.name.lower()):
            if o.name.lower() not in visible:
                continue
            if o.parent and o.parent.lower() in names:
                continue   # apare sub containerul lui
            tree.setdefault(site_of(o), {}).setdefault(o.page or "(fara pagina)", []).append(o)

        def add_obj(parent_iid, o):
            iid = "obj:" + o.name
            n = sum(1 for l in o.active_locators)
            self.objects.insert(parent_iid, "end", iid=iid, text=("▣ " if o.is_container else "") + o.name,
                                values=(o.object_type or "",), open=open_state.get(iid, True),
                                tags=("container",) if o.is_container else ())
            for ch in sorted(repo.children_of(o.name), key=lambda x: x.name.lower()):
                if ch.name.lower() in visible:
                    add_obj(iid, ch)

        def add_group(parent_iid, objs, depth, site, page):
            """Foldere (v4.11) in ordine alfabetica, apoi obiectele fara folder; subfoldere recursiv."""
            subs: Dict[str, List[UiObject]] = {}
            direct = []
            for o in objs:
                fp = rpr_scan.folder_parts(o)
                if len(fp) > depth:
                    subs.setdefault(fp[depth].lower(), []).append(o)
                else:
                    direct.append(o)
            for key in sorted(subs):
                grp = subs[key]
                parts = rpr_scan.folder_parts(grp[0])[:depth + 1]
                fid = f"folder:{site}|{page}|{'/'.join(parts)}"
                self.objects.insert(parent_iid, "end", iid=fid, text=f"📁 {parts[-1]}", values=(f"{len(grp)} ob.",),
                                    open=open_state.get(fid, True), tags=("folder",))
                add_group(fid, grp, depth + 1, site, page)
            for o in direct:
                add_obj(parent_iid, o)

        for site in sorted(tree, key=str.lower):
            sid = "site:" + site
            n = sum(len(v) for v in tree[site].values())
            self.objects.insert("", "end", iid=sid, text=f"🌐 {tr(site)}", values=(f"{n} ob.",), open=open_state.get(sid, True),
                                tags=("site",))
            for page in sorted(tree[site], key=str.lower):
                pid = f"page:{site}|{page}"
                self.objects.insert(sid, "end", iid=pid, text=f"📄 {tr(page)}", open=open_state.get(pid, True), tags=("page",))
                add_group(pid, tree[site][page], 0, site, page)
        for iid in sel:
            if self.objects.exists(iid):
                self.objects.selection_set(iid)
                self.objects.see(iid)

    @staticmethod
    def _site_of(o: UiObject) -> str:
        if o.technology in (UiTechnology.Web, UiTechnology.WebSelenium):
            return o.site or "(fara site)"
        return o.site or {UiTechnology.Sap: "SAP GUI", UiTechnology.Desktop: "Aplicatii desktop"}.get(o.technology, "Altele")

    def _all_object_iids(self):
        out, stack = [], list(self.objects.get_children())
        while stack:
            iid = stack.pop()
            out.append(iid)
            stack.extend(self.objects.get_children(iid))
        return out

    def _sel_object(self) -> Optional[UiObject]:
        sel = self.objects.selection()
        if not sel or not sel[0].startswith("obj:"):
            return None
        return self.repo.find(sel[0][4:])

    def _object_menu(self, e):
        iid = self.objects.identify_row(e.y)
        if iid and iid.startswith("folder:"):
            return self._folder_menu(e, iid)
        if iid and iid.startswith(("page:", "site:")):
            return self._group_menu(e, iid)
        if not iid or not iid.startswith("obj:"):
            return
        self.objects.selection_set(iid)
        obj = self._sel_object()
        C = self.C
        m = tk.Menu(self, tearoff=0, bg=C["bg_card"], fg=C["text"], activebackground=C["primary"])
        m.add_command(label="🧪 Testeaza pe pagina din browser", command=self.test_object)
        m.add_command(label="👁 Marcheaza in browser (8 s)", command=self.show_object)
        if rpr_scan.is_web(obj):
            m.add_command(label="🩺 Verifica fara click (merge? impedimente?)", command=lambda: self.check_saved([obj]))
        m.add_separator()
        m.add_command(label="➕ Adauga in rutina: Click", command=lambda: self._obj_step(RprAction.Click))
        m.add_command(label="➕ Adauga in rutina: Scrie text", command=lambda: self._obj_step(RprAction.TypeText))
        m.add_command(label="➕ Adauga in rutina: Citeste textul", command=lambda: self._obj_step(RprAction.ReadText))
        m.add_command(label="➕ Adauga in rutina: Alege din lista", command=lambda: self._obj_step(RprAction.SelectOption))
        m.add_command(label="➕ Adauga conditie: Daca obiectul exista", command=self._obj_if_exists)
        m.add_separator()
        m.add_command(label="✎ Editeaza", command=self.edit_object)
        m.add_command(label="▣ Muta in container...", command=self.move_to_container)
        m.add_command(label="📁 Muta in folder...", command=self.move_to_folder)
        m.add_command(label="⧉ Copiaza pentru alt site / alta pagina...", command=self.copy_object)
        m.add_separator()
        m.add_command(label="🗑 Sterge", command=self.delete_object)
        m.tk_popup(e.x_root, e.y_root)

    # ── v4.11: foldere in biblioteca ──
    def _folder_objects(self, iid: str) -> List[UiObject]:
        site, page, path = iid[len("folder:"):].split("|", 2)
        return [o for o in self.repo.objects if self._site_of(o) == site and (o.page or "(fara pagina)") == page
                and rpr_scan.in_folder(o, path)]

    def _folder_menu(self, e, iid: str):
        self.objects.selection_set(iid)
        C = self.C
        m = tk.Menu(self, tearoff=0, bg=C["bg_card"], fg=C["text"], activebackground=C["primary"])
        m.add_command(label="✎ Redenumeste folderul...", command=lambda: self.rename_folder(iid))
        if any(rpr_scan.is_web(o) for o in self._folder_objects(iid)):
            m.add_command(label="🩺 Verifica obiectele folderului", command=lambda: self.check_saved(
                [o for o in self._folder_objects(iid) if rpr_scan.is_web(o)]))
        m.tk_popup(e.x_root, e.y_root)

    def _group_objects(self, iid: str) -> List[UiObject]:
        """Obiectele de sub un rand de site / pagina din tree."""
        if iid.startswith("site:"):
            site = iid[len("site:"):]
            return [o for o in self.repo.objects if self._site_of(o) == site]
        site, page = iid[len("page:"):].split("|", 1)
        return [o for o in self.repo.objects if self._site_of(o) == site and (o.page or "(fara pagina)") == page]

    def _group_menu(self, e, iid: str):
        self.objects.selection_set(iid)
        C = self.C
        m = tk.Menu(self, tearoff=0, bg=C["bg_card"], fg=C["text"], activebackground=C["primary"])
        what = "site-ul" if iid.startswith("site:") else "pagina"
        m.add_command(label=f"✎ Redenumeste {what}...", command=lambda: self.rename_group(iid))
        web = [o for o in self._group_objects(iid) if rpr_scan.is_web(o)]
        if web:
            m.add_command(label="🩺 Verifica obiectele de aici", command=lambda: self.check_saved(web))
        m.tk_popup(e.x_root, e.y_root)

    def rename_group(self, iid: str):
        """Redenumeste o pagina (sau un site) pentru toate obiectele de sub ea."""
        objs = self._group_objects(iid)
        is_site = iid.startswith("site:")
        old = iid[len("site:"):] if is_site else iid.split("|", 1)[1]
        if old.startswith("("):
            old = ""
        new = input_dialog(self, "Redenumeste site-ul" if is_site else "Redenumeste pagina",
                           f"Nume nou pentru {'site-ul' if is_site else 'pagina'} \"{old or '-'}\" "
                           f"({len(objs)} obiecte):", old, C=self.C)
        if new is None or not new.strip() or new.strip() == old:
            return
        new = new.strip()
        if is_site:
            n = rpr_scan.rename_site(self.repo, objs, old, new)
        else:
            n = rpr_scan.rename_page(objs, new)
        self.save_repository()
        self.refresh_objects()
        self.set_status(f"Redenumit: {n} obiecte.")

    def rename_folder(self, iid: str):
        objs = self._folder_objects(iid)
        path = iid.split("|", 2)[2]
        new = input_dialog(self, "Redenumeste folderul", f"Nume nou pentru folderul \"{path.split('/')[-1]}\":",
                           path.split("/")[-1], C=self.C)
        if not new or not new.strip():
            return
        n = rpr_scan.rename_folder(objs, path, new)
        self.save_repository()
        self.refresh_objects()
        self.set_status(f"Folder redenumit: {n} obiecte.")

    def move_to_folder(self):
        obj = self._sel_object()
        if obj is None:
            return
        existing = ", ".join(rpr_scan.all_folders(self.repo)) or "-"
        f = input_dialog(self, "Muta in folder",
                         f"Folderul lui [{obj.name}] (gol = fara folder; subfolder: Comenzi/Export).\n"
                         f"Foldere existente: {existing}", obj.folder, C=self.C)
        if f is None:
            return
        obj.folder = rpr_scan.normalize_folder(f)
        self.save_repository()
        self.refresh_objects()

    def _obj_step(self, action: RprAction, obj: Optional[UiObject] = None):
        obj = obj or self._sel_object()
        if obj is None:
            return
        node = ActionNode(action=action, target=obj.name, technology=obj.technology)
        if action == RprAction.ReadText:
            node.output_variable = obj.name.split("_")[-1]
        self.insert_node(node)

    def _obj_if_exists(self):
        obj = self._sel_object()
        if obj is not None:
            self.insert_node(IfNode(condition=Condition(kind=ConditionKind.ElementExists, target=obj.name, timeout_ms=2000)))

    def new_object(self):
        obj = UiObject(name=self.repo.make_unique_name("Obiect"), locators=[Locator(LocatorKind.Css, "")])
        try:   # pagina din browser = site / pagina implicite
            if self.web().is_open:
                obj.context = self.web().current_url()
                self.repo.classify(obj)
                obj.object_type = ""
        except Exception:
            pass
        sel = self._sel_object()
        if sel is not None and sel.is_container:
            obj.parent, obj.site, obj.page = sel.name, sel.site, sel.page
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
                self.repo.rename_parent_refs(old, obj.name)
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
        kids = self.repo.children_of(obj.name)
        msg = f"Stergi obiectul \"{obj.name}\" din biblioteca?"
        if used:
            msg += f"\n\nAtentie: rutina curenta il foloseste in {used} pasi."
        if kids:
            msg += f"\n\nE container pentru {len(kids)} obiecte: ele raman, dar vor fi cautate in toata pagina."
        if messagebox.askyesno("Biblioteca", msg, parent=self):
            self.repo.remove(obj)
            self.save_repository()
            self.refresh_objects()

    def object_to_step(self):
        self._obj_step(RprAction.Click)

    def move_to_container(self):
        obj = self._sel_object()
        if obj is None:
            return
        banned = {obj.name.lower()} | {o.name.lower() for o in self.repo.objects
                                       if any(p.name.lower() == obj.name.lower() for p in self.repo.parent_chain(o))}
        options = ["(fara container — toata pagina)"] + [
            o.name for o in sorted(self.repo.objects, key=lambda x: x.name.lower())
            if o.is_container and o.name.lower() not in banned and o.technology == obj.technology]
        if len(options) == 1:
            messagebox.showinfo("Container", "Nu exista containere. Marcheaza o sectiune / un tabel / o lista cu Spy si "
                                             "alege tipul \"Container\", \"Tabel\" sau \"RefList\".", parent=self)
            return
        ans = list_dialog(self, "Muta in container", f"In ce container se afla [{obj.name}]?", options, C=self.C)
        if ans is None:
            return
        parent = "" if ans == options[0] else ans
        obj.parent = parent
        if parent:
            po = self.repo.find(parent)
            if po is not None:
                obj.site, obj.page = po.site, po.page
        self.save_repository()
        self.refresh_objects()
        self.set_status(f"[{obj.name}] e cautat acum " + (f"in containerul [{parent}]." if parent else "in toata pagina."))

    def copy_object(self):
        obj = self._sel_object()
        if obj is None:
            return
        sites = sorted({o.site for o in self.repo.objects if o.site} | {g.name for g in self.repo.sites}, key=str.lower)
        site = input_dialog(self, "Copiaza obiectul", f"Copie a lui [{obj.name}] pentru site-ul (poti scrie unul nou):\n"
                                                       f"Site-uri existente: {', '.join(sites) or '-'}", obj.site, C=self.C)
        if site is None:
            return
        page = input_dialog(self, "Copiaza obiectul", "Pagina:", obj.page, C=self.C)
        if page is None:
            return
        twin = copy.deepcopy(obj)
        twin.site, twin.page = site.strip(), page.strip()
        twin.name = self.repo.make_unique_name(obj.name + "_" + sanitize_name(site.split(".")[0] or "copie"))
        self.repo.add(twin)
        self.save_repository()
        self.refresh_objects()
        self.set_status(f"Copie creata: [{twin.name}] pentru {twin.site}{twin.page}. Testeaz-o pe noul site (🧪).")

    def test_object(self, obj: Optional[UiObject] = None):
        obj = obj or self._sel_object()
        if obj is None:
            return
        if obj.technology not in (UiTechnology.Web, UiTechnology.WebSelenium):
            driver = self.drivers.get(obj.technology)

            def work_win():
                try:
                    self.post("test_result", (obj, driver.test_object(obj), None))
                except Exception as ex:  # noqa: BLE001
                    self.post("test_result", (obj, None, str(ex)))
            self.set_status(f"🧪 Testez [{obj.name}] pe ecran...")
            threading.Thread(target=work_win, daemon=True).start()
            return
        try:
            if not self.web().is_open:
                url = self._ask_url_if_closed()
                if url is False:
                    return
            else:
                url = None
        except Exception:
            url = None
        self.repo.link_parents(obj)
        web = self.web()

        def work():
            try:
                if url:
                    web.open(url)
                self.post("test_result", (obj, web.test_object(obj), None))
            except Exception as ex:  # noqa: BLE001
                self.post("test_result", (obj, None, str(ex)))
        self.set_status(f"🧪 Testez [{obj.name}] pe pagina din browser...")
        threading.Thread(target=work, daemon=True).start()

    def _test_finished(self, obj, res, error):
        if error:
            messagebox.showerror("Test", error, parent=self)
            return
        TestResultDialog(self, obj, res)

    def edit_sites(self):
        SitesDialog(self)
        self.refresh_objects()

    def spy(self, technology):
        tech = str(technology).lower()
        if tech not in ("web", "webselenium"):
            return self._spy_windows(UiTechnology.Sap if tech == "sap" else UiTechnology.Desktop)
        if self.busy:
            self.set_status("Asteapta sa se termine operatia curenta.")
            return
        if self._recording:
            self.record_web()   # oprim inregistrarea inainte de Spy
        url = self._ask_url_if_closed()
        if url is False:
            return
        self.busy = True
        self._spy_driver = None
        self._show_spy_hint("🎯 SPY WEB: du mouse-ul peste element in browser (contur verde) si da CLICK.  "
                            "Esc in browser = anuleaza.")
        web = self.web()

        def work():
            try:
                if url:
                    web.open(url)
                obj = web.capture_object("Click = captureaza · Esc = anuleaza", RprPaths.object_images())
                if obj is not None:
                    self.repo.classify(obj)
                    # containerul sugerat: un container existent pe aceeasi pagina care include elementul
                    for c in [o for o in self.repo.objects if o.is_container and o.technology == obj.technology
                              and o.site == obj.site]:
                        self.repo.link_parents(c)
                        if web.element_inside(c, obj):
                            obj.parent = c.name
                            break
                self.post("spy_done", (obj, None))
            except Exception as ex:  # noqa: BLE001
                self.post("spy_done", (None, str(ex)))
        self.set_status("SPY WEB: du mouse-ul peste element in browser si da CLICK ca sa-l capturezi. Esc = anulare.")
        threading.Thread(target=work, daemon=True, name="Spy").start()

    def _spy_windows(self, tech: UiTechnology):
        """Spy SAP / Desktop: mouse-ul peste element (contur pe ecran) + F2 = captureaza, Esc = anuleaza."""
        if self.busy:
            self.set_status("Asteapta sa se termine operatia curenta.")
            return
        driver = self.drivers.get(tech)
        self._spy_driver = driver
        self.busy = True
        is_sap = tech == UiTechnology.Sap
        self._show_spy_hint(("🎯 SPY SAP: du mouse-ul peste camp / buton in SAP GUI (contur rosu) si apasa F2.  "
                             if is_sap else
                             "🎯 SPY DESKTOP: du mouse-ul peste element in aplicatie (contur verde) si apasa F2.  ")
                            + "Esc = anuleaza.")
        if self.studio_settings.minimize_on_run:
            self.winfo_toplevel().iconify()

        def work():
            try:
                obj = driver.capture_object("F2 = captureaza · Esc = anuleaza", RprPaths.object_images())
                if obj is not None:
                    self.repo.classify(obj)
                self.post("spy_done", (obj, None))
            except Exception as ex:  # noqa: BLE001
                self.post("spy_done", (None, str(ex)))
        self.set_status(("SPY SAP" if is_sap else "SPY DESKTOP") + ": mouse-ul peste element, apoi F2. Esc = anulare.")
        threading.Thread(target=work, daemon=True, name="Spy").start()

    def _ask_url_if_closed(self):
        """None = browserul e deja deschis; False = anulat; altfel adresa de deschis."""
        try:
            if self.web().is_open:
                return None
        except Exception:
            pass
        url = input_dialog(self, "Deschide browserul", "Browserul nu e deschis. La ce adresa sa-l deschid?",
                           "https://", C=self.C)
        if not url or not url.strip() or url.strip() == "https://":
            return False
        return url.strip()

    def _show_spy_hint(self, text: str, on_cancel: Optional[Callable[[], None]] = None, cancel_text: str = "Anuleaza"):
        self._hide_spy_hint()
        C = self.C
        w = tk.Toplevel(self)
        w.overrideredirect(True)
        w.attributes("-topmost", True)
        w.configure(bg=C["primary"])
        tk.Label(w, text=text, bg=C["primary"], fg="white", font=("Segoe UI", 10, "bold"), padx=12, pady=6).pack(side="left")
        cancel = on_cancel or (lambda: (getattr(self, "_spy_driver", None) or self.web()).cancel_spy())
        tk.Button(w, text=cancel_text, command=cancel, bg="white", fg=C["primary"],
                  relief="flat", font=("Segoe UI", 10, "bold"), cursor="hand2").pack(side="left", padx=8, pady=4)
        w.update_idletasks()
        w.geometry(f"+{(w.winfo_screenwidth() - w.winfo_reqwidth()) // 2}+8")
        self._spy_hint = w

    def _hide_spy_hint(self):
        if self._spy_hint is not None:
            try:
                self._spy_hint.destroy()
            except Exception:
                pass
            self._spy_hint = None

    def _spy_finished(self, obj, error):
        self.busy = False
        self._hide_spy_hint()
        top = self.winfo_toplevel()
        top.deiconify()
        top.lift()
        if error:
            messagebox.showerror("Spy", f"Spy nu a putut porni:\n{error}", parent=self)
            self.set_status("Spy esuat.")
            return
        if obj is None:
            self.set_status("Spy anulat.")
            return
        same = self.find_same_object(obj)
        if same is not None:
            a = choice_dialog(self, "Obiect existent", f"Elementul e deja in repository ca [{same.name}]. Il folosesti pe acela?",
                              ["Foloseste existentul", "Salveaza ca obiect nou", "Anuleaza"], C=self.C)
            if a == "Anuleaza":
                return
            if a == "Foloseste existentul":
                self.insert_node(ActionNode(action=RprAction.Click, target=same.name, technology=same.technology))
                return
        result = ObjectReviewDialog(self, obj).result
        if not result:
            self.set_status("Obiect nesalvat.")
            return
        self.repo.add(obj)
        self.save_repository()
        self.refresh_objects()
        self.set_status(f"Obiect salvat: [{obj.name}] — {sum(1 for l in obj.locators if l.enabled)} locatori activi.")
        if result == "click":
            self.insert_node(ActionNode(action=RprAction.Click, target=obj.name, technology=obj.technology))
        elif result == "type":
            self.insert_node(ActionNode(action=RprAction.TypeText, target=obj.name, technology=obj.technology))
        elif result == "read":
            self.insert_node(ActionNode(action=RprAction.ReadText, target=obj.name, technology=obj.technology,
                                        output_variable=obj.name.split("_")[-1]))

    def find_same_object(self, obj: UiObject) -> Optional[UiObject]:
        best = next((l for l in obj.locators if l.enabled), None)
        if best is None:
            return None
        for o in self.repo.objects:
            if o.technology == obj.technology and list(o.frame_path) == list(obj.frame_path) and \
                    any(l.kind == best.kind and l.value == best.value for l in o.locators):
                return o
        return None

    # ── Inregistrare web ──
    def record_web(self):
        web = self.web()
        if self._recording:
            web.stop_recording()
            self._set_recording(False)
            self.set_status("Inregistrare oprita.")
            return
        if self.busy:
            return
        url = self._ask_url_if_closed()
        if url is False:
            return

        def work():
            try:
                if url:
                    web.open(url)
                web.start_recording(lambda rec: self.post("recorded", rec), "INREGISTRARE · Esc = stop")
                self.post("record_started", None)
            except Exception as ex:  # noqa: BLE001
                self.post("record_failed", str(ex))
        self.set_status("Pornesc inregistrarea...")
        threading.Thread(target=work, daemon=True, name="RecordWeb").start()

    def _set_recording(self, on: bool):
        if on == self._recording:
            return
        self._recording = on
        if self._run_frame:
            self._run_frame.show("rec") if on else self._run_frame.hide()
        dnd = bool(self.routine.settings.do_not_disturb and safety and self._dnd_allowed())
        if dnd:
            safety.DoNotDisturb.enable(wait=False) if on else safety.DoNotDisturb.restore()
        if on:
            self.set_status("⏺ INREGISTRARE: lucreaza normal in browser — fiecare click, text completat sau optiune aleasa "
                            "devine un pas. Esc in browser sau ⏺ din nou = stop.")

    def _add_recorded(self, rec):
        obj = self.find_same_object(rec.target)
        if obj is None:
            self.repo.classify(rec.target)
            obj = self.repo.add(rec.target)
        self.save_repository()
        self.refresh_objects()
        # scrierea repetata in acelasi camp = un singur pas cu valoarea finala
        node, _ = self._sel_node()
        if rec.action == RprAction.TypeText and isinstance(node, ActionNode) and \
                node.action == RprAction.TypeText and node.target == obj.name:
            node.value = rec.value
            self.refresh_node(node)
            self.editor.show(node)
            self.mark_dirty()
            return
        self.insert_node(ActionNode(action=rec.action, target=obj.name, value=rec.value, technology=obj.technology))

    def show_object(self, obj: Optional[UiObject] = None, ms: int = 8000):
        obj = obj or self._sel_object()
        if obj is None:
            return
        self.repo.link_parents(obj)
        web = self.web() if obj.technology in (UiTechnology.Web, UiTechnology.WebSelenium)             else self.drivers.get(obj.technology)

        def work():
            try:
                ok, msg = web.show_object(obj, ms)
            except Exception as ex:  # noqa: BLE001
                msg = str(ex)
            self.post("status", "👁 " + msg)
        threading.Thread(target=work, daemon=True).start()

    # ── Programare (Windows Task Scheduler) ──
    def show_schedule(self):
        if self.dirty or not self.routine_path:
            if not messagebox.askyesno("Programare", "Rutina trebuie salvata inainte de programare. Salvez acum?",
                                       parent=self):
                return
            if not self.save_routine():
                return
        ScheduleDialog(self, self.routine_path, self.routine.name)

    # ── Setari Studio ──
    def show_settings(self, tab: int = 0):
        """v4.14: setarile pe tab-uri: 🌐 Browser · 🎨 Aspect · 📁 Unde se salveaza · 🎬 Filme."""
        C, st = self.C, self.studio_settings
        from rpr import locations
        import screen_recorder as sr
        import video_ui
        dlg = tk.Toplevel(self)
        dlg.title("Setari Studio")
        dlg.configure(bg=C["bg_main"])
        dlg.transient(self.winfo_toplevel())
        dlg.minsize(520, 380)
        tk.Label(dlg, text="⚙  Setari Studio", bg=C["bg_main"], fg=C["primary"], font=("Segoe UI", 13, "bold")).pack(
            anchor="w", padx=16, pady=(14, 6))
        nb = ttk.Notebook(dlg, style="Studio.TNotebook")
        nb.pack(fill="both", expand=True, padx=12)

        def page(title):
            f = tk.Frame(nb, bg=C["bg_main"])
            nb.add(f, text=title)
            return f

        def caption(host, text):
            tk.Label(host, text=text, bg=C["bg_main"], fg=C["text_dim"], font=("Segoe UI", 10, "bold"),
                     anchor="w").pack(fill="x", padx=12, pady=(12, 2))

        def hint(host, text):
            ui_theme.autowrap(tk.Label(host, text=text, bg=C["bg_main"], fg=C["text_dim"], font=("Segoe UI", 9),
                                       justify="left", anchor="w", wraplength=560), margin=10).pack(
                fill="x", padx=12, pady=(4, 6))

        def check(host, text, var):
            cb = tk.Checkbutton(host, text=text, variable=var, bg=C["bg_main"], fg=C["text"], selectcolor=C["bg_input"],
                                activebackground=C["bg_main"], activeforeground=C["text"], font=("Segoe UI", 10),
                                anchor="w", justify="left", wraplength=560)
            cb.pack(fill="x", padx=10, pady=2)
            ui_theme.autowrap(cb, margin=34)

        # ── 🌐 Browser ──
        pg = page("🌐 Browser")
        from rpr.drivers.web import BROWSERS
        caption(pg, "Browser pentru pasii Web")
        browser = ttk.Combobox(pg, values=[tr(l) for _, l in BROWSERS], state="readonly", width=40,
                               style="Studio.TCombobox")
        browser.current(next((i for i, (v, _) in enumerate(BROWSERS) if v.lower() == st.browser.lower()), 0))
        browser.pack(anchor="w", padx=12, pady=(0, 8))
        headless = tk.BooleanVar(value=st.headless)
        minimize = tk.BooleanVar(value=st.minimize_on_run)
        check(pg, "Browser fara fereastra (headless) — doar pentru rulari programate", headless)
        check(pg, "Minimizeaza aplicatia la rulare (ramane bara plutitoare de control)", minimize)
        hint(pg, "Edge / Chrome folosesc browserul instalat (nu se descarca nimic). Profilul browserului "
                 "(login, cookie-uri) se pastreaza intre rulari.")
        row = tk.Frame(pg, bg=C["bg_main"])
        row.pack(anchor="w", padx=10, pady=4)

        def close_browser():
            try:
                self.web().close_browser()
                self.set_status("Browserul a fost inchis.")
            except Exception as ex:  # noqa: BLE001
                self.set_status(str(ex))

        def clear_profile():
            if not messagebox.askyesno("Profil browser", "Stergi profilul browserului (logout din toate site-urile)?",
                                       parent=dlg):
                return
            import shutil
            self.drivers.close()
            self.drivers = self._build_drivers()
            shutil.rmtree(RprPaths.browser_profile(), ignore_errors=True)
            self.set_status("Profilul browserului a fost sters.")
        self._btn(row, "Inchide browserul", close_browser).pack(side="left", padx=2)
        self._btn(row, "Sterge profilul browserului", clear_profile).pack(side="left", padx=2)
        self._btn(row, "📂 Folderul de lucru", lambda: os.startfile(RprPaths.root)).pack(side="left", padx=2)

        # ── 🎨 Aspect ──
        pg = page("🎨 Aspect")
        caption(pg, "Marimea textului (toata aplicatia)")
        size = tk.StringVar(value=ui_theme.text_size())
        for key, label, _f in ui_theme.TEXT_SIZES:
            tk.Radiobutton(pg, text=label, value=key, variable=size, bg=C["bg_main"], fg=C["text"],
                           selectcolor=C["bg_input"], activebackground=C["bg_main"], activeforeground=C["text"],
                           font=("Segoe UI", 10), anchor="w").pack(fill="x", padx=12)
        hint(pg, "Se aplica la urmatoarea pornire a aplicatiei. Pe un ecran mic (laptop) alege Normal; pe un monitor "
                 "mare sau cu scalare mica alege Mare. Latimea panourilor Studio se tine minte (trage de marginea "
                 "dintre ele); butonul de mai jos le readuce la impartirea initiala.")
        lay_row = tk.Frame(pg, bg=C["bg_main"])
        lay_row.pack(anchor="w", padx=10, pady=4)

        def reset_layout():
            st.layout = {}
            st.save()
            self._layout_w = 0
            self._apply_layout()
            self.set_status("Panourile au revenit la impartirea initiala.")
        self._btn(lay_row, "↺ Panouri ca la inceput", reset_layout).pack(side="left", padx=2)

        # ── 📁 Unde se salveaza ──
        sf = ScrollFrame(nb, C["bg_main"])     # lunga: pe ecrane mici se deruleaza
        nb.add(sf, text="📁 Unde se salveaza")
        pg = sf.inner
        hint(pg, "Alege un folder comun (de ex. in OneDrive, ca fisierele sa ajunga singure in cloud). Tot ce creezi "
                 "ajunge acolo, in subfoldere: rutine, obiecte, rezultate, filme. Un camp completat mai jos are "
                 "prioritate pentru felul lui de fisiere; ce setezi pe o rutina (⚙ Rutina → folderul filmelor / "
                 "raportului) sau pe o biblioteca de obiecte (fisierul ei) are prioritate fata de toate.")
        vs = sr.VideoSettings.load()
        base_var = tk.StringVar(value=st.save_base_folder)
        legacy = {"routines": os.path.join(RprPaths.root, "rutine"),
                  "libraries": os.path.join(rpr_report.onedrive_folder() or os.path.join(os.path.expanduser("~"),
                                                                                         "Documents"),
                                            "AutoPilotDC", "obiecte"),
                  "results": os.path.join(RprPaths.root, "rezultate"),
                  "videos": sr._legacy_folder()}
        explicit_now = {"routines": st.routines_folder, "libraries": st.save_folders.get("libraries", ""),
                        "results": st.save_folders.get("results", ""),
                        "videos": "" if os.path.normcase(os.path.normpath(vs.folder)) == os.path.normcase(
                            os.path.normpath(sr._default_folder())) else vs.folder}
        vars_ = {k: tk.StringVar(value=explicit_now[k]) for k, _l, _s in locations.KINDS}
        info = {}

        def folder_row(host, var, title):
            r = tk.Frame(host, bg=C["bg_main"])
            r.pack(fill="x", padx=12, pady=(0, 2))
            e = tk.Entry(r, textvariable=var, bg=C["bg_input"], fg=C["text"], insertbackground=C["text"],
                         relief="flat", font=("Segoe UI", 10))
            e.pack(side="left", fill="x", expand=True, ipady=4)

            def browse():
                d = filedialog.askdirectory(parent=dlg, title=title, initialdir=var.get() or base_var.get() or None)
                if d:
                    var.set(os.path.normpath(d))
            self._btn(r, "…", browse, tip="Alege folderul").pack(side="left", padx=(4, 0))
            self._btn(r, "✕", lambda: var.set(""), tip="Goleste (foloseste folderul comun)").pack(side="left", padx=(2, 0))
            return r

        caption(pg, "Folderul comun")
        br = folder_row(pg, base_var, "Folderul comun")
        od = rpr_report.onedrive_folder()
        if od:
            self._btn(br, "☁ OneDrive", lambda: base_var.set(os.path.join(od, "AutoPilotDC")),
                      tip="Folder in OneDrive-ul sincronizat").pack(side="left", padx=(2, 0))
        for key, label, sub in locations.KINDS:
            caption(pg, label)
            folder_row(pg, vars_[key], label)
            info[key] = tk.Label(pg, text="", bg=C["bg_main"], fg=C["text_dim"], font=("Segoe UI", 9), anchor="w",
                                 justify="left", wraplength=560)
            info[key].pack(fill="x", padx=14)
            ui_theme.autowrap(info[key], margin=10)

        def refresh_info(*_a):
            b = base_var.get().strip().strip('"')
            for key, _label, sub in locations.KINDS:
                own = vars_[key].get().strip()
                where = own or (os.path.join(b, sub) if b else legacy[key])
                info[key].configure(text="→ " + where if own else tr("gol = implicit:") + " " + where)
        base_var.trace_add("write", refresh_info)
        for v in vars_.values():
            v.trace_add("write", refresh_info)
        refresh_info()

        # ── 🎬 Filme ──
        pg = page("🎬 Filme")
        caption(pg, "Deschide filmele cu")
        player_value = video_ui.build_player_chooser(pg, C, vs.player)
        hint(pg, "Se foloseste la 🎬, la linkurile din Excel / raport si la dublu-click pe un fisier .apvid. "
                 "Alta aplicatie decat playerul AutoPilot primeste o copie MP4 a filmului, facuta o singura data, "
                 "langa film (GIF daca lipseste pachetul opencv-python). Editarea (taieri, texte, zone ascunse) "
                 "ramane in playerul AutoPilot.")

        def save():
            new_browser = BROWSERS[browser.current()][0]
            changed = new_browser != st.browser or headless.get() != st.headless
            st.browser, st.headless, st.minimize_on_run = new_browser, headless.get(), minimize.get()
            old_routines = st.effective_routines_folder()
            st.save_base_folder = base_var.get().strip().strip('"')
            st.routines_folder = vars_["routines"].get().strip().strip('"')
            st.save_folders = {k: vars_[k].get().strip().strip('"') for k in ("libraries", "results")
                               if vars_[k].get().strip()}
            st.save()
            v = sr.VideoSettings.load()
            v.folder = vars_["videos"].get().strip().strip('"') or sr._default_folder()
            v.player = player_value()
            v.save()
            size_changed = size.get() != ui_theme.text_size()
            ui_theme.save(text_size=size.get())
            if changed:   # browser nou -> driver nou (cel vechi se inchide)
                self.drivers.close()
                self.drivers = self._build_drivers()
            dlg.destroy()
            self._update_routines_label()
            if os.path.normcase(st.effective_routines_folder()) != os.path.normcase(old_routines):
                self.refresh_routines()
            self.set_status(tr("Setarile Studio au fost salvate.") +
                            (" " + tr("Marimea textului se aplica la urmatoarea pornire.") if size_changed else ""))
        bottom = tk.Frame(dlg, bg=C["bg_main"])
        bottom.pack(anchor="e", padx=14, pady=12)
        self._btn(bottom, "💾 Salveaza", save, color=C["success"]).pack(side="left", padx=3)
        self._btn(bottom, "Anuleaza", dlg.destroy).pack(side="left", padx=3)
        if 0 <= tab < len(nb.tabs()):
            nb.select(tab)
        # fereastra incape pe ecran (si pe un laptop 1366 x 768)
        dlg.update_idletasks()
        sw, sh = dlg.winfo_screenwidth(), dlg.winfo_screenheight()
        w, h = min(max(680, dlg.winfo_reqwidth()), 820, sw - 40), min(max(560, dlg.winfo_reqheight()), sh - 80)
        dlg.geometry(f"{w}x{h}+{max(0, (sw - w) // 2)}+{max(0, (sh - h) // 3)}")
        dlg.grab_set()

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
                self._step_finished(node, ok)
            elif kind == "row_started":
                row, sheet, film, sec = p
                self._cur_row = row
                self._excel.row_started(row, film, sec)
                self._timeline.set_summary(f"Rulare in curs · randul {row}")
            elif kind == "row_finished":
                self._excel.row_finished(*p)
            elif kind == "ui":
                p()
            elif kind == "status":
                self.set_status(p)
                if isinstance(p, str) and p.startswith("Inregistrare oprita"):
                    self._set_recording(False)
            elif kind == "spy_done":
                self._spy_finished(*p)
            elif kind == "scan_ready":
                self._scan_ready(*p)
            elif kind == "scan_done":
                self._scan_done(*p)
            elif kind == "hover_obj":
                self._hover_object(p)
            elif kind == "hover_failed":
                self._hover_finished(p)
            elif kind == "test_result":
                self._test_finished(*p)
            elif kind == "routines_ready":
                self.refresh_routines_view()
            elif kind == "check_progress":
                self.set_status(p)
            elif kind == "check_done":
                self._check_done(*p)
            elif kind == "recapture_done":
                self._recapture_done(*p)
            elif kind == "recorded":
                self._add_recorded(p)
            elif kind == "record_started":
                self._set_recording(True)
            elif kind == "record_failed":
                messagebox.showerror("Inregistrare", f"Inregistrarea nu a putut porni:\n{p}", parent=self)
            elif kind == "call":
                fn, ev, box = p
                try:
                    box["r"] = fn()
                finally:
                    ev.set()
            elif kind == "done":
                self._run_finished(*p)
            elif kind == "prep_done":
                self._prep_finished(p)

    def _add_log(self, e: RunLogEntry):
        self._log_entries.append(e)
        if str(e.level) == "Error" and e.node_id:   # captura si mesajul ajung pe cardul pasului din cronologie
            self._step_errors[e.node_id] = (e.screenshot, e.message)
        iid = self.log.insert("", "end", values=(e.time.strftime("%H:%M:%S"), level_label(e.level),
                                                 e.excel_row or "", e.node_title[:60], e.message.replace("\n", " ")),
                              tags=(str(e.level),))
        kids = self.log.get_children()
        if len(kids) > 3000:
            self.log.delete(kids[0])
        self.log.see(iid)

    def _mark_running(self, node: RprNode):
        self._step_t0[node.id] = time.monotonic()
        prev = self._running_iid
        if self._running_iid and self.tree.exists(self._running_iid):
            tags = [t for t in self.tree.item(self._running_iid, "tags") if t != "running"]
            self.tree.item(self._running_iid, tags=tags)
        if self.tree.exists(node.id):
            tags = [t for t in self.tree.item(node.id, "tags") if t not in ("ok", "error")]
            self.tree.item(node.id, tags=tags + ["running"])
            self.tree.see(node.id)
            self._running_iid = node.id
        for fv in self._flows():
            if prev:
                fv.set_state(prev)
            fv.set_state(node.id)
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

    def run(self, step_mode: bool = False, variables: Optional[Dict[str, str]] = None,
            routine: Optional[Routine] = None, learn: bool = False):
        """routine: o copie de rulat in locul rutinei din editor (v4.15: Reia randul din ecranul Excel).
        learn: ▶ Ruleaza si marcheaza (v4.17): doar primul rand Excel; la un obiect negasit se poate marca pe loc."""
        if self.busy:
            if step_mode:
                self.step_once()
            return
        override = routine is not None
        routine = routine or self.routine
        if not routine.steps:
            messagebox.showinfo("Rutina goala", "Rutina nu are pasi. Adauga pasi din stanga sau deschide un exemplu "
                                                "(📚 Exemple).", parent=self)
            return
        self.busy = True
        for iid in self._items:
            if self.tree.exists(iid):
                self.tree.item(iid, tags=[t for t in self.tree.item(iid, "tags") if t not in ("running", "ok", "error")])
        self.clear_log()
        self._run_started_ui(routine, step_mode)
        self.engine = RprEngine(self.repo, self.drivers, StudioRunHost(self), RprPaths.output())
        self.engine.step_mode = step_mode
        self._learn_run = learn
        if learn:
            self.engine.ask_on_every_error = True
            self.engine.max_rows = 1
        self.engine.guard = StudioGuard() if safety else None
        if self._recording:
            self.record_web()   # oprim inregistrarea inainte de rulare
        self._run_control = RunControlWindow(self)
        if self._run_frame:
            self._run_frame.show("pause" if step_mode else "run")
        if self.studio_settings.minimize_on_run and not step_mode:
            self.winfo_toplevel().iconify()
        self.set_status("PAS CU PAS: apasa ⏭ Pas pentru fiecare pas." if step_mode else "Rulez...")
        engine = self.engine
        if self.video is not None and not step_mode:
            try:
                self.video.run_started(routine.name, folder=rpr_report.video_folder(routine))   # 🎥 daca e activ in Setari → Video
            except Exception as ex:  # noqa: BLE001
                self.set_status(f"🎥 {ex}")
        # "Nu deranja": setarea rutinei SI setarea generala a aplicatiei (Setari) trebuie sa fie pornite
        dnd = bool(routine.settings.do_not_disturb and safety and self._dnd_allowed())
        if dnd:
            safety.DoNotDisturb.enable(wait=False)   # cererea se inregistreaza imediat, pe firul interfetei
        if not step_mode:   # daca aplicatia se inchide brusc, la pornire se ofera reluarea
            unsaved = self.dirty or not self.routine_path or override
            self._resume_state = rpr_resume.begin(rpr_resume.KIND_ROUTINE, "" if override else self.routine_path or "",
                                                  routine.name,
                                                  routine=routine.to_dict() if unsaved else None, variables=variables)

        def work():
            result = None
            try:
                if dnd:
                    self.post("status", "🌙 Activez \"Nu deranja\" (cateva secunde)...")
                    safety.DoNotDisturb.wait_settled(timeout=20)
                    self.post("status", safety.DoNotDisturb.last_message)
                result = engine.run(routine, variables) if variables else engine.run(routine)
            except Exception as ex:  # noqa: BLE001
                from rpr.host import RunResult
                result = RunResult(success=False, message=str(ex))
            finally:
                if self.video is not None:
                    try:
                        self.video.settle()   # 🎥 filmul mai prinde cateva secunde: rezultatul ultimului pas
                    except Exception:  # noqa: BLE001
                        pass
                if dnd:
                    safety.DoNotDisturb.restore()
                self.post("done", (result,))

        threading.Thread(target=work, daemon=True, name="StudioRun").start()

    # ── v4.15: cronologia si ecranul Excel in timpul rularii ──
    def _run_started_ui(self, routine: Routine, step_mode: bool):
        self._step_t0.clear()
        self._step_errors.clear()
        self._cur_row = 0
        self._timeline.clear()
        self._timeline.set_summary(tr("Rulare in curs:") + f" {routine.name}")
        try:
            self._bottom.select(self._timeline)
        except tk.TclError:
            pass
        f = self.first_for_each(routine)
        if f is not None:
            self._excel.reset_run()
            if not step_mode:      # rutina cu Excel: ecranul de rulare pe randuri se deschide singur
                self.show_center("excel")
            self._excel.reload()

    def _step_finished(self, node: RprNode, ok: bool):
        for fv in self._flows():
            fv.set_state(node.id)
        if isinstance(node, ForEachRowNode):
            self._cur_row = 0
        if node.branches():         # in cronologie intra doar pasii propriu-zisi, nu blocurile
            return
        t0 = self._step_t0.pop(node.id, None)
        ms = (time.monotonic() - t0) * 1000 if t0 else 0.0
        shot, msg = self._step_errors.pop(node.id, ("", "")) if not ok else ("", "")
        self._timeline.add(node.id, node.title, ok, self._cur_row, ms, shot, msg)

    def _run_finished(self, result):
        self.busy = False
        learned = getattr(self, "_learn_run", False)
        self._learn_run = False
        win = getattr(self, "_complete_win", None)
        if learned and win is not None:
            try:
                if win.winfo_exists():
                    win.learn_finished(result)
            except tk.TclError:
                pass
        rpr_resume.end(self._resume_state)
        self._resume_state = None
        if self.video is not None:
            try:
                self.video.run_finished(result)
            except Exception:  # noqa: BLE001
                pass
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
        self._timeline.set_summary(f"{mark}{tr(result.message)}  ·  {studio_views.fmt_time(self._timeline.elapsed())}")
        for fv in self._flows():
            fv.sync_states()
        report = getattr(result, "report_path", "")
        self.set_status(mark + result.message + (f"  📊 {report}" if report else ""))
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
        if self._prep_runner is not None:
            self._prep_runner.cancel()   # si rutinele urmatoare din pregatire
        if self.engine:
            self.engine.stop()

    # ── 📂 Manager de rutine + pregatiri (rpr/batch.py) ──
    def show_routine_manager(self):
        from routine_manager_ui import RoutineManagerDialog
        RoutineManagerDialog(self)

    def run_preparation(self, prep, start_index: int = 0):
        """Ruleaza rutinele pregatirii una dupa alta, prin Studio: intrebari, preventie, Pauza / STOP raman active.
        start_index > 0: reluare dupa o inchidere neasteptata (primele rutine erau terminate)."""
        if self.busy:
            return
        from rpr.batch import PreparationRunner
        self.busy = True
        self.clear_log()
        self._run_control = RunControlWindow(self)
        if self._run_frame:
            self._run_frame.show("run")
        if self.studio_settings.minimize_on_run:
            self.winfo_toplevel().iconify()
        dnd = bool(safety and self._dnd_allowed())
        if dnd:
            safety.DoNotDisturb.enable(wait=False)

        def load(path):
            return RoutineStore.load(path, self.repo)

        def run_one(routine, item, folder):
            repo = RepositoryStore.load(routine.repository_path) if routine.repository_path.strip() else self.repo
            engine = RprEngine(repo, self.drivers, StudioRunHost(self), RprPaths.output())
            engine.guard = StudioGuard() if safety else None
            self.engine = engine
            if self._prep_runner is not None and self._prep_runner.cancelled:
                return None, ""
            filmed = False
            if self.video is not None and prep.video:
                try:
                    filmed = bool(self.call_ui(lambda: self.video.run_started(routine.name, force=True,
                                                                         folder=rpr_report.video_folder(routine))))
                except Exception:  # noqa: BLE001 — filmul nu are voie sa opreasca pregatirea
                    filmed = False
            result = None
            try:
                result = engine.run(routine)
            finally:
                film = ""
                if filmed:
                    try:
                        self.video.settle()
                        film = self.call_ui(lambda: self.video.run_finished(result)) or ""
                    except Exception:  # noqa: BLE001
                        film = ""
            return result, film

        state = rpr_resume.begin(rpr_resume.KIND_PREP, prep.path, prep.name)
        self._resume_state = state
        runner = PreparationRunner(prep, run_one, RprPaths.output(), load_routine=load,
                                   on_progress=lambda i, n, name: self.post("status", f"▶ Pregatire {i}/{n}: {name}"),
                                   on_item_done=lambda done: rpr_resume.update(state, done))
        self._prep_runner = runner

        def work():
            res = None
            try:
                if dnd:
                    safety.DoNotDisturb.wait_settled(timeout=20)
                res = runner.run(start_index)
            except Exception as ex:  # noqa: BLE001
                self.post("status", f"Pregatirea s-a oprit: {ex}")
            finally:
                if dnd:
                    safety.DoNotDisturb.restore()
                self.post("prep_done", res)
        threading.Thread(target=work, daemon=True, name="Pregatire").start()

    def _prep_finished(self, res):
        self.busy = False
        self._prep_runner = None
        rpr_resume.end(self._resume_state)
        self._resume_state = None
        if self._run_control:
            self._run_control.destroy()
            self._run_control = None
        if self._run_frame:
            self._run_frame.hide()
        self.winfo_toplevel().deiconify()
        if res is None:
            return
        self.set_status(("✔ " if res.success else "✖ ") + res.message)
        ans = choice_dialog(self, "Pregatire terminata", res.message,
                            ["Deschide documentatia", "Deschide folderul", "OK"],
                            f"Rezultatele: {res.folder}", C=self.C)
        target = res.documentation if ans == "Deschide documentatia" else res.folder if ans == "Deschide folderul" else ""
        if target:
            try:
                os.startfile(target)  # type: ignore[attr-defined]
            except Exception as ex:  # noqa: BLE001
                self.set_status(str(ex))

    def forget_resume(self):
        """Rularea a fost oprita de utilizator (ex. inchide aplicatia): nu se mai ofera reluarea la pornire."""
        rpr_resume.end(self._resume_state)
        self._resume_state = None

    def resume_interrupted(self, state, run: bool = True) -> bool:
        """Reia o rulare intrerupta brusc (rpr/resume.py). Randurile Excel cu OK se sar, randul ramas
        "IN LUCRU" e intrebat; la o pregatire se sar rutinele deja terminate.
        run=False: doar deschide rutina / Managerul de rutine, fara sa porneasca."""
        if self.busy:
            return False
        if state.kind == rpr_resume.KIND_PREP and not run:
            rpr_resume.discard(state)
            self.show_routine_manager()
            return True
        if state.kind == rpr_resume.KIND_PREP:
            from rpr.batch import Preparation
            try:
                prep = Preparation.load(state.path)
            except Exception as ex:  # noqa: BLE001
                messagebox.showerror("Studio RPR", f"Pregatirea nu poate fi deschisa:\n{ex}", parent=self)
                return False
            rpr_resume.discard(state)
            self.run_preparation(prep, start_index=int(state.done_items or 0))
            return True
        if state.routine:   # rutina avea modificari nesalvate: o refacem din copia salvata la pornire
            try:
                r = Routine.from_dict(state.routine)
            except Exception as ex:  # noqa: BLE001
                messagebox.showerror("Studio RPR", f"Rutina nu poate fi refacuta:\n{ex}", parent=self)
                return False
            self._new_doc_slot()
            self.routine = r
            self._load_routine_library(r)
            self.routine_path = state.path or None
            self.dirty = True
            self.rebuild_tree()
            self.show_routine_settings()
            self._update_title()
        else:
            self.open_routine(state.path)
            if os.path.normcase(os.path.abspath(self.routine_path or "")) != os.path.normcase(state.path):
                return False   # nu s-a deschis (lipseste sau utilizatorul a renuntat)
        rpr_resume.discard(state)
        if run:
            self.run(variables=state.variables or None)
        return True

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
        ui_theme.fix_contrast(self.p.props.inner)

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
        ui_theme.autowrap(tk.Label(self._host, text=text, bg=self.C["bg_card"], fg=self.C["primary"],
                                   font=("Segoe UI", 13, "bold"), anchor="w", justify="left")).pack(
            fill="x", padx=12, pady=(12, 4))

    def _caption(self, text, host=None):
        ui_theme.autowrap(tk.Label(host or self._host, text=text, bg=(host or self._host)["bg"], fg=self.C["text_dim"],
                                   font=("Segoe UI", 10, "bold"), anchor="w", justify="left", wraplength=330)).pack(
            fill="x", padx=12, pady=(10, 2))

    def _hint(self, text, host=None, color=None):
        ui_theme.autowrap(tk.Label(host or self._host, text=text, bg=(host or self._host)["bg"],
                                   fg=color or self.C["text_dim"], font=("Segoe UI", 9), anchor="w", justify="left",
                                   wraplength=330)).pack(fill="x", padx=12, pady=(2, 2))

    def _card(self, host=None, title="") -> tk.Frame:
        f = tk.Frame(host or self._host, bg=self.C["bg_main"], highlightthickness=1,
                     highlightbackground=self.C["border"])
        f.pack(fill="x", padx=10, pady=8)
        if title:
            ui_theme.autowrap(tk.Label(f, text=title, bg=self.C["bg_main"], fg=self.C["accent"],
                                       font=("Segoe UI", 10, "bold"), anchor="w", justify="left")).pack(
                fill="x", padx=10, pady=(8, 2))
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
                           font=("Segoe UI", 10, "bold"), cursor="hand2", activebackground=self.C["primary"])
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
                            activebackground=host["bg"], activeforeground=self.C["text"], font=("Segoe UI", 10),
                            command=lambda: (set_(var.get()), self._changed(node, structural)))
        cb.pack(fill="x", padx=10, pady=3)
        ui_theme.autowrap(cb, margin=34)
        return cb

    def combo(self, node, label, options, get, set_, host=None, structural=False):
        host = host or self._host
        if label:
            self._caption(label, host)
        labels = [tr(l) for _, l in options]
        current = get()
        idx = next((i for i, (v, _) in enumerate(options) if v == current), 0)
        cb = ttk.Combobox(host, values=labels, state="readonly", style="Studio.TCombobox", font=("Segoe UI", 10))
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
        cb = ttk.Combobox(host, textvariable=var, values=list(values), style="Studio.TCombobox", font=("Segoe UI", 10))
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

    def file_picker(self, node, label, get, set_, structural=True, filetypes=None, initialdir=None, on_pick=None):
        self._caption(label)
        row = tk.Frame(self._host, bg=self._host["bg"])
        row.pack(fill="x", padx=10)
        var = tk.StringVar(value=get() or "")
        tk.Entry(row, textvariable=var, **self._entry_style()).pack(side="left", fill="x", expand=True, ipady=3)
        var.trace_add("write", lambda *a: (set_(var.get()), self._changed(node)))

        def browse():
            kw = {"initialdir": initialdir} if initialdir else {}
            p = filedialog.askopenfilename(parent=self.p, title=label,
                                           filetypes=filetypes or [("Excel", "*.xlsx *.xlsm")], **kw)
            if p:
                var.set(os.path.normpath(p))
                if on_pick:
                    on_pick(os.path.normpath(p))
                if structural:
                    self._later_rebuild()
        self.p._btn(row, "📂", browse, tip="Alege fisierul").pack(side="left", padx=(4, 0))

    def _build_run_routine(self, node: RunRoutineNode):
        """Pasul 📋 Ruleaza rutina: alegi rutina salvata; ruleaza in locul pasului, cu variabilele si Excel-ul comune."""
        self._hint("Ruleaza o rutina salvata in locul acestui pas, cu aceleasi variabile, acelasi Excel si aceeasi "
                   "biblioteca de obiecte. Setarile rutinei principale (erori, pauze) se aplica si calupului. "
                   "Fisierul se verifica inainte de start.")

        def picked(path):
            try:
                node.name = RoutineStore.load(path, self.p.repo).name
            except Exception:  # noqa: BLE001
                node.name = ""
        self.file_picker(node, "Rutina (fisier .rpr.json; poate contine {variabile})", lambda: node.path,
                         lambda v: setattr(node, "path", v), structural=True,
                         filetypes=[("Rutine AutoPilot", "*.rpr.json *.json")],
                         initialdir=self.p.studio_settings.effective_routines_folder(), on_pick=picked)
        self.text(node, "Nume afisat (optional)", lambda: node.name, lambda v: setattr(node, "name", v), vars_=False)
        path = rpr_sub.resolve_path(node.path) if "{" not in node.path else ""
        if node.path.strip() and "{" not in node.path and not os.path.isfile(path):
            self._hint(f"⚠ Fisierul nu exista: {node.path}", None, self.C["warning"])
        self.button_row([
            ("📂 Deschide rutina", lambda: self.p.open_routine(path), None, "Deschide rutina apelata pentru editare"),
            ("📥 Inlocuieste cu pasii ei", lambda: self.p.expand_run_routine(node), None,
             "Copiaza pasii rutinei aici (nu mai urmaresc fisierul original)"),
        ])
        if path and os.path.isfile(path):
            self._hint("Pasii rutinei apelate (doar citire):", None, self.C["text_dim"])
            tv = self.p._steps_preview(self._host, 8)
            self.p._fill_steps_preview(tv, path)

    def button_row(self, buttons):
        row = tk.Frame(self._host, bg=self._host["bg"])
        row.pack(fill="x", padx=10, pady=(10, 4))
        for text, cmd, color, tip in buttons:
            self.p._btn(row, text, cmd, color=color, tip=tip).pack(side="left", padx=2)

    # ── pas ──
    def _build_node(self, node: RprNode):
        self._title(f"{icon_for(node)}  {tr(node.KIND_LABEL)}")
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
                if self.p.step_object_name(node):
                    self.button_row([("🎯 Remarcheaza", lambda: self.p.remark_step(node), None,
                                      "Pasul a gasit alt element? Da click pe elementul corect: obiectul primeste "
                                      "locatoarele noi (sau faci un obiect nou doar pentru acest pas)")])
        elif isinstance(node, SetVariableNode):
            self.text(node, "Numele variabilei", lambda: node.name, lambda v: setattr(node, "name", v.strip("{} ")), vars_=False)
            self._report_check(node, lambda: node.name)
            self.combo(node, "Operatie", VARIABLE_OPS, lambda: node.operation, lambda v: setattr(node, "operation", v), structural=True)
            op = node.operation
            if op == VariableOperation.Replace:
                self.text(node, "Cauta textul", lambda: node.find, lambda v: setattr(node, "find", v))
            if op in (VariableOperation.Set, VariableOperation.Append, VariableOperation.Replace,
                      VariableOperation.Increment, VariableOperation.Decrement):
                self.text(node, "Inlocuieste cu" if op == VariableOperation.Replace else "Valoare",
                          lambda: node.value, lambda v: setattr(node, "value", v))
        elif isinstance(node, IfNode):
            if node.optional:
                self._hint("Optional: asteapta scurt (timpul din conditie) sa apara mesajul / elementul. Daca apare, "
                           "ruleaza pasii din \"Atunci\"; daca nu apare, rutina merge mai departe fara eroare. "
                           "Pui pasul unde stii ca poate aparea ceva (ex. dupa ce inchizi browserul).")
            else:
                self._hint("Pasii din ramura \"Atunci\" ruleaza cand conditia e adevarata, cei din \"Altfel\" cand e falsa.")
            self.condition(node.condition, node)
        elif isinstance(node, RuleNode):
            self._hint("Regula e armata cand rutina ajunge aici si ramane activa pana la sfarsitul listei in care sta "
                       "(pune-o primul pas ca sa se aplice pe toata rutina). Daca un pas esueaza si regula se "
                       "potriveste, ruleaza pasii ei. Nu face nimic daca eroarea nu apare.")
            self.text(node, "Daca eroarea contine textul (gol = nu conteaza)", lambda: node.error_contains,
                      lambda v: setattr(node, "error_contains", v), vars_=False)
            self.check(node, "SAU: un element / o conditie e adevarata pe ecran (ex. fereastra de mesaj)",
                       lambda: node.use_element, lambda v: setattr(node, "use_element", v), structural=True)
            if node.use_element:
                self.condition(node.condition, node)
            self.combo(node, "Dupa ce ruleaza pasii regulii", RULE_AFTER, lambda: node.after,
                       lambda v: setattr(node, "after", v))
            self._hint("Mesajul erorii e in variabila {EroareRegula}. Pasii se pun in ramura \"Pasi de rulat\".")
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
            self.check(node, "Camp de tastat: valoarea scrisa intra in variabila (fara butoane)",
                       lambda: node.ask_value, lambda v: setattr(node, "ask_value", v))
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
        elif isinstance(node, RunRoutineNode):
            self._build_run_routine(node)
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
            self._hint("Pas pe coordonate de ecran (inregistrat cu ⏺ Ecran). Functioneaza, dar e fragil: daca fereastra se muta "
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
            options.append((ai.action, f"{tr(grp)}  ·  {tr(ai.label)}"))

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
            self._report_check(a, lambda: a.output_variable)
            self.text(a, "Valoarea asteptata (optional)", lambda: a.expected_value, lambda v: setattr(a, "expected_value", v))
            self._hint("Daca valoarea citita e diferita, rutina se opreste si te intreaba. * = orice text. "
                       "Ex: S:*  (orice mesaj de succes SAP),  {Rand.Status},  Salvat*")

        # 6. optiuni
        if info.needs_target or a.target.strip():
            self.number(a, "Asteapta obiectul maxim (ms)", lambda: a.timeout_ms, lambda v: setattr(a, "timeout_ms", v))
            self.check(a, "Mod direct (fara miscarea vizibila a mouse-ului, unde e posibil)",
                       lambda: a.direct_mode, lambda v: setattr(a, "direct_mode", v))
        buttons = [("▶ Testeaza pasul", lambda: self.p.test_node(a), self.C["success"],
                    "Executa doar acest pas acum (cu variabilele ultimei rulari)")]
        if info.needs_target or info.target_optional:
            buttons.append(("🎯 Remarcheaza", lambda: self.p.remark_step(a), None,
                            "Pasul a gasit alt element? Da click pe elementul corect: obiectul primeste "
                            "locatoarele noi (sau faci un obiect nou doar pentru acest pas)"))
        self.button_row(buttons)

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
        self.text(f, "Coloana cu linkul filmului (gol = fara)", lambda: f.extra.get("video_column", "Film"),
                  lambda v: f.extra.__setitem__("video_column", v.strip()), vars_=False)
        self._hint("Cand filmul e pornit (⚙ Setari → Video), fiecare rand primeste linkul spre film si minutul la "
                   "care incepe randul. Cu \"cate un film pe rand Excel\", fiecare rand are filmul lui.")
        self.check(f, "Coloreaza randurile (verde OK, rosu eroare)", lambda: f.color_rows, lambda v: setattr(f, "color_rows", v))
        self.check(f, "Salveaza Excel dupa fiecare rand (sigur la intreruperi)", lambda: f.save_after_each_row,
                   lambda v: setattr(f, "save_after_each_row", v))
        self.check(f, "La reluare, sari randurile deja marcate OK", lambda: f.skip_completed_rows,
                   lambda v: setattr(f, "skip_completed_rows", v))
        if info.error:
            self._hint(info.error, color=self.C["warning"])
        elif info.headers:
            self._hint(tr_template("Coloane gasite ({0} randuri cu date): {1}").format(info.data_rows,
                       ", ".join("{" + f.row_variable + "." + h + "}" for h in info.headers)))

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

        self._build_report_card(r)
        self._build_video_folder_card(r)

    # ── 🎥 folderul filmelor rutinei ──
    def _build_video_folder_card(self, r: Routine):
        card = self._card(title="🎥 Filmele rutinei")
        self.text(None, "Folderul filmelor (gol = cel din ⚙ Setari → Video)", lambda: rpr_report.video_folder(r),
                  lambda v: rpr_report.set_video_folder(r, v), vars_=False, host=card)

        def pick():
            d = filedialog.askdirectory(parent=self.p, title="Folderul filmelor")
            if d:
                rpr_report.set_video_folder(r, os.path.normpath(d))
                self._changed(None, structural=True)

        def onedrive():
            od = rpr_report.onedrive_folder()
            if not od:
                self.p.set_status("OneDrive nu e sincronizat pe acest PC (lipseste folderul OneDrive).")
                return
            rpr_report.set_video_folder(r, os.path.join(od, "AutoPilotDC", "filme", sanitize_name(r.name) or "Rutina"))
            self._changed(None, structural=True)
        row = tk.Frame(card, bg=card["bg"])
        row.pack(fill="x", padx=8, pady=2)
        self.p._btn(row, "📁 Alege folderul", pick).pack(side="left", padx=2)
        self.p._btn(row, "☁ OneDrive", onedrive, tip="Folder in OneDrive: filmele ajung singure si in cloud").pack(
            side="left", padx=2)
        self._hint("Filmul porneste cand e bifat in ⚙ Setari → Video (\"la fiecare rulare\") sau la pregatiri. "
                   "Fisierele se scriu din mers, deci si un film intrerupt ramane.", host=card)

    # ── 📊 raportul Excel al rularii (rpr/report.py) ──
    def _report_check(self, node, get_name):
        """Bifa de pe pas: valoarea variabilei apare ca o coloana in raportul Excel al rularii."""
        r = self.p.routine
        self.check(node, "📊 Pune valoarea in raportul Excel al rularii",
                   lambda: rpr_report.has_variable(r, get_name()),
                   lambda v: rpr_report.toggle_variable(r, get_name(), v))

    def _build_report_card(self, r: Routine):
        card = self._card(title="📊 Raport Excel al rularii (dovada muncii)")
        rs = rpr_report.ReportSettings.of(r)

        def upd(fn):
            def setter(v):
                s = rpr_report.ReportSettings.of(r)
                fn(s, v)
                s.save_to(r)
            return setter

        self.check(None, "Creeaza un raport Excel la fiecare rulare", lambda: rs.enabled,
                   upd(lambda s, v: setattr(s, "enabled", v)), host=card, structural=True)
        self._hint("Un fisier nou la fiecare rulare: un rand pentru fiecare rand Excel / repetare (sau unul pentru "
                   "toata rutina), cu ora de start, durata, statusul, valorile bifate, pasii parcursi, filmul si "
                   "captura erorii. Merge si fara un Excel de intrare.", host=card)
        if not rs.enabled:
            return
        self.text(None, "Folderul rapoartelor (gol = rezultate\\rapoarte)", lambda: rs.folder,
                  upd(lambda s, v: setattr(s, "folder", v.strip().strip('"'))), vars_=False, host=card)

        def pick():
            d = filedialog.askdirectory(parent=self.p, title="Folderul rapoartelor")
            if d:
                s = rpr_report.ReportSettings.of(r)
                s.folder = os.path.normpath(d)
                s.save_to(r)
                self._changed(None, structural=True)

        def open_folder():
            s = rpr_report.ReportSettings.of(r)
            folder = s.folder or os.path.join(RprPaths.output(), "rapoarte")
            os.makedirs(folder, exist_ok=True)
            try:
                os.startfile(folder)  # type: ignore[attr-defined]
            except Exception as ex:  # noqa: BLE001
                self.p.set_status(str(ex))
        def onedrive():
            od = rpr_report.onedrive_folder()
            if not od:
                self.p.set_status("OneDrive nu e sincronizat pe acest PC (lipseste folderul OneDrive).")
                return
            s = rpr_report.ReportSettings.of(r)
            s.folder = os.path.join(od, "AutoPilotDC", "rapoarte", sanitize_name(r.name) or "Rutina")
            s.save_to(r)
            self._changed(None, structural=True)
        row = tk.Frame(card, bg=card["bg"])
        row.pack(fill="x", padx=8, pady=2)
        self.p._btn(row, "📁 Alege folderul", pick).pack(side="left", padx=2)
        self.p._btn(row, "☁ OneDrive", onedrive,
                    tip="Folder in OneDrive: raportul ajunge singur si in cloud").pack(side="left", padx=2)
        self.p._btn(row, "Deschide folderul", open_folder).pack(side="left", padx=2)
        self._hint("Raportul se salveaza din mers, dupa fiecare rand / repetare: daca aplicatia se blocheaza sau "
                   "PC-ul se opreste, ramane tot ce s-a facut pana atunci.", host=card)

        self._caption("Coloane cu valori (bifeaza ce vrei sa apara in raport)", card)
        names = [v for v in self.p.known_variables(None) if v not in ("Azi", "Acum", "Acum:yyyyMMdd_HHmm", "NewLine")]
        names += [v for v in rs.variables if v.strip("{}").lower() not in {n.lower() for n in names}]
        if not names:
            self._hint("Nu exista inca variabile. Pasii care citesc valori (Citeste text...) si coloanele Excel apar aici.",
                       host=card)
        for name in names:
            self.check(None, name, lambda n=name: rpr_report.has_variable(r, n),
                       lambda v, n=name: rpr_report.toggle_variable(r, n, v), host=card)
        self.check(None, "Coloana \"Pasi parcursi\" (definitia fiecarui pas, pe element)", lambda: rs.steps_column,
                   upd(lambda s, v: setattr(s, "steps_column", v)), host=card)
        self.check(None, "Foaia \"Pasi\": fiecare pas executat, cu ora, rezultat si regula", lambda: rs.steps_sheet,
                   upd(lambda s, v: setattr(s, "steps_sheet", v)), host=card)
        self.check(None, "Definitia completa a rutinei in foaia \"Rutina\"", lambda: rs.definition_sheet,
                   upd(lambda s, v: setattr(s, "definition_sheet", v)), host=card)
        self._hint("Filmul apare in raport cand e pornit in ⚙ Setari → Video (\"la fiecare rulare\"). "
                   "Bifa 📊 exista si pe pasii care salveaza o valoare.", host=card)


# ==============================================================================
# 6. DIALOG OBIECT (nume, tehnologie, context, locatori)
# ==============================================================================
class DialogBase(tk.Toplevel):
    """Fereastra cu continut derulabil (roata mouse-ului + bara) si butoane fixe jos (self.bottom):
    nu mai trebuie marita ca sa ajungi la Salveaza / OK. Continutul se pune in self.body."""

    def __init__(self, panel):
        super().__init__(panel)
        C = panel.C
        self.configure(bg=C["bg_main"])
        self.transient(panel.winfo_toplevel())
        self.attributes("-topmost", True)
        self.bottom = tk.Frame(self, bg=C["bg_main"])
        self.bottom.pack(side="bottom", fill="x", padx=14, pady=(4, 10))
        self._canvas = tk.Canvas(self, bg=C["bg_main"], highlightthickness=0, borderwidth=0)
        self._vsb = ttk.Scrollbar(self, orient="vertical", command=self._canvas.yview)
        self._canvas.configure(yscrollcommand=self._vsb.set)
        self._vsb.pack(side="right", fill="y")
        self._canvas.pack(side="left", fill="both", expand=True)
        self.body = tk.Frame(self._canvas, bg=C["bg_main"])
        self._win = self._canvas.create_window((0, 0), window=self.body, anchor="nw")
        self.body.bind("<Configure>", lambda e: self._canvas.configure(scrollregion=self._canvas.bbox("all")))
        self._canvas.bind("<Configure>", lambda e: self._canvas.itemconfigure(self._win, width=e.width))
        self.bind("<MouseWheel>", self._wheel, add="+")
        self.bind("<Button-4>", lambda e: self._canvas.yview_scroll(-3, "units"), add="+")
        self.bind("<Button-5>", lambda e: self._canvas.yview_scroll(3, "units"), add="+")

    def _wheel(self, e):
        w = e.widget
        if isinstance(w, (ttk.Treeview, tk.Text, tk.Listbox)) or "listbox" in str(w).lower():
            return   # listele isi deruleaza continutul singure
        try:
            if self._canvas.bbox("all")[3] <= self._canvas.winfo_height():
                return   # incape intreg: nu e nimic de derulat
        except Exception:
            return
        self._canvas.yview_scroll(-1 if e.delta > 0 else 1, "units")

    def fit(self, width: Optional[int] = None, margin: int = 90):
        """Marimea ferestrei = cat cere continutul, dar nu mai mult decat ecranul (restul se deruleaza)."""
        self.update_idletasks()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        need_w = (width or self.body.winfo_reqwidth()) + 20
        need_h = self.body.winfo_reqheight() + self.bottom.winfo_reqheight() + 16
        w, h = min(max(need_w, 420), sw - 40), min(need_h, sh - margin)
        self.geometry(f"{w}x{h}+{max(0, (sw - w) // 2)}+{max(0, min(40, (sh - h) // 2))}")
        self.minsize(min(w, 420), min(h, 260))


class ObjectDialog(DialogBase):
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
            tk.Label(self.body, text=text, bg=C["bg_main"], fg=C["text_dim"], font=("Segoe UI", 10, "bold")).pack(
                anchor="w", padx=14, pady=(8, 1))
        cap("Nume (cum il alegi in pasi)")
        self.name = tk.StringVar(value=obj.name)
        tk.Entry(self.body, textvariable=self.name, **es).pack(fill="x", padx=14, ipady=3)
        cap("Tehnologie")
        self.tech = ttk.Combobox(self.body, values=[tr(l) for _, l in TECHNOLOGIES], state="readonly")
        self.tech.current(next((i for i, (v, _) in enumerate(TECHNOLOGIES) if v == obj.technology), 0))
        self.tech.pack(fill="x", padx=14)
        cap("Context (Web: link-ul paginii · Desktop: proces:nume.exe sau titlu · SAP: wnd[0])")
        self.context = tk.StringVar(value=obj.context)
        tk.Entry(self.body, textvariable=self.context, **es).pack(fill="x", padx=14, ipady=3)
        self.lib = LibraryFields(self.body, panel, obj)
        cap("Locatori (in ordinea de incercare; primul care gaseste exact UN element castiga)")
        self.loc_box = tk.Frame(self.body, bg=C["bg_main"])
        self.loc_box.pack(fill="x", padx=14)
        self.rows: List[Tuple[ttk.Combobox, tk.StringVar, tk.BooleanVar]] = []
        for l in obj.locators:
            self._add_row(l)
        panel._btn(self.body, "＋ Locator", lambda: self._add_row(Locator(LocatorKind.Css, ""))).pack(anchor="w", padx=14, pady=4)
        tk.Label(self.body, text="Web: TestId, Id, Role (button|Salveaza), Label, Name, Placeholder, Text, Css, XPath · "
                            "Desktop: AutomationId, UiaName (Button|OK), ClassName, UiaPath · SAP: SapId (wnd[0]/usr/...), SapName",
                 bg=C["bg_main"], fg=C["text_dim"], font=("Segoe UI", 9), wraplength=560, justify="left").pack(
            anchor="w", padx=14)
        row = tk.Frame(self.bottom, bg=C["bg_main"])
        row.pack(anchor="e")
        panel._btn(row, "💾 Salveaza", self._ok, color=C["success"]).pack(side="left", padx=3)
        panel._btn(row, "Anuleaza", self.destroy).pack(side="left", padx=3)
        self.fit(680)
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
        self.lib.apply()
        self.result = True
        self.destroy()


# ==============================================================================
# 6b. DIALOG "SCANARE SITE" (v4.9): alegi ce obiecte gasite intra in biblioteca
# ==============================================================================
class ScanReviewDialog(DialogBase):
    """result: None (anulat) / lista obiectelor alese, cu pagina si folderul puse (v4.11).
    Randul selectat se marcheaza in browser (👁), numele se pot edita (✎ / F2 / dublu-click),
    iar sus alegi pagina si folderul sub care intra obiectele in tree-ul bibliotecii."""

    def __init__(self, panel: "StudioPanel", objs: List[UiObject], existing: int = 0):
        super().__init__(panel)
        self.p, self.objs, self.result = panel, list(objs), None
        self.sel = [True] * len(self.objs)
        self._hl_job = None
        self._hl_msg: Optional[str] = None
        C = panel.C
        self.title("Scanare site")
        self.configure(bg=C["bg_main"])
        self.transient(panel.winfo_toplevel())
        self.attributes("-topmost", True)
        tk.Label(self.body, text="🔍  Obiecte gasite pe pagina", bg=C["bg_main"], fg=C["primary"],
                 font=("Segoe UI", 13, "bold")).pack(anchor="w", padx=14, pady=(12, 2))
        tk.Label(self.body, text=f"{len(self.objs)} obiecte noi, {existing} deja in biblioteca. "
                            f"Click pe un rand = il marchez in browser; bifa din prima coloana = il pastrezi / nu.",
                 bg=C["bg_main"], fg=C["text_dim"], font=("Segoe UI", 10), wraplength=860, justify="left").pack(
            anchor="w", padx=14)

        # unde intra in tree: Site · Pagina · Folder
        dest = tk.Frame(self.body, bg=C["bg_main"])
        dest.pack(fill="x", padx=14, pady=(8, 0))
        repo = panel.repo
        pages = sorted({o.page for o in repo.objects if o.page} | {o.page for o in self.objs if o.page}, key=str.lower)
        main_page = max(({o.page for o in self.objs if o.page} or {""}),
                        key=lambda pg: sum(1 for o in self.objs if o.page == pg))
        tk.Label(dest, text="Pagina", bg=C["bg_main"], fg=C["text_dim"], font=("Segoe UI", 10, "bold")).grid(
            row=0, column=0, sticky="w")
        tk.Label(dest, text="Folder (in tree-ul aplicatiei; subfolder: Comenzi/Export)", bg=C["bg_main"],
                 fg=C["text_dim"], font=("Segoe UI", 10, "bold")).grid(row=0, column=1, sticky="w", padx=(10, 0))
        self.page = ttk.Combobox(dest, values=pages, width=26)
        self.page.set(main_page)
        self.page.grid(row=1, column=0, sticky="ew")
        self.folder = ttk.Combobox(dest, values=rpr_scan.all_folders(repo), width=40)
        last_page, last_folder = panel._last_folder
        self.folder.set(last_folder if last_page == main_page else "")
        self.folder.grid(row=1, column=1, sticky="ew", padx=(10, 0))
        dest.columnconfigure(1, weight=1)

        box = tk.Frame(self.body, bg=C["bg_main"])
        box.pack(fill="both", expand=True, padx=14, pady=6)
        cols = ("sel", "nume", "tip", "locator")
        self.tree = ttk.Treeview(box, columns=cols, show="headings", style="Studio.Treeview", height=11,
                                 selectmode="browse")
        for c, title, w, stretch in [("sel", "✔", 34, False), ("nume", "Nume (dublu-click = editeaza)", 260, False),
                                     ("tip", "Tip", 90, False), ("locator", "Locator", 340, True)]:
            self.tree.heading(c, text=title, anchor="w")
            self.tree.column(c, width=w, stretch=stretch, anchor="w")
        vsb = ttk.Scrollbar(box, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        self.tree.pack(side="left", fill="both", expand=True)
        for i, o in enumerate(self.objs):
            best = next((l for l in o.locators if l.enabled), None)
            loc = f"{best.kind.value}: {best.value}" if best is not None else ""
            self.tree.insert("", "end", iid=str(i), values=("", o.name, o.object_type or o.element_type, loc[:120]))
        self.tree.bind("<ButtonRelease-1>", self._clicked)
        self.tree.bind("<Double-1>", lambda e: self._rename() if self.tree.identify_column(e.x) == "#2" else None)
        self.tree.bind("<space>", lambda e: (self._toggle(self.tree.selection()), "break")[1])
        self.tree.bind("<F2>", lambda e: (self._rename(), "break")[1])
        self.tree.bind("<<TreeviewSelect>>", lambda e: self._schedule_highlight())

        self._info = tk.Label(self.body, text="", bg=C["bg_main"], fg=C["text"], font=("Segoe UI", 10), anchor="w",
                              justify="left", wraplength=860)
        self._info.pack(fill="x", padx=14)
        row = tk.Frame(self.bottom, bg=C["bg_main"])
        row.pack(fill="x")
        panel._btn(row, "👁 Arata in browser", self._highlight_now,
                   tip="Marcheaza elementul selectat in browser (se face si singur la selectare)").pack(side="left", padx=2)
        panel._btn(row, "✎ Redenumeste", self._rename, tip="Schimba numele obiectului (F2)").pack(side="left", padx=2)
        panel._btn(row, "☑ Tine / scoate", lambda: self._toggle(self.tree.selection()),
                   tip="Bifeaza / debifeaza randul selectat (Space)").pack(side="left", padx=2)
        panel._btn(row, "Toate", lambda: self._set_all(True)).pack(side="left", padx=(10, 2))
        panel._btn(row, "Niciunul", lambda: self._set_all(False)).pack(side="left", padx=2)
        panel._btn(row, "Fara link-uri", self._no_links,
                   tip="Debifeaza link-urile (meniurile de navigare au de obicei multe)").pack(side="left", padx=2)
        self._ok_btn = panel._btn(row, "", self._ok, color=C["success"])
        self._ok_btn.pack(side="right", padx=2)
        panel._btn(row, "Anuleaza", self._cancel).pack(side="right", padx=2)
        self._refresh()
        self.fit(900)
        self.protocol("WM_DELETE_WINDOW", self._cancel)
        self.after(200, self._poll_info)
        self.grab_set()
        self.wait_window()

    # ── bifa / selectie ──
    def _refresh(self):
        for i in range(len(self.objs)):
            self.tree.set(str(i), "sel", "✔" if self.sel[i] else "")
        self._ok_btn.configure(text=f"💾 Adauga in biblioteca ({sum(self.sel)})")

    def _toggle(self, iids):
        for iid in iids:
            self.sel[int(iid)] = not self.sel[int(iid)]
        self._refresh()

    def _clicked(self, e):
        """Bifa din prima coloana tine / scoate; pe restul randului doar selectezi (si il marchez in browser)."""
        iid = self.tree.identify_row(e.y)
        if iid and self.tree.identify_region(e.x, e.y) == "cell" and self.tree.identify_column(e.x) == "#1":
            self._toggle([iid])

    def _set_all(self, on: bool):
        self.sel = [on] * len(self.objs)
        self._refresh()

    def _no_links(self):
        for i, o in enumerate(self.objs):
            if o.element_type == "a" or o.element_type.startswith("a ("):
                self.sel[i] = False
        self._refresh()

    def _current(self) -> Optional[UiObject]:
        s = self.tree.selection()
        return self.objs[int(s[0])] if s else None

    # ── marcare in browser ──
    def _schedule_highlight(self):
        if self._hl_job is not None:
            self.after_cancel(self._hl_job)
        self._hl_job = self.after(250, self._highlight_now)   # pauza: la sagetile sus / jos nu marcam fiecare rand

    def _highlight_now(self):
        self._hl_job = None
        o = self._current()
        if o is None:
            return
        web = self.p.web()
        self._info.configure(text=tr("Caut elementul in browser..."))

        def work():
            try:
                ok, msg = web.show_object(o, 3500)
            except Exception as ex:  # noqa: BLE001
                ok, msg = False, str(ex)
            self._hl_msg = ("👁 " + msg) if ok else ("⚠ " + msg + "\n" + tr("Deschide pagina / meniul lui si incearca din nou."))
        threading.Thread(target=work, daemon=True, name="ScanShow").start()

    def _poll_info(self):
        if not self.winfo_exists():
            return
        if self._hl_msg is not None:
            self._info.configure(text=self._hl_msg)
            self._hl_msg = None
        self.after(200, self._poll_info)

    # ── nume ──
    def _rename(self):
        o = self._current()
        if o is None:
            return
        new = input_dialog(self, "Redenumeste obiectul", "Nume nou (cum il alegi in pasi):", o.name, C=self.p.C)
        if new is None:
            return
        new = sanitize_name(new)
        if not new:
            return
        taken = {x.name.lower() for x in self.objs if x is not o} | {x.name.lower() for x in self.p.repo.objects}
        if new.lower() in taken:
            messagebox.showwarning("Redenumeste", f"Exista deja un obiect cu numele [{new}].", parent=self)
            return
        o.name = new
        self.tree.set(self.tree.selection()[0], "nume", new)

    # ── final ──
    def _cancel(self):
        self.result = None
        self.destroy()

    def _ok(self):
        page = self.page.get().strip()
        folder = rpr_scan.normalize_folder(self.folder.get())
        chosen = [o for o, on in zip(self.objs, self.sel) if on]
        for o in chosen:
            if page:
                o.page = page
            o.folder = folder
        self.p._last_folder = (page, folder)
        self.result = chosen
        self.destroy()


# ==============================================================================
# 7. DIALOG "OBIECT CAPTURAT" (dupa Spy): nume, locatori, captura, pas direct
# ==============================================================================
class ObjectReviewDialog(DialogBase):
    """result: None (anulat) / "save" / "click" / "type" / "read"."""

    def __init__(self, panel: StudioPanel, obj: UiObject):
        super().__init__(panel)
        self.p, self.obj, self.result = panel, obj, None
        C = panel.C
        self.title("Obiect capturat")
        self.configure(bg=C["bg_main"])
        self.transient(panel.winfo_toplevel())
        self.attributes("-topmost", True)
        tk.Label(self.body, text="🎯  Obiect capturat", bg=C["bg_main"], fg=C["primary"], font=("Segoe UI", 13, "bold")).pack(
            anchor="w", padx=14, pady=(12, 2))
        info = f"Tip: {obj.element_type or '-'}"
        if obj.captured_text:
            info += f"   ·   Text: \"{obj.captured_text[:60]}\""
        if obj.frame_path:
            info += f"   ·   in iframe: {' > '.join(obj.frame_path)}"
        tk.Label(self.body, text=info, bg=C["bg_main"], fg=C["text_dim"], font=("Segoe UI", 10), wraplength=620,
                 justify="left").pack(anchor="w", padx=14)

        # captura elementului
        self._img = None
        if obj.screenshot:
            try:
                img = tk.PhotoImage(file=os.path.join(RprPaths.object_images(), obj.screenshot))
                f = max(1, -(-img.width() // 600), -(-img.height() // 120))
                self._img = img.subsample(f, f) if f > 1 else img
                tk.Label(self.body, image=self._img, bg=C["bg_card"], bd=1, relief="solid").pack(anchor="w", padx=14, pady=6)
            except Exception:
                pass

        tk.Label(self.body, text="Nume (cum il alegi in pasi)", bg=C["bg_main"], fg=C["text_dim"],
                 font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=14, pady=(6, 1))
        self.name = tk.StringVar(value=panel.repo.make_unique_name(obj.name))
        tk.Entry(self.body, textvariable=self.name, bg=C["bg_input"], fg=C["text"], insertbackground=C["text"],
                 relief="flat", font=("Segoe UI", 11)).pack(fill="x", padx=14, ipady=3)
        self.lib = LibraryFields(self.body, panel, obj, compact=True)
        if obj.parent:
            tk.Label(self.body, text=f"▣ Elementul e in interiorul containerului [{obj.parent}] — va fi cautat acolo.",
                     bg=C["bg_main"], fg=C["accent"], font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=14)

        tk.Label(self.body, text="Locatori — primul care gaseste exact UN element castiga; daca pagina se schimba, se trece "
                            "automat la urmatorul. Debifeaza ce e instabil (ex: un text care se schimba).",
                 bg=C["bg_main"], fg=C["text_dim"], font=("Segoe UI", 9), wraplength=620, justify="left").pack(
            anchor="w", padx=14, pady=(10, 2))
        box = tk.Frame(self.body, bg=C["bg_main"])
        box.pack(fill="x", padx=14)
        self.rows = []
        for loc in obj.locators:
            r = tk.Frame(box, bg=C["bg_main"])
            r.pack(fill="x", pady=1)
            en = tk.BooleanVar(value=loc.enabled)
            tk.Checkbutton(r, variable=en, bg=C["bg_main"], selectcolor=C["bg_input"],
                           activebackground=C["bg_main"]).pack(side="left")
            color = "#3CCF6E" if loc.score >= 70 else "#FFC24B" if loc.score >= 40 else "#FF6B6B"
            tk.Label(r, text=f"{loc.score:>3}", bg=C["bg_main"], fg=color, font=("Consolas", 10, "bold"), width=4).pack(side="left")
            tk.Label(r, text=str(loc.kind), bg=C["bg_main"], fg=C["accent"], font=("Segoe UI", 10, "bold"), width=12,
                     anchor="w").pack(side="left")
            val = tk.StringVar(value=loc.value)
            tk.Entry(r, textvariable=val, bg=C["bg_input"], fg=C["text"], insertbackground=C["text"], relief="flat",
                     font=("Consolas", 9)).pack(side="left", fill="x", expand=True, padx=4, ipady=2)
            self.rows.append((loc, en, val))
        tk.Label(self.body, text="Scor: verde 70+ stabil · galben 40–69 acceptabil · rosu sub 40 fragil",
                 bg=C["bg_main"], fg=C["text_dim"], font=("Segoe UI", 9)).pack(anchor="w", padx=14, pady=(2, 0))

        row = tk.Frame(self.bottom, bg=C["bg_main"])
        row.pack(anchor="e")
        for text, res, color in [("💾 Salveaza", "save", C["primary"]), ("Salveaza + pas Click", "click", C["success"]),
                                 ("+ pas Scrie text", "type", C["success"]), ("+ pas Citeste", "read", C["success"])]:
            panel._btn(row, text, lambda r=res: self._ok(r), color=color).pack(side="left", padx=2)
        panel._btn(row, "Anuleaza", self.destroy).pack(side="left", padx=2)
        self.fit()
        self.grab_set()
        self.wait_window()

    def _ok(self, result: str):
        name = sanitize_name(self.name.get())
        if not name:
            messagebox.showwarning("Obiect", "Numele nu poate fi gol.", parent=self)
            return
        if self.p.repo.find(name) is not None:
            messagebox.showwarning("Obiect", f"Exista deja un obiect numit \"{name}\".", parent=self)
            return
        self.obj.name = name
        self.lib.apply()
        for loc, en, val in self.rows:
            loc.enabled, loc.value = en.get(), val.get().strip()
        self.obj.locators = [l for l in self.obj.locators if l.value]
        self.result = result
        self.destroy()


# ==============================================================================
# 8. BIBLIOTECA: campuri comune, alegere din lista, rezultatul testului, site-uri
# ==============================================================================
class LibraryFields:
    """Tip, site, pagina, container, link-uri valide, etichete — folosit in dialogurile de obiect."""

    def __init__(self, dlg: tk.Toplevel, panel: StudioPanel, obj: UiObject, compact: bool = False):
        self.p, self.obj = panel, obj
        C = panel.C
        f = tk.Frame(dlg, bg=C["bg_main"])
        f.pack(fill="x", padx=14, pady=(6, 0))
        es = dict(bg=C["bg_input"], fg=C["text"], insertbackground=C["text"], relief="flat", font=("Segoe UI", 10))
        repo = panel.repo
        sites = sorted({o.site for o in repo.objects if o.site} | {g.name for g in repo.sites} | ({obj.site} - {""}),
                       key=str.lower)
        banned = {obj.name.lower()} | {o.name.lower() for o in repo.objects
                                       if any(pp.name.lower() == obj.name.lower() for pp in repo.parent_chain(o))}
        containers = [""] + [o.name for o in sorted(repo.objects, key=lambda x: x.name.lower())
                             if o.is_container and o.name.lower() not in banned]

        def lbl(text, r, c, span=1):
            tk.Label(f, text=text, bg=C["bg_main"], fg=C["text_dim"], font=("Segoe UI", 10, "bold")).grid(
                row=r, column=c, columnspan=span, sticky="w", pady=(4, 0), padx=(0, 8))
        f.columnconfigure(0, weight=1, uniform="lib")
        f.columnconfigure(1, weight=1, uniform="lib")
        lbl("Tip", 0, 0)
        lbl("Container (cauta doar in interiorul lui)", 0, 1)
        self.type = ttk.Combobox(f, values=[tr(t) for t in OBJECT_TYPES], state="readonly")
        self.type.current(OBJECT_TYPES.index(obj.object_type) if obj.object_type in OBJECT_TYPES
                          else OBJECT_TYPES.index("Altul"))
        self.type.grid(row=1, column=0, sticky="ew", padx=(0, 8))
        self.parent = ttk.Combobox(f, values=containers)
        self.parent.set(obj.parent)
        self.parent.grid(row=1, column=1, sticky="ew")
        lbl("Site / aplicatie", 2, 0)
        lbl("Pagina", 2, 1)
        self.site = ttk.Combobox(f, values=sites)
        self.site.set(obj.site)
        self.site.grid(row=3, column=0, sticky="ew", padx=(0, 8))
        self.page = tk.StringVar(value=obj.page)
        tk.Entry(f, textvariable=self.page, **es).grid(row=3, column=1, sticky="ew", ipady=2)
        lbl("Folder (in tree-ul aplicatiei; subfolder: Comenzi/Export)", 4, 0, 2)
        self.folder = ttk.Combobox(f, values=rpr_scan.all_folders(repo))
        self.folder.set(obj.folder)
        self.folder.grid(row=5, column=0, columnspan=2, sticky="ew")
        self.urls = tk.StringVar(value=", ".join(obj.url_patterns))
        self.tags = tk.StringVar(value=", ".join(obj.tags))
        self.desc = tk.StringVar(value=obj.description)
        if not compact:
            lbl("Link-uri unde e valid (separate prin virgula; * = orice; gol = link-urile site-ului)", 6, 0, 2)
            tk.Entry(f, textvariable=self.urls, **es).grid(row=7, column=0, columnspan=2, sticky="ew", ipady=2)
            lbl("Etichete (separate prin virgula)", 8, 0)
            lbl("Descriere", 8, 1)
            tk.Entry(f, textvariable=self.tags, **es).grid(row=9, column=0, sticky="ew", padx=(0, 8), ipady=2)
            tk.Entry(f, textvariable=self.desc, **es).grid(row=9, column=1, sticky="ew", ipady=2)

    def apply(self):
        o = self.obj
        if self.type.current() >= 0:   # dupa index: tipul salvat e acelasi in orice limba
            o.object_type = OBJECT_TYPES[self.type.current()]
        o.parent = self.parent.get().strip()
        o.site = self.site.get().strip()
        o.page = self.page.get().strip()
        o.folder = rpr_scan.normalize_folder(self.folder.get())
        o.url_patterns = [u.strip() for u in self.urls.get().split(",") if u.strip()]
        o.tags = [t.strip() for t in self.tags.get().split(",") if t.strip()]
        o.description = self.desc.get().strip()


def list_dialog(parent, title: str, prompt: str, options: List[str], C=None) -> Optional[str]:
    C = C or {}
    dlg = tk.Toplevel(parent)
    dlg.title(title)
    dlg.configure(bg=C.get("bg_main", "#1E1E2E"))
    dlg.attributes("-topmost", True)
    res = {"v": None}
    tk.Label(dlg, text=prompt, bg=dlg["bg"], fg=C.get("text", "#FFF"), font=("Segoe UI", 10)).pack(anchor="w", padx=14, pady=(12, 4))
    lb = tk.Listbox(dlg, height=min(14, len(options)), width=50, bg=C.get("bg_input", "#333"), fg=C.get("text", "#FFF"),
                    selectbackground=C.get("primary", "#099"), font=("Segoe UI", 10), relief="flat")
    for o in options:
        lb.insert("end", o)
    lb.selection_set(0)
    lb.pack(padx=14, fill="both", expand=True)

    def ok(_e=None):
        sel = lb.curselection()
        res["v"] = options[sel[0]] if sel else None
        dlg.destroy()
    lb.bind("<Double-1>", ok)
    row = tk.Frame(dlg, bg=dlg["bg"])
    row.pack(anchor="e", padx=14, pady=10)
    tk.Button(row, text="OK", command=ok, bg=C.get("success", "#0A4"), fg="white", relief="flat", padx=14).pack(side="left", padx=3)
    tk.Button(row, text="Anuleaza", command=dlg.destroy, relief="flat", padx=10).pack(side="left", padx=3)
    dlg.grab_set()
    dlg.wait_window()
    return res["v"]


class CheckResultDialog(DialogBase):
    """Rezultatul 🩺 Verifica (v4.10): pe fiecare obiect ✅ merge / ⚠ impedimente / ❌ de recaptat.
    Fereastra nu blocheaza Studio: poti lucra in browser si apoi Verifica din nou."""

    def __init__(self, panel: "StudioPanel", rows, url: str):
        super().__init__(panel)
        self.p, self.rows = panel, []
        C = panel.C
        self.title("🩺 Verificare fara click")
        self.configure(bg=C["bg_main"])
        self.transient(panel.winfo_toplevel())
        self.attributes("-topmost", False)   # nu blocheaza: lucrezi in browser si apesi Verifica din nou
        tk.Label(self.body, text="🩺  Butoanele salvate pe pagina din browser", bg=C["bg_main"], fg=C["primary"],
                 font=("Segoe UI", 13, "bold")).pack(anchor="w", padx=14, pady=(12, 2))
        self._summary = tk.Label(self.body, text="", bg=C["bg_main"], fg=C["text_dim"], font=("Segoe UI", 10),
                                 justify="left", wraplength=760)
        self._summary.pack(anchor="w", padx=14)
        box = tk.Frame(self.body, bg=C["bg_main"])
        box.pack(fill="both", expand=True, padx=14, pady=6)
        cols = ("stare", "nume", "tip", "pagina", "motiv")
        self.tree = ttk.Treeview(box, columns=cols, show="headings", style="Studio.Treeview", height=10)
        for c, title, w, stretch in [("stare", "", 34, False), ("nume", "Nume", 200, False), ("tip", "Tip", 80, False),
                                     ("pagina", "Pagina", 110, False), ("motiv", "Ce am gasit", 380, True)]:
            self.tree.heading(c, text=title, anchor="w")
            self.tree.column(c, width=w, stretch=stretch, anchor="w")
        vsb = ttk.Scrollbar(box, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        self.tree.pack(side="left", fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", lambda e: self._show_detail())
        self.tree.bind("<Double-1>", lambda e: self._mark())
        self._detail = tk.Label(self.body, text="", bg=C["bg_main"], fg=C["text"], font=("Segoe UI", 10), justify="left",
                                wraplength=760, anchor="w")
        self._detail.pack(fill="x", padx=14)
        tk.Label(self.body, text="Simulare: aceleasi verificari ca la un click real (gasit, vizibil, activ, nu se misca, "
                            "nu e acoperit), dar fara apasare. Un element care apare doar dupa o actiune (meniu, tab) "
                            "se verifica dupa ce il deschizi in browser.",
                 bg=C["bg_main"], fg=C["text_dim"], font=("Segoe UI", 9), wraplength=760, justify="left").pack(
            anchor="w", padx=14, pady=(4, 0))
        row = tk.Frame(self.bottom, bg=C["bg_main"])
        row.pack(fill="x")
        panel._btn(row, "👁 Arata in browser", self._mark).pack(side="left", padx=2)
        panel._btn(row, "🔧 Repara locatorii", self._fix,
                   tip="Locatorul care merge trece primul (ceilalti raman)").pack(side="left", padx=2)
        panel._btn(row, "🎯 Recapteaza", self._recapture,
                   tip="Click pe element in browser; numele ramane, rutinele merg mai departe").pack(side="left", padx=2)
        panel._btn(row, "Inchide", self.destroy).pack(side="right", padx=2)
        panel._btn(row, "🔄 Verifica din nou", self._again, color=C["success"]).pack(side="right", padx=2)
        self.update_rows(rows)
        self.fit(820)

    def update_rows(self, rows):
        """rows: (obiect, rezultat, stare, motive). Un obiect deja in lista e actualizat pe loc."""
        by_name = {r[0].name: i for i, r in enumerate(self.rows)}
        for r in rows:
            if r[0].name in by_name:
                self.rows[by_name[r[0].name]] = r
            else:
                self.rows.append(r)
        self.tree.delete(*self.tree.get_children())
        order = {rpr_scan.REMAP: 0, rpr_scan.WARN: 1, rpr_scan.OK: 2, rpr_scan.OTHER_PAGE: 3}
        for i, (o, res, st, why) in sorted(enumerate(self.rows), key=lambda x: order.get(x[1][2], 9)):
            self.tree.insert("", "end", iid=str(i), values=(rpr_scan.STATUS_ICON.get(st, ""), o.name, o.object_type,
                                                            o.page + (f" › {o.folder}" if o.folder else ""),
                                                            why[0] if why else "Merge"))
        n = {k: sum(1 for r in self.rows if r[2] == k) for k in rpr_scan.STATUS_ICON}
        text = (f"✅ {n['ok']} merg   ⚠ {n['warn']} cu impedimente   ❌ {n['remap']} de recaptat")
        if n["other_page"]:
            text += f"   · {n['other_page']} pe alta pagina"
        self._summary.configure(text=text)
        self.lift()

    def _sel(self):
        s = self.tree.selection()
        return self.rows[int(s[0])] if s else None

    def _show_detail(self):
        r = self._sel()
        if r is None:
            return
        o, res, st, why = r
        lines = [f"[{o.name}]"] + [f"• {w}" for w in why] if why else [f"[{o.name}]: merge, nimic de semnalat."]
        if res.get("used") is not None:
            lines.append(f"Gasit prin: {res['used']}")
        self._detail.configure(text="\n".join(tr(x) for x in lines))

    def _mark(self):
        r = self._sel()
        if r is None:
            return
        web = self.p.web()
        threading.Thread(target=lambda: web.show_object(r[0]), daemon=True).start()

    def _fix(self):
        r = self._sel()
        if r is None:
            return
        o, res = r[0], r[1]
        if self.p.fix_object_locators(o, res.get("used")):
            self.p.recheck([o])
        else:
            messagebox.showinfo("🔧 Repara locatorii", "Aici nu am ce repara automat: primul locator merge deja "
                                                     "sau niciun locator nu gaseste elementul (atunci Recapteaza).",
                                parent=self)

    def _recapture(self):
        r = self._sel()
        if r is not None:
            self.p.recapture(r[0])

    def _again(self):
        self.p.recheck([r[0] for r in self.rows])


class TestResultDialog(DialogBase):
    """Rezultatul 🧪 Testeaza: obiectul gasit? cate elemente gaseste fiecare locator?"""

    def __init__(self, panel: StudioPanel, obj: UiObject, res: Dict[str, Any]):
        super().__init__(panel)
        C = panel.C
        self.title(f"Test: {obj.name}")
        self.configure(bg=C["bg_main"])
        self.attributes("-topmost", True)
        ok = res.get("found")
        web = obj.technology in (UiTechnology.Web, UiTechnology.WebSelenium)
        where = "pagina" if web else ("ecranul SAP" if obj.technology == UiTechnology.Sap else "fereastra")
        tk.Label(self.body, text=(("✔ Gasit pe pagina — e marcat in browser" if web else "✔ Gasit — e marcat pe ecran") if ok
                             else f"✖ Nu a fost gasit pe {where}"),
                 bg=C["bg_main"], fg="#3CCF6E" if ok else "#FF6B6B", font=("Segoe UI", 13, "bold")).pack(anchor="w", padx=14, pady=(12, 2))
        info = f"{'Pagina' if web else 'Unde'}: {res.get('url', '')}"
        if res.get("used") is not None:
            info += f"\nGasit prin: {res['used']}"
        if res.get("container"):
            info += (f"\nContainer [{res['container']}]: " + ("gasit — cautarea s-a facut in interiorul lui"
                                                                if res.get("container_found") else "NU a fost gasit pe pagina"))
        if web and not panel.repo.valid_on(obj, res.get("url", "")):
            info += f"\n⚠ Obiectul e definit pentru site-ul \"{obj.site}\", nu pentru aceasta pagina."
        tk.Label(self.body, text=info, bg=C["bg_main"], fg=C["text_dim"], font=("Segoe UI", 10), justify="left",
                 wraplength=640).pack(anchor="w", padx=14)
        grid = tk.Frame(self.body, bg=C["bg_main"])
        grid.pack(fill="x", padx=14, pady=8)
        heads = ["Locator", "Valoare", "In container", "In pagina" if web else "Gasite"]
        for c, h in enumerate(heads):
            tk.Label(grid, text=h, bg=C["bg_main"], fg=C["text_dim"], font=("Segoe UI", 10, "bold")).grid(row=0, column=c, sticky="w", padx=4)

        def cell(n, best_one=True):
            if n is None:
                return "—", C["text_dim"]
            return str(n), ("#3CCF6E" if n == 1 else "#FFC24B" if n > 1 else "#FF6B6B")
        for r, row in enumerate(res.get("rows", []), 1):
            loc = row["locator"]
            tk.Label(grid, text=str(loc.kind) + ("" if loc.enabled else " (inactiv)"), bg=C["bg_main"], fg=C["accent"],
                     font=("Segoe UI", 10, "bold")).grid(row=r, column=0, sticky="w", padx=4)
            tk.Label(grid, text=loc.value[:60], bg=C["bg_main"], fg=C["text"], font=("Consolas", 9)).grid(row=r, column=1, sticky="w", padx=4)
            for c, key in ((2, "in_container"), (3, "in_page")):
                t, col = cell(row.get(key))
                if row.get("error"):
                    t, col = "eroare", "#FF6B6B"
                tk.Label(grid, text=t, bg=C["bg_main"], fg=col, font=("Consolas", 10, "bold")).grid(row=r, column=c, padx=4)
        tk.Label(self.body, text="1 = exact elementul (bun) · mai multe = ambiguu (se ia primul) · 0 = nu gaseste. "
                            "Primul locator care gaseste exact UN element castiga.",
                 bg=C["bg_main"], fg=C["text_dim"], font=("Segoe UI", 9), wraplength=640, justify="left").pack(anchor="w", padx=14)
        row = tk.Frame(self.bottom, bg=C["bg_main"])
        row.pack(anchor="e")
        for text, action in [("➕ Pas Click", RprAction.Click), ("➕ Scrie text", RprAction.TypeText),
                             ("➕ Citeste", RprAction.ReadText)]:
            panel._btn(row, text, lambda a=action: (panel._obj_step(a, obj), self.destroy()), color=C["success"]).pack(side="left", padx=2)
        panel._btn(row, "👁 Marcheaza din nou", lambda: panel.show_object(obj), tip="Marcheaza elementul in browser 8 secunde").pack(side="left", padx=2)
        panel._btn(row, "✎ Editeaza locatorii", lambda: (self.destroy(), panel.edit_object())).pack(side="left", padx=2)
        panel._btn(row, "Inchide", self.destroy).pack(side="left", padx=2)
        self.fit(700)


class SitesDialog(DialogBase):
    """Site-uri / aplicatii si link-urile lor. Sisteme similare (test, productie, alt client) = acelasi site
    cu mai multe link-uri: obiectele lui merg pe toate."""

    def __init__(self, panel: StudioPanel):
        super().__init__(panel)
        self.p = panel
        C = panel.C
        self.title("Site-uri si link-uri")
        self.configure(bg=C["bg_main"])
        self.transient(panel.winfo_toplevel())
        self.attributes("-topmost", True)
        tk.Label(self.body, text="🌐  Site-uri si link-uri", bg=C["bg_main"], fg=C["primary"], font=("Segoe UI", 13, "bold")).pack(
            anchor="w", padx=14, pady=(12, 2))
        tk.Label(self.body, text="Un site grupeaza toate link-urile la care raspunde aceeasi aplicatie (ex: test + productie, "
                            "sau acelasi sistem la alt client). Obiectele din biblioteca ale site-ului merg pe toate link-urile lui. "
                            "Un link pe rand; * = orice (ex: *.portal.siemens.com/app/*).",
                 bg=C["bg_main"], fg=C["text_dim"], font=("Segoe UI", 10), wraplength=640, justify="left").pack(anchor="w", padx=14)
        body = tk.Frame(self.body, bg=C["bg_main"])
        body.pack(fill="both", expand=True, padx=14, pady=8)
        self.lb = tk.Listbox(body, width=26, height=12, bg=C["bg_input"], fg=C["text"], selectbackground=C["primary"],
                             font=("Segoe UI", 10), relief="flat", exportselection=False)
        self.lb.pack(side="left", fill="y")
        self.lb.bind("<<ListboxSelect>>", lambda e: self._load())
        right = tk.Frame(body, bg=C["bg_main"])
        right.pack(side="left", fill="both", expand=True, padx=(10, 0))
        es = dict(bg=C["bg_input"], fg=C["text"], insertbackground=C["text"], relief="flat", font=("Segoe UI", 10))
        tk.Label(right, text="Nume", bg=C["bg_main"], fg=C["text_dim"], font=("Segoe UI", 10, "bold")).pack(anchor="w")
        self.name = tk.StringVar()
        tk.Entry(right, textvariable=self.name, **es).pack(fill="x", ipady=2)
        tk.Label(right, text="Link-uri (unul pe rand)", bg=C["bg_main"], fg=C["text_dim"], font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(6, 0))
        self.urls = tk.Text(right, height=7, width=50, **es)
        self.urls.pack(fill="both", expand=True)
        tk.Label(right, text="Descriere", bg=C["bg_main"], fg=C["text_dim"], font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(6, 0))
        self.desc = tk.StringVar()
        tk.Entry(right, textvariable=self.desc, **es).pack(fill="x", ipady=2)
        row = tk.Frame(right, bg=C["bg_main"])
        row.pack(anchor="w", pady=6)
        panel._btn(row, "＋ Site nou", self._new).pack(side="left", padx=2)
        panel._btn(row, "💾 Aplica", self._apply, color=C["success"]).pack(side="left", padx=2)
        panel._btn(row, "🗑 Sterge", self._delete).pack(side="left", padx=2)
        panel._btn(row, "Grupeaza obiectele dupa link-uri", self._reclassify).pack(side="left", padx=2)
        panel._btn(self.bottom, "Inchide", self.destroy).pack(anchor="e")
        self._cur: Optional[SiteGroup] = None
        self._fill()
        self.fit()
        self.grab_set()
        self.wait_window()

    def _fill(self):
        self.lb.delete(0, "end")
        for g in self.p.repo.sites:
            self.lb.insert("end", g.name)

    def _load(self):
        sel = self.lb.curselection()
        if not sel:
            return
        g = self.p.repo.sites[sel[0]]
        self._cur = g
        self.name.set(g.name)
        self.urls.delete("1.0", "end")
        self.urls.insert("1.0", "\n".join(g.url_patterns))
        self.desc.set(g.description)

    def _new(self):
        g = SiteGroup(name="Site nou", url_patterns=[])
        try:
            if self.p.web().is_open:
                host = __import__("rpr.model", fromlist=["split_url"]).split_url(self.p.web().current_url())[0]
                if host:
                    g.name, g.url_patterns = host, [host]
        except Exception:
            pass
        self.p.repo.sites.append(g)
        self._fill()
        self.lb.selection_set(len(self.p.repo.sites) - 1)
        self._load()

    def _apply(self):
        g = self._cur
        if g is None:
            return
        old = g.name
        g.name = self.name.get().strip() or old
        g.url_patterns = [u.strip() for u in self.urls.get("1.0", "end").splitlines() if u.strip()]
        g.description = self.desc.get().strip()
        if old != g.name:   # obiectele site-ului vechi trec la numele nou
            for o in self.p.repo.objects:
                if o.site == old:
                    o.site = g.name
        self.p.save_repository()
        self._fill()
        self.p.set_status(f"Site-ul \"{g.name}\" salvat ({len(g.url_patterns)} link-uri).")

    def _delete(self):
        g = self._cur
        if g is None:
            return
        if messagebox.askyesno("Site-uri", f"Stergi site-ul \"{g.name}\"? Obiectele raman (cu numele site-ului).", parent=self):
            self.p.repo.sites.remove(g)
            self._cur = None
            self.p.save_repository()
            self._fill()

    def _reclassify(self):
        """Obiectele capturate pe link-urile unui site trec in acel site."""
        n = 0
        for o in self.p.repo.objects:
            if o.context:
                site = self.p.repo.site_for_url(o.context)
                if site and site != o.site and self.p.repo.find_site(site) is not None:
                    o.site = site
                    n += 1
        self.p.save_repository()
        messagebox.showinfo("Site-uri", f"{n} obiecte au fost mutate in site-urile lor.", parent=self)


# ==============================================================================
# 9. PROGRAMARE (Windows Task Scheduler)
# ==============================================================================
class ScheduleDialog(DialogBase):
    """Programeaza rutina curenta + lista programarilor AutoPilot + istoricul rularilor programate."""

    def __init__(self, panel: StudioPanel, routine_path: str, routine_name: str):
        super().__init__(panel)
        import datetime as dt
        from rpr import schedule as sch
        self.p, self.sch, self.path, self.rname = panel, sch, routine_path, routine_name
        C = panel.C
        self.title("Programare rutine")
        self.configure(bg=C["bg_main"])
        self.transient(panel.winfo_toplevel())
        tk.Label(self.body, text="🕒  Programeaza rutina", bg=C["bg_main"], fg=C["primary"],
                 font=("Segoe UI", 13, "bold")).pack(anchor="w", padx=14, pady=(12, 0))
        tk.Label(self.body, text=f"{routine_name}  ·  {routine_path}", bg=C["bg_main"], fg=C["text"],
                 font=("Segoe UI", 10, "bold"), wraplength=740, justify="left").pack(anchor="w", padx=14)
        tk.Label(self.body, text="Rutina ruleaza fara Studio, cu chenarul RUN si \"Nu deranja\" (daca e activ in rutina). "
                            "Calculatorul trebuie sa fie pornit si tu autentificat (rutinele folosesc ecranul). "
                            "La final apare un mesaj in coltul ecranului; logul ramane in folderul de rezultate.",
                 bg=C["bg_main"], fg=C["text_dim"], font=("Segoe UI", 10), wraplength=740, justify="left").pack(
            anchor="w", padx=14, pady=(2, 6))

        f = tk.Frame(self.body, bg=C["bg_main"])
        f.pack(fill="x", padx=14)
        es = dict(bg=C["bg_input"], fg=C["text"], insertbackground=C["text"], relief="flat", font=("Segoe UI", 10))

        def lbl(t, c):
            tk.Label(f, text=t, bg=C["bg_main"], fg=C["text_dim"], font=("Segoe UI", 10, "bold")).grid(
                row=0, column=c, sticky="w", padx=(0, 10))
        lbl("Cand", 0)
        lbl("Ora (HH:mm)", 1)
        lbl("Data (zz.ll.aaaa)", 2)
        lbl("La fiecare (minute)", 3)
        self.kind = ttk.Combobox(f, values=[tr(k) for k in sch.KINDS], state="readonly", width=30)
        self.kind.current(1)
        self.kind.grid(row=1, column=0, sticky="w", padx=(0, 10))
        self.kind.bind("<<ComboboxSelected>>", lambda e: self._sync())
        self.time = tk.StringVar(value="08:00")
        tk.Entry(f, textvariable=self.time, width=8, **es).grid(row=1, column=1, sticky="w", padx=(0, 10), ipady=2)
        self.date = tk.StringVar(value=(dt.date.today() + dt.timedelta(days=1)).strftime("%d.%m.%Y"))
        self.date_e = tk.Entry(f, textvariable=self.date, width=12, **es)
        self.date_e.grid(row=1, column=2, sticky="w", padx=(0, 10), ipady=2)
        self.every = tk.StringVar(value="60")
        self.every_e = tk.Entry(f, textvariable=self.every, width=6, **es)
        self.every_e.grid(row=1, column=3, sticky="w", ipady=2)
        days = tk.Frame(self.body, bg=C["bg_main"])
        days.pack(anchor="w", padx=14, pady=(6, 0))
        tk.Label(days, text="Zile:", bg=C["bg_main"], fg=C["text_dim"], font=("Segoe UI", 10, "bold")).pack(side="left")
        self.days = []
        for i, d in enumerate(sch.DAY_LABELS):
            v = tk.BooleanVar(value=i < 5)
            cb = tk.Checkbutton(days, text=d, variable=v, bg=C["bg_main"], fg=C["text"], selectcolor=C["bg_input"],
                                activebackground=C["bg_main"])
            cb.pack(side="left")
            self.days.append((v, cb))
        name_row = tk.Frame(self.body, bg=C["bg_main"])
        name_row.pack(fill="x", padx=14, pady=(6, 0))
        tk.Label(name_row, text="Numele programarii", bg=C["bg_main"], fg=C["text_dim"],
                 font=("Segoe UI", 10, "bold")).pack(side="left")
        self.task_name = tk.StringVar(value=sanitize_name(routine_name))
        tk.Entry(name_row, textvariable=self.task_name, width=34, **es).pack(side="left", padx=8, ipady=2)
        tk.Label(name_row, text="(acelasi nume = inlocuieste programarea)", bg=C["bg_main"], fg=C["text_dim"],
                 font=("Segoe UI", 9)).pack(side="left")
        row = tk.Frame(self.body, bg=C["bg_main"])
        row.pack(anchor="w", padx=14, pady=8)
        panel._btn(row, "✔ Creeaza programarea", self._create, color=C["success"]).pack(side="left", padx=2)
        panel._btn(row, "Deschide Task Scheduler", sch.open_task_scheduler).pack(side="left", padx=2)

        nb = ttk.Notebook(self.body)
        nb.pack(fill="both", expand=True, padx=14, pady=(4, 6))
        t1 = tk.Frame(nb, bg=C["bg_main"])
        t2 = tk.Frame(nb, bg=C["bg_main"])
        nb.add(t1, text="Programari AutoPilot")
        nb.add(t2, text="Istoric rulari programate")
        self.tasks = ttk.Treeview(t1, columns=("next", "last", "res", "status"), show="tree headings", height=7,
                                  style="Studio.Treeview")
        for col, text, w in (("#0", "Programare", 170), ("next", "Urmatoarea rulare", 140), ("last", "Ultima rulare", 140),
                             ("res", "Rezultat", 150), ("status", "Stare", 90)):
            self.tasks.heading(col, text=text, anchor="w")
            self.tasks.column(col, width=w, stretch=col == "res")
        self.tasks.pack(fill="both", expand=True)
        r2 = tk.Frame(t1, bg=C["bg_main"])
        r2.pack(anchor="w", pady=4)
        panel._btn(r2, "▶ Ruleaza acum", self._run_now).pack(side="left", padx=2)
        panel._btn(r2, "🗑 Sterge programarea", self._delete).pack(side="left", padx=2)
        panel._btn(r2, "↻ Reimprospateaza", self._refresh).pack(side="left", padx=2)
        self.hist = ttk.Treeview(t2, columns=("rez", "durata", "mesaj"), show="tree headings", height=7,
                                 style="Studio.Treeview")
        for col, text, w in (("#0", "Pornita / rutina", 230), ("rez", "Rezultat", 70), ("durata", "Durata", 60),
                             ("mesaj", "Mesaj", 330)):
            self.hist.heading(col, text=text, anchor="w")
            self.hist.column(col, width=w, stretch=col == "mesaj")
        self.hist.pack(fill="both", expand=True)
        self.hist.bind("<Double-1>", self._open_log)
        tk.Label(t2, text="Dublu click = deschide logul rularii.", bg=C["bg_main"], fg=C["text_dim"],
                 font=("Segoe UI", 9)).pack(anchor="w")
        panel._btn(self.bottom, "Inchide", self.destroy).pack(anchor="e")
        self._hist_items: List[dict] = []
        self.fit(780)
        self._sync()
        self.after(50, self._refresh)

    def _sync(self):
        k = self.kind.current()
        for v, cb in self.days:
            cb.configure(state="normal" if k == 2 else "disabled")
        self.every_e.configure(state="normal" if k == 4 else "disabled")
        self.date_e.configure(state="normal" if k in (3, 4) else "disabled")

    def _create(self):
        import datetime as dt
        k = self.kind.current()
        try:
            hh, mm = (int(x) for x in self.time.get().strip().split(":"))
            d = dt.datetime.strptime(self.date.get().strip(), "%d.%m.%Y") if k in (3, 4) else dt.datetime.now()
            at = d.replace(hour=hh, minute=mm, second=0, microsecond=0)
        except ValueError:
            messagebox.showerror("Programare", "Ora trebuie sa fie de forma 08:30, iar data de forma 25.12.2026.",
                                 parent=self)
            return
        if k == 3 and at < dt.datetime.now():
            messagebox.showerror("Programare", "Data si ora sunt in trecut.", parent=self)
            return
        try:
            every = int(self.every.get() or 0)
        except ValueError:
            every = 0
        days = [i for i, (v, _) in enumerate(self.days) if v.get()]
        try:
            ok, out, name = self.sch.create(self.path, self.rname, k, at, days, every, self.task_name.get())
        except ValueError as ex:
            messagebox.showerror("Programare", str(ex), parent=self)
            return
        if ok:
            self.p.set_status(f"🕒 Programare creata: {name}")
            messagebox.showinfo("Programare", f"Programare creata: {name}\n\n{out}", parent=self)
        else:
            messagebox.showerror("Programare", f"Programarea nu a putut fi creata:\n\n{out}", parent=self)
        self._refresh()

    def _refresh(self):
        """Lista din Task Scheduler se citeste pe alt fir (schtasks dureaza cateva secunde)."""
        self.tasks.delete(*self.tasks.get_children())
        self.tasks.insert("", "end", iid="__load", text="Se incarca...", values=("", "", "", ""))
        box: Dict[str, Any] = {}

        def work():
            try:
                box["tasks"] = self.sch.list_tasks()
            except Exception:  # noqa: BLE001
                box["tasks"] = []

        def fill():
            if "tasks" not in box:
                if self.winfo_exists():
                    self.after(200, fill)
                return
            if not self.winfo_exists():
                return
            self.tasks.delete(*self.tasks.get_children())
            for t in box["tasks"]:
                self.tasks.insert("", "end", iid=t.name, text=t.short,
                                  values=(t.next_run, t.last_run, t.last_result, t.status))
            if not box["tasks"]:
                self.tasks.insert("", "end", iid="__none", text="(nicio programare)", values=("", "", "", ""))
        threading.Thread(target=work, daemon=True).start()
        self.after(200, fill)
        self.hist.delete(*self.hist.get_children())
        self._hist_items = self.sch.load_history()
        for i, h in enumerate(self._hist_items):
            self.hist.insert("", "end", iid=str(i), text=f"{h.get('pornita', '')}  {h.get('rutina', '')}",
                             values=("✔" if h.get("succes") else "✖", f"{h.get('durata_s', 0)} s", h.get("mesaj", "")))

    def _sel_task(self):
        sel = self.tasks.selection()
        return sel[0] if sel and not sel[0].startswith("__") else None

    def _run_now(self):
        name = self._sel_task()
        if name:
            ok, out = self.sch.run_now(name)
            (messagebox.showinfo if ok else messagebox.showerror)("Programare", out, parent=self)
            self.after(1500, self._refresh)

    def _delete(self):
        name = self._sel_task()
        if name and messagebox.askyesno("Programare", f"Stergi programarea {name}?", parent=self):
            ok, out = self.sch.delete(name)
            if not ok:
                messagebox.showerror("Programare", out, parent=self)
            self._refresh()

    def _open_log(self, _e=None):
        sel = self.hist.selection()
        if sel:
            log = self._hist_items[int(sel[0])].get("log", "")
            if log and os.path.exists(log):
                os.startfile(log)
