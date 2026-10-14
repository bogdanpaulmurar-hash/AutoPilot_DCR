// ============================================================
// AutoPilot DC v4 — Studio RPR
// StudioDialogs.cs — Ferestre mici construite din cod:
//   Ui (helper stiluri), ChoiceDialog, InputBox, ObjectReviewDialog,
//   SpyHintWindow, RunControlWindow, ScheduleDialog.
// Toate folosesc culorile temei (DynamicResource) => lizibile in ambele teme.
// ============================================================

using System.Diagnostics;
using System.IO;
using System.Runtime.InteropServices;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using System.Windows.Media;
using System.Windows.Media.Imaging;
using System.Windows.Threading;
using AutoPilotDC.Rpr.Model;
using AutoPilotDC.Rpr.Storage;
using Application = System.Windows.Application;
using Brush = System.Windows.Media.Brush;
using Brushes = System.Windows.Media.Brushes;
using Color = System.Windows.Media.Color;
using Button = System.Windows.Controls.Button;
using CheckBox = System.Windows.Controls.CheckBox;
using ComboBox = System.Windows.Controls.ComboBox;
using FontFamily = System.Windows.Media.FontFamily;
using HorizontalAlignment = System.Windows.HorizontalAlignment;
using Image = System.Windows.Controls.Image;
using KeyEventArgs = System.Windows.Input.KeyEventArgs;
using MessageBox = System.Windows.MessageBox;
using Orientation = System.Windows.Controls.Orientation;
using TextBox = System.Windows.Controls.TextBox;
using VerticalAlignment = System.Windows.VerticalAlignment;

namespace AutoPilotDC.UI.Studio;

/// <summary>Helper pentru controale create din cod, cu stilurile temei.</summary>
public static class Ui
{
    public static readonly FontFamily Font = new("Segoe UI");

    public static Button Btn(string text, string style = "PrimaryButtonStyle", RoutedEventHandler? click = null, string? tip = null)
    {
        var b = new Button { Content = text, Margin = new Thickness(3), Padding = new Thickness(10, 5, 10, 5), ToolTip = tip };
        if (Application.Current.TryFindResource(style) is Style s) b.Style = s;
        if (click != null) b.Click += click;
        return b;
    }

    public static TextBlock Text(string text, double size = 13, bool bold = false, string brush = "TextBrush")
    {
        var t = new TextBlock { Text = text, FontFamily = Font, FontSize = size, TextWrapping = TextWrapping.Wrap };
        if (bold) t.FontWeight = FontWeights.SemiBold;
        t.SetResourceReference(TextBlock.ForegroundProperty, brush);
        return t;
    }

    public static TextBlock Caption(string text)
    {
        var t = Text(text, 12, true, "TextDimBrush");
        t.Margin = new Thickness(0, 8, 0, 3);
        return t;
    }

    public static TextBlock Hint(string text)
    {
        var t = Text(text, 11.5, false, "TextMutedBrush");
        t.Margin = new Thickness(0, 2, 0, 2);
        return t;
    }

    public static void Themed(Window w)
    {
        w.SetResourceReference(Window.BackgroundProperty, "BgMainBrush");
        w.SetResourceReference(Window.ForegroundProperty, "TextBrush");
        w.FontFamily = Font;
        w.FontSize = 13;
    }

    public static Border Card(UIElement child, double padding = 10)
    {
        var b = new Border { Child = child, Padding = new Thickness(padding), CornerRadius = new CornerRadius(4), BorderThickness = new Thickness(1), Margin = new Thickness(0, 4, 0, 4) };
        b.SetResourceReference(Border.BackgroundProperty, "BgPanelBrush");
        b.SetResourceReference(Border.BorderBrushProperty, "BorderBrush");
        return b;
    }

    public static Brush Res(string key) => Application.Current.TryFindResource(key) as Brush ?? Brushes.Gray;
}

// ─────────────────────────────────────────────────────────────
// Intrebare cu butoane personalizate
// ─────────────────────────────────────────────────────────────
public sealed class ChoiceDialog : Window
{
    public string Answer { get; private set; } = "";

