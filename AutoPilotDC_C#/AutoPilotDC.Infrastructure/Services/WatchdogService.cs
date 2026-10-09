// ============================================================
// AutoPilot DC v3.9 -> C# WPF .NET 8
// WatchdogService.cs
// - Detecteaza abateri in timpul executiei rutinei
// - Monitorizeaza: timing, miscarea mouse-ului de catre user,
//   aparitia ferestrelor neasteptate, erori repetate
// - La detectie: pauza instant + intrebare utilizator
// ============================================================

using System;
using System.Diagnostics;
using System.Runtime.InteropServices;
using System.Threading;
using System.Threading.Tasks;
using AutoPilotDC.Models;

namespace AutoPilotDC.Infrastructure.Services;

[System.Runtime.Versioning.SupportedOSPlatform("windows7.0")]
public sealed class WatchdogService : IDisposable
{
    // -- Win32 ----------------------------------------------------------------
    [DllImport("user32.dll")]
    private static extern bool GetCursorPos(out POINT lpPoint);

    [DllImport("user32.dll")]
    private static extern IntPtr GetForegroundWindow();

    [DllImport("user32.dll", CharSet = CharSet.Unicode)]
    private static extern int GetWindowText(IntPtr hWnd, System.Text.StringBuilder lpString, int nMaxCount);

    [StructLayout(LayoutKind.Sequential)]
    private struct POINT { public int X; public int Y; }

    // -- Configuration ---------------------------------------------------------
    private const int  MOUSE_DELTA_THRESHOLD  = 15;   // px - cat de mult poate misca user mouse-ul
    private const int  STEP_TIMEOUT_FACTOR    = 5;    // x mai mult decat delay-ul pasului = anomalie
    private const int  MIN_STEP_TIMEOUT_MS    = 8000; // min 8s inainte sa consideram timeout

    // -- State -----------------------------------------------------------------
    private CancellationTokenSource? _cts;
    private Task? _monitorTask;

    private volatile bool _active;
    private POINT   _expectedMousePos;
    private bool    _mouseTrackingEnabled;
    private string? _expectedWindowTitle;
    private double  _currentStepExpectedDurationMs;

    private readonly Stopwatch _stepStopwatch = new();

    // -- Settings (injectate din AppSettings) ---------------------------------
    public bool EnableMouseTakeoverDetection { get; set; } = true;
    public bool EnableWindowChangeDetection  { get; set; } = true;
    public bool EnableTimingAnomalyDetection { get; set; } = true;

    // -- Callbacks -------------------------------------------------------------

    /// <summary>
    /// Apelat cand Watchdog detecteaza o anomalie.
    /// Returneaza: true = continua, false = opreste rutina.
    /// </summary>
    public Func<WatchdogAnomaly, Task<bool>>? OnAnomalyDetected { get; set; }

    /// <summary>Mesaj de status pentru UI.</summary>
    public Action<string>? OnStatusChanged { get; set; }

    // -- Public API ------------------------------------------------------------

    /// <summary>Porneste monitorizarea. Apelat inainte de PlayAsync.</summary>
    public void Start()
    {
        _cts        = new CancellationTokenSource();
        _active     = true;
        _monitorTask = Task.Run(() => MonitorLoop(_cts.Token));
    }

    /// <summary>Opreste monitorizarea. Apelat dupa PlayAsync.</summary>
    public void Stop()
    {
        _active = false;
        _cts?.Cancel();
    }

    /// <summary>
    /// Notifica Watchdog-ul despre inceperea unui pas nou.
    /// Seteaza pozitia mouse-ului asteptata si durata estimata.
    /// </summary>
    public void NotifyStepStarted(StepModel step)
    {
        _stepStopwatch.Restart();
        _currentStepExpectedDurationMs = Math.Max(
            MIN_STEP_TIMEOUT_MS,
            (step.DelayBefore + step.DelayAfter + 1.0) * 1000 * STEP_TIMEOUT_FACTOR);

        // Seteaza pozitia mouse asteptata (pentru pasi cu coordonate)
        bool isCoordStep = step.StepType is "CLICK" or "DBLCLICK" or "RIGHTCLICK" or "MOVE" or "SCROLL";
        if (isCoordStep && step.X > 0 && step.Y > 0)
        {
            _expectedMousePos    = new POINT { X = step.X, Y = step.Y };
            _mouseTrackingEnabled = EnableMouseTakeoverDetection;
        }
        else
        {
            _mouseTrackingEnabled = false;
        }

        // Captureaza titlul ferestrei active (pentru detectie schimbare fereastra)
        if (EnableWindowChangeDetection)
        {
            var hwnd = GetForegroundWindow();
            var sb   = new System.Text.StringBuilder(256);
            GetWindowText(hwnd, sb, 256);
            _expectedWindowTitle = sb.ToString();
        }
    }

