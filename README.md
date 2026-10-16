# AutoPilot DC (AutoPilot_DCR)

Tool de automatizare RPA & Data Cleansing (recorder/player de pași desktop +
browser), dezvoltat în două variante:

| Variantă | Folder | Stare |
|---|---|---|
| **Python** (CustomTkinter + pynput + pyautogui) | [`AutoPilotDC_py/`](AutoPilotDC_py) | Recorder/player pe coordonate + siguranța la rulare v4.1 |
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

## AutoPilotDC_py (Python)

**Pornirea aplicației (mereu aceeași):** `AutoPilotDC_py\AutoPilot_DC.pyw` sau scurtătura „AutoPilot DC” de pe Desktop. Ce e nou în fiecare versiune: [`AutoPilotDC_py/CHANGELOG.md`](AutoPilotDC_py/CHANGELOG.md).

- **`INSTALEAZA.bat` — o singură dată pe fiecare calculator (dublu click).** Găsește Python,
  instalează toate pachetele (fără drepturi de administrator, cu reîncercare pentru rețeaua
  firmei), verifică fiecare pachet și poate crea scurtătura pe Desktop. Fereastra rămâne
  deschisă până apeși o tastă, ca să vezi dacă a mers.
- **`AutoPilot_DC.pyw` — fișierul de pornire (dublu click), fără fereastră de consolă.**
  Dacă lipsesc pachete, oferă butonul **„Instalează acum”** (pornește `INSTALEAZA.bat` pentru
  exact Python-ul care deschide aplicația); erorile se scriu în `loguri/autopilot_console.log`.
- `studio_ui.py` — **Studio RPR** (editorul vizual), deschis din comutatorul din bara de sus.
- `rpr/` — motorul Studio RPR: rutine pe obiecte (pași ca arbore,
  condiții, bucle, variabile, Excel, Încearcă/La eroare, sistemul de prevenție). Fișierele
  `.rpr.json` și `obiecte.json` sunt **identice cu cele din C#** (verificat pe cele 5 exemple).
  Rulare fără interfață: `py -m rpr run "rutina.rpr.json"`.
- `tests/` — testele motorului: `py -m unittest discover -s tests`.
- `app_shell.py` + `assets/` — **iconița aplicației**, **pornire cu Windows** și **pictograma din tray** (lângă ceas).
  Din **Setări → 🪟 Pornire și tray**: pornește cu Windows (opțional direct ascuns în tray), butonul ✕ ascunde
  aplicația în tray, „Creează scurtătură pe Desktop” — scurtătura pornește direct `pythonw.exe`, deci **niciodată
  fereastră CMD**, indiferent cum e asociat `.pyw` în Windows.
- `AutoPilot_DC_app.py` — aplicația principală (recorder + player pași
  desktop/mouse/tastatură cu `pynput`, GUI `customtkinter`). Pornită direct, deschide și consola.
- `autopilot_safety.py` — **v4.1**: Nu deranja, chenarul RUN/REC, sistemul de prevenție.
  Trebuie să fie în același folder cu aplicația.
- `AutoPilot_DCv3.9_RedCursor.py` — variantă veche cu overlay de cursor vizual
  (păstrată separat pentru comparație, **fără** funcțiile v4.1).
- `autopilot_dc_setup_refactoration.py`, `apply_patches_v4.py` — scripturi de
  refactorizare/patch folosite în dezvoltare.
- `playwrighttest.py` — script de test izolat pentru pașii de browser.
- `config.json` — configurație implicită a aplicației (shortcuts, delay-uri).

Pe un calculator nou:
1. Python 3.9+ instalat (python.org sau Company Portal), cu „Add python.exe to PATH”.
2. Dublu click pe **`INSTALEAZA.bat`** → la final „GATA” (și, opțional, scurtătura pe Desktop).
3. Dublu click pe **`AutoPilot_DC.pyw`** (sau pe scurtătura „AutoPilot DC”).

Starea migrării Studio RPR în Python:

| Etapa | Ce conține | Stare |
|---|---|---|
| 1 | Motorul + Excel + rulare din linie de comandă + teste | ✅ gata |
| 4 | Editorul vizual (Studio) în aplicație — comutatorul **🧩 Studio RPR** din bara de sus | ✅ gata (adus înainte, ca să-l poți vedea) |
| 2 | Driver Web (Playwright): acțiuni, Spy, înregistrare, iframe-uri (v4.4) | ✅ gata |
| 2b | **Biblioteca de obiecte** (ca SilkTest): site → pagină → container, test înainte de folosire, sisteme similare (v4.5) | ✅ gata |
| 3 | SAP GUI + aplicații desktop: drivere, Spy (F2), Test din Bibliotecă (v4.6) | ✅ gata |
| 3b | Programare automată (Windows Task Scheduler) din Studio, cu istoric (v4.6) | ✅ gata |
| 6 | **Limbi: română / engleză / germană** pentru toată interfața; limba se alege din Setări | după ce sunt gata toate funcțiile |
| 7 | **Tab nou „Instrucțiuni”** în toate cele 3 limbi: fiecare procedură explicată pe scurt, pas cu pas, cu exemple | la final |
| 5 | Renunțarea la versiunea C# | după testare |

Interfața Python v4.1: bara de sus are două rânduri — **comutatorul Recorder / Studio RPR** + STOP URGENȚĂ, apoi
butoane mici, grupate, specifice zonei deschise, care trec pe rândul următor când fereastra e îngustă.

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
