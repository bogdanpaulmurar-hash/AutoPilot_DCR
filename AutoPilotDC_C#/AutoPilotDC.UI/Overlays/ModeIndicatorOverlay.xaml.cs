// ============================================================
// AutoPilot DC v3.9 -> C# WPF .NET 8
// ModeIndicatorOverlay.xaml.cs � Overlay indicator mod curent
// Echivalent Python: ModeIndicatorOverlay (ui/overlays/__init__.py)
// ============================================================

using System.Windows;
using System.Windows.Media;
using Color = System.Windows.Media.Color;


namespace AutoPilotDC.UI.Overlays;

public partial class ModeIndicatorOverlay : Window
{
    public ModeIndicatorOverlay()
    {
        InitializeComponent();
    }

    public void ShowMode(string mode)
    {
        TxtMode.Text = mode switch
        {
            "recording" => "? RECORDING",
            "playing"   => "? PLAYING",
            "paused"    => "? PAUSED",
            _           => "? STANDBY"
        };

        TxtMode.Foreground = mode switch
        {
            "recording" => new SolidColorBrush(Color.FromRgb(224, 82, 82)),
            "playing"   => new SolidColorBrush(Color.FromRgb(0, 200, 150)),
            "paused"    => new SolidColorBrush(Color.FromRgb(255, 179, 71)),
            _           => new SolidColorBrush(Color.FromRgb(96, 96, 128)),
        };

        Show();
    }

    public void HideOverlay() => Hide();
}
