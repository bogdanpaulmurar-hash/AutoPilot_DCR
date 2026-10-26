# -*- coding: utf-8 -*-
# ============================================================
# AutoPilot DC v4.1 — RPR (Python)
# host.py — Legatura motor <-> interfata (log, intrebari, decizii)
# Studio implementeaza RunHost; rularea programata are HeadlessRunHost.
# ============================================================

from __future__ import annotations

import datetime as _dt
import threading
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Dict, List, Optional, Tuple

from .model import ActionNode, RprLogLevel, RprNode


@dataclass
class RunLogEntry:
    level: RprLogLevel
    node_id: str = ""
    node_title: str = ""
    message: str = ""
    excel_row: int = 0          # randul Excel curent (0 = in afara unei bucle Excel)
    duration_ms: float = 0.0
    screenshot: str = ""
    time: _dt.datetime = field(default_factory=_dt.datetime.now)

    def __str__(self) -> str:
        row = f" rand {self.excel_row}" if self.excel_row > 0 else ""
        return f"{self.time:%H:%M:%S} [{self.level}]{row} {self.node_title}: {self.message}"


class ErrorDecision(Enum):
    """Decizia utilizatorului cand un pas esueaza (politica Intreaba)."""
    RETRY = "retry"
    SKIP = "skip"
    SKIP_ROW = "skip_row"
    STOP = "stop"


@dataclass(frozen=True)
class RunAlert:
    """Ceva difera fata de ce asteapta rutina (fereastra de eroare, valoare diferita, eroare SAP...)."""
    title: str
    details: str
    key: str


class AlertDecision(Enum):
    CONTINUE = "continue"
    IGNORE_SIMILAR = "ignore_similar"
    SKIP_ROW = "skip_row"
    STOP = "stop"


class RunGuard:
    """Verificari dependente de sistem (ferestre de eroare, aplicatii blocate) inainte de fiecare actiune."""

    def begin_run(self) -> None:
        pass

    def check_before_action(self, node: ActionNode) -> Optional[RunAlert]:
        return None

    def acknowledge(self) -> None:
        pass


class RunHost:
    """Implementarea implicita = fara utilizator (rulare programata)."""

    def log(self, entry: RunLogEntry) -> None:
        pass

    def node_started(self, node: RprNode) -> None:
        pass

    def node_finished(self, node: RprNode, success: bool) -> None:
        pass

    def row_started(self, row: int, sheet: str) -> None:
        """Inceputul unui rand Excel (ex. video separat pentru fiecare rand)."""

    def row_finished(self, row: int, status: str) -> None:
        """Sfarsitul unui rand Excel, cu statusul scris in fisier (OK / EROARE / SARIT)."""

    def ask(self, title: str, text: str, buttons: List[str]) -> str:
        """Intrebare cu butoane personalizate. Fara utilizator: primul buton."""
        return buttons[0] if buttons else ""

    def ask_on_error(self, node: RprNode, error: str, inside_excel_loop: bool) -> ErrorDecision:
        """Fara utilizator: in Excel sarim randul, altfel oprim."""
        return ErrorDecision.SKIP_ROW if inside_excel_loop else ErrorDecision.STOP

    def ask_alert(self, node: RprNode, alert: RunAlert, inside_excel_loop: bool) -> AlertDecision:
        return AlertDecision.SKIP_ROW if inside_excel_loop else AlertDecision.STOP

    # Executa un pas vechi (coordonate): (dict pas) -> (ok, eroare). None = indisponibil.
    legacy_executor: Optional[Callable[[Dict], Tuple[bool, str]]] = None


class HeadlessRunHost(RunHost):
    """Rulare programata: logheaza (consola / fisier), nu intreaba."""

    def __init__(self, write: Optional[Callable[[str], None]] = None):
        self._write = write or print
        self.entries: List[RunLogEntry] = []
        self._lock = threading.Lock()

    def log(self, entry: RunLogEntry) -> None:
        with self._lock:
            self.entries.append(entry)
        try:
            self._write(str(entry))
        except Exception:
            pass


@dataclass
class RunResult:
    success: bool = False
    cancelled: bool = False
    message: str = ""
    steps_executed: int = 0
    errors: int = 0
    rows_ok: int = 0
    rows_failed: int = 0
    rows_skipped: int = 0
    duration: _dt.timedelta = _dt.timedelta(0)
    final_variables: Dict[str, str] = field(default_factory=dict)
