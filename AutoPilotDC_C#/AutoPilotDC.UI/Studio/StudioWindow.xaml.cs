// ============================================================
// AutoPilot DC v4 — Studio RPR
// StudioWindow.xaml.cs — Editorul vizual de rutine
//
//  Stanga : blocuri (pasi) + Object Repository
//  Centru : arborele rutinei (pasi, ramuri Atunci/Altfel, bucle)
//  Dreapta: proprietatile pasului selectat (PropertyEditor)
//  Jos    : logul rularii + variabilele
//
//  Fluxul tipic:
//   1. 🎯 Spy -> marchezi elementele (butoane, campuri) o singura data
//   2. adaugi pasi din stanga si alegi obiectele din liste
//   3. ▶ Ruleaza (sau ⏭ Pas cu pas) — elementele sunt marcate inainte de actiune
// ============================================================

using System.Collections.ObjectModel;
using System.Diagnostics;
using System.IO;
using System.Text.Json;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using AutoPilotDC.Infrastructure.Engines;
using AutoPilotDC.Rpr.Engine;
using AutoPilotDC.Rpr.Model;
using AutoPilotDC.Rpr.Storage;
using Application = System.Windows.Application;
using Button = System.Windows.Controls.Button;
using CheckBox = System.Windows.Controls.CheckBox;
using ComboBox = System.Windows.Controls.ComboBox;
using Condition = AutoPilotDC.Rpr.Model.Condition;
using HorizontalAlignment = System.Windows.HorizontalAlignment;
using KeyEventArgs = System.Windows.Input.KeyEventArgs;
using MessageBox = System.Windows.MessageBox;
using OpenFileDialog = Microsoft.Win32.OpenFileDialog;
using Orientation = System.Windows.Controls.Orientation;
using SaveFileDialog = Microsoft.Win32.SaveFileDialog;
using TextBox = System.Windows.Controls.TextBox;

namespace AutoPilotDC.UI.Studio;

public partial class StudioWindow : Window, IStudioContext
{
    // ── Stare ─────────────────────────────────────────────────
    private readonly StudioSettings _settings;
    private readonly StudioDriverProvider _drivers;
    private readonly DesktopEngine? _legacyDesktop;
    private readonly PropertyEditor _editor;

    private ObjectRepository _repo = new();
    private string _repoPath = RprPaths.DefaultRepository;
    private Routine _routine = new();
    private string? _routinePath;
    private bool _dirty;

    private RprEngine? _engine;
    private RunControlWindow? _runControl;
    private bool _busy;           // Spy / rulare in curs
    private bool _recording;

    private readonly Dictionary<string, NodeItem> _items = new();
    private NodeItem? _selected;

    public ObservableCollection<NodeItem> TreeItems { get; } = new();
    private readonly ObservableCollection<LogRow> _log = new();
    private readonly List<RunLogEntry> _logEntries = new();

    public StudioWindow(DesktopEngine? legacyDesktop = null)
    {
        InitializeComponent();
        DataContext = this;

        _legacyDesktop = legacyDesktop;
        _settings = StudioSettings.Load();
        _drivers = new StudioDriverProvider(_settings);
        _drivers.Info += msg => Dispatcher.InvokeAsync(() => OnDriverInfo(msg));
        _editor = new PropertyEditor(this);

        LogList.ItemsSource = _log;

        LoadRepository(RprPaths.DefaultRepository);
        BuildToolbox();

        // Ultima rutina deschisa (daca exista)
        if (!string.IsNullOrWhiteSpace(_settings.LastRoutinePath) && File.Exists(_settings.LastRoutinePath))
        {
            try { OpenRoutine(_settings.LastRoutinePath); }
            catch (Exception) { NewRoutine(); }
        }
        else NewRoutine();

        PreviewKeyDown += Window_PreviewKeyDown;
        Closing += Window_Closing;
    }

    // =========================================================
    // IStudioContext
    // =========================================================
    Window IStudioContext.Owner => this;
    public Routine Routine => _routine;
    public ObjectRepository Repository => _repo;

    public IReadOnlyList<string> KnownVariables(RprNode? at)
    {
        var list = new List<string>();
        list.AddRange(_routine.Variables.Keys);

        // variabile produse de pasi
        foreach (var n in _routine.AllNodes())
        {
            switch (n)
            {
                case ActionNode a when !string.IsNullOrWhiteSpace(a.OutputVariable): list.Add(a.OutputVariable); break;
                case SetVariableNode s when !string.IsNullOrWhiteSpace(s.Name): list.Add(s.Name); break;
                case LoopNode l when !string.IsNullOrWhiteSpace(l.CounterVariable): list.Add(l.CounterVariable); break;
                case QuestionNode q when !string.IsNullOrWhiteSpace(q.OutputVariable): list.Add(q.OutputVariable); break;
                case TryNode t when !string.IsNullOrWhiteSpace(t.ErrorVariable): list.Add(t.ErrorVariable); break;
            }
        }

        // coloanele Excel ale buclelor care contin pasul
        foreach (var f in _routine.AllNodes().OfType<ForEachRowNode>())
        {
            if (at != null && !Routine.Flatten(f.Body).Contains(at) && at != f) continue;
            list.Add($"{f.RowVariable}.#");
            foreach (var h in ExcelInfo.Read(f.FilePath, f.Sheet, f.HeaderRow).Headers)
                list.Add($"{f.RowVariable}.{h}");
        }

        list.AddRange(new[] { "Azi", "Acum", "Acum:yyyyMMdd_HHmm", "NewLine" });
        return list.Where(v => !string.IsNullOrWhiteSpace(v)).Distinct(StringComparer.OrdinalIgnoreCase).ToList();
    }

    public Task<UiObject?> SpyNewObjectAsync(UiTechnology technology) => SpyAsync(technology, offerActions: false);

