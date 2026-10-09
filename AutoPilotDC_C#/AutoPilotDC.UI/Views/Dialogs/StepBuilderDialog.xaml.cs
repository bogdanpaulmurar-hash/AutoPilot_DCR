// ============================================================
// AutoPilot DC v3.9 -> C# WPF .NET 8
// StepBuilderDialog.xaml.cs — Faza 8: Mouse Position Tracker
// Modificat: adaugat MouseTracker in StepBuilderDialog
// Echivalent Python: StepBuilderDialog (ui/dialogs/step_builder.py)
// Dimensiune: 560x660px (marita cu 40px pentru tracker row)
// ============================================================

using System;
using System.Collections.Generic;
using System.Linq;
using System.Windows;
using System.Windows.Controls;
using AutoPilotDC.Models;
using System.Threading.Tasks;

namespace AutoPilotDC.UI.Views.Dialogs;

public partial class StepBuilderDialog : Window
{
    // ── Toate tipurile de pasi (desktop + browser) — identic Python ALL_STEP_TYPES ──
    private static readonly List<string> ALL_STEP_TYPES =
    [
        // Desktop
        "CLICK", "DBLCLICK", "RIGHTCLICK", "KEY", "TYPE",
        "SCROLL", "MOVE", "DELAY", "SCREENSHOT", "QUESTION",
        // Browser
        "browser_open", "browser_navigate", "browser_click",
        "browser_fill", "browser_wait", "browser_screenshot", "browser_close"
    ];

    // ── Step-uri cu coordonate — tracker activ pentru acestea ──
    private static readonly HashSet<string> COORD_STEP_TYPES =
        new(StringComparer.OrdinalIgnoreCase)
        { "CLICK", "DBLCLICK", "RIGHTCLICK", "MOVE", "SCROLL" };

    // ── Faza 8: Mouse Position Tracker ──────────────────────────────────────────
    private System.Threading.Timer? _mouseTracker;
    private volatile bool _trackingActive = false;
    // ────────────────────────────────────────────────────────────────────────────

    public StepModel? ResultStep { get; private set; }

    private readonly StepModel? _editStep;

    public StepBuilderDialog(StepModel? stepToEdit)
    {
        InitializeComponent();
        _editStep = stepToEdit;

        // Populeaza ComboBox cu toate tipurile
        foreach (var t in ALL_STEP_TYPES)
            CmbStepType.Items.Add(t);

        if (_editStep != null)
            LoadStep(_editStep);
        else
        {
            CmbStepType.SelectedIndex = 0;   // CLICK implicit
            UpdateVisiblePanels("CLICK");
        }
    }

    // ── Load step pentru editare ─────────────────────────────────────────────────
    private void LoadStep(StepModel step)
    {
        CmbStepType.SelectedItem = step.StepType;
        TxtDescription.Text      = step.Description;
        TxtX.Text                = step.X.ToString();
        TxtY.Text                = step.Y.ToString();
        CmbButton.SelectedValue  = step.Button;
        TxtKeyCombo.Text         = step.KeyCombo;
        TxtTextInput.Text        = step.TextInput;
        TxtScrollDx.Text         = step.ScrollDx.ToString();
        TxtScrollDy.Text         = step.ScrollDy.ToString();
        TxtQuestionText.Text     = step.QuestionText;
        TxtQuestionButtons.Text  = step.QuestionButtons;
        TxtDelayBefore.Text      = step.DelayBefore.ToString("F2");
        TxtDelayAfter.Text       = step.DelayAfter.ToString("F2");
        TxtMonitorId.Text        = step.MonitorId.ToString();
        ChkSkip.IsChecked        = step.Skip;
        TxtComment.Text          = step.Comment;
        UpdateVisiblePanels(step.StepType);
    }

    // ── SelectionChanged: schimba panelurile SI tracker-ul ──────────────────────
    private void CmbStepType_SelectionChanged(object sender, SelectionChangedEventArgs e)
    {
        if (CmbStepType.SelectedItem is string stepType)
        {
            UpdateVisiblePanels(stepType);

            // Faza 8: porneste/opreste tracker la schimbarea tipului
            if (IsCoordStep(stepType))
                StartMouseTracker();
            else
                StopMouseTracker();
        }
    }

    /// <summary>
    /// Afiseaza/ascunde panelurile in functie de tipul de pas.
    /// Identic Python: StepBuilderDialog._on_type_change()
    /// </summary>
    private void UpdateVisiblePanels(string stepType)
    {
        bool isMouse    = stepType is "CLICK" or "DBLCLICK" or "RIGHTCLICK" or "MOVE";
        bool isKey      = stepType == "KEY";
        bool isType     = stepType == "TYPE";
        bool isScroll   = stepType == "SCROLL";
        bool isQuestion = stepType == "QUESTION";
        bool isBrowser  = stepType.StartsWith("browser_");

        PanelMouse.Visibility    = isMouse    ? Visibility.Visible : Visibility.Collapsed;
        PanelKey.Visibility      = isKey      ? Visibility.Visible : Visibility.Collapsed;
        PanelType.Visibility     = isType     ? Visibility.Visible : Visibility.Collapsed;
        PanelScroll.Visibility   = isScroll   ? Visibility.Visible : Visibility.Collapsed;
        PanelQuestion.Visibility = isQuestion ? Visibility.Visible : Visibility.Collapsed;
        PanelBrowser.Visibility  = isBrowser  ? Visibility.Visible : Visibility.Collapsed;
    }

