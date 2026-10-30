# -*- coding: utf-8 -*-
# ============================================================
# AutoPilot DC — 🎯 Completeaza obiectele (v4.16.3)
# Dupa 📥 Import AI obiectele au doar locatoare deduse din text (buton "OK", camp "Nume").
# Fereastra le ia pe rand pe pagina reala:
#   🧪 Verifica toate  — pe pagina deschisa, fara click (aceleasi verificari ca 🩺 Verifica)
#   🎯 Marcheaza       — click pe element in browser (sau F2 in SAP / Desktop); obiectul primeste
#                        locatoarele capturate (id, css, xpath, frame), iar cele vechi raman de rezerva
# Numele obiectului nu se schimba, deci pasii rutinei raman legati de el.
# ============================================================

import threading
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Dict, List, Optional

import ui_theme
from rpr.model import Routine, UiObject, UiTechnology
from rpr.storage import RprPaths

try:
    from i18n import tr, tr_template
except Exception:  # noqa: BLE001
    def tr(s):
        return s

    def tr_template(s):
        return s

FONT = "Segoe UI"
_WEB = (UiTechnology.Web, UiTechnology.WebSelenium)


def objects_of_routine(routine: Routine, repo) -> List[UiObject]:
    """Obiectele folosite de rutina, in ordinea pasilor, fiecare o data."""
    out, seen = [], set()
    for name in routine.referenced_objects():
        obj = repo.find(name)
        if obj is not None and id(obj) not in seen:
            seen.add(id(obj))
            out.append(obj)
    return out


def merge_captured(obj: UiObject, captured: UiObject) -> int:
    """Locatoarele capturate cu Spy intra primele; cele vechi (alt tip / alta valoare) raman dupa ele, de rezerva.
    Numele, descrierea, folderul si containerul raman ale obiectului. Intoarce cate locatoare noi a primit."""
    new = [l for l in captured.locators]
    keys = {(str(l.kind), l.value) for l in new}
    old = [l for l in obj.locators if (str(l.kind), l.value) not in keys]
    obj.locators = new + old
    for f in ("frame_path", "element_type", "attributes", "screenshot", "context", "technology"):
        v = getattr(captured, f, None)
        if v:
            setattr(obj, f, v)
    if captured.captured_text and not obj.captured_text:
        obj.captured_text = captured.captured_text
    if captured.object_type and not obj.object_type:
        obj.object_type = captured.object_type
    return len(new)


def has_variables(obj: UiObject) -> bool:
    return any("{" in l.value for l in obj.locators)


