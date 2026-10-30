# -*- coding: utf-8 -*-
# ============================================================
# AutoPilot DC v4.16 — RPR (Python)
# importer.py — 📥 Import pasi: din text simplu (scris de un AI dupa un document Word) sau din .rpr.json
#
# Fluxul: documentul Word cu procedura -> AI (cu promptul din ai_prompt()) -> textul "Pasi AutoPilot"
# -> lipit in Studio (📥 Import AI) -> verificare -> rutina noua (+ obiectele noi in biblioteca).
#
# Formatul (un pas pe rand, cuvinte cheie in romana sau engleza, fara diferenta mare / mica):
#   RUTINA: Raport zilnic                     DESCHIDE BROWSER https://exemplu.ro
#   VARIABILA: Fisier = C:\date.xlsx          SCRIE camp "Utilizator" = {Utilizator}
#   CLICK buton "Autentificare"               DACA vizibil text "Eroare" ... ALTFEL ... SFARSIT
# Lista completa: COMMANDS (mai jos) si promptul pentru AI.
# ============================================================

from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple

from .model import (ActionNode, Condition, ConditionKind, CompareOperator, ForEachRowNode, IfNode, Locator,
                    LocatorKind, LogNode, LoopMode, LoopNode, ObjectRepository, QuestionNode, Routine, RprAction,
                    RprNode, RunRoutineNode, SetVariableNode, StopNode, TryNode, UiObject, UiTechnology, WaitMode,
                    WaitNode, WriteExcelNode, guess_object_type, sanitize_name)


def _t(text: str) -> str:
    import sys
    m = sys.modules.get("i18n")
    if m is None or not hasattr(m, "tr"):
        return text
    return m.tr_template(text) if "{" in text and hasattr(m, "tr_template") else m.tr(text)


# ─────────────────────────────────────────────────────────────
# Rezultatul importului
# ─────────────────────────────────────────────────────────────
@dataclass
class ImportIssue:
    line: int           # 0 = tot textul
    text: str           # randul din text
    message: str
    error: bool = True


@dataclass
class ImportResult:
    routine: Routine
    new_objects: List[UiObject] = field(default_factory=list)
    issues: List[ImportIssue] = field(default_factory=list)
    source: str = "text"      # "text" sau "json"

    @property
    def errors(self) -> List[ImportIssue]:
        return [i for i in self.issues if i.error]

    @property
    def ok(self) -> bool:
        return not self.errors and bool(self.routine.steps)

    def step_count(self) -> int:
        return sum(1 for _ in self.routine.all_nodes())


# ─────────────────────────────────────────────────────────────
# Obiectele (tinta unui pas): [Nume din biblioteca] sau tip "valoare"
# ─────────────────────────────────────────────────────────────
# tip -> (tehnologie, locatori, tipul obiectului in biblioteca)
_W = UiTechnology.Web
_TARGET_KINDS: Dict[str, Tuple[UiTechnology, Callable[[str], List[Locator]], str]] = {
    "buton": (_W, lambda v: [Locator(LocatorKind.Role, "button|" + v, 90), Locator(LocatorKind.Text, v, 60)], "Buton"),
    "link": (_W, lambda v: [Locator(LocatorKind.Role, "link|" + v, 90), Locator(LocatorKind.Text, v, 60)], "Link"),
    "camp": (_W, lambda v: [Locator(LocatorKind.Label, v, 90), Locator(LocatorKind.Placeholder, v, 70)], "Camp text"),
    "lista": (_W, lambda v: [Locator(LocatorKind.Label, v, 90), Locator(LocatorKind.Role, "combobox|" + v, 70)],
              "ComboBox / lista derulanta"),
    "bifa": (_W, lambda v: [Locator(LocatorKind.Role, "checkbox|" + v, 90), Locator(LocatorKind.Label, v, 70)],
             "Checkbox / radio"),
    "text": (_W, lambda v: [Locator(LocatorKind.Text, v, 80)], "Text / eticheta"),
    "css": (_W, lambda v: [Locator(LocatorKind.Css, v, 80)], ""),
    "id": (_W, lambda v: [Locator(LocatorKind.Id, v, 95)], ""),
    "nume": (_W, lambda v: [Locator(LocatorKind.Name, v, 85)], ""),
    "xpath": (_W, lambda v: [Locator(LocatorKind.XPath, v, 60)], ""),
    "sap": (UiTechnology.Sap, lambda v: [Locator(LocatorKind.SapId, v, 95)], ""),
    "desktop": (UiTechnology.Desktop, lambda v: [Locator(LocatorKind.UiaName, v, 80)], ""),
    "desktopid": (UiTechnology.Desktop, lambda v: [Locator(LocatorKind.AutomationId, v, 95)], ""),
}
_KIND_ALIASES = {"button": "buton", "field": "camp", "input": "camp", "list": "lista", "dropdown": "lista",
                 "select": "lista", "checkbox": "bifa", "check": "bifa", "name": "nume", "label": "camp",
                 "eticheta": "text"}
_KIND_PREFIX = {"buton": "Buton", "link": "Link", "camp": "Camp", "lista": "Lista", "bifa": "Bifa", "text": "Text",
                "css": "Web", "id": "Web", "nume": "Web", "xpath": "Web", "sap": "SAP", "desktop": "Desktop",
                "desktopid": "Desktop"}


def _plain(s: str) -> str:
    """Fara diacritice, litere mici (pentru cuvintele cheie)."""
    s = unicodedata.normalize("NFKD", s)
    return "".join(c for c in s if not unicodedata.combining(c)).lower()


_QUOTES = {'"': '"', "'": "'", "„": "”", "“": "”", "”": "”", "«": "»"}


def _unquote(s: str) -> str:
    s = s.strip()
    if len(s) >= 2 and s[0] in _QUOTES and s[-1] == _QUOTES[s[0]]:
        return s[1:-1]
    if len(s) >= 2 and s[0] in "„“" and s[-1] in "”\"":
        return s[1:-1]
    return s


