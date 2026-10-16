# -*- coding: utf-8 -*-
# ============================================================
# AutoPilot DC — RPR (Python)
# schedule.py — Programarea rutinelor in Windows Task Scheduler (fara drepturi de administrator)
#
#  - Sarcina se creeaza din XML (fara probleme cu formatul datei din setarile regionale).
#  - Ruleaza "pythonw -m rpr run <rutina> --anunta" doar cand utilizatorul e autentificat
#    (rutinele folosesc ecranul), fara fereastra CMD; la final apare un mesaj scurt cu rezultatul.
#  - Toate programarile stau in folderul "AutoPilotDC" din Task Scheduler
#    (sau "AutoPilotDC - <nume>" in radacina, daca folderul nu poate fi creat).
# ============================================================

from __future__ import annotations

import csv
import datetime as _dt
import io
import json
import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from typing import Iterable, List, Optional, Tuple
from xml.sax.saxutils import escape

from .model import sanitize_name
from .storage import RprPaths

FOLDER = "AutoPilotDC"
ROOT_PREFIX = "AutoPilotDC - "
APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_NO_WINDOW = 0x08000000

KINDS = ["Zilnic", "In zilele lucratoare (L-V)", "In anumite zile", "O singura data", "Repetat (la fiecare N minute)",
         "La autentificarea in Windows"]
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
DAY_LABELS = ["Lu", "Ma", "Mi", "Jo", "Vi", "Sa", "Du"]


@dataclass
class TaskInfo:
    name: str          # numele complet din Task Scheduler (\AutoPilotDC\Raport)
    short: str         # numele afisat
    next_run: str
    status: str
    last_run: str
    last_result: str
    command: str


def pythonw() -> str:
    """pythonw.exe langa interpretorul curent (fara fereastra CMD)."""
    exe = sys.executable
    cand = os.path.join(os.path.dirname(exe), "pythonw.exe")
    return cand if os.path.exists(cand) else exe


def _run(args: List[str]) -> Tuple[int, str]:
    p = subprocess.run(["schtasks.exe"] + args, capture_output=True, creationflags=_NO_WINDOW)
    out = (p.stdout or b"") + (p.stderr or b"")
    for enc in ("oem", "mbcs", "utf-8"):
        try:
            return p.returncode, out.decode(enc).strip()
        except (LookupError, UnicodeDecodeError):
            continue
    return p.returncode, out.decode("latin-1", "replace").strip()


def build_xml(routine_path: str, routine_name: str, kind: int, at: _dt.datetime,
              days: Iterable[int] = (), every_minutes: int = 60) -> str:
    """XML-ul sarcinii. kind = index in KINDS; at = data + ora de start; days = indexi 0..6 (Lu..Du)."""
    start = at.strftime("%Y-%m-%dT%H:%M:00")
    if kind == 0:
        trig = f"<CalendarTrigger><StartBoundary>{start}</StartBoundary><Enabled>true</Enabled>" \
               "<ScheduleByDay><DaysInterval>1</DaysInterval></ScheduleByDay></CalendarTrigger>"
    elif kind in (1, 2):
        sel = range(5) if kind == 1 else sorted(set(days))
        if not sel:
            raise ValueError("Alege cel putin o zi.")
        d = "".join(f"<{DAYS[i]} />" for i in sel)
        trig = f"<CalendarTrigger><StartBoundary>{start}</StartBoundary><Enabled>true</Enabled>" \
               f"<ScheduleByWeek><DaysOfWeek>{d}</DaysOfWeek><WeeksInterval>1</WeeksInterval></ScheduleByWeek></CalendarTrigger>"
    elif kind == 3:
        trig = f"<TimeTrigger><StartBoundary>{start}</StartBoundary><Enabled>true</Enabled></TimeTrigger>"
    elif kind == 4:
        if every_minutes < 1:
            raise ValueError("Intervalul trebuie sa fie de cel putin 1 minut.")
        trig = f"<TimeTrigger><Repetition><Interval>PT{int(every_minutes)}M</Interval><StopAtDurationEnd>false</StopAtDurationEnd>" \
               f"</Repetition><StartBoundary>{start}</StartBoundary><Enabled>true</Enabled></TimeTrigger>"
    elif kind == 5:
        trig = "<LogonTrigger><Enabled>true</Enabled><Delay>PT1M</Delay></LogonTrigger>"
    else:
        raise ValueError("Tip de programare necunoscut.")
    args = f'-m rpr run "{routine_path}" --anunta'
    desc = f"AutoPilot DC: rutina \"{routine_name}\" ({routine_path})"
    return f"""<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo><Author>AutoPilot DC</Author><Description>{escape(desc)}</Description></RegistrationInfo>
  <Triggers>{trig}</Triggers>
  <Principals><Principal id="Author"><LogonType>InteractiveToken</LogonType><RunLevel>LeastPrivilege</RunLevel></Principal></Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <StartWhenAvailable>true</StartWhenAvailable>
    <ExecutionTimeLimit>PT8H</ExecutionTimeLimit>
    <Enabled>true</Enabled>
  </Settings>
  <Actions Context="Author">
    <Exec><Command>{escape(pythonw())}</Command><Arguments>{escape(args)}</Arguments><WorkingDirectory>{escape(APP_DIR)}</WorkingDirectory></Exec>
  </Actions>
</Task>
"""


