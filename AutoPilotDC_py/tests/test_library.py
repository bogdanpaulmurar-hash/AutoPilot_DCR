# -*- coding: utf-8 -*-
# ============================================================
# AutoPilot DC — Teste biblioteca de obiecte (v4.5): site / pagina / container / link-uri similare.
# Partea web (cautare in container) se sare daca playwright / Edge nu sunt disponibile.
#   Rulare:  py -m unittest tests.test_library
# ============================================================

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rpr import (ActionNode, DriverProvider, ErrorPolicy, Locator, LocatorKind, ObjectRepository,  # noqa: E402
                 Routine, RprAction, RprEngine, RunHost, UiObject, UiTechnology)
from rpr.model import SiteGroup, guess_object_type, split_url, url_matches  # noqa: E402


def _obj(name, css="", **kw):
    return UiObject(name=name, locators=[Locator(LocatorKind.Css, css or "#" + name, 70)], **kw)


class LibraryModelTests(unittest.TestCase):
    def test_url_matches(self):
        self.assertTrue(url_matches("https://portal.x.com/app/orders?id=3", ["portal.x.com/app"]))
        self.assertTrue(url_matches("http://test.x.com/app/a", ["*.x.com/app/*"]))
        self.assertFalse(url_matches("https://portal.x.com/application", ["portal.x.com/app"]))
        self.assertFalse(url_matches("https://other.com/app", ["portal.x.com"]))

    def test_split_url_skips_ids(self):
        self.assertEqual(("portal.x.com", "/app/orders"), split_url("https://Portal.X.com/app/orders/12345?a=1"))
        self.assertEqual(("x.com", "/client"), split_url("https://x.com/client/123/edit"))
        self.assertEqual(("x.com", "/"), split_url("https://x.com"))

    def test_guess_type(self):
        self.assertEqual("Buton", guess_object_type("button"))
        self.assertEqual("Camp text", guess_object_type("input (textbox)"))
        self.assertEqual("ComboBox / lista derulanta", guess_object_type("select"))
        self.assertEqual("Tabel / grid", guess_object_type("table"))
        self.assertEqual("Checkbox / radio", guess_object_type("input", {"type": "checkbox"}))

    def test_classify_uses_site_groups(self):
        repo = ObjectRepository()
        repo.sites.append(SiteGroup(name="Portal", url_patterns=["portal-test.x.com", "portal.x.com"]))
        o = _obj("Salveaza", context="https://portal-test.x.com/app/orders/77", element_type="button")
        repo.classify(o)
        self.assertEqual(("Portal", "/app/orders", "Buton"), (o.site, o.page, o.object_type))
        # sistem similar (productie) -> valid; alt site -> nu
        self.assertTrue(repo.valid_on(o, "https://portal.x.com/app/orders/1"))
        self.assertFalse(repo.valid_on(o, "https://alt.com/"))
        # fara grup: domeniul devine site
        o2 = _obj("B", context="https://alt.com/p/q", element_type="a")
        repo.classify(o2)
        self.assertEqual(("alt.com", "/p/q", "Link"), (o2.site, o2.page, o2.object_type))
        self.assertTrue(repo.valid_on(o2, "https://oriunde.com"))   # fara sabloane = oriunde

    def test_containers_chain_and_remove(self):
        repo = ObjectRepository()
        repo.add(_obj("Formular", object_type="Formular"))
        repo.add(_obj("Sectiune", object_type="Container / sectiune", parent="Formular"))
        btn = repo.add(_obj("Buton", object_type="Buton", parent="Sectiune"))
        self.assertTrue(repo.find("Formular").is_container)
        self.assertEqual(["Sectiune", "Formular"], [p.name for p in repo.parent_chain(btn)])
        repo.link_parents(btn)
        self.assertEqual("Sectiune", btn.parent_ref.name)
        self.assertEqual("Formular", btn.parent_ref.parent_ref.name)
        repo.rename_parent_refs("Sectiune", "Zona")
        self.assertEqual("Zona", btn.parent)
        repo.find("Sectiune").name = "Zona"
        repo.remove(repo.find("Zona"))
        self.assertEqual("Formular", btn.parent)   # urca la containerul de deasupra

    def test_cycle_is_safe(self):
        repo = ObjectRepository()
        a = repo.add(_obj("A", object_type="Formular", parent="B"))
        repo.add(_obj("B", object_type="Formular", parent="A"))
        self.assertEqual(["B"], [p.name for p in repo.parent_chain(a)])

    def test_json_roundtrip(self):
        repo = ObjectRepository()
        repo.sites.append(SiteGroup(name="Portal", url_patterns=["portal.x.com"]))
        repo.add(_obj("Buton", object_type="Buton", site="Portal", page="/a", parent="Sec",
                      url_patterns=["portal.x.com/a"], tags=["login"]))
        repo.link_parents(repo.find("Buton"))
        back = ObjectRepository.from_dict(repo.to_dict())
        b = back.find("Buton")
        self.assertEqual(("Buton", "Portal", "/a", "Sec", ["portal.x.com/a"], ["login"]),
                         (b.object_type, b.site, b.page, b.parent, b.url_patterns, b.tags))
        self.assertEqual("Portal", back.sites[0].name)
        self.assertNotIn("parent_ref", repo.to_dict()["objects"][0])

    def test_old_repository_still_loads(self):
        back = ObjectRepository.from_dict({"version": 1, "objects": [
            {"name": "Vechi", "technology": "Web", "locators": [{"kind": "Css", "value": "#x", "score": 50}]}]})
        o = back.find("Vechi")
        self.assertEqual(("", "", ""), (o.site, o.parent, o.object_type))
        self.assertEqual([], back.sites)


