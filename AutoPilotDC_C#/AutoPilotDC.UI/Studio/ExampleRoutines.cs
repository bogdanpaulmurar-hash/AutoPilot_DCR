// ============================================================
// AutoPilot DC v4 — Studio RPR
// ExampleRoutines.cs — Rutine exemplu gata de deschis (📚 Exemple)
//
//  01 Invatare      : variabile, bucla, Daca, Intrebare, Incearca — fara aplicatii externe
//  02 Web login     : site public de test (the-internet.herokuapp.com)
//  03 Web + Excel   : cauta fiecare termen din Excel pe Wikipedia, scrie titlul inapoi
//  04 SAP VA03      : sablon — afiseaza comenzi din Excel si scrie mesajul SAP
//  05 Desktop       : Notepad — porneste, ataseaza, scrie linii intr-o bucla
// ============================================================

using System.IO;
using System.Windows;
using System.Windows.Controls;
using ClosedXML.Excel;
using AutoPilotDC.Rpr.Model;
using AutoPilotDC.Rpr.Storage;
using Condition = AutoPilotDC.Rpr.Model.Condition;
using HorizontalAlignment = System.Windows.HorizontalAlignment;
using ListBox = System.Windows.Controls.ListBox;
using Orientation = System.Windows.Controls.Orientation;

namespace AutoPilotDC.UI.Studio;

public sealed record ExampleInfo(string Title, string Description, string Path);

public static class ExampleRoutines
{
    public static string Folder => Directory.CreateDirectory(System.IO.Path.Combine(RprPaths.Root, "exemple")).FullName;

    /// <summary>Creeaza (sau recreeaza) rutinele exemplu si obiectele lor in repository.</summary>
    public static List<ExampleInfo> Install(ObjectRepository repo)
    {
        var list = new List<ExampleInfo>();
        void Save(Routine r, string file, string description)
        {
            var path = System.IO.Path.Combine(Folder, file);
            RoutineStore.Save(r, path);
            list.Add(new ExampleInfo(r.Name, description, path));
        }

        Save(Learning(repo), "01_Invatare_variabile_bucle_conditii.rpr.json",
            "Fara aplicatii externe. Arata variabile, Repeta, Daca/Altfel, Intrebare si Incearca/La eroare. Ideal ca prima rulare.");
        Save(WebLogin(repo), "02_Web_Login_demo.rpr.json",
            "Deschide un site public de test, completeaza user/parola, apasa Login si verifica mesajul. Arata marcarea inainte de actiune.");
        Save(WebExcel(repo), "03_Web_Excel_Wikipedia.rpr.json",
            "Pentru fiecare termen din Excel cauta pe Wikipedia, citeste titlul si il scrie inapoi in Excel (cu status si culori).");
        Save(SapVa03(repo), "04_SAP_VA03_sablon.rpr.json",
            "SABLON SAP: pentru fiecare comanda din Excel deschide VA03 si scrie mesajul din bara de stare. Adapteaza obiectele la sistemul tau cu Spy SAP.");
        Save(DesktopNotepad(repo), "05_Desktop_Notepad.rpr.json",
            "Porneste Notepad, se ataseaza la fereastra si scrie 3 linii folosind o bucla si variabile.");
        return list;
    }

    // ── helper: obiect in repository (nu dubleaza daca exista) ──
    private static string Obj(ObjectRepository repo, string name, UiTechnology tech, string context, string type, params Locator[] locators)
    {
        var existing = repo.Find(name);
        if (existing != null) return existing.Name;
        repo.Objects.Add(new UiObject
        {
            Name = name,
            Technology = tech,
            Context = context,
            ElementType = type,
            Locators = locators.ToList(),
            Description = "Obiect din rutinele exemplu",
        });
        return name;
    }

