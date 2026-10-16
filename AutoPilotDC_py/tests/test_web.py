# -*- coding: utf-8 -*-
# ============================================================
# AutoPilot DC — Teste driver Web (Playwright) pe o pagina locala, browser fara fereastra.
# Se sar automat daca playwright / Edge nu sunt disponibile.
#   Rulare:  py -m unittest tests.test_web
# ============================================================

import os
import sys
import tempfile
import threading
import time
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rpr import (ActionNode, Condition, ConditionKind, DriverProvider, ErrorPolicy, IfNode, Locator,  # noqa: E402
                 LocatorKind, ObjectRepository, Routine, RprAction, RprEngine, RunHost, SetVariableNode, UiObject,
                 UiTechnology, WaitMode, WaitNode)

PAGE = """<!doctype html><html><head><meta charset="utf-8"><title>Pagina test AutoPilot</title></head><body>
<h1>Formular test</h1>
<label for="nume">Nume client</label><input id="nume" name="nume" placeholder="Scrie numele">
<button data-testid="salveaza" onclick="setTimeout(()=>{document.getElementById('mesaj').textContent='Salvat: '+document.getElementById('nume').value},300)">Salveaza</button>
<div id="mesaj" role="status"></div>
<select id="tara"><option value="ro">Romania</option><option value="de">Germania</option></select>
<label><input type="checkbox" id="accept"> Accept termenii</label>
<iframe id="cadru" srcdoc="<input id='in_cadru' placeholder='in iframe'><span id='ecou'></span><script>document.getElementById('in_cadru').oninput=e=>document.getElementById('ecou').textContent=e.target.value</script>"></iframe>
</body></html>"""


class Host(RunHost):
    def __init__(self):
        self.lines = []

    def log(self, e):
        self.lines.append(str(e))


def _available():
    try:
        import playwright  # noqa: F401
        return True
    except ImportError:
        return False


