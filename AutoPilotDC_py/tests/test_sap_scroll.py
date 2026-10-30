# -*- coding: utf-8 -*-
# ============================================================
# AutoPilot DC — Teste: pasul "SAP: deruleaza tabelul" (v4.22)
#   Rulare:  py -m unittest tests.test_sap_scroll
# Tabelele SAP sunt simulate (fara SAP GUI): GuiTableControl cu bara de derulare
# si GuiGridView (ALV) cu FirstVisibleRow.
# ============================================================

import os
import sys
import unittest

APP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, APP)

import i18n  # noqa: E402
from rpr.drivers.base import RprStepException  # noqa: E402
from rpr.drivers.sap_table import scroll_table  # noqa: E402
from rpr.importer import StepImporter  # noqa: E402
from rpr.model import RprAction, UiTechnology, action_info  # noqa: E402


class _Bar:
    def __init__(self, maximum):
        self.Position = 0
        self.Maximum = maximum


class FakeTableControl:
    """GuiTableControl: randurile din ID sunt relative la zona vizibila; bara se opreste la Maximum."""
    Type = "GuiTableControl"
    Id = "/app/con[0]/ses[0]/wnd[0]/usr/tblROLURI"

    def __init__(self, rows, visible):
        self.RowCount = rows
        self.VisibleRowCount = visible
        self.VerticalScrollbar = _Bar(max(0, rows - visible))
        self.scrolls = 0

    def scroll(self, pos):
        # ca SAP: pozitia se limiteaza la Maximum
        self.VerticalScrollbar.Position = max(0, min(pos, self.VerticalScrollbar.Maximum))
        self.scrolls += 1


class _BarProxy:
    def __init__(self, table):
        self._t = table

    @property
    def Position(self):
        return self._t.VerticalScrollbar.Position

    @Position.setter
    def Position(self, v):
        self._t.scroll(v)


class FakeGrid:
    Type = "GuiGridView"
    Id = "/app/con[0]/ses[0]/wnd[0]/usr/cntlGRID/shellcont/shell"

    def __init__(self, rows, visible):
        self.RowCount = rows
        self.VisibleRowCount = visible
        self.FirstVisibleRow = 0


def _scroll(table, value):
    """Ca in driver: dupa scroll obiectul tabelului se recitește (aici acelasi obiect)."""
    if isinstance(table, FakeTableControl):
        wrapper = _TableWrapper(table)
        return scroll_table(wrapper, value, lambda: None, lambda: wrapper)
    return scroll_table(table, value, lambda: None, lambda: table)


class _TableWrapper:
    """Expune bara de derulare cu setter, ca obiectul COM."""
    def __init__(self, t):
        self._t = t
        self.Type, self.Id = t.Type, t.Id
        self.RowCount, self.VisibleRowCount = t.RowCount, t.VisibleRowCount

    @property
    def VerticalScrollbar(self):
        bar = _BarProxy(self._t)
        bar.Maximum = self._t.VerticalScrollbar.Maximum
        return bar


class ScrollTableTests(unittest.TestCase):
    def test_loop_reaches_every_row_including_the_last_page(self):
        # 100 de randuri, 40 vizibile: randurile raman in lista (se marcheaza "sters")
        t = FakeTableControl(rows=100, visible=40)
        seen = []
        for rep in range(1, 101):                       # {Repetare} = 1..100
            pos = int(_scroll(t, str(rep)))
            first = t.VerticalScrollbar.Position
            self.assertTrue(0 <= pos < 40, (rep, pos))
            seen.append(first + pos)                    # randul absolut pe care s-ar da click
        self.assertEqual(seen, list(range(100)))        # fiecare rand o data, si ultimele 40
        self.assertEqual(t.VerticalScrollbar.Position, 60)

    def test_relative_start_end(self):
        t = FakeTableControl(rows=10, visible=4)
        self.assertEqual(_scroll(t, "+1"), "0")
        self.assertEqual(t.VerticalScrollbar.Position, 1)
        self.assertEqual(_scroll(t, "+ 3"), "0")
        self.assertEqual(t.VerticalScrollbar.Position, 4)
        self.assertEqual(_scroll(t, "-2"), "0")
        self.assertEqual(t.VerticalScrollbar.Position, 2)
        self.assertEqual(_scroll(t, "sfarsit"), "3")    # ultimul rand e al 4-lea vizibil
        self.assertEqual(t.VerticalScrollbar.Position, 6)
        self.assertEqual(_scroll(t, "Inceput"), "0")
        self.assertEqual(t.VerticalScrollbar.Position, 0)
        self.assertEqual(_scroll(t, "-5"), "0")          # nu trece de primul rand

    def test_no_scroll_when_already_there(self):
        t = FakeTableControl(rows=10, visible=4)
        _scroll(t, "1")
        self.assertEqual(t.scrolls, 0)

    def test_errors(self):
        t = FakeTableControl(rows=5, visible=4)
        for bad in ("", "abc", "0", "1.5"):
            with self.assertRaises(RprStepException, msg=bad):
                _scroll(t, bad)
        with self.assertRaises(RprStepException) as cm:
            _scroll(t, "6")
        self.assertIn("5", str(cm.exception))

    def test_alv_grid(self):
        g = FakeGrid(rows=50, visible=20)
        self.assertEqual(_scroll(g, "10"), "0")
        self.assertEqual(g.FirstVisibleRow, 9)
        self.assertEqual(_scroll(g, "45"), "14")        # ultima pagina: grila sta la 30
        self.assertEqual(g.FirstVisibleRow, 30)


class ScrollStepTests(unittest.TestCase):
    def setUp(self):
        i18n.load("ro")

    def tearDown(self):
        i18n.load("ro")

    def test_action_info(self):
        info = action_info(RprAction.SapScrollTable)
        self.assertTrue(info.needs_target)
        self.assertTrue(info.produces_output)
        self.assertEqual(info.technologies, (UiTechnology.Sap,))

    def test_import_ai(self):
        res = StepImporter().parse('SAP CONECTEAZA\nREPETA 5000\n'
                                   '  SAP DERULEAZA sap "wnd[0]/usr/tblROLURI" = {Repetare}\n'
                                   '  CLICK sap "wnd[0]/usr/tblROLURI/btnDEL[5,{Pozitie}]"\n'
                                   '  SAP DERULEAZA sap "wnd[0]/usr/tblROLURI" = +1 -> {Poz2}\n'
                                   'SFARSIT')
        self.assertEqual(res.errors, [], [i.message for i in res.errors])
        steps = [n for n in res.routine.all_nodes() if getattr(n, "action", None) == RprAction.SapScrollTable]
        self.assertEqual([(s.value, s.output_variable) for s in steps], [("{Repetare}", "Pozitie"), ("+1", "Poz2")])
        self.assertTrue(all(s.technology == UiTechnology.Sap and s.target for s in steps))

    def test_import_needs_value(self):
        res = StepImporter().parse('SAP DERULEAZA sap "wnd[0]/usr/tblROLURI"')
        self.assertTrue(res.errors)

    def test_import_english(self):
        res = StepImporter().parse('SAP SCROLL sap "wnd[0]/usr/tblX" = end')
        self.assertEqual(res.errors, [], [i.message for i in res.errors])
        self.assertEqual(res.routine.steps[0].action, RprAction.SapScrollTable)


if __name__ == "__main__":
    unittest.main()
