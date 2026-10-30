# AutoPilot DC instructions

Each chapter briefly explains one procedure, step by step, with an example. Pick a chapter on the left or search for a word.

> Variable names such as `{Azi}` (today), `{Acum}` (now), `{Rand.…}` (Excel row) and `{Repetare}` (loop counter) are the same in every language, so routines work for all colleagues.

## 1. Starting and the interface

- Start the application with **AutoPilot_DC.pyw** in the `AutoPilotDC_py` folder or with the "AutoPilot DC" desktop shortcut (no CMD window).
- The first time (or on a new laptop) run **INSTALEAZA.bat**: it installs everything needed, without administrator rights. The window stays open until you press a key.
- The application has one work area, **🧩 Studio RPR**. The former Recorder is now inside Studio (the **⏺ Screen** button, chapter 2).
- The top bar is a single row: the Studio commands (routine, run, Spy and recording) in the middle; when the window is narrow only the icons remain (the full text is in the tooltip). On the right, small buttons: **🎥** records the screen, **🎬** opens a video, **📖 Instructions** (here, or F1), **⚙ Settings** of the application, **✕**.
- **🚨 EMERGENCY STOP** (or F12) stops any run and recording immediately.
- Tray icon next to the clock: click = open the application; right-click = Studio, ⏺ Screen, video, EMERGENCY STOP, Exit.

> Example: open the application, press **⋯ → 📚 Examples** and open "01 Learning".

## 2. ⏺ Screen: recording mouse and keyboard (the former Recorder)

1. In Studio select the step after which the new steps should go (or nothing: they are added at the end).
2. Press **⏺ Screen** (F5). The AutoPilot window is minimized, the green **REC** border appears and a small bar at the top shows the number of steps and **⏹ Stop (F6)**.
3. Work normally in any application: clicks, scrolling, keys. Letters typed one after another become a single "Type" step. Clicks on AutoPilot itself are not recorded.
4. Press **F6** or **⏹ Stop**. The steps go into the routine in a group "Screen recording HH:MM", as 🖱 screen steps.
5. Run with **▶ Run** (F7). **Pause** = F8, **Stop** = F9, **EMERGENCY STOP** = F12. For repetitions put the group inside a **🔁 Repeat** block; for values from Excel, inside a **📊 For each row** (and change the text of the "Type" step to `{Rand.Column}`).
6. The prevention system also checks screen steps: if during the run the click would land in another application or the area looks different, the routine stops and asks you.

> Example: select the last step, press ⏺ Screen, open Notepad, type "Test", press F6. The routine gets the group with the clicks and the step Type "Test".

> Attention: screen steps work on coordinates. If the window moves or the resolution changes, the click lands somewhere else. Where possible, use object steps (🎯 Spy, ⏺ Web).

## 3. Screen steps: editing and what moved from the Recorder

- A 🖱 screen step is edited on the right like any step: **X / Y**, keys, text, wait before / after, comment. The title shows what it does and in which window ("Click (420, 310) · Notepad").
- The recorded group can be renamed, disabled, moved with the mouse or duplicated; its steps can be moved, deleted or disabled one by one.
- What was in the Recorder tabs is now in Studio: **Step Builder** → the blocks in 🧱 Steps; **Routines** → 📋 Routines and 🗂 Routine manager; **Excel** → 📊 For each Excel row; **Log** → ⏱ Timeline and Run log (with Excel export); **Settings** → the ⚙ button at the top right; **Help** → 📖 Instructions. Repetitions → the 🔁 Repeat block; pause between steps → ⚙ Routine.
- Old Recorder routines (`rutine_salvate\*.json`) open with **📂 Open**: they are converted automatically into screen steps; the old file stays unchanged.
- **Notes** no longer have a tab: use the **Comment / note** field of the steps and the routine description.

> Example: 📂 Open → `rutine_salvate\Report.json` → the routine appears in Studio with its 🖱 steps; save it (💾) as `.rpr.json`.

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

