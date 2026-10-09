// ============================================================
// AutoPilot DC v3.9 -> C# WPF .NET 8
// RedCursorOverlay.xaml.cs � Cursor ro?u �n Run/Simulation/Debug
// ============================================================

using System;
using System.Runtime.InteropServices;
using System.Windows;
using System.Windows.Threading;

namespace AutoPilotDC.UI.Overlays;

/// <summary>
/// Fereastra WPF transparenta Topmost � cerc ro?u �n jurul cursorului.
/// IsHitTestVisible=False ? nu intercepteaza click-uri.
/// Metode: ShowOverlay() / HideOverlay() (evita conflictul cu Window.Activate()).
/// </summary>
public partial class RedCursorOverlay : Window
{
    [StructLayout(LayoutKind.Sequential)]
    private struct POINT { public int X; public int Y; }

    [DllImport("user32.dll")]
    private static extern bool GetCursorPos(out POINT lpPoint);

    private readonly DispatcherTimer _timer;
    private const double CursorOffset = 20.0; // raza = 20px

    private bool _destroyed;

    public RedCursorOverlay()
    {
        InitializeComponent();

        _timer = new DispatcherTimer(DispatcherPriority.Render)
        {
            Interval = TimeSpan.FromMilliseconds(16) // ~60fps
        };
        _timer.Tick += OnTimerTick;
    }

    // -- API publica -------------------------------------------------------

    /// <summary>
    /// Activeaza overlay-ul (Run / Simulation / Debug).
    /// Redenumit fa?a de Window.Activate() pentru a evita conflictul.
    /// </summary>
    public void ShowOverlay()
    {
        if (_destroyed) return;
        Show();
        _timer.Start();
    }

    /// <summary>
    /// Dezactiveaza overlay-ul (Stop / Emergency Stop).
    /// </summary>
    public void HideOverlay()
    {
        _timer.Stop();
        Hide();
    }

    /// <summary>
    /// Distruge fereastra definitiv la shutdown aplica?ie.
    /// </summary>
    public void Destroy()
    {
        _destroyed = true;
        _timer.Stop();
        // Permite �nchiderea reala (override-ul de mai jos blocheaza altfel)
        Closing -= OnClosingHandler;
        Close();
    }

    // -- Timer -------------------------------------------------------------

    private void OnTimerTick(object? sender, EventArgs e)
    {
        if (!GetCursorPos(out POINT pt)) return;
        Left = pt.X - CursorOffset;
        Top = pt.Y - CursorOffset;
    }

    // -- Override Close ? Hide (refolosim fereastra) -----------------------

    protected override void OnInitialized(EventArgs e)
    {
        base.OnInitialized(e);
        Closing += OnClosingHandler;
    }

    private void OnClosingHandler(object? sender,
                                   System.ComponentModel.CancelEventArgs e)
    {
        if (!_destroyed)
        {
            e.Cancel = true;
            HideOverlay();
        }
    }
}