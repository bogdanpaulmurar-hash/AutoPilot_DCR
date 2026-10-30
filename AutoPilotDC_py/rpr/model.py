# -*- coding: utf-8 -*-
# ============================================================
# AutoPilot DC v4.1 — RPR (Python)
# model.py — Rutina ca arbore de pasi, conditii, Object Repository
#
# Formatul JSON e IDENTIC cu versiunea C# (fisierele .rpr.json si
# obiecte.json se deschid in ambele):
#   - chei snake_case, enum-uri ca text ("Click", "ElementExists")
#   - tipul pasului in campul "kind" (primul camp al obiectului)
#   - campurile necunoscute sunt pastrate la salvare (compatibilitate inainte)
# ============================================================

from __future__ import annotations

import datetime as _dt
import os
import re
import uuid
from dataclasses import dataclass, field, fields
from enum import Enum
from typing import Any, Dict, Iterable, Iterator, List, Optional, Tuple, Type


def _t(text: str) -> str:
    """Textul in limba aplicatiei (v4.16). Titlurile pasilor se compun din bucati traduse, ca sa nu ramana
    cuvinte romanesti in interfata in engleza. Fara i18n incarcat (teste, C#) textul ramane romanesc."""
    import sys
    m = sys.modules.get("i18n")
    if m is None or not hasattr(m, "tr"):
        return text
    if "{" in text and hasattr(m, "tr_template"):   # sablon completat apoi cu .format()
        return m.tr_template(text)
    return m.tr(text)


# ─────────────────────────────────────────────────────────────
# Enum-uri (valoarea = numele din C#, scris asa in JSON)
# ─────────────────────────────────────────────────────────────
class _StrEnum(str, Enum):
    def __str__(self) -> str:
        return self.value

    @classmethod
    def parse(cls, v: Any):
        if isinstance(v, cls):
            return v
        if isinstance(v, int):  # numeric (nu ar trebui, dar acceptam)
            return list(cls)[v]
        s = str(v)
        for m in cls:
            if m.value.lower() == s.lower():
                return m
        raise ValueError(f"Valoare necunoscuta pentru {cls.__name__}: {v}")


class ErrorPolicy(_StrEnum):
    Inherit = "Inherit"
    Stop = "Stop"
    Ask = "Ask"
    Continue = "Continue"
    SkipRow = "SkipRow"


class RuleAfter(_StrEnum):
    """Ce se intampla dupa ce o regula si-a rulat pasii."""
    Retry = "Retry"      # reia pasul care a esuat
    Skip = "Skip"        # pasul se considera rezolvat
    Error = "Error"      # eroarea merge mai departe (politica normala)


class UiTechnology(_StrEnum):
    Web = "Web"
    WebSelenium = "WebSelenium"
    Desktop = "Desktop"
    Sap = "Sap"


class LocatorKind(_StrEnum):
    TestId = "TestId"
    Id = "Id"
    Role = "Role"
    Label = "Label"
    Placeholder = "Placeholder"
    Name = "Name"
    Text = "Text"
    Css = "Css"
    XPath = "XPath"
    AutomationId = "AutomationId"
    UiaName = "UiaName"
    ClassName = "ClassName"
    UiaPath = "UiaPath"
    SapId = "SapId"
    SapName = "SapName"


class RprAction(_StrEnum):
    Click = "Click"
    DoubleClick = "DoubleClick"
    RightClick = "RightClick"
    Hover = "Hover"
    TypeText = "TypeText"
    AppendText = "AppendText"
    Clear = "Clear"
    PressKey = "PressKey"
    SelectOption = "SelectOption"
    Check = "Check"
    Uncheck = "Uncheck"
    Focus = "Focus"
    ReadText = "ReadText"
    ReadValue = "ReadValue"
    ReadAttribute = "ReadAttribute"
    Highlight = "Highlight"
    ScreenshotElement = "ScreenshotElement"
    OpenBrowser = "OpenBrowser"
    Navigate = "Navigate"
    Back = "Back"
    Refresh = "Refresh"
    SwitchTab = "SwitchTab"
    HandleDialog = "HandleDialog"
    ScreenshotPage = "ScreenshotPage"
    CloseBrowser = "CloseBrowser"
    SapConnect = "SapConnect"
    SapTransaction = "SapTransaction"
    SapSendKey = "SapSendKey"
    SapReadStatusBar = "SapReadStatusBar"
    SapGridReadCell = "SapGridReadCell"
    SapGridRowCount = "SapGridRowCount"
    LaunchApp = "LaunchApp"
    AttachWindow = "AttachWindow"
    CloseWindow = "CloseWindow"


class ConditionKind(_StrEnum):
    ElementExists = "ElementExists"
    ElementNotExists = "ElementNotExists"
    ElementVisible = "ElementVisible"
    ElementEnabled = "ElementEnabled"
    ElementText = "ElementText"
    Compare = "Compare"
    AllOf = "AllOf"
    AnyOf = "AnyOf"


class CompareOperator(_StrEnum):
    Equals = "Equals"
    NotEquals = "NotEquals"
    Contains = "Contains"
    NotContains = "NotContains"
    StartsWith = "StartsWith"
    EndsWith = "EndsWith"
    IsEmpty = "IsEmpty"
    IsNotEmpty = "IsNotEmpty"
    GreaterThan = "GreaterThan"
    GreaterOrEqual = "GreaterOrEqual"
    LessThan = "LessThan"
    LessOrEqual = "LessOrEqual"
    MatchesRegex = "MatchesRegex"


