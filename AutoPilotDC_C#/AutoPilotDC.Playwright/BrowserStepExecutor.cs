// ============================================================
// AutoPilot DC v3.9 -> C# WPF .NET 8
// BrowserStepExecutor.cs � Dispatcher + Simulation pentru browser steps
// Echivalent Python: automation/dispatcher.py + BrowserAutomationEngine
// Autor: Bogdan Murar (Z003FU5C) � Siemens AG
// ============================================================

using System;
using System.Threading;
using System.Threading.Tasks;
using AutoPilotDC.Core.Interfaces;
using AutoPilotDC.Models;

namespace AutoPilotDC.Playwright;

/// <summary>
/// Executor specializat pentru browser steps.
/// Implementeaza Strategy Pattern � routing browser_* steps catre PlaywrightEngine.
/// Suporta si modul SIMULATION (fara executie reala, doar log vizual).
/// Echivalent Python: AutomationDispatcher + BrowserAutomationEngine
/// </summary>
[System.Runtime.Versioning.SupportedOSPlatform("windows7.0")]
public sealed class BrowserStepExecutor : IAsyncDisposable
{
    // -- Engine ------------------------------------------------
    private readonly PlaywrightEngine _engine;

    // -- Simulation mode ---------------------------------------
    private bool _simulationMode;

    // -- Callbacks ---------------------------------------------
    /// <summary>Apelat inainte de executia unui step browser.</summary>
    public Action<StepModel>? OnStepExecuting { get; set; }

    /// <summary>Apelat dupa executia cu succes.</summary>
    public Action<StepModel>? OnStepExecuted { get; set; }

    /// <summary>Apelat la eroare.</summary>
    public Action<StepModel, string>? OnStepError { get; set; }

    /// <summary>Apelat in modul simulare (in loc de executie reala).</summary>
    public Action<StepModel>? OnStepSimulated { get; set; }

    // -- Constructor -------------------------------------------
    public BrowserStepExecutor(PlaywrightEngine engine)
    {
        _engine = engine ?? throw new ArgumentNullException(nameof(engine));
    }

    // =========================================================
    // SetSimulationMode � Activa/dezactiva modul SIMULATION
    // In modul simulare: pasii browser sunt logati dar NU executati.
    // Echivalent Python: modul SIMULATION din ModeIndicatorOverlay
    // =========================================================
    public void SetSimulationMode(bool enabled)
    {
        _simulationMode = enabled;
    }

    public bool IsSimulationMode => _simulationMode;

    // =========================================================
    // ExecuteAsync � Executa sau simuleaza un browser step
    // =========================================================
    public async Task<(bool Success, string Error)> ExecuteAsync(
        StepModel step,
        CancellationToken ct = default)
    {
        if (step == null) return (false, "Step null.");

        // Verifica daca e browser step
        if (!_engine.SupportsStep(step))
            return (false, $"BrowserStepExecutor: step '{step.StepType}' nu este browser step.");

        OnStepExecuting?.Invoke(step);

        // -- SIMULATION MODE -----------------------------------
        if (_simulationMode)
        {
            return await SimulateAsync(step, ct);
        }

        // -- EXECUTIE REALA ------------------------------------
        try
        {
            var (success, error) = await _engine.ExecuteStepAsync(step, ct);

            if (success)
                OnStepExecuted?.Invoke(step);
            else
                OnStepError?.Invoke(step, error);

            return (success, error);
        }
        catch (OperationCanceledException)
        {
            return (false, "Anulat.");
        }
        catch (Exception ex)
        {
            OnStepError?.Invoke(step, ex.Message);
            return (false, ex.Message);
        }
    }

    // =========================================================
    // SimulateAsync � Simulare browser step (fara executie reala)
    // Afiseaza ce ar face pasul, asteapta timing-ul, notifica UI.
    // Echivalent Python: _rec_simulate_step() + ModeIndicatorOverlay SIMULATION
    // =========================================================
    private async Task<(bool Success, string Error)> SimulateAsync(
        StepModel step, CancellationToken ct)
    {
        // Simuleaza delay_before
        if (step.DelayBefore > 0)
            await Task.Delay(TimeSpan.FromSeconds(step.DelayBefore), ct);

        // Timp vizual minim de simulare (150ms � identic cu desktop SimulateStepAsync)
        await Task.Delay(150, ct);

        // Notifica UI ca pasul a fost simulat
        OnStepSimulated?.Invoke(step);

        // Simuleaza delay_after
        if (step.DelayAfter > 0)
            await Task.Delay(TimeSpan.FromSeconds(step.DelayAfter), ct);

        return (true, string.Empty);
    }

    // =========================================================
    // IsAvailable � Verifica disponibilitatea Playwright
    // =========================================================
    public bool IsAvailable => _engine.IsAvailable;

    // =========================================================
    // IsOpen � Browserul este deschis si activ
    // =========================================================
    public bool IsOpen => _engine.IsOpen;

    // =========================================================
    // IAsyncDisposable
    // =========================================================
    public async ValueTask DisposeAsync()
    {
        await _engine.DisposeAsync();
    }
}
