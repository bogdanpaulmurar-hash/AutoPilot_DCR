# -*- coding: utf-8 -*-
# ============================================================
# AutoPilot DC — Teste: 🤖 Asistent AI (v4.30)
#   Rulare:  py -m unittest tests.test_assistant
# Fara AI real: un server HTTP local imita API-ul Anthropic si pe cel compatibil OpenAI.
# ============================================================

import glob
import json
import os
import sys
import tempfile
import threading
import unittest
import zipfile
from http.server import BaseHTTPRequestHandler, HTTPServer
from unittest import mock

APP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, APP)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from rpr import assistant as ai  # noqa: E402
from rpr.importer import StepImporter, ai_prompt  # noqa: E402
from rpr.model import (ActionNode, IfNode, ObjectRepository, Routine, RprAction, UiObject,  # noqa: E402
                       Locator, LocatorKind, UiTechnology)
from rpr.storage import RoutineStore  # noqa: E402
from rpr.host import RunLogEntry  # noqa: E402
from rpr.model import RprLogLevel  # noqa: E402

GOOD = "Iata:\n```text\nRUTINA: Test\nDESCHIDE BROWSER https://x.ro\nCLICK buton \"Salveaza\"\n```\nDE VERIFICAT: nimic"
BAD = "```text\nRUTINA: Test\nDESCHIDE BROWSER https://x.ro\nAPASA PE BUTONUL MARE\nCLICKK buton \"Salveaza\"\n```"


class FakeTransport:
    """Raspunsuri pe rand; tine minte cererile."""

    def __init__(self, provider, answers):
        self.provider, self.answers, self.calls = provider, list(answers), []

    def __call__(self, url, headers, body, timeout, ctx):
        self.calls.append((url, headers, json.loads(body.decode("utf-8"))))
        text = self.answers.pop(0)
        if self.provider == "anthropic":
            return {"content": [{"type": "text", "text": text}]}
        return {"choices": [{"message": {"content": text}}]}


def _settings(provider="anthropic", **kw):
    return ai.AiSettings(provider=provider, model="model-mic", **kw)


class ConnectionTests(unittest.TestCase):
    def test_settings_roundtrip_without_key(self):
        d = tempfile.mkdtemp()
        p = os.path.join(d, "s.json")
        s = _settings("openai", url="https://gw.firma/v1", ca_file="C:\\ca.pem")
        s.save(p)
        with open(p, encoding="utf-8") as f:
            raw = f.read()
        self.assertNotIn("key\":", raw.replace("key_env", ""))
        t = ai.AiSettings.load(p)
        self.assertEqual(("openai", "https://gw.firma/v1", "model-mic"), (t.provider, t.url, t.model))
        self.assertTrue(t.connected)
        self.assertFalse(ai.AiSettings.load(os.path.join(d, "lipsa.json")).connected)

    def test_key_from_environment(self):
        s = _settings(key_env="AP_TEST_KEY")
        with mock.patch.dict(os.environ, {"AP_TEST_KEY": "  sk-123 "}):
            self.assertEqual("sk-123", ai.get_key(s))
            self.assertEqual("env", ai.key_source(s))

    def test_endpoints_and_headers(self):
        a = _settings("anthropic")
        self.assertEqual("https://api.anthropic.com/v1/messages", ai.endpoint(a))
        a.url = "https://gw.firma/anthropic/v1"
        self.assertEqual("https://gw.firma/anthropic/v1/messages", ai.endpoint(a))
        url, h, body = ai.build_request(a, "SYS", [{"role": "user", "content": "q"}], "k1")
        b = json.loads(body)
        self.assertEqual(("k1", "2023-06-01"), (h["x-api-key"], h["anthropic-version"]))
        self.assertEqual("SYS", b["system"])
        self.assertEqual([{"role": "user", "content": "q"}], b["messages"])

        o = _settings("openai", url="https://gw.firma/v1/")
        self.assertEqual("https://gw.firma/v1/chat/completions", ai.endpoint(o))
        az = "https://x.openai.azure.com/openai/deployments/d/chat/completions?api-version=2024-02-01"
        o2 = _settings("openai", url=az, auth_header="api-key")
        self.assertEqual(az, ai.endpoint(o2))
        url, h, body = ai.build_request(o2, "SYS", [{"role": "user", "content": "q"}], "k2")
        self.assertEqual("k2", h["api-key"])
        self.assertNotIn("Authorization", h)
        self.assertEqual({"role": "system", "content": "SYS"}, json.loads(body)["messages"][0])
        _, h, _ = ai.build_request(o, "S", [], "k3")
        self.assertEqual("Bearer k3", h["Authorization"])

    def test_parse_responses(self):
        self.assertEqual("ab", ai.parse_response("anthropic", {"content": [{"type": "text", "text": "a"},
                                                                          {"type": "tool_use"},
                                                                          {"type": "text", "text": "b"}]}))
        self.assertEqual("x", ai.parse_response("openai", {"choices": [{"message": {"content": "x"}}]}))
        self.assertEqual("y", ai.parse_response("openai", {"choices": [{"message": {"content": [{"text": "y"}]}}]}))
        with self.assertRaises(ai.AiError):
            ai.parse_response("openai", {"choices": [{"message": {"content": ""}}]})

    def test_not_configured(self):
        with self.assertRaises(ai.AiError):
            ai.AiClient(ai.AiSettings(), key="").complete("s", [])


