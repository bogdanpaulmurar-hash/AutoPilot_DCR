# -*- coding: utf-8 -*-
# ============================================================
# AutoPilot DC — aspectul interfetei (v4.14)
#
#  - marimea textului (Mic / Normal / Mare / Foarte mare): o singura setare care
#    scaleaza tot (fonturile tkinter + widget-urile customtkinter); se aplica la pornire
#  - contrast: culoarea textului se alege dupa fundal (alb sau inchis), iar
#    fix_contrast() repara orice eticheta / buton cu text greu de citit
#  - autowrap(): textele explicative se rup pe randuri dupa latimea panoului
#  - style_combobox(): listele ttk (si cele "readonly") cu culorile temei
# ============================================================

from __future__ import annotations

import json
import os
import tkinter as tk
from tkinter import ttk
from typing import Dict, Optional

_SETTINGS = os.path.join(os.environ.get("APPDATA") or os.path.expanduser("~"), "AutoPilotDC", "aspect.json")

# cheie -> (eticheta, factor)
TEXT_SIZES = [("small", "Mic", 0.9), ("normal", "Normal", 1.0), ("large", "Mare", 1.15), ("xlarge", "Foarte mare", 1.3)]
DARK_TEXT = "#1B1B2E"


# ── setari ────────────────────────────────────────────────────
def load() -> Dict[str, object]:
    try:
        with open(_SETTINGS, encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def save(**values) -> None:
    d = load()
    d.update(values)
    try:
        os.makedirs(os.path.dirname(_SETTINGS), exist_ok=True)
        with open(_SETTINGS, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=1)
    except OSError:
        pass


def text_size() -> str:
    v = str(load().get("text_size", "normal"))
    return v if any(k == v for k, _, _ in TEXT_SIZES) else "normal"


def text_factor(key: Optional[str] = None) -> float:
    key = key or text_size()
    return next((f for k, _, f in TEXT_SIZES if k == key), 1.0)


def apply_scaling(root: tk.Misc) -> float:
    """La pornire, inainte de a construi interfata: fonturile (in puncte) cresc cu factorul ales."""
    f = text_factor()
    if abs(f - 1.0) < 0.01:
        return f
    try:
        cur = float(root.tk.call("tk", "scaling"))
        root.tk.call("tk", "scaling", cur * f)
    except tk.TclError:
        pass
    try:
        import customtkinter as ctk
        ctk.set_widget_scaling(f)
    except Exception:  # noqa: BLE001
        pass
    return f


# ── culori ───────────────────────────────────────────────────
def _rgb(color: str, widget: Optional[tk.Misc] = None):
    c = (color or "").strip()
    if c.startswith("#") and len(c) == 7:
        return tuple(int(c[i:i + 2], 16) for i in (1, 3, 5))
    if c.startswith("#") and len(c) == 4:
        return tuple(int(ch * 2, 16) for ch in c[1:])
    if widget is not None and c:
        try:
            r, g, b = widget.winfo_rgb(c)
            return r // 257, g // 257, b // 257
        except tk.TclError:
            pass
    named = {"white": (255, 255, 255), "black": (0, 0, 0)}
    return named.get(c.lower())


def luminance(color: str, widget: Optional[tk.Misc] = None) -> float:
    rgb = _rgb(color, widget)
    if rgb is None:
        return 0.0

    def ch(v):
        v /= 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = (ch(v) for v in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(fg: str, bg: str, widget: Optional[tk.Misc] = None) -> float:
    """Raportul de contrast WCAG (1 = invizibil, 21 = negru pe alb). Textul normal cere >= 4.5."""
    a, b = luminance(fg, widget), luminance(bg, widget)
    hi, lo = max(a, b), min(a, b)
    return (hi + 0.05) / (lo + 0.05)


def text_on(bg: str, widget: Optional[tk.Misc] = None) -> str:
    """Textul care se citeste cel mai bine pe fundalul dat: alb sau inchis."""
    return "white" if contrast("white", bg, widget) >= contrast(DARK_TEXT, bg, widget) else DARK_TEXT


def readable(color: str, bg: str, minimum: float = 4.5, widget: Optional[tk.Misc] = None) -> str:
    """Aceeasi nuanta, dar mai inchisa / mai deschisa pana se citeste pe fundal
    (ex. verdele "ok" din arbore pe tema deschisa)."""
    rgb = _rgb(color, widget)
    if rgb is None or contrast(color, bg, widget) >= minimum:
        return color
    target = (0, 0, 0) if luminance(bg, widget) > 0.4 else (255, 255, 255)
    best = color
    for step in range(1, 11):
        k = step / 10
        mixed = "#%02X%02X%02X" % tuple(int(c + (t - c) * k) for c, t in zip(rgb, target))
        best = mixed
        if contrast(mixed, bg, widget) >= minimum:
            break
    return best


_FIXABLE = (tk.Label, tk.Button, tk.Checkbutton, tk.Radiobutton, tk.Menubutton, tk.Entry, tk.Text)


def fix_contrast(widget: tk.Misc, minimum: float = 3.0) -> int:
    """Trece prin toate widget-urile si inlocuieste textul greu de citit (fata de fundalul lui).
    Returneaza cate a reparat. Pragul 3.0 lasa in pace textele "estompate" intentionat, dar
    prinde alb pe alb / gri pe gri."""
    fixed = 0
    stack = [widget]
    while stack:
        w = stack.pop()
        try:
            stack.extend(w.winfo_children())
        except tk.TclError:
            continue
        if not isinstance(w, _FIXABLE):
            continue
        try:
            fg, bg = str(w.cget("fg")), str(w.cget("bg"))
            if fg and bg and contrast(fg, bg, w) < minimum:
                w.configure(fg=text_on(bg, w))
                fixed += 1
            if isinstance(w, (tk.Button, tk.Menubutton, tk.Checkbutton, tk.Radiobutton)):
                afg, abg = str(w.cget("activeforeground")), str(w.cget("activebackground"))
                if afg and abg and contrast(afg, abg, w) < minimum:
                    w.configure(activeforeground=text_on(abg, w))
                    fixed += 1
            if isinstance(w, (tk.Checkbutton, tk.Radiobutton)):
                # bifa se deseneaza cu culoarea textului pe "selectcolor"
                sel = str(w.cget("selectcolor"))
                if sel and contrast(str(w.cget("fg")), sel, w) < minimum:
                    w.configure(selectcolor=bg if contrast(str(w.cget("fg")), bg, w) >= minimum else text_on(str(w.cget("fg")), w))
                    fixed += 1
            if isinstance(w, (tk.Entry, tk.Text)):
                ins = str(w.cget("insertbackground"))
                if ins and contrast(ins, bg, w) < minimum:
                    w.configure(insertbackground=str(w.cget("fg")))
        except tk.TclError:
            continue
    return fixed


def install_contrast_guard(root: tk.Misc) -> None:
    """Orice fereastra noua (dialog) e verificata cand apare."""
    def on_map(e):
        if isinstance(e.widget, (tk.Toplevel, tk.Tk)):
            e.widget.after_idle(lambda w=e.widget: _safe_fix(w))
    root.bind_class("Toplevel", "<Map>", on_map, add="+")


def _safe_fix(w):
    try:
        if w.winfo_exists():
            fix_contrast(w)
    except tk.TclError:
        pass


# ── ferestre care incap pe ecran ─────────────────────────────
def fit_window(win: tk.Misc, width: int, height: int, center: bool = True) -> None:
    """Marimea dorita, dar cel mult cat ecranul (laptop 1366 x 768): nimic nu iese in afara."""
    try:
        sw, sh = win.winfo_screenwidth(), win.winfo_screenheight()
    except tk.TclError:
        return
    w, h = min(width, sw - 40), min(height, sh - 90)
    if center:
        win.geometry(f"{w}x{h}+{max(0, (sw - w) // 2)}+{max(0, (sh - h) // 3)}")
    else:
        win.geometry(f"{w}x{h}")


# ── texte care se rup dupa latime ─────────────────────────────
def autowrap(label: tk.Label, margin: int = 6, minimum: int = 80) -> tk.Label:
    """Eticheta (pusa cu fill="x") isi rupe textul la latimea pe care o primeste."""
    def on_conf(e):
        wl = max(minimum, e.width - margin)
        if int(float(str(label.cget("wraplength")) or 0)) != wl:
            label.configure(wraplength=wl)
    label.bind("<Configure>", on_conf, add="+")
    return label


# ── liste ttk ─────────────────────────────────────────────────
def style_combobox(style: ttk.Style, name: str, C: Dict[str, str]) -> None:
    """Combobox cu culorile temei in toate starile. In tema "clam", o lista readonly primea
    fundal deschis, iar textul alb al temei inchise devenea invizibil."""
    bg, fg = C["bg_input"], C["text"]
    style.configure(name, fieldbackground=bg, background=C.get("bg_card", bg), foreground=fg,
                    arrowcolor=fg, bordercolor=C.get("border", bg), lightcolor=bg, darkcolor=bg,
                    selectbackground=bg, selectforeground=fg, padding=4)
    style.map(name,
              fieldbackground=[("disabled", C.get("bg_card", bg)), ("readonly", bg), ("!disabled", bg)],
              foreground=[("disabled", C.get("text_muted", fg)), ("readonly", fg), ("!disabled", fg)],
              selectbackground=[("readonly", bg), ("focus", C.get("primary", bg))],
              selectforeground=[("readonly", fg), ("focus", text_on(C.get("primary", bg)))],
              background=[("active", C.get("bg_card", bg)), ("pressed", C.get("bg_card", bg))],
              arrowcolor=[("disabled", C.get("text_muted", fg))])


def style_popdown(widget: tk.Misc, C: Dict[str, str]) -> None:
    """Lista care se deschide sub un Combobox."""
    widget.option_add("*TCombobox*Listbox.background", C["bg_input"])
    widget.option_add("*TCombobox*Listbox.foreground", C["text"])
    widget.option_add("*TCombobox*Listbox.selectBackground", C["primary"])
    widget.option_add("*TCombobox*Listbox.selectForeground", text_on(C["primary"]))
