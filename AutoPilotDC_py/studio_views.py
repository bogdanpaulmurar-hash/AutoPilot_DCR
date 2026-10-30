# -*- coding: utf-8 -*-
# ============================================================
# AutoPilot DC v4.15 — vederile noi din Studio RPR
#
#   ActivityBar   bara de activitati din stanga (Pasi, Biblioteca, Rutine, Filme, Setari, Ghid)
#   DocTabs       tab-uri pentru mai multe rutine deschise
#   RunTimeline   cronologia rularii: un card pe pas (status, rand, durata, captura erorii)
#   ExcelRunView  ecranul de rulare pe randurile Excel (status, film, reia randul)
#   FlowView      rutina ca flux de carduri legate (doar citire; click = pasul in arbore; zoom, harta, export)
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
from typing import Any, Callable, Dict, List, Optional, Tuple

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
    Click pe card = pasul se alege in arbore (proprietatile in dreapta); dublu-click = inapoi la lista de pasi.
    v4.20: zoom (Ctrl + rotita, − / +), tragere pe fundal, Potriveste, harta mica, ramuri restranse, export PNG / SVG.

    Desenul se face o data in coordonate „logice” (zoom 100 %) intr-o lista de primitive (self._prims);
    canvasul, harta mica si exportul le deseneaza pe aceleasi, la scara lor."""

    CW, CH, GAP, COLGAP, LBL = 250, 40, 22, 30, 18
    ZMIN, ZMAX = 0.05, 2.0
    MAP_W, MAP_H = 170, 210

    def __init__(self, master, panel, detached: bool = False):
        super().__init__(master, bg=panel.C["bg_main"])
        self.p = panel
        C = self.C = panel.C
        self.detached = detached             # v4.21: fluxul din fereastra separata (FlowWindow)
        self.z = 1.0
        self._ox = 0.0                       # deplasarea logica pe X (centrarea fluxului ingust)
        self._prims: List[tuple] = []
        self._size = (0.0, 0.0)              # latimea / inaltimea logica a desenului
        self.collapsed: set = set()          # nodurile cu ramurile restranse (doar in sesiune)
        self._owner: Dict[str, str] = {}     # pas ascuns -> cardul restrans care il contine
        self._drag = None
        self._map_on = True
        self._build_bar()
        body = tk.Frame(self, bg=C["bg_main"])
        body.pack(fill="both", expand=True)
        self.canvas = tk.Canvas(body, bg=C["bg_main"], highlightthickness=0)
        vsb = ttk.Scrollbar(body, orient="vertical", command=self.canvas.yview)
        hsb = ttk.Scrollbar(body, orient="horizontal", command=self.canvas.xview)
        self.canvas.configure(yscrollcommand=lambda *a: (vsb.set(*a), self._map_view()),
                              xscrollcommand=lambda *a: (hsb.set(*a), self._map_view()))
        vsb.pack(side="right", fill="y")
        hsb.pack(side="bottom", fill="x")
        self.canvas.pack(fill="both", expand=True)
        cv = self.canvas
        cv.bind("<MouseWheel>", self._wheel)
        cv.bind("<Shift-MouseWheel>", lambda e: self._scroll_x(-1 if e.delta > 0 else 1))
        cv.bind("<Control-MouseWheel>", lambda e: self._zoom_at(1.15 if e.delta > 0 else 1 / 1.15, e.x, e.y))
        cv.bind("<Button-4>", lambda e: self._scroll_y(-1))            # Linux
        cv.bind("<Button-5>", lambda e: self._scroll_y(1))
        cv.bind("<Control-Button-4>", lambda e: self._zoom_at(1.15, e.x, e.y))
        cv.bind("<Control-Button-5>", lambda e: self._zoom_at(1 / 1.15, e.x, e.y))
        cv.bind("<ButtonPress-1>", self._press, add="+")
        cv.bind("<B1-Motion>", self._move)
        cv.bind("<ButtonRelease-1>", self._release)
        cv.bind("<ButtonPress-2>", lambda e: self._start_pan(e))     # rotita apasata = trage oriunde
        cv.bind("<B2-Motion>", self._move)
        cv.bind("<ButtonRelease-2>", self._release)
        for seq, fn in [("<Control-plus>", lambda: self.zoom_by(1.25)), ("<Control-equal>", lambda: self.zoom_by(1.25)),
                        ("<Control-minus>", lambda: self.zoom_by(0.8)), ("<Control-KP_Add>", lambda: self.zoom_by(1.25)),
                        ("<Control-KP_Subtract>", lambda: self.zoom_by(0.8)), ("<Control-Key-0>", self.fit),
                        ("<Control-Key-1>", lambda: self.set_zoom(1.0)),
                        ("<Control-Key-2>", lambda: self.fit(width_only=True))]:
            cv.bind(seq, lambda e, f=fn: (f(), "break")[1])
        cv.bind("<Configure>", lambda e: self._on_resize())
        self.minimap = tk.Canvas(body, width=self.MAP_W, height=self.MAP_H, bg=C["bg_card"], cursor="hand2",
                                 highlightthickness=1, highlightbackground=C.get("border", C["bg_input"]))
        self.minimap.bind("<ButtonPress-1>", self._map_jump)
        self.minimap.bind("<B1-Motion>", self._map_jump)
        _tip(self.minimap, "Harta rutinei: click sau trage ca sa mergi acolo")
        self.cards: Dict[str, int] = {}     # node.id -> dreptunghiul cardului (pe canvas)
        self._selected = ""
        self._width = 0
        self._last_w = 0

    def _build_bar(self):
        C = self.C
        bar = tk.Frame(self, bg=C["bg_main"])
        bar.pack(side="top", fill="x", pady=(0, 2))

        def btn(text, cmd, tip):
            b = tk.Button(bar, text=text, command=cmd, bg=C["bg_input"], fg=C["text"], relief="flat", bd=0,
                          activebackground=C["primary"], activeforeground=ui_theme.text_on(C["primary"], self),
                          font=(FONT, 9), padx=7, pady=2, cursor="hand2", highlightthickness=0)
            b.pack(side="left", padx=1)
            _tip(b, tip)
            return b

        btn("−", lambda: self.zoom_by(0.8), "Micsoreaza (Ctrl + rotita / Ctrl + -)")
        self._zoom_lbl = tk.Label(bar, text="100 %", width=6, bg=C["bg_main"], fg=C["text"], font=(FONT, 9))
        self._zoom_lbl.pack(side="left")
        btn("+", lambda: self.zoom_by(1.25), "Mareste (Ctrl + rotita / Ctrl + +)")
        btn("⤢ Potriveste", self.fit, "Toata rutina pe ecran (Ctrl + 0)")
        btn("↔ Latime", lambda: self.fit(width_only=True), "Toata latimea pe ecran; derulezi doar in jos (Ctrl + 2)")
        btn("1:1", lambda: self.set_zoom(1.0), "Marimea normala (Ctrl + 1)")
        btn("▸ Restrange tot", self.collapse_all, "Ascunde pasii din ramurile Daca / Bucla (click pe ▾ / ▸ de pe card = doar acela)")
        btn("▾ Extinde tot", self.expand_all, "Arata din nou toti pasii")
        self._map_btn = btn("🗺 Harta", self.toggle_map, "Arata / ascunde harta mica din colt")
        btn("⬇ Export", self.export_dialog, "Salveaza fluxul ca imagine mare PNG sau SVG (se deschide in browser, cu zoom oricat)")
        if self.detached:
            btn("⛶ Ecran complet", lambda: self.winfo_toplevel().toggle_full(), "Fereastra pe tot ecranul (F11; Esc = iesi)")
        else:
            btn("🗗 Fereastra separata", self.open_window,
                "Fluxul in fereastra lui: o muti pe alt monitor si urmaresti rularea pe culori")
        tk.Label(bar, text="Trage pe fundal ca sa muti harta", bg=C["bg_main"], fg=C["text_dim"],
                 font=(FONT, 8)).pack(side="left", padx=8)

    # ── derulare + zoom ──
    def _wheel(self, e):
        return self._scroll_y(-1 if e.delta > 0 else 1)

    def _scroll_y(self, n):
        self.canvas.yview_scroll(n, "units")
        return "break"

    def _scroll_x(self, n):
        self.canvas.xview_scroll(n, "units")
        return "break"

    def zoom_by(self, f: float):
        cv = self.canvas
        self._zoom_at(f, cv.winfo_width() / 2, cv.winfo_height() / 2)

    def set_zoom(self, z: float):
        self._zoom_at(z / self.z, self.canvas.winfo_width() / 2, self.canvas.winfo_height() / 2)

    def _zoom_at(self, f: float, sx: float, sy: float):
        """Zoom pastrand punctul de sub mouse (sx, sy = pe ecran) in acelasi loc."""
        new = max(self.ZMIN, min(self.ZMAX, self.z * f))
        if abs(new - self.z) < 1e-3:
            return "break"
        cv = self.canvas
        lx = cv.canvasx(sx) / self.z - self._ox
        ly = cv.canvasy(sy) / self.z
        self.z = new
        self._render()
        self._scroll_to((lx + self._ox) * self.z - sx, ly * self.z - sy)
        return "break"

    def fit(self, width_only: bool = False):
        """Toata rutina pe ecran; width_only = doar latimea (apoi derulezi in jos, textul ramane citibil)."""
        cv = self.canvas
        W, H = max(50, cv.winfo_width()), max(50, cv.winfo_height())
        w, h = self._size
        if w <= 0 or h <= 0:
            return
        zw = (W - 20) / (w + 20)
        self.z = max(self.ZMIN, min(1.25, zw if width_only else min(zw, (H - 10) / (h + 30))))
        self._render()
        self._scroll_to(0, 0)

    def _scroll_to(self, left: float, top: float):
        """Coltul stanga-sus al ferestrei = punctul (left, top) de pe canvas."""
        cv = self.canvas
        cv.update_idletasks()
        sr = self._sr
        sw, sh = sr[2] - sr[0], sr[3] - sr[1]
        if sw > 0:
            cv.xview_moveto(max(0.0, (left - sr[0]) / sw))
        if sh > 0:
            cv.yview_moveto(max(0.0, (top - sr[1]) / sh))

    def _on_resize(self):
        W = self.canvas.winfo_width()
        if abs(W - self._last_w) > 2 and self._prims:
            self._last_w = W
            l, t = self.canvas.canvasx(0), self.canvas.canvasy(0)
            self._render()
            self._scroll_to(l, t)
        self._place_map()

    # ── tragere pe fundal (ca pe o harta) ──
    def _on_card(self) -> bool:
        cur = self.canvas.find_withtag("current")
        return bool(cur) and any(t.startswith("n") or t.startswith("tog") for t in self.canvas.gettags(cur[0]))

    def _press(self, e):
        self.canvas.focus_set()     # pentru Ctrl + / Ctrl - / Ctrl 0
        if not self._on_card():
            self._start_pan(e)

    def _start_pan(self, e):
        self._drag = (e.x, e.y)
        self.canvas.scan_mark(e.x, e.y)
        self.canvas.configure(cursor="fleur")

    def _move(self, e):
        if self._drag:
            self.canvas.scan_dragto(e.x, e.y, gain=1)

    def _release(self, _e=None):
        if self._drag:
            self._drag = None
            self.canvas.configure(cursor="")

    # ── restrangerea ramurilor ──
    @staticmethod
    def _count(nodes) -> int:
        return sum(1 + sum(FlowView._count(lst) for _, lst in n.branches()) for n in nodes)

    def toggle(self, node_id: str):
        if node_id in self.collapsed:
            self.collapsed.discard(node_id)
        else:
            self.collapsed.add(node_id)
        self.refresh(keep_view=True)

    def collapse_all(self):
        self.collapsed = {n.id for n in self.p.routine.all_nodes() if any(lst for _, lst in n.branches())}
        self.refresh(keep_view=True)

    def expand_all(self):
        self.collapsed.clear()
        self.refresh(keep_view=True)

    # ── masurare (coordonate logice) ──
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
        if not br or n.id in self.collapsed:
            return self.CW, self.CH
        cols = [self._measure_list(lst) for _, lst in br]
        w = max(self.CW, sum(c[0] for c in cols) + self.COLGAP * (len(cols) - 1))
        h = self.CH + self.GAP + self.LBL + max(c[1] for c in cols) + self.GAP
        return w, h

    # ── primitive (coordonate logice) ──
    def _rect(self, x1, y1, x2, y2, fill, outline="", tag=""):
        self._prims.append(("rect", (x1, y1, x2, y2), fill, outline, tag))

    def _oval(self, x1, y1, x2, y2, fill):
        self._prims.append(("oval", (x1, y1, x2, y2), fill, "", ""))

    def _line(self, *pts, arrow=None):
        self._prims.append(("line", pts, self.C["text_dim"], arrow, ""))

    def _text(self, x, y, text, color, size, style="normal", anchor="center", tag=""):
        self._prims.append(("text", (x, y), text, color, size, style, anchor, tag))

    def refresh(self, keep_view: bool = False):
        cv = self.canvas
        view = (cv.canvasx(0) / self.z - self._ox, cv.canvasy(0) / self.z) if keep_view else None
        self._prims = []
        self._owner = {}
        steps = self.p.routine.steps
        ids = {n.id for n in self.p.routine.all_nodes()}
        self.collapsed &= ids
        w, h = self._measure_list(steps)
        self._width = w
        x0 = max(self.CW // 2 + 20, w // 2 + 20)
        name = self.p.routine.name or "Rutina noua"
        self._text(x0, 14, name, self.C["text"], 12, "bold")
        self._oval(x0 - 6, 34, x0 + 6, 46, self.C["primary"])
        top = 66
        self._line(x0, 46, x0, top, arrow="last")
        if steps:
            end = self._draw_list(steps, x0, top)
        else:
            self._text(x0, top + 12, "Rutina nu are pasi inca. Adauga-i din 🧱 Pasi.", self.C["text_dim"], 10)
            end = top + 24
        self._line(x0, end, x0, end + 18, arrow="last")
        self._rect(x0 - 6, end + 20, x0 + 6, end + 32, self.C["text_dim"])
        self._size = (x0 * 2, end + 40)
        if self.detached:
            self.winfo_toplevel()._title()
        self._render()
        if view:
            self._scroll_to((view[0] + self._ox) * self.z, view[1] * self.z)

    def _render(self):
        """Deseneaza primitivele pe canvas la zoom-ul curent (textul se ascunde cand ar fi prea mic)."""
        cv, z = self.canvas, self.z
        cv.delete("all")
        self.cards.clear()
        W, H = cv.winfo_width(), cv.winfo_height()
        w, h = self._size
        self._ox = max(0.0, (W / z - w) / 2)       # fluxul sta pe mijloc cand e mai ingust decat fereastra
        ox = self._ox
        for p in self._prims:
            kind = p[0]
            if kind == "text":
                (x, y), text, color, size, style, anchor, tag = p[1:]
                fs = round(size * z)
                if fs < 4:
                    continue
                tags = ("flow", tag) if tag else ("flow",)
                cv.create_text((x + ox) * z, y * z, text=text, fill=color, anchor=anchor,
                               font=(FONT, fs, style) if style != "normal" else (FONT, fs), tags=tags)
                continue
            if kind == "line":
                pts, color, arrow, _ = p[1:]
                xy = [(v + ox) * z if i % 2 == 0 else v * z for i, v in enumerate(pts)]
                kw = {"arrow": arrow, "arrowshape": (max(3, 8 * z), max(4, 10 * z), max(2, 3 * z))} if arrow else {}
                cv.create_line(*xy, fill=color, width=1, tags=("flow",), **kw)
                continue
            (x1, y1, x2, y2), fill, outline, tag = p[1:]
            xy = ((x1 + ox) * z, y1 * z, (x2 + ox) * z, y2 * z)
            if kind == "oval":
                cv.create_oval(*xy, fill=fill, outline="", tags=("flow",))
            elif tag.startswith("card:"):
                nid = tag[5:]
                self.cards[nid] = cv.create_rectangle(*xy, fill=fill, outline=outline, width=1,
                                                      tags=("flow", "n" + nid, "card"))
            else:
                tags = ("flow", tag) if tag else ("flow",)
                cv.create_rectangle(*xy, fill=fill, outline=outline or fill, tags=tags)
        for nid in self.cards:
            tag = "n" + nid
            cv.tag_bind(tag, "<Button-1>", lambda e, i=nid: self.pick(i))
            cv.tag_bind(tag, "<Double-Button-1>", lambda e, i=nid: self.p.show_center("steps", select=i))
            cv.tag_bind("tog" + nid, "<Button-1>", lambda e, i=nid: (self.toggle(i), "break")[1])
        self._sr = (0.0, 0.0, max(W, (w + 2 * ox) * z), max(H, h * z + 20))
        cv.configure(scrollregion=self._sr)
        self._zoom_lbl.configure(text=f"{round(z * 100)} %")
        self.sync_states()
        self._draw_map()

    def _draw_list(self, nodes, cx: float, y: float) -> float:
        if not nodes:
            self._text(cx, y + 12, "(gol)", self.C["text_dim"], 9, "italic")
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

    def _hide(self, nodes, owner: str):
        for n in nodes:
            self._owner[n.id] = owner
            for _, lst in n.branches():
                self._hide(lst, owner)

    def _draw_node(self, n, cx: float, y: float) -> float:
        C = self.C
        try:
            from studio_ui import icon_for
            icon = icon_for(n)
        except Exception:  # noqa: BLE001
            icon = "•"
        x1, x2 = cx - self.CW / 2, cx + self.CW / 2
        tag = f"n{n.id}"
        fill = C["bg_card"]
        self._rect(x1, y, x2, y + self.CH, fill, C.get("border", C["bg_input"]), "card:" + n.id)
        strip = self._kind_color(n)
        self._rect(x1, y, x1 + 5, y + self.CH, strip, strip, tag)
        fg = C["text"] if n.enabled else ui_theme.readable(C["text_muted"], fill, 3.0, self)
        br = n.branches()
        has_kids = any(lst for _, lst in br)
        folded = n.id in self.collapsed and bool(br)
        n_title = 25 if has_kids else 30
        self._text(x1 + 14, y + self.CH / 2, f"{icon}  {_short(tr(n.title), n_title)}", fg, 10,
                   "normal" if n.enabled else "italic", "w", tag)
        if has_kids:
            self._rect(x2 - 34, y + 8, x2 - 6, y + self.CH - 8, C["bg_input"], "", "tog" + n.id)
            self._text(x2 - 20, y + self.CH / 2, "▸" if folded else "▾", C["text"], 10, "bold", "center", "tog" + n.id)
        if not br:
            return y + self.CH
        if folded:
            hidden = sum(self._count(lst) for _, lst in br)
            self._hide([k for _, lst in br for k in lst], n.id)
            self._text(x2 + 6, y + self.CH / 2, f"+{hidden}", ui_theme.readable(strip, C["bg_main"], 4.5, self),
                       9, "bold", "w", "tog" + n.id)
            return y + self.CH
        cols = [self._measure_list(lst) for _, lst in br]
        total = sum(c[0] for c in cols) + self.COLGAP * (len(cols) - 1)
        x = cx - total / 2
        split = y + self.CH + self.GAP / 2
        top = y + self.CH + self.GAP
        self._line(cx, y + self.CH, cx, split)
        bottoms = []
        lbl = ui_theme.readable(strip, C["bg_main"], 4.5, self)
        for (name, lst), (w, h) in zip(br, cols):
            ccx = x + w / 2
            self._line(cx, split, ccx, split)
            self._line(ccx, split, ccx, top + self.LBL - 4, arrow="last")
            self._text(ccx + 6, top + 6, _short(tr(name), 28), lbl, 9, "bold", "w")
            bottoms.append((ccx, self._draw_list(lst, ccx, top + self.LBL)))
            x += w + self.COLGAP
        merge = max(b for _, b in bottoms) + self.GAP / 2
        for ccx, b in bottoms:
            self._line(ccx, b, ccx, merge)
        self._line(min(c for c, _ in bottoms), merge, max(c for c, _ in bottoms), merge)
        if len(bottoms) == 1 and abs(bottoms[0][0] - cx) > 1:
            self._line(bottoms[0][0], merge, cx, merge)
        return merge

    # ── harta mica ──
    def toggle_map(self):
        self._map_on = not self._map_on
        self._place_map()

    def _map_needed(self) -> bool:
        cv = self.canvas
        w, h = self._size
        return w > 0 and (w * self.z > cv.winfo_width() + 2 or h * self.z > cv.winfo_height() + 2)

    def _place_map(self):
        if self._map_on and self._map_needed():
            self.minimap.place(in_=self.canvas, relx=1.0, rely=1.0, x=-8, y=-8, anchor="se")
            tk.Misc.lift(self.minimap)   # Canvas.lift = tag_raise
        else:
            self.minimap.place_forget()

    def _map_scale(self):
        """Scara hartii mici: are forma rutinei (inalta si ingusta la o rutina lunga), max. MAP_W x MAP_H."""
        w, h = self._size
        if w <= 0 or h <= 0:
            return 0.0, 0.0, 0.0
        cv = self.canvas
        mw = min(self.MAP_W, max(60, cv.winfo_width() // 4))
        mh = min(self.MAP_H, max(80, int(cv.winfo_height() * 0.45)))
        s = min((mw - 8) / w, (mh - 8) / h)
        W, H = max(40, int(w * s) + 8), max(40, int(h * s) + 8)
        if (int(float(self.minimap.cget("width"))), int(float(self.minimap.cget("height")))) != (W, H):
            self.minimap.configure(width=W, height=H)
        return s, (W - w * s) / 2, (H - h * s) / 2

    def _draw_map(self):
        mm = self.minimap
        mm.delete("all")
        s, mx, my = self._map_scale()
        if s <= 0:
            self._place_map()
            return
        for p in self._prims:
            if p[0] == "rect" and p[4].startswith("card:"):
                x1, y1, x2, y2 = p[1]
                mm.create_rectangle(mx + x1 * s, my + y1 * s, mx + x2 * s, my + max(y2 * s, y1 * s + 1),
                                    fill=self.C["text_dim"], outline="")
            elif p[0] == "rect" and p[2] != self.C["bg_card"] and p[4].startswith("n"):
                x1, y1, x2, y2 = p[1]   # banda colorata = tipul pasului
                mm.create_rectangle(mx + x1 * s, my + y1 * s, mx + x1 * s + 2, my + max(y2 * s, y1 * s + 1),
                                    fill=p[2], outline="")
        mm.create_rectangle(0, 0, 0, 0, outline=self.C["primary"], width=2, tags=("view",))
        self._map_view()
        self._place_map()

    def _map_view(self):
        mm = getattr(self, "minimap", None)
        if mm is None or not self._prims:
            return
        s, mx, my = self._map_scale()
        cv, z = self.canvas, self.z
        try:
            l, t = cv.canvasx(0) / z - self._ox, cv.canvasy(0) / z
            r, b = l + cv.winfo_width() / z, t + cv.winfo_height() / z
            mm.coords("view", mx + l * s, my + t * s, mx + r * s, my + b * s)
        except tk.TclError:
            pass

    def _map_jump(self, e):
        s, mx, my = self._map_scale()
        if s <= 0:
            return
        cv, z = self.canvas, self.z
        lx, ly = (e.x - mx) / s, (e.y - my) / s
        self._scroll_to((lx + self._ox) * z - cv.winfo_width() / 2, ly * z - cv.winfo_height() / 2)

    def open_window(self):
        """Deschide (sau aduce in fata) fereastra separata cu fluxul."""
        win = getattr(self.p, "_flow_win", None)
        if win is None or not win.winfo_exists():
            win = self.p._flow_win = FlowWindow(self.p)
        else:
            win.deiconify()
            win.lift()
        win.view.refresh()
        sel = self.p.tree.selection()
        if sel and sel[0] in win.view.cards:
            win.view.select(sel[0])
        return win

    # ── export ──
    def export_dialog(self):
        from tkinter import filedialog
        base = "".join(ch if ch.isalnum() or ch in " -_." else "_" for ch in (self.p.routine.name or "Rutina")).strip()
        path = filedialog.asksaveasfilename(parent=self, title="Exporta fluxul", initialfile=f"{base or 'Rutina'}_flux.png",
                                            defaultextension=".png",
                                            filetypes=[("Imagine PNG", "*.png"), ("Imagine vectoriala SVG", "*.svg")])
        if not path:
            return
        try:
            info = self.export_svg(path) if path.lower().endswith(".svg") else self.export_png(path)
        except Exception as ex:  # noqa: BLE001
            self.p.set_status(f"⬇ Export esuat: {ex}")
            return
        self.p.set_status(f"⬇ Flux salvat: {path} ({info})")
        try:
            self.p.open_path(path)
        except Exception:  # noqa: BLE001
            pass

    def _export_box(self):
        w, h = self._size
        return w, h

    def export_svg(self, path: str) -> str:
        """SVG din aceleasi primitive (zoom 100 %); in browser se mareste oricat fara sa se strice textul."""
        from xml.sax.saxutils import escape
        w, h = self._export_box()
        bg = self.C["bg_main"]
        out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w:.0f}" height="{h:.0f}" '
               f'viewBox="0 0 {w:.0f} {h:.0f}" font-family="Segoe UI, Arial, sans-serif">',
               '<defs><marker id="a" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="8" markerHeight="8" '
               f'orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="{self.C["text_dim"]}"/></marker></defs>',
               f'<rect width="100%" height="100%" fill="{bg}"/>']
        anchors = {"w": "start", "center": "middle", "e": "end"}
        for p in self._prims:
            kind = p[0]
            if kind == "text":
                (x, y), text, color, size, style, anchor, _ = p[1:]
                weight = ' font-weight="bold"' if style == "bold" else (' font-style="italic"' if style == "italic" else "")
                out.append(f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size * 4 / 3:.1f}" fill="{color}"{weight} '
                           f'text-anchor="{anchors.get(anchor, "middle")}" dominant-baseline="central">'
                           f'{escape(str(text))}</text>')
            elif kind == "line":
                pts, color, arrow, _ = p[1:]
                pl = " ".join(f"{pts[i]:.1f},{pts[i + 1]:.1f}" for i in range(0, len(pts), 2))
                mk = ' marker-end="url(#a)"' if arrow else ""
                out.append(f'<polyline points="{pl}" fill="none" stroke="{color}" stroke-width="1"{mk}/>')
            else:
                (x1, y1, x2, y2), fill, outline, tag = p[1:]
                if kind == "oval":
                    out.append(f'<ellipse cx="{(x1 + x2) / 2:.1f}" cy="{(y1 + y2) / 2:.1f}" rx="{(x2 - x1) / 2:.1f}" '
                               f'ry="{(y2 - y1) / 2:.1f}" fill="{fill}"/>')
                else:
                    stroke = f' stroke="{outline}"' if outline and outline != fill else ""
                    out.append(f'<rect x="{x1:.1f}" y="{y1:.1f}" width="{x2 - x1:.1f}" height="{y2 - y1:.1f}" '
                               f'fill="{fill}"{stroke}/>')
        out.append("</svg>")
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(out))
        return f"{w:.0f} × {h:.0f}, SVG"

    @staticmethod
    def _png_scale(w: float, h: float) -> float:
        """Cat de mare se face poza: de 2 ori, dar fara sa depaseasca ~40 de milioane de pixeli / 30000 pe latura."""
        if w <= 0 or h <= 0:
            return 1.0
        return max(0.25, min(2.0, (40e6 / (w * h)) ** 0.5, 30000 / max(w, h)))

    def export_png(self, path: str, scale: Optional[float] = None) -> str:
        from PIL import Image, ImageDraw, ImageFont
        w, h = self._export_box()
        s = scale or self._png_scale(w, h)
        img = Image.new("RGB", (max(1, int(w * s)), max(1, int(h * s))), self.C["bg_main"])
        d = ImageDraw.Draw(img)
        fonts: Dict[tuple, Any] = {}

        def font(size, style, emoji=False):
            key = (size, style, emoji)
            if key not in fonts:
                names = (["seguiemj.ttf", "NotoColorEmoji.ttf"] if emoji else
                         {"bold": ["segoeuib.ttf", "DejaVuSans-Bold.ttf"],
                          "italic": ["segoeuii.ttf", "DejaVuSans-Oblique.ttf"]}.get(style, []) +
                         ["segoeui.ttf", "DejaVuSans.ttf", "arial.ttf"])
                f = None
                for nm in names:
                    try:
                        f = ImageFont.truetype(nm, size)
                        break
                    except OSError:
                        continue
                if f is None and not emoji:
                    try:
                        f = ImageFont.load_default(size=size)
                    except TypeError:   # Pillow < 10.1
                        f = ImageFont.load_default()
                fonts[key] = f
            return fonts[key]

        dim = self.C["text_dim"]
        for p in self._prims:
            kind = p[0]
            if kind == "line":
                pts, color, arrow, _ = p[1:]
                xy = [v * s for v in pts]
                d.line(xy, fill=color, width=max(1, round(s)))
                if arrow and len(xy) >= 4:
                    import math
                    (ax, ay), (bx, by) = xy[-4:-2], xy[-2:]
                    ang = math.atan2(by - ay, bx - ax)
                    L, Wd = 9 * s, 4 * s
                    d.polygon([(bx, by), (bx - L * math.cos(ang) + Wd * math.sin(ang), by - L * math.sin(ang) - Wd * math.cos(ang)),
                               (bx - L * math.cos(ang) - Wd * math.sin(ang), by - L * math.sin(ang) + Wd * math.cos(ang))],
                              fill=dim)
            elif kind == "text":
                (x, y), text, color, size, style, anchor, _ = p[1:]
                px = max(6, round(size * 4 / 3 * s))
                text = str(text)
                icon, rest = "", text
                if "  " in text:      # "🔎  Titlu": iconita cu fontul de emoji, daca exista
                    icon, rest = text.split("  ", 1)
                    ef = font(px, style, emoji=True)
                    if ef is None:
                        icon = ""
                f = font(px, style)
                pa = {"w": "lm", "center": "mm", "e": "rm"}.get(anchor, "mm")
                cx, cy = x * s, y * s
                if icon:
                    try:
                        d.text((cx, cy), icon, font=font(px, style, emoji=True), anchor="lm", embedded_color=True)
                        cx += d.textlength(icon + "  ", font=f)
                    except Exception:  # noqa: BLE001 — fontul de emoji nu are marimea ceruta
                        pass
                    d.text((cx, cy), rest, fill=color, font=f, anchor="lm")
                else:
                    d.text((cx, cy), rest, fill=color, font=f, anchor=pa)
            else:
                (x1, y1, x2, y2), fill, outline, tag = p[1:]
                box = [x1 * s, y1 * s, x2 * s, y2 * s]
                if kind == "oval":
                    d.ellipse(box, fill=fill)
                else:
                    d.rectangle(box, fill=fill, outline=(outline or None) if outline != fill else None,
                                width=max(1, round(s)))
        img.save(path, "PNG", optimize=True)
        return f"{img.width} × {img.height} px"

    # ── stare ──
    def pick(self, node_id: str):
        self.select(node_id)
        self.p.select_node(node_id)

    def _reveal(self, node_id: str) -> bool:
        """Pasul ales e intr-o ramura restransa: o deschide (cu toti parintii)."""
        if node_id in self.cards or node_id not in self._owner:
            return False
        parents: Dict[str, str] = {}
        for n in self.p.routine.all_nodes():
            for _, lst in n.branches():
                for k in lst:
                    parents[k.id] = n.id
        cur = parents.get(node_id)
        while cur:
            self.collapsed.discard(cur)
            cur = parents.get(cur)
        return True

    def select(self, node_id: str):
        if self._reveal(node_id):
            self._selected = node_id
            self.refresh(keep_view=True)
            return
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
        except (ValueError, tk.TclError):
            return
        sr = getattr(self, "_sr", None)
        if not sr or sr[3] <= sr[1]:
            return
        top, bottom = cv.canvasy(0), cv.canvasy(cv.winfo_height())
        if y1 < top or y2 > bottom:
            cv.yview_moveto(max(0.0, (y1 - 60 - sr[1]) / (sr[3] - sr[1])))
        left, right = cv.canvasx(0), cv.canvasx(cv.winfo_width())
        if x1 < left or x2 > right:
            cv.xview_moveto(max(0.0, ((x1 + x2) / 2 - cv.winfo_width() / 2 - sr[0]) / (sr[2] - sr[0])))

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
        r = self.cards.get(self._selected)
        if r:   # fara derulare: zoom-ul si tragerea nu sar la pasul ales
            self.canvas.itemconfigure(r, outline=self.C["primary"], width=3)

    def set_state(self, node_id: str):
        if node_id not in self.cards:
            owner = self._owner.get(node_id)   # pasul e intr-o ramura restransa: urmarim cardul ei
            if owner in self.cards and self.p.tree.exists(node_id) and "running" in self.p.tree.item(node_id, "tags"):
                self._see(self.cards[owner])
            return
        self._paint_state(node_id)
        if self.p.tree.exists(node_id) and "running" in self.p.tree.item(node_id, "tags"):
            self._see(self.cards[node_id])   # fluxul urmareste pasul care ruleaza


class FlowWindow(tk.Toplevel):
    """Fluxul intr-o fereastra separata (v4.21): se pune pe al doilea monitor, pe tot ecranul (F11),
    si ramane pe flux in timpul rularii, chiar daca Studio trece pe 📊 Excel."""

    def __init__(self, panel):
        super().__init__(panel.winfo_toplevel())
        self.p = panel
        self.configure(bg=panel.C["bg_main"])
        self.geometry("1000x780")
        self.minsize(420, 320)
        self.view = FlowView(self, panel, detached=True)
        self.view.pack(fill="both", expand=True, padx=4, pady=4)
        self._full = False
        self.bind("<F11>", lambda e: self.toggle_full())
        self.bind("<Escape>", lambda e: self.toggle_full(False))
        self.protocol("WM_DELETE_WINDOW", self.close)
        self._title()

    def _title(self):
        self.title(f"🔀 {tr('Flux')} — {self.p.routine.name or tr('Rutina noua')}")

    def toggle_full(self, on: Optional[bool] = None):
        self._full = (not self._full) if on is None else on
        try:
            self.attributes("-fullscreen", self._full)
        except tk.TclError:
            pass

    def close(self):
        if getattr(self.p, "_flow_win", None) is self:
            self.p._flow_win = None
        self.destroy()


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
