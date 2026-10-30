# AutoPilot DC — ce s-a schimbat

Pornirea aplicației: **`AutoPilot_DC.pyw`** (sau scurtătura „AutoPilot DC” de pe Desktop). Numele fișierelor nu se mai schimbă de la o versiune la alta, deci scurtăturile și pornirea cu Windows rămân valabile.

## 4.20.0 — 2026-10-30
- **🔀 Flux pentru rutine mari** (ex. 145 de pași): până acum se putea doar derula. Bara nouă de deasupra fluxului:
  - **zoom**: Ctrl + rotița (în jurul mouse-ului), **−** / **+**, Ctrl + / Ctrl −; între 5 % și 200 %. Sub ~40 % textul se ascunde și rămâne forma rutinei;
  - **tragere pe fundal** (sau cu rotița apăsată) ca pe o hartă; click pe card face ce făcea (alege pasul);
  - **⤢ Potrivește** (Ctrl + 0) = toată rutina pe ecran; **↔ Lățime** (Ctrl + 2) = toată lățimea, derulezi doar în jos; **1:1** (Ctrl + 1);
  - **🗺 Harta** mică din colț (apare singură când rutina nu încape): toată rutina și dreptunghiul vizibil; click / tragere = sari acolo;
  - **▾ / ▸** pe cardurile Dacă / Buclă / Pentru fiecare rând ascund ramurile („+N” pași ascunși); **▸ Restrânge tot** / **▾ Extinde tot**. Pasul ales în listă sau din cronologie deschide singur ramura lui; la rulare, dacă pasul curent e ascuns, fluxul urmărește cardul restrâns. Starea e doar în sesiune, fișierul `.rpr.json` nu se schimbă;
  - **🗗 Fereastră separată**: fluxul în fereastra lui, pentru al doilea monitor (**⛶ Ecran complet** / F11, Esc = ieși). Urmărește rularea pe culori (galben / verde / roșu) și rămâne pe flux și când Studio trece singur pe 📊 Excel la o rutină cu buclă Excel. Se reface la fiecare modificare a rutinei sau la schimbarea tab-ului;
  - **⬇ Export** PNG (de 2 ori mărimea de pe ecran, plafonat la ~40 de milioane de pixeli) sau SVG (vectorial, se deschide în browser cu zoom oricât); se deschide după salvare.
- Desenul fluxului se face o dată, la 100 %, într-o listă de forme; ecranul, harta și exportul le desenează la scara lor (`studio_views.FlowView`).
- Instrucțiuni: capitolul 32, în RO / EN / DE; textele noi în EN / DE.
- Teste (Linux, Python 3.12, Xvfb): `test_views` +5 (fereastra separată urmărește rularea pe culori cu centrul pe Excel; zoom păstrează cardul sub mouse, Potrivește / Lățime, limitele; harta + click jos + tragere; restrângere, Restrânge tot, pas ascuns ales = se deschide; export SVG + PNG de 2×, plafonul la rutine uriașe). Suita: 229 rulate, 20 sărite; aceleași 4 eșecuri vechi ca pe main (`test_windows`, `test_schedule.test_weekdays`, 2 × `test_video`). Netestat pe Windows: Ctrl + rotița, iconițele emoji în PNG (fontul Segoe UI Emoji), deschiderea imaginii după export.
## 4.19.0 — 2026-10-30
- **🎯 Remarchează direct din pas** (nou): lângă ▶ Testează pasul (și la ⏱ Așteaptă un obiect). Dacă testul arată că pasul a găsit alt element, nu mai trebuie să mergi în 📚 Bibliotecă: dai click pe elementul corect (SAP / Desktop: F2) și alegi:
  - **Înlocuiește locatoarele**: obiectul își păstrează numele (deci și pașii), locatoarele greșite dispar; fereastra spune câți pași folosesc obiectul;
  - **Obiect nou doar pentru acest pas**: obiectul vechi rămâne neschimbat, pasul primește un obiect nou (nume propus `<vechi>_2`, același folder).
  - Pasul fără obiect primește direct un obiect nou. Biblioteca se salvează; apoi ▶ Testează pasul din nou. Esc = anulare, nimic nu se schimbă.
- Instrucțiuni: capitolul 11 în RO / EN / DE; texte noi în i18n.
- Teste (Linux, Python 3.12, Xvfb): `test_remark_step` nou (7: obiectul pasului inclusiv Așteaptă, câți pași îl folosesc, înlocuire păstrează numele, obiect nou doar pentru pas, pas fără obiect, Esc nu schimbă nimic, butonul din Studio real cu browser fals). Suita întreagă: 224 rulate, aceleași eșecuri vechi ca înainte (2 failures, 2 errors care cer Windows). Netestat pe Windows: Spy-ul real din pas (Edge / SAP F2).

## 4.17.0 — 2026-10-30
- **🎯 Completează obiectele → ▶ Rulează și marchează** (nou): obiectele de pe alte tab-uri sau secțiuni (ex. General, Contracts) nu se văd pe pagina deschisă, deci 🧪 Verifică toate le dădea ✖. Acum rutina însăși face navigarea:
  - rulează de la început, **doar pe primul rând din Excel**;
  - orice pas eșuat întreabă (chiar dacă rutina are „Oprește” la eroare), iar când pasul folosește un obiect Web / SAP / Desktop apare **🎯 Marchează acum**: click pe element (SAP / Desktop: F2), obiectul primește locatoarele, biblioteca se salvează și pasul se reia. Esc = întrebarea revine;
  - în INCEARCA eroarea merge în continuare la „La eroare”, ca în rularea normală;
  - înainte de pornire avertizează că pașii se fac de-adevăratelea (Save, Trigger…): folosește un rând de test.
- Motor: `ask_on_every_error` și `max_rows` (doar în rularea din Studio, nu se salvează în rutină; formatul `.rpr.json` nu se schimbă).
- Instrucțiuni: capitolul 33, pasul 5, în RO / EN / DE; texte noi în i18n.
- Teste (Linux, Python 3.12, Xvfb): `test_learn_run` nou (9: doar primul rând, întreabă și cu politica Oprește, fără steag nu întreabă, INCEARCA neschimbat, 🎯 Marchează acum → reia, Esc → întreabă din nou, fără buton în rularea normală, obiectul pasului inclusiv Așteaptă, locatoarele capturate + salvare). Suita întreagă: 217 rulate, aceleași eșecuri vechi ca înainte (2 failures, 2 errors care cer Windows). Netestat pe Windows: Spy-ul real în timpul rulării.

## 4.16.4 — 2026-10-30
- **📥 Import AI: Ctrl+V lipea promptul în loc de răspunsul AI-ului.** După 📋 Copiază promptul, fereastra Tk rămânea „proprietarul” clipboard-ului și, la lipire în chenar, punea tot promptul, chiar dacă între timp copiai textul din AI. Acum promptul se pune direct în clipboard-ul Windows, iar Ctrl+V / Shift+Insert în chenar citește clipboard-ul Windows (și înlocuiește textul selectat). Pe alte sisteme rămâne clipboard-ul Tk.
- Teste (Linux, Python 3.12, Xvfb): `test_import_paste` nou (5: lipirea ia clipboard-ul sistemului, nu promptul; înlocuiește selecția; revine la Tk; Copiază promptul nu mai trece prin Tk; pe Linux funcțiile Windows răspund „nu”). Fără corecție, 2 dintre ele cad. Suita întreagă: aceleași eșecuri vechi (3 failures; erorile sunt modulele care cer Windows/Playwright). Netestat pe Windows: apelurile reale la clipboard.

