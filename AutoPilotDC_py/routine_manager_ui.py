# -*- coding: utf-8 -*-
# ============================================================
# AutoPilot DC — 📂 Managerul de rutine (Studio)
#
# Stanga:  rutinele din folderul ales (citit la pornirea aplicatiei):
#          deschide in Studio, ruleaza, adauga in pregatire.
# Dreapta: "Pregatirea" — o lista de rutine rulate una dupa alta
#          (ex. sandbox: useri, apoi roluri, apoi alte obiecte), cu film
#          pentru fiecare rutina, raport Excel si documentatie la final.
# Logica e in rpr/batch.py; rularea trece prin Studio (intrebari +
# sistemul de preventie raman active).
# ============================================================

from __future__ import annotations

import os
from tkinter import filedialog, messagebox, ttk
import tkinter as tk
from typing import Optional

from rpr.batch import PREP_EXT, Preparation, PrepItem, RoutineLibrary, shared_library


class RoutineManagerDialog(tk.Toplevel):
    def __init__(self, panel):
        super().__init__(panel)
        self.p = panel
        C = self.C = panel.C
        self.title("Manager de rutine")
        self.configure(bg=C["bg_main"])
        self.transient(panel.winfo_toplevel())
        self.geometry("1180x640")
        self.minsize(900, 480)
        self.prep = Preparation()
        self.lib: RoutineLibrary = shared_library()

        top = tk.Frame(self, bg=C["bg_main"])
        top.pack(fill="x", padx=12, pady=(10, 4))
        tk.Label(top, text="📂  Manager de rutine", bg=C["bg_main"], fg=C["primary"],
                 font=("Segoe UI", 13, "bold")).pack(side="left")
        self.folder_var = tk.StringVar(value=panel.studio_settings.effective_routines_folder())
        b = panel._btn
        b(top, "Schimba folderul", self.choose_folder).pack(side="right", padx=2)
        b(top, "⟳ Reciteste", self.refresh).pack(side="right", padx=2)
        b(top, "Deschide folderul", lambda: self._startfile(self.folder_var.get())).pack(side="right", padx=2)
        tk.Label(top, textvariable=self.folder_var, bg=C["bg_main"], fg=C["text_dim"],
                 font=("Segoe UI", 9)).pack(side="right", padx=8)

        paned = ttk.PanedWindow(self, orient="horizontal", style="Studio.TPanedwindow")
        paned.pack(fill="both", expand=True, padx=8, pady=4)

        # ── stanga: rutinele din folder ──
        left = tk.Frame(paned, bg=C["bg_main"])
        paned.add(left, weight=3)
        tk.Label(left, text="Rutinele din folder (se citesc la pornirea aplicatiei)", bg=C["bg_main"],
                 fg=C["accent"], font=("Segoe UI", 10, "bold"), anchor="w").pack(fill="x", padx=4)
        self.routines = ttk.Treeview(left, columns=("name", "desc", "steps", "mod"), show="headings",
                                     style="Studio.Treeview", selectmode="extended")
        for col, text, w in (("name", "Rutina", 200), ("desc", "Descriere", 260), ("steps", "Pasi", 50),
                             ("mod", "Modificata", 120)):
            self.routines.heading(col, text=text)
            self.routines.column(col, width=w, stretch=col in ("name", "desc"))
        self.routines.pack(fill="both", expand=True, padx=4, pady=4)
        self.routines.bind("<Double-1>", lambda e: self.open_selected())
        row = tk.Frame(left, bg=C["bg_main"])
        row.pack(fill="x", padx=4, pady=(0, 6))
        b(row, "Deschide in Studio", self.open_selected).pack(side="left", padx=2)
        b(row, "▶ Ruleaza", self.run_selected, color=C["success"]).pack(side="left", padx=2)
        b(row, "➕ Adauga in pregatire  →", self.add_selected, color=C["primary"]).pack(side="right", padx=2)

        # ── dreapta: pregatirea ──
        right = tk.Frame(paned, bg=C["bg_card"])
        paned.add(right, weight=3)
        head = tk.Frame(right, bg=C["bg_card"])
        head.pack(fill="x", padx=6, pady=(6, 2))
        tk.Label(head, text="Pregatire", bg=C["bg_card"], fg=C["accent"],
                 font=("Segoe UI", 10, "bold")).pack(side="left")
        self.prep_combo = ttk.Combobox(head, state="readonly", width=34, style="Studio.TCombobox")
        self.prep_combo.pack(side="left", padx=6)
        self.prep_combo.bind("<<ComboboxSelected>>", lambda e: self.load_selected_prep())
        b(head, "Noua", self.new_prep).pack(side="left", padx=2)
        b(head, "💾 Salveaza", self.save_prep, color=C["primary"]).pack(side="left", padx=2)

        form = tk.Frame(right, bg=C["bg_card"])
        form.pack(fill="x", padx=6)
        tk.Label(form, text="Nume", bg=C["bg_card"], fg=C["text_dim"], font=("Segoe UI", 9)).grid(row=0, column=0, sticky="w")
        self.name_var = tk.StringVar()
        tk.Entry(form, textvariable=self.name_var, **panel.editor._entry_style()).grid(row=0, column=1, sticky="we", pady=2)
        tk.Label(form, text="Descriere", bg=C["bg_card"], fg=C["text_dim"], font=("Segoe UI", 9)).grid(row=1, column=0, sticky="w")
        self.desc_var = tk.StringVar()
        tk.Entry(form, textvariable=self.desc_var, **panel.editor._entry_style()).grid(row=1, column=1, sticky="we", pady=2)
        tk.Label(form, text="Folder rezultate", bg=C["bg_card"], fg=C["text_dim"], font=("Segoe UI", 9)).grid(row=2, column=0, sticky="w")
        self.out_var = tk.StringVar()
        out_row = tk.Frame(form, bg=C["bg_card"])
        out_row.grid(row=2, column=1, sticky="we", pady=2)
        tk.Entry(out_row, textvariable=self.out_var, **panel.editor._entry_style()).pack(side="left", fill="x", expand=True)
        b(out_row, "📁", self.choose_output).pack(side="left", padx=2)
        form.columnconfigure(1, weight=1)
        self.video_var, self.report_var = tk.BooleanVar(value=True), tk.BooleanVar(value=True)
        for text, var in (("🎥 Film pentru fiecare rutina", self.video_var),
                          ("📊 Raport Excel pentru fiecare rutina", self.report_var)):
            tk.Checkbutton(right, text=text, variable=var, bg=C["bg_card"], fg=C["text"], selectcolor=C["bg_input"],
                           activebackground=C["bg_card"], font=("Segoe UI", 9), anchor="w").pack(fill="x", padx=6)

        self.items = ttk.Treeview(right, columns=("on", "name", "err"), show="headings", style="Studio.Treeview",
                                  selectmode="browse")
        for col, text, w in (("on", "Ruleaza", 60), ("name", "Rutina", 260), ("err", "La eroare", 130)):
            self.items.heading(col, text=text)
            self.items.column(col, width=w, stretch=col == "name")
        self.items.pack(fill="both", expand=True, padx=6, pady=4)
        self.items.bind("<Double-1>", lambda e: self.toggle_item("enabled"))
        row = tk.Frame(right, bg=C["bg_card"])
        row.pack(fill="x", padx=6)
        b(row, "▲", lambda: self.move(-1)).pack(side="left", padx=1)
        b(row, "▼", lambda: self.move(1)).pack(side="left", padx=1)
        b(row, "Ruleaza / Omite", lambda: self.toggle_item("enabled")).pack(side="left", padx=1)
        b(row, "Opreste / Continua la eroare", lambda: self.toggle_item("stop_on_error")).pack(side="left", padx=1)
        b(row, "✕", self.remove_item).pack(side="left", padx=1)
        tk.Label(right, text="Rutinele ruleaza una dupa alta, cu intrebarile si sistemul de preventie ca la o rulare "
                             "normala. La final: un folder cu rezumatul Excel, documentatia (Documentatie.html), "
                             "rapoartele si filmele fiecarei rutine.", bg=C["bg_card"], fg=C["text_dim"],
                 font=("Segoe UI", 8), wraplength=480, justify="left").pack(fill="x", padx=6, pady=4)
        b(right, "▶ Ruleaza pregatirea", self.run_prep, color=C["success"]).pack(anchor="e", padx=6, pady=(0, 8))

        self.status = tk.Label(self, text="", bg=C["bg_main"], fg=C["text_dim"], font=("Segoe UI", 9), anchor="w")
        self.status.pack(fill="x", padx=12, pady=(0, 8))
        if self.lib.scanned_at is None or os.path.normcase(self.lib.folder) != os.path.normcase(self.folder_var.get()):
            self.refresh()
        else:
            self._fill()
        self.new_prep()

    # ── folderul rutinelor ──
    def _startfile(self, path):
        try:
            os.makedirs(path, exist_ok=True)
            os.startfile(path)  # type: ignore[attr-defined]
        except Exception as ex:  # noqa: BLE001
            self.status.configure(text=str(ex))

    def choose_folder(self):
        d = filedialog.askdirectory(parent=self, title="Folderul rutinelor", initialdir=self.folder_var.get())
        if not d:
            return
        st = self.p.studio_settings
        st.routines_folder = os.path.normpath(d)
        st.save()
        self.folder_var.set(st.effective_routines_folder())
        self.refresh()

    def refresh(self):
        self.lib.scan(self.folder_var.get())
        self._fill()

    def _fill(self):
        self.routines.delete(*self.routines.get_children())
        base = self.folder_var.get()
        for i, r in enumerate(self.lib.routines):
            rel = os.path.relpath(r.path, base) if r.path.lower().startswith(base.lower()) else r.path
            sub = os.path.dirname(rel)
            name = (f"{sub}\\" if sub else "") + r.name
            desc = ("⚠ " + r.error) if r.error else r.description.replace("\n", " ")
            self.routines.insert("", "end", iid=str(i), values=(name, desc[:120], r.steps, f"{r.modified:%d.%m.%Y %H:%M}"))
        names = [os.path.basename(p)[:-len(PREP_EXT)] for p in self.lib.preparations]
        self.prep_combo.configure(values=names)
        self.status.configure(text=f"{len(self.lib.routines)} rutine si {len(self.lib.preparations)} pregatiri in folder.")

    def _selected_routines(self):
        return [self.lib.routines[int(i)] for i in self.routines.selection() if int(i) < len(self.lib.routines)]

    def open_selected(self):
        sel = self._selected_routines()
        if sel:
            self.p.open_routine(sel[0].path)
            self.p.winfo_toplevel().lift()

    def run_selected(self):
        sel = self._selected_routines()
        if not sel or self.p.busy:
            return
        self.p.open_routine(sel[0].path)
        if self.p.routine_path and os.path.normcase(self.p.routine_path) == os.path.normcase(sel[0].path):
            self.destroy()
            self.p.run()

    # ── pregatirea ──
    def new_prep(self):
        self.prep = Preparation()
        self.prep_combo.set("")
        self._show_prep()

    def load_selected_prep(self):
        i = self.prep_combo.current()
        if i < 0 or i >= len(self.lib.preparations):
            return
        try:
            self.prep = Preparation.load(self.lib.preparations[i])
        except Exception as ex:  # noqa: BLE001
            messagebox.showerror("Pregatire", f"Pregatirea nu poate fi citita:\n{ex}", parent=self)
            return
        self._show_prep()

    def _show_prep(self):
        p = self.prep
        self.name_var.set(p.name)
        self.desc_var.set(p.description)
        self.out_var.set(p.output_folder)
        self.video_var.set(p.video)
        self.report_var.set(p.report)
        self._fill_items()

    def _fill_items(self, select: Optional[int] = None):
        self.items.delete(*self.items.get_children())
        for i, it in enumerate(self.prep.items):
            path = self.prep.resolve(it)
            exists = os.path.isfile(path)
            entry = self.lib.find(path)
            name = (entry.name if entry else it.name) + ("" if exists else "  ⚠ lipseste")
            self.items.insert("", "end", iid=str(i), values=("✔" if it.enabled else "—", name,
                                                             "opreste" if it.stop_on_error else "continua"))
        if select is not None and 0 <= select < len(self.prep.items):
            self.items.selection_set(str(select))

    def _collect(self):
        p = self.prep
        p.name = self.name_var.get().strip() or "Pregatire"
        p.description = self.desc_var.get().strip()
        p.output_folder = self.out_var.get().strip().strip('"')
        p.video, p.report = self.video_var.get(), self.report_var.get()

    def choose_output(self):
        d = filedialog.askdirectory(parent=self, title="Folderul rezultatelor pregatirii")
        if d:
            self.out_var.set(os.path.normpath(d))

    def add_selected(self):
        sel = self._selected_routines()
        if not sel:
            self.status.configure(text="Alege una sau mai multe rutine din stanga.")
            return
        self._collect()
        if not self.prep.path:   # caile se salveaza relativ la fisierul pregatirii (folderul rutinelor)
            self.prep.path = os.path.join(self.folder_var.get(), self._file_name())
        for r in sel:
            self.prep.items.append(PrepItem(self.prep.relative(r.path)))
        self._fill_items(len(self.prep.items) - 1)

    def _file_name(self) -> str:
        from rpr.model import sanitize_name
        return (sanitize_name(self.name_var.get().strip()) or "Pregatire") + PREP_EXT

    def _sel_item(self) -> int:
        s = self.items.selection()
        return int(s[0]) if s else -1

    def move(self, d: int):
        i = self._sel_item()
        j = i + d
        if i < 0 or not 0 <= j < len(self.prep.items):
            return
        items = self.prep.items
        items[i], items[j] = items[j], items[i]
        self._fill_items(j)

    def toggle_item(self, attr: str):
        i = self._sel_item()
        if i < 0:
            return
        it = self.prep.items[i]
        setattr(it, attr, not getattr(it, attr))
        self._fill_items(i)

    def remove_item(self):
        i = self._sel_item()
        if i >= 0:
            del self.prep.items[i]
            self._fill_items(min(i, len(self.prep.items) - 1))

    def save_prep(self) -> bool:
        self._collect()
        if not self.prep.items:
            messagebox.showinfo("Pregatire", "Adauga cel putin o rutina (din stanga).", parent=self)
            return False
        target = os.path.join(self.folder_var.get(), self._file_name())
        old = self.prep.path
        if old and os.path.normcase(os.path.abspath(old)) != os.path.normcase(os.path.abspath(target)):
            # pregatire redenumita / mutata: caile relative raman corecte fata de noul fisier
            for it in self.prep.items:
                it.path = self.prep.resolve(it)
            self.prep.path = target
            for it in self.prep.items:
                it.path = self.prep.relative(it.path)
        try:
            self.prep.save(target)
        except Exception as ex:  # noqa: BLE001
            messagebox.showerror("Pregatire", f"Nu am putut salva:\n{ex}", parent=self)
            return False
        self.refresh()
        name = os.path.basename(target)[:-len(PREP_EXT)]
        if name in self.prep_combo.cget("values"):
            self.prep_combo.set(name)
        self.status.configure(text=f"Pregatirea a fost salvata: {target}")
        return True

    def run_prep(self):
        if self.p.busy:
            self.status.configure(text="O rutina ruleaza deja.")
            return
        if not self.save_prep():
            return
        missing = [it.name for it in self.prep.items if it.enabled and not os.path.isfile(self.prep.resolve(it))]
        if missing and not messagebox.askyesno(
                "Pregatire", "Lipsesc rutinele:\n" + "\n".join(missing) + "\n\nContinui fara ele?", parent=self):
            return
        n = sum(1 for it in self.prep.items if it.enabled)
        if not messagebox.askyesno("Pregatire", f"Rulez {n} rutine una dupa alta?\n\nPoate dura mult. Pauza / STOP "
                                                "din bara plutitoare (Ctrl+F11 / Ctrl+F12).", parent=self):
            return
        prep = self.prep
        self.destroy()
        self.p.run_preparation(prep)