    private ChoiceDialog(string title, string text, IReadOnlyList<string> buttons, string? detail)
    {
        Ui.Themed(this);
        Title = title;
        SizeToContent = SizeToContent.WidthAndHeight;
        MinWidth = 380;
        MaxWidth = 720;
        WindowStartupLocation = WindowStartupLocation.CenterScreen;
        Topmost = true;
        ResizeMode = ResizeMode.NoResize;

        var root = new StackPanel { Margin = new Thickness(18) };
        root.Children.Add(Ui.Text(text, 14, true));
        if (!string.IsNullOrWhiteSpace(detail))
        {
            var d = new TextBox { Text = detail, IsReadOnly = true, TextWrapping = TextWrapping.Wrap, MaxHeight = 220, Margin = new Thickness(0, 10, 0, 0), VerticalScrollBarVisibility = ScrollBarVisibility.Auto };
            root.Children.Add(d);
        }

        var row = new WrapPanel { HorizontalAlignment = HorizontalAlignment.Right, Margin = new Thickness(0, 16, 0, 0) };
        foreach (var label in buttons)
        {
            var lower = label.ToLowerInvariant();
            var style = lower.StartsWith("opr") || lower.StartsWith("stop") ? "DangerButtonStyle"
                      : lower.StartsWith("sari") ? "NeutralButtonStyle"
                      : "SuccessButtonStyle";
            var captured = label;
            row.Children.Add(Ui.Btn(label, style, (_, _) => { Answer = captured; DialogResult = true; }));
        }
        root.Children.Add(row);
        Content = root;
    }

    public static string Ask(Window? owner, string title, string text, IReadOnlyList<string> buttons, string? detail = null)
    {
        var d = new ChoiceDialog(title, text, buttons, detail);
        if (owner != null && owner.IsVisible && owner.WindowState != WindowState.Minimized) d.Owner = owner;
        d.ShowDialog();
        return string.IsNullOrEmpty(d.Answer) ? buttons.LastOrDefault() ?? "" : d.Answer;
    }
}

// ─────────────────────────────────────────────────────────────
// Caseta de text
// ─────────────────────────────────────────────────────────────
public sealed class InputBox : Window
{
    private readonly TextBox _box;

    private InputBox(string title, string prompt, string initial)
    {
        Ui.Themed(this);
        Title = title;
        Width = 520;
        SizeToContent = SizeToContent.Height;
        WindowStartupLocation = WindowStartupLocation.CenterOwner;
        ResizeMode = ResizeMode.NoResize;

        var root = new StackPanel { Margin = new Thickness(16) };
        root.Children.Add(Ui.Text(prompt));
        _box = new TextBox { Text = initial, Margin = new Thickness(0, 8, 0, 0) };
        _box.KeyDown += (_, e) => { if (e.Key == Key.Enter) DialogResult = true; };
        root.Children.Add(_box);
        var row = new StackPanel { Orientation = Orientation.Horizontal, HorizontalAlignment = HorizontalAlignment.Right, Margin = new Thickness(0, 12, 0, 0) };
        row.Children.Add(Ui.Btn("OK", "SuccessButtonStyle", (_, _) => DialogResult = true));
        row.Children.Add(Ui.Btn("Anuleaza", "NeutralButtonStyle", (_, _) => DialogResult = false));
        root.Children.Add(row);
        Content = root;
        Loaded += (_, _) => { _box.Focus(); _box.SelectAll(); };
    }

    public static string? Ask(Window owner, string title, string prompt, string initial = "")
    {
        var d = new InputBox(title, prompt, initial) { Owner = owner };
        return d.ShowDialog() == true ? d._box.Text.Trim() : null;
    }
}

// ─────────────────────────────────────────────────────────────
// Verificarea obiectului capturat cu Spy
// ─────────────────────────────────────────────────────────────
public enum ObjectReviewResult { Cancel, Save, SaveAndClick, SaveAndType, SaveAndRead }

public sealed class ObjectReviewDialog : Window
{
    public ObjectReviewResult Result { get; private set; } = ObjectReviewResult.Cancel;

    private readonly UiObject _obj;
    private readonly ObjectRepository _repo;
    private readonly TextBox _name;
    private readonly TextBox _context;
    private readonly TextBox _description;

