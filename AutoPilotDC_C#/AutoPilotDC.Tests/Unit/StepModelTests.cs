// ============================================================
// AutoPilot DC v3.9 -> C# WPF .NET 8
// StepModelTests.cs - Faza 7: Unit Tests pentru StepModel
// Autor: Bogdan Murar (Z003FU5C) - Siemens AG
// ============================================================

using System.Text.Json;
using AutoPilotDC.Models;
using Xunit;

namespace AutoPilotDC.Tests.Unit;

public class StepModelTests
{
    // Test 1: Valori default corecte
    [Fact]
    public void StepModel_DefaultValues_AreCorrect()
    {
        var step = new StepModel();

        Assert.Equal("CLICK",                 step.StepType);
        Assert.Equal(0,                       step.StepId);
        Assert.Equal("",                      step.Description);
        Assert.Equal(0,                       step.X);
        Assert.Equal(0,                       step.Y);
        Assert.Equal("left",                  step.Button);
        Assert.Equal("single",                step.ClickType);
        Assert.Equal("",                      step.KeyCombo);
        Assert.Equal("",                      step.TextInput);
        Assert.Equal(0,                       step.ScrollDx);
        Assert.Equal(0,                       step.ScrollDy);
        Assert.Equal(0.0,                     step.DelayBefore);
        Assert.Equal(0.0,                     step.DelayAfter);
        Assert.False(step.Skip);
        Assert.Equal(0,                       step.MonitorId);
        Assert.Equal("",                      step.LocatorImage);
        Assert.Equal("",                      step.ExpectedValue);
        Assert.Equal("",                      step.ExtractedValue);  // NU actual_value!
        Assert.Equal("",                      step.QuestionText);
        Assert.Equal("Continua,Opreste,Sari", step.QuestionButtons);
        Assert.False(step.HasError);
        Assert.Equal("",                      step.ErrorMessage);
        Assert.Equal("",                      step.Comment);
        Assert.Equal("",                      step.Timestamp);
    }

    // Test 2: JSON round-trip pastreaza toate campurile
    [Fact]
    public void StepModel_JsonRoundTrip_PreservesAllFields()
    {
        var original = new StepModel
        {
            StepId          = 7,
            StepType        = "TYPE",
            Description     = "Scrie text",
            X               = 150,
            Y               = 300,
            Button          = "left",
            ClickType       = "single",
            KeyCombo        = "",
            TextInput       = "Hello AutoPilot",
            ScrollDx        = 0,
            ScrollDy        = -3,
            DelayBefore     = 0.8,
            DelayAfter      = 0.2,
            Skip            = false,
            MonitorId       = 0,
            LocatorImage    = "btn.png",
            ExpectedValue   = "expected",
            ExtractedValue  = "extracted",
            QuestionText    = "Continui?",
            QuestionButtons = "Da,Nu",
            HasError        = false,
            ErrorMessage    = "",
            Comment         = "test comment",
            Timestamp       = "2026-06-16T10:00:00"
        };

        var json     = JsonSerializer.Serialize(original);
        var restored = JsonSerializer.Deserialize<StepModel>(json);

        Assert.NotNull(restored);
        Assert.Equal(original.StepId,          restored!.StepId);
        Assert.Equal(original.StepType,        restored.StepType);
        Assert.Equal(original.Description,     restored.Description);
        Assert.Equal(original.X,               restored.X);
        Assert.Equal(original.Y,               restored.Y);
        Assert.Equal(original.Button,          restored.Button);
        Assert.Equal(original.ClickType,       restored.ClickType);
        Assert.Equal(original.TextInput,       restored.TextInput);
        Assert.Equal(original.ScrollDy,        restored.ScrollDy);
        Assert.Equal(original.DelayBefore,     restored.DelayBefore);
        Assert.Equal(original.DelayAfter,      restored.DelayAfter);
        Assert.Equal(original.Skip,            restored.Skip);
        Assert.Equal(original.LocatorImage,    restored.LocatorImage);
        Assert.Equal(original.ExpectedValue,   restored.ExpectedValue);
        Assert.Equal(original.ExtractedValue,  restored.ExtractedValue);
        Assert.Equal(original.QuestionText,    restored.QuestionText);
        Assert.Equal(original.QuestionButtons, restored.QuestionButtons);
        Assert.Equal(original.Comment,         restored.Comment);
        Assert.Equal(original.Timestamp,       restored.Timestamp);
    }