    // ════════════════════════════════════════════════════════════════════════════
    // FAZA 8 — Mouse Position Tracker
    // Echivalent Python: thread polling la 50ms, afiseaza X/Y live in dialog
    // ════════════════════════════════════════════════════════════════════════════

    /// <summary>
    /// Porneste thread-ul de tracking mouse (polling 50ms).
    /// Thread-safe: toate update-urile UI prin Dispatcher.InvokeAsync().
    /// </summary>
    private void StartMouseTracker()
    {
        // Opreste tracker anterior daca exista (evita leak de thread)
        StopMouseTracker();

        _trackingActive = true;
        _mouseTracker = new System.Threading.Timer(_ =>
        {
            if (!_trackingActive) return;

            // Citeste pozitia curenta a cursor-ului (coordonate ecran absolute)
            var pos = System.Windows.Forms.Cursor.Position;

            // Update UI pe thread-ul UI — thread-safe
            Dispatcher.InvokeAsync(() =>
            {
                if (!_trackingActive) return;

                // Update pentru PanelMouse (CLICK, DBLCLICK, RIGHTCLICK, MOVE)
                TxtMouseX.Text = pos.X.ToString();
                TxtMouseY.Text = pos.Y.ToString();

                // Update pentru PanelScroll (SCROLL)
                TxtScrollMouseX.Text = pos.X.ToString();
                TxtScrollMouseY.Text = pos.Y.ToString();
            });
        }, null, 0, 50); // polling la 50ms — identic Python
    }

    /// <summary>
    /// Opreste thread-ul de tracking si elibereaza resurse.
    /// Apelat la: schimbare tip pas non-coord, inchidere dialog.
    /// </summary>
    private void StopMouseTracker()
    {
        _trackingActive = false;
        _mouseTracker?.Dispose();
        _mouseTracker = null;
    }

    /// <summary>
    /// Captureaza pozitia curenta a mouse-ului si o pune in TxtX / TxtY.
    /// Echivalent Python: buton "Captează poziție" din StepBuilderDialog.
    /// </summary>
    private async void BtnCapturePos_Click(object sender, RoutedEventArgs e)
    {
        BtnCapturePos.IsEnabled = false;

        for (int i = 3; i >= 1; i--)
        {
            BtnCapturePos.Content = $"⏳ {i}...";
            BtnCapturePos.Background = new System.Windows.Media.SolidColorBrush(
                System.Windows.Media.Color.FromRgb(20, 20, 50));   // navy închis
            BtnCapturePos.Foreground = new System.Windows.Media.SolidColorBrush(
                System.Windows.Media.Color.FromRgb(255, 210, 0));  // galben auriu
            await Task.Delay(1000);
        }

        // Captează poziția
        var pos = System.Windows.Forms.Cursor.Position;
        TxtX.Text = pos.X.ToString();
        TxtY.Text = pos.Y.ToString();

        // Feedback verde
        BtnCapturePos.Content = "✅ Capturat!";
        BtnCapturePos.Background = new System.Windows.Media.SolidColorBrush(
            System.Windows.Media.Color.FromRgb(0, 140, 80));
        BtnCapturePos.Foreground = new System.Windows.Media.SolidColorBrush(
            System.Windows.Media.Colors.White);
        await Task.Delay(800);

        // Reset
        BtnCapturePos.Content = "📍 Captează poziție";
        BtnCapturePos.Background = new System.Windows.Media.SolidColorBrush(
            System.Windows.Media.Color.FromRgb(0, 153, 153));
        BtnCapturePos.Foreground = new System.Windows.Media.SolidColorBrush(
            System.Windows.Media.Colors.White);
        BtnCapturePos.IsEnabled = true;
    }

    // Același pattern pentru BtnCaptureScrollPos_Click
    private async void BtnCaptureScrollPos_Click(object sender, RoutedEventArgs e)
    {
        BtnCaptureScrollPos.IsEnabled = false;

        for (int i = 3; i >= 1; i--)
        {
            BtnCaptureScrollPos.Content = $"⏳ {i}...";
            await Task.Delay(1000);
        }

        // Pentru SCROLL: capturăm X/Y ca poziție de scroll
        var pos = System.Windows.Forms.Cursor.Position;
        // Afișăm în tracker (deja live) — opțional populăm TxtX/TxtY
        TxtScrollMouseX.Text = pos.X.ToString();
        TxtScrollMouseY.Text = pos.Y.ToString();

        BtnCaptureScrollPos.Content = "✅ Capturat!";
        BtnCaptureScrollPos.Background = new System.Windows.Media.SolidColorBrush(
            System.Windows.Media.Color.FromRgb(0, 200, 150));

        await Task.Delay(800);

        BtnCaptureScrollPos.Content = "📍 Captează poziție";
        BtnCaptureScrollPos.Background = new System.Windows.Media.SolidColorBrush(
            System.Windows.Media.Color.FromRgb(0, 153, 153));
        BtnCaptureScrollPos.IsEnabled = true;
    }

