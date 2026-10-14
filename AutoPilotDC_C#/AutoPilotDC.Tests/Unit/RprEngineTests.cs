// ============================================================
// AutoPilot DC v4 — Teste pentru motorul RPR (fara browser / SAP:
// un driver fals simuleaza ecranul).
// Rulare: dotnet test  (sau Test Explorer in Visual Studio)
// ============================================================

using System.Text.Json;
using ClosedXML.Excel;
using AutoPilotDC.Models;
using AutoPilotDC.Rpr.Engine;
using AutoPilotDC.Rpr.Excel;
using AutoPilotDC.Rpr.Model;
using AutoPilotDC.Rpr.Storage;
using Xunit;
using Condition = AutoPilotDC.Rpr.Model.Condition;

namespace AutoPilotDC.Tests.Unit;

// ── Driver fals: "ecranul" e un dictionar nume obiect -> text ──
internal sealed class FakeDriver : IUiDriver, IDriverProvider
{
    public Dictionary<string, string> Screen { get; } = new(StringComparer.OrdinalIgnoreCase);
    public List<string> Actions { get; } = new();
    public int FailuresBeforeSuccess { get; set; }

    public UiTechnology Technology => UiTechnology.Web;
    public string DisplayName => "Fake";
    public IUiDriver Get(UiTechnology technology) => this;

    public Task<ElementState> GetStateAsync(UiObject obj, int timeoutMs, CancellationToken ct) =>
        Task.FromResult(Screen.TryGetValue(obj.Name, out var t)
            ? new ElementState(true, true, true, t, t, obj.Locators.FirstOrDefault())
            : ElementState.NotFound);

    public Task<string?> ExecuteAsync(ActionRequest r, CancellationToken ct)
    {
        if (r.Target != null && !Screen.ContainsKey(r.Target.Name))
            throw new ElementNotFoundException(r.Target, r.TimeoutMs);
        if (FailuresBeforeSuccess > 0)
        {
            FailuresBeforeSuccess--;
            throw new RprStepException("esec simulat");
        }
        Actions.Add($"{r.Action}:{r.Target?.Name}:{r.Value}");
        if (r.Action == RprAction.TypeText && r.Target != null) Screen[r.Target.Name] = r.Value;
        return Task.FromResult(r.Action is RprAction.ReadText or RprAction.ReadValue && r.Target != null
            ? Screen[r.Target.Name]
            : null);
    }

    public Task HighlightAsync(UiObject obj, int durationMs, CancellationToken ct) => Task.CompletedTask;
    public Task<string?> CaptureErrorScreenshotAsync(string folder, string name, CancellationToken ct) => Task.FromResult<string?>(null);
    public ValueTask DisposeAsync() => ValueTask.CompletedTask;
}

internal sealed class FakeHost : IRunHost
{
    public List<RunLogEntry> Log { get; } = new();
    public Queue<string> Answers { get; } = new();
    public ErrorDecision OnError { get; set; } = ErrorDecision.Stop;

    void IRunHost.Log(RunLogEntry entry) => Log.Add(entry);
    public void NodeStarted(RprNode node) { }
    public void NodeFinished(RprNode node, bool success) { }
    public Task<string> AskAsync(string title, string text, IReadOnlyList<string> buttons, CancellationToken ct) =>
        Task.FromResult(Answers.Count > 0 ? Answers.Dequeue() : buttons[0]);
    public Task<ErrorDecision> AskOnErrorAsync(RprNode node, string error, bool insideExcelLoop, CancellationToken ct) =>
        Task.FromResult(OnError);
    public Func<StepModel, CancellationToken, Task<(bool Success, string Error)>>? LegacyExecutor => null;
}

public class RprEngineTests
{
    private static (RprEngine Engine, FakeDriver Driver, FakeHost Host, ObjectRepository Repo) Create()
    {
        var repo = new ObjectRepository();
        repo.Add(new UiObject { Name = "Camp", Locators = { new Locator(LocatorKind.Id, "camp") } });
        repo.Add(new UiObject { Name = "Buton", Locators = { new Locator(LocatorKind.Id, "btn") } });
        repo.Add(new UiObject { Name = "Lipsa", Locators = { new Locator(LocatorKind.Id, "lipsa") } });
        var driver = new FakeDriver();
        driver.Screen["Camp"] = "";
        driver.Screen["Buton"] = "OK";
        var host = new FakeHost();
        var engine = new RprEngine(repo, driver, host, Path.Combine(Path.GetTempPath(), "apdc-teste"));
        return (engine, driver, host, repo);
    }

