# -*- coding: utf-8 -*-
# ============================================================
# AutoPilot DC — genereaza filmele scurte din 📖 Instructiuni (docs/video/*.apvid)
#
# Porneste aplicatia reala (cu date temporare, nu atinge setarile tale), o comanda automat,
# face capturi ale ferestrei si muta un cursor animat pe butoanele reale. Textele de pe film
# sunt in romana / engleza / germana (playerul le arata in limba aleasa).
#
#   py tools\make_tutorials.py            -> toate filmele
#   py tools\make_tutorials.py 02 03      -> doar unele
# Regenereaza filmele dupa schimbari mari in interfata.
# ============================================================

import glob
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import time

APP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(APP, "docs", "video")
TMP = tempfile.mkdtemp(prefix="apdc_tut_")
os.environ["APPDATA"] = os.path.join(TMP, "appdata")
os.makedirs(os.path.join(TMP, "appdata", "AutoPilotDC", "Studio"), exist_ok=True)
json.dump({"browser": "Edge", "headless": True, "minimize_on_run": False},
          open(os.path.join(TMP, "appdata", "AutoPilotDC", "Studio", "studio-setari.json"), "w"))
json.dump({"folder": os.path.join(TMP, "filme"), "record_on_run": False},
          open(os.path.join(TMP, "appdata", "AutoPilotDC", "video.json"), "w"))
sys.path.insert(0, APP)
os.chdir(APP)

from PIL import ImageGrab  # noqa: E402

spec = importlib.util.spec_from_file_location("apdc", os.path.join(APP, "AutoPilot_DC_app.py"))
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
import autopilot_safety  # noqa: E402
import screen_recorder as sr  # noqa: E402
import studio_ui  # noqa: E402

autopilot_safety.DoNotDisturb.enable = staticmethod(lambda wait=True, timeout=25.0: False)
autopilot_safety.DoNotDisturb.restore = staticmethod(lambda wait=False, timeout=25.0: None)
studio_ui.input_dialog = lambda *a, **k: "https://the-internet.herokuapp.com/login"

app = mod.MainWindow()
root = app.root
W, H = 1280, 800
root.geometry(f"{W}x{H}+30+20")
ONLY = set(sys.argv[1:])


def L(ro, en, de):
    return {"ro": ro, "en": en, "de": de}


# ─────────────────────────────────────────────────────────────
# Mic "regizor": o lista de pasi executati cu root.after
# ─────────────────────────────────────────────────────────────
class Movie:
    def __init__(self, code, title):
        self.code, self.title = code, title
        self.b = sr.SlideVideoBuilder(title, (W, H), fps=8)
        self.actions = []

    # ── componente ──
    def do(self, fn, wait_ms=600):
        self.actions.append(("do", fn, wait_ms))
        return self

    def until(self, cond, timeout_s=60):
        self.actions.append(("until", cond, timeout_s))
        return self

    def snap(self):
        return self.do(self._snap, 0)

    def say(self, text, secs=3.5, pos="bottom"):
        return self.do(lambda: (self.b.caption(text, secs, pos), self.b.wait(secs)), 0)

    def point(self, widget_fn, click=True, secs=0.9):
        def f():
            w = widget_fn()
            if w is None:
                return
            w.update_idletasks()
            x = w.winfo_rootx() - root.winfo_rootx() + w.winfo_width() // 2
            y = w.winfo_rooty() - root.winfo_rooty() + w.winfo_height() // 2
            self.b.move(x, y, secs, click=click)
        return self.do(f, 0)

    def point_xy(self, xy_fn, click=True, secs=0.9):
        return self.do(lambda: self.b.move(*xy_fn(), secs, click=click), 0)

    def marker(self, text):
        return self.do(lambda: self.b.marker(text), 0)

    def _snap(self):
        root.update()
        time.sleep(0.25)
        root.update()
        x, y = root.winfo_rootx(), root.winfo_rooty()
        self.b.image(ImageGrab.grab(bbox=(x, y, x + W, y + H)), quality=62)

    def save(self):
        path = os.path.join(OUT_DIR, f"{self.code}.apvid")
        self.b.save(path)
        print(f"{self.code}: {os.path.getsize(path) // 1024} KB, {self.b.t:.0f} s")


