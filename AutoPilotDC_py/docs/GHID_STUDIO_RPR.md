# Ghid Studio RPR — AutoPilot DC v4

> **Versiunea Python (AutoPilot DC 4.1):** Studio se deschide din comutatorul **🧩 Studio RPR** din bara de sus.
> Disponibil acum: editorul (pasi, conditii, bucle, variabile, Excel, Incearca/La eroare), rularea cu Pas cu pas /
> Pauza / Stop, logul, exemplele si obiectele adaugate manual. **Spy, Inregistrarea Web si driverele Web / SAP /
> Desktop sosesc in etapele urmatoare** — pana atunci pasii pe obiecte raporteaza ca driverul nu e disponibil.

Studio RPR este editorul vizual în care construiești rutine reale de automatizare (RPR — Rutine Reale care Procesează) pentru **web**, **SAP GUI** și **aplicații desktop Windows**, combinate cu **Excel**, fără să scrii cod.

Ideea, pe scurt:

- **Obiecte**: marchezi o singură dată elementele cu care lucrezi (butoane, câmpuri, tabele) folosind **Spy**. Fiecare obiect primește un nume, de exemplu `Buton_Salveaza` sau `Camp_IBase`, și mai mulți locatori de rezervă.
- **Pași**: construiești rutina din blocuri — Click, Scrie text, Citește, Așteaptă, Dacă/Altfel, Repetă, Pentru fiecare rând Excel etc. Totul se alege din liste.
- **Rulare**: motorul găsește fiecare obiect, îl **marchează pe ecran înainte de acțiune** și execută pasul. La eroare te întreabă ce să facă, sau aplică regula pe care ai ales-o.

## 1. Pornire

1. Deschide AutoPilot DC și apasă butonul **🧩 Studio RPR** din bara de sus.
2. La prima pornire apasă **📚 Exemple** și deschide **01 Învățare**. Apasă **⏭ Pas cu pas** de mai multe ori și urmărește cum se execută fiecare bloc.
3. Apasă **❓ Ghid** sau **F1** oricând ca să revii la acest ghid.

Cerințe pe calculator:

- **Web**: Microsoft Edge (implicit) sau Google Chrome instalat. Nu trebuie descărcat nimic în plus.
- **SAP**: SAP GUI for Windows cu scripting activat (vezi capitolul SAP).
- **Desktop**: nimic în plus; funcționează cu aplicațiile Windows care expun UI Automation (aproape toate).
- **Excel**: fișierele `.xlsx` sunt citite și scrise direct. Fișierul trebuie să fie **închis în Excel** cât timp rulează rutina.

## 2. Ecranul Studio

- **Bara de sus**: Nou, Deschide, Salvează, Exemple · Rulează, Pauză, Pas cu pas, Stop · Spy Web, Spy SAP, Spy Desktop, Înregistrează Web · Marchează înainte de acțiune · Programează, Setări, Ghid.
- **Stânga, tab-ul 🧱 Pași**: blocurile pe care le adaugi în rutină.
- **Stânga, tab-ul 🎯 Obiecte**: Object Repository — toate elementele marcate. Le poți arăta pe ecran (👁), edita, șterge sau transforma direct în pas (➕).
- **Centru**: arborele rutinei. Ramurile (↳ Atunci, ↳ Altfel, ↳ Pași) conțin pașii din interiorul blocurilor.
- **Dreapta**: proprietățile pasului selectat. Când nu e selectat nimic (sau apeși **⚙ Rutina**) vezi setările rutinei și variabilele.
- **Jos**: **📋 Log rulare** (roșu = eroare, galben = atenționare) și **🔤 Variabile** (valorile după ultima rulare).

## 3. Prima ta rutină web, pas cu pas

1. Apasă **📄 Nou**, apoi **⚙ Rutina** și dă-i un nume.
2. Apasă **🎯 Spy Web**. Dacă browserul nu e deschis, scrie adresa paginii (ex. `https://the-internet.herokuapp.com/login`).
3. În browser, du mouse-ul peste câmpul de utilizator: se conturează **verde** și vezi numele propus și cel mai bun locator.
4. Dă **click**. Click-ul NU ajunge la pagină — elementul e doar capturat.
5. În fereastra **Obiect capturat** verifică numele (ex. `Camp_Username`), apoi apasă **Salvează + pas Scrie text**.
6. În dreapta, la **Text**, scrie valoarea sau alege o variabilă din lista **＋ {x}**.
7. Repetă Spy pentru câmpul de parolă și butonul Login (**Salvează + pas Click**).
8. Adaugă din stânga **⏱ Așteaptă** → „Până când o condiție e adevărată” → „Obiectul e vizibil” → alege mesajul de confirmare.
9. Apasă **▶ Rulează**. Fiecare element e marcat cu **portocaliu** înainte de acțiune.
10. Apasă **💾 Salvează** (Ctrl+S).

