// ============================================================
// AutoPilot DC v3.9 -> C# WPF .NET 8
// QuestionDialog.xaml.cs — Dialog pentru pasul QUESTION
// Echivalent Python: QuestionDialog (butoane custom din question_buttons)
// ============================================================

using System.Windows;
using System.Windows.Controls;
using AutoPilotDC.UI.Commands;
using Button = System.Windows.Controls.Button;

namespace AutoPilotDC.UI.Views.Dialogs;

public partial class QuestionDialog : Window
{
    public string? SelectedAnswer { get; private set; }

    public QuestionDialog(string questionText, string buttonsStr)
    {
        InitializeComponent();
        TxtQuestion.Text = questionText;

        // Genereaza butoane din string "Continua,Opreste,Sari"
        var buttons = buttonsStr.Split(',');
        foreach (var btn in buttons)
        {
            var btnText = btn.Trim();
            var button = new Button
            {
                Content = btnText,
                MinWidth = 90,
                Margin = new Thickness(6, 0, 6, 0),
                Style = FindResource(
                    btnText == "Opreste" ? "DangerButtonStyle" :
                    btnText == "Sari"    ? "NeutralButtonStyle" :
                                          "SuccessButtonStyle") as Style
            };
            button.Click += (_, _) =>
            {
                SelectedAnswer = btnText;
                DialogResult   = true;
                Close();
            };
            ButtonsPanel.Children.Add(button);
        }
    }
}

