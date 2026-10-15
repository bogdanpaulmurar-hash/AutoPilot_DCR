// ============================================================
// AutoPilot DC v3.9 -> C# WPF .NET 8
// AppSettings.cs - Configurare persistenta (config.json)
// Identic cu SettingsManager.DEFAULTS din Python v3.9
// ============================================================

using System.Text.Json.Serialization;

namespace AutoPilotDC.Models;

/// <summary>
/// Setarile aplicatiei, persistate in config.json.
/// Valorile default sunt identice cu Python SettingsManager.DEFAULTS.
/// </summary>
public class AppSettings
{
    // -- Tema ------------------------------------------------
    [JsonPropertyName("theme")]
    public string Theme { get; set; } = "dark";

    // -- Timing ----------------------------------------------
    [JsonPropertyName("step_delay")]
    public double StepDelay { get; set; } = 0.8;

    [JsonPropertyName("mouse_move_delay")]
    public double MouseMoveDelay { get; set; } = 0.05;

    // -- Recorder --------------------------------------------
    [JsonPropertyName("record_mouse_move")]
    public bool RecordMouseMove { get; set; } = false;

    [JsonPropertyName("mouse_move_threshold")]
    public int MouseMoveThreshold { get; set; } = 5;

    // -- Shortcut-uri ----------------------------------------
    [JsonPropertyName("shortcuts")]
    public Dictionary<string, string> Shortcuts { get; set; } = new()
    {
        ["start_rec"]      = "F5",
        ["stop_rec"]       = "F6",
        ["play"]           = "F7",
        ["resume_play"]    = "F3",
        ["pause"]          = "F8",
        ["stop_play"]      = "F9",
        ["emergency"]      = "F12",
        ["save"]           = "Ctrl+S",
        ["new"]            = "Ctrl+N",
        ["open"]           = "Ctrl+O",
        ["add_delay"]      = "Ctrl+D",
        ["add_step"]       = "Ctrl+M",
        ["delete_step"]    = "Delete",
        ["skip_step"]      = "Ctrl+K",
        ["debug_step"]     = "Ctrl+B",
        ["toggle_debug"]   = "Ctrl+Shift+B",
        ["move_step_up"]   = "Ctrl+Up",
        ["move_step_down"] = "Ctrl+Down",
        ["edit_step"]      = "Ctrl+E",
        ["show_shortcuts"] = "Ctrl+H",
    };

    // -- Avertizari ------------------------------------------
    [JsonPropertyName("max_steps_warning")]
    public int MaxStepsWarning { get; set; } = 50;

    // -- Auto-save -------------------------------------------
    [JsonPropertyName("auto_save")]
    public bool AutoSave { get; set; } = false;

    // -- Font ------------------------------------------------
    [JsonPropertyName("font_size")]
    public int FontSize { get; set; } = 11;

    // -- Playback --------------------------------------------
    [JsonPropertyName("playback_speed")]
    public double PlaybackSpeed { get; set; } = 1.0;

    [JsonPropertyName("countdown_before_play")]
    public int CountdownBeforePlay { get; set; } = 3;

    [JsonPropertyName("repeat_count")]
    public int RepeatCount { get; set; } = 1;

    // -- UI --------------------------------------------------
    [JsonPropertyName("show_floating_controls")]
    public bool ShowFloatingControls { get; set; } = true;

    [JsonPropertyName("show_emergency_btn")]
    public bool ShowEmergencyBtn { get; set; } = true;

    [JsonPropertyName("active_monitor")]
    public int ActiveMonitor { get; set; } = 0;

    // -- Siguranta la rulare (v4.1) ---------------------------
    /// <summary>Activeaza "Nu deranja" (fara notificari Windows) cat timp ruleaza sau inregistreaza.</summary>
    [JsonPropertyName("dnd_during_run")]
    public bool DndDuringRun { get; set; } = true;

    /// <summary>Chenar colorat pe ecran: rosu + RUN la rulare, verde + REC la inregistrare.</summary>
    [JsonPropertyName("show_run_frame")]
    public bool ShowRunFrame { get; set; } = true;

    /// <summary>Sistemul de preventie: pauza + intrebare cand ecranul difera de inregistrare.</summary>
    [JsonPropertyName("guard_enabled")]
    public bool GuardEnabled { get; set; } = true;

    /// <summary>relaxed / normal / strict — cat de mult poate diferi ecranul fata de inregistrare.</summary>
    [JsonPropertyName("guard_sensitivity")]
    public string GuardSensitivity { get; set; } = "normal";
}