- **⚙ Settings** (application, the small button at the top right): screen recording (mouse movements), run safety, shortcuts, **start with Windows** (optionally straight into the tray), the ✕ button hides into the tray, desktop shortcut, theme, video, **language** (Română / English / Deutsch), backup. Language and theme apply after a restart.
- **One language** for the whole application (⚙ Settings → 🌐 Language): besides the interface, the logs, the status column in the routine's Excel (OK / ERROR / IN PROGRESS), the run report and the preparation summary and documentation are written in the same language. When resuming, statuses are recognised in any language (e.g. "IN LUCRU" = "IN PROGRESS"), so an Excel started in Romanian can be resumed after switching to English.
- **🌐 Studio settings**: the browser for Web steps (Edge recommended, Chrome), without a window (only for schedules), minimize when running, close the browser, delete the browser profile (logout); plus the text size, where files are saved and the application for videos (chapter 31).
- **⚙ Routine**: error policy, highlighting objects, default timeout, pause between steps, retries, screenshots, do not disturb, prevention, variables.

> Example: ⚙ Settings → Language → Deutsch → Save settings → the application restarts in German.

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
- **⚙ Settings → 🎥 Video**: the video folder, **automatic video on every run** (Studio), **one video per Excel row**, also for scheduled runs, captures per second, size and quality.
- Videos are made of **screenshots saved only when the screen changes** (small `.apvid` files). The cursor and clicks are drawn during playback. **🎬** in the top bar opens a saved video.
- **Intro and outro** (on by default): a run's video starts with a screen showing the routine name and start time (3 s) and ends with a screen showing the result (✅ / ❌ and the error message), duration, steps and Excel rows (4 s). What was recorded stays in between. After the last step the video keeps going for **2 s** to catch its result, and the last screen is saved when it stops; the end is no longer shortened by "shorten pauses". Durations and turning them off: ⚙ Settings → 🎥 Video.
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
- **Saved as it goes, and cloud**: the report is saved after every row / repetition (at most once every few seconds), so it survives if the app freezes. The report folder and the videos folder (⚙ Routine settings → 🎥 Routine videos) can be chosen per routine; **☁ OneDrive** puts the folder in the synced OneDrive, so the files reach the cloud by themselves. A video interrupted abruptly is rebuilt automatically when opened, from the frames already saved.

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

## 25. Resume after an unexpected close

1. While a routine works on an Excel row, the status column shows "IN LUCRU" (in progress, orange); at the end it becomes OK or EROARE.
2. If AutoPilot DC or the PC closes in the middle of a run, the next start shows the question **Resume after closing**: **Resume the run**, **Just open it** or **No, discard**.
3. When resuming, rows with OK are skipped. For the row left "IN LUCRU" you choose: **Redo the row**, **It is done, mark OK** (if you checked in the system) or **Stop the routine**.
- In a preparation the routines already finished are skipped too; the interrupted routine continues from its row.
- The same question appears when you start the routine again by hand and a row was left "IN LUCRU" (e.g. after STOP).
- Step-by-step runs are not resumed. If you close the application yourself during a run, no resume is offered.

> Example: the routine creates 200 users and the power goes off at row 120. On restart you choose "Resume the run"; rows 2–119 are skipped, you check the user from row 120 in the system and choose "It is done, mark OK" or "Redo the row".

## 26. Scanning a site and one library per application

1. 📚 Library → **＋ New**: type the application name; AutoPilot suggests `OneDrive\AutoPilotDC\obiecte\<Application>\obiecte.json` (without OneDrive: in Documents). You can pick any other folder.
2. **🔍 Scan site**: type the address and the AutoPilot browser opens. Sign in and open the page you want, then choose **🔍 Scan automatically**.
3. You get the list of visible buttons, fields, lists, checkboxes and links (also inside iframes, up to 500). Click a row to **mark it in the browser** (so you see which button it is); the tick in the first column keeps or drops it (or Space / **☑ Keep / remove**). **✎ Rename** (F2, double-click on the name) changes the name. At the top choose the **Page** and **Folder** they go under (see chapter 28). **No links** removes navigation menus. **💾 Add to library** saves them.
4. Open another menu or tab in the browser and choose **🔍 Scan again**. Objects already in the library are skipped.
5. **🖐 3 s capture**: hold the cursor 3 seconds on a field or button (blue outline, countdown) and it is saved by itself; then move to the next one. Clicks work normally, so you can open menus. Esc in the browser or **Done** stops it.
- The scan only reads the page already loaded: it does not click, type or send anything to the server, so it does not load the application. Hidden elements (closed menus, other tabs) are not seen until you open them.
- **📂 Open** switches the library. A saved routine remembers its library and loads it by itself when opened; the application only remembers the path of the last library.
- If OneDrive has a different path on the other laptop, the library is found at the same place in that PC's OneDrive.