    public ObjectReviewDialog(UiObject obj, ObjectRepository repo, string imagesFolder, bool offerActions, bool editing = false)
    {
        _obj = obj;
        _repo = repo;
        Ui.Themed(this);
        Title = editing ? $"Editeaza obiectul {obj.Name}" : "Obiect capturat — verifica si salveaza";
        Width = 760;
        Height = 640;
        WindowStartupLocation = WindowStartupLocation.CenterScreen;
        Topmost = true;

        var root = new DockPanel { Margin = new Thickness(14) };

        // ── butoane jos ──
        var buttons = new WrapPanel { HorizontalAlignment = HorizontalAlignment.Right, Margin = new Thickness(0, 10, 0, 0) };
        DockPanel.SetDock(buttons, Dock.Bottom);
        if (offerActions)
        {
            buttons.Children.Add(Ui.Btn("Salveaza + pas Click", "SuccessButtonStyle", (_, _) => Finish(ObjectReviewResult.SaveAndClick)));
            buttons.Children.Add(Ui.Btn("Salveaza + pas Scrie text", "SuccessButtonStyle", (_, _) => Finish(ObjectReviewResult.SaveAndType)));
            buttons.Children.Add(Ui.Btn("Salveaza + pas Citeste", "SuccessButtonStyle", (_, _) => Finish(ObjectReviewResult.SaveAndRead)));
        }
        buttons.Children.Add(Ui.Btn(editing ? "Salveaza modificarile" : "Doar salveaza obiectul", "PrimaryButtonStyle", (_, _) => Finish(ObjectReviewResult.Save)));
        buttons.Children.Add(Ui.Btn("Anuleaza", "NeutralButtonStyle", (_, _) => { Result = ObjectReviewResult.Cancel; DialogResult = false; }));
        root.Children.Add(buttons);

        var stack = new StackPanel();
        var scroll = new ScrollViewer { Content = stack, VerticalScrollBarVisibility = ScrollBarVisibility.Auto };
        root.Children.Add(scroll);

        // ── nume + info ──
        stack.Children.Add(Ui.Caption("Nume obiect (cum il vei alege in pasi)"));
        _name = new TextBox { Text = editing ? obj.Name : repo.MakeUniqueName(obj.Name), FontSize = 15 };
        stack.Children.Add(_name);
        stack.Children.Add(Ui.Hint($"Tehnologie: {obj.Technology}   ·   Tip: {obj.ElementType}   ·   Text capturat: \"{Shorten(obj.CapturedText, 80)}\""));

        stack.Children.Add(Ui.Caption("Context (pagina / fereastra / ecran SAP)"));
        _context = new TextBox { Text = obj.Context };
        stack.Children.Add(_context);
        stack.Children.Add(Ui.Hint(obj.Technology == UiTechnology.Desktop
            ? "Desktop: \"proces:nume.exe\" (recomandat) sau titlul ferestrei ca expresie regulata."
            : "Informativ. Pentru desktop decide in ce ferestre se cauta obiectul."));

        if (obj.FramePath.Count > 0)
            stack.Children.Add(Ui.Hint("In iframe: " + string.Join("  →  ", obj.FramePath)));

        stack.Children.Add(Ui.Caption("Descriere (optional)"));
        _description = new TextBox { Text = obj.Description };
        stack.Children.Add(_description);

        // ── locatori ──
        stack.Children.Add(Ui.Caption("Locatori — incercati in ordine; primul care gaseste un singur element castiga"));
        stack.Children.Add(Ui.Hint("Debifeaza locatorii instabili. Scorul mare = mai stabil. Poti corecta valoarea direct."));
        foreach (var loc in obj.Locators)
        {
            var row = new Grid { Margin = new Thickness(0, 2, 0, 2) };
            row.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(28) });
            row.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(110) });
            row.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
            row.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(50) });

            var captured = loc;
            var chk = new CheckBox { IsChecked = loc.Enabled, VerticalAlignment = VerticalAlignment.Center };
            chk.Checked += (_, _) => captured.Enabled = true;
            chk.Unchecked += (_, _) => captured.Enabled = false;
            var kind = Ui.Text(loc.Kind.ToString(), 12, true, "AccentBrush");
            kind.VerticalAlignment = VerticalAlignment.Center;
            var val = new TextBox { Text = loc.Value };
            val.TextChanged += (_, _) => captured.Value = val.Text;
            var score = Ui.Text(loc.Score.ToString(), 12, false, loc.Score >= 70 ? "SuccessBrush" : loc.Score >= 40 ? "WarningBrush" : "DangerBrush");
            score.HorizontalAlignment = HorizontalAlignment.Center;
            score.VerticalAlignment = VerticalAlignment.Center;

            Grid.SetColumn(chk, 0); Grid.SetColumn(kind, 1); Grid.SetColumn(val, 2); Grid.SetColumn(score, 3);
            row.Children.Add(chk); row.Children.Add(kind); row.Children.Add(val); row.Children.Add(score);
            stack.Children.Add(row);
        }
        if (obj.Locators.Count == 0)
            stack.Children.Add(Ui.Text("Nu s-a putut genera niciun locator pentru acest element.", 13, true, "DangerBrush"));

        // ── captura ──
        var img = Path.Combine(imagesFolder, obj.Screenshot ?? "");
        if (!string.IsNullOrWhiteSpace(obj.Screenshot) && File.Exists(img))
        {
            stack.Children.Add(Ui.Caption("Captura elementului"));
            try
            {
                var bmp = new BitmapImage();
                bmp.BeginInit();
                bmp.CacheOption = BitmapCacheOption.OnLoad; // nu blocam fisierul
                bmp.UriSource = new Uri(img);
                bmp.EndInit();
                stack.Children.Add(new Image { Source = bmp, MaxHeight = 160, HorizontalAlignment = HorizontalAlignment.Left, Stretch = Stretch.Uniform });
            }
            catch (Exception) { }
        }

        Content = root;
        Loaded += (_, _) => { _name.Focus(); _name.SelectAll(); };
    }

    private void Finish(ObjectReviewResult result)
    {
        var name = ObjectRepository.Sanitize(_name.Text);
        if (string.IsNullOrWhiteSpace(name))
        {
            MessageBox.Show(this, "Da un nume obiectului.", "Nume lipsa");
            return;
        }
        if (_repo.Find(name) is { } existing && !ReferenceEquals(existing, _obj))
        {
            MessageBox.Show(this, $"Exista deja un obiect numit \"{name}\". Alege alt nume.", "Nume folosit");
            return;
        }
        if (!_obj.Locators.Any(l => l.Enabled))
        {
            MessageBox.Show(this, "Lasa bifat cel putin un locator.", "Fara locatori");
            return;
        }
        _obj.Name = name;
        _obj.Context = _context.Text.Trim();
        _obj.Description = _description.Text.Trim();
        Result = result;
        DialogResult = true;
    }

    private static string Shorten(string s, int n) => s.Length <= n ? s : s[..n] + "…";
}

