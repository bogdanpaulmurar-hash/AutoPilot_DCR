# -*- coding: utf-8 -*-
# ============================================================
# AutoPilot DC — Teste video: inregistrare, editare (taiere, texte, pauze), export, filmele din Instructiuni,
# semnalele motorului pentru randurile Excel (film separat pe rand).
#   Rulare:  py -m unittest tests.test_video
# ============================================================

import glob
import os
import sys
import tempfile
import time
import unittest

APP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, APP)

from PIL import Image  # noqa: E402

import screen_recorder as sr  # noqa: E402


def _slide_video(path, seconds=10):
    b = sr.SlideVideoBuilder("Test", (320, 200), fps=4)
    for i in range(seconds):
        b.image(Image.new("RGB", (320, 200), (i * 20, 80, 120)))
        b.move(50 + i * 10, 60, 0.5, click=i % 3 == 0)
        b.wait(0.5)
        b.marker(f"pas {i}")
    b.caption({"ro": "Salut", "en": "Hello", "de": "Hallo"}, 2.0)
    return b.save(path)


class VideoFileTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="apdc_vid_")
        self.path = _slide_video(os.path.join(self.dir, "t.apvid"))

    def test_timeline_trim_cut_idle(self):
        v = sr.VideoFile(self.path)
        full = v.out_duration
        self.assertGreater(full, 9)
        v.edits["trim"] = [1.0, 8.0]
        v.rebuild()
        self.assertAlmostEqual(7.0, v.out_duration, delta=0.6)
        v.edits["cuts"].append([2.0, 4.0])
        v.rebuild()
        self.assertAlmostEqual(5.0, v.out_duration, delta=0.6)
        self.assertGreaterEqual(v.src_at(1.5), 4.0)   # dupa taiere sarim peste 2-4
        v.edits.update({"trim": None, "cuts": []})
        v.m["cursor"] = []                              # fara miscare: pauzele se pot scurta
        v.m["clicks"] = []
        v._frame_times = [0.0]
        v.edits["idle"] = 1.0
        v.rebuild()
        self.assertLess(v.out_duration, full / 2)
        v.close()

    def test_render_caption_language_and_save(self):
        v = sr.VideoFile(self.path)
        t0 = v.edits["captions"][0]["t0"] + 0.5
        self.assertEqual("Hello", v.caption_text(v.edits["captions"][0], "en"))
        img = v.render(t0, "de")
        self.assertEqual((320, 200), img.size)
        v.edits["blur"].append({"t0": 0, "t1": 99, "rect": [10, 10, 50, 50]})
        v.edits["cuts"].append([1.0, 2.0])
        v.save_edits()
        v.close()
        v2 = sr.VideoFile(self.path)
        self.assertEqual([[1.0, 2.0]], v2.edits["cuts"])
        self.assertEqual(1, len(v2.edits["blur"]))
        v2.close()

    def test_export_gif(self):
        v = sr.VideoFile(self.path)
        out = v.export_gif(os.path.join(self.dir, "t.gif"), fps=4, width=200)
        v.close()
        with Image.open(out) as g:
            self.assertGreater(getattr(g, "n_frames", 1), 3)


