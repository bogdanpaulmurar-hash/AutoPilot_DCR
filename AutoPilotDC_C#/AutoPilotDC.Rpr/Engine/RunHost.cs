// ============================================================
// AutoPilot DC v4 — RPR
// RunHost.cs — Legatura motor <-> interfata (log, intrebari, decizii)
// Studio implementeaza IRunHost; rularea programata are propria implementare.
// ============================================================

using AutoPilotDC.Models;
using AutoPilotDC.Rpr.Model;

namespace AutoPilotDC.Rpr.Engine;

public sealed class RunLogEntry
{
    public DateTime Time { get; init; } = DateTime.Now;
    public RprLogLevel Level { get; init; }
    public string NodeId { get; init; } = "";
    public string NodeTitle { get; init; } = "";
    public string Message { get; init; } = "";
    /// <summary>Randul Excel curent (0 = in afara unei bucle Excel).</summary>
    public int ExcelRow { get; init; }
    public double DurationMs { get; init; }
    public string Screenshot { get; init; } = "";

    public override string ToString() =>
        $"{Time:HH:mm:ss} [{Level}]{(ExcelRow > 0 ? $" rand {ExcelRow}" : "")} {NodeTitle}: {Message}";
}

/// <summary>Decizia utilizatorului cand un pas esueaza (politica Ask).</summary>
public enum ErrorDecision { Retry, Skip, SkipRow, Stop }

// ── v4.1: Sistemul de preventie ─────────────────────────────────

/// <summary>Ceva difera fata de ce asteapta rutina (fereastra de eroare, valoare diferita, eroare SAP...).</summary>
public sealed record RunAlert(string Title, string Details, string Key);

/// <summary>Raspunsul utilizatorului la o alerta (rutina sta pe pauza pana atunci).</summary>
public enum AlertDecision { Continue, IgnoreSimilar, SkipRow, Stop }

/// <summary>
/// Verificari dependente de sistemul de operare (ferestre de eroare, aplicatii blocate),
/// facute inainte de fiecare actiune. Implementarea Windows e in Studio.
/// </summary>
public interface IRunGuard
{
    void BeginRun();

    /// <summary>Null = totul e in regula.</summary>
    RunAlert? CheckBeforeAction(ActionNode node);

    /// <summary>Utilizatorul a raspuns: starea de acum a ecranului devine "normala".</summary>
    void Acknowledge();
}

public interface IRunHost
{
    void Log(RunLogEntry entry);

    void NodeStarted(RprNode node);

    void NodeFinished(RprNode node, bool success);

    /// <summary>Intrebare cu butoane personalizate. Returneaza textul butonului apasat.</summary>
    Task<string> AskAsync(string title, string text, IReadOnlyList<string> buttons, CancellationToken ct);

    /// <summary>Un pas a esuat si politica e "Intreaba".</summary>
    Task<ErrorDecision> AskOnErrorAsync(RprNode node, string error, bool insideExcelLoop, CancellationToken ct);

    /// <summary>
    /// v4.1: sistemul de preventie a gasit o diferenta. Implicit (fara utilizator):
    /// in bucla Excel se sare randul, altfel rutina se opreste.
    /// </summary>
    Task<AlertDecision> AskAlertAsync(RprNode node, RunAlert alert, bool insideExcelLoop, CancellationToken ct)
        => Task.FromResult(insideExcelLoop ? AlertDecision.SkipRow : AlertDecision.Stop);

    /// <summary>Executa un pas vechi v3.9 (coordonate). Null = nu e disponibil.</summary>
    Func<StepModel, CancellationToken, Task<(bool Success, string Error)>>? LegacyExecutor { get; }
}

/// <summary>Host fara interfata (rulare programata): logheaza in consola, nu intreaba.</summary>
public sealed class HeadlessRunHost : IRunHost
{
    private readonly Action<string> _write;

    public HeadlessRunHost(Action<string>? write = null) => _write = write ?? Console.WriteLine;

    public List<RunLogEntry> Entries { get; } = new();

    public void Log(RunLogEntry entry) { lock (Entries) Entries.Add(entry); _write(entry.ToString()); }
    public void NodeStarted(RprNode node) { }
    public void NodeFinished(RprNode node, bool success) { }

    // Fara utilizator: alegem primul buton (de obicei "Continua")
    public Task<string> AskAsync(string title, string text, IReadOnlyList<string> buttons, CancellationToken ct)
        => Task.FromResult(buttons.FirstOrDefault() ?? "");

    // Fara utilizator: la eroare sarim randul (daca suntem in Excel), altfel oprim
    public Task<ErrorDecision> AskOnErrorAsync(RprNode node, string error, bool insideExcelLoop, CancellationToken ct)
        => Task.FromResult(insideExcelLoop ? ErrorDecision.SkipRow : ErrorDecision.Stop);

    public Func<StepModel, CancellationToken, Task<(bool Success, string Error)>>? LegacyExecutor { get; set; }
}

public sealed class RunResult
{
    public bool Success { get; set; }
    public bool Cancelled { get; set; }
    public string Message { get; set; } = "";
    public int StepsExecuted { get; set; }
    public int Errors { get; set; }
    public int RowsOk { get; set; }
    public int RowsFailed { get; set; }
    public int RowsSkipped { get; set; }
    public TimeSpan Duration { get; set; }
    public Dictionary<string, string> FinalVariables { get; set; } = new();
}
