# Instrucțiuni AutoPilot DC

Fiecare capitol explică pe scurt o procedură, pas cu pas, cu un exemplu. Alege capitolul din stânga sau caută un cuvânt.

## 1. Pornire și interfață

- Pornești aplicația cu **AutoPilot_DC.pyw** din folderul `AutoPilotDC_py` sau cu scurtătura „AutoPilot DC” de pe Desktop (fără fereastră CMD).
- Prima dată (sau pe un laptop nou) rulează **INSTALEAZA.bat**: instalează tot ce trebuie, fără drepturi de administrator. Fereastra rămâne deschisă până apeși o tastă.
- Aplicația are o singură zonă de lucru, **🧩 Studio RPR**. Fostul Recorder a intrat în Studio (butonul **⏺ Ecran**, capitolul 2).
- Bara de sus e pe un singur rând: comenzile Studio (rutină, rulare, Spy și înregistrare) în mijloc; când fereastra e îngustă rămân doar iconițele (textul întreg e în tooltip). În dreapta, butoane mici: **🎥** filmează ecranul, **🎬** deschide un film, **📖 Instrucțiuni** (aici, sau F1), **⚙ Setări** aplicației, **✕**.
- **🚨 STOP URGENȚĂ** (sau F12) oprește imediat orice rulare și înregistrare.
- Pictograma de lângă ceas (tray): click = deschide aplicația; click dreapta = Studio, ⏺ Ecran, film, STOP URGENȚĂ, Ieșire.

> Exemplu: deschide aplicația, apasă **⋯ → 📚 Exemple** și deschide „01 Învățare”.

## 2. ⏺ Ecran: înregistrare mouse și tastatură (fostul Recorder)

1. În Studio selectează pasul după care vrei pașii noi (sau nimic: se adaugă la sfârșit).
2. Apasă **⏺ Ecran** (F5). Fereastra AutoPilot se minimizează, apare chenarul verde **REC** și o bară mică sus, cu numărul de pași și **⏹ Stop (F6)**.
3. Lucrează normal în orice aplicație: click-uri, scroll, taste. Literele scrise una după alta devin un singur pas „Scrie”. Click-urile pe AutoPilot nu se înregistrează.
4. Apasă **F6** sau **⏹ Stop**. Pașii intră în rutină într-un grup „Înregistrare pe ecran HH:MM”, ca pași 🖱 pe ecran.
5. Rulezi cu **▶ Rulează** (F7). **Pauză** = F8, **Stop** = F9, **STOP URGENȚĂ** = F12. Pentru repetări pui grupul într-un bloc **🔁 Repetă**; pentru valori din Excel, într-un **📊 Pentru fiecare rând** (și schimbi textul pasului „Scrie” cu `{Rand.Coloana}`).
6. Sistemul de prevenție verifică și pașii pe ecran: dacă la rulare click-ul ar ajunge în altă aplicație sau zona arată diferit, rutina se oprește și te întreabă.

> Exemplu: selectează ultimul pas, apasă ⏺ Ecran, deschide Notepad, scrie „Test”, apasă F6. În rutină apare grupul cu click-urile și pasul „Scrie "Test"”.

> Atenție: pașii pe ecran lucrează pe coordonate. Dacă fereastra se mută sau rezoluția se schimbă, click-ul nimerește altundeva. Unde se poate, folosește pași pe obiecte (🎯 Spy, ⏺ Web).

## 3. Pași pe ecran: editare și ce s-a mutat din Recorder

- Un pas 🖱 pe ecran se editează în dreapta, ca orice pas: **X / Y**, tastele, textul, așteptarea dinainte / după, comentariul. Titlul arată ce face și în ce fereastră („Click (420, 310) · Notepad”).
- Grupul înregistrat se poate redenumi, dezactiva, muta cu mouse-ul sau duplica; pașii din el se mută, se șterg sau se dezactivează unul câte unul.
- Ce era în tab-urile Recorder-ului e acum în Studio: **Step Builder** → blocurile din 🧱 Pași; **Rutine** → 📋 Rutine și 🗂 Manager rutine; **Excel** → 📊 Pentru fiecare rând Excel; **Log** → ⏱ Cronologie și Log rulare (cu export Excel); **Setări** → butonul ⚙ din dreapta sus; **Ajutor** → 📖 Instrucțiuni. Repetările → blocul 🔁 Repetă; pauza dintre pași → ⚙ Rutina.
- Rutinele vechi ale Recorder-ului (`rutine_salvate\*.json`) se deschid cu **📂 Deschide**: se convertesc automat în pași pe ecran; fișierul vechi rămâne neschimbat.
- **Notițele** nu mai au tab: folosește câmpul **Comentariu / notiță** al pașilor și descrierea rutinei.

> Exemplu: 📂 Deschide → `rutine_salvate\Raport.json` → rutina apare în Studio cu pașii ei 🖱; salvează-o (💾) ca `.rpr.json`.

## 4. Siguranța la rulare

- **🌙 Nu deranja**: notificările Windows sunt oprite cât rulează sau înregistrează o rutină, ca să nu dai click pe ele din greșeală. La final revin singure.
- **Chenar pe ecran**: roșu + RUN la rulare, verde + REC la înregistrare, portocaliu la pauză. Chenarul nu se vede în capturi și nu primește click-uri.
- **🛡 Sistem de prevenție**: înainte de fiecare pas verifică dacă ai mișcat mouse-ul, dacă a apărut o fereastră de eroare, dacă aplicația nu răspunde sau dacă ecranul arată altfel decât la înregistrare. Atunci rutina se pune pe pauză și te întreabă: **Continuă / Reîncearcă / Sari / Oprește**.
- Le activezi din **⚙ Setări → 🛡 Siguranța la rulare**. Dacă notificările rămân oprite: **🔔 Repornește notificările acum**.

> Exemplu: pornește o rutină și mișcă mouse-ul în timpul ei — rutina se oprește și te întreabă dacă continui.

## 5. Studio RPR: ideea de bază

- O **rutină** e un arbore de pași: acțiuni (click, scrie, citește), condiții (Dacă), repetări, Excel, întrebări.
- Pașii lucrează pe **obiecte** (butoane, câmpuri, tabele) marcate o singură dată cu **Spy**, nu pe coordonate. Fiecare obiect are mai mulți **locatori** de rezervă: dacă unul nu mai merge, se încearcă următorul.
- **Variabilele** se scriu între acolade: `{Client}`, `{Rand.IBase}`, `{Azi}`.
- Ecranul Studio: stânga **🧱 Pași** (blocurile) și **📚 Bibliotecă** (obiectele); mijloc arborele rutinei; dreapta proprietățile pasului selectat; jos **Log** și **Variabile**.
- Click pe un bloc = îl adaugi după pasul selectat. Ca să-l pui **în interiorul** unui „Dacă” sau al unei bucle, selectează întâi ramura (ex. ▸ Atunci).

> Exemplu: deschide 📚 Exemple → „01 Învățare” și apasă ⏭ Pas cu pas de mai multe ori, urmărind fiecare bloc.

## 6. Prima rutină Web (pas cu pas)