class _Handler(BaseHTTPRequestHandler):
    seen = []

    def log_message(self, *a):
        pass

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        _Handler.seen.append((self.path, dict(self.headers), body))
        if self.headers.get("x-api-key") == "gresit" or self.headers.get("Authorization") == "Bearer gresit":
            self.send_response(401)
            self.end_headers()
            self.wfile.write(b'{"error": {"message": "invalid key"}}')
            return
        if self.path.endswith("/v1/messages"):
            out = {"content": [{"type": "text", "text": "Claude: " + body["messages"][-1]["content"][:20]}]}
        else:
            out = {"choices": [{"message": {"content": "GPT: " + body["messages"][-1]["content"][:20]}}]}
        data = json.dumps(out).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


class LocalServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = HTTPServer(("127.0.0.1", 0), _Handler)
        cls.base = f"http://127.0.0.1:{cls.srv.server_port}"
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        cls._env = mock.patch.dict(os.environ, {"NO_PROXY": "127.0.0.1", "no_proxy": "127.0.0.1"})
        cls._env.start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls._env.stop()

    def test_both_providers_over_http(self):
        c = ai.AiClient(_settings("anthropic", url=self.base), key="ok")
        self.assertEqual("Claude: Salut", c.complete("s", [{"role": "user", "content": "Salut"}]))
        c = ai.AiClient(_settings("openai", url=self.base + "/v1"), key="ok")
        self.assertEqual("GPT: Salut", c.complete("s", [{"role": "user", "content": "Salut"}]))
        path, headers, body = _Handler.seen[-1]
        self.assertEqual("/v1/chat/completions", path)
        self.assertEqual("model-mic", body["model"])

    def test_wrong_key_gives_clear_error(self):
        c = ai.AiClient(_settings("anthropic", url=self.base), key="gresit")
        with self.assertRaises(ai.AiError) as cm:
            c.test()
        self.assertIn("401", str(cm.exception))
        self.assertIn("cheia", str(cm.exception))

    def test_no_server(self):
        c = ai.AiClient(_settings("openai", url="http://127.0.0.1:9/v1", timeout=3), key="k")
        with self.assertRaises(ai.AiError):
            c.test()