PAGE = """<!doctype html><html><head><meta charset="utf-8"></head><body>
<section id="facturare"><h2>Facturare</h2><input class="oras"><button class="salveaza"
  onclick="document.getElementById('rez').textContent='facturare'">Salveaza</button></section>
<section id="livrare"><h2>Livrare</h2><input class="oras"><button class="salveaza"
  onclick="document.getElementById('rez').textContent='livrare'">Salveaza</button></section>
<div id="rez"></div></body></html>"""


class Host(RunHost):
    def __init__(self):
        self.lines = []

    def log(self, e):
        self.lines.append(str(e))


def _playwright():
    try:
        import playwright  # noqa: F401
        return True
    except ImportError:
        return False


@unittest.skipUnless(_playwright(), "playwright nu e instalat")
class LibraryWebTests(unittest.TestCase):
    """Acelasi buton in doua sectiuni: containerul decide pe care se da click."""

    @classmethod
    def setUpClass(cls):
        from rpr.drivers.web import PlaywrightDriver, WebSettings
        cls.tmp = tempfile.mkdtemp(prefix="apdc_lib_")
        path = os.path.join(cls.tmp, "lib.html")
        with open(path, "w", encoding="utf-8") as f:
            f.write(PAGE)
        cls.url = "file:///" + path.replace("\\", "/")
        cls.driver = PlaywrightDriver(WebSettings(browser=os.environ.get("APDC_TEST_BROWSER", "Edge"), headless=True))
        try:
            cls.driver.open(cls.url)
        except Exception as ex:  # noqa: BLE001
            raise unittest.SkipTest(f"browserul nu porneste: {ex}")
        repo = ObjectRepository()
        repo.add(_obj("Sectiune_Livrare", "#livrare", object_type="Container / sectiune"))
        repo.add(_obj("Sectiune_Facturare", "#facturare", object_type="Container / sectiune"))
        repo.add(_obj("Salveaza_Livrare", "button.salveaza", object_type="Buton", parent="Sectiune_Livrare"))
        repo.add(_obj("Oras_Livrare", "input.oras", object_type="Camp text", parent="Sectiune_Livrare"))
        repo.add(UiObject(name="Salveaza_XPath", parent="Sectiune_Livrare",
                          locators=[Locator(LocatorKind.XPath, "//button[contains(@class,'salveaza')]", 50)]))
        cls.repo = repo

    @classmethod
    def tearDownClass(cls):
        cls.driver.close()

    def _run(self, *steps):
        r = Routine(name="Test biblioteca")
        r.settings.auto_retries = 0
        r.settings.default_error_policy = ErrorPolicy.Stop
        r.settings.guard_enabled = False
        r.settings.highlight_before_action = False
        r.steps.extend(steps)
        host = Host()
        engine = RprEngine(self.repo, DriverProvider({UiTechnology.Web: lambda: self.driver}), host, self.tmp)
        return engine.run(r), host

    def test_click_inside_container(self):
        res, host = self._run(
            ActionNode(action=RprAction.Navigate, value=self.url),
            ActionNode(action=RprAction.TypeText, target="Oras_Livrare", value="Cluj"),
            ActionNode(action=RprAction.Click, target="Salveaza_Livrare"),
            ActionNode(action=RprAction.ReadText, target="Sectiune_Livrare", output_variable="dummy"),
        )
        self.assertTrue(res.success, res.message + "\n" + "\n".join(host.lines[-6:]))
        st = self.driver.get_state(UiObject(name="rez", locators=[Locator(LocatorKind.Css, "#rez", 50)]), 1000, None)
        self.assertEqual("livrare", st.text)

    def test_xpath_is_relative_to_container(self):
        res, host = self._run(ActionNode(action=RprAction.Navigate, value=self.url),
                              ActionNode(action=RprAction.Click, target="Salveaza_XPath"))
        self.assertTrue(res.success, res.message + "\n" + "\n".join(host.lines[-6:]))
        st = self.driver.get_state(UiObject(name="rez", locators=[Locator(LocatorKind.Css, "#rez", 50)]), 1000, None)
        self.assertEqual("livrare", st.text)

    def test_test_object_counts(self):
        self.driver.open(self.url)
        obj = self.repo.link_parents(self.repo.find("Salveaza_Livrare"))
        res = self.driver.test_object(obj)
        self.assertTrue(res["found"])
        self.assertEqual("Sectiune_Livrare", res["container"])
        self.assertTrue(res["container_found"])
        self.assertEqual(1, res["rows"][0]["in_container"])
        self.assertEqual(2, res["rows"][0]["in_page"])

    def test_element_inside(self):
        self.driver.open(self.url)
        child = _obj("Oras_Unic", "#livrare input.oras")
        self.assertTrue(self.driver.element_inside(self.repo.find("Sectiune_Livrare"), child))
        self.assertFalse(self.driver.element_inside(self.repo.find("Sectiune_Facturare"), child))