def _take_quoted(s: str) -> Tuple[Optional[str], str]:
    """Primul text intre ghilimele de la inceputul lui s -> (text, restul)."""
    s = s.lstrip()
    if not s or s[0] not in _QUOTES:
        return None, s
    end = s.find(_QUOTES[s[0]], 1)
    if end < 0 and s[0] in "„“":
        end = s.find('"', 1)
    if end < 0:
        return None, s
    return s[1:end], s[end + 1:]


# ─────────────────────────────────────────────────────────────
# Comenzile (RO, EN) — ordinea conteaza: cele mai lungi primele
# ─────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class Command:
    key: str
    ro: Tuple[str, ...]
    en: Tuple[str, ...]
    syntax_ro: str
    syntax_en: str
    help: str            # explicatia (romana, se traduce)


COMMANDS: List[Command] = [
    Command("routine", ("rutina:", "nume:"), ("routine:", "name:"), "RUTINA: <nume>", "ROUTINE: <name>",
            "Numele rutinei (primul rand)."),
    Command("description", ("descriere:",), ("description:",), "DESCRIERE: <text>", "DESCRIPTION: <text>",
            "Descrierea rutinei."),
    Command("variable", ("variabila:",), ("variable:",), "VARIABILA: <Nume> = <valoare>",
            "VARIABLE: <Name> = <value>", "Variabila cu valoare de pornire; o folosesti apoi ca {Nume}."),
    Command("open_browser", ("deschide browser",), ("open browser",), "DESCHIDE BROWSER <url>",
            "OPEN BROWSER <url>", "Porneste browserul la o adresa."),
    Command("navigate", ("mergi la",), ("go to", "navigate"), "MERGI LA <url>", "GO TO <url>",
            "Deschide o adresa in browserul deschis."),
    Command("close_browser", ("inchide browser",), ("close browser",), "INCHIDE BROWSER", "CLOSE BROWSER",
            "Inchide browserul."),
    Command("dblclick", ("dublu click",), ("double click",), "DUBLU CLICK <obiect>", "DOUBLE CLICK <object>",
            "Dublu click pe un obiect."),
    Command("rclick", ("click dreapta",), ("right click",), "CLICK DREAPTA <obiect>", "RIGHT CLICK <object>",
            "Click dreapta pe un obiect."),
    Command("click", ("click", "apasa pe"), ("click",), "CLICK <obiect>", "CLICK <object>",
            "Click pe un obiect."),
    Command("write_excel", ("scrie in excel",), ("write excel", "write to excel"),
            "SCRIE IN EXCEL <coloana> = <valoare>", "WRITE EXCEL <column> = <value>",
            "Scrie in randul Excel curent (doar in PENTRU FIECARE RAND)."),
    Command("type", ("scrie", "completeaza"), ("type", "fill"), "SCRIE <obiect> = <text>", "TYPE <object> = <text>",
            "Completeaza un camp (inlocuieste textul)."),
    Command("append", ("adauga text",), ("append",), "ADAUGA TEXT <obiect> = <text>", "APPEND <object> = <text>",
            "Tasteaza text la sfarsitul campului."),
    Command("clear", ("goleste",), ("clear",), "GOLESTE <obiect>", "CLEAR <object>", "Goleste un camp."),
    Command("press", ("apasa tasta", "apasa"), ("press key", "press"), "APASA <tasta> [IN <obiect>]",
            "PRESS <key> [IN <object>]", "Apasa o tasta (Enter, Tab, Ctrl+S...)."),
    Command("select", ("alege",), ("select", "choose"), "ALEGE <obiect> = <optiune>", "SELECT <object> = <option>",
            "Alege o optiune dintr-o lista."),
    Command("uncheck", ("debifeaza",), ("uncheck",), "DEBIFEAZA <obiect>", "UNCHECK <object>", "Debifeaza."),
    Command("check", ("bifeaza",), ("check",), "BIFEAZA <obiect>", "CHECK <object>", "Bifeaza."),
    Command("read", ("citeste",), ("read",), "CITESTE <obiect> -> {Variabila}", "READ <object> -> {Variable}",
            "Citeste textul unui obiect intr-o variabila."),
    Command("wait", ("asteapta",), ("wait",), "ASTEAPTA <secunde> | ASTEAPTA <obiect> [MAX <secunde>]",
            "WAIT <seconds> | WAIT <object> [MAX <seconds>]", "Asteapta secunde sau pana apare un obiect."),
    Command("if_appears", ("daca apare",), ("if appears",), "DACA APARE <obiect> ... [ALTFEL ...] SFARSIT",
            "IF APPEARS <object> ... [ELSE ...] END", "Pasii din interior ruleaza doar daca obiectul apare (fara eroare altfel)."),
    Command("if", ("daca",), ("if",), "DACA <conditie> ... [ALTFEL ...] SFARSIT", "IF <condition> ... [ELSE ...] END",
            "Ramuri dupa o conditie."),
    Command("else", ("altfel",), ("else",), "ALTFEL [DACA <conditie>]", "ELSE [IF <condition>]",
            "Ramura cand conditia nu e adevarata."),
    Command("repeat", ("repeta",), ("repeat",), "REPETA <n> ... SFARSIT", "REPEAT <n> ... END",
            "Repeta pasii de n ori ({Repetare} = 1, 2, 3...)."),
    Command("for_each_row", ("pentru fiecare rand",), ("for each row",),
            "PENTRU FIECARE RAND <fisier.xlsx> [FOAIE <nume>] ... SFARSIT",
            "FOR EACH ROW <file.xlsx> [SHEET <name>] ... END",
            "Repeta pasii pentru fiecare rand Excel; valorile: {Rand.Coloana}."),
    Command("try", ("incearca",), ("try",), "INCEARCA ... LA EROARE ... SFARSIT", "TRY ... ON ERROR ... END",
            "Prinde erorile fara sa opreasca rutina."),
    Command("catch", ("la eroare",), ("on error", "catch"), "LA EROARE", "ON ERROR", "Pasii cand ceva a esuat."),
    Command("end", ("sfarsit", "gata bloc"), ("end",), "SFARSIT", "END", "Inchide DACA / REPETA / PENTRU / INCEARCA."),
    Command("set", ("seteaza",), ("set",), "SETEAZA {Variabila} = <valoare>", "SET {Variable} = <value>",
            "Da o valoare unei variabile."),
    Command("ask", ("intreaba",), ("ask",), "INTREABA \"<text>\" [BUTOANE A, B]", "ASK \"<text>\" [BUTTONS A, B]",
            "Intreaba utilizatorul; raspunsul in {Raspuns}."),
    Command("manual", ("manual",), ("manual",), "MANUAL \"<ce face omul>\"", "MANUAL \"<what the person does>\"",
            "Pas facut de om: rutina se opreste si asteapta Continua."),
    Command("log", ("log", "nota log"), ("log",), "LOG \"<text>\"", "LOG \"<text>\"", "Mesaj in log."),
    Command("sap_connect", ("sap conecteaza",), ("sap connect",), "SAP CONECTEAZA", "SAP CONNECT",
            "Se ataseaza la SAP GUI deschis."),
    Command("sap_tcode", ("sap tranzactie",), ("sap transaction",), "SAP TRANZACTIE <cod>", "SAP TRANSACTION <code>",
            "Porneste o tranzactie (ex: /nVA03)."),
    Command("sap_key", ("sap tasta",), ("sap key",), "SAP TASTA <tasta>", "SAP KEY <key>",
            "Trimite o tasta catre SAP (Enter, F3, F8...)."),
    Command("sap_status", ("sap citeste stare",), ("sap read status",), "SAP CITESTE STARE -> {Variabila}",
            "SAP READ STATUS -> {Variable}", "Citeste bara de stare SAP."),
    Command("start_app", ("porneste aplicatie",), ("start app",), "PORNESTE APLICATIE <cale.exe>",
            "START APP <path.exe>", "Porneste un program Windows."),
    Command("attach", ("ataseaza fereastra",), ("attach window",), "ATASEAZA FEREASTRA <titlu>",
            "ATTACH WINDOW <title>", "Lucreaza intr-o fereastra deschisa."),
    Command("run_routine", ("ruleaza rutina",), ("run routine",), "RULEAZA RUTINA <cale.rpr.json>",
            "RUN ROUTINE <path.rpr.json>", "Ruleaza o rutina salvata ca pas."),
    Command("stop", ("opreste",), ("stop",), "OPRESTE [\"<mesaj>\"]", "STOP [\"<message>\"]", "Opreste rutina."),
]
_ALL_KEYWORDS: List[Tuple[str, Command]] = sorted(
    ((kw, c) for c in COMMANDS for kw in c.ro + c.en), key=lambda x: -len(x[0]))