## 4.16.3 — 2026-10-30
- **🎯 Completează obiectele** (nou): după 📥 Import AI, obiectele au doar locatoare deduse din text. Fereastra nouă le ia pe rând pe pagina reală, în ordinea pașilor rutinei:
  - **🧪 Verifică toate**: pe pagina deschisă, fără click (aceleași verificări ca 🩺 Verifică): ✔ găsit, ⚠ mai multe elemente la fel, ✖ negăsit. SAP / Desktop: testul obișnuit.
  - **🎯 Marchează în browser** (sau dublu-click): click pe element (SAP / Desktop: F2). Obiectul primește locatoarele capturate (id, css, xpath, frame), cele vechi rămân de rezervă; numele, deci și pașii rutinei, nu se schimbă. Biblioteca se salvează.
  - **⏭ Următorul negăsit**; obiectele cu `{variabile}` în locator se verifică la rulare.
  - Se propune singură după import (🎯 Acum / Mai târziu); oricând din 📚 Bibliotecă → 🎯 Completează sau ⋯ → 🎯 Completează obiectele rutinei. Modul nou `complete_ui.py`.
- Instrucțiuni: capitolul 33, pasul 5, în RO / EN / DE.
- Teste (Linux, Python 3.12, Xvfb): `test_complete` nou (4: locatoarele capturate + cele vechi de rezervă, obiectele rutinei în ordine, stările, fereastra cu Verifică toate + Marchează pe un browser fals). Verificat și cu Chromium fără interfață pe o pagină locală: ✔ / ⚠ 2 elemente / ✖ / variabilă. Netestat pe Windows: Spy-ul real din fereastră (click în Edge, F2 în SAP).

