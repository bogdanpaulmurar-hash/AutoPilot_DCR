# -*- coding: utf-8 -*-
# ============================================================
# AutoPilot DC v4.1 — RPR (Python)
# excel.py — Excel ca sursa de date pentru "Pentru fiecare rand"
# Citeste randuri dupa titlul coloanei, scrie rezultate inapoi,
# coloreaza randurile, creeaza coloane noi la nevoie.
#
# Formulele raman intacte: fisierul e deschis de doua ori —
#   _wb   (cu formule)  -> aici se scrie si se salveaza
#   _vals (data_only)   -> de aici se citesc valorile calculate
# ============================================================

from __future__ import annotations

import datetime as _dt
import os
import re
from typing import Dict, List, Optional, Tuple

from .drivers.base import RprStepException
from .model import CellColor
from .variables import VariableStore

try:
    import openpyxl
    from openpyxl.styles import Font, PatternFill
    from openpyxl.utils import column_index_from_string, get_column_letter
except ImportError:  # mesaj clar la folosire, nu la import
    openpyxl = None

_FILLS = {
    CellColor.Green: "C6EFCE",
    CellColor.Red: "FFC7CE",
    CellColor.Yellow: "FFEB9C",
    CellColor.Orange: "F8CBAD",
    CellColor.Blue: "BDD7EE",
}


# v4.23: coloana cheie se gaseste si sub alt nume (fisierul are "UEID", rutina cere "Id").
# Se folosesc doar daca titlul exact nu exista; spatiile, "_", "-", "." si literele mari nu conteaza.
ID_ALIASES = ("id", "ueid", "cod", "code", "nr", "numar", "number", "nummer", "cheie", "key", "schluessel")


def _compact(title: str) -> str:
    return re.sub(r"[\s_.\-]+", "", (title or "").strip().lower())


def _require_openpyxl():
    if openpyxl is None:
        raise RprStepException("Lipseste pachetul openpyxl. Ruleaza INSTALEAZA.bat din folderul aplicatiei.")


def format_cell(v) -> str:
    """Valoarea celulei ca text (aproape de ce vezi in Excel)."""
    if v is None:
        return ""
    if isinstance(v, bool):
        return "TRUE" if v else "FALSE"
    if isinstance(v, float):
        return str(int(v)) if v.is_integer() else repr(v)
    if isinstance(v, _dt.datetime):
        return v.strftime("%d.%m.%Y") if v.time() == _dt.time(0) else v.strftime("%d.%m.%Y %H:%M:%S")
    if isinstance(v, _dt.date):
        return v.strftime("%d.%m.%Y")
    if isinstance(v, _dt.time):
        return v.strftime("%H:%M:%S")
    return str(v)