    private static Routine NewRoutine(params RprNode[] steps)
    {
        var r = new Routine { Name = "Test" };
        r.Settings.HighlightBeforeAction = false;
        r.Settings.AutoRetries = 0;
        r.Settings.ScreenshotOnError = false;
        r.Settings.DefaultErrorPolicy = ErrorPolicy.Stop;
        r.Steps.AddRange(steps);
        return r;
    }

    // ── Variabile ───────────────────────────────────────────
    [Fact]
    public void Variables_ResolveKnownUnknownAndEscapes()
    {
        var v = new VariableStore();
        v.Set("Nume", "Ana Maria");
        v.Set("Rand.IBase", "12345");
        Assert.Equal("Salut Ana Maria / 12345", v.Resolve("Salut {Nume} / {Rand.IBase}"));
        Assert.Equal("{Necunoscut}", v.Resolve("{Necunoscut}", out var unknown));
        Assert.Single(unknown);
        Assert.Equal("{literal}", v.Resolve("{{literal}}"));
        Assert.Equal("Ana%20Maria", v.Resolve("{Nume:url}"));
        Assert.Equal("ANA MARIA", v.Resolve("{nume:upper}"));
        Assert.Matches(@"^\d{2}\.\d{2}\.\d{4}$", v.Resolve("{Azi}"));
    }

    [Theory]
    [InlineData("1.234,5", 1234.5)]
    [InlineData("1,234.5", 1234.5)]
    [InlineData("12,5", 12.5)]
    [InlineData("1,234", 1234)]
    [InlineData("-7", -7)]
    public void Numbers_ParseRomanianAndEnglishFormats(string text, double expected)
    {
        Assert.True(ConditionEvaluator.TryNumber(text, out var d));
        Assert.Equal((decimal)expected, d);
    }

    [Fact]
    public void Compare_NumericWhenPossible()
    {
        Assert.True(ConditionEvaluator.Compare("10", CompareOperator.GreaterThan, "9", true));   // numeric, nu alfabetic
        Assert.True(ConditionEvaluator.Compare("abc", CompareOperator.Contains, "B", true));
        Assert.False(ConditionEvaluator.Compare("abc", CompareOperator.Contains, "B", false));
        Assert.True(ConditionEvaluator.Compare("5,0", CompareOperator.Equals, "5", true));
        Assert.True(ConditionEvaluator.Compare("  ", CompareOperator.IsEmpty, "", true));
    }

    // ── Flux ────────────────────────────────────────────────
    [Fact]
    public async Task Loop_If_Break_Variables()
    {
        var (engine, _, _, _) = Create();
        var loop = new LoopNode { Count = "10", CounterVariable = "i" };
        loop.Body.Add(new SetVariableNode { Name = "Suma", Operation = VariableOperation.Increment, Value = "{i}" });
        var stop = new IfNode { Condition = new Condition { Kind = ConditionKind.Compare, Left = "{i}", Operator = CompareOperator.Equals, Right = "4" } };
        stop.Then.Add(new BreakNode());
        loop.Body.Add(stop);

        var result = await engine.RunAsync(NewRoutine(new SetVariableNode { Name = "Suma", Value = "0" }, loop));

        Assert.True(result.Success, result.Message);
        Assert.Equal("10", result.FinalVariables["Suma"]); // 1+2+3+4
    }

    [Fact]
    public async Task Action_TypeAndRead_WithVariables()
    {
        var (engine, driver, _, _) = Create();
        var r = NewRoutine(
            new ActionNode { Action = RprAction.TypeText, Target = "Camp", Value = "Cod-{X}" },
            new ActionNode { Action = RprAction.ReadText, Target = "Camp", OutputVariable = "Citit" });
        r.Variables["X"] = "42";

        var result = await engine.RunAsync(r);

        Assert.True(result.Success, result.Message);
        Assert.Equal("Cod-42", result.FinalVariables["Citit"]);
        Assert.Contains("TypeText:Camp:Cod-42", driver.Actions);
    }

    [Fact]
    public async Task MissingObjectInRepository_FailsBeforeRunning()
    {
        var (engine, driver, _, _) = Create();
        var result = await engine.RunAsync(NewRoutine(new ActionNode { Action = RprAction.Click, Target = "NuExista" }));
        Assert.False(result.Success);
        Assert.Contains("NuExista", result.Message);
        Assert.Empty(driver.Actions);
    }