Sfat: în loc de pașii 2–7 poți folosi **⏺ Înregistrează Web** — lucrezi normal în browser, iar fiecare click sau text completat devine automat un pas cu obiectul lui.

## 4. Spy — marcarea obiectelor

### Spy Web

- Pornește cu **🎯 Spy Web**. Funcționează în pagina principală și în **iframe-uri**.
- Mouse peste element = contur verde + numele propus și locatorul principal.
- **Click** = capturează elementul (click-ul nu se execută în pagină). **Esc** = anulează.
- Dacă dai click pe textul din interiorul unui buton, Spy urcă automat la butonul întreg.

### Spy SAP

- Deschide SAP GUI și autentifică-te. Apasă **🎯 Spy SAP**; Studio se minimizează și apare o bandă de indicații sus.
- Mouse peste câmp sau buton: SAP îl conturează cu **roșu**.
- **F2** = capturează, **Esc** = anulează.
- Dacă poziția nu poate fi determinată, dă click în câmp (să aibă focus) și apasă **F2**: se capturează câmpul activ.

### Spy Desktop

- Apasă **🎯 Spy Desktop**, du mouse-ul peste element (contur verde) și apasă **F2**. **Esc** anulează.
- Contextul obiectului este de obicei `proces:nume.exe` — obiectul e căutat în toate ferestrele acelui program.

### Fereastra „Obiect capturat”

- **Nume**: cum vei alege obiectul în pași. Folosește nume clare: `Buton_Salveaza`, `Camp_IBase`.
- **Locatori**: modurile în care e găsit obiectul, în ordine. La rulare primul locator care găsește **exact un** element câștigă; dacă pagina se schimbă, se trece automat la următorul (self-healing).
- **Scor**: verde (70+) stabil, galben (40–69) acceptabil, roșu sub 40 — fragil.
- Debifează locatorii instabili (de ex. un text care se schimbă). Poți corecta valoarea direct în căsuță.
- Butoanele **Salvează + pas Click / Scrie text / Citește** creează imediat și pasul.

### Tipuri de locatori

- **Web**: TestId (atribute de test, cele mai stabile), Id, Role (rol + nume accesibil, ex. `button|Salvează`), Label (eticheta câmpului), Name, Placeholder, Text, Css, XPath.
- **Desktop**: AutomationId, UiaName (`Tip|Nume`), ClassName (`Tip|Clasă`), UiaPath (calea în arbore).
- **SAP**: SapId (ex. `wnd[0]/usr/ctxtVBAK-VBELN`), SapName (`Nume|Tip`).

### Verificarea obiectelor

- În tab-ul **🎯 Obiecte** selectează un obiect și apasă **👁 Arată**: obiectul e căutat și conturat pe ecran, iar în bara de jos vezi prin ce locator a fost găsit și ce text are.
- **✎ Editează** (sau dublu click) schimbă numele, contextul și locatorii. Redenumirea actualizează automat toți pașii care folosesc obiectul.

## 5. Înregistrare Web (Recorder)

1. Apasă **⏺ Înregistrează Web** (butonul devine „Oprește înregistrarea”).
2. Lucrează normal în browser: click-uri, completări de câmpuri, alegeri din liste, bife.
3. Fiecare acțiune devine un pas, iar fiecare element nou devine obiect în repository (elementele deja existente sunt refolosite).
4. Mai multe tastări în același câmp devin un singur pas cu valoarea finală.
5. Oprește cu butonul roșu sau cu **Esc** în browser.
6. După înregistrare înlocuiește valorile fixe cu variabile (ex. `{Rand.IBase}`) și adaugă condiții.

## 6. Blocurile (pașii)

Click pe un bloc din stânga îl adaugă **după pasul selectat**. Ca să adaugi **în interiorul** unui Dacă/Repetă/Excel, selectează întâi ramura (↳ Atunci, ↳ Altfel, ↳ Pași) sau un pas din interior.

### Acțiuni

