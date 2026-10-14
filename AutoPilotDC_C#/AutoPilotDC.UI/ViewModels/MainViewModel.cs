// ============================================================
// AutoPilot DC v3.9 -> C# WPF .NET 8
// MainViewModel.cs — ViewModel principal (MVVM)
// Faza 9:  LoginConfigCmd + OpenLoginConfig
// Faza 10: SimulatorCmd + NextStepCmd + IsDryRun + IsSimulating
// ============================================================

using System;
using System.Collections.ObjectModel;
using System.ComponentModel;
using System.Linq;
using System.Runtime.CompilerServices;
using System.Threading;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Input;
using AutoPilotDC.Application;
using AutoPilotDC.Core.Interfaces;
using AutoPilotDC.Infrastructure.Engines;
using AutoPilotDC.Models;
using AutoPilotDC.UI.Commands;
using AutoPilotDC.UI.Overlays;
using MessageBox = System.Windows.MessageBox;

namespace AutoPilotDC.UI.ViewModels;

public sealed class MainViewModel : INotifyPropertyChanged, IDisposable
{
    // ── Servicii ──────────────────────────────────────────────────────
    private readonly RecorderService _recorderSvc;
    private readonly PlayerService _playerSvc;
    private readonly RoutineService _routineSvc;
    private readonly LogService _logSvc;
    private readonly ISettingsManager _settings;

    // ── Fields ────────────────────────────────────────────────────────
    private readonly SimulatorEngine _simulatorEngineSvc;  // injectat din DI
    private SimulatorEngine? _simulatorEngine;     // instanta activa per-run
    private SimulatorOverlay? _simulatorOverlay;
    private LoginConfig? _currentLoginConfig;
    private bool _isSimulating;
    private bool _isDryRun;
    private CancellationTokenSource? _simulatorCts;
    private int _nextLogId = 1;

    // ── Collections ───────────────────────────────────────────────────
    public ObservableCollection<StepModel> Steps { get; } = [];
    public ObservableCollection<LogEntry> LogItems { get; } = [];
    public ObservableCollection<string> Routines { get; } = [];

    // ── Selected items ────────────────────────────────────────────────
    private StepModel? _selectedStep;
    public StepModel? SelectedStep
    {
        get => _selectedStep;
        set { _selectedStep = value; OnPropertyChanged(); }
    }

    private LogEntry? _selectedLog;
    public LogEntry? SelectedLog
    {
        get => _selectedLog;
        set { _selectedLog = value; OnPropertyChanged(); }
    }

    private string? _selectedRoutine;
    public string? SelectedRoutine
    {
        get => _selectedRoutine;
        set { _selectedRoutine = value; OnPropertyChanged(); }
    }

    // ── State ─────────────────────────────────────────────────────────
    private bool _isRecording;
    public bool IsRecording
    {
        get => _isRecording;
        set { _isRecording = value; OnPropertyChanged(); OnPropertyChanged(nameof(CanPlay)); }
    }

    private bool _isPlaying;
    public bool IsPlaying
    {
        get => _isPlaying;
        set { _isPlaying = value; OnPropertyChanged(); OnPropertyChanged(nameof(CanPlay)); }
    }

    private bool _isPaused;
    public bool IsPaused
    {
        get => _isPaused;
        set { _isPaused = value; OnPropertyChanged(); OnPropertyChanged(nameof(PauseButtonText)); }
    }

    public bool CanPlay => Steps.Count > 0 && !IsRecording && !IsPlaying && !IsSimulating;

    private string _statusText = "Gata.";
    public string StatusText
    {
        get => _statusText;
        set { _statusText = value; OnPropertyChanged(); }
    }

    private string _stepCountText = "Pasi: 0";
    public string StepCountText
    {
        get => _stepCountText;
        set { _stepCountText = value; OnPropertyChanged(); }
    }

    private int _countdownValue;
    public int CountdownValue
    {
        get => _countdownValue;
        set { _countdownValue = value; OnPropertyChanged(); }
    }

