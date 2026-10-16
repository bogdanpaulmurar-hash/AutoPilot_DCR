# -*- coding: utf-8 -*-
# ============================================================
# AutoPilot DC — limbi: Romana (sursa) / English / Deutsch
#
# Textele din cod sunt in romana; i18n/en.json si i18n/de.json au traducerile
# (cheia = textul romanesc; mesajele cu valori variabile sunt sabloane "{0}").
# install() traduce automat tot ce ajunge pe ecran prin tkinter: butoane, etichete,
# meniuri, tab-uri, coloane, titluri de ferestre, mesaje. Logica programului
# (nume de obiecte, valori din liste, fisiere) ramane neschimbata.
# Limba se alege din Setari si se aplica la urmatoarea pornire.
# ============================================================

from __future__ import annotations

import json
import os
import re
import string
import threading
from typing import Dict, List, Optional, Tuple

LANGUAGES = [("ro", "Română"), ("en", "English"), ("de", "Deutsch")]
_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "i18n")
_SETTINGS = os.path.join(os.environ.get("APPDATA") or os.path.expanduser("~"), "AutoPilotDC", "limba.json")

LANG = "ro"
_exact: Dict[str, str] = {}
_templates: List[Tuple["re.Pattern", str, str]] = []   # (regex, sablon tradus, prefix literal)
_by_prefix: Dict[str, List[int]] = {}
_lock = threading.Lock()
_installed = False


# ─────────────────────────────────────────────────────────────
# Setare limba
# ─────────────────────────────────────────────────────────────
def saved_language() -> str:
    try:
        with open(_SETTINGS, encoding="utf-8") as f:
            lang = str(json.load(f).get("limba", "ro"))
        return lang if lang in dict(LANGUAGES) else "ro"
    except (OSError, ValueError):
        return "ro"


def save_language(lang: str) -> None:
    os.makedirs(os.path.dirname(_SETTINGS), exist_ok=True)
    with open(_SETTINGS, "w", encoding="utf-8") as f:
        json.dump({"limba": lang}, f)


# ─────────────────────────────────────────────────────────────
# Traducere
# ─────────────────────────────────────────────────────────────
def _literal(parts: str) -> str:
    return parts.replace("{{", "{").replace("}}", "}")


def _compile(src: str) -> Optional["re.Pattern"]:
    """Sablonul romanesc "Rutina '{0}' salvata" -> regex cu grupuri pentru valori."""
    out, n = [], 0
    try:
        for lit, field, _, _ in string.Formatter().parse(src):
            out.append(re.escape(lit))
            if field is not None:
                out.append(r"(?P<f%s>.*?)" % field if field.isdigit() else r"(.*?)")
                n += 1
    except ValueError:
        return None
    if n == 0:
        return None
    try:
        return re.compile("^" + "".join(out) + "$", re.S)
    except re.error:
        return None


def load(lang: str) -> None:
    global LANG
    with _lock:
        LANG = lang if lang in dict(LANGUAGES) else "ro"
        _exact.clear()
        _templates.clear()
        _by_prefix.clear()
        if LANG == "ro":
            return
        try:
            with open(os.path.join(_DIR, LANG + ".json"), encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, ValueError):
            return
        for src, dst in data.items():
            if not dst:
                continue
            rx = _compile(src) if re.search(r"\{\d+\}", src) else None
            if rx is None:
                _exact[src] = dst
            else:
                first = next(iter(string.Formatter().parse(src)))[0]
                prefix = _literal(first)[:4]
                _by_prefix.setdefault(prefix, []).append(len(_templates))
                _templates.append((rx, dst, prefix))


def tr(text):
    """Traducerea unui text (sau textul neschimbat daca nu exista traducere)."""
    if LANG == "ro" or not isinstance(text, str) or not text:
        return text
    hit = _exact.get(text)
    if hit is not None:
        return hit
    stripped = text.strip()
    if stripped != text and stripped in _exact:   # spatii in plus in jur
        lead = text[:len(text) - len(text.lstrip())]
        trail = text[len(text.rstrip()):]
        return lead + _exact[stripped] + trail
    if len(text) > 4000:
        return text
    cands: List[int] = []
    for k in range(5):   # sabloanele sunt indexate dupa primele 0..4 caractere fixe
        cands.extend(_by_prefix.get(text[:k], ()))
    for i in cands:
        rx, dst, _ = _templates[i]
        m = rx.match(text)
        if m:
            vals = {k[1:]: tr_value(v) for k, v in m.groupdict().items()}
            try:
                return dst.format(*[vals.get(str(j), "") for j in range(len(vals))])
            except (IndexError, KeyError, ValueError):
                return text
    return text


