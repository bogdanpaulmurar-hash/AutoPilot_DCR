# AutoPilot DC instructions

Each chapter briefly explains one procedure, step by step, with an example. Pick a chapter on the left or search for a word.

> Variable names such as `{Azi}` (today), `{Acum}` (now), `{Rand.…}` (Excel row) and `{Repetare}` (loop counter) are the same in every language, so routines work for all colleagues.

## 1. Starting and the interface

- Start the application with **AutoPilot_DC.pyw** in the `AutoPilotDC_py` folder or with the "AutoPilot DC" desktop shortcut (no CMD window).
- The first time (or on a new laptop) run **INSTALEAZA.bat**: it installs everything needed, without administrator rights. The window stays open until you press a key.
- At the top is the area switch: **🎬 Recorder** (screen coordinates), **🧩 Studio RPR** (objects), **📖 Instructions** (here).
- The buttons below the switch change with the open area and wrap to a second row when the window is narrow.
- **🚨 EMERGENCY STOP** (or F12) stops any run immediately.
- Tray icon next to the clock: click = open the application; right-click = Recorder, Studio, EMERGENCY STOP, Exit.

> Example: open the application, press 🧩 Studio RPR, then 📚 Examples and open "01 Invatare" (learning).

## 2. Recorder: recording and playback

[video:01_recorder]

1. In **🎬 Recorder** press **⏺ Record** (F5).
2. Perform the actions on screen (clicks, text, keys). A green **REC** border appears around the screen.
3. Press **⏹ Stop Rec** (F6). The steps appear in the list.
4. Choose the number of **Repetitions** and press **▶ Run** (F7). The border turns red **RUN**.
5. **Pause** = F8, **Stop** = F9, **EMERGENCY STOP** = F12.
6. **💾 Save** (Ctrl+S) keeps the routine in `rutine_salvate`; reopen it from the **📁 Routines** tab (double-click).

> Example: record opening Notepad and typing "Test", set Repetitions = 3, then Run.

> Note: the Recorder works with coordinates. If the window moves or the resolution changes, the click lands elsewhere. For stable routines use Studio.

## 3. Recorder: Step Builder, editing, debugging

- **🔧 Step Builder**: add steps one by one (type, coordinates, keys, text, pause, question to the user). **📍 Capture mouse position** gives you the coordinates within 3 seconds.
- Double-click a step = edit. **▲/▼** moves it, **⊘ Skip** skips it when running.
- **🐛 Debug step** executes a single step as a test; **🔍 Simulate** shows what it would do without doing it.
- **📊 Excel**: run the same routine for every value of an Excel range (e.g. `A1:A100`).
- **📋 Log** keeps every run; export it to XLSX / CSV / JSON. **📝 Notes** is a simple notepad.

> Example: in the Step Builder add "Type text" with `{valoare}`, then in the Excel tab choose the file and the range `A2:A20`.

## 4. Run safety

- **🌙 Do not disturb**: Windows notifications are off while a routine runs or records, so you don't click them by mistake. They come back by themselves at the end.
- **Screen border**: red + RUN when running, green + REC when recording, orange when paused. The border is not visible in screenshots and does not receive clicks.
- **🛡 Prevention system**: before every step it checks whether you moved the mouse, an error window appeared, the application is not responding or the screen looks different than when recording. The routine then pauses and asks: **Continue / Retry / Skip / Stop**.
- Turn them on in **⚙ Settings → 🛡 Run safety**. If notifications stay off: **🔔 Turn notifications back on now**.

> Example: start a routine and move the mouse during it — the routine stops and asks whether to continue.

## 5. Studio RPR: the basic idea

- A **routine** is a tree of steps: actions (click, type, read), conditions (If), loops, Excel, questions.
- Steps work on **objects** (buttons, fields, tables) marked once with **Spy**, not on coordinates. Each object has several backup **locators**: if one stops working, the next is tried.
- **Variables** are written in braces: `{Client}`, `{Rand.IBase}`, `{Azi}`.
- The Studio screen: left **🧱 Steps** (blocks) and **📚 Library** (objects); middle the routine tree; right the properties of the selected step; bottom **Log** and **Variables**.
- Click a block = add it after the selected step. To put it **inside** an "If" or a loop, first select the branch (e.g. ▸ Then).