    // Test 3: JSON keys sunt snake_case (compatibil Python v3.9)
    [Fact]
    public void StepModel_JsonKeys_ArePythonCompatible()
    {
        var step = new StepModel
        {
            StepId         = 42,
            StepType       = "CLICK",
            X              = 100,
            Y              = 200,
            ExtractedValue = "result"
        };

        var json = JsonSerializer.Serialize(step);

        Assert.Contains("\"step_id\":42",          json);
        Assert.Contains("\"step_type\":\"CLICK\"", json);
        Assert.Contains("\"x\":100",               json);
        Assert.Contains("\"y\":200",               json);
        Assert.Contains("\"extracted_value\"",     json);
        Assert.DoesNotContain("actual_value",        json);  // REGULA CRITICA
        Assert.Contains("\"delay_before\"",        json);
        Assert.Contains("\"delay_after\"",         json);
        Assert.Contains("\"question_buttons\"",    json);
        Assert.Contains("\"key_combo\"",           json);
        Assert.Contains("\"text_input\"",          json);
        Assert.Contains("\"scroll_dx\"",           json);
        Assert.Contains("\"scroll_dy\"",           json);
        Assert.Contains("\"locator_image\"",       json);
        Assert.Contains("\"expected_value\"",      json);
        Assert.Contains("\"monitor_id\"",          json);
        Assert.Contains("\"has_error\"",           json);
        Assert.Contains("\"error_message\"",       json);
    }

    // Test 4: ExtractedValue este campul corect (NU actual_value)
    [Fact]
    public void StepModel_ExtractedValue_FieldExists_NotActualValue()
    {
        var step = new StepModel { ExtractedValue = "valoare_extrasa" };

        Assert.Equal("valoare_extrasa", step.ExtractedValue);

        var json = JsonSerializer.Serialize(step);
        Assert.Contains("\"extracted_value\":\"valoare_extrasa\"", json);
        Assert.DoesNotContain("actual_value", json);
    }

    // Test 5: QuestionButtons default este "Continua,Opreste,Sari"
    [Fact]
    public void StepModel_QuestionButtons_DefaultIsCorrect()
    {
        var step    = new StepModel();
        var buttons = step.QuestionButtons.Split(',');

        Assert.Equal(3,          buttons.Length);
        Assert.Equal("Continua", buttons[0]);
        Assert.Equal("Opreste",  buttons[1]);
        Assert.Equal("Sari",     buttons[2]);
    }

    // Test 6: Skip si HasError default sunt false
    [Fact]
    public void StepModel_BoolDefaults_AreFalse()
    {
        var step = new StepModel();
        Assert.False(step.Skip);
        Assert.False(step.HasError);
    }

    // Test 7: Timing fields accepta valori valide
    [Fact]
    public void StepModel_TimingFields_AcceptValidValues()
    {
        var step = new StepModel { DelayBefore = 0.8, DelayAfter = 0.5 };
        Assert.Equal(0.8, step.DelayBefore);
        Assert.Equal(0.5, step.DelayAfter);
    }

    // Test 8: GetDisplayType - toate tipurile desktop (10 tipuri)
    [Theory]
    [InlineData("CLICK",      "Click")]
    [InlineData("DBLCLICK",   "Double Click")]
    [InlineData("RIGHTCLICK", "Right Click")]
    [InlineData("KEY",        "Key Press")]
    [InlineData("TYPE",       "Type Text")]
    [InlineData("SCROLL",     "Scroll")]
    [InlineData("MOVE",       "Mouse Move")]
    [InlineData("DELAY",      "Delay")]
    [InlineData("SCREENSHOT", "Screenshot")]
    [InlineData("QUESTION",   "Question")]
    public void StepModel_GetDisplayType_Desktop_ReturnsCorrectLabel(
        string stepType, string expected)
    {
        var step = new StepModel { StepType = stepType };
        Assert.Equal(expected, step.GetDisplayType());
    }

    // Test 9: GetDisplayType - toate tipurile browser (7 tipuri)
    [Theory]
    [InlineData("browser_open",       "Browser: Open")]
    [InlineData("browser_navigate",   "Browser: Navigate")]
    [InlineData("browser_click",      "Browser: Click")]
    [InlineData("browser_fill",       "Browser: Fill")]
    [InlineData("browser_wait",       "Browser: Wait")]
    [InlineData("browser_screenshot", "Browser: Screenshot")]
    [InlineData("browser_close",      "Browser: Close")]
    public void StepModel_GetDisplayType_Browser_ReturnsCorrectLabel(
        string stepType, string expected)
    {
        var step = new StepModel { StepType = stepType };
        Assert.Equal(expected, step.GetDisplayType());
    }

    // Test 10: GetDisplayType - tip necunoscut returneaza tipul brut
    [Fact]
    public void StepModel_GetDisplayType_Unknown_ReturnsRawType()
    {
        var step = new StepModel { StepType = "CUSTOM_STEP" };
        Assert.Equal("CUSTOM_STEP", step.GetDisplayType());
    }