// ─────────────────────────────────────────────────────────────
// Indicatie plutitoare in timpul Spy (desktop / SAP)
// ─────────────────────────────────────────────────────────────
public sealed class SpyHintWindow : Window
{
    public SpyHintWindow(string text)
    {
        WindowStyle = WindowStyle.None;
        AllowsTransparency = true;
        Background = Brushes.Transparent;
        Topmost = true;
        ShowActivated = false;
        ShowInTaskbar = false;
        SizeToContent = SizeToContent.WidthAndHeight;
        IsHitTestVisible = false;

        var border = new Border
        {
            Background = new SolidColorBrush(Color.FromRgb(0, 0, 40)),
            BorderBrush = new SolidColorBrush(Color.FromRgb(0, 215, 160)),
            BorderThickness = new Thickness(2),
            CornerRadius = new CornerRadius(6),
            Padding = new Thickness(14, 8, 14, 8),
            Child = new TextBlock { Text = text, Foreground = Brushes.White, FontFamily = Ui.Font, FontSize = 14, FontWeight = FontWeights.SemiBold },
        };
        Content = border;
        Loaded += (_, _) =>
        {
            var wa = SystemParameters.WorkArea;
            Left = wa.Left + (wa.Width - ActualWidth) / 2;
            Top = wa.Top + 12;
        };
    }
}

