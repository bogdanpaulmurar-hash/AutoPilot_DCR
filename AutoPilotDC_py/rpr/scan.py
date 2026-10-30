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

from .model import ObjectRepository, UiObject, UiTechnology, sanitize_name, split_url
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


# ============================================================
# v4.10 — 🩺 Verifica butoanele salvate (simulare fara click)
#   Driverul (PlaywrightDriver.check_object) face "click de proba": toate verificarile
#   unui click real, fara sa apese. Aici transformam rezultatul in verdict + motive.
# ============================================================

OK, WARN, REMAP, OTHER_PAGE = "ok", "warn", "remap", "other_page"
STATUS_ICON = {OK: "✅", WARN: "⚠", REMAP: "❌", OTHER_PAGE: "·"}

_FIELD_TYPES = {"Camp text"}


def is_web(obj: UiObject) -> bool:
    return obj.technology in (UiTechnology.Web, UiTechnology.WebSelenium)


def page_of_url(url: str) -> str:
    return split_url(url)[1]


def objects_to_check(repo: ObjectRepository, url: str, whole_site: bool = False) -> List[UiObject]:
    """Obiectele Web din biblioteca valabile pe adresa din browser: doar cele de pe pagina curenta
    sau (whole_site) toate ale site-ului."""
    page = page_of_url(url).lower()
    out = []
    for o in repo.objects:
        if not is_web(o) or not repo.valid_on(o, url) or not o.active_locators:
            continue
        if not whole_site and o.page and o.page.lower() != page:
            continue
        out.append(o)
    return out


def _trial_reason(err: str) -> str:
    """Motivul pentru care un click real nu ar merge, din mesajul Playwright."""
    low = (err or "").lower()
    m = re.search(r"(<[^\n]{1,160}?>)[^\n]*intercepts pointer events", err or "")
    if m or "intercepts pointer events" in low:
        who = m.group(1) if m else "alt element"
        return f"Acoperit de alt element (fereastra, overlay, meniu): {who}"
    if "not visible" in low:
        return "Elementul nu e vizibil (ascuns sau in afara ecranului)"
    if "not enabled" in low or "disabled" in low:
        return "Elementul e dezactivat (gri)"
    if "not stable" in low:
        return "Elementul se misca (animatie): click-ul ar putea nimeri alaturi"
    if "outside of the viewport" in low:
        return "Elementul nu poate fi adus pe ecran"
    if "detached" in low:
        return "Elementul dispare si reapare (pagina se reincarca)"
    line = next((x.strip() for x in (err or "").splitlines() if x.strip()), "")
    return "Click-ul de proba nu a reusit: " + line[:160]


def diagnose(obj: UiObject, res: dict, current_url: str = "") -> Tuple[str, List[str]]:
    """(stare, motive) pentru un obiect verificat. Stari: ok / warn (merge, dar cu impedimente) /
    remap (trebuie recaptat) / other_page (e pe alta pagina decat cea din browser)."""
    reasons: List[str] = []
    counts = res.get("counts", [])
    if not res.get("found"):
        page = page_of_url(current_url or res.get("url", ""))
        if obj.page and page and obj.page.lower() != page.lower():
            return OTHER_PAGE, [f"E pe pagina {obj.page}; in browser e deschisa {page}. Deschide pagina lui si verifica din nou."]
        if res.get("container_found") is False:
            reasons.append(f"Containerul [{obj.parent}] nu mai e gasit pe pagina")
        if any(n == -1 for _, n in counts):
            reasons.append("Un locator e scris gresit (invalid)")
        reasons.append("Niciun locator nu mai gaseste elementul: trebuie recaptat "
                       "(sau elementul apare doar dupa o actiune: meniu, tab, filtru)")
        return REMAP, reasons
    used = res.get("used")
    first = counts[0] if counts else None
    if first is not None and used is not None and first[0] is not used:
        n = first[1]
        what = "nu mai gaseste nimic" if n == 0 else ("e invalid" if n == -1 else f"gaseste {n} elemente")
        reasons.append(f"Primul locator ({first[0].kind.value}) {what}; merge doar cel de rezerva "
                       f"({used.kind.value}): Repara locatorii")
    used_n = next((n for l, n in counts if l is used), 1)
    if used_n and used_n > 1:
        reasons.append(f"Locatorul gaseste {used_n} elemente: se ia primul, poate nu cel bun")
    tag = res.get("tag", "")
    old_tag = (obj.element_type or "").split(" ")[0].lower()
    if tag and old_tag and old_tag.isalpha() and tag != old_tag:
        reasons.append(f"Pare alt element: era <{old_tag}>, acum <{tag}>. Verifica-l in browser sau recapteaza-l")
    old_text, text = (obj.captured_text or "").strip(), (res.get("text") or "").strip()
    if old_text and text and old_text.lower() != text.lower() and old_text.lower() not in text.lower():
        reasons.append(f"Textul s-a schimbat: era \"{old_text[:40]}\", acum \"{text[:40]}\"")
    if res.get("trial") is False:
        reasons.append(_trial_reason(res.get("trial_error", "")))
    elif res.get("enabled") is False:
        reasons.append("Elementul e dezactivat (gri)")
    if obj.object_type in _FIELD_TYPES and res.get("editable") is False:
        reasons.append("Campul nu accepta scriere (doar citire)")
    return (WARN if reasons else OK), reasons