class WaitMode(_StrEnum):
    Seconds = "Seconds"
    UntilTrue = "UntilTrue"


class VariableOperation(_StrEnum):
    Set = "Set"
    Append = "Append"
    Increment = "Increment"
    Decrement = "Decrement"
    Trim = "Trim"
    ToUpper = "ToUpper"
    ToLower = "ToLower"
    Replace = "Replace"


class LoopMode(_StrEnum):
    Times = "Times"
    While = "While"
    Until = "Until"


class CellColor(_StrEnum):
    None_ = "None"
    Green = "Green"
    Red = "Red"
    Yellow = "Yellow"
    Orange = "Orange"
    Blue = "Blue"


class RprLogLevel(_StrEnum):
    Info = "Info"
    Warning = "Warning"
    Error = "Error"


# ─────────────────────────────────────────────────────────────
# Catalogul actiunilor (ce campuri arata Studio pentru fiecare)
# ─────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class ActionInfo:
    action: RprAction
    label: str
    needs_target: bool
    target_optional: bool
    value_label: Optional[str]
    produces_output: bool
    technologies: Tuple[UiTechnology, ...]


_ALL = (UiTechnology.Web, UiTechnology.WebSelenium, UiTechnology.Desktop, UiTechnology.Sap)
_WEB = (UiTechnology.Web, UiTechnology.WebSelenium)
_SAP = (UiTechnology.Sap,)
_DESK = (UiTechnology.Desktop,)
A = RprAction

ACTIONS: List[ActionInfo] = [
    ActionInfo(A.Click, "Click", True, False, None, False, _ALL),
    ActionInfo(A.DoubleClick, "Dublu click", True, False, None, False, _ALL),
    ActionInfo(A.RightClick, "Click dreapta", True, False, None, False, _ALL),
    ActionInfo(A.Hover, "Mouse deasupra", True, False, None, False, _ALL),
    ActionInfo(A.TypeText, "Scrie text (inlocuieste)", True, False, "Text", False, _ALL),
    ActionInfo(A.AppendText, "Tasteaza text (adauga)", True, False, "Text", False, _ALL),
    ActionInfo(A.Clear, "Goleste campul", True, False, None, False, _ALL),
    ActionInfo(A.PressKey, "Apasa tasta", False, True, "Tasta (Enter, Tab, Ctrl+A...)", False, _ALL),
    ActionInfo(A.SelectOption, "Alege din lista", True, False, "Optiune (text)", False, _ALL),
    ActionInfo(A.Check, "Bifeaza", True, False, None, False, _ALL),
    ActionInfo(A.Uncheck, "Debifeaza", True, False, None, False, _ALL),
    ActionInfo(A.Focus, "Focus", True, False, None, False, _ALL),
    ActionInfo(A.ReadText, "Citeste textul", True, False, None, True, _ALL),
    ActionInfo(A.ReadValue, "Citeste valoarea", True, False, None, True, _ALL),
    ActionInfo(A.ReadAttribute, "Citeste atribut", True, False, "Nume atribut", True, _ALL),
    ActionInfo(A.Highlight, "Marcheaza (verificare)", True, False, None, False, _ALL),
    ActionInfo(A.ScreenshotElement, "Captura element", True, False, "Fisier (optional)", True, _ALL),
    ActionInfo(A.OpenBrowser, "Deschide browser", False, False, "URL de start", False, _WEB),
    ActionInfo(A.Navigate, "Mergi la URL", False, False, "URL", False, _WEB),
    ActionInfo(A.Back, "Inapoi", False, False, None, False, _WEB),
    ActionInfo(A.Refresh, "Reincarca pagina", False, False, None, False, _WEB),
    ActionInfo(A.SwitchTab, "Schimba tab-ul", False, False, "Index sau text din titlu", False, _WEB),
    ActionInfo(A.HandleDialog, "Raspuns la popup JS", False, False, "accept / dismiss", False, _WEB),
    ActionInfo(A.ScreenshotPage, "Captura pagina", False, False, "Fisier (optional)", True, _WEB),
    ActionInfo(A.CloseBrowser, "Inchide browser", False, False, None, False, _WEB),
    ActionInfo(A.SapConnect, "SAP: conecteaza la sesiune", False, False, "Index sesiune (gol = prima)", False, _SAP),
    ActionInfo(A.SapTransaction, "SAP: porneste tranzactie", False, False, "Cod tranzactie", False, _SAP),
    ActionInfo(A.SapSendKey, "SAP: trimite tasta", False, False, "Tasta (Enter, F3, F8...)", False, _SAP),
    ActionInfo(A.SapReadStatusBar, "SAP: citeste bara de stare", False, False, None, True, _SAP),
    ActionInfo(A.SapGridReadCell, "SAP: citeste celula tabel", True, False, "rand|coloana", True, _SAP),
    ActionInfo(A.SapGridRowCount, "SAP: numar randuri tabel", True, False, None, True, _SAP),
    ActionInfo(A.LaunchApp, "Porneste aplicatie", False, False, "Cale .exe [argumente]", False, _DESK),
    ActionInfo(A.AttachWindow, "Ataseaza fereastra", False, False, "Titlu (regex) sau proces:nume.exe", False, _DESK),
    ActionInfo(A.CloseWindow, "Inchide fereastra", False, False, None, False, _DESK),
]
_ACTION_INDEX = {a.action: a for a in ACTIONS}


