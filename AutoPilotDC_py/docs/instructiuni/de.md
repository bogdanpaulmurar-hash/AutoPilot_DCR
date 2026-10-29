# AutoPilot DC Anleitung

Jedes Kapitel erklärt kurz einen Ablauf, Schritt für Schritt, mit einem Beispiel. Wählen Sie links ein Kapitel oder suchen Sie nach einem Wort.

> Variablennamen wie `{Azi}` (heute), `{Acum}` (jetzt), `{Rand.…}` (Excel-Zeile) und `{Repetare}` (Schleifenzähler) sind in allen Sprachen gleich, damit Routinen bei allen Kollegen funktionieren.

## 1. Start und Oberfläche

- Starten Sie die Anwendung mit **AutoPilot_DC.pyw** im Ordner `AutoPilotDC_py` oder über die Desktop-Verknüpfung „AutoPilot DC“ (ohne CMD-Fenster).
- Beim ersten Mal (oder auf einem neuen Laptop) **INSTALEAZA.bat** ausführen: installiert alles Nötige ohne Administratorrechte. Das Fenster bleibt offen, bis Sie eine Taste drücken.
- Oben ist der Bereichsumschalter: **🎬 Recorder** (Bildschirmkoordinaten), **🧩 Studio RPR** (Objekte), **📖 Anleitung** (hier).
- Die Schaltflächen darunter wechseln mit dem geöffneten Bereich und rücken in eine zweite Zeile, wenn das Fenster schmal ist.
- **🚨 NOT-STOPP** (oder F12) beendet jede Ausführung sofort.
- Tray-Symbol neben der Uhr: Klick = Anwendung öffnen; Rechtsklick = Recorder, Studio, NOT-STOPP, Beenden.

> Beispiel: Anwendung öffnen, 🧩 Studio RPR drücken, dann 📚 Beispiele und „01 Invatare“ (Lernen) öffnen.

## 2. Recorder: Aufnahme und Wiedergabe

[video:01_recorder]

1. Im **🎬 Recorder** **⏺ Aufnehmen** (F5) drücken.
2. Die Aktionen am Bildschirm ausführen (Klicks, Text, Tasten). Ein grüner **REC**-Rahmen erscheint.
3. **⏹ Aufnahme stopp** (F6) drücken. Die Schritte erscheinen in der Liste.
4. Anzahl der **Wiederholungen** wählen und **▶ Ausführen** (F7) drücken. Der Rahmen wird rot **RUN**.
5. **Pause** = F8, **Stopp** = F9, **NOT-STOPP** = F12.
6. **💾 Speichern** (Ctrl+S) legt die Routine in `rutine_salvate` ab; im Tab **📁 Routinen** per Doppelklick wieder öffnen.

> Beispiel: Öffnen des Editors und Schreiben von „Test“ aufnehmen, Wiederholungen = 3, dann Ausführen.

> Hinweis: Der Recorder arbeitet mit Koordinaten. Wird das Fenster verschoben oder ändert sich die Auflösung, landet der Klick woanders. Für stabile Routinen Studio verwenden.

## 3. Recorder: Step Builder, Bearbeiten, Debuggen

- **🔧 Step Builder**: Schritte einzeln hinzufügen (Typ, Koordinaten, Tasten, Text, Pause, Frage an den Benutzer). **📍 Mausposition erfassen** liefert die Koordinaten in 3 Sekunden.
- Doppelklick auf einen Schritt = bearbeiten. **▲/▼** verschiebt, **⊘ Überspringen** lässt ihn bei der Ausführung aus.
- **🐛 Schritt debuggen** führt einen einzelnen Schritt als Test aus; **🔍 Simulieren** zeigt, was er täte, ohne es zu tun.
- **📊 Excel**: dieselbe Routine für jeden Wert eines Excel-Bereichs ausführen (z. B. `A1:A100`).
- **📋 Log** speichert jede Ausführung; Export als XLSX / CSV / JSON. **📝 Notizen** ist ein einfacher Notizblock.

> Beispiel: Im Step Builder „Text schreiben“ mit `{valoare}` hinzufügen, dann im Excel-Tab Datei und Bereich `A2:A20` wählen.

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

- **⚙ Einstellungen** (Anwendung): Verzögerung und Geschwindigkeit der Wiedergabe, Countdown, Aufzeichnung von Mausbewegungen, Sicherheit bei der Ausführung, Tastenkürzel, **Start mit Windows** (optional direkt ins Tray), die Schaltfläche ✕ versteckt ins Tray, Desktop-Verknüpfung, **Sprache** (Română / English / Deutsch) und Design. Sprache und Design gelten nach einem Neustart.
- **🌐 Studio-Einstellungen**: Browser für Web-Schritte (Edge empfohlen, Chrome), ohne Fenster (nur für Zeitpläne), Minimieren bei Ausführung, Browser schließen, Browserprofil löschen (Abmeldung).
- **⚙ Routineeinstellungen**: Fehlerverhalten, Objektmarkierung, Standard-Timeout, Pause zwischen Schritten, Wiederholungen, Screenshots, Nicht stören, Schutz, Variablen.

> Beispiel: Einstellungen → Sprache → English → Einstellungen speichern → die Anwendung startet auf Englisch neu.

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
- **⚙ Einstellungen → 🎥 Video**: Videoordner, **automatisches Video bei jeder Ausführung** (Studio und Recorder), **ein Video pro Excel-Zeile**, auch bei geplanten Ausführungen, Aufnahmen pro Sekunde, Größe und Qualität.
- Videos bestehen aus **Screenshots, die nur bei Bildschirmänderungen gespeichert werden** (kleine `.apvid`-Dateien). Cursor und Klicks werden bei der Wiedergabe gezeichnet. **🎬** in der oberen Leiste öffnet ein gespeichertes Video.
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