class ContextTests(unittest.TestCase):
    def test_pick_chapters_by_question(self):
        ch = ai.load_chapters("ro")
        self.assertGreater(len(ch), 30)
        titles = [t for t, _ in ai.pick_chapters("cum repet pasii pentru fiecare rand din Excel", ch)]
        self.assertTrue(any("Excel" in t for t in titles), titles)
        self.assertLessEqual(sum(len(t) + len(b) for t, b in ai.pick_chapters("excel sap web rutina", ch)),
                             ai.DOC_BUDGET + 100)
        forced = [t for t, _ in ai.pick_chapters("xyz", ch, always=("19.",))]
        self.assertTrue(any("Probleme frecvente" in t for t in forced))

    def _routine(self):
        repo = ObjectRepository()
        repo.objects.append(UiObject(name="Buton_Salveaza", technology=UiTechnology.Web,
                                     locators=[Locator(LocatorKind.Css, "#save", 90)]))
        res = StepImporter(repo).parse('RUTINA: R1\nDESCHIDE BROWSER https://x.ro\nCLICK [Buton_Salveaza]\n'
                                       'DACA vizibil text "Eroare"\n  LOG "e"\nSFARSIT')
        return repo, res.routine

    def test_ask_context_has_routine_objects_and_errors(self):
        repo, r = self._routine()
        logs = [RunLogEntry(RprLogLevel.Info, message="ok"),
                RunLogEntry(RprLogLevel.Error, node_title="Click [Buton_Salveaza]", message="Elementul nu a fost gasit",
                            excel_row=4)]
        text = ai.ask_copy_text("de ce nu merge click-ul?", "ro", r, logs, ai.AiSettings(), repo=repo)
        self.assertIn("Esti asistentul aplicatiei AutoPilot DC", text)
        self.assertIn("RUTINA DESCHISA", text)
        self.assertIn("Click [Buton_Salveaza]", text)
        self.assertIn("Css=#save", text)
        self.assertIn("Elementul nu a fost gasit", text)
        self.assertIn("rand 4", text)
        self.assertNotIn("ok\n", text.split("ULTIMELE ERORI")[1])
        self.assertTrue(text.rstrip().endswith("de ce nu merge click-ul?"))
        s = ai.AiSettings(send_routine=False, send_errors=False)
        text = ai.ask_context("intrebare", "ro", r, logs, s, repo=repo)
        self.assertNotIn("RUTINA DESCHISA", text)
        self.assertNotIn("ULTIMELE ERORI", text)

    def test_ask_keeps_history(self):
        t = FakeTransport("openai", ["raspuns 2"])
        c = ai.AiClient(_settings("openai"), key="k", transport=t)
        hist = [{"role": "user", "content": "q1"}, {"role": "assistant", "content": "a1"}]
        self.assertEqual("raspuns 2", ai.ask(c, "q2", history=hist))
        msgs = t.calls[0][2]["messages"]
        self.assertEqual(["system", "user", "assistant", "user"], [m["role"] for m in msgs])

    def test_extract_text_block(self):
        self.assertEqual("CLICK a\nCLICK b", ai.extract_text_block("x\n```text\nCLICK a\n```\ny\n```\nCLICK b\n```"))
        self.assertEqual("", ai.extract_text_block("fara pasi"))


class MakeRoutineTests(unittest.TestCase):
    def test_good_answer_first_try(self):
        t = FakeTransport("anthropic", [GOOD])
        d = ai.make_routine(ai.AiClient(_settings(), key="k", transport=t), "Procedura: salveaza", ObjectRepository())
        self.assertTrue(d.result.ok)
        self.assertEqual(1, d.attempts)
        self.assertIn("COMENZI", t.calls[0][2]["system"])
        self.assertNotIn("PASTREAZA", t.calls[0][2]["system"])   # doar la reparare

    def test_errors_go_back_to_ai(self):
        t = FakeTransport("openai", [BAD, GOOD])
        steps = []
        d = ai.make_routine(ai.AiClient(_settings("openai"), key="k", transport=t), "Procedura", ObjectRepository(),
                            progress=steps.append)
        self.assertTrue(d.result.ok)
        self.assertEqual(2, d.attempts)
        second = t.calls[1][2]["messages"]
        self.assertEqual(["system", "user", "assistant", "user"], [m["role"] for m in second])
        self.assertIn("randul 4", second[-1]["content"])
        self.assertIn("CLICKK", second[-1]["content"])
        self.assertTrue(any("corecteaza" in s for s in steps))

    def test_gives_up_after_max_repairs(self):
        t = FakeTransport("openai", [BAD, BAD, BAD, GOOD])
        d = ai.make_routine(ai.AiClient(_settings("openai"), key="k", transport=t), "P", ObjectRepository())
        self.assertFalse(d.result.ok)
        self.assertEqual(1 + ai.MAX_REPAIRS, d.attempts)
        self.assertEqual(1, len(t.answers))