class ExcelTable:
    def __init__(self, path: str, wb, vals, ws, ws_vals, header_row: int):
        self.file_path = path
        self._wb, self._vals, self._ws, self._wsv = wb, vals, ws, ws_vals
        self.header_row = max(0, header_row)
        self._written: Dict[Tuple[int, int], str] = {}   # celule scrise in aceasta rulare
        self.headers: Dict[str, int] = {}                 # titlu (lower) -> coloana
        self._titles: Dict[str, str] = {}                 # titlu (lower) -> titlul original
        self._load_headers()

    # ── 1. Deschidere cu mesaje clare ────────────────────────
    @classmethod
    def open(cls, path: str, sheet: Optional[str], header_row: int) -> "ExcelTable":
        _require_openpyxl()
        if not path or not path.strip():
            raise RprStepException("Nu ai ales fisierul Excel.")
        if not os.path.isfile(path):
            raise RprStepException(f"Fisierul Excel nu exista: {path}")
        try:
            wb = openpyxl.load_workbook(path)
            vals = openpyxl.load_workbook(path, data_only=True)
        except PermissionError as ex:
            raise RprStepException(f"Fisierul {os.path.basename(path)} e blocat (probabil deschis in Excel). "
                                   f"Inchide-l si porneste din nou. ({ex})")
        except Exception as ex:
            raise RprStepException(f"Nu pot deschide {os.path.basename(path)}: {ex}")

        if not sheet or not sheet.strip():
            name = wb.sheetnames[0]
        else:
            name = next((n for n in wb.sheetnames if n.lower() == sheet.strip().lower()), None)
            if name is None:
                raise RprStepException(f"Foaia \"{sheet}\" nu exista. Foi disponibile: {', '.join(wb.sheetnames)}")
        return cls(path, wb, vals, wb[name], vals[name], header_row)

    @staticmethod
    def sheet_names(path: str) -> List[str]:
        _require_openpyxl()
        wb = openpyxl.load_workbook(path, read_only=True)
        try:
            return list(wb.sheetnames)
        finally:
            wb.close()

    @property
    def sheet_name(self) -> str:
        return self._ws.title

    def _load_headers(self) -> None:
        self.headers.clear()
        self._titles.clear()
        if self.header_row <= 0:
            return
        for col in range(1, self._ws.max_column + 1):
            title = self._text(self.header_row, col).strip()
            if title and title.lower() not in self.headers:
                self.headers[title.lower()] = col
                self._titles[title.lower()] = title

    @property
    def max_row(self) -> int:
        return self._ws.max_row

    @property
    def header_titles(self) -> List[str]:
        return [self._titles[k] for k in sorted(self.headers, key=self.headers.get)]

    # ── 2. Coloana: titlu ("IBase") sau litera ("C") ─────────
    def resolve_column(self, column: str, key: bool = False) -> Optional[int]:
        """key=True doar pentru coloana cheie: atunci "Id" gaseste si "UEID" / "Cod" / "Nr".
        La scriere nu: "Cod" citit din SAP nu are voie sa ajunga peste coloana cu Id-ul."""
        if not column or not column.strip():
            return None
        column = column.strip()
        if column.lower() in self.headers:
            return self.headers[column.lower()]
        wanted = _compact(column)
        for title, col in self.headers.items():   # "Pret nou" = "pret_nou" = "PretNou"
            if _compact(title) == wanted:
                return col
        if key and wanted in ID_ALIASES:                # cheia: "Id" gaseste "UEID", "Cod", "Nr"... (prima din stanga)
            for k in sorted(self.headers, key=self.headers.get):
                if _compact(k) in ID_ALIASES:
                    return self.headers[k]
        if re.fullmatch(r"[A-Za-z]{1,3}", column):
            return column_index_from_string(column.upper())
        return None

    def title_of(self, column: str) -> str:
        """Titlul real din fisier pentru o coloana ceruta (ex. "Id" -> "UEID"); "" = nu exista."""
        col = self.resolve_column(column, key=True)
        if col is None:
            return ""
        for key, c in self.headers.items():
            if c == col:
                return self._titles[key]
        return ""

    def key_problems(self, key_column: str, first: int, last: int) -> Tuple[List[int], Dict[str, List[int]]]:
        """Verificarea dinaintea rularii: (randuri cu date dar fara cheie, {cheie: randuri} pentru duplicate)."""
        col = self.resolve_column(key_column, key=True)
        if col is None:
            return [], {}
        missing: List[int] = []
        seen: Dict[str, List[int]] = {}
        for r in range(first, max(first, last) + 1):
            key = self._text(r, col).strip()
            if key:
                seen.setdefault(key.lower(), []).append(r)
            elif not self._row_empty(r):
                missing.append(r)
        dup = {self._text(rows[0], col).strip(): rows for rows in seen.values() if len(rows) > 1}
        return missing, dup

    def get_or_create_column(self, column: str) -> int:
        existing = self.resolve_column(column)
        if existing is not None:
            return existing
        if self.header_row <= 0:
            raise RprStepException(f"Coloana \"{column}\" nu exista. Fara rand de titluri foloseste litere (A, B, C...).")
        new_col = max([0] + list(self.headers.values()) + [self._last_col_in_row(self.header_row)]) + 1
        cell = self._ws.cell(row=self.header_row, column=new_col, value=column.strip())
        cell.font = Font(bold=True)
        self._written[(self.header_row, new_col)] = column.strip()
        self.headers[column.strip().lower()] = new_col
        self._titles[column.strip().lower()] = column.strip()
        return new_col

    def first_data_row(self, start_row: int) -> int:
        return start_row if start_row > 0 else self.header_row + 1

    def last_data_row(self, key_column: str) -> int:
        col = self.resolve_column(key_column, key=True)
        if col is not None:
            for r in range(self._ws.max_row, 0, -1):
                if self._text(r, col).strip():
                    return r
            return 0
        for r in range(self._ws.max_row, 0, -1):
            if not self._row_empty(r):
                return r
        return 0

    def is_row_empty(self, row: int, key_column: str) -> bool:
        col = self.resolve_column(key_column, key=True)
        if col is not None:
            return not self._text(row, col).strip()
        return self._row_empty(row)

    # ── 3. Citire rand -> {Prefix.Titlu}, {Prefix.A}, {Prefix.#} ─
    def load_row_into(self, variables: VariableStore, prefix: str, row: int, key_column: str = "") -> None:
        variables.remove_prefix(prefix + ".")
        variables.set(f"{prefix}.#", str(row))
        last = max([self._last_col_in_row(row)] + list(self.headers.values()) + [0])
        for col in range(1, last + 1):
            variables.set(f"{prefix}.{get_column_letter(col)}", self._text(row, col))
        for key, col in self.headers.items():
            variables.set(f"{prefix}.{self._titles[key]}", self._text(row, col))
        # v4.23: rutina scrie {Rand.Id}, fisierul are "UEID" -> {Rand.Id} exista si el
        name = (key_column or "").strip()
        is_letter = re.fullmatch(r"[A-Za-z]{1,3}", name) and _compact(name) not in ID_ALIASES   # "Id" e titlu, nu litera
        if name and not is_letter and name.lower() not in self.headers:
            col = self.resolve_column(name, key=True)
            if col is not None:
                variables.set(f"{prefix}.{name}", self._text(row, col))

    def get_key(self, row: int, key_column: str) -> str:
        col = self.resolve_column(key_column, key=True)
        return self._text(row, col) if col is not None else ""

    def get_cell(self, row: int, column: str) -> str:
        col = self.resolve_column(column)
        return self._text(row, col) if col is not None else ""

    # ── 4. Scriere + culori ──────────────────────────────────
    def write(self, row: int, column: str, value: str, color: CellColor = CellColor.None_) -> None:
        col = self.get_or_create_column(column)
        cell = self._ws.cell(row=row, column=col, value=value)
        self._written[(row, col)] = "" if value is None else str(value)
        color = CellColor.parse(color)
        if color != CellColor.None_:
            cell.fill = PatternFill(fill_type="solid", start_color=_FILLS[color], end_color=_FILLS[color])

    def write_link(self, row: int, column: str, text: str, target: str) -> None:
        """Text cu link spre un fisier (ex. filmul randului)."""
        col = self.get_or_create_column(column)
        cell = self._ws.cell(row=row, column=col, value=text)
        cell.hyperlink = "file:///" + os.path.abspath(target).replace("\\", "/")
        cell.font = Font(color="0563C1", underline="single")
        self._written[(row, col)] = text

    def color_row(self, row: int, color: CellColor) -> None:
        last = max([self._last_col_in_row(row), 1] + list(self.headers.values()))
        color = CellColor.parse(color)
        for col in range(1, last + 1):
            c = self._ws.cell(row=row, column=col)
            c.fill = PatternFill(fill_type=None) if color == CellColor.None_ else \
                PatternFill(fill_type="solid", start_color=_FILLS[color], end_color=_FILLS[color])

    def save(self) -> None:
        try:
            self._wb.save(self.file_path)
        except PermissionError as ex:
            raise RprStepException(f"Nu pot salva {os.path.basename(self.file_path)}: fisierul e deschis in alt "
                                   f"program. Inchide-l in Excel. ({ex})")

    def close(self) -> None:
        for wb in (self._wb, self._vals):
            try:
                wb.close()
            except Exception:
                pass

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    # ── utilitare ────────────────────────────────────────────
    def _text(self, row: int, col: int) -> str:
        if (row, col) in self._written:
            return self._written[(row, col)]
        # citim fara ws.cell(): acela ar crea celule goale si ar mari foaia la salvare
        cv = self._wsv._cells.get((row, col))
        v = cv.value if cv is not None else None
        if v is None:
            # formula fara valoare calculata (fisier creat de un program, nu de Excel) -> gol
            cf = self._ws._cells.get((row, col))
            f = cf.value if cf is not None else None
            v = f if not (isinstance(f, str) and f.startswith("=")) else None
        return format_cell(v)

    def _last_col_in_row(self, row: int) -> int:
        for col in range(self._ws.max_column, 0, -1):
            if self._text(row, col).strip():
                return col
        return 0

    def _row_empty(self, row: int) -> bool:
        return self._last_col_in_row(row) == 0