TARGET_HELP = [
    ("[Nume]", "[Name]", "Obiect din biblioteca, dupa nume."),
    ("buton \"Text\"", "button \"Text\"", "Buton dupa textul de pe el."),
    ("link \"Text\"", "link \"Text\"", "Link dupa text."),
    ("camp \"Eticheta\"", "field \"Label\"", "Camp dupa eticheta sau textul din el."),
    ("lista \"Eticheta\"", "list \"Label\"", "Lista derulanta dupa eticheta."),
    ("bifa \"Eticheta\"", "checkbox \"Label\"", "Checkbox dupa eticheta."),
    ("text \"Text\"", "text \"Text\"", "Orice element dupa textul afisat."),
    ("css \"#id\" · id \"...\" · xpath \"...\"", "css \"#id\" · id \"...\" · xpath \"...\"",
     "Selector exact, daca il stii."),
    ("sap \"wnd[0]/usr/...\"", "sap \"wnd[0]/usr/...\"", "Camp / buton SAP dupa ID (din Spy SAP)."),
    ("desktop \"Nume\"", "desktop \"Name\"", "Element dintr-o aplicatie Windows dupa nume."),
]
_OPS = [("nu contine", CompareOperator.NotContains), ("not contains", CompareOperator.NotContains),
        ("incepe cu", CompareOperator.StartsWith), ("starts with", CompareOperator.StartsWith),
        ("se termina cu", CompareOperator.EndsWith), ("ends with", CompareOperator.EndsWith),
        ("contine", CompareOperator.Contains), ("contains", CompareOperator.Contains),
        ("!=", CompareOperator.NotEquals), ("<>", CompareOperator.NotEquals), ("≠", CompareOperator.NotEquals),
        (">=", CompareOperator.GreaterOrEqual), ("<=", CompareOperator.LessOrEqual),
        ("==", CompareOperator.Equals), ("=", CompareOperator.Equals), (">", CompareOperator.GreaterThan),
        ("<", CompareOperator.LessThan)]


class _LineError(Exception):
    pass