[video:02_studio_web]

1. Studio → **📄 Nou**.
2. Bloc **🌐 Deschide browser**, adresa `https://the-internet.herokuapp.com/login`.
3. **🎯 Web** (Spy): mouse-ul peste câmpul Username (contur verde) și **click**. În fereastra „Obiect capturat” apasă **+ pas Scrie text**. Scrie valoarea `tomsmith`.
4. La fel pentru Password (`SuperSecretPassword!`) și butonul Login (**Salvează + pas Click**).
5. Spy pe mesajul de după login → **+ pas Citește**; în pas pune **Valoarea așteptată** `You logged into*`.
6. **💾 Salvează**, apoi **▶ Rulează**.

> Sfat: **⏺ Înregistrează Web** face pașii 3–4 automat: lucrezi normal în browser, iar fiecare click / text / opțiune devine un pas. Esc în browser sau ⏺ din nou = stop.

## 7. Spy Web și Înregistrare Web

- **🎯 Web**: dacă browserul nu e deschis, Studio te întreabă adresa. Mouse-ul peste element → contur verde → **click** = capturează; **Esc** = anulează.
- În „Obiect capturat”: numele (cum îl alegi în pași), tipul, site-ul, pagina, containerul și locatorii cu scor (verde 70+ stabil, galben acceptabil, roșu fragil). Debifează locatorii instabili (ex. un text care se schimbă).
- Dacă elementul există deja în bibliotecă, Studio îți propune să-l folosești pe cel existent.
- Browserul (Edge sau Chrome) se alege în **🌐 Setări Studio**. Profilul (login, cookie-uri) se păstrează între rulări.
- iframe-urile, tab-urile noi și popup-urile JavaScript sunt tratate automat.

> Exemplu: pe o pagină cu căutare, Spy pe câmp → „+ pas Scrie text” cu `{Termen}`, apoi Spy pe butonul Caută → „Salvează + pas Click”.

## 8. SAP GUI

[video:05_studio_sap]

1. Activează scripting-ul: SAP GUI → Options → Accessibility & Scripting → Scripting → **Enable scripting** (debifează avertismentele). Pe server, `sapgui/user_scripting` trebuie să fie TRUE.
2. Deschide SAP Logon și autentifică-te.
3. Primul pas al rutinei: **🟦 SAP: conectează** (gol = prima sesiune).
4. **🟦 SAP: tranzacție** cu `/nVA03` (închide tranzacția curentă și pornește VA03).
5. **🎯 SAP**: mouse-ul peste câmp (contur roșu) și **F2**. Dacă poziția nu se poate determina, dă click în câmp și apasă F2.
6. **🟦 SAP: tastă** (Enter, F3, F8, Shift+F4, Ctrl+S) și **🟦 SAP: bara de stare** (`S:` succes, `E:` eroare, `W:` avertisment).
7. Tabele: **SAP: citește celula** cu `rând|coloană` (ex. `0|MATNR`); tabelul se derulează singur până la rând.

> Exemplu: rutina 04 „SAP VA03” citește numerele de comandă din Excel și scrie starea în coloana Status.

## 9. Aplicații desktop Windows

[video:04_studio_desktop]

1. **🖥 Pornește aplicație** (`notepad.exe` sau `"C:\Program Files\App\app.exe" /param`) sau **🖥 Atașează fereastra** (`proces:notepad.exe` sau titlul ferestrei).
2. **🎯 Desktop**: mouse-ul peste element (contur verde) și **F2**; Esc = anulează.
3. Folosește obiectul în pași: Click, Scrie text, Citește, Alege din listă, Bifează.
- Înainte de fiecare click, fereastra aplicației e adusă în față și elementul e derulat în zona vizibilă. Dacă punctul ar fi acoperit de altă fereastră, click-ul se face fără mouse (UI Automation) sau pasul se oprește cu un mesaj — niciodată în altă fereastră.
- **Liste (conversații, e-mailuri)**: Spy capturează rândul întreg. Numele cu text variabil primesc un șablon, ex. `ListItem|Ion Popescu*` (`*` = orice text).
- **Mod direct** (în pas): acțiuni fără mișcarea mouse-ului, unde aplicația permite.

> Exemplu: rutina 05 „Desktop Notepad” pornește Notepad și scrie trei rânduri într-o buclă.

## 10. Biblioteca de obiecte

[video:06_biblioteca]

- Tab-ul **📚 Bibliotecă** arată toate obiectele, comune tuturor rutinelor: **Site → Pagină → Container → obiect**. Site-ul și pagina se completează singure din link-ul unde ai capturat obiectul.
- **Test**: înainte să folosești un obiect într-o rutină nouă, vezi câte elemente găsește fiecare locator (1 = bun, mai multe = ambiguu, 0 = nu găsește); obiectul e marcat pe ecran. Din rezultat îl adaugi direct ca pas.
- **Containere** (secțiune, tabel, RefList, formular): obiectele din ele sunt căutate doar în interior. Același buton „Salvează” din două secțiuni nu mai e confundat. La Spy, containerul e propus automat.
- **🌐 Site-uri**: un site cu mai multe link-uri (test, producție, alt client) — obiectele lui merg pe toate. **Copiază pentru alt site** duplică un obiect pentru alt sistem.
- Click dreapta pe obiect: testează, adaugă pas, mută în container, copiază, șterge. Căutarea filtrează după nume, tip, site sau etichetă.

> Exemplu: Spy pe secțiunea „Livrare” → tip „Container / secțiune”; apoi Spy pe butonul Salvează din ea → e pus automat în containerul Livrare.

## 11. Pașii (acțiunile)

- **Pe obiect**: Click, Dublu click, Click dreapta, Mouse deasupra, Scrie text (înlocuiește), Tastează text (adaugă), Golește câmpul, Apasă tasta, Alege din listă, Bifează / Debifează, Citește textul / valoarea / atributul, Marchează, Captură element.
- **Browser**: Deschide browser, Mergi la URL, Înapoi, Reîncarcă, Schimbă tab-ul, Răspuns la popup JS, Captură pagină, Închide browser.
- **SAP**: Conectează, Tranzacție, Trimite tastă, Bara de stare, Citește celulă, Număr rânduri.
- **Desktop**: Pornește aplicație, Atașează fereastra, Închide fereastra.
- În fiecare pas: **Așteaptă obiectul maxim (ms)**, **La eroare**, **Așteaptă înainte / după**, **Comentariu**, **Pas activ**.
- **▶ Testează pasul** execută doar pasul selectat, cu variabilele ultimei rulări.
- **🎯 Remarchează** (lângă ▶ Testează pasul): dacă pasul a găsit alt element, dai click pe cel corect (SAP / Desktop: F2). Alegi:
  - **Înlocuiește locatoarele**: obiectul își păstrează numele, deci toți pașii care îl folosesc caută elementul nou (fereastra spune câți sunt);
  - **Obiect nou doar pentru acest pas**: obiectul vechi rămâne neschimbat, pasul primește obiectul nou (în același folder).
  Pasul fără obiect primește direct un obiect nou. Biblioteca se salvează; apoi apasă din nou ▶ Testează pasul. Alt obiect existent se alege din lista „Pe ce obiect”.

