# -*- coding: utf-8 -*-
# ============================================================
# AutoPilot DC v4.14 — unde se salveaza fisierele create
#
# 🌐 Setari Studio → 📁 Unde se salveaza:
#   - un FOLDER COMUN (de ex. in OneDrive): tot ce nu are un folder propriu ajunge in
#       <comun>\rutine   <comun>\obiecte   <comun>\rezultate   <comun>\filme
#   - cate un folder pentru fiecare fel de fisier (gol = in folderul comun)
#   - ce se seteaza pe o rutina (folderul filmelor / raportului) sau pe o biblioteca
#     (fisierul ei) are prioritate
#   Fara nimic setat, totul ramane ca inainte (%APPDATA%\AutoPilotDC\Studio\...).
#
# Valorile stau in studio-setari.json (campuri pe care varianta C# le ignora):
#   "save_base_folder": "...", "save_folders": {"libraries": "...", "results": "..."}
#   Folderul rutinelor e "routines_folder" (acelasi cu 📂 Manager rutine);
#   folderul filmelor e in setarile video (screen_recorder.VideoSettings).
# ============================================================

from __future__ import annotations

import json
import os
from typing import Dict, Optional, Tuple

# cheie, eticheta, subfolderul din folderul comun
KINDS = [("routines", "Rutine", "rutine"),
         ("libraries", "Biblioteci de obiecte", "obiecte"),
         ("results", "Rezultate (capturi, loguri, rapoarte Excel)", "rezultate"),
         ("videos", "Filme", "filme")]
SUBFOLDER = {k: sub for k, _, sub in KINDS}

_cache: Dict[str, object] = {"key": None, "data": {}}


def settings_file() -> str:
    from .storage import RprPaths
    return os.path.join(RprPaths.root, "studio-setari.json")


def _data() -> dict:
    path = settings_file()
    try:
        st = os.stat(path)
        key: Optional[Tuple] = (path, st.st_mtime_ns, st.st_size)
    except OSError:
        return {}
    if _cache["key"] != key:
        try:
            with open(path, encoding="utf-8-sig") as f:
                d = json.load(f)
            _cache["data"] = d if isinstance(d, dict) else {}
        except (OSError, ValueError):
            _cache["data"] = {}
        _cache["key"] = key
    return _cache["data"]  # type: ignore[return-value]


def reset() -> None:
    """Dupa salvarea setarilor: citim din nou fisierul."""
    _cache["key"] = None


def _clean(p) -> str:
    return os.path.expandvars(str(p or "").strip().strip('"'))


def base() -> str:
    """Folderul comun (gol = nesetat)."""
    return _clean(_data().get("save_base_folder"))


def explicit(kind: str) -> str:
    """Folderul setat anume pentru acest fel de fisiere (gol = nesetat)."""
    d = _data()
    if kind == "routines":
        return _clean(d.get("routines_folder"))
    folders = d.get("save_folders") or {}
    return _clean(folders.get(kind)) if isinstance(folders, dict) else ""


def common(kind: str) -> str:
    """<folderul comun>\\<subfolder> sau gol daca nu e setat folderul comun."""
    b = base()
    return os.path.join(b, SUBFOLDER.get(kind, kind)) if b else ""


def folder(kind: str, default: str = "") -> str:
    """Folderul efectiv: cel setat anume, altfel cel din folderul comun, altfel cel implicit."""
    return explicit(kind) or common(kind) or default


def describe(kind: str, default: str = "") -> str:
    """Pentru interfata: unde ajung fisierele daca nu se seteaza nimic anume."""
    return common(kind) or default
