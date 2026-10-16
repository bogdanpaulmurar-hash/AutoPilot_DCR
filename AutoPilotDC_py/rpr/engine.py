# -*- coding: utf-8 -*-
# ============================================================
# AutoPilot DC v4.1 — RPR (Python)
# engine.py — Motorul care executa rutina (arborele de pasi)
#
#   1. Valideaza ca toate obiectele folosite exista in repository.
#   2. Parcurge pasii; containerele (Daca, Repeta, Pentru fiecare
#      rand, Incearca) isi executa ramurile.
#   3. Pentru fiecare actiune: rezolva {variabilele}, marcheaza
#      elementul pe ecran, executa prin driverul tehnologiei.
#   4. La eroare: reincercare automata, apoi politica pasului
#      (Intreaba / Opreste / Continua / Sari randul).
#   5. Pauza / Pas cu pas / Stop in orice moment.
#   6. Sistemul de preventie: ferestre de eroare, valori diferite,
#      erori SAP -> pauza + intrebare.
#
# Motorul ruleaza pe firul apelantului (Studio il porneste pe un fir separat);
# pause()/resume()/stop()/step_once() se pot apela de pe orice fir.
# ============================================================

from __future__ import annotations

import datetime as _dt
import os
import re
import threading
import time
from dataclasses import dataclass
from decimal import Decimal
from typing import Dict, List, Optional

from .conditions import ConditionEvaluator, try_number
from .drivers.base import ActionRequest, DriverProvider, RprStepException
from .excel import ExcelTable
from .host import AlertDecision, ErrorDecision, RunAlert, RunGuard, RunHost, RunLogEntry, RunResult
from .model import (ActionNode, BreakNode, CellColor, ErrorPolicy, ForEachRowNode, GroupNode, IfNode,
                    LegacyStepNode, LogNode, LoopMode, LoopNode, ObjectRepository, QuestionNode, Routine,
                    RoutineSettings, RprAction, RprLogLevel, RprNode, SetVariableNode, StopNode, TryNode,
                    UiTechnology, VariableOperation, WaitMode, WaitNode, WriteExcelNode, action_info)
from .variables import VariableStore


# ── Semnale interne de control al fluxului ─────────────────────
class _ControlSignal(Exception):
    pass


class _LoopSignal(_ControlSignal):
    def __init__(self, next_iteration: bool):
        super().__init__("continue" if next_iteration else "break")
        self.next = next_iteration


class _SkipRowSignal(_ControlSignal):
    def __init__(self, message: str, is_error: bool):
        super().__init__(message)
        self.is_error = is_error


class _StopSignal(_ControlSignal):
    def __init__(self, message: str, is_error: bool):
        super().__init__(message)
        self.is_error = is_error


class _PropagatedStepError(_ControlSignal):
    """Eroare trimisa catre cel mai apropiat bloc "Incearca"."""


class Cancelled(Exception):
    """Rutina a fost oprita de utilizator."""


@dataclass
class _RowContext:
    table: ExcelTable
    node: ForEachRowNode
    row: int = 0


_SAP_NO_STATUS_CHECK = {RprAction.SapReadStatusBar, RprAction.SapConnect, RprAction.Highlight,
                        RprAction.ReadText, RprAction.ReadValue, RprAction.ReadAttribute,
                        RprAction.SapGridReadCell, RprAction.SapGridRowCount}


def matches_expected(actual: str, expected: str) -> bool:
    """Fara diferente de litere mari/mici si spatii la capete; * = orice text."""
    actual, expected = (actual or "").strip(), (expected or "").strip()
    if "*" not in expected:
        return actual.lower() == expected.lower()
    pattern = "^" + re.escape(expected).replace(r"\*", ".*") + "$"
    return re.match(pattern, actual, re.IGNORECASE | re.DOTALL) is not None


def _shorten(s: str, n: int = 120) -> str:
    return s if len(s) <= n else s[:n] + "…"


def _fmt_num(d: Decimal) -> str:
    """Ca in C#: 5 nu 5.0, 2.5 ramane 2.5."""
    s = format(d.normalize(), "f")
    return s


