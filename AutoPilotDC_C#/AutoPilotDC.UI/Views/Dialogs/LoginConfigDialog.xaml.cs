// ============================================================
// AutoPilot DC v3.9 -> C# WPF .NET 8
// LoginConfigDialog.xaml.cs — Faza 9: Code-behind dialog login
// FIX: Guard null in UpdatePanelVisibility() — NullReferenceException
//      la SelectionChanged declansat in timpul InitializeComponent()
// Autor: Bogdan Murar (Z003FU5C) - Siemens AG
// ============================================================

using System;
using System.Windows;
using System.Windows.Controls;
using AutoPilotDC.Infrastructure.Services;
using AutoPilotDC.Models;
using MessageBox = System.Windows.MessageBox;
using OpenFileDialog = Microsoft.Win32.OpenFileDialog;
using Button = System.Windows.Controls.Button;

namespace AutoPilotDC.UI.Views.Dialogs;

public partial class LoginConfigDialog : Window
{
    // ── Rezultat ──────────────────────────────────────────────────
    public LoginConfig? Result { get; private set; }

    // ── State ─────────────────────────────────────────────────────
    private readonly LoginConfig _config;
    private readonly LoginService _loginService = new();

    // ── Constructor ───────────────────────────────────────────────
    public LoginConfigDialog(LoginConfig? existingConfig = null)
    {
        InitializeComponent();   // ← panelurile (PnlNone etc.) exista DUPA aceasta linie

        _config = existingConfig != null
            ? CloneConfig(existingConfig)
            : new LoginConfig();

        LoadFromConfig();        // ← safe: InitializeComponent() deja rulat
    }

    // ── Incarcare configuratie existenta ──────────────────────────
    private void LoadFromConfig()
    {
        ChkEnabled.IsChecked = _config.Enabled;

        foreach (ComboBoxItem item in CmbMode.Items)
        {
            if (item.Tag?.ToString() == _config.Mode)
            {
                CmbMode.SelectedItem = item;
                break;
            }
        }
        if (CmbMode.SelectedIndex < 0) CmbMode.SelectedIndex = 0;

        // Credentials
        TxtLoginUrl.Text = _config.LoginUrl;
        TxtUsername.Text = _config.Username;
        TxtUsernameSelector.Text = _config.UsernameSelector;
        TxtPasswordSelector.Text = _config.PasswordSelector;
        TxtSubmitSelector.Text = _config.SubmitSelector;
        TxtSuccessSelector.Text = _config.SuccessSelector;

        // Entra ID
        TxtEntraLoginUrl.Text = _config.LoginUrl;
        TxtTenantId.Text = _config.EntraIdTenantId;
        TxtClientId.Text = _config.EntraIdClientId;
        TxtEntraUsername.Text = _config.Username;
        TxtEntraSuccessSelector.Text = _config.SuccessSelector;

        // Session reuse
        TxtProfilePath.Text = _config.BrowserProfilePath;
        ChkReuseSession.IsChecked = _config.ReuseExistingSession;

        // Timeout
        TxtTimeout.Text = _config.TimeoutSeconds.ToString();

        // Apelat ULTIMUL — dupa ce toate controalele sunt populate
        UpdatePanelVisibility();
    }

    // ── Events ────────────────────────────────────────────────────
    private void ChkEnabled_Changed(object sender, RoutedEventArgs e)
        => UpdatePanelVisibility();

    private void CmbMode_SelectionChanged(object sender, SelectionChangedEventArgs e)
        => UpdatePanelVisibility();

    // ── Vizibilitate paneluri ─────────────────────────────────────
    private void UpdatePanelVisibility()
    {
        // GUARD: SelectionChanged poate fi declansat de XAML inainte ca
        // InitializeComponent() sa termine — panelurile sunt inca null.
        if (PnlNone == null) return;

        var mode = GetSelectedMode();
        PnlNone.Visibility = mode == "none" ? Visibility.Visible : Visibility.Collapsed;
        PnlCredentials.Visibility = mode == "credentials" ? Visibility.Visible : Visibility.Collapsed;
        PnlEntraId.Visibility = mode == "entra_id" ? Visibility.Visible : Visibility.Collapsed;
        PnlSessionReuse.Visibility = mode == "session_reuse" ? Visibility.Visible : Visibility.Collapsed;
        PnlTimeout.Visibility = mode != "none" ? Visibility.Visible : Visibility.Collapsed;
    }

    private string GetSelectedMode()
        => CmbMode.SelectedItem is ComboBoxItem item
            ? item.Tag?.ToString() ?? "none"
            : "none";

    // ── Browse profil ─────────────────────────────────────────────
    private void BtnBrowseProfile_Click(object sender, RoutedEventArgs e)
    {
        var dialog = new OpenFileDialog
        {
            Title = "Selecteaza folderul profil browser",
            CheckFileExists = false,
            CheckPathExists = true,
            FileName = "Selecteaza folder",
            Filter = "Toate fisierele|*.*"
        };
        if (dialog.ShowDialog() == true)
        {
            var dir = System.IO.Path.GetDirectoryName(dialog.FileName);
            TxtProfilePath.Text = dir ?? dialog.FileName;
        }
    }

