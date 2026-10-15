// ============================================================
// AutoPilot DC v4.1 — Studio RPR
// StudioGuard.cs — Verificarile Windows ale sistemului de preventie:
//   - ferestre noi de eroare / avertisment aparute in timpul rularii
//   - aplicatia activa nu raspunde
// (Valorile diferite si erorile din bara SAP sunt verificate de motor.)
// ============================================================

using AutoPilotDC.Infrastructure.Safety;
using AutoPilotDC.Rpr.Engine;
using AutoPilotDC.Rpr.Model;

namespace AutoPilotDC.UI.Studio;

public sealed class StudioGuard : IRunGuard
{
    private readonly WindowWatcher _windows = new();

    public void BeginRun() => _windows.Reset();

    public void Acknowledge() => _windows.AcceptCurrent();

    public RunAlert? CheckBeforeAction(ActionNode node)
    {
        // Rutinele pe obiecte trateaza singure dialogurile asteptate -> raportam doar ce arata a eroare
        var alert = _windows.CheckNewWindows(reportAllDialogs: false);
        if (alert != null) return new RunAlert(alert.Title, alert.Details, alert.IgnoreKey);

        var fg = ScreenProbe.Foreground();
        if (!ScreenProbe.IsOwn(fg) && ScreenProbe.IsHung(fg.Handle))
            return new RunAlert("Aplicatia nu raspunde",
                $"Fereastra {fg} nu raspunde (Windows o arata ca \"Not Responding\").\nAsteapta sa-si revina, apoi apasa Continua.",
                "hung:" + fg.Process);
        return null;
    }
}