class RprEngine:
    def __init__(self, repo: ObjectRepository, drivers: DriverProvider, host: RunHost, output_folder: str):
        self._repo, self._drivers, self._host, self._output = repo, drivers, host, output_folder
        self.guard: Optional[RunGuard] = None

        self._routine = Routine()
        self._vars = VariableStore()
        self._rows: List[_RowContext] = []
        self._try_depth = 0
        self._result = RunResult()
        self._ignored_alerts: set = set()

        self._stop = threading.Event()
        self._gate = threading.Event()   # setat = merge; sters = pauza
        self._gate.set()
        self.is_running = False
        self.step_mode = False           # pas cu pas: se opreste inainte de fiecare pas
        self.last_variables: Dict[str, str] = {}
        self._conditions: Optional[ConditionEvaluator] = None

    # =========================================================
    # Control: pauza / reluare / pas / stop (de pe orice fir)
    # =========================================================
    @property
    def is_paused(self) -> bool:
        return self.is_running and not self._gate.is_set()

    def pause(self) -> None:
        self._gate.clear()

    def resume(self) -> None:
        self._gate.set()

    def step_once(self) -> None:
        self._gate.set()

    def stop(self) -> None:
        self._stop.set()
        self._gate.set()

    def _wait_gate(self) -> None:
        while not self._gate.wait(0.1):
            if self._stop.is_set():
                break
        self._check_stop()
        if self.step_mode:
            self._gate.clear()

    def _check_stop(self) -> None:
        if self._stop.is_set():
            raise Cancelled()

    def _sleep_ms(self, ms: float) -> None:
        if ms > 0 and self._stop.wait(ms / 1000.0):
            raise Cancelled()

    # =========================================================
    # run — ruleaza rutina completa
    # =========================================================
    def run(self, routine: Routine, variable_overrides: Optional[Dict[str, str]] = None) -> RunResult:
        if self.is_running:
            raise RuntimeError("O rutina ruleaza deja.")
        self.is_running = True
        self._routine = routine
        self._result = RunResult()
        self._rows = []
        self._try_depth = 0
        self._ignored_alerts = set()
        self._stop.clear()
        self._gate.set()
        if self.step_mode:
            self._gate.clear()
        if routine.settings.guard_enabled and self.guard is not None:
            self.guard.begin_run()
        self._vars = VariableStore()
        self._conditions = ConditionEvaluator(self._repo, self._drivers, self._vars, self._stop)
        t0 = time.monotonic()

        try:
            # 1. Variabile initiale
            for k, v in routine.variables.items():
                self._vars.set(k, v)
            for k, v in (variable_overrides or {}).items():
                self._vars.set(k, v)

            # 2. Validare obiecte
            seen, missing = set(), []
            for n in routine.referenced_objects():
                if n.lower() not in seen:
                    seen.add(n.lower())
                    if self._repo.find(n) is None:
                        missing.append(n)
            if missing:
                self._result.success = False
                self._result.message = ("Obiecte lipsa din Object Repository: " + ", ".join(missing) +
                                        ". Marcheaza-le cu Spy sau corecteaza numele in pasi.")
                self._log(RprLogLevel.Error, None, self._result.message)
                return self._result

            self._log(RprLogLevel.Info, None, f"Start rutina \"{routine.name}\"")

            # 3. Executie
            self._execute_list(routine.steps)

            self._result.success = True
            self._result.message = ("Rutina finalizata cu succes." if self._result.errors == 0
                                    else f"Rutina finalizata cu {self._result.errors} erori (continuate).")
        except _StopSignal as s:
            self._result.success = not s.is_error
            self._result.message = str(s) if str(s).strip() else "Rutina oprita."
        except _LoopSignal:
            self._result.success = True
            self._result.message = "Rutina incheiata (Iesi din bucla in afara unei bucle)."
        except (_SkipRowSignal, _PropagatedStepError) as e:
            self._result.success = False
            self._result.message = str(e)
        except Cancelled:
            self._result.success = False
            self._result.cancelled = True
            self._result.message = "Rutina oprita de utilizator."
        except Exception as ex:  # noqa: BLE001 — orice eroare neasteptata devine mesaj
            self._result.success = False
            self._result.message = f"Eroare interna: {ex}"
        finally:
            # Excel ramas deschis (oprire in mijlocul buclei)
            while self._rows:
                rc = self._rows.pop()
                try:
                    rc.table.save()
                except Exception:
                    pass
                rc.table.close()

            self._result.duration = _dt.timedelta(seconds=time.monotonic() - t0)
            self._result.final_variables = dict(self._vars.all)
            self.last_variables = self._result.final_variables
            r = self._result
            rows = (f", randuri OK: {r.rows_ok}, esuate: {r.rows_failed}, sarite: {r.rows_skipped}"
                    if r.rows_ok + r.rows_failed + r.rows_skipped > 0 else "")
            dur = str(r.duration).split(".")[0]
            self._log(RprLogLevel.Info if r.success else RprLogLevel.Error, None,
                      f"{r.message} Durata: {dur}, pasi: {r.steps_executed}{rows}")
            self.is_running = False
            self._gate.set()
        return self._result

    def run_single(self, routine: Routine, node: RprNode) -> RunResult:
        """"Testeaza pasul" din Studio: un singur pas, fara intrebari, cu variabilele ultimei rulari."""
        s = routine.settings
        temp = Routine(
            name=f"Test: {node.title}",
            repository_path=routine.repository_path,
            variables=dict(routine.variables),
            settings=RoutineSettings(
                default_error_policy=ErrorPolicy.Stop,
                highlight_before_action=s.highlight_before_action,
                highlight_ms=s.highlight_ms,
                default_timeout_ms=s.default_timeout_ms,
                auto_retries=0,
                screenshot_on_error=False,
                do_not_disturb=False,
                guard_enabled=False,
            ),
            steps=[node],
        )
        for k, v in self.last_variables.items():
            temp.variables.setdefault(k, v)
        return self.run(temp)

    # =========================================================
    # Parcurgerea pasilor
    # =========================================================
    def _execute_list(self, nodes: List[RprNode]) -> None:
        for node in list(nodes):  # copie: lista poate fi editata in Studio in timpul rularii
            self._check_stop()
            if not node.enabled:
                continue
            self._wait_gate()
            self._execute_node(node)

    def _execute_node(self, node: RprNode) -> None:
        is_container = node.is_container
        attempt = 0
        while True:
            t0 = time.monotonic()
            try:
                self._host.node_started(node)
                self._sleep_ms(node.delay_before_ms)
                self._execute_core(node)
                self._sleep_ms(node.delay_after_ms)
                if not is_container:
                    self._sleep_ms(self._routine.settings.step_delay_ms)
                self._result.steps_executed += 1
                self._host.node_finished(node, True)
                return
            except (_ControlSignal, Cancelled):
                raise
            except Exception as ex:  # noqa: BLE001
                message = str(ex) if isinstance(ex, RprStepException) else f"{type(ex).__name__}: {ex}"

                # 1. Reincercare automata (doar pasi simpli)
                attempt += 1
                retries = self._routine.settings.auto_retries
                if not is_container and attempt <= retries:
                    self._log(RprLogLevel.Warning, node, f"Esuat ({message}). Reincerc ({attempt}/{retries})...")
                    self._sleep_ms(700)
                    continue

                # 2. Log + captura ecran
                self._result.errors += 1
                shot = self._error_screenshot(node)
                self._log(RprLogLevel.Error, node, message, (time.monotonic() - t0) * 1000, shot)
                self._host.node_finished(node, False)

                # 3. Politica de eroare
                policy = node.on_error
                if policy == ErrorPolicy.Inherit:
                    if self._try_depth > 0:  # in "Incearca" eroarea merge la "La eroare"
                        raise _PropagatedStepError(message)
                    policy = self._routine.settings.default_error_policy

                if policy == ErrorPolicy.Continue:
                    return
                if policy == ErrorPolicy.SkipRow:
                    if self._rows:
                        raise _SkipRowSignal(message, True)
                    raise _StopSignal(message, True)
                if policy == ErrorPolicy.Ask:
                    decision = self._host.ask_on_error(node, message, bool(self._rows))
                    if decision == ErrorDecision.RETRY:
                        attempt = 0
                        self._result.errors -= 1
                        self._log(RprLogLevel.Info, node, "Reincerc la cererea utilizatorului.")
                        continue
                    if decision == ErrorDecision.SKIP:
                        self._log(RprLogLevel.Warning, node, "Pas sarit la cererea utilizatorului.")
                        return
                    if decision == ErrorDecision.SKIP_ROW and self._rows:
                        raise _SkipRowSignal(message, True)
                    raise _StopSignal(message, True)
                raise _StopSignal(message, True)

    def _error_screenshot(self, node: RprNode) -> str:
        if not self._routine.settings.screenshot_on_error or not isinstance(node, ActionNode):
            return ""
        try:
            obj = self._repo.find(node.target)
            tech = obj.technology if obj else node.technology
            folder = os.path.join(self._output, "erori")
            os.makedirs(folder, exist_ok=True)
            name = f"{_dt.datetime.now():%Y%m%d_%H%M%S}_{node.id}"
            return self._drivers.get(tech).capture_error_screenshot(folder, name) or ""
        except Exception:
            return ""

    # =========================================================
    # Executia fiecarui tip de pas
    # =========================================================
    def _execute_core(self, node: RprNode) -> None:
        if isinstance(node, ActionNode):
            self._execute_action(node)
        elif isinstance(node, WaitNode):
            self._execute_wait(node)
        elif isinstance(node, SetVariableNode):
            self._execute_set_variable(node)
        elif isinstance(node, IfNode):
            ok = self._conditions.evaluate(node.condition)
            self._log(RprLogLevel.Info, node, "Adevarat → Atunci" if ok else "Fals → Altfel")
            self._execute_list(node.then if ok else node.else_)
        elif isinstance(node, LoopNode):
            self._execute_loop(node)
        elif isinstance(node, ForEachRowNode):
            self._execute_for_each_row(node)
        elif isinstance(node, WriteExcelNode):
            self._execute_write_excel(node)
        elif isinstance(node, QuestionNode):
            self._execute_question(node)
        elif isinstance(node, TryNode):
            self._execute_try(node)
        elif isinstance(node, GroupNode):
            self._execute_list(node.body)
        elif isinstance(node, LogNode):
            self._log(node.level, node, self._vars.resolve(node.message))
        elif isinstance(node, BreakNode):
            raise _LoopSignal(node.next_iteration)
        elif isinstance(node, StopNode):
            msg = self._vars.resolve(node.message) if node.message.strip() else "Rutina oprita de pasul Stop."
            raise _StopSignal(msg, node.as_error)
        elif isinstance(node, LegacyStepNode):
            self._execute_legacy(node)
        else:
            raise RprStepException(f"Tip de pas necunoscut: {type(node).__name__}")

    # ── Actiune ────────────────────────────────────────────────
    def _execute_action(self, a: ActionNode) -> None:
        info = action_info(a.action)

        # 1. Obiectul tinta
        obj = None
        if a.target.strip():
            obj = self._repo.find(a.target)
            if obj is None:
                raise RprStepException(f"Obiectul [{a.target}] nu exista in Object Repository.")
            self._repo.link_parents(obj)   # cautare in containerul obiectului (biblioteca)
        elif info.needs_target:
            raise RprStepException(f"Pasul \"{info.label}\" are nevoie de un obiect. Alege-l in proprietatile pasului.")

        driver = self._drivers.get(obj.technology if obj else a.technology)

        # 2. Variabile in valoare
        unknown: List[str] = []
        value = self._vars.resolve(a.value, unknown)
        if unknown:
            self._log(RprLogLevel.Warning, a, "Variabile necunoscute: " + ", ".join("{" + u + "}" for u in unknown))

        timeout = a.timeout_ms if a.timeout_ms > 0 else self._routine.settings.default_timeout_ms

        # v4.1: ferestre de eroare / aplicatie blocata -> pauza + intrebare
        if self._routine.settings.guard_enabled and self.guard is not None:
            self._handle_alert(a, self.guard.check_before_action(a))

        # Biblioteca: obiectul e definit pentru pagina curenta? (doar atentionare, nu oprim)
        if obj is not None and hasattr(driver, "current_url"):
            url = driver.current_url()
            if url and not self._repo.valid_on(obj, url):
                self._log(RprLogLevel.Warning, a, f"[{obj.name}] e definit pentru site-ul \"{obj.site}\", "
                                                  f"dar pagina curenta e {url}. Verifica daca e pagina corecta.")

        # 3. Marcare pe ecran inainte de actiune (stil SilkTest)
        if obj is not None and (self._routine.settings.highlight_before_action or a.action == RprAction.Highlight):
            ms = max(150, self._routine.settings.highlight_ms)
            driver.highlight(obj, ms, self._stop)
            self._sleep_ms(ms)
            if a.action == RprAction.Highlight:
                self._log(RprLogLevel.Info, a, "Marcat.")
                return

        # 4. Executie
        shots = os.path.join(self._output, "capturi")
        output = driver.execute(ActionRequest(a.action, obj, value, timeout, a.direct_mode, shots), self._stop)

        # 5. Rezultat -> variabila
        if info.produces_output and a.output_variable.strip():
            self._vars.set(a.output_variable, output or "")
        self._log(RprLogLevel.Info, a, f"OK → \"{_shorten(output)}\"" if output is not None else "OK")

        # v4.1: valoarea citita difera de cea asteptata?
        if info.produces_output and a.expected_value.strip():
            expected = self._vars.resolve(a.expected_value)
            if not matches_expected(output or "", expected):
                msg = f"Valoare diferita: asteptat \"{_shorten(expected)}\", citit \"{_shorten(output or '')}\"."
                if self._try_depth > 0:  # in "Incearca" rutina trateaza singura
                    raise RprStepException(msg)
                self._handle_alert(a, RunAlert("Valoarea citita difera de cea asteptata",
                                               msg + "\n\nVerifica ecranul. Continua = merg mai departe cu valoarea citita.",
                                               "value:" + a.id))

        # v4.1: SAP a raportat o eroare in bara de stare?
        if (self._routine.settings.guard_enabled and self._try_depth == 0
                and driver.technology == UiTechnology.Sap and a.action not in _SAP_NO_STATUS_CHECK):
            status = ""
            try:
                status = driver.execute(ActionRequest(RprAction.SapReadStatusBar, None, "", 3000, False, shots),
                                        self._stop) or ""
            except RprStepException:
                pass  # bara de stare indisponibila: nu blocam rutina
            if status.startswith("E:") or status.startswith("A:"):
                self._handle_alert(a, RunAlert("SAP a raportat o eroare",
                                               f"Bara de stare SAP: {status}\n\nRezolva in SAP (sau verifica datele), "
                                               "apoi apasa Continua.", "sap:" + status))

    # ── v4.1: Alerte (sistemul de preventie) ───────────────────
    def _handle_alert(self, node: RprNode, alert: Optional[RunAlert]) -> None:
        if alert is None or alert.key in self._ignored_alerts:
            return
        self._log(RprLogLevel.Warning, node, f"⚠ {alert.title}: {alert.details.splitlines()[0]}")
        decision = self._host.ask_alert(node, alert, bool(self._rows))
        if self.guard is not None:
            self.guard.acknowledge()
        self._log(RprLogLevel.Info, node, {
            AlertDecision.CONTINUE: "Continui la cererea utilizatorului.",
            AlertDecision.IGNORE_SIMILAR: "Continui; nu mai intreb pentru aceasta situatie in rularea curenta.",
            AlertDecision.SKIP_ROW: "Sar randul Excel la cererea utilizatorului.",
        }.get(decision, "Oprit la cererea utilizatorului."))
        self._check_stop()
        if decision == AlertDecision.CONTINUE:
            return
        if decision == AlertDecision.IGNORE_SIMILAR:
            self._ignored_alerts.add(alert.key)
            return
        if decision == AlertDecision.SKIP_ROW and self._rows:
            raise _SkipRowSignal(alert.title, True)
        raise _StopSignal(alert.title, True)

    # ── Asteptare ──────────────────────────────────────────────
    def _execute_wait(self, w: WaitNode) -> None:
        if w.mode == WaitMode.Seconds:
            self._sleep_ms(max(0.0, float(w.seconds)) * 1000)
            return
        deadline = time.monotonic() + max(0, w.timeout_ms) / 1000.0
        while True:
            if self._conditions.evaluate(w.condition):
                self._log(RprLogLevel.Info, w, "Conditie indeplinita.")
                return
            if time.monotonic() >= deadline:
                msg = (f"Conditia \"{w.condition.describe()}\" nu s-a indeplinit in "
                       f"{w.timeout_ms / 1000.0:.1f} s.")
                if w.fail_on_timeout:
                    raise RprStepException(msg)
                self._log(RprLogLevel.Warning, w, msg + " Continui.")
                return
            self._sleep_ms(300)

    # ── Variabile ──────────────────────────────────────────────
    def _execute_set_variable(self, s: SetVariableNode) -> None:
        current = self._vars.get(s.name)
        value = self._vars.resolve(s.value)
        op = s.operation

        def number_or(text: str, fallback: Decimal) -> Decimal:
            ok, d = try_number(text)
            return d if ok else fallback

        def add(delta: Decimal) -> str:
            _, n = try_number(current)
            return _fmt_num(n + delta)

        if op == VariableOperation.Set:
            result = value
        elif op == VariableOperation.Append:
            result = current + value
        elif op == VariableOperation.Increment:
            result = add(Decimal(1) if not value.strip() else number_or(value, Decimal(1)))
        elif op == VariableOperation.Decrement:
            result = add(-(Decimal(1) if not value.strip() else number_or(value, Decimal(1))))
        elif op == VariableOperation.Trim:
            result = current.strip()
        elif op == VariableOperation.ToUpper:
            result = current.upper()
        elif op == VariableOperation.ToLower:
            result = current.lower()
        elif op == VariableOperation.Replace:
            result = current if not s.find else current.replace(self._vars.resolve(s.find), value)
        else:
            result = value
        self._vars.set(s.name, result)
        self._log(RprLogLevel.Info, s, f"{{{s.name}}} = \"{_shorten(result)}\"")

    # ── Repeta ─────────────────────────────────────────────────
    def _execute_loop(self, l: LoopNode) -> None:
        if l.mode == LoopMode.Times:
            text = self._vars.resolve(l.count).strip()
            if not re.fullmatch(r"[+-]?\d+", text):
                raise RprStepException(f"Numarul de repetari \"{l.count}\" nu e un numar intreg.")
            maximum = int(text)
        else:
            maximum = max(1, l.max_iterations)

        for it in range(1, maximum + 1):
            self._check_stop()
            if l.mode == LoopMode.While and not self._conditions.evaluate(l.condition):
                return
            if l.counter_variable.strip():
                self._vars.set(l.counter_variable, str(it))
            try:
                self._execute_list(l.body)
            except _LoopSignal as s:
                if not s.next:
                    return
            if l.mode == LoopMode.Until and self._conditions.evaluate(l.condition):
                return

        if l.mode != LoopMode.Times:
            self._log(RprLogLevel.Warning, l, f"S-a atins limita de {maximum} repetari (protectie bucla infinita).")

    # ── Pentru fiecare rand Excel ──────────────────────────────
    def _execute_for_each_row(self, f: ForEachRowNode) -> None:
        path = self._vars.resolve(f.file_path).strip().strip('"')
        table = ExcelTable.open(path, self._vars.resolve(f.sheet), f.header_row)
        ctx = _RowContext(table, f)
        self._rows.append(ctx)
        try:
            first = table.first_data_row(f.start_row)
            last = f.end_row if f.end_row > 0 else table.last_data_row(f.key_column)
            self._log(RprLogLevel.Info, f, f"Excel {os.path.basename(path)} / {table.sheet_name}: randurile {first}-{last}")

            for row in range(first, last + 1):
                self._check_stop()
                ctx.row = row

                # 1. rand gol = sfarsitul datelor (daca nu s-a dat end_row)
                if table.is_row_empty(row, f.key_column):
                    if f.end_row <= 0:
                        break
                    continue

                # 2. reluare: sarim randurile deja OK
                has_status = bool(f.status_column.strip())
                if has_status and f.skip_completed_rows and table.get_cell(row, f.status_column).upper().startswith("OK"):
                    self._result.rows_skipped += 1
                    continue

                table.load_row_into(self._vars, f.row_variable, row)
                self._log(RprLogLevel.Info, f, f"Rand {row}")

                # 3. pasii pentru rand
                stop_loop, rethrow = False, None
                try:
                    self._execute_list(f.body)
                    status, color = "OK", CellColor.Green
                    self._result.rows_ok += 1
                except _SkipRowSignal as s:
                    status = f"EROARE: {s}" if s.is_error else f"SARIT: {s}"
                    color = CellColor.Red if s.is_error else CellColor.Yellow
                    if s.is_error:
                        self._result.rows_failed += 1
                    else:
                        self._result.rows_skipped += 1
                except _LoopSignal as s:
                    status, color = "OK", CellColor.Green
                    self._result.rows_ok += 1
                    stop_loop = not s.next
                except _StopSignal as s:
                    status = f"EROARE: {s}" if s.is_error else f"OPRIT: {s}"
                    color = CellColor.Red if s.is_error else CellColor.Yellow
                    if s.is_error:
                        self._result.rows_failed += 1
                    rethrow = s
                except _PropagatedStepError as e:
                    status, color = f"EROARE: {e}", CellColor.Red
                    self._result.rows_failed += 1
                    rethrow = e
                except Cancelled:
                    if has_status:
                        table.write(row, f.status_column, f"OPRIT {_dt.datetime.now():%H:%M:%S}", CellColor.Yellow)
                    raise

                # 4. status + culoare + salvare
                if has_status:
                    table.write(row, f.status_column, _shorten(status, 250), color)
                if f.color_rows and color == CellColor.Red:
                    table.color_row(row, CellColor.Red)
                if f.save_after_each_row:
                    table.save()
                if rethrow is not None:
                    raise rethrow
                if stop_loop:
                    break
        finally:
            if self._rows and self._rows[-1] is ctx:
                self._rows.pop()
            try:
                table.save()
            except Exception as ex:  # noqa: BLE001
                self._log(RprLogLevel.Error, f, str(ex))
            table.close()
            self._vars.remove_prefix(f.row_variable + ".")

    # ── Scrie in Excel ─────────────────────────────────────────
    def _execute_write_excel(self, w: WriteExcelNode) -> None:
        if not self._rows:
            raise RprStepException("\"Scrie in Excel\" trebuie pus in interiorul unui bloc \"Pentru fiecare rand Excel\".")
        ctx = self._rows[-1]
        value = self._vars.resolve(w.value)
        ctx.table.write(ctx.row, self._vars.resolve(w.column), value, w.color)
        self._log(RprLogLevel.Info, w, f"Rand {ctx.row}, [{w.column}] = \"{_shorten(value)}\"")

    # ── Intrebare ──────────────────────────────────────────────
    def _execute_question(self, q: QuestionNode) -> None:
        buttons = [b.strip() for b in q.buttons.split(",") if b.strip()] or ["OK"]
        answer = self._host.ask(self._routine.name, self._vars.resolve(q.text), buttons)
        self._check_stop()
        if q.output_variable.strip():
            self._vars.set(q.output_variable, answer)
        self._log(RprLogLevel.Info, q, f"Raspuns: {answer}")
        if q.stop_button.strip() and answer.lower() == q.stop_button.lower():
            raise _StopSignal("Oprit de utilizator.", False)
        if q.skip_button.strip() and answer.lower() == q.skip_button.lower() and self._rows:
            raise _SkipRowSignal("sarit de utilizator", False)

    # ── Incearca / La eroare ───────────────────────────────────
    def _execute_try(self, t: TryNode) -> None:
        error = None
        self._try_depth += 1
        try:
            self._execute_list(t.body)
        except _PropagatedStepError as e:
            error = str(e)
        finally:
            self._try_depth -= 1
        if error is not None:
            if t.error_variable.strip():
                self._vars.set(t.error_variable, error)
            self._log(RprLogLevel.Warning, t, "Eroare prinsa → ramura \"La eroare\"")
            self._execute_list(t.catch)

    # ── Pas vechi (coordonate) ─────────────────────────────────
    def _execute_legacy(self, ls: LegacyStepNode) -> None:
        execu = self._host.legacy_executor
        if execu is None:
            raise RprStepException("Pasii vechi (coordonate) nu pot rula in acest mod.")
        ok, err = execu(ls.step)
        if not ok:
            raise RprStepException(err or "Pasul vechi a esuat.")
        self._log(RprLogLevel.Info, ls, "OK")

    # =========================================================
    # Utilitare
    # =========================================================
    def _log(self, level: RprLogLevel, node: Optional[RprNode], message: str,
             duration_ms: float = 0.0, screenshot: str = "") -> None:
        self._host.log(RunLogEntry(
            level=level,
            node_id=node.id if node else "",
            node_title=node.title if node else self._routine.name,
            message=message,
            excel_row=self._rows[-1].row if self._rows else 0,
            duration_ms=duration_ms,
            screenshot=screenshot,
        ))