    // ── Testare login ─────────────────────────────────────────────
    private async void BtnTest_Click(object sender, RoutedEventArgs e)
    {
        var config = BuildConfigFromUI();
        if (!config.Enabled || config.Mode == "none")
        {
            MessageBox.Show("Activati loginul si selectati un mod pentru a testa.",
                "Test Login", MessageBoxButton.OK, MessageBoxImage.Information);
            return;
        }

        var btn = (Button)sender;
        btn.IsEnabled = false;
        btn.Content = "⏳ Testare...";

        try
        {
            using var playwright = await Microsoft.Playwright.Playwright.CreateAsync();
            await using var browser = await playwright.Chromium.LaunchAsync(
                new Microsoft.Playwright.BrowserTypeLaunchOptions { Headless = false, SlowMo = 500 });
            var page = await browser.NewPageAsync();

            var (success, error) = await _loginService.ExecuteLoginAsync(config, page);

            if (success)
                MessageBox.Show("✅ Login reusit!",
                    "Test Login", MessageBoxButton.OK, MessageBoxImage.Information);
            else
                MessageBox.Show($"❌ Login esuat:\n{error}",
                    "Test Login", MessageBoxButton.OK, MessageBoxImage.Warning);
        }
        catch (Exception ex)
        {
            MessageBox.Show($"Eroare la testare:\n{ex.Message}",
                "Test Login", MessageBoxButton.OK, MessageBoxImage.Error);
        }
        finally
        {
            btn.IsEnabled = true;
            btn.Content = "🧪 Testeaza Login";
        }
    }

    // ── Salvare ───────────────────────────────────────────────────
    private void BtnSave_Click(object sender, RoutedEventArgs e)
    {
        Result = BuildConfigFromUI();
        DialogResult = true;
        Close();
    }

    // ── Anulare ───────────────────────────────────────────────────
    private void BtnCancel_Click(object sender, RoutedEventArgs e)
    {
        Result = null;
        DialogResult = false;
        Close();
    }

    // ── Build config din UI ───────────────────────────────────────
    private LoginConfig BuildConfigFromUI()
    {
        var mode = GetSelectedMode();
        int.TryParse(TxtTimeout.Text, out int timeout);
        if (timeout <= 0) timeout = 30;

        var cfg = new LoginConfig
        {
            Enabled = ChkEnabled.IsChecked == true,
            Mode = mode,
            TimeoutSeconds = timeout
        };

        switch (mode)
        {
            case "credentials":
                cfg.LoginUrl = TxtLoginUrl.Text.Trim();
                cfg.Username = TxtUsername.Text.Trim();
                cfg.UsernameSelector = TxtUsernameSelector.Text.Trim();
                cfg.PasswordSelector = TxtPasswordSelector.Text.Trim();
                cfg.SubmitSelector = TxtSubmitSelector.Text.Trim();
                cfg.SuccessSelector = TxtSuccessSelector.Text.Trim();
                var pwd = PbPassword.Password;
                cfg.PasswordEncrypted = !string.IsNullOrEmpty(pwd)
                    ? LoginService.EncryptPassword(pwd)
                    : _config.PasswordEncrypted;
                break;

            case "entra_id":
                cfg.LoginUrl = TxtEntraLoginUrl.Text.Trim();
                cfg.EntraIdTenantId = TxtTenantId.Text.Trim();
                cfg.EntraIdClientId = TxtClientId.Text.Trim();
                cfg.Username = TxtEntraUsername.Text.Trim();
                cfg.SuccessSelector = TxtEntraSuccessSelector.Text.Trim();
                break;

            case "session_reuse":
                cfg.BrowserProfilePath = TxtProfilePath.Text.Trim();
                cfg.ReuseExistingSession = ChkReuseSession.IsChecked == true;
                break;
        }

        return cfg;
    }

    // ── Clone ─────────────────────────────────────────────────────
    private static LoginConfig CloneConfig(LoginConfig src) => new()
    {
        Enabled = src.Enabled,
        Mode = src.Mode,
        LoginUrl = src.LoginUrl,
        Username = src.Username,
        PasswordEncrypted = src.PasswordEncrypted,
        UsernameSelector = src.UsernameSelector,
        PasswordSelector = src.PasswordSelector,
        SubmitSelector = src.SubmitSelector,
        SuccessSelector = src.SuccessSelector,
        EntraIdTenantId = src.EntraIdTenantId,
        EntraIdClientId = src.EntraIdClientId,
        ReuseExistingSession = src.ReuseExistingSession,
        BrowserProfilePath = src.BrowserProfilePath,
        TimeoutSeconds = src.TimeoutSeconds
    };
}

