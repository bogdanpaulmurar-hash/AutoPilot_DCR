# -*- coding: utf-8 -*-
# ============================================================
# AutoPilot DC — limba fisierelor scrise de motor (v4.8.5)
#
# Excel-ul de intrare (coloana de status), raportul rularii, rezumatul si documentatia
# pregatirilor si logurile text se scriu in limba aleasa in ⚙ Setari → 🌐 Limba fisierelor
# ("ca interfata" implicit). In cod, statusurile raman in romana (OK / EROARE / IN LUCRU ...):
# se traduc doar cand ajung in fisier, iar la citire (reluare) se recunosc in orice limba.
# ============================================================

from __future__ import annotations

from typing import Tuple

IN_PROGRESS = "IN LUCRU"            # statusul randului cat timp se lucreaza la el (textul romanesc)


def _i18n():
    try:
        import i18n
        return i18n
    except ImportError:
        pass
    try:   # rulare cu "py -m rpr" din alt folder: i18n.py sta langa folderul rpr
        import os
        import sys
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        import i18n
        return i18n
    except Exception:  # noqa: BLE001 — motorul folosit fara aplicatie: romana
        return None


def ft(text):
    """Textul in limba fisierelor (neschimbat daca nu are traducere sau daca limba e romana)."""
    m = _i18n()
    if m is None or not isinstance(text, str) or not text:
        return text
    try:
        return m.tr_file(text)
    except Exception:  # noqa: BLE001
        return text


def file_language() -> str:
    m = _i18n()
    try:
        return m.file_language() if m is not None else "ro"
    except Exception:  # noqa: BLE001
        return "ro"


def _all_translations(text: str) -> Tuple[str, ...]:
    out = [text]
    m = _i18n()
    if m is not None:
        for code, _ in m.LANGUAGES:
            try:
                t = m.tr_to(code, text)
            except Exception:  # noqa: BLE001
                continue
            if t and t not in out:
                out.append(t)
    return tuple(out)


def is_in_progress(status: str) -> bool:
    """Randul a ramas "IN LUCRU" (in orice limba: IN PROGRESS, IN BEARBEITUNG...)."""
    s = (status or "").strip().upper()
    return any(s.startswith(w.upper()) for w in _all_translations(IN_PROGRESS))


def is_ok(status: str) -> bool:
    """Rand terminat cu bine (OK in toate limbile)."""
    s = (status or "").strip().upper()
    return any(s.startswith(w.upper()) for w in _all_translations("OK"))
