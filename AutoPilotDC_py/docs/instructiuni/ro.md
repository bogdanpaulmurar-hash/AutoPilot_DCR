# Instrucțiuni AutoPilot DC

Fiecare capitol explică pe scurt o procedură, pas cu pas, cu un exemplu. Alege capitolul din stânga sau caută un cuvânt.

## 1. Pornire și interfață

- Pornești aplicația cu **AutoPilot_DC.pyw** din folderul `AutoPilotDC_py` sau cu scurtătura „AutoPilot DC” de pe Desktop (fără fereastră CMD).
- Prima dată (sau pe un laptop nou) rulează **INSTALEAZA.bat**: instalează tot ce trebuie, fără drepturi de administrator. Fereastra rămâne deschisă până apeși o tastă.
- Sus ai comutatorul de zone: **🎬 Recorder** (pe coordonate de ecran), **🧩 Studio RPR** (pe obiecte), **📖 Instrucțiuni** (aici).
- Butoanele de sub comutator se schimbă după zona deschisă și trec pe rândul următor când fereastra e îngustă.
- **🚨 STOP URGENȚĂ** (sau F12) oprește imediat orice rulare.
- Pictograma de lângă ceas (tray): click = deschide aplicația; click dreapta = Recorder, Studio, STOP URGENȚĂ, Ieșire.

> Exemplu: deschide aplicația, apasă 🧩 Studio RPR, apoi 📚 Exemple și deschide „01 Învățare”.

## 2. Recorder: înregistrare și redare

[video:01_recorder]

1. În zona **🎬 Recorder** apasă **⏺ Înregistrează** (F5).
2. Fă acțiunile pe ecran (click-uri, text, taste). Pe margini apare un chenar verde **REC**.
3. Apasă **⏹ Stop Rec** (F6). Pașii apar în listă.
4. Alege numărul de **Repetări** și apasă **▶ Rulează** (F7). Chenarul devine roșu **RUN**.
5. **Pauză** = F8, **Stop** = F9, **STOP URGENȚĂ** = F12.
6. **💾 Salvează** (Ctrl+S) păstrează rutina în `rutine_salvate`; o redeschizi din tab-ul **📁 Rutine** (dublu click).

> Exemplu: înregistrează deschiderea Notepad și scrierea „Test”, setează Repetări = 3, apoi Rulează.

> Atenție: Recorder-ul lucrează pe coordonate. Dacă fereastra se mută sau rezoluția se schimbă, click-ul nimerește altundeva. Pentru rutine stabile folosește Studio.

## 3. Recorder: Step Builder, editare, depanare

- **🔧 Step Builder**: adaugi pași unul câte unul (tip, coordonate, taste, text, pauză, întrebare către utilizator). **📍 Capturează poziția mouse-ului** îți dă coordonatele în 3 secunde.
- Dublu click pe un pas = editare. **▲/▼** mută pasul, **⊘ Skip** îl sare la rulare.
- **🐛 Debug pas** execută un singur pas ca test; **🔍 Simulează** arată ce ar face, fără să facă.
- **📊 Excel**: rulezi aceeași rutină pentru fiecare valoare dintr-un interval Excel (ex. `A1:A100`).
- **📋 Log** păstrează fiecare rulare; îl exporți în XLSX / CSV / JSON. **📝 Notițe** e un carnet simplu.

> Exemplu: în Step Builder adaugă „Scriere text” cu `{valoare}`, apoi în tab-ul Excel alege fișierul și intervalul `A2:A20`.

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

- **⚙ Setări** (aplicație): delay și viteză la redare, countdown, înregistrarea mișcărilor, siguranța la rulare, shortcut-uri, **pornire cu Windows** (opțional direct în tray), butonul ✕ ascunde în tray, scurtătură pe Desktop, **limba** (Română / English / Deutsch) și tema. Limba și tema se aplică după repornire.
- **🌐 Setări Studio**: browserul pentru pașii Web (Edge recomandat, Chrome), fără fereastră (doar pentru programări), minimizare la rulare, închide browserul, șterge profilul browserului (logout).
- **⚙ Setări rutină**: politica la eroare, marcarea obiectelor, timeout implicit, pauză între pași, reîncercări, capturi, Nu deranja, prevenție, variabile.

> Exemplu: Setări → Limba → English → Salvează setările → aplicația repornește în engleză.

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
- **⚙ Setări → 🎥 Video**: folderul filmelor, **film automat la fiecare rulare** (Studio și Recorder), **câte un film pentru fiecare rând Excel**, și la rulările programate, capturi pe secundă, mărimea și calitatea.
- Filmele se fac din **capturi de ecran salvate doar când ecranul se schimbă** (fișiere `.apvid` mici). Cursorul și click-urile se desenează la redare. **🎬** din bara de sus deschide un film salvat.
- MP4 are nevoie de pachetul `opencv-python` (opțional); GIF merge mereu.

> Exemplu: Setări → Video → bifează „film la fiecare rulare” și „câte un film pe rând Excel”; rulează rutina 03 — în folder apare câte un film pentru fiecare rând, cu capitole pentru fiecare pas.

## 22. Raportul Excel al rulării (dovada muncii)

1. **⚙ Setări rutină → 📊 Raport Excel al rulării**: bifează „Creează un raport Excel la fiecare rulare”.
2. Bifează **coloanele cu valori** (variabile, coloane din Excel-ul de intrare, valorile citite). Același lucru îl faci direct pe pas: **📊 Pune valoarea în raportul Excel al rulării** (la pașii care salvează o valoare și la „Setează variabila”).
3. Alege folderul (gol = `rezultate\rapoarte`) și ce intră în raport: coloana „Pași parcurși”, foaia „Pași” (fiecare pas, cu ora, rezultatul și regula), definiția rutinei.
4. Rulează. La final, în log apare `📊 Raport: ...`.
- Un rând pentru fiecare rând Excel sau repetare de pe primul nivel; fără bucle, un rând pentru toată rutina. Merge și fără un Excel de intrare.
- Fiecare rând are ora de start, durata, statusul, mesajul, valorile bifate, filmul (cu minutul în film) și captura erorii. Filmul apare când e pornit în ⚙ Setări → Video.
- Excel-ul de intrare primește în continuare statusul și ce scrii cu **📝 Scrie în Excel**.

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