> Exemplu: „Citește textul” pe mesajul de confirmare, salvat în variabila `Mesaj`, apoi „Log” cu `Am primit: {Mesaj}`.

## 12. Condiții, bucle și așteptări

- **🔀 Dacă / Altfel**: ramura „Atunci” rulează când condiția e adevărată, „Altfel” când e falsă. Condiții: obiectul există / nu există / e vizibil / e activ, textul obiectului, compară două valori, toate (ȘI) / oricare (SAU), NU.
- **🔁 Repetă**: de N ori, cât timp sau până când o condiție e adevărată; variabila `{Repetare}` = 1, 2, 3...
- **⏱ Așteaptă**: un număr de secunde sau până apare / dispare ceva (cu timp maxim).
- **🛡 Încearcă / La eroare**: dacă un pas din „Încearcă” eșuează, rutina nu se oprește, ci rulează „La eroare”; mesajul e în variabilă.
- **⏏ Ieși din buclă** și **⛔ Oprește rutina** (cu sau fără eroare).

> Exemplu: Dacă „Obiectul există: Buton_Accept_Cookies” → Atunci: Click pe el. Altfel: nimic.

## 13. Variabile

- Se folosesc oriunde între acolade: `{Client}`. Le definești în **⚙ Setări rutină** (valori de start) sau le creează pașii (Citește → „Salvează rezultatul în variabila”).
- **✎ Variabilă**: setează, adaugă la final, crește / scade, LITERE MARI / mici, înlocuiește text, șterge spațiile.
- Speciale: `{Azi}`, `{Acum}`, `{Acum:yyyyMMdd_HHmm}`, `{NewLine}`.
- Din Excel: `{Rand.TitluColoana}`, `{Rand.A}` (după literă), `{Rand.#}` (numărul rândului).
- Tab-ul **🔤 Variabile** de jos arată valorile după ultima rulare.

> Exemplu: Scrie text `Raport_{Acum:yyyyMMdd}` în câmpul de nume al fișierului.

## 14. Excel: o rutină pentru fiecare rând

[video:03_studio_excel]

1. Bloc **📊 Pentru fiecare rând Excel**: alege fișierul, foaia, rândul cu titluri, primul / ultimul rând, coloana cheie (rând gol = sfârșitul listei).
2. Pune pașii **în interiorul** blocului; folosește `{Rand.NumeColoana}`.
3. **📝 Scrie în Excel** (în interiorul buclei) scrie un rezultat în rândul curent (coloana se creează dacă lipsește) și poate colora celula.
4. **Coloana de status** primește OK / eroarea, iar rândurile se colorează verde / roșu. Cu „Salvează după fiecare rând” și „sari rândurile deja OK” poți relua o rulare întreruptă.
5. **📤 Exportă șablon Excel** (în panoul blocului): fișier nou cu coloana cheie (gol = `Id`) formatată ca text, deci zerourile din față și Id-urile lungi rămân cum le scrii, apoi coloanele din pașii **Scrie în Excel** (verzi) și statusul (gri). Are foaia *Instrucțiuni* și avertizează la un Id repetat. După salvare poți folosi șablonul ca fișier al buclei.
6. **Coloana cheie sub alt nume**: dacă rutina cere `Id`, iar fișierul are `ID`, `UEID`, `Cod` sau `Nr`, coloana e găsită și `{Rand.Id}` are valoarea ei. Spațiile, `_` și literele mari nu contează. La scriere nu se folosesc aceste nume: „Cod” citit din SAP nu ajunge peste coloana cu Id-ul.
7. **Verificare înainte de primul click**: rândurile cu date dar fără Id (lista se oprește la primul) și Id-urile repetate apar într-o întrebare: **Continui** sau **Opresc rutina**. La rularea programată se continuă și se notează în log.
- Formulele din fișier rămân intacte.

> Exemplu: fișier cu coloana `IBase`; în buclă: Scrie text `{Rand.IBase}` în câmpul de căutare, Click Caută, Citește statusul → Scrie în Excel în coloana `Rezultat`.

## 15. Întrebări, erori și valoarea așteptată

- **💬 Întrebare**: fereastră cu butoane alese de tine (ex. `Da, Nu, Sari`); răspunsul ajunge într-o variabilă. Poți stabili butonul care oprește rutina sau sare rândul Excel.
- **La eroare** (pe pas sau pe rutină): Întreabă-mă (Reîncearcă / Sari / Oprește), Oprește, Continuă (doar logează), Sari la următorul rând Excel.
- **Reîncercări automate** și **captură de ecran la eroare** se setează în ⚙ Setări rutină.
- **Valoarea așteptată** (la pașii Citește): dacă textul citit diferă, rutina se oprește și te întreabă. Acceptă variabile și `*` (ex. `S:*` = orice mesaj de succes SAP).

> Exemplu: Citește bara de stare SAP cu valoarea așteptată `S:*` — la orice eroare SAP rutina se oprește și îți arată mesajul.

## 16. Rulare și control

- **▶ Rulează** pornește rutina; aplicația se minimizează (opțional) și rămâne o bară mică de control.
- **⏭ Pas cu pas**: fiecare apăsare execută un singur pas — ideal pentru verificare.
- **Pauză / Reluare**: Ctrl+F11. **Stop**: Ctrl+F12.
- **📋 Log rulare**: fiecare pas cu ora, rezultatul și durata; erorile sunt roșii. **📤 Export Excel** salvează logul; **📂 Rezultate** deschide folderul cu capturi și loguri.
- Rulare fără interfață: `py -m rpr run "C:\cale\rutina.rpr.json" --var Client=Ion`.

> Exemplu: rulează o rutină nouă întâi cu ⏭ Pas cu pas și Marchează obiectul înainte de fiecare acțiune.

## 17. Programare automată

[video:07_programare]

1. Salvează rutina și apasă **🕒 Programează**.
2. Alege **când**: zilnic, în zilele lucrătoare, în anumite zile, o singură dată, la fiecare N minute sau la autentificarea în Windows; apoi ora (și data).
3. **✔ Creează programarea**: apare în Windows Task Scheduler, în folderul `AutoPilotDC` (fără drepturi de administrator). Același nume înlocuiește programarea.
4. Lista **Programări AutoPilot**: următoarea / ultima rulare și rezultatul; **▶ Rulează acum**, **🗑 Șterge**. Tab-ul **Istoric**: fiecare rulare programată (dublu click = log).
- La final apare un mesaj în colțul ecranului (verde / roșu). Calculatorul trebuie să fie pornit și tu autentificat.

> Exemplu: „Raport zilnic”, În zilele lucrătoare, ora 07:30.

## 18. Setări