> Example: for the orders application you create the "Orders" library in OneDrive, scan the search page and the order form, then use the 3 s capture to add the button from the menu that only appears on hover. New routines for this application use the "Orders" library.

## 27. Check saved buttons (simulation without clicking)

1. Open the application page in the AutoPilot browser (sign in, open the menu / tab with the buttons).
2. 📚 Library → **🩺 Check** (or, after 🔍 Scan site, choose **🩺 Check saved buttons**). If the site has objects on other pages too, choose **Current page** or **Whole site**.
3. For each object, AutoPilot makes a "trial click": the same checks as a real click (found, visible, enabled, not moving, not covered by another window), but it **does not press** and sends nothing to the server.
4. You get the list: **✅** works · **⚠** works, but with obstacles (covered by an overlay, disabled, found several times, only the fallback locator works, different text) · **❌** must be recaptured · **·** on another page. Click a row to see the reasons.
5. **👁 Show in browser** marks the element. **🔧 Repair locators** puts the working locator first. **🎯 Recapture**: click the element in the browser; the name stays, so routines that use it keep working. **🔄 Check again** after you changed something in the browser.
- The trial click may scroll the page to the element, but it presses nothing. A button that appears only after an action (menu, tab, filter) is checked after you open it.
- For a ⚠ "Covered" element, usually a window or message sits on top of it: close it and check again. If it stays, the routine needs a step before (close the message).

> Example: after an application update you open the orders page and press 🩺 Check. "Save" is ✅, "Send" is ⚠ disabled (normal until you fill in the form) and "Export" is ❌: you recapture it with one click and the export routine works again.

## 28. Folders in the library (sections under the same page)

Some web applications change their "folders" (menu, tree on the left) without changing the address: always `…/otwg20`. So that not all buttons sit together, you put each object in a **named folder**:

1. At **🔍 Scan site**, in the results window choose the **Page** and the **Folder** at the top (e.g. `Orders/Export`; `/` makes subfolders). Folders already used appear in the list. The last chosen folder is also used by **🖐 3 s capture**.
2. In the library the tree becomes **Site · Page · 📁 Folder · button**.
3. For an existing object: right-click → **📁 Move to folder...** or the **Folder** field in **Edit**.
4. Right-click a folder: **✎ Rename the folder...** (also renames its subfolders) and **🩺 Check the folder's objects**.
- **Rename page / site**: right-click a 📄 page (or 🌐 site) → **✎ Rename the page...**; it changes for all objects under it. If the new name already exists, the pages merge.
- A folder only groups. It does not change where the element is searched on the page (that is what a **Container** does). Routines do not change: steps still use the object name.
- Windows (object, scan, check, schedule) scroll with the mouse wheel and the **Save / Add / Close** buttons stay fixed at the bottom, so you no longer need to enlarge them.

> Example: in the orders application, the folder `Orders/Import` has the buttons "Upload file" and "Validate", and `Orders/Export` has "Export Excel". You open the folder in the application, scan, choose the folder and the buttons land in place.

## 29. Saved routines as a step (📋 Routines tab)

You already have a routine of 2–3 steps (e.g. the login) and want to use it in others without rebuilding the steps:

1. In **Studio RPR**, next to **📚 Library**, open the **📋 Routines** tab: it lists the routines in your folder (the same as in **📂 Routine manager**; **📁 Folder** changes it, **↻** reads again, the box at the top searches).
2. Pick a routine and press **➕ As step** (or double-click): the **📋 Run routine** step is added and it **follows the file**. Change the routine once and it works everywhere it is used.
3. Put your own steps before and after. Run routine uses **the same variables, the same Excel and the same object library**; the main routine's settings (errors, pauses) apply to it too. Default values of the called routine's variables are used only if they do not exist yet.
4. **📥 As steps** copies the steps into the current routine (you can edit them; they no longer follow the original). On an existing step, **📥 Replace with its steps** makes the same copy.
- Before the start the file, loops (A calls B, B calls A), depth (maximum 8) and missing objects are checked; if something is wrong the routine does not start and you are told which step. In the log the block's steps appear with its name in front.
- If you move the routine file, the step has to point to it again (the file field of the step).

