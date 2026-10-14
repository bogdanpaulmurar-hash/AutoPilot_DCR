// ============================================================
// AutoPilot DC v4 — RPR
// RprEngine.cs — Motorul care executa rutina (arborele de pasi)
//
// Ce face, pe scurt:
//   1. Valideaza ca toate obiectele folosite exista in repository.
//   2. Parcurge pasii; containerele (Daca, Repeta, Pentru fiecare
//      rand, Incearca) isi executa ramurile.
//   3. Pentru fiecare actiune: rezolva {variabilele}, marcheaza
//      elementul pe ecran, executa prin driverul tehnologiei.
//   4. La eroare: reincercare automata, apoi politica pasului
//      (Intreaba / Opreste / Continua / Sari randul).
//   5. Pauza / Pas cu pas / Stop in orice moment.
// ============================================================

using System.Diagnostics;
using System.Globalization;
using AutoPilotDC.Rpr.Excel;
using AutoPilotDC.Rpr.Model;

namespace AutoPilotDC.Rpr.Engine;

public sealed class RprEngine
{
    // ── Semnale interne de control al fluxului ─────────────────
    private abstract class ControlSignal : Exception
    {
        protected ControlSignal(string message) : base(message) { }
    }
    private sealed class LoopSignal : ControlSignal
    {
        public bool Next { get; }
        public LoopSignal(bool next) : base(next ? "continue" : "break") { Next = next; }
    }
    private sealed class SkipRowSignal : ControlSignal
    {
        public bool IsError { get; }
        public SkipRowSignal(string message, bool isError) : base(message) { IsError = isError; }
    }
    private sealed class StopSignal : ControlSignal
    {
        public bool IsError { get; }
        public StopSignal(string message, bool isError) : base(message) { IsError = isError; }
    }
    /// <summary>Eroare trimisa catre cel mai apropiat bloc "Incearca".</summary>
    private sealed class PropagatedStepError : ControlSignal
    {
        public PropagatedStepError(string message) : base(message) { }
    }

    private sealed class RowContext
    {
        public required ExcelTable Table { get; init; }
        public required ForEachRowNode Node { get; init; }
        public int Row { get; set; }
    }

    // ── Dependinte ─────────────────────────────────────────────
    private readonly ObjectRepository _repo;
    private readonly IDriverProvider _drivers;
    private readonly IRunHost _host;
    private readonly string _outputFolder;

    // ── Stare rulare ──────────────────────────────────────────
    private Routine _routine = new();
    private VariableStore _vars = new();
    private ConditionEvaluator _conditions = null!;
    private readonly Stack<RowContext> _rows = new();
    private int _tryDepth;
    private RunResult _result = new();
    private CancellationTokenSource? _cts;

    private readonly object _gateLock = new();
    private TaskCompletionSource<bool> _gate = NewOpenGate();

    public bool IsRunning { get; private set; }
    public bool IsPaused { get; private set; }

    /// <summary>Pas cu pas: motorul se opreste inainte de fiecare pas pana la <see cref="StepOnce"/>.</summary>
    public bool StepMode { get; set; }

    /// <summary>Variabilele dupa ultima rulare (afisate in Studio pentru verificare).</summary>
    public IReadOnlyDictionary<string, string> LastVariables { get; private set; } = new Dictionary<string, string>();

    public RprEngine(ObjectRepository repo, IDriverProvider drivers, IRunHost host, string outputFolder)
    {
        _repo = repo;
        _drivers = drivers;
        _host = host;
        _outputFolder = outputFolder;
    }

    // =========================================================
    // Control: Pauza / Reluare / Pas / Stop
    // =========================================================
    private static TaskCompletionSource<bool> NewOpenGate()
    {
        var tcs = new TaskCompletionSource<bool>(TaskCreationOptions.RunContinuationsAsynchronously);
        tcs.SetResult(true);
        return tcs;
    }

    public void Pause()
    {
        lock (_gateLock)
        {
            if (_gate.Task.IsCompleted)
                _gate = new TaskCompletionSource<bool>(TaskCreationOptions.RunContinuationsAsynchronously);
            IsPaused = true;
        }
    }

    public void Resume()
    {
        lock (_gateLock)
        {
            IsPaused = false;
            _gate.TrySetResult(true);
        }
    }