- **Click pe obiect**: click, dublu click, click dreapta, mouse deasupra. Poți schimba acțiunea din lista „Ce face pasul”.
- **Scrie text**: înlocuiește conținutul câmpului. „Tastează text (adaugă)” scrie caracter cu caracter fără să șteargă.
- **Citește valoare**: textul / valoarea / un atribut al obiectului se salvează într-o variabilă.
- **Apasă tastă**: `Enter`, `Tab`, `Escape`, `F5`, `Ctrl+A`, `Ctrl+Shift+S`, `Alt+F4`. Cu obiect = tasta se trimite obiectului; fără obiect = ferestrei active.
- **Alege din listă**, **Bifează / Debifează**, **Focus**, **Captură element**.
- **Browser**: Deschide browser, Mergi la adresă, Înapoi, Reîncarcă, Schimbă tab-ul, Răspuns la popup JS (accept/dismiss), Captură pagină, Închide browser.
- **SAP**: Conectează la sesiune, Pornește tranzacție, Trimite tastă, Citește bara de stare, Citește celulă tabel, Număr rânduri tabel.
- **Desktop**: Pornește aplicație, Atașează fereastră, Închide fereastră.

Opțiuni ale unei acțiuni:

- **Așteaptă obiectul maxim (ms)**: cât timp caută obiectul înainte de eroare (implicit 10 secunde).
- **Mod direct**: execută fără mișcarea vizibilă a mouse-ului (prin interfața de automatizare), unde e posibil.
- **▶ Testează pasul**: rulează doar acest pas, imediat.
- **👁 Arată obiectul**: verifică dacă obiectul e găsit pe ecranul curent.

### Flux

- **Așteaptă**: un număr de secunde sau până când o condiție devine adevărată (ex. „până când apare mesajul”, „până când dispare fereastra de încărcare”).
- **Dacă / Altfel**: ramura Atunci rulează când condiția e adevărată, Altfel când e falsă.
- **Repetă**: de N ori, cât timp o condiție e adevărată, sau până când devine adevărată. Variabila de numărare (implicit `{Repetare}`) are valorile 1, 2, 3...
- **Încearcă / La eroare**: dacă un pas din „Încearcă” eșuează, rutina nu se oprește — rulează ramura „La eroare”, iar mesajul erorii e în `{Eroare}`.
- **Întrebare**: fereastră cu butoane personalizate (ex. `Continuă,Oprește,Sari`). Răspunsul ajunge într-o variabilă; butonul de oprire oprește rutina, butonul de sărit trece la următorul rând Excel.
- **Ieși din buclă**: termină bucla curentă sau trece la următoarea repetare.
- **Oprește rutina**: cu sau fără eroare.

### Date

- **Pentru fiecare rând Excel**: pașii din interior rulează o dată pentru fiecare rând.
- **Scrie în Excel**: scrie în rândul curent, în coloana aleasă (o coloană nouă se creează automat), cu culoare opțională.
- **Variabilă**: setează, adaugă la final, crește/scade, taie spațiile, litere mari/mici, înlocuiește text.

### Organizare

- **Grup**: ține pași împreună (îl poți dezactiva cu totul).
- **Log**: scrie un mesaj în log (info, atenționare, eroare).

### Proprietăți comune tuturor pașilor

- **Titlu personalizat**: textul din arbore (gol = generat automat).
- **Pas activ**: debifat = pasul e omis la rulare (tasta Spațiu în arbore).
- **Așteaptă înainte / după (ms)**.
- **La eroare**: regula pentru acest pas (vezi capitolul 10).
- **Comentariu**: notițe pentru tine (apare 💬 în arbore).

### Organizarea arborelui

- ⬆ / ⬇ (Ctrl+Sus / Ctrl+Jos) mută pasul.
- ⧉ (Ctrl+D) duplică pasul cu tot ce conține.
- ⏯ (Spațiu) activează / omite pasul.
- 🗑 (Delete) șterge pasul.

## 7. Variabile

