# -*- coding: utf-8 -*-
# ============================================================
# AutoPilot DC v4.1 — RPR (Python)
# conditions.py — Evalueaza conditiile din Daca / Repeta / Asteapta
# ============================================================

from __future__ import annotations

import re
import threading
import time
from decimal import Decimal, InvalidOperation
from typing import Optional, Tuple

from .drivers.base import DriverProvider, RprStepException
from .model import CompareOperator, Condition, ConditionKind, ObjectRepository, UiObject, with_variables
from .variables import VariableStore

_NUM_RE = re.compile(r"^[+-]?[\d.,]+$")


def try_number(s: str) -> Tuple[bool, Decimal]:
    """Accepta 1234.5, 1234,5, 1.234,5 si 1,234.5 (separatorul zecimal e cel din dreapta)."""
    if s is None or not str(s).strip():
        return False, Decimal(0)
    s = str(s).strip().replace(" ", "").replace(" ", "")
    if not _NUM_RE.match(s):
        return False, Decimal(0)
    last_dot, last_comma = s.rfind("."), s.rfind(",")
    if last_dot >= 0 and last_comma >= 0:
        s = s.replace(".", "").replace(",", ".") if last_comma > last_dot else s.replace(",", "")
    elif last_comma >= 0:
        # doar virgula: zecimala daca e una singura si nu are exact 3 cifre dupa
        s = s.replace(",", ".") if s.count(",") == 1 and len(s) - last_comma - 1 != 3 else s.replace(",", "")
    try:
        return True, Decimal(s)
    except InvalidOperation:
        return False, Decimal(0)


def compare(left: str, op: CompareOperator, right: str, ignore_case: bool) -> bool:
    op = CompareOperator.parse(op)
    l, r = (left or "").strip(), (right or "").strip()
    lc, rc = (l.lower(), r.lower()) if ignore_case else (l, r)

    def num_equals() -> Optional[bool]:
        ok1, a = try_number(l)
        ok2, b = try_number(r)
        return a == b if ok1 and ok2 else None

    if op == CompareOperator.Equals:
        ne = num_equals()
        return ne if ne is not None else lc == rc
    if op == CompareOperator.NotEquals:
        ne = num_equals()
        return not (ne if ne is not None else lc == rc)
    if op == CompareOperator.Contains:
        return rc in lc
    if op == CompareOperator.NotContains:
        return rc not in lc
    if op == CompareOperator.StartsWith:
        return lc.startswith(rc)
    if op == CompareOperator.EndsWith:
        return lc.endswith(rc)
    if op == CompareOperator.IsEmpty:
        return len(l) == 0
    if op == CompareOperator.IsNotEmpty:
        return len(l) > 0
    if op == CompareOperator.MatchesRegex:
        try:
            return re.search(r, l, re.IGNORECASE if ignore_case else 0) is not None
        except re.error as ex:
            raise RprStepException(f"Expresie regulata invalida: \"{r}\" ({ex})")

    # Operatori de ordine: numeric daca se poate, altfel alfabetic
    ok1, a = try_number(l)
    ok2, b = try_number(r)
    if ok1 and ok2:
        order = (a > b) - (a < b)
    else:
        order = (lc > rc) - (lc < rc)
    return {
        CompareOperator.GreaterThan: order > 0,
        CompareOperator.GreaterOrEqual: order >= 0,
        CompareOperator.LessThan: order < 0,
        CompareOperator.LessOrEqual: order <= 0,
    }.get(op, False)


class ConditionEvaluator:
    def __init__(self, repo: ObjectRepository, drivers: DriverProvider, variables: VariableStore,
                 stop: threading.Event):
        self._repo, self._drivers, self._vars, self._stop = repo, drivers, variables, stop

    def evaluate(self, c: Condition) -> bool:
        result = self._core(c)
        return not result if c.negate else result

    def _core(self, c: Condition) -> bool:
        k = c.kind
        # 1. Grupuri SI / SAU (scurtcircuitat)
        if k == ConditionKind.AllOf:
            return all(self.evaluate(ch) for ch in c.children)
        if k == ConditionKind.AnyOf:
            return any(self.evaluate(ch) for ch in c.children)

        # 2. Comparatie de valori
        if k == ConditionKind.Compare:
            return compare(self._vars.resolve(c.left), c.operator, self._vars.resolve(c.right), c.ignore_case)

        obj = self._require(c.target)
        driver = self._drivers.get(obj.technology)

        # 3. NU exista: asteptam pana dispare (pana la timeout_ms)
        if k == ConditionKind.ElementNotExists:
            deadline = time.monotonic() + max(0, c.timeout_ms) / 1000.0
            while True:
                st = driver.get_state(obj, 0, self._stop)
                if not st.exists or not st.visible:
                    return True
                if time.monotonic() >= deadline or self._stop.is_set():
                    return False
                self._stop.wait(0.25)

        # 4. Conditii pe element
        st = driver.get_state(obj, max(0, c.timeout_ms), self._stop)
        if k == ConditionKind.ElementExists:
            return st.exists
        if k == ConditionKind.ElementVisible:
            return st.exists and st.visible
        if k == ConditionKind.ElementEnabled:
            return st.exists and st.enabled
        if k == ConditionKind.ElementText:
            return st.exists and compare(st.text or st.value, c.operator, self._vars.resolve(c.right), c.ignore_case)
        return False

    def _require(self, name: str) -> UiObject:
        obj = self._repo.find(name)
        if obj is None:
            raise RprStepException(f"Conditia foloseste obiectul [{name}], care nu exista in Object Repository.")
        return with_variables(self._repo.link_parents(obj), self._vars.resolve)
