# -*- coding: utf-8 -*-
# ============================================================
# AutoPilot DC — Teste: reluarea dupa o inchidere neasteptata (rpr/resume.py)
#   Rulare:  py -m unittest tests.test_resume
# ============================================================

import json
import os
import subprocess
import sys
import tempfile
import unittest

APP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, APP)

from rpr import DriverProvider, ObjectRepository, RprEngine, RunHost  # noqa: E402
from rpr import resume  # noqa: E402
from rpr.batch import PREP_EXT, Preparation, PreparationRunner, PrepItem  # noqa: E402
from rpr.model import LogNode, Routine  # noqa: E402
from rpr.storage import RoutineStore, RprPaths  # noqa: E402


def _dead_pid() -> int:
    p = subprocess.Popen([sys.executable, "-c", "pass"])
    p.wait()
    return p.pid


class _TempRoot(unittest.TestCase):
    def setUp(self):
        self._old = RprPaths.root
        self.d = tempfile.mkdtemp(prefix="apdc_resume_")
        RprPaths.root = os.path.join(self.d, "Studio")

    def tearDown(self):
        RprPaths.root = self._old

    def _simulate_crash(self, state):
        """Procesul care a scris starea nu mai exista (aplicatia s-a inchis brusc)."""
        with open(state.file, encoding="utf-8") as f:
            data = json.load(f)
        data["pid"] = _dead_pid()
        with open(state.file, "w", encoding="utf-8") as f:
            json.dump(data, f)


class StateFileTests(_TempRoot):
    def test_running_process_is_not_offered_finished_one_is_removed(self):
        st = resume.begin(resume.KIND_ROUTINE, os.path.join(self.d, "A.rpr.json"), "A", variables={"Nr": "3"})
        self.assertTrue(os.path.isfile(st.file))
        self.assertEqual([], resume.pending())          # procesul nostru inca ruleaza
        resume.end(st)
        self.assertFalse(os.path.exists(st.file))
        self.assertEqual([], resume.pending())

    def test_crash_is_detected_with_progress_and_unsaved_routine(self):
        r = Routine(name="Nesalvata")
        r.steps.append(LogNode(message="x"))
        st = resume.begin(resume.KIND_ROUTINE, "", r.name, routine=r.to_dict())
        prep = resume.begin(resume.KIND_PREP, os.path.join(self.d, "S" + PREP_EXT), "S")
        resume.update(prep, 2)
        self.assertNotEqual(st.file, prep.file)          # doua rulari in acelasi proces: fisiere separate
        self._simulate_crash(st)
        self._simulate_crash(prep)
        found = {s.name: s for s in resume.pending()}
        self.assertEqual({"Nesalvata", "S"}, set(found))
        self.assertEqual(2, found["S"].done_items)
        self.assertEqual("x", Routine.from_dict(found["Nesalvata"].routine).steps[0].message)
        self.assertTrue(found["S"].started_text)
        resume.discard(found["S"])
        self.assertEqual(["Nesalvata"], [s.name for s in resume.pending()])

    def test_broken_state_file_is_ignored(self):
        os.makedirs(os.path.join(RprPaths.root, resume.FOLDER), exist_ok=True)
        bad = os.path.join(RprPaths.root, resume.FOLDER, "rulare_1_1.json")
        with open(bad, "w", encoding="utf-8") as f:
            f.write("{stricat")
        self.assertEqual([], resume.pending())
        self.assertFalse(os.path.exists(bad))

    def test_pid_alive(self):
        self.assertTrue(resume.pid_alive(os.getpid()))
        self.assertFalse(resume.pid_alive(_dead_pid()))
        self.assertFalse(resume.pid_alive(0))


class PreparationResumeTests(_TempRoot):
    def test_start_index_skips_finished_routines_and_reports_progress(self):
        names = []
        for n in ("A", "B", "C"):
            r = Routine(name=n)
            r.settings.do_not_disturb = False
            r.settings.guard_enabled = False
            r.steps = [LogNode(message=n)]
            RoutineStore.save(r, os.path.join(self.d, n + ".rpr.json"))
            names.append(n + ".rpr.json")
        p = Preparation(name="P", report=False, video=False, path=os.path.join(self.d, "P" + PREP_EXT))
        p.items = [PrepItem(n) for n in names]
        ran, done = [], []

        def run_one(routine, item, folder):
            ran.append(routine.name)
            return RprEngine(ObjectRepository(), DriverProvider(), RunHost(), self.d).run(routine), ""
        res = PreparationRunner(p, run_one, self.d, on_item_done=done.append).run(start_index=2)
        self.assertEqual(["C"], ran)
        self.assertEqual(["OK", "OK", "OK"], [s.status for s in res.steps])
        self.assertIn("anterioara", res.steps[0].message)
        self.assertEqual([3], done)

    def test_headless_run_leaves_no_state(self):
        from rpr import __main__ as cli
        r = Routine(name="A")
        r.settings.do_not_disturb = False
        r.settings.guard_enabled = False
        r.steps = [LogNode(message="x")]
        path = os.path.join(self.d, "A.rpr.json")
        RoutineStore.save(r, path)
        os.makedirs(RprPaths.output(), exist_ok=True)
        self.assertEqual(0, cli.run_file(path, {}, show_frame=False))
        self.assertEqual([], os.listdir(os.path.join(RprPaths.root, resume.FOLDER)))


if __name__ == "__main__":
    unittest.main()
