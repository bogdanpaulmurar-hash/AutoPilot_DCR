// ============================================================
// AutoPilot DC v4 — Studio RPR
// PropertyEditor.cs — Panoul "Proprietati": tot ce se configureaza
// la un pas se alege din liste, casete si butoane — fara cod.
//
//  - Campurile de text au "＋ variabila" (insereaza {Rand.IBase} etc.)
//  - Obiectele se aleg din Object Repository sau se marcheaza pe loc (🎯)
//  - Conditiile se construiesc din liste: obiect / operator / valoare,
//    cu grupuri SI / SAU imbricate.
// ============================================================

using System.IO;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using AutoPilotDC.Rpr.Excel;
using AutoPilotDC.Rpr.Model;
using Microsoft.Win32;
using Brushes = System.Windows.Media.Brushes;
using Button = System.Windows.Controls.Button;
using CheckBox = System.Windows.Controls.CheckBox;
using ComboBox = System.Windows.Controls.ComboBox;
using Condition = AutoPilotDC.Rpr.Model.Condition;
using ContextMenu = System.Windows.Controls.ContextMenu;
using HorizontalAlignment = System.Windows.HorizontalAlignment;
using MenuItem = System.Windows.Controls.MenuItem;
using MessageBox = System.Windows.MessageBox;
using OpenFileDialog = Microsoft.Win32.OpenFileDialog;
using Orientation = System.Windows.Controls.Orientation;
using Panel = System.Windows.Controls.Panel;
using TextBox = System.Windows.Controls.TextBox;
using VerticalAlignment = System.Windows.VerticalAlignment;

namespace AutoPilotDC.UI.Studio;

/// <summary>Ce ofera fereastra Studio panoului de proprietati.</summary>
public interface IStudioContext
{
    Window Owner { get; }
    Routine Routine { get; }
    ObjectRepository Repository { get; }

    /// <summary>Variabilele cunoscute in punctul unui pas (pentru "＋ variabila").</summary>
    IReadOnlyList<string> KnownVariables(RprNode? at);

    /// <summary>Marcheaza un obiect nou cu Spy si il salveaza in repository.</summary>
    Task<UiObject?> SpyNewObjectAsync(UiTechnology technology);

    Task HighlightObjectAsync(string objectName);
    Task TestNodeAsync(RprNode node);

    /// <summary>Pasul s-a schimbat: structural = trebuie reconstruit arborele.</summary>
    void NodeChanged(RprNode node, bool structural);
    void RoutineChanged();
}

public sealed class PropertyEditor
{
    private readonly IStudioContext _ctx;
    private Panel _host = new StackPanel();
    private object? _target;

    public PropertyEditor(IStudioContext ctx) => _ctx = ctx;

    // =========================================================
    // Intrare
    // =========================================================
    public void Show(Panel host, object? target)
    {
        _host = host;
        _target = target;
        Rebuild();
    }

    public void Rebuild()
    {
        _host.Children.Clear();
        switch (_target)
        {
            case RprNode node: BuildNode(node); break;
            case Routine r:    BuildRoutine(r); break;
            default:
                _host.Children.Add(Ui.Hint("Selecteaza un pas din arbore ca sa-l configurezi."));
                break;
        }
    }

    private void Changed(RprNode node, bool structural = false)
    {
        _ctx.NodeChanged(node, structural);
        if (structural) Rebuild();
    }

    // =========================================================
    // Pas
    // =========================================================
    private void BuildNode(RprNode node)
    {
        var header = Ui.Text($"{StudioLabels.IconFor(node)}  {node.KindLabel}", 16, true, "PrimaryBrush");
        _host.Children.Add(header);

        switch (node)
        {
            case ActionNode a:      BuildAction(a); break;
            case WaitNode w:        BuildWait(w); break;
            case SetVariableNode s: BuildSetVariable(s); break;
            case IfNode i:
                _host.Children.Add(Ui.Hint("Pasii din ramura \"Atunci\" ruleaza cand conditia e adevarata, cei din \"Altfel\" cand e falsa."));
                AddCondition(_host, i.Condition, node, 0);
                break;
            case LoopNode l:        BuildLoop(l); break;
            case ForEachRowNode f:  BuildForEach(f); break;
            case WriteExcelNode we: BuildWriteExcel(we); break;
            case QuestionNode q:    BuildQuestion(q); break;
            case TryNode t:
                _host.Children.Add(Ui.Hint("Daca un pas din \"Incearca\" esueaza, rutina NU se opreste: ruleaza ramura \"La eroare\". " +
                                           "Mesajul erorii e in variabila de mai jos."));
                AddText(node, "Variabila cu mesajul erorii", () => t.ErrorVariable, v => t.ErrorVariable = v, vars: false);
                break;
            case GroupNode:
                _host.Children.Add(Ui.Hint("Grupul doar organizeaza pasii (il poti dezactiva cu totul sau redenumi)."));
                break;
            case LogNode lg:
                AddText(node, "Mesaj", () => lg.Message, v => lg.Message = v, multiline: true);
                AddCombo(node, "Nivel", StudioLabels.LogLevels, () => lg.Level, v => lg.Level = v);
                break;
            case BreakNode b:
                AddCheck(node, "Doar treci la urmatoarea repetare / urmatorul rand (nu iesi din bucla)", () => b.NextIteration, v => b.NextIteration = v);
                break;
            case StopNode st:
                AddText(node, "Mesaj", () => st.Message, v => st.Message = v);
                AddCheck(node, "Opreste ca EROARE (randul Excel curent va fi marcat cu rosu)", () => st.AsError, v => st.AsError = v);
                break;
            case LegacyStepNode ls:
                BuildLegacy(ls);
                break;
        }

        // ── Comun tuturor pasilor ───────────────────────────
        var common = new StackPanel();
        _host.Children.Add(Ui.Card(common));
        common.Children.Add(Ui.Text("General", 13, true, "TextDimBrush"));
        AddText(node, "Titlu personalizat (gol = automat)", () => node.Label, v => node.Label = v, vars: false, host: common);
        AddCheck(node, "Pas activ (debifat = omis la rulare)", () => node.Enabled, v => node.Enabled = v, host: common);
        AddInt(node, "Asteapta inainte (ms)", () => node.DelayBeforeMs, v => node.DelayBeforeMs = v, host: common);
        AddInt(node, "Asteapta dupa (ms)", () => node.DelayAfterMs, v => node.DelayAfterMs = v, host: common);
        AddCombo(node, "La eroare", StudioLabels.ErrorPolicies, () => node.OnError, v => node.OnError = v, host: common);
        AddText(node, "Comentariu / notita", () => node.Comment, v => node.Comment = v, vars: false, multiline: true, host: common);
    }

