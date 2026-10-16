# -*- coding: utf-8 -*-
# ============================================================
# AutoPilot DC — Teste programare (Task Scheduler) + rularea programata (--anunta).
# Testul real creeaza o programare "o singura data" in 2030 si o sterge imediat.
#   Rulare:  py -m unittest tests.test_schedule
# ============================================================

import datetime as dt
import os
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rpr import schedule as sch  # noqa: E402

NS = {"t": "http://schemas.microsoft.com/windows/2004/02/mit/task"}


def _parse(xml: str):
    return ET.fromstring(xml.split("?>", 1)[1])


class ScheduleXmlTests(unittest.TestCase):
    at = dt.datetime(2030, 5, 6, 8, 30)

    def test_weekdays(self):
        x = _parse(sch.build_xml(r"C:\r\a b.rpr.json", "A & B", 1, self.at))
        days = [d.tag.split("}")[1] for d in x.find(".//t:DaysOfWeek", NS)]
        self.assertEqual(["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"], days)
        self.assertEqual("2030-05-06T08:30:00", x.find(".//t:StartBoundary", NS).text)
        self.assertEqual('-m rpr run "C:\\r\\a b.rpr.json" --anunta', x.find(".//t:Arguments", NS).text)
        self.assertTrue(x.find(".//t:Command", NS).text.lower().endswith(("pythonw.exe", "python.exe")))
        self.assertEqual("InteractiveToken", x.find(".//t:LogonType", NS).text)
        self.assertIn("A & B", x.find(".//t:Description", NS).text)

    def test_other_kinds(self):
        self.assertIsNotNone(_parse(sch.build_xml("r", "r", 0, self.at)).find(".//t:ScheduleByDay", NS))
        sel = _parse(sch.build_xml("r", "r", 2, self.at, days=[5, 0]))
        self.assertEqual(["Monday", "Saturday"], [d.tag.split("}")[1] for d in sel.find(".//t:DaysOfWeek", NS)])
        self.assertIsNotNone(_parse(sch.build_xml("r", "r", 3, self.at)).find(".//t:TimeTrigger", NS))
        rep = _parse(sch.build_xml("r", "r", 4, self.at, every_minutes=15))
        self.assertEqual("PT15M", rep.find(".//t:Interval", NS).text)
        self.assertIsNotNone(_parse(sch.build_xml("r", "r", 5, self.at)).find(".//t:LogonTrigger", NS))
        with self.assertRaises(ValueError):
            sch.build_xml("r", "r", 2, self.at, days=[])

    def test_result_text(self):
        self.assertIn("succes", sch.describe_result("0"))
        self.assertIn("nu a rulat", sch.describe_result("267011"))


@unittest.skipUnless(os.name == "nt", "doar Windows")
class ScheduleRealTests(unittest.TestCase):
    def test_create_list_delete(self):
        tmp = tempfile.mkdtemp(prefix="apdc_sch_")
        path = os.path.join(tmp, "Test.rpr.json")
        ok, out, name = sch.create(path, "Test programare AutoPilot", 3, dt.datetime(2030, 1, 2, 3, 4),
                                   task_name="Test_programare_unittest")
        if not ok:
            self.skipTest(f"schtasks nu permite crearea: {out}")
        try:
            names = {t.name.lstrip("\\") for t in sch.list_tasks()}
            self.assertIn(name.lstrip("\\"), names)
        finally:
            ok_del, out_del = sch.delete(name)
        self.assertTrue(ok_del, out_del)
        self.assertNotIn(name.lstrip("\\"), {t.name.lstrip("\\") for t in sch.list_tasks()})


class AnnouncedRunTests(unittest.TestCase):
    def test_history_and_notify(self):
        from rpr import __main__ as cli
        from rpr.storage import RprPaths
        old_root = RprPaths.root
        RprPaths.root = tempfile.mkdtemp(prefix="apdc_hist_")
        shown = []
        old_notify = cli.notify
        cli.notify = lambda title, text, success, log="", seconds=25: shown.append((title, success, log))
        try:
            from rpr.model import LogNode, Routine
            from rpr.storage import RoutineStore
            r = Routine(name="Rutina programata")
            r.settings.do_not_disturb = False
            r.steps.append(LogNode(message="salut"))
            path = os.path.join(RprPaths.root, "p.rpr.json")
            RoutineStore.save(r, path)
            code = cli.run_file(path, {}, show_frame=False, announce=True)
            self.assertEqual(0, code)
            self.assertTrue(shown and shown[0][1])
            h = sch.load_history()
            self.assertEqual("Rutina programata", h[0]["rutina"])
            self.assertTrue(h[0]["succes"])
            self.assertTrue(os.path.exists(h[0]["log"]))
        finally:
            cli.notify = old_notify
            RprPaths.root = old_root


if __name__ == "__main__":
    unittest.main()