    [Fact]
    public async Task Try_CatchesErrorAndContinues()
    {
        var (engine, _, _, _) = Create();
        var t = new TryNode { ErrorVariable = "Err" };
        t.Body.Add(new ActionNode { Action = RprAction.Click, Target = "Lipsa", TimeoutMs = 10 });
        t.Catch.Add(new SetVariableNode { Name = "Prins", Value = "da" });

        var result = await engine.RunAsync(NewRoutine(t, new SetVariableNode { Name = "Dupa", Value = "ok" }));

        Assert.True(result.Success, result.Message);
        Assert.Equal("da", result.FinalVariables["Prins"]);
        Assert.Equal("ok", result.FinalVariables["Dupa"]);
        Assert.Contains("Lipsa", result.FinalVariables["Err"]);
    }

    [Fact]
    public async Task ErrorPolicy_Continue_And_Stop()
    {
        var (engine, _, _, _) = Create();
        var cont = await engine.RunAsync(NewRoutine(
            new ActionNode { Action = RprAction.Click, Target = "Lipsa", TimeoutMs = 10, OnError = ErrorPolicy.Continue },
            new SetVariableNode { Name = "Ajuns", Value = "da" }));
        Assert.True(cont.Success);
        Assert.Equal(1, cont.Errors);
        Assert.Equal("da", cont.FinalVariables["Ajuns"]);

        var (engine2, _, _, _) = Create();
        var stop = await engine2.RunAsync(NewRoutine(
            new ActionNode { Action = RprAction.Click, Target = "Lipsa", TimeoutMs = 10 },
            new SetVariableNode { Name = "Ajuns", Value = "da" }));
        Assert.False(stop.Success);
        Assert.False(stop.FinalVariables.ContainsKey("Ajuns"));
    }

    [Fact]
    public async Task AutoRetry_RecoversFromTransientFailure()
    {
        var (engine, driver, _, _) = Create();
        driver.FailuresBeforeSuccess = 1;
        var r = NewRoutine(new ActionNode { Action = RprAction.Click, Target = "Buton" });
        r.Settings.AutoRetries = 2;
        var result = await engine.RunAsync(r);
        Assert.True(result.Success, result.Message);
        Assert.Equal(0, result.Errors);
    }

    [Fact]
    public async Task Question_StopButtonStopsRoutine()
    {
        var (engine, _, host, _) = Create();
        host.Answers.Enqueue("Opreste");
        var result = await engine.RunAsync(NewRoutine(
            new QuestionNode { Text = "?", Buttons = "Continua,Opreste" },
            new SetVariableNode { Name = "Ajuns", Value = "da" }));
        Assert.True(result.Success);              // oprire voita, nu eroare
        Assert.False(result.FinalVariables.ContainsKey("Ajuns"));
    }

    [Fact]
    public async Task Condition_ElementExistsAndText()
    {
        var (engine, _, _, _) = Create();
        var i = new IfNode
        {
            Condition = new Condition
            {
                Kind = ConditionKind.AllOf,
                Children =
                {
                    new Condition { Kind = ConditionKind.ElementExists, Target = "Buton" },
                    new Condition { Kind = ConditionKind.ElementText, Target = "Buton", Operator = CompareOperator.Equals, Right = "ok" },
                    new Condition { Kind = ConditionKind.ElementExists, Target = "Lipsa", Negate = true },
                },
            },
        };
        i.Then.Add(new SetVariableNode { Name = "Ramura", Value = "Atunci" });
        i.Else.Add(new SetVariableNode { Name = "Ramura", Value = "Altfel" });
        var result = await engine.RunAsync(NewRoutine(i));
        Assert.Equal("Atunci", result.FinalVariables["Ramura"]);
    }

