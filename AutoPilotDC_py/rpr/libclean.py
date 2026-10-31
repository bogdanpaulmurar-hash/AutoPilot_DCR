# -*- coding: utf-8 -*-
# ============================================================
# AutoPilot DC — 🧹 Curatenia bibliotecii (v4.27): mai putine obiecte
#
#   - Dubluri: obiecte salvate de mai multe ori pentru acelasi element
#     (acelasi locator, sau acelasi text vizibil si tip pe acelasi ecran).
#     La unire ramane un obiect; primeste si locatorii celorlalte (de rezerva),
#     iar pasii din rutine (si containerele) trec pe numele lui.
#   - Curatenie: obiecte nefolosite in rutine sau stricate la ultimul test.
# Inainte de orice schimbare se face o copie a bibliotecii si a rutinelor
# atinse in "_backup_biblioteca/<data>" langa biblioteca (folderul cu "_"
# nu e citit ca folder de rutine).
# ============================================================

from __future__ import annotations

import datetime as _dt
import json
import os
import shutil
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Tuple

from .libsearch import (LibraryState, STATUS_BAD, Usage, normalize, object_label, routines_of)
from .model import Condition, ObjectRepository, RprNode, UiObject, flatten

BACKUP_DIR = "_backup_biblioteca"
SAME_LOCATOR = "locator"
SAME_TEXT = "text"
# locatori dupa text: acelasi text poate fi pe elemente diferite (eticheta si campul ei)
TEXT_LOCATORS = {"Text", "Label", "Name", "Placeholder", "UiaName", "SapName", "Role"}


# ─────────────────────────────────────────────────────────────
# 1. Dublurile
# ─────────────────────────────────────────────────────────────
def _place(o: UiObject) -> Tuple[str, str, str, str]:
    return (str(o.technology), normalize(o.site), normalize(o.page), "/".join(o.frame_path))


def _locator_keys(o: UiObject) -> List[Tuple[str, str]]:
    return [(str(l.kind), l.value.strip()) for l in o.locators if l.value.strip()]


@dataclass
class DuplicateGroup:
    objects: List[UiObject]
    reason: str                     # SAME_LOCATOR (sigur) sau SAME_TEXT (probabil)

    @property
    def sure(self) -> bool:
        return self.reason == SAME_LOCATOR