> Example: open 📚 Examples → "01 Invatare" and press ⏭ Step by step several times, following each block.

## 6. Your first Web routine (step by step)

[video:02_studio_web]

1. Studio → **📄 New**.
2. Block **🌐 Open browser**, address `https://the-internet.herokuapp.com/login`.
3. **🎯 Web** (Spy): move the mouse over the Username field (green outline) and **click**. In the "Captured object" window press **+ Type text step**. Enter the value `tomsmith`.
4. Do the same for Password (`SuperSecretPassword!`) and the Login button (**Save + Click step**).
5. Spy the message shown after login → **+ Read step**; in the step set the **Expected value** `You logged into*`.
6. **💾 Save**, then **▶ Run**.

> Tip: **⏺ Record Web** does steps 3–4 automatically: work normally in the browser and every click / text / option becomes a step. Esc in the browser or ⏺ again = stop.

## 7. Spy Web and Record Web

- **🎯 Web**: if the browser is not open, Studio asks for the address. Mouse over the element → green outline → **click** = capture; **Esc** = cancel.
- In "Captured object": the name (how you pick it in steps), type, site, page, container and the locators with a score (green 70+ stable, yellow acceptable, red fragile). Uncheck unstable locators (e.g. a text that changes).
- If the element is already in the library, Studio offers to use the existing one.
- The browser (Edge or Chrome) is chosen in **🌐 Studio settings**. The profile (login, cookies) is kept between runs.
- iframes, new tabs and JavaScript popups are handled automatically.

> Example: on a page with a search, Spy the field → "+ Type text step" with `{Termen}`, then Spy the Search button → "Save + Click step".

## 8. SAP GUI

[video:05_studio_sap]

1. Enable scripting: SAP GUI → Options → Accessibility & Scripting → Scripting → **Enable scripting** (uncheck the warnings). On the server, `sapgui/user_scripting` must be TRUE.
2. Open SAP Logon and log in.
3. First step of the routine: **🟦 SAP: connect** (empty = first session).
4. **🟦 SAP: transaction** with `/nVA03` (closes the current transaction and starts VA03).
5. **🎯 SAP**: mouse over the field (red outline) and **F2**. If the position cannot be determined, click into the field and press F2.
6. **🟦 SAP: key** (Enter, F3, F8, Shift+F4, Ctrl+S) and **🟦 SAP: status bar** (`S:` success, `E:` error, `W:` warning).
7. Tables: **SAP: read table cell** with `row|column` (e.g. `0|MATNR`); the table scrolls to the row by itself.

> Example: routine 04 "SAP VA03" reads the order numbers from Excel and writes the status into the Status column.

## 9. Windows desktop applications

[video:04_studio_desktop]

1. **🖥 Start application** (`notepad.exe` or `"C:\Program Files\App\app.exe" /param`) or **🖥 Attach window** (`proces:notepad.exe` or the window title).
2. **🎯 Desktop**: mouse over the element (green outline) and **F2**; Esc = cancel.
3. Use the object in steps: Click, Type text, Read, Choose from list, Check.
- Before every click the application window is brought to the front and the element is scrolled into view. If the point were covered by another window, the click is done without the mouse (UI Automation) or the step stops with a message — never in another window.
- **Lists (conversations, e-mails)**: Spy captures the whole row. Names with changing text get a pattern, e.g. `ListItem|Ion Popescu*` (`*` = any text).
- **Direct mode** (in the step): actions without moving the mouse, where the application allows it.

> Example: routine 05 "Desktop Notepad" starts Notepad and types three lines in a loop.

## 10. The object library

[video:06_biblioteca]

- The **📚 Library** tab shows all objects, shared by all routines: **Site → Page → Container → object**. Site and page are filled in from the link where you captured the object.
- **Test**: before using an object in a new routine, see how many elements each locator finds (1 = good, several = ambiguous, 0 = not found); the object is highlighted on screen. From the result you add it directly as a step.
- **Containers** (section, table, RefList, form): their objects are searched only inside them. The same "Save" button in two sections is no longer confused. With Spy, the container is suggested automatically.
- **🌐 Sites**: one site with several links (test, production, another customer) — its objects work on all of them. **Copy for another site** duplicates an object for another system.
- Right-click an object: test, add a step, move into a container, copy, delete. The search filters by name, type, site or tag.

