// ============================================================
// AutoPilot DC v3.9 -> C# WPF .NET 8
// InputDialog.xaml.cs � Dialog input text generic
// ============================================================

using System.Windows;

namespace AutoPilotDC.UI.Views.Dialogs;

public partial class InputDialog : Window
{
    public string? Result => TxtInput.Text.Trim();

    public InputDialog(string title, string prompt)
    {
        InitializeComponent();
        Title        = title;
        LblPrompt.Content = prompt;
        TxtInput.Focus();
    }

    private void BtnOk_Click(object sender, RoutedEventArgs e)
    {
        if (!string.IsNullOrWhiteSpace(TxtInput.Text))
        {
            DialogResult = true;
            Close();
        }
    }

    private void BtnCancel_Click(object sender, RoutedEventArgs e)
    {
        DialogResult = false;
        Close();
    }
}