def find_duplicates(objects: Iterable[UiObject], usage: Optional[Dict[str, List[Usage]]] = None) -> List[DuplicateGroup]:
    """Grupurile de obiecte care par acelasi element. In fiecare grup, primul e cel propus de pastrat:
    cel folosit in mai multe rutine, apoi cel cu mai multi locatori, apoi numele cel mai scurt."""
    objs = list(objects)
    parent = list(range(len(objs)))
    reason: Dict[int, str] = {}

    def root(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def join(i, j, why):
        ri, rj = root(i), root(j)
        if ri == rj:
            return          # deja in acelasi grup: textul nu slabeste o potrivire pe locator
        parent[rj] = ri
        r = SAME_TEXT if SAME_TEXT in (why, reason.get(ri), reason.get(rj)) else SAME_LOCATOR
        reason[ri] = r

    by_loc: Dict[tuple, int] = {}
    by_text: Dict[tuple, int] = {}
    for i, o in enumerate(objs):
        place = _place(o)
        otype = normalize(o.object_type)
        for k in _locator_keys(o):
            if k[0] in TEXT_LOCATORS:    # textul poate fi pe mai multe elemente: doar cu acelasi tip, "probabil"
                key = place + (o.is_container, otype, normalize(o.parent), "text") + k
                if key in by_text:
                    join(by_text[key], i, SAME_TEXT)
                else:
                    by_text[key] = i
                continue
            key = place + (o.is_container, otype) + k
            if key in by_loc:
                join(by_loc[key], i, SAME_LOCATOR)
            else:
                by_loc[key] = i
        label = normalize(object_label(o))
        if label and o.page:
            key = place + (o.is_container, normalize(o.object_type), normalize(o.parent), label)
            if key in by_text:
                join(by_text[key], i, SAME_TEXT)
            else:
                by_text[key] = i

    groups: Dict[int, List[UiObject]] = {}
    for i, o in enumerate(objs):
        groups.setdefault(root(i), []).append(o)

    def rank(o: UiObject):
        used = len(routines_of(usage, o.name)) if usage else 0
        return (-used, -len(_locator_keys(o)), len(o.name), o.name.lower())

    out = []
    for r, members in groups.items():
        if len(members) > 1:
            out.append(DuplicateGroup(sorted(members, key=rank), reason.get(r, SAME_LOCATOR)))
    out.sort(key=lambda g: (not g.sure, g.objects[0].site.lower(), g.objects[0].page.lower(), g.objects[0].name.lower()))
    return out


# ─────────────────────────────────────────────────────────────
# 2. Copia de rezerva
# ─────────────────────────────────────────────────────────────
def backup(library_path: str, routine_paths: Iterable[str] = ()) -> str:
    """Copiaza biblioteca, starea ei si rutinele date in _backup_biblioteca/<data>/. Intoarce folderul."""
    base = os.path.dirname(os.path.abspath(library_path))
    first = os.path.join(base, BACKUP_DIR, _dt.datetime.now().strftime("%Y-%m-%d_%H%M%S"))
    folder, n = first, 1
    while os.path.exists(folder):
        n += 1
        folder = f"{first}_{n}"
    os.makedirs(os.path.join(folder, "rutine"))
    from .libsearch import state_path
    for p in (library_path, state_path(library_path)):
        if os.path.isfile(p):
            shutil.copy2(p, folder)
    used = set()
    for p in routine_paths:
        if not os.path.isfile(p):
            continue
        name = os.path.basename(p)
        while name.lower() in used:
            name = "_" + name
        used.add(name.lower())
        shutil.copy2(p, os.path.join(folder, "rutine", name))
    with open(os.path.join(folder, "de_unde.json"), "w", encoding="utf-8") as f:
        json.dump({"biblioteca": os.path.abspath(library_path),
                   "rutine": [os.path.abspath(p) for p in routine_paths]}, f, ensure_ascii=False, indent=1)
    return folder


# ─────────────────────────────────────────────────────────────
# 3. Unirea
# ─────────────────────────────────────────────────────────────
def _rename_in_json(value, names: Dict[str, str]) -> int:
    """Schimba "target" in toate nodurile / conditiile unei rutine citite ca JSON. Intoarce cate a schimbat."""
    n = 0
    if isinstance(value, dict):
        t = value.get("target")
        if isinstance(t, str) and t.strip().lower() in names:
            value["target"] = names[t.strip().lower()]
            n += 1
        for v in value.values():
            if isinstance(v, (dict, list)):
                n += _rename_in_json(v, names)
    elif isinstance(value, list):
        for v in value:
            n += _rename_in_json(v, names)
    return n


def _rename_condition(c: Condition, names: Dict[str, str]) -> int:
    n = 0
    if c.target.strip().lower() in names:
        c.target = names[c.target.strip().lower()]
        n += 1
    for ch in c.children:
        n += _rename_condition(ch, names)
    return n


def rename_in_steps(steps: List[RprNode], names: Dict[str, str]) -> int:
    """Acelasi lucru pe o rutina deschisa (obiectele din memorie)."""
    n = 0
    for node in flatten(steps):
        t = getattr(node, "target", None)
        if isinstance(t, str) and t.strip().lower() in names:
            node.target = names[t.strip().lower()]
            n += 1
        c = getattr(node, "condition", None)
        if isinstance(c, Condition):
            n += _rename_condition(c, names)
    return n


def files_using(usage: Optional[Dict[str, List[Usage]]], names: Iterable[str]) -> List[str]:
    out = set()
    for nm in names:
        out.update(routines_of(usage or {}, nm))
    return sorted(out)


@dataclass
class MergeResult:
    kept: str
    removed: List[str] = field(default_factory=list)
    steps_changed: int = 0
    routines_changed: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    backup_folder: str = ""


def merge(repo: ObjectRepository, keep: UiObject, drops: List[UiObject], routine_paths: Iterable[str] = (),
          state: Optional[LibraryState] = None) -> MergeResult:
    """Unul ramane, celelalte dispar. Pastratul primeste locatorii lipsa (la final, ca rezerva) si etichetele;
    copiii si pasii rutinelor trec pe el. Nu salveaza biblioteca (o salveaza cine cheama)."""
    drops = [d for d in drops if d is not keep]
    names = {d.name.lower(): keep.name for d in drops}
    res = MergeResult(keep.name, [d.name for d in drops])
    have = set(_locator_keys(keep))
    for d in drops:
        for l in d.locators:
            k = (str(l.kind), l.value.strip())
            if l.value.strip() and k not in have:
                have.add(k)
                keep.locators.append(type(l).from_dict(l.to_dict()))
        for t in d.tags:
            if t not in keep.tags:
                keep.tags.append(t)
        if not keep.captured_text and d.captured_text:
            keep.captured_text = d.captured_text
        if not keep.screenshot and d.screenshot:
            keep.screenshot = d.screenshot
    for o in repo.objects:
        if o.parent and o.parent.lower() in names and o not in drops:
            o.parent = keep.name
    for d in drops:
        if d in repo.objects:
            repo.objects.remove(d)
    if keep.parent and keep.parent.lower() == keep.name.lower():
        keep.parent = ""
    for p in routine_paths:
        try:
            with open(p, encoding="utf-8-sig") as f:
                data = json.load(f)
            n = _rename_in_json(data.get("steps") or [], names)
            if n:
                from .storage import atomic_write
                atomic_write(p, json.dumps(data, ensure_ascii=False, indent=1))
                res.steps_changed += n
                res.routines_changed.append(p)
        except (OSError, ValueError, AttributeError) as ex:
            res.errors.append(f"{os.path.basename(p)}: {ex}")
    if state is not None:
        fav = any(state.is_favorite(d.name) for d in drops)
        for d in drops:
            state.objects.pop(d.name.lower(), None)
        if fav and not state.is_favorite(keep.name):
            state.toggle_favorite(keep.name)
    return res


# ─────────────────────────────────────────────────────────────
# 4. Curatenia: nefolosite si stricate
# ─────────────────────────────────────────────────────────────
def cleanup_candidates(repo: ObjectRepository, usage: Dict[str, List[Usage]], state: Optional[LibraryState] = None,
                       unused: bool = True, broken: bool = True) -> List[Tuple[UiObject, str]]:
    """(obiect, motiv) pentru obiectele care pot fi sterse. Containerele cu obiecte inauntru nu se propun."""
    state = state or LibraryState()
    out = []
    for o in repo.objects:
        if o.is_container and repo.children_of(o.name):
            continue
        why = []
        if unused and not usage.get(o.name.lower()):
            why.append("nefolosit")
        if broken and state.status(o.name) == STATUS_BAD:
            why.append("stricat")
        if why and not state.is_favorite(o.name):
            out.append((o, " + ".join(why)))
    out.sort(key=lambda x: (x[0].site.lower(), x[0].page.lower(), x[0].name.lower()))
    return out


def delete_objects(repo: ObjectRepository, objs: Iterable[UiObject], state: Optional[LibraryState] = None) -> int:
    n = 0
    for o in list(objs):
        if repo.remove(o):
            n += 1
            if state is not None:
                state.objects.pop(o.name.lower(), None)
    return n
