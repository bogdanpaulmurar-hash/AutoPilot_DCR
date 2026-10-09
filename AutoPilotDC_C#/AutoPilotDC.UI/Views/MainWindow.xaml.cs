// ============================================================
// AutoPilot DC v3.9 -> C# WPF .NET 8
// MainWindow.xaml.cs � Code-behind (minimal � logica in ViewModel)
// ============================================================

using System;
using System.Windows;
using System.Windows.Interop;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Win32;
using AutoPilotDC.Infrastructure.Services;
using AutoPilotDC.UI.ViewModels;
using MessageBox = System.Windows.MessageBox;
using OpenFileDialog = Microsoft.Win32.OpenFileDialog;

namespace AutoPilotDC.UI.Views;

public partial class MainWindow : Window
{
    private readonly MainViewModel    _vm;
    private readonly HotkeyManager   _hotkeyManager;

    public MainWindow(MainViewModel vm, HotkeyManager hotkeyManager)
    {
        InitializeComponent();
        _vm            = vm;
        _hotkeyManager = hotkeyManager;
        DataContext    = _vm;

        Loaded  += OnLoaded;
        Closing += OnClosing;
    }

    private void OnLoaded(object sender, RoutedEventArgs e)
    {
        // Initializeaza HotkeyManager cu HWND + Dispatcher
        var hwnd = new WindowInteropHelper(this).Handle;
        _hotkeyManager.Initialize(hwnd, action => Dispatcher.InvokeAsync(action));

        // Adauga WndProc hook pentru WM_HOTKEY
        HwndSource.FromHwnd(hwnd).AddHook(_hotkeyManager.WndProcHook);

        // Conecteaza hotkeys la ViewModel commands
        _hotkeyManager.StartRecording += () => _vm.StartRecordingCmd.Execute(null);
        _hotkeyManager.StopRecording  += () => _vm.StopRecordingCmd.Execute(null);
        _hotkeyManager.Play           += () => _vm.PlayCmd.Execute(null);
        _hotkeyManager.PauseResume    += () => _vm.PauseResumeCmd.Execute(null);
        _hotkeyManager.ResumePlay     += () => _vm.PauseResumeCmd.Execute(null);
        _hotkeyManager.StopPlay       += () => _vm.StopPlayCmd.Execute(null);
        _hotkeyManager.EmergencyStop  += () => _vm.EmergencyStopCmd.Execute(null);
    }

    private void OnClosing(object? sender, System.ComponentModel.CancelEventArgs e)
    {
        _hotkeyManager.Dispose();
        _vm.Dispose();
    }

    // -- Event handlers pentru elemente non-bindable -------------------

    private void StepsGrid_SelectionChanged(object sender, System.Windows.Controls.SelectionChangedEventArgs e)
    {
        // Sincronizare selectie intre tab-uri (deja bound prin SelectedStep)
    }

    private void BrowseExcel_Click(object sender, RoutedEventArgs e)
    {
        var dlg = new OpenFileDialog
        {
            Filter = "Excel Files|*.xlsx;*.xls|All Files|*.*",
            Title  = "Selecteaza fisier Excel"
        };
        if (dlg.ShowDialog() == true)
            _vm.ExcelPath = dlg.FileName;
    }

    private void RunExcel_Click(object sender, RoutedEventArgs e)
    {
        MessageBox.Show(
            $"Excel automation:\nFisier: {_vm.ExcelPath}\nSheet: {_vm.ExcelSheet}\nRange: {_vm.ExcelRange}",
            "Excel Run", MessageBoxButton.OK, MessageBoxImage.Information);
    }

    private void NoteBullet_Click(object sender, RoutedEventArgs e)
        => _vm.NotesText += "\n� ";

    private void NoteNumbered_Click(object sender, RoutedEventArgs e)
    {
        int count = _vm.NotesText.Split('\n').Length;
        _vm.NotesText += $"\n{count}. ";
    }

    private void NoteSave_Click(object sender, RoutedEventArgs e)
        => MessageBox.Show("Nota salvata!", "Notite", MessageBoxButton.OK, MessageBoxImage.Information);

    private void NoteClear_Click(object sender, RoutedEventArgs e)
        => _vm.NotesText = "";

    private void Button_Click(object sender, RoutedEventArgs e)
    {

    }
}