    private string _iterText = "";
    public string IterText
    {
        get => _iterText;
        set { _iterText = value; OnPropertyChanged(); }
    }

    private string _recIndicatorText = "⬤ STANDBY";
    public string RecIndicatorText
    {
        get => _recIndicatorText;
        set { _recIndicatorText = value; OnPropertyChanged(); }
    }

    public string PauseButtonText => IsPaused ? "▶ Reia [F8]" : "⏸ Pauza [F8]";

    // ── Simulator State (Faza 10) ─────────────────────────────────────
    public bool IsSimulating
    {
        get => _isSimulating;
        set
        {
            _isSimulating = value;
            OnPropertyChanged();
            OnPropertyChanged(nameof(IsNotSimulating));
            OnPropertyChanged(nameof(IsNextStepVisible));
            OnPropertyChanged(nameof(CanPlay));
        }
    }

    /// <summary>Folosit in XAML: IsEnabled="{Binding IsNotSimulating}"</summary>
    public bool IsNotSimulating => !_isSimulating;

    public bool IsDryRun
    {
        get => _isDryRun;
        set { _isDryRun = value; OnPropertyChanged(); }
    }

    public bool IsNextStepVisible => IsSimulating;

    // ── Login Config State (Faza 9) ───────────────────────────────────
    public LoginConfig? CurrentLoginConfig
    {
        get => _currentLoginConfig;
        set { _currentLoginConfig = value; OnPropertyChanged(); }
    }

    // ── Settings bindable ─────────────────────────────────────────────
    private double _stepDelay = 0.8;
    public double StepDelay
    {
        get => _stepDelay;
        set { _stepDelay = value; OnPropertyChanged(); _settings.Set("step_delay", value); }
    }

    private double _playbackSpeed = 1.0;
    public double PlaybackSpeed
    {
        get => _playbackSpeed;
        set { _playbackSpeed = value; OnPropertyChanged(); _settings.Set("playback_speed", value); }
    }

    private int _repeatCount = 1;
    public int RepeatCount
    {
        get => _repeatCount;
        set { _repeatCount = Math.Max(1, value); OnPropertyChanged(); _settings.Set("repeat_count", _repeatCount); }
    }

    private int _countdownSetting = 3;
    public int CountdownSetting
    {
        get => _countdownSetting;
        set { _countdownSetting = value; OnPropertyChanged(); _settings.Set("countdown_before_play", value); }
    }

    private string _currentTheme = "dark";
    public string CurrentTheme
    {
        get => _currentTheme;
        set { _currentTheme = value; OnPropertyChanged(); ApplyTheme(value); }
    }

    private bool _recordMouseMove;
    public bool RecordMouseMove
    {
        get => _recordMouseMove;
        set { _recordMouseMove = value; OnPropertyChanged(); _settings.Set("record_mouse_move", value); }
    }

    private int _mouseMoveThreshold = 5;
    public int MouseMoveThreshold
    {
        get => _mouseMoveThreshold;
        set { _mouseMoveThreshold = value; OnPropertyChanged(); _settings.Set("mouse_move_threshold", value); }
    }


    // DND indicator
    private bool _dndActive;
    public bool DndActive
    {
        get => _dndActive;
        set { _dndActive = value; OnPropertyChanged(); OnPropertyChanged(nameof(DndIndicatorText)); }
    }
    public string DndIndicatorText => DndActive ? "🌙 DND activ" : "";

    // Tab visibility
    private bool _showTabRecorder    = true;
    private bool _showTabStepBuilder = true;
    private bool _showTabLog         = true;
    private bool _showTabRutine      = true;
    private bool _showTabExcel       = true;
    private bool _showTabNotite      = true;
    private bool _showTabSetari      = true;
    private bool _showTabAjutor      = true;

