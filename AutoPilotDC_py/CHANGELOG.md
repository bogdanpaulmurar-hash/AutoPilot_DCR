# AutoPilot DC — ce s-a schimbat

Pornirea aplicației: **`AutoPilot_DC.pyw`** (sau scurtătura „AutoPilot DC” de pe Desktop). Numele fișierelor nu se mai schimbă de la o versiune la alta, deci scurtăturile și pornirea cu Windows rămân valabile.

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