# ─────────────────────────────────────────────────────────────
# Parserul
# ─────────────────────────────────────────────────────────────
class StepImporter:
    """Textul "Pasi AutoPilot" (sau un .rpr.json) -> Routine + obiecte noi pentru biblioteca."""

    def __init__(self, repo: Optional[ObjectRepository] = None):
        self.repo = repo or ObjectRepository()

    # ── intrarea ──
    def parse(self, text: str) -> ImportResult:
        text = (text or "").replace("\r\n", "\n").replace("\ufeff", "")
        stripped = _strip_fence(text)
        if stripped.lstrip().startswith(("{", "[")):
            return self._parse_json(stripped)
        return self._parse_text(stripped)

    # ── JSON: rutina .rpr.json sau {"name": ..., "steps": ["CLICK ...", ...]} ──
    def _parse_json(self, text: str) -> ImportResult:
        try:
            data = json.loads(text)
        except ValueError as ex:
            r = ImportResult(Routine(name=_t("Rutina importata")), source="json")
            r.issues.append(ImportIssue(0, "", _t("JSON invalid: {0}").format(ex)))
            return r
        if isinstance(data, list):
            data = {"steps": data}
        steps = data.get("steps") if isinstance(data, dict) else None
        if isinstance(steps, list) and steps and all(isinstance(s, str) for s in steps):
            lines = []
            for k in ("name", "routine", "rutina", "nume"):
                if data.get(k):
                    lines.append("RUTINA: " + str(data[k]))
                    break
            if data.get("description") or data.get("descriere"):
                lines.append("DESCRIERE: " + str(data.get("description") or data.get("descriere")))
            for k, v in (data.get("variables") or data.get("variabile") or {}).items():
                lines.append(f"VARIABILA: {k} = {v}")
            res = self._parse_text("\n".join(lines + steps))
            res.source = "json"
            return res
        try:   # rutina completa (formatul aplicatiei)
            routine = Routine.from_dict(data)
        except Exception as ex:  # noqa: BLE001
            r = ImportResult(Routine(name=_t("Rutina importata")), source="json")
            r.issues.append(ImportIssue(0, "", _t("Fisierul JSON nu e o rutina AutoPilot: {0}").format(ex)))
            return r
        res = ImportResult(routine, source="json")
        known = {o.name.lower() for o in self.repo.objects}
        for name in sorted(set(routine.referenced_objects())):
            if name.lower() not in known:
                res.issues.append(ImportIssue(0, name, _t("Obiectul [{0}] nu e in biblioteca: il marchezi cu Spy "
                                                          "inainte de rulare.").format(name), error=False))
        if not routine.steps:
            res.issues.append(ImportIssue(0, "", _t("Rutina nu are pasi.")))
        return res

    # ── text ──
    def _parse_text(self, text: str) -> ImportResult:
        res = ImportResult(Routine(name=_t("Rutina importata"), description=_t("Importata din text (📥 Import AI)")))
        self._res = res
        self._new: Dict[Tuple[str, str], UiObject] = {}
        self._url = ""
        # stiva: (nod, lista curenta, randul unde a inceput)
        self._stack: List[Tuple[Optional[RprNode], List[RprNode], int]] = [(None, res.routine.steps, 0)]
        self._chained: set = set()          # DACA-urile deschise de ALTFEL DACA
        self._end_if = 0                    # randul SFARSIT-ului care tocmai a inchis un DACA fara ALTFEL
        self._prev_end_if = 0
        for no, raw in enumerate(text.split("\n"), 1):
            line = _clean_line(raw)
            if not line:
                continue
            try:
                self._line(no, line)
            except _LineError as ex:
                res.issues.append(ImportIssue(no, raw.strip(), str(ex)))
            except Exception as ex:  # noqa: BLE001 — un rand gresit nu opreste importul
                res.issues.append(ImportIssue(no, raw.strip(), _t("Nu am inteles randul: {0}").format(ex)))
        for node, _, no in self._stack[1:]:
            res.issues.append(ImportIssue(no, node.title if node else "",
                                          _t("Blocul inceput aici nu are SFARSIT (END): l-am inchis la final."),
                                          error=False))
        res.new_objects = [o for o in self._new.values() if not any(o is x for x in self.repo.objects)]
        _declare_missing_variables(res)
        if not res.routine.steps and not res.errors:
            res.issues.append(ImportIssue(0, "", _t("Nu am gasit niciun pas. Verifica formatul (vezi promptul).")))
        return res

    def _add(self, node: RprNode) -> None:
        self._stack[-1][1].append(node)

    def _open(self, node: RprNode, lst: List[RprNode], no: int) -> None:
        self._add(node)
        self._stack.append((node, lst, no))

    def _line(self, no: int, line: str) -> None:
        low = _plain(line)
        cmd, rest = None, ""
        for kw, c in _ALL_KEYWORDS:
            if low.startswith(kw) and (len(low) == len(kw) or not low[len(kw)].isalnum() or kw.endswith(":")):
                cmd, rest = c, line[len(kw):].strip()
                break
        if cmd is None:
            raise _LineError(_t("Comanda necunoscuta. Randul trebuie sa inceapa cu o comanda (ex: CLICK, SCRIE, "
                                "DACA). Pentru un pas facut de om foloseste MANUAL \"...\"."))
        self._prev_end_if, self._end_if = self._end_if, 0
        getattr(self, "_c_" + cmd.key)(no, rest)

    # ── antet ──
    def _c_routine(self, no, rest):
        self._res.routine.name = _unquote(rest) or self._res.routine.name

    def _c_description(self, no, rest):
        self._res.routine.description = _unquote(rest)

    def _c_variable(self, no, rest):
        name, val = _split_eq(rest, _t("VARIABILA: Nume = valoare"))
        self._res.routine.variables[_var_name(name)] = _unquote(val)

    # ── browser / aplicatii ──
    def _c_open_browser(self, no, rest):
        self._url = _unquote(rest)
        self._add(ActionNode(action=RprAction.OpenBrowser, technology=UiTechnology.Web, value=self._url))

    def _c_navigate(self, no, rest):
        if not rest:
            raise _LineError(_t("Lipseste adresa (URL)."))
        self._url = _unquote(rest)
        self._add(ActionNode(action=RprAction.Navigate, technology=UiTechnology.Web, value=self._url))

    def _c_close_browser(self, no, rest):
        self._add(ActionNode(action=RprAction.CloseBrowser, technology=UiTechnology.Web))

    def _c_start_app(self, no, rest):
        self._add(ActionNode(action=RprAction.LaunchApp, technology=UiTechnology.Desktop, value=_unquote(rest)))

    def _c_attach(self, no, rest):
        self._add(ActionNode(action=RprAction.AttachWindow, technology=UiTechnology.Desktop, value=_unquote(rest)))

    def _c_sap_connect(self, no, rest):
        self._add(ActionNode(action=RprAction.SapConnect, technology=UiTechnology.Sap, value=_unquote(rest)))

    def _c_sap_tcode(self, no, rest):
        self._add(ActionNode(action=RprAction.SapTransaction, technology=UiTechnology.Sap, value=_unquote(rest)))

    def _c_sap_key(self, no, rest):
        self._add(ActionNode(action=RprAction.SapSendKey, technology=UiTechnology.Sap, value=_unquote(rest) or "Enter"))

    def _c_sap_status(self, no, rest):
        _, var = _split_arrow(rest)
        self._add(ActionNode(action=RprAction.SapReadStatusBar, technology=UiTechnology.Sap,
                             output_variable=var or "StareSAP"))

    def _c_run_routine(self, no, rest):
        self._add(RunRoutineNode(path=_unquote(rest)))

    # ── actiuni pe obiecte ──
    def _action(self, action, rest, value=None):
        obj = self._target(rest)
        self._add(ActionNode(action=action, target=obj.name, technology=obj.technology,
                             value=_unquote(value) if value is not None else ""))

    def _c_click(self, no, rest):
        self._action(RprAction.Click, rest)

    def _c_dblclick(self, no, rest):
        self._action(RprAction.DoubleClick, rest)

    def _c_rclick(self, no, rest):
        self._action(RprAction.RightClick, rest)

    def _c_type(self, no, rest):
        tgt, val = _split_eq(rest, _t("SCRIE <obiect> = <text>"))
        self._action(RprAction.TypeText, tgt, val)

    def _c_append(self, no, rest):
        tgt, val = _split_eq(rest, _t("ADAUGA TEXT <obiect> = <text>"))
        self._action(RprAction.AppendText, tgt, val)

    def _c_clear(self, no, rest):
        self._action(RprAction.Clear, rest)

    def _c_select(self, no, rest):
        tgt, val = _split_eq(rest, _t("ALEGE <obiect> = <optiune>"))
        self._action(RprAction.SelectOption, tgt, val)

    def _c_check(self, no, rest):
        self._action(RprAction.Check, rest)

    def _c_uncheck(self, no, rest):
        self._action(RprAction.Uncheck, rest)

    def _c_press(self, no, rest):
        m = re.match(r"(.+?)\s+(?:in|în|on)\s+(.+)$", rest, re.I)
        key, tgt = (m.group(1), m.group(2)) if m else (rest, "")
        key = _unquote(key)
        if not key:
            raise _LineError(_t("Lipseste tasta (ex: APASA Enter)."))
        if tgt:
            obj = self._target(tgt)
            self._add(ActionNode(action=RprAction.PressKey, target=obj.name, technology=obj.technology, value=key))
        else:
            tech = self._last_tech()
            if tech == UiTechnology.Sap:
                self._add(ActionNode(action=RprAction.SapSendKey, technology=tech, value=key))
            else:
                self._add(ActionNode(action=RprAction.PressKey, technology=tech, value=key))

    def _c_read(self, no, rest):
        tgt, var = _split_arrow(rest)
        obj = self._target(tgt)
        self._add(ActionNode(action=RprAction.ReadText, target=obj.name, technology=obj.technology,
                             output_variable=var or "Text"))

    def _c_wait(self, no, rest):
        r = rest.strip()
        m = re.fullmatch(r"(\d+(?:[.,]\d+)?)\s*(?:s|sec|secunde|secunda|seconds?)?", r, re.I)
        if m:
            self._add(WaitNode(seconds=float(m.group(1).replace(",", "."))))
            return
        mx = re.search(r"\s+max\s+(\d+(?:[.,]\d+)?)\s*(?:s|sec|secunde|seconds?)?\s*$", r, re.I)
        timeout = 30.0
        if mx:
            timeout = float(mx.group(1).replace(",", "."))
            r = r[:mx.start()]
        cond = self._condition(r) if _plain(r).startswith(("vizibil", "visible", "exista", "exists", "nu exista",
                                                          "not exists", "dispare", "disappears")) \
            else Condition(kind=ConditionKind.ElementVisible, target=self._target(r).name)
        self._add(WaitNode(mode=WaitMode.UntilTrue, condition=cond, timeout_ms=int(timeout * 1000)))

    # ── blocuri ──
    def _c_if(self, no, rest):
        node = IfNode(condition=self._condition(rest))
        self._open(node, node.then, no)

    def _c_if_appears(self, no, rest):
        r = rest
        if not _plain(r).startswith(("vizibil", "visible", "exista", "exists")):
            r = "vizibil " + r
        node = IfNode(condition=self._condition(r), optional=True)
        self._open(node, node.then, no)

    def _c_else(self, no, rest):
        node, lst, start = self._stack[-1]
        if not isinstance(node, IfNode):
            if self._prev_end_if:
                raise _LineError(_t("ALTFEL dupa SFARSIT: SFARSIT-ul de pe randul {0} a inchis deja DACA. "
                                    "Sterge acel SFARSIT (DACA ... ALTFEL ... SFARSIT are un singur SFARSIT).")
                                 .format(self._prev_end_if))
            raise _LineError(_t("ALTFEL fara DACA deschis."))
        if lst is node.else_:
            raise _LineError(_t("Al doilea ALTFEL in acelasi DACA. Inchide primul DACA cu SFARSIT sau "
                                "foloseste ALTFEL DACA <conditie>."))
        self._stack.pop()
        self._stack.append((node, node.else_, start))
        r = rest.strip()
        if not r:
            return
        m = re.match(r"(?:dac[aă]|if)\b\s*(.*)$", r, re.I | re.S)
        if not m:
            raise _LineError(_t("Dupa ALTFEL nu urmeaza nimic pe acelasi rand (doar ALTFEL DACA <conditie>)."))
        # ALTFEL DACA: un DACA nou in ramura Altfel, inchis de acelasi SFARSIT
        cond = m.group(1)
        ma = re.match(r"(?:apare|appears)\b\s*(.*)$", cond, re.I | re.S)
        if ma:
            self._c_if_appears(no, ma.group(1))
        else:
            self._c_if(no, cond)
        self._chained.add(id(self._stack[-1][0]))

    def _c_repeat(self, no, rest):
        m = re.match(r"(\{?\w[\w.]*\}?)\s*(?:ori|times|x)?\s*$", rest.strip(), re.I)
        if not m:
            raise _LineError(_t("REPETA are nevoie de un numar (ex: REPETA 3)."))
        count = m.group(1)
        node = LoopNode(mode=LoopMode.Times, count=count)
        self._open(node, node.body, no)

    def _c_for_each_row(self, no, rest):
        m = re.match(r"(.+?)(?:\s+(?:foaie|foaia|sheet)\s+(.+))?$", rest.strip(), re.I)
        if not m or not m.group(1).strip():
            raise _LineError(_t("Lipseste fisierul Excel (ex: PENTRU FIECARE RAND {Fisier} FOAIE Date)."))
        node = ForEachRowNode(file_path=_unquote(m.group(1)), sheet=_unquote(m.group(2) or ""))
        self._open(node, node.body, no)

    def _c_try(self, no, rest):
        node = TryNode()
        self._open(node, node.body, no)

    def _c_catch(self, no, rest):
        node = self._stack[-1][0]
        if not isinstance(node, TryNode):
            raise _LineError(_t("LA EROARE fara INCEARCA deschis."))
        _, _, start = self._stack.pop()
        self._stack.append((node, node.catch, start))

    def _c_end(self, no, rest):
        if len(self._stack) == 1:
            raise _LineError(_t("SFARSIT fara bloc deschis."))
        node, lst, _ = self._stack.pop()
        while id(node) in self._chained and len(self._stack) > 1:   # ALTFEL DACA: inchide si DACA-ul de deasupra
            node, lst, _ = self._stack.pop()
        if isinstance(node, IfNode) and lst is node.then:
            self._end_if = no

    # ── variabile, mesaje ──
    def _c_set(self, no, rest):
        name, val = _split_eq(rest, _t("SETEAZA {Variabila} = valoare"))
        self._add(SetVariableNode(name=_var_name(name), value=_unquote(val)))

    def _c_write_excel(self, no, rest):
        col, val = _split_eq(rest, _t("SCRIE IN EXCEL <coloana> = <valoare>"))
        if not any(isinstance(n, ForEachRowNode) for n, _, _ in self._stack[1:]):
            self._res.issues.append(ImportIssue(no, rest, _t("SCRIE IN EXCEL merge doar in PENTRU FIECARE RAND."),
                                                error=False))
        self._add(WriteExcelNode(column=_unquote(col), value=_unquote(val)))

    def _c_ask(self, no, rest):
        text, tail = _take_quoted(rest)
        if text is None:
            text, tail = rest, ""
        m = re.search(r"(?:butoane|buttons)\s*:?\s*(.+)$", tail, re.I)
        buttons = ",".join(b.strip() for b in m.group(1).split(",") if b.strip()) if m else "Continua,Opreste"
        self._add(QuestionNode(text=text.strip(), buttons=buttons))

    def _c_manual(self, no, rest):
        text = _unquote(rest)
        self._add(QuestionNode(text=_t("Pas manual: {0}\n\nFa pasul, apoi apasa Continua.").format(text),
                               buttons="Continua,Opreste", label=_t("✋ Manual: {0}").format(text[:60])))

    def _c_log(self, no, rest):
        self._add(LogNode(message=_unquote(rest)))

    def _c_stop(self, no, rest):
        self._add(StopNode(message=_unquote(rest)))

    # ── conditii ──
    def _condition(self, text: str) -> Condition:
        t = text.strip()
        for sep, kind in ((" sau ", ConditionKind.AnyOf), (" or ", ConditionKind.AnyOf),
                          (" si ", ConditionKind.AllOf), (" and ", ConditionKind.AllOf)):
            parts = _split_outside_quotes(t, sep)
            if len(parts) > 1:
                return Condition(kind=kind, children=[self._condition(p) for p in parts])
        low = _plain(t)
        for prefixes, kind in ((("nu exista", "not exists", "dispare", "disappears"), ConditionKind.ElementNotExists),
                               (("exista", "exists"), ConditionKind.ElementExists),
                               (("vizibil", "visible", "apare", "appears"), ConditionKind.ElementVisible),
                               (("activ", "enabled"), ConditionKind.ElementEnabled)):
            for p in prefixes:
                if low.startswith(p + " "):
                    return Condition(kind=kind, target=self._target(t[len(p):]).name)
        for word in ("e gol", "is empty"):
            if low.endswith(" " + word):
                return Condition(kind=ConditionKind.Compare, left=t[:-len(word)].strip(),
                                 operator=CompareOperator.IsEmpty)
        for op, cop in _OPS:
            i = _find_outside_quotes(low, " " + op + " ") if op[0].isalpha() else _find_outside_quotes(low, op)
            if i >= 0:
                n = len(op) + (2 if op[0].isalpha() else 0)
                left, right = t[:i].strip(), t[i + n:].strip()
                if left and right:
                    return Condition(kind=ConditionKind.Compare, left=left, operator=cop, right=_unquote(right))
        raise _LineError(_t("Nu am inteles conditia \"{0}\". Exemple: {{Raspuns}} = \"Da\" · vizibil buton \"OK\" · "
                            "exista [Nume]").format(text))

    # ── obiecte ──
    def _last_tech(self) -> UiTechnology:
        for n in reversed(list(self._res.routine.all_nodes())):
            if isinstance(n, ActionNode):
                return n.technology
        return UiTechnology.Web

    def _target(self, text: str) -> UiObject:
        t = text.strip()
        if not t:
            raise _LineError(_t("Lipseste obiectul (ex: buton \"Salveaza\" sau [Nume din biblioteca])."))
        m = re.fullmatch(r"\[(.+)\]", t)
        if m:   # obiect existent in biblioteca
            name = m.group(1).strip()
            obj = self.repo.find(name) or next((o for o in self._new.values() if o.name.lower() == name.lower()), None)
            if obj is None:
                self._res.issues.append(ImportIssue(0, name, _t("Obiectul [{0}] nu e in biblioteca: il marchezi cu "
                                                                "Spy inainte de rulare.").format(name), error=False))
                return UiObject(name=name, technology=self._last_tech())
            return obj
        m = re.match(r"([A-Za-zăâîșțĂÂÎȘȚ]+)\s*:?\s*(.+)$", t)
        kind = _plain(m.group(1)) if m else ""
        kind = _KIND_ALIASES.get(kind, kind)
        if kind not in _TARGET_KINDS:
            raise _LineError(_t("Nu stiu ce obiect e \"{0}\". Scrie tipul si textul: buton \"Salveaza\", camp "
                                "\"Utilizator\", link \"...\", text \"...\", sap \"...\" sau [Nume].").format(t))
        value = _unquote(m.group(2))
        if not value:
            raise _LineError(_t("Lipseste textul obiectului."))
        return self._object_for(kind, value)

    def _object_for(self, kind: str, value: str) -> UiObject:
        key = (kind, value.lower())
        if key in self._new:
            return self._new[key]
        tech, make, otype = _TARGET_KINDS[kind]
        locs = make(value)
        # acelasi obiect deja in biblioteca (acelasi prim locator)?
        for o in self.repo.objects:
            if o.technology == tech and o.active_locators and o.active_locators[0].kind == locs[0].kind \
                    and o.active_locators[0].value == locs[0].value:
                self._new[key] = o
                return o
        base = sanitize_name(f"{_KIND_PREFIX[kind]}_{value}")[:48] or "Obiect"
        taken = {o.name.lower() for o in self.repo.objects} | {o.name.lower() for o in self._new.values()}
        name, k = base, 2
        while name.lower() in taken:
            name, k = f"{base}_{k}", k + 1
        obj = UiObject(name=name, technology=tech, locators=locs, context=self._url if tech == _W else "",
                       captured_text=value, description=_t("Creat de 📥 Import AI"),
                       object_type=otype or guess_object_type("", {}))
        self._new[key] = obj
        return obj