class DocxTests(unittest.TestCase):
    def test_word_paragraphs_lists_and_tables(self):
        w = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'
        xml = (f'<?xml version="1.0"?><w:document {w}><w:body>'
               '<w:p><w:r><w:t>Procedura comenzi</w:t></w:r></w:p>'
               '<w:p><w:pPr><w:numPr><w:ilvl w:val="0"/></w:numPr></w:pPr><w:r><w:t>Apasa </w:t></w:r>'
               '<w:r><w:t>Salveaza</w:t></w:r></w:p>'
               '<w:tbl><w:tr><w:tc><w:p><w:r><w:t>Coloana</w:t></w:r></w:p></w:tc>'
               '<w:tc><w:p><w:r><w:t>Valoare</w:t></w:r></w:p></w:tc></w:tr></w:tbl>'
               '</w:body></w:document>')
        p = os.path.join(tempfile.mkdtemp(), "proc.docx")
        with zipfile.ZipFile(p, "w") as z:
            z.writestr("word/document.xml", xml)
        self.assertEqual("Procedura comenzi\n- Apasa Salveaza\nColoana | Valoare", ai.read_procedure(p))
        bad = os.path.join(os.path.dirname(p), "rau.docx")
        with open(bad, "w") as f:
            f.write("nu e zip")
        with self.assertRaises(ai.AiError):
            ai.read_procedure(bad)


EXAMPLES = sorted(glob.glob(os.path.join(APP, "rpr", "exemple", "*.rpr.json")))


def _no_ids(d):
    if isinstance(d, dict):
        return {k: _no_ids(v) for k, v in d.items() if k != "id"}
    if isinstance(d, list):
        return [_no_ids(x) for x in d]
    return d


class RepairTests(unittest.TestCase):
    def test_examples_roundtrip_without_loss(self):
        """Rutina -> text -> import (+PASTREAZA, +setarile) = aceeasi rutina, in RO si EN."""
        self.assertGreaterEqual(len(EXAMPLES), 5)
        kept = 0
        for f in EXAMPLES:
            r = RoutineStore.load(f)
            for lang in ("ro", "en"):
                job = ai.prepare_repair(r, lang)
                kept += len(job.writer.keep)
                res = job.importer(ObjectRepository()).parse(job.steps_text)
                self.assertFalse(res.errors, (f, lang, [i.message for i in res.errors]))
                job.finish(res)
                self.assertEqual(_no_ids(r.to_dict()["steps"]), _no_ids(res.routine.to_dict()["steps"]), (f, lang))
                self.assertTrue(res.routine.name.startswith(r.name))
                self.assertNotEqual(r.name, res.routine.name)
        self.assertGreater(kept, 0)   # exemplele au si pasi fara text (reguli, bucle "cat timp")

    def test_changed_line_new_value_others_keep_settings(self):
        r = Routine(name="Veche")
        a = ActionNode(action=RprAction.Click, target="Buton_Vechi", timeout_ms=2500, delay_after_ms=300)
        b = ActionNode(action=RprAction.TypeText, target="Camp_Nume", value="{Rand.Nume}", timeout_ms=7000,
                       comment="important")
        r.steps = [a, b]
        job = ai.prepare_repair(r)
        self.assertIn("CLICK [Buton_Vechi]", job.steps_text)
        self.assertIn("# important", job.steps_text)
        answer = job.steps_text.replace("CLICK [Buton_Vechi]", "# TODO: butonul s-a mutat\nCLICK buton \"Salveaza\"")
        res = job.importer(ObjectRepository()).parse("```text\n" + answer + "```\nSCHIMBARI: butonul")
        self.assertTrue(res.ok, [i.message for i in res.errors])
        job.finish(res)
        n1, n2 = res.routine.steps
        self.assertEqual("Buton_Salveaza", n1.target)
        self.assertEqual(10000, n1.timeout_ms)           # pas nou: setarile implicite
        self.assertIn("TODO", n1.comment)
        self.assertEqual((7000, "important"), (n2.timeout_ms, n2.comment))   # neschimbat: setarile vechi
        self.assertNotEqual(b.id, n2.id)
        self.assertEqual(1, len(res.new_objects))
        self.assertEqual("Buton_Vechi", r.steps[0].target)   # originalul ramane neatins

    def test_passwords_do_not_leave(self):
        r = Routine(name="X", variables={"Parola": "secret123", "Fisier": "C:\\a.xlsx"})
        r.steps = [ActionNode(action=RprAction.TypeText, target="Camp_Parola", value="{Parola}")]
        job = ai.prepare_repair(r)
        self.assertNotIn("secret123", job.steps_text)
        self.assertIn("C:\\a.xlsx", job.steps_text)
        t = FakeTransport("openai", ["```text\n" + job.steps_text + "```"])
        d = ai.repair_routine(ai.AiClient(_settings("openai"), key="k", transport=t), job, "", ObjectRepository())
        self.assertNotIn("secret123", json.dumps(t.calls))
        job.finish(d.result)
        self.assertEqual("secret123", d.result.routine.variables["Parola"])
        self.assertNotIn("secret123", ai.ask_copy_text("q", "ro", r, [], ai.AiSettings()))

    def test_keep_without_repair_is_an_error(self):
        res = StepImporter(ObjectRepository()).parse("RUTINA: X\nPASTREAZA #1\nCLICK buton \"a\"")
        self.assertEqual(1, len(res.errors))
        self.assertIn("PASTREAZA", res.errors[0].message)
        self.assertNotIn("PASTREAZA", ai_prompt("ro"))
        self.assertIn("PASTREAZA", ai_prompt("ro", repair=True))

    def test_repair_routine_with_fake_ai(self):
        r = RoutineStore.load([f for f in EXAMPLES if "06_" in os.path.basename(f)][0])
        job = ai.prepare_repair(r)
        self.assertIn("PASTREAZA #1", job.steps_text)
        fixed = job.steps_text.replace('CLICK [Demo2_Final]', 'ASTEAPTA [Demo2_Final] MAX 20\nCLICK [Demo2_Final]')
        t = FakeTransport("anthropic", ["```text\n" + fixed + "```\nSCHIMBARI: asteptare"])
        logs = [RunLogEntry(RprLogLevel.Error, node_title="Click [Demo2_Final]", message="Timeout 10000ms")]
        d = ai.repair_routine(ai.AiClient(_settings(), key="k", transport=t), job, "pagina e lenta",
                              ObjectRepository(), logs)
        self.assertTrue(d.result.ok, [i.message for i in d.result.errors])
        sent = t.calls[0][2]
        self.assertIn("REPARAREA UNEI RUTINE", sent["system"])
        self.assertIn("PASTREAZA #1", sent["messages"][0]["content"])
        self.assertIn("Timeout 10000ms", sent["messages"][0]["content"])
        self.assertIn("pagina e lenta", sent["messages"][0]["content"])
        job.finish(d.result)
        self.assertEqual(sum(1 for _ in r.all_nodes()) + 1, sum(1 for _ in d.result.routine.all_nodes()))
        self.assertEqual(r.to_dict()["settings"], d.result.routine.to_dict()["settings"])


