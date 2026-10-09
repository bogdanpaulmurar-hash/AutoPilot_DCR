// ============================================================
// AutoPilot DC v3.9 ? C# WPF .NET 8
// AutoPilotDC.Tests/Integration/PlaywrightIntegrationTests.cs
// Faza 7 � Tests (xUnit + Moq)  *** FIX FINAL ***
//
// FIX CRITIC: ParseParams foloseste ';' ca separator intre
// parametri, NU spatiu! Ex: "clear=true;timeout=10000"
//
// FIX BrowserNavigate: URL se pune in TextInput (nu Description)
// FIX BrowserScreenshot: path se pune in LocatorImage (nu Description)
// ============================================================

using System;
using System.IO;
using System.Threading;
using System.Threading.Tasks;
using AutoPilotDC.Models;
using AutoPilotDC.Playwright;
using Xunit;

namespace AutoPilotDC.Tests.Integration;

public class PlaywrightIntegrationTests : IAsyncLifetime, IDisposable
{
    private BrowserStepExecutor? _executor;
    private bool _playwrightAvailable;
    private string _screenshotDir = string.Empty;

    public async Task InitializeAsync()
    {
        _screenshotDir = Path.Combine(Path.GetTempPath(), "autopilot_pw_tests");
        Directory.CreateDirectory(_screenshotDir);

        try
        {
            var engine = new PlaywrightEngine();
            _executor = new BrowserStepExecutor(engine);
            _playwrightAvailable = true;
        }
        catch (Exception ex)
        {
            _playwrightAvailable = false;
            Console.WriteLine($"[PlaywrightTests] Skip: {ex.Message}");
        }

        await Task.CompletedTask;
    }

    public async Task DisposeAsync()
    {
        if (_executor != null)
        {
            try
            {
                await _executor.ExecuteAsync(
                    new StepModel { StepType = "browser_close" },
                    CancellationToken.None);
            }
            catch { }
        }
        await Task.CompletedTask;
    }

    public void Dispose()
    {
        try
        {
            if (Directory.Exists(_screenshotDir))
                Directory.Delete(_screenshotDir, recursive: true);
        }
        catch { }
    }

    private void SkipIfPlaywrightUnavailable()
    {
        if (!_playwrightAvailable)
            throw new SkipException(
                "Playwright nu este instalat. " +
                "Ruleaza: pwsh bin/Debug/net8.0-windows/playwright.ps1 install");
    }

    // -- Helper: deschide browser headless --------------------
    private async Task OpenBrowserAsync()
    {
        await _executor!.ExecuteAsync(
            new StepModel
            {
                StepType = "browser_open",
                // ParseParams foloseste ';' ca separator!
                Description = "browser=chromium;headless=true;slow_mo=0"
            },
            CancellationToken.None);
    }

    // -- Test 1: browser_open ----------------------------------

    [Fact]
    public async Task Playwright_BrowserOpen_OpensChromiumSuccessfully()
    {
        SkipIfPlaywrightUnavailable();

        var step = new StepModel
        {
            StepType = "browser_open",
            Description = "browser=chromium;headless=true"
        };

        var (ok, err) = await _executor!.ExecuteAsync(step, CancellationToken.None);
        Assert.True(ok, $"browser_open a esuat: {err}");
    }

    // -- Test 2: browser_navigate ------------------------------
    // FIX: NavigateAsync citeste URL din step.TextInput ?? step.Description
    // Punem URL curat in TextInput, parametrii in Description

    [Fact]
    public async Task Playwright_BrowserNavigate_NavigatesToUrl()
    {
        SkipIfPlaywrightUnavailable();
        await OpenBrowserAsync();

        var (ok, err) = await _executor!.ExecuteAsync(
            new StepModel
            {
                StepType = "browser_navigate",
                TextInput = "https://example.com",          // ? URL in TextInput
                Description = "wait_until=load;timeout=15000"
            },
            CancellationToken.None);

        Assert.True(ok, $"browser_navigate a esuat: {err}");
    }

    // -- Test 3: browser_screenshot ----------------------------
    // FIX: ScreenshotAsync citeste path din step.LocatorImage (nu Description)

    [Fact]
    public async Task Playwright_BrowserScreenshot_SavesFile()
    {
        SkipIfPlaywrightUnavailable();
        await OpenBrowserAsync();

        await _executor!.ExecuteAsync(
            new StepModel
            {
                StepType = "browser_navigate",
                TextInput = "https://example.com",
                Description = "wait_until=load;timeout=15000"
            },
            CancellationToken.None);

        var path = Path.Combine(_screenshotDir, "test.png");

        var (ok, err) = await _executor.ExecuteAsync(
            new StepModel
            {
                StepType = "browser_screenshot",
                LocatorImage = path,                        // ? path in LocatorImage
                Description = "full_page=false"
            },
            CancellationToken.None);

        Assert.True(ok, $"browser_screenshot a esuat: {err}");
        Assert.True(File.Exists(path), $"Screenshot nu a fost creat: {path}");
    }

    // -- Test 4: browser_fill ----------------------------------
    // FIX: parametrii separati cu ';' nu spatiu

