# -*- coding: utf-8 -*-
# ============================================================
# AutoPilot DC v4.15 — vederile noi din Studio RPR
#
#   ActivityBar   bara de activitati din stanga (Pasi, Biblioteca, Rutine, Filme, Setari, Ghid)
#   DocTabs       tab-uri pentru mai multe rutine deschise
#   RunTimeline   cronologia rularii: un card pe pas (status, rand, durata, captura erorii)
#   ExcelRunView  ecranul de rulare pe randurile Excel (status, film, reia randul)
#   FlowView      rutina ca flux de carduri legate (doar citire; click = pasul in arbore)
#   FilmsPanel    filmele salvate (cele mai noi primele)
#
# Toate primesc culorile (C) ale aplicatiei; textele sunt in romana si se traduc prin i18n.
# ============================================================

from __future__ import annotations

import os
import threading
import time
import tkinter as tk
from tkinter import ttk
from typing import Callable, Dict, List, Optional, Tuple

import ui_theme

try:
    from i18n import tr   # textele compuse se traduc pe bucati
except ImportError:       # pragma: no cover
    def tr(text):
        return text

FONT = "Segoe UI"


def _tip(widget, text: str):
    try:
        from studio_ui import ToolTip
        ToolTip(widget, text)
    except Exception:  # noqa: BLE001
        pass


def _hex(c: str, w: tk.Misc) -> Tuple[int, int, int]:
    r, g, b = w.winfo_rgb(c)
    return r >> 8, g >> 8, b >> 8


def tint(color: str, bg: str, w: tk.Misc, alpha: float = 0.22) -> str:
    """Culoarea amestecata peste fundal (fundaluri discrete pentru statusuri, pe ambele teme)."""
    try:
        a, b = _hex(color, w), _hex(bg, w)
    except tk.TclError:
        return bg
    return "#%02X%02X%02X" % tuple(int(b[i] + (a[i] - b[i]) * alpha) for i in range(3))


def _short(text: str, n: int) -> str:
    text = " ".join(str(text or "").split())
    return text if len(text) <= n else text[:n - 1] + "…"


def fmt_time(sec: float) -> str:
    m, s = divmod(int(max(0, sec)), 60)
    return f"{m}:{s:02d}"


# ─────────────────────────────────────────────────────────────
# 1. Bara de activitati
# ─────────────────────────────────────────────────────────────
class ActivityBar(tk.Frame):
    """Iconite verticale. Click pe iconita activa strange panoul lateral; inca un click il redeschide.
    items: (cheie, iconita, eticheta, "panel" | "action") sau None pentru spatiul dintre grupuri."""

    def __init__(self, master, C: Dict[str, str], items, on_panel: Callable[[Optional[str]], None],
                 on_action: Callable[[str], None]):
        super().__init__(master, bg=C["bg_panel"] if "bg_panel" in C else C["bg_card"], width=66)
        self.C = C
        self._on_panel, self._on_action = on_panel, on_action
        self.active: Optional[str] = None
        self.collapsed = False
        self._cells: Dict[str, Tuple[tk.Frame, tk.Label, tk.Label, tk.Frame]] = {}
        bg = self["bg"]
        top = tk.Frame(self, bg=bg)
        top.pack(side="top", fill="x", pady=(6, 0))
        bottom = tk.Frame(self, bg=bg)
        bottom.pack(side="bottom", fill="x", pady=(0, 6))
        host = top
        for it in items:
            if it is None:
                host = bottom
                continue
            key, icon, label, kind = it
            cell = tk.Frame(host, bg=bg, cursor="hand2")
            cell.pack(side="top", fill="x", pady=1)
            mark = tk.Frame(cell, bg=bg, width=3)
            mark.pack(side="left", fill="y")
            ic = tk.Label(cell, text=icon, bg=bg, fg=C["text"], font=(FONT, 15), cursor="hand2")
            ic.pack(side="top", pady=(4, 0))
            tx = tk.Label(cell, text=label, bg=bg, fg=C["text_dim"], font=(FONT, 8), cursor="hand2")
            tx.pack(side="top", pady=(0, 3))
            for w in (cell, ic, tx):
                w.bind("<Button-1>", lambda e, k=key, kd=kind: self._click(k, kd))
                w.bind("<Enter>", lambda e, k=key: self._hover(k, True))
                w.bind("<Leave>", lambda e, k=key: self._hover(k, False))
            _tip(cell, label)
            self._cells[key] = (cell, ic, tx, mark)
        self.pack_propagate(True)

    def _click(self, key: str, kind: str):
        if kind == "action":
            self._on_action(key)
            return
        if key == self.active and not self.collapsed:
            self.collapsed = True
            self._paint()
            self._on_panel(None)
            return
        self.select(key)

    def select(self, key: str, notify: bool = True):
        self.active, self.collapsed = key, False
        self._paint()
        if notify:
            self._on_panel(key)

    def _hover(self, key: str, on: bool):
        if key == self.active and not self.collapsed:
            return
        cell, ic, tx, mark = self._cells[key]
        bg = self.C["bg_input"] if on else self["bg"]
        for w in (cell, ic, tx):
            w.configure(bg=bg)

    def _paint(self):
        bg = self["bg"]
        for key, (cell, ic, tx, mark) in self._cells.items():
            on = key == self.active and not self.collapsed
            cbg = self.C["bg_input"] if on else bg
            for w in (cell, ic, tx):
                w.configure(bg=cbg)
            tx.configure(fg=self.C["text"] if on else self.C["text_dim"],
                         font=(FONT, 8, "bold" if on else "normal"))
            mark.configure(bg=self.C["primary"] if on else cbg)