def action_info(action: RprAction) -> ActionInfo:
    return _ACTION_INDEX[RprAction.parse(action)]


# ─────────────────────────────────────────────────────────────
# Serializare generica (dataclass <-> dict JSON)
# ─────────────────────────────────────────────────────────────
def _now_iso() -> str:
    return _dt.datetime.now().astimezone().isoformat()


def _new_id() -> str:
    return uuid.uuid4().hex[:10]


class _Json:
    """Baza: to_dict / from_dict pe baza campurilor dataclass; pastreaza campurile necunoscute."""

    # campurile enum: nume camp -> tipul enum (fara adnotare, ca sa nu devina camp dataclass)
    _enum_fields = {}

    def to_dict(self) -> Dict[str, Any]:
        out: Dict[str, Any] = {}
        for f in fields(self):  # type: ignore[arg-type]
            if f.name == "extra":
                continue
            out[f.name] = _to_json(getattr(self, f.name))
        out.update(getattr(self, "extra", {}) or {})
        return out

    @classmethod
    def from_dict(cls, d: Dict[str, Any]):
        known = {f.name for f in fields(cls)}  # type: ignore[arg-type]
        kwargs: Dict[str, Any] = {}
        extra: Dict[str, Any] = {}
        for k, v in (d or {}).items():
            key = _snake(k)
            if key in known and key != "extra":
                kwargs[key] = cls._convert(key, v)
            elif key != "kind":
                extra[k] = v
        obj = cls(**kwargs)
        if "extra" in known:
            obj.extra = extra  # type: ignore[attr-defined]
        return obj

    @classmethod
    def _convert(cls, key: str, v: Any) -> Any:
        enum_t = cls._enum_fields.get(key)
        if enum_t is not None and v is not None:
            return enum_t.parse(v)
        return v


def _to_json(v: Any) -> Any:
    if isinstance(v, _StrEnum):
        return v.value
    if isinstance(v, _Json):
        return v.to_dict()
    if isinstance(v, list):
        return [_to_json(x) for x in v]
    if isinstance(v, dict):
        return {k: _to_json(x) for k, x in v.items()}
    return v


_CAMEL = re.compile(r"(?<=[a-z0-9])([A-Z])")


def _snake(name: str) -> str:
    """Accepta si chei PascalCase / camelCase (C# e case-insensitive la citire)."""
    if "_" in name or name.islower():
        return name.lower()
    return _CAMEL.sub(r"_\1", name).lower()


# ─────────────────────────────────────────────────────────────
# Conditie
# ─────────────────────────────────────────────────────────────
_OP_TEXT = {
    "Equals": "=", "NotEquals": "≠", "Contains": "contine", "NotContains": "nu contine",
    "StartsWith": "incepe cu", "EndsWith": "se termina cu", "IsEmpty": "e gol", "IsNotEmpty": "nu e gol",
    "GreaterThan": ">", "GreaterOrEqual": "≥", "LessThan": "<", "LessOrEqual": "≤",
    "MatchesRegex": "potriveste regex",
}


def op_text(op: CompareOperator) -> str:
    return _t(_OP_TEXT.get(CompareOperator.parse(op).value, str(op)))


@dataclass
class Condition(_Json):
    kind: ConditionKind = ConditionKind.ElementExists
    target: str = ""
    left: str = ""
    operator: CompareOperator = CompareOperator.Equals
    right: str = ""
    ignore_case: bool = True
    negate: bool = False
    timeout_ms: int = 0
    children: List["Condition"] = field(default_factory=list)
    extra: Dict[str, Any] = field(default_factory=dict, repr=False)

    _enum_fields = {"kind": ConditionKind, "operator": CompareOperator}

    @classmethod
    def _convert(cls, key, v):
        if key == "children":
            return [Condition.from_dict(x) for x in (v or [])]
        return super()._convert(key, v)

    def describe(self) -> str:
        k = self.kind
        if k == ConditionKind.ElementExists:
            core = f"[{self.target}] " + _t("exista")
        elif k == ConditionKind.ElementNotExists:
            core = f"[{self.target}] " + _t("nu exista")
        elif k == ConditionKind.ElementVisible:
            core = f"[{self.target}] " + _t("e vizibil")
        elif k == ConditionKind.ElementEnabled:
            core = f"[{self.target}] " + _t("e activ")
        elif k == ConditionKind.ElementText:
            core = f"text [{self.target}] {op_text(self.operator)} \"{self.right}\""
        elif k == ConditionKind.Compare:
            core = f"{self.left} {op_text(self.operator)} \"{self.right}\""
        elif k == ConditionKind.AllOf:
            core = "(" + (" %s " % _t("SI")).join(c.describe() for c in self.children) + ")"
        elif k == ConditionKind.AnyOf:
            core = "(" + (" %s " % _t("SAU")).join(c.describe() for c in self.children) + ")"
        else:
            core = str(k)
        return f"{_t('NU')} {core}" if self.negate else core


# ─────────────────────────────────────────────────────────────
# Pasii (nodurile arborelui)
# ─────────────────────────────────────────────────────────────
NODE_TYPES: Dict[str, Type["RprNode"]] = {}