    public bool ShowTabRecorder    { get => _showTabRecorder;    set { _showTabRecorder    = value; OnPropertyChanged(); _settings.Set("show_tab_recorder",    value); } }
    public bool ShowTabStepBuilder { get => _showTabStepBuilder; set { _showTabStepBuilder = value; OnPropertyChanged(); _settings.Set("show_tab_stepbuilder", value); } }
    public bool ShowTabLog         { get => _showTabLog;         set { _showTabLog         = value; OnPropertyChanged(); _settings.Set("show_tab_log",         value); } }
    public bool ShowTabRutine      { get => _showTabRutine;      set { _showTabRutine      = value; OnPropertyChanged(); _settings.Set("show_tab_rutine",      value); } }
    public bool ShowTabExcel       { get => _showTabExcel;       set { _showTabExcel       = value; OnPropertyChanged(); _settings.Set("show_tab_excel",       value); } }
    public bool ShowTabNotite      { get => _showTabNotite;      set { _showTabNotite      = value; OnPropertyChanged(); _settings.Set("show_tab_notite",      value); } }
    public bool ShowTabSetari      { get => _showTabSetari;      set { _showTabSetari      = value; OnPropertyChanged(); _settings.Set("show_tab_setari",      value); } }
    public bool ShowTabAjutor      { get => _showTabAjutor;      set { _showTabAjutor      = value; OnPropertyChanged(); _settings.Set("show_tab_ajutor",      value); } }

    // End-of-cycle power action
    public System.Collections.Generic.List<string> EndOfCycleOptions { get; } = new() { "None", "Sleep", "Hibernate", "Shutdown" };

    private string _endOfCycleActionSetting = "None";
    public string EndOfCycleActionSetting
    {
        get => _endOfCycleActionSetting;
        set
        {
            _endOfCycleActionSetting = value;
            OnPropertyChanged();
            _settings.Set("end_of_cycle_action", value);
            if (System.Enum.TryParse<AutoPilotDC.Infrastructure.Services.EndOfCycleAction>(value, out var eoca))
                _playerSvc.EndOfCycleAction = eoca;
        }
    }

    private bool _debugMode;
    public bool DebugMode
    {
        get => _debugMode;
        set { _debugMode = value; OnPropertyChanged(); }
    }

    // ── Excel ─────────────────────────────────────────────────────────
    private string _excelPath = "";
    public string ExcelPath
    {
        get => _excelPath;
        set { _excelPath = value; OnPropertyChanged(); }
    }

    private string _excelSheet = "Sheet1";
    public string ExcelSheet
    {
        get => _excelSheet;
        set { _excelSheet = value; OnPropertyChanged(); }
    }

    private string _excelRange = "A1:Z100";
    public string ExcelRange
    {
        get => _excelRange;
        set { _excelRange = value; OnPropertyChanged(); }
    }

    // ── Notes ─────────────────────────────────────────────────────────
    private string _notesText = "";
    public string NotesText
    {
        get => _notesText;
        set { _notesText = value; OnPropertyChanged(); }
    }

    // ── Commands ──────────────────────────────────────────────────────

    // Recorder
    public ICommand StartRecordingCmd { get; }
    public ICommand StopRecordingCmd { get; }
    public ICommand ClearStepsCmd { get; }

    // Player
    public ICommand PlayCmd { get; }
    public ICommand PauseResumeCmd { get; }
    public ICommand StopPlayCmd { get; }
    public ICommand EmergencyStopCmd { get; }

    // Steps
    public ICommand AddStepCmd { get; }
    public ICommand EditStepCmd { get; }
    public ICommand DeleteStepCmd { get; }
    public ICommand MoveStepUpCmd { get; }
    public ICommand MoveStepDownCmd { get; }
    public ICommand ToggleSkipCmd { get; }
    public ICommand DebugStepCmd { get; }

    // Routines
    public ICommand SaveRoutineCmd { get; }
    public ICommand LoadRoutineCmd { get; }
    public ICommand DeleteRoutineCmd { get; }
    public ICommand NewRoutineCmd { get; }

    // Log
    public ICommand ExportLogXlsxCmd { get; }
    public ICommand ExportLogCsvCmd { get; }
    public ICommand ExportLogJsonCmd { get; }
    public ICommand ClearLogCmd { get; }

