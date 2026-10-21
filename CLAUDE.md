# AutoPilot DC — note pentru Claude

Tool RPA + Data Cleansing: recorder/player de pași desktop și browser, plus **Studio RPR** (rutine pe obiecte Web / SAP GUI / Desktop + Excel, fără cod, în stilul SilkTest). Două variante în același repo.

## Care variantă
- **Python (`AutoPilotDC_py/`) e varianta principală.** Are tot ce avea C#, inclusiv Studio RPR, drivere Web (Playwright), SAP GUI și Desktop, biblioteca de obiecte, programarea, limbile RO/EN/DE.
- **C# (`AutoPilotDC_C#/`)** urmează să fie abandonat după testare. Nu adăuga funcții noi acolo fără cerere explicită.
- Fișierele `.rpr.json` și `obiecte.json` sunt identice între variante. Nu le schimba formatul într-o singură parte.

## Comenzi (Python)
- Instalare pe un PC: `AutoPilotDC_py\INSTALEAZA.bat`; verificare: `python verifica_instalare.py`
- Pornire: `AutoPilot_DC.pyw` (fără consolă); erorile în `loguri/autopilot_console.log`
- Teste: `cd AutoPilotDC_py && python -m unittest discover -s tests` (unele teste cer Windows; pe Linux unele cad)
- Rulare rutină fără interfață: `py -m rpr run "rutina.rpr.json"`
- Versiune: `AutoPilotDC_py/version.py` (sursă unică) + intrare în `AutoPilotDC_py/CHANGELOG.md`

## Hartă (Python)
`AutoPilot_DC_app.py` (recorder/player, customtkinter) · `studio_ui.py` (Studio RPR) · `rpr/` (motorul: pași, condiții, bucle, variabile, Excel, drivere) · `autopilot_safety.py` (Nu deranja, chenar RUN/REC, prevenție) · `app_shell.py` (icon, tray, pornire cu Windows) · `i18n/` + `i18n.py` · `instructions_ui.py` (tab Instrucțiuni) · `docs/`
Fișiere vechi păstrate doar ca referință: `AutoPilot_DCv3.9_RedCursor.py`, `apply_patches_v4.py`, `autopilot_dc_setup_refactoration.py`, `0. Prompt_*`.

## Reguli
- Fără `.exe`: Python pornit cu `pythonw`, tray, pornire cu Windows. Nu trebuie să interfereze cu alte aplicații Python pornite.
- Sistemul de prevenție (v4.1) rămâne activ pe orice cale nouă de rulare: mai bine pauză și întrebare decât un click în locul greșit.
- Orice text nou trece prin i18n în RO/EN/DE și, dacă e o procedură, în tab-ul Instrucțiuni.
- Integrare planificată cu ScreenPilot (de aceea varianta principală e în Python).
- Comentarii, documentație și commit-uri în română.
- Documentație vizibilă: fără numele angajatorului, e-mailuri de firmă, ID-uri sau numere interne.

## Context comun
Prezentarea proiectelor și lista de erori/modificări sunt în două Google Docs: **PROIECTE_CONTEXT (live)** și **MODIFICARI_PROIECTE (live)** — citește doar secțiunea AutoPilot DC. Ce s-a implementat și confirmat se șterge din MODIFICARI.

## Când se actualizează fișierul
În același commit, când se schimbă comenzile de instalare/pornire/test, structura, formatul `.rpr.json`, decizia despre varianta C# sau când un defect scoate la iveală o regulă de ținut minte. Nu pentru funcții obișnuite. Sub ~60 de rânduri.