    // ─────────────────────────────────────────────────────────
    // 01 — Invatare
    // ─────────────────────────────────────────────────────────
    private static Routine Learning(ObjectRepository repo)
    {
        var missing = Obj(repo, "Exemplu_Obiect_Inexistent", UiTechnology.Web, "", "button",
            new Locator(LocatorKind.Css, "#acest-element-nu-exista", 50));

        var r = new Routine
        {
            Name = "01 Invatare - variabile, bucle, conditii",
            Description = "Ruleaza cu ⏭ Pas cu pas ca sa vezi fiecare bloc. Nu deschide nicio aplicatie.",
            Variables = { ["Total"] = "0", ["Prag"] = "6" },
        };
        r.Settings.DefaultErrorPolicy = ErrorPolicy.Ask;
        r.Settings.StepDelayMs = 300;

        var loop = new LoopNode { Count = "5", CounterVariable = "Repetare", Comment = "Repeta de 5 ori; {Repetare} = 1..5" };
        loop.Body.Add(new SetVariableNode { Name = "Total", Operation = VariableOperation.Increment, Value = "{Repetare}" });
        loop.Body.Add(new LogNode { Message = "Repetarea {Repetare}: total = {Total}" });

        var check = new IfNode
        {
            Condition = new Condition { Kind = ConditionKind.Compare, Left = "{Total}", Operator = CompareOperator.GreaterOrEqual, Right = "{Prag}" },
            Comment = "Comparatie numerica: 6 >= 6",
        };
        check.Then.Add(new QuestionNode
        {
            Text = "Totalul a ajuns la {Total} (prag {Prag}). Continui bucla?",
            Buttons = "Continua,Iesi din bucla,Opreste",
            OutputVariable = "Raspuns",
            StopButton = "Opreste",
            SkipButton = "",
        });
        var exit = new IfNode { Condition = new Condition { Kind = ConditionKind.Compare, Left = "{Raspuns}", Operator = CompareOperator.Equals, Right = "Iesi din bucla" } };
        exit.Then.Add(new BreakNode());
        check.Then.Add(exit);
        loop.Body.Add(check);

        var attempt = new TryNode { ErrorVariable = "Eroare", Comment = "Pasul din Incearca esueaza intentionat; rutina continua pe ramura La eroare" };
        attempt.Body.Add(new ActionNode { Action = RprAction.ReadText, Target = missing, OutputVariable = "Text", TimeoutMs = 1000 });
        attempt.Catch.Add(new LogNode { Level = RprLogLevel.Warning, Message = "Eroare prinsa (asa trebuie): {Eroare}" });

        r.Steps.Add(new LogNode { Message = "Start: Total = {Total}, azi este {Azi}" });
        r.Steps.Add(loop);
        r.Steps.Add(attempt);
        r.Steps.Add(new QuestionNode { Text = "Gata! Totalul final este {Total}. Deschide tab-ul Variabile ca sa vezi toate valorile.", Buttons = "OK", StopButton = "", SkipButton = "" });
        return r;
    }

    // ─────────────────────────────────────────────────────────
    // 02 — Web: login pe site de test
    // ─────────────────────────────────────────────────────────
    private static Routine WebLogin(ObjectRepository repo)
    {
        const string ctx = "https://the-internet.herokuapp.com/login";
        var user = Obj(repo, "Demo_Camp_Username", UiTechnology.Web, ctx, "input (textbox)",
            new Locator(LocatorKind.Id, "username", 90), new Locator(LocatorKind.Label, "Username", 80), new Locator(LocatorKind.Css, "#username", 45));
        var pass = Obj(repo, "Demo_Camp_Password", UiTechnology.Web, ctx, "input",
            new Locator(LocatorKind.Id, "password", 90), new Locator(LocatorKind.Css, "input[type=\"password\"]", 45));
        var login = Obj(repo, "Demo_Buton_Login", UiTechnology.Web, ctx, "button",
            new Locator(LocatorKind.Role, "button|Login", 85), new Locator(LocatorKind.Css, "button[type=\"submit\"]", 45));
        var flash = Obj(repo, "Demo_Mesaj", UiTechnology.Web, ctx, "div",
            new Locator(LocatorKind.Id, "flash", 90), new Locator(LocatorKind.Css, "#flash", 45));

        var r = new Routine
        {
            Name = "02 Web - Login demo",
            Description = "Site public de test. Schimba {Parola} cu o valoare gresita ca sa vezi ramura Altfel.",
            Variables = { ["Utilizator"] = "tomsmith", ["Parola"] = "SuperSecretPassword!" },
        };
        r.Settings.HighlightBeforeAction = true;
        r.Settings.HighlightMs = 600;

        r.Steps.Add(new ActionNode { Action = RprAction.OpenBrowser, Technology = UiTechnology.Web, Value = ctx });
        r.Steps.Add(new ActionNode { Action = RprAction.TypeText, Target = user, Value = "{Utilizator}" });
        r.Steps.Add(new ActionNode { Action = RprAction.TypeText, Target = pass, Value = "{Parola}" });
        r.Steps.Add(new ActionNode { Action = RprAction.Click, Target = login });
        r.Steps.Add(new WaitNode { Mode = WaitMode.UntilTrue, Condition = new Condition { Kind = ConditionKind.ElementVisible, Target = flash }, TimeoutMs = 15000 });
        r.Steps.Add(new ActionNode { Action = RprAction.ReadText, Target = flash, OutputVariable = "Mesaj" });

        var ok = new IfNode { Condition = new Condition { Kind = ConditionKind.Compare, Left = "{Mesaj}", Operator = CompareOperator.Contains, Right = "logged into" } };
        ok.Then.Add(new LogNode { Message = "✔ Login reusit: {Mesaj}" });
        ok.Else.Add(new QuestionNode { Text = "Login esuat: {Mesaj}", Buttons = "Continua,Opreste", StopButton = "Opreste", SkipButton = "" });
        r.Steps.Add(ok);
        return r;
    }