    // ── Actiune ────────────────────────────────────────────────
    private void BuildAction(ActionNode a)
    {
        var info = ActionCatalog.Get(a.Action);

        // 1. Actiunea (grupata pe tehnologii)
        _host.Children.Add(Ui.Caption("Ce face pasul"));
        var actions = new ComboBox { MaxDropDownHeight = 480 };
        foreach (var ai in ActionCatalog.Actions)
        {
            string group = ai.Technologies.Length == 4 ? "Pe obiect"
                         : ai.Technologies.Contains(UiTechnology.Sap) ? "SAP"
                         : ai.Technologies.Contains(UiTechnology.Desktop) ? "Desktop"
                         : "Browser";
            actions.Items.Add(new ComboBoxItem { Content = $"{group}  ·  {ai.Label}", Tag = ai.Action });
        }
        actions.SelectedIndex = ActionCatalog.Actions.ToList().FindIndex(x => x.Action == a.Action);
        actions.SelectionChanged += (_, _) =>
        {
            if (actions.SelectedItem is ComboBoxItem { Tag: RprAction act } && act != a.Action)
            {
                a.Action = act;
                var ni = ActionCatalog.Get(act);
                if (!ni.Technologies.Contains(a.Technology)) a.Technology = ni.Technologies[0];
                if (!ni.NeedsTarget && !ni.TargetOptional) a.Target = "";
                Changed(a, structural: true);
            }
        };
        _host.Children.Add(actions);

        // 2. Obiectul
        if (info.NeedsTarget || info.TargetOptional)
        {
            AddObjectPicker(a, info.TargetOptional ? "Obiect (optional — gol = tasta se trimite ferestrei active)" : "Pe ce obiect",
                () => a.Target, v => a.Target = v, info.Technologies);
        }

        // 3. Tehnologia (doar fara obiect)
        if (string.IsNullOrWhiteSpace(a.Target) && info.Technologies.Length > 1 && !info.NeedsTarget)
        {
            var opts = StudioLabels.Technologies.Where(t => info.Technologies.Contains(t.Value)).ToArray();
            AddCombo(a, "Tehnologie", opts, () => a.Technology, v => a.Technology = v);
        }

        // 4. Valoarea
        if (info.ValueLabel != null)
        {
            AddText(a, info.ValueLabel, () => a.Value, v => a.Value = v, multiline: a.Action is RprAction.TypeText or RprAction.AppendText);
            var hint = a.Action switch
            {
                RprAction.TypeText or RprAction.AppendText => "Poti folosi variabile, ex: {Rand.IBase} sau {Azi}.",
                RprAction.PressKey => "Exemple: Enter, Tab, Escape, F5, Ctrl+A, Ctrl+Shift+S, Alt+F4.",
                RprAction.SapSendKey => "Exemple: Enter, F3 (Inapoi), F8 (Executa), Ctrl+S (Salvare), Shift+F4.",
                RprAction.SapTransaction => "Ex: VA03. Cu /n in fata (/nVA03) se inchide tranzactia curenta.",
                RprAction.SapGridReadCell => "Ex: 0|MATNR (rand 0, coloana tehnica MATNR) sau 0|2 pentru tabele clasice.",
                RprAction.SwitchTab => "0 = primul tab, -1 = ultimul tab, sau un text din titlu / adresa.",
                RprAction.AttachWindow => "Ex: proces:notepad.exe  sau  ^Calculator$ (titlu, expresie regulata).",
                RprAction.LaunchApp => "Ex: notepad.exe  sau  \"C:\\Program Files\\App\\app.exe\" /param",
                RprAction.SapConnect => "Gol = prima sesiune. \"1\" = a doua sesiune. \"1/0\" = conexiunea 2, sesiunea 1.",
                _ => null,
            };
            if (hint != null) _host.Children.Add(Ui.Hint(hint));
        }

        // 5. Rezultat
        if (info.ProducesOutput)
        {
            AddText(a, "Salveaza rezultatul in variabila", () => a.OutputVariable, v => a.OutputVariable = v, vars: false);
            _host.Children.Add(Ui.Hint("Ex: Status. Apoi folosesti {Status} in pasii urmatori, in conditii sau in Excel."));

            AddText(a, "Valoarea asteptata (optional)", () => a.ExpectedValue, v => a.ExpectedValue = v);
            _host.Children.Add(Ui.Hint("Daca valoarea citita e diferita, rutina se opreste si te intreaba. " +
                                       "* = orice text. Ex: S:*  (orice mesaj de succes SAP),  {Rand.Status},  Salvat*"));
        }

        // 6. Optiuni
        if (info.NeedsTarget || !string.IsNullOrWhiteSpace(a.Target))
        {
            AddInt(a, "Asteapta obiectul maxim (ms)", () => a.TimeoutMs, v => a.TimeoutMs = v);
            AddCheck(a, "Mod direct (fara miscarea vizibila a mouse-ului, unde e posibil)", () => a.DirectMode, v => a.DirectMode = v);
        }

        var row = new WrapPanel { Margin = new Thickness(0, 8, 0, 0) };
        row.Children.Add(Ui.Btn("▶ Testeaza pasul", "SuccessButtonStyle", async (_, _) => await _ctx.TestNodeAsync(a),
            "Executa doar acest pas acum (cu variabilele ultimei rulari)"));
        if (!string.IsNullOrWhiteSpace(a.Target))
            row.Children.Add(Ui.Btn("👁 Arata obiectul", "NeutralButtonStyle", async (_, _) => await _ctx.HighlightObjectAsync(a.Target),
                "Marcheaza obiectul pe ecran (verifici ca e gasit corect)"));
        _host.Children.Add(row);
    }

