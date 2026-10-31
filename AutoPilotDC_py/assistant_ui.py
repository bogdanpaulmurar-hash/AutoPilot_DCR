# -*- coding: utf-8 -*-
# ============================================================
# AutoPilot DC v4.24 — 🤖 Asistent AI (fereastra din Studio)
#
# 💬 Intreaba: o intrebare despre aplicatie sau despre rutina deschisa; AutoPilot adauga capitolele potrivite
#    din Instructiuni, schita rutinei, obiectele ei si ultimele erori.
# 🛠 Fa rutina: procedura (text sau document Word) -> rutina, prin 📥 Import (verificare + ✅ Creeaza rutina).
# 🔧 Repara rutina: rutina deschisa + erorile + ce s-a schimbat -> rutina corectata, intr-un tab nou.
# Fara conexiune: 📋 Copiaza pentru AI pune tot textul in clipboard, pentru AI-ul tau.
# Cu conexiune (⚙ Conexiune): trimite direct; cererea merge pe un fir separat, fereastra nu se blocheaza.
# Motorul: rpr/assistant.py
# ============================================================

from __future__ import annotations

import os
import queue
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import List, Optional

import ui_theme
from rpr import assistant as ai

try:
    import i18n
    from i18n import tr, tr_template
except ImportError:  # pragma: no cover
    i18n = None

    def tr(text):
        return text
    tr_template = tr

FONT = "Segoe UI"


def _clip(widget, text: str) -> None:
    try:
        from import_ui import win_clipboard_set
        if win_clipboard_set(text):
            return
    except Exception:
        pass
    widget.clipboard_clear()
    widget.clipboard_append(text)


