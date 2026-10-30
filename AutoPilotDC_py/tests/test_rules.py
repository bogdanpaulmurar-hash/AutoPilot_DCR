# -*- coding: utf-8 -*-
# ============================================================
# AutoPilot DC — Teste: "Daca apare" si reguli pentru mesaje / erori (v4.13)
#   Rulare:  py -m unittest tests.test_rules
# ============================================================

import os
import sys
import unittest

APP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, APP)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from rpr.model import (ActionNode, Condition, ConditionKind, GroupNode, IfNode, LogNode, RuleAfter,  # noqa: E402
                       RuleNode, RprAction, SetVariableNode, node_from_dict)
from test_rpr import create, new_routine  # noqa: E402


def _click():
    return ActionNode(action=RprAction.Click, target="Buton")


def _rule(**kw):
    kw.setdefault("body", [SetVariableNode(name="Regula", value="ok")])
    return RuleNode(**kw)


class RuleTests(unittest.TestCase):
    def test_roundtrip_and_title(self):
        r = _rule(error_contains="Sigur", after=RuleAfter.Skip)
        back = node_from_dict(r.to_dict())
        self.assertIsInstance(back, RuleNode)
        self.assertEqual(RuleAfter.Skip, back.after)
        self.assertEqual(1, len(back.body))
        self.assertIn("Sigur", back.title)

    def test_error_text_rule_runs_steps_and_retries(self):
        engine, driver, host, _ = create()
        driver.failures_before_success = 1
        result = engine.run(new_routine(_rule(error_contains="SIMULAT"), _click()))   # fara diferenta mare / mica
        self.assertTrue(result.success, result.message)
        self.assertEqual("ok", result.final_variables["Regula"])
        self.assertEqual(["Click:Buton:"], driver.actions)
        self.assertEqual(0, result.errors)

    def test_rule_gets_error_text_in_variable(self):
        engine, driver, _, _ = create()
        driver.failures_before_success = 1
        r = _rule(error_contains="simulat", body=[SetVariableNode(name="Copie", value="{EroareRegula}")])
        result = engine.run(new_routine(r, _click()))
        self.assertIn("esec simulat", result.final_variables["Copie"])

    def test_element_rule(self):
        engine, driver, _, _ = create()
        driver.failures_before_success = 1
        cond = Condition(kind=ConditionKind.ElementExists, target="Camp")   # "mesajul" e pe ecran
        result = engine.run(new_routine(_rule(use_element=True, condition=cond), _click()))
        self.assertTrue(result.success, result.message)
        self.assertEqual("ok", result.final_variables["Regula"])

    def test_no_match_follows_normal_policy(self):
        engine, driver, _, _ = create()
        driver.failures_before_success = 1
        result = engine.run(new_routine(_rule(error_contains="altceva"), _click()))
        self.assertFalse(result.success)
        self.assertNotIn("Regula", result.final_variables)

    def test_after_skip_marks_step_done(self):
        engine, driver, _, _ = create()
        driver.failures_before_success = 1
        result = engine.run(new_routine(_rule(error_contains="simulat", after=RuleAfter.Skip), _click(),
                                        SetVariableNode(name="Dupa", value="da")))
        self.assertTrue(result.success, result.message)
        self.assertEqual([], driver.actions)          # pasul nu s-a mai repetat
        self.assertEqual("da", result.final_variables["Dupa"])

    def test_after_error_runs_steps_then_fails(self):
        engine, driver, _, _ = create()
        driver.failures_before_success = 1
        result = engine.run(new_routine(_rule(error_contains="simulat", after=RuleAfter.Error), _click()))
        self.assertFalse(result.success)
        self.assertEqual("ok", result.final_variables["Regula"])

    def test_rule_is_scoped_to_its_list(self):
        engine, driver, _, _ = create()
        driver.failures_before_success = 1
        grup = GroupNode(body=[_rule(error_contains="simulat")])
        result = engine.run(new_routine(grup, _click()))      # regula s-a stins la sfarsitul grupului
        self.assertFalse(result.success)

    def test_retry_is_limited(self):
        engine, driver, _, _ = create()
        driver.failures_before_success = 50
        result = engine.run(new_routine(_rule(error_contains="simulat"), _click()))
        self.assertFalse(result.success)               # nu se reia la infinit

    def test_rule_steps_ignore_other_rules(self):
        engine, driver, _, _ = create()
        driver.failures_before_success = 2
        inner = _rule(error_contains="simulat", body=[_click()])
        result = engine.run(new_routine(inner, _click()))   # pasul din regula esueaza si el: fara bucla de reguli
        self.assertFalse(result.success)


class OptionalIfTests(unittest.TestCase):
    def test_absent_continues_without_error(self):
        engine, driver, _, _ = create()
        cond = Condition(kind=ConditionKind.ElementExists, target="Lipsa", timeout_ms=0)
        n = IfNode(optional=True, condition=cond, then=[SetVariableNode(name="Apasat", value="da")])
        result = engine.run(new_routine(n, SetVariableNode(name="Dupa", value="da")))
        self.assertTrue(result.success, result.message)
        self.assertNotIn("Apasat", result.final_variables)
        self.assertEqual("da", result.final_variables["Dupa"])

    def test_present_runs_steps(self):
        engine, driver, _, _ = create()
        cond = Condition(kind=ConditionKind.ElementExists, target="Buton", timeout_ms=0)
        n = IfNode(optional=True, condition=cond, then=[SetVariableNode(name="Apasat", value="da")])
        result = engine.run(new_routine(n))
        self.assertEqual("da", result.final_variables["Apasat"])

    def test_title_and_roundtrip(self):
        cond = Condition(kind=ConditionKind.ElementExists, target="Buton")
        n = IfNode(optional=True, condition=cond)
        self.assertTrue(n.title.startswith("Daca apare"))
        self.assertTrue(node_from_dict(n.to_dict()).optional)
        self.assertFalse(node_from_dict(IfNode(condition=cond).to_dict()).optional)


if __name__ == "__main__":
    unittest.main()
