# -*- coding: utf-8 -*-
# ============================================================
# AutoPilot DC — 📖 Instructiuni (tab-ul de ajutor, in romana / engleza / germana)
#
# Continutul sta in docs/instructiuni/<limba>.md (un subset simplu de Markdown):
#   # Titlu   ## Capitol   - lista   1. pasi   > nota / exemplu   **ingrosat**   `cod`
# Stanga: capitolele (cu cautare); dreapta: textul formatat.
# ============================================================

from __future__ import annotations

import os
import re
import tkinter as tk
from tkinter import ttk
from typing import Dict, List, Tuple

try:
    import i18n
except ImportError:   # pragma: no cover
    i18n = None

DOCS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "docs", "instructiuni")
VIDEO_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "docs", "video")
# filmele scurte (docs/video/<cod>.apvid), generate cu tools/make_tutorials.py
VIDEOS = [("01_recorder", {"ro": "Recorder", "en": "Recorder", "de": "Recorder"}),
          ("02_studio_web", {"ro": "Studio: Web", "en": "Studio: Web", "de": "Studio: Web"}),
          ("03_studio_excel", {"ro": "Studio: Excel", "en": "Studio: Excel", "de": "Studio: Excel"}),
          ("04_studio_desktop", {"ro": "Studio: Desktop", "en": "Studio: Desktop", "de": "Studio: Desktop"}),
          ("05_studio_sap", {"ro": "Studio: SAP", "en": "Studio: SAP", "de": "Studio: SAP"}),
          ("06_biblioteca", {"ro": "Biblioteca", "en": "Library", "de": "Bibliothek"}),
          ("07_programare", {"ro": "Programare", "en": "Scheduling", "de": "Planung"}),
          ("08_video", {"ro": "Video", "en": "Video", "de": "Video"})]
_VIDEO_LABEL = {"ro": "🎬 Filme scurte:", "en": "🎬 Short videos:", "de": "🎬 Kurze Videos:"}
_VIDEO_LINK = {"ro": "Film", "en": "Video", "de": "Video"}
LANGS = [("ro", "Română"), ("en", "English"), ("de", "Deutsch")]
_INLINE = re.compile(r"(\*\*[^*]+\*\*|`[^`]+`)")


def load_doc(lang: str) -> str:
    for code in (lang, "ro"):
        try:
            with open(os.path.join(DOCS, code + ".md"), encoding="utf-8") as f:
                return f.read()
        except OSError:
            continue
    return "# Instructiuni\n\nFisierele docs/instructiuni/*.md lipsesc."


def chapters(text: str) -> List[Tuple[str, str]]:
    """[(titlu capitol, continut)] — capitolele incep cu "## "."""
    out: List[Tuple[str, str]] = []
    cur_title, cur = None, []
    for line in text.splitlines():
        if line.startswith("## "):
            if cur_title is not None:
                out.append((cur_title, "\n".join(cur)))
            cur_title, cur = line[3:].strip(), []
        elif cur_title is not None:
            cur.append(line)
    if cur_title is not None:
        out.append((cur_title, "\n".join(cur)))
    return out


