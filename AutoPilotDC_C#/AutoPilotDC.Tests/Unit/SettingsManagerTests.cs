// ============================================================
// AutoPilotDC.Tests/Unit/SettingsManagerTests.cs
// FIX FINAL � bazat pe sursa reala SettingsManager.cs
// BuildDefaults() este public static in Infrastructure.Services
// ============================================================

using System;
using System.Collections.Generic;
using System.IO;
using AutoPilotDC.Infrastructure.Services;   // ? CRITIC: namespace corect
using AutoPilotDC.Models;
using Xunit;

namespace AutoPilotDC.Tests.Unit;

public class SettingsManagerTests : IDisposable
{
    // -- Fiecare test primeste un config.json izolat ----------
    private readonly string _tempConfig;
    private readonly SettingsManager _sm;

    public SettingsManagerTests()
    {
        // GUID unic per instanta � evita coliziuni intre teste paralele
        _tempConfig = Path.Combine(
            Path.GetTempPath(),
            $"autopilot_test_{Guid.NewGuid():N}.json");

        _sm = new SettingsManager(_tempConfig);
    }

    public void Dispose()
    {
        try { if (File.Exists(_tempConfig)) File.Delete(_tempConfig); }
        catch { }
        GC.SuppressFinalize(this);
    }

    // -- 1. Load � fisier inexistent ? defaults ---------------
    [Fact]
    public void SettingsManager_Load_NoFile_UsesDefaults()
    {
        // Fisierul nu exista ? defaults
        Assert.Equal("dark", _sm.Current.Theme);
        Assert.Equal(0.8, _sm.Current.StepDelay);
        Assert.Equal(1, _sm.Current.RepeatCount);
    }

    // -- 2. Save + Load round-trip ----------------------------
    [Fact]
    public void SettingsManager_SaveLoad_RoundTrip_PreservesValues()
    {
        _sm.Current.Theme = "light";
        _sm.Current.StepDelay = 1.5;
        _sm.Save();

        // Nou SettingsManager pe acelasi fisier
        var sm2 = new SettingsManager(_tempConfig);
        Assert.Equal("light", sm2.Current.Theme);
        Assert.Equal(1.5, sm2.Current.StepDelay);
    }

    // -- 3. Get<T> � cheie valida -----------------------------
    [Fact]
    public void SettingsManager_Get_ValidKey_ReturnsValue()
    {
        var theme = _sm.Get<string>("theme", "default");
        Assert.Equal("dark", theme);
    }

    // -- 4. Get<T> � cheie invalida ? defaultValue ------------
    [Fact]
    public void SettingsManager_Get_InvalidKey_ReturnsDefault()
    {
        var val = _sm.Get<string>("cheie_inexistenta", "fallback");
        Assert.Equal("fallback", val);
    }

    // -- 5. Set<T> + Get<T> -----------------------------------
    [Fact]
    public void SettingsManager_Set_UpdatesValue()
    {
        _sm.Set("theme", "light");
        Assert.Equal("light", _sm.Get<string>("theme", "dark"));
    }

    // -- 6. GetShortcut � chei REALE din BuildDefaults() ------
    // Lista exacta din sursa SettingsManager.cs:
    // start_rec, stop_rec, resume_play, play, pause, resume,
    // stop_play, emergency, save, new, open, add_delay, add_step,
    // delete_step, skip_step, debug_step, toggle_debug,
    // move_step_up, move_step_down, edit_step, show_shortcuts
    [Fact]
    public void SettingsManager_GetShortcut_ReturnsCorrectDefaults()
    {
        Assert.Equal("F5", _sm.GetShortcut("start_rec"));
        Assert.Equal("F6", _sm.GetShortcut("stop_rec"));
        Assert.Equal("F7", _sm.GetShortcut("play"));
        Assert.Equal("F3", _sm.GetShortcut("resume_play"));
        Assert.Equal("F8", _sm.GetShortcut("pause"));
        Assert.Equal("F8", _sm.GetShortcut("resume"));
        Assert.Equal("F9", _sm.GetShortcut("stop_play"));
        Assert.Equal("F12", _sm.GetShortcut("emergency"));
        Assert.Equal("Ctrl+S", _sm.GetShortcut("save"));
        Assert.Equal("Ctrl+N", _sm.GetShortcut("new"));
        Assert.Equal("Ctrl+O", _sm.GetShortcut("open"));
        Assert.Equal("Ctrl+D", _sm.GetShortcut("add_delay"));
        Assert.Equal("Ctrl+M", _sm.GetShortcut("add_step"));
        Assert.Equal("Delete", _sm.GetShortcut("delete_step"));
        Assert.Equal("Ctrl+K", _sm.GetShortcut("skip_step"));
        Assert.Equal("Ctrl+B", _sm.GetShortcut("debug_step"));
        Assert.Equal("Ctrl+Shift+B", _sm.GetShortcut("toggle_debug"));
        Assert.Equal("Ctrl+Up", _sm.GetShortcut("move_step_up"));
        Assert.Equal("Ctrl+Down", _sm.GetShortcut("move_step_down"));
        Assert.Equal("Ctrl+E", _sm.GetShortcut("edit_step"));
        Assert.Equal("Ctrl+H", _sm.GetShortcut("show_shortcuts"));
    }