def _node(kind: str):
    def deco(cls):
        cls.KIND = kind
        NODE_TYPES[kind] = cls
        return cls
    return deco


def _nodes_from(v) -> List["RprNode"]:
    return [node_from_dict(x) for x in (v or [])]


@dataclass
class RprNode(_Json):
    KIND = ""
    KIND_LABEL = ""

    id: str = field(default_factory=_new_id)
    label: str = ""
    enabled: bool = True
    delay_before_ms: int = 0
    delay_after_ms: int = 0
    on_error: ErrorPolicy = ErrorPolicy.Inherit
    comment: str = ""
    extra: Dict[str, Any] = field(default_factory=dict, repr=False)

    # (fara adnotari de tip: altfel dataclass le-ar trata drept campuri)
    _enum_fields = {"on_error": ErrorPolicy}
    _child_lists = ()            # campurile care contin liste de pasi
    _branch_names = ()           # numele ramurilor in Studio

    @property
    def title(self) -> str:
        return self.label if self.label.strip() else self.auto_title()

    def auto_title(self) -> str:
        return _t(self.KIND_LABEL)

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        return {"kind": self.KIND, **d}  # "kind" primul: C# (System.Text.Json) il cere primul

    @classmethod
    def _convert(cls, key, v):
        if key in cls._child_lists:
            return _nodes_from(v)
        if key == "condition":
            return Condition.from_dict(v or {})
        return super()._convert(key, v)

    @property
    def is_container(self) -> bool:
        return bool(self._child_lists)

    def branches(self) -> List[Tuple[str, List["RprNode"]]]:
        return [(n, getattr(self, f)) for n, f in zip(self._branch_names, self._child_lists)]


def node_from_dict(d: Dict[str, Any]) -> RprNode:
    kind = (d or {}).get("kind") or (d or {}).get("Kind") or ""
    cls = NODE_TYPES.get(str(kind).lower())
    if cls is None:
        raise ValueError(f"Tip de pas necunoscut in fisier: \"{kind}\"")
    return cls.from_dict(d)


@_node("action")
@dataclass
class ActionNode(RprNode):
    KIND_LABEL = "Actiune"
    action: RprAction = RprAction.Click
    target: str = ""
    value: str = ""
    output_variable: str = ""
    expected_value: str = ""
    technology: UiTechnology = UiTechnology.Web
    timeout_ms: int = 10000
    direct_mode: bool = False

    _enum_fields = {**RprNode._enum_fields, "action": RprAction, "technology": UiTechnology}

    def auto_title(self) -> str:
        info = action_info(self.action)
        s = _t(info.label)
        if self.target.strip():
            s += f" [{self.target}]"
        if info.value_label and self.value.strip():
            s += f" = \"{self.value}\""
        if info.produces_output and self.output_variable.strip():
            s += f" → {{{self.output_variable}}}"
        return s


@_node("wait")
@dataclass
class WaitNode(RprNode):
    KIND_LABEL = "Asteapta"
    mode: WaitMode = WaitMode.Seconds
    seconds: float = 1
    condition: Condition = field(default_factory=Condition)
    timeout_ms: int = 30000
    fail_on_timeout: bool = True

    _enum_fields = {**RprNode._enum_fields, "mode": WaitMode}

    def auto_title(self) -> str:
        if self.mode == WaitMode.Seconds:
            return _t("Asteapta {0} s").format(_num(self.seconds))
        return _t("Asteapta pana cand {0} (max {1} s)").format(self.condition.describe(),
                                                             _num(self.timeout_ms / 1000.0, 1))


@_node("set_variable")
@dataclass
class SetVariableNode(RprNode):
    KIND_LABEL = "Variabila"
    name: str = "Var1"
    operation: VariableOperation = VariableOperation.Set
    value: str = ""
    find: str = ""

    _enum_fields = {**RprNode._enum_fields, "operation": VariableOperation}

    def auto_title(self) -> str:
        op, n = self.operation, self.name
        if op == VariableOperation.Set:
            return f"{{{n}}} = \"{self.value}\""
        if op == VariableOperation.Append:
            return f"{{{n}}} += \"{self.value}\""
        if op == VariableOperation.Increment:
            return f"{{{n}}} + 1"
        if op == VariableOperation.Decrement:
            return f"{{{n}}} - 1"
        if op == VariableOperation.Replace:
            return f"{{{n}}}: \"{self.find}\" → \"{self.value}\""
        return f"{{{n}}}: {op}"


@_node("if")
@dataclass
class IfNode(RprNode):
    KIND_LABEL = "Daca"
    condition: Condition = field(default_factory=Condition)
    then: List[RprNode] = field(default_factory=list)
    else_: List[RprNode] = field(default_factory=list)
    optional: bool = False   # "Daca apare" (v4.13): se asteapta scurt; daca nu apare, rutina merge mai departe

    _child_lists = ("then", "else_")
    _branch_names = ("Atunci", "Altfel")

    def auto_title(self) -> str:
        return (_t("Daca apare {0}") if self.optional else _t("Daca {0}")).format(self.condition.describe())

    # "else" e cuvant rezervat in Python -> campul se numeste else_, in JSON "else"
    def to_dict(self):
        d = super().to_dict()
        d["else"] = d.pop("else_")
        return d

    @classmethod
    def from_dict(cls, d):
        d = dict(d or {})
        if "else" in d:
            d["else_"] = d.pop("else")
        elif "Else" in d:
            d["else_"] = d.pop("Else")
        return super().from_dict(d)


