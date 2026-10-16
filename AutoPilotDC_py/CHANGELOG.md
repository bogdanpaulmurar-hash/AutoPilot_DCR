# AutoPilot DC — ce s-a schimbat

Pornirea aplicației: **`AutoPilot_DC.pyw`** (sau scurtătura „AutoPilot DC” de pe Desktop). Numele fișierelor nu se mai schimbă de la o versiune la alta, deci scurtăturile și pornirea cu Windows rămân valabile.

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