- Se scriu între acolade: `{Nume}`. Pot apărea în orice text: valori, adrese URL, condiții, Excel, întrebări.
- Lista **＋ {x}** de lângă căsuțe inserează variabilele cunoscute.
- Se creează prin: setările rutinei (⚙ Rutina → Variabile), blocul Variabilă, „Salvează rezultatul în variabila” la citiri, contorul buclelor, răspunsul la întrebări, eroarea prinsă.
- Din Excel: `{Rand.Titlu coloană}`, `{Rand.A}` (după literă), `{Rand.#}` (numărul rândului).
- Speciale: `{Azi}`, `{Acum}`, `{Acum:yyyyMMdd_HHmm}`, `{NewLine}`.
- Transformări: `{Nume:url}` (pentru adrese web), `{Nume:upper}`, `{Nume:lower}`, `{Nume:trim}`.
- Acolade literale: `{{` și `}}`.
- După rulare, tab-ul **🔤 Variabile** arată toate valorile.

## 8. Condiții

Se folosesc în Dacă, Repetă (cât timp / până când) și Așteaptă (până când).

- **Obiectul există / NU există / e vizibil / e activ**: verifică ecranul. „Așteaptă obiectul maxim” transformă verificarea într-o așteptare scurtă.
- **Textul obiectului ...**: compară textul unui element (ex. „conține Salvat”).
- **Compară două valori**: ex. `{StareSAP}` „începe cu” `E:`.
- Operatori: egal, diferit, conține, nu conține, începe cu, se termină cu, gol, nu e gol, mai mare / mai mic (numeric dacă ambele sunt numere — acceptă `1.234,5` și `1,234.5`), regex.
- **Toate condițiile (ȘI)** / **Oricare (SAU)**: grupuri imbricate, cu „＋ Adaugă condiție”.
- **NU**: inversează rezultatul.

## 9. Lucrul cu Excel

1. Adaugă **📊 Pentru fiecare rând Excel** și alege fișierul cu 📂.
2. Alege foaia, rândul cu titluri (de obicei 1) și **coloana cheie** — primul rând gol în ea înseamnă sfârșitul listei.
3. În interior folosește `{Rand.NumeColoană}` în pași (lista ＋ {x} le arată).
4. Adaugă **📝 Scrie în Excel** pentru rezultate (ex. coloana „Rezultat” = `{ValoareCitită}`).
5. **Coloana de status**: motorul scrie automat `OK`, `EROARE: mesaj` sau `SĂRIT: motiv` pe fiecare rând.
6. **Colorează rândurile**: status verde la succes, rând roșu la eroare.
7. **Salvează după fiecare rând**: dacă rutina se oprește, nu pierzi nimic.
8. **Sari rândurile deja OK**: la repornire continuă de unde a rămas.

Important: **închide fișierul în Excel** înainte de rulare.

## 10. Erori și decizii

Fiecare pas are regula „La eroare”; dacă e „Ca setarea rutinei”, se folosește regula din ⚙ Rutina:

- **Întreabă-mă**: fereastră cu Reîncearcă / Sari pasul / Sari rândul / Oprește și mesajul complet al erorii.
- **Oprește rutina**.
- **Continuă**: doar înregistrează eroarea în log și merge mai departe.
- **Sari la următorul rând Excel**: rândul e marcat roșu cu mesajul erorii, rutina continuă cu rândul următor.

Alte protecții:

- **Reîncercări automate** (⚙ Rutina): un pas eșuat e reîncercat automat înainte de regula de eroare.
- **Captură de ecran la eroare**: salvată în folderul de rezultate, sub `erori`.
- **Încearcă / La eroare**: tratezi erorile chiar în rutină (ex. „dacă nu găsesc butonul, închid popup-ul și continui”).
- **Ferestre popup JavaScript** (alert/confirm) sunt acceptate automat; schimbi comportamentul cu „Răspuns la popup JS”.
- **Tab-uri noi** deschise de aplicație devin automat pagina curentă.

## 10b. Siguranța la rulare (v4.1)

În **⚙ Rutina → Siguranța la rulare**:

- **🌙 Nu deranja**: cât timp rulează rutina, Windows nu afișează notificări (nu apar peste butoane și nu poți da click pe ele din greșeală). La final revin automat.
- **🛡 Sistem de prevenție**: înainte de fiecare acțiune rutina se pune pe **pauză și te întreabă** (Continuă / Continuă și nu mai întreba pentru asta / Sari rândul / Oprește) când:
  - apare o **fereastră de eroare** (titlu sau mesaj cu „Eroare”, „Error”, „Warning”...);
  - aplicația activă **nu răspunde**;
  - după o acțiune SAP, **bara de stare arată o eroare** (`E:` sau `A:`);
  - o valoare citită **diferă de „Valoarea așteptată”** a pasului.
