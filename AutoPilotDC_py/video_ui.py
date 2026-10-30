# -*- coding: utf-8 -*-
# ============================================================
# AutoPilot DC — 🎥 Video: bara de inregistrare, player / editor, controller pentru rulari
#
#   VideoController   — un singur ScreenRecorder pentru aplicatie: manual (🎥) sau la rularea rutinelor
#   RecordingBar      — fereastra mica ● REC 00:12  ⏸  ⏹  (nu apare in film)
#   VideoEditor       — redare + editare usoara (taiere, texte, zone ascunse, pauze scurtate) + export
# ============================================================

from __future__ import annotations

import ctypes
import datetime as _dt
import os
import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk
from typing import Callable, Dict, List, Optional

from PIL import ImageTk

import screen_recorder as sr

try:
    from i18n import tr, tr_template, LANG as _LANG
except ImportError:   # pragma: no cover
    def tr(t):
        return t
    tr_template = tr
    _LANG = "ro"


def _lang() -> str:
    try:
        import i18n
        return i18n.LANG
    except ImportError:
        return "ro"


def _fmt(t: float) -> str:
    t = max(0, int(t))
    return f"{t // 60:02d}:{t % 60:02d}"


def _exclude_from_capture(win: tk.Misc):
    """Fereastra nu apare in capturi / in film (Windows 10 2004+)."""
    try:
        win.update_idletasks()
        hwnd = ctypes.windll.user32.GetParent(win.winfo_id()) or win.winfo_id()
        ctypes.windll.user32.SetWindowDisplayAffinity(hwnd, 0x11)
    except Exception:
        pass


# ─────────────────────────────────────────────────────────────
# 1. Controller
# ─────────────────────────────────────────────────────────────
class VideoController:
    """Folosit de aplicatie: 🎥 manual, la rularea rutinelor (Studio / Recorder) si per rand Excel."""

    def __init__(self, root: tk.Misc, C: Dict[str, str], on_status: Callable[[str], None] = lambda s: None):
        self.root, self.C, self.on_status = root, C, on_status
        self.rec: Optional[sr.ScreenRecorder] = None
        self.bar: Optional[RecordingBar] = None
        self.mode = ""            # "manual" / "run"
        self._run_name = ""
        self._run_files: List[str] = []

    @property
    def settings(self) -> sr.VideoSettings:
        return sr.VideoSettings.load()

    @property
    def active(self) -> bool:
        return self.rec is not None and self.rec.active

    # ── manual ──
    def toggle_manual(self):
        if self.active:
            self.stop()
        else:
            self.start_manual()

    def start_manual(self, title: str = ""):
        if self.active or getattr(self, "_picker", None) is not None:
            return
        s = self.settings
        if s.area == "window":   # implicit: doar fereastra aleasa cu un click
            self._picker = WindowPicker(self.root, self.C, lambda h: self._picked(h, title))
            return
        self._begin(title, 0)

    def _picked(self, hwnd: int, title: str):
        self._picker = None
        if hwnd:
            self._begin(title or sr.window_title(hwnd) or tr("Inregistrare"), hwnd)
        else:
            self.on_status(tr("🎥 Inregistrare anulata."))

    def _begin(self, title: str, hwnd: int):
        self.mode = "manual"
        self.rec = sr.ScreenRecorder(self.settings)
        path = self.rec.start(title or tr("Inregistrare"), hwnd=hwnd)
        self._show_bar()
        self.on_status(tr("🎥 Inregistrez ecranul — oprire din bara ● REC sau din nou 🎥."))
        return path

    def _app_hwnd(self) -> int:
        try:
            return int(self.root.wm_frame(), 16)
        except Exception:
            return 0

    # ── rulari ──
    def run_started(self, routine_name: str, force: bool = False, folder: str = "") -> bool:
        """Apelat la pornirea unei rutine. Porneste filmul daca e activ in Setari (si nu inregistram deja).
        force=True: pregatirile cu "film pentru fiecare rutina" filmeaza oricum."""
        s = self.settings
        if (not s.record_on_run and not force) or self.active:
            return False
        self.mode = "run"
        self._run_name = routine_name
        self._run_files = []
        self._run_t0 = time.monotonic()
        self._last_row = ""
        self.rec = sr.ScreenRecorder(s)
        intro = self._intro()
        if s.area == "window":   # doar fereastra in care lucreaza rutina (fara AutoPilot si alte aplicatii)
            self.rec.ignore_hwnds = {self._app_hwnd()}
            self.rec.start(routine_name, folder=folder, follow=True, intro=intro)
        else:
            self.rec.start(routine_name, folder=folder, intro=intro)
        self._show_bar()
        return True

    @staticmethod
    def _intro(extra: str = "") -> List[str]:
        """Randurile introducerii: ce se ruleaza si cand."""
        now = _dt.datetime.now().strftime("%d.%m.%Y  %H:%M:%S")
        lines = [tr("▶ Rulare automata"), f"{tr('Inceput')}: {now}"]
        return lines + ([extra] if extra else [])

    def _outro(self, result=None, extra: str = "") -> List[str]:
        """Randurile iesirii: rezultatul rularii, durata, pasii, randurile Excel."""
        lines = []
        if result is None:
            lines.append(tr("■ Sfarsitul filmului"))
        elif getattr(result, "cancelled", False):
            lines.append(tr("⛔ Rulare oprita"))
        elif getattr(result, "success", False):
            lines.append(tr("✅ Rutina s-a terminat cu succes"))
        else:
            msg = str(getattr(result, "message", "") or "")[:120]
            lines.append(tr("❌ Rutina s-a oprit cu eroare") + (f": {msg}" if msg else ""))
        if extra:
            lines.append(extra)
        secs = time.monotonic() - getattr(self, "_run_t0", time.monotonic())
        lines.append(f"{tr('Durata')}: {_fmt(secs)}   ·   {tr('Sfarsit')}: {_dt.datetime.now().strftime('%H:%M:%S')}")
        if result is not None:
            info = tr_template("{0} pasi, {1} erori").format(getattr(result, "steps_executed", 0),
                                                            getattr(result, "errors", 0))
            rows = getattr(result, "rows_ok", 0) + getattr(result, "rows_failed", 0)
            if rows:
                info += "   ·   " + tr_template("Randuri Excel: {0} OK, {1} cu eroare").format(
                    result.rows_ok, result.rows_failed)
            lines.append(info)
        return lines

    def settle(self):
        """Apelat pe firul rularii, dupa ultimul pas: filmul mai merge putin, ca sa prinda rezultatul ultimului pas."""
        if self.mode == "run" and self.active:
            tail = self.settings.tail_s
            if tail > 0:
                time.sleep(tail)

    def marker(self, text: str):
        if self.active:
            self.rec.marker(text)

    def row_started(self, row: int, sheet: str = ""):
        if not self.active:
            return
        if self.mode == "run" and self.settings.per_row:
            label = f"{tr('Rand')} {row}" + (f" ({sheet})" if sheet else "")
            last = getattr(self, "_last_row", "")
            old = self.rec.split(f"{self._run_name}_rand{row}", outro=self._outro(None, last),
                                 intro=self._intro(label))
            if old:
                self._run_files.append(old)
        self.rec.marker(f"{tr('Rand')} {row}")

    def row_finished(self, row: int, status: str):
        self._last_row = f"{tr('Rand')} {row}: {status[:60]}"
        self.marker(self._last_row)

    def run_finished(self, result=None) -> str:
        """Opreste filmul rularii (cu iesirea: rezultat, durata); intoarce primul fisier (la film pe rand: primul rand)."""
        if self.mode == "run" and self.active:
            path = self.stop(open_editor=False, outro=self._outro(result))
            files = self._run_files + ([path] if path else [])
            if files:
                self.on_status(tr("🎥 Filmul rularii a fost salvat: ") + os.path.basename(files[-1]) +
                               (f" (+{len(files) - 1})" if len(files) > 1 else ""))
                return files[0]
        return ""

    def stop(self, open_editor: bool = True, outro: Optional[List[str]] = None) -> str:
        if self.rec is None:
            return ""
        path = self.rec.stop(outro)
        self.rec = None
        if self.bar is not None:
            self.bar.destroy()
            self.bar = None
        manual = self.mode == "manual"
        self.mode = ""
        if path and manual and open_editor:
            self.on_status(tr("🎥 Film salvat: ") + path)
            self.root.after(200, lambda: VideoEditor(self.root, self.C, path))
        return path

    def _show_bar(self):
        if self.bar is None:
            self.bar = RecordingBar(self.root, self.C, self)

    def open_file(self):
        path = filedialog.askopenfilename(title=tr("Deschide un film"), initialdir=self.settings.folder,
                                          filetypes=[(tr("Filme AutoPilot"), "*" + sr.EXT), (tr("Toate fisierele"), "*.*")])
        if path:
            open_video(self.root, self.C, path, on_status=self.on_status)


