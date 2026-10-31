# AutoPilot DC Anleitung

Jedes Kapitel erklärt kurz einen Ablauf, Schritt für Schritt, mit einem Beispiel. Wählen Sie links ein Kapitel oder suchen Sie nach einem Wort.

> Variablennamen wie `{Azi}` (heute), `{Acum}` (jetzt), `{Rand.…}` (Excel-Zeile) und `{Repetare}` (Schleifenzähler) sind in allen Sprachen gleich, damit Routinen bei allen Kollegen funktionieren.

## 1. Start und Oberfläche

- Starten Sie die Anwendung mit **AutoPilot_DC.pyw** im Ordner `AutoPilotDC_py` oder über die Desktop-Verknüpfung „AutoPilot DC“ (ohne CMD-Fenster).
- Beim ersten Mal (oder auf einem neuen Laptop) **INSTALEAZA.bat** ausführen: installiert alles Nötige ohne Administratorrechte. Das Fenster bleibt offen, bis Sie eine Taste drücken.
- Die Anwendung hat einen Arbeitsbereich, **🧩 Studio RPR**. Der frühere Recorder ist jetzt in Studio (Schaltfläche **⏺ Bildschirm**, Kapitel 2).
- Die obere Leiste ist einzeilig: die Studio-Befehle (Routine, Ausführung, Spy und Aufnahme) in der Mitte; bei schmalem Fenster bleiben nur die Symbole (der ganze Text steht im Tooltip). Rechts kleine Schaltflächen: **🎥** nimmt den Bildschirm auf, **🎬** öffnet ein Video, **📖 Anleitung** (hier, oder F1), **⚙ Einstellungen** der Anwendung, **✕**.
- **🚨 NOT-STOPP** (oder F12) beendet jede Ausführung und Aufnahme sofort.
- Tray-Symbol neben der Uhr: Klick = Anwendung öffnen; Rechtsklick = Studio, ⏺ Bildschirm, Video, NOT-STOPP, Beenden.

> Beispiel: Anwendung öffnen, **⋯ → 📚 Beispiele** drücken und „01 Lernen“ öffnen.

## 2. ⏺ Bildschirm: Maus und Tastatur aufnehmen (der frühere Recorder)

1. Wählen Sie in Studio den Schritt, nach dem die neuen Schritte kommen sollen (oder keinen: sie kommen ans Ende).
2. **⏺ Bildschirm** (F5) drücken. Das AutoPilot-Fenster wird minimiert, der grüne **REC**-Rahmen erscheint und oben eine kleine Leiste mit der Anzahl der Schritte und **⏹ Stopp (F6)**.
3. Arbeiten Sie normal in jeder Anwendung: Klicks, Scrollen, Tasten. Nacheinander getippte Buchstaben werden ein einziger Schritt „Schreiben“. Klicks auf AutoPilot selbst werden nicht aufgenommen.
4. **F6** oder **⏹ Stopp** drücken. Die Schritte kommen in die Routine, in eine Gruppe „Bildschirmaufnahme HH:MM“, als 🖱 Bildschirmschritte.
5. Ausführen mit **▶ Ausführen** (F7). **Pause** = F8, **Stopp** = F9, **NOT-STOPP** = F12. Für Wiederholungen die Gruppe in einen **🔁 Wiederholen**-Block legen; für Werte aus Excel in ein **📊 Für jede Zeile** (und den Text des Schritts „Schreiben“ durch `{Rand.Spalte}` ersetzen).
6. Das Schutzsystem prüft auch Bildschirmschritte: Würde der Klick bei der Ausführung in einer anderen Anwendung landen oder sieht der Bereich anders aus, hält die Routine an und fragt.

> Beispiel: letzten Schritt wählen, ⏺ Bildschirm drücken, Editor öffnen, „Test“ tippen, F6 drücken. Die Routine erhält die Gruppe mit den Klicks und den Schritt Schreiben "Test".

> Achtung: Bildschirmschritte arbeiten mit Koordinaten. Wird das Fenster verschoben oder ändert sich die Auflösung, landet der Klick woanders. Nutzen Sie wo möglich Objektschritte (🎯 Spy, ⏺ Web).

## 3. Bildschirmschritte: Bearbeiten und was aus dem Recorder umgezogen ist

- Ein 🖱 Bildschirmschritt wird rechts wie jeder Schritt bearbeitet: **X / Y**, Tasten, Text, Warten davor / danach, Kommentar. Der Titel zeigt, was er tut und in welchem Fenster („Klick (420, 310) · Editor“).
- Die aufgenommene Gruppe kann umbenannt, deaktiviert, mit der Maus verschoben oder dupliziert werden; ihre Schritte einzeln verschieben, löschen oder deaktivieren.
- Was in den Recorder-Tabs war, ist jetzt in Studio: **Step Builder** → die Blöcke in 🧱 Schritte; **Routinen** → 📋 Routinen und 🗂 Routinenmanager; **Excel** → 📊 Für jede Excel-Zeile; **Log** → ⏱ Zeitachse und Ausführungslog (mit Excel-Export); **Einstellungen** → die Schaltfläche ⚙ oben rechts; **Hilfe** → 📖 Anleitung. Wiederholungen → der Block 🔁 Wiederholen; Pause zwischen Schritten → ⚙ Routine.
- Alte Recorder-Routinen (`rutine_salvate\*.json`) öffnen Sie mit **📂 Öffnen**: Sie werden automatisch in Bildschirmschritte umgewandelt; die alte Datei bleibt unverändert.
- **Notizen** haben keinen Tab mehr: nutzen Sie das Feld **Kommentar / Notiz** der Schritte und die Routinenbeschreibung.

> Beispiel: 📂 Öffnen → `rutine_salvate\Bericht.json` → die Routine erscheint in Studio mit ihren 🖱 Schritten; speichern Sie sie (💾) als `.rpr.json`.

## 4. Sicherheit bei der Ausführung

- **🌙 Nicht stören**: Windows-Benachrichtigungen sind aus, solange eine Routine läuft oder aufnimmt, damit Sie sie nicht versehentlich anklicken. Am Ende kommen sie von selbst zurück.
- **Bildschirmrahmen**: rot + RUN bei Ausführung, grün + REC bei Aufnahme, orange bei Pause. Der Rahmen ist in Screenshots unsichtbar und nimmt keine Klicks an.
- **🛡 Schutzsystem**: prüft vor jedem Schritt, ob Sie die Maus bewegt haben, ein Fehlerfenster erschienen ist, die Anwendung nicht reagiert oder der Bildschirm anders aussieht als bei der Aufnahme. Dann pausiert die Routine und fragt: **Fortfahren / Wiederholen / Überspringen / Stoppen**.
- Aktivieren unter **⚙ Einstellungen → 🛡 Sicherheit bei der Ausführung**. Bleiben die Benachrichtigungen aus: **🔔 Benachrichtigungen jetzt wieder einschalten**.

> Beispiel: Eine Routine starten und währenddessen die Maus bewegen — die Routine hält an und fragt, ob sie weitermachen soll.

## 5. Studio RPR: die Grundidee

- Eine **Routine** ist ein Baum von Schritten: Aktionen (Klick, Schreiben, Lesen), Bedingungen (Wenn), Schleifen, Excel, Fragen.
- Die Schritte arbeiten mit **Objekten** (Schaltflächen, Felder, Tabellen), die einmal mit **Spy** markiert werden, nicht mit Koordinaten. Jedes Objekt hat mehrere **Locatoren** als Reserve: Funktioniert einer nicht mehr, wird der nächste versucht.
- **Variablen** stehen in geschweiften Klammern: `{Client}`, `{Rand.IBase}`, `{Azi}`.
- Der Studio-Bildschirm: links **🧱 Schritte** (Blöcke) und **📚 Bibliothek** (Objekte); Mitte der Routinenbaum; rechts die Eigenschaften des gewählten Schritts; unten **Log** und **Variablen**.
- Klick auf einen Block = nach dem gewählten Schritt einfügen. Um ihn **in** ein „Wenn“ oder eine Schleife zu setzen, zuerst den Zweig wählen (z. B. ▸ Dann).

> Beispiel: 📚 Beispiele → „01 Invatare“ öffnen und mehrmals ⏭ Schrittweise drücken, dabei jeden Block verfolgen.

## 6. Die erste Web-Routine (Schritt für Schritt)

[video:02_studio_web]

1. Studio → **📄 Neu**.
2. Block **🌐 Browser öffnen**, Adresse `https://the-internet.herokuapp.com/login`.
3. **🎯 Web** (Spy): Maus über das Feld Username (grüner Rahmen) und **klicken**. Im Fenster „Erfasstes Objekt“ **+ Schritt Text schreiben** drücken. Wert `tomsmith` eintragen.
4. Ebenso für Password (`SuperSecretPassword!`) und die Login-Schaltfläche (**Speichern + Klick-Schritt**).
5. Spy auf die Meldung nach dem Login → **+ Schritt Lesen**; im Schritt den **Erwarteten Wert** `You logged into*` setzen.
6. **💾 Speichern**, dann **▶ Ausführen**.

> Tipp: **⏺ Web aufnehmen** erledigt Schritte 3–4 automatisch: normal im Browser arbeiten, jeder Klick / Text / jede Option wird ein Schritt. Esc im Browser oder erneut ⏺ = Stopp.

## 7. Spy Web und Web aufnehmen