    /// <summary>
    /// Captureaza pozitia curenta pentru pasul SCROLL (populeaza TxtX/TxtY via ScrollDx/Dy).
    /// Nota: SCROLL foloseste X/Y ca pozitie de scroll, nu TxtScrollDx/Dy.
    /// </summary>
    //private void BtnCaptureScrollPos_Click(object sender, RoutedEventArgs e)
    //{
    //    var pos = System.Windows.Forms.Cursor.Position;
    //    // Pentru SCROLL, X/Y reprezinta pozitia unde se face scroll-ul
    //    // ScrollDx/ScrollDy raman valorile de delta (cat se scrolleaza)
    //    // Afisam in TxtScrollMouseX/Y (deja facut de tracker)
    //    // Optionally: putem popula TxtScrollDx/Dy cu pozitia — dar Python nu face asta
    //    // Comportament identic Python: nu face nimic special pentru SCROLL capture
    //    // (tracker-ul afiseaza pozitia, utilizatorul decide manual ce valori pune)
    //    _ = pos; // suppress warning — pozitia e deja afisata de tracker
    //}

    /// <summary>
    /// Porneste tracker-ul dupa ce fereastra e complet initializata (handle Win32 disponibil).
    /// Identic Python: tracker pornit la deschiderea dialogului daca tipul e coord-step.
    /// </summary>
    protected override void OnSourceInitialized(EventArgs e)
    {
        base.OnSourceInitialized(e);

        // Porneste tracker doar daca tipul initial e coord-step
        if (CmbStepType.SelectedItem is string stepType && IsCoordStep(stepType))
            StartMouseTracker();
    }

    /// <summary>
    /// Opreste tracker-ul la inchiderea dialogului — elibereaza thread-ul.
    /// </summary>
    protected override void OnClosed(EventArgs e)
    {
        StopMouseTracker();
        base.OnClosed(e);
    }

    /// <summary>
    /// Returneaza true daca tipul de pas curent necesita coordonate (si deci tracker).
    /// Tipuri coord: CLICK, DBLCLICK, RIGHTCLICK, MOVE, SCROLL.
    /// </summary>
    private static bool IsCoordStep(string stepType) =>
        COORD_STEP_TYPES.Contains(stepType);

    // ════════════════════════════════════════════════════════════════════════════
    // OK / Cancel
    // ════════════════════════════════════════════════════════════════════════════

    private void BtnOk_Click(object sender, RoutedEventArgs e)
    {
        var stepType = CmbStepType.SelectedItem as string ?? "CLICK";

        ResultStep = new StepModel
        {
            StepId          = _editStep?.StepId ?? 0,
            StepType        = stepType,
            Description     = TxtDescription.Text.Trim(),
            X               = TryParseInt(TxtX.Text),
            Y               = TryParseInt(TxtY.Text),
            Button          = (CmbButton.SelectedItem as ComboBoxItem)?.Content?.ToString() ?? "left",
            KeyCombo        = TxtKeyCombo.Text.Trim(),
            TextInput       = TxtTextInput.Text,
            ScrollDx        = TryParseInt(TxtScrollDx.Text),
            ScrollDy        = TryParseInt(TxtScrollDy.Text, 3),
            QuestionText    = TxtQuestionText.Text.Trim(),
            QuestionButtons = string.IsNullOrWhiteSpace(TxtQuestionButtons.Text)
                              ? "Continua,Opreste,Sari"
                              : TxtQuestionButtons.Text.Trim(),
            DelayBefore     = TryParseDouble(TxtDelayBefore.Text),
            DelayAfter      = TryParseDouble(TxtDelayAfter.Text),
            MonitorId       = TryParseInt(TxtMonitorId.Text),
            Skip            = ChkSkip.IsChecked == true,
            Comment         = TxtComment.Text.Trim(),
            Timestamp       = DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss"),
        };

        DialogResult = true;
        Close();
    }

    private void BtnCancel_Click(object sender, RoutedEventArgs e)
    {
        DialogResult = false;
        Close();
    }

    // ── Helpers ──────────────────────────────────────────────────────────────────
    private static int TryParseInt(string s, int def = 0)
        => int.TryParse(s, out var v) ? v : def;

    private static double TryParseDouble(string s, double def = 0.0)
        => double.TryParse(s, System.Globalization.NumberStyles.Any,
                           System.Globalization.CultureInfo.InvariantCulture, out var v) ? v : def;
}

