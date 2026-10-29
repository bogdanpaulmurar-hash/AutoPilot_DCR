# -*- coding: utf-8 -*-
# ============================================================
# AutoPilot DC v4.1 — RPR (Python)
# storage.py — Salvare/incarcare rutine si Object Repository (JSON)
# + conversia rutinelor vechi (pe coordonate) + exportul logului in Excel.
#
# Folderele sunt aceleasi ca la versiunea C#:
#   %APPDATA%\AutoPilotDC\Studio\  rutine\ obiecte.json rezultate\ exemple\ ...
# ============================================================

from __future__ import annotations

import datetime as _dt
import json
import os
from typing import Any, Dict, Iterable, List, Optional

from .model import (ActionNode, Condition, ConditionKind, Locator, LocatorKind, LegacyStepNode, ObjectRepository,
                    QuestionNode, Routine, RprAction, RprLogLevel, RprNode, UiObject, UiTechnology, WaitMode,
                    WaitNode, sanitize_name)


class RprPaths:
    root = os.path.join(os.environ.get("APPDATA") or os.path.expanduser("~"), "AutoPilotDC", "Studio")

    @classmethod
    def _ensure(cls, *parts: str) -> str:
        p = os.path.join(cls.root, *parts)
        os.makedirs(p, exist_ok=True)
        return p

    @classmethod
    def routines(cls) -> str:
        return cls._ensure("rutine")

    @classmethod
    def output(cls) -> str:
        return cls._ensure("rezultate")

    @classmethod
    def object_images(cls) -> str:
        return cls._ensure("obiecte")

    @classmethod
    def browser_profile(cls) -> str:
        return cls._ensure("browser-profil")

    @classmethod
    def examples(cls) -> str:
        return cls._ensure("exemple")

    @classmethod
    def default_repository(cls) -> str:
        return os.path.join(cls._ensure(), "obiecte.json")


def _dumps(data: Any) -> str:
    # diacritice lizibile in fisier, indentare ca in C#
    return json.dumps(data, ensure_ascii=False, indent=2)


def atomic_write(path: str, content: str) -> None:
    """Scriem in .tmp apoi inlocuim: nu pierdem fisierul la o oprire brusca."""
    folder = os.path.dirname(os.path.abspath(path))
    os.makedirs(folder, exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)
    os.replace(tmp, path)


def _read_json(path: str) -> Any:
    with open(path, "r", encoding="utf-8-sig") as f:   # -sig: fisierele C# pot avea BOM
        return json.load(f)


class RoutineStore:
    @staticmethod
    def load(path: str, repo_for_legacy_import: Optional[ObjectRepository] = None) -> Routine:
        """Accepta formatul nou (format_version) si rutinele vechi (lista de pasi pe coordonate)."""
        data = _read_json(path)
        if isinstance(data, dict) and any(k.lower() in ("format_version", "formatversion") for k in data):
            return Routine.from_dict(data)

        name = os.path.splitext(os.path.basename(path))[0]
        if isinstance(data, list):
            steps = data
        else:
            steps = data.get("steps") or data.get("Steps") or []
            name = data.get("name") or data.get("Name") or name
        return LegacyConverter.convert(name, steps, repo_for_legacy_import)

    @staticmethod
    def save(routine: Routine, path: str) -> None:
        routine.modified_at = _dt.datetime.now().astimezone().isoformat()
        atomic_write(path, _dumps(routine.to_dict()))

    @staticmethod
    def default_path_for(routine: Routine) -> str:
        return os.path.join(RprPaths.routines(), (sanitize_name(routine.name) or "Rutina") + ".rpr.json")


class RepositoryStore:
    @staticmethod
    def load(path: Optional[str]) -> ObjectRepository:
        path = path if path and path.strip() else RprPaths.default_repository()
        if not os.path.isfile(path):
            return ObjectRepository()
        return ObjectRepository.from_dict(_read_json(path) or {})

    @staticmethod
    def save(repo: ObjectRepository, path: Optional[str]) -> None:
        path = path if path and path.strip() else RprPaths.default_repository()
        atomic_write(path, _dumps(repo.to_dict()))


