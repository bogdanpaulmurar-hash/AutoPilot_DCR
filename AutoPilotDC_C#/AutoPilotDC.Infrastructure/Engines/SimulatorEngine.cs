// ============================================================
// AutoPilot DC v3.9 -> C# WPF .NET 8
// SimulatorEngine.cs � Motor de simulare (Dry Run) (Faza 10)
// Itereaza pasii fara executie reala, emite events catre UI.
// Autor: Bogdan Murar (Z003FU5C) � Siemens AG
// ============================================================

using System;
using System.Collections.Generic;
using System.Threading;
using System.Threading.Tasks;
using AutoPilotDC.Core.Interfaces;
using AutoPilotDC.Models;

namespace AutoPilotDC.Infrastructure.Engines;

[System.Runtime.Versioning.SupportedOSPlatform("windows7.0")]
public class SimulatorEngine
{
    // -- Dependinte ----------------------------------------------------
    private readonly ILogRepository _log;
    private readonly DesktopEngine _desktop;

    // -- Stare interna -------------------------------------------------
    private volatile bool _isRunning;
    private volatile bool _paused;
    private CancellationTokenSource? _cts;
    private readonly SemaphoreSlim _pauseSemaphore = new(1, 1);

    // -- Manual step mode ----------------------------------------------
    private bool _manualStep;
    private readonly SemaphoreSlim _manualStepSignal = new(0, 1);

    // -- Callbacks catre UI --------------------------------------------
    public Action<StepModel>? OnStepSimulating { get; set; }
    public Action<StepModel>? OnStepSimulated { get; set; }
    public Action<bool>? OnSimulationFinished { get; set; }
    public Action<string>? OnStatusChanged { get; set; }
    public Action<int, int>? OnProgressChanged { get; set; }

    // -- Proprietati ---------------------------------------------------
    public bool IsRunning => _isRunning;
    public bool IsPaused => _paused;

    // -- Constructor ---------------------------------------------------
    public SimulatorEngine(ILogRepository log, DesktopEngine desktop)
    {
        _log = log;
        _desktop = desktop;
    }

    // =================================================================
    // SimulateAsync � Ruleaza simularea completa a rutinei
    // =================================================================
    public async Task SimulateAsync(List<StepModel> steps, CancellationToken ct = default)
    {
        if (_isRunning) return;

        _isRunning = true;
        _paused = false;
        _cts = CancellationTokenSource.CreateLinkedTokenSource(ct);

        bool success = false;

        try
        {
            OnStatusChanged?.Invoke("Simulare activa (Dry Run)");

            for (int i = 0; i < steps.Count; i++)
            {
                _cts.Token.ThrowIfCancellationRequested();

                // Pauza
                if (_paused)
                {
                    OnStatusChanged?.Invoke("Simulare in pauza...");
                    await _pauseSemaphore.WaitAsync(_cts.Token);
                    _pauseSemaphore.Release();
                    OnStatusChanged?.Invoke("Simulare reluata.");
                }

                var step = steps[i];
                if (step.Skip) continue;

                OnStepSimulating?.Invoke(step);
                OnProgressChanged?.Invoke(i + 1, steps.Count);
                OnStatusChanged?.Invoke($"Simulare pas {i + 1}/{steps.Count}: {step.StepType} @ ({step.X},{step.Y})");

                // Muta mouse-ul la coordonatele pasului (fara click)
                if (step.X > 0 || step.Y > 0)
                {
                    await Task.Run(() => DesktopEngine.MoveTo(step.X, step.Y), _cts.Token);
                }

                // Delay simulat (proportional cu delay_before)
                double delay = Math.Max(0.3, step.DelayBefore > 0 ? step.DelayBefore : 0.5);
                await Task.Delay(TimeSpan.FromSeconds(delay), _cts.Token);

                // Manual step mode � asteapta semnal NextStep
                if (_manualStep)
                {
                    OnStatusChanged?.Invoke($"Manual mode: apasa 'Next Step' pentru a continua.");
                    await _manualStepSignal.WaitAsync(_cts.Token);
                }

                // Logeaza simularea
                _log.Add(new LogEntry
                {
                    EntryId = i + 1,
                    StepId = step.StepId,
                    Action = $"[SIM] {step.StepType}",
                    Result = $"Simulat @ ({step.X},{step.Y})",
                    HasError = false,
                    Comment = step.Comment ?? string.Empty,
                    Timestamp = DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss"),
                    Iteration = 1,
                });

                OnStepSimulated?.Invoke(step);
            }

            success = true;
            OnStatusChanged?.Invoke("Simulare finalizata.");
        }
        catch (OperationCanceledException)
        {
            success = false;
            OnStatusChanged?.Invoke("Simulare anulata.");
        }
        catch (Exception ex)
        {
            success = false;
            OnStatusChanged?.Invoke($"Eroare simulare: {ex.Message}");
        }
        finally
        {
            _isRunning = false;
            _paused = false;
            OnSimulationFinished?.Invoke(success);
        }
    }

    // =================================================================
    // Pause / Resume / Stop
    // =================================================================
    public void Pause()
    {
        if (!_isRunning || _paused) return;
        _paused = true;
        // Blocheaza semaforul ca sa opreasca loop-ul
        _pauseSemaphore.Wait(0);
        OnStatusChanged?.Invoke("Simulare in pauza.");
    }

    public void Resume()
    {
        if (!_paused) return;
        _paused = false;
        _pauseSemaphore.Release();
        OnStatusChanged?.Invoke("Simulare reluata.");
    }

    public void Stop()
    {
        _cts?.Cancel();
        _paused = false;
        _isRunning = false;
        // Deblocheaza semafoarele ca sa nu ramana suspendat
        if (_pauseSemaphore.CurrentCount == 0)
            _pauseSemaphore.Release();
        if (_manualStepSignal.CurrentCount == 0)
            _manualStepSignal.Release();
        OnStatusChanged?.Invoke("Simulare oprita.");
    }

    // =================================================================
    // Manual Step Mode
    // =================================================================
    public void SetManualMode(bool enabled)
    {
        _manualStep = enabled;
    }

    public async Task NextStepAsync()
    {
        if (_manualStep && _manualStepSignal.CurrentCount == 0)
            _manualStepSignal.Release();
        await Task.CompletedTask;
    }
}