- **⚙ Setări** (aplicație, butonul mic din dreapta sus): înregistrarea pe ecran (mișcări mouse), siguranța la rulare, shortcut-uri, **pornire cu Windows** (opțional direct în tray), butonul ✕ ascunde în tray, scurtătură pe Desktop, tema, video, **limba** (Română / English / Deutsch), backup. Limba și tema se aplică după repornire.
- **O singură limbă** pentru toată aplicația (⚙ Setări → 🌐 Limba): pe lângă interfață, în aceeași limbă se scriu logurile, coloana de status din Excel-ul rutinei (OK / EROARE / IN LUCRU), raportul rulării, rezumatul și documentația pregătirilor. La reluare, statusurile sunt recunoscute în orice limbă (ex. „IN PROGRESS” = „IN LUCRU”), deci un Excel început în română poate fi reluat după trecerea pe engleză.
- **🌐 Setări Studio**: browserul pentru pașii Web (Edge recomandat, Chrome), fără fereastră (doar pentru programări), minimizare la rulare, închide browserul, șterge profilul browserului (logout); plus mărimea textului, unde se salvează fișierele și aplicația pentru filme (capitolul 31).
- **⚙ Rutina**: politica la eroare, marcarea obiectelor, timeout implicit, pauză între pași, reîncercări, capturi, Nu deranja, prevenție, variabile.

> Exemplu: ⚙ Setări → Limba → English → Salvează setările → aplicația repornește în engleză.

## 19. Probleme frecvente

- **Lipsesc pachete la pornire**: apasă „Instalează acum” sau rulează INSTALEAZA.bat.
- **Edge nu pornește („Target page… has been closed”)**: închide ferestrele Edge rămase de la AutoPilot; aplicația reîncearcă și, la nevoie, pornește cu un profil temporar. Sau alege Chrome în 🌐 Setări Studio.
- **Obiectul nu e găsit**: apasă **Test** în Bibliotecă; dacă un locator dă 0, editează-l sau capturează din nou cu Spy. Verifică site-ul / pagina și containerul.
- **Click-ul ajunge în altă fereastră (Desktop)**: aplicația trebuie să fie deschisă și nu minimizată la nesfârșit; folosește „Mod direct” pentru butoane și rânduri de listă.
- **Fișierul Excel e blocat**: închide-l în Excel înainte de rulare.
- **SAP nu răspunde**: verifică scripting-ul (capitolul 8).
- **Pictograma din tray lipsește**: Setări → Pornire și tray arată starea; pe Windows 10/11 poate fi ascunsă sub săgeata ^.
- **Notificările rămân oprite**: Setări → 🔔 Repornește notificările acum.
- **„Nu deranja” nu pornește sau nu se oprește**: Setări → 🔍 Verifică Nu deranja (cu „test real” dacă vrei). Raportul arată versiunea Windows, setarea găsită și dacă Windows permite repornirea serviciului de notificări; e salvat și în `loguri\nu_deranja_diagnostic.txt`.

## 20. Fișiere, foldere și colegi

- Aplicația: folderul `AutoPilotDC_py` (îl poți copia sau aduce cu `git pull`). Rutinele Recorder: `rutine_salvate`, logurile: `loguri`.
- Studio: `%APPDATA%\AutoPilotDC\Studio` — `rutine`, `rezultate` (loguri, capturi), `obiecte.json` (biblioteca), `exemple`, `browser-profil`.
- Pentru un coleg: trimite fișierul `.rpr.json` și `obiecte.json` (sau exportă obiectele folosite); colegul rulează INSTALEAZA.bat o singură dată.
- Versiunea aplicației apare în bara de jos; noutățile sunt în `CHANGELOG.md`.

## 21. Video: înregistrarea ecranului

[video:08_video]

- **🎥** (bara de sus sau meniul din tray) pornește o înregistrare oricând, fără rutină — de exemplu ca să arăți unui coleg o procedură. Apasă din nou 🎥 sau **⏹ Stop** din bara mică ● REC (care nu apare în film). **⏸** pune filmul pe pauză.
- La oprire se deschide **editorul**: capitolele (pașii rutinei, rândurile Excel), **A ▸ / ◂ B** pentru o selecție, **✂ Taie A–B**, **💬 Text A–B** (un text pe ecran), **▦ Ascunde zona** (blur peste date personale), **⟦ Început / Sfârșit ⟧**, **scurtarea pauzelor** lungi. Filmul original rămâne neschimbat; **💾 Salvează** păstrează editările, **GIF** / **MP4** exportă.
- **⚙ Setări → 🎥 Video**: folderul filmelor, **film automat la fiecare rulare** (Studio), **câte un film pentru fiecare rând Excel**, și la rulările programate, capturi pe secundă, mărimea și calitatea.
- Filmele se fac din **capturi de ecran salvate doar când ecranul se schimbă** (fișiere `.apvid` mici). Cursorul și click-urile se desenează la redare. **🎬** din bara de sus deschide un film salvat.
- **Introducere și ieșire** (implicit pornite): filmul unei rulări începe cu un ecran cu numele rutinei și ora de start (3 s) și se termină cu un ecran cu rezultatul (✅ / ❌ și mesajul erorii), durata, pașii și rândurile Excel (4 s). Între ele rămâne ce s-a înregistrat. După ultimul pas filmul mai merge **2 s**, ca să prindă rezultatul lui, iar ultimul ecran se salvează la oprire; finalul nu se mai scurtează la „scurtarea pauzelor”. Duratele și oprirea lor: ⚙ Setări → 🎥 Video.
- MP4 are nevoie de pachetul `opencv-python` (opțional); GIF merge mereu.
- În bucla Excel, cu filmul pornit, fiecare rând primește în coloana **Film** linkul spre film și minutul la care începe rândul (coloana se schimbă sau se oprește din proprietățile buclei). Același link apare și în raportul rulării. Dublu-click pe un fișier `.apvid` (sau click pe link în Excel) îl deschide în player, fără să pornească aplicația.

> Exemplu: Setări → Video → bifează „film la fiecare rulare” și „câte un film pe rând Excel”; rulează rutina 03 — în folder apare câte un film pentru fiecare rând, cu capitole pentru fiecare pas.

## 22. Raportul Excel al rulării (dovada muncii)

1. **⚙ Setări rutină → 📊 Raport Excel al rulării**: bifează „Creează un raport Excel la fiecare rulare”.
2. Bifează **coloanele cu valori** (variabile, coloane din Excel-ul de intrare, valorile citite). Același lucru îl faci direct pe pas: **📊 Pune valoarea în raportul Excel al rulării** (la pașii care salvează o valoare și la „Setează variabila”).
3. Alege folderul (gol = `rezultate\rapoarte`) și ce intră în raport: coloana „Pași parcurși”, foaia „Pași” (fiecare pas, cu ora, rezultatul și regula), definiția rutinei.
4. Rulează. La final, în log apare `📊 Raport: ...`.
- Un rând pentru fiecare rând Excel sau repetare de pe primul nivel; fără bucle, un rând pentru toată rutina. Merge și fără un Excel de intrare.
- Fiecare rând are ora de start, durata, statusul, mesajul, valorile bifate, filmul (cu minutul în film) și captura erorii. Filmul apare când e pornit în ⚙ Setări → Video.
- Excel-ul de intrare primește în continuare statusul și ce scrii cu **📝 Scrie în Excel**.
- **Salvare din mers și cloud**: raportul se salvează după fiecare rând / repetare (cel mult o dată la câteva secunde), deci rămâne și dacă aplicația se blochează. Folderul raportului și folderul filmelor (⚙ Setări rutină → 🎥 Filmele rutinei) pot fi alese pe fiecare rutină; **☁ OneDrive** pune folderul în OneDrive-ul sincronizat, ca fișierele să ajungă singure în cloud. Un film întrerupt brusc se reface automat la deschidere, din cadrele deja salvate.

