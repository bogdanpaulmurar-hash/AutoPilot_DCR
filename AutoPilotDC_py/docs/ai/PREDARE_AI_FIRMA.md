# 🤖 Asistent AI — predare pentru Claude-ul din rețeaua firmei

Citește întâi `CLAUDE.md` din rădăcina repo-ului (regulile proiectului). Acest fișier spune ce s-a făcut în afara rețelei firmei (v4.24.0) și ce rămâne de verificat acolo, unde există acces la AI. Documentația pentru utilizator: `docs/instructiuni/ro.md`, capitolul 34.

## Ce există
- `rpr/assistant.py`: motorul, fără Tk și fără pachete noi (doar `urllib`).
  - `AiSettings`: setările în `%APPDATA%\AutoPilotDC\asistent_ai.json` (fără cheie). Cheia: variabila de mediu (implicit `AUTOPILOT_AI_KEY`), altfel `keyring` (serviciul `AutoPilotDC-AI`), dacă e instalat.
  - `AiClient`: `provider="anthropic"` (Messages API, `x-api-key`, `anthropic-version`) sau `provider="openai"` (`/chat/completions`, `Authorization: Bearer`, sau `api-key` pentru Azure). O adresă care conține deja `/chat/completions` sau se termină în `/messages` e folosită exact cum e scrisă.
  - `ask()`: întrebare cu context: capitolele potrivite din Instrucțiuni (max ~18.000 caractere), schița rutinei, obiectele ei cu locatoare și ultimele 8 erori/avertismente.
  - `make_routine()`: procedură → `ai_prompt()` → `StepImporter`; dacă sunt erori, AI-ul le primește înapoi (`MAX_REPAIRS = 2`).
  - `repair_routine()` + `prepare_repair()` / `RepairJob.finish()`: rutină existentă → text (`rpr/steps_text.py`) → AI → import. Pașii fără comandă text devin `PASTREAZA #n` / `KEEP #n` și revin identici. Rândurile neschimbate își recapătă setările. Variabilele cu nume de parolă/cheie pleacă drept `***`.
- `assistant_ui.py`: fereastra 🤖 (tab-urile Întreabă / Fă rutina / Repară rutina, ⚙ Conexiune). Cererile rulează pe un fir separat. Rezultatele intră în `import_ui.ImportDialog.set_text(text, repair=job)`.
- `py -m rpr ai test | intreaba "..." | rutina proc.docx -o pasi.txt | repara r.rpr.json --nota "..."`: același lucru fără interfață, pentru testele de mai jos.
- Teste: `tests/test_assistant.py` (server HTTP local care imită ambele API-uri, Studio real sub Xvfb).

## De verificat în firmă (în ordine)
1. Pe ce adresă și cu ce antet merge gateway-ul intern: `py -m rpr ai test`, după ce setezi în Studio → 🤖 → ⚙ Conexiune furnizorul, adresa și modelul. Dacă gateway-ul are alt format decât cele două, adaugă un al treilea `provider` în `build_request()` și `parse_response()`, plus un test în `ConnectionTests`.
2. Proxy și certificat: `urllib` folosește `HTTPS_PROXY` din mediu. La eroare `CERTIFICATE_VERIFY_FAILED`, câmpul **Certificatul firmei** primește fișierul `.pem` exportat de IT.
3. Calitate pe modelele mici (Haiku / Flash): rulează `py -m rpr ai rutina` pe 2–3 proceduri reale și notează câte încercări trebuie (`Incercarea N` în ieșire). Dacă mai rămân erori după 2 încercări, primele lucruri de reglat sunt `MAX_REPAIRS`, `max_tokens` (răspuns tăiat) și exemplul din `importer._EXAMPLE_RO`.
4. `🔧 Repară` pe o rutină reală care nu mai merge: verifică dacă tab-ul nou are aceleași setări (timeout, la eroare) la pașii neschimbați.
5. Windows: clipboard-ul în modul „copiez”, fereastra pe ecrane mici (`ui_theme.fit_window`), keyring-ul (`py -m pip install --user keyring`).

## Reguli de păstrat
- AI-ul nu rulează nimic și nu dă click: orice rutină trece prin 📥 Import și prin sistemul de prevenție.
- Nicio dependență nouă obligatorie: `keyring` rămâne opțional.
- Formatul `.rpr.json` nu se schimbă. `PASTREAZA #n` există doar în textul de import (Python).
- Texte noi: prin `i18n` (RO/EN/DE) și în Instrucțiuni. Textele trimise AI-ului au în `de.json` varianta engleză (la fel ca promptul de import).
- Nu scrie în repo adresa gateway-ului, numele modelelor interne, chei sau numele firmei.

## Idei pentru mai târziu (necerute încă)
- Răspunsul afișat pe măsură ce vine (streaming).
- Butonul „🤖 Întreabă despre eroare” direct din cronologie, pe pasul roșu.
- O listă de proceduri de test cu rezultatul așteptat, ca să compari modelele din gateway.