    /// <summary>In modul pas cu pas: executa urmatorul pas.</summary>
    public void StepOnce() => Resume();

    public void Stop()
    {
        _cts?.Cancel();
        Resume();
    }

    private async Task WaitGateAsync(CancellationToken ct)
    {
        Task gate;
        lock (_gateLock) gate = _gate.Task;
        await gate.WaitAsync(ct);
        if (StepMode) Pause();
    }

    // =========================================================
    // RunAsync — ruleaza rutina completa
    // =========================================================
    public async Task<RunResult> RunAsync(
        Routine routine,
        CancellationToken ct = default,
        IReadOnlyDictionary<string, string>? variableOverrides = null)
    {
        if (IsRunning) throw new InvalidOperationException("O rutina ruleaza deja.");

        IsRunning = true;
        _routine = routine;
        _result = new RunResult();
        _rows.Clear();
        _tryDepth = 0;
        _vars = new VariableStore();
        _conditions = new ConditionEvaluator(_repo, _drivers, _vars);
        _cts = CancellationTokenSource.CreateLinkedTokenSource(ct);
        lock (_gateLock) { _gate = NewOpenGate(); IsPaused = false; }
        if (StepMode) Pause();

        var sw = Stopwatch.StartNew();
        var token = _cts.Token;

        try
        {
            // 1. Variabile initiale
            foreach (var (k, v) in routine.Variables) _vars.Set(k, v);
            if (variableOverrides != null)
                foreach (var (k, v) in variableOverrides) _vars.Set(k, v);

            // 2. Validare obiecte
            var missing = routine.ReferencedObjects()
                .Distinct(StringComparer.OrdinalIgnoreCase)
                .Where(n => _repo.Find(n) == null)
                .ToList();
            if (missing.Count > 0)
            {
                _result.Success = false;
                _result.Message = "Obiecte lipsa din Object Repository: " + string.Join(", ", missing) +
                                  ". Marcheaza-le cu Spy sau corecteaza numele in pasi.";
                Log(RprLogLevel.Error, null, _result.Message);
                return _result;
            }

            Log(RprLogLevel.Info, null, $"Start rutina \"{routine.Name}\"");

            // 3. Executie
            await ExecuteListAsync(routine.Steps, token);

            _result.Success = true;
            _result.Message = _result.Errors == 0
                ? "Rutina finalizata cu succes."
                : $"Rutina finalizata cu {_result.Errors} erori (continuate).";
        }
        catch (StopSignal s)
        {
            _result.Success = !s.IsError;
            _result.Message = string.IsNullOrWhiteSpace(s.Message) ? "Rutina oprita." : s.Message;
        }
        catch (LoopSignal)
        {
            _result.Success = true;
            _result.Message = "Rutina incheiata (Iesi din bucla in afara unei bucle).";
        }
        catch (SkipRowSignal s)
        {
            _result.Success = false;
            _result.Message = s.Message;
        }
        catch (PropagatedStepError e)
        {
            _result.Success = false;
            _result.Message = e.Message;
        }
        catch (OperationCanceledException)
        {
            _result.Success = false;
            _result.Cancelled = true;
            _result.Message = "Rutina oprita de utilizator.";
        }
        catch (Exception ex)
        {
            _result.Success = false;
            _result.Message = "Eroare interna: " + ex.Message;
        }
        finally
        {
            // Inchidem orice Excel ramas deschis (oprire in mijlocul buclei)
            while (_rows.Count > 0)
            {
                var rc = _rows.Pop();
                try { rc.Table.Save(); } catch { /* raportat deja */ }
                rc.Table.Dispose();
            }

            sw.Stop();
            _result.Duration = sw.Elapsed;
            _result.FinalVariables = _vars.All.ToDictionary(k => k.Key, v => v.Value, StringComparer.OrdinalIgnoreCase);
            LastVariables = _result.FinalVariables;
            Log(_result.Success ? RprLogLevel.Info : RprLogLevel.Error, null,
                $"{_result.Message} Durata: {_result.Duration:hh\\:mm\\:ss}, pasi: {_result.StepsExecuted}" +
                (_result.RowsOk + _result.RowsFailed + _result.RowsSkipped > 0
                    ? $", randuri OK: {_result.RowsOk}, esuate: {_result.RowsFailed}, sarite: {_result.RowsSkipped}"
                    : ""));

            _cts.Dispose();
            _cts = null;
            IsRunning = false;
            IsPaused = false;
        }

        return _result;
    }

