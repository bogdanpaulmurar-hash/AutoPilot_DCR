# -*- coding: utf-8 -*-
# ============================================================
# AutoPilot DC v4.1 — RPR (Python)
# Rulare fara interfata (programari Windows / linie de comanda):
#
#   python -m rpr run "C:\...\rutina.rpr.json" [--var Nume=Valoare ...] [--fara-chenar]
#
# Cod de iesire: 0 = succes, 1 = rutina a esuat, 2 = fisier invalid.
# Logul se salveaza in %APPDATA%\AutoPilotDC\Studio\rezultate (txt + xlsx).
# Fara utilizator: intrebarile primesc primul buton, iar erorile sar randul
# Excel curent (sau opresc rutina in afara unei bucle Excel).
# ============================================================

from __future__ import annotations

import argparse
import datetime as _dt
import os
import sys
import threading

from .engine import RprEngine
from .host import HeadlessRunHost
from .legacy import execute_legacy_step
from .storage import RepositoryStore, RoutineStore, RprPaths, RunLogExporter
from .drivers.base import DriverProvider
from .model import sanitize_name


def build_drivers() -> DriverProvider:
    """Driverele disponibile (se completeaza pe masura ce sunt portate)."""
    provider = DriverProvider()
    try:
        from .drivers.registry import register_all  # etapele urmatoare: web / sap / desktop
    except ImportError:
        return provider
    register_all(provider)
    return provider


def _safety():
    """Modulul de siguranta al aplicatiei (Nu deranja, chenar). Optional."""
    try:
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        import autopilot_safety
        return autopilot_safety
    except Exception:
        return None


def run_file(path: str, variables: dict, show_frame: bool = True) -> int:
    stamp = _dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    text_log = os.path.join(RprPaths.output(), f"Log_programat_{stamp}.txt")
    with open(text_log, "w", encoding="utf-8", buffering=1) as writer:
        try:
            repo = RepositoryStore.load(None)
            routine = RoutineStore.load(path, repo)
            if routine.repository_path.strip():
                repo = RepositoryStore.load(routine.repository_path)
        except Exception as ex:  # noqa: BLE001
            writer.write(f"EROARE la citirea rutinei: {ex}\n")
            return 2

        host = HeadlessRunHost(lambda line: writer.write(line + "\n"))
        host.legacy_executor = execute_legacy_step
        drivers = build_drivers()
        engine = RprEngine(repo, drivers, host, RprPaths.output())

        safety = _safety()
        dnd = bool(routine.settings.do_not_disturb and safety)
        if dnd:
            safety.DoNotDisturb.enable()
            writer.write(safety.DoNotDisturb.last_message + "\n")

        result_box = {}

        def work():
            result_box["r"] = engine.run(routine, variables)

        try:
            root = None
            if show_frame and safety is not None:
                try:
                    import tkinter as tk
                    root = tk.Tk()
                    root.withdraw()
                    frame = safety.RunFrame(root)
                    frame.show("run")
                except Exception:
                    root = None
            t = threading.Thread(target=work, daemon=True, name="RprEngine")
            t.start()
            if root is not None:
                def poll():
                    if t.is_alive():
                        root.after(200, poll)
                    else:
                        root.destroy()
                root.after(200, poll)
                root.mainloop()
            t.join()
        finally:
            drivers.close()
            if dnd:
                safety.DoNotDisturb.restore()

        result = result_box.get("r")
        xlsx = os.path.join(RprPaths.output(), f"Log_programat_{sanitize_name(routine.name)}_{stamp}.xlsx")
        try:
            RunLogExporter.export_xlsx(host.entries, xlsx)
        except Exception as ex:  # noqa: BLE001
            writer.write(f"Exportul logului in Excel a esuat: {ex}\n")
        return 0 if result is not None and result.success else 1


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="python -m rpr", description="AutoPilot DC — rulare rutine RPR fara interfata")
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="ruleaza o rutina .rpr.json")
    r.add_argument("file")
    r.add_argument("--var", action="append", default=[], metavar="NUME=VALOARE", help="suprascrie o variabila")
    r.add_argument("--fara-chenar", action="store_true", help="fara chenarul RUN pe ecran")
    a = p.parse_args(argv)
    if a.cmd == "run":
        variables = dict(v.split("=", 1) for v in a.var if "=" in v)
        return run_file(a.file, variables, show_frame=not a.fara_chenar)
    return 2


if __name__ == "__main__":
    sys.exit(main())