class IntroOutroTests(unittest.TestCase):
    """v4.16: filmul rularii = introducere + ce s-a inregistrat (pana la ultimul pas) + iesire."""

    def setUp(self):
        self._grab = sr.ImageGrab.grab
        self.n = 0

        def fake_grab(bbox=None, all_screens=False):   # ecran care se schimba doar la inceput
            self.n += 1
            return Image.new("RGB", (bbox[2] - bbox[0], bbox[3] - bbox[1]), (min(self.n, 3) * 60, 80, 120))
        sr.ImageGrab.grab = fake_grab

    def tearDown(self):
        sr.ImageGrab.grab = self._grab

    def _rec(self, **kw):
        d = tempfile.mkdtemp(prefix="apdc_io_")
        return sr.ScreenRecorder(sr.VideoSettings(folder=d, fps=8, scale=0.25, area="primary", intro_s=2.0,
                                                  outro_s=3.0, idle_compress_s=0.5, **kw))

    def test_intro_last_frame_and_outro(self):
        r = self._rec()
        r.start("Rutina test", intro=["▶ Rulare automata", "Inceput: azi"])
        time.sleep(1.5)
        self.n = 100                       # ultimul pas schimba ecranul chiar inainte de oprire
        v = sr.VideoFile(r.stop(["✅ Rutina s-a terminat cu succes", "Durata: 00:02"]))
        frames = v.m["frames"]
        self.assertEqual([0.0, "frames/intro.webp"], frames[0])
        self.assertGreaterEqual(frames[1][0], 2.0)                 # inregistrarea incepe dupa introducere
        self.assertEqual("frames/outro.webp", frames[-1][1])
        end = frames[-2][0]
        self.assertGreaterEqual(end, 3.4)                          # ultimul cadru = ecranul de la oprire
        self.assertAlmostEqual(v.duration, frames[-1][0] + 3.0, delta=0.05)
        self.assertEqual([0.0, 2.0], v.m["intro"])
        # pauzele se scurteaza, dar introducerea, finalul si iesirea raman intregi
        self.assertGreater(v.out_duration, 2.0 + 1.0 + 3.0 - 0.3)
        self.assertEqual("▶ Rutina test", v.m["markers"][0][1])
        img = v.render(0.5)
        self.assertEqual(tuple(v.m["size"]), img.size)
        v.close()

    def test_manual_without_intro(self):
        r = self._rec()
        r.start("Manual")
        time.sleep(0.5)
        v = sr.VideoFile(r.stop())
        self.assertNotIn("intro", v.m)
        self.assertNotIn("outro", v.m)
        self.assertLess(v.m["frames"][0][0], 0.5)
        v.close()

    def test_disabled_in_settings(self):
        r = self._rec(intro_outro=False)
        r.start("Fara", intro=["x"])
        time.sleep(0.3)
        v = sr.VideoFile(r.stop(["y"]))
        self.assertNotIn("intro", v.m)
        self.assertNotIn("outro", v.m)
        v.close()

    def test_controller_outro_lines(self):
        import video_ui
        from rpr.host import RunResult
        c = video_ui.VideoController.__new__(video_ui.VideoController)
        c._run_t0 = time.monotonic() - 65
        ok = c._outro(RunResult(success=True, steps_executed=12, errors=0, rows_ok=3, rows_failed=1))
        self.assertTrue(ok[0].startswith("✅"))
        self.assertIn("01:05", ok[1])
        self.assertIn("12", ok[2])
        bad = c._outro(RunResult(success=False, message="Nu am gasit [Buton_OK]"))
        self.assertTrue(bad[0].startswith("❌") and "Buton_OK" in bad[0])
        self.assertTrue(video_ui.VideoController._intro("Rand 3")[-1] == "Rand 3")


@unittest.skipUnless(os.name == "nt", "doar Windows")
class RecorderTests(unittest.TestCase):
    def test_record_marker_split(self):
        d = tempfile.mkdtemp(prefix="apdc_rec_")
        r = sr.ScreenRecorder(sr.VideoSettings(folder=d, fps=4, scale=0.4))
        p1 = r.start("Rutina")
        time.sleep(1.2)
        r.marker("pas 1")
        old = r.split("Rutina_rand2")
        time.sleep(1.0)
        p2 = r.stop()
        self.assertEqual(p1, old)
        self.assertNotEqual(p1, p2)
        for p in (p1, p2):
            v = sr.VideoFile(p)
            self.assertGreaterEqual(len(v.m["frames"]), 1)
            self.assertGreater(v.duration, 0.5)
            v.close()
        v = sr.VideoFile(p1)
        self.assertEqual("pas 1", v.m["markers"][0][1])
        v.close()

    def test_pause_does_not_count(self):
        d = tempfile.mkdtemp(prefix="apdc_rec_")
        r = sr.ScreenRecorder(sr.VideoSettings(folder=d, fps=4, scale=0.3))
        r.start("P")
        time.sleep(0.6)
        r.pause(True)
        time.sleep(1.0)
        r.pause(False)
        time.sleep(0.4)
        v = sr.VideoFile(r.stop())
        self.assertLess(v.duration, 1.6)
        v.close()


