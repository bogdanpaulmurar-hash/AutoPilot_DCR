# AutoPilot DC — note pentru Claude

Reguli generale (v1.1; textul complet: repo `dev-framework`, GLOBAL_RULES.md):
- Răspunde în română, scurt; rezultatul primul; spune ce nu ai putut verifica.
- Lucrează în etape mici: citește doar ce trebuie (caută, apoi deschide porțiunea), scrie doar funcțiile modificate, plan de 3–5 rânduri înainte de schimbări mari.
- După fiecare etapă rulează testele proiectului și notează în CHANGELOG.md.
- Parolele și cheile stau în keyring sau variabile de mediu; documentația vizibilă omite numele angajatorului, e-mailurile de firmă, ID-urile și numerele interne.
- Aplicații Windows: Python cu `pythonw`, tray, fără `.exe`; respectă DevPilot (`DEVPILOT_MANAGED`, `DEVPILOT_SUPPRESS`).
- Git: GitHub e sursa de adevăr; un singur laptop o dată; commit și push înainte de schimbarea laptopului; lasă Drive să termine sincronizarea.

Tool RPA + Data Cleansing: recorder/player de pași desktop și browser, plus **Studio RPR** (rutine pe obiecte Web / SAP GUI / Desktop + Excel, fără cod, în stilul SilkTest). Doar varianta Python (`AutoPilotDC_py/`); varianta C# a fost scoasă în v4.25.0 (rămâne în istoricul git).

## Formatul fișierelor
- `.rpr.json`, `obiecte.json` și `.pregatire.json` sunt doar ale aplicației Python; formatul se poate extinde, dar rutinele și bibliotecile vechi trebuie să se deschidă în continuare (câmpuri noi opționale, cu valori implicite).

## Comenzi (Python)
- Instalare pe un PC: `AutoPilotDC_py\INSTALEAZA.bat`; verificare: `python verifica_instalare.py`
- Pornire: `AutoPilot_DC.pyw` (fără consolă); erorile în `loguri/autopilot_console.log`
- Teste: `cd AutoPilotDC_py && python -m unittest discover -s tests` (unele teste cer Windows; pe Linux unele cad)
- Rulare rutină fără interfață: `py -m rpr run "rutina.rpr.json"` (sau o pregătire: `"Nume.pregatire.json"`)
- Versiune: `AutoPilotDC_py/version.py` (sursă unică) + intrare în `AutoPilotDC_py/CHANGELOG.md`

## Hartă (Python)
`AutoPilot_DC_app.py` (fereastra principală = Studio; ⏺ Ecran înregistrează mouse/tastatură în pași pe ecran; ⚙ Setări aplicație; tray) · `studio_ui.py` (Studio RPR) · `import_ui.py` + `rpr/importer.py` (📥 Import AI: pași în text/JSON → rutină) + `complete_ui.py` (🎯 Completează obiectele pe pagina reală) · `studio_views.py` (bara de activități, tab-uri, cronologia, ecranul Excel, fluxul) · `rpr/` (motorul: pași, condiții, bucle, variabile, Excel, drivere; `report.py` raportul Excel al rulării, `template.py` 📤 șablonul Excel al buclei (Id ca text + coloanele scrise), `batch.py` managerul de rutine și pregătirile, `resume.py` reluarea după o închidere neașteptată, `scan.py` scanarea site-ului și biblioteca pe aplicație, `locations.py` folderul comun / unde se salvează) · `routine_manager_ui.py` (📂 Manager rutine) · `autopilot_safety.py` (Nu deranja, chenar RUN/REC, prevenție) · `ui_theme.py` (mărimea textului, contrast, ferestre care încap pe ecran) · `app_shell.py` (icon, tray, pornire cu Windows) · `i18n/` + `i18n.py` · `instructions_ui.py` (📖 Instrucțiuni, F1) · `docs/`
Fișiere vechi păstrate doar ca referință: `AutoPilot_DCv3.9_RedCursor.py`, `apply_patches_v4.py`, `autopilot_dc_setup_refactoration.py`, `0. Prompt_*`.

## Reguli
- Fără `.exe`: Python pornit cu `pythonw`, tray, pornire cu Windows. Nu trebuie să interfereze cu alte aplicații Python pornite.
- Sistemul de prevenție (v4.1) rămâne activ pe orice cale nouă de rulare: mai bine pauză și întrebare decât un click în locul greșit.
- Orice text nou trece prin i18n în RO/EN/DE și, dacă e o procedură, în Instrucțiuni (`docs/instructiuni`). Nu mai există tab-ul Recorder: funcțiile noi intră în Studio.
- Integrare planificată cu ScreenPilot (de aceea varianta principală e în Python).
- Comentarii, documentație și commit-uri în română.
- Documentație vizibilă: fără numele angajatorului, e-mailuri de firmă, ID-uri sau numere interne.

## Context comun
Prezentarea proiectelor și lista de erori/modificări sunt în două Google Docs: **PROIECTE_CONTEXT (live)** și **MODIFICARI_PROIECTE (live)** — citește doar secțiunea AutoPilot DC. Ce s-a implementat și confirmat se șterge din MODIFICARI.

## Când se actualizează fișierul
În același commit, când se schimbă comenzile de instalare/pornire/test, structura, formatul `.rpr.json`, sau când un defect scoate la iveală o regulă de ținut minte. Nu pentru funcții obișnuite. Sub ~60 de rânduri.