def tr_value(v: str) -> str:
    """Valorile din interiorul unui mesaj se traduc doar daca sunt fraze cunoscute (ex. descrierea unei conditii).
    Un singur cuvant (nume de variabila, obiect, fisier) ramane neschimbat."""
    if " " not in v.strip() or len(v) > 400:
        return v
    return tr(v)


# ─────────────────────────────────────────────────────────────
# Legarea de tkinter (o singura data, inainte de crearea ferestrelor)
# ─────────────────────────────────────────────────────────────
_TEXT_KEYS = ("text", "label")


def install(lang: Optional[str] = None) -> str:
    global _installed
    load(lang or saved_language())
    if _installed or LANG == "ro":
        return LANG
    _installed = True
    import tkinter as tk
    from tkinter import messagebox, ttk

    orig_options = tk.Misc._options

    def _options(self, cnf, kw=None):
        if kw:
            for k in _TEXT_KEYS:
                v = kw.get(k)
                if isinstance(v, str):
                    kw = dict(kw)
                    kw[k] = tr(v)
        if isinstance(cnf, dict):
            for k in _TEXT_KEYS:
                v = cnf.get(k)
                if isinstance(v, str):
                    cnf = dict(cnf)
                    cnf[k] = tr(v)
        return orig_options(self, cnf, kw)
    tk.Misc._options = _options

    orig_title = tk.Wm.wm_title

    def wm_title(self, string=None):
        return orig_title(self, tr(string) if isinstance(string, str) else string)
    tk.Wm.wm_title = wm_title
    tk.Wm.title = wm_title

    # ttk: coloane, tab-uri, randuri din tabele (text si valori afisate)
    orig_fmt = ttk._format_optdict

    def _format_optdict(optdict, script=False, ignore=None):
        if optdict:
            changed = None
            for k in ("text",):
                v = optdict.get(k)
                if isinstance(v, str):
                    changed = changed or dict(optdict)
                    changed[k] = tr(v)
            if changed is not None:
                optdict = changed
        return orig_fmt(optdict, script, ignore)
    ttk._format_optdict = _format_optdict

    orig_insert = ttk.Treeview.insert

    def insert(self, parent, index, iid=None, **kw):
        vals = kw.get("values")
        if isinstance(vals, (list, tuple)):
            kw["values"] = [tr(v) if isinstance(v, str) else v for v in vals]
        return orig_insert(self, parent, index, iid, **kw)
    ttk.Treeview.insert = insert

    # mesaje (titlu + text)
    for name in ("showinfo", "showwarning", "showerror", "askquestion", "askokcancel", "askyesno",
                 "askyesnocancel", "askretrycancel"):
        f = getattr(messagebox, name, None)
        if f is None:
            continue

        def wrap(fn):
            def inner(title=None, message=None, **options):
                return fn(tr(title) if isinstance(title, str) else title,
                          tr(message) if isinstance(message, str) else message, **options)
            return inner
        setattr(messagebox, name, wrap(f))

    try:   # dialogurile de fisiere: titlul
        from tkinter import filedialog
        for name in ("askopenfilename", "asksaveasfilename", "askdirectory", "askopenfilenames"):
            f = getattr(filedialog, name, None)
            if f is None:
                continue

            def wrapf(fn):
                def inner(**options):
                    if isinstance(options.get("title"), str):
                        options["title"] = tr(options["title"])
                    if isinstance(options.get("filetypes"), (list, tuple)):
                        options["filetypes"] = [(tr(a), b) if isinstance(a, str) else (a, b)
                                                for a, b in options["filetypes"]]
                    return fn(**options)
                return inner
            setattr(filedialog, name, wrapf(f))
    except ImportError:
        pass
    try:
        from tkinter import simpledialog
        orig_ask = simpledialog.askstring

        def askstring(title, prompt, **kw):
            return orig_ask(tr(title), tr(prompt), **kw)
        simpledialog.askstring = askstring
    except ImportError:
        pass
    return LANG


class TrVar:
    """StringVar pentru texte afisate (bara de stare, contoare): set() traduce automat."""

    def __new__(cls, *args, **kwargs):
        import tkinter as tk

        class _V(tk.StringVar):
            def set(self, value):
                return super().set(tr(value) if isinstance(value, str) else value)
        v = _V(*args, **kwargs)
        if "value" in kwargs:
            v.set(kwargs["value"])
        return v
