# -*- coding: utf-8 -*-
# ============================================================
# AutoPilot DC v4.30 — rutina existenta -> text "Pasi AutoPilot" (inversul importului)
#
# Folosit de 🔧 Repara rutina (🤖 Asistent AI): rutina se scrie ca text, AI-ul o corecteaza, iar textul
# corectat trece prin StepImporter ca la 📥 Import AI.
#   - Pasii care nu au comanda in text (reguli, grupuri, pasi pe coordonate, bucle "cat timp"...) se scriu
#     `PASTREAZA #n`: la import revin exact cum erau (cu tot ce au in interior).
#   - Un rand pe care AI-ul nu l-a schimbat isi primeste inapoi setarile ascunse (timeout, pauze, la eroare,
#     eticheta, comentariu...): restore_settings().
# Formatul .rpr.json nu se schimba.
# ============================================================

from __future__ import annotations

import re
from typing import Dict, List, Optional, Tuple

from .model import (ActionNode, CompareOperator, Condition, ConditionKind, ForEachRowNode, IfNode, LogNode,
                    LoopMode, LoopNode, QuestionNode, RprAction, RprNode, RunRoutineNode, SetVariableNode,
                    StopNode, TryNode, VariableOperation, WaitMode, WaitNode, WriteExcelNode, _new_id,
                    node_from_dict)

# cuvintele cheie (ro, en) — aceleasi ca in importer.COMMANDS
_KW = {
    "routine": ("RUTINA:", "ROUTINE:"), "description": ("DESCRIERE:", "DESCRIPTION:"),
    "variable": ("VARIABILA:", "VARIABLE:"), "open_browser": ("DESCHIDE BROWSER", "OPEN BROWSER"),
    "navigate": ("MERGI LA", "GO TO"), "close_browser": ("INCHIDE BROWSER", "CLOSE BROWSER"),
    "click": ("CLICK", "CLICK"), "dblclick": ("DUBLU CLICK", "DOUBLE CLICK"),
    "rclick": ("CLICK DREAPTA", "RIGHT CLICK"), "type": ("SCRIE", "TYPE"), "append": ("ADAUGA TEXT", "APPEND"),
    "clear": ("GOLESTE", "CLEAR"), "press": ("APASA", "PRESS"), "in": ("IN", "IN"), "select": ("ALEGE", "SELECT"),
    "check": ("BIFEAZA", "CHECK"), "uncheck": ("DEBIFEAZA", "UNCHECK"), "read": ("CITESTE", "READ"),
    "wait": ("ASTEAPTA", "WAIT"), "max": ("MAX", "MAX"), "if": ("DACA", "IF"), "if_appears": ("DACA APARE", "IF APPEARS"),
    "else": ("ALTFEL", "ELSE"), "end": ("SFARSIT", "END"), "repeat": ("REPETA", "REPEAT"),
    "for_each_row": ("PENTRU FIECARE RAND", "FOR EACH ROW"), "sheet": ("FOAIE", "SHEET"),
    "try": ("INCEARCA", "TRY"), "catch": ("LA EROARE", "ON ERROR"), "set": ("SETEAZA", "SET"),
    "write_excel": ("SCRIE IN EXCEL", "WRITE EXCEL"), "ask_value": ("INTREABA VALOARE", "ASK VALUE"),
    "ask": ("INTREABA", "ASK"), "buttons": ("BUTOANE", "BUTTONS"), "log": ("LOG", "LOG"), "stop": ("OPRESTE", "STOP"),
    "sap_connect": ("SAP CONECTEAZA", "SAP CONNECT"), "sap_tcode": ("SAP TRANZACTIE", "SAP TRANSACTION"),
    "sap_key": ("SAP TASTA", "SAP KEY"), "sap_status": ("SAP CITESTE STARE", "SAP READ STATUS"),
    "sap_scroll": ("SAP DERULEAZA", "SAP SCROLL"), "start_app": ("PORNESTE APLICATIE", "START APP"),
    "attach": ("ATASEAZA FEREASTRA", "ATTACH WINDOW"), "run_routine": ("RULEAZA RUTINA", "RUN ROUTINE"),
    "keep": ("PASTREAZA", "KEEP"),
    # conditii
    "and": ("SI", "AND"), "or": ("SAU", "OR"), "exists": ("exista", "exists"), "not_exists": ("nu exista", "not exists"),
    "visible": ("vizibil", "visible"), "enabled": ("activ", "enabled"), "empty": ("e gol", "is empty"),
    "contains": ("contine", "contains"), "not_contains": ("nu contine", "not contains"),
    "starts": ("incepe cu", "starts with"), "ends": ("se termina cu", "ends with"),
}
_OPS = {CompareOperator.Equals: "=", CompareOperator.NotEquals: "!=", CompareOperator.GreaterThan: ">",
        CompareOperator.GreaterOrEqual: ">=", CompareOperator.LessThan: "<", CompareOperator.LessOrEqual: "<=",
        CompareOperator.Contains: "contains", CompareOperator.NotContains: "not_contains",
        CompareOperator.StartsWith: "starts", CompareOperator.EndsWith: "ends"}
