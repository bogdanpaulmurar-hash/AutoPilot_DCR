# AutoPilot DC — ce s-a schimbat

Pornirea aplicației: **`AutoPilot_DC.pyw`** (sau scurtătura „AutoPilot DC” de pe Desktop). Numele fișierelor nu se mai schimbă de la o versiune la alta, deci scurtăturile și pornirea cu Windows rămân valabile.

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
