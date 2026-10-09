// ============================================================
// AutoPilot DC v3.9 -> C# WPF .NET 8
// IAutomationEngine.cs - Contract pentru motoarele de executie
// Echivalent Python: AbstractAutomationEngine (ABC)
// ============================================================

using AutoPilotDC.Models;

namespace AutoPilotDC.Core.Interfaces;

/// <summary>
/// Contract de baza pentru toate motoarele de automatizare.
/// Echivalent cu AbstractAutomationEngine din Python v3.9.
/// </summary>
public interface IAutomationEngine
{
    /// <summary>Tipul motorului: "desktop", "browser", "future"</summary>
    string EngineType { get; }

    /// <summary>True daca motorul este disponibil pe sistemul curent.</summary>
    bool IsAvailable { get; }

    /// <summary>True daca motorul poate executa tipul de pas dat.</summary>
    bool SupportsStep(StepModel step);

    /// <summary>
    /// Executa un pas si returneaza (success, errorMessage).
    /// </summary>
    Task<(bool Success, string Error)> ExecuteStepAsync(
        StepModel step,
        CancellationToken cancellationToken = default);
}