    /// <summary>"Testeaza pasul" din Studio: un singur pas, fara intrebari, cu variabilele ultimei rulari.</summary>
    public Task<RunResult> RunSingleAsync(Routine routine, RprNode node, CancellationToken ct = default)
    {
        var temp = new Routine
        {
            Name = $"Test: {node.Title}",
            RepositoryPath = routine.RepositoryPath,
            Variables = new Dictionary<string, string>(routine.Variables, StringComparer.OrdinalIgnoreCase),
            Settings = new RoutineSettings
            {
                DefaultErrorPolicy = ErrorPolicy.Stop,
                HighlightBeforeAction = routine.Settings.HighlightBeforeAction,
                HighlightMs = routine.Settings.HighlightMs,
                DefaultTimeoutMs = routine.Settings.DefaultTimeoutMs,
                AutoRetries = 0,
                ScreenshotOnError = false,
            },
            Steps = new List<RprNode> { node },
        };
        foreach (var (k, v) in LastVariables) temp.Variables.TryAdd(k, v);
        return RunAsync(temp, ct);
    }

    // =========================================================
    // Parcurgerea pasilor
    // =========================================================
    private async Task ExecuteListAsync(List<RprNode> nodes, CancellationToken ct)
    {
        // Copie: lista poate fi editata in Studio in timpul rularii
        foreach (var node in nodes.ToList())
        {
            ct.ThrowIfCancellationRequested();
            if (!node.Enabled) continue;
            await WaitGateAsync(ct);
            await ExecuteNodeAsync(node, ct);
        }
    }

    private async Task ExecuteNodeAsync(RprNode node, CancellationToken ct)
    {
        bool isContainer = node is IContainerNode;
        int attempt = 0;

        while (true)
        {
            var sw = Stopwatch.StartNew();
            try
            {
                _host.NodeStarted(node);
                if (node.DelayBeforeMs > 0) await Task.Delay(node.DelayBeforeMs, ct);

                await ExecuteCoreAsync(node, ct);

                if (node.DelayAfterMs > 0) await Task.Delay(node.DelayAfterMs, ct);
                if (!isContainer && _routine.Settings.StepDelayMs > 0)
                    await Task.Delay(_routine.Settings.StepDelayMs, ct);

                _result.StepsExecuted++;
                _host.NodeFinished(node, true);
                return;
            }
            catch (Exception ex) when (ex is not ControlSignal && ex is not OperationCanceledException)
            {
                var message = ex is RprStepException ? ex.Message : $"{ex.GetType().Name}: {ex.Message}";

                // 1. Reincercare automata (doar pasi simpli)
                attempt++;
                if (!isContainer && attempt <= _routine.Settings.AutoRetries)
                {
                    Log(RprLogLevel.Warning, node, $"Esuat ({message}). Reincerc ({attempt}/{_routine.Settings.AutoRetries})...");
                    await Task.Delay(700, ct);
                    continue;
                }

                // 2. Log + captura ecran
                _result.Errors++;
                string shot = await TryErrorScreenshotAsync(node, ct);
                Log(RprLogLevel.Error, node, message, sw.Elapsed.TotalMilliseconds, shot);
                _host.NodeFinished(node, false);

                // 3. Politica de eroare
                var policy = node.OnError;
                if (policy == ErrorPolicy.Inherit)
                {
                    // In interiorul unui "Incearca", eroarea merge la ramura "La eroare"
                    if (_tryDepth > 0) throw new PropagatedStepError(message);
                    policy = _routine.Settings.DefaultErrorPolicy;
                }

                switch (policy)
                {
                    case ErrorPolicy.Continue:
                        return;

                    case ErrorPolicy.SkipRow:
                        if (_rows.Count > 0) throw new SkipRowSignal(message, true);
                        throw new StopSignal(message, true);

                    case ErrorPolicy.Ask:
                        var decision = await _host.AskOnErrorAsync(node, message, _rows.Count > 0, ct);
                        switch (decision)
                        {
                            case ErrorDecision.Retry:
                                attempt = 0;
                                _result.Errors--;
                                Log(RprLogLevel.Info, node, "Reincerc la cererea utilizatorului.");
                                continue;
                            case ErrorDecision.Skip:
                                Log(RprLogLevel.Warning, node, "Pas sarit la cererea utilizatorului.");
                                return;
                            case ErrorDecision.SkipRow when _rows.Count > 0:
                                throw new SkipRowSignal(message, true);
                            default:
                                throw new StopSignal(message, true);
                        }

                    default: // Stop
                        throw new StopSignal(message, true);
                }
            }
        }
    }

