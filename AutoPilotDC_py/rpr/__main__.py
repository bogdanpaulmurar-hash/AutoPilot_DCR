# -*- coding: utf-8 -*-
# ============================================================
# AutoPilot DC v4.1 — RPR (Python)
# Rulare fara interfata (programari Windows / linie de comanda):
#
#   python -m rpr run "C:\...\rutina.rpr.json" [--var Nume=Valoare ...] [--fara-chenar]
#
#   --anunta: la final apare un mesaj scurt cu rezultatul (programari) + istoric
# Cod de iesire: 0 = succes, 1 = rutina a esuat, 2 = fisier invalid, 3 = alta rutina programata ruleaza deja.
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


def _single_instance():
    """O singura rulare programata o data (doua rutine nu pot folosi ecranul simultan)."""
    try:
        import ctypes
        h = ctypes.windll.kernel32.CreateMutexW(None, False, "Local\\AutoPilotDC_RprRun")
        return h if ctypes.windll.kernel32.GetLastError() != 183 else None   # 183 = exista deja
    except Exception:
        return True


def notify(title: str, text: str, success: bool, log_path: str = "", seconds: int = 25) -> None:
    """Fereastra mica in coltul din dreapta-jos (se inchide singura)."""
    try:
        import tkinter as tk
    except ImportError:
        return
    root = tk.Tk()
    root.overrideredirect(True)
    root.attributes("-topmost", True)
    bg = "#1F7A4D" if success else "#A12A2A"
    root.configure(bg=bg)
    tk.Label(root, text=title, bg=bg, fg="white", font=("Segoe UI", 11, "bold"), anchor="w").pack(
        fill="x", padx=14, pady=(10, 2))
    tk.Label(root, text=text, bg=bg, fg="white", font=("Segoe UI", 9), wraplength=360, justify="left",
             anchor="w").pack(fill="x", padx=14)
    row = tk.Frame(root, bg=bg)
    row.pack(anchor="e", padx=10, pady=8)
    if log_path and os.path.exists(log_path):
        tk.Button(row, text="Deschide logul", relief="flat",
                  command=lambda: (os.startfile(log_path), root.destroy())).pack(side="left", padx=3)
    tk.Button(row, text="Inchide", relief="flat", command=root.destroy).pack(side="left", padx=3)
    root.update_idletasks()
    w, h = max(380, root.winfo_reqwidth()), root.winfo_reqheight()
    root.geometry(f"{w}x{h}+{root.winfo_screenwidth() - w - 16}+{root.winfo_screenheight() - h - 56}")
    root.after(seconds * 1000, root.destroy)
    root.mainloop()


def run_file(path: str, variables: dict, show_frame: bool = True, announce: bool = False) -> int:
    started = _dt.datetime.now()
    mutex = _single_instance() if announce else True
    if mutex is None:
        notify("AutoPilot DC — rulare amanata", f"{os.path.basename(path)}: alta rutina programata ruleaza acum.", False)
        return 3
    code, name, msg, log = _run_file(path, variables, show_frame, started)
    if announce:
        try:
            from .schedule import add_history
            add_history(name, path, code == 0, msg, log, started)
        except Exception:
            pass
        notify(("✔ " if code == 0 else "✖ ") + f"AutoPilot DC — {name}", msg, code == 0, log)
    return code


def _run_file(path: str, variables: dict, show_frame: bool, started) -> tuple:
    stamp = started.strftime("%Y%m%d_%H%M%S")
    text_log = os.path.join(RprPaths.output(), f"Log_programat_{stamp}.txt")
    with open(text_log, "w", encoding="utf-8", buffering=1) as writer:
        try:
            repo = RepositoryStore.load(None)
            routine = RoutineStore.load(path, repo)
            if routine.repository_path.strip():
                repo = RepositoryStore.load(routine.repository_path)
        except Exception as ex:  # noqa: BLE001
            writer.write(f"EROARE la citirea rutinei: {ex}\n")
            return 2, os.path.basename(path), f"Rutina nu poate fi citita: {ex}", text_log

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
                # procesul se inchide imediat dupa: asteptam ca notificarile sa revina efectiv
                safety.DoNotDisturb.restore(wait=True)
                writer.write(safety.DoNotDisturb.last_message + "\n")

        result = result_box.get("r")
        xlsx = os.path.join(RprPaths.output(), f"Log_programat_{sanitize_name(routine.name)}_{stamp}.xlsx")
        try:
            RunLogExporter.export_xlsx(host.entries, xlsx)
        except Exception as ex:  # noqa: BLE001
            writer.write(f"Exportul logului in Excel a esuat: {ex}\n")
            xlsx = text_log
        ok = result is not None and result.success
        msg = result.message if result is not None else "Rutina nu s-a terminat."
        return (0 if ok else 1), routine.name, msg, xlsx


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="python -m rpr", description="AutoPilot DC — rulare rutine RPR fara interfata")
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="ruleaza o rutina .rpr.json")
    r.add_argument("file")
    r.add_argument("--var", action="append", default=[], metavar="NUME=VALOARE", help="suprascrie o variabila")
    r.add_argument("--fara-chenar", action="store_true", help="fara chenarul RUN pe ecran")
    r.add_argument("--anunta", action="store_true", help="mesaj cu rezultatul la final + istoric (programari)")
    a = p.parse_args(argv)
    if a.cmd == "run":
        variables = dict(v.split("=", 1) for v in a.var if "=" in v)
        return run_file(a.file, variables, show_frame=not a.fara_chenar, announce=a.anunta)
    return 2


if __name__ == "__main__":
    sys.exit(main())