    // Test 11: Clone produce o copie independenta
    [Fact]
    public void StepModel_Clone_ProducesIndependentCopy()
    {
        var original = new StepModel
        {
            StepId         = 5,
            StepType       = "CLICK",
            X              = 100,
            Y              = 200,
            Description    = "Original",
            ExtractedValue = "val",
            DelayBefore    = 0.5,
            DelayAfter     = 0.3
        };

        var clone = original.Clone();

        Assert.Equal(original.StepId,         clone.StepId);
        Assert.Equal(original.StepType,       clone.StepType);
        Assert.Equal(original.X,              clone.X);
        Assert.Equal(original.Y,              clone.Y);
        Assert.Equal(original.Description,    clone.Description);
        Assert.Equal(original.ExtractedValue, clone.ExtractedValue);
        Assert.Equal(original.DelayBefore,    clone.DelayBefore);
        Assert.Equal(original.DelayAfter,     clone.DelayAfter);

        // Modificarea clonei NU afecteaza originalul
        clone.Description = "Modificat";
        clone.X           = 999;
        Assert.Equal("Original", original.Description);
        Assert.Equal(100,        original.X);
    }

    // Test 12: ToString contine informatii relevante
    [Fact]
    public void StepModel_ToString_ContainsKeyInfo()
    {
        var step = new StepModel { StepId = 3, StepType = "CLICK", Description = "Test" };
        var str  = step.ToString();

        Assert.Contains("3",     str);
        Assert.Contains("CLICK", str);
    }

    // Test 13: browser_navigate se serializeaza corect
    [Fact]
    public void StepModel_BrowserStepType_SerializesCorrectly()
    {
        var step = new StepModel
        {
            StepType    = "browser_navigate",
            Description = "url=https://siemens.com"
        };

        var json = JsonSerializer.Serialize(step);
        Assert.Contains("\"step_type\":\"browser_navigate\"", json);
        Assert.DoesNotContain("actual_value", json);
    }

    // Test 14: Deserializare din JSON Python-style
    [Fact]
    public void StepModel_Deserialize_FromPythonStyleJson()
    {
        // JSON identic cu ce genereaza Python v3.9
        const string json = "{" +
            "\"step_id\": 1," +
            "\"step_type\": \"CLICK\"," +
            "\"description\": \"Click buton\"," +
            "\"x\": 500," +
            "\"y\": 300," +
            "\"button\": \"left\"," +
            "\"click_type\": \"single\"," +
            "\"key_combo\": \"\"," +
            "\"text_input\": \"\"," +
            "\"scroll_dx\": 0," +
            "\"scroll_dy\": 0," +
            "\"delay_before\": 0.8," +
            "\"delay_after\": 0.0," +
            "\"skip\": false," +
            "\"monitor_id\": 0," +
            "\"locator_image\": \"\"," +
            "\"expected_value\": \"\"," +
            "\"extracted_value\": \"\"," +
            "\"question_text\": \"\"," +
            "\"question_buttons\": \"Continua,Opreste,Sari\"," +
            "\"has_error\": false," +
            "\"error_message\": \"\"," +
            "\"comment\": \"\"," +
            "\"timestamp\": \"\"" +
            "}";

        var step = JsonSerializer.Deserialize<StepModel>(json);

        Assert.NotNull(step);
        Assert.Equal(1,                       step!.StepId);
        Assert.Equal("CLICK",                 step.StepType);
        Assert.Equal("Click buton",           step.Description);
        Assert.Equal(500,                     step.X);
        Assert.Equal(300,                     step.Y);
        Assert.Equal("left",                  step.Button);
        Assert.Equal(0.8,                     step.DelayBefore);
        Assert.Equal("Continua,Opreste,Sari", step.QuestionButtons);
        Assert.False(step.Skip);
        Assert.False(step.HasError);
        Assert.Equal("",                      step.ExtractedValue);
    }

    // Test 15: Toate 17 ALL_STEP_TYPES sunt valide ca StepType
    [Theory]
    [InlineData("CLICK")]
    [InlineData("DBLCLICK")]
    [InlineData("RIGHTCLICK")]
    [InlineData("KEY")]
    [InlineData("TYPE")]
    [InlineData("SCROLL")]
    [InlineData("MOVE")]
    [InlineData("DELAY")]
    [InlineData("SCREENSHOT")]
    [InlineData("QUESTION")]
    [InlineData("browser_open")]
    [InlineData("browser_navigate")]
    [InlineData("browser_click")]
    [InlineData("browser_fill")]
    [InlineData("browser_wait")]
    [InlineData("browser_screenshot")]
    [InlineData("browser_close")]
    public void StepModel_AllStepTypes_AreValid(string stepType)
    {
        var step = new StepModel { StepType = stepType };
        Assert.Equal(stepType, step.StepType);

        var json = JsonSerializer.Serialize(step);
        Assert.NotEmpty(json);
        Assert.Contains(stepType, json);
    }
}