    private async Task<string> TryErrorScreenshotAsync(RprNode node, CancellationToken ct)
    {
        if (!_routine.Settings.ScreenshotOnError || node is not ActionNode a) return "";
        try
        {
            var tech = _repo.Find(a.Target)?.Technology ?? a.Technology;
            var folder = Path.Combine(_outputFolder, "erori");
            Directory.CreateDirectory(folder);
            var name = $"{DateTime.Now:yyyyMMdd_HHmmss}_{node.Id}";
            return await _drivers.Get(tech).CaptureErrorScreenshotAsync(folder, name, ct) ?? "";
        }
        catch
        {
            return "";
        }
    }

    // =========================================================
    // Executia fiecarui tip de pas
    // =========================================================
    private Task ExecuteCoreAsync(RprNode node, CancellationToken ct) => node switch
    {
        ActionNode a      => ExecuteActionAsync(a, ct),
        WaitNode w        => ExecuteWaitAsync(w, ct),
        SetVariableNode s => Sync(() => ExecuteSetVariable(s)),
        IfNode i          => ExecuteIfAsync(i, ct),
        LoopNode l        => ExecuteLoopAsync(l, ct),
        ForEachRowNode f  => ExecuteForEachRowAsync(f, ct),
        WriteExcelNode we => Sync(() => ExecuteWriteExcel(we)),
        QuestionNode q    => ExecuteQuestionAsync(q, ct),
        TryNode t         => ExecuteTryAsync(t, ct),
        GroupNode g       => ExecuteListAsync(g.Body, ct),
        LogNode lg        => Sync(() => Log(lg.Level, lg, _vars.Resolve(lg.Message))),
        BreakNode b       => throw new LoopSignal(b.NextIteration),
        StopNode st       => throw new StopSignal(string.IsNullOrWhiteSpace(st.Message) ? "Rutina oprita de pasul Stop." : _vars.Resolve(st.Message), st.AsError),
        LegacyStepNode ls => ExecuteLegacyAsync(ls, ct),
        _ => throw new RprStepException($"Tip de pas necunoscut: {node.GetType().Name}"),
    };

    /// <summary>Executa sincron; exceptiile ajung in Task (tratate uniform).</summary>
    private static Task Sync(Action action)
    {
        try { action(); return Task.CompletedTask; }
        catch (Exception ex) { return Task.FromException(ex); }
    }

    // ── Actiune ────────────────────────────────────────────────
    private async Task ExecuteActionAsync(ActionNode a, CancellationToken ct)
    {
        var info = ActionCatalog.Get(a.Action);

        // 1. Obiectul tinta
        UiObject? obj = null;
        if (!string.IsNullOrWhiteSpace(a.Target))
            obj = _repo.Find(a.Target) ?? throw new RprStepException($"Obiectul [{a.Target}] nu exista in Object Repository.");
        else if (info.NeedsTarget)
            throw new RprStepException($"Pasul \"{info.Label}\" are nevoie de un obiect. Alege-l in proprietatile pasului.");

        var driver = _drivers.Get(obj?.Technology ?? a.Technology);

        // 2. Variabile in valoare
        var value = _vars.Resolve(a.Value, out var unknown);
        if (unknown.Count > 0)
            Log(RprLogLevel.Warning, a, "Variabile necunoscute: " + string.Join(", ", unknown.Select(u => "{" + u + "}")));

        int timeout = a.TimeoutMs > 0 ? a.TimeoutMs : _routine.Settings.DefaultTimeoutMs;

        // 3. Marcare pe ecran inainte de actiune (stil SilkTest)
        if (obj != null && (_routine.Settings.HighlightBeforeAction || a.Action == RprAction.Highlight))
        {
            int ms = Math.Max(150, _routine.Settings.HighlightMs);
            await driver.HighlightAsync(obj, ms, ct);
            await Task.Delay(ms, ct);
            if (a.Action == RprAction.Highlight)
            {
                Log(RprLogLevel.Info, a, "Marcat.");
                return;
            }
        }

        // 4. Executie
        var screenshotsFolder = Path.Combine(_outputFolder, "capturi");
        var output = await driver.ExecuteAsync(
            new ActionRequest(a.Action, obj, value, timeout, a.DirectMode, screenshotsFolder), ct);

        // 5. Rezultat -> variabila
        if (info.ProducesOutput && !string.IsNullOrWhiteSpace(a.OutputVariable))
            _vars.Set(a.OutputVariable, output ?? "");

        Log(RprLogLevel.Info, a, output != null ? $"OK → \"{Shorten(output)}\"" : "OK");
    }