@_node("loop")
@dataclass
class LoopNode(RprNode):
    KIND_LABEL = "Repeta"
    mode: LoopMode = LoopMode.Times
    count: str = "3"
    condition: Condition = field(default_factory=Condition)
    max_iterations: int = 1000
    counter_variable: str = "Repetare"
    body: List[RprNode] = field(default_factory=list)

    _enum_fields = {**RprNode._enum_fields, "mode": LoopMode}
    _child_lists = ("body",)
    _branch_names = ("Pasi",)

    def auto_title(self) -> str:
        if self.mode == LoopMode.Times:
            return _t("Repeta de {0} ori").format(self.count)
        if self.mode == LoopMode.While:
            return _t("Repeta cat timp {0}").format(self.condition.describe())
        return _t("Repeta pana cand {0}").format(self.condition.describe())


@_node("for_each_row")
@dataclass
class ForEachRowNode(RprNode):
    KIND_LABEL = "Pentru fiecare rand Excel"
    file_path: str = ""
    sheet: str = ""
    header_row: int = 1
    start_row: int = 0
    end_row: int = 0
    key_column: str = ""
    row_variable: str = "Rand"
    status_column: str = "Status"
    color_rows: bool = True
    save_after_each_row: bool = True
    skip_completed_rows: bool = True
    body: List[RprNode] = field(default_factory=list)

    _child_lists = ("body",)
    _branch_names = ("Pasi pentru fiecare rand",)

    def auto_title(self) -> str:
        f = os.path.basename(self.file_path.replace("\\", "/")) if self.file_path.strip() else _t("(alege fisier)")
        sh = f" / {self.sheet}" if self.sheet.strip() else ""
        return _t("Pentru fiecare rand din {0} → {1}").format(f + sh, "{%s.*}" % self.row_variable)


@_node("write_excel")
@dataclass
class WriteExcelNode(RprNode):
    KIND_LABEL = "Scrie in Excel"
    column: str = "Rezultat"
    value: str = ""
    color: CellColor = CellColor.None_

    _enum_fields = {**RprNode._enum_fields, "color": CellColor}

    def auto_title(self) -> str:
        return f"Excel [{self.column}] = \"{self.value}\""


@_node("question")
@dataclass
class QuestionNode(RprNode):
    KIND_LABEL = "Intrebare"
    text: str = "Continui?"
    buttons: str = "Continua,Opreste,Sari"
    output_variable: str = "Raspuns"
    stop_button: str = "Opreste"
    skip_button: str = "Sari"

    def auto_title(self) -> str:
        return _t("Intreaba") + f": \"{self.text}\" [{self.buttons}]"


@_node("try")
@dataclass
class TryNode(RprNode):
    KIND_LABEL = "Incearca"
    body: List[RprNode] = field(default_factory=list)
    catch: List[RprNode] = field(default_factory=list)
    error_variable: str = "Eroare"

    _child_lists = ("body", "catch")
    _branch_names = ("Incearca", "La eroare")

    def auto_title(self) -> str:
        return _t("Incearca (eroarea → {{{0}}})").format(self.error_variable)


@_node("group")
@dataclass
class GroupNode(RprNode):
    KIND_LABEL = "Grup"
    body: List[RprNode] = field(default_factory=list)

    _child_lists = ("body",)
    _branch_names = ("Pasi",)

    def auto_title(self) -> str:
        return _t("Grup")


@_node("on_error_rule")
@dataclass
class RuleNode(RprNode):
    """Regula pentru mesaje / erori (v4.13): nu ruleaza cand e intalnita, ci se armeaza pana la sfarsitul
    listei in care sta. Daca un pas esueaza si regula se potriveste, se ruleaza pasii ei."""
    KIND_LABEL = "Regula la mesaj / eroare"
    error_contains: str = ""     # textul erorii (fara diferenta mare/mica); gol = nu conteaza
    use_element: bool = False    # sau: un element apare pe ecran (conditia de mai jos)
    condition: Condition = field(default_factory=lambda: Condition(kind=ConditionKind.ElementVisible))
    after: RuleAfter = RuleAfter.Retry
    body: List[RprNode] = field(default_factory=list)

    _enum_fields = {"on_error": ErrorPolicy, "after": RuleAfter}
    _child_lists = ("body",)
    _branch_names = ("Pasi de rulat",)

    def auto_title(self) -> str:
        what = []
        if self.error_contains.strip():
            what.append(_t("eroarea contine \"{0}\"").format(self.error_contains.strip()))
        if self.use_element:
            what.append(_t("apare {0}").format(self.condition.describe()))
        return _t("Regula") + ": " + ((" %s " % _t("sau")).join(what) if what else _t("(neconfigurata)"))


@_node("run_routine")
@dataclass
class RunRoutineNode(RprNode):
    """v4.12: ruleaza o rutina salvata (calup) ca pas. Foloseste aceleasi variabile, acelasi Excel si aceeasi
    biblioteca de obiecte ca rutina principala; setarile rutinei principale se aplica si calupului."""
    KIND_LABEL = "Ruleaza rutina"
    path: str = ""   # fisierul .rpr.json (poate contine {variabile})
    name: str = ""   # numele rutinei, doar pentru titlu

    def auto_title(self) -> str:
        shown = self.name.strip() or re.split(r"[\\/]", self.path.strip().rstrip("\\/"))[-1]
        for ext in (".rpr.json", ".json"):
            if shown.lower().endswith(ext):
                shown = shown[:-len(ext)]
        return _t("Ruleaza rutina") + (f" [{shown}]" if shown else "")


