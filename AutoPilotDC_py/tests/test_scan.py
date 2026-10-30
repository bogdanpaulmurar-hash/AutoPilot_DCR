# -*- coding: utf-8 -*-
# ============================================================
# AutoPilot DC — Teste: scanarea site-ului si biblioteca pe aplicatie (v4.9)
#   Rulare:  py -m unittest tests.test_scan
# ============================================================

import os
import sys
import tempfile
import time
import unittest
from unittest import mock

APP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, APP)

from rpr import scan  # noqa: E402
from rpr.model import Locator, LocatorKind, ObjectRepository, Routine, SiteGroup, UiObject, UiTechnology  # noqa: E402
from rpr.storage import RepositoryStore, RoutineStore  # noqa: E402

PAGE = """<!doctype html><html><body>
<h1>Formular</h1>
<label for="nume">Nume client</label><input id="nume">
<input type="hidden" name="secret" value="x">
<button data-testid="salveaza"><span>Salveaza</span></button>
<button style="display:none">Ascuns</button>
<a href="#ajutor">Ajutor</a>
<select id="tara"><option>Romania</option></select>
<label><input type="checkbox" id="accept"> Accept termenii</label>
<iframe id="cadru" srcdoc="<input id='in_cadru' placeholder='in iframe'>"></iframe>
</body></html>"""


def _obj(name, site="app.local", kind=LocatorKind.Id, value="x", frame=None):
    return UiObject(name=name, technology=UiTechnology.Web, site=site, context=f"https://{site}/pagina",
                    locators=[Locator(kind, value, 90)], frame_path=frame or [])


class LibraryPathTests(unittest.TestCase):
    def test_app_name_from_url(self):
        self.assertEqual("app.local", scan.app_name_from_url("https://www.app.local/x/y?z=1"))
        self.assertEqual("intranet", scan.app_name_from_url("http://intranet:8080/"))
        self.assertEqual("Aplicatie", scan.app_name_from_url("nu e adresa"))

    def test_suggest_path_in_onedrive(self):
        od = tempfile.mkdtemp(prefix="od_")
        with mock.patch.dict(os.environ, {"OneDriveCommercial": od, "OneDrive": "", "OneDriveConsumer": ""}):
            p = scan.suggest_library_path("app.local")
        self.assertEqual(os.path.join(od, "AutoPilotDC", "obiecte", "app.local", "obiecte.json"), p)

    def test_resolve_path_from_other_laptop(self):
        od = tempfile.mkdtemp(prefix="od_")
        real = os.path.join(od, "AutoPilotDC", "obiecte", "app", "obiecte.json")
        os.makedirs(os.path.dirname(real))
        RepositoryStore.save(ObjectRepository(objects=[_obj("Buton_OK")]), real)
        other = r"C:\Users\alt_utilizator\OneDrive - Firma\AutoPilotDC\obiecte\app\obiecte.json"
        with mock.patch.dict(os.environ, {"OneDriveCommercial": od}):
            self.assertEqual(real, scan.resolve_library_path(other))
            self.assertEqual(["Buton_OK"], [o.name for o in RepositoryStore.load(other).objects])
        self.assertEqual("", scan.resolve_library_path(""))

    def test_routine_keeps_library_path(self):
        d = tempfile.mkdtemp()
        r = Routine(name="R")
        r.repository_path = os.path.join(d, "obiecte.json")
        p = os.path.join(d, "r.rpr.json")
        RoutineStore.save(r, p)
        self.assertEqual(r.repository_path, RoutineStore.load(p).repository_path)


class NewObjectsTests(unittest.TestCase):
    def test_skips_existing_and_duplicates(self):
        repo = ObjectRepository(objects=[_obj("Buton_OK", value="ok")])
        scanned = [_obj("Buton_OK", value="ok"), _obj("Camp_Nume", value="nume"), _obj("Camp_Nume", value="nume"),
                   _obj("Alt_site", site="alt.local", value="ok"), _obj("In_cadru", value="ok", frame=["#cadru"])]
        fresh, existing = scan.new_objects(repo, scanned)
        self.assertEqual(1, existing)
        self.assertEqual(["Camp_Nume", "Alt_site", "In_cadru"], [o.name for o in fresh])
        self.assertEqual(3, scan.add_objects(repo, fresh))
        self.assertEqual(4, len(repo.objects))

    def test_object_without_locator_is_ignored(self):
        o = _obj("Gol")
        o.locators[0].enabled = False
        self.assertEqual(([], 0), scan.new_objects(ObjectRepository(), [o]))