    // ── Asteptare ──────────────────────────────────────────────
    private async Task ExecuteWaitAsync(WaitNode w, CancellationToken ct)
    {
        if (w.Mode == WaitMode.Seconds)
        {
            await Task.Delay(TimeSpan.FromSeconds(Math.Max(0, w.Seconds)), ct);
            return;
        }

        var deadline = DateTime.UtcNow.AddMilliseconds(Math.Max(0, w.TimeoutMs));
        while (true)
        {
            if (await _conditions.EvaluateAsync(w.Condition, ct))
            {
                Log(RprLogLevel.Info, w, "Conditie indeplinita.");
                return;
            }
            if (DateTime.UtcNow >= deadline)
            {
                var msg = $"Conditia \"{w.Condition.Describe()}\" nu s-a indeplinit in {w.TimeoutMs / 1000.0:0.#} s.";
                if (w.FailOnTimeout) throw new RprStepException(msg);
                Log(RprLogLevel.Warning, w, msg + " Continui.");
                return;
            }
            await Task.Delay(300, ct);
        }
    }

    // ── Variabile ──────────────────────────────────────────────
    private void ExecuteSetVariable(SetVariableNode s)
    {
        var current = _vars.Get(s.Name);
        var value = _vars.Resolve(s.Value);
        string result = s.Operation switch
        {
            VariableOperation.Set       => value,
            VariableOperation.Append    => current + value,
            VariableOperation.Increment => AddNumber(current, string.IsNullOrWhiteSpace(value) ? 1 : ParseNumberOr(value, 1)),
            VariableOperation.Decrement => AddNumber(current, -(string.IsNullOrWhiteSpace(value) ? 1 : ParseNumberOr(value, 1))),
            VariableOperation.Trim      => current.Trim(),
            VariableOperation.ToUpper   => current.ToUpperInvariant(),
            VariableOperation.ToLower   => current.ToLowerInvariant(),
            VariableOperation.Replace   => string.IsNullOrEmpty(s.Find) ? current : current.Replace(_vars.Resolve(s.Find), value),
            _ => value,
        };
        _vars.Set(s.Name, result);
        Log(RprLogLevel.Info, s, $"{{{s.Name}}} = \"{Shorten(result)}\"");
    }

    private static decimal ParseNumberOr(string s, decimal fallback) =>
        ConditionEvaluator.TryNumber(s, out var v) ? v : fallback;

    private static string AddNumber(string current, decimal delta)
    {
        ConditionEvaluator.TryNumber(current, out var n);
        return (n + delta).ToString(CultureInfo.InvariantCulture);
    }

    // ── Daca ───────────────────────────────────────────────────
    private async Task ExecuteIfAsync(IfNode i, CancellationToken ct)
    {
        bool ok = await _conditions.EvaluateAsync(i.Condition, ct);
        Log(RprLogLevel.Info, i, ok ? "Adevarat → Atunci" : "Fals → Altfel");
        await ExecuteListAsync(ok ? i.Then : i.Else, ct);
    }