class CompleteObjectsDialog(tk.Toplevel):
    """Lista obiectelor rutinei, cu starea fiecaruia pe pagina reala si 🎯 pentru cele negasite."""

    def __init__(self, panel, objects: Optional[List[UiObject]] = None):
        super().__init__(panel)
        self.p = panel
        self.C = C = panel.C
        self.objs: List[UiObject] = objects if objects is not None else objects_of_routine(panel.routine, panel.repo)
        self.state: Dict[int, str] = {}
        self._job: Optional[dict] = None
        self.title("🎯 Completeaza obiectele")
        self.configure(bg=C["bg_main"])
        self.attributes("-topmost", True)
        ui_theme.fit_window(self, 760, 520)

        tk.Label(self, text="🎯  Completeaza obiectele rutinei pe pagina reala", bg=C["bg_main"], fg=C["primary"],
                 font=(FONT, 12, "bold"), anchor="w").pack(fill="x", padx=14, pady=(12, 2))
        ui_theme.autowrap(tk.Label(
            self, text="1. Deschide in browser pagina pe care apar obiectele (sau ruleaza rutina ⏭ Pas cu pas pana "
                       "acolo).   2. 🧪 Verifica toate: fara click, vezi ce se gaseste.   3. Pe cele cu ✖ sau ⚠: "
                       "🎯 Marcheaza si da click pe element. Obiectul primeste locatoarele capturate, iar textul vechi "
                       "ramane de rezerva. Pasii rutinei nu se schimba.",
            bg=C["bg_main"], fg=C["text_dim"], font=(FONT, 10), justify="left", anchor="w")).pack(fill="x", padx=14)

        foot = tk.Frame(self, bg=C["bg_main"])
        foot.pack(side="bottom", fill="x", padx=12, pady=(4, 12))
        self.btn_check = self._b(foot, "🧪 Verifica toate", self.check_all, C["primary"])
        self.btn_check.pack(side="left", padx=2)
        self.btn_mark = self._b(foot, "🎯 Marcheaza in browser", self.mark, C["success"])
        self.btn_mark.pack(side="left", padx=2)
        self._b(foot, "⏭ Urmatorul negasit", self.next_missing).pack(side="left", padx=2)
        self._b(foot, "Inchide", self.destroy).pack(side="right", padx=2)
        self.summary = tk.Label(self, text="", bg=C["bg_main"], fg=C["text"], font=(FONT, 10, "bold"), anchor="w")
        self.summary.pack(side="bottom", fill="x", padx=14)

        box = tk.Frame(self, bg=C["bg_main"])
        box.pack(fill="both", expand=True, padx=12, pady=6)
        self.tree = ttk.Treeview(box, columns=("text", "state"), show="tree headings", style="Studio.Treeview",
                                 selectmode="browse", height=8)
        self.tree.heading("#0", text="Obiect")
        self.tree.heading("text", text="Text / locator")
        self.tree.heading("state", text="Stare")
        self.tree.column("#0", width=230)
        self.tree.column("text", width=250)
        self.tree.column("state", width=200)
        ys = ttk.Scrollbar(box, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=ys.set)
        ys.pack(side="right", fill="y")
        self.tree.pack(side="left", fill="both", expand=True)
        self.tree.bind("<Double-1>", lambda e: self.mark())
        self._fill()
        if self.objs:
            self.tree.selection_set("0")
        self.protocol("WM_DELETE_WINDOW", self.destroy)

    def _b(self, parent, text, cmd, color=None):
        return self.p._btn(parent, text, cmd, color=color)

    # ── lista ──
    def _fill(self):
        self.tree.delete(*self.tree.get_children())
        for i, o in enumerate(self.objs):
            hint = o.captured_text or (o.active_locators[0].value if o.active_locators else "")
            st = self.state.get(i) or (tr("variabila: se verifica la rulare") if has_variables(o) else "—")
            self.tree.insert("", "end", iid=str(i), text=o.name, values=(hint[:60], st))
        self._summary()

    def _set(self, i: int, text: str):
        self.state[i] = text
        if self.tree.exists(str(i)):
            self.tree.set(str(i), "state", text)
        self._summary()

    def _summary(self):
        ok = sum(1 for s in self.state.values() if s.startswith(("✔", "🎯")))
        bad = sum(1 for s in self.state.values() if s.startswith(("✖", "⚠")))
        self.summary.configure(text=tr_template("{0} obiecte · {1} bune · {2} de marcat").format(len(self.objs), ok, bad))

    def _selected(self) -> Optional[int]:
        sel = self.tree.selection()
        return int(sel[0]) if sel else None

    def next_missing(self):
        start = (self._selected() or -1) + 1
        order = list(range(start, len(self.objs))) + list(range(0, start))
        for i in order:
            if self.state.get(i, "").startswith(("✖", "⚠")) or (i not in self.state and not has_variables(self.objs[i])):
                self.tree.selection_set(str(i))
                self.tree.see(str(i))
                return
        self.p.set_status(tr("Toate obiectele verificate sunt bune."))

    # ── lucru in fundal (driverele nu se apeleaza din Tk) ──
    def _busy(self) -> bool:
        if self._job is not None or self.p.busy:
            self.p.set_status(tr("Asteapta sa se termine operatia curenta."))
            return True
        return False

    def _run(self, work, done):
        job = {"result": None, "error": None, "done": False}
        self._job = job

        def target():
            try:
                job["result"] = work()
            except Exception as ex:  # noqa: BLE001
                job["error"] = str(ex)
            job["done"] = True
        threading.Thread(target=target, daemon=True, name="Completeaza").start()

        def poll():
            if not job["done"]:
                self.after(150, poll)
                return
            self._job = None
            if self.winfo_exists():
                done(job["result"], job["error"])
        self.after(150, poll)

    def _driver(self, obj: UiObject):
        return self.p.web() if obj.technology in _WEB else self.p.drivers.get(obj.technology)

    # ── 🧪 Verifica toate (fara click) ──
    def check_all(self):
        if self._busy():
            return
        objs = [(i, o) for i, o in enumerate(self.objs) if not has_variables(o)]
        if any(o.technology in _WEB for _, o in objs):
            url = self.p._ask_url_if_closed()
            if url is False:
                return
            if url:
                self._run(lambda: self.p.web().open(url), lambda r, e: self.check_all() if not e else
                          messagebox.showerror("🎯", e, parent=self))
                return
        for _, o in objs:
            self.p.repo.link_parents(o)
        self.p.set_status(tr("🧪 Verific obiectele pe pagina deschisa, fara click..."))

        def work():
            out = []
            for i, o in objs:
                try:
                    d = self._driver(o)
                    res = d.check_object(o) if o.technology in _WEB else d.test_object(o)
                except Exception as ex:  # noqa: BLE001
                    res = {"found": False, "error": str(ex)}
                out.append((i, res))
            return out

        def done(results, error):
            if error:
                messagebox.showerror("🎯", error, parent=self)
                return
            for i, res in results or []:
                self._set(i, self._state_of(res))
            self.p.set_status(tr("Verificare terminata: marcheaza cu 🎯 obiectele cu ✖ sau ⚠."))
            self.next_missing()
        self._run(work, done)

    @staticmethod
    def _state_of(res: dict) -> str:
        if not res.get("found"):
            return "✖ " + tr("negasit pe pagina")
        counts = [n for _, n in res.get("counts", []) if isinstance(n, int) and n > 0]
        if counts and min(counts) > 1:
            return "⚠ " + tr_template("{0} elemente la fel").format(min(counts))
        return "✔ " + tr("gasit")

    # ── 🎯 Marcheaza (Spy pentru obiectul ales) ──
    def mark(self):
        i = self._selected()
        if i is None or self._busy():
            return
        obj = self.objs[i]
        web = obj.technology in _WEB
        url = None
        if web:
            url = self.p._ask_url_if_closed()
            if url is False:
                return
        driver = self._driver(obj)
        self.p.busy = True
        self.p._spy_driver = None if web else driver
        self.p._show_spy_hint(tr_template("🎯 [{0}]: du mouse-ul peste element si da CLICK (SAP / Desktop: F2). "
                                          "Esc = anuleaza.").format(obj.name))
        self.withdraw()

        def work():
            if url:
                driver.open(url)
            hint = "Click = captureaza · Esc = anuleaza" if web else "F2 = captureaza · Esc = anuleaza"
            return driver.capture_object(hint, RprPaths.object_images())

        def done(captured, error):
            self.p.busy = False
            self.p._hide_spy_hint()
            self.deiconify()
            self.lift()
            if error:
                messagebox.showerror("🎯", error, parent=self)
                return
            if captured is None:
                self.p.set_status(tr("Marcare anulata."))
                return
            n = merge_captured(obj, captured)
            if obj.context:
                self.p.repo.classify(obj)
            self.p.save_repository()
            self.p.refresh_objects()
            self._set(i, "🎯 " + tr_template("marcat: {0} locatoare noi").format(n))
            self.p.set_status(tr_template("🎯 [{0}] are acum {1} locatoare.").format(obj.name, len(obj.locators)))
            self.next_missing()
        self._run(work, done)