    // ── Excel ───────────────────────────────────────────────
    [Fact]
    public async Task ForEachRow_WritesResultsStatusAndSkipsFailedRow()
    {
        var file = Path.Combine(Path.GetTempPath(), $"apdc_test_{Guid.NewGuid():N}.xlsx");
        using (var wb = new XLWorkbook())
        {
            var ws = wb.AddWorksheet("Date");
            ws.Cell(1, 1).Value = "Cod";
            ws.Cell(2, 1).Value = "A1";
            ws.Cell(3, 1).Value = "RAU";
            ws.Cell(4, 1).Value = "C3";
            wb.SaveAs(file);
        }

        try
        {
            var (engine, _, _, _) = Create();
            var each = new ForEachRowNode { FilePath = file, KeyColumn = "Cod", StatusColumn = "Status" };
            var bad = new IfNode { Condition = new Condition { Kind = ConditionKind.Compare, Left = "{Rand.Cod}", Operator = CompareOperator.Equals, Right = "RAU" } };
            bad.Then.Add(new ActionNode { Action = RprAction.Click, Target = "Lipsa", TimeoutMs = 10, OnError = ErrorPolicy.SkipRow });
            each.Body.Add(bad);
            each.Body.Add(new WriteExcelNode { Column = "Rezultat", Value = "procesat {Rand.Cod} (rand {Rand.#})" });

            var result = await engine.RunAsync(NewRoutine(each));

            Assert.True(result.Success, result.Message);
            Assert.Equal(2, result.RowsOk);
            Assert.Equal(1, result.RowsFailed);

            using var check = ExcelTable.Open(file, null, 1);
            Assert.Equal("procesat A1 (rand 2)", check.GetCell(2, "Rezultat"));
            Assert.Equal("OK", check.GetCell(2, "Status"));
            Assert.StartsWith("EROARE", check.GetCell(3, "Status"));
            Assert.Equal("", check.GetCell(3, "Rezultat"));
            Assert.Equal("procesat C3 (rand 4)", check.GetCell(4, "Rezultat"));
        }
        finally
        {
            File.Delete(file);
        }
    }

    // ── Persistenta ─────────────────────────────────────────
    [Fact]
    public void Routine_JsonRoundTrip_KeepsTreeAndTypes()
    {
        var i = new IfNode { Condition = new Condition { Kind = ConditionKind.ElementVisible, Target = "Buton" } };
        i.Then.Add(new ActionNode { Action = RprAction.Click, Target = "Buton" });
        i.Else.Add(new LoopNode { Count = "2" });
        var r = NewRoutine(i, new ForEachRowNode { FilePath = "x.xlsx" });
        r.Variables["A"] = "1";

        var json = JsonSerializer.Serialize(r, RprJson.Options);
        var back = JsonSerializer.Deserialize<Routine>(json, RprJson.Options)!;

        Assert.Contains("\"kind\": \"if\"", json);
        var bi = Assert.IsType<IfNode>(back.Steps[0]);
        Assert.Equal(ConditionKind.ElementVisible, bi.Condition.Kind);
        Assert.IsType<ActionNode>(bi.Then[0]);
        Assert.IsType<LoopNode>(bi.Else[0]);
        Assert.IsType<ForEachRowNode>(back.Steps[1]);
        Assert.Equal("1", back.Variables["A"]);
    }

    [Fact]
    public void LegacyConverter_BrowserStepsBecomeObjects()
    {
        var repo = new ObjectRepository();
        var r = LegacyConverter.Convert("Vechi", new[]
        {
            new StepModel { StepType = "browser_click", KeyCombo = "#submit", Description = "Buton Submit" },
            new StepModel { StepType = "CLICK", X = 100, Y = 200, DelayBefore = 1.5 },
            new StepModel { StepType = "QUESTION", QuestionText = "Continui?" },
        }, repo);

        Assert.Single(repo.Objects);
        var a = Assert.IsType<ActionNode>(r.Steps[0]);
        Assert.Equal(RprAction.Click, a.Action);
        Assert.Equal(repo.Objects[0].Name, a.Target);
        var legacy = Assert.IsType<LegacyStepNode>(r.Steps[1]);
        Assert.Equal(1500, legacy.DelayBeforeMs);
        Assert.Equal(0, legacy.Step.DelayBefore);   // intarzierea nu se aplica de doua ori
        Assert.IsType<QuestionNode>(r.Steps[2]);
    }

    [Fact]
    public void Repository_UniqueNamesAndSanitize()
    {
        var repo = new ObjectRepository();
        var a = repo.Add(new UiObject { Name = "Buton OK" });
        var b = repo.Add(new UiObject { Name = "Buton OK" });
        Assert.Equal("Buton_OK", a.Name);
        Assert.Equal("Buton_OK_2", b.Name);
        Assert.False(repo.Rename(b, "Buton_OK"));
        Assert.True(repo.Rename(b, "Buton Anuleaza"));
        Assert.Equal("Buton_Anuleaza", b.Name);
    }
}