class InstructionsPanel(tk.Frame):
    def __init__(self, master, C: Dict[str, str]):
        super().__init__(master, bg=C["bg_main"])
        self.C = C
        self.lang = i18n.LANG if i18n is not None else "ro"
        self._marks: Dict[str, str] = {}

        top = tk.Frame(self, bg=C["bg_main"])
        top.pack(fill="x", padx=10, pady=(8, 4))
        tk.Label(top, text="📖  Instructiuni", bg=C["bg_main"], fg=C["primary"],
                 font=("Segoe UI", 14, "bold")).pack(side="left")
        self._lang_btns = {}
        for code, name in reversed(LANGS):
            b = tk.Button(top, text=name, relief="flat", bd=0, font=("Segoe UI", 9, "bold"), padx=10, pady=3,
                          cursor="hand2", command=lambda c=code: self.set_language(c))
            b.pack(side="right", padx=1)
            self._lang_btns[code] = b
        self.search = tk.StringVar()
        e = tk.Entry(top, textvariable=self.search, width=28, bg=C["bg_input"], fg=C["text"],
                     insertbackground=C["text"], relief="flat", font=("Segoe UI", 10))
        e.pack(side="right", padx=(0, 12), ipady=3)
        tk.Label(top, text="🔍", bg=C["bg_main"], fg=C["text_dim"], font=("Segoe UI", 10)).pack(side="right")
        self.search.trace_add("write", lambda *a: self._apply_search())
        e.bind("<Return>", lambda ev: self._next_hit())

        # filmele scurte, cate unul pentru fiecare tip de rutina
        self.vbar = tk.Frame(self, bg=C["bg_main"])
        self.vbar.pack(fill="x", padx=10, pady=(0, 6))

        body = ttk.PanedWindow(self, orient="horizontal")
        body.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        left = tk.Frame(body, bg=C["bg_card"])
        right = tk.Frame(body, bg=C["bg_card"])
        body.add(left, weight=1)
        body.add(right, weight=4)
        self.after(150, lambda: body.sashpos(0, 340) if body.winfo_exists() else None)   # titlurile intregi

        self.toc = tk.Listbox(left, bg=C["bg_card"], fg=C["text"], selectbackground=C["primary"],
                              selectforeground="white", activestyle="none", relief="flat", bd=0,
                              highlightthickness=0, font=("Segoe UI", 10), exportselection=False)
        self.toc.pack(fill="both", expand=True, padx=6, pady=6)
        self.toc.bind("<<ListboxSelect>>", lambda e: self._goto_selected())

        self.text = tk.Text(right, wrap="word", bg=C["bg_card"], fg=C["text"], relief="flat", bd=0,
                            padx=18, pady=12, font=("Segoe UI", 10), spacing1=2, spacing3=2, cursor="arrow",
                            highlightthickness=0)
        sb = ttk.Scrollbar(right, orient="vertical", command=self.text.yview)
        self.text.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.text.pack(fill="both", expand=True)
        t = self.text
        t.tag_configure("h1", font=("Segoe UI", 16, "bold"), foreground=C["primary"], spacing3=8)
        t.tag_configure("h2", font=("Segoe UI", 13, "bold"), foreground=C["primary"], spacing1=14, spacing3=6)
        t.tag_configure("h3", font=("Segoe UI", 11, "bold"), foreground=C["accent"], spacing1=8)
        t.tag_configure("bold", font=("Segoe UI", 10, "bold"))
        t.tag_configure("code", font=("Consolas", 10), foreground=C["accent"], background=C["bg_input"])
        t.tag_configure("bullet", lmargin1=14, lmargin2=30)
        t.tag_configure("num", lmargin1=14, lmargin2=30)
        t.tag_configure("note", lmargin1=14, lmargin2=14, rmargin=14, background=C["bg_input"],
                        foreground=C["text"], spacing1=6, spacing3=6)
        t.tag_configure("hit", background="#FFC24B", foreground="#000000")
        t.tag_configure("video", foreground="white", background=C["primary"], font=("Segoe UI", 10, "bold"),
                        lmargin1=14, spacing1=4, spacing3=4)
        self._hits: List[str] = []
        self._hit_i = -1
        self.set_language(self.lang)

    # ── continut ──
    def set_language(self, lang: str):
        self.lang = lang
        C = self.C
        for code, b in self._lang_btns.items():
            on = code == lang
            b.configure(bg=C["primary"] if on else C["bg_input"], fg="white" if on else C["text_dim"],
                        activebackground=C["primary"], activeforeground="white")
        self._render(load_doc(lang))
        self._fill_videos()
        self._apply_search()

    def _fill_videos(self):
        C = self.C
        for w in self.vbar.winfo_children():
            w.destroy()
        tk.Label(self.vbar, text=_VIDEO_LABEL.get(self.lang, _VIDEO_LABEL["ro"]), bg=C["bg_main"], fg=C["primary"],
                 font=("Segoe UI", 10, "bold")).pack(side="left", padx=(0, 6))
        for code, names in VIDEOS:
            if not os.path.isfile(os.path.join(VIDEO_DIR, code + ".apvid")):
                continue
            tk.Button(self.vbar, text="▶ " + names.get(self.lang, names["ro"]), relief="flat", bd=0, cursor="hand2",
                      bg=C["bg_card"], fg=C["text"], activebackground=C["primary"], activeforeground="white",
                      font=("Segoe UI", 9, "bold"), padx=8, pady=2,
                      command=lambda c=code: self.play(c)).pack(side="left", padx=2)

    def play(self, code: str):
        path = os.path.join(VIDEO_DIR, code + ".apvid")
        if not os.path.isfile(path):
            return
        from video_ui import VideoEditor
        VideoEditor(self.winfo_toplevel(), self.C, path, readonly=True, lang=self.lang)

    def _inline(self, line: str, base_tags: Tuple[str, ...]):
        for part in _INLINE.split(line):
            if not part:
                continue
            if part.startswith("**") and part.endswith("**"):
                self.text.insert("end", part[2:-2], base_tags + ("bold",))
            elif part.startswith("`") and part.endswith("`"):
                self.text.insert("end", part[1:-1], base_tags + ("code",))
            else:
                self.text.insert("end", part, base_tags)

    def _render(self, md: str):
        t = self.text
        t.configure(state="normal")
        t.delete("1.0", "end")
        for m in list(self._marks.values()):
            t.mark_unset(m)
        self._marks.clear()
        self.toc.delete(0, "end")
        for raw in md.splitlines():
            line = raw.rstrip()
            if line.startswith("# "):
                t.insert("end", line[2:] + "\n", ("h1",))
            elif line.startswith("## "):
                title = line[3:].strip()
                mark = f"ch{len(self._marks)}"
                t.mark_set(mark, "end-1c")
                t.mark_gravity(mark, "left")
                self._marks[title] = mark
                self.toc.insert("end", title)
                t.insert("end", title + "\n", ("h2",))
            elif line.startswith("[video:") and line.endswith("]"):
                code = line[7:-1]
                name = dict(VIDEOS).get(code, {}).get(self.lang, code)
                tag = "vid_" + code
                t.tag_configure(tag)
                t.tag_bind(tag, "<Button-1>", lambda e, c=code: self.play(c))
                t.tag_bind(tag, "<Enter>", lambda e: t.configure(cursor="hand2"))
                t.tag_bind(tag, "<Leave>", lambda e: t.configure(cursor="arrow"))
                t.insert("end", f"  ▶  {_VIDEO_LINK.get(self.lang, 'Film')}: {name}  ", ("video", tag))
                t.insert("end", "\n")
            elif line.startswith("### "):
                t.insert("end", line[4:] + "\n", ("h3",))
            elif line.startswith("> "):
                self._inline(line[2:], ("note",))
                t.insert("end", "\n", ("note",))
            elif re.match(r"^\s*- ", line):
                t.insert("end", "•  ", ("bullet",))
                self._inline(re.sub(r"^\s*- ", "", line), ("bullet",))
                t.insert("end", "\n", ("bullet",))
            elif re.match(r"^\s*\d+\. ", line):
                num, rest = re.match(r"^\s*(\d+\.) (.*)$", line).groups()
                t.insert("end", num + "  ", ("num", "bold"))
                self._inline(rest, ("num",))
                t.insert("end", "\n", ("num",))
            elif not line:
                t.insert("end", "\n")
            else:
                self._inline(line, ())
                t.insert("end", "\n")
        t.configure(state="disabled")

    def _goto_selected(self):
        sel = self.toc.curselection()
        if not sel:
            return
        mark = self._marks.get(self.toc.get(sel[0]))
        if mark:
            self.text.see("end")      # apoi inapoi, ca titlul capitolului sa ajunga sus
            self.text.see(mark)
            self.text.yview(mark)

    # ── cautare ──
    def _apply_search(self):
        t = self.text
        t.tag_remove("hit", "1.0", "end")
        self._hits, self._hit_i = [], -1
        term = self.search.get().strip()
        titles = list(self._marks)
        if not term:
            self.toc.delete(0, "end")
            for title in titles:
                self.toc.insert("end", title)
            return
        start = "1.0"
        while True:
            pos = t.search(term, start, stopindex="end", nocase=True)
            if not pos:
                break
            end = f"{pos}+{len(term)}c"
            t.tag_add("hit", pos, end)
            self._hits.append(pos)
            start = end
        # capitolele care contin termenul
        doc = load_doc(self.lang)
        keep = [title for title, body in chapters(doc) if term.lower() in (title + "\n" + body).lower()]
        self.toc.delete(0, "end")
        for title in keep:
            self.toc.insert("end", title)
        if self._hits:
            self._next_hit()

    def _next_hit(self):
        if not self._hits:
            return
        self._hit_i = (self._hit_i + 1) % len(self._hits)
        self.text.see(self._hits[self._hit_i])
