# -*- coding: utf-8 -*-
# ============================================================
# AutoPilot DC — Teste: 🧹 Curata biblioteca (v4.27): dubluri, unire, stergere
#   Rulare:  py -m unittest tests.test_libclean
# ============================================================

import json
import os
import shutil
import sys
import tempfile
import unittest
from unittest import mock

APP = os.path.dirname(os.path.abspath(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, APP)

from rpr import libclean, libsearch, testlib  # noqa: E402
from rpr.model import (ActionNode, Condition, ConditionKind, IfNode, Locator, LocatorKind,  # noqa: E402
                       ObjectRepository, Routine, RprAction, UiObject, UiTechnology)
from rpr.storage import RepositoryStore, RoutineStore, RprPaths  # noqa: E402


def _o(name, locs, **kw):
    kw.setdefault("site", "Portal")
    kw.setdefault("page", "Comenzi")
    kw.setdefault("object_type", "Buton")
    return UiObject(name=name, locators=[Locator(k, v) for k, v in locs], **kw)


class DuplicateTests(unittest.TestCase):
    def test_groups_sure_probable_and_separate(self):
        objs = [
            _o("Salveaza", [(LocatorKind.Id, "save")], captured_text="Salveaza"),
            _o("Salveaza_2", [(LocatorKind.Id, "save"), (LocatorKind.Css, "#s")]),
            _o("Salveaza_3", [(LocatorKind.Css, ".x")], captured_text="Salveaza"),
            _o("Salveaza_Adrese", [(LocatorKind.Id, "save")], page="Adrese"),      # alt ecran
            _o("Label_Client", [(LocatorKind.Text, "Client")], object_type="Text / eticheta"),
            _o("Camp_Client", [(LocatorKind.Text, "Client")], object_type="Camp text"),  # alt tip
            _o("Sap_Save", [(LocatorKind.Id, "save")], technology=UiTechnology.Sap),
        ]
        usage = {"salveaza_2": [libsearch.Usage("r.rpr.json", "R")]}
        groups = libclean.find_duplicates(objs, usage)
        self.assertEqual(1, len(groups))
        g = groups[0]
        self.assertEqual("Salveaza_2", g.objects[0].name)          # cel folosit in rutine e propus primul
        self.assertEqual({"Salveaza", "Salveaza_2", "Salveaza_3"}, {o.name for o in g.objects})
        self.assertFalse(g.sure)                                    # Salveaza_3 vine doar prin text
        only_loc = libclean.find_duplicates(objs[:2])
        self.assertTrue(only_loc[0].sure)

    def test_test_library_has_sure_duplicates(self):
        groups = libclean.find_duplicates(testlib.generate_repository(600).objects)
        self.assertTrue(any(g.sure for g in groups))
        self.assertTrue(all(len(g.objects) > 1 for g in groups))


class MergeTests(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="apdc_clean_")

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def test_merge_moves_steps_conditions_children_and_backs_up(self):
        repo = ObjectRepository()
        keep = repo.add(_o("Salveaza", [(LocatorKind.Id, "save")]))
        dup = repo.add(_o("Salveaza_copie", [(LocatorKind.Id, "save"), (LocatorKind.Css, "#s")], tags=["x"]))
        child = repo.add(_o("Icon", [(LocatorKind.Css, "i")], parent="Salveaza_copie"))
        lib = os.path.join(self.d, "obiecte.json")
        RepositoryStore.save(repo, lib)
        r = Routine(name="R")
        r.steps = [ActionNode(action=RprAction.Click, target="salveaza_copie"),
                   IfNode(condition=Condition(kind=ConditionKind.AllOf, children=[
                       Condition(kind=ConditionKind.ElementExists, target="Salveaza_copie")]))]
        rp = os.path.join(self.d, "R.rpr.json")
        RoutineStore.save(r, rp)
        other = os.path.join(self.d, "Alta.rpr.json")
        RoutineStore.save(Routine(name="Alta", steps=[ActionNode(action=RprAction.Click, target="Salveaza")]), other)
        before = open(other, encoding="utf-8").read()

        folder = libclean.backup(lib, [rp])
        st = libsearch.LibraryState()
        st.toggle_favorite("Salveaza_copie")
        res = libclean.merge(repo, keep, [dup], [rp, other], st)

        self.assertEqual(["Salveaza_copie"], res.removed)
        self.assertEqual(2, res.steps_changed)
        self.assertEqual([rp], res.routines_changed)
        self.assertEqual(["Salveaza", "Icon"], [o.name for o in repo.objects])
        self.assertEqual("Salveaza", child.parent)
        self.assertEqual([("Id", "save"), ("Css", "#s")], [(str(l.kind), l.value) for l in keep.locators])
        self.assertIn("x", keep.tags)
        self.assertTrue(st.is_favorite("Salveaza"))
        data = json.dumps(json.load(open(rp, encoding="utf-8")))
        self.assertNotIn("Salveaza_copie", data)
        self.assertEqual(before, open(other, encoding="utf-8").read())   # rutina neatinsa nu se rescrie
        loaded = RoutineStore.load(rp, repo)
        self.assertEqual("Salveaza", loaded.steps[0].target)
        # copia de rezerva: biblioteca si rutina de dinainte
        self.assertTrue(folder.startswith(os.path.join(self.d, libclean.BACKUP_DIR)))
        self.assertTrue(os.path.isfile(os.path.join(folder, "obiecte.json")))
        self.assertIn("Salveaza_copie", open(os.path.join(folder, "rutine", "R.rpr.json"), encoding="utf-8").read())
        self.assertNotEqual(folder, libclean.backup(lib, []))            # a doua copie, alt folder
        # folderul de rezerva nu e citit ca folder de rutine
        self.assertEqual(sorted([rp, other]), sorted(libsearch.routine_files([self.d])))

    def test_rename_in_open_routine(self):
        steps = [ActionNode(action=RprAction.Click, target="A_copie"),
                 IfNode(condition=Condition(kind=ConditionKind.ElementExists, target="a_copie"))]
        self.assertEqual(2, libclean.rename_in_steps(steps, {"a_copie": "A"}))
        self.assertEqual(["A", "A"], [steps[0].target, steps[1].condition.target])

    def test_cleanup_candidates_skip_favorites_and_parents(self):
        repo = ObjectRepository()
        used = repo.add(_o("Folosit", [(LocatorKind.Id, "a")]))
        repo.add(_o("Nefolosit", [(LocatorKind.Id, "b")]))
        repo.add(_o("Fav", [(LocatorKind.Id, "c")]))
        box = repo.add(_o("Tabel", [(LocatorKind.Id, "t")], object_type="Tabel / grid"))
        repo.add(_o("Rand", [(LocatorKind.Id, "r")], parent="Tabel"))
        st = libsearch.LibraryState()
        st.toggle_favorite("Fav")
        st.mark_checked("Folosit", False)
        usage = {"folosit": [libsearch.Usage("r", "R")], "rand": [libsearch.Usage("r", "R")]}
        rows = {o.name: why for o, why in libclean.cleanup_candidates(repo, usage, st)}
        self.assertEqual({"Folosit": "stricat", "Nefolosit": "nefolosit"}, rows)
        self.assertNotIn("Tabel", rows)
        only_broken = libclean.cleanup_candidates(repo, usage, st, unused=False)
        self.assertEqual(["Folosit"], [o.name for o, _w in only_broken])
        self.assertEqual(1, libclean.delete_objects(repo, [used], st))
        self.assertIsNone(repo.find("Folosit"))


class StudioCleanupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            import tkinter as tk
            cls.root = tk.Tk()
            cls.root.withdraw()
        except Exception as ex:  # noqa: BLE001
            raise unittest.SkipTest(f"fara afisaj: {ex}")
        cls.d = tempfile.mkdtemp(prefix="apdc_studio_clean_")
        cls.old_root = RprPaths.root
        RprPaths.root = os.path.join(cls.d, "Studio")
        import studio_ui
        cls.studio_ui = studio_ui
        colors = {"bg_main": "#1E1E2E", "bg_panel": "#252535", "bg_card": "#2A2A3E", "bg_input": "#32324A",
                  "border": "#444466", "primary": "#009999", "accent": "#3DA9E0", "text": "#FFFFFF",
                  "text_dim": "#B4B4D0", "text_muted": "#8A8AAA", "success": "#1F8F4E", "warning": "#FF8800",
                  "danger": "#CC0000", "row_active": "#1A4A4A"}
        cls.p = studio_ui.StudioPanel(cls.root, colors)
        cls.p.pack(fill="both", expand=True)

    @classmethod
    def tearDownClass(cls):
        try:
            cls.p.shutdown()
            cls.root.destroy()
        except Exception:  # noqa: BLE001
            pass
        RprPaths.root = cls.old_root
        shutil.rmtree(cls.d, ignore_errors=True)

    def test_dialog_merge_all_sure_updates_open_routine(self):
        p = self.p
        lib = testlib.create(self.d, count=400, routines=6)
        p.load_repository(lib)
        groups = libclean.find_duplicates(p.repo.objects, p._ensure_usage())
        sure = [g for g in groups if g.sure]
        self.assertTrue(sure)
        drop = sure[0].objects[1]
        # rutina deschisa (nesalvata) care foloseste dublura
        p.routine.steps = [ActionNode(action=RprAction.Click, target=drop.name)]
        n_before = len(p.repo.objects)
        with mock.patch.object(self.studio_ui.messagebox, "askyesno", return_value=True), \
                mock.patch.object(self.studio_ui.messagebox, "showinfo"):
            dlg = self.studio_ui.LibraryCleanupDialog(p)
            self.assertTrue(dlg.dups.get_children())
            dlg.merge_all_sure()
        removed = sum(len(g.objects) - 1 for g in sure)
        self.assertEqual(n_before - removed, len(p.repo.objects))
        self.assertEqual(sure[0].objects[0].name, p.routine.steps[0].target)
        self.assertTrue(p.dirty)
        self.assertFalse(any(g.sure for g in libclean.find_duplicates(p.repo.objects)))
        saved = RepositoryStore.load(lib)
        self.assertEqual(len(p.repo.objects), len(saved.objects))
        self.assertTrue(os.path.isdir(os.path.join(os.path.dirname(lib), libclean.BACKUP_DIR)))
        # stergerea nefolositelor din dialog
        dlg.v_broken.set(False)
        dlg._fill_unused()
        kids = dlg.unused.get_children()
        self.assertTrue(kids)
        dlg.unused.selection_set(kids[:3])
        with mock.patch.object(self.studio_ui.messagebox, "askyesno", return_value=True):
            dlg.delete_selected()
        self.assertEqual(n_before - removed - 3, len(RepositoryStore.load(lib).objects))
        dlg.destroy()


if __name__ == "__main__":
    unittest.main()