> Exemplu: listă cu numere unice. În buclă: dacă `{Rand.Data}` e gol, citești data din link, o formatezi și o scrii; altfel apeși butonul Y. Bifează `Rand.Nr`, `DataCitita` și `Actiune` pentru raport. Raportul arată, pentru fiecare număr, ce s-a făcut, când și unde în film.

## 23. Manager de rutine și pregătiri

1. **📂 Manager rutine** (bara Studio): rutinele din folderul setat, citite la pornirea aplicației. **Schimbă folderul** alege alt folder (ex. un folder din Drive).
2. Din listă: **Deschide în Studio**, **▶ Rulează** sau **➕ Adaugă în pregătire**.
3. O **pregătire** e o listă de rutine rulate una după alta: ordinea cu ▲ ▼, „Rulează / Omite” și ce se întâmplă la eroare (oprește sau continuă cu următoarea).
4. Bifează **🎥 Film pentru fiecare rutină** și **📊 Raport Excel pentru fiecare rutină**, apoi **💾 Salvează** (fișierul `Nume.pregatire.json` din folderul rutinelor).
5. **▶ Rulează pregătirea**. Pauză / STOP din bara plutitoare (Ctrl+F11 / Ctrl+F12); întrebările și sistemul de prevenție rămân active.
- La final: un folder `rezultate\pregatiri\Nume_data_ora` cu `Pregatire_Nume.xlsx` (rezumat și definiții), `Documentatie.html` (tot ce s-a făcut, în detaliu), rapoartele și linkurile spre filme.
- O pregătire se poate programa ca o rutină: `py -m rpr run "Sandbox.pregatire.json"`.

> Exemplu: sandbox de test cu `01_Useri`, `02_Roluri`, `03_Obiecte`. Rulezi pregătirea seara; dimineața deschizi documentația și vezi pentru fiecare rutină cât a durat, ce a creat și filmul ei.

## 24. Backup și restaurare

1. **⚙ Setări → 💾 Backup și restaurare → Creează backup...**: alegi unde se salvează fișierul `.zip` (ex. un stick sau un folder din Drive).
2. Bifează „Include și rezultatele” doar dacă vrei și rapoartele, logurile Studio și capturile erorilor (fișierul crește).
3. Pe alt PC sau după o reinstalare: **♻ Restaurează din backup...**, alegi fișierul, confirmi, apoi repornești AutoPilot DC.
- Intră: setările, rutinele Recorder și Studio, biblioteca de obiecte cu imaginile ei, programările, notițele, limba, setările video și folderul rutinelor din 📂 Manager.
- Nu intră: profilul browserului (login-urile) și filmele.
- Înainte de restaurare, starea curentă se salvează automat în `%APPDATA%\AutoPilotDC\backup-automat`. Dacă folderul rutinelor nu există pe PC-ul nou, rutinele ajung în `Studio\rutine\biblioteca`, iar Managerul e mutat acolo.

> Exemplu: înainte de schimbarea laptopului creezi un backup în Drive; pe laptopul nou instalezi cu INSTALEAZA.bat, apoi restaurezi backup-ul și ai aceleași rutine, obiecte și setări.

## 25. Reluare după o închidere neașteptată

1. Cât timp o rutină lucrează pe un rând Excel, coloana de status arată „IN LUCRU” (portocaliu); la final devine OK sau EROARE.
2. Dacă AutoPilot DC sau PC-ul se închide în mijlocul unei rulări, la următoarea pornire apare întrebarea **Reluare după închidere**: **Reiau rularea**, **Doar deschid** sau **Nu, renunț**.
3. La reluare, rândurile cu OK sunt sărite. Pentru rândul rămas „IN LUCRU” alegi: **Refac rândul**, **E făcut, marchez OK** (dacă ai verificat în sistem) sau **Opresc rutina**.
- La o pregătire se sar și rutinele deja terminate; rutina întreruptă continuă de la rândul ei.
- Aceeași întrebare apare și când pornești din nou rutina de mână, dacă un rând a rămas „IN LUCRU” (ex. după STOP).
- Rularea pas cu pas nu se reia. Dacă închizi tu aplicația în timpul rulării, nu se oferă reluarea.

> Exemplu: rutina creează 200 de useri și se oprește curentul la rândul 120. La repornire alegi „Reiau rularea”; rândurile 2–119 sunt sărite, verifici în sistem userul de pe rândul 120 și alegi „E făcut, marchez OK” sau „Refac rândul”.

## 26. Scanarea unui site și biblioteca pe aplicație

1. 📚 Biblioteca → **＋ Noua**: scrii numele aplicației; AutoPilot propune `OneDrive\AutoPilotDC\obiecte\<Aplicație>\obiecte.json` (fără OneDrive: în Documente). Poți alege orice alt folder.
2. **🔍 Scaneaza site**: scrii adresa, se deschide browserul AutoPilot. Te autentifici și deschizi pagina dorită, apoi alegi **🔍 Scaneaza automat**.
3. Primești lista cu butoanele, câmpurile, listele, bifele și link-urile vizibile (și din iframe-uri, maxim 500). Click pe un rând îl **marchează în browser** (ca să vezi ce buton e); bifa din prima coloană îl ține sau îl scoate (sau Space / **☑ Tine / scoate**). **✎ Redenumeste** (F2, dublu-click pe nume) schimbă numele. Sus alegi **Pagina** și **Folderul** sub care intră (vezi capitolul 28). **Fara link-uri** scoate meniurile de navigare. **💾 Adauga in biblioteca** le salvează.
4. Deschizi alt meniu sau alt tab în browser și alegi **🔍 Scaneaza din nou**. Obiectele deja în bibliotecă sunt sărite.
5. **🖐 Captura 3 s**: ții cursorul 3 secunde pe un câmp sau buton (contur albastru, numărătoare inversă) și se salvează singur; apoi treci la următorul. Click-urile merg normal, deci poți deschide meniuri. Esc în browser sau **Am terminat** oprește.
- Scanarea doar citește pagina deja încărcată: nu dă click, nu scrie și nu trimite nimic la server, deci nu încarcă aplicația. Elementele ascunse (meniuri închise, alte taburi) nu se văd până nu le deschizi tu.
- **📂 Deschide** schimbă biblioteca. Rutina salvată ține minte biblioteca ei și o încarcă singură la deschidere; aplicația ține minte doar calea ultimei biblioteci.
- Dacă pe celălalt laptop OneDrive are altă cale, biblioteca e găsită la același loc din OneDrive-ul de pe acel PC.