@_node("log")
@dataclass
class LogNode(RprNode):
    KIND_LABEL = "Log"
    message: str = ""
    level: RprLogLevel = RprLogLevel.Info

    _enum_fields = {**RprNode._enum_fields, "level": RprLogLevel}

    def auto_title(self) -> str:
        return f"Log: \"{self.message}\""


@_node("break")
@dataclass
class BreakNode(RprNode):
    KIND_LABEL = "Iesi din bucla"
    next_iteration: bool = False

    def auto_title(self) -> str:
        return _t("Treci la urmatoarea repetare" if self.next_iteration else "Iesi din bucla")


@_node("stop")
@dataclass
class StopNode(RprNode):
    KIND_LABEL = "Opreste rutina"
    message: str = ""
    as_error: bool = False

    def auto_title(self) -> str:
        return _t("Opreste cu eroare") + f": \"{self.message}\"" if self.as_error else _t("Opreste rutina")


@_node("legacy_step")
@dataclass
class LegacyStepNode(RprNode):
    """Pas din rutinele vechi (pe coordonate). `step` = dictionarul StepModel (chei snake_case)."""
    KIND_LABEL = "Pas vechi (coordonate)"
    step: Dict[str, Any] = field(default_factory=dict)

    def auto_title(self) -> str:
        s = self.step
        return f"[v3.9] {s.get('step_type', '')} ({s.get('x', 0)},{s.get('y', 0)}) {s.get('description', '')}".strip()


def _num(v: float, decimals: int = 2) -> str:
    """Ca formatul C# 0.## : fara zerouri inutile."""
    s = f"{v:.{decimals}f}".rstrip("0").rstrip(".")
    return s or "0"


# ─────────────────────────────────────────────────────────────
# Rutina
# ─────────────────────────────────────────────────────────────
@dataclass
class RoutineSettings(_Json):
    default_error_policy: ErrorPolicy = ErrorPolicy.Ask
    highlight_before_action: bool = True
    highlight_ms: int = 350
    default_timeout_ms: int = 10000
    step_delay_ms: int = 0
    auto_retries: int = 1
    screenshot_on_error: bool = True
    do_not_disturb: bool = True
    guard_enabled: bool = True
    extra: Dict[str, Any] = field(default_factory=dict, repr=False)

    _enum_fields = {"default_error_policy": ErrorPolicy}


@dataclass
class Routine(_Json):
    format_version: int = 2
    name: str = "Rutina noua"
    description: str = ""
    repository_path: str = ""
    variables: Dict[str, str] = field(default_factory=dict)
    settings: RoutineSettings = field(default_factory=RoutineSettings)
    steps: List[RprNode] = field(default_factory=list)
    created_at: str = field(default_factory=_now_iso)
    modified_at: str = field(default_factory=_now_iso)
    extra: Dict[str, Any] = field(default_factory=dict, repr=False)

    @classmethod
    def _convert(cls, key, v):
        if key == "steps":
            return _nodes_from(v)
        if key == "settings":
            return RoutineSettings.from_dict(v or {})
        if key == "variables":
            return {str(k): "" if x is None else str(x) for k, x in (v or {}).items()}
        return super()._convert(key, v)

    # ── Utilitare pentru arbore ─────────────────────────────
    def all_nodes(self) -> Iterator[RprNode]:
        return flatten(self.steps)

    def find_parent_list(self, node: RprNode) -> Optional[List[RprNode]]:
        return _find_parent_list(self.steps, node)

    def referenced_objects(self) -> Iterator[str]:
        for n in self.all_nodes():
            if isinstance(n, ActionNode) and n.target.strip():
                yield n.target
            cond = getattr(n, "condition", None)
            if isinstance(n, (IfNode, LoopNode, WaitNode)) and cond is not None:
                yield from _condition_targets(cond)
            if isinstance(n, RuleNode) and n.use_element:
                yield from _condition_targets(n.condition)


_ELEMENT_KINDS = {ConditionKind.ElementExists, ConditionKind.ElementNotExists, ConditionKind.ElementVisible,
                  ConditionKind.ElementEnabled, ConditionKind.ElementText}


def _condition_targets(c: Condition) -> Iterator[str]:
    if c.target.strip() and c.kind in _ELEMENT_KINDS:
        yield c.target
    for ch in c.children:
        yield from _condition_targets(ch)


def flatten(nodes: Iterable[RprNode]) -> Iterator[RprNode]:
    for n in nodes:
        yield n
        for _, lst in n.branches():
            yield from flatten(lst)


def _find_parent_list(lst: List[RprNode], node: RprNode) -> Optional[List[RprNode]]:
    if any(x is node for x in lst):
        return lst
    for n in lst:
        for _, child in n.branches():
            found = _find_parent_list(child, node)
            if found is not None:
                return found
    return None