    // ─────────────────────────────────────────────────────────
    // 03 — Web + Excel
    // ─────────────────────────────────────────────────────────
    private static Routine WebExcel(ObjectRepository repo)
    {
        var excel = System.IO.Path.Combine(Folder, "Exemplu_Termeni.xlsx");
        if (!File.Exists(excel))
        {
            using var wb = new XLWorkbook();
            var ws = wb.AddWorksheet("Termeni");
            ws.Cell(1, 1).Value = "Termen";
            ws.Cell(1, 1).Style.Font.Bold = true;
            string[] terms = { "Robotic process automation", "Siemens", "Playwright (software)", "Selenium (software)", "SAP ERP", "Xyzzy fara rezultat 12345" };
            for (int i = 0; i < terms.Length; i++) ws.Cell(i + 2, 1).Value = terms[i];
            ws.Column(1).Width = 36;
            wb.SaveAs(excel);
        }

        var title = Obj(repo, "Wiki_Titlu", UiTechnology.Web, "https://en.wikipedia.org/wiki", "h1 (heading)",
            new Locator(LocatorKind.Id, "firstHeading", 90), new Locator(LocatorKind.Css, "h1#firstHeading", 45));

        var r = new Routine
        {
            Name = "03 Web + Excel - Wikipedia",
            Description = "Lista de termeni din Excel -> titlul paginii Wikipedia scris inapoi. Inchide fisierul in Excel inainte de rulare.",
            Variables = { ["Fisier"] = excel },
        };
        r.Settings.DefaultErrorPolicy = ErrorPolicy.SkipRow;

        var each = new ForEachRowNode { FilePath = "{Fisier}", Sheet = "Termeni", KeyColumn = "Termen", StatusColumn = "Status" };
        each.Body.Add(new ActionNode { Action = RprAction.Navigate, Technology = UiTechnology.Web, Value = "https://en.wikipedia.org/w/index.php?search={Rand.Termen:url}&go=Go" });
        each.Body.Add(new ActionNode { Action = RprAction.ReadText, Target = title, OutputVariable = "Titlu", TimeoutMs = 15000 });
        each.Body.Add(new WriteExcelNode { Column = "Titlu gasit", Value = "{Titlu}" });

        var notFound = new IfNode { Condition = new Condition { Kind = ConditionKind.Compare, Left = "{Titlu}", Operator = CompareOperator.Contains, Right = "Search results" } };
        notFound.Then.Add(new WriteExcelNode { Column = "Observatie", Value = "Nu exista pagina exacta", Color = CellColor.Yellow });
        notFound.Else.Add(new WriteExcelNode { Column = "Observatie", Value = "Pagina gasita", Color = CellColor.Green });
        each.Body.Add(notFound);
        each.Body.Add(new WriteExcelNode { Column = "Verificat la", Value = "{Acum}" });

        r.Steps.Add(new ActionNode { Action = RprAction.OpenBrowser, Technology = UiTechnology.Web, Value = "https://en.wikipedia.org" });
        r.Steps.Add(each);
        r.Steps.Add(new QuestionNode { Text = "Gata. Rezultatele sunt in {Fisier}", Buttons = "OK", StopButton = "", SkipButton = "" });
        return r;
    }

