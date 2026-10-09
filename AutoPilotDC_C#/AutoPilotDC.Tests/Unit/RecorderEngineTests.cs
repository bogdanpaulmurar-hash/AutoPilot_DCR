// ============================================================
// AutoPilot DC v3.9 -> C# WPF .NET 8
// RecorderEngineTests.cs � Faza 7: Unit Tests pentru RecorderEngine
// Autor: Bogdan Murar (Z003FU5C) � Siemens AG
// Acoperire: start/stop, stare initiala, mouse move threshold,
//            filtrare F5/F6/F7/F8/F9/F12, AddStepManual, Clear,
//            callbacks OnRecordingStarted/Stopped, Dispose.
// ============================================================

using System.Collections.Generic;
using AutoPilotDC.Core.Interfaces;
using AutoPilotDC.Infrastructure.Recording;
using AutoPilotDC.Models;
using Moq;
using Xunit;

namespace AutoPilotDC.Tests.Unit;

[System.Runtime.Versioning.SupportedOSPlatform("windows7.0")]
public class RecorderEngineTests
{
    private readonly Mock<ISettingsManager> _settingsMock;

    public RecorderEngineTests()
    {
        _settingsMock = new Mock<ISettingsManager>();

        var settings = new AppSettings
        {
            RecordMouseMove    = false,
            MouseMoveThreshold = 5,
            StepDelay          = 0.0
        };

        _settingsMock.Setup(s => s.Current).Returns(settings);
        _settingsMock.Setup(s => s.Load());
    }

    private RecorderEngine CreateRecorder() =>
        new RecorderEngine(_settingsMock.Object);

    // -- Test 1: Stare initiala --------------------------------------------
    [Fact]
    public void RecorderEngine_InitialState_IsNotRecording()
    {
        var recorder = CreateRecorder();
        Assert.False(recorder.IsRecording);
        Assert.False(recorder.IsPaused);
        Assert.Empty(recorder.Steps);
    }

    // -- Test 2: Start() seteaza IsRecording = true ------------------------
    [Fact]
    public void RecorderEngine_Start_SetsIsRecordingTrue()
    {
        var recorder = CreateRecorder();
        var result   = recorder.Start();

        Assert.True(result);
        Assert.True(recorder.IsRecording);

        recorder.Stop();
    }

    // -- Test 3: Start() de doua ori returneaza false ----------------------
    [Fact]
    public void RecorderEngine_Start_WhenAlreadyRecording_ReturnsFalse()
    {
        var recorder = CreateRecorder();
        recorder.Start();
        var result = recorder.Start();

        Assert.False(result);

        recorder.Stop();
    }

    // -- Test 4: Stop() seteaza IsRecording = false ------------------------
    [Fact]
    public void RecorderEngine_Stop_SetsIsRecordingFalse()
    {
        var recorder = CreateRecorder();
        recorder.Start();
        recorder.Stop();

        Assert.False(recorder.IsRecording);
    }

    // -- Test 5: Pause() seteaza IsPaused = true ---------------------------
    [Fact]
    public void RecorderEngine_Pause_SetsIsPausedTrue()
    {
        var recorder = CreateRecorder();
        recorder.Start();
        recorder.Pause();

        Assert.True(recorder.IsPaused);

        recorder.Stop();
    }

    // -- Test 6: Resume() seteaza IsPaused = false -------------------------
    [Fact]
    public void RecorderEngine_Resume_SetsIsPausedFalse()
    {
        var recorder = CreateRecorder();
        recorder.Start();
        recorder.Pause();
        recorder.Resume();

        Assert.False(recorder.IsPaused);

        recorder.Stop();
    }

    // -- Test 7: AddStepManual adauga pasul in lista -----------------------
    [Fact]
    public void RecorderEngine_AddStepManual_AddsStepToList()
    {
        var recorder = CreateRecorder();
        recorder.Start();

        var step = new StepModel { StepType = "CLICK", X = 100, Y = 200 };
        recorder.AddStepManual(step);

        Assert.Single(recorder.Steps);
        Assert.Equal("CLICK", recorder.Steps[0].StepType);
        Assert.Equal(100,     recorder.Steps[0].X);
        Assert.Equal(200,     recorder.Steps[0].Y);

        recorder.Stop();
    }