// ─────────────────────────────────────────────────────────────
// Bara plutitoare de control in timpul rularii
// Ctrl+F11 = Pauza / Reluare, Ctrl+F12 = Stop (functioneaza oriunde)
// ─────────────────────────────────────────────────────────────
public sealed class RunControlWindow : Window
{
    [DllImport("user32.dll")] private static extern short GetAsyncKeyState(int vKey);
    private static bool Down(int vk) => (GetAsyncKeyState(vk) & 0x8000) != 0;

    private readonly TextBlock _status;
    private readonly Button _pause;
    private readonly DispatcherTimer _keys;
    private bool _wasPauseCombo, _wasStopCombo;

    public event Action? PauseResumeRequested;
    public event Action? StepRequested;
    public event Action? StopRequested;

    public RunControlWindow()
    {
        Ui.Themed(this);
        WindowStyle = WindowStyle.ToolWindow;
        Title = "AutoPilot DC — rulare";
        Topmost = true;
        ShowActivated = false;
        SizeToContent = SizeToContent.WidthAndHeight;
        ResizeMode = ResizeMode.NoResize;

        var root = new StackPanel { Margin = new Thickness(8) };
        _status = Ui.Text("Pornire...", 12, true);
        _status.MaxWidth = 420;
        _status.TextTrimming = TextTrimming.CharacterEllipsis;
        _status.TextWrapping = TextWrapping.NoWrap;
        root.Children.Add(_status);

        var row = new StackPanel { Orientation = Orientation.Horizontal, Margin = new Thickness(0, 6, 0, 0) };
        _pause = Ui.Btn("⏸ Pauza", "NeutralButtonStyle", (_, _) => PauseResumeRequested?.Invoke(), "Ctrl+F11");
        row.Children.Add(_pause);
        row.Children.Add(Ui.Btn("⏭ Pas", "NeutralButtonStyle", (_, _) => StepRequested?.Invoke(), "Executa un singur pas (in pauza)"));
        row.Children.Add(Ui.Btn("⏹ STOP", "DangerButtonStyle", (_, _) => StopRequested?.Invoke(), "Ctrl+F12"));
        root.Children.Add(row);
        root.Children.Add(Ui.Hint("Ctrl+F11 pauza/reluare  ·  Ctrl+F12 stop"));
        Content = root;

        Loaded += (_, _) =>
        {
            var wa = SystemParameters.WorkArea;
            Left = wa.Right - ActualWidth - 16;
            Top = wa.Bottom - ActualHeight - 16;
        };

        // Scurtaturi globale prin interogarea tastaturii (fara hook-uri)
        _keys = new DispatcherTimer { Interval = TimeSpan.FromMilliseconds(80) };
        _keys.Tick += (_, _) =>
        {
            bool ctrl = Down(0x11);
            bool pauseCombo = ctrl && Down(0x7A); // F11
            bool stopCombo = ctrl && Down(0x7B);  // F12
            if (pauseCombo && !_wasPauseCombo) PauseResumeRequested?.Invoke();
            if (stopCombo && !_wasStopCombo) StopRequested?.Invoke();
            _wasPauseCombo = pauseCombo;
            _wasStopCombo = stopCombo;
        };
        _keys.Start();
        Closed += (_, _) => _keys.Stop();
    }

    public void SetStatus(string text) => _status.Text = text;

    public void SetPaused(bool paused) => _pause.Content = paused ? "▶ Reluare" : "⏸ Pauza";
}

// ─────────────────────────────────────────────────────────────
// Programare (Windows Task Scheduler)
// ─────────────────────────────────────────────────────────────
public sealed class ScheduleDialog : Window
{
    private readonly ComboBox _freq;
    private readonly TextBox _time;
    private readonly TextBox _date;
    private readonly string _routinePath;
    private readonly string _routineName;