_BUILTIN_VARS = {"azi", "today", "acum", "now", "newline", "repetare", "raspuns", "eroare", "eroareregula"}


def _declare_missing_variables(res: ImportResult) -> None:
    """Variabilele folosite ({Utilizator}) dar nedeclarate si neproduse de pasi primesc o valoare goala in rutina,
    ca sa le completezi in ⚙ Rutina (altfel rularea le-ar lasa ca text)."""
    produced = {k.lower() for k in res.routine.variables}
    used: List[str] = []
    for n in res.routine.all_nodes():
        for attr in ("output_variable", "error_variable", "counter_variable", "row_variable"):
            v = getattr(n, attr, "")
            if v:
                produced.add(v.lower())
        if isinstance(n, SetVariableNode):
            produced.add(n.name.lower())
        texts = [getattr(n, a, "") for a in ("value", "message", "text", "file_path", "count", "path")]
        cond = getattr(n, "condition", None)
        if cond is not None:
            texts += [cond.left, cond.right] + [c.left for c in cond.children] + [c.right for c in cond.children]
        for t in texts:
            if isinstance(t, str):
                used += re.findall(r"(?<!\{)\{([A-Za-z_ăâîșțĂÂÎȘȚ][\w ăâîșțĂÂÎȘȚ]*)(?::[^}]*)?\}", t)
    rows = {v.lower() for v in produced}
    for name in dict.fromkeys(used):
        low = name.lower()
        if low in produced or low in _BUILTIN_VARS or low.split(".")[0] in rows:
            continue
        res.routine.variables[name] = ""
        produced.add(low)
        res.issues.append(ImportIssue(0, name, _t("Variabila {{{0}}} nu are valoare: o completezi in ⚙ Rutina "
                                                  "(sau din Excel).").format(name), error=False))


