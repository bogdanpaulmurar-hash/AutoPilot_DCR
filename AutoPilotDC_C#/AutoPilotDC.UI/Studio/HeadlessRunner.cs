// ============================================================
// AutoPilot DC v4 — Studio RPR
// HeadlessRunner.cs — Rulare fara interfata (programari Windows):
//   AutoPilotDC.UI.exe --run "C:\...\rutina.rpr.json"
// Logul se salveaza ca Excel in %AppData%\AutoPilotDC\Studio\rezultate.
// ============================================================

using System.IO;
using AutoPilotDC.Infrastructure.Engines;
using AutoPilotDC.Infrastructure.Services;
using AutoPilotDC.Rpr.Engine;
using AutoPilotDC.Rpr.Storage;

namespace AutoPilotDC.UI.Studio;

public static class HeadlessRunner
{
    /// <summary>Ruleaza rutina si inchide aplicatia. Cod de iesire: 0 = succes, 1 = esec, 2 = fisier invalid.</summary>
    public static async Task<int> RunAsync(string routinePath)
    {
        var textLog = Path.Combine(RprPaths.Output, $"Log_programat_{DateTime.Now:yyyyMMdd_HHmmss}.txt");
        await using var writer = new StreamWriter(textLog) { AutoFlush = true };

        try
        {
            var repo = RepositoryStore.Load(null);
            var routine = RoutineStore.Load(routinePath, repo);
            if (!string.IsNullOrWhiteSpace(routine.RepositoryPath))
                repo = RepositoryStore.Load(routine.RepositoryPath);

            var desktop = new DesktopEngine();
            var host = new HeadlessRunHost(line => writer.WriteLine(line))
            {
                LegacyExecutor = (step, ct) => desktop.ExecuteStepAsync(step, ct),
            };

            await using var drivers = new StudioDriverProvider(StudioSettings.Load());
            var engine = new RprEngine(repo, drivers, host, RprPaths.Output);

            // v4.1: fara notificari + chenar RUN si la rularile programate
            bool dnd = routine.Settings.DoNotDisturb;
            if (dnd)
            {
                await Task.Run(() => DoNotDisturb.Enable(wait: true));
                writer.WriteLine(DoNotDisturb.LastMessage);
            }
            Overlays.RunFrame.Show(Overlays.FrameMode.Run);
            RunResult result;
            try
            {
                result = await engine.RunAsync(routine);
            }
            finally
            {
                Overlays.RunFrame.Hide();
                // procesul se inchide imediat dupa: asteptam ca notificarile sa revina efectiv
                if (dnd) await Task.Run(() => DoNotDisturb.Restore(wait: true));
            }

            var xlsx = Path.Combine(RprPaths.Output,
                $"Log_programat_{Rpr.Model.ObjectRepository.Sanitize(routine.Name)}_{DateTime.Now:yyyyMMdd_HHmmss}.xlsx");
            try { RunLogExporter.ExportXlsx(host.Entries, xlsx); }
            catch (Exception ex) { writer.WriteLine("Exportul logului in Excel a esuat: " + ex.Message); }

            return result.Success ? 0 : 1;
        }
        catch (Exception ex)
        {
            writer.WriteLine("EROARE: " + ex);
            return 2;
        }
    }
}