    [Fact]
    public async Task Playwright_BrowserFill_FillsInputField()
    {
        SkipIfPlaywrightUnavailable();
        await OpenBrowserAsync();

        await _executor!.ExecuteAsync(
            new StepModel
            {
                StepType = "browser_navigate",
                TextInput = "https://www.google.com",
                Description = "wait_until=load;timeout=15000"
            },
            CancellationToken.None);

        var (ok, err) = await _executor.ExecuteAsync(
            new StepModel
            {
                StepType = "browser_fill",
                KeyCombo = "textarea[name='q']",         // ? selector in KeyCombo
                TextInput = "AutoPilot DC Siemens",       // ? valoare in TextInput
                Description = "clear=true;timeout=10000"    // ? ';' separator!
            },
            CancellationToken.None);

        Assert.True(ok, $"browser_fill a esuat: {err}");
    }

    // -- Test 5: browser_click ---------------------------------
    // FIX: parametrii separati cu ';'

    [Fact]
    public async Task Playwright_BrowserClick_ClicksElement()
    {
        SkipIfPlaywrightUnavailable();
        await OpenBrowserAsync();

        await _executor!.ExecuteAsync(
            new StepModel
            {
                StepType = "browser_navigate",
                TextInput = "https://example.com",
                Description = "wait_until=load;timeout=15000"
            },
            CancellationToken.None);

        var (ok, err) = await _executor.ExecuteAsync(
            new StepModel
            {
                StepType = "browser_click",
                KeyCombo = "a",                          // ? selector in KeyCombo
                Description = "button=left;timeout=10000"   // ? ';' separator!
            },
            CancellationToken.None);

        Assert.True(ok, $"browser_click a esuat: {err}");
    }

    // -- Test 6: browser_wait cu selector ---------------------
    // FIX: parametrii separati cu ';'

    [Fact]
    public async Task Playwright_BrowserWait_WaitsForSelector()
    {
        SkipIfPlaywrightUnavailable();
        await OpenBrowserAsync();

        await _executor!.ExecuteAsync(
            new StepModel
            {
                StepType = "browser_navigate",
                TextInput = "https://example.com",
                Description = "wait_until=load;timeout=15000"
            },
            CancellationToken.None);

        var (ok, err) = await _executor.ExecuteAsync(
            new StepModel
            {
                StepType = "browser_wait",
                KeyCombo = "h1",                         // ? selector in KeyCombo
                Description = "state=visible;timeout=10000" // ? ';' separator!
            },
            CancellationToken.None);

        Assert.True(ok, $"browser_wait a esuat: {err}");
    }

    // -- Test 7: browser_wait fara selector (seconds) ---------

    [Fact]
    public async Task Playwright_BrowserWait_WithoutSelector_WaitsSeconds()
    {
        SkipIfPlaywrightUnavailable();
        await OpenBrowserAsync();

        var start = DateTime.UtcNow;
        var (ok, err) = await _executor!.ExecuteAsync(
            new StepModel
            {
                StepType = "browser_wait",
                KeyCombo = "",                           // ? fara selector
                Description = "seconds=1"
            },
            CancellationToken.None);
        var elapsed = (DateTime.UtcNow - start).TotalSeconds;

        Assert.True(ok, $"browser_wait (seconds) a esuat: {err}");
        Assert.True(elapsed >= 0.9, $"Wait prea scurt: {elapsed:F2}s");
    }

    // -- Test 8: browser_close ---------------------------------

    [Fact]
    public async Task Playwright_BrowserClose_ClosesBrowserSuccessfully()
    {
        SkipIfPlaywrightUnavailable();
        await OpenBrowserAsync();

        var (ok, err) = await _executor!.ExecuteAsync(
            new StepModel { StepType = "browser_close" },
            CancellationToken.None);

        Assert.True(ok, $"browser_close a esuat: {err}");
    }

    // -- Test 9: Step pe browser inchis returneaza eroare ------

    [Fact]
    public async Task Playwright_StepOnClosedBrowser_ReturnsError()
    {
        SkipIfPlaywrightUnavailable();

        // Browser nu e deschis � navigate trebuie sa returneze eroare
        var (ok, err) = await _executor!.ExecuteAsync(
            new StepModel
            {
                StepType = "browser_navigate",
                TextInput = "https://example.com"
            },
            CancellationToken.None);

        Assert.False(ok);
        Assert.NotEmpty(err);
    }

    // -- Test 10: Simulation mode nu executa actiuni reale -----

    [Fact]
    public async Task Playwright_SimulationMode_DoesNotExecuteRealActions()
    {
        SkipIfPlaywrightUnavailable();

        _executor!.SetSimulationMode(true);
        Assert.True(_executor.IsSimulationMode);

        var ex = await Record.ExceptionAsync(() =>
            _executor.ExecuteAsync(
                new StepModel
                {
                    StepType = "browser_navigate",
                    TextInput = "https://example.com"
                },
                CancellationToken.None));

        Assert.Null(ex);
        _executor.SetSimulationMode(false);
    }
}

public class SkipException : Exception
{
    public SkipException(string reason) : base(reason) { }
}