    // Faza 9: Login
    public ICommand LoginConfigCmd { get; }

    // Faza 10: Simulator
    public ICommand SimulatorCmd { get; }
    public ICommand NextStepCmd { get; }

    // ── Constructor ───────────────────────────────────────────────────
    public MainViewModel(
        RecorderService recorderSvc,
        PlayerService playerSvc,
        RoutineService routineSvc,
        LogService logSvc,
        ISettingsManager settings,
        SimulatorEngine simulatorEngine)
    {
        _recorderSvc = recorderSvc;
        _playerSvc = playerSvc;
        _routineSvc = routineSvc;
        _logSvc = logSvc;
        _settings = settings;
        _simulatorEngineSvc = simulatorEngine;

        // ── Incarca setari ────────────────────────────────────────────
        _stepDelay = settings.Get("step_delay", 0.8);
        _playbackSpeed = settings.Get("playback_speed", 1.0);
        _repeatCount = settings.Get("repeat_count", 1);
        _countdownSetting = settings.Get("countdown_before_play", 3);
        _currentTheme = settings.Get("theme", "dark");
        _recordMouseMove = settings.Get("record_mouse_move", false);
        _mouseMoveThreshold = settings.Get("mouse_move_threshold", 5);

        // ── Conecteaza callbacks recorder (events) ────────────────────
        _recorderSvc.StepRecorded += OnStepRecorded;
        _recorderSvc.RecordingStarted += OnRecordingStarted;
        _recorderSvc.RecordingStopped += OnRecordingStopped;

        // ── Conecteaza callbacks player (events) ──────────────────────
        _playerSvc.PlaybackFinished += OnPlaybackFinished;
        _playerSvc.StepExecuting += OnStepExecuting;
        _playerSvc.StepError += OnStepError;
        _playerSvc.Countdown += OnCountdown;
        _playerSvc.Started += OnPlayStarted;
        _playerSvc.Paused += OnPlayPaused;
        _playerSvc.Resumed += OnPlayResumed;
        _playerSvc.IterUpdate += OnIterUpdate;
        _playerSvc.OnQuestion = ShowQuestionDialog;

        // Initializeaza EndOfCycleAction din settings
        if (System.Enum.TryParse<AutoPilotDC.Infrastructure.Services.EndOfCycleAction>(_settings.Get("end_of_cycle_action", "None"), out var eoca))
            _playerSvc.EndOfCycleAction = eoca;

        // ── Initializeaza comenzi ─────────────────────────────────────
        StartRecordingCmd = new RelayCommand(StartRecording, () => !IsRecording && !IsPlaying && !IsSimulating);
        StopRecordingCmd = new RelayCommand(StopRecording, () => IsRecording);
        ClearStepsCmd = new RelayCommand(ClearSteps, () => !IsRecording && !IsPlaying && !IsSimulating);

        PlayCmd = new AsyncRelayCommand(StartPlay, () => CanPlay);
        PauseResumeCmd = new RelayCommand(TogglePause, () => IsPlaying);
        StopPlayCmd = new RelayCommand(StopPlay, () => IsPlaying);
        EmergencyStopCmd = new RelayCommand(EmergencyStop);

        AddStepCmd = new RelayCommand(AddStep, () => !IsRecording && !IsPlaying && !IsSimulating);
        EditStepCmd = new RelayCommand(EditStep, () => SelectedStep != null && !IsRecording && !IsPlaying && !IsSimulating);
        DeleteStepCmd = new RelayCommand(DeleteStep, () => SelectedStep != null && !IsRecording && !IsPlaying && !IsSimulating);
        MoveStepUpCmd = new RelayCommand(MoveStepUp, () => SelectedStep != null && Steps.IndexOf(SelectedStep) > 0);
        MoveStepDownCmd = new RelayCommand(MoveStepDown, () => SelectedStep != null && Steps.IndexOf(SelectedStep) < Steps.Count - 1);
        ToggleSkipCmd = new RelayCommand(ToggleSkip, () => SelectedStep != null);
        DebugStepCmd = new AsyncRelayCommand(DebugStep, () => SelectedStep != null && !IsPlaying && !IsSimulating);

        SaveRoutineCmd = new RelayCommand(SaveRoutine, () => Steps.Count > 0);
        LoadRoutineCmd = new RelayCommand(LoadRoutine, () => SelectedRoutine != null);
        DeleteRoutineCmd = new RelayCommand(DeleteRoutine, () => SelectedRoutine != null);
        NewRoutineCmd = new RelayCommand(NewRoutine);

        ExportLogXlsxCmd = new RelayCommand(ExportLogXlsx, () => LogItems.Count > 0);
        ExportLogCsvCmd = new RelayCommand(ExportLogCsv, () => LogItems.Count > 0);
        ExportLogJsonCmd = new RelayCommand(ExportLogJson, () => LogItems.Count > 0);
        ClearLogCmd = new RelayCommand(ClearLog, () => LogItems.Count > 0);

        // Faza 9
        LoginConfigCmd = new RelayCommand(OpenLoginConfig);

        // Faza 10
        SimulatorCmd = new AsyncRelayCommand(StartSimulatorAsync, () => !IsSimulating && Steps.Count > 0);
        NextStepCmd = new AsyncRelayCommand(NextSimulatorStepAsync, () => IsSimulating);

        // Incarca rutine existente
        RefreshRoutines();
    }