- **🎯 Web**: Ist der Browser nicht geöffnet, fragt Studio nach der Adresse. Maus über das Element → grüner Rahmen → **Klick** = erfassen; **Esc** = abbrechen.
- In „Erfasstes Objekt“: Name (so wählen Sie es in Schritten), Typ, Website, Seite, Container und Locatoren mit Punkten (grün 70+ stabil, gelb akzeptabel, rot fragil). Instabile Locatoren abwählen (z. B. einen sich ändernden Text).
- Ist das Element bereits in der Bibliothek, schlägt Studio vor, das vorhandene zu verwenden.
- Der Browser (Edge oder Chrome) wird in **🌐 Studio-Einstellungen** gewählt. Das Profil (Login, Cookies) bleibt zwischen Ausführungen erhalten.
- iframes, neue Tabs und JavaScript-Popups werden automatisch behandelt.

> Beispiel: Auf einer Seite mit Suche Spy auf das Feld → „+ Schritt Text schreiben“ mit `{Termen}`, dann Spy auf die Suchen-Schaltfläche → „Speichern + Klick-Schritt“.

## 8. SAP GUI

[video:05_studio_sap]

1. Scripting aktivieren: SAP GUI → Optionen → Barrierefreiheit und Scripting → Scripting → **Scripting aktivieren** (Warnungen abwählen). Auf dem Server muss `sapgui/user_scripting` TRUE sein.
2. SAP Logon öffnen und anmelden.
3. Erster Schritt der Routine: **🟦 SAP: verbinden** (leer = erste Sitzung).
4. **🟦 SAP: Transaktion** mit `/nVA03` (beendet die aktuelle Transaktion und startet VA03).
5. **🎯 SAP**: Maus über das Feld (roter Rahmen) und **F2**. Lässt sich die Position nicht bestimmen, ins Feld klicken und F2 drücken.
6. **🟦 SAP: Taste** (Enter, F3, F8, Shift+F4, Ctrl+S) und **🟦 SAP: Statusleiste** (`S:` Erfolg, `E:` Fehler, `W:` Warnung).
7. Tabellen: **SAP: Tabellenzelle lesen** mit `Zeile|Spalte` (z. B. `0|MATNR`); die Tabelle scrollt selbst zur Zeile.
8. **🟦 SAP: Tabelle blättern**: Tabelle wählen (🎯 SAP auf der Tabelle) und die Zeile eingeben (`1` = erste, oder `{Repetare}` in einer Schleife), `+1` / `-1`, `start` oder `end`. Die Zeile rückt so weit wie möglich nach oben, ihre Position auf dem Bildschirm (`0` = erste sichtbare Zeile) kommt in `{Pozitie}`. Diese setzt du in die Zell-ID: `btnDEL[5,{Pozitie}]` (in 📚 Bibliothek, im Id-Lokator des Objekts; den Ersatz-Lokator Name|Typ abwählen, sonst findet er eventuell den Papierkorb einer anderen Zeile). Am Ende der Liste blättert die Tabelle nicht mehr, die Position wächst aber weiter, so erreicht die Schleife die letzte Zeile ohne Scrollpfeil.

> Beispiel (Zeilen bleiben nach dem Löschen in der Liste): **🔁 Wiederholen** so oft wie Zeilen; darin: SAP: Tabelle blättern = `{Repetare}`, Klick auf den Papierkorb `...btnDEL[5,{Pozitie}]`, Klick auf „Yes“ im ersten Fenster, Klick auf „Yes“ im zweiten.

> Beispiel: Routine 04 „SAP VA03“ liest die Auftragsnummern aus Excel und schreibt den Status in die Spalte Status.

## 9. Windows-Desktop-Anwendungen

[video:04_studio_desktop]

1. **🖥 Anwendung starten** (`notepad.exe` oder `"C:\Program Files\App\app.exe" /param`) oder **🖥 Fenster verbinden** (`proces:notepad.exe` oder der Fenstertitel).
2. **🎯 Desktop**: Maus über das Element (grüner Rahmen) und **F2**; Esc = abbrechen.
3. Das Objekt in Schritten verwenden: Klick, Text schreiben, Lesen, Aus Liste wählen, Ankreuzen.
- Vor jedem Klick wird das Anwendungsfenster nach vorne geholt und das Element in den sichtbaren Bereich gescrollt. Wäre der Punkt von einem anderen Fenster verdeckt, erfolgt der Klick ohne Maus (UI Automation) oder der Schritt stoppt mit einer Meldung — nie in einem anderen Fenster.
- **Listen (Unterhaltungen, E-Mails)**: Spy erfasst die ganze Zeile. Namen mit wechselndem Text erhalten ein Muster, z. B. `ListItem|Ion Popescu*` (`*` = beliebiger Text).
- **Direktmodus** (im Schritt): Aktionen ohne Mausbewegung, wo die Anwendung es erlaubt.

> Beispiel: Routine 05 „Desktop Notepad“ startet den Editor und schreibt drei Zeilen in einer Schleife.

## 10. Die Objektbibliothek

[video:06_biblioteca]

- Der Tab **📚 Bibliothek** zeigt alle Objekte, gemeinsam für alle Routinen: **Website → Seite → Container → Objekt**. Website und Seite werden aus dem Link ausgefüllt, auf dem das Objekt erfasst wurde.
- **Test**: Bevor Sie ein Objekt in einer neuen Routine verwenden, sehen Sie, wie viele Elemente jeder Locator findet (1 = gut, mehrere = mehrdeutig, 0 = nicht gefunden); das Objekt wird auf dem Bildschirm markiert. Aus dem Ergebnis fügen Sie es direkt als Schritt ein.
- **Container** (Abschnitt, Tabelle, RefList, Formular): Ihre Objekte werden nur darin gesucht. Dieselbe Schaltfläche „Speichern“ in zwei Abschnitten wird nicht mehr verwechselt. Bei Spy wird der Container automatisch vorgeschlagen.
- **🌐 Websites**: eine Website mit mehreren Links (Test, Produktion, anderer Kunde) — ihre Objekte funktionieren auf allen. **Für andere Website kopieren** dupliziert ein Objekt für ein anderes System.
- Rechtsklick auf ein Objekt: testen, Schritt hinzufügen, in Container verschieben, kopieren, löschen. Die Suche filtert nach Name, Typ, Website oder Tag.

> Beispiel: Spy auf den Abschnitt „Lieferung“ → Typ „Container / Abschnitt“; dann Spy auf seine Schaltfläche Speichern → sie wird automatisch in den Container Lieferung gelegt.

## 11. Schritte (Aktionen)

- **Am Objekt**: Klick, Doppelklick, Rechtsklick, Maus darüber, Text schreiben (ersetzen), Text tippen (anfügen), Feld leeren, Taste drücken, Aus Liste wählen, Ankreuzen / Abwählen, Text / Wert / Attribut lesen, Markieren, Element-Screenshot.
- **Browser**: Browser öffnen, URL aufrufen, Zurück, Neu laden, Tab wechseln, Auf JS-Popup antworten, Seiten-Screenshot, Browser schließen.
- **SAP**: Verbinden, Transaktion, Taste senden, Statusleiste, Zelle lesen, Anzahl Zeilen.
- **Desktop**: Anwendung starten, Fenster verbinden, Fenster schließen.
- In jedem Schritt: **Maximal auf das Objekt warten (ms)**, **Bei Fehler**, **Vorher / nachher warten**, **Kommentar**, **Schritt aktiv**.
- **▶ Schritt testen** führt nur den gewählten Schritt aus, mit den Variablen der letzten Ausführung.
- **🎯 Neu markieren** (neben ▶ Schritt testen): Hat der Schritt das falsche Element gefunden, klicken Sie auf das richtige (SAP / Desktop: F2). Sie wählen:
  - **Locatoren ersetzen**: Das Objekt behält seinen Namen, alle Schritte, die es verwenden, suchen das neue Element (das Fenster zeigt, wie viele);
  - **Neues Objekt nur für diesen Schritt**: Das alte Objekt bleibt unverändert, der Schritt erhält das neue Objekt (im selben Ordner).
  Ein Schritt ohne Objekt erhält direkt ein neues Objekt. Die Bibliothek wird gespeichert; danach erneut ▶ Schritt testen. Ein anderes vorhandenes Objekt wählen Sie in der Liste „An welchem Objekt“.

> Beispiel: „Text lesen“ auf der Bestätigungsmeldung, gespeichert in der Variable `Mesaj`, danach „Log“ mit `Erhalten: {Mesaj}`.

## 12. Bedingungen, Schleifen und Warten

- **🔀 Wenn / Sonst**: Der Zweig „Dann“ läuft, wenn die Bedingung wahr ist, „Sonst“, wenn sie falsch ist. Bedingungen: Objekt existiert / existiert nicht / ist sichtbar / ist aktiv, Text des Objekts, zwei Werte vergleichen, alle (UND) / eine (ODER), NICHT.
- **🔁 Wiederholen**: N-mal, solange oder bis eine Bedingung wahr ist; die Variable `{Repetare}` = 1, 2, 3...
- **⏱ Warten**: eine Anzahl Sekunden oder bis etwas erscheint / verschwindet (mit Höchstzeit).
- **🛡 Versuchen / Bei Fehler**: Schlägt ein Schritt in „Versuchen“ fehl, stoppt die Routine nicht, sondern führt „Bei Fehler“ aus; die Meldung steht in einer Variable.
- **⏏ Schleife verlassen** und **⛔ Routine stoppen** (mit oder ohne Fehler).

> Beispiel: Wenn „Das Objekt existiert: Button_Accept_Cookies“ → Dann: anklicken. Sonst: nichts.

## 13. Variablen

- Überall in geschweiften Klammern verwenden: `{Client}`. In **⚙ Routineeinstellungen** definieren (Startwerte) oder von Schritten erstellen lassen (Lesen → „Ergebnis in Variable speichern“).
- **✎ Variable**: setzen, anfügen, erhöhen / verringern, GROSS / klein, Text ersetzen, Leerzeichen entfernen.
- Speziell: `{Azi}` (heute), `{Acum}` (jetzt), `{Acum:yyyyMMdd_HHmm}`, `{NewLine}`.
- Aus Excel: `{Rand.Spaltentitel}`, `{Rand.A}` (nach Buchstabe), `{Rand.#}` (Zeilennummer).
- Der Tab **🔤 Variablen** unten zeigt die Werte nach der letzten Ausführung.