> Exemplu: pentru aplicația de comenzi creezi biblioteca „Comenzi” în OneDrive, scanezi pagina de căutare și formularul de comandă, apoi cu Captura 3 s adaugi butonul din meniul care apare doar la hover. Rutinele noi pentru această aplicație folosesc biblioteca „Comenzi”.

## 27. Verifică butoanele salvate (simulare fără click)

1. Deschide în browserul AutoPilot pagina aplicației (te autentifici, deschizi meniul / tabul unde sunt butoanele).
2. 📚 Biblioteca → **🩺 Verifica** (sau, după 🔍 Scaneaza site, alegi **🩺 Verifica butoanele salvate**). Dacă site-ul are obiecte și pe alte pagini, alegi **Pagina curenta** sau **Tot site-ul**.
3. Pentru fiecare obiect, AutoPilot face un „click de probă”: aceleași verificări ca la un click real (îl găsește, e vizibil, e activ, nu se mișcă, nu e acoperit de altă fereastră), dar **nu apasă** și nu trimite nimic la server.
4. Primești lista: **✅** merge · **⚠** merge, dar cu impedimente (acoperit de un overlay, dezactivat, găsit de mai multe ori, merge doar locatorul de rezervă, alt text) · **❌** trebuie recaptat · **·** e pe altă pagină. Click pe un rând arată motivele.
5. **👁 Arata in browser** marchează elementul. **🔧 Repara locatorii** pune primul locatorul care merge. **🎯 Recapteaza**: dai click pe element în browser; numele rămâne, deci rutinele care îl folosesc merg mai departe. **🔄 Verifica din nou** după ce ai schimbat ceva în browser.
- Click-ul de probă poate derula pagina până la element, dar nu apasă nimic. Un buton care apare doar după o acțiune (meniu, tab, filtru) se verifică după ce îl deschizi tu.
- La un element ⚠ „Acoperit”, de obicei o fereastră sau un mesaj stă peste el: închide-l și verifică din nou. Dacă rămâne, rutina are nevoie de un pas înainte (închide mesajul).

> Exemplu: după o actualizare a aplicației, deschizi pagina de comenzi și apeși 🩺 Verifica. „Salveaza” e ✅, „Trimite” e ⚠ dezactivat (normal până completezi formularul), iar „Export” e ❌: îl recaptezi dintr-un click și rutina de export merge din nou.

## 28. Foldere în bibliotecă (secțiuni sub aceeași pagină)

Unele aplicații web își schimbă „folderele” (meniul, arborele din stânga) fără să schimbe adresa: tot `…/otwg20`. Ca să nu ai toate butoanele la comun, pui fiecare obiect într-un **folder cu nume**:

1. La **🔍 Scaneaza site**, în fereastra cu rezultate alegi sus **Pagina** și **Folderul** (ex. `Comenzi/Export`; `/` face subfoldere). Folderele deja folosite apar în listă. Ultimul folder ales îl folosește și **🖐 Captura 3 s**.
2. În bibliotecă arborele devine **Site · Pagină · 📁 Folder · buton**.
3. Pentru un obiect existent: click dreapta → **📁 Muta in folder...** sau câmpul **Folder** din **Editeaza**.
4. Click dreapta pe un folder: **✎ Redenumeste folderul...** (schimbă și subfolderele) și **🩺 Verifica obiectele folderului**.
- **Redenumire pagină / site**: click dreapta pe 📄 pagină (sau 🌐 site) → **✎ Redenumeste pagina...**; se schimbă pentru toate obiectele de sub ea. Dacă noul nume există deja, paginile se unesc.
- Folderul doar grupează. Nu schimbă unde se caută elementul pe pagină (asta face **Containerul**). Rutinele nu se schimbă: pașii folosesc tot numele obiectului.
- Ferestrele (obiect, scanare, verificare, programare) se derulează cu roata mouse-ului, iar butoanele **Salveaza / Adauga / Inchide** rămân fixe jos, deci nu mai trebuie să le măreșți.

> Exemplu: în aplicația de comenzi, folderul `Comenzi/Import` are butoanele „Încarcă fișier” și „Validează”, iar `Comenzi/Export` are „Export Excel”. Deschizi folderul în aplicație, scanezi, alegi folderul și butoanele intră la locul lor.

## 29. Rutine salvate ca pas (tab 📋 Rutine)

Ai deja o rutină de 2–3 pași (ex. autentificarea) și vrei s-o folosești în altele, fără să refaci pașii:

1. În **Studio RPR**, lângă **📚 Biblioteca**, deschide tab-ul **📋 Rutine**: arată rutinele din folderul tău (același ca în **📂 Manager rutine**; **📁 Folder** îl schimbă, **↻** citește din nou, câmpul de sus caută).
2. Alege o rutină și apasă **➕ Ca pas** (sau dublu-click): se adaugă pasul **📋 Ruleaza rutina**, care **urmărește fișierul**. Schimbi rutina o dată și merge în toate locurile unde e folosită.
3. Pune pașii tăi înainte și după. Ruleaza rutina folosește **aceleași variabile, același Excel și aceeași bibliotecă de obiecte**; setările rutinei principale (erori, pauze) se aplică și ei. Variabilele cu valoare implicită din rutina apelată se iau doar dacă nu există deja.
4. **📥 Ca pasi** copiază pașii în rutina curentă (îi poți edita; nu mai urmăresc originalul). La un pas existent, **📥 Inlocuieste cu pasii ei** face aceeași copie.
- Înainte de start se verifică fișierul, buclele (A apelează B, B apelează A), adâncimea (maxim 8) și obiectele lipsă; dacă ceva nu merge, rutina nu pornește și ți se spune care pas. În log, pașii calupului apar cu numele lui în față.
- Dacă mutați fișierul rutinei, pasul trebuie să arate din nou spre el (câmpul fișier din pas).

> Exemplu: `Login SAP` (2 pași) e salvată în folderul rutinelor. În rutina de raport: ➕ Ca pas „Login SAP”, apoi pașii raportului.

## 30. „Daca apare” și reguli pentru mesaje / erori

Uneori apar mesaje sau erori pe care le știi dinainte (ex. „Sigur vrei să închizi?”). Nu trebuie să încurce rutina când nu apar.

**👁 Daca apare (optional)** (Flux): pui pasul unde poate apărea mesajul, alegi elementul (în **Conditia**, cu **Asteapta obiectul maxim** de ex. 1500 ms) și pașii care trebuie făcuți în ramura „Atunci”. Dacă mesajul nu apare, rutina merge mai departe fără eroare.

