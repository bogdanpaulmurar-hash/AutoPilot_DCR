# AutoPilot DC — ce s-a schimbat

Pornirea aplicației: **`AutoPilot_DC.pyw`** (sau scurtătura „AutoPilot DC” de pe Desktop). Numele fișierelor nu se mai schimbă de la o versiune la alta, deci scurtăturile și pornirea cu Windows rămân valabile.

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