    // ── Repeta ─────────────────────────────────────────────────
    private async Task ExecuteLoopAsync(LoopNode l, CancellationToken ct)
    {
        int max = l.Mode == LoopMode.Times
            ? (int.TryParse(_vars.Resolve(l.Count).Trim(), out var n) ? n
               : throw new RprStepException($"Numarul de repetari \"{l.Count}\" nu e un numar intreg."))
            : Math.Max(1, l.MaxIterations);

        for (int iter = 1; iter <= max; iter++)
        {
            ct.ThrowIfCancellationRequested();

            if (l.Mode == LoopMode.While && !await _conditions.EvaluateAsync(l.Condition, ct))
                return;

            if (!string.IsNullOrWhiteSpace(l.CounterVariable))
                _vars.Set(l.CounterVariable, iter.ToString());

            try
            {
                await ExecuteListAsync(l.Body, ct);
            }
            catch (LoopSignal s)
            {
                if (!s.Next) return;
            }

            if (l.Mode == LoopMode.Until && await _conditions.EvaluateAsync(l.Condition, ct))
                return;
        }

        if (l.Mode != LoopMode.Times)
            Log(RprLogLevel.Warning, l, $"S-a atins limita de {max} repetari (protectie bucla infinita).");
    }

    // ── Pentru fiecare rand Excel ──────────────────────────────
    private async Task ExecuteForEachRowAsync(ForEachRowNode f, CancellationToken ct)
    {
        var path = _vars.Resolve(f.FilePath).Trim().Trim('"');
        var table = ExcelTable.Open(path, _vars.Resolve(f.Sheet), f.HeaderRow);
        var ctx = new RowContext { Table = table, Node = f };
        _rows.Push(ctx);

        try
        {
            int first = table.FirstDataRow(f.StartRow);
            int last = f.EndRow > 0 ? f.EndRow : table.LastDataRow(f.KeyColumn);
            Log(RprLogLevel.Info, f, $"Excel {Path.GetFileName(path)} / {table.SheetName}: randurile {first}-{last}");

            for (int row = first; row <= last; row++)
            {
                ct.ThrowIfCancellationRequested();
                ctx.Row = row;

                // 1. Rand gol = sfarsitul datelor (daca nu s-a dat EndRow)
                if (table.IsRowEmpty(row, f.KeyColumn))
                {
                    if (f.EndRow <= 0) break;
                    continue;
                }

                // 2. Reluare: sarim randurile deja OK
                bool hasStatus = !string.IsNullOrWhiteSpace(f.StatusColumn);
                if (hasStatus && f.SkipCompletedRows &&
                    table.GetCell(row, f.StatusColumn).StartsWith("OK", StringComparison.OrdinalIgnoreCase))
                {
                    _result.RowsSkipped++;
                    continue;
                }

                table.LoadRowInto(_vars, f.RowVariable, row);
                Log(RprLogLevel.Info, f, $"Rand {row}");

                // 3. Pasii pentru rand
                string status; CellColor color; bool stop = false; ControlSignal? rethrow = null;
                try
                {
                    await ExecuteListAsync(f.Body, ct);
                    status = "OK"; color = CellColor.Green; _result.RowsOk++;
                }
                catch (SkipRowSignal s)
                {
                    status = s.IsError ? $"EROARE: {s.Message}" : $"SARIT: {s.Message}";
                    color = s.IsError ? CellColor.Red : CellColor.Yellow;
                    if (s.IsError) _result.RowsFailed++; else _result.RowsSkipped++;
                }
                catch (LoopSignal s)
                {
                    status = "OK"; color = CellColor.Green; _result.RowsOk++;
                    if (!s.Next) stop = true;
                }
                catch (StopSignal s)
                {
                    status = s.IsError ? $"EROARE: {s.Message}" : $"OPRIT: {s.Message}";
                    color = s.IsError ? CellColor.Red : CellColor.Yellow;
                    if (s.IsError) _result.RowsFailed++;
                    rethrow = s;
                }
                catch (PropagatedStepError e)
                {
                    status = $"EROARE: {e.Message}"; color = CellColor.Red; _result.RowsFailed++;
                    rethrow = e;
                }
                catch (OperationCanceledException)
                {
                    if (hasStatus) table.Write(row, f.StatusColumn, $"OPRIT {DateTime.Now:HH:mm:ss}", CellColor.Yellow);
                    throw;
                }

                // 4. Status + culoare + salvare
                if (hasStatus)
                    table.Write(row, f.StatusColumn, Shorten(status, 250), color);
                if (f.ColorRows && color == CellColor.Red)
                    table.ColorRow(row, CellColor.Red);
                if (f.SaveAfterEachRow)
                    table.Save();

                if (rethrow != null) throw rethrow;
                if (stop) break;
            }
        }
        finally
        {
            _rows.Pop();
            try { table.Save(); }
            catch (Exception ex) { Log(RprLogLevel.Error, f, ex.Message); }
            table.Dispose();
            _vars.RemovePrefix(f.RowVariable + ".");
        }
    }