    public async Task HighlightObjectAsync(string objectName)
    {
        var obj = _repo.Find(objectName);
        if (obj == null) { SetStatus($"Obiectul {objectName} nu exista in repository."); return; }
        try
        {
            var driver = _drivers.Get(obj.Technology);
            SetStatus($"Caut [{obj.Name}]...");
            var state = await driver.GetStateAsync(obj, 3000, CancellationToken.None);
            if (!state.Exists)
            {
                SetStatus($"[{obj.Name}] NU a fost gasit pe ecranul curent.");
                MessageBox.Show(this, $"Obiectul [{obj.Name}] nu a fost gasit pe ecranul curent.\n\n" +
                                      "Verifica daca aplicatia / pagina e deschisa la ecranul potrivit. " +
                                      "Daca pagina s-a schimbat, marcheaza-l din nou cu Spy sau corecteaza locatorii (✎ Editeaza).",
                    "Obiect negasit", MessageBoxButton.OK, MessageBoxImage.Warning);
                return;
            }
            await driver.HighlightAsync(obj, 1500, CancellationToken.None);
            SetStatus($"[{obj.Name}] gasit prin {state.UsedLocator}. Text: \"{Shorten(string.IsNullOrEmpty(state.Text) ? state.Value : state.Text, 60)}\"");
        }
        catch (Exception ex)
        {
            ShowError("Nu pot verifica obiectul", ex);
        }
    }

    public async Task TestNodeAsync(RprNode node)
    {
        if (_busy) return;
        _busy = true;
        SetStatus($"Testez: {node.Title}");
        try
        {
            var engine = new RprEngine(_repo, _drivers, new StudioRunHost(this), RprPaths.Output);
            var result = await Task.Run(() => engine.RunSingleAsync(_routine, node));
            SetStatus(result.Success ? $"✔ Pasul a reusit: {node.Title}" : $"✖ {result.Message}");
            ShowVariables(engine.LastVariables);
        }
        finally
        {
            _busy = false;
        }
    }

    public void NodeChanged(RprNode node, bool structural)
    {
        MarkDirty();
        if (_items.TryGetValue(node.Id, out var item)) item.Refresh();
    }

    public void RoutineChanged()
    {
        MarkDirty();
        UpdateTitles();
    }

    // =========================================================
    // Rutina: nou / deschide / salveaza
    // =========================================================
    private void NewRoutine()
    {
        _routine = new Routine { Name = "Rutina noua" };
        _routinePath = null;
        _dirty = false;
        RebuildTree(null);
        ShowProperties(_routine);
        UpdateTitles();
    }

    private void OpenRoutine(string path)
    {
        int before = _repo.Objects.Count;
        _routine = RoutineStore.Load(path, _repo);
        if (_repo.Objects.Count != before) SaveRepository(); // obiecte importate din rutina veche

        bool legacy = _routine.Description.StartsWith("Convertita automat", StringComparison.Ordinal);
        _routinePath = legacy ? null : path;  // rutinele vechi se salveaza ca rutina noua (originalul ramane intact)
        _dirty = legacy;
        _settings.LastRoutinePath = legacy ? "" : path;
        _settings.Save();

        RebuildTree(null);
        ShowProperties(_routine);
        UpdateTitles();
        SetStatus(legacy
            ? $"Rutina v3.9 importata ({_routine.Steps.Count} pasi). Pasii pe coordonate sunt marcati 🖱 — inlocuieste-i treptat cu pasi pe obiecte."
            : $"Deschis: {path}");
    }

    private bool SaveRoutine(bool askPath)
    {
        try
        {
            if (askPath || _routinePath == null)
            {
                var dlg = new SaveFileDialog
                {
                    Filter = "Rutina AutoPilot|*.rpr.json",
                    InitialDirectory = RprPaths.Routines,
                    FileName = ObjectRepository.Sanitize(_routine.Name) + ".rpr.json",
                };
                if (dlg.ShowDialog(this) != true) return false;
                _routinePath = dlg.FileName;
            }
            RoutineStore.Save(_routine, _routinePath);
            SaveRepository();
            _dirty = false;
            _settings.LastRoutinePath = _routinePath;
            _settings.Save();
            UpdateTitles();
            SetStatus($"Salvat: {_routinePath}");
            return true;
        }
        catch (Exception ex)
        {
            ShowError("Nu pot salva rutina", ex);
            return false;
        }
    }

    private bool ConfirmDiscard()
    {
        if (!_dirty) return true;
        var answer = ChoiceDialog.Ask(this, "Modificari nesalvate", $"Rutina \"{_routine.Name}\" are modificari nesalvate.",
            new[] { "Salveaza", "Nu salva", "Anuleaza" });
        return answer switch
        {
            "Salveaza" => SaveRoutine(false),
            "Nu salva" => true,
            _ => false,
        };
    }

    private void LoadRepository(string path)
    {
        try
        {
            _repo = RepositoryStore.Load(path);
            _repoPath = path;
        }
        catch (Exception ex)
        {
            ShowError("Object Repository nu a putut fi citit (se porneste unul gol)", ex);
            _repo = new ObjectRepository();
        }
        RefreshObjects();
    }

    private void SaveRepository()
    {
        try { RepositoryStore.Save(_repo, _repoPath); }
        catch (Exception ex) { ShowError("Nu pot salva Object Repository", ex); }
    }

    private void MarkDirty()
    {
        if (_dirty) return;
        _dirty = true;
        UpdateTitles();
    }

    private void UpdateTitles()
    {
        RoutineTitle.Text = $"{_routine.Name}{(_dirty ? "  •" : "")}";
        Title = $"AutoPilot DC — Studio RPR — {_routine.Name}{(_dirty ? " *" : "")}";
        StatusRight.Text = $"{Routine.Flatten(_routine.Steps).Count()} pasi · {_repo.Objects.Count} obiecte · browser: {_settings.Browser}";
        ChkHighlight.IsChecked = _routine.Settings.HighlightBeforeAction;
    }