    // ── Asteapta ───────────────────────────────────────────────
    private void BuildWait(WaitNode w)
    {
        AddCombo(w, "Cat asteapta", StudioLabels.WaitModes, () => w.Mode, v => w.Mode = v, structural: true);
        if (w.Mode == WaitMode.Seconds)
        {
            AddDouble(w, "Secunde", () => w.Seconds, v => w.Seconds = v);
            return;
        }
        AddCondition(_host, w.Condition, w, 0);
        AddInt(w, "Timp maxim (ms)", () => w.TimeoutMs, v => w.TimeoutMs = v);
        AddCheck(w, "Daca nu se indeplineste in timp: eroare (debifat = continua)", () => w.FailOnTimeout, v => w.FailOnTimeout = v);
    }

    // ── Variabila ──────────────────────────────────────────────
    private void BuildSetVariable(SetVariableNode s)
    {
        AddText(s, "Numele variabilei", () => s.Name, v => s.Name = v.Trim('{', '}', ' '), vars: false);
        AddCombo(s, "Operatie", StudioLabels.VariableOperations, () => s.Operation, v => s.Operation = v, structural: true);
        if (s.Operation == VariableOperation.Replace)
            AddText(s, "Cauta textul", () => s.Find, v => s.Find = v);
        if (s.Operation is VariableOperation.Set or VariableOperation.Append or VariableOperation.Replace
            or VariableOperation.Increment or VariableOperation.Decrement)
            AddText(s, s.Operation == VariableOperation.Replace ? "Inlocuieste cu" : "Valoare", () => s.Value, v => s.Value = v);
    }

    // ── Repeta ─────────────────────────────────────────────────
    private void BuildLoop(LoopNode l)
    {
        AddCombo(l, "Cum repeta", StudioLabels.LoopModes, () => l.Mode, v => l.Mode = v, structural: true);
        if (l.Mode == LoopMode.Times)
            AddText(l, "De cate ori", () => l.Count, v => l.Count = v);
        else
        {
            AddCondition(_host, l.Condition, l, 0);
            AddInt(l, "Maxim repetari (protectie)", () => l.MaxIterations, v => l.MaxIterations = v);
        }
        AddText(l, "Variabila cu numarul repetarii", () => l.CounterVariable, v => l.CounterVariable = v, vars: false);
        _host.Children.Add(Ui.Hint($"In pasii din bucla folosesti {{{l.CounterVariable}}} = 1, 2, 3..."));
    }

    // ── Pentru fiecare rand Excel ──────────────────────────────
    private void BuildForEach(ForEachRowNode f)
    {
        _host.Children.Add(Ui.Hint("Pasii din interior ruleaza o data pentru fiecare rand. Valorile randului sunt variabile: " +
                                   $"{{{f.RowVariable}.TitluColoana}}, {{{f.RowVariable}.A}} (dupa litera), {{{f.RowVariable}.#}} (numarul randului)."));

        AddFile(f, "Fisier Excel", () => f.FilePath, v => f.FilePath = v, "Excel|*.xlsx;*.xlsm");

        var info = ExcelInfo.Read(f.FilePath, f.Sheet, f.HeaderRow);
        if (info.Sheets.Count > 0)
            AddEditableChoice(f, "Foaia (gol = prima)", info.Sheets, () => f.Sheet, v => f.Sheet = v, structural: true);
        else
            AddText(f, "Foaia (gol = prima)", () => f.Sheet, v => f.Sheet = v, vars: false);

        AddInt(f, "Randul cu titlurile coloanelor (0 = fara titluri)", () => f.HeaderRow, v => f.HeaderRow = v, structural: true);
        AddInt(f, "Primul rand cu date (0 = imediat sub titluri)", () => f.StartRow, v => f.StartRow = v);
        AddInt(f, "Ultimul rand (0 = pana la primul rand gol)", () => f.EndRow, v => f.EndRow = v);
        AddEditableChoice(f, "Coloana cheie (rand gol aici = sfarsitul listei)", info.Headers, () => f.KeyColumn, v => f.KeyColumn = v);
        AddText(f, "Prefixul variabilelor de rand", () => f.RowVariable, v => f.RowVariable = v.Trim(), vars: false);
        AddEditableChoice(f, "Coloana de status (gol = nu scrie status)", info.Headers.Append("Status"), () => f.StatusColumn, v => f.StatusColumn = v);
        AddCheck(f, "Coloreaza randurile (verde OK, rosu eroare)", () => f.ColorRows, v => f.ColorRows = v);
        AddCheck(f, "Salveaza Excel dupa fiecare rand (sigur la intreruperi)", () => f.SaveAfterEachRow, v => f.SaveAfterEachRow = v);
        AddCheck(f, "La reluare, sari randurile deja marcate OK", () => f.SkipCompletedRows, v => f.SkipCompletedRows = v);

        if (info.Error != null)
            _host.Children.Add(Ui.Text(info.Error, 12, false, "WarningBrush"));
        else if (info.Headers.Count > 0)
            _host.Children.Add(Ui.Hint($"Coloane gasite ({info.DataRows} randuri cu date): " +
                                       string.Join(", ", info.Headers.Select(h => "{" + f.RowVariable + "." + h + "}"))));
    }

