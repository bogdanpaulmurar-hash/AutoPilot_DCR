# -*- coding: utf-8 -*-
# ============================================================
# AutoPilot DC v4.16 — 📥 Import AI (fereastra din Studio)
#
# 1. 📋 Copiezi promptul si il dai AI-ului impreuna cu documentul Word (procedura).
# 2. Lipesti aici raspunsul AI-ului (sau deschizi un fisier .txt / .json / .rpr.json).
# 3. Verificarea arata pasii si problemele pe randuri; ✅ Creeaza rutina o deschide intr-un tab nou.
# Formatul si cititorul: rpr/importer.py
# ============================================================

from __future__ import annotations

import os
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Optional

import ui_theme
from rpr.importer import ImportResult, StepImporter, ai_prompt

try:
    import i18n
    from i18n import tr, tr_template
except ImportError:  # pragma: no cover
    i18n = None

    def tr(text):
        return text
    tr_template = tr


# ── clipboard-ul Windows, direct ──
# Dupa 📋 Copiaza promptul, Tk ramane "proprietarul" clipboard-ului si, la Ctrl+V in aceeasi fereastra,
# lipea tot promptul in loc de textul copiat intre timp din AI. De aceea scriem si citim direct
# clipboard-ul din Windows; pe alte sisteme (sau daca nu merge) ramane clipboard-ul Tk.
_CF_UNICODETEXT = 13
_GMEM_MOVEABLE = 0x0002


def _win_api():
    import ctypes
    from ctypes import wintypes
    u32, k32 = ctypes.windll.user32, ctypes.windll.kernel32
    u32.OpenClipboard.argtypes = [wintypes.HWND]
    u32.OpenClipboard.restype = wintypes.BOOL
    u32.GetClipboardData.argtypes = [wintypes.UINT]
    u32.GetClipboardData.restype = wintypes.HANDLE
    u32.SetClipboardData.argtypes = [wintypes.UINT, wintypes.HANDLE]
    u32.SetClipboardData.restype = wintypes.HANDLE
    k32.GlobalAlloc.argtypes = [wintypes.UINT, ctypes.c_size_t]
    k32.GlobalAlloc.restype = wintypes.HGLOBAL
    k32.GlobalLock.argtypes = [wintypes.HGLOBAL]
    k32.GlobalLock.restype = ctypes.c_void_p
    k32.GlobalUnlock.argtypes = [wintypes.HGLOBAL]
    k32.GlobalFree.argtypes = [wintypes.HGLOBAL]
    return ctypes, u32, k32


def _open_clipboard(u32) -> bool:
    import time
    for _ in range(10):   # alta aplicatie il poate tine deschis cateva milisecunde
        if u32.OpenClipboard(None):
            return True
        time.sleep(0.02)
    return False


def win_clipboard_get() -> Optional[str]:
    """Textul din clipboard-ul Windows; None daca nu e Windows sau nu se poate citi."""
    if sys.platform != "win32":
        return None
    try:
        ctypes, u32, k32 = _win_api()
        if not _open_clipboard(u32):
            return None
        try:
            h = u32.GetClipboardData(_CF_UNICODETEXT)
            if not h:
                return ""
            ptr = k32.GlobalLock(h)
            if not ptr:
                return None
            try:
                return ctypes.wstring_at(ptr)
            finally:
                k32.GlobalUnlock(h)
        finally:
            u32.CloseClipboard()
    except Exception:
        return None


def win_clipboard_set(text: str) -> bool:
    """Pune textul in clipboard-ul Windows (fara ca Tk sa devina proprietar). False = nu s-a putut."""
    if sys.platform != "win32":
        return False
    try:
        ctypes, u32, k32 = _win_api()
        data = (text or "").encode("utf-16-le") + b"\x00\x00"
        if not _open_clipboard(u32):
            return False
        try:
            u32.EmptyClipboard()
            h = k32.GlobalAlloc(_GMEM_MOVEABLE, len(data))
            if not h:
                return False
            ptr = k32.GlobalLock(h)
            if not ptr:
                k32.GlobalFree(h)
                return False
            ctypes.memmove(ptr, data, len(data))
            k32.GlobalUnlock(h)
            if not u32.SetClipboardData(_CF_UNICODETEXT, h):
                k32.GlobalFree(h)
                return False
            return True   # de aici memoria e a Windows-ului
        finally:
            u32.CloseClipboard()
    except Exception:
        return False

FONT = "Segoe UI"