class LegacyConverter:
    """Transforma rutinele vechi (pe coordonate) in pasi noi, unde se poate."""

    @staticmethod
    def convert(name: str, steps: Iterable[Dict[str, Any]], repo: Optional[ObjectRepository] = None) -> Routine:
        routine = Routine(name=name, description="Convertita automat din v3.9")
        for raw in steps:
            s = {k.lower() if "_" in k or k.islower() else _snake(k): v for k, v in dict(raw).items()}
            t = s.get("step_type", "")
            key_combo = (s.get("key_combo") or "").strip()
            text = s.get("text_input") or ""
            skip = bool(s.get("skip", False))
            comment = s.get("comment") or ""

            # pasi de browser cu selector -> obiect in repository + actiune pe obiect
            if repo is not None and t in ("browser_click", "browser_fill", "browser_wait") and key_combo:
                obj = next((o for o in repo.objects if any(l.value == key_combo for l in o.locators)), None)
                if obj is None:
                    obj = repo.add(UiObject(name=s.get("description") or "Web_Element", technology=UiTechnology.Web,
                                            locators=[_selector_to_locator(key_combo)], description="Importat din v3.9"))
                if t == "browser_click":
                    node: RprNode = ActionNode(action=RprAction.Click, target=obj.name)
                elif t == "browser_fill":
                    node = ActionNode(action=RprAction.TypeText, target=obj.name, value=text)
                else:
                    node = WaitNode(mode=WaitMode.UntilTrue,
                                    condition=Condition(kind=ConditionKind.ElementVisible, target=obj.name))
                node.enabled, node.comment = not skip, comment
                routine.steps.append(node)
                continue

            before, after = float(s.get("delay_before") or 0), float(s.get("delay_after") or 0)
            if t == "browser_open":
                node = ActionNode(action=RprAction.OpenBrowser, technology=UiTechnology.Web, value=text)
            elif t == "browser_navigate":
                node = ActionNode(action=RprAction.Navigate, technology=UiTechnology.Web, value=text)
            elif t == "browser_close":
                node = ActionNode(action=RprAction.CloseBrowser, technology=UiTechnology.Web)
            elif t == "DELAY":
                node = WaitNode(seconds=max(after, before))
            elif t == "QUESTION":
                node = QuestionNode(text=s.get("question_text") or "",
                                    buttons=s.get("question_buttons") or "Continua,Opreste,Sari")
            else:
                node = LegacyStepNode(step=dict(raw))
            node.enabled, node.comment = not skip, comment
            if t != "DELAY":
                node.delay_before_ms = int(before * 1000)
                node.delay_after_ms = int(after * 1000)
                if isinstance(node, LegacyStepNode):
                    # intarzierile trec pe nod; motorul vechi nu le mai aplica a doua oara
                    for k in list(node.step):
                        if k.lower() in ("delay_before", "delay_after", "delaybefore", "delayafter"):
                            node.step[k] = 0.0
            routine.steps.append(node)
        return routine


def _snake(name: str) -> str:
    import re
    return re.sub(r"(?<=[a-z0-9])([A-Z])", r"_\1", name).lower()


def _selector_to_locator(selector: str) -> Locator:
    low = selector.lower()
    if selector.startswith("//") or low.startswith("xpath="):
        return Locator(LocatorKind.XPath, selector[6:] if low.startswith("xpath=") else selector, 40)
    if low.startswith("text="):
        return Locator(LocatorKind.Text, selector[5:], 50)
    return Locator(LocatorKind.Css, selector[4:] if low.startswith("css=") else selector, 50)


