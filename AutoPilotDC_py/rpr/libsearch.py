# -*- coding: utf-8 -*-
# ============================================================
# AutoPilot DC — 🔍 Cautarea in biblioteca de obiecte (v4.25) + 🔎 Gaseste din ecran (v4.26)
#
# Arborele (Aplicatie -> Ecran -> Container -> Obiect) pastreaza obiectele;
# cautarea le gaseste:
#   - textul scris se cauta in nume, textul capturat de pe buton, eticheta,
#     tip, aplicatie, ecran, folder, descriere, etichete si locatori;
#     fara diacritice si fara litere mari; tolereaza o greseala de tastare;
#   - prescurtari: tip:combo  app:SAP  ecran:VA03  stare:stricat  #eticheta;
#   - starea obiectului (merge / stricat / nefolosit / recent / favorit) e
#     calculata din fisierul "<biblioteca>.stare.json" de langa biblioteca si
#     din rutinele care il folosesc ("Folosit in"); obiecte.json nu se schimba.
# ============================================================

from __future__ import annotations

import datetime as _dt
import difflib
import json
import os
import re
import unicodedata
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Tuple

from .model import UiObject

STATE_SUFFIX = ".stare.json"
RECENT_DAYS = 7
MAX_RESULTS = 200

# Starile din filtru (cheia interna, textul din lista)
STATUS_ALL = ""
STATUS_OK = "ok"
STATUS_BAD = "bad"
STATUS_UNUSED = "unused"
STATUS_RECENT = "recent"
STATUS_FAVORITE = "favorite"
STATUS_CHOICES = [(STATUS_ALL, "Toate starile"), (STATUS_OK, "✅ Merge"), (STATUS_BAD, "❌ Stricat"),
                  (STATUS_UNUSED, "⚪ Nefolosit"), (STATUS_RECENT, "🕐 Recent"), (STATUS_FAVORITE, "⭐ Favorit")]

# Prescurtarile din cautare (RO / EN / DE) -> campul filtrat
_PREFIXES = {
    "tip": "type", "type": "type", "typ": "type",
    "app": "app", "site": "app", "aplicatie": "app", "anwendung": "app",
    "ecran": "page", "pagina": "page", "page": "page", "screen": "page", "seite": "page", "bild": "page",
    "stare": "status", "status": "status", "state": "status", "zustand": "status",
}
_STATUS_WORDS = {
    STATUS_OK: ("ok", "merge", "works", "funktioniert", "bun"),
    STATUS_BAD: ("stricat", "bad", "broken", "defekt", "eroare", "error"),
    STATUS_UNUSED: ("nefolosit", "unused", "unbenutzt"),
    STATUS_RECENT: ("recent", "recente", "zuletzt"),
    STATUS_FAVORITE: ("favorit", "favorite", "fav", "favoriten", "stea", "star"),
}
_LABEL_ATTRS = ("label", "aria-label", "title", "placeholder", "name", "text", "value", "alt", "tooltip")


def normalize(text: str) -> str:
    """Litere mici, fara diacritice, spatii simple: "Salvează" -> "salveaza"."""
    s = unicodedata.normalize("NFKD", str(text or ""))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", s.lower()).strip()


def _words(text: str) -> List[str]:
    return [w for w in re.split(r"[^0-9a-z]+", normalize(text)) if w]


# ─────────────────────────────────────────────────────────────
# 1. Cererea scrisa in campul de cautare
# ─────────────────────────────────────────────────────────────
@dataclass
class Query:
    words: List[str] = field(default_factory=list)
    types: List[str] = field(default_factory=list)
    apps: List[str] = field(default_factory=list)
    pages: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    status: str = STATUS_ALL

    @property
    def empty(self) -> bool:
        return not (self.words or self.types or self.apps or self.pages or self.tags or self.status)


def status_from_word(word: str) -> str:
    w = normalize(word)
    for key, words in _STATUS_WORDS.items():
        if w in words:
            return key
    return STATUS_ALL


