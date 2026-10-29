# -*- coding: utf-8 -*-
# ============================================================
# AutoPilot DC — 💾 Backup și restaurare (setări + context înregistrat)
#
# Un fișier .zip, salvat unde alegi, cu:
#   app/        config.json, rutine_salvate/, notite/, locatori/ (Recorder)
#   appdata/    %APPDATA%\AutoPilotDC: limba, video, Studio (rutine, biblioteca de
#               obiecte și imaginile ei, setări Studio, programări, exemple)
#   biblioteca/ folderul rutinelor din 📂 Manager rutine, dacă e în afara Studio
#   backup.json ce conține backup-ul și căile de pe PC-ul unde s-a făcut
#
# Nu intră: profilul browserului (login-uri, mare), filmele, rezultatele (opțional).
# La restaurare se face întâi un backup automat al stării curente, iar căile
# care nu există pe PC-ul nou (ex. folderul rutinelor) sunt adaptate.
# ============================================================

from __future__ import annotations

import datetime as _dt
import json
import os
import shutil
import zipfile
from dataclasses import dataclass, field
from typing import Dict, List, Optional

FORMAT = 1
APP_FILES = ["config.json"]
APP_DIRS = ["rutine_salvate", "notite", "locatori"]
SKIP_DIRS = {"browser-profil", "__pycache__", "backup-automat"}
RESULTS_DIR = "rezultate"


@dataclass
class Roots:
    """Folderele aplicației (în teste: foldere temporare)."""
    app: str
    appdata: str
    library: str = ""          # folderul rutinelor ales în Manager (gol = cel din Studio)

    @classmethod
    def default(cls) -> "Roots":
        app = os.path.dirname(os.path.abspath(__file__))
        appdata = os.path.join(os.environ.get("APPDATA") or os.path.expanduser("~"), "AutoPilotDC")
        library = ""
        try:
            from rpr.drivers.registry import StudioSettings
            library = StudioSettings.load().routines_folder.strip().strip('"')
        except Exception:  # noqa: BLE001
            pass
        return cls(app, appdata, library)


@dataclass
class BackupInfo:
    created: str = ""
    version: str = ""
    computer: str = ""
    files: int = 0
    paths: Dict[str, str] = field(default_factory=dict)
    include_results: bool = False


def _version() -> str:
    try:
        from version import __version__
        return __version__
    except Exception:  # noqa: BLE001
        return ""


def _inside(path: str, folder: str) -> bool:
    try:
        return os.path.commonpath([os.path.abspath(path), os.path.abspath(folder)]) == os.path.abspath(folder)
    except ValueError:   # alt disc
        return False


def _add_tree(z: zipfile.ZipFile, src: str, prefix: str, skip_top: set) -> int:
    n = 0
    if not os.path.isdir(src):
        return 0
    for dirpath, dirnames, filenames in os.walk(src):
        rel_dir = os.path.relpath(dirpath, src)
        top = rel_dir.split(os.sep)[0] if rel_dir != "." else ""
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not (rel_dir == "." and d in skip_top)]
        if top in skip_top:
            continue
        for fn in filenames:
            if fn.endswith((".tmp", ".lock")):
                continue
            full = os.path.join(dirpath, fn)
            arc = prefix + "/" + os.path.relpath(full, src).replace(os.sep, "/")
            try:
                z.write(full, arc)
                n += 1
            except OSError:
                pass   # fișier blocat (ex. deschis în Excel): restul backup-ului contează mai mult
    return n


