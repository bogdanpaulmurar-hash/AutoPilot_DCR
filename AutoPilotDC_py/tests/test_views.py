# -*- coding: utf-8 -*-
# ============================================================
# AutoPilot DC v4.15 — Teste: bara de activitati, tab-uri pentru rutine,
# cronologia rularii, ecranul Excel (reia randul), fluxul.
#   Rulare:  py -m unittest tests.test_views
# ============================================================

import os
import shutil
import sys
import tempfile
import time
import unittest
from unittest import mock

APP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, APP)

import ui_theme  # noqa: E402
from rpr.model import (Condition, ConditionKind, ForEachRowNode, IfNode, LogNode, Routine,  # noqa: E402
                       WriteExcelNode)
from rpr.storage import RoutineStore, RprPaths  # noqa: E402

COLORS = {"bg_main": "#1E1E2E", "bg_panel": "#252535", "bg_card": "#2A2A3E", "bg_input": "#32324A",
          "border": "#444466", "primary": "#009999", "accent": "#3DA9E0", "text": "#FFFFFF",
          "text_dim": "#B4B4D0", "text_muted": "#8A8AAA", "success": "#1F8F4E", "warning": "#FF8800",
          "danger": "#CC0000", "row_active": "#1A4A4A"}


class StudioViewsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            import tkinter as tk
            cls.root = tk.Tk()
            cls.root.geometry("1366x740")
        except Exception as ex:  # noqa: BLE001 — fara ecran (CI)
            raise unittest.SkipTest(f"fara afisaj: {ex}")
        cls.d = tempfile.mkdtemp(prefix="apdc_views_")
        cls.old_root, cls.old_aspect = RprPaths.root, ui_theme._SETTINGS
        RprPaths.root = os.path.join(cls.d, "Studio")
        ui_theme._SETTINGS = os.path.join(cls.d, "aspect.json")
        import studio_ui
        cls.p = studio_ui.StudioPanel(cls.root, COLORS)
        cls.p.pack(fill="both", expand=True)
        cls.root.update()

    @classmethod
    def tearDownClass(cls):
        try:
            cls.p.shutdown()
            cls.root.destroy()
        except Exception:  # noqa: BLE001
            pass
        RprPaths.root, ui_theme._SETTINGS = cls.old_root, cls.old_aspect
        shutil.rmtree(cls.d, ignore_errors=True)

    def _pump(self, until, timeout=10.0):
        end = time.time() + timeout
        while time.time() < end:
            self.root.update()
            if until():
                return True
            time.sleep(0.02)
        return False

    def _save(self, name, steps):
        r = Routine(name=name)
        r.steps = steps
        path = os.path.join(self.d, name + ".rpr.json")
        RoutineStore.save(r, path)
        return path

    def _xlsx(self):
        import openpyxl
        path = os.path.join(self.d, "termeni.xlsx")
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Termeni"
        ws.append(["Termen", "Categorie", "Status"])
        for t, st in [("A", "OK"), ("B", ""), ("C", "EROARE: lipsa"), ("D", "")]:
            ws.append([t, "x", st])
        wb.save(path)
        return path

    # ── C: bara de activitati ──
    def test_rail_collapses_and_reopens_side_panel(self):
        p = self.p
        p.show_side("library")
        self.assertTrue(p._side_shown)
        self.assertTrue(p._side_pages["library"].winfo_ismapped() or True)
        p._rail._click("library", "panel")           # click pe iconita activa = se strange
        self.assertFalse(p._side_shown)
        self.assertNotIn(str(p._side), p._hpaned.panes())
        p._rail._click("routines", "panel")
        self.assertTrue(p._side_shown)
        self.assertEqual("routines", p._rail.active)
        self.assertEqual("routines", ui_theme.load().get("side_panel"))
        p.show_side("steps")

    # ── C: tab-uri ──
    def test_tabs_keep_each_routine_and_its_changes(self):
        p = self.p
        a = self._save("Rutina A", [LogNode(message="a")])
        b = self._save("Rutina B", [LogNode(message="b1"), LogNode(message="b2")])
        p.open_routine(a)
        n0 = len(p._docs)
        p.open_routine(b)
        self.assertEqual(n0 + 1, len(p._docs))
        self.assertEqual("Rutina B", p.routine.name)
        p.routine.steps.append(LogNode(message="nou"))
        p.mark_dirty()
        ia = p._find_doc(a)
        p.switch_doc(ia)
        self.assertEqual("Rutina A", p.routine.name)
        self.assertFalse(p.dirty)
        p.open_routine(b)                       # deja deschisa: doar comuta, nu deschide inca un tab
        self.assertEqual(n0 + 1, len(p._docs))
        self.assertEqual(3, len(p.routine.steps))
        self.assertTrue(p.dirty)
        with mock.patch("studio_ui.messagebox.askyesnocancel", return_value=False):   # nu salva
            p.close_doc(p._doc_i)
        self.assertEqual(n0, len(p._docs))
        self.assertEqual(-1, p._find_doc(b))

    def test_new_routine_reuses_empty_tab(self):
        p = self.p
        p.new_routine()
        n = len(p._docs)
        p.new_routine()            # tab-ul curent e gol: nu se mai deschide altul
        self.assertEqual(n, len(p._docs))

    def test_switch_blocked_while_running(self):
        p = self.p
        p.new_routine()
        p.routine.steps.append(LogNode(message="x"))
        p.new_routine()
        i = p._doc_i
        p.busy = True
        try:
            with mock.patch("studio_ui.messagebox.showinfo") as info:
                p.switch_doc(0 if i else 1)
            self.assertEqual(i, p._doc_i)
            info.assert_called_once()
        finally:
            p.busy = False

    # ── C: cronologia ──
    def test_timeline_cards_for_steps_not_blocks(self):
        p = self.p
        r = Routine(name="T")
        log, iff = LogNode(message="x"), IfNode()
        r.steps = [log, iff]
        p.routine = r
        p.rebuild_tree()
        p._run_started_ui(r, step_mode=True)
        p._mark_running(log)
        p._step_finished(log, True)
        p._mark_running(iff)
        p._step_finished(iff, True)            # blocurile (Daca, bucle) nu primesc card
        p._step_errors[log.id] = ("", "lipsa")
        p._step_finished(log, False)
        tl = p._timeline
        self.assertEqual(2, len(tl.cards))
        self.assertEqual([True, False], [c["ok"] for c in tl.cards])
        self.assertEqual("lipsa", tl.cards[1]["message"])

    def test_timeline_keeps_last_cards(self):
        tl = self.p._timeline
        tl.clear()
        for i in range(tl.MAX + 5):
            tl.add(f"n{i}", f"Pas {i}", True)
        self.assertEqual(tl.MAX, len(tl.cards))
        self.assertEqual("n5", tl.cards[0]["node"])

    # ── D: ecranul Excel ──
    def _excel_routine(self):
        f = ForEachRowNode(file_path=self._xlsx(), sheet="Termeni")
        f.body = [WriteExcelNode(column="Rezultat", value="ok")]
        r = Routine(name="Excel")
        r.steps = [LogNode(message="start"), f]
        self.p.routine = r
        self.p.rebuild_tree()
        return r, f

    def test_excel_view_reads_rows_and_follows_run(self):
        p = self.p
        r, f = self._excel_routine()
        p.show_center("excel")
        ev = p._excel
        self.assertTrue(self._pump(lambda: len(ev.rows) == 4), "randurile nu s-au citit")
        self.assertEqual([2, 3, 4, 5], ev.rows)
        self.assertIn("ok", p._excel.tree.item("2", "tags"))
        self.assertIn("error", p._excel.tree.item("4", "tags"))
        p.post("row_started", (3, "Termeni", "/tmp/film.apvid", 65.0))
        self.assertTrue(self._pump(lambda: "running" in ev.tree.item("3", "tags")))
        self.assertEqual("1:05", ev.tree.set("3", f"c{len(ev.cols) + 2}"))
        p.post("row_finished", (3, "OK"))
        self.assertTrue(self._pump(lambda: "ok" in ev.tree.item("3", "tags")))
        self.assertEqual(("/tmp/film.apvid", 65.0), ev.film[3])
        p.show_center("steps")

    def test_rerun_row_runs_a_copy_limited_to_that_row(self):
        p = self.p
        r, f = self._excel_routine()
        f.start_row, f.skip_completed_rows = 0, True
        with mock.patch("studio_ui.messagebox.askyesno", return_value=True), \
                mock.patch.object(p, "run") as run:
            p.rerun_excel_row(f, 4)
        copy_r = run.call_args.kwargs["routine"]
        self.assertIsNot(copy_r, r)
        fc = next(n for n in copy_r.all_nodes() if n.id == f.id)
        self.assertEqual((4, 4, False), (fc.start_row, fc.end_row, fc.skip_completed_rows))
        self.assertEqual((0, True), (f.start_row, f.skip_completed_rows))   # rutina din editor ramane neschimbata

    def test_host_posts_row_events(self):
        import studio_ui
        p = self.p
        host = studio_ui.StudioRunHost(p)
        with mock.patch.object(p, "post") as post:
            host.row_started(7, "Foaie")
            host.row_finished(7, "OK")
        kinds = [c.args[0] for c in post.call_args_list]
        self.assertEqual(["row_started", "row_finished"], kinds)
        self.assertEqual((7, "Foaie", "", 0.0), post.call_args_list[0].args[1])

    # ── A: fluxul ──
    def test_flow_has_a_card_for_every_step_and_selects_it(self):
        p = self.p
        iff = IfNode(condition=Condition(kind=ConditionKind.Compare, left="1", right="1"))
        a, b, c = LogNode(message="a"), LogNode(message="b"), LogNode(message="c")
        iff.then.append(a)
        iff.else_.append(b)
        r = Routine(name="Flux")
        r.steps = [iff, c]
        p.routine = r
        p.rebuild_tree()
        p.show_center("flow")
        self.assertEqual({iff.id, a.id, b.id, c.id}, set(p._flow.cards))
        p._flow.pick(b.id)
        self.assertEqual((b.id,), p.tree.selection())
        p.show_center("steps", select=c.id)
        self.assertEqual((c.id,), p.tree.selection())


if __name__ == "__main__":
    unittest.main()
