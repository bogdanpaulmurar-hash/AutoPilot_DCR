// ============================================================
// AutoPilot DC v3.9 -> C# WPF .NET 8
// PlayerEngine.cs — Motor de redare rutine
// Faza 4 + Faza 6 (browser) + Faza 9 (LoginConfig) + Faza 10 (SimulateAsync, IsDryRun)
// Autor: Bogdan Murar (Z003FU5C) — Siemens AG
// ============================================================

using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;
using AutoPilotDC.Core.Interfaces;
using AutoPilotDC.Infrastructure.Safety;
using AutoPilotDC.Infrastructure.Services;
using AutoPilotDC.Models;
using AutoPilotDC.Playwright;

namespace AutoPilotDC.Infrastructure.Engines;

/// <summary>
/// Motor de redare rutine. Executa pasii inregistrati pas cu pas.
/// Desktop steps: executate DIRECT via DesktopEngine (Win32 API).
/// Browser steps: rutate via BrowserStepExecutor -> PlaywrightEngine.
/// Simulation mode: SimulateStepAsync muta mouse-ul fara executie reala.
/// Echivalent Python: PlayerEngine
/// </summary>
[System.Runtime.Versioning.SupportedOSPlatform("windows7.0")]
public class PlayerEngine : IPlayer
{
    // ── Dependinte ────────────────────────────────────────────────────
    private readonly ISettingsManager _settings;
    private readonly ILogRepository   _log;
    private readonly DesktopEngine    _desktop;

    // ── Browser executor (optional, setat din App.xaml.cs) ───────────
    private BrowserStepExecutor? _browserExecutor;


    // -- Servicii optionale ---------------------------------------------------
    public WatchdogService?        Watchdog              { get; set; }
    public PowerManagementService? PowerMgmt             { get; set; }
    public EndOfCycleAction        EndOfCycleAction      { get; set; } = EndOfCycleAction.None;
    public bool                    SuppressNotifications { get; set; } = true;
    public bool                    PreventSleepOption    { get; set; } = true;

    // -- v4.1: Sistemul de preventie ------------------------------------------
    /// <summary>Verifica ecranul inainte de fiecare pas (null = dezactivat).</summary>
    public SafetyGuard?            Guard                 { get; set; }

    /// <summary>
    /// Intreaba utilizatorul cand Guard gaseste o diferenta sau un pas esueaza.
    /// (pas, alerta, poate reincerca) -> decizie. Null = continua fara intrebari.
    /// </summary>
    public Func<StepModel, GuardAlert, bool, Task<GuardDecision>>? OnGuardQuestion { get; set; }

    private volatile bool _isRunning;
    private volatile bool _isPaused;
    private volatile bool _isDryRun;
    private CancellationTokenSource? _cts;
    private readonly SemaphoreSlim _pauseSemaphore = new(1, 1);

    // ── IPlayer: proprietati ──────────────────────────────────────────
    public bool IsRunning => _isRunning;
    public bool IsPaused  => _isPaused;
    public bool IsDryRun  { get => _isDryRun; set => _isDryRun = value; }

    // ── IPlayer: callback-uri originale ──────────────────────────────
    public Action<bool>?                  OnPlaybackFinished { get; set; }
    public Action<StepModel>?             OnStepExecuting    { get; set; }
    public Action<StepModel, string>?     OnStepError        { get; set; }
    public Func<StepModel, Task<string>>? OnQuestion         { get; set; }
    public Action<int>?                   OnCountdown        { get; set; }
    public Action?                        OnStarted          { get; set; }
    public Action?                        OnPaused           { get; set; }
    public Action?                        OnResumed          { get; set; }
    public Action<int, int>?              OnIterUpdate       { get; set; }

    // ── IPlayer: callback-uri noi Faza 9/10 ──────────────────────────
    public Action<StepModel>? OnStepFinished    { get; set; }
    public Action<string>?    OnStatusChanged   { get; set; }
    public Action<int, int>?  OnProgressChanged { get; set; }

