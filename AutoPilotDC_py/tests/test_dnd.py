# -*- coding: utf-8 -*-
# ============================================================
# AutoPilot DC v4.1 — Teste "Nu deranja" (logica, fara sa atinga Windows):
# pornirea / oprirea reala sunt inlocuite cu functii false care numara apelurile.
# ============================================================

import os
import sys
import threading
import time
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import autopilot_safety as s  # noqa: E402

D = s.DoNotDisturb


class FakeWindows:
    """Starea "Windows": on = notificari oprite. Pornirea / oprirea dureaza putin (ca in realitate)."""

    def __init__(self, already_on=False, delay=0.15):
        self.on = already_on
        self.delay = delay
        self.turn_on_calls = 0
        self.turn_off_calls = 0

    def turn_on(self):
        self.turn_on_calls += 1
        time.sleep(self.delay)
        if self.on:          # pornit de utilizator: nu e al nostru
            return False
        self.on = True
        return True

    def turn_off(self):
        self.turn_off_calls += 1
        time.sleep(self.delay)
        self.on = False


class DndLogic(unittest.TestCase):
    def setUp(self):
        self._orig = (D._turn_on, D._turn_off, s.IS_WINDOWS)
        self.win = FakeWindows()
        D._turn_on = classmethod(lambda cls: self.win.turn_on())
        D._turn_off = classmethod(lambda cls: self.win.turn_off())
        s.IS_WINDOWS = True
        D._users, D._applied, D._req, D._done = 0, False, 0, 0

    def tearDown(self):
        D.wait_settled(5)
        D._turn_on, D._turn_off, s.IS_WINDOWS = self._orig

    def test_normal_run(self):
        D.enable(wait=False)
        D.wait_settled(5)
        self.assertTrue(self.win.on)
        D.restore()
        D.wait_settled(5)
        self.assertFalse(self.win.on)

    def test_stop_immediately_after_start_restores(self):
        """Cauza problemei: oprire imediata (Stop in countdown) -> notificarile trebuie sa revina."""
        for _ in range(20):
            D.enable(wait=False)
            D.restore()
        D.wait_settled(10)
        self.assertFalse(self.win.on, "Nu deranja a ramas pornit dupa oprire imediata")

    def test_overlapping_users(self):
        """Inregistrare + rulare suprapuse: notificarile revin doar dupa ultima."""
        D.enable(wait=False)
        D.enable(wait=False)
        D.wait_settled(5)
        D.restore()
        D.wait_settled(5)
        self.assertTrue(self.win.on)
        D.restore()
        D.wait_settled(5)
        self.assertFalse(self.win.on)

    def test_already_on_by_user_is_left_on(self):
        self.win.on = True
        D.enable(wait=False)
        D.restore()
        D.wait_settled(5)
        self.assertTrue(self.win.on, "DND pornit de utilizator nu trebuie oprit de aplicatie")
        self.assertEqual(0, self.win.turn_off_calls)

    def test_restore_from_many_threads(self):
        threads = [threading.Thread(target=lambda: (D.enable(wait=False), time.sleep(0.01), D.restore()))
                   for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        D.wait_settled(10)
        self.assertFalse(self.win.on)
        self.assertEqual(0, D._users)

    def test_restore_all_on_close(self):
        D.enable(wait=False)
        D.enable(wait=False)
        D.restore_all(5)
        self.assertFalse(self.win.on)

    def test_extra_restore_is_harmless(self):
        D.restore()
        D.restore()
        D.wait_settled(5)
        self.assertEqual(0, D._users)
        self.assertEqual(0, self.win.turn_on_calls)


if __name__ == "__main__":
    unittest.main()