> Example: `Login SAP` (2 steps) is saved in the routines folder. In the report routine: ➕ As step "Login SAP", then the report steps.

## 30. "If it appears" and rules for messages / errors

Sometimes messages or errors show up that you know about in advance (e.g. "Are you sure you want to close?"). They should not get in the way when they do not appear.

**👁 If it appears (optional)** (Flow): put the step where the message may appear, choose the element (in **Condition**, with **Wait for the object at most** e.g. 1500 ms) and the steps to do in the "Atunci" branch. If the message does not appear, the routine carries on without an error.

**🧯 Rule for message / error** (Flow): place it **before** the steps it covers (first step = whole routine). It does nothing by itself: it is armed and stays active until the end of the list it sits in (inside a Group, only in that Group). When a step **fails** and the rule matches, the steps in "Pasi de rulat" run:
1. **If the error contains the text**: part of the error message (case-insensitive) and / or
2. **OR an element / condition is true on screen** (e.g. the message window is open);
3. **After the rule's steps have run**: *retry the step* (default; at most 3 times), *treat the step as solved* or *the error goes on*.
- The error message is in the variable `{EroareRegula}`. With several rules, the one closest to the step is checked first.
- Rules are checked only when a step fails; if the message does not come, nothing happens. The rule's own steps do not trigger other rules.
- Browser: alert / confirm dialogs of the page are accepted automatically (the "Handle dialog" step chooses "dismiss"). A message inside the application page is an element: handle it with **If it appears** or a rule.
- For messages choose the condition **The object is visible** (a hidden message "exists" in the page but cannot be seen).
- **Demo**: the **Examples** button → **06 Demo - Daca apare si reguli la mesaj** (a local page, no internet): press "Porneste", "Are you sure?" appears, the rule closes it by itself, and "If it appears" carries on when the message is missing. Run it with **⏭ Step by step** to see every step.

> Example: at the start of the routine, a **🧯 Rule** with "Sure" and the step Click on "Yes, close", then *retry the step*; if the message does not appear, the routine runs as before.

## 31. Appearance, drag and drop and where files are saved

**🌐 Studio settings** now has four tabs: 🌐 Browser, 🎨 Appearance, 📁 Where files are saved, 🎬 Videos.

- **🎨 Appearance → Text size**: Small / Normal / Large / Very large, for the whole application (applied after a restart). The width of the Studio panels is remembered as a percentage of the window, so it looks the same on a laptop and on a monitor; **↺ Reset panels** restores the initial layout.
- On small screens the top bar stays on one row: buttons lose part of their text (the full text is in the tooltip), and rarely used commands (Save as…, Examples, Schedule, Guide) are under **⋯**.
- **Drag and drop**: drag a step in the tree to another place (a line shows where it lands; over "▸ Then" / "▸ Else" or over the middle of a loop it goes inside). The same way you drag a block from 🧱 Steps, an object from 📚 Library (choose Click / Type text / Read / If it exists) or a routine from 📋 Routines (it becomes a "Run routine" step).
- **📁 Where files are saved**: choose a **common folder** (e.g. ☁ OneDrive); routines, object libraries, results (screenshots, logs, reports) and videos go to the subfolders `rutine`, `obiecte`, `rezultate`, `filme`. A field filled in for one kind of file takes priority; what you set on a routine (folder of videos / report) or on a library takes priority over everything. Empty fields = as before.
- **🎬 Videos → Open videos with**: the AutoPilot player (playback + editing), the default Windows application or another application on the laptop (e.g. VLC). For other applications the video is exported once to MP4, next to it (GIF if opencv-python is missing). The same choice is in ⚙ Settings → Video.

> Example: 🌐 Studio settings → 📁 Where files are saved → ☁ OneDrive → Save; a new routine saved with 💾 suggests the folder `OneDrive\AutoPilotDC\rutine`, and videos go to `OneDrive\AutoPilotDC\filme`.

## 32. Activity bar, tabs, timeline, the Excel screen and the flow

Studio has an **activity bar** on the left: 🧱 Steps, 📚 Library, 📋 Routines, 🎬 Videos, and at the bottom 🌐 Settings and ❓ Guide. Each icon only changes the panel next to it; the routine stays where it is. Clicking the icon that is already selected **collapses the panel** (more room for the routine on a laptop); another click opens it again. The app remembers the chosen panel.

