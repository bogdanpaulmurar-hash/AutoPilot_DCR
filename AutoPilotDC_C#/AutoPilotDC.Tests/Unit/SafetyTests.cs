// ============================================================
// AutoPilot DC v4.1 — Teste: sistemul de preventie, "Nu deranja", context pasi
// ============================================================

using System.Text;
using System.Text.Json;
using AutoPilotDC.Infrastructure.Safety;
using AutoPilotDC.Infrastructure.Services;
using AutoPilotDC.Models;
using AutoPilotDC.Rpr.Engine;
using AutoPilotDC.Rpr.Model;
using Xunit;

namespace AutoPilotDC.Tests.Unit;

/// <summary>Host care raspunde la alerte cu o decizie fixa si le numara.</summary>
internal sealed class AlertHost : IRunHost
{
    public AlertDecision Decision { get; set; } = AlertDecision.Continue;
    public List<RunAlert> Alerts { get; } = new();

    public void Log(RunLogEntry entry) { }
    public void NodeStarted(RprNode node) { }
    public void NodeFinished(RprNode node, bool success) { }
    public Task<string> AskAsync(string title, string text, IReadOnlyList<string> buttons, CancellationToken ct) => Task.FromResult(buttons[0]);
    public Task<ErrorDecision> AskOnErrorAsync(RprNode node, string error, bool insideExcelLoop, CancellationToken ct) => Task.FromResult(ErrorDecision.Stop);
    public Task<AlertDecision> AskAlertAsync(RprNode node, RunAlert alert, bool insideExcelLoop, CancellationToken ct)
    {
        Alerts.Add(alert);
        return Task.FromResult(Decision);
    }
    public Func<StepModel, CancellationToken, Task<(bool Success, string Error)>>? LegacyExecutor => null;
}

/// <summary>Garda falsa: raporteaza aceeasi alerta de N ori.</summary>
internal sealed class FakeGuard : IRunGuard
{
    public int AlertsLeft { get; set; }
    public int Acknowledged { get; private set; }
    public void BeginRun() { }
    public void Acknowledge() => Acknowledged++;
    public RunAlert? CheckBeforeAction(ActionNode node) =>
        AlertsLeft-- > 0 ? new RunAlert("A aparut o fereastra de eroare", "Eroare: test", "window:Eroare") : null;
}