> Beispiel: Text `Bericht_{Acum:yyyyMMdd}` in das Dateinamenfeld schreiben.

## 14. Excel: eine Routine für jede Zeile

[video:03_studio_excel]

1. Block **📊 Für jede Excel-Zeile**: Datei, Blatt, Titelzeile, erste / letzte Zeile und Schlüsselspalte wählen (leere Zeile = Ende der Liste).
2. Die Schritte **in** den Block setzen; `{Rand.Spaltenname}` verwenden.
3. **📝 In Excel schreiben** (in der Schleife) schreibt ein Ergebnis in die aktuelle Zeile (die Spalte wird bei Bedarf angelegt) und kann die Zelle einfärben.
4. Die **Statusspalte** erhält OK / den Fehler, die Zeilen werden grün / rot eingefärbt. Mit „Nach jeder Zeile speichern“ und „bereits OK markierte Zeilen überspringen“ lässt sich eine unterbrochene Ausführung fortsetzen.
5. **📤 Excel-Vorlage exportieren** (im Bereich des Blocks): neue Datei mit der Schlüsselspalte (leer = `Id`) als Text formatiert, damit führende Nullen und lange Ids so bleiben, wie du sie eingibst, danach die Spalten aus den Schritten **In Excel schreiben** (grün) und der Status (grau). Sie hat ein Blatt *Anleitung* und warnt bei einer doppelten Id. Nach dem Speichern kann die Vorlage als Datei der Schleife verwendet werden.
6. **Schlüsselspalte unter anderem Namen**: verlangt die Routine `Id` und die Datei hat `ID`, `UEID`, `Code`/`Cod` oder `Nr`, wird die Spalte gefunden und `{Rand.Id}` enthält ihren Wert. Leerzeichen, `_` und Großbuchstaben spielen keine Rolle. Beim Schreiben werden diese Namen nicht verwendet: ein aus SAP gelesener „Cod“ landet nie in der Id-Spalte.
7. **Prüfung vor dem ersten Klick**: Zeilen mit Daten, aber ohne Id (die Liste endet bei der ersten) und doppelte Ids erscheinen in einer Frage: **Weiter** oder **Routine stoppen**. Eine geplante Ausführung läuft weiter und schreibt es ins Log.
- Formeln in der Datei bleiben erhalten.

> Beispiel: Datei mit der Spalte `IBase`; in der Schleife: Text `{Rand.IBase}` ins Suchfeld schreiben, Suchen klicken, Status lesen → In Excel schreiben in die Spalte `Ergebnis`.

## 15. Fragen, Fehler und der erwartete Wert

- **💬 Frage**: ein Fenster mit selbst gewählten Schaltflächen (z. B. `Ja, Nein, Überspringen`); die Antwort landet in einer Variable. Sie können festlegen, welche Schaltfläche die Routine stoppt oder die Excel-Zeile überspringt.
- **Bei Fehler** (pro Schritt oder Routine): Mich fragen (Wiederholen / Überspringen / Stoppen), Stoppen, Fortfahren (nur protokollieren), Zur nächsten Excel-Zeile.
- **Automatische Wiederholungen** und **Screenshot bei Fehler** werden in ⚙ Routineeinstellungen gesetzt.
- **Erwarteter Wert** (bei Lese-Schritten): Weicht der gelesene Text ab, hält die Routine an und fragt. Variablen und `*` sind erlaubt (z. B. `S:*` = jede SAP-Erfolgsmeldung).

> Beispiel: SAP-Statusleiste lesen mit erwartetem Wert `S:*` — bei jedem SAP-Fehler hält die Routine an und zeigt die Meldung.

## 16. Ausführung und Steuerung

- **▶ Ausführen** startet die Routine; die Anwendung wird (optional) minimiert, eine kleine Steuerleiste bleibt.
- **⏭ Schrittweise**: jeder Druck führt einen einzigen Schritt aus — ideal zur Kontrolle.
- **Pause / Fortsetzen**: Ctrl+F11. **Stopp**: Ctrl+F12.
- **📋 Ausführungslog**: jeder Schritt mit Uhrzeit, Ergebnis und Dauer; Fehler sind rot. **📤 Export Excel** speichert das Log; **📂 Ergebnisse** öffnet den Ordner mit Screenshots und Logs.
- Ohne Oberfläche ausführen: `py -m rpr run "C:\Pfad\routine.rpr.json" --var Client=Max`.

> Beispiel: Eine neue Routine zuerst mit ⏭ Schrittweise und „Objekt vor jeder Aktion markieren“ ausführen.

## 17. Zeitplanung

[video:07_programare]

1. Routine speichern und **🕒 Planen** drücken.
2. **Wann** wählen: täglich, an Werktagen, an bestimmten Tagen, einmalig, alle N Minuten oder bei der Windows-Anmeldung; dann die Uhrzeit (und das Datum).
3. **✔ Zeitplan erstellen**: erscheint in der Windows-Aufgabenplanung im Ordner `AutoPilotDC` (ohne Administratorrechte). Gleicher Name ersetzt den Zeitplan.
4. Liste **AutoPilot-Zeitpläne**: nächste / letzte Ausführung und Ergebnis; **▶ Jetzt ausführen**, **🗑 Löschen**. Tab **Verlauf**: jede geplante Ausführung (Doppelklick = Log).
- Am Ende erscheint eine Meldung in der Bildschirmecke (grün / rot). Der Computer muss eingeschaltet und Sie angemeldet sein.

> Beispiel: „Tagesbericht“, An Werktagen, 07:30 Uhr.

## 18. Einstellungen

- **⚙ Einstellungen** (Anwendung, kleine Schaltfläche oben rechts): Bildschirmaufnahme (Mausbewegungen), Sicherheit bei der Ausführung, Tastenkürzel, **Start mit Windows** (optional direkt ins Tray), die Schaltfläche ✕ versteckt ins Tray, Desktop-Verknüpfung, Design, Video, **Sprache** (Română / English / Deutsch), Backup. Sprache und Design gelten nach einem Neustart.
- **Eine Sprache** für die ganze Anwendung (⚙ Einstellungen → 🌐 Sprache): neben der Oberfläche werden auch die Logs, die Statusspalte in der Excel-Datei der Routine (OK / FEHLER / IN BEARBEITUNG), der Ausführungsbericht sowie Zusammenfassung und Dokumentation der Vorbereitungen in dieser Sprache geschrieben. Bei der Wiederaufnahme werden Status in jeder Sprache erkannt (z. B. „IN LUCRU“ = „IN BEARBEITUNG“), eine auf Rumänisch begonnene Excel-Datei kann also nach dem Wechsel weitergeführt werden.
- **🌐 Studio-Einstellungen**: Browser für Web-Schritte (Edge empfohlen, Chrome), ohne Fenster (nur für Zeitpläne), Minimieren bei Ausführung, Browser schließen, Browserprofil löschen (Abmeldung); dazu Textgröße, Speicherorte und die Anwendung für Videos (Kapitel 31).
- **⚙ Routine**: Fehlerverhalten, Objektmarkierung, Standard-Timeout, Pause zwischen Schritten, Wiederholungen, Screenshots, Nicht stören, Schutz, Variablen.

> Beispiel: ⚙ Einstellungen → Sprache → English → Einstellungen speichern → die Anwendung startet auf Englisch neu.

## 19. Häufige Probleme

- **Pakete fehlen beim Start**: „Jetzt installieren“ drücken oder INSTALEAZA.bat ausführen.
- **Edge startet nicht („Target page… has been closed“)**: Von AutoPilot offene Edge-Fenster schließen; die Anwendung versucht es erneut und startet bei Bedarf mit einem temporären Profil. Oder Chrome in 🌐 Studio-Einstellungen wählen.
- **Das Objekt wird nicht gefunden**: In der Bibliothek **Test** drücken; liefert ein Locator 0, ihn bearbeiten oder mit Spy neu erfassen. Website / Seite und Container prüfen.
- **Der Klick geht in ein anderes Fenster (Desktop)**: Die Anwendung muss geöffnet sein; für Schaltflächen und Listenzeilen „Direktmodus“ verwenden.
- **Die Excel-Datei ist gesperrt**: vor der Ausführung in Excel schließen.
- **SAP reagiert nicht**: Scripting prüfen (Kapitel 8).
- **Das Tray-Symbol fehlt**: Einstellungen → Autostart und Tray zeigt den Status; unter Windows 10/11 evtl. unter dem Pfeil ^ versteckt.
- **Benachrichtigungen bleiben aus**: Einstellungen → 🔔 Benachrichtigungen jetzt wieder einschalten.
- **„Nicht stören“ geht nicht an oder aus**: Einstellungen → 🔍 Nicht stören prüfen (auf Wunsch mit „echtem Test“). Der Bericht zeigt die Windows-Version, die gefundene Einstellung und ob Windows den Neustart des Benachrichtigungsdienstes erlaubt; er wird auch in `loguri\nu_deranja_diagnostic.txt` gespeichert.

## 20. Dateien, Ordner und Kollegen

- Die Anwendung: Ordner `AutoPilotDC_py` (kopieren oder mit `git pull` holen). Recorder-Routinen: `rutine_salvate`, Logs: `loguri`.
- Studio: `%APPDATA%\AutoPilotDC\Studio` — `rutine` (Routinen), `rezultate` (Logs, Screenshots), `obiecte.json` (die Bibliothek), `exemple`, `browser-profil`.
- Für einen Kollegen: die `.rpr.json`-Datei und `obiecte.json` senden; der Kollege führt einmal INSTALEAZA.bat aus.
- Die Version steht in der unteren Leiste; Neuerungen in `CHANGELOG.md`.