    /// <summary>Notifica Watchdog-ul ca pasul s-a terminat cu succes.</summary>
    public void NotifyStepFinished()
    {
        _stepStopwatch.Reset();
        _mouseTrackingEnabled = false;
        _expectedWindowTitle  = null;
    }

    // -- Monitor loop ----------------------------------------------------------

    private async Task MonitorLoop(CancellationToken ct)
    {
        while (!ct.IsCancellationRequested && _active)
        {
            try
            {
                await Task.Delay(500, ct);
                if (!_active) break;

                // 1. Detectie mouse takeover
                if (_mouseTrackingEnabled && EnableMouseTakeoverDetection)
                {
                    GetCursorPos(out var current);
                    int dx = Math.Abs(current.X - _expectedMousePos.X);
                    int dy = Math.Abs(current.Y - _expectedMousePos.Y);

                    if (dx > MOUSE_DELTA_THRESHOLD || dy > MOUSE_DELTA_THRESHOLD)
                    {
                        _mouseTrackingEnabled = false; // evita re-triggering
                        await ReportAnomaly(new WatchdogAnomaly
                        {
                            Type        = AnomalyType.MouseTakeover,
                            Description = $"Mouse mutat de utilizator! Pozitie asteptata: ({_expectedMousePos.X},{_expectedMousePos.Y}), Curenta: ({current.X},{current.Y}). Delta: dx={dx}, dy={dy}.",
                        }, ct);
                    }
                }

                // 2. Detectie timeout pas
                if (EnableTimingAnomalyDetection && _stepStopwatch.IsRunning)
                {
                    if (_stepStopwatch.ElapsedMilliseconds > _currentStepExpectedDurationMs)
                    {
                        _stepStopwatch.Reset(); // evita re-triggering
                        await ReportAnomaly(new WatchdogAnomaly
                        {
                            Type        = AnomalyType.StepTimeout,
                            Description = $"Pasul dureaza prea mult! Asteptat: <{_currentStepExpectedDurationMs / 1000:F1}s, Actual: {_stepStopwatch.Elapsed.TotalSeconds:F1}s. Posibil dialog/fereastra blocheaza.",
                        }, ct);
                    }
                }

                // 3. Detectie schimbare fereastra activa
                if (EnableWindowChangeDetection && _expectedWindowTitle != null)
                {
                    var hwnd = GetForegroundWindow();
                    var sb   = new System.Text.StringBuilder(256);
                    GetWindowText(hwnd, sb, 256);
                    var current = sb.ToString();

                    if (!string.IsNullOrEmpty(current) &&
                        !string.IsNullOrEmpty(_expectedWindowTitle) &&
                        current != _expectedWindowTitle &&
                        !current.Contains("AutoPilot", StringComparison.OrdinalIgnoreCase))
                    {
                        _expectedWindowTitle = current; // actualizeaza (nu re-trigger)
                        await ReportAnomaly(new WatchdogAnomaly
                        {
                            Type        = AnomalyType.UnexpectedWindow,
                            Description = $"Fereastra activa s-a schimbat!\nAsteptat: \"{_expectedWindowTitle}\"\nCurenta: \"{current}\".",
                        }, ct);
                    }
                }
            }
            catch (OperationCanceledException) { break; }
            catch { /* ignora erori de monitorizare */ }
        }
    }

    private async Task ReportAnomaly(WatchdogAnomaly anomaly, CancellationToken ct)
    {
        if (ct.IsCancellationRequested) return;
        OnStatusChanged?.Invoke($"[WATCHDOG] {anomaly.Type}: {anomaly.Description}");

        if (OnAnomalyDetected != null)
            await OnAnomalyDetected(anomaly);
    }

    // -- IDisposable -----------------------------------------------------------
    public void Dispose()
    {
        Stop();
        _cts?.Dispose();
    }
}

// -- Data types ----------------------------------------------------------------

public enum AnomalyType
{
    MouseTakeover,
    StepTimeout,
    UnexpectedWindow,
    StepError,
}

public sealed class WatchdogAnomaly
{
    public AnomalyType Type        { get; init; }
    public string      Description { get; init; } = "";
}