    private void BuildWriteExcel(WriteExcelNode w)
    {
        var loop = FindParentForEach(w);
        if (loop == null)
            _host.Children.Add(Ui.Text("Pune acest pas IN INTERIORUL unui bloc \"Pentru fiecare rand Excel\".", 12, true, "WarningBrush"));
        var headers = loop != null ? ExcelInfo.Read(loop.FilePath, loop.Sheet, loop.HeaderRow).Headers : new List<string>();
        AddEditableChoice(w, "Coloana (titlu sau litera; coloana noua se creeaza automat)", headers, () => w.Column, v => w.Column = v);
        AddText(w, "Valoare", () => w.Value, v => w.Value = v);
        AddCombo(w, "Culoare celula", StudioLabels.CellColors, () => w.Color, v => w.Color = v);
    }

    private void BuildQuestion(QuestionNode q)
    {
        AddText(q, "Intrebarea", () => q.Text, v => q.Text = v, multiline: true);
        AddText(q, "Butoane (separate prin virgula)", () => q.Buttons, v => q.Buttons = v, vars: false);
        AddText(q, "Raspunsul se salveaza in variabila", () => q.OutputVariable, v => q.OutputVariable = v, vars: false);
        AddText(q, "Butonul care OPRESTE rutina", () => q.StopButton, v => q.StopButton = v, vars: false);
        AddText(q, "Butonul care SARE randul Excel curent", () => q.SkipButton, v => q.SkipButton = v, vars: false);
        _host.Children.Add(Ui.Hint($"Celelalte butoane continua rutina. Poti pune apoi un \"Daca\" cu conditia {{{q.OutputVariable}}} = \"NumeButon\"."));
    }

    private void BuildLegacy(LegacyStepNode ls)
    {
        _host.Children.Add(Ui.Hint("Pas importat din versiunea 3.9 (coordonate de ecran). Functioneaza, dar e fragil: " +
                                   "daca fereastra se muta sau rezolutia se schimba, click-ul nimereste altundeva. " +
                                   "Recomandat: inlocuieste-l cu un pas \"Actiune\" pe un obiect marcat cu Spy."));
        var s = ls.Step;
        AddText(ls, "Descriere", () => s.Description, v => s.Description = v, vars: false);
        AddInt(ls, "X", () => s.X, v => s.X = v);
        AddInt(ls, "Y", () => s.Y, v => s.Y = v);
        if (!string.IsNullOrEmpty(s.KeyCombo) || s.StepType == "KEY")
            AddText(ls, "Taste", () => s.KeyCombo, v => s.KeyCombo = v, vars: false);
        if (!string.IsNullOrEmpty(s.TextInput) || s.StepType == "TYPE")
            AddText(ls, "Text", () => s.TextInput, v => s.TextInput = v, vars: false);
    }