## 21. Video: Bildschirmaufnahme

[video:08_video]

- **🎥** (obere Leiste oder Tray-Menü) startet jederzeit eine Aufnahme, ohne Routine — z. B. um einem Kollegen einen Ablauf zu zeigen. Erneut 🎥 oder **⏹ Stopp** in der kleinen ● REC-Leiste drücken (sie erscheint nicht im Video). **⏸** pausiert das Video.
- Beim Stoppen öffnet sich der **Editor**: Kapitel (Schritte der Routine, Excel-Zeilen), **A ▸ / ◂ B** für eine Auswahl, **✂ A–B schneiden**, **💬 Text A–B** (Einblendung), **▦ Bereich verdecken** (Unschärfe über persönliche Daten), **⟦ Anfang / Ende ⟧**, **lange Pausen kürzen**. Das Original bleibt unverändert; **💾 Speichern** behält die Änderungen, **GIF** / **MP4** exportieren.
- **⚙ Einstellungen → 🎥 Video**: Videoordner, **automatisches Video bei jeder Ausführung** (Studio), **ein Video pro Excel-Zeile**, auch bei geplanten Ausführungen, Aufnahmen pro Sekunde, Größe und Qualität.
- Videos bestehen aus **Screenshots, die nur bei Bildschirmänderungen gespeichert werden** (kleine `.apvid`-Dateien). Cursor und Klicks werden bei der Wiedergabe gezeichnet. **🎬** in der oberen Leiste öffnet ein gespeichertes Video.
- **Intro und Abspann** (standardmäßig an): Das Video einer Ausführung beginnt mit einem Bild mit dem Namen der Routine und der Startzeit (3 s) und endet mit einem Bild mit dem Ergebnis (✅ / ❌ und Fehlermeldung), Dauer, Schritten und Excel-Zeilen (4 s). Dazwischen bleibt, was aufgenommen wurde. Nach dem letzten Schritt läuft das Video noch **2 s** weiter, um dessen Ergebnis zu zeigen, und das letzte Bild wird beim Stoppen gespeichert; das Ende wird beim „Pausen kürzen“ nicht mehr gekürzt. Dauer und Abschalten: ⚙ Einstellungen → 🎥 Video.
- MP4 benötigt das Paket `opencv-python` (optional); GIF funktioniert immer.
- In der Excel-Schleife erhält bei aktivem Video jede Zeile in der Spalte **Film** den Link zum Video und die Minute, in der die Zeile beginnt (Spalte in den Eigenschaften der Schleife ändern oder abschalten). Derselbe Link steht im Laufbericht. Doppelklick auf eine `.apvid`-Datei (oder Klick auf den Link in Excel) öffnet sie im Player, ohne die App zu starten.

> Beispiel: Einstellungen → Video → „Video bei jeder Ausführung“ und „ein Video pro Excel-Zeile“ ankreuzen; Routine 03 ausführen — im Ordner entsteht pro Zeile ein Video mit Kapiteln für jeden Schritt.

## 22. Der Excel-Bericht des Laufs (Arbeitsnachweis)

1. **⚙ Routineneinstellungen → 📊 Excel-Bericht des Laufs**: „Bei jedem Lauf einen Excel-Bericht erstellen“ anhaken.
2. Die **Wertspalten** anhaken (Variablen, Spalten der Eingabe-Excel, gelesene Werte). Das geht auch direkt am Schritt: **📊 Wert in den Excel-Bericht des Laufs übernehmen** (bei Schritten, die einen Wert speichern, und bei „Variable setzen“).
3. Ordner wählen (leer = `rezultate\rapoarte`) und was in den Bericht kommt: Spalte „Ausgeführte Schritte“, Blatt „Schritte“ (jeder Schritt mit Uhrzeit, Ergebnis und Regel), Routinendefinition.
4. Ausführen. Am Ende zeigt das Log `📊 Bericht: ...`.
- Eine Zeile pro Excel-Zeile oder Wiederholung der obersten Ebene; ohne Schleifen eine Zeile für die ganze Routine. Funktioniert auch ohne Eingabe-Excel.
- Jede Zeile enthält Startzeit, Dauer, Status, Meldung, die angehakten Werte, das Video (mit der Zeit im Video) und den Fehler-Screenshot. Das Video erscheint, wenn es in ⚙ Einstellungen → Video aktiv ist.
- Die Eingabe-Excel erhält weiterhin den Status und alles, was du mit **📝 In Excel schreiben** schreibst.
- **Laufend gespeichert, und Cloud**: Der Bericht wird nach jeder Zeile / Wiederholung gespeichert (höchstens alle paar Sekunden) und bleibt erhalten, wenn die App einfriert. Berichtsordner und Videoordner (⚙ Routineneinstellungen → 🎥 Videos der Routine) sind pro Routine wählbar; **☁ OneDrive** legt den Ordner ins synchronisierte OneDrive, sodass die Dateien automatisch in die Cloud gelangen. Ein abrupt unterbrochenes Video wird beim Öffnen aus den bereits gespeicherten Bildern wiederhergestellt.

> Beispiel: eine Liste eindeutiger Nummern. In der Schleife: Ist `{Rand.Data}` leer, das Datum aus dem Link lesen, formatieren und eintragen; sonst Button Y drücken. `Rand.Nr`, `DataCitita` und `Actiune` für den Bericht anhaken. Der Bericht zeigt für jede Nummer, was wann getan wurde und wo im Video.

## 23. Routinen-Manager und Vorbereitungen

1. **📂 Routinen-Manager** (Studio-Leiste): die Routinen im gewählten Ordner, beim Start der App gelesen. **Ordner ändern** wählt einen anderen Ordner (z. B. in Drive).
2. Aus der Liste: **In Studio öffnen**, **▶ Ausführen** oder **➕ Zur Vorbereitung hinzufügen**.
3. Eine **Vorbereitung** ist eine Liste von Routinen, die nacheinander laufen: Reihenfolge mit ▲ ▼, „Ausführen / Auslassen“ und was bei einem Fehler passiert (stoppen oder mit der nächsten fortfahren).
4. **🎥 Video für jede Routine** und **📊 Excel-Bericht für jede Routine** anhaken, dann **💾 Speichern** (Datei `Name.pregatire.json` im Routinenordner).
5. **▶ Vorbereitung ausführen**. Pause / STOP über die schwebende Leiste (Strg+F11 / Strg+F12); Rückfragen und Präventionssystem bleiben aktiv.
- Am Ende: ein Ordner `rezultate\pregatiri\Name_Datum_Uhrzeit` mit `Pregatire_Name.xlsx` (Zusammenfassung und Definitionen), `Documentatie.html` (alles, was getan wurde, im Detail), den Berichten und Links zu den Videos.
- Eine Vorbereitung lässt sich wie eine Routine planen: `py -m rpr run "Sandbox.pregatire.json"`.

> Beispiel: ein Test-Sandbox mit `01_Benutzer`, `02_Rollen`, `03_Objekte`. Du startest die Vorbereitung abends; morgens öffnest du die Dokumentation und siehst für jede Routine, wie lange sie dauerte, was sie angelegt hat und ihr Video.

## 24. Sicherung und Wiederherstellung

1. **⚙ Einstellungen → 💾 Sicherung und Wiederherstellung → Sicherung erstellen...**: wähle, wo die `.zip`-Datei gespeichert wird (z. B. USB-Stick oder Drive-Ordner).
2. „Auch die Ergebnisse einschließen“ nur anhaken, wenn du auch Berichte, Studio-Logs und Fehler-Screenshots willst (die Datei wird größer).
3. Auf einem anderen PC oder nach einer Neuinstallation: **♻ Aus Sicherung wiederherstellen...**, Datei wählen, bestätigen, dann AutoPilot DC neu starten.
- Enthalten: Einstellungen, Recorder- und Studio-Routinen, die Objektbibliothek mit Bildern, Zeitpläne, Notizen, Sprache, Video-Einstellungen und der Routinenordner aus 📂 Manager.
- Nicht enthalten: das Browserprofil (Anmeldungen) und die Videos.
- Vor der Wiederherstellung wird der aktuelle Stand automatisch in `%APPDATA%\AutoPilotDC\backup-automat` gesichert. Gibt es den Routinenordner auf dem neuen PC nicht, landen die Routinen in `Studio\rutine\biblioteca` und der Manager zeigt dorthin.

> Beispiel: Vor dem Laptopwechsel erstellst du eine Sicherung in Drive; auf dem neuen Laptop installierst du mit INSTALEAZA.bat, stellst die Sicherung wieder her und hast dieselben Routinen, Objekte und Einstellungen.

## 25. Fortsetzen nach einem unerwarteten Beenden

1. Solange eine Routine an einer Excel-Zeile arbeitet, zeigt die Statusspalte „IN LUCRU“ (in Arbeit, orange); am Ende wird daraus OK oder EROARE.
2. Wird AutoPilot DC oder der PC mitten in einem Lauf beendet, erscheint beim nächsten Start die Frage **Fortsetzen nach dem Beenden**: **Lauf fortsetzen**, **Nur öffnen** oder **Nein, verwerfen**.
3. Beim Fortsetzen werden Zeilen mit OK übersprungen. Für die Zeile mit „IN LUCRU“ wählst du: **Zeile neu ausführen**, **Ist erledigt, als OK markieren** (wenn du es im System geprüft hast) oder **Routine stoppen**.
- Bei einer Vorbereitung werden auch die fertigen Routinen übersprungen; die unterbrochene Routine macht bei ihrer Zeile weiter.
- Dieselbe Frage erscheint, wenn du die Routine von Hand neu startest und eine Zeile auf „IN LUCRU“ blieb (z. B. nach STOP).
- Schritt-für-Schritt-Läufe werden nicht fortgesetzt. Beendest du die Anwendung selbst während eines Laufs, wird kein Fortsetzen angeboten.

