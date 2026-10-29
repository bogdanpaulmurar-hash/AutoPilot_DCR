# -*- coding: utf-8 -*-
# ============================================================
# AutoPilot DC — Teste: backup și restaurare (backup.py), pe foldere temporare
#   Rulare:  py -m unittest tests.test_backup
# ============================================================

import json
import os
import sys
import tempfile
import unittest
import zipfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import backup  # noqa: E402


def _write(path, text="x"):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def _read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


class BackupTests(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="apdc_bak_")
        self.roots = backup.Roots(app=os.path.join(self.d, "app"), appdata=os.path.join(self.d, "appdata"),
                                  library=os.path.join(self.d, "Drive", "Rutine"))
        r = self.roots
        _write(os.path.join(r.app, "config.json"), '{"theme": "dark"}')
        _write(os.path.join(r.app, "rutine_salvate", "veche.json"), "rec")
        _write(os.path.join(r.app, "notite", "n.txt"), "nota")
        _write(os.path.join(r.app, "AutoPilot_DC_app.py"), "cod")                 # codul nu intra in backup
        _write(os.path.join(r.appdata, "limba.json"), '{"limba": "de"}')
        _write(os.path.join(r.appdata, "Studio", "obiecte.json"), "obiecte")
        _write(os.path.join(r.appdata, "Studio", "rutine", "A.rpr.json"), "A")
        _write(os.path.join(r.appdata, "Studio", "rezultate", "Raport.xlsx"), "rez")
        _write(os.path.join(r.appdata, "Studio", "browser-profil", "Cookies"), "secret")
        _write(os.path.join(r.appdata, "Studio", "studio-setari.json"),
               json.dumps({"browser": "Edge", "routines_folder": r.library,
                           "last_routine_path": os.path.join(self.d, "nu_exista.rpr.json")}))
        _write(os.path.join(r.library, "Sandbox.pregatire.json"), "prep")
        _write(os.path.join(r.library, "sub", "B.rpr.json"), "B")

    def test_backup_contents(self):
        z = os.path.join(self.d, "out", "b.zip")
        info = backup.create_backup(z, self.roots)
        names = set(zipfile.ZipFile(z).namelist())
        for n in ("app/config.json", "app/rutine_salvate/veche.json", "app/notite/n.txt", "appdata/limba.json",
                  "appdata/Studio/obiecte.json", "appdata/Studio/rutine/A.rpr.json",
                  "biblioteca/Sandbox.pregatire.json", "biblioteca/sub/B.rpr.json", "backup.json"):
            self.assertIn(n, names)
        self.assertNotIn("app/AutoPilot_DC_app.py", names)
        self.assertFalse(any("browser-profil" in n for n in names))
        self.assertFalse(any("/rezultate/" in n for n in names))
        self.assertEqual(info.files, len(names) - 1)
        with_results = os.path.join(self.d, "out", "r.zip")
        backup.create_backup(with_results, self.roots, include_results=True)
        self.assertIn("appdata/Studio/rezultate/Raport.xlsx", zipfile.ZipFile(with_results).namelist())

    def test_restore_on_same_pc_with_safety_backup(self):
        z = os.path.join(self.d, "b.zip")
        backup.create_backup(z, self.roots)
        _write(os.path.join(self.roots.appdata, "Studio", "obiecte.json"), "schimbat")
        os.remove(os.path.join(self.roots.library, "sub", "B.rpr.json"))
        res = backup.restore_backup(z, self.roots)
        self.assertEqual("obiecte", _read(os.path.join(self.roots.appdata, "Studio", "obiecte.json")))
        self.assertEqual("B", _read(os.path.join(self.roots.library, "sub", "B.rpr.json")))
        self.assertTrue(os.path.isfile(res.safety_backup))
        names = zipfile.ZipFile(res.safety_backup).namelist()
        self.assertIn("appdata/Studio/obiecte.json", names)
        # backup-ul automat nu intra in backup-urile urmatoare
        z2 = os.path.join(self.d, "b2.zip")
        backup.create_backup(z2, self.roots)
        self.assertFalse(any("backup-automat" in n for n in zipfile.ZipFile(z2).namelist()))
        st = json.loads(_read(os.path.join(self.roots.appdata, "Studio", "studio-setari.json")))
        self.assertEqual("", st["last_routine_path"])       # calea veche nu exista -> golita

    def test_restore_on_other_pc_moves_library(self):
        z = os.path.join(self.d, "b.zip")
        backup.create_backup(z, self.roots)
        # alt PC: alte foldere; folderul rutinelor de pe PC-ul vechi e pe un disc care lipseste
        with zipfile.ZipFile(z) as src:
            info = json.loads(src.read("backup.json"))
            info["paths"]["library"] = os.path.join(self.d, "disc_lipsa", "Drive", "Rutine")
            moved = os.path.join(self.d, "moved.zip")
            with zipfile.ZipFile(moved, "w") as dst:
                for n in src.namelist():
                    dst.writestr(n, json.dumps(info) if n == "backup.json" else src.read(n))
        other = backup.Roots(app=os.path.join(self.d, "pc2", "app"), appdata=os.path.join(self.d, "pc2", "appdata"))
        res = backup.restore_backup(moved, other)
        self.assertTrue(res.library.endswith(os.path.join("Studio", "rutine", "biblioteca")))
        self.assertFalse(os.path.exists(os.path.join(self.d, "disc_lipsa")))
        self.assertEqual("B", _read(os.path.join(res.library, "sub", "B.rpr.json")))
        st = json.loads(_read(os.path.join(other.appdata, "Studio", "studio-setari.json")))
        self.assertEqual(res.library, st["routines_folder"])
        self.assertTrue(res.notes)
        self.assertEqual('{"theme": "dark"}', _read(os.path.join(other.app, "config.json")))
        self.assertEqual("A", _read(os.path.join(other.appdata, "Studio", "rutine", "A.rpr.json")))

    def test_not_a_backup_and_zip_slip(self):
        bad = os.path.join(self.d, "bad.zip")
        with zipfile.ZipFile(bad, "w") as z:
            z.writestr("altceva.txt", "x")
        with self.assertRaises(KeyError):
            backup.restore_backup(bad, self.roots)
        evil = os.path.join(self.d, "evil.zip")
        with zipfile.ZipFile(evil, "w") as z:
            z.writestr("backup.json", json.dumps({"paths": {}}))
            z.writestr("app/../../evil.txt", "x")
            z.writestr("app/ok.txt", "ok")
        res = backup.restore_backup(evil, self.roots)
        self.assertFalse(os.path.exists(os.path.join(self.d, "evil.txt")))
        self.assertEqual(1, res.files)


if __name__ == "__main__":
    unittest.main()