    /// <summary>Apelat cand Watchdog detecteaza o anomalie. Returneaza true=continua, false=opreste.</summary>
    public Func<WatchdogAnomaly, Task<bool>>? OnWatchdogQuestion { get; set; }

    // ── Constructor ───────────────────────────────────────────────────
    public PlayerEngine(
        ISettingsManager settings,
        ILogRepository   log,
        DesktopEngine    desktop)
    {
        _settings = settings;
        _log      = log;
        _desktop  = desktop;
    }

    // =========================================================
    // SetBrowserExecutor — Injecteaza BrowserStepExecutor (Faza 6)
    // Apelat din App.xaml.cs dupa initializare Playwright.
    // =========================================================
    public void SetBrowserExecutor(BrowserStepExecutor? executor)
    {
        _browserExecutor = executor;

        if (_browserExecutor != null)
        {
            _browserExecutor.OnStepExecuting = step => OnStepExecuting?.Invoke(step);
            _browserExecutor.OnStepError     = (step, err) => OnStepError?.Invoke(step, err);
            _browserExecutor.OnStepSimulated = step => OnStepExecuting?.Invoke(step);
        }
    }

    // =========================================================
    // SetSimulationMode — Activa/dezactiva SIMULATION pe browser steps
    // Echivalent Python: ModeIndicatorOverlay SIMULATION
    // =========================================================
    public void SetSimulationMode(bool enabled)
    {
        _browserExecutor?.SetSimulationMode(enabled);
    }

    // =========================================================
    // IPlayer.PlayAsync — Redare completa (original Faza 4+6)
    // Delegate catre overload cu LoginConfig = null
    // =========================================================
    public async Task PlayAsync(
        IEnumerable<StepModel> steps,
        int repeatCount = 1,
        CancellationToken cancellationToken = default)
    {
        await PlayAsync(steps, repeatCount, null, cancellationToken);
    }

    // =========================================================
    // IPlayer.PlayAsync — cu LoginConfig (Faza 9)
    // =========================================================
    public async Task PlayAsync(
        IEnumerable<StepModel> steps,
        int repeatCount,
        LoginConfig? loginConfig,
        CancellationToken cancellationToken = default)
    {
        if (_isRunning) return;

        _isRunning = true;
        _isPaused  = false;
        _cts = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken);

        bool success = true;

        // ── Power + Notifications ─────────────────────────────────────────────
        if (PreventSleepOption)        PowerMgmt?.PreventSleep();
        // "Nu deranja": cererea se inregistreaza IMEDIAT (aici, pe firul apelantului), iar aplicarea
        // (cateva secunde) merge in fundal, in paralel cu numaratoarea inversa. Asa, chiar daca rularea
        // e oprita imediat, "am terminat" nu mai poate ajunge inaintea lui "am nevoie".
        bool dnd = SuppressNotifications && PowerMgmt != null;
        if (dnd) PowerMgmt!.SuppressNotifications();
        Task dndTask = dnd ? Task.Run(() => DoNotDisturb.WaitSettled(15000)) : Task.CompletedTask;

        // ── Watchdog ──────────────────────────────────────────────────────────
        if (Watchdog != null)
        {
            Watchdog.OnAnomalyDetected = async anomaly =>
            {
                // Pauza instant
                if (_isRunning && !_isPaused)
                {
                    _isPaused = true;
                    _pauseSemaphore.Wait(0);
                    OnPaused?.Invoke();
                    OnStatusChanged?.Invoke($"[WATCHDOG] {anomaly.Type}: {anomaly.Description}");
                }

                // Intreaba utilizatorul
                bool continua = true;
                if (OnWatchdogQuestion != null)
                    continua = await OnWatchdogQuestion(anomaly);

                if (continua)
                {
                    _isPaused = false;
                    try { _pauseSemaphore.Release(); } catch { }
                    OnResumed?.Invoke();
                    OnStatusChanged?.Invoke("Rutina reluata dupa Watchdog.");
                }
                else
                {
                    _cts?.Cancel();
                }
                return continua;
            };
            Watchdog.Start();
        }

