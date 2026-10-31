# -*- coding: utf-8 -*-
# ============================================================
# AutoPilot DC — Teste: 🔍 cautarea in biblioteca, starea obiectelor,
# "Folosit in" si biblioteca de test (v4.25)
#   Rulare:  py -m unittest tests.test_libsearch
# ============================================================

import datetime as dt
import os
import shutil
import sys
import tempfile
import time
import unittest

APP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, APP)

from rpr import libsearch, testlib  # noqa: E402
from rpr.model import Locator, LocatorKind, UiObject, UiTechnology  # noqa: E402
from rpr.storage import RepositoryStore, RprPaths  # noqa: E402


def _obj(name, **kw):
    kw.setdefault("locators", [Locator(LocatorKind.Css, "#" + name.lower())])
    return UiObject(name=name, **kw)


OBJS = [
    _obj("Buton_Salveaza", object_type="Buton", site="Portal", page="Comenzi", captured_text="Salvează"),
    _obj("Camp_Client", object_type="Camp text", site="Portal", page="Comenzi", captured_text="Client"),
    _obj("Combo_Tara", object_type="ComboBox / lista derulanta", site="Portal", page="Adrese", tags=["export"]),
    _obj("btnSAVE", technology=UiTechnology.Sap, object_type="Buton", site="SAP GUI", page="VA03",
         attributes={"tooltip": "Save"}),
]


class QueryTests(unittest.TestCase):
    def test_normalize_removes_diacritics_and_case(self):
        self.assertEqual("salveaza tara", libsearch.normalize("  Salvează  ȚARA "))

    def test_parse_prefixes_tags_and_quotes(self):
        q = libsearch.parse_query('salv tip:buton app:SAP ecran:"Lista comenzi" #export stare:stricat')
        self.assertEqual(["salv"], q.words)
        self.assertEqual(["buton"], q.types)
        self.assertEqual(["sap"], q.apps)
        self.assertEqual(["lista comenzi"], q.pages)
        self.assertEqual(["export"], q.tags)
        self.assertEqual(libsearch.STATUS_BAD, q.status)
        # un "a:b" necunoscut ramane text cautat
        self.assertEqual(["wnd", "0"], libsearch.parse_query("wnd:0").words)


class SearchTests(unittest.TestCase):
    def names(self, text, **kw):
        return [o.name for o in libsearch.search(OBJS, text, **kw)[0]]

    def test_visible_text_without_diacritics(self):
        self.assertEqual("Buton_Salveaza", self.names("salvează")[0])
        self.assertIn("btnSAVE", self.names("save"))

    def test_typo_is_tolerated(self):
        self.assertIn("Camp_Client", self.names("clinet"))

    def test_every_word_must_match(self):
        self.assertEqual([], self.names("salveaza client"))

    def test_filters(self):
        self.assertEqual(["btnSAVE"], self.names("app:sap"))
        self.assertEqual(["Combo_Tara"], self.names("tip:combo"))
        self.assertEqual(["Combo_Tara"], self.names("#export"))
        self.assertEqual(["Buton_Salveaza", "btnSAVE"], sorted(self.names("", type_filter="Buton")))
        self.assertEqual(["Camp_Client"], self.names("ecran:comenzi tip:camp"))

    def test_limit_reports_total(self):
        hits, total = libsearch.search(OBJS, "", type_filter="Buton", limit=1)
        self.assertEqual((1, 2), (len(hits), total))

    def test_status_filters_and_favorite_first(self):
        st = libsearch.LibraryState()
        st.mark_checked("Camp_Client", False)
        st.toggle_favorite("Combo_Tara")
        st.mark_used("Buton_Salveaza")
        usage = {"buton_salveaza": [libsearch.Usage("r.rpr.json", "R")]}
        self.assertEqual(["Camp_Client"], self.names("", state=st, status_filter=libsearch.STATUS_BAD))
        self.assertEqual(["Combo_Tara"], self.names("stare:favorit", state=st))
        self.assertEqual(["Buton_Salveaza"], self.names("", state=st, status_filter=libsearch.STATUS_RECENT))
        self.assertNotIn("Buton_Salveaza", self.names("", state=st, usage=usage, status_filter=libsearch.STATUS_UNUSED))
        self.assertEqual("Combo_Tara", self.names("portal", state=st)[0])