## 4.16.2 — 2026-10-30
- **📥 Import AI: promptul nou** pentru surse mai mari. Sursa poate fi o procedură (cu sau fără poze) sau **cod** (C#, VBA, Python, Selenium, SilkTest, UiPath). AI-ul păstrează selectorii din cod (`id`, `css`, `xpath`, `sap`), traduce doar ce se face pe ecran și în Excel, folosește pozele doar pentru textele exacte și primește lista obiectelor din 📚 Bibliotecă (le folosește ca `[Nume]`). Răspunsul: blocul cu rutina și o listă „De verificat”. Un răspuns prea lung continuă în mesajul următor (`# CONTINUARE`); la import blocurile se unesc, iar numerele rândurilor rămân cele din text.
- **`# TODO: …` = locurile unde intervii tu** (selector ghicit, valoare din alt sistem, decizie neclară). La import apar în galben în lista de probleme (click = rândul), nu blochează crearea și rămân în comentariul pasului (💬 în arbore).
- **Pas nou `INTREABA VALOARE "text" -> {Var}`** (`ASK VALUE`): la rulare apare un câmp de tastat, iar valoarea intră în variabilă. Anulează oprește rutina; fără utilizator, variabila își păstrează valoarea. În Studio: 💬 Întrebare cu bifa „Câmp de tastat”. Câmp nou `ask_value` în pasul `question`, doar în Python (C# îl ignoră).
- **Variabile în locatoare**: `CLICK text "{Rand.UEID}"` caută la rulare valoarea din rândul Excel (și în condiții). Biblioteca păstrează textul cu `{…}`.
- `VARIABILA:` din interiorul unui bloc devine pasul `SETEAZA` (înainte dădea doar valoarea de start a rutinei, deci nu se schimba la fiecare rând).
- Obiectele scanate sau marcate cu 🎯 Spy se refolosesc la import și după text (eticheta / textul lor), cu toate locatoarele; înainte se potriveau doar dacă primul locator era identic.
- Instrucțiuni: capitolul 33, în RO / EN / DE.
- Teste (Linux, Python 3.12, Xvfb): 183 rulate, 8 sărite; aceleași eșecuri vechi. Teste noi: `test_importer` (4: TODO, INTREABA VALOARE, VARIABILA în bloc; mai multe blocuri de cod; obiect scanat refolosit după text; promptul cu biblioteca), `test_rpr` (2: INTREABA VALOARE, locator cu variabilă). Netestat pe Windows: fereastra de tastat la rulare.

## 4.16.1 — 2026-10-30
- **📥 Import AI: butonul ✅ Creează rutina nu se vedea** pe ecranele mai mici (sau cu scalare 125–150 %): bara de jos era așezată ultima și rămânea în afara ferestrei. Acum e așezată prima, jos, iar textul și lista de pași se micșorează în locul ei. Nou: **Ctrl + Enter** creează rutina.
- **DACA / ALTFEL în textul de la AI**:
  - `DACA APARE <obiect>` … `ALTFEL` … `SFARSIT` era respins cu „ALTFEL fără DACA deschis”, deși motorul știa să ruleze ramura. Acum e acceptat.
  - `ALTFEL DACA <condiție>` (și `ALTFEL DACA APARE`) e înțeles: un DACA nou în ramura Altfel, închis de același `SFARSIT`. Înainte, textul de după ALTFEL era ignorat fără niciun mesaj.
  - Mesaje mai clare: „ALTFEL după SFARSIT: SFARSIT-ul de pe rândul N a închis deja DACA” (șterge acel SFARSIT), „Al doilea ALTFEL în același DACA”, „După ALTFEL nu urmează nimic pe același rând”.
  - Promptul pentru AI spune acum explicit: un singur SFARSIT după ALTFEL, DACA în DACA cu propriul SFARSIT, ALTFEL DACA pentru mai multe variante, indentare cu 2 spații.
- Instrucțiuni: capitolul 33, în RO / EN / DE.
- Teste (Linux, Python 3.12, Xvfb): 177 rulate, 8 sărite; aceleași eșecuri vechi ca pe 4.16.0 (2 pentru Windows, programarea pe zile, filmele scurte). Teste noi în `test_importer` (2): DACA în DACA, DACA APARE cu ALTFEL, lanț ALTFEL DACA, mesajele pentru ALTFEL greșit (RO / EN). Verificat în Xvfb la 1366 × 768 și 1280 × 600: butonul ✅ Creează rutina rămâne vizibil. Netestat pe Windows (scalarea reală a ecranului).

## 4.16.0 — 2026-10-30
- **Traduceri**: pe interfața în engleză / germană mai rămâneau texte în română: titlurile pașilor din arbore („Daca…”, „Pentru fiecare rand…”, „Asteapta…”), ramurile, listele (acțiuni, browsere, tehnologii), numele și descrierile exemplelor, mesaje de stare. Titlurile pașilor se compun acum din bucăți traduse; toate textele noi din această versiune au EN / DE.
- **Recorder-ul intră în Studio**: tab-urile vechi (Recorder, Rutine, Log, Excel, Setări, Instrucțiuni) au dispărut; fereastra e doar Studio, cu bara de sus pe un rând. Ce era util s-a mutat:
  - **⏺ Ecran** (F5, oprire F6 sau bara mică ⏺ REC): înregistrează mouse-ul și tastatura în orice aplicație, ca fostul Recorder; pașii intră în rutina deschisă, într-un grup, după pasul selectat. Literele scrise una după alta devin un singur pas „Scrie”, click-urile pe AutoPilot nu se înregistrează. **Sistemul de prevenție** verifică și acești pași (fereastra și zona click-ului, tastele în fereastra corectă).
  - **📖 Instrucțiuni** (F1) e un buton mic lângă ⚙, pe același rând; **⚙ Setări aplicație** se deschide într-o fereastră (siguranță, scurtături, pornire, temă, video, limbă, backup).
  - Rutinele vechi pe coordonate (`.json`) se deschid în Studio ca până acum (pași „pe ecran”). Lista de rutine / log-ul / Excel-ul Recorder-ului erau dublate de 📋 Rutine, ⏱ Cronologie / 📜 Log și pașii Excel din Studio.
- **📥 Import AI** (bara din stânga, sau ⋯ → Importă pași): rutina se creează din pașii scriși de un AI pe baza unui document Word.
  1. 📋 Copiază promptul (explică formatul) și dă-l AI-ului împreună cu documentul.
  2. Lipește răspunsul (sau deschide fișierul .txt / .json / .rpr.json). Formatul e text simplu, un pas pe rând: `DESCHIDE BROWSER`, `CLICK buton "OK"`, `SCRIE camp "Nume" = {Nume}`, `DACA … ALTFEL … SFARSIT`, `PENTRU FIECARE RAND`, `INCEARCA`, `MANUAL "…"`, SAP, Desktop (cuvinte cheie în RO sau EN); merge și JSON.
  3. Verificarea arată arborele de pași și problemele pe rânduri (marcate în text); ✅ Creează rutina o deschide într-un tab nou, iar butoanele / câmpurile noi intră în 📚 Bibliotecă (obiectele existente se refolosesc). Formatul `.rpr.json` nu se schimbă. Module noi `rpr/importer.py`, `import_ui.py`.
- **Filmele rulărilor**: se terminau prea repede și ultimul pas lipsea. Cauze: oprirea imediată după ultimul pas (rezultatul lui apărea pe ecran după oprire) și „scurtarea pauzelor”, care tăia finalul static. Acum filmul mai merge **2 s** după ultimul pas, ultimul ecran se salvează la oprire, iar finalul nu se mai scurtează. Nou: **introducere** (numele rutinei, ora de start, 3 s) și **ieșire** (✅ / ❌ cu mesajul erorii, durata, pașii, rândurile Excel, 4 s); între ele rămâne ce s-a înregistrat. La film pe rând Excel, fiecare film are introducerea și ieșirea lui. Se reglează în ⚙ Setări → 🎥 Video (câmpuri noi în `video.json`: `intro_outro`, `intro_s`, `outro_s`, `tail_s`). Reparat și mesajul de eroare la exportul GIF / MP4.
- Instrucțiuni: capitolele 1–3, 18 și 21 actualizate, capitolul 33 (📥 Import AI) nou, în RO / EN / DE. Filmul scurt „Recorder” a fost scos; celelalte filme scurte arată încă bara de sus veche.
- Teste (Linux, Python 3.12, Xvfb, Chromium fără interfață): 191 rulate, 3 sărite; aceleași 3 eșecuri vechi. Teste noi: `test_importer` (11: exemplele RO / EN dau aceeași rutină, salvare și reîncărcare, JSON cu bloc de cod, erori pe rânduri, obiecte refolosite, Încearcă / condiții, promptul conține toate comenzile, mesajele în limba interfeței, unirea literelor în „Scrie”, titlurile pașilor pe ecran în EN), `test_video.IntroOutroTests` (4: introducere, ultimul cadru, ieșire, finalul nescurtat; fără introducere la filmul manual sau când e oprită din setări; textul ieșirii), `test_i18n` (titlurile pașilor). Verificat în Xvfb în RO și EN: fereastra principală, Setări aplicație, Instrucțiuni, Import AI cu exemplul, rutina importată, pașii înregistrați. Netestat pe Windows: înregistrarea reală ⏺ Ecran (pynput), prevenția pe pașii înregistrați, filmul real cu fereastra urmărită.

## 4.15.0 — 2026-10-30
- **Aspect nou în Studio (varianta C + D + A aleasă din machete)**. Panourile rămân aceleași, se schimbă felul în care le ajungi.
- **Bara de activități** în stânga: 🧱 Pași, 📚 Bibliotecă, 📋 Rutine, 🎬 Filme (nou: filmele salvate, cele mai noi primele, dublu-click = aplicația aleasă pentru filme), jos 🌐 Setări și ❓ Ghid. Click pe iconița activă strânge panoul lateral; panoul ales se ține minte (`aspect.json`: `side_panel`, `side_collapsed`). Tab-urile vechi Pași / Bibliotecă / Rutine au dispărut.
- **Tab-uri pentru mai multe rutine deschise**: 📄 Nou și Deschide pun rutina într-un tab nou (tab-ul gol curent se refolosește); o rutină deja deschisă doar se arată; × întreabă de salvare; la închiderea aplicației se întreabă pentru fiecare tab nesalvat. Cât rulează o rutină, tab-ul nu se schimbă.
- **Centrul are trei vederi**: ✎ Pași (lista de până acum), 🔀 Flux (rutina ca flux de carduri, ramurile una lângă alta; doar citire, click = pasul și proprietățile lui, dublu-click = pasul în listă; cardurile se colorează la rulare) și 📊 Excel.
- **📊 Ecranul de rulare pe Excel**: rândurile din primul pas „Pentru fiecare rând Excel” (până la 6 coloane + Status + Film), citite în fundal. La rulare se deschide singur (nu și la Pas cu pas), arată rândul în lucru, statusul fiecărui rând și minutul din film. Pe rândul ales: pașii lui din log, eroarea, captura; **↻ Reia rândul** rulează o copie a rutinei cu bucla limitată la acel rând (rutina din editor nu se schimbă; prevenția rămâne activă); **🎬 Vezi în film** deschide filmul la minutul rândului.
- **⏱ Cronologia rulării** (primul tab de jos): un card pe pas terminat (✓ / ✕, rândul, durata; la erori mesajul și captura ecranului). Blocurile (Dacă, bucle) nu primesc card; se păstrează ultimele 400.
- Motorul trimite rândurile Excel și spre interfață (`row_started` / `row_finished` cu filmul și secunda), pe lângă film. Formatul `.rpr.json` nu se schimbă.
- Modul nou `studio_views.py`. Instrucțiuni: capitolul 32, în RO / EN / DE; texte noi traduse în EN / DE.
- Teste (Linux, Python 3.12, Xvfb, Chromium fără interfață): 175 rulate, 3 sărite; aceleași 3 eșecuri vechi. Teste noi `test_views` (10): panoul lateral se strânge și se redeschide, tab-urile păstrează fiecare rutina și modificările ei, rutina deja deschisă doar comută, tab-ul gol se refolosește, schimbarea blocată la rulare, cronologia (doar pașii, ultimele 400), ecranul Excel citește rândurile și urmează rularea, Reia rândul rulează o copie limitată la rând, gazda trimite rândurile, fluxul are un card pe pas și alege pasul. Verificat în Xvfb la 1366 × 768, temă închisă și deschisă, cu o rulare reală pe un Excel cu 8 rânduri (un rând cu eroare). Netestat pe Windows (fonturi, DPI, filmul la minutul rândului, capturile pe ecranul real).

## 4.14.0 — 2026-10-30
- **Design mai aerisit și lizibil**: textul din Studio, Managerul de rutine și player crește de la 8–9 la 9–10 pt, mai mult spațiu între elemente, butoane plate fără bold peste tot, tab-uri mai mari. Rândurile din liste cresc odată cu textul (nu se mai taie).
- **🎨 Mărimea textului** (🌐 Setări Studio → Aspect): Mic / Normal / Mare / Foarte mare, pentru toată aplicația (fonturi + widget-uri customtkinter), aplicată la pornire. Fișier nou `%APPDATA%\AutoPilotDC\aspect.json`.
- **Contrast**: lista „La eroare” din ⚙ Rutina (și orice listă de același tip, pe tema închisă și pe cea deschisă) avea text alb pe fundal deschis; stilul listelor e acum complet pentru toate stările. Culoarea textului pe butoane se alege după fundal, iar orice fereastră nouă e verificată automat (text sub raportul de contrast 3:1 se înlocuiește). Verde „OK” / roșu „eroare” / albastru „ramură” se ajustează pe fiecare temă. Paleta: verde mai închis (text alb lizibil), albastru și gri estompat mai deschise pe tema închisă.
- **Ecrane mici**: pe laptop (≤ 1440 × 900) fereastra pornește maximizată; bara de sus stă pe un rând (fără titlurile mici ale grupurilor; pe ecrane înguste butoanele rămân cu iconița și un cuvânt, textul întreg e în tooltip); comenzile rare (Salvează ca…, Exemple, Programează, Ghid) sunt în **⋯**. Panourile Studio se împart în procente din fereastră și se țin minte (↺ le resetează). Textele explicative se rup după lățimea panoului. Managerul de rutine, playerul și ghidul încap pe un ecran 1366 × 768.
- **Drag and drop**: muți pașii în arbore cu mouse-ul (linie de inserare; peste „▸ Atunci / Altfel” sau mijlocul unei bucle intră în interior; nu se poate muta un pas în el însuși); tragi blocuri din 🧱 Pași, obiecte din 📚 Bibliotecă (meniu: Click / Scrie text / Citește / Alege din listă / Dacă există) și rutine din 📋 Rutine (pas „Rulează rutina”).
- **📁 Unde se salvează** (🌐 Setări Studio): un folder comun (☁ OneDrive cu un click) cu subfolderele `rutine`, `obiecte`, `rezultate`, `filme`, plus câte un câmp pe fel de fișier. Ordinea: ce e setat pe rutină / bibliotecă → câmpul anume → folderul comun → folderele de până acum. Câmpuri noi în `studio-setari.json` (`save_base_folder`, `save_folders`, `layout`), ignorate de C#; folderul rutinelor rămâne `routines_folder` (același cu 📂 Manager rutine). Modul nou `rpr/locations.py`.
- **🎬 Deschide filmele cu**: playerul AutoPilot, aplicația implicită din Windows sau altă aplicație (ex. VLC). Pentru alte aplicații filmul se exportă o dată în MP4 lângă el (GIF fără opencv-python) și se refolosește. Se aplică la 🎬, la linkurile din Excel / raport și la dublu-click pe `.apvid`. Și în ⚙ Setări → Video.
- Instrucțiuni: capitolul 31, în RO / EN / DE; texte noi traduse în EN / DE.
- Teste (Linux, Python 3.12, Xvfb, Chromium fără interfață): 165 rulate, 3 sărite; aceleași 3 eșecuri vechi. Teste noi `test_aspect` (12): contrast și culori lizibile, mărimea textului, folderul comun / câmp anume / folderul Managerului, setările Studio păstrează câmpurile C#, folderul filmelor urmează folderul comun, aplicația pentru filme, mutarea pașilor (sus, jos, în ramură, în buclă, nu în el însuși), inserarea la locul ales. Verificat în Xvfb la 1366 × 768 și 1920 × 1080, temă închisă și deschisă: Studio, pașii exemplelor, Setări Studio, Managerul de rutine, Recorder; drag and drop cu mouse-ul simulat (pas mutat sus, bloc tras în „Atunci”); o verificare automată a contrastului pe toate panourile exemplelor. Netestat pe Windows (fonturi Segoe UI reale, scalare DPI, exportul MP4 și deschiderea în VLC).

## 4.13.1 — 2026-10-30
- **Derulare cu roata mouse-ului în panourile Studio** (setări rutină, proprietăți pas, lista de pași din stânga): mergea doar cu cursorul pe bara de derulare, pentru că legarea roții se pierdea când cursorul trecea peste un câmp din panou. Acum e o singură legare pe aplicație: derulează cadrul de sub cursor, oriunde în el (listele cu derulare proprie nu sunt atinse). Ca efect secundar dispare și legarea / dezlegarea evenimentelor la fiecare mișcare peste panou, care putea da lag.
- **Lag**: tab-ul 📋 Rutine nu mai citește folderul de rutine la fiecare trecere pe tab (doar dacă a trecut peste 30 s). Pe Linux pornirea Studio durează ~0,25 s și arătarea unui pas ~25 ms; nu am putut reproduce lagul pe Windows, deci dacă mai apare, spune-mi când (la pornire, la selectarea unui pas, la o anumită listă).
- **Demo nou**: **Exemple** → **06 Demo - Daca apare si reguli la mesaj** (pagină locală, fără internet): regula închide singură mesajul „Sigur vrei să continui?”, iar „Daca apare” trece mai departe când mesajul lipsește. Obiectele lui intră în biblioteca exemplelor. Regula și „Daca apare” folosesc implicit condiția **Obiectul e vizibil** (un mesaj ascuns „există” în pagină).
- Instrucțiuni: capitolul 30 completat (vizibil vs. există, demo), în RO / EN / DE. Nu am adăugat un tutorial video nou (cele 8 existente rămân neschimbate).
- Teste (Linux, Python 3.12, Chromium fără interfață): 153 rulate, 3 sărite; aceleași 3 eșecuri vechi. Teste noi: demo-ul referă doar obiecte din bibliotecă; demo-ul rulează în browser (regula apasă „Da”, „Daca apare” trece mai departe). Verificat în Xvfb: roata mouse-ului derulează panoul când cursorul e pe un câmp. Netestat pe Windows (roata, lagul).

## 4.13.0 — 2026-10-30
- **👁 Daca apare (optional)** (Flux): așteaptă scurt un mesaj / element; dacă apare, rulează pașii din „Atunci”, dacă nu, rutina merge mai departe fără eroare. Câmp nou `optional` pe pasul `if` (versiunile care nu-l cunosc îl tratează ca „Daca” obișnuit).
- **🧯 Regula la mesaj / eroare** (Flux): pas nou care se **armează** când e întâlnit și rămâne activ până la sfârșitul listei în care stă (primul pas = pe toată rutina). Când un pas pică și regula se potrivește (textul erorii conține un text dat și / sau un element e pe ecran), rulează pașii regulii, apoi *reia pasul* (maxim 3 ori), *îl consideră rezolvat* sau lasă eroarea să meargă mai departe. Mesajul erorii e în `{EroareRegula}`. Regulile se verifică doar la o eroare, deci nu încetinesc rutina; pașii regulii nu declanșează alte reguli. Tip nou de pas `on_error_rule` (doar Python; C# nu-l cunoaște).
- Instrucțiuni: capitolul 30, în RO / EN / DE.
- Teste (Linux, Python 3.12, Chromium fără interfață): 151 rulate, 3 sărite; aceleași 3 eșecuri vechi. Teste noi `test_rules` (13): regulă după text (fără diferență mare / mică), după element, variabila cu eroarea, nepotrivire = eroare normală, „sari”, „eroare mai departe”, regula se stinge la sfârșitul grupului, limita de 3 reluări, pașii regulii nu declanșează reguli, „Daca apare” cu element absent / prezent, titlu și salvare. Verificat în Studio (Xvfb): adăugare din meniu, editorul regulii și al pasului. Nu am putut testa pe Windows, cu o aplicație reală, nici regulile pe mesaje din SAP.

## 4.12.2 — 2026-10-30
- **✎ Redenumește rutina din 📋 Rutine** (buton **✎ Nume** sau click dreapta → Redenumeste...): schimbă numele afișat direct în fișier, fără să deschizi rutina. Rutina deschisă acum se redenumește din ⚙ Rutina (câmpul Nume).
- Teste: fără schimbări de logică (doar interfață); verificat în Studio (Xvfb) că numele se scrie în fișier și lista se reface. Netestat pe Windows.

## 4.12.1 — 2026-10-30
- **Pașii rutinei se văd înainte s-o adaugi**: în 📋 Rutine, sub listă, apare arborele de pași al rutinei alese (cu structura Dacă / bucle, doar citire); același arbore în editorul pasului „Ruleaza rutina”.
- Teste (Linux, Python 3.12): fără schimbări de logică, doar interfață. Verificat în Studio (Xvfb): arborele din editorul pasului. Previzualizarea din tab folosește aceeași funcție, dar nu am văzut-o pe ecran; netestat pe Windows.

## 4.12.0 — 2026-10-30
- **📋 Rutine salvate ca pas.** Pas nou **📋 Ruleaza rutina** (Organizare): rulează o rutină salvată în locul pasului, cu **aceleași variabile, același Excel și aceeași bibliotecă**; setările rutinei principale se aplică și ei, iar pașii calupului apar în log cu numele lui. Înainte de start se verifică fișierul, buclele, adâncimea (maxim 8) și obiectele lipsă. Fișierul se urmărește: o schimbi o dată și merge peste tot.
- **Tab nou 📋 Rutine** lângă 📚 Biblioteca (folderul din 📂 Manager rutine, căutare, subfoldere): **➕ Ca pas** (dublu-click) adaugă pasul care apelează rutina, **📥 Ca pasi** copiază pașii în rutina curentă (cu variabilele lor), **📂 Deschide**. La pasul existent: **📥 Inlocuieste cu pasii ei**.
- Instrucțiuni: capitolul 29, în RO / EN / DE. Format `.rpr.json`: tip nou de pas `run_routine` (câmpurile `path`, `name`); versiunile mai vechi păstrează pasul necunoscut, dar nu îl rulează.
- Teste (Linux, Python 3.12, Chromium fără interfață): 138 rulate, 3 sărite; aceleași eșecuri vechi (`test_windows`, `test_schedule.test_weekdays`, tutorialul `06_biblioteca`). Teste noi `test_subroutine` (11): rulare pe loc cu variabile comune, valoare implicită vs. variabilă din rutina principală, fișier lipsă, buclă, obiect lipsă numit, pas dezactivat, cale cu variabilă, politica de erori, copiere de pași, cale relativă. Verificat în Studio (Xvfb): lista rutinelor, ➕ Ca pas, 📥 Ca pasi, editorul pasului, Inlocuieste cu pasii ei. Nu am putut testa pe Windows, cu rutine pe Drive / OneDrive reale și nici o rulare completă cu SAP / Web printr-un calup.

## 4.11.2 — 2026-10-30
- **Marcarea în browser durează 8 s** (înainte 2 s la 🧪 Test, deci o secțiune mare se pierdea). Buton nou **👁 Marcheaza din nou** în fereastra de test și **👁 Marcheaza in browser (8 s)** la click dreapta pe obiect. Merge și pe containere (secțiuni): se marchează chenarul întreg.
- **Reparat**: `version.py` rămăsese gol în 4.11.1 (aplicația nu pornea: lipsea `__version__`); restaurat.
- Teste (Linux, Python 3.12): 127 rulate, 3 sărite; aceleași 3 eșecuri vechi; fără schimbări de logică. Verificat doar compilarea și testele existente; marcajul vizual pe Windows nu l-am putut vedea.

## 4.11.1 — 2026-10-30
- **Redenumire pagină / site în bibliotecă**: click dreapta pe 📄 pagină (sau 🌐 site) → **✎ Redenumeste pagina... / site-ul...** schimbă numele pentru toate obiectele de sub ea (și grupul de link-uri al site-ului). Dacă numele nou există deja, paginile se unesc. Tot acolo: **🩺 Verifica obiectele de aici**.
- Instrucțiuni: capitolul 28, în RO / EN / DE.
- Teste (Linux, Python 3.12): 127 rulate, 3 sărite; aceleași 3 eșecuri vechi; test nou `test_rename_page_and_site`. Verificat în Studio (Xvfb): redenumirea paginii și a site-ului. Meniul click-dreapta nu a fost încercat pe Windows.

## 4.11.0 — 2026-10-30
- **🔍 Fereastra de scanare**: click pe un rând **marchează elementul în browser** (3,5 s, cu textul găsit) ca să știi ce buton e și dacă îl ții; bifa din prima coloană (sau Space / **☑ Tine / scoate**) îl ține sau îl scoate. **✎ Redenumeste** (F2 / dublu-click pe nume) schimbă numele înainte de salvare (nume unic față de bibliotecă).
- **📁 Foldere în bibliotecă**: câmp nou `folder` pe obiect (doar Python; C# îl ignoră), ex. `Comenzi/Export`, cu subfoldere. Arborele devine **Site · Pagină · 📁 Folder · buton**. Sus în fereastra de scanare alegi **Pagina** și **Folderul** sub care intră obiectele; **🖐 Captura 3 s** folosește ultimul folder ales. Pe obiect: câmpul **Folder** din Editează și **📁 Muta in folder...** (click dreapta). Pe folder (click dreapta): **✎ Redenumeste folderul...** (și subfolderele) și **🩺 Verifica obiectele folderului**. Folderul doar grupează: nu schimbă locul unde se caută elementul (asta face Containerul), iar rutinele nu se schimbă.
- **Ferestre derulabile**: ferestrele Obiect, Scanare, Verificare, Test, Site-uri și Programare se derulează cu roata mouse-ului, iar butoanele (Salveaza / Adauga / Inchide) stau fixe jos; fereastra nu mai iese din ecran, deci nu mai trebuie mărită.
- Instrucțiuni: capitolul 26 actualizat, capitolul nou 28 (foldere), în RO / EN / DE.
- Teste (Linux, Python 3.12, Chromium fără interfață): 126 rulate, 3 sărite; aceleași 3 eșecuri vechi (`test_windows`, `test_schedule.test_weekdays`, tutorialul `06_biblioteca`). Teste noi `FolderTests` (normalizare, foldere cu părinți, subfoldere, redenumire, salvare / încărcare). Verificat în Studio (Xvfb, ecran de 560 px înălțime): marcare în browser, redenumire, folder ales la scanare, arborele cu foldere, redenumirea folderului, derulare + butoane fixe în fereastra Obiect. Nu am putut testa pe Windows / Edge (roata mouse-ului pe Windows folosește `delta`, verificat doar cu un eveniment simulat).

## 4.10.0 — 2026-10-30
- **🩺 Verifica** (📚 Biblioteca, lângă 🔍 Scaneaza site; și după „Pagina e gata?”, și la click dreapta pe un obiect): verifică dacă butoanele și câmpurile salvate mai merg pe pagina deschisă în browser. Pentru fiecare face un **click de probă** (Playwright `trial`): aceleași verificări ca la un click real (găsit, vizibil, activ, nu se mișcă, nu e acoperit de alt element), **fără să apese** și fără cereri la server. Alegi pagina curentă sau tot site-ul.
- Rezultat pe obiect: ✅ merge · ⚠ impedimente (acoperit de o fereastră / overlay, cu elementul care îl acoperă; dezactivat; ascuns; se mișcă; găsit de mai multe ori; merge doar locatorul de rezervă; pare alt element; textul s-a schimbat; câmp doar citire) · ❌ trebuie recaptat · · e pe altă pagină.
- **🔧 Repara locatorii** pune primul locatorul care merge (ceilalți rămân, pentru test / producție). **🎯 Recapteaza**: click pe element în browser; obiectul își păstrează numele, tipul, pagina și containerul, deci rutinele merg mai departe. **🔄 Verifica din nou** actualizează lista.
- Instrucțiuni: capitolul 27, în RO / EN / DE.
- Teste (Linux, Python 3.12, Chromium fără interfață): 121 rulate, 3 sărite; aceleași 3 eșecuri vechi (`test_windows`, `test_schedule.test_weekdays`, tutorialul `06_biblioteca`). Teste noi în `test_scan`: obiect care merge (fără niciun click pe pagină), obiect dispărut, locator de rezervă, buton dezactivat, acoperit de overlay, locator ambiguu, câmp doar citire, alegerea obiectelor pe pagină, reparare și recaptare cu păstrarea numelui. Verificat în Studio (Xvfb): lista, detaliile, Repara locatorii + Verifica din nou. Nu am putut testa pe Windows / Edge, pe aplicația de firmă și nici Recaptarea cu mouse-ul.

## 4.9.0 — 2026-10-30
- **🔍 Scanează site** (📚 Biblioteca): scrii adresa aplicației, se deschide browserul AutoPilot, te autentifici și deschizi pagina, apoi **Scanează automat**. Se găsesc butoanele, câmpurile, listele, bifele și link-urile vizibile (și din iframe-uri, maxim 500), cu aceiași locatori ca la Spy. Alegi din listă ce intră (**Fără link-uri** scoate meniurile de navigare); obiectele deja în bibliotecă sunt sărite. Apoi deschizi alt meniu / tab și **Scanează din nou**. Scanarea doar citește pagina încărcată: fără click-uri, fără scriere, fără cereri la server, în loturi mici cu pauze, ca aplicația să rămână fluidă.
- **🖐 Captură 3 s**: ții cursorul 3 secunde pe un câmp / buton (contur albastru cu numărătoare inversă) și se salvează singur în bibliotecă; treci la următorul. Click-urile merg normal (poți deschide meniuri). Esc în browser sau **Am terminat** oprește.
- **Biblioteca pe aplicație, într-un fișier ales de tine**: **📂 Deschide / ＋ Nouă / 📁** în 📚 Biblioteca; „Nouă” propune `OneDrive\AutoPilotDC\obiecte\<Aplicație>\obiecte.json` (fără OneDrive: Documente). Aplicația ține minte doar calea ultimei biblioteci (`studio-setari.json`, `library_path`). Rutina salvată păstrează calea bibliotecii (câmpul existent `repository_path`, același format ca în C#) și o încarcă singură; o rutină fără cale folosește biblioteca implicită, ca până acum. Dacă OneDrive are altă cale pe celălalt laptop, biblioteca e găsită la același loc relativ.
- Instrucțiuni: capitolul 26, în RO / EN / DE.
- Teste (Linux, Python 3.12, Chromium fără interfață): 114 rulate, 3 sărite; aceleași 3 eșecuri vechi (`test_windows`, `test_schedule.test_weekdays`, tutorialul `06_biblioteca`). Test nou `test_scan`: căi de bibliotecă (OneDrive, alt laptop), dubluri, scanarea unei pagini reale (câmpuri, butoane, link, listă, bifă, iframe; fără elemente ascunse), limita, captura cu cursorul ținut 3 s și oprirea cu Esc. `test_web` trece și el. Verificat în Studio (Xvfb): bibliotecă nouă în OneDrive, lista scanării, salvarea rutinei cu calea bibliotecii. Nu am putut testa pe Windows / Edge și nici pe aplicația de firmă.

## 4.8.6 — 2026-10-29
- **O singură limbă pentru toată aplicația**: setarea separată „Limba fișierelor” din 4.8.5 a fost scoasă. ⚙ Setări → 🌐 Limba schimbă acum totul: interfața, logurile (și nivelurile Info / Avertisment / Eroare), statusurile din Excel, raportul rulării, rezumatul și documentația pregătirilor. Română = totul în română, English = totul în engleză. Reluarea recunoaște în continuare statusurile în orice limbă.
- Instrucțiuni: capitolul 18 actualizat, în RO / EN / DE.
- Teste (Linux, Python 3.12): 96 rulate, 5 sărite; aceleași 3 eșecuri vechi. `test_file_language` adaptat (fișierele urmează limba aplicației, nivelurile din log). Ecranul de Setări doar compilat, nepornit.

## 4.8.5 — 2026-10-29
- **🌐 Limba fișierelor** (⚙ Setări → 🌐 Limba): o setare separată de limba interfeței pentru tot ce se scrie în fișiere: coloana de status din Excel-ul rutinei (OK / EROARE / SARIT / OPRIT / IN LUCRU), raportul Excel al rulării, rezumatul și `Documentatie.html` ale pregătirilor, logul exportat în Excel și logurile text ale rulărilor programate. Implicit „Ca interfața” (deci română, ca până acum); se poate alege English sau Deutsch fără să schimbi interfața. Se aplică de la următoarea rulare, fără repornire. Setarea stă în `limba.json` (cheia `fisiere`) și intră în backup.
- **Reluarea recunoaște statusurile în orice limbă**: un Excel început în română și reluat în engleză (sau invers) sare rândurile OK și întreabă la rândul „IN LUCRU” / „IN PROGRESS” / „IN BEARBEITUNG”.
- În cod, statusurile rămân în română și se traduc doar la scriere (`rpr/lang.py`); culorile din raport se aleg după statusul intern (reparat: „EROARE: …” nu primea culoarea roșie în raport).
- Instrucțiuni: capitolul 18 (Setări), în RO / EN / DE.
- Teste (Linux, Python 3.12): 96 rulate, 5 sărite; aceleași 3 eșecuri vechi (`test_windows`, `test_schedule.test_weekdays`, tutorialul `06_biblioteca`). Test nou: `test_file_language` (setarea, traducerea independentă de interfață, statusuri scrise în engleză / germană, reluare cu statusuri în altă limbă). Interfața de Setări nu a fost pornită (doar compilată).

## 4.8.4 — 2026-10-29
- **Reluare după o închidere neașteptată**: cât timp rulează o rutină sau o pregătire (din Studio sau programată), AutoPilot DC ține un fișier mic de stare în `Studio\in-curs`. Dacă aplicația sau PC-ul se închide în mijlocul rulării, la următoarea pornire apare întrebarea **Reiau rularea / Doar deschid / Nu, renunț**. La reluare, rândurile Excel cu OK sunt sărite, iar la o pregătire și rutinele deja terminate. Rutinele cu modificări nesalvate se refac din copia făcută la pornirea rulării. Dacă închizi tu aplicația în timpul rulării, nu se oferă reluarea.
- **Rândul „IN LUCRU”**: înainte de pașii unui rând, coloana de status primește „IN LUCRU zz.ll hh:mm” (portocaliu), salvat imediat. La STOP în mijlocul rândului rămâne „IN LUCRU (oprit …)” (înainte era „OPRIT”). La o rulare nouă, pentru un astfel de rând se întreabă: **Refac rândul / E făcut, marchez OK / Opresc rutina** (fără interfață: refacere).
- Instrucțiuni: capitolul 25, în RO / EN / DE.
- Teste (Linux, Python 3.12): 100 rulate, 12 sărite; aceleași 3 eșecuri vechi. Teste noi: `test_resume` (starea rulării, detectarea, pregătire reluată, rulare fără interfață) și întrebarea pentru rândul „IN LUCRU”. Verificat și în Studio (Xvfb): reluare rutină salvată, nesalvată și pregătire.

## 4.8.3 — 2026-10-29
- **💾 Raportul Excel se salvează din mers**, după fiecare rând / repetare (cel mult o dată la 5 s; la rulări mari mai rar), în același fișier care se completează la final. Dacă aplicația se blochează sau PC-ul se oprește, rămâne tot ce s-a făcut. Dacă fișierul e deschis în Excel la final, raportul final primește sufixul `_final`.
- **Filmele pe rutină**: ⚙ Setări rutină → 🎥 Filmele rutinei (gol = folderul din Setări → Video); la pregătiri, filmele stau lângă rezumat (`filme`), dacă rutina nu are alt folder.
- **☁ OneDrive**: buton pentru folderul raportului și al filmelor, care alege un folder din OneDrive-ul sincronizat (`AutoPilotDC\rapoarte|filme\<rutina>`); clientul OneDrive le duce singur în cloud, fără conturi sau chei în aplicație.
- **Film întrerupt brusc**: la înregistrare se scrie un jurnal la 10 s; la deschidere, un film neterminat se reface automat din cadrele deja salvate (originalul rămâne `.stricat`).
- Excel-ul de intrare se salva deja după fiecare rând (opțiunea buclei).
- Teste (Linux, Python 3.12): 93 rulate, 12 sărite; aceleași 3 eșecuri vechi. Teste noi: salvarea din mers, folderul filmelor, recuperarea filmului.

## 4.8.2 — 2026-10-29
- **🎥 Filmul direct din listă**: în bucla „Pentru fiecare rând Excel”, cu filmul pornit, fiecare rând primește în Excel-ul de intrare coloana **Film**, cu linkul spre film și minutul la care începe rândul (din proprietățile buclei se schimbă coloana sau se oprește). Un rând marcat greșit se verifică dintr-un click.
- **Player separat pentru `.apvid`**: dublu-click pe film sau click pe link în Excel / raport îl deschide în player (proces separat, fără aplicația principală). Asocierea se face la pornirea aplicației, doar pentru utilizatorul curent, fără drepturi de administrator. Manual: `pythonw video_ui.py "film.apvid" --t 75`.
- Instrucțiuni (capitolul 21) în RO / EN / DE.
- Teste (Linux, Python 3.12): 89 rulate, 12 sărite; aceleași 3 eșecuri vechi. Teste noi pentru linkul filmului în Excel.

## 4.8.1 — 2026-10-29
- **💾 Backup și restaurare** (⚙ Setări): un `.zip` salvat unde alegi, cu setările, rutinele Recorder și Studio, biblioteca de obiecte, programările, notițele, limba, setările video și folderul rutinelor din 📂 Manager (fără profilul browserului și fără filme; rezultatele doar la cerere). La restaurare, starea curentă se salvează întâi automat în `backup-automat`; căile care nu există pe PC-ul nou sunt adaptate.
- **„Nu deranja”**: repornirea serviciului de notificări raportează acum când Windows o refuză (acces interzis), iar mesajul spune de ce setarea poate să nu se aplice. Nou: **⚙ Setări → 🔍 Verifică Nu deranja** (și `python autopilot_safety.py dnd --test`): versiunea Windows, setarea găsită, serviciul, opțional un test real; raportul se salvează în `loguri\nu_deranja_diagnostic.txt`. Cauza exactă pe laptopul tău rămâne de confirmat cu acest raport.
- Instrucțiuni: capitolul 24 (Backup) și „Nu deranja” la Probleme frecvente, în RO / EN / DE.
- Teste (Linux, Python 3.12): 87 rulate, 12 sărite; aceleași 3 eșecuri vechi ca la 4.8.0 (cer Windows / tutorialul 06). `test_backup` nou trece.

## 4.8.0 — 2026-10-29
- **📊 Raport Excel al rulării** („dovada muncii”), cu sau fără Excel de intrare: ⚙ Setări rutină → 📊 Raport. Un fișier la fiecare rulare, cu un rând pentru fiecare rând Excel / repetare de pe primul nivel (sau unul pentru toată rutina): ora de start, durata, statusul, mesajul, **valorile bifate**, pașii parcurși, filmul (cu minutul în film) și captura erorii. Foaia „Pași” are fiecare pas executat (definiția / regula, ora, rezultatul), iar foaia „Rutina” rezumatul și definiția completă. Bifa **📊 Pune valoarea în raport** apare și pe pașii care salvează o valoare. Setările stau în `settings.report` din `.rpr.json` (C# le ignoră).
- **📂 Manager de rutine** (bara Studio): rutinele din folderul setat, citite la pornirea aplicației; deschide / rulează / adaugă în pregătire; folderul se schimbă din manager.
- **Pregătiri**: o listă de rutine rulate una după alta (ordine, rulează / omite, oprește sau continuă la eroare), salvată ca `Nume.pregatire.json` lângă rutine. Fiecare rutină are filmul și raportul ei; la final, un folder `rezultate\pregatiri\Nume_data_ora` cu `Pregatire_Nume.xlsx` (rezumat + definiții) și `Documentatie.html` (tot ce s-a făcut, în detaliu). Întrebările, Pauza / STOP și sistemul de prevenție rămân active. Se poate rula și fără interfață / programa: `py -m rpr run "Nume.pregatire.json"`.
- **🎥 Video** (inclus din commit-ul anterior, acum în versiune): înregistrarea ecranului manual sau la fiecare rulare, film pe rând Excel, editor, export GIF / MP4, tutoriale în Instrucțiuni.
- Instrucțiuni: capitolele 22 (Raportul Excel) și 23 (Manager de rutine și pregătiri), în RO / EN / DE.
- Teste (Linux, Python 3.12): 83 rulate, 12 sărite; 3 cad independent de această versiune: `test_windows` (cere Windows), `test_schedule.test_weekdays` (calea Python pe Linux nu e `pythonw.exe`), `test_video.test_all_tutorials_present_and_trilingual` (tutorialul `06_biblioteca` are un singur cadru). Testele noi `test_report` și `test_batch` trec.

## 4.7.0 — 2026-10-16
- **Limbi: Română / English / Deutsch** pentru toată interfața — Recorder, Studio, Bibliotecă, Programare, Setări, mesaje, log-ul rulării, meniul din tray și mesajele rulărilor programate. Limba se alege în **⚙ Setări → 🌐 Limba** și se aplică după repornire (aplicația se repornește singură după confirmare).
- Traducerile sunt în `i18n/en.json` și `i18n/de.json` (cheia = textul românesc). Logica nu se schimbă cu limba: numele obiectelor, variabilele (`{Rand.…}`, `{Azi}`) și fișierele rutinelor rămân aceleași, deci rutinele merg la toți colegii, indiferent de limbă.
- **📖 Instrucțiuni**: zonă nouă lângă Recorder / Studio (și butonul ❓): 20 de capitole care explică pe scurt fiecare procedură, pas cu pas, cu exemple — pornire, Recorder, siguranță, Studio, Web / SAP / Desktop, Bibliotecă, pași, condiții, variabile, Excel, erori, rulare, programare, setări, probleme frecvente, fișiere. În română, engleză și germană (comuți limba textului direct din pagină), cu căutare.
- Setări: tema / limba repornesc aplicația doar dacă s-au schimbat (înainte întreba la fiecare salvare).

## 4.6.1 — 2026-10-16
- **Reparat Desktop: click-ul ajungea în altă fereastră.** Windows bloca aducerea aplicației în față, așa că click-ul (ex. schimbarea conversației) cădea pe fereastra de deasupra. Acum fereastra aplicației e adusă sigur în față (și restaurată dacă e minimizată), iar înainte de fiecare click se verifică dacă punctul chiar e în aplicație; dacă nu, click-ul se face prin UI Automation sau pasul se oprește cu un mesaj clar — niciodată în altă fereastră.
- **Scroll automat Desktop**: elementul din afara zonei vizibile e adus în zonă înainte de acțiune.
- **Spy Desktop pe liste (conversații, e-mailuri)**: se capturează rândul întreg, nu textul din interior; numele care conțin text variabil (ultimul mesaj, ora, necitite) primesc un locator cu șablon (`ListItem|Ion Popescu*`); calea după poziția din listă e doar rezervă, dezactivată (lista se reordonează).
- Locatorii Nume / ClassName acceptă `*` și `?` (ex: `Button|Salv*`).
- **Pornește aplicație** așteaptă ca aplicația să fie gata de lucru (nu doar să apară fereastra).
- **SAP: citirea celulelor din tabele** derulează tabelul până la rândul cerut (ALV și table control).
- Pașii creați din Spy / Bibliotecă / înregistrare primesc tehnologia obiectului (SAP / Desktop), nu „Web”.

## 4.6.0 — 2026-10-16
- **Driver SAP GUI** (SAP GUI Scripting): conectare la sesiune, tranzacții, taste (Enter, F3, F8, Shift+F4, Ctrl+S...), câmpuri, butoane, liste, bife, tab-uri, citirea barei de stare și a tabelelor (ALV / table control), capturi. Exemplul 04 (VA03) rulează acum și în Python.
- **Driver aplicații desktop** (UI Automation): pornește / atașează / închide aplicații, click, scriere text (cu diacritice), liste, bife, citire text / valoare / atribute; „Mod direct” fără mișcarea mouse-ului. Exemplul 05 (Notepad) rulează.
- **🎯 Spy SAP și 🎯 Spy Desktop**: mouse-ul peste element (contur pe ecran), **F2** = capturează, **Esc** = anulează; locatorii sunt aceiași ca în versiunea C#.
- **Test** din 📚 Biblioteca funcționează și pentru obiectele SAP / Desktop (câte elemente găsește fiecare locator, marcarea pe ecran).
- **🕒 Programează** (bara Studio): zilnic, zile lucrătoare, anumite zile, o singură dată, la fiecare N minute sau la autentificare; fără drepturi de administrator și fără probleme cu formatul datei. Lista programărilor (rulează acum / șterge) și istoricul rulărilor programate.
- Rularea programată pornește fără fereastră CMD și arată la final un mesaj în colțul ecranului (verde / roșu, cu „Deschide logul”); două rulări programate nu pornesc una peste alta.

## 4.5.0 — 2026-10-16
- **📚 Biblioteca de obiecte** (ca în SilkTest) în locul tab-ului „Obiecte”: arbore **Site → Pagină → Container → obiecte**, comun tuturor rutinelor; căutare după nume / tip / site / etichetă și filtrul „doar ce merge pe pagina din browser”.
- **Clasificare automată după link**: la Spy / înregistrare obiectul primește site-ul, pagina (din link, fără ID-uri) și tipul (Buton, Câmp text, ComboBox, Tabel, RefList, Container...). Obiectele vechi se clasifică singure.
- **Containere** (secțiune, tabel, RefList, formular, meniu): obiectele din ele sunt căutate *în interiorul containerului* — același buton „Salvează” din două secțiuni nu mai e confundat. La Spy, containerul în care se află elementul e propus automat.
- **🧪 Test** înainte de a folosi un obiect: câte elemente găsește fiecare locator în container și în pagină, îl marchează în browser; din rezultat îl adaugi direct ca pas.
- **🌐 Site-uri (sisteme similare)**: un site = mai multe link-uri (test, producție, alt client); obiectele lui merg pe toate. *Copiază pentru alt site* duplică un obiect pentru alt sistem.
- Click dreapta pe obiect: testează, adaugă pas (Click / Scrie / Citește / Alege din listă / Dacă există), mută în container, copiază, șterge.
- La rulare, log-ul avertizează când obiectul e folosit pe un link care nu e al site-ului lui.

## 4.4.1 — 2026-10-16
- **Reparat: Edge nu pornea** („Target page, context or browser has been closed”): fiecare browser are acum profilul lui (Edge și Chrome nu mai împart același folder), browserul pornește cu sandbox-ul normal (fără bara galbenă `--no-sandbox`), iar dacă profilul e blocat de o fereastră rămasă deschisă se reîncearcă și apoi se pornește cu un profil temporar (cu mesaj).
- **Reparat: pictograma din tray**: e afișată mereu cât rulează aplicația; dacă nu poate fi creată, fereastra se deschide normal (înainte, la pornirea cu Windows aplicația putea rămâne invizibilă); starea pictogramei apare în Setări.

## 4.4.0 — 2026-10-16
- **Driver Web (Playwright)** în Studio: acțiuni reale în Edge / Chrome instalat (nu se descarcă nimic), profil de browser păstrat (login-ul rămâne), iframe-uri, tab-uri noi, popup-uri JavaScript, „self-healing” (dacă un locator nu mai merge, se trece la următorul).
- **🎯 Spy Web**: click pe un element din browser → fereastra „Obiect capturat” (nume, locatori cu scor, captura elementului) → Salvează / + pas Click / Scrie text / Citește.
- **⏺ Înregistrează Web**: lucrezi normal în browser, fiecare click / text / opțiune devine un pas cu obiectul lui.
- **👁 Arată** obiectul pe pagină (tab-ul Obiecte); **🌐 Setări Studio**: alegerea browserului, ștergerea profilului.
- Exemplele 02 (Web login) și 03 (Web + Excel) rulează acum în versiunea Python.

## 4.3.0 — 2026-10-16
- **Studio RPR în aplicație**: comutatorul *🎬 Recorder | 🧩 Studio RPR* din bara de sus; blocuri, arborele rutinei, proprietăți fără cod, rulare cu Pas cu pas / Pauză / Stop, log, variabile, obiecte, exemple, ghid.
- **Bara de sus pe două rânduri**: butoane mici, grupate, care trec pe rândul următor când fereastra e îngustă; STOP URGENȚĂ mereu vizibil.
- **Iconiță proprie**, **pornire cu Windows** (opțional direct în tray), **pictogramă lângă ceas** (tray), ✕ poate ascunde aplicația în tray.
- **Scurtătura de pe Desktop pornește fără fereastră CMD** (direct `pythonw.exe`).
- **Reparat „Nu deranja”** care rămânea pornit după rulare; buton „Repornește notificările acum” în Setări.
- Folderul a devenit `AutoPilotDC_py` (fără număr de versiune în nume).

## 4.2.0 — 2026-10-15
- **Motorul Studio RPR în Python** (`rpr/`): pași ca arbore, condiții, bucle, variabile, Excel (formulele rămân intacte), Încearcă / La eroare; fișiere `.rpr.json` identice cu versiunea C#.
- Rulare fără interfață: `py -m rpr run rutina.rpr.json`.
- **`INSTALEAZA.bat`**: instalează tot ce trebuie, fără drepturi de administrator; fereastra rămâne deschisă până apeși o tastă.

## 4.1.0 — 2026-10-15
- **Siguranța la rulare**: „Nu deranja” pe durata rulării, chenar roșu RUN / verde REC / portocaliu PAUZĂ, sistemul de prevenție (pauză + întrebare când ecranul diferă de înregistrare, la ferestre de eroare, aplicații blocate, pași eșuați).
- Pornire fără consolă (`AutoPilot_DC.pyw`).

## 3.9
- Versiunea inițială (recorder / player pe coordonate).
