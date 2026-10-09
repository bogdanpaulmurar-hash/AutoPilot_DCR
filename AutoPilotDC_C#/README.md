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