def create(routine_path: str, routine_name: str, kind: int, at: _dt.datetime, days: Iterable[int] = (),
           every_minutes: int = 60, task_name: str = "") -> Tuple[bool, str, str]:
    """Creeaza (sau inlocuieste) programarea. Returneaza (reusit, mesaj, numele sarcinii)."""
    xml = build_xml(routine_path, routine_name, kind, at, days, every_minutes)
    fd, tmp = tempfile.mkstemp(suffix=".xml", prefix="apdc_task_")
    os.close(fd)
    try:
        with open(tmp, "w", encoding="utf-16") as f:
            f.write(xml)
        short = sanitize_name(task_name or routine_name) or "Rutina"
        name = f"\\{FOLDER}\\{short}"
        code, out = _run(["/Create", "/F", "/XML", tmp, "/TN", name])
        if code != 0:   # folderul nu poate fi creat fara drepturi: radacina, cu prefix
            name = ROOT_PREFIX + short
            code, out = _run(["/Create", "/F", "/XML", tmp, "/TN", name])
        return code == 0, out, name
    finally:
        try:
            os.remove(tmp)
        except OSError:
            pass


def list_tasks() -> List[TaskInfo]:
    code, out = _run(["/Query", "/FO", "CSV", "/V"])
    if code != 0:
        return []
    tasks, seen = [], set()
    for row in csv.reader(io.StringIO(out)):
        if len(row) < 9:
            continue
        name = row[1]
        short = ""
        if name.lower().startswith(f"\\{FOLDER.lower()}\\"):
            short = name[len(FOLDER) + 2:]
        elif name.lstrip("\\").startswith(ROOT_PREFIX):
            short = name.lstrip("\\")[len(ROOT_PREFIX):]
        if not short or name in seen:   # /V repeta randul pentru fiecare declansator
            continue
        seen.add(name)
        result = row[6]
        tasks.append(TaskInfo(name, short, row[2], row[3], row[5], describe_result(result), row[8]))
    return tasks


def describe_result(code: str) -> str:
    known = {"0": "succes", "1": "rutina a esuat", "2": "fisier invalid", "267011": "nu a rulat inca",
             "267009": "ruleaza acum", "267014": "oprita", "-2147020576": "utilizatorul nu era autentificat"}
    return f"{code} ({known[code]})" if code in known else code


def delete(name: str) -> Tuple[bool, str]:
    code, out = _run(["/Delete", "/F", "/TN", name])
    return code == 0, out


def run_now(name: str) -> Tuple[bool, str]:
    code, out = _run(["/Run", "/TN", name])
    return code == 0, out


def open_task_scheduler():
    os.startfile("taskschd.msc")   # noqa: S606


# ── Istoric (scris de "py -m rpr run ... --anunta") ──
def history_path() -> str:
    return os.path.join(RprPaths.root, "programari_istoric.json")


def add_history(routine: str, path: str, success: bool, message: str, log: str, started: _dt.datetime) -> None:
    items = load_history()
    items.insert(0, {"rutina": routine, "fisier": path, "succes": success, "mesaj": message[:300], "log": log,
                     "pornita": started.strftime("%Y-%m-%d %H:%M:%S"),
                     "durata_s": round((_dt.datetime.now() - started).total_seconds())})
    try:
        os.makedirs(RprPaths.root, exist_ok=True)
        with open(history_path(), "w", encoding="utf-8") as f:
            json.dump(items[:200], f, ensure_ascii=False, indent=1)
    except OSError:
        pass


def load_history() -> List[dict]:
    try:
        with open(history_path(), encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except (OSError, ValueError):
        return []