- În interiorul unui bloc **Încearcă / La eroare** rutina nu te întreabă: valoarea diferită merge direct pe ramura „La eroare”, iar bara SAP nu e verificată (tratezi tu situația în rutină).

**Valoarea așteptată** (la pașii Citește...): textul pe care trebuie să-l găsească pasul. Acceptă variabile și `*` = orice text. Exemple: `S:*` (orice mesaj de succes SAP), `Salvat*`, `{Rand.Status}`.

Pe ecran, cât timp rulează rutina, apare un **chenar roșu** cu „▶ RUN” în colțul din dreapta-sus; la pauză sau când te întreabă ceva chenarul devine **portocaliu** („❚❚ PAUZA”); la **⏺ Înregistrează Web** chenarul e **verde** („● REC”). Click-urile trec prin chenar și el nu apare în capturile de ecran.

## 11. Rularea

- **▶ Rulează** (F5): Studio se minimizează (opțional, din Setări) și apare **bara plutitoare** dreapta-jos cu pasul curent și butoanele Pauză, Pas, STOP.
- **⏭ Pas cu pas**: rutina pornește în pauză; fiecare apăsare execută un singur pas. Ideal la verificarea unei rutine noi.
- **⏸ Pauză / Reluare**: oricând. Din pauză poți continua pas cu pas.
- **⏹ Stop**: oprire imediată.
- Scurtături globale în timpul rulării: **Ctrl+F11** pauză/reluare, **Ctrl+F12** stop — funcționează și când lucrezi în altă fereastră.
- **Marchează înainte de acțiune** (bifă în bara de sus): fiecare element e conturat portocaliu înainte de click / scriere. Durata se setează în ⚙ Rutina.
- În arbore: pasul curent e portocaliu, pașii reușiți au linie verde, pașii eșuați sunt roșii.
- **Pauză între pași** (⚙ Rutina): încetinește rularea pentru verificare.

## 12. SAP GUI

1. Activează scripting: în SAP GUI → Options → Accessibility & Scripting → Scripting → bifează **Enable scripting** și debifează avertismentele „Notify when a script attaches...” (altfel apare o întrebare la fiecare conectare). Pe server, parametrul `sapgui/user_scripting` trebuie să fie TRUE (cere echipei SAP Basis dacă e dezactivat).
2. Deschide SAP Logon și autentifică-te.
3. În rutină pune primul pas **SAP: conectează** (gol = prima sesiune; `1` = a doua sesiune; `1/0` = conexiunea 2, sesiunea 1).
4. **SAP: tranzacție** cu `/nVA03` închide tranzacția curentă și pornește VA03.
5. Marchează câmpurile cu **🎯 Spy SAP** și folosește-le în Scrie text / Click / Citește.
6. **SAP: tastă**: Enter, F3 (Înapoi), F8 (Execută), Ctrl+S (Salvare), Shift+F4 etc.
7. **SAP: bara de stare** dă mesajul cu tipul în față: `S:` succes, `E:` eroare, `W:` avertisment, `I:` informație, `A:` abandon. Folosește-l în Dacă (ex. „începe cu E:”).
8. Tabele: **Citește celulă tabel** cu valoarea `rând|coloană` (ex. `0|MATNR` pentru ALV, `0|2` pentru tabele clasice).

## 13. Aplicații desktop

1. **Pornește aplicație** (ex. `notepad.exe` sau `"C:\Program Files\App\app.exe" /param`) sau **Atașează fereastră** (`proces:nume.exe` sau titlul ca expresie regulată).
2. Marchează elementele cu **🎯 Spy Desktop** (F2).
3. Contextul `proces:nume.exe` face ca obiectul să fie găsit în orice fereastră a programului.
4. **Mod direct** folosește UI Automation (Invoke, Value, Toggle) — mai rapid și fără mouse.

## 14. Programare automată

1. Salvează rutina.
2. Apasă **⏰ Programează**: alege zilnic / zile lucrătoare / săptămânal / o singură dată și ora.
3. Se creează o sarcină în Windows Task Scheduler (`AutoPilotDC\NumeRutina`), vizibilă și modificabilă cu „Deschide Task Scheduler”.
4. La ora stabilită rutina rulează fără Studio. Logul se salvează în folderul de rezultate (`Log_programat_...xlsx`).
5. Calculatorul trebuie să fie pornit și utilizatorul autentificat (rutinele folosesc ecranul).
6. La rularea programată, întrebările primesc automat primul buton, iar erorile sar rândul Excel curent (sau opresc rutina în afara unei bucle Excel).