# ─────────────────────────────────────────────────────────────
# Ajutoare de text
# ─────────────────────────────────────────────────────────────
def _strip_fence(text: str) -> str:
    """AI-ul pune des textul intre ``` ... ```: pastram doar interiorul primului bloc."""
    m = re.search(r"```[^\n]*\n(.*?)```", text, re.S)
    return m.group(1) if m else text


def _clean_line(raw: str) -> str:
    s = raw.strip()
    if not s or s.startswith(("#", "//", "--", ">")):
        return ""
    s = re.sub(r"^(?:\d+[.)]|[-*•·])\s+", "", s)          # numerotare / liste puse de AI
    s = re.sub(r"^\*\*(.+?)\*\*", r"\1", s)                # **CLICK** ...
    s = re.sub(r"^`(.+)`$", r"\1", s)
    return s.strip()


def _var_name(s: str) -> str:
    s = s.strip().strip("{}").strip()
    if not s:
        raise _LineError(_t("Lipseste numele variabilei."))
    return s


def _find_outside_quotes(s: str, needle: str) -> int:
    quote = None
    i = 0
    while i <= len(s) - len(needle):
        c = s[i]
        if quote:
            if c == quote:
                quote = None
        elif c in _QUOTES:
            quote = _QUOTES[c]
        elif s.startswith(needle, i):
            return i
        i += 1
    return -1


