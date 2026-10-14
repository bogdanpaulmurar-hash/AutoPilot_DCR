// ============================================================
// AutoPilot DC v3.9 -> C# WPF .NET 8
// App.xaml.cs — Entry point + Dependency Injection
// ============================================================

using System;
using System.Windows;
using Microsoft.Extensions.DependencyInjection;
using AutoPilotDC.Application;
using AutoPilotDC.Core.Interfaces;
using AutoPilotDC.Infrastructure.Engines;
using AutoPilotDC.Infrastructure.Recording;
using AutoPilotDC.Infrastructure.Repositories;
using AutoPilotDC.Infrastructure.Services;
using PowerManagementService = AutoPilotDC.Infrastructure.Services.PowerManagementService;
using WatchdogService = AutoPilotDC.Infrastructure.Services.WatchdogService;
using AutoPilotDC.UI.ViewModels;
using AutoPilotDC.UI.Views;

namespace AutoPilotDC.UI;

[System.Runtime.Versioning.SupportedOSPlatform("windows7.0")]
public partial class App : System.Windows.Application
{
    private ServiceProvider? _serviceProvider;

    protected override void OnStartup(StartupEventArgs e)
    {
        base.OnStartup(e);

        // Erorile neprinse NU mai sunt ascunse: utilizatorul vede mesajul (inainte aplicatia "nu facea nimic")
        DispatcherUnhandledException += (s, ex) =>
        {
            System.Diagnostics.Debug.WriteLine($"[APP ERROR] {ex.Exception}");
            ex.Handled = true;
            System.Windows.MessageBox.Show(ex.Exception.Message, "AutoPilot DC — eroare",
                System.Windows.MessageBoxButton.OK, System.Windows.MessageBoxImage.Error);
        };

        // Rulare programata fara interfata: AutoPilotDC.UI.exe --run "rutina.rpr.json"
        var runIndex = Array.FindIndex(e.Args, a => string.Equals(a, "--run", StringComparison.OrdinalIgnoreCase));
        if (runIndex >= 0 && runIndex + 1 < e.Args.Length)
        {
            ShutdownMode = ShutdownMode.OnExplicitShutdown;
            var path = e.Args[runIndex + 1];
            _ = Dispatcher.InvokeAsync(async () =>
            {
                int code = await AutoPilotDC.UI.Studio.HeadlessRunner.RunAsync(path);
                System.Environment.Exit(code);
            });
            return;
        }

        var services = new ServiceCollection();
        ConfigureServices(services);
        _serviceProvider = services.BuildServiceProvider();

        var mainWindow = _serviceProvider.GetRequiredService<MainWindow>();
        mainWindow.Show();
    }

    private static void ConfigureServices(IServiceCollection services)
    {
        // ── Infrastructure ────────────────────────────────────────────
        services.AddSingleton<ISettingsManager, SettingsManager>();
        services.AddSingleton<IRoutineRepository, JsonRoutineRepository>();
        services.AddSingleton<ILogRepository, JsonLogRepository>();
        services.AddSingleton<DesktopEngine>();
        services.AddSingleton<ExcelEngine>();
        services.AddSingleton<HotkeyManager>();

        // ── Engines ───────────────────────────────────────────────────
        services.AddSingleton<IRecorder>(sp =>
            new RecorderEngine(
                sp.GetRequiredService<ISettingsManager>()
            ));

        services.AddSingleton<IPlayer>(sp =>
        {
            var engine = new PlayerEngine(
                sp.GetRequiredService<ISettingsManager>(),
                sp.GetRequiredService<ILogRepository>(),
                sp.GetRequiredService<DesktopEngine>()
            );
            engine.PowerMgmt = sp.GetRequiredService<PowerManagementService>();
            engine.Watchdog   = sp.GetRequiredService<WatchdogService>();
            return engine;
        });

        // ── Faza 10: SimulatorEngine ──────────────────────────────────
        services.AddSingleton<SimulatorEngine>(sp =>
            new SimulatorEngine(
                sp.GetRequiredService<ILogRepository>(),
                sp.GetRequiredService<DesktopEngine>()
            ));

        // ── Application Services ──────────────────────────────────────
        services.AddSingleton<PlayerService>();
        services.AddSingleton<RecorderService>();
        services.AddSingleton<RoutineService>();
        services.AddSingleton<LogService>();
        services.AddSingleton<PowerManagementService>();
        services.AddSingleton<WatchdogService>();

        // ── UI ────────────────────────────────────────────────────────
        services.AddSingleton<MainViewModel>();
        services.AddSingleton<MainWindow>();
    }

    protected override void OnExit(ExitEventArgs e)
    {
        _serviceProvider?.Dispose();
        base.OnExit(e);
        System.Environment.Exit(0);
    }
}