- **Tabs for routines**: every open routine has its own tab above the steps (● = unsaved changes). **+** or 📄 New opens a new routine in a new tab; × closes the tab (it asks whether to save). A routine that is already open is not opened twice: its tab is shown. While a routine runs you cannot switch tabs.
- **The center view**: **✎ Steps** (the list, for editing), **🔀 Flow** (the routine as a flow of cards, with "Then" and "Else" side by side; read only: clicking a card shows the step's properties on the right, double-click takes you to the step in the list) and **📊 Excel**.
- **📊 Excel**: the rows of the file from the first "For each Excel row" step, with their status and the minute in the video. When you run a routine with Excel, this screen opens by itself and shows the row being worked on. Pick a row: on the right you see its steps, the error and its screenshot; **↻ Rerun row** runs only that row again (plus the steps before the loop, e.g. opening the browser), **🎬 See in video** opens the run's video at the row's minute (if recording during runs is on in Settings → Video).
- **⏱ Timeline** (at the bottom, next to Log): one card for every finished step, with ✓ / ✕, the Excel row, the duration and, for errors, the message and the screenshot (double-click the screenshot to open it large). Clicking a card shows the step in the routine.
- **🎬 Videos**: the saved videos, newest first; double-click opens them with the app chosen in 🌐 Studio settings → 🎬 Videos.

> Example: open **Examples → 03 Web + Excel** and press ▶ Run. The center switches to 📊 Excel and colors every row (green OK, red error). Pick a red row, read the error on the right and press ↻ Rerun row.

## 33. 📥 AI import: a routine from a Word document

You have the procedure in a Word document. An AI (ChatGPT, Copilot, Claude...) turns it into **AutoPilot steps**, plain text with one step per line, and Studio builds the routine from it.

1. In Studio press **📥 AI import** (left bar or **⋯ → 📥 Import steps**).
2. **📋 Copy the prompt for the AI** and paste it into the AI; then paste the text of the procedure (or attach the Word document). The prompt explains the format and the rules, in the application language (**💾 Save the prompt** keeps it as a file).
3. Paste the AI's answer into the import window (or **📂 Open file**: `.txt`, `.json`, `.rpr.json`). It is checked automatically: on the right you see the steps, below the problems; wrong lines are coloured (click a problem = its line).
4. **✅ Create the routine**: it opens in a new tab (unsaved). New buttons and fields go into the 📚 Library, found by the text on screen.
5. Check the new objects with **🧪 Test** on the real page (or mark them again with 🎯 Spy), fill in the variables in ⚙ Routine, run **⏭ Step by step**, then save (💾). Automatic scheduling: 🕒 Schedule.

The format (keywords in English or Romanian, upper or lower case):

- Header: `ROUTINE: <name>`, `DESCRIPTION: <text>`, `VARIABLE: Name = value`.
- Steps: `OPEN BROWSER <url>`, `GO TO <url>`, `CLICK <object>`, `TYPE <object> = <text>`, `SELECT <object> = <option>`, `CHECK <object>`, `PRESS Enter`, `READ <object> -> {Var}`, `WAIT 2` or `WAIT <object> MAX 15`, `LOG "text"`, `ASK "text"`, `MANUAL "what the person does"`, `SAP TRANSACTION /nVA03`, `START APP notepad.exe`.
- Blocks: `IF <condition>` … `ELSE` … `END`, `REPEAT 3` … `END`, `FOR EACH ROW {File} SHEET Data` … `END` (values: `{Rand.Column}`, writing: `WRITE EXCEL Result = OK`), `TRY` … `ON ERROR` … `END`.
- Objects: `button "Save"`, `field "User"`, `link "..."`, `list "Country"`, `checkbox "..."`, `text "..."`, `css "#id"`, `sap "wnd[0]/usr/..."`, `desktop "Name"` or `[Name]` from the library.
- Conditions: `{Var} = "x"`, `{Var} contains "x"`, `visible button "OK"`, `exists [Name]`, combined with `AND` / `OR`.
- A complete `.rpr.json` routine is accepted too. What cannot be automated becomes `MANUAL`: the routine stops and waits for Continue.

> Example: in the import window press **📝 Example**: an order entry procedure from an Excel appears; on the right you see the routine with the loop and the condition; ✅ Create the routine opens it in Studio.
