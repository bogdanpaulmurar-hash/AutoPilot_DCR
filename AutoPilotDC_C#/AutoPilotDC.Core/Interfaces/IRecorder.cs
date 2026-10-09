// ============================================================
// AutoPilot DC v3.9 -> C# WPF .NET 8
// IRecorder.cs - Contract pentru RecorderEngine
// Echivalent Python: RecorderEngine
// ============================================================

using AutoPilotDC.Models;

namespace AutoPilotDC.Core.Interfaces;

/// <summary>
/// Contract pentru motorul de inregistrare mouse + tastatura.
/// </summary>
public interface IRecorder
{
    /// <summary>True daca inregistrarea este activa.</summary>
    bool IsRecording { get; }

    /// <summary>True daca inregistrarea este in pauza.</summary>
    bool IsPaused { get; }

    /// <summary>Callback apelat la fiecare pas inregistrat.</summary>
    Action<StepModel>? OnStepRecorded { get; set; }

    /// <summary>Callback apelat la start inregistrare.</summary>
    Action? OnRecordingStarted { get; set; }

    /// <summary>Callback apelat la stop inregistrare.</summary>
    Action? OnRecordingStopped { get; set; }

    /// <summary>Porneste inregistrarea. Returneaza false daca deja activa.</summary>
    bool Start();

    /// <summary>Opreste inregistrarea.</summary>
    void Stop();

    /// <summary>Pune inregistrarea in pauza.</summary>
    void Pause();

    /// <summary>Reia inregistrarea din pauza.</summary>
    void Resume();

    /// <summary>Sterge toti pasii inregistrati.</summary>
    void Clear();

    /// <summary>Returneaza lista curenta de pasi.</summary>
    IReadOnlyList<StepModel> GetSteps();

    /// <summary>Seteaza pasii (la incarcare rutina).</summary>
    void SetSteps(IEnumerable<StepModel> steps);

    /// <summary>Adauga un pas manual (din Step Builder).</summary>
    void AddStepManual(StepModel step);
}