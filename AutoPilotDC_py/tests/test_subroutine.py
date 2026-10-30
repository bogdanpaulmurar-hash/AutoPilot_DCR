# -*- coding: utf-8 -*-
# ============================================================
# AutoPilot DC — Teste: rutine ca pasi / calupuri (v4.12)
#   Rulare:  py -m unittest tests.test_subroutine
# ============================================================

import os
import sys
import tempfile
import unittest

APP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, APP)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from rpr import subroutine  # noqa: E402
from rpr.model import (ActionNode, LogNode, Routine, RprAction, RunRoutineNode, SetVariableNode,  # noqa: E402
                       node_from_dict)
from rpr.storage import RoutineStore  # noqa: E402
from test_rpr import create, new_routine  # noqa: E402


def _save(folder, name, *steps, variables=None):
    r = Routine(name=name, steps=list(steps), variables=dict(variables or {}))
    path = os.path.join(folder, name + ".rpr.json")
    RoutineStore.save(r, path)
    return path


def _type(text):
    return ActionNode(action=RprAction.TypeText, target="Camp", value=text)


class SubroutineRunTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="apdc_calup_")

    def test_node_roundtrip_and_title(self):
        n = RunRoutineNode(path=r"C:\x\Login.rpr.json")
        self.assertEqual("Ruleaza rutina [Login]", n.title)
        back = node_from_dict(n.to_dict())
        self.assertIsInstance(back, RunRoutineNode)
        self.assertEqual(r"C:\x\Login.rpr.json", back.path)

    def test_runs_in_place_between_own_steps(self):
        a = _save(self.dir, "Login", SetVariableNode(name="X", value="1"), _type("{Nume}"),
                  variables={"Implicit": "da"})
        engine, driver, host, _ = create()
        r = new_routine(LogNode(message="inainte"), RunRoutineNode(path=a), SetVariableNode(name="Dupa", value="ok"))
        r.variables["Nume"] = "Ana"
        result = engine.run(r)
        self.assertTrue(result.success, result.message)
        self.assertEqual("1", result.final_variables["X"])          # variabilele sunt comune
        self.assertEqual("da", result.final_variables["Implicit"])   # valoarea implicita a calupului
        self.assertEqual("ok", result.final_variables["Dupa"])
        self.assertEqual(["TypeText:Camp:Ana"], driver.actions)      # {Nume} din rutina principala
        msgs = [e.message for e in host.entries]
        self.assertTrue(any("Calup \"Login\": start (2 pasi)" in m for m in msgs), msgs)
        self.assertTrue(any("terminat" in m for m in msgs), msgs)
        titles = [e.node_title for e in host.entries if "Ana" in e.node_title or e.node_title.startswith("[Login]")]
        self.assertTrue(titles, [e.node_title for e in host.entries])

    def test_main_variable_wins_over_calup_default(self):
        a = _save(self.dir, "A", _type("{Nume}"), variables={"Nume": "implicit"})
        engine, driver, _, _ = create()
        r = new_routine(RunRoutineNode(path=a))
        r.variables["Nume"] = "principal"
        self.assertTrue(engine.run(r).success)
        self.assertEqual(["TypeText:Camp:principal"], driver.actions)

    def test_missing_file_stops_before_start(self):
        engine, driver, host, _ = create()
        result = engine.run(new_routine(SetVariableNode(name="Pornit", value="da"),
                                        RunRoutineNode(path=os.path.join(self.dir, "lipsa.rpr.json"))))
        self.assertFalse(result.success)
        self.assertIn("lipseste", result.message)
        self.assertNotIn("Pornit", result.final_variables)            # nimic nu a rulat

    def test_cycle_is_detected_before_start(self):
        pa, pb = os.path.join(self.dir, "A.rpr.json"), os.path.join(self.dir, "B.rpr.json")
        _save(self.dir, "A", RunRoutineNode(path=pb))
        _save(self.dir, "B", RunRoutineNode(path=pa))
        engine, _, _, _ = create()
        result = engine.run(new_routine(RunRoutineNode(path=pa)))
        self.assertFalse(result.success)
        self.assertIn("cerc", result.message)

    def test_missing_object_in_calup_is_named(self):
        a = _save(self.dir, "A", ActionNode(action=RprAction.Click, target="ObiectInexistent"))
        engine, _, _, _ = create()
        result = engine.run(new_routine(RunRoutineNode(path=a)))
        self.assertFalse(result.success)
        self.assertIn("ObiectInexistent", result.message)

    def test_disabled_step_is_skipped(self):
        a = _save(self.dir, "A", _type("x"))
        engine, driver, _, _ = create()
        n = RunRoutineNode(path=a)
        n.enabled = False
        self.assertTrue(engine.run(new_routine(n)).success)
        self.assertEqual([], driver.actions)

    def test_path_with_variable_is_resolved_at_runtime(self):
        a = _save(self.dir, "Dinamic", _type("ok"))
        engine, driver, _, _ = create()
        r = new_routine(RunRoutineNode(path="{Cale}"))
        r.variables["Cale"] = a
        self.assertTrue(engine.run(r).success)
        self.assertEqual(["TypeText:Camp:ok"], driver.actions)

    def test_calup_error_follows_main_routine_policy(self):
        a = _save(self.dir, "A", ActionNode(action=RprAction.Click, target="Camp"), _type("dupa"))
        engine, driver, _, _ = create()
        driver.failures_before_success = 99
        result = engine.run(new_routine(RunRoutineNode(path=a), SetVariableNode(name="Dupa", value="da")))
        self.assertFalse(result.success)                              # politica implicita: Stop
        self.assertNotIn("Dupa", result.final_variables)


class SubroutineHelpersTests(unittest.TestCase):
    def test_steps_copy_gets_new_ids_and_variables_merge(self):
        sub = Routine(name="S", steps=[_type("a"), _type("b")], variables={"V1": "1", "V2": "2"})
        copy = subroutine.steps_copy(sub)
        self.assertEqual(2, len(copy))
        self.assertTrue(all(c.id != s.id for c, s in zip(copy, sub.steps)))
        target = Routine(variables={"V1": "mine"})
        self.assertEqual(1, subroutine.merge_variables(target, sub))
        self.assertEqual({"V1": "mine", "V2": "2"}, target.variables)

    def test_resolve_relative_to_routines_folder(self):
        folder = tempfile.mkdtemp(prefix="apdc_calup_rel_")
        p = _save(folder, "Rel", _type("x"))
        from rpr.batch import shared_library
        lib = shared_library()
        old = lib.folder
        lib.folder = folder
        try:
            self.assertEqual(p, subroutine.resolve_path("Rel.rpr.json"))
        finally:
            lib.folder = old


if __name__ == "__main__":
    unittest.main()