    // =========================================================
    // Rutina (nimic selectat)
    // =========================================================
    private void BuildRoutine(Routine r)
    {
        _host.Children.Add(Ui.Text("⚙  Setarile rutinei", 16, true, "PrimaryBrush"));

        AddRoutineText("Nume", () => r.Name, v => r.Name = v);
        AddRoutineText("Descriere", () => r.Description, v => r.Description = v, multiline: true);

        var s = r.Settings;
        _host.Children.Add(Ui.Caption("La eroare (implicit pentru toti pasii)"));
        _host.Children.Add(MakeCombo(StudioLabels.ErrorPolicies.Where(x => x.Value != ErrorPolicy.Inherit).ToArray(),
            () => s.DefaultErrorPolicy, v => { s.DefaultErrorPolicy = v; _ctx.RoutineChanged(); }));
        AddRoutineCheck("Marcheaza obiectul pe ecran inainte de fiecare actiune", () => s.HighlightBeforeAction, v => s.HighlightBeforeAction = v);
        AddRoutineInt("Durata marcarii (ms)", () => s.HighlightMs, v => s.HighlightMs = v);
        AddRoutineInt("Timeout implicit pentru obiecte (ms)", () => s.DefaultTimeoutMs, v => s.DefaultTimeoutMs = v);
        AddRoutineInt("Pauza intre pasi (ms) — util la verificare", () => s.StepDelayMs, v => s.StepDelayMs = v);
        AddRoutineInt("Reincercari automate la eroare", () => s.AutoRetries, v => s.AutoRetries = v);
        AddRoutineCheck("Captura de ecran automata la eroare", () => s.ScreenshotOnError, v => s.ScreenshotOnError = v);

        _host.Children.Add(Ui.Caption("Siguranta la rulare"));
        AddRoutineCheck("🌙 Nu deranja (fara notificari Windows) cat timp ruleaza", () => s.DoNotDisturb, v => s.DoNotDisturb = v);
        AddRoutineCheck("🛡 Sistem de preventie (pauza + intrebare cand ceva difera)", () => s.GuardEnabled, v => s.GuardEnabled = v);
        _host.Children.Add(Ui.Hint("Te intreaba inainte sa continue cand: apare o fereastra de eroare, aplicatia nu raspunde, " +
                                   "SAP arata o eroare in bara de stare sau o valoare citita difera de \"Valoarea asteptata\" a pasului."));

        // ── Variabile ───────────────────────────────────────
        _host.Children.Add(Ui.Caption("Variabile (valori de start, folosite ca {Nume})"));
        var list = new StackPanel();
        _host.Children.Add(list);

        void Refill()
        {
            list.Children.Clear();
            foreach (var key in r.Variables.Keys.ToList())
            {
                var row = new Grid { Margin = new Thickness(0, 2, 0, 2) };
                row.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
                row.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1.4, GridUnitType.Star) });
                row.ColumnDefinitions.Add(new ColumnDefinition { Width = GridLength.Auto });
                var name = new TextBox { Text = key, Margin = new Thickness(0, 0, 4, 0) };
                var value = new TextBox { Text = r.Variables[key] };
                var currentKey = key;
                name.LostFocus += (_, _) =>
                {
                    var nk = name.Text.Trim().Trim('{', '}');
                    if (nk == currentKey || string.IsNullOrEmpty(nk) || r.Variables.ContainsKey(nk)) { name.Text = currentKey; return; }
                    var v = r.Variables[currentKey];
                    r.Variables.Remove(currentKey);
                    r.Variables[nk] = v;
                    currentKey = nk;
                    _ctx.RoutineChanged();
                };
                value.TextChanged += (_, _) => { r.Variables[currentKey] = value.Text; _ctx.RoutineChanged(); };
                var del = Ui.Btn("✕", "NeutralButtonStyle", (_, _) => { r.Variables.Remove(currentKey); _ctx.RoutineChanged(); Refill(); }, "Sterge variabila");
                del.Padding = new Thickness(8, 2, 8, 2);
                Grid.SetColumn(name, 0); Grid.SetColumn(value, 1); Grid.SetColumn(del, 2);
                row.Children.Add(name); row.Children.Add(value); row.Children.Add(del);
                list.Children.Add(row);
            }
        }
        Refill();
        _host.Children.Add(Ui.Btn("＋ Variabila noua", "NeutralButtonStyle", (_, _) =>
        {
            int i = 1;
            while (r.Variables.ContainsKey($"Var{i}")) i++;
            r.Variables[$"Var{i}"] = "";
            _ctx.RoutineChanged();
            Refill();
        }));
        _host.Children.Add(Ui.Hint("Variabile speciale mereu disponibile: {Azi}, {Acum}, {Acum:yyyyMMdd_HHmm}, {NewLine}."));
    }

    // =========================================================
    // Editor de conditii (recursiv pentru SI / SAU)
    // =========================================================
    private void AddCondition(Panel host, Condition c, RprNode node, int depth)
    {
        var panel = new StackPanel();
        host.Children.Add(Ui.Card(panel, 8));
        panel.Children.Add(Ui.Text(depth == 0 ? "Conditia" : "Conditie", 13, true, "AccentBrush"));

        panel.Children.Add(MakeCombo(StudioLabels.ConditionKinds, () => c.Kind, v =>
        {
            c.Kind = v;
            if (v is ConditionKind.AllOf or ConditionKind.AnyOf && c.Children.Count == 0)
                c.Children.Add(new Condition { Kind = ConditionKind.ElementExists });
            Changed(node, structural: true);
        }));

        switch (c.Kind)
        {
            case ConditionKind.AllOf:
            case ConditionKind.AnyOf:
                foreach (var child in c.Children.ToList())
                {
                    var childHost = new StackPanel { Margin = new Thickness(12, 0, 0, 0) };
                    panel.Children.Add(childHost);
                    AddCondition(childHost, child, node, depth + 1);
                    var captured = child;
                    childHost.Children.Add(Ui.Btn("✕ Scoate conditia", "NeutralButtonStyle", (_, _) =>
                    {
                        c.Children.Remove(captured);
                        Changed(node, structural: true);
                    }));
                }
                panel.Children.Add(Ui.Btn("＋ Adauga conditie", "NeutralButtonStyle", (_, _) =>
                {
                    c.Children.Add(new Condition { Kind = ConditionKind.ElementExists });
                    Changed(node, structural: true);
                }));
                break;

            case ConditionKind.Compare:
                AddText(node, "Valoarea (stanga)", () => c.Left, v => c.Left = v, host: panel);
                panel.Children.Add(MakeCombo(StudioLabels.Operators, () => c.Operator, v => { c.Operator = v; Changed(node, structural: true); }));
                if (c.Operator is not (CompareOperator.IsEmpty or CompareOperator.IsNotEmpty))
                    AddText(node, "Comparata cu (dreapta)", () => c.Right, v => c.Right = v, host: panel);
                AddCheck(node, "Ignora literele mari/mici", () => c.IgnoreCase, v => c.IgnoreCase = v, host: panel);
                break;

            default:
                AddObjectPicker(node, "Obiectul", () => c.Target, v => c.Target = v, null, panel);
                if (c.Kind == ConditionKind.ElementText)
                {
                    panel.Children.Add(MakeCombo(StudioLabels.Operators, () => c.Operator, v => { c.Operator = v; Changed(node, structural: true); }));
                    if (c.Operator is not (CompareOperator.IsEmpty or CompareOperator.IsNotEmpty))
                        AddText(node, "Valoarea", () => c.Right, v => c.Right = v, host: panel);
                    AddCheck(node, "Ignora literele mari/mici", () => c.IgnoreCase, v => c.IgnoreCase = v, host: panel);
                }
                AddInt(node, c.Kind == ConditionKind.ElementNotExists
                        ? "Asteapta sa dispara maxim (ms)"
                        : "Asteapta obiectul maxim (ms, 0 = verificare imediata)",
                    () => c.TimeoutMs, v => c.TimeoutMs = v, host: panel);
                break;
        }

        AddCheck(node, "NU (inverseaza rezultatul)", () => c.Negate, v => c.Negate = v, host: panel);
    }

    // =========================================================
    // Constructori de campuri
    // =========================================================
    private TextBox AddText(RprNode node, string label, Func<string> get, Action<string> set,
                            bool vars = true, bool multiline = false, Panel? host = null)
    {
        host ??= _host;
        host.Children.Add(Ui.Caption(label));
        var box = new TextBox
        {
            Text = get() ?? "",
            AcceptsReturn = multiline,
            TextWrapping = multiline ? TextWrapping.Wrap : TextWrapping.NoWrap,
            MinHeight = multiline ? 52 : 0,
            VerticalScrollBarVisibility = multiline ? ScrollBarVisibility.Auto : ScrollBarVisibility.Hidden,
        };
        box.TextChanged += (_, _) => { set(box.Text); Changed(node); };

        if (!vars)
        {
            host.Children.Add(box);
            return box;
        }

        var grid = new Grid();
        grid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
        grid.ColumnDefinitions.Add(new ColumnDefinition { Width = GridLength.Auto });
        Grid.SetColumn(box, 0);
        grid.Children.Add(box);
        var insert = VariableInserter(node, box);
        Grid.SetColumn(insert, 1);
        grid.Children.Add(insert);
        host.Children.Add(grid);
        return box;
    }

    /// <summary>Lista "＋ {x}" care insereaza o variabila la pozitia cursorului.</summary>
    private ComboBox VariableInserter(RprNode? node, TextBox target)
    {
        var combo = new ComboBox { Width = 92, Margin = new Thickness(4, 0, 0, 0), ToolTip = "Insereaza o variabila in text" };
        combo.Items.Add(new ComboBoxItem { Content = "＋ {x}", IsEnabled = false });
        combo.SelectedIndex = 0;
        combo.DropDownOpened += (_, _) =>
        {
            while (combo.Items.Count > 1) combo.Items.RemoveAt(1);
            foreach (var v in _ctx.KnownVariables(node))
                combo.Items.Add(new ComboBoxItem { Content = "{" + v + "}", Tag = v });
            if (combo.Items.Count == 1)
                combo.Items.Add(new ComboBoxItem { Content = "(nicio variabila inca)", IsEnabled = false });
        };
        combo.SelectionChanged += (_, _) =>
        {
            if (combo.SelectedItem is ComboBoxItem { Tag: string v })
            {
                int at = Math.Min(target.CaretIndex, target.Text.Length);
                target.Text = target.Text.Insert(at, "{" + v + "}");
                target.CaretIndex = at + v.Length + 2;
                target.Focus();
                combo.SelectedIndex = 0;
            }
        };
        return combo;
    }

    private void AddInt(RprNode node, string label, Func<int> get, Action<int> set, Panel? host = null, bool structural = false)
    {
        host ??= _host;
        host.Children.Add(Ui.Caption(label));
        var box = new TextBox { Text = get().ToString(), Width = 140, HorizontalAlignment = HorizontalAlignment.Left };
        box.TextChanged += (_, _) =>
        {
            if (int.TryParse(box.Text.Trim(), out var v) && v >= 0)
            {
                box.ClearValue(TextBox.BorderBrushProperty);
                set(v);
                Changed(node);
            }
            else box.BorderBrush = Brushes.OrangeRed;
        };
        if (structural) box.LostFocus += (_, _) => Changed(node, structural: true);
        host.Children.Add(box);
    }

    private void AddDouble(RprNode node, string label, Func<double> get, Action<double> set)
    {
        _host.Children.Add(Ui.Caption(label));
        var box = new TextBox { Text = get().ToString(System.Globalization.CultureInfo.InvariantCulture), Width = 140, HorizontalAlignment = HorizontalAlignment.Left };
        box.TextChanged += (_, _) =>
        {
            var t = box.Text.Trim().Replace(',', '.');
            if (double.TryParse(t, System.Globalization.NumberStyles.Float, System.Globalization.CultureInfo.InvariantCulture, out var v) && v >= 0)
            {
                box.ClearValue(TextBox.BorderBrushProperty);
                set(v);
                Changed(node);
            }
            else box.BorderBrush = Brushes.OrangeRed;
        };
        _host.Children.Add(box);
    }

    private void AddCheck(RprNode node, string label, Func<bool> get, Action<bool> set, Panel? host = null)
    {
        host ??= _host;
        var chk = new CheckBox { Content = label, IsChecked = get(), Margin = new Thickness(0, 6, 0, 2) };
        chk.Checked += (_, _) => { set(true); Changed(node); };
        chk.Unchecked += (_, _) => { set(false); Changed(node); };
        host.Children.Add(chk);
    }

    private void AddCombo<T>(RprNode node, string label, (T Value, string Label)[] options, Func<T> get, Action<T> set,
                             Panel? host = null, bool structural = false) where T : struct, Enum
    {
        host ??= _host;
        host.Children.Add(Ui.Caption(label));
        host.Children.Add(MakeCombo(options, get, v => { set(v); Changed(node, structural); }));
    }

    private static ComboBox MakeCombo<T>((T Value, string Label)[] options, Func<T> get, Action<T> set) where T : struct, Enum
    {
        var combo = new ComboBox();
        var current = get();
        foreach (var (value, label) in options)
        {
            var item = new ComboBoxItem { Content = label, Tag = value };
            combo.Items.Add(item);
            if (EqualityComparer<T>.Default.Equals(value, current)) combo.SelectedItem = item;
        }
        combo.SelectionChanged += (_, _) =>
        {
            if (combo.SelectedItem is ComboBoxItem { Tag: T v } && !EqualityComparer<T>.Default.Equals(v, get()))
                set(v);
        };
        return combo;
    }

    /// <summary>Lista editabila: alegi din valorile cunoscute sau scrii alta.</summary>
    private void AddEditableChoice(RprNode node, string label, IEnumerable<string> choices, Func<string> get, Action<string> set,
                                   bool structural = false)
    {
        _host.Children.Add(Ui.Caption(label));
        var combo = new ComboBox { IsEditable = true, Text = get() ?? "" };
        foreach (var c in choices.Distinct()) combo.Items.Add(c);
        combo.Text = get() ?? "";
        void Apply()
        {
            if (combo.Text == get()) return;
            set(combo.Text.Trim());
            Changed(node, structural);
        }
        combo.SelectionChanged += (_, _) =>
        {
            if (combo.SelectedItem is string s) { combo.Text = s; Apply(); }
        };
        combo.LostFocus += (_, _) => Apply();
        _host.Children.Add(combo);
    }

    private void AddFile(RprNode node, string label, Func<string> get, Action<string> set, string filter)
    {
        _host.Children.Add(Ui.Caption(label));
        var grid = new Grid();
        grid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
        grid.ColumnDefinitions.Add(new ColumnDefinition { Width = GridLength.Auto });
        var box = new TextBox { Text = get() ?? "" };
        box.LostFocus += (_, _) => { if (box.Text != get()) { set(box.Text.Trim().Trim('"')); Changed(node, structural: true); } };
        var browse = Ui.Btn("📂", "NeutralButtonStyle", (_, _) =>
        {
            var dlg = new OpenFileDialog { Filter = filter + "|Toate fisierele|*.*" };
            if (dlg.ShowDialog(_ctx.Owner) == true)
            {
                set(dlg.FileName);
                Changed(node, structural: true);
            }
        }, "Alege fisierul");
        browse.Padding = new Thickness(8, 2, 8, 2);
        Grid.SetColumn(box, 0); Grid.SetColumn(browse, 1);
        grid.Children.Add(box); grid.Children.Add(browse);
        _host.Children.Add(grid);
    }

    /// <summary>Alegerea obiectului din repository + marcare noua cu Spy + verificare pe ecran.</summary>
    private void AddObjectPicker(RprNode node, string label, Func<string> get, Action<string> set,
                                 UiTechnology[]? technologies, Panel? host = null)
    {
        host ??= _host;
        host.Children.Add(Ui.Caption(label));

        var grid = new Grid();
        grid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
        grid.ColumnDefinitions.Add(new ColumnDefinition { Width = GridLength.Auto });
        grid.ColumnDefinitions.Add(new ColumnDefinition { Width = GridLength.Auto });

        var combo = new ComboBox { MaxDropDownHeight = 420 };
        combo.Items.Add(new ComboBoxItem { Content = "(alege un obiect)", Tag = "" });
        foreach (var o in _ctx.Repository.Objects
                     .Where(o => technologies == null || technologies.Contains(o.Technology))
                     .OrderBy(o => o.Technology).ThenBy(o => o.Name))
        {
            var item = new ComboBoxItem { Content = $"{o.Name}   ·   {TechShort(o.Technology)}", Tag = o.Name, ToolTip = o.Locators.FirstOrDefault()?.ToString() };
            combo.Items.Add(item);
            if (string.Equals(o.Name, get(), StringComparison.OrdinalIgnoreCase)) combo.SelectedItem = item;
        }
        if (combo.SelectedItem == null)
        {
            if (!string.IsNullOrWhiteSpace(get()))
            {
                var missing = new ComboBoxItem { Content = $"⚠ {get()} (lipseste din repository)", Tag = get() };
                combo.Items.Add(missing);
                combo.SelectedItem = missing;
            }
            else combo.SelectedIndex = 0;
        }
        combo.SelectionChanged += (_, _) =>
        {
            if (combo.SelectedItem is ComboBoxItem { Tag: string name } && name != get())
            {
                set(name);
                Changed(node, structural: true);
            }
        };

        // 🎯 marcheaza un obiect nou (meniu cu tehnologiile)
        var spy = Ui.Btn("🎯", "PrimaryButtonStyle", null, "Marcheaza un obiect nou pe ecran (Spy)");
        spy.Padding = new Thickness(8, 2, 8, 2);
        var menu = new ContextMenu();
        foreach (var (tech, techLabel) in StudioLabels.Technologies.Where(t => technologies == null || technologies.Contains(t.Value)))
        {
            var mi = new MenuItem { Header = "Spy " + techLabel };
            var captured = tech;
            mi.Click += async (_, _) =>
            {
                var obj = await _ctx.SpyNewObjectAsync(captured);
                if (obj != null)
                {
                    set(obj.Name);
                    Changed(node, structural: true);
                }
            };
            menu.Items.Add(mi);
        }
        spy.Click += (_, _) => { menu.PlacementTarget = spy; menu.IsOpen = true; };

        var show = Ui.Btn("👁", "NeutralButtonStyle", async (_, _) =>
        {
            if (!string.IsNullOrWhiteSpace(get())) await _ctx.HighlightObjectAsync(get());
        }, "Arata obiectul pe ecran");
        show.Padding = new Thickness(8, 2, 8, 2);

        Grid.SetColumn(combo, 0); Grid.SetColumn(spy, 1); Grid.SetColumn(show, 2);
        grid.Children.Add(combo); grid.Children.Add(spy); grid.Children.Add(show);
        host.Children.Add(grid);
    }

    private static string TechShort(UiTechnology t) => t switch
    {
        UiTechnology.Web => "Web",
        UiTechnology.WebSelenium => "Selenium",
        UiTechnology.Sap => "SAP",
        _ => "Desktop",
    };

    // ── campuri pentru setarile rutinei ──────────────────────
    private void AddRoutineText(string label, Func<string> get, Action<string> set, bool multiline = false)
    {
        _host.Children.Add(Ui.Caption(label));
        var box = new TextBox { Text = get(), AcceptsReturn = multiline, TextWrapping = multiline ? TextWrapping.Wrap : TextWrapping.NoWrap, MinHeight = multiline ? 52 : 0 };
        box.TextChanged += (_, _) => { set(box.Text); _ctx.RoutineChanged(); };
        _host.Children.Add(box);
    }

    private void AddRoutineInt(string label, Func<int> get, Action<int> set)
    {
        _host.Children.Add(Ui.Caption(label));
        var box = new TextBox { Text = get().ToString(), Width = 140, HorizontalAlignment = HorizontalAlignment.Left };
        box.TextChanged += (_, _) =>
        {
            if (int.TryParse(box.Text.Trim(), out var v) && v >= 0) { box.ClearValue(TextBox.BorderBrushProperty); set(v); _ctx.RoutineChanged(); }
            else box.BorderBrush = Brushes.OrangeRed;
        };
        _host.Children.Add(box);
    }

    private void AddRoutineCheck(string label, Func<bool> get, Action<bool> set)
    {
        var chk = new CheckBox { Content = label, IsChecked = get(), Margin = new Thickness(0, 6, 0, 2) };
        chk.Checked += (_, _) => { set(true); _ctx.RoutineChanged(); };
        chk.Unchecked += (_, _) => { set(false); _ctx.RoutineChanged(); };
        _host.Children.Add(chk);
    }

    private ForEachRowNode? FindParentForEach(RprNode node) =>
        _ctx.Routine.AllNodes().OfType<ForEachRowNode>()
            .Where(f => Routine.Flatten(f.Body).Contains(node))
            .LastOrDefault();
}