# ─────────────────────────────────────────────────────────────
# Object Repository
# ─────────────────────────────────────────────────────────────
@dataclass
class Locator(_Json):
    kind: LocatorKind = LocatorKind.Css
    value: str = ""
    score: int = 50
    enabled: bool = True
    extra: Dict[str, Any] = field(default_factory=dict, repr=False)

    _enum_fields = {"kind": LocatorKind}

    def __str__(self) -> str:
        return f"{self.kind}: {self.value}"


@dataclass
class UiObject(_Json):
    name: str = ""
    technology: UiTechnology = UiTechnology.Web
    locators: List[Locator] = field(default_factory=list)
    context: str = ""
    frame_path: List[str] = field(default_factory=list)
    element_type: str = ""
    captured_text: str = ""
    screenshot: str = ""
    attributes: Dict[str, str] = field(default_factory=dict)
    description: str = ""
    captured_at: str = field(default_factory=_now_iso)
    # ── Biblioteca de obiecte (v4.5, ca in SilkTest) ──
    object_type: str = ""                                   # Buton, Camp, ComboBox, Tabel, RefList, Container...
    site: str = ""                                          # aplicatia / site-ul (grup de link-uri similare)
    page: str = ""                                          # pagina / ecranul din site
    parent: str = ""                                        # containerul in care se cauta obiectul (gol = toata pagina)
    folder: str = ""                                        # v4.11: folderul din tree-ul aplicatiei ("Comenzi/Export"); doar grupeaza, nu schimba cautarea
    url_patterns: List[str] = field(default_factory=list)   # link-uri unde e valid (* = orice); gol = ale site-ului
    tags: List[str] = field(default_factory=list)
    extra: Dict[str, Any] = field(default_factory=dict, repr=False)

    _enum_fields = {"technology": UiTechnology}

    @property
    def is_container(self) -> bool:
        return self.object_type in CONTAINER_TYPES

    @classmethod
    def _convert(cls, key, v):
        if key == "locators":
            return [Locator.from_dict(x) for x in (v or [])]
        return super()._convert(key, v)

    @property
    def active_locators(self) -> List[Locator]:
        return [l for l in self.locators if l.enabled and l.value.strip()]

    def __str__(self) -> str:
        return f"{self.name} ({self.technology})"


# ── Tipuri de obiecte (biblioteca) ──
OBJECT_TYPES = ["Buton", "Camp text", "ComboBox / lista derulanta", "Checkbox / radio", "Link", "Text / eticheta",
                "Tabel / grid", "RefList / lista", "Formular", "Container / sectiune", "Meniu / tab", "Altul"]
CONTAINER_TYPES = {"Tabel / grid", "RefList / lista", "Formular", "Container / sectiune", "Meniu / tab"}


def guess_object_type(element_type: str, attributes: Optional[Dict[str, str]] = None) -> str:
    """Tipul de obiect ghicit din elementul capturat (ex: "input (textbox)", "button", "select")."""
    t = (element_type or "").lower()
    a = {k.lower(): str(v).lower() for k, v in (attributes or {}).items()}
    typ = a.get("type", "")
    if "combobox" in t or "listbox" in t or t.startswith("select"):
        return "ComboBox / lista derulanta"
    if "checkbox" in t or "radio" in t or typ in ("checkbox", "radio") or "switch" in t:
        return "Checkbox / radio"
    if t.startswith("button") or "(button)" in t or typ in ("submit", "button", "reset"):
        return "Buton"
    if t.startswith(("input", "textarea")) or "textbox" in t or "searchbox" in t or "spinbutton" in t:
        return "Camp text"
    if t.startswith("a ") or t == "a" or "(link)" in t:
        return "Link"
    if t.startswith("table") or "grid" in t or "(table)" in t:
        return "Tabel / grid"
    if t.startswith(("ul", "ol")) or "(list)" in t:
        return "RefList / lista"
    if t.startswith("form"):
        return "Formular"
    if "tab" in t or "menu" in t:
        return "Meniu / tab"
    if t.startswith(("section", "fieldset", "nav", "aside", "main", "div")):
        return "Container / sectiune"
    if t.startswith(("label", "span", "p", "h1", "h2", "h3", "h4", "td", "th")):
        return "Text / eticheta"
    return "Altul"


def url_matches(url: str, patterns: Iterable[str]) -> bool:
    """Potrivire link cu sabloane: * = orice text; fara * = link-ul incepe cu sablonul (fara http(s)://)."""
    import fnmatch
    u = re.sub(r"^\w+://", "", (url or "").strip().lower()).rstrip("/")
    for p in patterns:
        p = re.sub(r"^\w+://", "", (p or "").strip().lower()).rstrip("/")
        if not p:
            continue
        if "*" in p or "?" in p:
            if fnmatch.fnmatch(u, p) or fnmatch.fnmatch(u, p + "/*"):
                return True
        elif u == p or u.startswith(p + "/") or u.startswith(p + "?") or u.startswith(p + "#"):
            return True
    return False


def split_url(url: str) -> Tuple[str, str]:
    """(domeniu, pagina) dintr-un link: "https://portal.x.com/app/orders/123?a=1" -> ("portal.x.com", "/app/orders")."""
    m = re.match(r"^\w+://([^/?#]+)([^?#]*)", (url or "").strip())
    if not m:
        return "", ""
    host, path = m.group(1).lower(), m.group(2)
    # pagina = primele 2 segmente care nu arata a ID (numere / coduri lungi)
    segs = [x for x in path.split("/") if x]
    keep = []
    for seg in segs:
        if re.fullmatch(r"[\d\-_.]+", seg) or re.fullmatch(r"[0-9a-fA-F\-]{16,}", seg):
            break
        keep.append(seg)
        if len(keep) == 2:
            break
    return host, "/" + "/".join(keep) if keep else "/"