> Beispiel: Die Routine legt 200 Benutzer an und bei Zeile 120 fällt der Strom aus. Beim Neustart wählst du „Lauf fortsetzen“; die Zeilen 2–119 werden übersprungen, du prüfst den Benutzer aus Zeile 120 im System und wählst „Ist erledigt, als OK markieren“ oder „Zeile neu ausführen“.

## 26. Website scannen und eine Bibliothek pro Anwendung

1. 📚 Bibliothek → **＋ Neu**: Namen der Anwendung eingeben; AutoPilot schlägt `OneDrive\AutoPilotDC\obiecte\<Anwendung>\obiecte.json` vor (ohne OneDrive: in Dokumente). Jeder andere Ordner ist möglich.
2. **🔍 Website scannen**: Adresse eingeben, der AutoPilot-Browser öffnet sich. Melden Sie sich an, öffnen Sie die gewünschte Seite und wählen Sie **🔍 Automatisch scannen**.
3. Sie erhalten die Liste der sichtbaren Schaltflächen, Felder, Listen, Kontrollkästchen und Links (auch in iframes, höchstens 500). Klick auf eine Zeile **markiert sie im Browser** (so sehen Sie, welche Schaltfläche es ist); der Haken in der ersten Spalte behält sie oder lässt sie weg (oder Leertaste / **☑ Behalten / entfernen**). **✎ Umbenennen** (F2, Doppelklick auf den Namen) ändert den Namen. Oben wählen Sie **Seite** und **Ordner**, unter denen sie landen (siehe Kapitel 28). **Ohne Links** entfernt Navigationsmenüs. **💾 Zur Bibliothek hinzufügen** speichert sie.
4. Öffnen Sie ein anderes Menü oder einen anderen Tab im Browser und wählen Sie **🔍 Erneut scannen**. Objekte, die schon in der Bibliothek sind, werden übersprungen.
5. **🖐 3-s-Erfassung**: Mauszeiger 3 Sekunden auf einem Feld oder einer Schaltfläche halten (blauer Rahmen, Countdown), es wird automatisch gespeichert; dann zum nächsten. Klicks funktionieren normal, Menüs lassen sich also öffnen. Esc im Browser oder **Fertig** beendet.
- Der Scan liest nur die bereits geladene Seite: kein Klick, keine Eingabe, nichts wird an den Server gesendet, die Anwendung wird also nicht belastet. Ausgeblendete Elemente (geschlossene Menüs, andere Tabs) erscheinen erst, wenn Sie sie öffnen.
- **📂 Öffnen** wechselt die Bibliothek. Eine gespeicherte Routine merkt sich ihre Bibliothek und lädt sie beim Öffnen selbst; die Anwendung merkt sich nur den Pfad der letzten Bibliothek.
- Hat OneDrive auf dem anderen Laptop einen anderen Pfad, wird die Bibliothek an derselben Stelle im OneDrive dieses PCs gefunden.

> Beispiel: Für die Bestellanwendung legen Sie die Bibliothek „Bestellungen“ in OneDrive an, scannen die Suchseite und das Bestellformular und fügen mit der 3-s-Erfassung die Schaltfläche aus dem Menü hinzu, das nur beim Überfahren erscheint. Neue Routinen für diese Anwendung nutzen die Bibliothek „Bestellungen“.

## 27. Gespeicherte Schaltflächen prüfen (Simulation ohne Klick)

1. Öffnen Sie die Seite der Anwendung im AutoPilot-Browser (anmelden, Menü / Tab mit den Schaltflächen öffnen).
2. 📚 Bibliothek → **🩺 Prüfen** (oder nach 🔍 Website scannen **🩺 Gespeicherte Schaltflächen prüfen** wählen). Hat die Website auch Objekte auf anderen Seiten, wählen Sie **Aktuelle Seite** oder **Ganze Website**.
3. Für jedes Objekt macht AutoPilot einen „Probeklick“: dieselben Prüfungen wie bei einem echten Klick (gefunden, sichtbar, aktiv, bewegt sich nicht, nicht von einem anderen Fenster verdeckt), aber es **drückt nicht** und sendet nichts an den Server.
4. Sie erhalten die Liste: **✅** funktioniert · **⚠** funktioniert, aber mit Hindernissen (von einem Overlay verdeckt, deaktiviert, mehrfach gefunden, nur der Ersatz-Locator funktioniert, anderer Text) · **❌** muss neu erfasst werden · **·** auf einer anderen Seite. Klick auf eine Zeile zeigt die Gründe.
5. **👁 Im Browser zeigen** markiert das Element. **🔧 Locatoren reparieren** setzt den funktionierenden Locator an die erste Stelle. **🎯 Neu erfassen**: Element im Browser anklicken; der Name bleibt, Routinen, die es verwenden, funktionieren weiter. **🔄 Erneut prüfen**, nachdem Sie im Browser etwas geändert haben.
- Der Probeklick kann die Seite bis zum Element scrollen, drückt aber nichts. Eine Schaltfläche, die erst nach einer Aktion erscheint (Menü, Tab, Filter), wird geprüft, nachdem Sie sie geöffnet haben.
- Bei einem ⚠ „Verdeckt“-Element liegt meist ein Fenster oder eine Meldung darüber: schließen und erneut prüfen. Bleibt es, braucht die Routine vorher einen Schritt (Meldung schließen).

> Beispiel: Nach einem Update der Anwendung öffnen Sie die Bestellseite und drücken 🩺 Prüfen. „Speichern“ ist ✅, „Senden“ ist ⚠ deaktiviert (normal, bis das Formular ausgefüllt ist) und „Export“ ist ❌: Sie erfassen es mit einem Klick neu und die Export-Routine funktioniert wieder.

## 28. Ordner in der Bibliothek (Abschnitte unter derselben Seite)

Manche Web-Anwendungen wechseln ihre „Ordner“ (Menü, Baum links), ohne die Adresse zu ändern: immer `…/otwg20`. Damit nicht alle Schaltflächen zusammen liegen, legen Sie jedes Objekt in einen **benannten Ordner**:

1. Bei **🔍 Website scannen** wählen Sie im Ergebnisfenster oben die **Seite** und den **Ordner** (z. B. `Bestellungen/Export`; `/` erzeugt Unterordner). Bereits verwendete Ordner erscheinen in der Liste. Den zuletzt gewählten Ordner nutzt auch **🖐 3-s-Erfassung**.
2. In der Bibliothek wird der Baum zu **Website · Seite · 📁 Ordner · Schaltfläche**.
3. Für ein vorhandenes Objekt: Rechtsklick → **📁 In Ordner verschieben...** oder das Feld **Ordner** in **Bearbeiten**.
4. Rechtsklick auf einen Ordner: **✎ Ordner umbenennen...** (benennt auch die Unterordner um) und **🩺 Objekte des Ordners prüfen**.
- **Seite / Website umbenennen**: Rechtsklick auf eine 📄 Seite (oder 🌐 Website) → **✎ Seite umbenennen...**; gilt für alle Objekte darunter. Existiert der neue Name schon, werden die Seiten zusammengeführt.
- Ein Ordner gruppiert nur. Er ändert nicht, wo das Element auf der Seite gesucht wird (das macht der **Container**). Routinen ändern sich nicht: Schritte verwenden weiter den Objektnamen.
- Fenster (Objekt, Scan, Prüfung, Zeitplan) scrollen mit dem Mausrad, und die Schaltflächen **Speichern / Hinzufügen / Schließen** bleiben unten fest, sodass Sie die Fenster nicht mehr vergrößern müssen.

> Beispiel: In der Bestellanwendung hat der Ordner `Bestellungen/Import` die Schaltflächen „Datei hochladen“ und „Validieren“, und `Bestellungen/Export` hat „Excel exportieren“. Sie öffnen den Ordner in der Anwendung, scannen, wählen den Ordner, und die Schaltflächen landen am richtigen Platz.

## 29. Gespeicherte Routinen als Schritt (Tab 📋 Routinen)

Sie haben schon eine Routine mit 2–3 Schritten (z. B. die Anmeldung) und wollen sie in anderen nutzen, ohne die Schritte neu zu bauen:

1. Im **Studio RPR** oeffnen Sie neben **📚 Bibliothek** den Tab **📋 Routinen**: er zeigt die Routinen Ihres Ordners (derselbe wie im **📂 Routinen-Manager**; **📁 Ordner** aendert ihn, **↻** liest neu, das Feld oben sucht).
2. Waehlen Sie eine Routine und druecken Sie **➕ Als Schritt** (oder Doppelklick): der Schritt **📋 Routine ausfuehren** wird eingefuegt und **folgt der Datei**. Sie aendern die Routine einmal, und es gilt ueberall, wo sie verwendet wird.
3. Setzen Sie Ihre eigenen Schritte davor und danach. Routine ausfuehren nutzt **dieselben Variablen, dasselbe Excel und dieselbe Objektbibliothek**; die Einstellungen der Hauptroutine (Fehler, Pausen) gelten auch dafuer. Standardwerte der Variablen der aufgerufenen Routine werden nur uebernommen, wenn es sie noch nicht gibt.
4. **📥 Als Schritte** kopiert die Schritte in die aktuelle Routine (bearbeitbar; sie folgen dem Original nicht mehr). Bei einem vorhandenen Schritt macht **📥 Durch ihre Schritte ersetzen** dieselbe Kopie.
- Vor dem Start werden Datei, Schleifen (A ruft B, B ruft A), Tiefe (maximal 8) und fehlende Objekte geprueft; stimmt etwas nicht, startet die Routine nicht und Sie erfahren, welcher Schritt betroffen ist. Im Log erscheinen die Schritte des Blocks mit seinem Namen davor.
- Wenn Sie die Routinendatei verschieben, muss der Schritt neu darauf zeigen (Dateifeld des Schritts).