def _available():
    try:
        import playwright  # noqa: F401
        return True
    except ImportError:
        return False


@unittest.skipUnless(_available(), "playwright nu e instalat")
class WebScanTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from rpr.drivers.web import PlaywrightDriver, WebSettings
        cls.tmp = tempfile.mkdtemp(prefix="apdc_scan_")
        path = os.path.join(cls.tmp, "test.html")
        with open(path, "w", encoding="utf-8") as f:
            f.write(PAGE)
        cls.driver = PlaywrightDriver(WebSettings(browser=os.environ.get("APDC_TEST_BROWSER", "Edge"), headless=True))
        try:
            cls.driver.open("file:///" + path.replace("\\", "/"))
        except Exception as ex:  # noqa: BLE001
            raise unittest.SkipTest(f"browserul nu porneste: {ex}")

    @classmethod
    def tearDownClass(cls):
        cls.driver.close()

    def test_scan_finds_visible_fields_and_buttons(self):
        objs = self.driver.scan_page()
        names = [o.name for o in objs]
        best = {o.name: next(l for l in o.locators if l.enabled) for o in objs}
        self.assertIn("Camp_Nume_client", names)
        self.assertIn("Buton_Salveaza", names)
        self.assertIn("Link_Ajutor", names)
        self.assertTrue(any(n.startswith("Lista") for n in names))
        self.assertTrue(any(n.startswith("Bifa") for n in names))
        self.assertNotIn("Buton_Ascuns", names)                      # ascuns: nu
        self.assertFalse(any("secret" in n for n in names))          # hidden: nu
        self.assertEqual(LocatorKind.TestId, best["Buton_Salveaza"].kind)
        cadru = [o for o in objs if o.frame_path]
        self.assertEqual(["#cadru"], cadru[0].frame_path)             # si din iframe
        self.assertEqual(1, names.count("Buton_Salveaza"))            # span-ul din buton nu e dublura

    def test_scan_limit(self):
        self.assertEqual(2, len(self.driver.scan_page(max_items=2)))

    def test_hover_capture_after_three_seconds(self):
        got = []
        self.driver.start_hover_capture(got.append)
        try:
            box = self.driver._call(lambda: self.driver._page.locator("#nume").bounding_box())
            x, y = box["x"] + 5, box["y"] + 5
            self.driver._call(lambda: self.driver._page.mouse.move(x, y))
            self.driver._call(lambda: self.driver._page.mouse.move(x + 2, y + 1))
            time.sleep(1.5)
            self.assertEqual([], got)                                   # inca nu: abia 1,5 s
            end = time.monotonic() + 6
            while not got and time.monotonic() < end:
                time.sleep(0.1)
            self.assertEqual(1, len(got))
            self.assertEqual("Camp_Nume_client", got[0].name)
            # cursorul ramane pe acelasi element: nu se captureaza din nou
            time.sleep(3.5)
            self.assertEqual(1, len(got))
            # Esc in browser = gata (on_object(None))
            self.driver._call(lambda: self.driver._page.keyboard.press("Escape"))
            end = time.monotonic() + 3
            while (len(got) < 2) and time.monotonic() < end:
                time.sleep(0.1)
            self.assertIsNone(got[-1])
            self.assertFalse(self.driver.is_hover_capturing)
        finally:
            self.driver.stop_hover_capture()


CHECK_PAGE = """<!doctype html><html><body>
<script>window.clicks = 0;</script>
<button id="ok" onclick="window.clicks++">Salveaza</button>
<button id="gri" disabled>Trimite</button>
<button id="sub" onclick="window.clicks++">Sub overlay</button>
<div id="ov" style="position:fixed;left:0;top:0;width:100%;height:100%;display:none"></div>
<button class="dublu">A</button><button class="dublu">A</button>
<input id="citire" readonly value="x">
</body></html>"""


