# -*- coding: utf-8 -*-
# AutoPilot DC v4.1 — verifica daca toate pachetele Python sunt instalate.
# Folosit de INSTALEAZA.bat; se poate rula si separat:  py verifica_instalare.py
import importlib.util
import sys

PACHETE = [
    ("customtkinter", "interfata aplicatiei"),
    ("pynput", "inregistrare mouse / tastatura"),
    ("pyautogui", "redare pasi"),
    ("openpyxl", "Excel"),
    ("PIL", "capturi de ecran (pillow)"),
    ("pystray", "pictograma langa ceas (tray)"),
    ("playwright", "Studio: Web"),
    ("win32com", "Studio: SAP GUI (pywin32)"),
    ("uiautomation", "Studio: aplicatii desktop"),
]

lipsa = 0
for modul, rol in PACHETE:
    ok = importlib.util.find_spec(modul) is not None
    lipsa += not ok
    print(f"   {'OK      ' if ok else 'LIPSESTE'}  {modul:<14} {rol}")
print(f"\n   Python {sys.version.split()[0]}  ({sys.executable})")
sys.exit(1 if lipsa else 0)
