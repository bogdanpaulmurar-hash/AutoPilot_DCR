// ============================================================
// AutoPilot DC v3.9 -> C# WPF .NET 8
// StepModel.cs - Model atomic RPA step, JSON-compatibil Python
// Autor: Bogdan Murar (Z003FU5C) - Siemens AG
// IMPORTANT: JSON keys sunt snake_case pentru compatibilitate
//            cu rutinele salvate in Python v3.9
// ============================================================

using System.Text.Json.Serialization;

namespace AutoPilotDC.Models;

/// <summary>
/// Reprezinta un pas atomic dintr-o rutina RPA.
/// Fiecare pas este serializabil in JSON pentru persistenta.
/// JSON keys sunt identice cu Python v3.9 (snake_case).
/// </summary>
public class StepModel
{
    // -- 3.1 Identificare ----------------------------------------
    [JsonPropertyName("step_id")]
    public int StepId { get; set; } = 0;

    [JsonPropertyName("step_type")]
    public string StepType { get; set; } = "CLICK";

    [JsonPropertyName("description")]
    public string Description { get; set; } = "";

    // -- 3.2 Coordonate si mouse ---------------------------------
    [JsonPropertyName("x")]
    public int X { get; set; } = 0;

    [JsonPropertyName("y")]
    public int Y { get; set; } = 0;

    /// <summary>left / right / middle</summary>
    [JsonPropertyName("button")]
    public string Button { get; set; } = "left";

    /// <summary>single / double / triple / right</summary>
    [JsonPropertyName("click_type")]
    public string ClickType { get; set; } = "single";

    // -- 3.3 Tastatura -------------------------------------------
    [JsonPropertyName("key_combo")]
    public string KeyCombo { get; set; } = "";

    [JsonPropertyName("text_input")]
    public string TextInput { get; set; } = "";

    // -- 3.4 Scroll ----------------------------------------------
    [JsonPropertyName("scroll_dx")]
    public int ScrollDx { get; set; } = 0;

    [JsonPropertyName("scroll_dy")]
    public int ScrollDy { get; set; } = 0;

    // -- 3.5 Timing ----------------------------------------------
    [JsonPropertyName("delay_before")]
    public double DelayBefore { get; set; } = 0.0;

    [JsonPropertyName("delay_after")]
    public double DelayAfter { get; set; } = 0.0;

    // -- 3.6 Control flux ----------------------------------------
    [JsonPropertyName("skip")]
    public bool Skip { get; set; } = false;

    [JsonPropertyName("monitor_id")]
    public int MonitorId { get; set; } = 0;

    // -- 3.7 Locator vizual --------------------------------------
    [JsonPropertyName("locator_image")]
    public string LocatorImage { get; set; } = "";

    // -- 3.8 Date extrase/asteptate ------------------------------
    [JsonPropertyName("expected_value")]
    public string ExpectedValue { get; set; } = "";

    /// <summary>
    /// IMPORTANT: campul corect este "extracted_value"
    /// NU "actual_value" cum apare in documente vechi!
    /// </summary>
    [JsonPropertyName("extracted_value")]
    public string ExtractedValue { get; set; } = "";

    // -- 3.9 Intrebare user --------------------------------------
    [JsonPropertyName("question_text")]
    public string QuestionText { get; set; } = "";

    /// <summary>Default: "Continua,Opreste,Sari"</summary>
    [JsonPropertyName("question_buttons")]
    public string QuestionButtons { get; set; } = "Continua,Opreste,Sari";

    // -- 3.10 Stare executie -------------------------------------
    [JsonPropertyName("has_error")]
    public bool HasError { get; set; } = false;

    [JsonPropertyName("error_message")]
    public string ErrorMessage { get; set; } = "";

    [JsonPropertyName("comment")]
    public string Comment { get; set; } = "";

    [JsonPropertyName("timestamp")]
    public string Timestamp { get; set; } = "";

    // -- 3.11 Context la inregistrare (sistemul de preventie) ----
    // Identic in Python v3.9+: aceleasi chei JSON, acelasi format de semnatura.

    /// <summary>Titlul ferestrei in care s-a dat click / s-a tastat la inregistrare.</summary>
    [JsonPropertyName("window_title")]
    public string WindowTitle { get; set; } = "";

    /// <summary>Procesul ferestrei (ex: excel.exe) la inregistrare.</summary>
    [JsonPropertyName("window_process")]
    public string WindowProcess { get; set; } = "";

    /// <summary>Amprenta zonei de 40x40 px din jurul click-ului (20x20 tonuri de gri, base64).</summary>
    [JsonPropertyName("screen_signature")]
    public string ScreenSignature { get; set; } = "";

    /// <summary>true = sistemul de preventie nu mai verifica acest pas.</summary>
    [JsonPropertyName("guard_ignore")]
    public bool GuardIgnore { get; set; } = false;

    // -- Metode helper -------------------------------------------

    /// <summary>
    /// Returneaza tipul formatat pentru afisare in UI.
    /// Identic cu Python get_display_type().
    /// NOTE: Label map-ul complet este in AppConstants.StepTypeLabels (AutoPilotDC.UI).
    ///       Aceasta metoda ofera un fallback simplu fara dependenta circulara.
    /// </summary>
    public string GetDisplayType()
    {
        return StepType switch
        {
            "CLICK"              => "Click",
            "DBLCLICK"           => "Double Click",
            "RIGHTCLICK"         => "Right Click",
            "KEY"                => "Key Press",
            "TYPE"               => "Type Text",
            "SCROLL"             => "Scroll",
            "MOVE"               => "Mouse Move",
            "DELAY"              => "Delay",
            "SCREENSHOT"         => "Screenshot",
            "QUESTION"           => "Question",
            "browser_open"       => "Browser: Open",
            "browser_navigate"   => "Browser: Navigate",
            "browser_click"      => "Browser: Click",
            "browser_fill"       => "Browser: Fill",
            "browser_wait"       => "Browser: Wait",
            "browser_screenshot" => "Browser: Screenshot",
            "browser_close"      => "Browser: Close",
            _                    => StepType,
        };
    }

    /// <summary>
    /// Creeaza o copie independenta a pasului (deep clone).
    /// </summary>
    public StepModel Clone() => new()
    {
        StepId          = StepId,
        StepType        = StepType,
        Description     = Description,
        X               = X,
        Y               = Y,
        Button          = Button,
        ClickType       = ClickType,
        KeyCombo        = KeyCombo,
        TextInput       = TextInput,
        ScrollDx        = ScrollDx,
        ScrollDy        = ScrollDy,
        DelayBefore     = DelayBefore,
        DelayAfter      = DelayAfter,
        Skip            = Skip,
        MonitorId       = MonitorId,
        LocatorImage    = LocatorImage,
        ExpectedValue   = ExpectedValue,
        ExtractedValue  = ExtractedValue,
        QuestionText    = QuestionText,
        QuestionButtons = QuestionButtons,
        HasError        = HasError,
        ErrorMessage    = ErrorMessage,
        Comment         = Comment,
        Timestamp       = Timestamp,
        WindowTitle     = WindowTitle,
        WindowProcess   = WindowProcess,
        ScreenSignature = ScreenSignature,
        GuardIgnore     = GuardIgnore,
    };

    public override string ToString() =>
        $"[{StepId}] {StepType} @ ({X},{Y}) - {Description}";
}