    // ── Recorder Actions ──────────────────────────────────────────────

    private void StartRecording() => _recorderSvc.Start();

    private void StopRecording() => _recorderSvc.Stop();

    private void ClearSteps()
    {
        var r = MessageBox.Show("Stergi toti pasii?", "Confirmare",
            MessageBoxButton.YesNo, MessageBoxImage.Question);
        if (r != MessageBoxResult.Yes) return;

        Steps.Clear();
        _recorderSvc.Clear();
        UpdateStepCount();
        StatusText = "Pasi stearsi.";
        OnPropertyChanged(nameof(CanPlay));
    }

    // ── Player Actions ────────────────────────────────────────────────

    private async Task StartPlay()
    {
        if (Steps.Count == 0) return;
        await _playerSvc.PlayAsync([.. Steps], RepeatCount, CurrentLoginConfig);
    }

    private void TogglePause()
    {
        _playerSvc.TogglePause();
        IsPaused = !IsPaused;
    }

    private void StopPlay() => _playerSvc.Stop();

    private void EmergencyStop()
    {
        _playerSvc.EmergencyStop();
        _simulatorCts?.Cancel();
        IsSimulating = false;
        _simulatorOverlay?.HideOverlay();
        UIInvoke(() =>
        {
            IsPlaying = false;
            IsRecording = false;
            DndActive = false;
            StatusText = "🚨 STOP URGENTA activat.";
            RecIndicatorText = "⬤ STANDBY";
            CountdownValue = 0;
            IterText = "";
        });
    }

    // ── Step Actions ──────────────────────────────────────────────────

    private void AddStep()
    {
        var dialog = new Views.Dialogs.StepBuilderDialog(null)
        {
            Owner = System.Windows.Application.Current.MainWindow
        };
        if (dialog.ShowDialog() == true && dialog.ResultStep != null)
        {
            dialog.ResultStep.StepId = Steps.Count + 1;
            Steps.Add(dialog.ResultStep);
            _recorderSvc.SetSteps(Steps);
            UpdateStepCount();
            OnPropertyChanged(nameof(CanPlay));
            StatusText = $"Pas adaugat: {dialog.ResultStep.StepType}";
        }
    }

    private void EditStep()
    {
        if (SelectedStep == null) return;
        var dialog = new Views.Dialogs.StepBuilderDialog(SelectedStep)
        {
            Owner = System.Windows.Application.Current.MainWindow
        };
        if (dialog.ShowDialog() == true && dialog.ResultStep != null)
        {
            int idx = Steps.IndexOf(SelectedStep);
            if (idx >= 0)
            {
                dialog.ResultStep.StepId = SelectedStep.StepId;
                Steps[idx] = dialog.ResultStep;
                SelectedStep = dialog.ResultStep;
                _recorderSvc.SetSteps(Steps);
                StatusText = $"Pas editat: {dialog.ResultStep.StepType}";
            }
        }
    }

