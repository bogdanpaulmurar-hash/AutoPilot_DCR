# -*- coding: utf-8 -*-
# ============================================================
# AutoPilot DC — Teste: 📥 Import AI (pasi din text / JSON) si ⏺ Ecran (v4.16)
#   Rulare:  py -m unittest tests.test_importer
# ============================================================

import json
import os
import sys
import unittest

APP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, APP)

import i18n  # noqa: E402
from rpr.importer import COMMANDS, StepImporter, _EXAMPLE_EN, _EXAMPLE_RO, ai_prompt  # noqa: E402
from rpr.legacy import merge_typing, recorded_to_nodes  # noqa: E402
from rpr.model import (ForEachRowNode, IfNode, LegacyStepNode, QuestionNode, Routine, RprAction,  # noqa: E402
                       TryNode, WriteExcelNode)


def _kinds(routine):
    return [type(n).__name__ for n in routine.all_nodes()]


class ImporterTests(unittest.TestCase):
    def setUp(self):
        i18n.load("ro")

    def tearDown(self):
        i18n.load("ro")

    def test_examples_ro_and_en_give_same_routine(self):
        ro = StepImporter().parse(_EXAMPLE_RO)
        en = StepImporter().parse(_EXAMPLE_EN)
        for r in (ro, en):
            self.assertTrue(r.ok, [i.message for i in r.issues])
            self.assertEqual(r.step_count(), 16)
            self.assertEqual(len(r.new_objects), 9)
        self.assertEqual(_kinds(ro.routine), _kinds(en.routine))
        self.assertEqual(ro.routine.name, "Inregistrare comenzi")
        loop = [n for n in ro.routine.steps if isinstance(n, ForEachRowNode)][0]
        self.assertEqual(loop.sheet, "Comenzi")
        self.assertTrue(any(isinstance(n, IfNode) for n in loop.body))
        self.assertTrue(any(isinstance(n, WriteExcelNode) for n in ro.routine.all_nodes()))
        self.assertTrue(any(isinstance(n, QuestionNode) for n in ro.routine.steps))   # MANUAL
        # variabilele folosite fara valoare: avertisment, nu eroare
        warn = [i.message for i in ro.issues if not i.error]
        self.assertTrue(any("Utilizator" in m for m in warn))

    def test_routine_roundtrip_json(self):
        res = StepImporter().parse(_EXAMPLE_RO)
        data = json.loads(json.dumps(res.routine.to_dict()))
        again = Routine.from_dict(data)
        self.assertEqual(_kinds(again), _kinds(res.routine))
        # .rpr.json lipit direct = aceeasi rutina
        res2 = StepImporter().parse(json.dumps(data))
        self.assertTrue(res2.ok)
        self.assertEqual(_kinds(res2.routine), _kinds(res.routine))

    def test_json_with_text_lines_and_code_fence(self):
        txt = "```json\n" + json.dumps({"name": "Mini", "steps": ['CLICK buton "OK"', "ASTEAPTA 2"]}) + "\n```"
        res = StepImporter().parse(txt)
        self.assertTrue(res.ok, [i.message for i in res.issues])
        self.assertEqual(res.routine.name, "Mini")
        self.assertEqual(res.step_count(), 2)

    def test_errors_are_reported_on_lines(self):
        res = StepImporter().parse('RUTINA: X\nCLICK buton "OK"\nZBOARA pe luna\nALTFEL\nDACA {A} = "1"\n  LOG "a"')
        self.assertFalse(res.ok)
        lines = sorted(i.line for i in res.errors)
        self.assertEqual(lines, [3, 4])
        self.assertTrue(any(not i.error and i.line == 5 for i in res.issues))   # DACA fara SFARSIT: inchis automat

    def test_existing_object_is_reused(self):
        imp = StepImporter()
        first = imp.parse('CLICK buton "Salveaza"')
        repo = imp.repo
        for o in first.new_objects:
            repo.objects.append(o)
        again = StepImporter(repo).parse('CLICK buton "Salveaza"\nDUBLU CLICK buton "Salveaza"')
        self.assertEqual(again.new_objects, [])
        acts = [n.action for n in again.routine.steps]
        self.assertEqual(acts, [RprAction.Click, RprAction.DoubleClick])

    def test_try_and_conditions(self):
        res = StepImporter().parse('INCEARCA\n  CLICK [Buton_OK]\nLA EROARE\n  LOG "nu"\nSFARSIT\n'
                                   'DACA {Raspuns} = "Da" SI vizibil buton "OK"\n  OPRESTE\nSFARSIT')
        self.assertTrue(any(isinstance(n, TryNode) for n in res.routine.steps))
        self.assertTrue(res.errors == [], [i.message for i in res.errors])
        cond = [n for n in res.routine.steps if isinstance(n, IfNode)][0].condition
        self.assertEqual(len(cond.children), 2)

    def test_prompt_lists_every_command(self):
        for lang in ("ro", "en"):
            i18n.load(lang)
            p = ai_prompt(lang)
            for c in COMMANDS:
                self.assertIn(c.syntax_en if lang == "en" else c.syntax_ro, p)
        i18n.load("en")
        self.assertIn("RULES:", ai_prompt("en"))
        self.assertNotIn("Raspunde DOAR", ai_prompt("en"))

    def test_messages_follow_language(self):
        i18n.load("en")
        res = StepImporter().parse("ZBOARA")
        self.assertTrue(res.errors[0].message.startswith("Unknown command"), res.errors[0].message)


class ScreenRecordingTests(unittest.TestCase):
    def setUp(self):
        i18n.load("ro")

    def test_merge_typing(self):
        keys = [dict(step_type="KEY", key_combo=c, window_process="notepad.exe", delay_before=0.2)
                for c in ("a", "Shift+b", "space", "c")]
        steps = [dict(step_type="CLICK", x=10, y=20, window_process="notepad.exe")] + keys + \
                [dict(step_type="KEY", key_combo="Enter", window_process="notepad.exe")]
        out = merge_typing(steps)
        self.assertEqual([s["step_type"] for s in out], ["CLICK", "TYPE", "KEY"])
        self.assertEqual(out[1]["text_input"], "aB c")
        self.assertNotIn("_typing", out[1])

    def test_new_window_or_pause_starts_new_text(self):
        steps = [dict(step_type="KEY", key_combo="a", window_process="a.exe"),
                 dict(step_type="KEY", key_combo="b", window_process="b.exe"),
                 dict(step_type="KEY", key_combo="c", window_process="b.exe", delay_before=5)]
        self.assertEqual([s["text_input"] for s in merge_typing(steps)], ["a", "b", "c"])

    def test_recorded_to_nodes_titles_follow_language(self):
        steps = [dict(step_type="CLICK", x=10, y=20, window_title="Notepad"),
                 dict(step_type="KEY", key_combo="x"), dict(step_type="KEY", key_combo="Ctrl+S")]
        nodes = [n for n in recorded_to_nodes(steps) if isinstance(n, LegacyStepNode)]
        self.assertEqual(len(nodes), 3)
        i18n.load("en")
        try:
            titles = [n.auto_title() for n in nodes]
        finally:
            i18n.load("ro")
        self.assertTrue(titles[0].startswith("Click (10, 20)"), titles)
        self.assertTrue(titles[1].startswith("Type \"x\""), titles)
        self.assertTrue(titles[2].startswith("Key Ctrl+S"), titles)


if __name__ == "__main__":
    unittest.main()
