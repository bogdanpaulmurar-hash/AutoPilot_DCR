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

1. Scripting aktivieren: SAP GUI → Optionen → Barrierefreiheit und Scripting → Scripting → **Scripting aktivieren** (Warnungen abwählen). Auf dem Server muss `sapgui/user_scripting` TRUE sein.
2. SAP Logon öffnen und anmelden.
3. Erster Schritt der Routine: **🟦 SAP: verbinden** (leer = erste Sitzung).
4. **🟦 SAP: Transaktion** mit `/nVA03` (beendet die aktuelle Transaktion und startet VA03).
5. **🎯 SAP**: Maus über das Feld (roter Rahmen) und **F2**. Lässt sich die Position nicht bestimmen, ins Feld klicken und F2 drücken.
6. **🟦 SAP: Taste** (Enter, F3, F8, Shift+F4, Ctrl+S) und **🟦 SAP: Statusleiste** (`S:` Erfolg, `E:` Fehler, `W:` Warnung).
7. Tabellen: **SAP: Tabellenzelle lesen** mit `Zeile|Spalte` (z. B. `0|MATNR`); die Tabelle scrollt selbst zur Zeile.

> Beispiel: Routine 04 „SAP VA03“ liest die Auftragsnummern aus Excel und schreibt den Status in die Spalte Status.

## 9. Windows-Desktop-Anwendungen

1. **🖥 Anwendung starten** (`notepad.exe` oder `"C:\Program Files\App\app.exe" /param`) oder **🖥 Fenster verbinden** (`proces:notepad.exe` oder der Fenstertitel).
2. **🎯 Desktop**: Maus über das Element (grüner Rahmen) und **F2**; Esc = abbrechen.
3. Das Objekt in Schritten verwenden: Klick, Text schreiben, Lesen, Aus Liste wählen, Ankreuzen.
- Vor jedem Klick wird das Anwendungsfenster nach vorne geholt und das Element in den sichtbaren Bereich gescrollt. Wäre der Punkt von einem anderen Fenster verdeckt, erfolgt der Klick ohne Maus (UI Automation) oder der Schritt stoppt mit einer Meldung — nie in einem anderen Fenster.
- **Listen (Unterhaltungen, E-Mails)**: Spy erfasst die ganze Zeile. Namen mit wechselndem Text erhalten ein Muster, z. B. `ListItem|Ion Popescu*` (`*` = beliebiger Text).
- **Direktmodus** (im Schritt): Aktionen ohne Mausbewegung, wo die Anwendung es erlaubt.

> Beispiel: Routine 05 „Desktop Notepad“ startet den Editor und schreibt drei Zeilen in einer Schleife.

## 10. Die Objektbibliothek

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

## 20. Dateien, Ordner und Kollegen

- Die Anwendung: Ordner `AutoPilotDC_py` (kopieren oder mit `git pull` holen). Recorder-Routinen: `rutine_salvate`, Logs: `loguri`.
- Studio: `%APPDATA%\AutoPilotDC\Studio` — `rutine` (Routinen), `rezultate` (Logs, Screenshots), `obiecte.json` (die Bibliothek), `exemple`, `browser-profil`.
- Für einen Kollegen: die `.rpr.json`-Datei und `obiecte.json` senden; der Kollege führt einmal INSTALEAZA.bat aus.
- Die Version steht in der unteren Leiste; Neuerungen in `CHANGELOG.md`.
