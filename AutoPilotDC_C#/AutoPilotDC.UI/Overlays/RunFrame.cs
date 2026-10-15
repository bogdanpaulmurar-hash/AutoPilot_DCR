// ============================================================
// AutoPilot DC v4.1
// RunFrame.cs — Chenar pe ecran in timpul rularii / inregistrarii
//
//   Rulare        -> chenar ROSU  + "RUN" mic in coltul din dreapta-sus
//   Inregistrare  -> chenar VERDE + "REC"
//   Pauza / intrebare -> chenar PORTOCALIU + "PAUZA"
//
// Chenarul lasa click-urile sa treaca prin el, nu ia focusul si nu apare
// in capturile de ecran (deci nu strica amprentele sistemului de preventie).
// Apare pe toate monitoarele.
// ============================================================

using System.Windows;
using System.Windows.Controls;
using System.Windows.Interop;
using System.Windows.Media;
using System.Windows.Threading;
using AutoPilotDC.Infrastructure.Safety;
using Brushes = System.Windows.Media.Brushes;
using Color = System.Windows.Media.Color;
using FontFamily = System.Windows.Media.FontFamily;
using HorizontalAlignment = System.Windows.HorizontalAlignment;

namespace AutoPilotDC.UI.Overlays;

public enum FrameMode { Off, Run, Rec, Pause }

public static class RunFrame
{
    private static readonly List<FrameWindow> Windows = new();
    private static DispatcherTimer? _keepOnTop;

    /// <summary>Setarea "show_run_frame" (Setari). False = chenarul nu se mai afiseaza.</summary>
    public static bool Enabled { get; set; } = true;

    public static FrameMode Current { get; private set; } = FrameMode.Off;

    /// <summary>Afiseaza / schimba / ascunde chenarul. Se poate apela de pe orice fir.</summary>
    public static void Show(FrameMode mode)
    {
        var d = System.Windows.Application.Current?.Dispatcher;
        if (d == null) return;
        if (!d.CheckAccess()) { d.BeginInvoke(() => Show(mode)); return; }

        Current = mode;
        if (mode == FrameMode.Off || !Enabled)
        {
            foreach (var w in Windows) w.Close();
            Windows.Clear();
            _keepOnTop?.Stop();
            return;
        }

        var screens = System.Windows.Forms.Screen.AllScreens;
        if (Windows.Count != screens.Length)
        {
            foreach (var w in Windows) w.Close();
            Windows.Clear();
            foreach (var s in screens)
            {
                var w = new FrameWindow(s.Bounds);
                Windows.Add(w);
                w.Show();
            }
        }
        foreach (var w in Windows) w.SetMode(mode);

        // Alte ferestre "mereu deasupra" (ex: video, prezentari) pot acoperi chenarul -> il readucem periodic
        _keepOnTop ??= new DispatcherTimer(TimeSpan.FromSeconds(2), DispatcherPriority.Background,
            (_, _) => { foreach (var w in Windows) w.BringToTop(); }, System.Windows.Application.Current!.Dispatcher);
        _keepOnTop.Start();
    }

    public static void Hide() => Show(FrameMode.Off);

    private sealed class FrameWindow : Window
    {
        private readonly System.Drawing.Rectangle _bounds;
        private readonly Border _frame;
        private readonly Border _badge;
        private readonly TextBlock _label;
        private IntPtr _hwnd;

        public FrameWindow(System.Drawing.Rectangle bounds)
        {
            _bounds = bounds;
            WindowStyle = WindowStyle.None;
            AllowsTransparency = true;
            Background = Brushes.Transparent;
            Topmost = true;
            ShowInTaskbar = false;
            ShowActivated = false;
            Focusable = false;
            ResizeMode = ResizeMode.NoResize;
            Title = "AutoPilot DC — indicator";
            // pozitie provizorie; cea reala (pixeli fizici) se seteaza in OnSourceInitialized
            Left = bounds.Left; Top = bounds.Top; Width = 200; Height = 200;

            _frame = new Border { BorderThickness = new Thickness(5), IsHitTestVisible = false };
            _label = new TextBlock
            {
                Foreground = Brushes.White,
                FontFamily = new FontFamily("Segoe UI"),
                FontWeight = FontWeights.Bold,
                FontSize = 12,
            };
            _badge = new Border
            {
                Child = _label,
                Padding = new Thickness(8, 1, 8, 2),
                CornerRadius = new CornerRadius(0, 0, 0, 6),
                HorizontalAlignment = HorizontalAlignment.Right,
                VerticalAlignment = VerticalAlignment.Top,
                IsHitTestVisible = false,
            };
            var grid = new Grid { IsHitTestVisible = false };
            grid.Children.Add(_frame);
            grid.Children.Add(_badge);
            Content = grid;
        }

        protected override void OnSourceInitialized(EventArgs e)
        {
            base.OnSourceInitialized(e);
            _hwnd = new WindowInteropHelper(this).Handle;
            ScreenProbe.MakeClickThrough(_hwnd);
            ScreenProbe.ExcludeFromCapture(_hwnd);
            BringToTop();
        }

        public void BringToTop()
        {
            if (_hwnd != IntPtr.Zero)
                ScreenProbe.PlaceTopmost(_hwnd, _bounds.Left, _bounds.Top, _bounds.Width, _bounds.Height);
        }

        public void SetMode(FrameMode mode)
        {
            var (color, text) = mode switch
            {
                FrameMode.Rec => (Color.FromRgb(0x00, 0xC8, 0x53), "● REC"),
                FrameMode.Pause => (Color.FromRgb(0xFF, 0x8F, 0x00), "❚❚ PAUZA"),
                _ => (Color.FromRgb(0xE5, 0x1C, 0x23), "▶ RUN"),
            };
            var brush = new SolidColorBrush(color);
            _frame.BorderBrush = brush;
            _badge.Background = brush;
            _label.Text = text;
        }
    }
}