class TutorialVideosTests(unittest.TestCase):
    def test_all_tutorials_present_and_trilingual(self):
        import instructions_ui
        files = {os.path.basename(p)[:-6] for p in glob.glob(os.path.join(APP, "docs", "video", "*.apvid"))}
        for code, _ in instructions_ui.VIDEOS:
            self.assertIn(code, files)
            v = sr.VideoFile(os.path.join(APP, "docs", "video", code + ".apvid"))
            self.assertGreater(len(v.m["frames"]), 1, code)
            for c in v.edits["captions"]:
                self.assertEqual({"ro", "en", "de"}, set(c["text"]), code)
            v.close()
        # fiecare link [video:...] din instructiuni are un film
        for lang, _ in instructions_ui.LANGS:
            for line in instructions_ui.load_doc(lang).splitlines():
                if line.startswith("[video:"):
                    self.assertIn(line[7:-1], files, lang)


class EngineRowHooksTests(unittest.TestCase):
    def test_row_started_finished(self):
        import openpyxl
        from rpr import DriverProvider, ObjectRepository, RprEngine, RunHost
        from rpr.model import ForEachRowNode, LogNode, Routine
        d = tempfile.mkdtemp(prefix="apdc_rows_")
        xl = os.path.join(d, "date.xlsx")
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(["Nume"])
        for n in ("Ana", "Ion", "Maria"):
            ws.append([n])
        wb.save(xl)

        class H(RunHost):
            def __init__(self):
                self.ev = []

            def row_started(self, row, sheet):
                self.ev.append(("start", row))

            def row_finished(self, row, status):
                self.ev.append(("end", row, status))
        r = Routine(name="Rows")
        r.settings.do_not_disturb = False
        r.settings.guard_enabled = False
        r.steps.append(ForEachRowNode(file_path=xl, key_column="Nume", status_column="",
                                      body=[LogNode(message="{Rand.Nume}")]))
        h = H()
        res = RprEngine(ObjectRepository(), DriverProvider(), h, d).run(r)
        self.assertTrue(res.success, res.message)
        self.assertEqual([("start", 2), ("end", 2, "OK"), ("start", 3), ("end", 3, "OK"), ("start", 4), ("end", 4, "OK")],
                         h.ev)


class RecoverTests(unittest.TestCase):
    """Film neterminat (aplicatia blocata in timpul inregistrarii): se reface din cadre + jurnal."""

    def _broken(self, with_journal):
        import io
        import json
        import zipfile
        d = tempfile.mkdtemp(prefix="apdc_rec_")
        path = os.path.join(d, "film.apvid")
        z = zipfile.ZipFile(path, "w", zipfile.ZIP_STORED)
        frames = []
        for k in range(4):
            buf = io.BytesIO()
            Image.new("RGB", (64, 40), (k * 40, 10, 10)).save(buf, "WEBP")
            name = f"frames/{k + 1:06d}.webp"
            z.writestr(name, buf.getvalue())
            frames.append([k * 2.0, name])
        z.fp.flush()
        if with_journal:   # jurnalul are doar primele 3 cadre (al 4-lea a venit dupa ultimul jurnal)
            m = {"version": 1, "title": "Rutina", "size": [64, 40], "fps": 4, "frames": frames[:3],
                 "cursor": [], "clicks": [], "markers": [[2.0, "Rand 2"]], "duration": 4.0,
                 "edits": {"trim": None, "cuts": [], "captions": [], "blur": [], "idle": 2.0}}
            with open(path + sr.JOURNAL_EXT, "w", encoding="utf-8") as f:
                json.dump(m, f)
        # fara z.close(): ca dupa o oprire brusca (lipseste cuprinsul zip-ului si manifest.json)
        z.fp.close()
        z.fp = None
        return path

    def test_recover_with_journal(self):
        path = self._broken(True)
        v = sr.VideoFile(path)
        self.assertEqual(4, len(v.m["frames"]))
        self.assertEqual([[2.0, "Rand 2"]], v.m["markers"])
        self.assertIn("recuperat", v.m["title"])
        v.close()
        self.assertTrue(os.path.exists(path + ".stricat"))
        self.assertFalse(os.path.exists(path + sr.JOURNAL_EXT))

    def test_recover_without_journal(self):
        path = self._broken(False)
        v = sr.VideoFile(path)
        self.assertEqual(4, len(v.m["frames"]))
        self.assertEqual([64, 40], list(v.size))
        v.close()


if __name__ == "__main__":
    unittest.main()