> Example: Spy the "Delivery" section → type "Container / section"; then Spy its Save button → it is placed in the Delivery container automatically.

## 11. Steps (actions)

- **On an object**: Click, Double click, Right click, Hover, Type text (replace), Type text (append), Clear the field, Press key, Choose from list, Check / Uncheck, Read the text / value / attribute, Highlight, Element screenshot.
- **Browser**: Open browser, Go to URL, Back, Reload, Switch tab, Answer a JS popup, Page screenshot, Close browser.
- **SAP**: Connect, Transaction, Send key, Status bar, Read cell, Row count.
- **Desktop**: Start application, Attach window, Close window.
- In every step: **Wait for the object at most (ms)**, **On error**, **Wait before / after**, **Comment**, **Step active**.
- **▶ Test the step** executes only the selected step, with the variables of the last run.

> Example: "Read the text" on the confirmation message, saved in the variable `Mesaj`, then "Log" with `Received: {Mesaj}`.

## 12. Conditions, loops and waits

- **🔀 If / Else**: the "Then" branch runs when the condition is true, "Else" when it is false. Conditions: the object exists / does not exist / is visible / is enabled, the object's text, compare two values, all (AND) / any (OR), NOT.
- **🔁 Repeat**: N times, while or until a condition is true; the variable `{Repetare}` = 1, 2, 3...
- **⏱ Wait**: a number of seconds or until something appears / disappears (with a maximum time).
- **🛡 Try / On error**: if a step in "Try" fails, the routine does not stop but runs "On error"; the message is in a variable.
- **⏏ Exit the loop** and **⛔ Stop the routine** (with or without an error).

> Example: If "The object exists: Button_Accept_Cookies" → Then: click it. Else: nothing.

## 13. Variables

- Use them anywhere in braces: `{Client}`. Define them in **⚙ Routine settings** (start values) or let steps create them (Read → "Save the result in the variable").
- **✎ Variable**: set, append, increase / decrease, UPPER / lower case, replace text, trim spaces.
- Special: `{Azi}` (today), `{Acum}` (now), `{Acum:yyyyMMdd_HHmm}`, `{NewLine}`.
- From Excel: `{Rand.ColumnTitle}`, `{Rand.A}` (by letter), `{Rand.#}` (row number).
- The **🔤 Variables** tab at the bottom shows the values after the last run.

> Example: Type text `Report_{Acum:yyyyMMdd}` into the file name field.

## 14. Excel: one routine for every row

[video:03_studio_excel]

1. Block **📊 For each Excel row**: choose the file, the sheet, the title row, the first / last row and the key column (empty row = end of the list).
2. Put the steps **inside** the block; use `{Rand.ColumnName}`.
3. **📝 Write to Excel** (inside the loop) writes a result into the current row (the column is created if missing) and can color the cell.
4. The **status column** receives OK / the error and rows are colored green / red. With "Save after every row" and "skip rows already OK" you can resume an interrupted run.
- Formulas in the file stay intact.

> Example: a file with the column `IBase`; in the loop: Type text `{Rand.IBase}` into the search field, Click Search, Read the status → Write to Excel in the column `Result`.

## 15. Questions, errors and the expected value

- **💬 Question**: a window with buttons you choose (e.g. `Yes, No, Skip`); the answer goes into a variable. You can set the button that stops the routine or skips the Excel row.
- **On error** (per step or per routine): Ask me (Retry / Skip / Stop), Stop, Continue (only log), Skip to the next Excel row.
- **Automatic retries** and **screenshot on error** are set in ⚙ Routine settings.
- **Expected value** (on Read steps): if the text read differs, the routine stops and asks you. Variables and `*` are accepted (e.g. `S:*` = any SAP success message).

> Example: Read the SAP status bar with the expected value `S:*` — on any SAP error the routine stops and shows you the message.

## 16. Running and control

