# -*- coding: utf-8 -*-
# ============================================================
# AutoPilot DC — RPR (Python)
# drivers/sap_table.py — pasul "SAP: deruleaza tabelul" (v4.22)
# Fara COM / Windows, ca sa se poata testa cu tabele simulate.
# ============================================================

from __future__ import annotations

import re

from .base import RprStepException


def _s(f, default: str = "") -> str:
    try:
        v = f()
        return "" if v is None else str(v)
    except Exception:
        return default


_SCROLL_START = {"inceput", "început", "start", "top", "anfang"}
_SCROLL_END = {"sfarsit", "sfârșit", "end", "bottom", "ende"}


def scroll_table(el, value: str, wait, refind) -> str:
    """Deruleaza un tabel SAP (GuiTableControl sau GuiGridView / ALV).

    value: "5" = randul 5 din tabel (1 = primul) ajunge sus, cat se poate;
           "+1" / "-3" = cu atatea randuri in jos / sus; "inceput" / "sfarsit".
    Intoarce pozitia pe ecran a randului tinta (0 = primul rand vizibil), adica indexul
    din ID-ul celulelor (ex. btnDEL[5,{Pozitie}]). La capatul listei tabelul nu mai coboara,
    dar pozitia creste, deci aceeasi bucla merge pana la ultimul rand.
    """
    v = (value or "").strip().lower()
    grid = _s(lambda: el.Type) == "GuiGridView"
    if grid:
        first = int(_s(lambda: el.FirstVisibleRow) or 0)
        visible = int(_s(lambda: el.VisibleRowCount) or 0)
        top = max(0, int(_s(lambda: el.RowCount) or 0) - max(1, visible))
    else:
        bar = el.VerticalScrollbar
        first = int(_s(lambda: bar.Position) or 0)
        top = int(_s(lambda: bar.Maximum) or 0)
    count = int(_s(lambda: el.RowCount) or 0)

    if v in _SCROLL_START:
        target = 0
    elif v in _SCROLL_END:
        target = max(0, count - 1)
    elif re.fullmatch(r"[+-]\s*\d+", v):
        target = first + int(v.replace(" ", ""))
    elif v.isdigit() and int(v) >= 1:
        target = int(v) - 1
    else:
        raise RprStepException("Valoarea trebuie sa fie un rand (1 = primul), +1 / -1, inceput sau sfarsit.")
    if count and target >= count:
        raise RprStepException(f"Tabelul are doar {count} randuri (cerut: randul {target + 1}).")
    target = max(0, target)

    pos = min(target, max(0, top))
    if pos != first:
        if grid:
            el.FirstVisibleRow = pos
        else:
            el.VerticalScrollbar.Position = pos
        wait()
        if not grid:
            el = refind()   # dupa scroll obiectul tabelului se reincarca
        first = int(_s(lambda: el.FirstVisibleRow if grid else el.VerticalScrollbar.Position) or 0)
    return str(target - first)
