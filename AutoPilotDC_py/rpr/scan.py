# -*- coding: utf-8 -*-
# ============================================================
# AutoPilot DC v4.9 — Scanarea unui site in biblioteca de obiecte
#
#  - scanarea propriu-zisa e in driverul Web (PlaywrightDriver.scan_page):
#    doar citeste pagina deja incarcata, fara click-uri si fara cereri la server;
#  - aici: ce obiecte sunt noi (fara dubluri), adaugarea lor in biblioteca
#    si fisierele de biblioteca pe aplicatie (de ex. in OneDrive):
#        OneDrive\AutoPilotDC\obiecte\<Aplicatie>\obiecte.json
# ============================================================

from __future__ import annotations

import os
import re
from typing import Iterable, List, Optional, Tuple
from urllib.parse import urlsplit

from .model import ObjectRepository, UiObject, sanitize_name
from .report import onedrive_folder

LIBRARY_FILE = "obiecte.json"


def app_name_from_url(url: str) -> str:
    """Numele propus pentru aplicatie: domeniul fara www (ex. https://www.app.local/x -> app.local)."""
    try:
        host = urlsplit((url or "").strip()).hostname or ""
    except ValueError:
        host = ""
    host = re.sub(r"^www\d*\.", "", host)
    return sanitize_name(host) or "Aplicatie"


def libraries_root() -> str:
    """Folderul cu bibliotecile pe aplicatii: in OneDrive daca exista, altfel in Documente."""
    base = onedrive_folder() or os.path.join(os.path.expanduser("~"), "Documents")
    return os.path.join(base, "AutoPilotDC", "obiecte")


def suggest_library_path(app_name: str) -> str:
    return os.path.join(libraries_root(), sanitize_name(app_name) or "Aplicatie", LIBRARY_FILE)


def resolve_library_path(path: str) -> str:
    """Calea salvata pe un laptop poate avea alt folder OneDrive pe celalalt (alt utilizator):
    daca fisierul lipseste, il cautam la acelasi loc relativ in OneDrive-ul de pe acest PC."""
    if not path or os.path.isfile(path):
        return path
    od = onedrive_folder()
    if not od:
        return path
    parts = re.split(r"[\\/]+", path)
    for i, part in enumerate(parts):
        if part.lower().startswith("onedrive"):
            candidate = os.path.join(od, *parts[i + 1:])
            if os.path.isfile(candidate):
                return candidate
    return path


def _best_locator(obj: UiObject):
    return next((l for l in obj.locators if l.enabled and l.value), None)


def find_existing(repo: ObjectRepository, obj: UiObject) -> Optional[UiObject]:
    """Acelasi element deja in biblioteca: aceeasi tehnologie, acelasi site, acelasi iframe
    si cel mai bun locator al lui apare si la obiectul existent."""
    best = _best_locator(obj)
    if best is None:
        return None
    for o in repo.objects:
        if o.technology != obj.technology or list(o.frame_path) != list(obj.frame_path):
            continue
        if obj.site and o.site and o.site.lower() != obj.site.lower():
            continue
        if any(l.kind == best.kind and l.value == best.value for l in o.locators):
            return o
    return None


def new_objects(repo: ObjectRepository, scanned: Iterable[UiObject]) -> Tuple[List[UiObject], int]:
    """Clasifica obiectele scanate si le pastreaza doar pe cele noi (si fara dubluri intre ele).
    Intoarce (obiectele noi, cate erau deja in biblioteca)."""
    fresh: List[UiObject] = []
    seen = ObjectRepository(objects=[], sites=list(repo.sites))
    existing = 0
    for obj in scanned:
        if _best_locator(obj) is None:
            continue
        repo.classify(obj)
        if find_existing(repo, obj) is not None:
            existing += 1
            continue
        if find_existing(seen, obj) is not None:
            continue
        seen.objects.append(obj)
        fresh.append(obj)
    return fresh, existing


def add_objects(repo: ObjectRepository, objs: Iterable[UiObject]) -> int:
    n = 0
    for obj in objs:
        repo.add(obj)
        n += 1
    return n