> Beispiel: `Login SAP` (2 Schritte) liegt im Routinenordner. In der Berichtsroutine: ➕ Als Schritt „Login SAP“, danach die Berichtsschritte.

## 30. „Falls es erscheint“ und Regeln fuer Meldungen / Fehler

Manchmal erscheinen Meldungen oder Fehler, die Sie vorher kennen (z. B. „Wirklich schliessen?“). Sie sollen nicht stoeren, wenn sie nicht erscheinen.

**👁 Falls es erscheint (optional)** (Ablauf): Setzen Sie den Schritt dorthin, wo die Meldung erscheinen kann, waehlen Sie das Element (unter **Bedingung**, mit **Auf das Objekt hoechstens warten** z. B. 1500 ms) und die auszufuehrenden Schritte im Zweig „Atunci“. Erscheint die Meldung nicht, laeuft die Routine ohne Fehler weiter.

**🧯 Regel fuer Meldung / Fehler** (Ablauf): Setzen Sie sie **vor** die Schritte, die sie abdeckt (erster Schritt = ganze Routine). Sie tut nichts von allein: sie wird aktiviert und bleibt bis zum Ende der Liste aktiv, in der sie steht (in einer Gruppe nur dort). **Scheitert** ein Schritt und die Regel passt, laufen die Schritte unter „Pasi de rulat“:
1. **Wenn der Fehler den Text enthaelt**: ein Teil der Fehlermeldung (ohne Gross-/Kleinschreibung) und / oder
2. **ODER ein Element / eine Bedingung ist am Bildschirm wahr** (z. B. das Meldungsfenster ist offen);
3. **Nachdem die Schritte der Regel gelaufen sind**: *Schritt wiederholen* (Standard; hoechstens 3-mal), *Schritt als erledigt ansehen* oder *Fehler wird weitergegeben*.
- Die Fehlermeldung steht in der Variablen `{EroareRegula}`. Bei mehreren Regeln wird zuerst die dem Schritt naechste geprueft.
- Regeln werden nur geprueft, wenn ein Schritt scheitert; kommt die Meldung nicht, passiert nichts. Die Schritte einer Regel loesen keine anderen Regeln aus.
- Browser: alert-/confirm-Dialoge der Seite werden automatisch akzeptiert (der Schritt „Handle dialog“ waehlt „dismiss“). Eine Meldung innerhalb der Anwendungsseite ist ein Element: behandeln Sie sie mit **Falls es erscheint** oder einer Regel.
- Waehlen Sie fuer Meldungen die Bedingung **Das Objekt ist sichtbar** (eine versteckte Meldung „existiert“ in der Seite, ist aber nicht zu sehen).
- **Demo**: Schaltflaeche **Beispiele** → **06 Demo - Daca apare si reguli la mesaj** (lokale Seite, ohne Internet): Sie druecken „Porneste“, „Wirklich fortfahren?“ erscheint, die Regel schliesst es selbst, und „Falls es erscheint“ laeuft weiter, wenn die Meldung fehlt. Starten Sie es mit **⏭ Schritt fuer Schritt**, um jeden Schritt zu sehen.

> Beispiel: am Anfang der Routine eine **🧯 Regel** mit „Sicher“ und dem Schritt Klick auf „Ja, schliessen“, dann *Schritt wiederholen*; erscheint die Meldung nicht, laeuft die Routine wie bisher.

## 31. Darstellung, Drag and Drop und Speicherorte

**🌐 Studio-Einstellungen** hat jetzt vier Registerkarten: 🌐 Browser, 🎨 Darstellung, 📁 Speicherorte, 🎬 Videos.

- **🎨 Darstellung → Textgröße**: Klein / Normal / Groß / Sehr groß, für die gesamte Anwendung (gilt nach einem Neustart). Die Breite der Studio-Bereiche wird als Prozent des Fensters gespeichert und sieht daher auf Laptop und Monitor gleich aus; **↺ Bereiche zurücksetzen** stellt die ursprüngliche Aufteilung wieder her.
- Auf kleinen Bildschirmen bleibt die obere Leiste einzeilig: Schaltflächen verlieren einen Teil des Textes (der volle Text steht im Tooltip), selten genutzte Befehle (Speichern unter…, Beispiele, Planen, Anleitung) liegen unter **⋯**.
- **Drag and Drop**: einen Schritt im Baum an eine andere Stelle ziehen (eine Linie zeigt, wo er landet; über „▸ Dann“ / „▸ Sonst“ oder über der Mitte einer Schleife kommt er hinein). Ebenso einen Block aus 🧱 Schritte, ein Objekt aus 📚 Bibliothek (Klick / Text schreiben / Lesen / Wenn vorhanden wählen) oder eine Routine aus 📋 Routinen (wird zum Schritt „Routine ausführen“).
- **📁 Speicherorte**: einen **gemeinsamen Ordner** wählen (z. B. ☁ OneDrive); Routinen, Objektbibliotheken, Ergebnisse (Screenshots, Logs, Berichte) und Videos landen in den Unterordnern `rutine`, `obiecte`, `rezultate`, `filme`. Ein ausgefülltes Feld für eine Dateiart hat Vorrang; was an einer Routine (Ordner der Videos / des Berichts) oder an einer Bibliothek eingestellt ist, hat Vorrang vor allem. Leere Felder = wie bisher.
- **🎬 Videos → Videos öffnen mit**: der AutoPilot-Player (Wiedergabe + Bearbeitung), die Standardanwendung von Windows oder eine andere Anwendung auf dem Laptop (z. B. VLC). Für andere Anwendungen wird das Video einmal als MP4 daneben exportiert (GIF, wenn opencv-python fehlt). Dieselbe Auswahl gibt es unter ⚙ Einstellungen → Video.

> Beispiel: 🌐 Studio-Einstellungen → 📁 Speicherorte → ☁ OneDrive → Speichern; eine neue, mit 💾 gespeicherte Routine schlägt den Ordner `OneDrive\AutoPilotDC\rutine` vor, Videos landen in `OneDrive\AutoPilotDC\filme`.

## 32. Aktivitaetsleiste, Tabs, Zeitachse, Excel-Ansicht und Ablauf

Studio hat links eine **Aktivitaetsleiste**: 🧱 Schritte, 📚 Bibliothek, 📋 Routinen, 🎬 Videos, unten 🌐 Einstellungen und ❓ Anleitung. Jedes Symbol wechselt nur das Feld daneben; die Routine bleibt, wo sie ist. Ein Klick auf das bereits gewaehlte Symbol **klappt das Feld ein** (mehr Platz fuer die Routine auf einem Laptop); ein weiterer Klick oeffnet es wieder. Die App merkt sich das gewaehlte Feld.

- **Tabs fuer Routinen**: jede offene Routine hat ihren Tab ueber den Schritten (● = ungespeicherte Aenderungen). **+** oder 📄 Neu oeffnet eine neue Routine in einem neuen Tab; × schliesst den Tab (mit Frage, ob gespeichert werden soll). Eine bereits offene Routine wird nicht doppelt geoeffnet: ihr Tab wird gezeigt. Waehrend eine Routine laeuft, kann der Tab nicht gewechselt werden.
- **Die Ansicht in der Mitte**: **✎ Schritte** (die Liste, zum Bearbeiten), **🔀 Ablauf** (die Routine als Ablauf aus Karten, „Dann“ und „Sonst“ nebeneinander; nur lesen: Klick auf eine Karte zeigt rechts die Eigenschaften des Schritts, Doppelklick fuehrt zum Schritt in der Liste) und **📊 Excel**.
- **🔀 Ablauf bei grossen Routinen** (v4.20): **Strg + Mausrad** (oder **−** / **+**) vergroessert und verkleinert um die Maus herum; **Hintergrund ziehen** (oder mit gedruecktem Mausrad), um die „Karte“ zu verschieben; **⤢ Einpassen** (Strg + 0) zeigt die ganze Routine, **↔ Breite** (Strg + 2) die ganze Breite, Sie scrollen nur nach unten; **1:1** (Strg + 1) = normale Groesse. Die **🗺 Karte** in der Ecke zeigt die ganze Routine und wo Sie sind: klicken oder ziehen, um dorthin zu springen. **▾ / ▸** auf einer Wenn- / Schleifen-Karte blendet ihre Zweige aus („+N“ = wie viele Schritte ausgeblendet sind); **▸ Alle einklappen** / **▾ Alle ausklappen** fuer alle. Ein in der Liste gewaehlter Schritt klappt sich von selbst auf. **⬇ Export** speichert den Ablauf als grosses **PNG** (doppelt so scharf wie am Bildschirm) oder **SVG** (oeffnet sich im Browser, beliebig zoombar); eingeklappte Zweige bleiben auch im Bild eingeklappt. (v4.21) **🗗 Eigenes Fenster** oeffnet den Ablauf in einem eigenen Fenster: auf den zweiten Monitor ziehen, **⛶ Vollbild** (F11, Esc = beenden), und den Lauf an den Farben verfolgen (gelb = laeuft, gruen = erledigt, rot = Fehler), auch wenn Studio auf 📊 Excel wechselt.
- **📊 Excel**: die Zeilen der Datei aus dem ersten Schritt „Fuer jede Excel-Zeile“, mit Status und Minute im Video. Beim Ausfuehren einer Routine mit Excel oeffnet sich diese Ansicht von selbst und zeigt die Zeile in Arbeit. Waehle eine Zeile: rechts stehen ihre Schritte, der Fehler und sein Screenshot; **↻ Zeile wiederholen** fuehrt nur diese Zeile erneut aus (plus die Schritte vor der Schleife, z. B. Browser oeffnen), **🎬 Im Video ansehen** oeffnet das Video des Laufs an der Minute der Zeile (wenn die Aufnahme beim Ausfuehren unter Einstellungen → Video aktiv ist).
- **⏱ Zeitachse** (unten, neben dem Log): eine Karte fuer jeden fertigen Schritt, mit ✓ / ✕, Excel-Zeile, Dauer und bei Fehlern Meldung und Screenshot (Doppelklick auf den Screenshot oeffnet ihn gross). Klick auf eine Karte zeigt den Schritt in der Routine.
- **🎬 Videos**: die gespeicherten Videos, die neuesten zuerst; Doppelklick oeffnet sie mit der App aus 🌐 Studio-Einstellungen → 🎬 Videos.