    // =========================================================
    // Toolbox — blocurile din stanga
    // =========================================================
    private void BuildToolbox()
    {
        void Group(string title) => Toolbox.Children.Add(Ui.Caption(title));
        void Item(string text, string tip, Func<RprNode> factory)
        {
            var b = new Button
            {
                Content = text,
                ToolTip = tip,
                HorizontalContentAlignment = HorizontalAlignment.Left,
                Margin = new Thickness(0, 2, 0, 2),
                Padding = new Thickness(10, 6, 10, 6),
            };
            if (Application.Current.TryFindResource("NeutralButtonStyle") is Style s) b.Style = s;
            b.HorizontalContentAlignment = HorizontalAlignment.Left;
            b.Click += (_, _) => InsertNode(factory());
            Toolbox.Children.Add(b);
        }

        Toolbox.Children.Add(Ui.Hint("Click pe un bloc = il adaugi dupa pasul selectat. Ca sa adaugi IN interiorul unui " +
                                     "\"Daca\" sau al unei bucle, selecteaza mai intai ramura (ex: ↳ Atunci)."));

        Group("Actiuni");
        Item("👆  Click pe obiect", "Click / dublu click / click dreapta pe un element marcat", () => new ActionNode { Action = RprAction.Click });
        Item("⌨  Scrie text", "Completeaza un camp (accepta variabile din Excel)", () => new ActionNode { Action = RprAction.TypeText });
        Item("👁  Citeste valoare", "Citeste textul unui element intr-o variabila", () => new ActionNode { Action = RprAction.ReadText, OutputVariable = "Valoare" });
        Item("⌨  Apasa tasta", "Enter, Tab, F5, Ctrl+S ...", () => new ActionNode { Action = RprAction.PressKey, Value = "Enter" });
        Item("🌐  Deschide browser", "Porneste browserul (Edge implicit) la o adresa", () => new ActionNode { Action = RprAction.OpenBrowser, Technology = UiTechnology.Web, Value = "https://" });
        Item("🌐  Mergi la adresa", "Navigheaza la un URL (poate contine variabile)", () => new ActionNode { Action = RprAction.Navigate, Technology = UiTechnology.Web, Value = "https://" });
        Item("🟦  SAP: conecteaza", "Se ataseaza la SAP GUI deschis", () => new ActionNode { Action = RprAction.SapConnect, Technology = UiTechnology.Sap });
        Item("🟦  SAP: tranzactie", "Porneste o tranzactie (ex: /nVA03)", () => new ActionNode { Action = RprAction.SapTransaction, Technology = UiTechnology.Sap, Value = "/n" });
        Item("🟦  SAP: tasta (Enter/F8...)", "Trimite o tasta catre SAP", () => new ActionNode { Action = RprAction.SapSendKey, Technology = UiTechnology.Sap, Value = "Enter" });
        Item("🟦  SAP: bara de stare", "Citeste mesajul din bara de stare SAP", () => new ActionNode { Action = RprAction.SapReadStatusBar, Technology = UiTechnology.Sap, OutputVariable = "StareSAP" });
        Item("🖥  Porneste aplicatie", "Porneste un program Windows", () => new ActionNode { Action = RprAction.LaunchApp, Technology = UiTechnology.Desktop });
        Item("🖥  Ataseaza fereastra", "Lucreaza intr-o fereastra deja deschisa", () => new ActionNode { Action = RprAction.AttachWindow, Technology = UiTechnology.Desktop, Value = "proces:" });

        Group("Flux (conditii si repetari)");
        Item("⏱  Asteapta", "Secunde sau pana apare / dispare ceva", () => new WaitNode());
        Item("🔀  Daca / Altfel", "Ramuri diferite dupa o conditie", () => new IfNode());
        Item("🔁  Repeta", "De N ori, cat timp sau pana cand", () => new LoopNode());
        Item("🛡  Incearca / La eroare", "Prinde erorile fara sa opreasca rutina", () => new TryNode());
        Item("💬  Intrebare", "Intreaba utilizatorul, cu butoane personalizate", () => new QuestionNode());
        Item("⏏  Iesi din bucla", "Opreste bucla curenta / sari la urmatoarea repetare", () => new BreakNode());
        Item("⛔  Opreste rutina", "Opreste rutina (cu sau fara eroare)", () => new StopNode());

        Group("Date (Excel si variabile)");
        Item("📊  Pentru fiecare rand Excel", "Repeta pasii pentru fiecare rand dintr-un fisier Excel", () => new ForEachRowNode());
        Item("📝  Scrie in Excel", "Scrie in randul curent (in interiorul buclei Excel)", () => new WriteExcelNode());
        Item("✎  Variabila", "Seteaza / modifica o variabila", () => new SetVariableNode());

        Group("Organizare");
        Item("📁  Grup", "Grupeaza pasi (doar pentru ordine)", () => new GroupNode());
        Item("🗒  Log", "Scrie un mesaj in log", () => new LogNode { Message = "" });
    }

    private void InsertNode(RprNode node)
    {
        // 1. Unde: in ramura selectata, dupa pasul selectat, sau la final
        List<RprNode> target;
        int index;
        if (_selected?.IsBranch == true)
        {
            target = _selected.OwnerList;
            index = target.Count;
        }
        else if (_selected?.Node != null)
        {
            target = _selected.OwnerList;
            index = target.IndexOf(_selected.Node) + 1;
        }
        else
        {
            target = _routine.Steps;
            index = target.Count;
        }

        // 2. Containerele noi primesc ramurile goale gata de umplut
        target.Insert(index, node);
        MarkDirty();
        RebuildTree(node);
    }

    // =========================================================
    // Arborele
    // =========================================================
    private void RebuildTree(RprNode? select)
    {
        var collapsed = _items.Values.Where(i => !i.IsExpanded && i.Node != null).Select(i => i.Node!.Id).ToHashSet();
        TreeItems.Clear();
        _items.Clear();
        foreach (var n in _routine.Steps)
            TreeItems.Add(BuildItem(n, _routine.Steps, null, collapsed));

        if (select != null && _items.TryGetValue(select.Id, out var item))
        {
            for (var p = item.Parent; p != null; p = p.Parent) p.IsExpanded = true;
            item.IsSelected = true;
            _selected = item;
        }
        else _selected = null;
        UpdateTitles();
    }