**🧯 Regula la mesaj / eroare** (Flux): o pui **înaintea** pașilor pe care îi acoperă (primul pas = pe toată rutina). Ea nu face nimic singură: se armează și rămâne activă până la sfârșitul listei în care stă (într-un Grup, doar în Grup). Când un pas **eșuează** și regula se potrivește, se rulează pașii din „Pasi de rulat”:
1. **Daca eroarea contine textul**: o parte din mesajul erorii (fără diferență între litere mari și mici) și / sau
2. **SAU un element / o condiție e adevărată pe ecran** (ex. fereastra de mesaj e deschisă);
3. **Dupa ce ruleaza pasii regulii**: *reia pasul* (implicit; maxim de 3 ori), *consideră pasul rezolvat* sau *eroarea merge mai departe*.
- Mesajul erorii e în variabila `{EroareRegula}`. Mai multe reguli: se verifică întâi cea mai apropiată de pas.
- Regulile se verifică doar când un pas pică; dacă mesajul nu vine, nu se întâmplă nimic. Pașii din regulă nu declanșează alte reguli.
- Browserul: ferestrele de tip alert / confirm ale paginii se acceptă automat (pasul „Handle dialog” alege „dismiss”). Un mesaj din pagina aplicației e un element: îl tratezi cu **Daca apare** sau cu o regulă.
- Pentru mesaje alege condiția **Obiectul e vizibil** (un mesaj ascuns „există” în pagină, dar nu se vede).
- **Demo**: butonul **Exemple** → **06 Demo - Daca apare si reguli la mesaj** (o pagină locală, fără internet): apeși „Porneste”, apare „Sigur vrei să continui?”, regula îl închide singură, iar „Daca apare” trece mai departe când mesajul lipsește. Rulează-l cu **⏭ Pas cu pas** ca să vezi fiecare pas.

> Exemplu: la începutul rutinei, **🧯 Regula** cu „Sigur” și pasul Click pe „Da, închide”, apoi *reia pasul*; dacă mesajul nu apare, rutina rulează ca până acum.

## 31. Aspect, drag and drop și unde se salvează fișierele

**🌐 Setări Studio** are acum patru tab-uri: 🌐 Browser, 🎨 Aspect, 📁 Unde se salvează, 🎬 Filme.

- **🎨 Aspect → Mărimea textului**: Mic / Normal / Mare / Foarte mare, pentru toată aplicația (se aplică la repornire). Lățimea panourilor Studio se ține minte ca procent din fereastră, deci arată la fel pe laptop și pe monitor; **↺ Panouri ca la început** le readuce la împărțirea inițială.
- Pe ecrane mici bara de sus rămâne pe un rând: butoanele pierd o parte din text (textul întreg e în tooltip), iar comenzile rare (Salvează ca…, Exemple, Programează, Ghid) sunt în **⋯**.
- **Drag and drop**: tragi un pas din arbore în alt loc (o linie arată unde ajunge; peste „▸ Atunci” / „▸ Altfel” sau peste mijlocul unei bucle intră în interior). La fel tragi un bloc din 🧱 Pași, un obiect din 📚 Bibliotecă (alegi Click / Scrie text / Citește / Dacă există) sau o rutină din 📋 Rutine (devine pas „Rulează rutina”).
- **📁 Unde se salvează**: alegi un **folder comun** (de ex. ☁ OneDrive); rutinele, bibliotecile de obiecte, rezultatele (capturi, loguri, rapoarte) și filmele ajung în subfolderele `rutine`, `obiecte`, `rezultate`, `filme`. Un câmp completat pentru un fel de fișiere are prioritate; ce setezi pe o rutină (folderul filmelor / raportului) sau pe o bibliotecă are prioritate față de toate. Câmpurile goale = ca până acum.
- **🎬 Filme → Deschide filmele cu**: playerul AutoPilot (redare + editare), aplicația implicită din Windows sau altă aplicație de pe laptop (ex. VLC). Pentru alte aplicații filmul se exportă o dată în MP4, lângă el (GIF dacă lipsește opencv-python). Aceeași alegere e și în ⚙ Setări → Video.

> Exemplu: 🌐 Setări Studio → 📁 Unde se salvează → ☁ OneDrive → Salvează; rutina nouă salvată cu 💾 propune folderul `OneDrive\AutoPilotDC\rutine`, iar filmele ajung în `OneDrive\AutoPilotDC\filme`.

## 32. Bara de activități, tab-uri, cronologie, ecranul Excel și fluxul

Studio are o **bară de activități** în stânga: 🧱 Pași, 📚 Bibliotecă, 📋 Rutine, 🎬 Filme, iar jos 🌐 Setări și ❓ Ghid. Fiecare iconiță schimbă doar panoul de lângă ea; rutina rămâne pe loc. Un click pe iconița deja aleasă **strânge panoul** (mai mult loc pentru rutină pe un laptop); încă un click îl redeschide. Aplicația ține minte panoul ales.

- **Tab-uri pentru rutine**: fiecare rutină deschisă are tab-ul ei deasupra pașilor (● = modificări nesalvate). **+** sau 📄 Nou deschide o rutină nouă într-un tab nou; × închide tab-ul (te întreabă dacă vrei să salvezi). O rutină deja deschisă nu se deschide de două ori: se arată tab-ul ei. Cât rulează o rutină nu poți schimba tab-ul.
- **Vederea din centru**: **✎ Pași** (lista, pentru editare), **🔀 Flux** (rutina ca flux de carduri, cu „Atunci” și „Altfel” una lângă alta; doar citire: click pe un card arată proprietățile pasului în dreapta, dublu-click te duce la pas în listă) și **📊 Excel**.
- **🔀 Flux la rutine mari** (v4.20): **Ctrl + rotița** (sau **−** / **+**) mărește și micșorează în jurul mouse-ului; **trage pe fundal** (sau cu rotița apăsată) ca să muți „harta”; **⤢ Potrivește** (Ctrl + 0) pune toată rutina pe ecran, **↔ Lățime** (Ctrl + 2) toată lățimea, iar tu derulezi doar în jos; **1:1** (Ctrl + 1) = mărimea normală. **🗺 Harta** din colț arată toată rutina și unde ești: click sau trage pe ea ca să sari acolo. **▾ / ▸** pe un card Dacă / Buclă îi ascunde ramurile („+N” = câți pași sunt ascunși); **▸ Restrânge tot** / **▾ Extinde tot** pentru toate. Un pas ales în listă se deschide singur. **⬇ Export** salvează fluxul ca **PNG** mare (de 2 ori mai clar decât pe ecran) sau **SVG** (se deschide în browser și se mărește oricât); ramurile restrânse rămân restrânse și în imagine. (v4.21) **🗗 Fereastră separată** deschide fluxul în fereastra lui: o muți pe al doilea monitor, **⛶ Ecran complet** (F11, Esc = ieși), și urmărești rularea pe culori (galben = rulează, verde = reușit, roșu = eroare), chiar dacă Studio trece pe 📊 Excel.
- **📊 Excel**: rândurile fișierului din primul pas „Pentru fiecare rând Excel”, cu statusul și minutul din film. Când rulezi o rutină cu Excel, ecranul acesta se deschide singur și arată rândul în lucru. Alegi un rând: în dreapta vezi pașii lui, eroarea și captura ei; **↻ Reia rândul** rulează din nou doar acel rând (și pașii de dinaintea buclei, de ex. deschiderea browserului), **🎬 Vezi în film** deschide filmul rulării la minutul rândului (dacă filmarea la rulare e pornită din Setări → Video).
- **⏱ Cronologie** (jos, lângă Log): un card pentru fiecare pas terminat, cu ✓ / ✕, rândul Excel, durata și, la erori, mesajul și captura ecranului (dublu-click pe captură o deschide mare). Click pe un card arată pasul în rutină.
- **🎬 Filme**: filmele salvate, cele mai noi primele; dublu-click le deschide cu aplicația aleasă în 🌐 Setări Studio → 🎬 Filme.