- **▶ Run** starts the routine; the application minimizes (optional) and a small control bar remains.
- **⏭ Step by step**: each press executes a single step — ideal for checking.
- **Pause / Resume**: Ctrl+F11. **Stop**: Ctrl+F12.
- **📋 Run log**: every step with time, result and duration; errors are red. **📤 Export Excel** saves the log; **📂 Results** opens the folder with screenshots and logs.
- Run without the interface: `py -m rpr run "C:\path\routine.rpr.json" --var Client=John`.

> Example: run a new routine first with ⏭ Step by step and "Highlight the object before every action".

## 17. Scheduling

[video:07_programare]

1. Save the routine and press **🕒 Schedule**.
2. Choose **when**: daily, on working days, on certain days, once, every N minutes or at Windows logon; then the time (and date).
3. **✔ Create the schedule**: it appears in Windows Task Scheduler in the `AutoPilotDC` folder (no administrator rights). The same name replaces the schedule.
4. The **AutoPilot schedules** list: next / last run and result; **▶ Run now**, **🗑 Delete**. The **History** tab: every scheduled run (double-click = log).
- At the end a message appears in the corner of the screen (green / red). The computer must be on and you must be logged in.

> Example: "Daily report", On working days, at 07:30.

## 18. Settings

- **⚙ Settings** (application): playback delay and speed, countdown, recording mouse movements, run safety, shortcuts, **start with Windows** (optionally straight into the tray), the ✕ button hides into the tray, desktop shortcut, **language** (Română / English / Deutsch) and theme. Language and theme apply after a restart.
- **🌐 Studio settings**: the browser for Web steps (Edge recommended, Chrome), without a window (only for schedules), minimize when running, close the browser, delete the browser profile (logout).
- **⚙ Routine settings**: error policy, highlighting objects, default timeout, pause between steps, retries, screenshots, do not disturb, prevention, variables.

> Example: Settings → Language → Deutsch → Save settings → the application restarts in German.

## 19. Common problems

- **Packages missing at start**: press "Install now" or run INSTALEAZA.bat.
- **Edge does not start ("Target page… has been closed")**: close the Edge windows left by AutoPilot; the application retries and, if needed, starts with a temporary profile. Or choose Chrome in 🌐 Studio settings.
- **The object is not found**: press **Test** in the Library; if a locator gives 0, edit it or capture it again with Spy. Check the site / page and the container.
- **The click goes to another window (Desktop)**: the application must be open; use "Direct mode" for buttons and list rows.
- **The Excel file is locked**: close it in Excel before running.
- **SAP does not respond**: check scripting (chapter 8).
- **The tray icon is missing**: Settings → Startup and tray shows the status; on Windows 10/11 it may be hidden under the ^ arrow.
- **Notifications stay off**: Settings → 🔔 Turn notifications back on now.
- **"Do not disturb" does not turn on or off**: Settings → 🔍 Check Do not disturb (with a "real test" if you want). The report shows the Windows version, the setting found and whether Windows allows restarting the notification service; it is also saved in `loguri\nu_deranja_diagnostic.txt`.

## 20. Files, folders and colleagues

- The application: the `AutoPilotDC_py` folder (copy it or get it with `git pull`). Recorder routines: `rutine_salvate`, logs: `loguri`.
- Studio: `%APPDATA%\AutoPilotDC\Studio` — `rutine` (routines), `rezultate` (logs, screenshots), `obiecte.json` (the library), `exemple`, `browser-profil`.
- For a colleague: send the `.rpr.json` file and `obiecte.json`; the colleague runs INSTALEAZA.bat once.
- The application version is shown in the bottom bar; what's new is in `CHANGELOG.md`.

## 21. Video: screen recording

[video:08_video]

