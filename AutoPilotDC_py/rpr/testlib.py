# -*- coding: utf-8 -*-
# ============================================================
# AutoPilot DC — 🧪 Biblioteca de test (v4.25)
#
# O biblioteca generata (implicit 3000 de obiecte: Web, SAP GUI, Desktop, ~2% dubluri) si
# cateva rutine care le folosesc, ca sa incerci cautarea si "Folosit in" pe o
# biblioteca mare. Totul sta intr-un singur folder ales de tine, marcat cu
# fisierul MARKER; stergerea merge doar pe un folder marcat (nu poate sterge
# altceva din greseala). Datele sunt inventate, fara nume reale.
# ============================================================

from __future__ import annotations

import os
import random
import shutil
from typing import List, Tuple

from .model import (ActionNode, Condition, ConditionKind, IfNode, Locator, LocatorKind, ObjectRepository,
                    RprAction, Routine, UiObject, UiTechnology)
from .storage import RepositoryStore, RoutineStore

MARKER = ".autopilot_biblioteca_test"
FOLDER_NAME = "Biblioteca_test"
LIBRARY_FILE = "obiecte.json"
ROUTINES_DIR = "rutine"

_WEB_APPS = {
    "Portal comenzi": ["Login", "Cautare comenzi", "Detalii comanda", "Export", "Setari cont"],
    "Portal clienti": ["Lista clienti", "Fisa client", "Adrese", "Documente", "Istoric"],
    "Ticketing demo": ["Tichete", "Tichet nou", "Rapoarte", "Administrare", "Notificari"],
}
_SAP_SCREENS = ["VA01", "VA02", "VA03", "MM03", "SU01", "PFCG", "ME23N", "FB03", "XD03", "SE16"]
_DESKTOP_APPS = {"Notepad": ["Editor", "Salvare"], "Calculator": ["Standard"], "Explorer": ["Fisiere", "Proprietati"]}

_ACTIONS = ["Salveaza", "Anuleaza", "Cauta", "Sterge", "Adauga", "Editeaza", "Export", "Import", "Trimite",
            "Inchide", "Deschide", "Filtreaza", "Reseteaza", "Confirma", "Inapoi", "Inainte", "Incarca mai mult",
            "Copiaza", "Tipareste", "Aproba", "Respinge", "Detalii", "Actualizeaza", "Login", "Logout"]
_FIELDS = ["Nume", "Prenume", "Email", "Telefon", "Oras", "Cod postal", "Numar comanda", "Data start", "Data final",
           "Client", "Material", "Cantitate", "Pret", "Moneda", "Observatii", "Utilizator", "Parola", "Rol",
           "Departament", "Status", "Prioritate", "Categorie", "Descriere", "Referinta", "Cod fiscal"]
# (tipul din biblioteca, prefixul numelui, lista de cuvinte, element_type)
_KINDS = [
    ("Buton", "Buton", _ACTIONS, "button"),
    ("Camp text", "Camp", _FIELDS, "input (textbox)"),
    ("ComboBox / lista derulanta", "Combo", _FIELDS, "select"),
    ("Checkbox / radio", "Bifa", _FIELDS, "input (checkbox)"),
    ("Link", "Link", _ACTIONS, "a"),
    ("Text / eticheta", "Text", _FIELDS, "span"),
    ("Meniu / tab", "Meniu", _ACTIONS, "li"),
]
_CONTAINERS = [("Tabel / grid", "Tabel"), ("RefList / lista", "Lista"), ("Formular", "Formular"),
               ("Container / sectiune", "Sectiune")]


def _locators(tech: UiTechnology, slug: str, label: str, rnd: random.Random) -> List[Locator]:
    if tech == UiTechnology.Sap:
        return [Locator(LocatorKind.SapId, f"wnd[0]/usr/{rnd.choice(['btn', 'txt', 'cmb', 'chk'])}{slug.upper()}")]
    if tech == UiTechnology.Desktop:
        return [Locator(LocatorKind.AutomationId, slug), Locator(LocatorKind.UiaName, label)]
    return [Locator(LocatorKind.TestId, slug), Locator(LocatorKind.Text, label), Locator(LocatorKind.Css, f"#{slug}")]


def _screens() -> List[Tuple[UiTechnology, str, str]]:
    out = []
    for app, pages in _WEB_APPS.items():
        out += [(UiTechnology.Web, app, p) for p in pages]
    out += [(UiTechnology.Sap, "SAP GUI", s) for s in _SAP_SCREENS]
    for app, pages in _DESKTOP_APPS.items():
        out += [(UiTechnology.Desktop, app, p) for p in pages]
    return out


