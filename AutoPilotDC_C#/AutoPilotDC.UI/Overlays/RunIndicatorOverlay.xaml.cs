// ============================================================
// AutoPilot DC v3.9 -> C# WPF .NET 8
// RunIndicatorOverlay.xaml.cs � Overlay iteratie curenta
// Echivalent Python: RunIndicatorOverlay
// ============================================================

using System.Windows;

namespace AutoPilotDC.UI.Overlays;

public partial class RunIndicatorOverlay : Window
{
    public RunIndicatorOverlay() => InitializeComponent();

    public void UpdateIter(int current, int total)
    {
        TxtIter.Text = $"? {current} / {total}";
        if (!IsVisible) Show();
    }

    public void HideOverlay() => Hide();
}