    public ScheduleDialog(string routinePath, string routineName)
    {
        _routinePath = routinePath;
        _routineName = routineName;
        Ui.Themed(this);
        Title = "Programeaza rutina";
        Width = 520;
        SizeToContent = SizeToContent.Height;
        WindowStartupLocation = WindowStartupLocation.CenterOwner;
        ResizeMode = ResizeMode.NoResize;

        var root = new StackPanel { Margin = new Thickness(16) };
        root.Children.Add(Ui.Text($"Rutina: {routineName}", 14, true));
        root.Children.Add(Ui.Hint("Rutina va rula fara Studio, cu logul salvat in folderul de rezultate. " +
                                  "Calculatorul trebuie sa fie pornit si utilizatorul autentificat (rutinele folosesc ecranul)."));

        root.Children.Add(Ui.Caption("Cand"));
        _freq = new ComboBox();
        foreach (var f in new[] { "Zilnic", "In zilele lucratoare (L-V)", "Saptamanal (azi)", "O singura data" })
            _freq.Items.Add(new ComboBoxItem { Content = f });
        _freq.SelectedIndex = 1;
        root.Children.Add(_freq);

        root.Children.Add(Ui.Caption("Ora (HH:mm)"));
        _time = new TextBox { Text = "08:00" };
        root.Children.Add(_time);

        root.Children.Add(Ui.Caption("Data (doar pentru \"O singura data\", zz.ll.aaaa)"));
        _date = new TextBox { Text = DateTime.Today.AddDays(1).ToString("dd.MM.yyyy") };
        root.Children.Add(_date);

        var row = new StackPanel { Orientation = Orientation.Horizontal, HorizontalAlignment = HorizontalAlignment.Right, Margin = new Thickness(0, 14, 0, 0) };
        row.Children.Add(Ui.Btn("Creeaza programarea", "SuccessButtonStyle", (_, _) => Create()));
        row.Children.Add(Ui.Btn("Deschide Task Scheduler", "NeutralButtonStyle", (_, _) => Process.Start(new ProcessStartInfo("taskschd.msc") { UseShellExecute = true })));
        row.Children.Add(Ui.Btn("Inchide", "NeutralButtonStyle", (_, _) => Close()));
        root.Children.Add(row);
        Content = root;
    }

    private void Create()
    {
        if (!TimeSpan.TryParse(_time.Text.Trim(), out var t))
        {
            MessageBox.Show(this, "Ora trebuie sa fie de forma 08:30.", "Ora invalida");
            return;
        }
        var exe = Environment.ProcessPath ?? Process.GetCurrentProcess().MainModule?.FileName ?? "";
        var taskName = "AutoPilotDC\\" + ObjectRepository.Sanitize(_routineName);
        var command = $"\\\"{exe}\\\" --run \\\"{_routinePath}\\\"";
        var st = $"{t.Hours:00}:{t.Minutes:00}";

        string schedule = _freq.SelectedIndex switch
        {
            0 => "/SC DAILY",
            1 => "/SC WEEKLY /D MON,TUE,WED,THU,FRI",
            2 => "/SC WEEKLY",
            _ => DateTime.TryParseExact(_date.Text.Trim(), "dd.MM.yyyy", null, System.Globalization.DateTimeStyles.None, out var d)
                    ? $"/SC ONCE /SD {d:MM\\/dd\\/yyyy}"
                    : "",
        };
        if (schedule == "")
        {
            MessageBox.Show(this, "Data trebuie sa fie de forma 25.12.2026.", "Data invalida");
            return;
        }

        var args = $"/Create /F /TN \"{taskName}\" /TR \"{command}\" {schedule} /ST {st}";
        try
        {
            var psi = new ProcessStartInfo("schtasks.exe", args)
            {
                UseShellExecute = false,
                CreateNoWindow = true,
                RedirectStandardOutput = true,
                RedirectStandardError = true,
            };
            using var p = Process.Start(psi)!;
            var output = p.StandardOutput.ReadToEnd() + p.StandardError.ReadToEnd();
            p.WaitForExit(15000);
            MessageBox.Show(this, p.ExitCode == 0
                    ? $"Programare creata: {taskName}\n{output.Trim()}"
                    : $"Programarea nu a putut fi creata:\n{output.Trim()}\n\nNota: formatul datei pentru /SD depinde de setarile regionale Windows.",
                "Programare");
        }
        catch (Exception ex)
        {
            MessageBox.Show(this, ex.Message, "Eroare schtasks");
        }
    }
}