def _split_outside_quotes(s: str, sep: str) -> List[str]:
    parts, low = [], _plain(s)
    while True:
        i = _find_outside_quotes(low, sep)
        if i < 0:
            break
        parts.append(s[:i])
        s, low = s[i + len(sep):], low[i + len(sep):]
    parts.append(s)
    return [p.strip() for p in parts if p.strip()]


def _split_eq(rest: str, example: str) -> Tuple[str, str]:
    i = _find_outside_quotes(rest, "=")
    if i < 0:
        raise _LineError(_t("Lipseste \"=\". Exemplu: {0}").format(example))
    return rest[:i].strip(), rest[i + 1:].strip()


def _split_arrow(rest: str) -> Tuple[str, str]:
    for arrow in ("->", "→", "=>"):
        i = _find_outside_quotes(rest, arrow)
        if i >= 0:
            return rest[:i].strip(), rest[i + len(arrow):].strip().strip("{}").strip()
    return rest.strip(), ""


# ─────────────────────────────────────────────────────────────
# Promptul pentru AI (in limba aplicatiei)
# ─────────────────────────────────────────────────────────────
def ai_prompt(lang: str = "ro") -> str:
    """Textul de dat AI-ului impreuna cu documentul Word: explica formatul si regulile."""
    en = lang != "ro"
    t = _t
    lines = [
        t("Esti un asistent care transforma o procedura (document Word) in pasi pentru AutoPilot DC, un tool RPA."),
        t("Raspunde DOAR cu pasii, intr-un singur bloc de cod ```text ... ```, fara explicatii."),
        "",
        t("REGULI:"),
        t("- Un pas pe rand. Fiecare rand incepe cu o comanda din lista de mai jos (litere mari sau mici)."),
        t("- Textele de pe ecran (butoane, campuri, optiuni) se scriu EXACT ca in document, intre ghilimele."),
        t("- Valorile care se schimba de la o rulare la alta devin variabile: VARIABILA: Nume = valoare, apoi {Nume}."),
        t("- Daca procedura se repeta pentru mai multe randuri dintr-un Excel, foloseste PENTRU FIECARE RAND; "
          "valoarea unei coloane este {Rand.Coloana}."),
        t("- Ce nu se poate automatiza (o decizie, o semnatura, un telefon) devine MANUAL \"...\"."),
        t("- Nu inventa adrese, coduri sau texte care nu sunt in document; daca lipsesc, pune o variabila si un "
          "comentariu # pe randul de deasupra."),
        t("- Blocurile DACA / REPETA / PENTRU FIECARE RAND / INCEARCA se inchid cu SFARSIT."),
        t("- DACA ... ALTFEL ... SFARSIT are un singur SFARSIT, dupa ramura ALTFEL; nu pune SFARSIT inainte de "
          "ALTFEL. Un DACA in interiorul altui DACA se inchide cu propriul SFARSIT. Pentru mai multe variante "
          "foloseste ALTFEL DACA <conditie> (tot un singur SFARSIT la final)."),
        t("- Indenteaza cu 2 spatii pasii din interiorul unui bloc, ca sa se vada unde se inchide fiecare."),
        t("- Randurile care incep cu # sunt comentarii."),
        "",
        t("COMENZI:"),
    ]
    for c in COMMANDS:
        lines.append(f"  {c.syntax_en if en else c.syntax_ro}  —  {t(c.help)}")
    lines += ["", t("OBIECTE (<obiect> in comenzi):")]
    for ro, en_s, h in TARGET_HELP:
        lines.append(f"  {en_s if en else ro}  —  {t(h)}")
    lines += ["", t("CONDITII (dupa DACA):"),
              "  {Var} = \"x\" · {Var} != \"x\" · {Var} " + ("contains" if en else "contine") + " \"x\" · {Var} > 10 · "
              + ("visible" if en else "vizibil") + " <obj> · " + ("exists" if en else "exista") + " <obj> · "
              + ("not exists" if en else "nu exista") + " <obj> · A " + ("AND" if en else "SI") + " B · A "
              + ("OR" if en else "SAU") + " B",
              "", t("EXEMPLU:"), "```text", _EXAMPLE_EN if en else _EXAMPLE_RO, "```", "",
              t("Procedura de transformat:"), ""]
    return "\n".join(lines)