# ─────────────────────────────────────────────────────────────
# 1b. Alegerea ferestrei de inregistrat (click pe ea)
# ─────────────────────────────────────────────────────────────
class WindowPicker(tk.Toplevel):
    """Banda sus: "Click pe fereastra pe care vrei s-o inregistrezi". Conturul arata fereastra de sub mouse."""

    def __init__(self, master, C, done: Callable[[int], None]):
        super().__init__(master)
        self.done = done
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.configure(bg=C["primary"])
        tk.Label(self, text=tr("🎥 Click pe fereastra pe care vrei s-o inregistrezi (doar ea apare in film).  Esc = anuleaza"),
                 bg=C["primary"], fg="white", font=("Segoe UI", 10, "bold"), padx=12, pady=6).pack(side="left")
        tk.Button(self, text=tr("Anuleaza"), command=lambda: self._finish(0), bg="white", fg=C["primary"], relief="flat",
                  font=("Segoe UI", 10, "bold")).pack(side="left", padx=8, pady=4)
        self.update_idletasks()
        self.geometry(f"+{(self.winfo_screenwidth() - self.winfo_reqwidth()) // 2}+8")
        _exclude_from_capture(self)
        self._own = {int(self.wm_frame(), 16), int(master.winfo_toplevel().wm_frame(), 16)}
        from rpr.drivers.winutil import Highlighter
        self._hl = Highlighter((0, 215, 160))
        self._was_down = True   # ignoram click-ul care a pornit alegerea
        self.after(100, self._poll)

    def _poll(self):
        import ctypes
        u = ctypes.windll.user32
        down = bool(u.GetAsyncKeyState(0x01) & 0x8000)
        if u.GetAsyncKeyState(0x1B) & 0x8000:
            return self._finish(0)
        x, y = sr._cursor()
        h = sr.root_window_at(x, y)
        if h and h not in self._own:
            r = sr.window_rect(h)
            if r:
                self._hl.show(*r)
        else:
            self._hl.hide()
        if down and not self._was_down and h and h not in self._own:
            return self._finish(h)
        self._was_down = down
        self.after(60, self._poll)

    def _finish(self, hwnd: int):
        try:
            self._hl.hide()
        except Exception:
            pass
        self.destroy()
        self.done(hwnd)


