// ============================================================
// AutoPilot DC v3.9 -> C# WPF .NET 8
// RecorderService.cs - Application layer pentru RecorderEngine
// FIX CS0266: GetSteps() returneaza IReadOnlyList<StepModel>,
//             nu List<StepModel> � folosim tipul corect.
// ============================================================
using AutoPilotDC.Core.Interfaces;
using AutoPilotDC.Models;

namespace AutoPilotDC.Application;

[System.Runtime.Versioning.SupportedOSPlatform("windows7.0")]
public class RecorderService
{
    private readonly IRecorder _recorder;
    public RecorderService(IRecorder recorder) => _recorder = recorder;

    // -- Properties --------------------------------------------
    public bool IsRecording => _recorder.IsRecording;
    public bool IsPaused => _recorder.IsPaused;

    // -- Callbacks ---------------------------------------------
    public Action<StepModel>? StepRecorded
    {
        get => _recorder.OnStepRecorded;
        set => _recorder.OnStepRecorded = value;
    }
    public Action? RecordingStarted
    {
        get => _recorder.OnRecordingStarted;
        set => _recorder.OnRecordingStarted = value;
    }
    public Action? RecordingStopped
    {
        get => _recorder.OnRecordingStopped;
        set => _recorder.OnRecordingStopped = value;
    }

    // -- Control -----------------------------------------------
    public void Start() => _recorder.Start();
    public void Stop() => _recorder.Stop();
    public void Pause() => _recorder.Pause();
    public void Resume() => _recorder.Resume();
    public void Clear() => _recorder.Clear();

    // -- Steps -------------------------------------------------
    // FIX CS0266: returnam IReadOnlyList<StepModel>, NU List<StepModel>
    public IReadOnlyList<StepModel> GetSteps() => _recorder.GetSteps();

    public void AddStepManual(StepModel s) => _recorder.AddStepManual(s);

    public void SetSteps(IEnumerable<StepModel> steps) => _recorder.SetSteps(steps);
}