class ImportDialog(tk.Toplevel):
    """Text "Pasi AutoPilot" (sau JSON) -> verificare -> rutina noua in Studio."""

    def __init__(self, panel):
        super().__init__(panel)
        self.p = panel
        self.C = C = panel.C
        self.result: Optional[ImportResult] = None
        self._after = None
        self.title("📥 Import AI — pasi din text")
        self.configure(bg=C["bg_main"])
        self.transient(panel.winfo_toplevel())
        ui_theme.fit_window(self, 1180, 760)

        tk.Label(self, text="📥  Import AI: rutina din pasii scrisi de un AI", bg=C["bg_main"], fg=C["primary"],
                 font=(FONT, 13, "bold"), anchor="w").pack(fill="x", padx=14, pady=(12, 2))
        ui_theme.autowrap(tk.Label(
            self, text="1. 📋 Copiaza promptul si da-l AI-ului impreuna cu documentul Word (procedura).   "
                       "2. Lipeste aici raspunsul AI-ului sau deschide fisierul primit (.txt, .json, .rpr.json).   "
                       "3. Verifica pasii din dreapta, apoi ✅ Creeaza rutina: se deschide intr-un tab nou, iar "
                       "butoanele si campurile noi intra in 📚 Biblioteca.",
            bg=C["bg_main"], fg=C["text_dim"], font=(FONT, 10), justify="left", anchor="w")).pack(
            fill="x", padx=14)

        bar = tk.Frame(self, bg=C["bg_main"])
        bar.pack(fill="x", padx=12, pady=8)
        self._b(bar, "📋 Copiaza promptul pentru AI", self.copy_prompt, C["primary"]).pack(side="left", padx=2)
        self._b(bar, "💾 Salveaza promptul…", self.save_prompt).pack(side="left", padx=2)
        self._b(bar, "📂 Deschide fisier…", self.open_file).pack(side="left", padx=2)
        self._b(bar, "📝 Exemplu", self.load_example).pack(side="left", padx=2)
        self._b(bar, "🧹 Goleste", lambda: (self.text.delete("1.0", "end"), self.check())).pack(side="left", padx=2)

        body = ttk.PanedWindow(self, orient="horizontal")
        body.pack(fill="both", expand=True, padx=12, pady=(0, 6))
        left = tk.Frame(body, bg=C["bg_main"])
        body.add(left, weight=1)
        tk.Label(left, text="Textul primit de la AI", bg=C["bg_main"], fg=C["text_dim"], font=(FONT, 10, "bold"),
                 anchor="w").pack(fill="x")
        tbox = tk.Frame(left, bg=C["bg_main"])
        tbox.pack(fill="both", expand=True)
        self.text = tk.Text(tbox, wrap="none", undo=True, bg=C["bg_input"], fg=C["text"], insertbackground=C["text"],
                            font=("Consolas", 10), relief="flat", padx=6, pady=4, height=8)
        ys = ttk.Scrollbar(tbox, orient="vertical", command=self.text.yview)
        self.text.configure(yscrollcommand=ys.set)
        ys.pack(side="right", fill="y")
        self.text.pack(side="left", fill="both", expand=True)
        self.text.tag_configure("bad", background="#7A1F1F", foreground="white")
        self.text.tag_configure("warn", background="#6B5200", foreground="white")
        self.text.bind("<<Modified>>", self._on_modified)
        self.text.bind("<<Paste>>", self._paste)

        right = tk.Frame(body, bg=C["bg_main"])
        body.add(right, weight=1)
        self.summary = tk.Label(right, text="", bg=C["bg_main"], fg=C["text"], font=(FONT, 10, "bold"), anchor="w",
                                justify="left")
        self.summary.pack(fill="x")
        self.tree = ttk.Treeview(right, show="tree", style="Studio.Treeview", selectmode="browse", height=6)
        self.tree.pack(fill="both", expand=True, pady=(2, 6))
        tk.Label(right, text="Probleme (click = randul din text)", bg=C["bg_main"], fg=C["text_dim"],
                 font=(FONT, 10, "bold"), anchor="w").pack(fill="x")
        self.issues = tk.Listbox(right, height=5, bg=C["bg_input"], fg=C["text"], relief="flat", font=(FONT, 10),
                                 selectbackground=C["primary"], activestyle="none")
        self.issues.pack(fill="x")
        self.issues.bind("<<ListboxSelect>>", self._goto_issue)
        self._issue_lines = []

        # jos, pus inaintea panourilor: pe un ecran mic se micsoreaza textul, nu dispare butonul
        foot = tk.Frame(self, bg=C["bg_main"])
        foot.pack(side="bottom", fill="x", padx=12, pady=(0, 12), before=body)
        self.btn_create = self._b(foot, "✅ Creeaza rutina", self.create, C["success"])
        self.btn_create.pack(side="right", padx=2)
        self._b(foot, "Inchide", self.destroy).pack(side="right", padx=2)
        self.btn_create.configure(state="disabled")
        self.bind("<Control-Return>", lambda e: self.create() if str(self.btn_create.cget("state")) != "disabled" else None)
        self.check()
        self.text.focus_set()

    def _b(self, parent, text, cmd, color=None):
        return self.p._btn(parent, text, cmd, color=color)

    # ── prompt ──
    def _lang(self) -> str:
        return getattr(i18n, "LANG", "ro") if i18n is not None else "ro"

    def copy_prompt(self):
        prompt = ai_prompt(self._lang(), list(self.p.repo.objects))
        if not win_clipboard_set(prompt):
            self.clipboard_clear()
            self.clipboard_append(prompt)
        self.p.set_status("📋 Promptul e copiat: lipeste-l in AI, apoi adauga textul documentului Word.")
        messagebox.showinfo("📥 Import AI", "Promptul e copiat.\n\nIn AI: lipeste promptul, apoi textul procedurii "
                                           "(sau ataseaza documentul Word). Raspunsul AI-ului il lipesti aici.",
                            parent=self)

    def save_prompt(self):
        path = filedialog.asksaveasfilename(parent=self, title="Salveaza promptul pentru AI",
                                            initialfile="Prompt_AutoPilot_Import.txt", defaultextension=".txt",
                                            filetypes=[("Text", "*.txt")])
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write(ai_prompt(self._lang(), list(self.p.repo.objects)))
            self.p.set_status(f"Promptul a fost salvat: {path}")

    def load_example(self):
        from rpr.importer import _EXAMPLE_EN, _EXAMPLE_RO
        self.text.delete("1.0", "end")
        self.text.insert("1.0", _EXAMPLE_RO if self._lang() == "ro" else _EXAMPLE_EN)
        self.check()

    def open_file(self):
        path = filedialog.askopenfilename(parent=self, title="Deschide pasii primiti de la AI",
                                          filetypes=[("Pasi AutoPilot", "*.txt *.md *.json"),
                                                     ("Toate fisierele", "*.*")])
        if not path:
            return
        try:
            with open(path, encoding="utf-8-sig") as f:
                data = f.read()
        except (OSError, UnicodeDecodeError) as ex:
            messagebox.showerror("📥 Import AI", str(ex), parent=self)
            return
        self.text.delete("1.0", "end")
        self.text.insert("1.0", data)
        self.check()
        self.p.set_status(f"Fisier citit: {os.path.basename(path)}")

    def _paste(self, _e=None):
        """Ctrl+V / Shift+Insert: textul din clipboard-ul sistemului (vezi win_clipboard_get)."""
        data = win_clipboard_get()
        if data is None:
            try:
                data = self.clipboard_get()
            except tk.TclError:
                return "break"
        try:
            self.text.delete("sel.first", "sel.last")
        except tk.TclError:
            pass
        self.text.insert("insert", data)
        self.text.see("insert")
        return "break"

    # ── verificare ──
    def _on_modified(self, _e=None):
        if not self.text.edit_modified():
            return
        self.text.edit_modified(False)
        if self._after is not None:
            self.after_cancel(self._after)
        self._after = self.after(500, self.check)

    def check(self):
        self._after = None
        res = StepImporter(self.p.repo).parse(self.text.get("1.0", "end"))
        self.result = res
        self.tree.delete(*self.tree.get_children())
        from studio_ui import icon_for

        def add(node, parent):
            iid = self.tree.insert(parent, "end", text=f"{icon_for(node)}  {node.title}", open=True)
            br = node.branches()
            for name, lst in br:
                par = iid
                if len(br) > 1:
                    par = self.tree.insert(iid, "end", text=f"▸ {tr(name)}", open=True)
                for ch in lst:
                    add(ch, par)
        for n in res.routine.steps:
            add(n, "")
        self.issues.delete(0, "end")
        self._issue_lines = []
        self.text.tag_remove("bad", "1.0", "end")
        self.text.tag_remove("warn", "1.0", "end")
        for i in res.issues:
            prefix = ("✕ " if i.error else "⚠ ") + (tr_template("Randul {0}").format(i.line) + ": " if i.line else "")
            self.issues.insert("end", prefix + i.message)
            self._issue_lines.append(i.line)
            if i.line:
                self.text.tag_add("bad" if i.error else "warn", f"{i.line}.0", f"{i.line}.end")
        empty = not self.text.get("1.0", "end").strip()
        if empty:
            self.summary.configure(text=tr("Lipeste aici textul primit de la AI."), fg=self.C["text_dim"])
        else:
            msg = tr_template("\"{0}\": {1} pasi, {2} obiecte noi in biblioteca").format(
                res.routine.name, res.step_count(), len(res.new_objects))
            if res.errors:
                msg += "  ·  " + tr_template("{0} erori: corecteaza randurile marcate cu rosu").format(len(res.errors))
            if res.todos:
                msg += "  ·  " + tr_template("{0} locuri de completat de tine (# TODO, in galben)").format(res.todos)
            self.summary.configure(text=msg, fg=self.C["danger"] if res.errors else self.C["text"])
        self.btn_create.configure(state="normal" if res.ok else "disabled")

    def _goto_issue(self, _e=None):
        sel = self.issues.curselection()
        if not sel:
            return
        line = self._issue_lines[sel[0]]
        if line:
            self.text.see(f"{line}.0")
            self.text.mark_set("insert", f"{line}.0")
            self.text.focus_set()

    def create(self):
        self.check()
        res = self.result
        if res is None or not res.ok:
            return
        if self.p.open_imported(res.routine, res.new_objects):
            self.destroy()