# ─────────────────────────────────────────────────────────────
# 2. Bara de inregistrare
# ─────────────────────────────────────────────────────────────
class RecordingBar(tk.Toplevel):
    def __init__(self, master, C, ctl: VideoController):
        super().__init__(master)
        self.ctl, self.C = ctl, C
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.configure(bg="#2A0F14")
        self._dot = tk.Label(self, text="●", fg="#FF3B3B", bg="#2A0F14", font=("Segoe UI", 12, "bold"))
        self._dot.pack(side="left", padx=(10, 2), pady=4)
        self._time = tk.Label(self, text="REC 00:00", fg="white", bg="#2A0F14", font=("Consolas", 11, "bold"))
        self._time.pack(side="left", padx=(0, 8))
        self._pause = tk.Button(self, text="⏸", command=self._toggle_pause, relief="flat", bg="#47202A", fg="white",
                                font=("Segoe UI", 10, "bold"), padx=8, cursor="hand2")
        self._pause.pack(side="left", padx=2, pady=4)
        tk.Button(self, text="⏹ " + tr("Stop"), command=lambda: ctl.stop(), relief="flat", bg="#C0392B", fg="white",
                  font=("Segoe UI", 10, "bold"), padx=8, cursor="hand2").pack(side="left", padx=(2, 8), pady=4)
        self.update_idletasks()
        self.geometry(f"+{self.winfo_screenwidth() // 2 - self.winfo_reqwidth() // 2}+4")
        _exclude_from_capture(self)
        self.bind("<ButtonPress-1>", self._drag_start)
        self.bind("<B1-Motion>", self._drag)
        self._blink = True
        self._tick()

    def _toggle_pause(self):
        rec = self.ctl.rec
        if rec is None:
            return
        rec.pause(not rec.paused)
        self._pause.configure(text="▶" if rec.paused else "⏸")

    def _tick(self):
        rec = self.ctl.rec
        if rec is None or not self.winfo_exists():
            return
        self._blink = not self._blink
        self._dot.configure(fg="#FF3B3B" if (self._blink or rec.paused) else "#2A0F14")
        self._time.configure(text=("II " if rec.paused else "REC ") + _fmt(rec.elapsed()))
        self.after(500, self._tick)

    def _drag_start(self, e):
        self._dx, self._dy = e.x, e.y

    def _drag(self, e):
        self.geometry(f"+{self.winfo_x() + e.x - self._dx}+{self.winfo_y() + e.y - self._dy}")


