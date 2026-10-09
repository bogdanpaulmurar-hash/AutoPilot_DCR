// ============================================================
// AutoPilot DC v3.9 ? C# WPF .NET 8
// AutoPilotDC.Tests/Unit/PlayerEngineTests.cs
// Faza 7 � Tests (xUnit + Moq)
// API real PlayerEngine:
//   IsRunning (nu IsPlaying), IsPaused
//   OnStepExecuting (Action<StepModel>)
//   OnPlaybackFinished (Action<bool>)
//   OnStepError (Action<StepModel, string>)
//   Stop() (nu EmergencyStop separat)
//   PlayAsync(IEnumerable<StepModel>, int, CancellationToken)
// ============================================================

using System;
using System.Collections.Generic;
using System.Threading;
using System.Threading.Tasks;
using AutoPilotDC.Core.Interfaces;
using AutoPilotDC.Infrastructure.Engines;
using AutoPilotDC.Models;
using Moq;
using Xunit;

namespace AutoPilotDC.Tests.Unit;

[System.Runtime.Versioning.SupportedOSPlatform("windows7.0")]
public class PlayerEngineTests : IDisposable
{
    // -- Dependinte ----------------------------------------------------
    private readonly Mock<ISettingsManager> _settingsMock;
    private readonly Mock<ILogRepository> _logMock;
    private readonly DesktopEngine _desktopEngine;
    private readonly PlayerEngine _sut;

    public PlayerEngineTests()
    {
        _settingsMock = new Mock<ISettingsManager>();
        _logMock = new Mock<ILogRepository>();

        // Setup minimal ISettingsManager � valorile folosite in PlayAsync
        _settingsMock.Setup(s => s.Get<int>("countdown_before_play", It.IsAny<int>())).Returns(0);
        _settingsMock.Setup(s => s.Get<double>("playback_speed", It.IsAny<double>())).Returns(1.0);
        _settingsMock.Setup(s => s.Get<double>("step_delay", It.IsAny<double>())).Returns(0.0);
        _settingsMock.Setup(s => s.Get<double>("mouse_move_delay", It.IsAny<double>())).Returns(0.0);
        _settingsMock.Setup(s => s.Get<int>("repeat_count", It.IsAny<int>())).Returns(1);

        // DesktopEngine este clasa concreta � NU se poate mocka cu Moq
        _desktopEngine = new DesktopEngine();

        // Constructor real: (ISettingsManager, ILogRepository, DesktopEngine)
        _sut = new PlayerEngine(
            _settingsMock.Object,
            _logMock.Object,
            _desktopEngine
        );
    }

    public void Dispose()
    {
        _sut.Stop();
        GC.SuppressFinalize(this);
    }

    // ---------------------------------------------------------------
    // 1. Stare initiala
    // ---------------------------------------------------------------

    [Fact]
    public void InitialState_IsNotRunning()
    {
        Assert.False(_sut.IsRunning);
    }

    [Fact]
    public void InitialState_IsNotPaused()
    {
        Assert.False(_sut.IsPaused);
    }

    // ---------------------------------------------------------------
    // 2. Lista goala � PlayAsync se termina imediat fara erori
    // ---------------------------------------------------------------