# ─────────────────────────────────────────────────────────────
# 2. Tab-uri pentru rutinele deschise
# ─────────────────────────────────────────────────────────────
class DocTabs(tk.Frame):
    """Un tab pe rutina deschisa: click = comuta, × = inchide, + = rutina noua."""

    def __init__(self, master, C: Dict[str, str], on_switch: Callable[[int], None],
                 on_close: Callable[[int], None], on_new: Callable[[], None]):
        super().__init__(master, bg=C["bg_main"])
        self.C = C
        self._on_switch, self._on_close, self._on_new = on_switch, on_close, on_new
        self._row = tk.Frame(self, bg=C["bg_main"])
        self._row.pack(side="left", fill="x", expand=True)
        self.tabs: List[tk.Frame] = []

    def render(self, docs: List[Tuple[str, bool, str]], active: int):
        """docs: (nume, nesalvat, cale)."""
        C = self.C
        for w in self._row.winfo_children():
            w.destroy()
        self.tabs = []
        # cu multe rutine deschise numele se scurteaza, ca tab-urile sa incapa pe un rand
        width = max(1, self.winfo_width() or 900)
        n = max(10, min(32, int((width - 50) / max(1, len(docs)) / 8) - 4))
        for i, (name, dirty, path) in enumerate(docs):
            on = i == active
            bg = C["bg_card"] if on else C["bg_main"]
            tab = tk.Frame(self._row, bg=bg, cursor="hand2", highlightthickness=0)
            tab.pack(side="left", padx=(0, 2))
            line = tk.Frame(tab, bg=C["primary"] if on else bg, height=2)
            line.pack(side="top", fill="x")
            body = tk.Frame(tab, bg=bg)
            body.pack(side="top")
            lbl = tk.Label(body, text=_short(name or "Rutina noua", n) + ("  ●" if dirty else ""), bg=bg,
                           fg=C["text"] if on else C["text_dim"], font=(FONT, 10, "bold" if on else "normal"),
                           padx=10, pady=4, cursor="hand2")
            lbl.pack(side="left")
            x = tk.Label(body, text="×", bg=bg, fg=C["text_dim"], font=(FONT, 11), padx=6, cursor="hand2")
            x.pack(side="left")
            for w in (tab, body, lbl):
                w.bind("<Button-1>", lambda e, k=i: self._on_switch(k))
                w.bind("<Button-2>", lambda e, k=i: self._on_close(k))   # click pe rotita = inchide (ca in browser)
            x.bind("<Button-1>", lambda e, k=i: self._on_close(k))
            x.bind("<Enter>", lambda e, w=x: w.configure(fg=C["danger"]))
            x.bind("<Leave>", lambda e, w=x: w.configure(fg=C["text_dim"]))
            _tip(lbl, (path or tr("Rutina nesalvata")) + ("\n" + tr("● modificari nesalvate") if dirty else ""))
            self.tabs.append(tab)
        plus = tk.Label(self._row, text="+", bg=C["bg_main"], fg=C["text_dim"], font=(FONT, 13, "bold"),
                        padx=10, cursor="hand2")
        plus.pack(side="left")
        plus.bind("<Button-1>", lambda e: self._on_new())
        _tip(plus, "Rutina noua intr-un tab nou (Ctrl+N)")