def create_backup(dest_zip: str, roots: Optional[Roots] = None, include_results: bool = False) -> BackupInfo:
    roots = roots or Roots.default()
    info = BackupInfo(created=_dt.datetime.now().isoformat(timespec="seconds"), version=_version(),
                      computer=os.environ.get("COMPUTERNAME", ""), include_results=include_results,
                      paths={"app": roots.app, "appdata": roots.appdata, "library": roots.library})
    os.makedirs(os.path.dirname(os.path.abspath(dest_zip)) or ".", exist_ok=True)
    tmp = dest_zip + ".tmp"
    skip_studio = set() if include_results else {RESULTS_DIR}
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as z:
        for f in APP_FILES:
            p = os.path.join(roots.app, f)
            if os.path.isfile(p):
                z.write(p, "app/" + f)
                info.files += 1
        for d in APP_DIRS:
            info.files += _add_tree(z, os.path.join(roots.app, d), "app/" + d, set())
        # appdata: totul în afară de profilul browserului; rezultatele doar la cerere
        if os.path.isdir(roots.appdata):
            for name in sorted(os.listdir(roots.appdata)):
                full = os.path.join(roots.appdata, name)
                if os.path.isfile(full):
                    z.write(full, "appdata/" + name)
                    info.files += 1
                elif name == "Studio":
                    info.files += _add_tree(z, full, "appdata/Studio", skip_studio)
                elif name not in SKIP_DIRS:
                    info.files += _add_tree(z, full, "appdata/" + name, set())
        lib = roots.library
        if lib and os.path.isdir(lib) and not _inside(lib, roots.appdata):
            info.files += _add_tree(z, lib, "biblioteca", set())
        z.writestr("backup.json", json.dumps(info.__dict__, ensure_ascii=False, indent=2))
    os.replace(tmp, dest_zip)
    return info


def read_info(zip_path: str) -> BackupInfo:
    with zipfile.ZipFile(zip_path) as z:
        d = json.loads(z.read("backup.json").decode("utf-8"))
    info = BackupInfo()
    for k, v in d.items():
        if hasattr(info, k):
            setattr(info, k, v)
    return info


@dataclass
class RestoreResult:
    files: int = 0
    safety_backup: str = ""
    library: str = ""
    notes: List[str] = field(default_factory=list)


def restore_backup(zip_path: str, roots: Optional[Roots] = None, safety_folder: str = "") -> RestoreResult:
    """Restaurează peste starea curentă. Înainte face un backup automat al stării curente."""
    roots = roots or Roots.default()
    info = read_info(zip_path)   # verifică și că e un backup AutoPilot DC
    res = RestoreResult()
    safety_folder = safety_folder or os.path.join(roots.appdata, "backup-automat")
    stamp = _dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    res.safety_backup = os.path.join(safety_folder, f"Inainte_de_restaurare_{stamp}.zip")
    create_backup(res.safety_backup, roots)

    # folderul rutinelor: aceeași cale dacă folderul părinte există pe acest PC, altfel lângă rutinele Studio
    old_lib = (info.paths or {}).get("library", "")
    lib_target = ""
    with zipfile.ZipFile(zip_path) as z:
        names = z.namelist()
        if any(n.startswith("biblioteca/") for n in names):
            parent = os.path.dirname(old_lib.rstrip("\\/")) if old_lib else ""
            if parent and os.path.isdir(parent):     # ex. G:\My Drive\Dev exista si pe acest PC
                lib_target = old_lib
            else:
                lib_target = os.path.join(roots.appdata, "Studio", "rutine", "biblioteca")
                res.notes.append(f"Folderul rutinelor nu exista pe acest PC; rutinele au fost puse in {lib_target}.")
        res.library = lib_target
        for n in names:
            if n.endswith("/") or n == "backup.json":
                continue
            top, _, rest = n.partition("/")
            base = {"app": roots.app, "appdata": roots.appdata, "biblioteca": lib_target}.get(top)
            if not base or not rest:
                continue
            target = os.path.abspath(os.path.join(base, *rest.split("/")))
            if not _inside(target, base):     # protecție: nimic în afara folderului ales
                continue
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with z.open(n) as src, open(target + ".tmp", "wb") as dst:
                shutil.copyfileobj(src, dst)
            os.replace(target + ".tmp", target)
            res.files += 1

    # setările Studio: folderul rutinelor mutat → calea nouă
    st_path = os.path.join(roots.appdata, "Studio", "studio-setari.json")
    if os.path.isfile(st_path):
        try:
            with open(st_path, encoding="utf-8-sig") as f:
                st = json.load(f)
            changed = False
            if lib_target and os.path.normcase(str(st.get("routines_folder", ""))) != os.path.normcase(lib_target):
                st["routines_folder"] = lib_target
                changed = True
            last = str(st.get("last_routine_path", ""))
            if last and not os.path.exists(last):
                st["last_routine_path"] = ""
                changed = True
            if changed:
                with open(st_path, "w", encoding="utf-8") as f:
                    json.dump(st, f, ensure_ascii=False, indent=2)
        except (OSError, ValueError):
            pass
    return res


def default_name() -> str:
    return f"AutoPilotDC_backup_{_dt.datetime.now():%Y%m%d_%H%M}.zip"
