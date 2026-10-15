# -*- coding: utf-8 -*-
# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  AUTOPILOT DC v4.1 — pornire FARA fereastra de consola (CMD)                 ║
# ║  Dublu click pe acest fisier (extensia .pyw ruleaza cu pythonw.exe).          ║
# ╚══════════════════════════════════════════════════════════════════════════════╝
#
# Fara consola, mesajele de eroare nu s-ar vedea nicaieri. De aceea:
#   - pachetele lipsa sunt anuntate intr-o fereastra (cu comanda pip de rulat);
#   - tot ce ar fi aparut in consola se scrie in loguri/autopilot_console.log;
#   - o eroare la pornire apare intr-o fereastra, nu se pierde.

import os
import runpy
import sys
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
MAIN = os.path.join(HERE, "AutoPilot_DCv4.1.py")
LOG_DIR = os.path.join(HERE, "loguri")


def _message(title: str, text: str) -> None:
    """Fereastra proprie (messagebox-ul standard se inchide singur cu Tk 9 cand radacina e ascunsa)."""
    import tkinter as tk
    root = tk.Tk()
    root.title(title)
    root.configure(bg="#1E1E2E")
    root.resizable(False, False)
    root.attributes("-topmost", True)  # fara consola, mesajul ar putea aparea in spatele altor ferestre
    tk.Label(root, text="⚠  " + title, bg="#1E1E2E", fg="#FF8800",
             font=("Segoe UI", 13, "bold")).pack(anchor="w", padx=18, pady=(16, 6))
    box = tk.Text(root, width=72, height=min(14, text.count("\n") + 3), wrap="word",
                  bg="#2A2A3E", fg="#FFFFFF", font=("Consolas", 10), relief="flat", padx=8, pady=6)
    box.insert("1.0", text)
    box.configure(state="disabled")  # textul se poate selecta si copia (ex: comanda pip)
    box.pack(padx=18)
    tk.Button(root, text="OK", command=root.destroy, bg="#009999", fg="white", relief="flat",
              font=("Segoe UI", 11, "bold"), padx=24, pady=4, cursor="hand2").pack(pady=14)
    root.update_idletasks()
    w, h = root.winfo_reqwidth(), root.winfo_reqheight()
    root.geometry(f"+{(root.winfo_screenwidth() - w) // 2}+{(root.winfo_screenheight() - h) // 3}")
    root.focus_force()
    root.mainloop()


def main() -> None:
    # 1. Iesirea "de consola" merge intr-un fisier (sub pythonw, stdout/stderr sunt None)
    os.makedirs(LOG_DIR, exist_ok=True)
    log = open(os.path.join(LOG_DIR, "autopilot_console.log"), "a", encoding="utf-8", buffering=1)
    sys.stdout = sys.stderr = log

    # 2. Pachetele necesare
    missing = []
    for module, package in [("customtkinter", "customtkinter"), ("pynput", "pynput"),
                            ("pyautogui", "pyautogui"), ("openpyxl", "openpyxl"), ("PIL", "pillow")]:
        try:
            __import__(module)
        except ImportError:
            missing.append(package)
    if missing:
        # comanda exacta pentru Python-ul care deschide fisierele .pyw (pip poate fi al altui Python)
        exe = sys.executable
        if os.path.basename(exe).lower() == "pythonw.exe":
            exe = os.path.join(os.path.dirname(exe), "python.exe")
        _message("AutoPilot DC — lipsesc pachete",
                 "Lipsesc pachetele Python: " + ", ".join(missing) + "\n\n"
                 "Deschide PowerShell si ruleaza (poti copia de aici):\n\n"
                 f'& "{exe}" -m pip install ' + " ".join(missing) + "\n\n"
                 "apoi porneste din nou AutoPilot DC.")
        return

    # 3. Aplicatia (fisierul principal are un punct in nume -> se ruleaza dupa cale, nu prin import)
    sys.argv = [MAIN] + sys.argv[1:]
    try:
        runpy.run_path(MAIN, run_name="__main__")
    except SystemExit:
        pass
    except Exception:
        traceback.print_exc()
        _message("AutoPilot DC — eroare la pornire",
                 traceback.format_exc(limit=6) + "\n\nDetalii: loguri\\autopilot_console.log")


if __name__ == "__main__":
    main()