    private NodeItem BuildItem(RprNode node, List<RprNode> owner, NodeItem? parent, HashSet<string> collapsed)
    {
        var item = new NodeItem(node, owner, null, parent) { IsExpanded = !collapsed.Contains(node.Id) };
        _items[node.Id] = item;
        if (node is IContainerNode c)
        {
            var branches = c.Branches.ToList();
            foreach (var (name, list) in branches)
            {
                // Un singur "Pasi": copiii direct sub nod (fara element-ramura in plus)
                NodeItem holder = item;
                if (branches.Count > 1)
                {
                    holder = new NodeItem(null, list, name, item);
                    item.Children.Add(holder);
                }
                else
                {
                    var b = new NodeItem(null, list, "↳ " + name, item);
                    if (list.Count == 0) item.Children.Add(b); // ramura goala ramane selectabila
                }
                foreach (var child in list)
                    holder.Children.Add(BuildItem(child, list, holder, collapsed));
            }
        }
        return item;
    }

    private void Tree_SelectedItemChanged(object sender, RoutedPropertyChangedEventArgs<object> e)
    {
        _selected = e.NewValue as NodeItem;
        if (_selected?.Node != null) ShowProperties(_selected.Node);
        else if (_selected?.IsBranch == true)
        {
            PropertiesHost.Children.Clear();
            PropertiesHost.Children.Add(Ui.Text($"↳ Ramura \"{_selected.Branch}\"", 16, true, "AccentBrush"));
            PropertiesHost.Children.Add(Ui.Hint("Click pe un bloc din stanga ca sa adaugi un pas IN aceasta ramura."));
        }
        else ShowProperties(_routine);
    }

    private void ShowProperties(object target) => _editor.Show(PropertiesHost, target);

    private void Tree_PreviewKeyDown(object sender, KeyEventArgs e)
    {
        bool ctrl = Keyboard.Modifiers.HasFlag(ModifierKeys.Control);
        if (e.OriginalSource is TextBox) return;
        switch (e.Key)
        {
            case Key.Delete: Delete_Click(sender, e); e.Handled = true; break;
            case Key.Space:  ToggleEnabled_Click(sender, e); e.Handled = true; break;
            case Key.Up when ctrl:   MoveUp_Click(sender, e); e.Handled = true; break;
            case Key.Down when ctrl: MoveDown_Click(sender, e); e.Handled = true; break;
            case Key.D when ctrl:    Duplicate_Click(sender, e); e.Handled = true; break;
        }
    }

    private void MoveUp_Click(object sender, RoutedEventArgs e) => Move(-1);
    private void MoveDown_Click(object sender, RoutedEventArgs e) => Move(+1);

    private void Move(int delta)
    {
        if (_selected?.Node is not { } node) return;
        var list = _selected.OwnerList;
        int i = list.IndexOf(node), j = i + delta;
        if (i < 0 || j < 0 || j >= list.Count) return;
        (list[i], list[j]) = (list[j], list[i]);
        MarkDirty();
        RebuildTree(node);
    }

    private void Delete_Click(object sender, RoutedEventArgs e)
    {
        if (_selected?.Node is not { } node) return;
        int inner = node is IContainerNode ? Routine.Flatten(new[] { node }).Count() - 1 : 0;
        if (inner > 0 && MessageBox.Show(this, $"Stergi \"{node.Title}\" impreuna cu cei {inner} pasi din interior?",
                "Confirmare", MessageBoxButton.YesNo, MessageBoxImage.Question) != MessageBoxResult.Yes) return;

        var list = _selected.OwnerList;
        int i = list.IndexOf(node);
        list.Remove(node);
        MarkDirty();
        RebuildTree(list.Count == 0 ? null : list[Math.Min(i, list.Count - 1)]);
    }

    private void Duplicate_Click(object sender, RoutedEventArgs e)
    {
        if (_selected?.Node is not { } node) return;
        var json = JsonSerializer.Serialize<RprNode>(node, RprJson.Options);
        var copy = JsonSerializer.Deserialize<RprNode>(json, RprJson.Options)!;
        foreach (var n in Routine.Flatten(new[] { copy })) n.Id = Guid.NewGuid().ToString("N")[..10];
        var list = _selected.OwnerList;
        list.Insert(list.IndexOf(node) + 1, copy);
        MarkDirty();
        RebuildTree(copy);
    }

    private void ToggleEnabled_Click(object sender, RoutedEventArgs e)
    {
        if (_selected?.Node is not { } node) return;
        node.Enabled = !node.Enabled;
        _selected.Refresh();
        MarkDirty();
        ShowProperties(node);
    }

    private void RoutineSettings_Click(object sender, RoutedEventArgs e)
    {
        if (_selected != null) _selected.IsSelected = false;
        _selected = null;
        ShowProperties(_routine);
    }

    // =========================================================
    // Object Repository (lista din stanga)
    // =========================================================
    private void RefreshObjects()
    {
        var filter = ObjectFilter?.Text?.Trim() ?? "";
        ObjectList.ItemsSource = _repo.Objects
            .Where(o => filter.Length == 0 || o.Name.Contains(filter, StringComparison.OrdinalIgnoreCase)
                        || o.CapturedText.Contains(filter, StringComparison.OrdinalIgnoreCase))
            .OrderBy(o => o.Technology).ThenBy(o => o.Name)
            .ToList();
    }

    private void ObjectFilter_TextChanged(object sender, TextChangedEventArgs e) => RefreshObjects();

    private async void ObjShow_Click(object sender, RoutedEventArgs e)
    {
        if (ObjectList.SelectedItem is UiObject o) await HighlightObjectAsync(o.Name);
    }

    private void ObjEdit_Click(object sender, RoutedEventArgs e)
    {
        if (ObjectList.SelectedItem is not UiObject o) return;

        // editam o copie: "Anuleaza" nu lasa modificari pe jumatate
        var copy = JsonSerializer.Deserialize<UiObject>(JsonSerializer.Serialize(o, RprJson.Options), RprJson.Options)!;
        var dlg = new ObjectReviewDialog(copy, _repo, RprPaths.ObjectImages, offerActions: false, editing: true) { Owner = this };
        if (dlg.ShowDialog() != true) return;

        var oldName = o.Name;
        int idx = _repo.Objects.IndexOf(o);
        _repo.Objects[idx] = copy;
        if (!string.Equals(oldName, copy.Name, StringComparison.Ordinal))
            RenameReferences(oldName, copy.Name);
        SaveRepository();
        RefreshObjects();
        RebuildTree(_selected?.Node);
        MarkDirty();
    }