_ACTION_SIMPLE = {RprAction.Click: "click", RprAction.DoubleClick: "dblclick", RprAction.RightClick: "rclick",
                  RprAction.Clear: "clear", RprAction.Check: "check", RprAction.Uncheck: "uncheck"}
_ACTION_VALUE = {RprAction.TypeText: "type", RprAction.AppendText: "append", RprAction.SelectOption: "select"}
_APP_VALUE = {RprAction.OpenBrowser: "open_browser", RprAction.Navigate: "navigate",
              RprAction.SapTransaction: "sap_tcode", RprAction.SapSendKey: "sap_key",
              RprAction.LaunchApp: "start_app", RprAction.AttachWindow: "attach"}


MASK = "***"
_SECRET = re.compile(r"parol|pass|pwd|token|secret|cheie|key|pin\b", re.I)


def is_secret(name: str) -> bool:
    """Variabilele cu parole / chei: valoarea nu pleaca la AI (se scrie *** si revine la import)."""
    return bool(_SECRET.search(name or ""))


class _NoText(Exception):
    """Pasul nu are comanda in text: se scrie PASTREAZA #n."""


def q(s: str) -> str:
    """Valoarea intre ghilimele (cu „…“ daca are deja ghilimele drepte)."""
    s = str(s or "")
    if "\n" in s:
        raise _NoText()
    return f"„{s}“" if '"' in s else f'"{s}"'