_EXAMPLE_RO = """RUTINA: Inregistrare comenzi
VARIABILA: Fisier = C:\\Date\\comenzi.xlsx
DESCHIDE BROWSER https://portal.exemplu.ro
SCRIE camp "Utilizator" = {Utilizator}
SCRIE camp "Parola" = {Parola}
CLICK buton "Autentificare"
ASTEAPTA text "Bun venit" MAX 15
PENTRU FIECARE RAND {Fisier} FOAIE Comenzi
  CLICK link "Comanda noua"
  SCRIE camp "Numar comanda" = {Rand.Comanda}
  ALEGE lista "Tara" = {Rand.Tara}
  CLICK buton "Salveaza"
  DACA vizibil text "Eroare"
    CITESTE text "Eroare" -> {Mesaj}
    SCRIE IN EXCEL Rezultat = {Mesaj}
  ALTFEL
    SCRIE IN EXCEL Rezultat = OK
  SFARSIT
SFARSIT
MANUAL "Verifica totalul in raportul zilnic"
INCHIDE BROWSER"""

_EXAMPLE_EN = """ROUTINE: Order entry
VARIABLE: File = C:\\Data\\orders.xlsx
OPEN BROWSER https://portal.example.com
TYPE field "User" = {User}
TYPE field "Password" = {Password}
CLICK button "Sign in"
WAIT text "Welcome" MAX 15
FOR EACH ROW {File} SHEET Orders
  CLICK link "New order"
  TYPE field "Order number" = {Rand.Order}
  SELECT list "Country" = {Rand.Country}
  CLICK button "Save"
  IF visible text "Error"
    READ text "Error" -> {Message}
    WRITE EXCEL Result = {Message}
  ELSE
    WRITE EXCEL Result = OK
  END
END
MANUAL "Check the total in the daily report"
CLOSE BROWSER"""