# ─────────────────────────────────────────────────────────────
# 3. Player / editor
# ─────────────────────────────────────────────────────────────
class VideoEditor(tk.Toplevel):
    """Redare + editare usoara. readonly=True: doar player (filmele din 📖 Instructiuni)."""

    def __init__(self, master, C: Dict[str, str], path: str, readonly: bool = False, lang: str = ""):
        super().__init__(master)
        self.C, self.readonly = C, readonly
        self.lang = lang or _lang()
        try:
            self.v = sr.VideoFile(path)
        except Exception as ex:  # noqa: BLE001
            self.destroy()
            messagebox.showerror(tr("Video"), tr("Filmul nu poate fi deschis:") + f"\n{ex}", parent=master)
            return
        self.title(("🎬 " if readonly else "🎥 ") + self.v.m.get("title", os.path.basename(path)))
        self.configure(bg=C["bg_main"])
        import ui_theme
        ui_theme.fit_window(self, 1180, 760)   # v4.14: incape si pe un laptop 1366 x 768
        self.minsize(min(820, self.winfo_screenwidth() - 40), min(520, self.winfo_screenheight() - 90))
        self.playing = False
        self.out_t = 0.0
        self.speed = 1.0
        self.mark_a: Optional[float] = None
        self.mark_b: Optional[float] = None
        self._photo = None
        self._blur_mode = False
        self._rect_start = None
        self._dirty = False
        self.protocol("WM_DELETE_WINDOW", self._close)
        self._build()
        self.after(100, self._show)
        self.bind("<space>", lambda e: self.toggle_play())

    # ── interfata ──
    def _btn(self, parent, text, cmd, color=None, tip=""):
        C = self.C
        bg = color or C["bg_input"]
        b = tk.Button(parent, text=text, command=cmd, bg=bg, fg="white" if color else C["text"], relief="flat",
                      bd=0, font=("Segoe UI", 10, "bold"), padx=8, pady=3, cursor="hand2",
                      activebackground=C["primary"], activeforeground="white")
        return b

    def _build(self):
        C = self.C
        main = tk.Frame(self, bg=C["bg_main"])
        main.pack(fill="both", expand=True)
        left = tk.Frame(main, bg=C["bg_main"])
        left.pack(side="left", fill="both", expand=True, padx=(10, 6), pady=10)
        self.canvas = tk.Canvas(left, bg="#111118", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Configure>", lambda e: self._show())
        self.canvas.bind("<ButtonPress-1>", self._canvas_down)
        self.canvas.bind("<B1-Motion>", self._canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self._canvas_up)

        ctrl = tk.Frame(left, bg=C["bg_main"])
        ctrl.pack(fill="x", pady=(6, 0))
        self._play = self._btn(ctrl, "▶", self.toggle_play, C["primary"])
        self._play.pack(side="left")
        self.pos = tk.DoubleVar(value=0.0)
        self.scale = ttk.Scale(ctrl, from_=0, to=max(0.1, self.v.out_duration), variable=self.pos,
                               command=lambda v: self._seek(float(v)))
        self.scale.pack(side="left", fill="x", expand=True, padx=8)
        self.time_lbl = tk.Label(ctrl, text="00:00 / 00:00", bg=C["bg_main"], fg=C["text"], font=("Consolas", 10))
        self.time_lbl.pack(side="left")
        self.speed_cb = ttk.Combobox(ctrl, values=["0.5x", "1x", "2x", "4x"], width=5, state="readonly")
        self.speed_cb.set("1x")
        self.speed_cb.pack(side="left", padx=(8, 0))
        self.speed_cb.bind("<<ComboboxSelected>>", lambda e: setattr(self, "speed", float(self.speed_cb.get()[:-1])))
        if self.readonly:
            langs = tk.Frame(left, bg=C["bg_main"])
            langs.pack(anchor="e", pady=(4, 0))
            for code, name in (("ro", "RO"), ("en", "EN"), ("de", "DE")):
                self._btn(langs, name, lambda c=code: self._set_lang(c)).pack(side="left", padx=1)

        right = tk.Frame(main, bg=C["bg_card"], width=300)
        right.pack(side="right", fill="y", padx=(0, 10), pady=10)
        right.pack_propagate(False)
        tk.Label(right, text=tr("Capitole"), bg=C["bg_card"], fg=C["primary"], font=("Segoe UI", 10, "bold")).pack(
            anchor="w", padx=10, pady=(8, 2))
        self.chapters = tk.Listbox(right, height=6, bg=C["bg_input"], fg=C["text"], relief="flat",
                                   selectbackground=C["primary"], font=("Segoe UI", 10), exportselection=False)
        self.chapters.pack(fill="x", padx=10)
        self.chapters.bind("<<ListboxSelect>>", lambda e: self._goto_chapter())
        if not self.readonly:
            self._build_edit_panel(right)
        self._fill_chapters()

    def _build_edit_panel(self, right):
        C = self.C
        tk.Label(right, text=tr("Editare"), bg=C["bg_card"], fg=C["primary"], font=("Segoe UI", 10, "bold")).pack(
            anchor="w", padx=10, pady=(10, 2))
        self.ab_lbl = tk.Label(right, text=tr("Selectie A–B: —"), bg=C["bg_card"], fg=C["text_dim"], font=("Segoe UI", 10))
        self.ab_lbl.pack(anchor="w", padx=10)
        grid = tk.Frame(right, bg=C["bg_card"])
        grid.pack(fill="x", padx=10, pady=4)
        items = [("A ▸", self._set_a, tr("Inceputul selectiei = momentul curent")),
                 ("◂ B", self._set_b, tr("Sfarsitul selectiei = momentul curent")),
                 ("⟦ " + tr("Inceput"), self._trim_start, tr("Filmul incepe de aici")),
                 (tr("Sfarsit") + " ⟧", self._trim_end, tr("Filmul se termina aici")),
                 ("✂ " + tr("Taie A–B"), self._cut, tr("Scoate bucata dintre A si B")),
                 ("💬 " + tr("Text A–B"), self._caption, tr("Un text pe ecran intre A si B")),
                 ("▦ " + tr("Ascunde zona"), self._blur, tr("Trage un dreptunghi peste date personale (A–B)")),
                 ("↺ " + tr("Fara editari"), self._reset, tr("Sterge toate editarile (filmul original ramane)"))]
        for i, (text, cmd, _tip) in enumerate(items):
            self._btn(grid, text, cmd).grid(row=i // 2, column=i % 2, sticky="ew", padx=2, pady=2)
        grid.columnconfigure(0, weight=1)
        grid.columnconfigure(1, weight=1)
        idle = tk.Frame(right, bg=C["bg_card"])
        idle.pack(fill="x", padx=10, pady=(4, 0))
        tk.Label(idle, text=tr("Scurteaza pauzele mai lungi de (s, 0 = nu):"), bg=C["bg_card"], fg=C["text_dim"],
                 font=("Segoe UI", 10)).pack(side="left")
        self.idle = tk.StringVar(value=str(self.v.edits.get("idle") or 0))
        e = tk.Entry(idle, textvariable=self.idle, width=4, bg=C["bg_input"], fg=C["text"], relief="flat")
        e.pack(side="left", padx=4)
        e.bind("<Return>", lambda ev: self._apply_idle())
        e.bind("<FocusOut>", lambda ev: self._apply_idle())
        tk.Label(right, text=tr("Editari"), bg=C["bg_card"], fg=C["primary"], font=("Segoe UI", 10, "bold")).pack(
            anchor="w", padx=10, pady=(10, 2))
        self.edits_lb = tk.Listbox(right, height=5, bg=C["bg_input"], fg=C["text"], relief="flat",
                                   selectbackground=C["primary"], font=("Segoe UI", 10), exportselection=False)
        self.edits_lb.pack(fill="x", padx=10)
        self._btn(right, "🗑 " + tr("Sterge editarea"), self._del_edit).pack(anchor="w", padx=10, pady=4)
        tk.Label(right, text=tr("Salvare / export"), bg=C["bg_card"], fg=C["primary"], font=("Segoe UI", 10, "bold")).pack(
            anchor="w", padx=10, pady=(8, 2))
        ex = tk.Frame(right, bg=C["bg_card"])
        ex.pack(fill="x", padx=10)
        self._btn(ex, "💾 " + tr("Salveaza"), self._save, C["success"]).pack(side="left", padx=1)
        self._btn(ex, "GIF", lambda: self._export("gif")).pack(side="left", padx=1)
        self._btn(ex, "MP4", lambda: self._export("mp4")).pack(side="left", padx=1)
        self._btn(ex, "📂", lambda: os.startfile(os.path.dirname(self.v.path))).pack(side="left", padx=1)
        self.info = tk.Label(right, text="", bg=C["bg_card"], fg=C["text_dim"], font=("Segoe UI", 9), wraplength=270,
                             justify="left")
        self.info.pack(anchor="w", padx=10, pady=6)
        self._refresh_edits()

    # ── redare ──
    def _set_lang(self, code):
        self.lang = code
        self._show()

    def toggle_play(self):
        self.playing = not self.playing
        self._play.configure(text="⏸" if self.playing else "▶")
        if self.playing:
            if self.out_t >= self.v.out_duration - 0.05:
                self.out_t = 0.0
            self._last = time.monotonic()
            self._loop()

    def _loop(self):
        if not self.playing or not self.winfo_exists():
            return
        now = time.monotonic()
        self.out_t += (now - self._last) * self.speed
        self._last = now
        if self.out_t >= self.v.out_duration:
            self.out_t = self.v.out_duration
            self.playing = False
            self._play.configure(text="▶")
        self._show()
        if self.playing:
            self.after(max(40, int(1000 / max(4, self.v.m.get("fps", 4) * 2))), self._loop)

    def _seek(self, out_t: float):
        self.out_t = out_t
        if not self.playing:
            self._show()

    def _show(self):
        if not hasattr(self, "canvas") or not self.winfo_exists():
            return
        src = self.v.src_at(self.out_t)
        img = self.v.render(src, self.lang)
        cw, ch = max(10, self.canvas.winfo_width()), max(10, self.canvas.winfo_height())
        k = min(cw / img.width, ch / img.height)
        w, h = max(1, int(img.width * k)), max(1, int(img.height * k))
        self._k, self._ox, self._oy = k, (cw - w) // 2, (ch - h) // 2
        self._photo = ImageTk.PhotoImage(img.resize((w, h)))
        self.canvas.delete("all")
        self.canvas.create_image(self._ox, self._oy, image=self._photo, anchor="nw")
        self.pos.set(self.out_t)
        self.time_lbl.configure(text=f"{_fmt(self.out_t)} / {_fmt(self.v.out_duration)}")

    # ── capitole ──
    def _fill_chapters(self):
        self._chap = []
        self.chapters.delete(0, "end")
        items = [(t, txt) for t, txt in self.v.m.get("markers", [])]
        for c in self.v.edits.get("captions", []):
            items.append((c["t0"], "💬 " + sr.VideoFile.caption_text(c, self.lang)[:40]))
        for t, txt in sorted(items):
            self._chap.append(t)
            self.chapters.insert("end", f"{_fmt(self.v.out_at(t))}  {txt}")

    def _goto_chapter(self):
        sel = self.chapters.curselection()
        if sel:
            self._seek(self.v.out_at(self._chap[sel[0]]))

    # ── editari ──
    def _src_now(self) -> float:
        return self.v.src_at(self.out_t)

    def _changed(self):
        self._dirty = True
        self.v.rebuild()
        self.scale.configure(to=max(0.1, self.v.out_duration))
        self.out_t = min(self.out_t, self.v.out_duration)
        self._refresh_edits()
        self._fill_chapters()
        self._show()

    def _need_ab(self) -> bool:
        if self.mark_a is None or self.mark_b is None or self.mark_b <= self.mark_a:
            messagebox.showinfo(tr("Video"), tr("Alege intai selectia: A ▸ la inceput, ◂ B la sfarsit."), parent=self)
            return False
        return True

    def _set_a(self):
        self.mark_a = self._src_now()
        self._ab()

    def _set_b(self):
        self.mark_b = self._src_now()
        self._ab()

    def _ab(self):
        a = _fmt(self.mark_a) if self.mark_a is not None else "—"
        b = _fmt(self.mark_b) if self.mark_b is not None else "—"
        self.ab_lbl.configure(text=f"{tr('Selectie A–B:')} {a} – {b}")

    def _trim_start(self):
        e = self.v.edits
        end = e["trim"][1] if e.get("trim") else self.v.duration
        e["trim"] = [self._src_now(), end]
        self._changed()

    def _trim_end(self):
        e = self.v.edits
        start = e["trim"][0] if e.get("trim") else 0.0
        e["trim"] = [start, self._src_now()]
        self._changed()

    def _cut(self):
        if self._need_ab():
            self.v.edits["cuts"].append([self.mark_a, self.mark_b])
            self.mark_a = self.mark_b = None
            self._ab()
            self._changed()

    def _caption(self):
        if not self._need_ab():
            return
        text = simpledialog.askstring(tr("Text pe ecran"), tr("Textul afisat intre A si B:"), parent=self)
        if not text:
            return
        top = messagebox.askyesno(tr("Text pe ecran"), tr("Il afisez SUS? (Nu = jos)"), parent=self)
        self.v.edits["captions"].append({"t0": self.mark_a, "t1": self.mark_b, "text": text,
                                         "pos": "top" if top else "bottom"})
        self._changed()

    def _blur(self):
        if not self._need_ab():
            return
        self._blur_mode = True
        self.canvas.configure(cursor="crosshair")
        self.info.configure(text=tr("Trage cu mouse-ul un dreptunghi peste zona de ascuns."))

    def _canvas_down(self, e):
        if self._blur_mode:
            self._rect_start = (e.x, e.y)

    def _canvas_drag(self, e):
        if self._blur_mode and self._rect_start:
            self.canvas.delete("sel")
            x0, y0 = self._rect_start
            self.canvas.create_rectangle(x0, y0, e.x, e.y, outline="#FFC24B", width=2, tags="sel")
        elif not self._blur_mode:
            pass

    def _canvas_up(self, e):
        if not (self._blur_mode and self._rect_start):
            if not self._blur_mode:   # click pe imagine = play / pauza
                self.toggle_play()
            return
        x0, y0 = self._rect_start
        x1, y1 = e.x, e.y
        k, ox, oy = self._k, self._ox, self._oy
        rx, ry = (min(x0, x1) - ox) / k, (min(y0, y1) - oy) / k
        rw, rh = abs(x1 - x0) / k, abs(y1 - y0) / k
        self._blur_mode = False
        self._rect_start = None
        self.canvas.configure(cursor="")
        if rw > 4 and rh > 4:
            self.v.edits["blur"].append({"t0": self.mark_a, "t1": self.mark_b,
                                         "rect": [int(rx), int(ry), int(rw), int(rh)]})
            self.info.configure(text="")
            self._changed()

    def _apply_idle(self):
        try:
            val = max(0.0, float(self.idle.get().replace(",", ".")))
        except ValueError:
            return
        if val != float(self.v.edits.get("idle") or 0):
            self.v.edits["idle"] = val
            self._changed()

    def _reset(self):
        if messagebox.askyesno(tr("Video"), tr("Stergi toate editarile? Filmul original ramane neschimbat."), parent=self):
            self.v.edits.update({"trim": None, "cuts": [], "captions": [], "blur": [], "idle": 0.0})
            self.idle.set("0")
            self._changed()

    def _edit_rows(self):
        e = self.v.edits
        rows = []
        if e.get("trim"):
            rows.append((("trim", None), f"⟦⟧ {tr('Pastrat')} {_fmt(e['trim'][0])} – {_fmt(e['trim'][1])}"))
        for i, (a, b) in enumerate(e.get("cuts", [])):
            rows.append((("cuts", i), f"✂ {tr('Taiat')} {_fmt(a)} – {_fmt(b)}"))
        for i, c in enumerate(e.get("captions", [])):
            rows.append((("captions", i), f"💬 {_fmt(c['t0'])} – {_fmt(c['t1'])}: {sr.VideoFile.caption_text(c, self.lang)[:28]}"))
        for i, b in enumerate(e.get("blur", [])):
            rows.append((("blur", i), f"▦ {tr('Zona ascunsa')} {_fmt(b['t0'])} – {_fmt(b['t1'])}"))
        return rows

    def _refresh_edits(self):
        if not hasattr(self, "edits_lb"):
            return
        self._rows = self._edit_rows()
        self.edits_lb.delete(0, "end")
        for _, text in self._rows:
            self.edits_lb.insert("end", text)
        size = os.path.getsize(self.v.path) // 1024
        self.info.configure(text=f"{len(self.v.m['frames'])} {tr('cadre')} · {size} KB · "
                                 f"{tr('durata')} {_fmt(self.v.duration)} → {_fmt(self.v.out_duration)}")

    def _del_edit(self):
        sel = self.edits_lb.curselection()
        if not sel:
            return
        (kind, i), _ = self._rows[sel[0]]
        if kind == "trim":
            self.v.edits["trim"] = None
        else:
            self.v.edits[kind].pop(i)
        self._changed()

    def _save(self):
        try:
            self.v.save_edits()
            self._dirty = False
            self.info.configure(text=tr("Salvat: ") + os.path.basename(self.v.path))
        except Exception as ex:  # noqa: BLE001
            messagebox.showerror(tr("Video"), str(ex), parent=self)

    def _export(self, kind: str):
        if kind == "mp4" and not sr.mp4_available():
            messagebox.showinfo(tr("Video"), tr("Pentru MP4 lipseste pachetul opencv-python. Ruleaza in PowerShell:\n"
                                                "py -m pip install --user opencv-python\n\nGIF merge si fara el."),
                                parent=self)
            return
        base = os.path.splitext(self.v.path)[0]
        path = filedialog.asksaveasfilename(parent=self, title=tr("Export video"), defaultextension="." + kind,
                                            initialfile=os.path.basename(base) + "." + kind,
                                            initialdir=os.path.dirname(base),
                                            filetypes=[(kind.upper(), "*." + kind)])
        if not path:
            return
        self.info.configure(text=tr("Export in curs..."))
        lang = self.lang

        def work():
            try:
                fn = self.v.export_gif if kind == "gif" else self.v.export_mp4
                prog = lambda p: self.after(0, lambda: self.info.configure(text=f"{tr('Export in curs...')} {int(p * 100)}%"))
                fn(path, lang=lang, progress=prog)
                self.after(0, lambda: self.info.configure(text=tr("Exportat: ") + os.path.basename(path)))
            except Exception as ex:  # noqa: BLE001
                self.after(0, lambda e=str(ex): messagebox.showerror(tr("Video"), e, parent=self))
        threading.Thread(target=work, daemon=True).start()

    def _close(self):
        if self._dirty and not self.readonly:
            ans = messagebox.askyesnocancel(tr("Video"), tr("Salvezi editarile inainte de inchidere?"), parent=self)
            if ans is None:
                return
            if ans:
                self._save()
        self.playing = False
        self.v.close()
        self.destroy()


# ─────────────────────────────────────────────────────────────
# v4.14 — cu ce aplicatie se deschid filmele
#   "" (implicit)  = playerul / editorul AutoPilot
#   "system"       = aplicatia din Windows pentru MP4 (Filme si TV, VLC daca e implicit...)
#   cale .exe      = o aplicatie aleasa (de ex. VLC)
# Celelalte aplicatii nu cunosc .apvid: filmul se exporta o data in MP4 langa el
# (sau GIF daca lipseste opencv-python) si se refoloseste cat timp filmul nu se schimba.
# ─────────────────────────────────────────────────────────────
PLAYER_CHOICES = [(sr.PLAYER_BUILTIN, "Player AutoPilot (redare + editare)"),
                  (sr.PLAYER_SYSTEM, "Aplicatia implicita din Windows (MP4)"),
                  ("exe", "Alta aplicatie de pe laptop (ex. VLC)…")]


def player_label(player: str) -> str:
    p = (player or "").strip()
    if not p:
        return PLAYER_CHOICES[0][1]
    if p == sr.PLAYER_SYSTEM:
        return PLAYER_CHOICES[1][1]
    return os.path.basename(p)


def export_target(path: str) -> str:
    """Fisierul exportat refolosit (MP4 daca se poate, altfel GIF) langa film."""
    base = os.path.splitext(path)[0]
    return base + (".mp4" if sr.mp4_available() else ".gif")


def _export_fresh(path: str, target: str) -> bool:
    try:
        return os.path.getmtime(target) >= os.path.getmtime(path)
    except OSError:
        return False


def launch_external(player: str, file_path: str) -> None:
    import subprocess
    if player == sr.PLAYER_SYSTEM:
        if hasattr(os, "startfile"):
            os.startfile(file_path)  # noqa: S606 — fisier local, ales de utilizator
        else:
            subprocess.Popen(["xdg-open", file_path])
    else:
        subprocess.Popen([player, file_path])


def open_video(master, C: Dict[str, str], path: str, start_s: float = 0.0,
               on_status: Optional[Callable[[str], None]] = None, on_done: Optional[Callable[[], None]] = None,
               player: Optional[str] = None):
    """Deschide filmul cu aplicatia aleasa in setari (🎬, linkurile din Excel, dublu-click pe .apvid)."""
    player = (sr.VideoSettings.load().player if player is None else player).strip()
    status = on_status or (lambda m: None)
    if player and player != sr.PLAYER_SYSTEM and not os.path.isfile(player):
        messagebox.showwarning(tr("Video"), tr("Aplicatia aleasa pentru filme nu mai exista:") + f"\n{player}\n\n" +
                               tr("Filmul se deschide in playerul AutoPilot."), parent=master)
        player = ""
    if not player:
        ed = VideoEditor(master, C, path)
        if start_s > 0 and ed.winfo_exists():
            ed.after(300, lambda: ed._seek(ed.v.out_at(start_s)))
        if on_done:
            if ed.winfo_exists():
                ed.bind("<Destroy>", lambda e: master.after(50, on_done) if e.widget is ed else None)
            else:
                master.after(50, on_done)
        return ed
    target = export_target(path)
    if _export_fresh(path, target):
        launch_external(player, target)
        if on_done:
            master.after(50, on_done)
        return None
    # exportul dureaza cateva secunde: o fereastra mica arata progresul
    win = tk.Toplevel(master)
    win.title(tr("Video"))
    win.configure(bg=C.get("bg_main", "#1E1E2E"))
    win.resizable(False, False)
    try:
        win.attributes("-topmost", True)
    except tk.TclError:
        pass
    lbl = tk.Label(win, text=tr("Pregatesc filmul pentru aplicatia aleasa..."), bg=C.get("bg_main", "#1E1E2E"),
                   fg=C.get("text", "#FFFFFF"), font=("Segoe UI", 10), padx=18, pady=14)
    lbl.pack()
    state = {"p": 0.0, "done": False, "err": None}

    def work():
        try:
            v = sr.VideoFile(path)
            fn = v.export_mp4 if target.endswith(".mp4") else v.export_gif
            tmp = target + ".tmp" + os.path.splitext(target)[1]
            fn(tmp, lang=_lang(), progress=lambda p: state.__setitem__("p", p))
            v.close()
            os.replace(tmp, target)
        except Exception as ex:  # noqa: BLE001
            state["err"] = ex
        state["done"] = True

    def poll():
        if not state["done"]:
            try:
                lbl.configure(text=f"{tr('Pregatesc filmul pentru aplicatia aleasa...')} {int(state['p'] * 100)}%")
            except tk.TclError:
                return
            master.after(200, poll)
            return
        try:
            win.destroy()
        except tk.TclError:
            pass
        if state["err"] is not None:
            messagebox.showerror(tr("Video"), str(state["err"]), parent=master)
        else:
            try:
                launch_external(player, target)
                status(tr("🎬 Film deschis: ") + os.path.basename(target))
            except OSError as ex:
                messagebox.showerror(tr("Video"), str(ex), parent=master)
        if on_done:
            master.after(50, on_done)
    threading.Thread(target=work, daemon=True).start()
    master.after(200, poll)
    return None


def build_player_chooser(parent: tk.Frame, C: Dict[str, str], current: str) -> Callable[[], str]:
    """Lista "Deschide filmele cu"; returneaza functia care da valoarea aleasa."""
    bg = parent["bg"]
    state = {"exe": current if current and current != sr.PLAYER_SYSTEM else ""}
    labels = [l for _, l in PLAYER_CHOICES]
    row = tk.Frame(parent, bg=bg)
    row.pack(fill="x", padx=12, pady=(2, 2))
    cb = ttk.Combobox(row, values=[tr(l) for l in labels], state="readonly", width=40)
    cb.pack(side="left")
    exe_lbl = tk.Label(parent, text="", bg=bg, fg=C.get("text_dim", "#AAAACC"), font=("Segoe UI", 9), anchor="w",
                       justify="left")
    exe_lbl.pack(fill="x", padx=14)

    def show():
        if state["exe"] and cb.current() == 2:
            exe_lbl.configure(text="→ " + state["exe"])
        else:
            exe_lbl.configure(text="")

    def pick_exe():
        p = filedialog.askopenfilename(parent=parent, title=tr("Alege aplicatia pentru filme"),
                                       filetypes=[(tr("Aplicatii"), "*.exe"), (tr("Toate fisierele"), "*.*")])
        if p:
            state["exe"] = os.path.normpath(p)
        elif not state["exe"]:
            cb.current(0)
        show()

    def on_sel(_e=None):
        if cb.current() == 2:
            pick_exe()
        show()
    cb.bind("<<ComboboxSelected>>", on_sel)
    if not current:
        cb.current(0)
    elif current == sr.PLAYER_SYSTEM:
        cb.current(1)
    else:
        cb.current(2)
    show()

    def value() -> str:
        i = cb.current()
        if i == 1:
            return sr.PLAYER_SYSTEM
        if i == 2 and state["exe"]:
            return state["exe"]
        return sr.PLAYER_BUILTIN
    return value


# ─────────────────────────────────────────────────────────────
# 4. Sectiunea din Setari
# ─────────────────────────────────────────────────────────────
def build_settings_section(parent: tk.Frame, C: Dict[str, str]) -> Callable[[], None]:
    """Construieste campurile pentru setarile video; returneaza functia care le salveaza."""
    s = sr.VideoSettings.load()
    bg = parent["bg"]
    vars_ = {}

    def row(label, widget):
        r = tk.Frame(parent, bg=bg)
        r.pack(fill="x", padx=12, pady=3)
        tk.Label(r, text=label, bg=bg, fg=C["text_dim"], font=("Segoe UI", 10), width=40, anchor="w").pack(side="left")
        widget(r)

    def entry(r, key, width=8):
        v = tk.StringVar(value=str(getattr(s, key)))
        vars_[key] = v
        tk.Entry(r, textvariable=v, width=width, bg=C["bg_input"], fg=C["text"], relief="flat",
                 insertbackground=C["text"], font=("Segoe UI", 10)).pack(side="left", ipady=2)

    def check(text, key):
        v = tk.BooleanVar(value=bool(getattr(s, key)))
        vars_[key] = v
        tk.Checkbutton(parent, text=text, variable=v, bg=bg, fg=C["text"], selectcolor=C["bg_input"],
                       activebackground=bg, font=("Segoe UI", 10)).pack(anchor="w", padx=12, pady=1)

    def folder_row(r):
        v = tk.StringVar(value=s.folder)
        vars_["folder"] = v
        tk.Entry(r, textvariable=v, width=48, bg=C["bg_input"], fg=C["text"], relief="flat",
                 insertbackground=C["text"], font=("Segoe UI", 10)).pack(side="left", ipady=2)

        def browse():
            d = filedialog.askdirectory(initialdir=v.get() or s.folder, title=tr("Folderul pentru filme"))
            if d:
                v.set(d)
        tk.Button(r, text="…", command=browse, relief="flat", bg=C["bg_input"], fg=C["text"], padx=6).pack(side="left", padx=4)
        tk.Button(r, text="📂", command=lambda: (os.makedirs(v.get(), exist_ok=True), os.startfile(v.get())),
                  relief="flat", bg=C["bg_input"], fg=C["text"], padx=6).pack(side="left")

    row(tr("Folderul pentru filme:"), folder_row)
    check(tr("Inregistreaza automat un film la fiecare rulare de rutina (Studio)"), "record_on_run")
    check(tr("   ... in bucla Excel: cate un film pentru fiecare rand"), "per_row")
    check(tr("   ... si la rularile programate"), "on_schedule")
    row(tr("Capturi pe secunda (1-10):"), lambda r: entry(r, "fps"))
    row(tr("Marime cadre (0.3-1.0 din ecran):"), lambda r: entry(r, "scale"))
    row(tr("Calitate imagine (20-95):"), lambda r: entry(r, "quality"))

    areas = [("window", tr("Doar fereastra (recomandat)")), ("primary", tr("Ecranul principal")),
             ("all", tr("Toate ecranele"))]

    def area_row(r):
        v = tk.StringVar(value=dict(areas).get(s.area, areas[0][1]))
        vars_["area"] = v
        ttk.Combobox(r, textvariable=v, values=[n for _, n in areas], state="readonly", width=26).pack(side="left")
    row(tr("Ce se inregistreaza:"), area_row)
    row(tr("Scurteaza automat pauzele mai lungi de (s):"), lambda r: entry(r, "idle_compress_s"))
    check(tr("Filmele rularilor: introducere (rutina, data) la inceput si iesire (rezultat, durata) la final"),
          "intro_outro")
    row(tr("Introducere / iesire (s):"), lambda r: (entry(r, "intro_s"), tk.Label(r, text=" / ", bg=bg, fg=C["text"]).pack(
        side="left"), entry(r, "outro_s")))
    row(tr("Dupa ultimul pas se mai filmeaza (s):"), lambda r: entry(r, "tail_s"))
    tk.Label(parent, text=tr("Deschide filmele cu:"), bg=bg, fg=C["text_dim"], font=("Segoe UI", 10),
             anchor="w").pack(fill="x", padx=12, pady=(6, 0))
    player_value = build_player_chooser(parent, C, s.player)
    tk.Label(parent, text=tr("Doar fereastra: la 🎥 alegi fereastra cu un click, iar la rulari se inregistreaza doar fereastra "
                             "in care lucreaza rutina — alte aplicatii, notificarile si bara de activitati nu apar in film."),
             bg=bg, fg=C["text_dim"], font=("Segoe UI", 10), wraplength=720, justify="left").pack(anchor="w", padx=12)
    tk.Label(parent, text=tr("Filmele se fac din capturi de ecran salvate doar cand ecranul se schimba (fisiere mici). "
                             "Butonul 🎥 din bara de sus porneste / opreste o inregistrare oricand, fara rutina; "
                             "la final se deschide editorul (taiere, texte, zone ascunse, export GIF / MP4)."),
             bg=bg, fg=C["text_dim"], font=("Segoe UI", 10), wraplength=720, justify="left").pack(anchor="w", padx=12, pady=(4, 8))

    def save():
        n = sr.VideoSettings.load()
        n.folder = vars_["folder"].get().strip() or n.folder
        for key in ("record_on_run", "per_row", "on_schedule", "intro_outro"):
            setattr(n, key, bool(vars_[key].get()))
        for key, cast in (("fps", int), ("scale", float), ("quality", int), ("idle_compress_s", float),
                          ("intro_s", float), ("outro_s", float), ("tail_s", float)):
            try:
                setattr(n, key, cast(str(vars_[key].get()).replace(",", ".")))
            except ValueError:
                pass
        n.area = next((k for k, name in areas if name == vars_["area"].get()), "window")
        n.player = player_value()
        n.save()
    return save


# ─────────────────────────────────────────────────────────────
# Player separat: dublu-click pe un .apvid (sau linkul din Excel / raport)
#   pythonw video_ui.py "film.apvid" [--t SECUNDE]
# Ruleaza in procesul lui, deci nu deranjeaza aplicatia deschisa.
# ─────────────────────────────────────────────────────────────
PROG_ID = "AutoPilotDC.Video"


def register_file_type() -> bool:
    """Asociaza .apvid cu acest player (doar pentru utilizatorul curent, fara administrator)."""
    if os.name != "nt":
        return False
    try:
        import sys
        import winreg
        exe = sys.executable
        if os.path.basename(exe).lower() == "python.exe":
            w = os.path.join(os.path.dirname(exe), "pythonw.exe")
            exe = w if os.path.isfile(w) else exe
        cmd = f'"{exe}" "{os.path.abspath(__file__)}" "%1"'
        base = r"Software\Classes"
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, base + "\\" + PROG_ID + r"\shell\open\command") as k:
                if winreg.QueryValueEx(k, "")[0] == cmd:
                    return True        # deja asociat cu aceasta instalare
        except OSError:
            pass
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, base + r"\.apvid") as k:
            winreg.SetValueEx(k, "", 0, winreg.REG_SZ, PROG_ID)
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, base + "\\" + PROG_ID) as k:
            winreg.SetValueEx(k, "", 0, winreg.REG_SZ, "Film AutoPilot DC")
        icon = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "autopilot.ico")
        if os.path.isfile(icon):
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, base + "\\" + PROG_ID + r"\DefaultIcon") as k:
                winreg.SetValueEx(k, "", 0, winreg.REG_SZ, icon)
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, base + "\\" + PROG_ID + r"\shell\open\command") as k:
            winreg.SetValueEx(k, "", 0, winreg.REG_SZ, cmd)
        try:   # Explorer afla imediat de asociere
            ctypes.windll.shell32.SHChangeNotify(0x08000000, 0, None, None)
        except Exception:
            pass
        return True
    except Exception:  # noqa: BLE001
        return False