def parse_query(text: str) -> Query:
    """ "salv tip:buton app:sap #export" -> cuvinte + filtre. Ghilimelele pastreaza spatiile: ecran:"Lista comenzi"."""
    q = Query()
    for m in re.finditer(r'(\S+?):"([^"]*)"|"([^"]*)"|(\S+)', text or ""):
        if m.group(1) is not None:
            key, val = m.group(1), m.group(2)
        else:
            tok = m.group(3) if m.group(3) is not None else m.group(4)
            key, val = "", tok
            if m.group(4) is not None and ":" in tok:
                k, v = tok.split(":", 1)
                if normalize(k) in _PREFIXES and v:
                    key, val = k, v
        val = normalize(val)
        if not val:
            continue
        field_ = _PREFIXES.get(normalize(key), "")
        if field_ == "type":
            q.types.append(val)
        elif field_ == "app":
            q.apps.append(val)
        elif field_ == "page":
            q.pages.append(val)
        elif field_ == "status":
            q.status = status_from_word(val) or q.status
        elif val.startswith("#") and len(val) > 1:
            q.tags.append(val[1:])
        else:
            q.words.extend(_words(val) or [val])
    return q


# ─────────────────────────────────────────────────────────────
# 2. Starea obiectelor: fisierul de langa biblioteca
# ─────────────────────────────────────────────────────────────
def state_path(library_path: str) -> str:
    base = library_path[:-5] if library_path.lower().endswith(".json") else library_path
    return base + STATE_SUFFIX


def _now() -> str:
    return _dt.datetime.now().replace(microsecond=0).isoformat()


def _parse_time(s: str) -> Optional[_dt.datetime]:
    try:
        return _dt.datetime.fromisoformat(str(s))
    except (TypeError, ValueError):
        return None


class LibraryState:
    """Ultima verificare, ultima folosire si favoritele, pe nume de obiect.
    Fisierul lipsa sau stricat = stare goala (cautarea merge oricum)."""

    def __init__(self, path: str = ""):
        self.path = path
        self.objects: Dict[str, Dict[str, object]] = {}
        if path:
            try:
                with open(path, encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict) and isinstance(data.get("objects"), dict):
                    self.objects = {str(k).lower(): dict(v) for k, v in data["objects"].items() if isinstance(v, dict)}
            except (OSError, ValueError):
                self.objects = {}

    @classmethod
    def for_library(cls, library_path: str) -> "LibraryState":
        return cls(state_path(library_path) if library_path else "")

    def save(self) -> None:
        if not self.path:
            return
        from .storage import atomic_write
        try:
            atomic_write(self.path, json.dumps({"version": 1, "objects": self.objects}, ensure_ascii=False, indent=1))
        except OSError:
            pass   # starea e doar ajutatoare; biblioteca se salveaza separat

    def get(self, name: str) -> Dict[str, object]:
        return self.objects.get((name or "").lower(), {})

    def _entry(self, name: str) -> Dict[str, object]:
        return self.objects.setdefault((name or "").lower(), {})

    def mark_checked(self, name: str, ok: bool) -> None:
        e = self._entry(name)
        e["status"] = STATUS_OK if ok else STATUS_BAD
        e["checked_at"] = _now()

    def mark_used(self, name: str) -> None:
        self._entry(name)["used_at"] = _now()

    def toggle_favorite(self, name: str) -> bool:
        e = self._entry(name)
        e["favorite"] = not e.get("favorite")
        if not e["favorite"]:
            e.pop("favorite", None)
        return bool(e.get("favorite"))

    def is_favorite(self, name: str) -> bool:
        return bool(self.get(name).get("favorite"))

    def status(self, name: str) -> str:
        return str(self.get(name).get("status") or "")

    def used_at(self, name: str) -> Optional[_dt.datetime]:
        return _parse_time(self.get(name).get("used_at", ""))

    def rename(self, old: str, new: str) -> None:
        e = self.objects.pop((old or "").lower(), None)
        if e is not None:
            self.objects[(new or "").lower()] = e

    def recent_names(self, limit: int = 10) -> List[str]:
        items = [(t, n) for n, e in self.objects.items() if (t := _parse_time(e.get("used_at", ""))) is not None]
        return [n for _t, n in sorted(items, reverse=True)[:limit]]