- **🎥** (top bar or tray menu) starts a recording at any time, without a routine — for example to show a colleague a procedure. Press 🎥 again or **⏹ Stop** in the small ● REC bar (which does not appear in the video). **⏸** pauses the video.
- When it stops, the **editor** opens: chapters (routine steps, Excel rows), **A ▸ / ◂ B** for a selection, **✂ Cut A–B**, **💬 Text A–B** (a caption on screen), **▦ Hide area** (blur over personal data), **⟦ Start / End ⟧**, **shortening long pauses**. The original video stays unchanged; **💾 Save** keeps the edits, **GIF** / **MP4** export.
- **⚙ Settings → 🎥 Video**: the video folder, **automatic video on every run** (Studio and Recorder), **one video per Excel row**, also for scheduled runs, captures per second, size and quality.
- Videos are made of **screenshots saved only when the screen changes** (small `.apvid` files). The cursor and clicks are drawn during playback. **🎬** in the top bar opens a saved video.
- MP4 needs the `opencv-python` package (optional); GIF always works.
- In the Excel loop, with video on, every row gets the link to the video and the minute where the row starts in the **Film** column (change or turn off the column in the loop's properties). The same link appears in the run report. Double-clicking an `.apvid` file (or clicking the link in Excel) opens it in the player without starting the app.

> Example: Settings → Video → check "video on every run" and "one video per Excel row"; run routine 03 — the folder gets one video per row, with chapters for every step.

## 22. The run's Excel report (proof of work)

1. **⚙ Routine settings → 📊 Excel report of the run**: tick "Create an Excel report on every run".
2. Tick the **value columns** (variables, columns of the input Excel, values read). You can do the same directly on a step: **📊 Put the value in the run's Excel report** (on steps that save a value and on "Set variable").
3. Choose the folder (empty = `rezultate\rapoarte`) and what goes into the report: the "Steps taken" column, the "Steps" sheet (every step with time, result and rule), the routine definition.
4. Run. At the end the log shows `📊 Report: ...`.
- One row for each Excel row or top-level repetition; without loops, one row for the whole routine. Works without an input Excel too.
- Every row has the start time, duration, status, message, ticked values, the video (with the time in the video) and the error screenshot. The video appears when it is on in ⚙ Settings → Video.
- The input Excel still gets the status and whatever you write with **📝 Write to Excel**.

> Example: a list of unique numbers. In the loop: if `{Rand.Data}` is empty, read the date from the link, format it and type it; otherwise press button Y. Tick `Rand.Nr`, `DataCitita` and `Actiune` for the report. The report shows, for every number, what was done, when, and where in the video.

## 23. Routine manager and preparations

1. **📂 Routine manager** (Studio bar): the routines in the chosen folder, read when the app starts. **Change folder** picks another folder (e.g. a Drive folder).
2. From the list: **Open in Studio**, **▶ Run** or **➕ Add to preparation**.
3. A **preparation** is a list of routines run one after another: order with ▲ ▼, "Run / Skip" and what happens on error (stop, or continue with the next one).
4. Tick **🎥 Video for each routine** and **📊 Excel report for each routine**, then **💾 Save** (the file `Name.pregatire.json` in the routines folder).
5. **▶ Run preparation**. Pause / STOP from the floating bar (Ctrl+F11 / Ctrl+F12); the questions and the prevention system stay active.
- At the end: a folder `rezultate\pregatiri\Name_date_time` with `Pregatire_Name.xlsx` (summary and definitions), `Documentatie.html` (everything that was done, in detail), the reports and links to the videos.
- A preparation can be scheduled like a routine: `py -m rpr run "Sandbox.pregatire.json"`.

> Example: a test sandbox with `01_Users`, `02_Roles`, `03_Objects`. You run the preparation in the evening; in the morning you open the documentation and see for every routine how long it took, what it created and its video.

## 24. Backup and restore

1. **⚙ Settings → 💾 Backup and restore → Create backup...**: choose where the `.zip` file is saved (e.g. a USB stick or a Drive folder).
2. Tick "Include the results too" only if you also want the reports, Studio logs and error screenshots (the file gets bigger).
3. On another PC or after a reinstall: **♻ Restore from backup...**, choose the file, confirm, then restart AutoPilot DC.
- Included: the settings, Recorder and Studio routines, the object library with its images, the schedules, the notes, the language, the video settings and the routines folder from 📂 Manager.
- Not included: the browser profile (logins) and the videos.
- Before restoring, the current state is saved automatically in `%APPDATA%\AutoPilotDC\backup-automat`. If the routines folder does not exist on the new PC, the routines go to `Studio\rutine\biblioteca` and the Manager points there.

> Example: before changing laptops you create a backup in Drive; on the new laptop you install with INSTALEAZA.bat, restore the backup and have the same routines, objects and settings.
