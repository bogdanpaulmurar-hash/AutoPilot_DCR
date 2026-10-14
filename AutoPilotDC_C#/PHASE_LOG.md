# AutoPilot DC — Migration Phase Log

## FAZA 0 — FREEZE ANALYSIS ✅
- 31 features inventariate (inclusiv Simulator pas)
- UI Map complet (8 tab-uri, toate overlays)
- StepModel spec complet (24 campuri)
- Execution flow documentat
- Data model map complet

## FAZA 1 — SOLUTION SETUP & MODELS ✅
**Fisiere generate:**
- AutoPilotDC.sln (7 proiecte)
- AutoPilotDC.Models/StepModel.cs
- AutoPilotDC.Models/LogEntry.cs
- AutoPilotDC.Models/AppSettings.cs
- AutoPilotDC.Models/RoutineFile.cs
- AutoPilotDC.Core/Interfaces/IAutomationEngine.cs
- AutoPilotDC.Core/Interfaces/IRecorder.cs
- AutoPilotDC.Core/Interfaces/IPlayer.cs (cu SimulateStepAsync)
- AutoPilotDC.Core/Interfaces/IRoutineRepository.cs
- AutoPilotDC.Core/Interfaces/ILogRepository.cs
- AutoPilotDC.Core/Interfaces/ISettingsManager.cs
- AutoPilotDC.Core/Exceptions/AutomationException.cs
- AutoPilotDC.UI/AppConstants.cs
- AutoPilotDC.Tests/Unit/StepModelTests.cs

**Validation Gate:** PASSED
- extracted_value (NU actual_value) ✅
- JSON snake_case keys ✅
- 17 AllStepTypes (10+7) ✅
- F5/F6/F7/F8/F9/F12 shortcuts ✅
- SimulateStepAsync in IPlayer ✅
- ColorSimulate = #6A5ACD ✅
- ModeSimulation = SIMULATION ✅
- Simulator in Tab Recorder SI Tab Step Builder ✅

**UI Change Log:**
- Butonul Simuleaza (#6A5ACD) adaugat in Tab Recorder langa Debug Pas
  (decizie: Bogdan Murar, confirmat inainte de Faza 1)

## FAZA 2 — INFRASTRUCTURE (urmatoarea)
- DesktopEngine.cs (Win32 API)
- SettingsManager.cs
- JsonRoutineRepository.cs
- JsonLogRepository.cs
- ExcelEngine.cs (ClosedXML)

## v4 — STUDIO RPR (automatizare pe obiecte)
- Motor nou `AutoPilotDC.Rpr`: rutina = arbore de pasi (Actiune, Asteapta, Daca/Altfel, Repeta,
  Pentru fiecare rand Excel, Scrie in Excel, Variabila, Intrebare, Incearca/La eroare, Grup, Log, Stop),
  conditii SI/SAU/NU, variabile {Rand.Coloana}, politici de eroare, reincercari, pauza / pas cu pas.
- Object Repository + Spy: Web (Playwright, iframe-uri), Selenium, SAP GUI Scripting, Desktop (FlaUI).
- Recorder web: actiunile din browser devin pasi pe obiecte.
- Studio WPF: toolbox, arbore, panou de proprietati fara cod, log, variabile, bara plutitoare de control.
- Rulare programata: `--run` + Windows Task Scheduler.
- Import rutine v3.9 (pasii browser devin obiecte; pasii pe coordonate raman compatibili).
- Lizibilitate: ComboBox cu sablon propriu (text deschis pe fundal deschis rezolvat), meniuri/tooltip-uri/
  liste in culorile temei, butoane cu contrast >= 4.5:1, text secundar mai lizibil, comutare tema reala.
- Erorile neprinse sunt afisate (nu mai sunt inghitite).
- Ghid pas cu pas (docs + in aplicatie) si 5 rutine exemplu.