    [Fact]
    public async Task PlayAsync_EmptyList_CompletesWithoutError()
    {
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(5));
        await _sut.PlayAsync(new List<StepModel>(), repeatCount: 1, cts.Token);
        Assert.False(_sut.IsRunning);
    }

    // ---------------------------------------------------------------
    // 3. Pasii cu skip=true sunt ignorati � OnStepExecuting nu se declanseaza
    // ---------------------------------------------------------------

    [Fact]
    public async Task PlayAsync_SkippedSteps_OnStepExecutingNotCalled()
    {
        var calledIds = new List<int>();
        _sut.OnStepExecuting = step => calledIds.Add(step.StepId);

        var steps = new List<StepModel>
        {
            new() { StepId = 1, StepType = "DELAY", DelayBefore = 0, DelayAfter = 0, Skip = true },
            new() { StepId = 2, StepType = "DELAY", DelayBefore = 0, DelayAfter = 0, Skip = true },
        };

        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(5));
        await _sut.PlayAsync(steps, repeatCount: 1, cts.Token);

        Assert.Empty(calledIds);
    }

    // ---------------------------------------------------------------
    // 4. Pasul DELAY � OnStepExecuting se declanseaza
    // ---------------------------------------------------------------

    [Fact]
    public async Task PlayAsync_DelayStep_OnStepExecutingCalled()
    {
        var calledIds = new List<int>();
        _sut.OnStepExecuting = step => calledIds.Add(step.StepId);

        var steps = new List<StepModel>
        {
            new() { StepId = 42, StepType = "DELAY", DelayBefore = 0.0, DelayAfter = 0.0 }
        };

        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(5));
        await _sut.PlayAsync(steps, repeatCount: 1, cts.Token);

        Assert.Contains(42, calledIds);
    }

    // ---------------------------------------------------------------
    // 5. Stop() opreste executia
    // ---------------------------------------------------------------

    [Fact]
    public async Task Stop_DuringPlayback_StopsExecution()
    {
        var steps = new List<StepModel>
        {
            new() { StepId = 1, StepType = "DELAY", DelayBefore = 30.0, DelayAfter = 0 },
        };

        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(30));
        var playTask = Task.Run(() => _sut.PlayAsync(steps, repeatCount: 1, cts.Token));

        await Task.Delay(150);
        _sut.Stop();

        var completed = await Task.WhenAny(playTask, Task.Delay(3000));
        Assert.Equal(playTask, completed);
        Assert.False(_sut.IsRunning);
    }

    // ---------------------------------------------------------------
    // 6. Pause / Resume
    // ---------------------------------------------------------------

    [Fact]
    public async Task Pause_SetsIsPaused_True()
    {
        var steps = new List<StepModel>
        {
            new() { StepId = 1, StepType = "DELAY", DelayBefore = 10.0, DelayAfter = 0 },
        };

        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(10));
        var playTask = Task.Run(() => _sut.PlayAsync(steps, repeatCount: 1, cts.Token));

        await Task.Delay(100);
        _sut.Pause();

        Assert.True(_sut.IsPaused);

        // Cleanup
        _sut.Stop();
        await Task.WhenAny(playTask, Task.Delay(2000));
    }

    [Fact]
    public async Task Resume_AfterPause_ClearsIsPaused()
    {
        var steps = new List<StepModel>
        {
            new() { StepId = 1, StepType = "DELAY", DelayBefore = 10.0, DelayAfter = 0 },
        };

        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(10));
        var playTask = Task.Run(() => _sut.PlayAsync(steps, repeatCount: 1, cts.Token));

        await Task.Delay(100);
        _sut.Pause();
        Assert.True(_sut.IsPaused);

        _sut.Resume();
        Assert.False(_sut.IsPaused);

        _sut.Stop();
        await Task.WhenAny(playTask, Task.Delay(2000));
    }

    // ---------------------------------------------------------------
    // 7. RepeatCount � OnStepExecuting apelat de N ori
    // ---------------------------------------------------------------

    [Fact]
    public async Task PlayAsync_RepeatCount3_ExecutesSteps3Times()
    {
        int count = 0;
        _sut.OnStepExecuting = _ => Interlocked.Increment(ref count);

        var steps = new List<StepModel>
        {
            new() { StepId = 1, StepType = "DELAY", DelayBefore = 0, DelayAfter = 0 }
        };

        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(10));
        await _sut.PlayAsync(steps, repeatCount: 3, cts.Token);

        Assert.Equal(3, count);
    }

    // ---------------------------------------------------------------
    // 8. CancellationToken extern opreste executia
    // ---------------------------------------------------------------

    [Fact]
    public async Task PlayAsync_ExternalCancellation_StopsExecution()
    {
        var steps = new List<StepModel>
        {
            new() { StepId = 1, StepType = "DELAY", DelayBefore = 30.0, DelayAfter = 0 },
        };

        using var cts = new CancellationTokenSource();
        var playTask = Task.Run(() => _sut.PlayAsync(steps, repeatCount: 1, cts.Token));

        await Task.Delay(150);
        cts.Cancel();

        var completed = await Task.WhenAny(playTask, Task.Delay(3000));
        Assert.Equal(playTask, completed);
    }

    // ---------------------------------------------------------------
    // 9. OnPlaybackFinished se declanseaza la final (Action<bool>)
    // ---------------------------------------------------------------

    [Fact]
    public async Task PlayAsync_RaisesOnPlaybackFinished_WithTrue()
    {
        bool? finishedResult = null;
        _sut.OnPlaybackFinished = success => finishedResult = success;

        var steps = new List<StepModel>
        {
            new() { StepId = 1, StepType = "DELAY", DelayBefore = 0, DelayAfter = 0 }
        };

        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(5));
        await _sut.PlayAsync(steps, repeatCount: 1, cts.Token);

        Assert.NotNull(finishedResult);
        Assert.True(finishedResult!.Value);
    }

    // ---------------------------------------------------------------
    // 10. OnPlaybackFinished cu false la Stop() fortat
    // ---------------------------------------------------------------

    [Fact]
    public async Task Stop_RaisesOnPlaybackFinished_WithFalse()
    {
        bool? finishedResult = null;
        _sut.OnPlaybackFinished = success => finishedResult = success;

        var steps = new List<StepModel>
        {
            new() { StepId = 1, StepType = "DELAY", DelayBefore = 30.0, DelayAfter = 0 },
        };

        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(30));
        var playTask = Task.Run(() => _sut.PlayAsync(steps, repeatCount: 1, cts.Token));

        await Task.Delay(150);
        _sut.Stop();

        await Task.WhenAny(playTask, Task.Delay(3000));

        Assert.NotNull(finishedResult);
        Assert.False(finishedResult!.Value);
    }

    // ---------------------------------------------------------------
    // 11. IsRunning = true in timpul executiei
    // ---------------------------------------------------------------

    [Fact]
    public async Task IsRunning_TrueWhileExecuting()
    {
        bool wasRunningDuringStep = false;
        _sut.OnStepExecuting = _ => wasRunningDuringStep = _sut.IsRunning;

        var steps = new List<StepModel>
        {
            new() { StepId = 1, StepType = "DELAY", DelayBefore = 0, DelayAfter = 0 }
        };

        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(5));
        await _sut.PlayAsync(steps, repeatCount: 1, cts.Token);

        Assert.True(wasRunningDuringStep);
    }

    // ---------------------------------------------------------------
    // 12. PlayAsync nu porneste daca deja ruleaza (guard _isRunning)
    // ---------------------------------------------------------------

    [Fact]
    public async Task PlayAsync_AlreadyRunning_SecondCallIgnored()
    {
        int startCount = 0;
        _sut.OnStarted = () => Interlocked.Increment(ref startCount);

        var steps = new List<StepModel>
        {
            new() { StepId = 1, StepType = "DELAY", DelayBefore = 2.0, DelayAfter = 0 },
        };

        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(10));

        // Primul PlayAsync � porneste
        var first = Task.Run(() => _sut.PlayAsync(steps, repeatCount: 1, cts.Token));
        await Task.Delay(100);

        // Al doilea PlayAsync � trebuie ignorat (IsRunning = true)
        var second = Task.Run(() => _sut.PlayAsync(steps, repeatCount: 1, cts.Token));
        await second; // se termina imediat

        _sut.Stop();
        await Task.WhenAny(first, Task.Delay(3000));

        // OnStarted apelat o singura data
        Assert.Equal(1, startCount);
    }
}