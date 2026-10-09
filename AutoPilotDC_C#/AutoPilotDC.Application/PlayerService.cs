using System;
using System.Collections.Generic;
using System.Threading;
using System.Threading.Tasks;
using AutoPilotDC.Core.Interfaces;
using AutoPilotDC.Infrastructure.Services;
using AutoPilotDC.Models;

namespace AutoPilotDC.Application
{
    /// <summary>
    /// Application-layer wrapper peste IPlayer.
    /// Expune callbacks ca proprietati pentru binding MVVM.
    /// Echivalent Python: PlayerEngine (interfata catre UI)
    /// </summary>
    [System.Runtime.Versioning.SupportedOSPlatform("windows7.0")]
    public class PlayerService
    {
        private readonly IPlayer _player;

        public PlayerService(IPlayer player) => _player = player;

        // ── State ─────────────────────────────────────────────────
        public bool IsRunning => _player.IsRunning;
        public bool IsPaused  => _player.IsPaused;

        // ── Callbacks (proxy direct pe IPlayer) ───────────────────
        public Action<bool>?              PlaybackFinished { get => _player.OnPlaybackFinished; set => _player.OnPlaybackFinished = value; }
        public Action<StepModel>?         StepExecuting    { get => _player.OnStepExecuting;    set => _player.OnStepExecuting    = value; }
        public Action<StepModel, string>? StepError        { get => _player.OnStepError;        set => _player.OnStepError        = value; }
        public Action<int>?               Countdown        { get => _player.OnCountdown;        set => _player.OnCountdown        = value; }
        public Action?                    Started          { get => _player.OnStarted;          set => _player.OnStarted          = value; }
        public Action?                    Paused           { get => _player.OnPaused;           set => _player.OnPaused           = value; }
        public Action?                    Resumed          { get => _player.OnResumed;          set => _player.OnResumed          = value; }
        public Action<int, int>?          IterUpdate       { get => _player.OnIterUpdate;       set => _player.OnIterUpdate       = value; }
        public Func<StepModel, Task<string>>? OnQuestion   { get => _player.OnQuestion;         set => _player.OnQuestion         = value; }

        /// <summary>Watchdog anomaly callback — proxied to PlayerEngine if available.</summary>
        public Func<AutoPilotDC.Infrastructure.Services.WatchdogAnomaly, Task<bool>>? OnWatchdogQuestion
        {
            get => (_player as AutoPilotDC.Infrastructure.Engines.PlayerEngine)?.OnWatchdogQuestion;
            set { if (_player is AutoPilotDC.Infrastructure.Engines.PlayerEngine pe) pe.OnWatchdogQuestion = value; }
        }

        /// <summary>Actiune la finalul ciclului — proxied to PlayerEngine.</summary>
        public AutoPilotDC.Infrastructure.Services.EndOfCycleAction EndOfCycleAction
        {
            get => (_player as AutoPilotDC.Infrastructure.Engines.PlayerEngine)?.EndOfCycleAction
                   ?? AutoPilotDC.Infrastructure.Services.EndOfCycleAction.None;
            set { if (_player is AutoPilotDC.Infrastructure.Engines.PlayerEngine pe) pe.EndOfCycleAction = value; }
        }

        // ── Control ───────────────────────────────────────────────
        public Task PlayAsync(IEnumerable<StepModel> steps, int repeatCount = 1,
                              CancellationToken ct = default)
            => _player.PlayAsync(steps, repeatCount, ct);

        public Task PlayAsync(IEnumerable<StepModel> steps, int repeatCount,
                              LoginConfig? loginConfig, CancellationToken ct = default)
            => _player.PlayAsync(steps, repeatCount, loginConfig, ct);

        public void Pause()         => _player.Pause();
        public void Resume()        => _player.Resume();
        public void Stop()          => _player.Stop();
        public void TogglePause()   { if (_player.IsPaused) _player.Resume(); else _player.Pause(); }
        public void EmergencyStop() => _player.Stop();

        public Task<(bool Success, string Error)> ExecuteStepAsync(StepModel step)
            => _player.ExecuteStepAsync(step);

        public Task SimulateStepAsync(StepModel step)
            => _player.SimulateStepAsync(step);
    }
}
