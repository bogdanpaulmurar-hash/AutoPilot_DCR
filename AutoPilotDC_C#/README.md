# AutoPilot DC v4 — Studio RPR (nou)

Versiunea 4 adaugă **Studio RPR**: automatizare pe **obiecte** (nu pe coordonate), în stilul SilkTest,
pentru **web (Playwright / Selenium)**, **SAP GUI** și **aplicații desktop Windows**, combinate cu **Excel** — fără cod.

- **Spy**: marchezi elementele o singură dată (contur pe ecran), cu locatori multipli și self-healing.
- **Rutine vizuale**: Click, Scrie, Citește, Așteaptă, Dacă/Altfel, Repetă, Pentru fiecare rând Excel, Încearcă/La eroare, Întrebare — configurate din liste.
- **Rulare**: elementul e marcat înainte de fiecare acțiune; Pas cu pas, Pauză, Stop (Ctrl+F11 / Ctrl+F12), log exportabil în Excel.
- **Recorder web**: click-urile din browser devin pași reali + obiecte.
- **Programare**: Windows Task Scheduler (`AutoPilotDC.UI.exe --run rutina.rpr.json`).
- **5 rutine exemplu** și ghid complet pas cu pas: [`docs/GHID_STUDIO_RPR.md`](docs/GHID_STUDIO_RPR.md) (și în aplicație: ❓ Ghid / F1).

Pornire: `Start_AutoPilotDC.bat` (sau build `AutoPilotDC.sln` → rulează `AutoPilotDC.UI`) → butonul **🧩 Studio RPR**.

**v4.1 — siguranța la rulare** (recorder/player și Studio): „Nu deranja” cât timp rulează,
chenar roșu RUN / verde REC / portocaliu PAUZA, sistem de prevenție (pauză + întrebare când
ecranul diferă de înregistrare, la ferestre de eroare, erori SAP, valori diferite). Detalii în
[`../README.md`](../README.md) și în ghid, capitolul 10b. Cod: `AutoPilotDC.Infrastructure/Safety/`,
`Services/DoNotDisturb.cs`, `UI/Overlays/RunFrame.cs`, `UI/Studio/StudioGuard.cs`.

Proiecte noi:

```
AutoPilotDC.Rpr/             # nucleul: model rutina (arbore), Object Repository, conditii, variabile, motor, Excel
AutoPilotDC.Drivers.Web/     # Playwright (Spy + Recorder + iframe-uri) si Selenium, acelasi contract IUiDriver
AutoPilotDC.Drivers.Windows/ # Desktop (FlaUI / UI Automation) si SAP GUI Scripting (COM)
AutoPilotDC.UI/Studio/       # editorul vizual (arbore, proprietati, Spy, rulare, ghid, exemple)
docs/GHID_STUDIO_RPR.md      # instructiuni pas cu pas
```

Testele motorului: `AutoPilotDC.Tests/Unit/RprEngineTests.cs` (`dotnet test`).

---

# AutoPilot DC v3.9 — C# WPF .NET 8 Migration

**Autor:** Bogdan Murar (Z003FU5C) — Siemens AG
**Sursa:** Python v3.9 (AutoPilot_DCv3.9.txt)
**Target:** C# WPF .NET 8 + Playwright

---

## Structura Solution

```
AutoPilotDC.sln
├── AutoPilotDC.Models/        # StepModel, LogEntry, AppSettings, RoutineFile
├── AutoPilotDC.Core/          # Interfete + Exceptii
├── AutoPilotDC.Infrastructure/ # Engines, Repos, Services (Faza 2)
├── AutoPilotDC.Application/   # RecorderService, PlayerService (Faza 3-4)
├── AutoPilotDC.Playwright/    # Browser automation (Faza 6)
├── AutoPilotDC.UI/            # WPF MainWindow + Overlays (Faza 5)
└── AutoPilotDC.Tests/         # Unit + Integration tests (Faza 7)
```

## Faze completate

- [x] **Faza 0** — Analiza completa Python v3.9 (31 features inventariate)
- [x] **Faza 1** — Solution Setup + Models + Interfete + AppConstants

## Reguli critice

- `extracted_value` (NU `actual_value`)
- JSON keys sunt `snake_case` (compatibilitate Python)
- Shortcut-uri default: F5/F6/F7/F8/F9/F12
- `question_buttons` default = `"Continua,Opreste,Sari"`
- ALL_STEP_TYPES = 10 desktop + 7 browser = 17 total
- Simulator (`SimulateStepAsync`) prezent in Tab Recorder SI Tab Step Builder
- Culoare buton Simuleaza: `#6A5ACD` (Slate Blue)

## Cum deschizi

1. Deschide `AutoPilotDC.sln` in Visual Studio 2022+
2. Build Solution (Ctrl+Shift+B)
3. Ruleaza testele: `dotnet test`

## Dependinte (se adauga in fazele urmatoare)

- Faza 2: `ClosedXML` (Excel), `Serilog`
- Faza 5: WPF (.NET 8 Windows)
- Faza 6: `Microsoft.Playwright`
- Faza 7: `xunit`, `Moq`