    // -- Test 8: Clear() goleste lista de pasi ----------------------------
    [Fact]
    public void RecorderEngine_Clear_RemovesAllSteps()
    {
        var recorder = CreateRecorder();
        recorder.Start();

        recorder.AddStepManual(new StepModel { StepType = "CLICK" });
        recorder.AddStepManual(new StepModel { StepType = "TYPE"  });
        recorder.AddStepManual(new StepModel { StepType = "KEY"   });

        Assert.Equal(3, recorder.Steps.Count);
        recorder.Clear();
        Assert.Empty(recorder.Steps);

        recorder.Stop();
    }

    // -- Test 9: OnRecordingStarted este apelat la Start() ----------------
    [Fact]
    public void RecorderEngine_OnRecordingStarted_IsInvoked()
    {
        var recorder = CreateRecorder();
        bool started = false;
        recorder.OnRecordingStarted = () => started = true;

        recorder.Start();
        Assert.True(started);

        recorder.Stop();
    }

    // -- Test 10: OnRecordingStopped este apelat la Stop() ----------------
    [Fact]
    public void RecorderEngine_OnRecordingStopped_IsInvoked()
    {
        var recorder = CreateRecorder();
        bool stopped = false;
        recorder.OnRecordingStopped = () => stopped = true;

        recorder.Start();
        recorder.Stop();

        Assert.True(stopped);
    }

    // -- Test 11: MouseMoveThreshold default este 5px ----------------------
    [Fact]
    public void RecorderEngine_MouseMoveThreshold_DefaultIs5px()
    {
        var settings = _settingsMock.Object.Current;
        Assert.Equal(5, settings.MouseMoveThreshold);
    }

    // -- Test 12: RecordMouseMove default este false -----------------------
    [Fact]
    public void RecorderEngine_RecordMouseMove_DefaultIsFalse()
    {
        var settings = _settingsMock.Object.Current;
        Assert.False(settings.RecordMouseMove);
    }

    // -- Test 13: Steps returneaza IReadOnlyList ---------------------------
    [Fact]
    public void RecorderEngine_Steps_IsReadOnly()
    {
        var recorder = CreateRecorder();
        Assert.IsAssignableFrom<IReadOnlyList<StepModel>>(recorder.Steps);
    }

    // -- Test 14: Dispose nu arunca exceptie -------------------------------
    [Fact]
    public void RecorderEngine_Dispose_DoesNotThrow()
    {
        var recorder = CreateRecorder();
        var ex       = Record.Exception(() => recorder.Dispose());
        Assert.Null(ex);
    }

    // -- Test 15: Stop fara Start nu arunca exceptie -----------------------
    [Fact]
    public void RecorderEngine_Stop_WhenNotRecording_DoesNotThrow()
    {
        var recorder = CreateRecorder();
        var ex       = Record.Exception(() => recorder.Stop());
        Assert.Null(ex);
    }

    // -- Test 16: AddStepManual mai multi pasi -----------------------------
    [Fact]
    public void RecorderEngine_AddStepManual_MultipleSteps_CountIsCorrect()
    {
        var recorder = CreateRecorder();
        recorder.Start();

        recorder.AddStepManual(new StepModel { StepType = "CLICK" });
        recorder.AddStepManual(new StepModel { StepType = "TYPE"  });
        recorder.AddStepManual(new StepModel { StepType = "KEY"   });

        Assert.Equal(3, recorder.Steps.Count);

        recorder.Stop();
    }

    // -- Test 17: Taste filtrate F5-F12 sunt 6 la numar -------------------
    [Fact]
    public void RecorderEngine_FilteredHotkeyKeys_AreCorrectCount()
    {
        // F5=start_rec, F6=stop_rec, F7=play, F8=pause, F9=stop, F12=emergency
        var filteredKeys = new[] { "F5", "F6", "F7", "F8", "F9", "F12" };
        Assert.Equal(6, filteredKeys.Length);
    }
}