# -*- coding: utf-8 -*-
# ============================================================
# AutoPilot DC v4.1 — RPR (Python)
# Rulare fara interfata (programari Windows / linie de comanda):
#
#   python -m rpr run "C:\...\rutina.rpr.json" [--var Nume=Valoare ...] [--fara-chenar]
#   python -m rpr run "C:\...\Sandbox.pregatire.json"   (o pregatire: mai multe rutine una dupa alta)
#
#   python -m rpr device ["R58M12 | com.firma.app"]   (📱 v4.29: verifica telefonul Android, fara rulare)
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
from .lang import ft
from .legacy import execute_legacy_step
from .storage import RepositoryStore, RoutineStore, RprPaths, RunLogExporter
from .drivers.base import DriverProvider
from .model import sanitize_name
from . import resume
from .batch import PREP_EXT, Preparation, PreparationRunner


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


def _start_video(name: str, host, writer, force: bool = False, folder: str = ""):
    """Film al rularii programate (Setari → Video: "la fiecare rulare" + "si la rularile programate").
    force=True: pregatirile cu "film pentru fiecare rutina" filmeaza oricum."""
    try:
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        import screen_recorder as sr
        vs = sr.VideoSettings.load()
        if not force and not (vs.record_on_run and vs.on_schedule):
            return None
        rec = sr.ScreenRecorder(vs)
        rec.start(name, folder=folder)
        host.video_recorder = rec   # linkurile din raportul Excel al rularii

        def row_started(row, sheet):
            if vs.per_row:
                old = rec.split(f"{name}_rand{row}")
                if old:
                    writer.write(ft(f"Film: {old}") + "\n")
            rec.marker(f"Rand {row}")
        host.row_started = row_started
        host.row_finished = lambda row, status: rec.marker(f"Rand {row}: {status[:60]}")
        return rec
    except Exception as ex:  # noqa: BLE001 — filmul nu are voie sa opreasca rutina
        writer.write(ft(f"Filmul nu a putut porni: {ex}") + "\n")
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
    try:   # mesajul in limba aleasa in Setari
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        import i18n
        i18n.install()
    except Exception:
        pass
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
    # starea rularii: daca procesul / PC-ul se inchide brusc, aplicatia ofera reluarea la pornire
    is_prep = path.lower().endswith(PREP_EXT)
    state = resume.begin(resume.KIND_PREP if is_prep else resume.KIND_ROUTINE, path,
                         os.path.splitext(os.path.basename(path))[0], variables=variables)
    try:
        if is_prep:
            code, name, msg, log = _run_preparation(path, show_frame, started, state)
        else:
            code, name, msg, log = _run_file(path, variables, show_frame, started)
    finally:
        resume.end(state)
    if announce:
        try:
            from .schedule import add_history
            add_history(name, path, code == 0, msg, log, started)
        except Exception:
            pass
        notify(("✔ " if code == 0 else "✖ ") + f"AutoPilot DC — {name}", msg, code == 0, log)
    return code


def _run_preparation(path: str, show_frame: bool, started, state=None, start_index: int = 0) -> tuple:
    """Pregatire fara interfata: fiecare rutina ca la rularea programata (film, raport), plus rezumat + documentatie."""
    try:
        prep = Preparation.load(path)
    except Exception as ex:  # noqa: BLE001
        return 2, os.path.basename(path), f"Pregatirea nu poate fi citita: {ex}", ""

    def run_one(routine, item, folder):
        out = {}
        _run_file(prep.resolve(item), {}, show_frame, _dt.datetime.now(), routine=routine, out=out,
                  force_video=prep.video, log_folder=folder)
        return out.get("result"), out.get("video", "")

    runner = PreparationRunner(prep, run_one, RprPaths.output(),
                               on_item_done=lambda done: resume.update(state, done))
    res = runner.run(start_index)
    return (0 if res.success else 1), prep.name, res.message, res.summary or res.documentation


def _run_file(path: str, variables: dict, show_frame: bool, started, routine=None, out=None,
              force_video: bool = False, log_folder: str = "") -> tuple:
    stamp = started.strftime("%Y%m%d_%H%M%S")
    log_folder = log_folder or RprPaths.output()
    text_log = os.path.join(log_folder, f"Log_programat_{stamp}.txt")
    with open(text_log, "w", encoding="utf-8", buffering=1) as writer:
        try:
            repo = RepositoryStore.load(None)
            if routine is None:
                routine = RoutineStore.load(path, repo)
            if routine.repository_path.strip():
                repo = RepositoryStore.load(routine.repository_path)
        except Exception as ex:  # noqa: BLE001
            writer.write(ft(f"EROARE la citirea rutinei: {ex}\n"))
            return 2, os.path.basename(path), f"Rutina nu poate fi citita: {ex}", text_log

        host = HeadlessRunHost(lambda line: writer.write(line + "\n"))
        host.legacy_executor = execute_legacy_step
        drivers = build_drivers()
        engine = RprEngine(repo, drivers, host, RprPaths.output())

        safety = _safety()
        dnd = bool(routine.settings.do_not_disturb and safety)
        if dnd:
            safety.DoNotDisturb.enable()
            writer.write(ft(safety.DoNotDisturb.last_message) + "\n")

        result_box = {}
        from .report import video_folder
        rec = _start_video(routine.name, host, writer, force_video, video_folder(routine))   # 🎥 daca e activ in Setari → Video

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
            if rec is not None:
                film = rec.stop()
                writer.write(ft(f"Film: {film}") + "\n")
                if out is not None:
                    out["video"] = film
            drivers.close()
            if dnd:
                # procesul se inchide imediat dupa: asteptam ca notificarile sa revina efectiv
                safety.DoNotDisturb.restore(wait=True)
                writer.write(ft(safety.DoNotDisturb.last_message) + "\n")

        result = result_box.get("r")
        if out is not None:
            out["result"] = result
        xlsx = os.path.join(log_folder, f"Log_programat_{sanitize_name(routine.name)}_{stamp}.xlsx")
        try:
            RunLogExporter.export_xlsx(host.entries, xlsx)
        except Exception as ex:  # noqa: BLE001
            writer.write(ft(f"Exportul logului in Excel a esuat: {ex}\n"))
            xlsx = text_log
        ok = result is not None and result.success
        msg = result.message if result is not None else "Rutina nu s-a terminat."
        return (0 if ok else 1), routine.name, msg, xlsx


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="python -m rpr", description="AutoPilot DC — rulare rutine RPR fara interfata")
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="ruleaza o rutina .rpr.json sau o pregatire .pregatire.json")
    r.add_argument("file")
    r.add_argument("--var", action="append", default=[], metavar="NUME=VALOARE", help="suprascrie o variabila")
    r.add_argument("--fara-chenar", action="store_true", help="fara chenarul RUN pe ecran")
    r.add_argument("--anunta", action="store_true", help="mesaj cu rezultatul la final + istoric (programari)")
    d = sub.add_parser("device", help="verifica telefonul Android (adb, aplicatia, Appium), fara rulare")
    d.add_argument("target", nargs="?", default="", help='"telefon | pachet/activitate" (gol = primul telefon)')
    a = p.parse_args(argv)
    if a.cmd == "device":
        from . import mobile
        res = mobile.check_device(mobile.parse_target(a.target))
        print(res.text())
        return 0 if res.ok else 1
    if a.cmd == "run":
        variables = dict(v.split("=", 1) for v in a.var if "=" in v)
        return run_file(a.file, variables, show_frame=not a.fara_chenar, announce=a.anunta)
    return 2


if __name__ == "__main__":
    sys.exit(main())