class StateAndUsageTests(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="apdc_libs_")

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def test_state_file_next_to_library_roundtrip(self):
        lib = os.path.join(self.d, "obiecte.json")
        self.assertEqual(os.path.join(self.d, "obiecte.stare.json"), libsearch.state_path(lib))
        st = libsearch.LibraryState.for_library(lib)
        st.mark_checked("A", True)
        st.toggle_favorite("B")
        st.mark_used("A")
        st.save()
        again = libsearch.LibraryState.for_library(lib)
        self.assertEqual(libsearch.STATUS_OK, again.status("a"))
        self.assertTrue(again.is_favorite("B"))
        self.assertEqual(["a"], again.recent_names())
        self.assertFalse(again.toggle_favorite("B"))

    def test_broken_state_file_is_ignored(self):
        lib = os.path.join(self.d, "obiecte.json")
        with open(libsearch.state_path(lib), "w", encoding="utf-8") as f:
            f.write("{nu e json")
        self.assertEqual({}, libsearch.LibraryState.for_library(lib).objects)

    def test_usage_index_finds_steps_and_conditions(self):
        lib = testlib.create(self.d, count=300, routines=5)
        rdir = os.path.join(os.path.dirname(lib), testlib.ROUTINES_DIR)
        files = libsearch.routine_files([rdir, rdir])
        self.assertEqual(5, len(files))
        idx = libsearch.build_usage_index(files + files)
        repo = RepositoryStore.load(lib)
        used = [o for o in repo.objects if idx.get(o.name.lower())]
        self.assertTrue(used)
        self.assertLess(len(used), len(repo.objects))   # o parte raman nefolosite
        u = idx[used[0].name.lower()][0]
        self.assertTrue(u.step_id)
        self.assertIn(used[0].name, u.step)
        self.assertGreaterEqual(len(libsearch.routines_of(idx, used[0].name)), 1)


class TestLibraryTests(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="apdc_testlib_")

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def test_create_is_repeatable_and_searchable_fast(self):
        lib = testlib.create(self.d)
        repo = RepositoryStore.load(lib)
        self.assertEqual(3000, len(repo.objects))
        self.assertEqual({UiTechnology.Web, UiTechnology.Sap, UiTechnology.Desktop},
                         {o.technology for o in repo.objects})
        self.assertEqual([o.name for o in testlib.generate_repository(200).objects],
                         [o.name for o in testlib.generate_repository(200).objects])
        t = time.time()
        hits, total = libsearch.search(repo.objects, "salv tip:buton")
        self.assertLess(time.time() - t, 2.0)
        self.assertTrue(hits and all(o.object_type == "Buton" for o in hits))
        self.assertEqual(os.path.dirname(lib), testlib.test_folder_of(lib))

    def test_delete_only_marked_folder(self):
        other = os.path.join(self.d, "altceva")
        os.makedirs(other)
        with self.assertRaises(PermissionError):
            testlib.delete(other)
        self.assertTrue(os.path.isdir(other))
        lib = testlib.create(self.d, count=200, routines=2)
        folder = os.path.dirname(lib)
        testlib.delete(folder)
        self.assertFalse(os.path.exists(folder))
        self.assertTrue(os.path.isdir(other))

    def test_create_refuses_foreign_folder_with_files(self):
        foreign = os.path.join(self.d, testlib.FOLDER_NAME)
        os.makedirs(foreign)
        with open(os.path.join(foreign, "important.txt"), "w") as f:
            f.write("x")
        with self.assertRaises(FileExistsError):
            testlib.create(self.d)


class StudioLibraryTests(unittest.TestCase):
    """Panoul de obiecte din Studio: cautarea ca lista, favoritele sus, biblioteca de test."""

    @classmethod
    def setUpClass(cls):
        try:
            import tkinter as tk
            cls.root = tk.Tk()
            cls.root.withdraw()
        except Exception as ex:  # noqa: BLE001
            raise unittest.SkipTest(f"fara afisaj: {ex}")
        cls.d = tempfile.mkdtemp(prefix="apdc_studio_lib_")
        cls.old_root = RprPaths.root
        RprPaths.root = os.path.join(cls.d, "Studio")
        import studio_ui
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

    def test_search_list_favorites_and_delete(self):
        p = self.p
        lib = testlib.create(self.d, count=400, routines=4)
        p.load_repository(lib)
        p._usage_ready(libsearch.build_usage_index(libsearch.routine_files(p._usage_folders())))
        self.assertIsNotNone(p._obj_usage)
        # cautare -> lista simpla, fara grupuri
        p._obj_filter.set("salv tip:buton")
        p.refresh_objects()
        rows = p.objects.get_children()
        self.assertTrue(rows)
        self.assertTrue(all(r.startswith("obj:") for r in rows if r not in ("more", "none")))
        # favorit -> grupul de sus cand nu se cauta
        p.objects.selection_set(rows[0])
        name = rows[0][4:]
        p.toggle_favorite_object()
        p._obj_filter.set("")
        p.refresh_objects()
        self.assertEqual("group:fav", p.objects.get_children()[0])
        self.assertIn("fav:" + name, p.objects.get_children("group:fav"))
        self.assertTrue(os.path.isfile(libsearch.state_path(lib)))
        # filtrul de stare din lista
        p._obj_status_cb.current([k for k, _l in libsearch.STATUS_CHOICES].index(libsearch.STATUS_FAVORITE))
        p.refresh_objects()
        self.assertEqual(["obj:" + name], list(p.objects.get_children()))
        p._obj_status_cb.current(0)
        # previzualizarea arata "Folosit in" / "Nefolosit"
        p.objects.selection_set("obj:" + name) if p.objects.exists("obj:" + name) else None
        p._object_preview()
        # stergerea bibliotecii de test revine la biblioteca implicita
        from unittest import mock
        with mock.patch("studio_ui.messagebox.askyesno", return_value=True):
            p.delete_test_library()
        self.assertFalse(os.path.exists(os.path.dirname(lib)))
        self.assertTrue(p._is_default_library())


if __name__ == "__main__":
    unittest.main()