# ─────────────────────────────────────────────────────────────
# 3. Cronologia rularii
# ─────────────────────────────────────────────────────────────
class RunTimeline(tk.Frame):
    """Un card pentru fiecare pas terminat, de la stanga la dreapta. Pasii cu eroare au captura ecranului.
    Click pe card = pasul in arbore; dublu-click pe captura = captura mare."""

    CARD_W, CARD_H, GAP, MAX = 188, 64, 8, 400
    SHOT_W = 112      # cardurile cu eroare au captura ecranului in dreapta

    def __init__(self, master, C: Dict[str, str], on_pick: Callable[[str], None],
                 on_open: Callable[[str], None]):
        super().__init__(master, bg=C["bg_main"])
        self.C = C
        self._on_pick, self._on_open = on_pick, on_open
        head = tk.Frame(self, bg=C["bg_main"])
        head.pack(fill="x", padx=6, pady=(4, 2))
        self._summary = tk.Label(head, text="Ruleaza rutina: aici apare fiecare pas, cu durata si captura erorilor.",
                                 bg=C["bg_main"], fg=C["text_dim"], font=(FONT, 10), anchor="w")
        self._summary.pack(side="left", fill="x", expand=True)
        self._counts = tk.Label(head, text="", bg=C["bg_main"], fg=C["text"], font=(FONT, 10, "bold"))
        self._counts.pack(side="right")
        self.canvas = tk.Canvas(self, bg=C["bg_main"], highlightthickness=0, height=self.CARD_H + 12)
        hsb = ttk.Scrollbar(self, orient="horizontal", command=self.canvas.xview)
        self.canvas.configure(xscrollcommand=hsb.set)
        hsb.pack(side="bottom", fill="x")
        self.canvas.pack(fill="both", expand=True, padx=6)
        self.canvas.bind("<MouseWheel>", lambda e: (self.canvas.xview_scroll(-1 if e.delta > 0 else 1, "units"),
                                                    "break")[1])
        self.cards: List[dict] = []
        self._images: Dict[int, object] = {}
        self._x = 6
        self._ok = self._err = 0
        self._t0 = 0.0

    def clear(self):
        self.canvas.delete("all")
        self.cards.clear()
        self._images.clear()
        self._x = 6
        self._ok = self._err = 0
        self._t0 = time.monotonic()
        self._counts.configure(text="")

    def set_summary(self, text: str):
        self._summary.configure(text=text)

    def elapsed(self) -> float:
        return time.monotonic() - self._t0 if self._t0 else 0.0

    def add(self, node_id: str, title: str, ok: bool, row: int = 0, ms: float = 0.0, shot: str = "",
            message: str = ""):
        C, cv = self.C, self.canvas
        if len(self.cards) >= self.MAX:   # cele mai vechi carduri ies din stanga
            old = self.cards.pop(0)
            cv.delete(old["tag"])
            self._images.pop(old["n"], None)
            dx = old["w"] + self.GAP
            cv.move("all", -dx, 0)
            self._x -= dx
        n = (self.cards[-1]["n"] + 1) if self.cards else 1
        tag = f"c{n}"
        img = self._thumb(shot, self.SHOT_W, self.CARD_H - 10) if shot and not ok else None
        x, y, h = self._x, 4, self.CARD_H
        w = self.CARD_W + (self.SHOT_W + 6 if img is not None else 0)
        color = C["success"] if ok else C["danger"]
        bg = C["bg_card"]
        cv.create_rectangle(x, y, x + w, y + h, fill=bg, outline=tint(color, bg, self, 0.6), tags=(tag, "card"))
        cv.create_rectangle(x, y, x + w, y + 3, fill=color, outline=color, tags=(tag,))
        fg_st = ui_theme.readable(color, bg, 4.5, self)
        cv.create_text(x + 8, y + 10, text="✓" if ok else "✕", fill=fg_st, font=(FONT, 11, "bold"), anchor="nw",
                       tags=(tag,))
        cv.create_text(x + 26, y + 10, text=_short(tr(title), 22), fill=C["text"], font=(FONT, 9, "bold"),
                       anchor="nw", tags=(tag,))
        meta = []
        if row:
            meta.append(f"r{row}")
        if ms:
            meta.append(f"{ms / 1000:.1f} s".replace(".", ","))
        if not ok and message:
            meta.append(_short(tr(message), 26 - 6 * len(meta)))
        cv.create_text(x + 26, y + 32, text=" · ".join(meta) or " ", fill=fg_st if not ok else C["text_dim"],
                       font=(FONT, 9), anchor="nw", tags=(tag,))
        if img is not None:
            self._images[n] = img
            cv.create_image(x + self.CARD_W, y + 6, image=img, anchor="nw", tags=(tag, f"{tag}img"))
            cv.tag_bind(f"{tag}img", "<Double-Button-1>", lambda e, p=shot: self._on_open(p))
        cv.tag_bind(tag, "<Button-1>", lambda e, nid=node_id: self._on_pick(nid))
        self.cards.append({"n": n, "tag": tag, "node": node_id, "ok": ok, "row": row, "shot": shot, "w": w,
                           "message": message})
        self._x += w + self.GAP
        if ok:
            self._ok += 1
        else:
            self._err += 1
        self._counts.configure(text=f"✓ {self._ok}   ✕ {self._err}" if self._err else f"✓ {self._ok}")
        cv.configure(scrollregion=(0, 0, self._x + 6, h + 8))
        cv.xview_moveto(1.0)

    def _thumb(self, path: str, w: int, h: int):
        try:
            from PIL import Image, ImageTk
            im = Image.open(path)
            im.thumbnail((w, h))
            return ImageTk.PhotoImage(im, master=self)
        except Exception:  # noqa: BLE001 — fara pillow sau captura lipsa: cardul ramane fara imagine
            return None


