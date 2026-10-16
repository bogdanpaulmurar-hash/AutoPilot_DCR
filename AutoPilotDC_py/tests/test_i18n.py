# -*- coding: utf-8 -*-
# ============================================================
# AutoPilot DC — Teste limbi (RO / EN / DE) si instructiuni.
#   Rulare:  py -m unittest tests.test_i18n
# ============================================================

import json
import os
import string
import sys
import unittest

APP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, APP)

import i18n  # noqa: E402
import instructions_ui  # noqa: E402


def _fields(t):
    return sorted(f for _, f, _, _ in string.Formatter().parse(t) if f is not None)


class TranslationFileTests(unittest.TestCase):
    def test_files_have_same_keys_and_placeholders(self):
        en = json.load(open(os.path.join(APP, "i18n", "en.json"), encoding="utf-8"))
        de = json.load(open(os.path.join(APP, "i18n", "de.json"), encoding="utf-8"))
        self.assertEqual(set(en), set(de))
        self.assertGreater(len(en), 1000)
        for src in en:
            if "{" in src and any(c.isdigit() for c in src):
                try:
                    want = _fields(src)
                except ValueError:
                    continue
                self.assertEqual(want, _fields(en[src]), src)
                self.assertEqual(want, _fields(de[src]), src)

    def test_translate_exact_template_and_unknown(self):
        try:
            i18n.load("en")
            self.assertEqual("Save", i18n.tr("Salveaza"))
            self.assertEqual("Routine 'Raport' loaded (3 steps)", i18n.tr("Rutina 'Raport' incarcata (3 pasi)"))
            self.assertEqual("  ✖  Cancel   ", i18n.tr("  ✖  Anuleaza   "))
            self.assertEqual("Ceva necunoscut", i18n.tr("Ceva necunoscut"))
            # numele de variabile / obiecte (un singur cuvant) nu se traduc
            self.assertIn("{Rand.A}", i18n.tr("Pasii din interior ruleaza o data pentru fiecare rand. Valorile randului "
                                              "sunt variabile: {Rand.TitluColoana}, {Rand.A} (dupa litera), {Rand.#} "
                                              "(numarul randului)."))
            # sabloane in sabloane: conditia din interiorul lui "Daca"
            i18n.load("de")
            self.assertEqual("Wenn [Buton_OK] existiert", i18n.tr("Daca [Buton_OK] exista"))
        finally:
            i18n.load("ro")
        self.assertEqual("Salveaza", i18n.tr("Salveaza"))

    def test_saved_language_roundtrip(self):
        import tempfile
        old = i18n._SETTINGS
        i18n._SETTINGS = os.path.join(tempfile.mkdtemp(), "limba.json")
        try:
            self.assertEqual("ro", i18n.saved_language())
            i18n.save_language("de")
            self.assertEqual("de", i18n.saved_language())
        finally:
            i18n._SETTINGS = old


class InstructionsTests(unittest.TestCase):
    def test_three_languages_same_chapters(self):
        counts = {}
        for code, _ in instructions_ui.LANGS:
            text = instructions_ui.load_doc(code)
            ch = instructions_ui.chapters(text)
            counts[code] = len(ch)
            self.assertGreaterEqual(len(ch), 20, code)
            for title, body in ch:
                self.assertTrue(body.strip(), f"{code}: {title} e gol")
        self.assertEqual(1, len(set(counts.values())), counts)

    def test_every_chapter_has_example_or_steps(self):
        for code, _ in instructions_ui.LANGS:
            for title, body in instructions_ui.chapters(instructions_ui.load_doc(code)):
                self.assertTrue("> " in body or "\n1. " in body or "\n- " in body, f"{code}: {title}")


if __name__ == "__main__":
    unittest.main()
