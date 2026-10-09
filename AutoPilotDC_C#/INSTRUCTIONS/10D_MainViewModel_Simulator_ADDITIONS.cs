// ============================================================
// AutoPilot DC v3.9 -> C# WPF .NET 8
// MainViewModel.cs � Faza 10: Adaugari SimulatorCmd + NextStepCmd
// INSTRUCTIUNI: Integreaza aceste adaugiri in MainViewModel.cs existent
// Autor: Bogdan Murar (Z003FU5C) - Siemens AG
// ============================================================

// -- ADAUGARI IN MainViewModel.cs ---------------------------------
//
// 1. USING-uri noi (adauga la inceputul fisierului):
//    using AutoPilotDC.Infrastructure.Engines;
//    using AutoPilotDC.UI.Overlays;
//
// 2. In sectiunea "// -- Fields --" adauga:
//    private SimulatorEngine? _simulatorEngine;
//    private SimulatorOverlay? _simulatorOverlay;
//
// 3. In sectiunea "// -- Commands --" adauga:
//    public ICommand SimulatorCmd  { get; }
//    public ICommand NextStepCmd   { get; }
//
// 4. In sectiunea "// -- Properties --" adauga:
//    private bool _isSimulating;
//    public bool IsSimulating
//    {
//        get => _isSimulating;
//        set { _isSimulating = value; OnPropertyChanged(); OnPropertyChanged(nameof(IsNextStepVisible)); }
//    }
//
//    private bool _isDryRun;
//    public bool IsDryRun
//    {
//        get => _isDryRun;
//        set { _isDryRun = value; OnPropertyChanged(); }
//    }
//
//    public bool IsNextStepVisible => IsSimulating;
//
// 5. In constructor, adauga:
//    SimulatorCmd = new RelayCommand(_ => _ = StartSimulatorAsync(), _ => !IsSimulating && Steps.Count > 0);
//    NextStepCmd  = new RelayCommand(_ => _ = NextSimulatorStep(), _ => IsSimulating);
//
// 6. Adauga metodele private:

/*
private async Task StartSimulatorAsync()
{
    if (Steps.Count == 0)
    {
        StatusText = "Nu exista pasi de simulat.";
        return;
    }

    // Initializeaza SimulatorEngine
    _simulatorEngine = new SimulatorEngine(_settings, null);
    _simulatorEngine.IsDryRun = IsDryRun;

    // Initializeaza SimulatorOverlay
    _simulatorOverlay = new SimulatorOverlay();
    _simulatorOverlay.ShowOverlay();

    // Conecteaza callbacks
    _simulatorEngine.OnStepSimulating = step =>
    {
        UIInvoke(() =>
        {
            // Highlight rand in ListView
            SelectedStep = step;

            // Afiseaza overlay la coordonatele pasului
            if (step.X > 0 || step.Y > 0)
                _simulatorOverlay?.ShowAt(step.X, step.Y, step);
        });
    };

    _simulatorEngine.OnStepSimulated = step =>
    {
        UIInvoke(() => StatusText = $"? Simulat: {step.StepType} #{step.StepId}");
    };

    _simulatorEngine.OnSimulationFinished = success =>
    {
        UIInvoke(() =>
        {
            IsSimulating = false;
            _simulatorOverlay?.CloseOverlay();
            StatusText = success
                ? "? Simulare finalizata cu succes."
                : "? Simulare oprita.";
        });
    };

    _simulatorEngine.OnStatusChanged  = msg => UIInvoke(() => StatusText = msg);
    _simulatorEngine.OnProgressChanged = (cur, tot) => UIInvoke(() =>
        StatusText = $"?? Simulare {cur}/{tot}");

    IsSimulating = true;
    StatusText   = "?? Simulare pornita...";

    var cts = new System.Threading.CancellationTokenSource();
    await _simulatorEngine.SimulateAsync(Steps.ToList(), IsDryRun, cts.Token);
}

private Task NextSimulatorStep()
{
    return _simulatorEngine?.NextStepAsync() ?? Task.CompletedTask;
}

private void StopSimulator()
{
    _simulatorEngine?.Stop();
    _simulatorOverlay?.CloseOverlay();
    IsSimulating = false;
}
*/