class AssistantDialog(tk.Toplevel):
    def __init__(self, panel):
        super().__init__(panel)
        self.p = panel
        self.C = C = panel.C
        self.settings = ai.AiSettings.load()
        self.history: List[ai.Message] = []
        self._q: "queue.Queue" = queue.Queue()
        self._busy = False
        self._last_answer = ""
        self._draft: Optional[ai.RoutineDraft] = None
        self.title("🤖 Asistent AI")
        self.configure(bg=C["bg_main"])
        self.transient(panel.winfo_toplevel())
        ui_theme.fit_window(self, 1040, 720)

        head = tk.Frame(self, bg=C["bg_main"])
        head.pack(fill="x", padx=14, pady=(12, 2))
        tk.Label(head, text="🤖  Asistent AI pentru AutoPilot", bg=C["bg_main"], fg=C["primary"],
                 font=(FONT, 13, "bold"), anchor="w").pack(side="left")
        self._b(head, "⚙ Conexiune…", self.edit_settings).pack(side="right", padx=2)
        self.conn = tk.Label(head, text="", bg=C["bg_main"], fg=C["text_dim"], font=(FONT, 10), anchor="e")
        self.conn.pack(side="right", padx=8)
        ui_theme.autowrap(tk.Label(
            self, text="AI-ul raspunde din Instructiuni, rutina deschisa si ultimele erori, si face rutine din "
                       "proceduri. Nu ruleaza nimic singur: rutina propusa trece prin 📥 Import, unde o verifici.",
            bg=C["bg_main"], fg=C["text_dim"], font=(FONT, 10), justify="left", anchor="w")).pack(fill="x", padx=14)

        self.nb = ttk.Notebook(self)
        self.nb.pack(fill="both", expand=True, padx=12, pady=8)
        self._build_ask()
        self._build_routine()
        self._build_repair()
        self.nb.bind("<<NotebookTabChanged>>", lambda e: self._refresh_repair())

        foot = tk.Frame(self, bg=C["bg_main"])
        foot.pack(side="bottom", fill="x", padx=12, pady=(0, 12), before=self.nb)
        self.status = tk.Label(foot, text="", bg=C["bg_main"], fg=C["text_dim"], font=(FONT, 10), anchor="w")
        self.status.pack(side="left", fill="x", expand=True)
        self._b(foot, "Inchide", self.destroy).pack(side="right", padx=2)
        self._refresh_conn()
        self._poll_id = self.after(100, self._poll)

    def destroy(self):
        try:
            self.after_cancel(self._poll_id)
        except (tk.TclError, AttributeError):
            pass
        super().destroy()

    def _b(self, parent, text, cmd, color=None):
        return self.p._btn(parent, text, cmd, color=color)

    def _text(self, parent, height=6, mono=False):
        box = tk.Frame(parent, bg=self.C["bg_main"])
        t = tk.Text(box, wrap="word", undo=True, bg=self.C["bg_input"], fg=self.C["text"],
                    insertbackground=self.C["text"], font=("Consolas", 10) if mono else (FONT, 10), relief="flat",
                    padx=6, pady=4, height=height)
        ys = ttk.Scrollbar(box, orient="vertical", command=t.yview)
        t.configure(yscrollcommand=ys.set)
        ys.pack(side="right", fill="y")
        t.pack(side="left", fill="both", expand=True)
        return box, t

    def _lang(self) -> str:
        return getattr(i18n, "LANG", "ro") if i18n is not None else "ro"

    # ── 💬 Intreaba ──
    def _build_ask(self):
        C = self.C
        f = tk.Frame(self.nb, bg=C["bg_main"])
        self.nb.add(f, text="💬 Intreaba")
        tk.Label(f, text="Intrebarea ta (ex.: de ce nu gaseste butonul Salveaza? cum repet pasii pentru fiecare rand "
                         "din Excel?)", bg=C["bg_main"], fg=C["text_dim"], font=(FONT, 10, "bold"),
                 anchor="w").pack(fill="x", pady=(6, 0))
        box, self.q_text = self._text(f, height=4)
        box.pack(fill="x")
        opts = tk.Frame(f, bg=C["bg_main"])
        opts.pack(fill="x", pady=4)
        self.v_routine = tk.BooleanVar(value=self.settings.send_routine)
        self.v_errors = tk.BooleanVar(value=self.settings.send_errors)
        for var, txt in [(self.v_routine, "Trimite si rutina deschisa"), (self.v_errors, "Trimite si ultimele erori")]:
            tk.Checkbutton(opts, text=txt, variable=var, bg=C["bg_main"], fg=C["text"], selectcolor=C["bg_input"],
                           activebackground=C["bg_main"], activeforeground=C["text"],
                           font=(FONT, 10)).pack(side="left", padx=(0, 12))
        self.btn_ask = self._b(opts, "➤ Trimite", self.send_question, C["primary"])
        self.btn_ask.pack(side="right", padx=2)
        self._b(opts, "📋 Copiaza pentru AI", self.copy_question).pack(side="right", padx=2)
        self._b(opts, "🧹 Conversatie noua", self.new_chat).pack(side="right", padx=2)
        tk.Label(f, text="Raspunsul", bg=C["bg_main"], fg=C["text_dim"], font=(FONT, 10, "bold"),
                 anchor="w").pack(fill="x")
        box, self.a_text = self._text(f, height=12)
        box.pack(fill="both", expand=True)
        self.a_text.tag_configure("me", foreground=C["primary"], font=(FONT, 10, "bold"))
        row = tk.Frame(f, bg=C["bg_main"])
        row.pack(fill="x", pady=(4, 0))
        self.btn_to_import = self._b(row, "📥 Pasii din raspuns in Import", self.answer_to_import)
        self.btn_to_import.pack(side="right", padx=2)
        self._b(row, "📋 Copiaza raspunsul", lambda: _clip(self, self._last_answer)).pack(side="right", padx=2)
        self.q_text.bind("<Control-Return>", lambda e: (self.send_question(), "break")[1])

    def _question(self) -> str:
        return self.q_text.get("1.0", "end").strip()

    def _ctx(self):
        s = ai.AiSettings(**{**self.settings.__dict__})
        s.send_routine, s.send_errors = bool(self.v_routine.get()), bool(self.v_errors.get())
        routine = getattr(self.p, "routine", None)
        logs = list(getattr(self.p, "_log_entries", []) or [])
        return s, routine, logs, getattr(self.p, "repo", None)

    def copy_question(self):
        q = self._question()
        if not q:
            self._say(tr("Scrie intai intrebarea."))
            return
        s, routine, logs, repo = self._ctx()
        _clip(self, ai.ask_copy_text(q, self._lang(), routine, logs, s, repo=repo))
        self._say(tr("📋 Copiat: lipeste-l in AI-ul tau; raspunsul il poti lipi aici, in Raspunsul."))

    def send_question(self):
        q = self._question()
        if not q or self._busy:
            return
        if not self.settings.connected:
            self.copy_question()
            return
        s, routine, logs, repo = self._ctx()
        client = ai.AiClient(s)
        hist = list(self.history)
        self.a_text.insert("end", ("\n" if self.a_text.get("1.0", "end").strip() else "") + "▶ " + q + "\n", "me")
        self.a_text.see("end")
        self.q_text.delete("1.0", "end")

        def job():
            return ai.ask(client, q, self._lang(), routine, logs, history=hist, repo=repo)

        def done(answer):
            self.history += [{"role": "user", "content": q}, {"role": "assistant", "content": answer}]
            self.history = self.history[-8:]   # ultimele 4 schimburi: modelele mici au context mic
            self._show_answer(answer)
        self._run(job, done, tr("Astept raspunsul AI-ului…"))

    def _show_answer(self, answer: str):
        self._last_answer = answer
        self.a_text.insert("end", answer.strip() + "\n")
        self.a_text.see("end")
        has = bool(ai.extract_text_block(answer))
        self._say(tr("Raspuns primit.") + ("  " + tr("Are pasi: 📥 Pasii din raspuns in Import.") if has else ""))

    def new_chat(self):
        self.history = []
        self._last_answer = ""
        self.a_text.delete("1.0", "end")
        self._say(tr("Conversatie noua."))

    def answer_to_import(self):
        src = self._last_answer
        try:
            sel = self.a_text.get("sel.first", "sel.last")
            if sel.strip():
                src = sel
        except tk.TclError:
            if not src:   # raspuns lipit de mana din AI-ul tau
                src = self.a_text.get("1.0", "end")
        steps = ai.extract_text_block(src) or src
        if not steps.strip():
            self._say(tr("Raspunsul nu are pasi de importat."))
            return
        self._open_import(steps)

    # ── 🛠 Fa rutina ──
    def _build_routine(self):
        C = self.C
        f = tk.Frame(self.nb, bg=C["bg_main"])
        self.nb.add(f, text="🛠 Fa rutina din procedura")
        tk.Label(f, text="Procedura: lipeste textul sau deschide documentul (Word .docx, .txt, .md). Scrie ce se "
                         "face, pe ce ecran, cu ce date (ex. coloanele din Excel).", bg=C["bg_main"],
                 fg=C["text_dim"], font=(FONT, 10, "bold"), anchor="w", justify="left").pack(fill="x", pady=(6, 0))
        bar = tk.Frame(f, bg=C["bg_main"])
        bar.pack(fill="x", pady=4)
        self._b(bar, "📂 Deschide procedura…", self.open_procedure).pack(side="left", padx=2)
        self._b(bar, "🧹 Goleste", lambda: self.p_text.delete("1.0", "end")).pack(side="left", padx=2)
        self.btn_make = self._b(bar, "🤖 Fa rutina", self.make_routine, C["primary"])
        self.btn_make.pack(side="right", padx=2)
        self._b(bar, "📋 Copiaza pentru AI", self.copy_procedure).pack(side="right", padx=2)
        box, self.p_text = self._text(f, height=16, mono=True)
        box.pack(fill="both", expand=True)
        self.r_info = tk.Label(f, text="", bg=C["bg_main"], fg=C["text"], font=(FONT, 10), anchor="w",
                               justify="left")
        self.r_info.pack(fill="x", pady=(4, 0))
        ui_theme.autowrap(self.r_info)

    def open_procedure(self):
        path = filedialog.askopenfilename(parent=self, title=tr("Deschide procedura"),
                                          filetypes=[(tr("Procedura"), "*.docx *.txt *.md"), (tr("Toate fisierele"), "*.*")])
        if not path:
            return
        try:
            text = ai.read_procedure(path)
        except (OSError, ai.AiError) as ex:
            messagebox.showerror("🤖 Asistent AI", str(ex), parent=self)
            return
        self.p_text.delete("1.0", "end")
        self.p_text.insert("1.0", text)
        self._say(tr_template("Procedura citita: {0}").format(os.path.basename(path)))

    def _procedure(self) -> str:
        return self.p_text.get("1.0", "end").strip()

    def copy_procedure(self):
        proc = self._procedure()
        if not proc:
            self._say(tr("Lipeste intai procedura."))
            return
        _clip(self, ai.routine_copy_text(proc, self._lang(), list(getattr(self.p.repo, "objects", []))))
        self._say(tr("📋 Copiat (promptul + procedura): lipeste-l in AI, apoi raspunsul in 📥 Import AI."))
        self.r_info.configure(text=tr("Dupa raspunsul AI-ului: 📥 Import AI → lipeste → ✅ Creeaza rutina."))

    def make_routine(self):
        proc = self._procedure()
        if not proc or self._busy:
            if not proc:
                self._say(tr("Lipeste intai procedura."))
            return
        if not self.settings.connected:
            self.copy_procedure()
            return
        client = ai.AiClient(self.settings)
        repo, lang = self.p.repo, self._lang()

        def job():
            return ai.make_routine(client, proc, repo, lang, progress=lambda m: self._q.put(("say", m)))

        def done(draft: "ai.RoutineDraft"):
            self._draft = draft
            res = draft.result
            msg = "  ·  ".join(draft.log)
            if res.ok:
                msg += "\n" + tr_template("Rutina \"{0}\": {1} pasi, {2} locuri de completat (# TODO). Se deschide "
                                          "in 📥 Import: verifica si ✅ Creeaza rutina.").format(
                    res.routine.name, res.step_count(), res.todos)
            else:
                msg += "\n" + tr_template("Au ramas {0} erori: le vezi marcate cu rosu in 📥 Import.").format(
                    len(res.errors))
            self.r_info.configure(text=msg, fg=self.C["text"] if res.ok else self.C["danger"])
            self._open_import(draft.text)
        self._run(job, done, tr("Astept rutina de la AI…"))

    # ── 🔧 Repara rutina ──
    def _build_repair(self):
        C = self.C
        f = tk.Frame(self.nb, bg=C["bg_main"])
        self.nb.add(f, text="🔧 Repara rutina")
        self.rep_info = tk.Label(f, text="", bg=C["bg_main"], fg=C["text"], font=(FONT, 10, "bold"), anchor="w",
                                 justify="left")
        self.rep_info.pack(fill="x", pady=(6, 0))
        ui_theme.autowrap(self.rep_info)
        tk.Label(f, text="Ce s-a schimbat sau ce nu merge (ex.: butonul Salveaza s-a mutat in meniul Actiuni; dupa "
                         "Trimite apare un mesaj nou de confirmare).", bg=C["bg_main"], fg=C["text_dim"],
                 font=(FONT, 10), anchor="w", justify="left").pack(fill="x", pady=(6, 0))
        box, self.rep_text = self._text(f, height=6)
        box.pack(fill="both", expand=True)
        bar = tk.Frame(f, bg=C["bg_main"])
        bar.pack(fill="x", pady=4)
        self.v_rep_errors = tk.BooleanVar(value=True)
        tk.Checkbutton(bar, text="Trimite si ultimele erori", variable=self.v_rep_errors, bg=C["bg_main"],
                       fg=C["text"], selectcolor=C["bg_input"], activebackground=C["bg_main"],
                       activeforeground=C["text"], font=(FONT, 10)).pack(side="left")
        self.btn_repair = self._b(bar, "🔧 Repara", self.repair_routine, C["primary"])
        self.btn_repair.pack(side="right", padx=2)
        self._b(bar, "📋 Copiaza pentru AI", self.copy_repair).pack(side="right", padx=2)
        ui_theme.autowrap(tk.Label(
            f, text="Rutina reparata se deschide intr-un tab nou, nesalvata; originalul ramane neschimbat. Randurile "
                    "pe care AI-ul nu le-a schimbat isi pastreaza setarile (timeout, pauze, la eroare).",
            bg=C["bg_main"], fg=C["text_dim"], font=(FONT, 10), justify="left", anchor="w")).pack(fill="x")
        self.rep_result = tk.Label(f, text="", bg=C["bg_main"], fg=C["text"], font=(FONT, 10), anchor="w",
                                   justify="left")
        self.rep_result.pack(fill="x", pady=(4, 0))
        ui_theme.autowrap(self.rep_result)
        self._refresh_repair()

    def _repair_job(self):
        r = getattr(self.p, "routine", None)
        if r is None or not r.steps:
            return None
        return ai.prepare_repair(r, self._lang())

    def _refresh_repair(self):
        job = self._repair_job()
        if job is None:
            self.rep_info.configure(text=tr("Deschide intai rutina de reparat (tab-ul ei in Studio)."))
            return
        n = sum(1 for _ in job.original.all_nodes())
        self.rep_info.configure(text=tr_template("Rutina deschisa: \"{0}\" ({1} pasi; {2} raman neschimbati, "
                                                 "PASTREAZA)").format(job.original.name, n, len(job.writer.keep)))

    def _rep_logs(self):
        return list(getattr(self.p, "_log_entries", []) or []) if self.v_rep_errors.get() else []

    def copy_repair(self):
        job = self._repair_job()
        if job is None:
            self._say(tr("Deschide intai rutina de reparat (tab-ul ei in Studio)."))
            return
        note = self.rep_text.get("1.0", "end").strip()
        _clip(self, ai.repair_copy_text(job, note, self._rep_logs(), list(getattr(self.p.repo, "objects", []))))
        self._open_import("", repair=job)
        self._say(tr("📋 Copiat: lipeste-l in AI, apoi raspunsul in fereastra 📥 Import deschisa acum."))

    def repair_routine(self):
        if self._busy:
            return
        job = self._repair_job()
        if job is None:
            self._say(tr("Deschide intai rutina de reparat (tab-ul ei in Studio)."))
            return
        if not self.settings.connected:
            self.copy_repair()
            return
        note = self.rep_text.get("1.0", "end").strip()
        client, repo, logs = ai.AiClient(self.settings), self.p.repo, self._rep_logs()

        def job_fn():
            return ai.repair_routine(client, job, note, repo, logs, progress=lambda m: self._q.put(("say", m)))

        def done(draft: "ai.RoutineDraft"):
            res = draft.result
            msg = "  ·  ".join(draft.log)
            if not res.ok:
                msg += "\n" + tr_template("Au ramas {0} erori: le vezi marcate cu rosu in 📥 Import.").format(
                    len(res.errors))
            self.rep_result.configure(text=msg, fg=self.C["text"] if res.ok else self.C["danger"])
            self._open_import(draft.text, repair=job)
        self._run(job_fn, done, tr("Astept rutina reparata de la AI…"))

    # ── comun ──
    def _open_import(self, text: str, repair=None):
        self.p.show_import()
        w = getattr(self.p, "_import_win", None)
        if w is not None and w.winfo_exists():
            w.set_text(text, repair=repair)
            w.lift()

    def _say(self, text: str):
        self.status.configure(text=text, fg=self.C["text_dim"])

    def _run(self, job, done, waiting: str):
        """Cererea pe un fir separat (fereastra si Studio raman libere); rezultatul vine prin coada."""
        self._busy = True
        for b in (self.btn_ask, self.btn_make, self.btn_repair):
            b.configure(state="disabled")
        self._say("⏳ " + waiting)

        def work():
            try:
                self._q.put(("ok", (done, job())))
            except ai.AiError as ex:
                self._q.put(("err", str(ex)))
            except Exception as ex:  # noqa: BLE001 — orice eroare ajunge in fereastra, nu in consola
                self._q.put(("err", f"{type(ex).__name__}: {ex}"))
        threading.Thread(target=work, daemon=True, name="AutoPilotAI").start()

    def _poll(self):
        try:
            while True:
                kind, p = self._q.get_nowait()
                if kind == "say":
                    self._say("⏳ " + p)
                    continue
                self._busy = False
                for b in (self.btn_ask, self.btn_make, self.btn_repair):
                    b.configure(state="normal")
                if kind == "ok":
                    p[0](p[1])
                else:
                    self.status.configure(text="✕ " + p.splitlines()[0][:200], fg=self.C["danger"])
                    messagebox.showerror("🤖 Asistent AI", p, parent=self)
        except queue.Empty:
            pass
        self._poll_id = self.after(100, self._poll)

    def _refresh_conn(self):
        s = self.settings
        txt = s.label()
        if s.connected and not ai.get_key(s):
            txt += "  ·  " + tr("fara cheie")
        self.conn.configure(text=txt)
        mode = "➤ Trimite" if s.connected else "➤ Trimite (copiez)"
        self.btn_ask.configure(text=tr(mode))
        self.btn_make.configure(text=tr("🤖 Fa rutina" if s.connected else "🤖 Fa rutina (copiez)"))
        self.btn_repair.configure(text=tr("🔧 Repara" if s.connected else "🔧 Repara (copiez)"))

    def edit_settings(self):
        d = AiSettingsDialog(self, self.settings)
        self.wait_window(d)
        if d.saved:
            self.settings = d.saved
            self._refresh_conn()