        try
        {
            // Countdown 3-2-1
            int countdown = _settings.Get<int>("countdown_before_play", 3);
            for (int i = countdown; i > 0; i--)
            {
                _cts.Token.ThrowIfCancellationRequested();
                OnCountdown?.Invoke(i);
                OnStatusChanged?.Invoke($"Start in {i}...");
                await Task.Delay(1000, _cts.Token);
            }
            OnCountdown?.Invoke(0);
            await dndTask;
            OnStarted?.Invoke();
            OnStatusChanged?.Invoke("Redare activa");

            // ── Faza 9: Login inainte de primul pas ───────────────────
            if (loginConfig?.Enabled == true)
            {
                OnStatusChanged?.Invoke("Executare login...");
                // LoginService.ExecuteLoginAsync() este apelat din exterior
                // (injectat via SetLoginService sau din MainViewModel)
            }

            var stepList = steps.ToList();
            int totalSteps = stepList.Count;
            double speed = _settings.Get<double>("playback_speed", 1.0);
            if (speed <= 0) speed = 1.0;

            for (int iter = 0; iter < repeatCount; iter++)
            {
                _cts.Token.ThrowIfCancellationRequested();
                OnIterUpdate?.Invoke(iter + 1, repeatCount);

                Guard?.BeginRun();

                for (int si = 0; si < stepList.Count; si++)
                {
                    var step = stepList[si];
                    _cts.Token.ThrowIfCancellationRequested();

                    if (step.Skip) continue;

                    if (_isPaused)
                        await _pauseSemaphore.WaitAsync(_cts.Token);

                    OnStepExecuting?.Invoke(step);
                    OnProgressChanged?.Invoke(si + 1, totalSteps);
                    OnStatusChanged?.Invoke($"Pas {si + 1}/{totalSteps}: {step.StepType}");

                    // Asteptarea dinainte de pas se face AICI, ca verificarea sa vada ecranul de dupa ea
                    var adjustedStep = ApplySpeed(step, speed).Clone();
                    if (adjustedStep.DelayBefore > 0 && !_isDryRun)
                        await Task.Delay(TimeSpan.FromSeconds(adjustedStep.DelayBefore), _cts.Token);
                    adjustedStep.DelayBefore = 0;

                    // ── v4.1: Sistemul de preventie ────────────────────
                    if (!_isDryRun && Guard != null)
                    {
                        var upcoming = stepList.Skip(si).Where(s => !s.Skip).ToList();
                        var alert = await Task.Run(() => Guard.CheckBeforeStep(step, upcoming), _cts.Token);
                        if (alert != null)
                        {
                            var decision = await AskGuardAsync(step, alert, canRetry: false);
                            if (decision == GuardDecision.Stop) { success = false; _cts.Cancel(); _cts.Token.ThrowIfCancellationRequested(); }
                            if (decision == GuardDecision.SkipStep) continue;
                            if (decision == GuardDecision.IgnoreStep) step.GuardIgnore = true;
                        }
                    }

                    Watchdog?.NotifyStepStarted(step);

                    bool ok; string err;
                    while (true)
                    {
                        if (_isDryRun)
                        {
                            await SimulateStepAsync(adjustedStep);
                            ok = true; err = string.Empty;
                        }
                        else
                        {
                            (ok, err) = await ExecuteStepCoreAsync(adjustedStep, _cts.Token);
                        }
                        if (ok || _isDryRun || OnGuardQuestion == null) break;

                        // Pasul a esuat: pauza + intrebare (inainte rutina mergea mai departe in tacere)
                        OnStepError?.Invoke(step, err);
                        var d = await AskGuardAsync(step,
                            new GuardAlert($"Pasul {step.StepId} ({step.GetDisplayType()}) a esuat", err, "error:" + step.StepId, CanIgnoreStep: false),
                            canRetry: true);
                        if (d == GuardDecision.Retry) continue;
                        if (d == GuardDecision.Stop) { success = false; _cts.Cancel(); _cts.Token.ThrowIfCancellationRequested(); }
                        break; // Continua / Sari pasul: mergem mai departe
                    }

                    Watchdog?.NotifyStepFinished();
                    Guard?.AfterStep();

                    if (ok)
                        OnStepFinished?.Invoke(step);
                    else
                    {
                        if (OnGuardQuestion == null) OnStepError?.Invoke(step, err);
                        success = false;
                    }
                }
            }

            OnStatusChanged?.Invoke("Redare finalizata");

            // ── End-of-cycle action ───────────────────────────────────────────
            if (success && EndOfCycleAction != EndOfCycleAction.None)
            {
                OnStatusChanged?.Invoke($"Actiune finala: {EndOfCycleAction}...");
                await Task.Delay(1500, CancellationToken.None);
                PowerMgmt?.ExecuteEndOfCycleAction(EndOfCycleAction);
            }
        }
        catch (OperationCanceledException)
        {
            success = false;
            OnStatusChanged?.Invoke("Redare oprita");
        }
        finally
        {
            Watchdog?.Stop();
            PowerMgmt?.RestoreSleep();
            // repornirea notificarilor dureaza cateva secunde: in fundal, ca interfata sa nu se blocheze
            var power = PowerMgmt;
            power?.RestoreNotifications();   // nu blocheaza: lucratorul reporneste notificarile
            _isRunning = false;
            _isPaused  = false;
            OnPlaybackFinished?.Invoke(success);
        }
    }

    // =========================================================
    // v4.1: Intrebare la diferente / erori — rutina sta pe pauza pana la raspuns
    // =========================================================
    private async Task<GuardDecision> AskGuardAsync(StepModel step, GuardAlert alert, bool canRetry)
    {
        OnStatusChanged?.Invoke($"⚠ {alert.Title} — astept decizia ta");
        if (OnGuardQuestion == null) return GuardDecision.Continue;

        _isPaused = true;
        OnPaused?.Invoke();
        GuardDecision decision;
        try
        {
            decision = await OnGuardQuestion(step, alert, canRetry);
        }
        finally
        {
            _isPaused = false;
            OnResumed?.Invoke();
        }

        Guard?.Acknowledge();
        OnStatusChanged?.Invoke(decision == GuardDecision.Stop
            ? "Oprit la cererea ta."
            : $"Preventie: \"{alert.Title}\" -> {decision}. Redare reluata.");
        return decision;
    }

    // =========================================================
    // IPlayer.Pause / Resume / Stop
    // =========================================================
    public void Pause()
    {
        if (!_isRunning || _isPaused) return;
        _isPaused = true;
        _pauseSemaphore.Wait(0);
        OnPaused?.Invoke();
        OnStatusChanged?.Invoke("Pauza");
    }

    public void Resume()
    {
        if (!_isPaused) return;
        _isPaused = false;
        try { _pauseSemaphore.Release(); } catch { }
        OnResumed?.Invoke();
        OnStatusChanged?.Invoke("Redare reluata");
    }

    public void Stop()
    {
        _cts?.Cancel();
        Resume();
        OnStatusChanged?.Invoke("Oprit");
    }

    // =========================================================
    // IPlayer.ExecuteStepAsync — Executa UN singur pas (Debug mode)
    // =========================================================
    public async Task<(bool Success, string Error)> ExecuteStepAsync(StepModel step)
    {
        try
        {
            return await ExecuteStepCoreAsync(step, CancellationToken.None);
        }
        catch (Exception ex)
        {
            return (false, ex.Message);
        }
    }

    // =========================================================
    // IPlayer.SimulateStepAsync — Simulare vizuala pas (Faza 1)
    // Muta mouse-ul la pozitie fara executie reala.
    // =========================================================
    public async Task SimulateStepAsync(StepModel step)
    {
        if (step.DelayBefore > 0)
            await Task.Delay(TimeSpan.FromSeconds(Math.Min(step.DelayBefore, 2.0)));

        // Muta mouse-ul la pozitia pasului (fara click)
        if (step.X > 0 || step.Y > 0)
            DesktopEngine.MoveTo(step.X, step.Y);

        await Task.Delay(150); // timp vizual minim

        if (step.DelayAfter > 0)
            await Task.Delay(TimeSpan.FromSeconds(Math.Min(step.DelayAfter, 2.0)));
    }

    // =========================================================
    // IPlayer.SimulateAsync — Simulare completa rutina (Faza 10)
    // Itereaza pasii fara executie reala.
    // =========================================================
    public async Task SimulateAsync(List<StepModel> steps, CancellationToken ct = default)
    {
        if (_isRunning) return;

        _isRunning = true;
        _isDryRun  = true;

        try
        {
            OnStarted?.Invoke();
            OnStatusChanged?.Invoke("Simulare activa (Dry Run)");

            for (int i = 0; i < steps.Count; i++)
            {
                ct.ThrowIfCancellationRequested();

                var step = steps[i];
                if (step.Skip) continue;

                OnStepExecuting?.Invoke(step);
                OnProgressChanged?.Invoke(i + 1, steps.Count);
                OnStatusChanged?.Invoke($"Simulare pas {i + 1}/{steps.Count}: {step.StepType}");

                await SimulateStepAsync(step);

                OnStepFinished?.Invoke(step);
            }

            OnStatusChanged?.Invoke("Simulare finalizata");
        }
        catch (OperationCanceledException)
        {
            OnStatusChanged?.Invoke("Simulare oprita");
        }
        finally
        {
            _isRunning = false;
            _isDryRun  = false;
            OnPlaybackFinished?.Invoke(true);
        }
    }

    // =========================================================
    // ExecuteStepCoreAsync — Executia interna a unui pas
    // Desktop: DIRECT via DesktopEngine | Browser: via BrowserStepExecutor
    // =========================================================
    private async Task<(bool Success, string Error)> ExecuteStepCoreAsync(
        StepModel step, CancellationToken ct)
    {
        try
        {
            if (step.DelayBefore > 0)
                await Task.Delay(TimeSpan.FromSeconds(step.DelayBefore), ct);

            bool ok; string err = string.Empty;

            if (IsBrowserStep(step.StepType))
            {
                if (_browserExecutor == null)
                    return (false, "Browser executor nu este initializat. Instaleaza Playwright.");

                (ok, err) = await _browserExecutor.ExecuteAsync(step, ct);
            }
            else
            {
                (ok, err) = await _desktop.ExecuteStepAsync(step, ct);
            }

            if (step.DelayAfter > 0)
                await Task.Delay(TimeSpan.FromSeconds(step.DelayAfter), ct);

            return (ok, err);
        }
        catch (OperationCanceledException)
        {
            throw;
        }
        catch (Exception ex)
        {
            return (false, ex.Message);
        }
    }

    // =========================================================
    // ApplySpeed — Ajusteaza delay-urile in functie de playback speed
    // =========================================================
    private static StepModel ApplySpeed(StepModel step, double speed)
    {
        if (Math.Abs(speed - 1.0) < 0.001) return step;

        var copy = step.Clone();
        copy.DelayBefore = step.DelayBefore / speed;
        copy.DelayAfter  = step.DelayAfter  / speed;
        return copy;
    }

    // =========================================================
    // IsBrowserStep — Verifica daca pasul este de tip browser
    // =========================================================
    private static bool IsBrowserStep(string stepType) =>
        stepType.StartsWith("browser_", StringComparison.OrdinalIgnoreCase);
}