class CliTests(unittest.TestCase):
    def test_cli_repair_writes_new_file(self):
        from rpr import __main__ as cli
        d = tempfile.mkdtemp()
        src = os.path.join(d, "Rutina.rpr.json")
        r = Routine(name="Rutina")
        r.steps = [ActionNode(action=RprAction.Click, target="Buton_A", timeout_ms=1234)]
        RoutineStore.save(r, src)
        answer = "```text\nRUTINA: Rutina\nASTEAPTA 2\nCLICK [Buton_A]\n```"
        t = FakeTransport("openai", [answer])
        with mock.patch.object(ai.AiSettings, "load", return_value=_settings("openai")), \
                mock.patch.object(ai, "_http_post", t), mock.patch.object(ai, "get_key", return_value="k"), \
                mock.patch("rpr.__main__.RepositoryStore.load", return_value=ObjectRepository()), \
                mock.patch("builtins.print"):
            code = cli.ai_command("repara", src, note="mai incet")
        self.assertEqual(0, code)
        out = RoutineStore.load(os.path.join(d, "Rutina_reparata.rpr.json"))
        self.assertEqual(2, len(out.steps))
        self.assertEqual(1234, out.steps[1].timeout_ms)
        self.assertEqual(1, len(RoutineStore.load(src).steps))


class StudioAssistantTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            import tkinter as tk
            cls.root = tk.Tk()
            cls.root.geometry("1366x740")
        except Exception as ex:  # noqa: BLE001 — fara ecran (CI)
            raise unittest.SkipTest(f"fara afisaj: {ex}")
        from test_views import COLORS
        import ui_theme
        from rpr.storage import RprPaths
        cls.d = tempfile.mkdtemp(prefix="apdc_ai_")
        cls.old = (RprPaths.root, ui_theme._SETTINGS, ai._SETTINGS)
        RprPaths.root = os.path.join(cls.d, "Studio")
        ui_theme._SETTINGS = os.path.join(cls.d, "aspect.json")
        ai._SETTINGS = os.path.join(cls.d, "asistent_ai.json")
        import studio_ui
        cls.p = studio_ui.StudioPanel(cls.root, COLORS)
        cls.p.pack(fill="both", expand=True)
        cls.root.update()

    @classmethod
    def tearDownClass(cls):
        import ui_theme
        from rpr.storage import RprPaths
        RprPaths.root, ui_theme._SETTINGS, ai._SETTINGS = cls.old
        cls.root.destroy()

    def tearDown(self):
        for attr in ("_assistant_win", "_import_win"):
            w = getattr(self.p, attr, None)
            if w is not None and w.winfo_exists():
                w.destroy()
        self.root.update()

    def _wait(self, dlg):
        import time
        t0 = time.time()
        while dlg._busy and time.time() - t0 < 10:
            self.root.update()
            time.sleep(0.02)
        for _ in range(5):
            self.root.update()

    def test_rail_opens_assistant_once(self):
        self.p._on_rail_action("assistant")
        self.root.update()
        w = self.p._assistant_win
        self.assertTrue(w.winfo_exists())
        self.p.show_assistant()
        self.assertIs(w, self.p._assistant_win)
        self.assertIn("Fara conexiune", w.conn.cget("text"))
        self.assertEqual(3, len(w.nb.tabs()))

    def test_copy_mode_puts_package_in_clipboard(self):
        self.p.show_assistant()
        w = self.p._assistant_win
        w.p_text.insert("1.0", "1. Deschide portalul\n2. Apasa Salveaza")
        w.make_routine()   # fara conexiune = copiaza
        clip = self.root.clipboard_get()
        self.assertIn("COMENZI", clip)
        self.assertTrue(clip.rstrip().endswith("2. Apasa Salveaza"))
        w.q_text.insert("1.0", "cum fac o bucla?")
        w.send_question()
        self.assertIn("cum fac o bucla?", self.root.clipboard_get())

    def test_connected_make_routine_opens_import(self):
        self.p.show_assistant()
        w = self.p._assistant_win
        w.settings = _settings("openai")
        w._refresh_conn()
        t = FakeTransport("openai", [BAD, GOOD])
        with mock.patch.object(ai, "_http_post", t), mock.patch.object(ai, "get_key", return_value="k"):
            w.p_text.insert("1.0", "Procedura")
            w.make_routine()
            self._wait(w)
        imp = self.p._import_win
        self.assertTrue(imp.winfo_exists())
        self.assertTrue(imp.result.ok)
        self.assertEqual("Test", imp.result.routine.name)
        self.assertIn("Incercarea 2", w.r_info.cget("text"))

    def test_connected_error_is_shown_not_raised(self):
        self.p.show_assistant()
        w = self.p._assistant_win
        w.settings = _settings("anthropic", url="http://127.0.0.1:9", timeout=2)
        with mock.patch("tkinter.messagebox.showerror") as err:
            w.q_text.insert("1.0", "intrebare")
            w.send_question()
            self._wait(w)
        self.assertTrue(err.called)
        self.assertTrue(w.status.cget("text").startswith("✕"))
        self.assertEqual("normal", str(w.btn_ask.cget("state")))

    def test_repair_opens_new_tab_original_unchanged(self):
        r = RoutineStore.load([f for f in EXAMPLES if "01_" in os.path.basename(f)][0])
        self.p.routine = r
        before = json.dumps(r.to_dict(), sort_keys=True)
        self.p.show_assistant()
        w = self.p._assistant_win
        w._refresh_repair()
        self.assertIn(r.name, w.rep_info.cget("text"))
        w.settings = _settings("anthropic")
        job = ai.prepare_repair(r)
        t = FakeTransport("anthropic", ["```text\n" + job.steps_text + "LOG \"gata\"\n```"])
        with mock.patch.object(ai, "_http_post", t), mock.patch.object(ai, "get_key", return_value="k"):
            w.rep_text.insert("1.0", "adauga un log la final")
            w.repair_routine()
            self._wait(w)
        imp = self.p._import_win
        self.assertTrue(imp.result.ok, [i.message for i in imp.result.errors])
        self.assertIsNotNone(imp.repair)
        with mock.patch.object(self.p, "_offer_complete"):
            imp.create()
        self.root.update()
        self.assertTrue(self.p.routine.name.endswith("(reparata)"))
        self.assertEqual(sum(1 for _ in r.all_nodes()) + 1, sum(1 for _ in self.p.routine.all_nodes()))
        self.assertEqual(before, json.dumps(r.to_dict(), sort_keys=True))


if __name__ == "__main__":
    unittest.main()