class StepsWriter:
    def __init__(self, lang: str = "ro"):
        self.en = 1 if lang != "ro" else 0
        self.keep: Dict[str, RprNode] = {}       # "n" -> pasul original (PASTREAZA #n)
        self.lines: Dict[str, List[RprNode]] = {}  # randul scris -> pasii originali cu acest rand (in ordine)

    def k(self, key: str) -> str:
        return _KW[key][self.en]

    # ── rutina ──
    def write(self, routine) -> str:
        out = [f"{self.k('routine')} {routine.name}"]
        if (routine.description or "").strip() and "\n" not in routine.description:
            out.append(f"{self.k('description')} {routine.description.strip()}")
        for name, val in (routine.variables or {}).items():
            out.append(f"{self.k('variable')} {name} = {MASK if is_secret(name) and val else val}")
        self._list(routine.steps, 0, out)
        return "\n".join(out) + "\n"

    def _list(self, nodes: List[RprNode], depth: int, out: List[str]) -> None:
        for n in nodes:
            self._node(n, depth, out)

    def _node(self, n: RprNode, depth: int, out: List[str]) -> None:
        pad = "  " * depth
        for c in (n.comment or "").splitlines():
            if c.strip():
                out.append(f"{pad}# {c.strip()}")
        try:
            if not n.enabled:
                raise _NoText()
            if isinstance(n, IfNode):
                head = self._if_head(n)
                then, els = [], []
                self._list(n.then, depth + 1, then)
                self._list(n.else_, depth + 1, els)
                self._remember(head, n)
                out.append(pad + head)
                out += then
                if n.else_:
                    out.append(pad + self.k("else"))
                    out += els
                out.append(pad + self.k("end"))
                return
            if isinstance(n, LoopNode):
                if n.mode != LoopMode.Times:
                    raise _NoText()
                self._block(f"{self.k('repeat')} {n.count}", n, [n.body], depth, out)
                return
            if isinstance(n, ForEachRowNode):
                head = f"{self.k('for_each_row')} {q(n.file_path)}" + (
                    f" {self.k('sheet')} {q(n.sheet)}" if n.sheet.strip() else "")
                self._block(head, n, [n.body], depth, out)
                return
            if isinstance(n, TryNode):
                self._block(self.k("try"), n, [n.body, n.catch], depth, out, middle=self.k("catch"))
                return
            if n.is_container:
                raise _NoText()
            line = self._leaf(n)
            self._remember(line, n)
            out.append(pad + line)
        except _NoText:
            idx = str(len(self.keep) + 1)
            self.keep[idx] = n
            inner = sum(1 for _ in _walk(n)) - 1
            extra = f" ({inner} …)" if inner else ""
            out.append(f"{pad}{self.k('keep')} #{idx}   # {n.title[:80]}{extra}")

    def _block(self, head: str, n: RprNode, lists, depth: int, out: List[str], middle: str = "") -> None:
        body: List[List[str]] = []
        for lst in lists:
            part: List[str] = []
            self._list(lst, depth + 1, part)
            body.append(part)
        self._remember(head, n)
        pad = "  " * depth
        out.append(pad + head)
        out += body[0]
        if middle and len(body) > 1:
            out.append(pad + middle)
            out += body[1]
        out.append(pad + self.k("end"))

    def _remember(self, line: str, n: RprNode) -> None:
        self.lines.setdefault(line.strip(), []).append(n)

    # ── un pas ──
    def _leaf(self, n: RprNode) -> str:
        k = self.k
        if isinstance(n, ActionNode):
            a, t = n.action, f"[{n.target}]" if n.target else ""
            if a in _ACTION_SIMPLE and t:
                return f"{k(_ACTION_SIMPLE[a])} {t}"
            if a in _ACTION_VALUE and t:
                return f"{k(_ACTION_VALUE[a])} {t} = {q(n.value)}"
            if a in _APP_VALUE:
                return f"{k(_APP_VALUE[a])} {q(n.value)}" if n.value or a != RprAction.SapSendKey else k("sap_key")
            if a == RprAction.CloseBrowser:
                return k("close_browser")
            if a == RprAction.SapConnect:
                return k("sap_connect") + (f" {q(n.value)}" if n.value else "")
            if a == RprAction.PressKey and n.value:
                return f"{k('press')} {n.value}" + (f" {k('in')} {t}" if t else "")
            if a == RprAction.ReadText and t:
                return f"{k('read')} {t} -> {{{n.output_variable or 'Text'}}}"
            if a == RprAction.SapReadStatusBar:
                return f"{k('sap_status')} -> {{{n.output_variable or 'StareSAP'}}}"
            if a == RprAction.SapScrollTable and t:
                return f"{k('sap_scroll')} {t} = {n.value or '+1'} -> {{{n.output_variable or 'Pozitie'}}}"
            raise _NoText()
        if isinstance(n, WaitNode):
            if n.mode == WaitMode.Seconds:
                return f"{k('wait')} {n.seconds:g}"
            return f"{k('wait')} {self._cond(n.condition, element_only=True)} {k('max')} {n.timeout_ms / 1000:g}"
        if isinstance(n, SetVariableNode):
            if n.operation != VariableOperation.Set:
                raise _NoText()
            return f"{k('set')} {{{n.name}}} = {q(n.value)}"
        if isinstance(n, WriteExcelNode):
            return f"{k('write_excel')} {q(n.column)} = {q(n.value)}"
        if isinstance(n, QuestionNode):
            if n.ask_value:
                return f"{k('ask_value')} {q(n.text)} -> {{{n.output_variable or 'Raspuns'}}}"
            return f"{k('ask')} {q(n.text)} {k('buttons')} {', '.join(b.strip() for b in n.buttons.split(','))}"
        if isinstance(n, RunRoutineNode):
            return f"{k('run_routine')} {q(n.path)}"
        if isinstance(n, LogNode) and str(n.level) == "Info":
            return f"{k('log')} {q(n.message)}"
        if isinstance(n, StopNode) and not n.as_error:
            return k("stop") + (f" {q(n.message)}" if n.message else "")
        raise _NoText()

    def _if_head(self, n: IfNode) -> str:
        c = n.condition
        if n.optional:
            if c.kind != ConditionKind.ElementVisible or c.negate:
                raise _NoText()
            return f"{self.k('if_appears')} [{c.target}]"
        return f"{self.k('if')} {self._cond(c)}"

    def _cond(self, c: Condition, element_only: bool = False, nested: bool = False) -> str:
        if c.negate:
            raise _NoText()
        k = self.k
        if c.kind in (ConditionKind.AllOf, ConditionKind.AnyOf):
            if nested or element_only or not c.children:
                raise _NoText()   # parantezele nu exista in text
            sep = f" {k('and') if c.kind == ConditionKind.AllOf else k('or')} "
            return sep.join(self._cond(x, nested=True) for x in c.children)
        el = {ConditionKind.ElementExists: "exists", ConditionKind.ElementNotExists: "not_exists",
              ConditionKind.ElementVisible: "visible", ConditionKind.ElementEnabled: "enabled"}
        if c.kind in el:
            return f"{k(el[c.kind])} [{c.target}]"
        if element_only or c.kind != ConditionKind.Compare or not c.left.strip():
            raise _NoText()
        if c.operator == CompareOperator.IsEmpty:
            return f"{c.left} {k('empty')}"
        op = _OPS.get(c.operator)
        if op is None:
            raise _NoText()
        return f"{c.left} {k(op) if op in _KW else op} {q(c.right)}"


