// ============================================================
// AutoPilot DC v3.9 -> C# WPF .NET 8
// LogEntry.cs - Intrare log executie, JSON-compatibil Python
// ============================================================

using System.Text.Json.Serialization;

namespace AutoPilotDC.Models;

/// <summary>
/// Reprezinta o intrare in log-ul de executie.
/// JSON keys identice cu Python v3.9.
/// </summary>
public class LogEntry
{
    [JsonPropertyName("entry_id")]
    public int EntryId { get; set; } = 0;

    [JsonPropertyName("timestamp")]
    public string Timestamp { get; set; } = "";

    [JsonPropertyName("step_id")]
    public int StepId { get; set; } = 0;

    [JsonPropertyName("action")]
    public string Action { get; set; } = "";

    [JsonPropertyName("result")]
    public string Result { get; set; } = "";

    [JsonPropertyName("has_error")]
    public bool HasError { get; set; } = false;

    [JsonPropertyName("error_msg")]
    public string ErrorMsg { get; set; } = "";

    [JsonPropertyName("comment")]
    public string Comment { get; set; } = "";

    [JsonPropertyName("duration_ms")]
    public double DurationMs { get; set; } = 0.0;

    [JsonPropertyName("iteration")]
    public int Iteration { get; set; } = 0;

    public override string ToString() =>
        $"[{EntryId}] {Timestamp} | Step#{StepId} | {Action} -> {Result}";
}