    // -- 7. GetShortcut � cheie inexistenta ? string.Empty ----
    [Fact]
    public void SettingsManager_GetShortcut_UnknownKey_ReturnsEmpty()
    {
        var result = _sm.GetShortcut("cheie_inexistenta");
        Assert.Equal(string.Empty, result);
    }

    // -- 8. SetShortcut + GetShortcut -------------------------
    [Fact]
    public void SettingsManager_SetShortcut_UpdatesAndPersists()
    {
        _sm.SetShortcut("play", "F4");
        Assert.Equal("F4", _sm.GetShortcut("play"));

        // Verifica persistenta
        var sm2 = new SettingsManager(_tempConfig);
        Assert.Equal("F4", sm2.GetShortcut("play"));
    }

    // -- 9. BuildDefaults() � valori numerice -----------------
    // Valori EXACTE din sursa BuildDefaults():
    [Fact]
    public void SettingsManager_BuildDefaults_NumericValues_AreCorrect()
    {
        var d = SettingsManager.BuildDefaults();

        Assert.Equal(0.8, d.StepDelay);
        Assert.Equal(0.05, d.MouseMoveDelay);
        Assert.Equal(5, d.MouseMoveThreshold);
        Assert.Equal(50, d.MaxStepsWarning);
        Assert.Equal(12, d.FontSize);
        Assert.Equal(1.0, d.PlaybackSpeed);
        Assert.Equal(3, d.CountdownBeforePlay);
        Assert.Equal(1, d.RepeatCount);
        Assert.Equal(0, d.ActiveMonitor);
    }

    // -- 10. BuildDefaults() � valori bool --------------------
    [Fact]
    public void SettingsManager_BuildDefaults_BoolValues_AreCorrect()
    {
        var d = SettingsManager.BuildDefaults();

        Assert.False(d.RecordMouseMove);
        Assert.True(d.AutoSave);
        Assert.True(d.ShowFloatingControls);
        Assert.True(d.ShowEmergencyBtn);
    }

    // -- 11. BuildDefaults() � tema si shortcuts count ---------
    [Fact]
    public void SettingsManager_BuildDefaults_ThemeAndShortcuts()
    {
        var d = SettingsManager.BuildDefaults();

        Assert.Equal("dark", d.Theme);
        // 21 shortcuts definite in BuildDefaults()
        Assert.Equal(21, d.Shortcuts.Count);
        Assert.True(d.Shortcuts.ContainsKey("start_rec"));
        Assert.True(d.Shortcuts.ContainsKey("emergency"));
        Assert.False(d.Shortcuts.ContainsKey("pause_resume")); // NU exista!
    }

    // -- 12. ResetToDefaults() --------------------------------
    [Fact]
    public void SettingsManager_ResetToDefaults_RestoresAllDefaults()
    {
        // Modifica setari
        _sm.Current.Theme = "light";
        _sm.Current.StepDelay = 5.0;
        _sm.Save();

        // Reset
        _sm.ResetToDefaults();

        Assert.Equal("dark", _sm.Current.Theme);
        Assert.Equal(0.8, _sm.Current.StepDelay);
    }

    // -- 13. Thread safety � Set concurent --------------------
    [Fact]
    public void SettingsManager_Set_ConcurrentAccess_DoesNotThrow()
    {
        var threads = new System.Threading.Thread[10];
        var exceptions = new List<Exception>();
        var lockObj = new object();

        for (int i = 0; i < threads.Length; i++)
        {
            int idx = i;
            threads[idx] = new System.Threading.Thread(() =>
            {
                try { _sm.Set("font_size", idx + 8); }
                catch (Exception ex)
                {
                    lock (lockObj) exceptions.Add(ex);
                }
            });
        }

        foreach (var t in threads) t.Start();
        foreach (var t in threads) t.Join();

        Assert.Empty(exceptions);
    }
}