    /// <summary>Dupa redenumirea unui obiect, actualizam toti pasii si conditiile care il folosesc.</summary>
    private void RenameReferences(string oldName, string newName)
    {
        static void FixCondition(Condition c, string o, string n)
        {
            if (string.Equals(c.Target, o, StringComparison.OrdinalIgnoreCase)) c.Target = n;
            foreach (var ch in c.Children) FixCondition(ch, o, n);
        }
        foreach (var node in _routine.AllNodes())
        {
            switch (node)
            {
                case ActionNode a when string.Equals(a.Target, oldName, StringComparison.OrdinalIgnoreCase): a.Target = newName; break;
                case IfNode i: FixCondition(i.Condition, oldName, newName); break;
                case LoopNode l: FixCondition(l.Condition, oldName, newName); break;
                case WaitNode w: FixCondition(w.Condition, oldName, newName); break;
            }
        }
    }

    private void ObjAddStep_Click(object sender, RoutedEventArgs e)
    {
        if (ObjectList.SelectedItem is UiObject o)
            InsertNode(new ActionNode { Action = RprAction.Click, Target = o.Name });
    }

    private void ObjDelete_Click(object sender, RoutedEventArgs e)
    {
        if (ObjectList.SelectedItem is not UiObject o) return;
        int uses = _routine.ReferencedObjects().Count(n => string.Equals(n, o.Name, StringComparison.OrdinalIgnoreCase));
        var msg = uses > 0
            ? $"Obiectul [{o.Name}] e folosit de {uses} pasi din rutina curenta (si poate de alte rutine). Il stergi oricum?"
            : $"Stergi obiectul [{o.Name}]? (Alte rutine salvate il pot folosi.)";
        if (MessageBox.Show(this, msg, "Sterge obiect", MessageBoxButton.YesNo, MessageBoxImage.Warning) != MessageBoxResult.Yes) return;
        _repo.Remove(o);
        SaveRepository();
        RefreshObjects();
        UpdateTitles();
    }

    // =========================================================
    // Spy
    // =========================================================
    private async void SpyWeb_Click(object sender, RoutedEventArgs e) => await SpyAsync(UiTechnology.Web, offerActions: true);
    private async void SpySap_Click(object sender, RoutedEventArgs e) => await SpyAsync(UiTechnology.Sap, offerActions: true);
    private async void SpyDesktop_Click(object sender, RoutedEventArgs e) => await SpyAsync(UiTechnology.Desktop, offerActions: true);

    private async Task<bool> EnsureBrowserAsync(UiTechnology tech)
    {
        bool open = tech == UiTechnology.Web ? _drivers.Web.IsOpen : _drivers.Selenium.IsOpen;
        if (open) return true;
        var url = InputBox.Ask(this, "Deschide browserul", "Browserul nu e deschis. La ce adresa sa-l deschid?", "https://");
        if (string.IsNullOrWhiteSpace(url)) return false;
        SetStatus($"Pornesc {_settings.Browser}...");
        if (tech == UiTechnology.Web) await _drivers.Web.OpenAsync(url, CancellationToken.None);
        else await Task.Run(() => _drivers.Selenium.Open(url));
        return true;
    }

    private async Task<UiObject?> SpyAsync(UiTechnology tech, bool offerActions)
    {
        if (_busy) { SetStatus("Asteapta sa se termine operatia curenta."); return null; }
        _busy = true;
        SpyHintWindow? hint = null;
        var oldState = WindowState;
        try
        {
            // 1. Pregatire
            ISpyCapable spy;
            if (tech is UiTechnology.Web or UiTechnology.WebSelenium)
            {
                if (!await EnsureBrowserAsync(tech)) return null;
                spy = tech == UiTechnology.Web ? _drivers.Web : _drivers.Selenium;
                SetStatus("SPY WEB: du mouse-ul peste element in browser (se contureaza verde) si da CLICK ca sa-l capturezi. Esc = anulare.");
            }
            else
            {
                spy = tech == UiTechnology.Sap ? _drivers.Sap : _drivers.Desktop;
                hint = new SpyHintWindow(tech == UiTechnology.Sap
                    ? "🎯 SPY SAP: mouse peste element (contur rosu SAP)  ·  F2 = captureaza  ·  Esc = anuleaza"
                    : "🎯 SPY DESKTOP: mouse peste element (contur verde)  ·  F2 = captureaza  ·  Esc = anuleaza");
                hint.Show();
                WindowState = WindowState.Minimized;
            }

            // 2. Capturare
            var obj = await spy.CaptureObjectAsync(new SpyOptions
            {
                ScreenshotFolder = RprPaths.ObjectImages,
                Hint = "Click = captureaza · Esc = anuleaza",
            }, CancellationToken.None);

            hint?.Close();
            hint = null;
            WindowState = oldState == WindowState.Minimized ? WindowState.Normal : oldState;
            Activate();

            if (obj == null) { SetStatus("Spy anulat."); return null; }

            // 3. Exista deja?
            var same = FindSameObject(obj);
            if (same != null)
            {
                var a = ChoiceDialog.Ask(this, "Obiect existent",
                    $"Elementul e deja in repository ca [{same.Name}]. Il folosesti pe acela?",
                    new[] { "Foloseste existentul", "Salveaza ca obiect nou", "Anuleaza" });
                if (a == "Anuleaza") return null;
                if (a == "Foloseste existentul")
                {
                    if (offerActions) InsertNode(new ActionNode { Action = RprAction.Click, Target = same.Name });
                    return same;
                }
            }

            // 4. Verificare + nume
            var dlg = new ObjectReviewDialog(obj, _repo, RprPaths.ObjectImages, offerActions) { Owner = this };
            if (dlg.ShowDialog() != true) { SetStatus("Obiect nesalvat."); return null; }

            _repo.Add(obj);
            SaveRepository();
            RefreshObjects();
            UpdateTitles();
            SetStatus($"Obiect salvat: [{obj.Name}] — {obj.Locators.Count(l => l.Enabled)} locatori activi.");

            // 5. Pas creat direct
            switch (dlg.Result)
            {
                case ObjectReviewResult.SaveAndClick:
                    InsertNode(new ActionNode { Action = RprAction.Click, Target = obj.Name });
                    break;
                case ObjectReviewResult.SaveAndType:
                    InsertNode(new ActionNode { Action = RprAction.TypeText, Target = obj.Name });
                    break;
                case ObjectReviewResult.SaveAndRead:
                    InsertNode(new ActionNode { Action = RprAction.ReadText, Target = obj.Name, OutputVariable = obj.Name.Split('_').Last() });
                    break;
            }
            return obj;
        }
        catch (Exception ex)
        {
            ShowError("Spy nu a putut porni", ex);
            return null;
        }
        finally
        {
            hint?.Close();
            if (WindowState == WindowState.Minimized) WindowState = WindowState.Normal;
            _busy = false;
        }
    }

