// ============================================================
// AutoPilot DC v3.9 -> C# WPF .NET 8
// RecorderEngine.cs - Implementare IRecorder (conform Phase 1)
// FIX aplicat:
//   - Start() returneaza bool (conform IRecorder)
//   - GetSteps() returneaza IReadOnlyList<StepModel> (conform IRecorder)
//   - Eliminat Keys enum (nu e disponibil fara WinForms ref)
//   - Steps property adaugat (conform IRecorder)
// ============================================================

using System;
using System.Collections.Generic;
using AutoPilotDC.Core.Interfaces;
using AutoPilotDC.Models;

namespace AutoPilotDC.Infrastructure.Recording;

[System.Runtime.Versioning.SupportedOSPlatform("windows7.0")]
public sealed class RecorderEngine : IRecorder, IDisposable
{
    // -- Dependente -------------------------------------------------------
    private readonly ISettingsManager _settings;
    private readonly MouseRecorder _mouseRecorder;
    private readonly KeyboardRecorder _keyboardRecorder;

    // -- State ------------------------------------------------------------
    private readonly List<StepModel> _steps = new List<StepModel>();
    private readonly object _lock = new object();
    private int _counter = 0;

    private volatile bool _isRecording;
    private volatile bool _isPaused;

    // -- IRecorder: Properties --------------------------------------------
    public bool IsRecording => _isRecording;
    public bool IsPaused => _isPaused;

    // -- IRecorder: Steps property (conform IRecorder) --------------------
    public IReadOnlyList<StepModel> Steps
    {
        get { lock (_lock) return _steps.AsReadOnly(); }
    }

    // -- IRecorder: Callbacks (Action<> � identic Python) -----------------
    /// <summary>Callback apelat la fiecare pas inregistrat.</summary>
    public Action<StepModel>? OnStepRecorded { get; set; }

    /// <summary>Callback apelat la start inregistrare.</summary>
    public Action? OnRecordingStarted { get; set; }

    /// <summary>Callback apelat la stop inregistrare.</summary>
    public Action? OnRecordingStopped { get; set; }

    // -- Constructor ------------------------------------------------------
    public RecorderEngine(ISettingsManager settings)
    {
        _settings = settings;
        _mouseRecorder = new MouseRecorder();
        _keyboardRecorder = new KeyboardRecorder();

        // Conecteaza evenimentele din sub-recordere
        _mouseRecorder.StepRecorded += OnStepFromRecorder;
        _keyboardRecorder.StepRecorded += OnStepFromRecorder;
    }

    // -- IRecorder: Control -----------------------------------------------

    /// <summary>
    /// Porneste inregistrarea.
    /// Returneaza false daca deja activa (identic Python: return False daca _recording).
    /// </summary>
    public bool Start()
    {
        if (_isRecording) return false;

        _settings.Load();
        AppSettings s = _settings.Current;

        lock (_lock)
        {
            _isRecording = true;
            _isPaused = false;
        }

        // Start sub-recordere
        _mouseRecorder.Start(s.RecordMouseMove, s.MouseMoveThreshold);
        _keyboardRecorder.Start();

        _mouseRecorder.SetState(true, false);
        _keyboardRecorder.SetState(true, false);

        OnRecordingStarted?.Invoke();
        return true;
    }

    /// <summary>Opreste inregistrarea.</summary>
    public void Stop()
    {
        if (!_isRecording) return;

        lock (_lock)
        {
            _isRecording = false;
            _isPaused = false;
        }

        _mouseRecorder.SetState(false, false);
        _keyboardRecorder.SetState(false, false);

        _mouseRecorder.Stop();
        _keyboardRecorder.Stop();

        OnRecordingStopped?.Invoke();
    }

    /// <summary>Pune inregistrarea pe pauza.</summary>
    public void Pause()
    {
        lock (_lock) _isPaused = true;
        _mouseRecorder.SetState(_isRecording, true);
        _keyboardRecorder.SetState(_isRecording, true);
    }

    /// <summary>Reia inregistrarea dupa pauza.</summary>
    public void Resume()
    {
        lock (_lock) _isPaused = false;
        _mouseRecorder.SetState(_isRecording, false);
        _keyboardRecorder.SetState(_isRecording, false);
    }

    /// <summary>Sterge toti pasii inregistrati.</summary>
    public void Clear()
    {
        lock (_lock)
        {
            _steps.Clear();
            _counter = 0;
        }
    }

    /// <summary>Adauga manual un pas (din Step Builder sau UI).</summary>
    public void AddStepManual(StepModel step)
    {
        lock (_lock)
        {
            step.StepId = ++_counter;
            _steps.Add(step);
        }
        OnStepRecorded?.Invoke(step);
    }

    /// <summary>
    /// Returneaza pasii inregistrati ca IReadOnlyList (conform IRecorder).
    /// </summary>
    public IReadOnlyList<StepModel> GetSteps()
    {
        lock (_lock) return _steps.AsReadOnly();
    }

    /// <summary>Seteaza pasii (pentru load rutina din fisier).</summary>
    public void SetSteps(IEnumerable<StepModel> steps)
    {
        lock (_lock)
        {
            _steps.Clear();
            _counter = 0;
            foreach (var s in steps)
            {
                s.StepId = ++_counter;
                _steps.Add(s);
            }
        }
    }

    // -- Handler intern ---------------------------------------------------
    private void OnStepFromRecorder(StepModel step)
    {
        // v4.1: fereastra + amprenta zonei, pentru sistemul de preventie la rulare
        AutoPilotDC.Infrastructure.Safety.SafetyGuard.RecordContext(step);

        lock (_lock)
        {
            step.StepId = ++_counter;
            _steps.Add(step);
        }
        OnStepRecorded?.Invoke(step);
    }

    // -- IDisposable ------------------------------------------------------
    public void Dispose()
    {
        Stop();
        _mouseRecorder.StepRecorded -= OnStepFromRecorder;
        _keyboardRecorder.StepRecorded -= OnStepFromRecorder;
    }
}