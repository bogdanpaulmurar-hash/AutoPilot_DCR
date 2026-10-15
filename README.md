# AutoPilot DC (AutoPilot_DCR)

Tool de automatizare RPA & Data Cleansing (recorder/player de pași desktop +
browser), dezvoltat în două variante:

| Variantă | Folder | Stare |
|---|---|---|
| **Python** (CustomTkinter + pynput + pyautogui) | [`AutoPilotDC_v4.1_py/`](AutoPilotDC_v4.1_py) | Recorder/player pe coordonate + siguranța la rulare v4.1 |
| **C# WPF (.NET 8)** | [`AutoPilotDC_C#/`](AutoPilotDC_C%23) | Recorder/player + **Studio RPR** (rutine pe obiecte: Web/SAP/Desktop + Excel) + siguranța la rulare v4.1 |

## Ce e nou în v4.1 — siguranța la rulare (ambele variante)

| Funcție | Ce face |
|---|---|
| 🌙 **Nu deranja** | Cât timp rulează sau înregistrează o rutină, Windows nu mai afișează notificări (nu poți da click din greșeală pe ele, nu acoperă butoanele). La final notificările revin. Dacă aplicația e închisă forțat, revin la următoarea pornire. |
| 🟥 **Chenar RUN / REC** | Chenar **roșu** + „▶ RUN” în colțul din dreapta-sus la rulare, **verde** + „● REC” la înregistrare, **portocaliu** + „❚❚ PAUZA” cât timp rutina așteaptă decizia ta. Click-urile trec prin chenar, nu apare în capturi de ecran. |
| 🛡 **Sistem de prevenție** | Înainte de fiecare pas verifică dacă ecranul arată ca la înregistrare. Dacă nu, **pune rutina pe pauză și te întreabă** (Continuă / Nu mai verifica pasul / Sari pasul / Oprește). |

Ce detectează sistemul de prevenție:

1. ai mișcat mouse-ul în timpul rulării;
2. a apărut o fereastră de eroare / avertisment (titlu sau mesaj cu „Eroare”, „Error”, „Warning”, …);
3. aplicația nu răspunde („Not Responding”);
4. click-ul ar ajunge în **altă aplicație** decât la înregistrare;
5. zona din jurul click-ului **arată diferit** (alt ecran, popup peste buton, date diferite) — sensibilitate relaxed 35% / normal 22% / strict 12%;
6. tastele ar ajunge în altă fereastră decât la înregistrare;
7. un pas **eșuează** — înainte rutina mergea mai departe fără să spună nimic, acum te întreabă (cu „Reîncearcă pasul”);
8. *(doar Studio RPR)* SAP afișează o eroare în bara de stare (`E:` / `A:`) și **valoarea citită diferă de „Valoarea așteptată”** a pasului.

Pentru 4–6 rutina trebuie **înregistrată cu v4.1** (la înregistrare se salvează fereastra și amprenta zonei fiecărui click). Rutinele vechi primesc doar verificările 1–3 și 7. Amprenta e identică în Python și C#, deci o rutină înregistrată într-o variantă e verificată corect și în cealaltă.

Toate se pot opri din **Setări → 🛡 Siguranța la rulare** (în Studio RPR: **⚙ Rutina → Siguranța la rulare**).

## AutoPilotDC_v4.1_py (Python)

- **`AutoPilot_DC.pyw` — fișierul de pornire (dublu click), fără fereastră de consolă.**
  Dacă lipsesc pachete, afișează o fereastră cu comanda `pip` de rulat; erorile se scriu în
  `loguri/autopilot_console.log`.
- `AutoPilot_DCv4.1.py` — aplicația principală (recorder + player pași
  desktop/mouse/tastatură cu `pynput`, GUI `customtkinter`). Pornită direct, deschide și consola.
- `autopilot_safety.py` — **v4.1**: Nu deranja, chenarul RUN/REC, sistemul de prevenție.
  Trebuie să fie în același folder cu aplicația.
- `AutoPilot_DCv3.9_RedCursor.py` — variantă veche cu overlay de cursor vizual
  (păstrată separat pentru comparație, **fără** funcțiile v4.1).
- `autopilot_dc_setup_refactoration.py`, `apply_patches_v4.py` — scripturi de
  refactorizare/patch folosite în dezvoltare.
- `playwrighttest.py` — script de test izolat pentru pașii de browser.
- `config.json` — configurație implicită a aplicației (shortcuts, delay-uri).

Rulare:
```powershell
cd AutoPilotDC_v4.1_py
pip install customtkinter pynput pyautogui openpyxl pillow
```
Apoi dublu click pe **`AutoPilot_DC.pyw`** (sau `pythonw AutoPilot_DC.pyw`). Pentru o
scurtătură pe Desktop: click dreapta pe `AutoPilot_DC.pyw` → *Send to* → *Desktop (create shortcut)*.

## AutoPilotDC_C# (C# WPF .NET 8)

Pornire (nu e nevoie de Visual Studio, doar de [.NET SDK 8 sau mai nou](https://dotnet.microsoft.com/download)):

```powershell
cd AutoPilotDC_C#
.\Start_AutoPilotDC.bat
```

Scriptul compilează în `%LOCALAPPDATA%\AutoPilotDC_build` (în afara Google Drive,
care blochează fișierele `.exe`) și pornește aplicația. Studio RPR se deschide din
butonul **🧩 Studio RPR** din bara de sus.

Alternativ: `AutoPilotDC_C#/AutoPilotDC.sln` în Visual Studio 2022+ → proiectul de
start `AutoPilotDC.UI` → F5.

Detalii: [`AutoPilotDC_C#/README.md`](AutoPilotDC_C%23/README.md),
ghidul Studio [`AutoPilotDC_C#/docs/GHID_STUDIO_RPR.md`](AutoPilotDC_C%23/docs/GHID_STUDIO_RPR.md),
fazele migrării [`AutoPilotDC_C#/PHASE_LOG.md`](AutoPilotDC_C%23/PHASE_LOG.md).

Teste: `dotnet test AutoPilotDC_C#/AutoPilotDC.Tests` (testele de integrare Playwright
cer browserele instalate cu `playwright install`).

## Note

- Fișierele de build (`bin/`, `obj/`, `.vs/`), publish-urile self-contained,
  arhivele cu versiuni vechi și export-urile de cod generate pentru AI nu sunt
  incluse în acest repository (erau de ordinul GB și nu fac parte din codul
  sursă funcțional).
- „Nu deranja” nu are un API oficial în Windows: aplicația scrie profilul
  „Priority only” în setarea Windows (CloudStore) și repornește serviciul de
  notificări al utilizatorului (fără drepturi de administrator). Dacă pe un
  calculator nu funcționează, chenarul și sistemul de prevenție rămân active
  (o notificare apărută peste zona unui click e prinsă de verificarea 5).