class AiSettingsDialog(tk.Toplevel):
    """⚙ Conexiunea la AI: furnizorul, adresa, modelul, cheia (keyring / variabila de mediu)."""

    def __init__(self, owner: AssistantDialog, s: ai.AiSettings):
        super().__init__(owner)
        self.owner = owner
        self.C = C = owner.C
        self.saved: Optional[ai.AiSettings] = None
        self.title("⚙ Conexiunea la AI")
        self.configure(bg=C["bg_main"])
        self.transient(owner)
        ui_theme.fit_window(self, 640, 520)
        g = tk.Frame(self, bg=C["bg_main"])
        g.pack(fill="both", expand=True, padx=14, pady=12)
        g.columnconfigure(1, weight=1)
        self._prov = {tr(lbl): code for code, lbl in ai.PROVIDERS}
        self._auth = {tr(lbl): code for code, lbl in ai.AUTH_HEADERS}
        self.v = {
            "provider": tk.StringVar(value=next(k for k, c in self._prov.items() if c == s.provider)),
            "url": tk.StringVar(value=s.url), "model": tk.StringVar(value=s.model),
            "auth": tk.StringVar(value=next((k for k, c in self._auth.items() if c == s.auth_header),
                                            next(iter(self._auth)))),
            "key_env": tk.StringVar(value=s.key_env or ai.DEFAULT_KEY_ENV), "key": tk.StringVar(),
            "ca": tk.StringVar(value=s.ca_file), "max_tokens": tk.StringVar(value=str(s.max_tokens)),
        }
        r = 0

        def row(label, widget, hint=""):
            nonlocal r
            tk.Label(g, text=label, bg=C["bg_main"], fg=C["text"], font=(FONT, 10), anchor="w").grid(
                row=r, column=0, sticky="w", pady=3, padx=(0, 8))
            widget.grid(row=r, column=1, sticky="ew", pady=3)
            r += 1
            if hint:
                tk.Label(g, text=hint, bg=C["bg_main"], fg=C["text_dim"], font=(FONT, 9), anchor="w", justify="left",
                         wraplength=380).grid(row=r, column=1, sticky="w")
                r += 1

        def entry(var, show=None):
            return tk.Entry(g, textvariable=var, bg=C["bg_input"], fg=C["text"], insertbackground=C["text"],
                            relief="flat", font=(FONT, 10), show=show)

        row(tr("Furnizor"), ttk.Combobox(g, textvariable=self.v["provider"], values=list(self._prov), state="readonly"))
        row(tr("Adresa API"), entry(self.v["url"]),
            tr("Gol = adresa publica. Gateway-ul firmei: adresa data de IT (ex. https://.../v1)."))
        row(tr("Model"), entry(self.v["model"]), tr("Numele exact al modelului din gateway (ex. un model Haiku sau Flash)."))
        row(tr("Antet cheie"), ttk.Combobox(g, textvariable=self.v["auth"], values=list(self._auth), state="readonly"))
        row(tr("Cheia API"), entry(self.v["key"], show="•"),
            tr("Se pastreaza in Windows (keyring), nu in fisier. Gol = neschimbata."))
        row(tr("Sau variabila de mediu"), entry(self.v["key_env"]))
        ca = tk.Frame(g, bg=C["bg_main"])
        entry_ca = tk.Entry(ca, textvariable=self.v["ca"], bg=C["bg_input"], fg=C["text"], insertbackground=C["text"],
                            relief="flat", font=(FONT, 10))
        entry_ca.pack(side="left", fill="x", expand=True)
        owner._b(ca, "…", self._pick_ca).pack(side="left", padx=(4, 0))
        row(tr("Certificatul firmei"), ca, tr("Doar daca apare o eroare de certificat (proxy cu inspectie SSL)."))
        row(tr("Lungimea maxima a raspunsului"), entry(self.v["max_tokens"]))
        self.src = tk.Label(g, text="", bg=C["bg_main"], fg=C["text_dim"], font=(FONT, 9), anchor="w")
        self.src.grid(row=r, column=1, sticky="w")
        self._show_key_source(s)

        foot = tk.Frame(self, bg=C["bg_main"])
        foot.pack(fill="x", padx=12, pady=(0, 12))
        owner._b(foot, "💾 Salveaza", self.save, C["success"]).pack(side="right", padx=2)
        owner._b(foot, "Anuleaza", self.destroy).pack(side="right", padx=2)
        owner._b(foot, "🧪 Testeaza conexiunea", self.test).pack(side="left", padx=2)
        self.grab_set()

    def _show_key_source(self, s):
        src = ai.key_source(s)
        self.src.configure(text={"env": tr_template("Cheia: din variabila de mediu {0}").format(s.key_env),
                                 "keyring": tr("Cheia: salvata in Windows (keyring)")}.get(src, tr("Cheia: lipseste")))

    def _pick_ca(self):
        p = filedialog.askopenfilename(parent=self, filetypes=[(tr("Certificat"), "*.pem *.crt *.cer"),
                                                               (tr("Toate fisierele"), "*.*")])
        if p:
            self.v["ca"].set(p)

    def _collect(self) -> ai.AiSettings:
        s = ai.AiSettings(**{**self.owner.settings.__dict__})
        s.provider = self._prov.get(self.v["provider"].get(), "")
        s.url = self.v["url"].get().strip()
        s.model = self.v["model"].get().strip()
        s.auth_header = self._auth.get(self.v["auth"].get(), "")
        s.key_env = self.v["key_env"].get().strip() or ai.DEFAULT_KEY_ENV
        s.ca_file = self.v["ca"].get().strip()
        try:
            s.max_tokens = max(256, min(32000, int(self.v["max_tokens"].get())))
        except ValueError:
            pass
        return s

    def _store_key(self, s) -> bool:
        key = self.v["key"].get().strip()
        if not key:
            return True
        if ai.set_key(s, key):
            self.v["key"].set("")
            return True
        messagebox.showwarning(
            "⚙ Conexiunea la AI",
            tr_template("Keyring nu e instalat, deci cheia nu poate fi salvata in Windows. Pune-o in variabila de "
                        "mediu {0} (sau: py -m pip install --user keyring).").format(s.key_env), parent=self)
        return False

    def test(self):
        s = self._collect()
        key = self.v["key"].get().strip() or None
        try:
            ans = ai.AiClient(s, key=key).test()
        except ai.AiError as ex:
            messagebox.showerror("🧪", str(ex), parent=self)
            return
        messagebox.showinfo("🧪", tr("Conexiunea merge. Raspunsul AI-ului:") + "\n\n" + ans.strip()[:300], parent=self)

    def save(self):
        s = self._collect()
        self._store_key(s)
        s.save()
        self.saved = s
        self.destroy()