def find_text(container, starts):
    """Primul widget (buton / eticheta) al carui text incepe cu `starts`."""
    stack = [container]
    while stack:
        w = stack.pop(0)
        try:
            t = w.cget("text")
            if isinstance(t, str) and t.strip().startswith(starts):
                return w
        except Exception:
            pass
        stack.extend(w.winfo_children())
    return None


def top_of(cls):
    for w in root.winfo_children():
        for d in [w] + list(w.winfo_children()):
            if isinstance(d, cls):
                return d
    st = app._studio
    if st is not None:
        for d in st.winfo_children():
            if isinstance(d, cls):
                return d
    return None


def tree_row(tree, iid):
    def f():
        bb = tree.bbox(iid)
        if not bb:
            return W // 2, H // 2
        return (tree.winfo_rootx() - root.winfo_rootx() + bb[0] + 120,
                tree.winfo_rooty() - root.winfo_rooty() + bb[1] + bb[3] // 2)
    return f


def st():
    return app._studio


def open_example(name):
    from rpr.storage import Examples, RprPaths
    Examples.install(st().repo)
    st().save_repository()
    st().refresh_objects()
    path = os.path.join(RprPaths.examples(), name)
    st().open_routine(path)
    for n in st().routine.all_nodes():   # in film fara intrebari (ar bloca rularea)
        if type(n).__name__ == "QuestionNode":
            n.enabled = False
    st().dirty = False


def first_iid(pred):
    for n in st().routine.all_nodes():
        if pred(n) and st().tree.exists(n.id):
            return n.id
    return None


# ─────────────────────────────────────────────────────────────
# Filmele
# ─────────────────────────────────────────────────────────────
movies = []


def recorder_movie():
    m = Movie("01_recorder", "Recorder")
    StepModel = mod.StepModel
    m.do(lambda: app._set_mode("recorder"), 800).do(lambda: app._nb.select(app._tab_recorder), 600).snap()
    m.say(L("Recorder: inregistrezi ce faci cu mouse-ul si tastatura, apoi rutina o repeta.",
            "Recorder: you record what you do with the mouse and keyboard, then the routine repeats it.",
            "Recorder: Sie zeichnen auf, was Sie mit Maus und Tastatur tun, dann wiederholt die Routine es."), 4)
    m.point(lambda: find_text(app.root, "⏺ Inregistreaza") or find_text(app.root, "Inregistreaza"))
    m.say(L("1. Apasa Inregistreaza (F5) si lucreaza normal. Pe margini apare chenarul verde REC.",
            "1. Press Record (F5) and work normally. A green REC border appears around the screen.",
            "1. Aufnehmen (F5) drücken und normal arbeiten. Ein grüner REC-Rahmen erscheint."), 4)

    def fill():
        steps = [StepModel(step_id=1, step_type="CLICK", description="Click pe Start", x=24, y=1060),
                 StepModel(step_id=2, step_type="TYPE", description="Scrie: notepad", text_input="notepad"),
                 StepModel(step_id=3, step_type="KEY", description="Tasta Enter", key_combo="enter"),
                 StepModel(step_id=4, step_type="DELAY", description="Pauza 1.5 s", delay_after=1.5),
                 StepModel(step_id=5, step_type="TYPE", description="Scrie: Raport zilnic", text_input="Raport zilnic"),
                 StepModel(step_id=6, step_type="KEY", description="Ctrl+S", key_combo="ctrl+s")]
        app._load_steps_to_ui(steps)
    m.do(fill, 600).snap()
    m.point(lambda: find_text(app.root, "⏹ Stop Rec") or find_text(app.root, "Stop Rec"))
    m.say(L("2. Stop Rec (F6): pasii apar in lista. Dublu click pe un pas = il editezi.",
            "2. Stop Rec (F6): the steps appear in the list. Double-click a step = edit it.",
            "2. Aufnahme stopp (F6): Die Schritte erscheinen in der Liste. Doppelklick = bearbeiten."), 4.5)
    m.point(lambda: app._entry_repeat if hasattr(app, "_entry_repeat") else None, click=False)
    m.say(L("3. Alege de cate ori se repeta rutina.", "3. Choose how many times the routine repeats.",
            "3. Wählen Sie, wie oft die Routine wiederholt wird."), 3)
    m.point(lambda: find_text(app.root, "▶ Ruleaza"))
    m.say(L("4. Ruleaza (F7). Pauza = F8, Stop = F9, STOP URGENTA = F12.",
            "4. Run (F7). Pause = F8, Stop = F9, EMERGENCY STOP = F12.",
            "4. Ausführen (F7). Pause = F8, Stopp = F9, NOT-STOPP = F12."), 4)
    m.point(lambda: find_text(app.root, "💾 Salveaza") or find_text(app.root, "Salveaza"))
    m.say(L("5. Salveaza rutina (Ctrl+S). O redeschizi din tab-ul Rutine.",
            "5. Save the routine (Ctrl+S). Reopen it from the Routines tab.",
            "5. Routine speichern (Ctrl+S). Im Tab Routinen wieder öffnen."), 4)
    m.say(L("Sfat: pentru rutine stabile (care nu depind de pozitia ferestrelor) foloseste Studio RPR.",
            "Tip: for stable routines (independent of window positions) use Studio RPR.",
            "Tipp: Für stabile Routinen (unabhängig von Fensterpositionen) Studio RPR verwenden."), 4)
    m.do(lambda: app._load_steps_to_ui([]), 100)
    return m


def web_movie():
    m = Movie("02_studio_web", "Studio: Web")
    m.do(lambda: app._set_mode("studio"), 1500).do(lambda: open_example("02_Web_Login_demo.rpr.json"), 1200).snap()
    m.say(L("Studio RPR: rutina pe obiecte. Exemplul 02 se autentifica pe un site de test.",
            "Studio RPR: an object-based routine. Example 02 logs into a test site.",
            "Studio RPR: objektbasierte Routine. Beispiel 02 meldet sich auf einer Testseite an."), 4)
    m.point(lambda: find_text(st(), "🌐  Deschide browser"), click=False)
    m.say(L("Blocurile din stanga se adauga cu un click: Deschide browser, Scrie text, Click...",
            "The blocks on the left are added with one click: Open browser, Type text, Click...",
            "Die Blöcke links werden per Klick eingefügt: Browser öffnen, Text schreiben, Klick..."), 4)
    m.point_xy(lambda: tree_row(st().tree, first_iid(lambda n: getattr(n, "action", "") == "TypeText"))())
    m.do(lambda: (st().tree.selection_set(first_iid(lambda n: getattr(n, "action", "") == "TypeText")),
                  st().tree.focus(first_iid(lambda n: getattr(n, "action", "") == "TypeText"))), 900).snap()
    m.say(L("Click pe un pas: in dreapta ii vezi proprietatile — obiectul, textul (poate fi o variabila).",
            "Click a step: its properties appear on the right — the object, the text (can be a variable).",
            "Klick auf einen Schritt: rechts erscheinen seine Eigenschaften — Objekt, Text (auch Variable)."), 4.5)
    m.point(lambda: find_text(app.root, "🎯 Web"), click=False)
    m.say(L("Obiectele noi le marchezi cu 🎯 Web (Spy): mouse-ul peste element in browser si click.",
            "New objects are marked with 🎯 Web (Spy): mouse over the element in the browser and click.",
            "Neue Objekte markieren Sie mit 🎯 Web (Spy): Maus über das Element im Browser und klicken."), 4)
    m.point(lambda: find_text(app.root, "⏺ Inregistreaza Web"), click=False)
    m.say(L("Sau ⏺ Inregistreaza Web: fiecare click / text din browser devine un pas.",
            "Or ⏺ Record Web: every click / text in the browser becomes a step.",
            "Oder ⏺ Web aufnehmen: jeder Klick / Text im Browser wird ein Schritt."), 4)
    m.point(lambda: find_text(app.root, "▶ Ruleaza"))
    m.do(lambda: st().run(), 500)
    m.until(lambda: not st().busy, 90).do(lambda: None, 800).snap()
    m.say(L("Rulare: in Log vezi fiecare pas, cu rezultatul. Valoarea citita e verificata automat.",
            "Run: the Log shows every step with its result. The value read is checked automatically.",
            "Ausführung: Das Log zeigt jeden Schritt mit Ergebnis. Der gelesene Wert wird automatisch geprüft."), 5)
    return m


def excel_movie():
    m = Movie("03_studio_excel", "Studio: Excel")
    m.do(lambda: app._set_mode("studio"), 1200).do(lambda: open_example("03_Web_Excel_Wikipedia.rpr.json"), 1200)
    fe = lambda: first_iid(lambda n: type(n).__name__ == "ForEachRowNode")
    m.do(lambda: (st().tree.selection_set(fe()), st().tree.focus(fe())), 900).snap()
    m.say(L("Excel: blocul „Pentru fiecare rand Excel” repeta pasii din el pentru fiecare rand.",
            "Excel: the \"For each Excel row\" block repeats its steps for every row.",
            "Excel: Der Block „Für jede Excel-Zeile“ wiederholt seine Schritte für jede Zeile."), 4.5)
    m.point_xy(lambda: tree_row(st().tree, fe())(), click=False)
    m.say(L("In dreapta: fisierul, foaia, coloana cheie si coloana de status (OK / eroare).",
            "On the right: the file, the sheet, the key column and the status column (OK / error).",
            "Rechts: Datei, Blatt, Schlüsselspalte und Statusspalte (OK / Fehler)."), 4.5)
    wr = lambda: first_iid(lambda n: type(n).__name__ == "WriteExcelNode")
    m.point_xy(lambda: tree_row(st().tree, wr())())
    m.do(lambda: (st().tree.selection_set(wr()), st().tree.focus(wr())), 900).snap()
    m.say(L("In bucla folosesti {Rand.Coloana}; „Scrie in Excel” pune rezultatul in randul curent.",
            "Inside the loop you use {Rand.Column}; \"Write to Excel\" puts the result into the current row.",
            "In der Schleife verwenden Sie {Rand.Spalte}; „In Excel schreiben“ schreibt ins aktuelle Feld."), 5)
    m.point(lambda: find_text(app.root, "▶ Ruleaza"))
    m.do(lambda: st().run(), 500)
    m.until(lambda: not st().busy, 150).do(lambda: None, 800).snap()
    m.say(L("Dupa rulare: randurile sunt marcate OK (verde) sau cu eroarea (rosu) direct in fisier.",
            "After the run: the rows are marked OK (green) or with the error (red) directly in the file.",
            "Nach der Ausführung: Zeilen werden direkt in der Datei als OK (grün) oder Fehler (rot) markiert."), 5)
    return m


def desktop_movie():
    m = Movie("04_studio_desktop", "Studio: Desktop")
    m.do(lambda: app._set_mode("studio"), 1200).do(lambda: open_example("05_Desktop_Notepad.rpr.json"), 1200).snap()
    m.say(L("Desktop: Studio lucreaza si cu aplicatii Windows (aici Notepad).",
            "Desktop: Studio also works with Windows applications (here Notepad).",
            "Desktop: Studio arbeitet auch mit Windows-Anwendungen (hier Editor)."), 4)
    la = lambda: first_iid(lambda n: getattr(n, "action", "") == "LaunchApp")
    m.point_xy(lambda: tree_row(st().tree, la())())
    m.do(lambda: (st().tree.selection_set(la()), st().tree.focus(la())), 900).snap()
    m.say(L("„Porneste aplicatie” si „Ataseaza fereastra” (proces:notepad.exe) aleg aplicatia.",
            "\"Start application\" and \"Attach window\" (proces:notepad.exe) select the application.",
            "„Anwendung starten“ und „Fenster verbinden“ (proces:notepad.exe) wählen die Anwendung."), 4.5)
    m.point(lambda: find_text(app.root, "🎯 Desktop"), click=False)
    m.say(L("🎯 Desktop: mouse-ul peste element (contur verde) si F2. Esc anuleaza.",
            "🎯 Desktop: mouse over the element (green outline) and F2. Esc cancels.",
            "🎯 Desktop: Maus über das Element (grüner Rahmen) und F2. Esc bricht ab."), 4)
    m.say(L("Inainte de fiecare click, fereastra aplicatiei e adusa in fata, iar elementul e derulat in zona vizibila.",
            "Before every click the application window is brought to the front and the element scrolled into view.",
            "Vor jedem Klick wird das Anwendungsfenster nach vorne geholt und das Element sichtbar gescrollt."), 4.5)
    m.point(lambda: find_text(app.root, "▶ Ruleaza"))
    m.do(lambda: st().run(), 500)
    m.until(lambda: not st().busy, 60).do(lambda: None, 600).snap()
    m.do(lambda: subprocess.run(["taskkill", "/IM", "notepad.exe", "/F"], capture_output=True), 300)
    m.say(L("Rutina a pornit Notepad si a scris trei randuri intr-o bucla. Detaliile sunt in Log.",
            "The routine started Notepad and typed three lines in a loop. Details are in the Log.",
            "Die Routine startete den Editor und schrieb drei Zeilen in einer Schleife. Details im Log."), 4.5)
    return m


def sap_movie():
    m = Movie("05_studio_sap", "Studio: SAP")
    m.do(lambda: app._set_mode("studio"), 1200).do(lambda: open_example("04_SAP_VA03_sablon.rpr.json"), 1200).snap()
    m.say(L("SAP GUI: activeaza scripting-ul (Options → Accessibility & Scripting) si autentifica-te in SAP Logon.",
            "SAP GUI: enable scripting (Options → Accessibility & Scripting) and log in through SAP Logon.",
            "SAP GUI: Scripting aktivieren (Optionen → Barrierefreiheit und Scripting) und in SAP Logon anmelden."), 5)
    con = lambda: first_iid(lambda n: getattr(n, "action", "") == "SapConnect")
    m.point_xy(lambda: tree_row(st().tree, con())())
    m.do(lambda: (st().tree.selection_set(con()), st().tree.focus(con())), 900).snap()
    m.say(L("Primul pas: SAP conecteaza (gol = prima sesiune). Apoi tranzactia, ex. /nVA03.",
            "First step: SAP connect (empty = first session). Then the transaction, e.g. /nVA03.",
            "Erster Schritt: SAP verbinden (leer = erste Sitzung). Dann die Transaktion, z. B. /nVA03."), 4.5)
    m.point(lambda: find_text(app.root, "🎯 SAP"), click=False)
    m.say(L("🎯 SAP: mouse-ul peste camp (contur rosu) si F2. Obiectul primeste Id-ul SAP (wnd[0]/usr/...).",
            "🎯 SAP: mouse over the field (red outline) and F2. The object gets the SAP Id (wnd[0]/usr/...).",
            "🎯 SAP: Maus über das Feld (roter Rahmen) und F2. Das Objekt erhält die SAP-Id (wnd[0]/usr/...)."), 4.5)
    m.say(L("Bara de stare SAP (S: succes, E: eroare) si „Valoarea asteptata” opresc rutina la erori.",
            "The SAP status bar (S: success, E: error) and the \"Expected value\" stop the routine on errors.",
            "SAP-Statusleiste (S: Erfolg, E: Fehler) und „Erwarteter Wert“ stoppen die Routine bei Fehlern."), 4.5)
    return m


def library_movie():
    m = Movie("06_biblioteca", "Biblioteca")
    m.do(lambda: app._set_mode("studio"), 1200).do(lambda: open_example("02_Web_Login_demo.rpr.json"), 800)

    def lib_tab():
        from tkinter import ttk
        stack = [st()]
        while stack:
            w = stack.pop()
            if isinstance(w, ttk.Notebook):
                for t in w.tabs():
                    if "Biblioteca" in w.tab(t, "text"):
                        w.select(t)
                        return
            stack.extend(w.winfo_children())
    m.do(lib_tab, 900).snap()
    m.say(L("📚 Biblioteca: toate obiectele, comune tuturor rutinelor: Site → Pagina → Container → obiect.",
            "📚 Library: all objects, shared by all routines: Site → Page → Container → object.",
            "📚 Bibliothek: alle Objekte, gemeinsam für alle Routinen: Website → Seite → Container → Objekt."), 4.5)
    m.say(L("Site-ul si pagina se completeaza singure din link-ul unde ai capturat obiectul.",
            "Site and page are filled in automatically from the link where you captured the object.",
            "Website und Seite werden automatisch aus dem Link ausgefüllt, auf dem das Objekt erfasst wurde."), 4)
    m.point(lambda: find_text(st(), "Test"), click=False)
    m.say(L("Test: vezi cate elemente gaseste fiecare locator (1 = bun) si obiectul e marcat pe ecran.",
            "Test: see how many elements each locator finds (1 = good); the object is highlighted on screen.",
            "Test: Wie viele Elemente findet jeder Locator (1 = gut); das Objekt wird markiert."), 4.5)
    m.point(lambda: find_text(st(), "🌐 Site-uri"), click=False)
    m.say(L("🌐 Site-uri: test + productie (sau alt client) = acelasi site; obiectele merg pe toate link-urile.",
            "🌐 Sites: test + production (or another customer) = the same site; objects work on all links.",
            "🌐 Websites: Test + Produktion (oder anderer Kunde) = dieselbe Website; Objekte gelten für alle Links."), 4.5)
    m.say(L("Containere (sectiune, tabel, lista): acelasi buton din doua sectiuni nu mai e confundat.",
            "Containers (section, table, list): the same button in two sections is no longer confused.",
            "Container (Abschnitt, Tabelle, Liste): Dieselbe Schaltfläche in zwei Abschnitten wird nicht verwechselt."), 4.5)
    return m


def schedule_movie():
    m = Movie("07_programare", "Programare")
    m.do(lambda: app._set_mode("studio"), 1200).do(lambda: open_example("01_Invatare_variabile_bucle_conditii.rpr.json"), 1000)
    m.point(lambda: find_text(app.root, "🕒 Programeaza"))
    holder = {}

    def open_dlg():
        d = studio_ui.ScheduleDialog(st(), st().routine_path, st().routine.name)
        d.geometry(f"780x660+{root.winfo_rootx() + 250}+{root.winfo_rooty() + 70}")
        d.attributes("-topmost", True)
        d.kind.current(2)
        d._sync()
        holder["d"] = d
    m.do(open_dlg, 4000).snap()
    m.say(L("🕒 Programeaza: zilnic, zile lucratoare, anumite zile, o data, la N minute sau la logare.",
            "🕒 Schedule: daily, working days, certain days, once, every N minutes or at logon.",
            "🕒 Planen: täglich, Werktage, bestimmte Tage, einmalig, alle N Minuten oder bei Anmeldung."), 4.5)
    m.say(L("Se creeaza in Windows Task Scheduler, fara drepturi de administrator. Mai jos: lista si istoricul.",
            "It is created in Windows Task Scheduler without administrator rights. Below: the list and history.",
            "Wird in der Windows-Aufgabenplanung ohne Administratorrechte angelegt. Unten: Liste und Verlauf."), 4.5)
    m.say(L("La ora stabilita rutina ruleaza singura; la final apare un mesaj verde / rosu in coltul ecranului.",
            "At the set time the routine runs on its own; at the end a green / red message appears in the corner.",
            "Zur festgelegten Zeit läuft die Routine selbst; am Ende erscheint eine grüne / rote Meldung."), 4.5)
    m.do(lambda: holder.get("d") and holder["d"].destroy(), 300)
    return m


def video_movie():
    m = Movie("08_video", "Video")
    m.do(lambda: app._set_mode("recorder"), 800).snap()
    m.point(lambda: app._btn_video)
    m.say(L("🎥 porneste o inregistrare a ecranului oricand, fara rutina. Apasa din nou ca sa opresti.",
            "🎥 starts a screen recording at any time, without a routine. Press again to stop.",
            "🎥 startet jederzeit eine Bildschirmaufnahme, ohne Routine. Erneut drücken zum Stoppen."), 4.5)
    m.say(L("Setari → Video: film automat la fiecare rulare (si cate unul pe rand Excel), folderul, calitatea.",
            "Settings → Video: automatic film on every run (and one per Excel row), the folder, the quality.",
            "Einstellungen → Video: automatischer Film bei jeder Ausführung (auch pro Excel-Zeile), Ordner, Qualität."), 5)
    holder = {}

    def make_and_open():
        rec = sr.ScreenRecorder(sr.VideoSettings(folder=os.path.join(TMP, "filme"), fps=4))
        p = rec.start("Demo")
        time.sleep(2.0)
        rec.stop()
        v = sr.VideoFile(p)
        v.edits["captions"].append({"t0": 0.2, "t1": 2.0, "text": "Text pe film", "pos": "bottom"})
        v.save_edits()
        v.close()
        from video_ui import VideoEditor
        ed = VideoEditor(root, mod.C, p)
        ed.geometry(f"1180x740+{root.winfo_rootx() + 50}+{root.winfo_rooty() + 30}")
        ed.attributes("-topmost", True)
        holder["ed"] = ed
    m.do(make_and_open, 2500).snap()
    m.say(L("La oprire se deschide editorul: capitole (pasi, randuri Excel), taiere, texte, zone ascunse.",
            "When it stops, the editor opens: chapters (steps, Excel rows), cutting, captions, hidden areas.",
            "Beim Stoppen öffnet sich der Editor: Kapitel (Schritte, Excel-Zeilen), Schneiden, Texte, verdeckte Bereiche."), 5)
    m.say(L("Pauzele lungi se scurteaza automat. Export: GIF (mereu) sau MP4. Filmul original ramane neschimbat.",
            "Long pauses are shortened automatically. Export: GIF (always) or MP4. The original stays unchanged.",
            "Lange Pausen werden automatisch gekürzt. Export: GIF (immer) oder MP4. Das Original bleibt erhalten."), 5)
    m.do(lambda: holder.get("ed") and holder["ed"]._close(), 300)
    return m


ALL = [recorder_movie, web_movie, excel_movie, desktop_movie, sap_movie, library_movie, schedule_movie, video_movie]


def run_all():
    os.makedirs(OUT_DIR, exist_ok=True)
    queue = [f() for f in ALL]
    queue = [m for m in queue if not ONLY or m.code[:2] in ONLY]

    def next_movie(i=0):
        if i >= len(queue):
            st().dirty = False
            app._quit_app()
            return
        m = queue[i]
        print("film", m.code)
        acts = list(m.actions)

        def step(j=0):
            if j >= len(acts):
                m.save()
                root.after(500, lambda: next_movie(i + 1))
                return
            kind, fn, arg = acts[j]
            if kind == "do":
                try:
                    fn()
                except Exception as ex:  # noqa: BLE001
                    import traceback
                    traceback.print_exc()
                    print("eroare la", m.code, j, ex)
                root.after(arg, lambda: step(j + 1))
            else:
                deadline = time.time() + arg

                def wait():
                    try:
                        ok = fn()
                    except Exception:
                        ok = True
                    if ok or time.time() > deadline:
                        step(j + 1)
                    else:
                        root.after(300, wait)
                wait()
        step()
    root.after(1500, next_movie)


run_all()
app.run()