class Examples:
    """Rutinele exemplu (aceleasi ca in C#), livrate in rpr/exemple si instalate in folderul de lucru."""

    SOURCE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "exemple")

    @classmethod
    def install(cls, repo: ObjectRepository) -> List[Dict[str, str]]:
        """Copiaza exemplele (si fisierele Excel) in %APPDATA%\\...\\exemple, adauga obiectele lor in
        repository si returneaza lista [{name, description, path}]."""
        import shutil
        dest = RprPaths.examples()
        for f in os.listdir(cls.SOURCE):
            if f.lower().endswith(".xlsx") and not os.path.exists(os.path.join(dest, f)):
                shutil.copyfile(os.path.join(cls.SOURCE, f), os.path.join(dest, f))

        # obiectele folosite de exemple (doar cele care lipsesc din repository)
        src_repo = os.path.join(cls.SOURCE, "obiecte_exemple.json")
        if os.path.isfile(src_repo):
            for obj in ObjectRepository.from_dict(_read_json(src_repo)).objects:
                if repo.find(obj.name) is None:
                    repo.objects.append(obj)

        out = []
        for f in sorted(os.listdir(cls.SOURCE)):
            if not f.endswith(".rpr.json"):
                continue
            r = Routine.from_dict(_read_json(os.path.join(cls.SOURCE, f)))
            # variabilele care indica un fisier Excel exemplu primesc calea din folderul de lucru
            for k, v in list(r.variables.items()):
                if v.lower().endswith(".xlsx") and os.path.basename(v) == v:
                    r.variables[k] = os.path.join(dest, v)
            path = os.path.join(dest, f)
            RoutineStore.save(r, path)
            out.append({"name": r.name, "description": r.description, "path": path})
        return out


class ExcelInfo:
    """Ce contine un fisier Excel (pentru Studio: foi, coloane). Nu arunca exceptii."""

    _cache: Dict[tuple, "ExcelInfo"] = {}

    def __init__(self):
        self.sheets: List[str] = []
        self.headers: List[str] = []
        self.data_rows = 0
        self.error: Optional[str] = None

    @classmethod
    def read(cls, path: str, sheet: str, header_row: int) -> "ExcelInfo":
        info = cls()
        path = (path or "").strip().strip('"')
        if not path or "{" in path:
            return info
        if not os.path.isfile(path):
            info.error = f"Fisierul nu exista: {path}"
            return info
        key = (path, os.path.getmtime(path), (sheet or "").lower(), header_row)
        if key in cls._cache:
            return cls._cache[key]
        try:
            from .excel import ExcelTable
            info.sheets = ExcelTable.sheet_names(path)
            with ExcelTable.open(path, sheet, header_row) as t:
                info.headers = t.header_titles
                last = t.last_data_row("")
                info.data_rows = max(0, last - t.first_data_row(0) + 1)
        except Exception as ex:  # noqa: BLE001
            info.error = str(ex)
        if len(cls._cache) > 50:
            cls._cache.clear()
        cls._cache[key] = info
        return info


class RunLogExporter:
    """Logul rularii in Excel (randurile cu erori colorate)."""

    @staticmethod
    def export_xlsx(entries, path: str) -> None:
        import openpyxl
        from openpyxl.styles import Font, PatternFill
        wb = openpyxl.Workbook()
        ws = wb.active
        from .lang import ft, level_label   # v4.8.5: in limba aplicatiei
        ws.title = ft("Log")
        headers = [ft(h) for h in ["Ora", "Nivel", "Rand Excel", "Pas", "Mesaj", "Durata (ms)", "Captura"]]
        for c, h in enumerate(headers, 1):
            cell = ws.cell(row=1, column=c, value=h)
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill(fill_type="solid", start_color="009999", end_color="009999")
        fills = {RprLogLevel.Error: "FFC7CE", RprLogLevel.Warning: "FFEB9C"}
        r = 2
        for e in entries:
            vals = [e.time.strftime("%Y-%m-%d %H:%M:%S"), level_label(e.level), e.excel_row or None, e.node_title,
                    ft(e.message), round(e.duration_ms) if e.duration_ms > 0 else None, e.screenshot]
            for c, v in enumerate(vals, 1):
                ws.cell(row=r, column=c, value=v)
            color = fills.get(e.level)
            if color:
                for c in range(1, len(headers) + 1):
                    ws.cell(row=r, column=c).fill = PatternFill(fill_type="solid", start_color=color, end_color=color)
            r += 1
        for col, width in zip("ABCDEFG", (20, 9, 11, 40, 80, 12, 40)):
            ws.column_dimensions[col].width = width
        ws.freeze_panes = "A2"
        wb.save(path)