# ─────────────────────────────────────────────────────────────
# 3. "Folosit in": ce rutine si ce pasi folosesc fiecare obiect
# ─────────────────────────────────────────────────────────────
@dataclass
class Usage:
    path: str
    routine: str
    step_id: str = ""
    step: str = ""


def _step_title(node: dict, target: str) -> str:
    label = str(node.get("label") or "").strip()
    if label:
        return label
    what = str(node.get("action") or node.get("kind") or "")
    return f"{what} [{target}]" if what else f"[{target}]"


def _walk(value, node: Optional[dict], found: List[Tuple[dict, str]]) -> None:
    if isinstance(value, dict):
        if "kind" in value and "id" in value:
            node = value
        t = value.get("target")
        if isinstance(t, str) and t.strip():
            found.append((node or value, t.strip()))
        for k, v in value.items():
            if isinstance(v, (dict, list)):
                _walk(v, node, found)
    elif isinstance(value, list):
        for v in value:
            _walk(v, node, found)


def usages_in_file(path: str) -> List[Tuple[str, Usage]]:
    """(nume obiect, folosire) pentru fiecare pas / conditie care foloseste un obiect."""
    try:
        with open(path, encoding="utf-8-sig") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return []
    if not isinstance(data, dict):
        return []
    name = str(data.get("name") or os.path.basename(path).split(".")[0])
    found: List[Tuple[dict, str]] = []
    _walk(data.get("steps") or [], None, found)
    out = []
    for node, target in found:
        out.append((target, Usage(path, name, str(node.get("id") or ""), _step_title(node, target))))
    return out


def build_usage_index(paths: Iterable[str]) -> Dict[str, List[Usage]]:
    index: Dict[str, List[Usage]] = {}
    seen = set()
    for p in paths:
        key = os.path.normcase(os.path.abspath(p))
        if key in seen:
            continue
        seen.add(key)
        for target, u in usages_in_file(p):
            index.setdefault(target.lower(), []).append(u)
    return index


def routine_files(folders: Iterable[str], max_depth: int = 4) -> List[str]:
    """Fisierele .rpr.json din folderele date (si subfoldere)."""
    out, seen = [], set()
    for root in folders:
        root = (root or "").strip().strip('"')
        if not root or not os.path.isdir(root):
            continue
        key = os.path.normcase(os.path.abspath(root))
        if key in seen:
            continue
        seen.add(key)
        base = root.rstrip("\\/").count(os.sep)
        for dirpath, dirnames, filenames in os.walk(root):
            if dirpath.count(os.sep) - base >= max_depth:
                dirnames[:] = []
            dirnames[:] = [d for d in dirnames if not d.startswith((".", "_"))]
            out.extend(os.path.join(dirpath, fn) for fn in filenames if fn.lower().endswith(".rpr.json"))
    return list(dict.fromkeys(out))


def routines_of(index: Dict[str, List[Usage]], name: str) -> List[str]:
    """Rutinele distincte (cai) care folosesc obiectul."""
    return sorted({u.path for u in index.get((name or "").lower(), [])})


# ─────────────────────────────────────────────────────────────
# 4. Potrivirea si ordinea rezultatelor
# ─────────────────────────────────────────────────────────────
def object_label(obj: UiObject) -> str:
    """Textul vizibil al obiectului: textul capturat sau eticheta din atribute."""
    if (obj.captured_text or "").strip():
        return obj.captured_text.strip()
    attrs = {str(k).lower(): str(v) for k, v in (obj.attributes or {}).items()}
    for k in _LABEL_ATTRS:
        if attrs.get(k, "").strip():
            return attrs[k].strip()
    return ""