@dataclass
class SiteGroup(_Json):
    """Un site / o aplicatie, cu toate link-urile la care raspunde (ex: test + productie = sisteme similare)."""
    name: str = ""
    url_patterns: List[str] = field(default_factory=list)
    description: str = ""
    extra: Dict[str, Any] = field(default_factory=dict, repr=False)


def sanitize_name(name: str) -> str:
    """Nume curat: fara spatii / caractere speciale, max 60 caractere."""
    name = re.sub(r"\s+", "_", (name or "").strip())
    name = re.sub(r"[^\w\-.]", "", name)  # \w in Python = litere (cu diacritice), cifre, _
    return name[:60]


@dataclass
class ObjectRepository(_Json):
    version: int = 1
    objects: List[UiObject] = field(default_factory=list)
    sites: List[SiteGroup] = field(default_factory=list)      # v4.5: site-uri cu link-uri similare
    extra: Dict[str, Any] = field(default_factory=dict, repr=False)

    @classmethod
    def _convert(cls, key, v):
        if key == "objects":
            return [UiObject.from_dict(x) for x in (v or [])]
        if key == "sites":
            return [SiteGroup.from_dict(x) for x in (v or [])]
        return super()._convert(key, v)

    # ── Biblioteca: clasificare dupa link ──
    def site_for_url(self, url: str) -> str:
        """Numele site-ului (grupului) care contine link-ul; altfel domeniul."""
        for g in self.sites:
            if url_matches(url, g.url_patterns):
                return g.name
        return split_url(url)[0]

    def find_site(self, name: str) -> Optional[SiteGroup]:
        return next((g for g in self.sites if g.name.lower() == (name or "").lower()), None)

    def classify(self, obj: UiObject) -> None:
        """Completeaza site / pagina / tipul unui obiect nou din link-ul unde a fost capturat."""
        if obj.context and not obj.site:
            if obj.technology in (UiTechnology.Web, UiTechnology.WebSelenium):
                obj.site = self.site_for_url(obj.context)
            elif obj.technology == UiTechnology.Sap:
                obj.site = "SAP GUI"
            else:
                obj.site = obj.context.replace("proces:", "")
        if obj.context and not obj.page and obj.technology in (UiTechnology.Web, UiTechnology.WebSelenium):
            obj.page = split_url(obj.context)[1]
        if not obj.object_type:
            obj.object_type = guess_object_type(obj.element_type, obj.attributes)

    def valid_on(self, obj: UiObject, url: str) -> bool:
        """Obiectul e definit pentru link-ul dat? (sabloanele lui; altfel ale site-ului; altfel orice)"""
        if obj.url_patterns:
            return url_matches(url, obj.url_patterns)
        g = self.find_site(obj.site)
        if g is not None and g.url_patterns:
            return url_matches(url, g.url_patterns)
        return True

    def children_of(self, name: str) -> List[UiObject]:
        return [o for o in self.objects if o.parent.lower() == (name or "").lower() and o.parent]

    def parent_chain(self, obj: UiObject) -> List[UiObject]:
        """Containerele obiectului, de la cel mai apropiat in sus (protectie la cicluri)."""
        chain, seen, cur = [], {obj.name.lower()}, obj
        while cur.parent and cur.parent.lower() not in seen:
            p = self.find(cur.parent)
            if p is None:
                break
            chain.append(p)
            seen.add(p.name.lower())
            cur = p
        return chain

    def link_parents(self, obj: UiObject) -> UiObject:
        """Leaga obiectul de containerele lui (parent_ref, nesalvat) — driverele cauta in container."""
        cur = obj
        for p in self.parent_chain(obj):
            object.__setattr__(cur, "parent_ref", p)
            cur = p
        object.__setattr__(cur, "parent_ref", None)
        return obj

    def find(self, name: Optional[str]) -> Optional[UiObject]:
        if not name or not name.strip():
            return None
        low = name.lower()
        return next((o for o in self.objects if o.name.lower() == low), None)

    def add(self, obj: UiObject) -> UiObject:
        obj.name = self.make_unique_name(obj.name or "Obiect")
        self.objects.append(obj)
        return obj

    def rename(self, obj: UiObject, new_name: str) -> bool:
        new_name = sanitize_name(new_name)
        if not new_name:
            return False
        existing = self.find(new_name)
        if existing is not None and existing is not obj:
            return False
        obj.name = new_name
        return True

    def remove(self, obj: UiObject) -> bool:
        if obj in self.objects:
            self.objects.remove(obj)
            for ch in self.children_of(obj.name):   # copiii raman, dar cautati in toata pagina
                ch.parent = obj.parent
            return True
        return False

    def rename_parent_refs(self, old: str, new: str) -> None:
        for o in self.objects:
            if o.parent.lower() == old.lower():
                o.parent = new

    def make_unique_name(self, base: str) -> str:
        base = sanitize_name(base) or "Obiect"
        if self.find(base) is None:
            return base
        i = 2
        while self.find(f"{base}_{i}") is not None:
            i += 1
        return f"{base}_{i}"