/// <summary>Informatii despre un fisier Excel (foi, titluri) pentru listele din Studio. Cu cache.</summary>
public sealed class ExcelInfo
{
    public List<string> Sheets { get; init; } = new();
    public List<string> Headers { get; init; } = new();
    public int DataRows { get; init; }
    public string? Error { get; init; }

    private static readonly Dictionary<string, (DateTime Stamp, ExcelInfo Info)> Cache = new();

    public static ExcelInfo Read(string path, string sheet, int headerRow)
    {
        if (string.IsNullOrWhiteSpace(path) || path.Contains('{')) return new ExcelInfo();
        if (!File.Exists(path)) return new ExcelInfo { Error = "Fisierul nu exista (inca)." };

        var key = $"{path}|{sheet}|{headerRow}";
        var stamp = File.GetLastWriteTimeUtc(path);
        if (Cache.TryGetValue(key, out var c) && c.Stamp == stamp) return c.Info;

        ExcelInfo info;
        try
        {
            var sheets = ExcelTable.GetSheetNames(path).ToList();
            using var t = ExcelTable.Open(path, sheet, headerRow);
            var first = t.FirstDataRow(0);
            var last = t.LastDataRow("");
            info = new ExcelInfo
            {
                Sheets = sheets,
                Headers = t.Headers.OrderBy(h => h.Value).Select(h => h.Key).ToList(),
                DataRows = Math.Max(0, last - first + 1),
            };
        }
        catch (Exception ex)
        {
            info = new ExcelInfo { Error = "Nu pot citi fisierul: " + ex.Message };
        }
        Cache[key] = (stamp, info);
        return info;
    }
}