    // ── Scrie in Excel ─────────────────────────────────────────
    private void ExecuteWriteExcel(WriteExcelNode w)
    {
        if (_rows.Count == 0)
            throw new RprStepException("\"Scrie in Excel\" trebuie pus in interiorul unui bloc \"Pentru fiecare rand Excel\".");
        var ctx = _rows.Peek();
        var value = _vars.Resolve(w.Value);
        ctx.Table.Write(ctx.Row, _vars.Resolve(w.Column), value, w.Color);
        Log(RprLogLevel.Info, w, $"Rand {ctx.Row}, [{w.Column}] = \"{Shorten(value)}\"");
    }

    // ── Intrebare ──────────────────────────────────────────────
    private async Task ExecuteQuestionAsync(QuestionNode q, CancellationToken ct)
    {
        var buttons = q.Buttons.Split(',', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries).ToList();
        if (buttons.Count == 0) buttons.Add("OK");

        var answer = await _host.AskAsync(_routine.Name, _vars.Resolve(q.Text), buttons, ct);
        if (!string.IsNullOrWhiteSpace(q.OutputVariable)) _vars.Set(q.OutputVariable, answer);
        Log(RprLogLevel.Info, q, $"Raspuns: {answer}");

        if (!string.IsNullOrWhiteSpace(q.StopButton) && string.Equals(answer, q.StopButton, StringComparison.OrdinalIgnoreCase))
            throw new StopSignal("Oprit de utilizator.", false);

        if (!string.IsNullOrWhiteSpace(q.SkipButton) && string.Equals(answer, q.SkipButton, StringComparison.OrdinalIgnoreCase)
            && _rows.Count > 0)
            throw new SkipRowSignal("sarit de utilizator", false);
    }

    // ── Incearca / La eroare ───────────────────────────────────
    private async Task ExecuteTryAsync(TryNode t, CancellationToken ct)
    {
        string? error = null;
        _tryDepth++;
        try
        {
            await ExecuteListAsync(t.Body, ct);
        }
        catch (PropagatedStepError e)
        {
            error = e.Message;
        }
        finally
        {
            _tryDepth--;
        }

        if (error != null)
        {
            if (!string.IsNullOrWhiteSpace(t.ErrorVariable)) _vars.Set(t.ErrorVariable, error);
            Log(RprLogLevel.Warning, t, "Eroare prinsa → ramura \"La eroare\"");
            await ExecuteListAsync(t.Catch, ct);
        }
    }

    // ── Pas vechi v3.9 ─────────────────────────────────────────
    private async Task ExecuteLegacyAsync(LegacyStepNode ls, CancellationToken ct)
    {
        var exec = _host.LegacyExecutor
                   ?? throw new RprStepException("Pasii vechi (coordonate) nu pot rula in acest mod.");
        var (ok, err) = await exec(ls.Step, ct);
        if (!ok) throw new RprStepException(string.IsNullOrWhiteSpace(err) ? "Pasul vechi a esuat." : err);
        Log(RprLogLevel.Info, ls, "OK");
    }

    // =========================================================
    // Utilitare
    // =========================================================
    private void Log(RprLogLevel level, RprNode? node, string message, double durationMs = 0, string screenshot = "")
    {
        _host.Log(new RunLogEntry
        {
            Level = level,
            NodeId = node?.Id ?? "",
            NodeTitle = node?.Title ?? _routine.Name,
            Message = message,
            ExcelRow = _rows.Count > 0 ? _rows.Peek().Row : 0,
            DurationMs = durationMs,
            Screenshot = screenshot,
        });
    }

    private static string Shorten(string s, int max = 120) =>
        s.Length <= max ? s : s[..max] + "…";
}
