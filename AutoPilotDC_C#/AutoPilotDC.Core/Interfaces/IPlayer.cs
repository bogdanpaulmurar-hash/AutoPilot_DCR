// ============================================================
// AutoPilot DC v3.9 -> C# WPF .NET 8
// IPlayer.cs � Contract pentru PlayerEngine
// Faza 1 (original) + Faza 9/10 (SimulateAsync, LoginConfig, IsDryRun)
// COMPATIBIL cu PlayerEngine 17KB existent
// Autor: Bogdan Murar (Z003FU5C) � Siemens AG
// ============================================================

using AutoPilotDC.Models;

namespace AutoPilotDC.Core.Interfaces;

public interface IPlayer
{
    // -- State ---------------------------------------------------------
    /// <summary>True daca redarea este activa.</summary>
    bool IsRunning { get; }

    /// <summary>Alias IsPlaying � pentru compatibilitate UI Faza 9/10.</summary>
    bool IsPlaying => IsRunning;

    /// <summary>True daca redarea este in pauza.</summary>
    bool IsPaused { get; }

    /// <summary>Dry Run mode � simulare fara executie reala (Faza 10).</summary>
    bool IsDryRun { get; set; }

    // -- Callbacks originale (implementate in PlayerEngine 17KB) -------
    Action<bool>?                  OnPlaybackFinished { get; set; }
    Action<StepModel>?             OnStepExecuting    { get; set; }
    Action<StepModel, string>?     OnStepError        { get; set; }
    Func<StepModel, Task<string>>? OnQuestion         { get; set; }
    Action<int>?                   OnCountdown        { get; set; }
    Action?                        OnStarted          { get; set; }
    Action?                        OnPaused           { get; set; }
    Action?                        OnResumed          { get; set; }
    Action<int, int>?              OnIterUpdate       { get; set; }

    // -- Callbacks noi Faza 9/10 � cu default impl (alias) ------------
    /// <summary>Alias OnStarted � compatibilitate Faza 9/10.</summary>
    Action? OnPlayStarted
    {
        get => OnStarted;
        set => OnStarted = value;
    }

    /// <summary>Alias OnPlaybackFinished � compatibilitate Faza 9/10.</summary>
    Action<bool>? OnPlayFinished
    {
        get => OnPlaybackFinished;
        set => OnPlaybackFinished = value;
    }

    /// <summary>Alias OnStepExecuting � compatibilitate Faza 9/10.</summary>
    Action<StepModel>? OnStepStarted
    {
        get => OnStepExecuting;
        set => OnStepExecuting = value;
    }

    /// <summary>Apelat dupa executia cu succes a unui pas.</summary>
    Action<StepModel>? OnStepFinished    { get; set; }

    /// <summary>Apelat la schimbarea statusului (mesaj text).</summary>
    Action<string>?    OnStatusChanged   { get; set; }

    /// <summary>Apelat la actualizarea progresului (currentStep, totalSteps).</summary>
    Action<int, int>?  OnProgressChanged { get; set; }

    // -- Metode originale -----------------------------------------------
    Task PlayAsync(
        IEnumerable<StepModel> steps,
        int repeatCount = 1,
        CancellationToken cancellationToken = default);

    /// <summary>PlayAsync cu LoginConfig � Faza 9.</summary>
    Task PlayAsync(
        IEnumerable<StepModel> steps,
        int repeatCount,
        LoginConfig? loginConfig,
        CancellationToken cancellationToken = default);

    void Pause();
    void Resume();
    void Stop();

    /// <summary>EmergencyStop � alias Stop() pentru Faza 9/10.</summary>
    void EmergencyStop() => Stop();

    Task<(bool Success, string Error)> ExecuteStepAsync(StepModel step);

    /// <summary>Simulare vizuala a unui pas (fara executie reala).</summary>
    Task SimulateStepAsync(StepModel step);

    /// <summary>Simulare completa rutina � Faza 10 SimulatorEngine.</summary>
    Task SimulateAsync(List<StepModel> steps, CancellationToken ct = default);
}