Linie de comandă: `AutoPilotDC.UI.exe --run "C:\cale\rutina.rpr.json"`.

## 15. Rutinele vechi (v3.9)

- **📂 Deschide** acceptă și rutinele vechi `.json`. Ele sunt convertite: pașii de browser cu selector devin obiecte + acțiuni, întrebările și așteptările devin blocuri noi, iar click-urile pe coordonate rămân pași 🖱 „Pas vechi”.
- Fișierul vechi rămâne neschimbat; rutina convertită se salvează ca fișier nou `.rpr.json`.
- Recomandare: înlocuiește treptat pașii 🖱 cu acțiuni pe obiecte marcate cu Spy — sunt mult mai stabile la mutarea ferestrelor sau schimbarea rezoluției.

## 16. Rutinele exemplu

- **01 Învățare**: variabile, Repetă, Dacă, Întrebare, Încearcă — fără aplicații externe. Rulează-l cu Pas cu pas.
- **02 Web – Login demo**: site public de test. Schimbă variabila `Parola` ca să vezi ramura Altfel.
- **03 Web + Excel – Wikipedia**: pentru fiecare termen din `Exemplu_Termeni.xlsx` caută pe Wikipedia și scrie titlul, observația și ora în Excel.
- **04 SAP – VA03 (șablon)**: pune numere de comenzi în `Exemplu_Comenzi_SAP.xlsx`; verifică obiectul `SAP_Camp_Comanda_VA03` cu 👁 pe sistemul tău.
- **05 Desktop – Notepad**: pornește Notepad și scrie trei linii dintr-o buclă.

Exemplele se instalează în folderul de lucru, sub `exemple`; le poți modifica liber și le poți reinstala oricând din 📚 Exemple.

## 17. Scurtături de tastatură

- **Ctrl+N** rutină nouă · **Ctrl+O** deschide · **Ctrl+S** salvează
- **F5** rulează · **F1** ghid
- În arbore: **Delete** șterge · **Spațiu** activează/omite · **Ctrl+Sus/Jos** mută · **Ctrl+D** duplică
- În timpul rulării (oriunde): **Ctrl+F11** pauză/reluare · **Ctrl+F12** stop
- Spy Web: **Click** capturează · **Esc** anulează
- Spy SAP / Desktop: **F2** capturează · **Esc** anulează

## 18. Probleme frecvente

- **„Obiectul nu a fost găsit”**: verifică cu 👁 Arată dacă ești pe ecranul potrivit. Dacă pagina s-a schimbat, marchează din nou obiectul sau corectează locatorii (✎ Editează). Mărește „Așteaptă obiectul maxim” pentru pagini lente sau adaugă un pas Așteaptă până când.
- **„Nu pot porni browserul”**: verifică dacă Edge/Chrome e instalat sau alege altul în ⚙ Setări. Dacă profilul e blocat de o altă fereastră AutoPilot, închide-o.
- **Trebuie să mă autentific la fiecare rulare**: nu e cazul — profilul browserului e păstrat. Pentru logout: ⚙ Setări → Șterge profilul browserului.
- **„SAP GUI nu este deschis”**: deschide SAP Logon, autentifică-te și verifică dacă scripting-ul e activat (capitolul 12).
- **Excel „blocat”**: închide fișierul în Excel și pornește din nou; cu „Sari rândurile deja OK” rutina continuă de unde a rămas.
- **Rutina merge prea repede pentru aplicație**: adaugă „Așteaptă până când” (recomandat) sau „Așteaptă după (ms)” pe pasul respectiv.
- **Un click nu are efect pe web**: încearcă „Mod direct” sau verifică dacă elementul e acoperit de alt element (un popup, un banner de cookie).

## 19. Unde se salvează fișierele

În `%AppData%\AutoPilotDC\Studio\`:

- `rutine\` — rutinele tale (`.rpr.json`)
- `obiecte.json` — Object Repository (comun tuturor rutinelor)
- `obiecte\` — capturile obiectelor marcate
- `rezultate\` — capturi, loguri, capturile erorilor (`erori\`)
- `exemple\` — rutinele și fișierele Excel exemplu
- `browser-profil\` — profilul browserului (sesiuni, cookie-uri)

Folderul se deschide din ⚙ Setări → Deschide folderul de lucru.
