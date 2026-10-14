# AutoPilot DC (AutoPilot_DCR)

Tool de automatizare RPA & Data Cleansing (recorder/player de pași desktop +
browser), dezvoltat în două variante:

| Variantă | Folder | Stare |
|---|---|---|
| **Python** (CustomTkinter + pynput + Playwright) | [`AutoPilotDC_v3.9_py/`](AutoPilotDC_v3.9_py) | Versiunea curentă, mai stabilă/funcțională |
| **C# WPF (.NET 8)** | [`AutoPilotDC_C#/`](AutoPilotDC_C%23) | v4: Studio RPR — rutine pe obiecte (Web/SAP/Desktop + Excel), Spy, ghid pas cu pas |

## AutoPilotDC_v3.9_py (Python)

- `AutoPilot_DCv3.9.py` — aplicația principală (recorder + player pași
  desktop/mouse/tastatură cu `pynput`, pași de browser cu `Playwright`, GUI
  `customtkinter`).
- `AutoPilot_DCv3.9_RedCursor.py` — variantă cu overlay de cursor vizual
  (~2% diff față de principal, păstrată separat pentru comparație).
- `autopilot_dc_setup_refactoration.py`, `apply_patches_v4.py` — scripturi de
  refactorizare/patch folosite în dezvoltare.
- `playwrighttest.py` — script de test izolat pentru pașii de browser.
- `config.json` — configurație implicită a aplicației (shortcuts, delay-uri).

Rulare:
```powershell
pip install customtkinter pynput playwright pyautogui
python -m playwright install chromium
python AutoPilot_DCv3.9.py
```

## AutoPilotDC_C# (C# WPF .NET 8)

Migrare pe straturi (`Core` / `Models` / `Infrastructure` / `Application` /
`Playwright` / `UI` / `Tests`) — vezi [`AutoPilotDC_C#/README.md`](AutoPilotDC_C%23/README.md)
și [`AutoPilotDC_C#/PHASE_LOG.md`](AutoPilotDC_C%23/PHASE_LOG.md) pentru detalii
despre fazele de migrare completate.

Deschide `AutoPilotDC_C#/AutoPilotDC.sln` în Visual Studio 2022+ și fă Build
Solution.

## Note

- Fișierele de build (`bin/`, `obj/`, `.vs/`), publish-urile self-contained,
  arhivele cu versiuni vechi și export-urile de cod generate pentru AI nu sunt
  incluse în acest repository (erau de ordinul GB și nu fac parte din codul
  sursă funcțional).
