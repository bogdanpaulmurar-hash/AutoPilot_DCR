// ============================================================
// AutoPilot DC v3.9 -> C# WPF .NET 8
// AutomationException.cs - Exceptii motor automatizare
// Echivalent Python: AutomationError, UnsupportedStepError
// ============================================================

namespace AutoPilotDC.Core.Exceptions;

/// <summary>
/// Exceptie de baza pentru erori de automatizare.
/// Echivalent Python: AutomationError.
/// </summary>
public class AutomationException : Exception
{
    public AutomationException(string message) : base(message) { }
    public AutomationException(string message, Exception inner) : base(message, inner) { }
}

/// <summary>
/// Aruncata cand niciun motor nu suporta tipul de pas dat.
/// Echivalent Python: UnsupportedStepError.
/// </summary>
public class UnsupportedStepException : AutomationException
{
    public string StepType { get; }

    public UnsupportedStepException(string stepType)
        : base($"No engine supports step type: '{stepType}'")
    {
        StepType = stepType;
    }
}

/// <summary>
/// Aruncata cand un motor necesar nu este disponibil.
/// </summary>
public class EngineNotAvailableException : AutomationException
{
    public string EngineType { get; }

    public EngineNotAvailableException(string engineType)
        : base($"Engine '{engineType}' is not available on this system.")
    {
        EngineType = engineType;
    }
}