public class SafetyTests
{
    private static (RprEngine Engine, FakeDriver Driver, AlertHost Host) Create()
    {
        var repo = new ObjectRepository();
        repo.Add(new UiObject { Name = "Camp", Locators = { new Locator(LocatorKind.Id, "camp") } });
        var driver = new FakeDriver();
        driver.Screen["Camp"] = "Comanda salvata 4711";
        var host = new AlertHost();
        return (new RprEngine(repo, driver, host, Path.Combine(Path.GetTempPath(), "apdc-teste")), driver, host);
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

    private static ActionNode Read(string expected) => new()
    {
        Action = RprAction.ReadText, Target = "Camp", OutputVariable = "Mesaj", ExpectedValue = expected,
    };

    // ── Valoarea asteptata ──────────────────────────────────
    [Theory]
    [InlineData("Comanda salvata 4711", "comanda salvata 4711", true)]
    [InlineData("Comanda salvata 4711", "Comanda salvata*", true)]
    [InlineData("Comanda salvata 4711", "*4711", true)]
    [InlineData("S: Document 12 salvat", "S:*", true)]
    [InlineData("E: Material inexistent", "S:*", false)]
    [InlineData("abc", "abd", false)]
    [InlineData("a.b", "a*b", true)]
    [InlineData("axb", "a.b", false)] // punctul nu e wildcard
    public void ExpectedValue_Matching(string actual, string expected, bool match) =>
        Assert.Equal(match, RprEngine.MatchesExpected(actual, expected));

    [Fact]
    public async Task ExpectedValue_Matches_NoQuestion()
    {
        var (engine, _, host) = Create();
        var result = await engine.RunAsync(NewRoutine(Read("Comanda salvata*")));
        Assert.True(result.Success, result.Message);
        Assert.Empty(host.Alerts);
    }

    [Fact]
    public async Task ExpectedValue_Differs_AsksAndStops()
    {
        var (engine, _, host) = Create();
        host.Decision = AlertDecision.Stop;
        var result = await engine.RunAsync(NewRoutine(Read("Eroare*"), new LogNode { Message = "nu trebuie sa ajung aici" }));
        Assert.False(result.Success);
        Assert.Single(host.Alerts);
        Assert.Contains("difera", host.Alerts[0].Title);
        Assert.Equal("Comanda salvata 4711", result.FinalVariables["Mesaj"]); // citirea s-a facut
        Assert.Equal(0, result.StepsExecuted);                                // dar rutina s-a oprit acolo
    }

    [Fact]
    public async Task ExpectedValue_Differs_ContinueGoesOn()
    {
        var (engine, _, host) = Create();
        host.Decision = AlertDecision.Continue;
        var result = await engine.RunAsync(NewRoutine(Read("Altceva"), new SetVariableNode { Name = "Dupa", Value = "da" }));
        Assert.True(result.Success, result.Message);
        Assert.Equal("da", result.FinalVariables["Dupa"]);
        Assert.Single(host.Alerts);
    }

    [Fact]
    public async Task ExpectedValue_InsideTry_GoesToCatchWithoutQuestion()
    {
        var (engine, _, host) = Create();
        var t = new TryNode { ErrorVariable = "Eroare" };
        t.Body.Add(Read("Altceva"));
        t.Catch.Add(new SetVariableNode { Name = "Prins", Value = "da" });
        var result = await engine.RunAsync(NewRoutine(t));
        Assert.True(result.Success, result.Message);
        Assert.Equal("da", result.FinalVariables["Prins"]);
        Assert.Empty(host.Alerts);
    }

    // ── Garda Windows (falsa) ───────────────────────────────
    [Fact]
    public async Task Guard_Alert_IgnoreSimilar_AsksOnlyOnce()
    {
        var (engine, driver, host) = Create();
        engine.Guard = new FakeGuard { AlertsLeft = 5 };
        host.Decision = AlertDecision.IgnoreSimilar;
        var click = new ActionNode { Action = RprAction.Click, Target = "Camp" };
        var result = await engine.RunAsync(NewRoutine(click, new ActionNode { Action = RprAction.Click, Target = "Camp" }));
        Assert.True(result.Success, result.Message);
        Assert.Single(host.Alerts);              // a doua oara: ignorat
        Assert.Equal(2, driver.Actions.Count);   // ambele click-uri au rulat
    }

    [Fact]
    public async Task Guard_DisabledInRoutine_NoChecks()
    {
        var (engine, _, host) = Create();
        engine.Guard = new FakeGuard { AlertsLeft = 5 };
        var r = NewRoutine(new ActionNode { Action = RprAction.Click, Target = "Camp" });
        r.Settings.GuardEnabled = false;
        var result = await engine.RunAsync(r);
        Assert.True(result.Success);
        Assert.Empty(host.Alerts);
    }

    [Fact]
    public async Task Guard_StopDecision_StopsBeforeAction()
    {
        var (engine, driver, host) = Create();
        engine.Guard = new FakeGuard { AlertsLeft = 1 };
        host.Decision = AlertDecision.Stop;
        var result = await engine.RunAsync(NewRoutine(new ActionNode { Action = RprAction.Click, Target = "Camp" }));
        Assert.False(result.Success);
        Assert.Empty(driver.Actions); // click-ul NU s-a executat
    }

    // ── Amprente / titluri ──────────────────────────────────
    [Fact]
    public void Signatures_CompareIdenticalAndOpposite()
    {
        var black = Convert.ToBase64String(new byte[400]);
        var white = Convert.ToBase64String(Enumerable.Repeat((byte)255, 400).ToArray());
        Assert.Equal(0, ScreenProbe.CompareSignatures(black, black));
        Assert.Equal(100, ScreenProbe.CompareSignatures(black, white));
        Assert.Null(ScreenProbe.CompareSignatures("", black));
        Assert.Null(ScreenProbe.CompareSignatures("nu-e-base64!", black));
    }

    [Theory]
    [InlineData("Book1 - Excel", "Book2 - Excel", true)]
    [InlineData("Inbox (5) - Outlook", "Inbox (12) - Outlook", true)]
    [InlineData("SAP Easy Access", "Display Sales Order: Initial Screen", false)]
    [InlineData("", "orice", true)]
    public void Titles_Similarity(string a, string b, bool similar) =>
        Assert.Equal(similar, SafetyGuard.SimilarTitles(a, b));

    [Fact]
    public void Errors_DetectedInTitlesAndTexts()
    {
        Assert.True(ScreenProbe.LooksLikeError("Microsoft Excel - Eroare"));
        Assert.True(ScreenProbe.LooksLikeError("Program (Not Responding)"));
        Assert.False(ScreenProbe.LooksLikeError("Save As"));
    }

    // ── "Nu deranja": blob-ul real din registry (Windows 10 22H2) ──
    private static byte[] RealBlob() => Convert.FromHexString(
        "434201000a0201002a06c8d38eb8062a2b0e5e43420100c20a01d21428" +
        Convert.ToHexString(Encoding.Unicode.GetBytes("Microsoft.QuietHoursProfile.Unrestricted")) +
        "ca280000000000");

    [Fact]
    public void Dnd_Blob_ReadAndSwitchProfile()
    {
        var blob = RealBlob();
        Assert.Equal(116, blob.Length);
        Assert.Equal("Microsoft.QuietHoursProfile.Unrestricted", DoNotDisturb.ReadProfile(blob));

        var on = DoNotDisturb.WriteProfile(blob, "Microsoft.QuietHoursProfile.PriorityOnly")!;
        Assert.Equal(blob.Length, on.Length);
        Assert.Equal("Microsoft.QuietHoursProfile.PriorityOnly", DoNotDisturb.ReadProfile(on));
        Assert.NotEqual(blob[10..15], on[10..15]);   // marca de timp actualizata
        Assert.Equal(blob[..8], on[..8]);            // antetul neatins

        var off = DoNotDisturb.WriteProfile(on, "Microsoft.QuietHoursProfile.Unrestricted")!;
        Assert.Equal("Microsoft.QuietHoursProfile.Unrestricted", DoNotDisturb.ReadProfile(off));

        // AlarmsOnly are alta lungime: refuzat (altfel Windows il citeste gresit)
        Assert.Null(DoNotDisturb.WriteProfile(blob, "Microsoft.QuietHoursProfile.AlarmsOnly"));
    }

    // ── Compatibilitate JSON cu Python (chei snake_case) ─────
    [Fact]
    public void StepModel_ContextFields_SnakeCaseJson()
    {
        var s = new StepModel { WindowTitle = "Book1 - Excel", WindowProcess = "excel.exe", ScreenSignature = "AAAA", GuardIgnore = true };
        var json = JsonSerializer.Serialize(s);
        Assert.Contains("\"window_title\":\"Book1 - Excel\"", json);
        Assert.Contains("\"window_process\":\"excel.exe\"", json);
        Assert.Contains("\"screen_signature\":\"AAAA\"", json);
        Assert.Contains("\"guard_ignore\":true", json);

        var back = JsonSerializer.Deserialize<StepModel>(json)!;
        Assert.Equal("excel.exe", back.WindowProcess);
        Assert.True(back.Clone().GuardIgnore);
    }
}