_PLAYER_COLORS = {"bg_main": "#1E1E2E", "bg_panel": "#252535", "bg_card": "#2A2A3E", "bg_input": "#32324A",
                  "border": "#444466", "primary": "#009999", "accent": "#00B3B3", "text": "#E8E8F0",
                  "text_dim": "#A0A0B8", "text_muted": "#6C6C88", "success": "#2E9E5B", "warning": "#C98A00",
                  "danger": "#C0392B", "separator": "#444466"}


def open_player(path: str, start_s: float = 0.0) -> None:
    root = tk.Tk()
    root.withdraw()
    try:
        import i18n
        i18n.install()
    except Exception:  # noqa: BLE001
        pass
    from collections import defaultdict
    C = defaultdict(lambda: "#336699", _PLAYER_COLORS)
    # v4.14: aplicatia aleasa in setari (playerul AutoPilot sau alta, de ex. VLC)
    open_video(root, C, path, start_s, on_done=root.destroy)
    root.mainloop()


if __name__ == "__main__":
    import sys
    args = sys.argv[1:]
    t = 0.0
    if "--t" in args:
        i = args.index("--t")
        try:
            t = float(args[i + 1])
        except (IndexError, ValueError):
            pass
        del args[i:i + 2]
    if args:
        open_player(args[0], t)