    private void DeleteStep()
    {
        if (SelectedStep == null) return;
        Steps.Remove(SelectedStep);
        SelectedStep = null;
        _recorderSvc.SetSteps(Steps);
        UpdateStepCount();
        OnPropertyChanged(nameof(CanPlay));
        StatusText = "Pas sters.";
    }

    private void MoveStepUp()
    {
        if (SelectedStep == null) return;
        int idx = Steps.IndexOf(SelectedStep);
        if (idx <= 0) return;
        Steps.Move(idx, idx - 1);
        StatusText = "Pas mutat sus.";
    }

    private void MoveStepDown()
    {
        if (SelectedStep == null) return;
        int idx = Steps.IndexOf(SelectedStep);
        if (idx >= Steps.Count - 1) return;
        Steps.Move(idx, idx + 1);
        StatusText = "Pas mutat jos.";
    }

    private void ToggleSkip()
    {
        if (SelectedStep == null) return;
        SelectedStep.Skip = !SelectedStep.Skip;
        // Forteaza refresh DataGrid
        int idx = Steps.IndexOf(SelectedStep);
        var step = SelectedStep;
        Steps.RemoveAt(idx);
        Steps.Insert(idx, step);
        SelectedStep = step;
        StatusText = SelectedStep.Skip
            ? $"Pas {SelectedStep.StepId} marcat Skip."
            : $"Pas {SelectedStep.StepId} activ.";
    }

    private async Task DebugStep()
    {
        if (SelectedStep == null) return;
        StatusText = $"Debug pas {SelectedStep.StepId}...";
        var (ok, err) = await _playerSvc.ExecuteStepAsync(SelectedStep);
        StatusText = ok
            ? $"✅ Pas {SelectedStep.StepId} executat OK."
            : $"❌ Pas {SelectedStep.StepId} eroare: {err}";
    }

    // ── Routine Actions ───────────────────────────────────────────────

    private void SaveRoutine()
    {
        var dialog = new Views.Dialogs.InputDialog("Salveaza Rutina", "Nume rutina:");
        if (dialog.ShowDialog() != true || string.IsNullOrWhiteSpace(dialog.Result)) return;

        var routine = new RoutineFile
        {
            Name = dialog.Result,
            Steps = [.. Steps]
        };
        _routineSvc.Save(routine);
        RefreshRoutines();
        StatusText = $"Rutina '{dialog.Result}' salvata.";
    }

    private void LoadRoutine()
    {
        if (SelectedRoutine == null) return;
        var routine = _routineSvc.Load(SelectedRoutine);
        if (routine == null) return;

        Steps.Clear();
        foreach (var s in routine.Steps) Steps.Add(s);
        _recorderSvc.SetSteps(Steps);
        UpdateStepCount();
        OnPropertyChanged(nameof(CanPlay));
        StatusText = $"Rutina '{SelectedRoutine}' incarcata ({Steps.Count} pasi).";
    }

    private void DeleteRoutine()
    {
        if (SelectedRoutine == null) return;
        var result = MessageBox.Show(
            $"Stergi rutina '{SelectedRoutine}'?",
            "Confirmare", MessageBoxButton.YesNo, MessageBoxImage.Question);
        if (result != MessageBoxResult.Yes) return;

        _routineSvc.Delete(SelectedRoutine);
        RefreshRoutines();
        StatusText = "Rutina stearsa.";
    }

    private void NewRoutine()
    {
        Steps.Clear();
        _recorderSvc.Clear();
        CurrentLoginConfig = null;
        SelectedRoutine = null;
        UpdateStepCount();
        OnPropertyChanged(nameof(CanPlay));
        StatusText = "Rutina noua.";
    }