    private UiObject? FindSameObject(UiObject obj)
    {
        var best = obj.Locators.FirstOrDefault(l => l.Enabled);
        if (best == null) return null;
        return _repo.Objects.FirstOrDefault(o =>
            o.Technology == obj.Technology &&
            o.FramePath.SequenceEqual(obj.FramePath) &&
            o.Locators.Any(l => l.Enabled && l.Kind == best.Kind && l.Value == best.Value));
    }

    // =========================================================
    // Recorder web
    // =========================================================
    private async void Record_Click(object sender, RoutedEventArgs e)
    {
        try
        {
            if (_recording)
            {
                await _drivers.Web.StopRecordingAsync();
                SetRecording(false);
                return;
            }
            if (_busy) return;
            if (!await EnsureBrowserAsync(UiTechnology.Web)) return;

            await _drivers.Web.StartRecordingAsync(
                rec => Dispatcher.InvokeAsync(() => AddRecorded(rec)),
                new SpyOptions { Hint = "INREGISTRARE · Esc = stop" },
                CancellationToken.None);
            SetRecording(true);
            SetStatus("INREGISTRARE: lucreaza normal in browser — fiecare click, text completat sau optiune aleasa devine un pas. Esc in browser sau butonul rosu = stop.");
        }
        catch (Exception ex)
        {
            ShowError("Inregistrarea nu a putut porni", ex);
            SetRecording(false);
        }
    }

    private void SetRecording(bool on)
    {
        _recording = on;
        BtnRecord.Content = on ? "⏹ Opreste inregistrarea" : "⏺ Inregistreaza Web";
    }

    private void AddRecorded(RecordedAction rec)
    {
        var obj = FindSameObject(rec.Target) ?? _repo.Add(rec.Target);
        SaveRepository();
        RefreshObjects();

        // scrierea repetata in acelasi camp = un singur pas cu valoarea finala
        if (rec.Action == RprAction.TypeText && _selected?.Node is ActionNode last &&
            last.Action == RprAction.TypeText && last.Target == obj.Name)
        {
            last.Value = rec.Value;
            _selected.Refresh();
            ShowProperties(last);
            MarkDirty();
            return;
        }
        InsertNode(new ActionNode { Action = rec.Action, Target = obj.Name, Value = rec.Value });
    }

    private void OnDriverInfo(string msg)
    {
        SetStatus(msg);
        if (msg.StartsWith("Inregistrare oprita", StringComparison.Ordinal)) SetRecording(false);
    }

    // =========================================================
    // Rulare
    // =========================================================
    private async void Run_Click(object sender, RoutedEventArgs e) => await RunAsync(stepMode: false);

    private async void Step_Click(object sender, RoutedEventArgs e)
    {
        if (_engine?.IsRunning == true)
        {
            _engine.StepMode = true;
            _engine.StepOnce();
            return;
        }
        await RunAsync(stepMode: true);
    }

    private void Pause_Click(object sender, RoutedEventArgs e) => TogglePause();

    private void Stop_Click(object sender, RoutedEventArgs e) => _engine?.Stop();

    private void TogglePause()
    {
        if (_engine?.IsRunning != true) return;
        if (_engine.IsPaused) { _engine.StepMode = false; _engine.Resume(); }
        else _engine.Pause();
        bool paused = _engine.IsPaused;
        BtnPause.Content = paused ? "▶ Reluare" : "⏸ Pauza";
        _runControl?.SetPaused(paused);
        SetStatus(paused ? "PAUZA — Reluare sau Pas cu pas." : "Rulare reluata.");
    }

    private async Task RunAsync(bool stepMode)
    {
        if (_busy || _engine?.IsRunning == true) return;
        if (_recording) { await _drivers.Web.StopRecordingAsync(); SetRecording(false); }
        if (_routine.Steps.Count == 0)
        {
            MessageBox.Show(this, "Rutina nu are pasi. Adauga pasi din stanga sau deschide un exemplu (📚 Exemple).", "Rutina goala");
            return;
        }

        _busy = true;
        foreach (var i in _items.Values) i.State = NodeRunState.None;
        _log.Clear();
        _logEntries.Clear();

        _engine = new RprEngine(_repo, _drivers, new StudioRunHost(this), RprPaths.Output) { StepMode = stepMode };
        BtnRun.IsEnabled = false;
        BtnPause.IsEnabled = true;
        BtnStop.IsEnabled = true;
        BtnStep.Content = "⏭ Pasul urmator";

        _runControl = new RunControlWindow();
        _runControl.PauseResumeRequested += TogglePause;
        _runControl.StepRequested += () => { if (_engine != null) { _engine.StepMode = true; _engine.StepOnce(); } };
        _runControl.StopRequested += () => _engine?.Stop();
        _runControl.Show();
        if (_settings.MinimizeOnRun && !stepMode) WindowState = WindowState.Minimized;

        SetStatus(stepMode ? "PAS CU PAS: apasa \"Pasul urmator\" pentru fiecare pas." : "Rulez...");
        RunResult result;
        try
        {
            var engine = _engine;
            var routine = _routine;
            result = await Task.Run(() => engine.RunAsync(routine));
        }
        catch (Exception ex)
        {
            result = new RunResult { Success = false, Message = ex.Message };
        }
        finally
        {
            _runControl?.Close();
            _runControl = null;
            BtnRun.IsEnabled = true;
            BtnPause.IsEnabled = false;
            BtnStop.IsEnabled = false;
            BtnPause.Content = "⏸ Pauza";
            BtnStep.Content = "⏭ Pas cu pas";
            _busy = false;
            if (WindowState == WindowState.Minimized) WindowState = WindowState.Normal;
            Activate();
        }

        ShowVariables(_engine.LastVariables);
        SetStatus((result.Success ? "✔ " : result.Cancelled ? "⏹ " : "✖ ") + result.Message);
        if (!result.Success && !result.Cancelled)
            ChoiceDialog.Ask(this, "Rutina oprita", result.Message, new[] { "OK" },
                "Detaliile sunt in Log (randurile rosii). Capturile de ecran ale erorilor: " + Path.Combine(RprPaths.Output, "erori"));
    }