> Beispiel: Oeffne **Beispiele → 03 Web + Excel** und druecke ▶ Ausfuehren. Die Mitte wechselt zu 📊 Excel und faerbt jede Zeile (gruen OK, rot Fehler). Waehle eine rote Zeile, lies rechts den Fehler und druecke ↻ Zeile wiederholen.

## 33. 📥 KI-Import: eine Routine aus einem Word-Dokument

Sie haben die Vorgehensweise in einem Word-Dokument. Eine KI (ChatGPT, Copilot, Claude...) macht daraus **AutoPilot-Schritte**, einfachen Text mit einem Schritt pro Zeile, und Studio baut daraus die Routine.

1. In Studio **📥 KI-Import** drücken (linke Leiste oder **⋯ → 📥 Schritte importieren**).
2. **📋 Prompt für die KI kopieren** und in die KI einfügen; danach den Text der Vorgehensweise einfügen (oder das Word-Dokument anhängen). Der Prompt erklärt Format und Regeln in der Sprache der Anwendung (**💾 Prompt speichern** legt ihn als Datei ab).
3. Die Antwort der KI in das Importfenster einfügen (oder **📂 Datei öffnen**: `.txt`, `.json`, `.rpr.json`). Die Prüfung läuft automatisch: rechts die Schritte, unten die Probleme; fehlerhafte Zeilen werden eingefärbt (Klick auf ein Problem = seine Zeile).
4. **✅ Routine erstellen**: Sie öffnet sich in einem neuen Tab (ungespeichert). Neue Schaltflächen und Felder kommen in die 📚 Bibliothek, gefunden über den Text auf dem Bildschirm.
5. **🎯 Objekte vervollständigen** (direkt nach dem Import angeboten; jederzeit über 📚 Bibliothek → 🎯 Vervollständigen oder ⋯ → 🎯 Objekte der Routine vervollständigen): die Objekte der Routine in der Reihenfolge der Schritte. Öffnen Sie die Seite im Browser (oder führen Sie ⏭ Schritt für Schritt bis dorthin aus) und drücken Sie **🧪 Alle prüfen**: Ohne Klick erhält jedes ✔ gefunden, ⚠ mehrere gleiche Elemente oder ✖ nicht gefunden. Bei ✖ / ⚠ **🎯 Im Browser markieren** (oder Doppelklick) und auf das Element klicken (SAP / Desktop: F2): Das Objekt erhält die erfassten Lokatoren (id, css, xpath, Frame), der alte Text bleibt als Reserve, Name und Schritte der Routine ändern sich nicht. **⏭ Nächstes nicht gefundenes** springt zum nächsten. Objekte mit `{Variablen}` werden beim Ausführen geprüft. **▶ Ausführen und markieren**: Für Objekte auf anderen Registerkarten oder Abschnitten läuft die Routine von Anfang an, nur für die erste Excel-Zeile, und öffnet die Registerkarten selbst. Wird ein Objekt nicht gefunden, hält der Lauf an: **🎯 Jetzt markieren**, Element anklicken, der Schritt wird wiederholt. Die Schritte werden wirklich ausgeführt (Save, Trigger…), verwenden Sie also eine Testzeile. Dann füllen Sie die Variablen in ⚙ Routine aus, führen Sie **⏭ Schritt für Schritt** aus und speichern Sie (💾). Automatischer Zeitplan: 🕒 Planen.

Das Format (Schlüsselwörter auf Englisch oder Rumänisch, Groß- oder Kleinschreibung egal):

- Kopf: `ROUTINE: <Name>`, `DESCRIPTION: <Text>`, `VARIABLE: Name = Wert`.
- Schritte: `OPEN BROWSER <url>`, `GO TO <url>`, `CLICK <Objekt>`, `TYPE <Objekt> = <Text>`, `SELECT <Objekt> = <Option>`, `CHECK <Objekt>`, `PRESS Enter`, `READ <Objekt> -> {Var}`, `WAIT 2` oder `WAIT <Objekt> MAX 15`, `LOG "Text"`, `ASK "Text"`, `MANUAL "was der Mensch tut"`, `SAP TRANSACTION /nVA03`, `START APP notepad.exe`.
- Blöcke: `IF <Bedingung>` … `ELSE` … `END`, `REPEAT 3` … `END`, `FOR EACH ROW {File} SHEET Daten` … `END` (Werte: `{Rand.Spalte}`, Schreiben: `WRITE EXCEL Ergebnis = OK`), `TRY` … `ON ERROR` … `END`.
- `IF` … `ELSE` … `END` hat **nur ein** `END`, nach dem `ELSE`-Zweig. Ein `IF` (oder `IF APPEARS`) innerhalb eines anderen `IF` wird mit seinem eigenen `END` geschlossen. Mehrere Fälle: `ELSE IF <Bedingung>`, weiterhin mit nur einem `END` am Ende. `IF APPEARS <Objekt>` akzeptiert ebenfalls `ELSE`. Der Fehler „ELSE nach END“ nennt die Zeile des zu löschenden `END`.
- `ASK VALUE "Text" -> {Var}`: Beim Ausführen erscheint ein Eingabefeld, der Wert kommt in die Variable (z. B. ein Datum aus einem anderen System). **Abbrechen** stoppt die Routine. In Studio: der Schritt 💬 Frage mit angehaktem „Eingabefeld“.
- Variablen funktionieren auch im Text von Objekten: `CLICK text "{Rand.UEID}"` sucht in jeder Zeile den Excel-Wert (die Bibliothek behält `{Rand.UEID}`).
- `VARIABLE:` im Kopf gibt den Startwert; innerhalb eines Blocks wird daraus ein `SET`-Schritt.