> Exemplu: deschide **Exemple → 03 Web + Excel**, apasă ▶ Rulează. Centrul trece pe 📊 Excel și colorează fiecare rând (verde OK, roșu eroare). Alegi un rând roșu, citești eroarea în dreapta și apeși ↻ Reia rândul.

## 33. 📥 Import AI: rutină dintr-un document Word

Ai procedura într-un document Word. Un AI (ChatGPT, Copilot, Claude...) o transformă în **pași AutoPilot**, un text simplu cu un pas pe rând, iar Studio face din el rutina.

1. În Studio apasă **📥 Import AI** (bara din stânga sau **⋯ → 📥 Importă pași**).
2. **📋 Copiază promptul pentru AI** și lipește-l în AI; apoi lipește textul procedurii (sau atașează documentul Word). Promptul explică formatul și regulile, în limba aplicației (**💾 Salvează promptul** îl păstrează ca fișier).
3. Răspunsul AI-ului îl lipești în fereastra de import (sau **📂 Deschide fișier**: `.txt`, `.json`, `.rpr.json`). Verificarea se face singură: în dreapta vezi pașii, jos problemele; rândurile greșite se colorează (click pe problemă = rândul).
4. **✅ Creează rutina**: rutina se deschide într-un tab nou (nesalvată). Butoanele și câmpurile noi intră în 📚 Bibliotecă, găsite după textul de pe ecran.
5. **🎯 Completează obiectele** (propus imediat după import; oricând din 📚 Bibliotecă → 🎯 Completează sau ⋯ → 🎯 Completează obiectele rutinei): lista obiectelor rutinei, în ordinea pașilor. Deschide pagina în browser (sau rulează ⏭ Pas cu pas până acolo) și apasă **🧪 Verifică toate**: fără click, fiecare primește ✔ găsit, ⚠ mai multe elemente la fel sau ✖ negăsit. Pe cele cu ✖ / ⚠ apasă **🎯 Marchează în browser** (sau dublu-click) și dă click pe element (SAP / Desktop: F2): obiectul primește locatoarele capturate (id, css, xpath, frame), textul vechi rămâne de rezervă, iar numele și pașii rutinei nu se schimbă. **⏭ Următorul negăsit** trece la următorul de marcat. Obiectele cu `{variabile}` se verifică la rulare. **▶ Rulează și marchează**: pentru obiectele de pe alte tab-uri sau secțiuni, rutina rulează de la început, doar pe primul rând din Excel, și deschide singură tab-urile. Când un obiect nu e găsit, rularea se oprește: **🎯 Marchează acum**, click pe element, iar pasul se reia. Pașii se fac de-adevăratelea (Save, Trigger…), deci folosește un rând de test. Apoi completează variabilele în ⚙ Rutina, rulează **⏭ Pas cu pas**, apoi salvează (💾). Programarea automată: 🕒 Programează.

Formatul (cuvinte cheie în română sau engleză, fără diferență mare / mică):

- Antet: `RUTINA: <nume>`, `DESCRIERE: <text>`, `VARIABILA: Nume = valoare`.
- Pași: `DESCHIDE BROWSER <url>`, `MERGI LA <url>`, `CLICK <obiect>`, `SCRIE <obiect> = <text>`, `ALEGE <obiect> = <opțiune>`, `BIFEAZA <obiect>`, `APASA Enter`, `CITESTE <obiect> -> {Var}`, `ASTEAPTA 2` sau `ASTEAPTA <obiect> MAX 15`, `LOG "text"`, `INTREABA "text"`, `MANUAL "ce face omul"`, `SAP TRANZACTIE /nVA03`, `PORNESTE APLICATIE notepad.exe`.
- Blocuri: `DACA <condiție>` … `ALTFEL` … `SFARSIT`, `REPETA 3` … `SFARSIT`, `PENTRU FIECARE RAND {Fisier} FOAIE Date` … `SFARSIT` (valori: `{Rand.Coloana}`, scriere: `SCRIE IN EXCEL Rezultat = OK`), `INCEARCA` … `LA EROARE` … `SFARSIT`.
- `DACA` … `ALTFEL` … `SFARSIT` are **un singur** `SFARSIT`, după ramura `ALTFEL`. Un `DACA` (sau `DACA APARE`) din interiorul altui `DACA` se închide cu propriul `SFARSIT`. Mai multe variante: `ALTFEL DACA <condiție>`, tot cu un singur `SFARSIT` la final. `DACA APARE <obiect>` acceptă și `ALTFEL`. Eroarea „ALTFEL după SFARSIT” spune rândul `SFARSIT`-ului de șters.
- `INTREABA VALOARE "text" -> {Var}`: la rulare apare un câmp de tastat, iar valoarea intră în variabilă (ex. o dată luată din alt sistem). **Anulează** oprește rutina. În Studio: pasul 💬 Întrebare cu bifa „Câmp de tastat”.
- Variabilele merg și în textul obiectelor: `CLICK text "{Rand.UEID}"` caută la fiecare rând valoarea din Excel (biblioteca păstrează `{Rand.UEID}`).
- `VARIABILA:` din antet dă valoarea de start; în interiorul unui bloc devine pasul `SETEAZA`.

**Sursa poate fi și cod** (C#, VBA, Python, Selenium, SilkTest, UiPath) sau o procedură cu poze. Promptul cere AI-ului să păstreze selectorii din cod (`id`, `css`, `xpath`, `sap`), să folosească obiectele deja din 📚 Bibliotecă (promptul copiat conține lista lor) și să marcheze cu `# TODO: …` locurile unde intervii tu (selector ghicit, valoare din alt sistem, decizie neclară). La import, fiecare `# TODO` apare în galben în lista de probleme (nu blochează crearea) și rămâne în comentariul pasului (💬 în arbore). Un răspuns lung, continuat în mai multe mesaje, se lipește întreg: blocurile de cod se unesc. Obiectele scanate sau marcate cu 🎯 Spy se refolosesc și după textul lor, cu toate locatoarele.
- Obiecte: `buton "Salvează"`, `camp "Utilizator"`, `link "..."`, `lista "Țara"`, `bifa "..."`, `text "..."`, `css "#id"`, `sap "wnd[0]/usr/..."`, `desktop "Nume"` sau `[Nume]` din bibliotecă.
- Condiții: `{Var} = "x"`, `{Var} contine "x"`, `vizibil buton "OK"`, `exista [Nume]`, combinate cu `SI` / `SAU`.
- Se acceptă și o rutină completă `.rpr.json`. Ce nu se poate automatiza devine `MANUAL`: rutina se oprește și așteaptă Continuă.

> Exemplu: în fereastra de import apasă **📝 Exemplu**: apare o procedură de introducere a comenzilor dintr-un Excel; în dreapta vezi rutina cu bucla și condiția; ✅ Creează rutina o deschide în Studio.