    private void ShowVariables(IReadOnlyDictionary<string, string> vars) =>
        VarList.ItemsSource = vars.OrderBy(v => v.Key).ToList();

    /// <summary>Legatura motor -> interfata. Motorul ruleaza pe alt fir: totul trece prin Dispatcher.</summary>
    private sealed class StudioRunHost : IRunHost
    {
        private readonly StudioWindow _w;
        private NodeItem? _running;

        public StudioRunHost(StudioWindow w) => _w = w;

        public void Log(RunLogEntry entry) => _w.Dispatcher.InvokeAsync(() =>
        {
            _w._logEntries.Add(entry);
            _w._log.Add(new LogRow { Entry = entry });
            if (_w._log.Count > 3000) _w._log.RemoveAt(0);
            _w.LogList.ScrollIntoView(_w._log[^1]);
        });

        public void NodeStarted(RprNode node) => _w.Dispatcher.InvokeAsync(() =>
        {
            if (_running?.State == NodeRunState.Running) _running.State = NodeRunState.None;
            if (_w._items.TryGetValue(node.Id, out var item))
            {
                item.State = NodeRunState.Running;
                _running = item;
            }
            _w._runControl?.SetStatus(node.Title);
            _w.StatusText.Text = "▶ " + node.Title;
        });

        public void NodeFinished(RprNode node, bool success) => _w.Dispatcher.InvokeAsync(() =>
        {
            if (_w._items.TryGetValue(node.Id, out var item))
                item.State = success ? NodeRunState.Ok : NodeRunState.Error;
        });

        public Task<string> AskAsync(string title, string text, IReadOnlyList<string> buttons, CancellationToken ct) =>
            _w.Dispatcher.InvokeAsync(() => ChoiceDialog.Ask(_w, title, text, buttons)).Task;

        public async Task<ErrorDecision> AskOnErrorAsync(RprNode node, string error, bool insideExcelLoop, CancellationToken ct)
        {
            var buttons = new List<string> { "Reincearca", "Sari pasul" };
            if (insideExcelLoop) buttons.Add("Sari randul");
            buttons.Add("Opreste");
            var answer = await _w.Dispatcher.InvokeAsync(() =>
                ChoiceDialog.Ask(_w, "Pasul a esuat", $"Pasul \"{node.Title}\" a esuat.", buttons, error)).Task;
            return answer switch
            {
                "Reincearca" => ErrorDecision.Retry,
                "Sari pasul" => ErrorDecision.Skip,
                "Sari randul" => ErrorDecision.SkipRow,
                _ => ErrorDecision.Stop,
            };
        }

        public Func<AutoPilotDC.Models.StepModel, CancellationToken, Task<(bool Success, string Error)>>? LegacyExecutor =>
            _w._legacyDesktop == null ? null : (step, ct) => _w._legacyDesktop.ExecuteStepAsync(step, ct);
    }

    // =========================================================
    // Bara de unelte
    // =========================================================
    private void New_Click(object sender, RoutedEventArgs e)
    {
        if (ConfirmDiscard()) NewRoutine();
    }

    private void Open_Click(object sender, RoutedEventArgs e)
    {
        if (!ConfirmDiscard()) return;
        var dlg = new OpenFileDialog
        {
            Filter = "Rutine (*.rpr.json, *.json)|*.rpr.json;*.json|Toate|*.*",
            InitialDirectory = RprPaths.Routines,
        };
        if (dlg.ShowDialog(this) != true) return;
        try { OpenRoutine(dlg.FileName); }
        catch (Exception ex) { ShowError("Rutina nu a putut fi deschisa", ex); }
    }

    private void Save_Click(object sender, RoutedEventArgs e) => SaveRoutine(false);
    private void SaveAs_Click(object sender, RoutedEventArgs e) => SaveRoutine(true);

    private void Examples_Click(object sender, RoutedEventArgs e)
    {
        try
        {
            var examples = ExampleRoutines.Install(_repo);
            SaveRepository();
            RefreshObjects();
            var picked = ExamplePickerDialog.Pick(this, examples);
            if (picked != null && ConfirmDiscard()) OpenRoutine(picked);
        }
        catch (Exception ex)
        {
            ShowError("Exemplele nu au putut fi create", ex);
        }
    }

    private void Highlight_Changed(object sender, RoutedEventArgs e)
    {
        bool v = ChkHighlight.IsChecked == true;
        if (_routine.Settings.HighlightBeforeAction == v) return;
        _routine.Settings.HighlightBeforeAction = v;
        MarkDirty();
    }

    private void Schedule_Click(object sender, RoutedEventArgs e)
    {
        if (_dirty || _routinePath == null)
        {
            if (MessageBox.Show(this, "Rutina trebuie salvata inainte de programare. Salvez acum?", "Programare",
                    MessageBoxButton.YesNo) != MessageBoxResult.Yes) return;
            if (!SaveRoutine(false)) return;
        }
        new ScheduleDialog(_routinePath!, _routine.Name) { Owner = this }.ShowDialog();
    }