def _fields(obj: UiObject) -> List[Tuple[float, str]]:
    attrs = " ".join(str(v) for k, v in (obj.attributes or {}).items() if str(k).lower() in _LABEL_ATTRS)
    return [
        (3.0, normalize(obj.name.replace("_", " "))),
        (3.2, normalize(f"{obj.captured_text} {attrs}")),   # textul vazut pe ecran: ce tii minte
        (1.5, normalize(" ".join([obj.object_type, obj.site, obj.page, obj.folder, obj.parent, obj.description,
                                  " ".join(obj.tags), str(obj.technology)]))),
        (1.0, normalize(" ".join(l.value for l in obj.locators))),
    ]


def _word_score(word: str, fields: List[Tuple[float, str]]) -> float:
    best = 0.0
    for weight, text in fields:
        if word in text:
            bonus = 0.5 if re.search(r"(^|[^0-9a-z])" + re.escape(word), text) else 0.0
            best = max(best, weight + bonus)
    if best or len(word) < 4:
        return best
    # o greseala de tastare: "salavre" ~ "salvare" (doar nume si text vizibil)
    for weight, text in fields[:2]:
        for w in set(re.split(r"[^0-9a-z]+", text)):
            if len(w) >= 3 and abs(len(w) - len(word)) <= 2 and difflib.SequenceMatcher(None, word, w).ratio() >= 0.8:
                best = max(best, weight * 0.6)
    return best


def object_status(obj: UiObject, state: LibraryState, usage: Optional[Dict[str, List[Usage]]]) -> List[str]:
    """Starile care se potrivesc obiectului (pot fi mai multe)."""
    out = []
    st = state.status(obj.name)
    if st in (STATUS_OK, STATUS_BAD):
        out.append(st)
    if usage is not None and not usage.get(obj.name.lower()):
        out.append(STATUS_UNUSED)
    t = state.used_at(obj.name)
    if t is not None and (_dt.datetime.now() - t).days < RECENT_DAYS:
        out.append(STATUS_RECENT)
    if state.is_favorite(obj.name):
        out.append(STATUS_FAVORITE)
    return out


def status_icon(obj: UiObject, state: LibraryState, usage: Optional[Dict[str, List[Usage]]]) -> str:
    s = object_status(obj, state, usage)
    icon = "⭐" if STATUS_FAVORITE in s else ""
    if STATUS_BAD in s:
        icon += "❌"
    elif STATUS_OK in s:
        icon += "✅"
    elif STATUS_UNUSED in s:
        icon += "⚪"
    return icon


def score(obj: UiObject, q: Query, state: Optional[LibraryState] = None,
          usage: Optional[Dict[str, List[Usage]]] = None, type_filter: str = "", status_filter: str = "") -> Optional[float]:
    """Cat de bine se potriveste obiectul; None = nu se potriveste."""
    state = state or LibraryState()
    otype = normalize(obj.object_type)
    if type_filter and normalize(type_filter) != otype:
        return None
    if q.types and not any(t in otype for t in q.types):
        return None
    if q.apps and not any(a in normalize(obj.site or str(obj.technology)) for a in q.apps):
        return None
    if q.pages and not any(p in normalize(obj.page) for p in q.pages):
        return None
    tags = [normalize(t) for t in obj.tags]
    if q.tags and not all(any(t in x for x in tags) for t in q.tags):
        return None
    wanted = [s for s in (status_filter, q.status) if s]
    if wanted:
        have = object_status(obj, state, usage)
        if not all(s in have for s in wanted):
            return None
    total = 1.0
    if q.words:
        fields = _fields(obj)
        total = 0.0
        for w in q.words:
            s = _word_score(w, fields)
            if not s:
                return None
            total += s
    if state.is_favorite(obj.name):
        total += 0.5
    t = state.used_at(obj.name)
    if t is not None and (_dt.datetime.now() - t).days < RECENT_DAYS:
        total += 0.3
    return total


