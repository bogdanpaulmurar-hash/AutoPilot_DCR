# -*- coding: utf-8 -*-
# ============================================================
# AutoPilot DC v4.1 — RPR (Python)
# variables.py — Variabilele rularii + inlocuirea {Variabila}
#
# Numele nu tin cont de litere mari/mici. Variabile speciale:
#   {Azi} / {Today}     -> data curenta (dd.MM.yyyy)
#   {Acum} / {Now}      -> data si ora (dd.MM.yyyy HH:mm:ss)
#   {Acum:yyyyMMdd}     -> data/ora in formatul dat (format .NET, ca in C#)
#   {NewLine}           -> rand nou
#   {Nume:url} {Nume:upper} {Nume:lower} {Nume:trim}
# Acoladele literale se scriu dublate: {{ si }}.
# ============================================================

from __future__ import annotations

import datetime as _dt
import os
import re
from typing import Dict, List, Optional, Tuple
from urllib.parse import quote

# Formatul .NET (dd.MM.yyyy HH:mm:ss) -> strftime
_NET_TOKENS = [
    ("yyyy", "%Y"), ("yy", "%y"), ("MM", "%m"), ("dd", "%d"), ("HH", "%H"),
    ("hh", "%I"), ("mm", "%M"), ("ss", "%S"), ("fff", "{ms}"), ("tt", "%p"),
]


def format_net_date(d: _dt.datetime, fmt: str) -> str:
    """Formateaza o data cu un format .NET (doar token-urile uzuale)."""
    out, i = [], 0
    while i < len(fmt):
        for tok, rep in _NET_TOKENS:
            if fmt.startswith(tok, i):
                out.append(rep)
                i += len(tok)
                break
        else:
            ch = fmt[i]
            out.append("%%" if ch == "%" else ch)
            i += 1
    return d.strftime("".join(out)).replace("{ms}", f"{d.microsecond // 1000:03d}")


class VariableStore:
    def __init__(self) -> None:
        self._values: Dict[str, Tuple[str, str]] = {}   # cheie lower -> (nume original, valoare)

    # ── Acces ────────────────────────────────────────────────
    @property
    def all(self) -> Dict[str, str]:
        return {name: value for name, value in self._values.values()}

    @staticmethod
    def _norm(name: str) -> str:
        return (name or "").strip().lstrip("{").rstrip("}").strip()

    def set(self, name: str, value: Optional[str]) -> None:
        if not name or not name.strip():
            return
        n = self._norm(name)
        self._values[n.lower()] = (n, "" if value is None else str(value))

    def remove(self, name: str) -> None:
        self._values.pop(self._norm(name).lower(), None)

    def remove_prefix(self, prefix: str) -> None:
        p = prefix.lower()
        for k in [k for k in self._values if k.startswith(p)]:
            del self._values[k]

    def try_get(self, name: str) -> Tuple[bool, str]:
        name = self._norm(name)
        hit = self._values.get(name.lower())
        if hit is not None:
            return True, hit[1]

        now = _dt.datetime.now()
        base, _, fmt = name.partition(":")
        fmt_opt = fmt if ":" in name else None

        # {Variabila:url} / :upper / :lower / :trim
        if fmt_opt is not None:
            raw = self._values.get(base.strip().lower())
            if raw is not None:
                f = fmt_opt.strip().lower()
                if f == "url":
                    return True, quote(raw[1], safe="-_.~")
                if f == "upper":
                    return True, raw[1].upper()
                if f == "lower":
                    return True, raw[1].lower()
                if f == "trim":
                    return True, raw[1].strip()

        b = base.lower()
        if b in ("azi", "today"):
            return True, format_net_date(now, fmt_opt or "dd.MM.yyyy")
        if b in ("acum", "now"):
            return True, format_net_date(now, fmt_opt or "dd.MM.yyyy HH:mm:ss")
        if b == "newline":
            return True, os.linesep
        return False, ""

    def get(self, name: str) -> str:
        return self.try_get(name)[1]

    # ── Resolve: inlocuieste {Nume} in text ──────────────────
    def resolve(self, template: Optional[str], unknown: Optional[List[str]] = None) -> str:
        """Variabilele necunoscute raman neschimbate (si sunt adaugate in `unknown`)."""
        if not template:
            return ""
        if "{" not in template and "}" not in template:
            return template
        out, i, n = [], 0, len(template)
        while i < n:
            c = template[i]
            # 1. acolade dublate = caracter literal
            if c == "{" and i + 1 < n and template[i + 1] == "{":
                out.append("{"); i += 2; continue
            if c == "}" and i + 1 < n and template[i + 1] == "}":
                out.append("}"); i += 2; continue
            # 2. {Nume}
            if c == "{":
                end = template.find("}", i + 1)
                if end > i + 1:
                    name = template[i + 1:end]
                    if "{" not in name:
                        ok, val = self.try_get(name)
                        if ok:
                            out.append(val)
                            i = end + 1
                            continue
                        if unknown is not None:
                            unknown.append(name)
            out.append(c)
            i += 1
        return "".join(out)


_VAR_RE = re.compile(r"(?<!\{)\{([^{}]+)\}(?!\})")


def variables_in(text: str) -> List[str]:
    """Numele variabilelor folosite intr-un text (pentru Studio / validare)."""
    return [m.group(1) for m in _VAR_RE.finditer(text or "")]
