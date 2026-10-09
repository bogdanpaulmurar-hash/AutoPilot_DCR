// ============================================================
// AutoPilot DC v3.9 -> C# WPF .NET 8
// RoutineFile.cs - Container JSON pentru rutine salvate
// Compatibil cu formatul Python rutine_salvate/*.json
// ============================================================

using System.Text.Json.Serialization;

namespace AutoPilotDC.Models;

/// <summary>
/// Container pentru o rutina salvata pe disc.
/// Structura JSON este identica cu Python v3.9.
/// </summary>
public class RoutineFile
{
    [JsonPropertyName("name")]
    public string Name { get; set; } = "";

    [JsonPropertyName("description")]
    public string Description { get; set; } = "";

    [JsonPropertyName("created_at")]
    public string CreatedAt { get; set; } = "";

    [JsonPropertyName("modified_at")]
    public string ModifiedAt { get; set; } = "";

    [JsonPropertyName("version")]
    public string Version { get; set; } = "3.9";

    [JsonPropertyName("author")]
    public string Author { get; set; } = "";

    [JsonPropertyName("steps")]
    public List<StepModel> Steps { get; set; } = new();

    /// <summary>Numarul total de pasi din rutina.</summary>
    [JsonIgnore]
    public int StepCount { get; set; }
}