def fix_locators(obj: UiObject, used) -> bool:
    """Locatorul care merge trece primul (ceilalti raman, pot merge pe alt sistem: test / productie)."""
    if used is None or used not in obj.locators or obj.locators[0] is used:
        return False
    obj.locators.remove(used)
    obj.locators.insert(0, used)
    return True


def apply_recapture(old: UiObject, new: UiObject) -> None:
    """Recaptare: obiectul pastreaza numele, tipul, site-ul, pagina si containerul (rutinele merg mai
    departe); primeste locatorii si datele elementului nou."""
    for f in ("locators", "frame_path", "element_type", "captured_text", "screenshot", "attributes",
              "context", "captured_at"):
        setattr(old, f, getattr(new, f))


# ============================================================
# v4.11 — foldere in biblioteca (Site · Pagina · Folder · obiect)
#   Un folder doar grupeaza obiectele (ca meniurile aplicatiei: "Comenzi/Export");
#   spre deosebire de container, nu schimba locul unde se cauta elementul pe pagina.
# ============================================================

def normalize_folder(folder: str) -> str:
    """"Comenzi \\ Export/" -> "Comenzi/Export"."""
    return "/".join(p.strip() for p in (folder or "").replace("\\", "/").split("/") if p.strip())


def folder_parts(obj_or_folder) -> List[str]:
    f = obj_or_folder if isinstance(obj_or_folder, str) else getattr(obj_or_folder, "folder", "")
    return normalize_folder(f).split("/") if normalize_folder(f) else []


def all_folders(repo: ObjectRepository) -> List[str]:
    """Toate folderele din biblioteca, cu parintii lor (pentru liste de alegere)."""
    out = set()
    for o in repo.objects:
        parts = folder_parts(o)
        for i in range(1, len(parts) + 1):
            out.add("/".join(parts[:i]))
    return sorted(out, key=str.lower)


def in_folder(obj: UiObject, path: str) -> bool:
    """Obiectul e in folderul dat sau intr-un subfolder al lui."""
    f, p = normalize_folder(obj.folder).lower(), normalize_folder(path).lower()
    return bool(p) and (f == p or f.startswith(p + "/"))


def rename_folder(objs: Iterable[UiObject], old_path: str, new_last: str) -> int:
    """Redenumeste ultimul segment al folderului (si al subfolderelor lui) pe obiectele date."""
    old = folder_parts(old_path)
    new_last = normalize_folder(new_last).replace("/", " ").strip()
    if not old or not new_last:
        return 0
    new = old[:-1] + [new_last]
    n = 0
    for o in objs:
        parts = folder_parts(o)
        if [x.lower() for x in parts[:len(old)]] == [x.lower() for x in old]:
            o.folder = "/".join(new + parts[len(old):])
            n += 1
    return n


def rename_page(objs: Iterable[UiObject], new_name: str) -> int:
    """Pagina noua pentru toate obiectele date (v4.11.1)."""
    n = 0
    for o in objs:
        o.page = new_name.strip()
        n += 1
    return n


def rename_site(repo: ObjectRepository, objs: Iterable[UiObject], old: str, new_name: str) -> int:
    """Site-ul nou pentru obiectele date; grupul de link-uri al site-ului (daca exista) isi schimba si el numele."""
    new_name = new_name.strip()
    n = 0
    for o in objs:
        o.site = new_name
        n += 1
    g = repo.find_site(old) if old else None
    if g is not None and repo.find_site(new_name) is None:
        g.name = new_name
    return n