    // ─────────────────────────────────────────────────────────
    // 04 — SAP VA03 (sablon)
    // ─────────────────────────────────────────────────────────
    private static Routine SapVa03(ObjectRepository repo)
    {
        var excel = System.IO.Path.Combine(Folder, "Exemplu_Comenzi_SAP.xlsx");
        if (!File.Exists(excel))
        {
            using var wb = new XLWorkbook();
            var ws = wb.AddWorksheet("Comenzi");
            ws.Cell(1, 1).Value = "Comanda";
            ws.Cell(1, 1).Style.Font.Bold = true;
            ws.Cell(2, 1).Value = "(pune aici numerele comenzilor)";
            ws.Column(1).Width = 32;
            wb.SaveAs(excel);
        }

        var order = Obj(repo, "SAP_Camp_Comanda_VA03", UiTechnology.Sap, "wnd[0]", "GuiCTextField",
            new Locator(LocatorKind.SapId, "wnd[0]/usr/ctxtVBAK-VBELN", 90),
            new Locator(LocatorKind.SapName, "VBAK-VBELN|GuiCTextField", 60));

        var r = new Routine
        {
            Name = "04 SAP - VA03 afisare comenzi (sablon)",
            Description = "SABLON: deschide SAP Logon si autentifica-te inainte. Verifica obiectul SAP_Camp_Comanda_VA03 cu 👁 / Spy SAP.",
            Variables = { ["Fisier"] = excel },
        };
        r.Settings.DefaultErrorPolicy = ErrorPolicy.Ask;

        var each = new ForEachRowNode { FilePath = "{Fisier}", Sheet = "Comenzi", KeyColumn = "Comanda", StatusColumn = "Status" };
        each.Body.Add(new ActionNode { Action = RprAction.SapTransaction, Technology = UiTechnology.Sap, Value = "/nVA03" });
        each.Body.Add(new ActionNode { Action = RprAction.TypeText, Target = order, Value = "{Rand.Comanda}" });
        each.Body.Add(new ActionNode { Action = RprAction.SapSendKey, Technology = UiTechnology.Sap, Value = "Enter" });
        each.Body.Add(new ActionNode { Action = RprAction.SapReadStatusBar, Technology = UiTechnology.Sap, OutputVariable = "StareSAP" });

        var err = new IfNode
        {
            Condition = new Condition
            {
                Kind = ConditionKind.AnyOf,
                Children =
                {
                    new Condition { Kind = ConditionKind.Compare, Left = "{StareSAP}", Operator = CompareOperator.StartsWith, Right = "E:" },
                    new Condition { Kind = ConditionKind.Compare, Left = "{StareSAP}", Operator = CompareOperator.StartsWith, Right = "A:" },
                },
            },
        };
        err.Then.Add(new WriteExcelNode { Column = "Mesaj SAP", Value = "{StareSAP}", Color = CellColor.Red });
        err.Else.Add(new WriteExcelNode { Column = "Mesaj SAP", Value = "Afisata OK {StareSAP}", Color = CellColor.Green });
        each.Body.Add(err);
        each.Body.Add(new ActionNode { Action = RprAction.SapSendKey, Technology = UiTechnology.Sap, Value = "F3", OnError = ErrorPolicy.Continue });

        r.Steps.Add(new ActionNode { Action = RprAction.SapConnect, Technology = UiTechnology.Sap });
        r.Steps.Add(each);
        return r;
    }