    private async void Settings_Click(object sender, RoutedEventArgs e)
    {
        var w = new Window { Title = "Setari Studio", Width = 520, SizeToContent = SizeToContent.Height, Owner = this, WindowStartupLocation = WindowStartupLocation.CenterOwner, ResizeMode = ResizeMode.NoResize };
        Ui.Themed(w);
        var root = new StackPanel { Margin = new Thickness(16) };

        root.Children.Add(Ui.Caption("Browser pentru Web"));
        var browser = new ComboBox();
        foreach (var (k, label) in new[]
                 {
                     (AutoPilotDC.Drivers.Web.BrowserKind.Edge, "Microsoft Edge (recomandat)"),
                     (AutoPilotDC.Drivers.Web.BrowserKind.Chrome, "Google Chrome"),
                     (AutoPilotDC.Drivers.Web.BrowserKind.Chromium, "Chromium (descarcat de Playwright)"),
                     (AutoPilotDC.Drivers.Web.BrowserKind.Firefox, "Firefox (descarcat de Playwright)"),
                 })
        {
            var item = new ComboBoxItem { Content = label, Tag = k };
            browser.Items.Add(item);
            if (k == _settings.Browser) browser.SelectedItem = item;
        }
        root.Children.Add(browser);
        root.Children.Add(Ui.Hint("Browserul foloseste un profil separat, pastrat intre rulari: te autentifici o data (SSO), apoi ramai logat."));

        var headless = new CheckBox { Content = "Browser invizibil (headless) — doar pentru rutine verificate", IsChecked = _settings.Headless, Margin = new Thickness(0, 10, 0, 0) };
        root.Children.Add(headless);
        var minimize = new CheckBox { Content = "Minimizeaza Studio la rulare (ramane bara plutitoare de control)", IsChecked = _settings.MinimizeOnRun, Margin = new Thickness(0, 6, 0, 0) };
        root.Children.Add(minimize);

        root.Children.Add(Ui.Caption("Foldere"));
        root.Children.Add(Ui.Hint($"Lucru: {RprPaths.Root}"));
        var row = new WrapPanel { Margin = new Thickness(0, 4, 0, 0) };
        row.Children.Add(Ui.Btn("📁 Deschide folderul de lucru", "NeutralButtonStyle", (_, _) => OpenFolder(RprPaths.Root)));
        row.Children.Add(Ui.Btn("🧹 Sterge profilul browserului (logout)", "NeutralButtonStyle", async (_, _) =>
        {
            await _drivers.ResetWebAsync();
            try { Directory.Delete(RprPaths.BrowserProfile, true); MessageBox.Show(w, "Profil sters."); }
            catch (Exception ex) { MessageBox.Show(w, ex.Message); }
        }));
        root.Children.Add(row);

        var ok = Ui.Btn("Salveaza", "SuccessButtonStyle", (_, _) => w.DialogResult = true);
        ok.HorizontalAlignment = HorizontalAlignment.Right;
        ok.Margin = new Thickness(0, 14, 0, 0);
        root.Children.Add(ok);
        w.Content = root;

        if (w.ShowDialog() != true) return;
        var newBrowser = browser.SelectedItem is ComboBoxItem { Tag: AutoPilotDC.Drivers.Web.BrowserKind b } ? b : _settings.Browser;
        bool browserChanged = newBrowser != _settings.Browser || headless.IsChecked != _settings.Headless;
        _settings.Browser = newBrowser;
        _settings.Headless = headless.IsChecked == true;
        _settings.MinimizeOnRun = minimize.IsChecked == true;
        _settings.Save();
        if (browserChanged) await _drivers.ResetWebAsync();
        UpdateTitles();
    }

    private void Help_Click(object sender, RoutedEventArgs e) => HelpWindow.ShowGuide(this);

    private void ExportLog_Click(object sender, RoutedEventArgs e)
    {
        if (_logEntries.Count == 0) { SetStatus("Logul e gol."); return; }
        var dlg = new SaveFileDialog
        {
            Filter = "Excel|*.xlsx",
            InitialDirectory = RprPaths.Output,
            FileName = $"Log_{ObjectRepository.Sanitize(_routine.Name)}_{DateTime.Now:yyyyMMdd_HHmm}.xlsx",
        };
        if (dlg.ShowDialog(this) != true) return;
        try
        {
            RunLogExporter.ExportXlsx(_logEntries, dlg.FileName);
            SetStatus($"Log exportat: {dlg.FileName}");
        }
        catch (Exception ex) { ShowError("Exportul a esuat", ex); }
    }

    private void OpenOutput_Click(object sender, RoutedEventArgs e) => OpenFolder(RprPaths.Output);

    private void ClearLog_Click(object sender, RoutedEventArgs e)
    {
        _log.Clear();
        _logEntries.Clear();
    }

    private static void OpenFolder(string path)
    {
        try { Process.Start(new ProcessStartInfo("explorer.exe", $"\"{path}\"") { UseShellExecute = true }); }
        catch (Exception) { }
    }

    // =========================================================
    // Taste + inchidere
    // =========================================================
    private void Window_PreviewKeyDown(object sender, KeyEventArgs e)
    {
        bool ctrl = Keyboard.Modifiers.HasFlag(ModifierKeys.Control);
        if (ctrl && e.Key == Key.S) { SaveRoutine(false); e.Handled = true; }
        else if (ctrl && e.Key == Key.N) { New_Click(sender, e); e.Handled = true; }
        else if (ctrl && e.Key == Key.O) { Open_Click(sender, e); e.Handled = true; }
        else if (e.Key == Key.F5) { Run_Click(sender, e); e.Handled = true; }
        else if (e.Key == Key.F1) { Help_Click(sender, e); e.Handled = true; }
    }

    private async void Window_Closing(object? sender, System.ComponentModel.CancelEventArgs e)
    {
        if (_engine?.IsRunning == true)
        {
            if (MessageBox.Show(this, "O rutina ruleaza. O opresti si inchizi Studio?", "Inchidere",
                    MessageBoxButton.YesNo) != MessageBoxResult.Yes) { e.Cancel = true; return; }
            _engine.Stop();
        }
        if (!ConfirmDiscard()) { e.Cancel = true; return; }
        _runControl?.Close();
        try { await _drivers.DisposeAsync(); } catch (Exception) { }
    }

    // =========================================================
    // Utilitare
    // =========================================================
    private void SetStatus(string text) => StatusText.Text = text;

    private void ShowError(string title, Exception ex)
    {
        SetStatus($"✖ {title}: {ex.Message}");
        ChoiceDialog.Ask(this, title, title, new[] { "OK" }, ex.Message);
    }

    private static string Shorten(string s, int n) => s.Length <= n ? s : s[..n] + "…";
}