def search(objects: Iterable[UiObject], text: str, state: Optional[LibraryState] = None,
           usage: Optional[Dict[str, List[Usage]]] = None, type_filter: str = "", status_filter: str = "",
           limit: int = MAX_RESULTS) -> Tuple[List[UiObject], int]:
    """Obiectele potrivite, cele mai bune primele (maxim `limit`), si cate s-au potrivit in total."""
    q = parse_query(text)
    hits = []
    for o in objects:
        s = score(o, q, state, usage, type_filter, status_filter)
        if s is not None:
            hits.append((-s, o.name.lower(), o))
    hits.sort(key=lambda x: (x[0], x[1]))
    return [o for _s, _n, o in hits[:limit]], len(hits)


# ─────────────────────────────────────────────────────────────
# 5. 🔎 Gaseste din ecran (v4.26): elementul marcat pe ecran -> obiectele salvate
# ─────────────────────────────────────────────────────────────
MATCH_LOCATOR = "locator"   # acelasi locator: e sigur acelasi element
MATCH_TEXT = "text"         # acelasi text vizibil pe acelasi ecran: probabil acelasi element


def _same_place(a: UiObject, b: UiObject) -> bool:
    if a.site and b.site and normalize(a.site) != normalize(b.site):
        return False
    if a.page and b.page and normalize(a.page) != normalize(b.page):
        return False
    return True


def find_matches(objects: Iterable[UiObject], captured: UiObject) -> List[Tuple[UiObject, str]]:
    """Obiectele salvate care sunt (probabil) elementul marcat pe ecran: intai cele cu acelasi locator,
    apoi cele cu acelasi text vizibil si acelasi tip pe acelasi ecran. Nu schimba nimic."""
    locs = {(str(l.kind), l.value.strip()) for l in captured.locators if l.value.strip()}
    label = normalize(object_label(captured))
    otype = normalize(captured.object_type)
    strong, weak = [], []
    for o in objects:
        if o.technology != captured.technology:
            continue
        if list(o.frame_path) != list(captured.frame_path) and o.frame_path and captured.frame_path:
            continue
        if not _same_place(o, captured):
            continue
        if any((str(l.kind), l.value.strip()) in locs for l in o.locators if l.value.strip()):
            strong.append((o, MATCH_LOCATOR))
        elif label and normalize(object_label(o)) == label and (not otype or not o.object_type
                                                                or normalize(o.object_type) == otype):
            weak.append((o, MATCH_TEXT))
    key = lambda x: x[0].name.lower()  # noqa: E731
    return sorted(strong, key=key) + sorted(weak, key=key)


# ─────────────────────────────────────────────────────────────
# 6. 🧩 Obiect cu parametru (v4.28): textul vizibil devine {Parametru}
# ─────────────────────────────────────────────────────────────
# locatorii care tintesc un singur element anume (id, css...): in obiectul general se dezactiveaza
_SPECIFIC_LOCATORS = {"TestId", "Id", "Css", "XPath", "AutomationId", "SapId", "UiaPath"}


def parametrize(obj: UiObject, param: str, label: str = "") -> Tuple[UiObject, int]:
    """Copie a obiectului in care textul `label` din locatori devine {param}. Locatorii specifici
    (id, css, xpath...) fara text se dezactiveaza. Intoarce (copia, cati locatori au primit parametrul)."""
    twin = UiObject.from_dict(obj.to_dict())
    label = (label or object_label(obj)).strip()
    token = "{" + param + "}"
    n = 0
    for l in twin.locators:
        if label and label.lower() in (l.value or "").lower():
            l.value = re.sub(re.escape(label), lambda _m: token, l.value, flags=re.IGNORECASE)
            n += 1
        elif str(l.kind) in _SPECIFIC_LOCATORS:
            l.enabled = False
    twin.params = [param]
    twin.captured_text = ""
    twin.screenshot = ""
    twin.description = (f"Obiect cu parametru {token} (din {obj.name})").strip()
    if "parametru" not in twin.tags:
        twin.tags = list(twin.tags) + ["parametru"]
    return twin, n