def _wobj(name, *locs, typ="Buton", et="button", text=""):
    return UiObject(name=name, technology=UiTechnology.Web, object_type=typ, element_type=et, captured_text=text,
                    locators=[Locator(k, v, 90) for k, v in locs])


class DiagnoseTests(unittest.TestCase):
    def test_fix_and_recapture_keep_name(self):
        o = _wobj("Buton_X", (LocatorKind.Id, "vechi"), (LocatorKind.Text, "X"))
        used = o.locators[1]
        self.assertTrue(scan.fix_locators(o, used))
        self.assertIs(used, o.locators[0])
        self.assertFalse(scan.fix_locators(o, used))
        new = _wobj("Buton_Nou", (LocatorKind.Css, "#nou"))
        o.parent, o.page = "Formular", "/app"
        scan.apply_recapture(o, new)
        self.assertEqual(("Buton_X", "Formular", "/app"), (o.name, o.parent, o.page))
        self.assertEqual("#nou", o.locators[0].value)

    def test_objects_to_check_by_page(self):
        repo = ObjectRepository(objects=[])
        a, b = _wobj("A", (LocatorKind.Id, "a")), _wobj("B", (LocatorKind.Id, "b"))
        a.page, b.page = "/app/comenzi", "/app/clienti"
        repo.objects += [a, b]
        url = "https://app.local/app/comenzi/123"
        self.assertEqual(["A"], [o.name for o in scan.objects_to_check(repo, url)])
        self.assertEqual(["A", "B"], [o.name for o in scan.objects_to_check(repo, url, whole_site=True)])

    def test_other_page_is_not_remap(self):
        o = _wobj("B", (LocatorKind.Id, "b"))
        o.page = "/app/clienti"
        st, _ = scan.diagnose(o, {"found": False, "counts": []}, "https://app.local/app/comenzi")
        self.assertEqual(scan.OTHER_PAGE, st)


@unittest.skipUnless(_available(), "playwright nu e instalat")
class WebCheckTests(unittest.TestCase):
    """Verificarea fara click pe o pagina reala: nimic nu e apasat."""

    @classmethod
    def setUpClass(cls):
        from rpr.drivers.web import PlaywrightDriver, WebSettings
        cls.tmp = tempfile.mkdtemp(prefix="apdc_check_")
        path = os.path.join(cls.tmp, "check.html")
        with open(path, "w", encoding="utf-8") as f:
            f.write(CHECK_PAGE)
        cls.url = "file:///" + path.replace("\\", "/")
        cls.driver = PlaywrightDriver(WebSettings(browser=os.environ.get("APDC_TEST_BROWSER", "Edge"), headless=True))
        try:
            cls.driver.open(cls.url)
        except Exception as ex:  # noqa: BLE001
            raise unittest.SkipTest(f"browserul nu porneste: {ex}")

    @classmethod
    def tearDownClass(cls):
        cls.driver.close()

    def _check(self, obj, overlay=False):
        self.driver._call(lambda: self.driver._page.evaluate(
            f"document.getElementById('ov').style.display = '{'block' if overlay else 'none'}'"))
        res = self.driver.check_object(obj, 600)
        return scan.diagnose(obj, res, self.url)

    def test_ok_without_click(self):
        st, why = self._check(_wobj("Buton_Salveaza", (LocatorKind.Id, "ok"), text="Salveaza"))
        self.assertEqual((scan.OK, []), (st, why))
        self.assertEqual(0, self.driver._call(lambda: self.driver._page.evaluate("window.clicks")))

    def test_missing_needs_remap(self):
        st, why = self._check(_wobj("Buton_Disparut", (LocatorKind.Id, "nu_exista")))
        self.assertEqual(scan.REMAP, st)

    def test_fallback_locator(self):
        o = _wobj("Buton_Salveaza", (LocatorKind.Id, "vechi_id"), (LocatorKind.Text, "Salveaza"))
        st, why = self._check(o)
        self.assertEqual(scan.WARN, st)
        self.assertIn("Repara locatorii", why[0])

    def test_disabled_covered_ambiguous_readonly(self):
        st, why = self._check(_wobj("Buton_Trimite", (LocatorKind.Id, "gri")))
        self.assertEqual(scan.WARN, st)
        self.assertTrue(any("dezactivat" in w for w in why), why)
        st, why = self._check(_wobj("Buton_Sub", (LocatorKind.Id, "sub")), overlay=True)
        self.assertEqual(scan.WARN, st)
        self.assertTrue(any("Acoperit" in w and "ov" in w for w in why), why)
        self.assertEqual(0, self.driver._call(lambda: self.driver._page.evaluate("window.clicks")))
        st, why = self._check(_wobj("Buton_A", (LocatorKind.Css, ".dublu")))
        self.assertTrue(any("2 elemente" in w for w in why), why)
        st, why = self._check(_wobj("Camp_Citire", (LocatorKind.Id, "citire"), typ="Camp text", et="input"))
        self.assertTrue(any("scriere" in w for w in why), why)


