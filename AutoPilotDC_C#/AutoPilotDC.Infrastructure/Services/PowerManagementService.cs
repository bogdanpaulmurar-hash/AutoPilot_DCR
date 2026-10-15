// ============================================================
// AutoPilot DC v3.9 -> C# WPF .NET 8
// PowerManagementService.cs
// - Previne intrarea in standby/sleep in timpul rularii
// - Suprima notificarile Windows (Focus Assist / Presentation Mode)
// - Actiuni la finalul ciclului: Sleep / Hibernate / Shutdown
// ============================================================

using System;
using System.Runtime.InteropServices;

namespace AutoPilotDC.Infrastructure.Services;

[System.Runtime.Versioning.SupportedOSPlatform("windows7.0")]
public sealed class PowerManagementService : IDisposable
{
    // -- Win32 ----------------------------------------------------------------
    [DllImport("kernel32.dll", SetLastError = true)]
    private static extern EXECUTION_STATE SetThreadExecutionState(EXECUTION_STATE esFlags);

    [DllImport("PowrProf.dll", SetLastError = false)]
    private static extern bool SetSuspendState(bool hibernate, bool forceCritical, bool disableWakeEvent);

    [DllImport("user32.dll", SetLastError = false)]
    private static extern void ExitWindowsEx(uint uFlags, uint dwReason);

    [Flags]
    private enum EXECUTION_STATE : uint
    {
        ES_AWAYMODE_REQUIRED = 0x00000040,
        ES_CONTINUOUS        = 0x80000000,
        ES_DISPLAY_REQUIRED  = 0x00000002,
        ES_SYSTEM_REQUIRED   = 0x00000001,
    }

    private bool   _preventingSleep;
    private bool   _notificationsSuppressed;

    // -- Sleep prevention -----------------------------------------------------

    /// <summary>
    /// Previne hibernarea/sleep-ul si stingerea ecranului pe durata rularii.
    /// Apelat la inceputul PlayAsync / Recording.
    /// </summary>
    public void PreventSleep()
    {
        if (_preventingSleep) return;
        SetThreadExecutionState(
            EXECUTION_STATE.ES_CONTINUOUS |
            EXECUTION_STATE.ES_SYSTEM_REQUIRED |
            EXECUTION_STATE.ES_DISPLAY_REQUIRED);
        _preventingSleep = true;
    }

    /// <summary>
    /// Restaureaza comportamentul normal de sleep.
    /// Apelat la sfarsitul PlayAsync / Recording.
    /// </summary>
    public void RestoreSleep()
    {
        if (!_preventingSleep) return;
        SetThreadExecutionState(EXECUTION_STATE.ES_CONTINUOUS);
        _preventingSleep = false;
    }

    // -- Notification suppression ("Nu deranja") -----------------------------

    /// <summary>
    /// Activeaza "Nu deranja" (vezi <see cref="DoNotDisturb"/>). Poate dura cateva secunde:
    /// apeleaz-o de pe un fir de fundal.
    /// </summary>
    public void SuppressNotifications()
    {
        if (_notificationsSuppressed) return;
        _notificationsSuppressed = true;
        DoNotDisturb.Enable();
    }

    /// <summary>Reda notificarile, doar daca au fost oprite de noi.</summary>
    public void RestoreNotifications()
    {
        if (!_notificationsSuppressed) return;
        _notificationsSuppressed = false;
        DoNotDisturb.Restore();
    }

    // -- End-of-cycle actions --------------------------------------------------

    /// <summary>
    /// Executa actiunea configurata la finalul unui ciclu de repetare.
    /// </summary>
    public void ExecuteEndOfCycleAction(EndOfCycleAction action)
    {
        switch (action)
        {
            case EndOfCycleAction.Sleep:
                System.Threading.Thread.Sleep(2000); // grace period
                SetSuspendState(hibernate: false, forceCritical: false, disableWakeEvent: false);
                break;

            case EndOfCycleAction.Hibernate:
                System.Threading.Thread.Sleep(2000);
                SetSuspendState(hibernate: true, forceCritical: false, disableWakeEvent: false);
                break;

            case EndOfCycleAction.Shutdown:
                System.Threading.Thread.Sleep(2000);
                ExitWindowsEx(0x00000001 | 0x00000008, 0); // EWX_SHUTDOWN | EWX_FORCEIFHUNG
                break;

            case EndOfCycleAction.LogOff:
                System.Threading.Thread.Sleep(2000);
                ExitWindowsEx(0x00000000, 0); // EWX_LOGOFF
                break;

            case EndOfCycleAction.None:
            default:
                break;
        }
    }

    // -- IDisposable -----------------------------------------------------------

    public void Dispose()
    {
        RestoreSleep();
        RestoreNotifications();
    }
}

/// <summary>Actiune executata la finalul tuturor ciclurilor de repetare.</summary>
public enum EndOfCycleAction
{
    None      = 0,
    Sleep     = 1,
    Hibernate = 2,
    Shutdown  = 3,
    LogOff    = 4,
}