def _walk(n: RprNode):
    yield n
    for _, lst in n.branches():
        for ch in lst:
            yield from _walk(ch)


def routine_to_steps(routine, lang: str = "ro") -> Tuple[str, StepsWriter]:
    """(textul, scriitorul): scriitorul tine pasii PASTREAZA #n si randurile scrise, pentru import."""
    w = StepsWriter(lang)
    return w.write(routine), w


def fresh_copy(node: RprNode) -> RprNode:
    """Copie a pasului (cu tot ce are inauntru), cu id-uri noi."""
    c = node_from_dict(node.to_dict())
    for x in _walk(c):
        x.id = _new_id()
    return c


def restore_settings(routine, writer: StepsWriter, lang: str = "ro") -> int:
    """Pasii al caror rand nu s-a schimbat isi primesc inapoi setarile din rutina originala (in ordine).
    Intoarce cati pasi au fost refacuti."""
    pool = {line: list(nodes) for line, nodes in writer.lines.items()}
    probe = StepsWriter(lang)
    done = 0

    def line_of(n: RprNode) -> Optional[str]:
        """Randul pasului; None = pas PASTREAZA (sau fara text): nu se atinge, nici ce are inauntru."""
        if not n.enabled:
            return None
        try:
            if isinstance(n, IfNode):
                return probe._if_head(n)
            if isinstance(n, LoopNode):
                return f"{probe.k('repeat')} {n.count}" if n.mode == LoopMode.Times else None
            if isinstance(n, ForEachRowNode):
                return f"{probe.k('for_each_row')} {q(n.file_path)}" + (
                    f" {probe.k('sheet')} {q(n.sheet)}" if n.sheet.strip() else "")
            if isinstance(n, TryNode):
                return probe.k("try")
            if n.is_container:
                return None
            return probe._leaf(n)
        except _NoText:
            return None

    def walk(nodes: List[RprNode]):
        for n in nodes:
            line = line_of(n)
            if line is None:
                continue
            yield n, line
            for _, lst in n.branches():
                yield from walk(lst)

    for n, line in list(walk(routine.steps)):
        cands = pool.get(line.strip())
        if not cands:
            continue
        orig = cands.pop(0)
        if type(orig) is not type(n):
            continue
        keep_children = {f: getattr(n, f) for f in n._child_lists}
        d = orig.to_dict()
        for f in n._child_lists:
            d.pop("else" if f == "else_" else f, None)
        fresh = type(n).from_dict(d)
        for f in fresh.__dataclass_fields__:
            if f in n._child_lists or f == "id":
                continue
            if f == "comment" and n.comment and n.comment != orig.comment:
                continue   # comentariul / TODO-ul nou scris de AI ramane
            setattr(n, f, getattr(fresh, f))
        for f, v in keep_children.items():
            setattr(n, f, v)
        done += 1
    return done