    private void RefreshRoutines()
    {
        Routines.Clear();
        foreach (var name in _routineSvc.GetNames())
            Routines.Add(name);
    }

    // ── Log Actions ───────────────────────────────────────────────────

    private void ExportLogXlsx() => _logSvc.ExportXlsx();
    private void ExportLogCsv() => _logSvc.ExportCsv();
    private void ExportLogJson() => _logSvc.ExportJson();

    private void ClearLog()
    {
        LogItems.Clear();
        _logSvc.Clear();
        StatusText = "Log sters.";
    }

    // ── Recorder Callbacks ────────────────────────────────────────────

    private void OnStepRecorded(StepModel step)
    {
        UIInvoke(() =>
        {
            Steps.Add(step);
            UpdateStepCount();
            OnPropertyChanged(nameof(CanPlay));
        });
    }

    private void OnRecordingStarted()
    {
        UIInvoke(() =>
        {
            IsRecording = true;
            DndActive = true;
            StatusText = "🔴 INREGISTRARE ACTIVA";
            RecIndicatorText = "⬤ REC";
        });
    }

    private void OnRecordingStopped()
    {
        UIInvoke(() =>
        {
            IsRecording = false;
            DndActive = false;
            StatusText = $"Inregistrare oprita — {Steps.Count} pasi";
            RecIndicatorText = "⬤ STANDBY";
        });
    }

    // ── Player Callbacks ──────────────────────────────────────────────

    private void OnPlayStarted()
    {
        UIInvoke(() =>
        {
            IsPlaying = true;
            StatusText = "▶ REDARE ACTIVA";
            RecIndicatorText = "▶ REDARE";
        });
    }

    private void OnPlaybackFinished(bool success)
    {
        UIInvoke(() =>
        {
            IsPlaying = false;
            IsPaused = false;
            StatusText = success ? "✅ Redare finalizata." : "⏹ Redare oprita.";
            RecIndicatorText = "⬤ STANDBY";
            CountdownValue = 0;
            IterText = "";
            OnPropertyChanged(nameof(CanPlay));
        });
    }

    private void OnStepExecuting(StepModel step)
        => UIInvoke(() => StatusText = $"▶ Pas #{step.StepId}: {step.StepType}");

    private void OnStepError(StepModel step, string error)
        => UIInvoke(() => StatusText = $"❌ Eroare pas #{step.StepId}: {error}");

    private void OnCountdown(int sec)
    {
        UIInvoke(() =>
        {
            CountdownValue = sec;
            StatusText = sec > 0 ? $"Start in {sec}s..." : "▶ Start!";
        });
    }

    private void OnPlayPaused()
        => UIInvoke(() => { IsPaused = true; StatusText = "⏸ PAUZA"; });

    private void OnPlayResumed()
        => UIInvoke(() => { IsPaused = false; StatusText = "▶ REDARE ACTIVA"; });

    private void OnIterUpdate(int cur, int total)
        => UIInvoke(() => IterText = total > 1 ? $"Iteratie {cur}/{total}" : "");

    // ── Question Dialog ───────────────────────────────────────────────

    private Task<string> ShowQuestionDialog(StepModel step)
    {
        var tcs = new TaskCompletionSource<string>();
        UIInvoke(() =>
        {
            var dlg = new Views.Dialogs.QuestionDialog(step.QuestionText, step.QuestionButtons);
            dlg.ShowDialog();
            tcs.SetResult(dlg.SelectedAnswer ?? "Continua");
        });
        return tcs.Task;
    }

    // ── Faza 9: Login Config ──────────────────────────────────────────

    private void OpenLoginConfig()
    {
        var dialog = new Views.Dialogs.LoginConfigDialog(CurrentLoginConfig)
        {
            Owner = System.Windows.Application.Current.MainWindow
        };
        if (dialog.ShowDialog() == true && dialog.Result != null)
        {
            CurrentLoginConfig = dialog.Result;
            StatusText = CurrentLoginConfig.Enabled
                ? $"🔐 Login configurat: {CurrentLoginConfig.Mode}"
                : "🔐 Login dezactivat.";
        }
    }