# ─────────────────────────────────────────────────────────────
# 4. Ecranul de rulare pe randurile Excel
# ─────────────────────────────────────────────────────────────
class ExcelRunView(tk.Frame):
    """Excel-ul ca pagina, rutina ca banda: un rand pe linie, cu status si minutul din film.
    In dreapta: ce s-a intamplat pe randul ales, captura erorii, Reia randul, Vezi in film."""

    MAX_COLS, MAX_ROWS = 6, 5000

    def __init__(self, master, panel):
        super().__init__(master, bg=panel.C["bg_main"])
        self.p = panel
        C = self.C = panel.C
        self.node = None            # ForEachRowNode urmarit
        self.path = ""
        self.cols: List[str] = []
        self.status_col = ""
        self.rows: List[int] = []
        self.film: Dict[int, Tuple[str, float]] = {}
        self.result: Dict[int, str] = {}
        self.running_row = 0
        self._img = None

        head = tk.Frame(self, bg=C["bg_main"])
        head.pack(fill="x", pady=(0, 2))
        panel._btn(head, "📂", self.open_file, tip="Deschide fisierul in Excel").pack(side="right", padx=1)
        panel._btn(head, "⟳", self.reload, tip="Citeste din nou fisierul (dupa o rulare sau o modificare)"
                   ).pack(side="right", padx=1)
        self._file = tk.Label(head, text="", bg=C["bg_main"], fg=C["text"], font=(FONT, 11, "bold"), anchor="w")
        self._file.pack(side="left", padx=(4, 8), fill="x", expand=True)
        self._info = tk.Label(self, text="", bg=C["bg_main"], fg=C["text_dim"], font=(FONT, 10), anchor="w",
                              justify="left")
        self._info.pack(fill="x", padx=4, pady=(0, 4))
        self.bind("<Configure>", lambda e: self._info.configure(wraplength=max(200, e.width - 12)), add="+")

        # tabelul si detaliile randului: latimea se imparte cu mouse-ul
        body = ttk.PanedWindow(self, orient="horizontal", style="Studio.TPanedwindow")
        body.pack(fill="both", expand=True)
        self._body = body
        box = tk.Frame(body, bg=C["bg_main"])
        body.add(box, weight=3)
        self._aside = tk.Frame(body, bg=C["bg_card"], width=260)
        body.add(self._aside, weight=1)
        self._aside_set = False
        body.bind("<Configure>", lambda e: self._place_aside(), add="+")
        self.tree = ttk.Treeview(box, show="headings", style="Studio.Treeview", selectmode="browse")
        vsb = ttk.Scrollbar(box, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(box, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        vsb.pack(side="right", fill="y")
        hsb.pack(side="bottom", fill="x")
        self.tree.pack(side="left", fill="both", expand=True)
        base = C["bg_input"]
        for tag, col in (("ok", C["success"]), ("error", C["danger"]), ("skip", C["warning"]),
                         ("running", C["accent"] if "accent" in C else C["primary"])):
            self.tree.tag_configure(tag, background=tint(col, base, self, 0.28))
        self.tree.bind("<<TreeviewSelect>>", lambda e: self._show_row())
        self.tree.bind("<Double-Button-1>", lambda e: self.open_film())

        a = self._aside
        self._row_title = tk.Label(a, text="Alege un rand", bg=C["bg_card"], fg=C["text"], font=(FONT, 11, "bold"),
                                   anchor="w", justify="left", wraplength=240)
        self._row_title.pack(fill="x", padx=10, pady=(10, 6))
        self._row_log = tk.Label(a, text="", bg=C["bg_card"], fg=C["text_dim"], font=(FONT, 9), anchor="nw",
                                 justify="left", wraplength=240)
        self._row_log.pack(fill="x", padx=10)
        self._shot = tk.Label(a, bg=C["bg_card"], cursor="hand2")
        self._shot.pack(padx=10, pady=6)
        self._shot.bind("<Double-Button-1>", lambda e: self._open_shot())
        btns = tk.Frame(a, bg=C["bg_card"])
        btns.pack(fill="x", padx=10, pady=4)
        self._rerun = panel._btn(btns, "↻ Reia randul", self.rerun_row, tip="Ruleaza din nou doar randul ales "
                                 "(chiar daca are deja OK)")
        self._rerun.pack(side="top", fill="x", pady=(0, 3))
        self._see = panel._btn(btns, "🎬 Vezi in film", self.open_film, tip="Deschide filmul rularii la minutul randului")
        self._see.pack(side="top", fill="x")
        self._foot = tk.Label(a, text="La final, aceeasi vedere ramane raportul rularii: reiei doar randurile cu eroare.",
                              bg=C["bg_card"], fg=C["text_dim"], font=(FONT, 9), justify="left", wraplength=240)
        self._foot.pack(side="bottom", fill="x", padx=10, pady=10)
        a.bind("<Configure>", lambda e: [w.configure(wraplength=max(120, e.width - 22))
                                         for w in (self._row_title, self._row_log, self._foot)], add="+")
        self._shot_path = ""

    def _place_aside(self):
        if self._aside_set:
            return
        W = self._body.winfo_width()
        if W < 300:
            return
        try:
            self._body.sashpos(0, W - max(200, min(280, int(W * 0.36))))
            self._aside_set = True
        except tk.TclError:
            pass

    # ── citire ──
    def bind_node(self, node, path: str):
        """Fisierul (cu variabilele inlocuite) si pasul "Pentru fiecare rand"."""
        changed = node is not self.node or path != self.path
        self.node, self.path = node, path
        if changed or not self.rows:
            self.reload()

    def reset_run(self):
        """O rulare noua: statusurile si filmele din sesiunea trecuta se uita (fisierul le are oricum)."""
        self.film, self.result, self.running_row = {}, {}, 0

    def reload(self):
        f, path = self.node, self.path
        self.tree.delete(*self.tree.get_children())
        self.rows = []
        if f is None:
            self._file.configure(text="")
            self._info.configure(text="Rutina nu are un pas \"Pentru fiecare rand Excel\".")
            return
        self._file.configure(text=os.path.basename(path) if path else "(alege fisier)")
        if not path or "{" in path:
            self._info.configure(text="Fisierul se afla abia la rulare (calea are variabile).")
            return
        if not os.path.isfile(path):
            self._info.configure(text="Fisierul nu exista.")
            return
        self._info.configure(text="Citesc...")
        self._token = token = getattr(self, "_token", 0) + 1
        sheet, header, key, status = f.sheet, f.header_row, f.key_column, f.status_column
        try:
            from rpr.variables import VariableStore
            vs = VariableStore()
            for k, v in self.p.routine.variables.items():
                vs.set(k, v)
            sheet = vs.resolve(sheet)
        except Exception:  # noqa: BLE001
            pass

        def work():
            data = None
            try:
                from rpr.excel import ExcelTable
                with ExcelTable.open(path, sheet, header) as t:
                    titles = list(t.header_titles)
                    st = status.strip()
                    cols = [c for c in titles if c and c.strip().lower() != st.lower()][:self.MAX_COLS]
                    first, last = t.first_data_row(0), t.last_data_row(key)
                    rows = []
                    for r in range(first, min(last, first + self.MAX_ROWS - 1) + 1):
                        if t.is_row_empty(r, key):
                            continue
                        rows.append((r, [t.get_cell(r, c) for c in cols], t.get_cell(r, st) if st else ""))
                    data = (t.sheet_name, cols, st, rows, last)
            except Exception as ex:  # noqa: BLE001
                data = ex
            self.p.post("ui", lambda: self._loaded(token, data))

        threading.Thread(target=work, daemon=True, name="ExcelView").start()

    def _loaded(self, token: int, data):
        if token != self._token or not self.winfo_exists():
            return   # intre timp s-a cerut alta citire
        self.tree.delete(*self.tree.get_children())
        self.rows = []
        if isinstance(data, Exception) or data is None:
            self._info.configure(text=tr("Nu pot citi fisierul:") + f" {data}")
            return
        sheet, cols, st, rows, last = data
        self.cols, self.status_col = cols, st or "Status"
        all_cols = ["#"] + cols + ["Status", "Film"]
        ids = [f"c{i}" for i in range(len(all_cols))]
        self.tree.configure(columns=ids)
        for i, (cid, title) in enumerate(zip(ids, all_cols)):
            self.tree.heading(cid, text=title, anchor="w")
            w = 44 if title == "#" else 60 if title == "Film" else 120 if title == "Status" else 110
            self.tree.column(cid, width=w, minwidth=40, stretch=title not in ("#", "Film"), anchor="w")
        for r, vals, status in rows:
            self.tree.insert("", "end", iid=str(r), values=[r] + [_short(v, 60) for v in vals] +
                             [_short(status, 60), ""], tags=(self._tag(status),))
            self.rows.append(r)
        self._base = tr(f"foaia {sheet} · {len(rows)} randuri")
        # randurile la care s-a lucrat intre timp (citirea ruleaza in fundal) raman la zi
        for row, (film, sec) in self.film.items():
            if self.tree.exists(str(row)):
                self._set(str(row), "Film", fmt_time(sec))
        for row, status in self.result.items():
            if self.tree.exists(str(row)):
                self._set(str(row), "Status", _short(status, 60))
                self.tree.item(str(row), tags=(self._tag(status),))
        if self.running_row and self.tree.exists(str(self.running_row)) and self.running_row not in self.result:
            self._set(str(self.running_row), "Status", "IN LUCRU")
            self.tree.item(str(self.running_row), tags=("running",))
        self._update_counts()

    @staticmethod
    def _tag(status: str) -> str:
        from rpr.lang import is_in_progress, is_ok
        s = (status or "").strip()
        if not s:
            return ""
        if is_ok(s):
            return "ok"
        if is_in_progress(s):
            return "running"
        up = s.upper()
        if up.startswith(("SARIT", "OPRIT", "SKIP", "STOP", "ÜBER", "GESTOPPT")):
            return "skip"
        return "error"

    def _update_counts(self):
        n = {"ok": 0, "error": 0}
        for iid in self.tree.get_children():
            tags = self.tree.item(iid, "tags")
            for t in n:
                if t in tags:
                    n[t] += 1
        rest = len(self.tree.get_children()) - n["ok"] - n["error"]
        parts = [getattr(self, "_base", ""), f"✓ {n['ok']} OK", tr(f"✕ {n['error']} eroare"), tr(f"{rest} ramase")]
        self._info.configure(text="  ·  ".join(p for p in parts if p))

    # ── in timpul rularii (din coada panoului) ──
    def row_started(self, row: int, film: str = "", sec: float = 0.0):
        iid = str(row)
        self.running_row = row
        if film:
            self.film[row] = (film, sec)
        if not self.tree.exists(iid):
            return
        self._set(iid, "Status", "IN LUCRU")
        if film:
            self._set(iid, "Film", fmt_time(sec))
        self.tree.item(iid, tags=("running",))
        self.tree.see(iid)

    def row_finished(self, row: int, status: str):
        iid = str(row)
        self.result[row] = status
        if not self.tree.exists(iid):
            return
        self._set(iid, "Status", _short(status, 60))
        self.tree.item(iid, tags=(self._tag(status),))
        self._update_counts()
        if self.tree.selection() == (iid,):
            self._show_row()

    def _set(self, iid: str, col: str, value: str):
        try:
            idx = (["#"] + self.cols + ["Status", "Film"]).index(col)
            self.tree.set(iid, f"c{idx}", value)
        except (ValueError, tk.TclError):
            pass

    # ── randul ales ──
    def selected_row(self) -> int:
        sel = self.tree.selection()
        return int(sel[0]) if sel else 0

    def _show_row(self):
        row = self.selected_row()
        if not row:
            return
        C = self.C
        vals = self.tree.item(str(row), "values")
        key = vals[1] if len(vals) > 1 else ""
        self._row_title.configure(text=tr(f"Randul {row}") + (f" · {key}" if key else ""))
        lines, shot = [], ""
        for e in self.p._log_entries:
            if e.excel_row != row:
                continue
            ok = str(e.level) != "Error"
            dur = f", {e.duration_ms / 1000:.1f} s".replace(".", ",") if e.duration_ms else ""
            lines.append(("• " if ok else "✕ ") + _short(f"{tr(e.node_title)} — {tr(e.message)}{dur}", 140))
            if e.screenshot and not shot:
                shot = e.screenshot
        if not lines:
            st = self.result.get(row) or (vals[-2] if len(vals) >= 2 else "")
            lines = [st or tr("Nu a rulat inca in aceasta sesiune.")]
        self._row_log.configure(text="\n".join(lines[-12:]),
                                fg=C["text"] if any(x.startswith("✕") for x in lines) else C["text_dim"])
        self._shot_path = shot
        self._img = None
        if shot:
            try:
                from PIL import Image, ImageTk
                im = Image.open(shot)
                im.thumbnail((max(120, self._aside.winfo_width() - 20), 150))
                self._img = ImageTk.PhotoImage(im, master=self)
            except Exception:  # noqa: BLE001
                self._img = None
        self._shot.configure(image=self._img or "")
        self._see.configure(state="normal" if row in self.film else "disabled")
        self._rerun.configure(state="disabled" if self.p.busy else "normal")

    def _open_shot(self):
        if self._shot_path and os.path.isfile(self._shot_path):
            self.p.open_path(self._shot_path)

    def open_film(self):
        row = self.selected_row()
        if row not in self.film:
            self.p.set_status("Randul nu are film: porneste filmarea la rulare din Setari → Video.")
            return
        path, sec = self.film[row]
        try:
            import video_ui
            video_ui.open_video(self.winfo_toplevel(), self.C, path, max(0.0, sec - 1), on_status=self.p.set_status)
        except Exception as ex:  # noqa: BLE001
            self.p.set_status(f"🎥 {ex}")

    def open_file(self):
        if self.path and os.path.isfile(self.path):
            self.p.open_path(self.path)

    def rerun_row(self):
        row = self.selected_row()
        if row and self.node is not None:
            self.p.rerun_excel_row(self.node, row)


# ─────────────────────────────────────────────────────────────
# 5. Rutina ca flux (doar citire)
# ─────────────────────────────────────────────────────────────
class FlowView(tk.Frame):
    """Pasii ca un flux de carduri legate; ramurile (Atunci / Altfel...) stau una langa alta.
    Click pe card = pasul se alege in arbore (proprietatile in dreapta); dublu-click = inapoi la lista de pasi."""

    CW, CH, GAP, COLGAP, LBL = 250, 40, 22, 30, 18

    def __init__(self, master, panel):
        super().__init__(master, bg=panel.C["bg_main"])
        self.p = panel
        C = self.C = panel.C
        self.canvas = tk.Canvas(self, bg=C["bg_main"], highlightthickness=0)
        vsb = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        hsb = ttk.Scrollbar(self, orient="horizontal", command=self.canvas.xview)
        self.canvas.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        vsb.pack(side="right", fill="y")
        hsb.pack(side="bottom", fill="x")
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<MouseWheel>", self._wheel)
        self.canvas.bind("<Shift-MouseWheel>", lambda e: (self.canvas.xview_scroll(-1 if e.delta > 0 else 1,
                                                                                    "units"), "break")[1])
        self.canvas.bind("<Configure>", lambda e: self._center())
        self.cards: Dict[str, int] = {}     # node.id -> dreptunghiul cardului
        self._selected = ""
        self._width = 0

    def _wheel(self, e):
        self.canvas.yview_scroll(-1 if e.delta > 0 else 1, "units")
        return "break"

    # ── masurare + desen ──
    def _measure_list(self, nodes) -> Tuple[int, int]:
        if not nodes:
            return self.CW // 2, 24
        w, h = 0, 0
        for n in nodes:
            bw, bh = self._measure_node(n)
            w, h = max(w, bw), h + bh + self.GAP
        return w, h - self.GAP

    def _measure_node(self, n) -> Tuple[int, int]:
        br = n.branches()
        if not br:
            return self.CW, self.CH
        cols = [self._measure_list(lst) for _, lst in br]
        w = max(self.CW, sum(c[0] for c in cols) + self.COLGAP * (len(cols) - 1))
        h = self.CH + self.GAP + self.LBL + max(c[1] for c in cols) + self.GAP
        return w, h

    def refresh(self):
        cv = self.canvas
        cv.delete("all")
        self.cards.clear()
        steps = self.p.routine.steps
        w, h = self._measure_list(steps)
        self._width = w
        x0 = max(self.CW // 2 + 20, w // 2 + 20)
        name = self.p.routine.name or "Rutina noua"
        cv.create_text(x0, 14, text=name, fill=self.C["text"], font=(FONT, 12, "bold"), tags=("flow",))
        cv.create_oval(x0 - 6, 34, x0 + 6, 46, fill=self.C["primary"], outline="", tags=("flow",))
        top = 66
        cv.create_line(x0, 46, x0, top, fill=self.C["text_dim"], arrow="last", tags=("flow",))
        if steps:
            end = self._draw_list(steps, x0, top)
        else:
            cv.create_text(x0, top + 12, text="Rutina nu are pasi inca. Adauga-i din 🧱 Pasi.", fill=self.C["text_dim"],
                           font=(FONT, 10), tags=("flow",))
            end = top + 24
        cv.create_line(x0, end, x0, end + 18, fill=self.C["text_dim"], arrow="last", tags=("flow",))
        cv.create_rectangle(x0 - 6, end + 20, x0 + 6, end + 32, fill=self.C["text_dim"], outline="", tags=("flow",))
        cv.configure(scrollregion=(0, 0, x0 * 2, end + 60))
        self._center()
        self.sync_states()

    def _center(self):
        # fluxul sta pe mijloc cand e mai ingust decat fereastra
        cv = self.canvas
        try:
            bbox = cv.bbox("flow")
        except tk.TclError:
            return
        if not bbox:
            return
        W = cv.winfo_width()
        width = bbox[2] - bbox[0]
        dx = (W - width) / 2 - bbox[0] if width < W else 20 - bbox[0]
        if abs(dx) >= 1:
            cv.move("flow", dx, 0)
        bbox = cv.bbox("flow")
        cv.configure(scrollregion=(min(0, bbox[0] - 20), 0, max(W, bbox[2] + 20), bbox[3] + 30))

    def _line(self, *pts, arrow=None):
        kw = {"arrow": arrow} if arrow else {}
        self.canvas.create_line(*pts, fill=self.C["text_dim"], width=1, tags=("flow",), **kw)

    def _draw_list(self, nodes, cx: float, y: float) -> float:
        if not nodes:
            self.canvas.create_text(cx, y + 12, text="(gol)", fill=self.C["text_dim"], font=(FONT, 9, "italic"),
                                    tags=("flow",))
            return y + 24
        prev = None
        for n in nodes:
            if prev is not None:
                self._line(cx, prev, cx, y, arrow="last")
            prev = self._draw_node(n, cx, y)
            y = prev + self.GAP
        return prev

    def _kind_color(self, n) -> str:
        from rpr.model import ForEachRowNode, IfNode, LoopNode
        C = self.C
        if isinstance(n, ForEachRowNode):
            return C["success"]
        if isinstance(n, LoopNode):
            return C.get("accent", C["primary"])
        if isinstance(n, IfNode) or n.branches():
            return C["warning"]
        return C["primary"]

    def _draw_node(self, n, cx: float, y: float) -> float:
        C, cv = self.C, self.canvas
        try:
            from studio_ui import icon_for
            icon = icon_for(n)
        except Exception:  # noqa: BLE001
            icon = "•"
        x1, x2 = cx - self.CW / 2, cx + self.CW / 2
        tag = f"n{n.id}"
        fill = C["bg_card"]
        rect = cv.create_rectangle(x1, y, x2, y + self.CH, fill=fill, outline=C.get("border", C["bg_input"]),
                                   width=1, tags=("flow", tag, "card"))
        strip = self._kind_color(n)
        cv.create_rectangle(x1, y, x1 + 5, y + self.CH, fill=strip, outline=strip, tags=("flow", tag))
        fg = C["text"] if n.enabled else ui_theme.readable(C["text_muted"], fill, 3.0, self)
        cv.create_text(x1 + 14, y + self.CH / 2, text=f"{icon}  {_short(tr(n.title), 30)}", fill=fg, anchor="w",
                       font=(FONT, 10, "normal" if n.enabled else "italic"), tags=("flow", tag))
        cv.tag_bind(tag, "<Button-1>", lambda e, nid=n.id: self.pick(nid))
        cv.tag_bind(tag, "<Double-Button-1>", lambda e, nid=n.id: self.p.show_center("steps", select=nid))
        self.cards[n.id] = rect
        br = n.branches()
        if not br:
            return y + self.CH
        cols = [self._measure_list(lst) for _, lst in br]
        total = sum(c[0] for c in cols) + self.COLGAP * (len(cols) - 1)
        x = cx - total / 2
        split = y + self.CH + self.GAP / 2
        top = y + self.CH + self.GAP
        self._line(cx, y + self.CH, cx, split)
        bottoms = []
        for (name, lst), (w, h) in zip(br, cols):
            ccx = x + w / 2
            self._line(cx, split, ccx, split)
            self._line(ccx, split, ccx, top + self.LBL - 4, arrow="last")
            cv.create_text(ccx + 6, top + 6, text=_short(tr(name), 28), anchor="w",
                           fill=ui_theme.readable(strip, C["bg_main"], 4.5, self), font=(FONT, 9, "bold"), tags=("flow",))
            bottoms.append((ccx, self._draw_list(lst, ccx, top + self.LBL)))
            x += w + self.COLGAP
        merge = max(b for _, b in bottoms) + self.GAP / 2
        for ccx, b in bottoms:
            self._line(ccx, b, ccx, merge)
        self._line(min(c for c, _ in bottoms), merge, max(c for c, _ in bottoms), merge)
        if len(bottoms) == 1 and abs(bottoms[0][0] - cx) > 1:
            self._line(bottoms[0][0], merge, cx, merge)
        return merge

    # ── stare ──
    def pick(self, node_id: str):
        self.select(node_id)
        self.p.select_node(node_id)

    def select(self, node_id: str):
        C = self.C
        old = self.cards.get(self._selected)
        if old:
            self.canvas.itemconfigure(old, outline=C.get("border", C["bg_input"]), width=1)
            self._paint_state(self._selected)
        self._selected = node_id
        r = self.cards.get(node_id)
        if r:
            self.canvas.itemconfigure(r, outline=C["primary"], width=3)
            self._see(r)

    def _see(self, item):
        cv = self.canvas
        try:
            x1, y1, x2, y2 = cv.coords(item)
            sr = [float(v) for v in str(cv.cget("scrollregion")).split()]
        except (ValueError, tk.TclError):
            return
        if len(sr) != 4 or sr[3] <= sr[1]:
            return
        top, bottom = cv.canvasy(0), cv.canvasy(cv.winfo_height())
        if y1 < top or y2 > bottom:
            cv.yview_moveto(max(0.0, (y1 - 60 - sr[1]) / (sr[3] - sr[1])))

    def _paint_state(self, node_id: str):
        r = self.cards.get(node_id)
        if not r or node_id == self._selected:
            return
        C = self.C
        tags = ()
        try:
            if self.p.tree.exists(node_id):
                tags = self.p.tree.item(node_id, "tags")
        except tk.TclError:
            pass
        if "running" in tags:
            color, wd = C["warning"], 3
        elif "error" in tags:
            color, wd = C["danger"], 2
        elif "ok" in tags:
            color, wd = C["success"], 2
        else:
            color, wd = C.get("border", C["bg_input"]), 1
        self.canvas.itemconfigure(r, outline=color, width=wd)

    def sync_states(self):
        for nid in self.cards:
            self._paint_state(nid)
        if self._selected in self.cards:
            self.select(self._selected)

    def set_state(self, node_id: str):
        if node_id not in self.cards:
            return
        self._paint_state(node_id)
        if self.p.tree.exists(node_id) and "running" in self.p.tree.item(node_id, "tags"):
            self._see(self.cards[node_id])   # fluxul urmareste pasul care ruleaza


# ─────────────────────────────────────────────────────────────
# 6. Filmele salvate
# ─────────────────────────────────────────────────────────────
class FilmsPanel(tk.Frame):
    """Filmele din folderul de filme (si subfolderele lui), cele mai noi primele. Dublu-click = deschide."""

    def __init__(self, master, panel):
        super().__init__(master, bg=panel.C["bg_main"])
        self.p = panel
        C = self.C = panel.C
        head = tk.Frame(self, bg=C["bg_main"])
        head.pack(fill="x", padx=4, pady=(6, 2))
        self._folder = tk.Label(head, text="", bg=C["bg_main"], fg=C["text"], font=(FONT, 10, "bold"), anchor="w")
        self._folder.pack(side="left", fill="x", expand=True)
        bar = tk.Frame(self, bg=C["bg_main"])
        bar.pack(fill="x", padx=2, pady=2)
        panel._btn(bar, "▶ Deschide", self.open_selected, tip="Deschide filmul ales (aplicatia din Setari → Filme)"
                   ).pack(side="left", padx=2)
        panel._btn(bar, "📂", self.open_folder, tip="Deschide folderul cu filme").pack(side="left", padx=2)
        panel._btn(bar, "⟳", self.refresh, tip="Reciteste lista").pack(side="left", padx=2)
        box = tk.Frame(self, bg=C["bg_main"])
        box.pack(fill="both", expand=True, padx=2)
        self.tree = ttk.Treeview(box, columns=("cand",), show="tree headings", style="Studio.Treeview",
                                 selectmode="browse")
        self.tree.heading("#0", text="Film", anchor="w")
        self.tree.heading("cand", text="Cand", anchor="w")
        self.tree.column("#0", width=160, stretch=True)
        self.tree.column("cand", width=96, stretch=False)
        vsb = ttk.Scrollbar(box, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        self.tree.pack(side="left", fill="both", expand=True)
        self.tree.bind("<Double-Button-1>", lambda e: self.open_selected())
        self.tree.bind("<Return>", lambda e: self.open_selected())
        self._hint = tk.Label(self, text="Filmele se fac la rulare (Setari → Video) sau cu 🎥. Dublu-click deschide "
                                         "filmul cu aplicatia aleasa in 🌐 Setari Studio → 🎬 Filme.",
                              bg=C["bg_main"], fg=C["text_dim"], font=(FONT, 9), justify="left", wraplength=220)
        self._hint.pack(fill="x", padx=6, pady=6)
        self.bind("<Configure>", lambda e: self._hint.configure(wraplength=max(140, e.width - 16)), add="+")
        self.paths: Dict[str, str] = {}
        self.loaded_at = 0.0

    def folder(self) -> str:
        try:
            import screen_recorder as sr
            return sr.VideoSettings.load().folder
        except Exception:  # noqa: BLE001
            return ""

    @staticmethod
    def find(folder: str, limit: int = 300) -> List[Tuple[float, str]]:
        try:
            import screen_recorder as sr
            ext = sr.EXT.lower()
        except Exception:  # noqa: BLE001
            ext = ".apvid"
        out = []
        if not folder or not os.path.isdir(folder):
            return out
        base_depth = folder.rstrip("\\/").count(os.sep)
        for root, dirs, files in os.walk(folder):
            if root.count(os.sep) - base_depth >= 2:
                dirs[:] = []
            for f in files:
                if f.lower().endswith(ext):
                    p = os.path.join(root, f)
                    try:
                        out.append((os.path.getmtime(p), p))
                    except OSError:
                        pass
        out.sort(reverse=True)
        return out[:limit]

    def refresh(self):
        import datetime as _dt
        folder = self.folder()
        self._folder.configure(text="🎬 " + (os.path.basename(folder.rstrip("\\/")) or folder or "Filme"))
        _tip(self._folder, folder)
        self.tree.delete(*self.tree.get_children())
        self.paths.clear()
        for mt, p in self.find(folder):
            iid = self.tree.insert("", "end", text=os.path.splitext(os.path.basename(p))[0],
                                   values=(_dt.datetime.fromtimestamp(mt).strftime("%d.%m %H:%M"),))
            self.paths[iid] = p
        self.loaded_at = time.time()

    def open_selected(self):
        sel = self.tree.selection()
        if not sel or sel[0] not in self.paths:
            return
        try:
            import video_ui
            video_ui.open_video(self.winfo_toplevel(), self.C, self.paths[sel[0]], on_status=self.p.set_status)
        except Exception as ex:  # noqa: BLE001
            self.p.set_status(f"🎥 {ex}")

    def open_folder(self):
        folder = self.folder()
        if folder:
            os.makedirs(folder, exist_ok=True)
            self.p.open_path(folder)