def generate_repository(count: int = 3000, seed: int = 7) -> ObjectRepository:
    """Biblioteca inventata, mereu aceeasi pentru acelasi seed: ecrane, containere, obiecte, cateva dubluri."""
    rnd = random.Random(seed)
    repo = ObjectRepository()
    screens = _screens()
    containers: dict = {}
    for tech, app, page in screens:
        for ctype, cname in rnd.sample(_CONTAINERS, 2):
            name = repo.make_unique_name(f"{cname}_{page}".replace(" ", "_"))
            slug = name.lower()
            repo.objects.append(UiObject(name=name, technology=tech, object_type=ctype, site=app, page=page,
                                         locators=_locators(tech, slug, cname, rnd), captured_text=cname,
                                         description="Obiect de test", tags=["test"]))
            containers.setdefault((app, page), []).append(name)
    i = 0
    while len(repo.objects) < count:
        tech, app, page = screens[i % len(screens)]
        otype, prefix, words, etype = rnd.choice(_KINDS)
        label = rnd.choice(words)
        name = repo.make_unique_name(f"{prefix}_{label}_{page}".replace(" ", "_"))
        slug = f"{prefix}-{label}-{i}".lower().replace(" ", "-")
        obj = UiObject(name=name, technology=tech, object_type=otype, site=app, page=page, element_type=etype,
                       locators=_locators(tech, slug, label, rnd), captured_text=label,
                       description="Obiect de test", tags=["test"])
        if rnd.random() < 0.4:
            obj.parent = rnd.choice(containers[(app, page)])
        if rnd.random() < 0.15:
            obj.folder = rnd.choice(["Actiuni", "Filtre", "Antet", "Subsol/Linkuri"])
        repo.objects.append(obj)
        i += 1
    # ~2% dubluri: acelasi element salvat de doua ori (pentru 🧹 Curata biblioteca)
    plain = [o for o in repo.objects if not o.is_container]
    for o in rnd.sample(plain, max(1, len(plain) // 50)):
        twin = UiObject.from_dict(o.to_dict())
        twin.name = repo.make_unique_name(o.name + "_copie")
        twin.tags = ["test", "dublura"]
        if len(repo.objects) >= count:
            repo.objects.remove(next(x for x in reversed(repo.objects) if x is not o and not x.is_container
                                     and "dublura" not in x.tags and not repo.children_of(x.name)))
        repo.objects.append(twin)
    return repo


def generate_routines(repo: ObjectRepository, count: int = 25, seed: int = 11) -> List[Routine]:
    """Rutine care folosesc obiecte din biblioteca (pentru "Folosit in"); aproape jumatate raman nefolosite."""
    rnd = random.Random(seed)
    usable = [o for o in repo.objects if not o.is_container]
    if not usable:
        return []
    pool = rnd.sample(usable, max(1, len(usable) // 2))
    out = []
    for n in range(count):
        r = Routine(name=f"Test {n + 1:02d}", description="Rutina de test (biblioteca generata)")
        for o in rnd.sample(pool, min(len(pool), rnd.randint(4, 12))):
            act = RprAction.TypeText if o.object_type == "Camp text" else RprAction.Click
            r.steps.append(ActionNode(action=act, target=o.name, technology=o.technology,
                                      value="test" if act == RprAction.TypeText else ""))
        cond = rnd.choice(pool)
        r.steps.append(IfNode(condition=Condition(kind=ConditionKind.ElementExists, target=cond.name, timeout_ms=2000)))
        out.append(r)
    return out


def create(parent_folder: str, count: int = 3000, routines: int = 25) -> str:
    """Creeaza <parent_folder>/Biblioteca_test (obiecte.json + rutine/). Intoarce calea bibliotecii."""
    folder = os.path.join(parent_folder, FOLDER_NAME)
    if os.path.isdir(folder) and not is_test_folder(folder) and os.listdir(folder):
        raise FileExistsError(f"Folderul exista si nu e o biblioteca de test: {folder}")
    os.makedirs(os.path.join(folder, ROUTINES_DIR), exist_ok=True)
    with open(os.path.join(folder, MARKER), "w", encoding="utf-8") as f:
        f.write("Biblioteca de test AutoPilot DC. Folderul poate fi sters din Studio (🧪 → Sterge).\n")
    repo = generate_repository(count)
    lib = os.path.join(folder, LIBRARY_FILE)
    RepositoryStore.save(repo, lib)
    rdir = os.path.join(folder, ROUTINES_DIR)
    for r in generate_routines(repo, routines):
        r.repository_path = lib
        RoutineStore.save(r, os.path.join(rdir, r.name.replace(" ", "_") + ".rpr.json"))
    return lib


def is_test_folder(folder: str) -> bool:
    return bool(folder) and os.path.isfile(os.path.join(folder, MARKER))


def test_folder_of(library_path: str) -> str:
    """Folderul de test care contine biblioteca, sau "" daca biblioteca nu e una de test."""
    folder = os.path.dirname(os.path.abspath(library_path or ""))
    return folder if is_test_folder(folder) else ""


def delete(folder: str) -> None:
    """Sterge folderul bibliotecii de test; refuza orice folder fara MARKER."""
    if not is_test_folder(folder):
        raise PermissionError(f"Nu e o biblioteca de test (lipseste {MARKER}): {folder}")
    shutil.rmtree(folder)