    // ─────────────────────────────────────────────────────────
    // 05 — Desktop: Notepad
    // ─────────────────────────────────────────────────────────
    private static Routine DesktopNotepad(ObjectRepository repo)
    {
        var editor = Obj(repo, "Notepad_Editor", UiTechnology.Desktop, "proces:notepad.exe", "Document / Edit",
            new Locator(LocatorKind.ClassName, "Document|RichEditD2DPT", 70),   // Notepad Windows 11
            new Locator(LocatorKind.ClassName, "Edit|Edit", 60));               // Notepad clasic

        var r = new Routine
        {
            Name = "05 Desktop - Notepad",
            Description = "Arata pasii desktop: porneste aplicatia, ataseaza fereastra, scrie text intr-o bucla.",
        };

        var loop = new LoopNode { Count = "3", CounterVariable = "Linie" };
        loop.Body.Add(new ActionNode { Action = RprAction.AppendText, Target = editor, Value = "Linia {Linie} scrisa de AutoPilot la {Acum}{NewLine}" });

        r.Steps.Add(new ActionNode
        {
            Action = RprAction.LaunchApp, Technology = UiTechnology.Desktop, Value = "notepad.exe",
            OnError = ErrorPolicy.Continue,
            Comment = "In Windows 11 Notepad porneste prin alt proces; pasul urmator se ataseaza oricum la fereastra.",
        });
        r.Steps.Add(new WaitNode { Seconds = 1.5 });
        r.Steps.Add(new ActionNode { Action = RprAction.AttachWindow, Technology = UiTechnology.Desktop, Value = "proces:notepad.exe", TimeoutMs = 10000 });
        r.Steps.Add(loop);
        r.Steps.Add(new LogNode { Message = "Verifica textul in Notepad (nu se salveaza nimic automat)." });
        return r;
    }
}

/// <summary>Lista cu exemplele instalate; returneaza calea aleasa.</summary>
public static class ExamplePickerDialog
{
    public static string? Pick(Window owner, List<ExampleInfo> examples)
    {
        var w = new Window
        {
            Title = "Rutine exemplu",
            Width = 720,
            Height = 520,
            Owner = owner,
            WindowStartupLocation = WindowStartupLocation.CenterOwner,
        };
        Ui.Themed(w);

        var root = new DockPanel { Margin = new Thickness(14) };
        var top = Ui.Text("Alege un exemplu. Toate se pot rula imediat (SAP necesita SAP GUI deschis). Obiectele lor au fost adaugate in repository.", 13);
        top.Margin = new Thickness(0, 0, 0, 8);
        DockPanel.SetDock(top, Dock.Top);
        root.Children.Add(top);

        string? picked = null;
        var list = new ListBox { HorizontalContentAlignment = HorizontalAlignment.Stretch };
        foreach (var ex in examples)
        {
            var panel = new StackPanel { Margin = new Thickness(4, 6, 4, 6), Tag = ex.Path };
            panel.Children.Add(Ui.Text(ex.Title, 14, true));
            panel.Children.Add(Ui.Text(ex.Description, 12, false, "TextDimBrush"));
            list.Items.Add(panel);
        }
        list.SelectedIndex = 0;

        var buttons = new StackPanel { Orientation = Orientation.Horizontal, HorizontalAlignment = HorizontalAlignment.Right, Margin = new Thickness(0, 10, 0, 0) };
        DockPanel.SetDock(buttons, Dock.Bottom);
        void Accept()
        {
            if (list.SelectedItem is StackPanel { Tag: string p }) { picked = p; w.DialogResult = true; }
        }
        buttons.Children.Add(Ui.Btn("Deschide", "SuccessButtonStyle", (_, _) => Accept()));
        buttons.Children.Add(Ui.Btn("Deschide folderul", "NeutralButtonStyle", (_, _) =>
            System.Diagnostics.Process.Start(new System.Diagnostics.ProcessStartInfo("explorer.exe", $"\"{ExampleRoutines.Folder}\"") { UseShellExecute = true })));
        buttons.Children.Add(Ui.Btn("Inchide", "NeutralButtonStyle", (_, _) => w.DialogResult = false));
        root.Children.Add(buttons);

        list.MouseDoubleClick += (_, _) => Accept();
        root.Children.Add(list);
        w.Content = root;
        return w.ShowDialog() == true ? picked : null;
    }
}
