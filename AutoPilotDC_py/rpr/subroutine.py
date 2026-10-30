# -*- coding: utf-8 -*-
# ============================================================
# AutoPilot DC v4.12 — Rutine ca pasi (calupuri)
#
#  - pasul "Ruleaza rutina" (RunRoutineNode) ruleaza o rutina salvata in locul lui;
#  - aici: gasirea fisierului, verificarea inainte de start (fisier lipsa, bucle, obiecte lipsa)
#    si copierea pasilor unei rutine in alta ("Insereaza ca pasi").
# ============================================================

from __future__ import annotations

import copy
import os
import uuid
from typing import Dict, Iterable, List, Optional, Tuple

from .model import ObjectRepository, Routine, RprNode, RunRoutineNode, flatten

MAX_DEPTH = 8   # cate calupuri se pot apela unul din altul


def _key(path: str) -> str:
    return os.path.normcase(os.path.abspath(path))


def resolve_path(path: str) -> str:
    """Calea reala a rutinei: cea scrisa, apoi aceeasi cale in OneDrive-ul de pe acest PC (alt laptop),
    apoi relativ la folderul rutinelor."""
    p = (path or "").strip().strip('"')
    if not p or os.path.isfile(p):
        return p
    try:
        from .scan import resolve_library_path
        q = resolve_library_path(p)
        if os.path.isfile(q):
            return q
    except Exception:  # noqa: BLE001
        pass
    folders: List[str] = []
    try:
        from .batch import shared_library
        folders.append(shared_library().folder)
    except Exception:  # noqa: BLE001
        pass
    try:
        from .storage import RprPaths
        folders.append(RprPaths.routines())
    except Exception:  # noqa: BLE001
        pass
    if not os.path.isabs(p):
        for f in folders:
            if f and os.path.isfile(os.path.join(f, p)):
                return os.path.join(f, p)
    return p


def load_routine(path: str, repo: Optional[ObjectRepository] = None) -> Routine:
    from .storage import RoutineStore
    return RoutineStore.load(path, repo)


def called_nodes(routine: Routine) -> List[RunRoutineNode]:
    return [n for n in routine.all_nodes() if isinstance(n, RunRoutineNode) and n.enabled]


def check(routine: Routine, repo: ObjectRepository, _stack: Optional[List[str]] = None) -> List[str]:
    """Probleme care ar opri rularea, gasite INAINTE de start: fisier lipsa, rutina care se apeleaza pe ea
    insasi, calupuri prea adanci, obiecte lipsa din biblioteca. Lista goala = totul in regula."""
    stack = list(_stack or [])
    problems: List[str] = []
    for node in called_nodes(routine):
        raw = node.path
        if "{" in raw:
            continue   # calea depinde de o variabila: se verifica la rulare
        path = resolve_path(raw)
        label = node.title
        if not path or not os.path.isfile(path):
            problems.append(f"{label}: fisierul rutinei lipseste ({raw or 'gol'}).")
            continue
        k = _key(path)
        if k in stack:
            problems.append(f"{label}: rutinele se apeleaza una pe alta in cerc.")
            continue
        if len(stack) >= MAX_DEPTH:
            problems.append(f"{label}: prea multe calupuri unul in altul (maxim {MAX_DEPTH}).")
            continue
        try:
            sub = load_routine(path, repo)
        except Exception as ex:  # noqa: BLE001
            problems.append(f"{label}: rutina nu poate fi citita ({ex}).")
            continue
        missing = sorted({n for n in sub.referenced_objects() if repo.find(n) is None}, key=str.lower)
        if missing:
            problems.append(f"{label}: obiecte lipsa din biblioteca: {', '.join(missing)}. "
                            f"Deschide biblioteca rutinei sau scaneaza din nou.")
        problems.extend(check(sub, repo, stack + [k]))
    return problems


def new_ids(node: RprNode) -> None:
    node.id = uuid.uuid4().hex[:10]
    for _, lst in node.branches():
        for ch in lst:
            new_ids(ch)


def steps_copy(sub: Routine) -> List[RprNode]:
    """Pasii unei rutine, copiati (id-uri noi), ca sa fie lipiti in alta rutina."""
    out = copy.deepcopy(sub.steps)
    for n in out:
        new_ids(n)
    return out


def merge_variables(target: Routine, sub: Routine) -> int:
    """Variabilele rutinei copiate care lipsesc din rutina curenta (valorile implicite). Intoarce cate s-au adaugat."""
    n = 0
    for k, v in sub.variables.items():
        if k not in target.variables:
            target.variables[k] = v
            n += 1
    return n


def count_steps(routine: Routine) -> int:
    return sum(1 for _ in flatten(routine.steps))