    // ── Faza 10: Simulator ────────────────────────────────────────────

    private async Task StartSimulatorAsync()
    {
        _simulatorCts = new CancellationTokenSource();
        _simulatorOverlay = new SimulatorOverlay();
        _simulatorEngine = _simulatorEngineSvc;

        _simulatorEngine.OnStepSimulating = step =>
            System.Windows.Application.Current.Dispatcher.Invoke(() =>
                _simulatorOverlay.ShowStep(step));

        _simulatorEngine.OnSimulationFinished = success =>
            System.Windows.Application.Current.Dispatcher.Invoke(() =>
            {
                _simulatorOverlay.HideOverlay();
                IsSimulating = false;
                StatusText = success
                    ? "✅ Simulare finalizata cu succes."
                    : "⚠ Simulare oprita.";
            });

        _simulatorEngine.OnStatusChanged = msg =>
            System.Windows.Application.Current.Dispatcher.Invoke(() => StatusText = msg);

        _simulatorEngine.OnProgressChanged = (cur, tot) =>
            System.Windows.Application.Current.Dispatcher.Invoke(() =>
                StatusText = $"🎬 Simulare {cur}/{tot}");

        IsSimulating = true;
        StatusText = "🎬 Simulare pornita...";
        _simulatorOverlay.ShowOverlay();

        await _simulatorEngine.SimulateAsync([.. Steps], _simulatorCts.Token);
    }

    private async Task NextSimulatorStepAsync()
    {
        if (_simulatorEngine != null)
            await _simulatorEngine.NextStepAsync();
    }

    // ── Theme ─────────────────────────────────────────────────────────

    private static void ApplyTheme(string theme)
    {
        // [0] = tema, [1] = Controls.xaml (stilurile lizibile raman mereu incarcate)
        var app = System.Windows.Application.Current;
        if (app == null) return;
        var source = string.Equals(theme, "light", StringComparison.OrdinalIgnoreCase)
            ? "Themes/LightTheme.xaml"
            : "Themes/DarkTheme.xaml";
        var dict = new System.Windows.ResourceDictionary
        {
            Source = new Uri($"pack://application:,,,/AutoPilotDC.UI;component/{source}", UriKind.Absolute),
        };
        var merged = app.Resources.MergedDictionaries;
        if (merged.Count > 0) merged[0] = dict; else merged.Insert(0, dict);
    }

    // ── INotifyPropertyChanged ────────────────────────────────────────
    public event PropertyChangedEventHandler? PropertyChanged;

    private void OnPropertyChanged([CallerMemberName] string? name = null)
        => PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(name));

    // ── Helpers ───────────────────────────────────────────────────────

    private void UpdateStepCount()
        => StepCountText = $"Pasi: {Steps.Count}";

    private static void UIInvoke(Action action)
    {
        if (System.Windows.Application.Current?.Dispatcher?.CheckAccess() == true)
            action();
        else
            System.Windows.Application.Current?.Dispatcher?.Invoke(action);
    }

    // ── IDisposable ───────────────────────────────────────────────────
    public void Dispose()
    {
        _simulatorCts?.Cancel();
        _simulatorCts?.Dispose();

        _recorderSvc.StepRecorded -= OnStepRecorded;
        _recorderSvc.RecordingStarted -= OnRecordingStarted;
        _recorderSvc.RecordingStopped -= OnRecordingStopped;

        _playerSvc.PlaybackFinished -= OnPlaybackFinished;
        _playerSvc.StepExecuting -= OnStepExecuting;
        _playerSvc.StepError -= OnStepError;
        _playerSvc.Countdown -= OnCountdown;
        _playerSvc.Started -= OnPlayStarted;
        _playerSvc.Paused -= OnPlayPaused;
        _playerSvc.Resumed -= OnPlayResumed;
        _playerSvc.IterUpdate -= OnIterUpdate;
    }
}