**Die Quelle kann auch Code sein** (C#, VBA, Python, Selenium, SilkTest, UiPath) oder eine Vorgehensweise mit Bildern. Der Prompt bittet die KI, die Selektoren aus dem Code zu behalten (`id`, `css`, `xpath`, `sap`), die Objekte aus der 📚 Bibliothek zu verwenden (der kopierte Prompt listet sie auf) und mit `# TODO: …` die Stellen zu markieren, an denen Sie eingreifen (geratener Selektor, Wert aus einem anderen System, unklare Entscheidung). Beim Import erscheint jedes `# TODO` gelb in der Problemliste (es blockiert das Erstellen nicht) und bleibt im Kommentar des Schritts (💬 im Baum). Eine lange Antwort über mehrere Nachrichten kann ganz eingefügt werden: Die Codeblöcke werden zusammengefügt. Mit Scan oder 🎯 Spy erfasste Objekte werden auch über ihren Text wiederverwendet, mit allen Lokatoren.
- Objekte: `button "Speichern"`, `field "Benutzer"`, `link "..."`, `list "Land"`, `checkbox "..."`, `text "..."`, `css "#id"`, `sap "wnd[0]/usr/..."`, `desktop "Name"` oder `[Name]` aus der Bibliothek.
- Bedingungen: `{Var} = "x"`, `{Var} contains "x"`, `visible button "OK"`, `exists [Name]`, verknüpft mit `AND` / `OR`.
- Eine vollständige `.rpr.json`-Routine wird ebenfalls angenommen. Was nicht automatisierbar ist, wird `MANUAL`: Die Routine hält an und wartet auf Weiter.

> Beispiel: Im Importfenster **📝 Beispiel** drücken: eine Auftragserfassung aus einer Excel-Datei erscheint; rechts sehen Sie die Routine mit Schleife und Bedingung; ✅ Routine erstellen öffnet sie in Studio.

## 34. 🔍 In der Bibliothek suchen: Filter, Zustand, Favoriten, „Verwendet in“

Bei Hunderten oder Tausenden von Objekten blättern Sie nicht mehr im Baum: Sie tippen, was Sie auf dem Bildschirm sehen.

1. Tippen Sie in **📚 Bibliothek** den Text der Schaltfläche in das Suchfeld, z. B. `salv`. Gefunden werden „Salvează“ und „Save“, ohne Akzente und ohne Groß-/Kleinschreibung, auch mit einem Tippfehler.
2. Die Treffer erscheinen als **einfache Liste**, beste zuerst (☰). Die Schaltfläche ☰ / 🌳 wechselt zum Baum Anwendung → Bild.
3. Eingrenzen mit den Listen unter der Suche: **Typ** (Schaltfläche, Textfeld, ComboBox, Tabelle, RefList…) und **Zustand**: ✅ beim letzten Test funktioniert, ❌ defekt, ⚪ in keiner Routine benutzt, 🕐 in den letzten 7 Tagen benutzt, ⭐ Favorit.
4. Oder Kürzel direkt in die Suche schreiben: `typ:combo`, `app:SAP`, `seite:VA03`, `status:defekt`, `#schlagwort`. Bilder mit Leerzeichen in Anführungszeichen: `seite:"Auftragsliste"`.
5. Klick auf ein Objekt: unter der Liste sehen Sie den Text auf dem Bildschirm, Anwendung / Bild, den ersten Locator, das letzte Testergebnis und in wie vielen Routinen es verwendet wird. **👁** zeigt es in der Anwendung (Web, SAP, Desktop), **⭐** macht es zum Favoriten, **📋** öffnet „Verwendet in“: die Routinen und Schritte, die es benutzen (Doppelklick = Routine öffnet beim Schritt).

- **🔎 Vom Bildschirm finden** (neben ☰): Web / SAP GUI / Desktop wählen und das Element wie mit Spy markieren (Web: Klick im Browser; SAP / Desktop: Maus auf das Element + F2). Nichts wird gespeichert: die Bibliothek entfernt die Filter und wählt das gespeicherte Objekt aus. Findet sie mehrere Objekte für dasselbe Element, zeigt sie diese in der Liste (Duplikate). Findet sie keines, fragt sie, ob es jetzt gespeichert werden soll. Umgekehrt: aus der Liste zeigt **👁** das Objekt in der Anwendung.
- Favoriten und zuletzt benutzte Objekte stehen oben in der Gruppe **⭐ Favoriten und zuletzt benutzt**.
- Der Zustand wird automatisch bei 🧪 Test, bei 🩺 Prüfen und beim Einfügen in eine Routine notiert. Er liegt in `obiecte.stare.json` neben der Bibliothek; `obiecte.json` ändert sich nicht.
- „Verwendet in“ liest die Routinen im Routinenordner (📋 Routinen → 📁 Ordner) und im Ordner `rutine` neben der Bibliothek.
- **🧪 Testbibliothek** (neben 📁): erstellt einen Ordner `Biblioteca_test` mit 3000 erfundenen Objekten (Web, SAP, Desktop) und 25 Routinen, um die Suche auszuprobieren. Sie wählen, wo der Ordner entsteht. **🧪 → Löschen** löscht nur einen so erstellten Ordner und kehrt zur Standardbibliothek zurück. **🧪 → Andere Bibliothek öffnen** wechselt den Ordner.

> Beispiel: Sie haben 3000 Objekte und suchen die Speichern-Schaltfläche in VA03. Sie tippen `salv app:sap seite:va03`, es erscheint eine Zeile; 👁 zeigt sie auf dem SAP-Bild und 📋 sagt, dass sie in 4 Routinen verwendet wird.

## 35. 🧹 Bibliothek aufräumen: Duplikate, unbenutzt, defekt

Weniger Objekte machen die Bibliothek leichter zu benutzen. **🧹** (in 📚 Bibliothek, neben 🧪) öffnet zwei Listen.

1. **🔁 Duplikate**: Objekte, die mehrmals für dasselbe Element gespeichert wurden. *Sicher* = gleicher Locator (id, css, xpath, SAP-ID…). *Wahrscheinlich* = gleicher sichtbarer Text und Typ auf demselben Bild. ⭐ zeigt das zum Behalten vorgeschlagene Objekt (das in mehr Routinen benutzte).
2. Wählen Sie das zu behaltende Objekt und drücken Sie **⭐ Dieses behalten und Gruppe zusammenführen**. Die anderen verschwinden. Das behaltene erhält ihre Locatoren (als Reserve) und Schlagwörter. Schritte und Bedingungen in Routinen wechseln auf seinen Namen, ebenso die Objekte in ihren Containern und die in Studio geöffneten Routinen.
3. **🔁 Alle sicheren Gruppen zusammenführen** macht dasselbe in einem Schritt für alle Gruppen mit gleichem Locator. *Wahrscheinliche* Gruppen zuerst mit **👁** prüfen.
4. **🗑 Unbenutzt / defekt**: Objekte in keiner Routine des Routinenordners und solche, die beim letzten Test fehlschlugen. Favoriten und Container mit Objekten darin erscheinen nicht. Auswählen und **🗑 Ausgewählte löschen** drücken.

- Vor jedem Zusammenführen oder Löschen werden Bibliothek und betroffene Routinen nach `_backup_biblioteca\<Datum>` neben der Bibliothek kopiert. Zum Rückgängigmachen die Dateien zurückkopieren (`de_unde.json` sagt, woher sie kamen).
- „Unbenutzt“ sieht nur Routinen im Routinenordner und in `rutine` neben der Bibliothek. Eine anderswo abgelegte Routine wird nicht gesehen.

> Beispiel: in der Testbibliothek (🧪) zeigt 🧹 → 🔁 Duplikate Paare wie `Buton_Anuleaza_Standard` und `Buton_Anuleaza_Standard_copie` (sicher). 🔁 Alle sicheren Gruppen zusammenführen vereint sie; Routinen, die `_copie` benutzten, verwenden jetzt das behaltene Objekt.

## 36. 🧩 Objekte mit Parameter und 📌 gemeinsame Teile

Viele Schaltflächen unterscheiden sich nur durch ihren Text (Speichern, Abbrechen, Senden…). Statt je eines Objekts behältst du **ein einziges Objekt mit Parameter**: in den Locatoren wird der Text zu `{Text}`, und jeder Schritt sagt, welchen Wert er hat.

1. In 📚 Bibliothek Rechtsklick auf eine gespeicherte Schaltfläche → **🧩 Daraus ein Objekt mit Parameter machen...**. Gib den Namen des Parameters (Standard `Text`) und den Namen des neuen Objekts an.
2. Im neuen Objekt ist der Text der Schaltfläche in den Locatoren durch `{Text}` ersetzt. Locatoren ohne Text (id, css, xpath…) werden deaktiviert, weil sie immer dieselbe Schaltfläche finden würden.
3. Im Schritt das Objekt wählen. Darunter erscheint das Feld **Parameter: Text**: `Speichern` eintragen. Eine Variable geht auch, z. B. `{Rand.Nume}`. Ebenso in Bedingungen (Wenn erscheint…).
4. **🧪 Testen** und **👁 Zeigen** fragen zuerst nach dem Parameterwert.
5. Für Elemente, die auf allen Bildschirmen der Anwendung erscheinen (SAP-Leiste, Kopfzeile der Website, Menü): Rechtsklick → **📌 Gemeinsam in der ganzen Anwendung**. Das Objekt kommt in die Gruppe **📌 Gemeinsam (alle Bildschirme)** und wird auf jedem Bildschirm der Anwendung gefunden.

- Parameter kannst du auch von Hand schreiben: in ✎ Bearbeiten das Feld **Parameter** (z. B. `Text`) und `{Text}` in den Locatoren.
- Im 📥 KI-Import: `CLICK [Schaltflaeche_mit_Text](Text=Speichern)`.
- Alte Routinen und Bibliotheken öffnen sich wie bisher; Parameter sind neue, optionale Felder.

> Beispiel: aus `Schaltflaeche_Speichern` machst du `Schaltflaeche_mit_Text` (der Locator `text=Speichern` wird `text={Text}`). Die Schritte „Click Schaltflaeche_mit_Text (Text=Speichern)“ und „Click Schaltflaeche_mit_Text (Text=Abbrechen)“ nutzen dasselbe Objekt.

## 37. 📱 Tests auf einem Android-Telefon

AutoPilot kann Routinen auf einem Android-Telefon oder -Tablet über **Appium** ausführen (ein eigenes Programm, das das Telefon steuert). Appium startet nur, wenn die Routine Telefonschritte hat, der Rest der App bleibt also genauso schnell. iOS folgt später: dafür braucht es einen Mac oder eine Gerätefarm in der Cloud.

**Einmalig, auf dem Laptop:**
1. Android platform-tools (`adb`) im PATH oder in `ANDROID_HOME`.
2. Node.js, dann `npm install -g appium` und `appium driver install uiautomator2`.
3. `py -m pip install --user Appium-Python-Client`.
4. Auf dem Telefon: Entwickleroptionen → **USB-Debugging** an; bei der ersten Verbindung „USB-Debugging zulassen“ bestätigen.

**Die Routine:**
1. Erster Schritt: **📱 Mobil: Telefon verbinden**. Wert: `Telefon | Paket/Aktivität`, z. B. `R58M12 | com.firma.app/.MainActivity`. Leeres Telefon = das erste verbundene.
2. In den Schritteigenschaften **📱 Telefon prüfen** drücken: Sie sehen, ob adb, das Telefon (verbunden, entsperrt), die App, der Akku und Appium in Ordnung sind, ohne etwas auszuführen.
3. Telefonobjekte haben die Technologie **Mobil (Android)** und Locatoren **AccessibilityId**, **ResourceId** (z. B. `com.firma.app:id/login`), **UiAutomator**, **XPath** oder **Text**. Sie sehen sie auf dem Telefon mit Appium Inspector.
4. Die üblichen Schritte funktionieren auf dem Telefon: Klick (Tippen), Doppelklick, Rechtsklick (langes Drücken), Text schreiben, Lesen, Ankreuzen, Aus Liste wählen, Taste drücken (Enter, Back, Home...). Zusätzlich: **Mobil: Wischen** (hoch / runter / links / rechts), **Mobil: Zurück**, **Mobil: Bildschirmfoto**, **Mobil: App schließen**.

**Die Ergebnisse** jedes Laufs liegen im Ergebnisordner (oder im gemeinsamen Ordner): `mobil\<Datum_Uhrzeit>_<Routine>\<Telefon>\`, mit den Bildschirmfotos, dem Video des Telefonbildschirms (`ecran_telefon.mp4`), `logcat.txt`, `telefon.txt` und dem Excel-Bericht des Laufs.

- Beim Verbinden wird das Telefon zuerst geprüft. Stimmt etwas nicht (gesperrt, App fehlt...), stoppt die Routine mit der Liste der Probleme und berührt nichts.
- Ohne Oberfläche: `py -m rpr device "R58M12 | com.firma.app"` führt nur die Prüfung aus.
- Die App-Daten werden beim Verbinden nicht gelöscht (Sie bleiben angemeldet).