@unittest.skipUnless(_available(), "playwright nu e instalat")
class WebDriverTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from rpr.drivers.web import PlaywrightDriver, WebSettings
        cls.tmp = tempfile.mkdtemp(prefix="apdc_web_")
        cls.page_path = os.path.join(cls.tmp, "test.html")
        with open(cls.page_path, "w", encoding="utf-8") as f:
            f.write(PAGE)
        cls.url = "file:///" + cls.page_path.replace("\\", "/")
        cls.driver = PlaywrightDriver(WebSettings(browser=os.environ.get("APDC_TEST_BROWSER", "Edge"), headless=True))
        try:
            cls.driver.open(cls.url)
        except Exception as ex:  # noqa: BLE001
            raise unittest.SkipTest(f"browserul nu porneste: {ex}")

        repo = ObjectRepository()
        add = lambda name, *locs, frame=None: repo.add(UiObject(  # noqa: E731
            name=name, locators=[Locator(k, v, s) for k, v, s in locs], frame_path=frame or []))
        add("Camp_Nume", (LocatorKind.Label, "Nume client", 80), (LocatorKind.Id, "nume", 90))
        add("Buton_Salveaza", (LocatorKind.Id, "nu_exista", 95), (LocatorKind.TestId, "[data-testid='salveaza']", 90))
        add("Mesaj", (LocatorKind.Role, "status", 60))
        add("Lista_Tara", (LocatorKind.Css, "#tara", 70))
        add("Bifa_Accept", (LocatorKind.Css, "#accept", 70))
        add("Camp_Cadru", (LocatorKind.Placeholder, "in iframe", 70), frame=["#cadru"])
        add("Ecou_Cadru", (LocatorKind.Css, "#ecou", 70), frame=["#cadru"])
        cls.repo = repo

    @classmethod
    def tearDownClass(cls):
        cls.driver.close()

    def _engine(self):
        provider = DriverProvider({UiTechnology.Web: lambda: self.driver})
        host = Host()
        return RprEngine(self.repo, provider, host, self.tmp), host

    def _routine(self, *steps):
        r = Routine(name="Test web")
        r.settings.highlight_before_action = True
        r.settings.highlight_ms = 150
        r.settings.auto_retries = 0
        r.settings.default_error_policy = ErrorPolicy.Stop
        r.settings.guard_enabled = False
        r.steps.extend(steps)
        return r

    def test_full_routine_on_page(self):
        engine, host = self._engine()
        r = self._routine(
            ActionNode(action=RprAction.Navigate, value=self.url),
            ActionNode(action=RprAction.TypeText, target="Camp_Nume", value="{Client}"),
            ActionNode(action=RprAction.Click, target="Buton_Salveaza"),   # primul locator gresit -> self-healing
            WaitNode(mode=WaitMode.UntilTrue, timeout_ms=5000,
                     condition=Condition(kind=ConditionKind.ElementText, target="Mesaj", right="Salvat",
                                         operator="Contains")),
            ActionNode(action=RprAction.ReadText, target="Mesaj", output_variable="Mesaj",
                       expected_value="Salvat: *"),
            ActionNode(action=RprAction.SelectOption, target="Lista_Tara", value="Germania"),
            ActionNode(action=RprAction.ReadValue, target="Lista_Tara", output_variable="Tara"),
            ActionNode(action=RprAction.Check, target="Bifa_Accept"),
            ActionNode(action=RprAction.TypeText, target="Camp_Cadru", value="salut din iframe"),
            ActionNode(action=RprAction.ReadText, target="Ecou_Cadru", output_variable="Ecou"),
            ActionNode(action=RprAction.PressKey, value="Tab"),
        )
        r.variables["Client"] = "Ion Popescu"
        result = engine.run(r)
        self.assertTrue(result.success, result.message + "\n" + "\n".join(host.lines[-8:]))
        v = result.final_variables
        self.assertEqual("Salvat: Ion Popescu", v["Mesaj"])
        self.assertEqual("de", v["Tara"])
        self.assertEqual("salut din iframe", v["Ecou"])

    def test_missing_element_fails_with_clear_message(self):
        engine, _ = self._engine()
        self.repo.add(UiObject(name="Fantoma", locators=[Locator(LocatorKind.Id, "nu_e_aici", 90)]))
        result = engine.run(self._routine(ActionNode(action=RprAction.Click, target="Fantoma", timeout_ms=500)))
        self.assertFalse(result.success)
        self.assertIn("Fantoma", result.message)
        self.assertIn("nu a fost gasit", result.message)

    def test_condition_exists(self):
        engine, _ = self._engine()
        i = IfNode(condition=Condition(kind=ConditionKind.ElementVisible, target="Buton_Salveaza", timeout_ms=1000))
        i.then.append(SetVariableNode(name="Ramura", value="vizibil"))
        i.else_.append(SetVariableNode(name="Ramura", value="lipsa"))
        result = engine.run(self._routine(i))
        self.assertEqual("vizibil", result.final_variables["Ramura"])

    def test_spy_captures_clicked_element(self):
        """Spy: click (simulat in browser) pe camp -> obiect cu locatori verificati."""
        box = {}
        t = threading.Thread(target=lambda: box.setdefault("obj", self.driver.capture_object("test", self.tmp)))
        t.start()
        time.sleep(1.0)

        def click_field():
            page = self.driver._page
            b = page.locator("#nume").bounding_box()
            page.mouse.move(b["x"] + 5, b["y"] + 5)
            page.mouse.click(b["x"] + 5, b["y"] + 5)
        self.driver._call(click_field)
        t.join(15)
        obj = box.get("obj")
        self.assertIsNotNone(obj, "Spy nu a capturat elementul")
        kinds = {l.kind for l in obj.locators if l.enabled}
        self.assertIn(LocatorKind.Id, kinds)
        self.assertTrue(obj.name)
        self.assertTrue(obj.screenshot)

    def test_recorder_turns_browser_actions_into_steps(self):
        got = []
        self.driver._call(lambda: self.driver._page.goto(self.url))
        self.driver.start_recording(got.append)

        def act():
            page = self.driver._page
            page.locator("#nume").fill("Maria")
            page.locator("#nume").dispatch_event("change")
            b = page.locator("[data-testid='salveaza']").bounding_box()
            page.mouse.click(b["x"] + 4, b["y"] + 4)
            page.locator("#tara").select_option("ro")
        self.driver._call(act)
        time.sleep(1.0)   # evenimentele se proceseaza intre comenzi
        self.driver.stop_recording()
        actions = [(a.action, a.value) for a in got]
        self.assertIn((RprAction.TypeText, "Maria"), actions)
        self.assertTrue(any(a == RprAction.Click for a, _ in actions), actions)
        self.assertTrue(any(a == RprAction.SelectOption for a, _ in actions), actions)


if __name__ == "__main__":
    unittest.main()