class FolderTests(unittest.TestCase):
    """v4.11: foldere in biblioteca (Site · Pagina · Folder · obiect)."""

    def _repo(self):
        a = _wobj("Buton_Import", (LocatorKind.Id, "a"))
        b = _wobj("Buton_Valideaza", (LocatorKind.Id, "b"))
        c = _wobj("Buton_Export", (LocatorKind.Id, "c"))
        d = _wobj("Buton_Fara_Folder", (LocatorKind.Id, "d"))
        a.folder, b.folder, c.folder = "Comenzi/Import", " Comenzi \\ Import/", "Comenzi/Export"
        return ObjectRepository(objects=[a, b, c, d])

    def test_normalize_and_parts(self):
        self.assertEqual("Comenzi/Export", scan.normalize_folder(" Comenzi \\ Export/ "))
        self.assertEqual([], scan.folder_parts(""))
        self.assertEqual(["Comenzi", "Import"], scan.folder_parts(self._repo().objects[1]))

    def test_all_folders_include_parents(self):
        self.assertEqual(["Comenzi", "Comenzi/Export", "Comenzi/Import"], scan.all_folders(self._repo()))

    def test_in_folder_includes_subfolders(self):
        repo = self._repo()
        self.assertEqual(["Buton_Import", "Buton_Valideaza", "Buton_Export"],
                         [o.name for o in repo.objects if scan.in_folder(o, "Comenzi")])
        self.assertEqual(["Buton_Export"], [o.name for o in repo.objects if scan.in_folder(o, "comenzi/export")])
        self.assertFalse(scan.in_folder(repo.objects[3], "Comenzi"))

    def test_rename_folder_renames_subfolders_too(self):
        repo = self._repo()
        n = scan.rename_folder(repo.objects, "Comenzi", "Orders")
        self.assertEqual(3, n)
        self.assertEqual(["Orders/Import", "Orders/Import", "Orders/Export", ""], [o.folder for o in repo.objects])
        scan.rename_folder(repo.objects, "Orders/Export", "Iesire")
        self.assertEqual("Orders/Iesire", repo.objects[2].folder)

    def test_rename_page_and_site(self):
        repo = self._repo()
        repo.objects[0].site = repo.objects[1].site = "app.local"
        repo.sites.append(SiteGroup(name="app.local"))
        self.assertEqual(2, scan.rename_page(repo.objects[:2], " Principal "))
        self.assertEqual(["Principal", "Principal"], [o.page for o in repo.objects[:2]])
        self.assertEqual(2, scan.rename_site(repo, repo.objects[:2], "app.local", "Comenzi"))
        self.assertEqual(["Comenzi", "Comenzi"], [o.site for o in repo.objects[:2]])
        self.assertIsNotNone(repo.find_site("Comenzi"))

    def test_folder_survives_save_and_load(self):
        path = os.path.join(tempfile.mkdtemp(prefix="apdc_fold_"), "obiecte.json")
        RepositoryStore.save(self._repo(), path)
        loaded = RepositoryStore.load(path)
        self.assertEqual("Comenzi/Export", next(o for o in loaded.objects if o.name == "Buton_Export").folder)
        import json
        with open(path, encoding="utf-8") as f:   # cheia noua e doar un camp in plus (C# il ignora)
            self.assertIn("folder", json.dumps(json.load(f)))


if __name__ == "__main__":
    unittest.main()
