// ============================================================
// AutoPilot DC v3.9 -> C# WPF .NET 8
// PlaywrightEngine.cs � Motor browser automation (Faza 6)
// Echivalent Python: browser/playwright_engine.py
// Autor: Bogdan Murar (Z003FU5C) � Siemens AG
// ============================================================

using System;
using System.IO;
using System.Threading;
using System.Threading.Tasks;
using AutoPilotDC.Core.Interfaces;
using AutoPilotDC.Models;
using Microsoft.Playwright;

namespace AutoPilotDC.Playwright;

/// <summary>
/// Motor de automatizare browser via Microsoft Playwright.
/// Implementeaza IAutomationEngine � acelasi contract ca DesktopEngine.
/// Suporta: browser_open, browser_navigate, browser_click, browser_fill,
///          browser_wait, browser_screenshot, browser_close.
/// Echivalent Python: PlaywrightEngine (browser/playwright_engine.py)
/// </summary>
[System.Runtime.Versioning.SupportedOSPlatform("windows7.0")]
public sealed class PlaywrightEngine : IAutomationEngine, IAsyncDisposable
{
    // -- Stare interna -----------------------------------------
    private IPlaywright?  _playwright;
    private IBrowser?     _browser;
    private IBrowserContext? _context;
    private IPage?        _page;
    private readonly object _lock = new();

    // -- Directoare --------------------------------------------
    private static readonly string LocatorsDir = Path.Combine(
        AppDomain.CurrentDomain.BaseDirectory, "locatori");

    // -- IAutomationEngine -------------------------------------
    public string EngineType => "browser";

    /// <summary>True daca Playwright este instalat si disponibil.</summary>
    public bool IsAvailable
    {
        get
        {
            try
            {
                // Verifica daca assembly-ul Playwright este incarcat
                var t = typeof(Microsoft.Playwright.Playwright);
                return t != null;
            }
            catch { return false; }
        }
    }

    /// <summary>Returneaza true pentru orice step de tip browser_*</summary>
    public bool SupportsStep(StepModel step) =>
        step.StepType?.StartsWith("browser_", StringComparison.OrdinalIgnoreCase) == true;

    /// <summary>True daca browserul este deschis si pagina activa.</summary>
    public bool IsOpen => _page != null && !_page.IsClosed;

    /// <summary>Pagina activa (poate fi null daca browserul nu e deschis).</summary>
    public IPage? Page => _page;

    // =========================================================
    // IAutomationEngine.ExecuteStepAsync � dispatcher principal
    // =========================================================
    public async Task<(bool Success, string Error)> ExecuteStepAsync(
        StepModel step,
        CancellationToken cancellationToken = default)
    {
        if (step == null) return (false, "Step null.");

        try
        {
            return step.StepType?.ToLowerInvariant() switch
            {
                "browser_open"       => await OpenBrowserAsync(step, cancellationToken),
                "browser_navigate"   => await NavigateAsync(step, cancellationToken),
                "browser_click"      => await ClickAsync(step, cancellationToken),
                "browser_fill"       => await FillAsync(step, cancellationToken),
                "browser_wait"       => await WaitForAsync(step, cancellationToken),
                "browser_screenshot" => await ScreenshotAsync(step, cancellationToken),
                "browser_close"      => await CloseBrowserAsync(),
                _ => (false, $"Unsupported browser step type: {step.StepType}")
            };
        }
        catch (OperationCanceledException)
        {
            return (false, "Operatiune anulata.");
        }
        catch (Exception ex)
        {
            // La eroare browser step � screenshot automat in locatori/
            await TakeErrorScreenshotAsync(step);
            return (false, ex.Message);
        }
    }

    // =========================================================
    // browser_open � Deschide browser (chromium/firefox/webkit)
    // Params din StepModel.Description (JSON inline) sau defaults:
    //   browser   : "chromium" | "firefox" | "webkit"  (default: chromium)
    //   headless  : bool  (default: false)
    //   slow_mo   : int ms  (default: 0)
    //   width     : int  (default: 1280)
    //   height    : int  (default: 720)
    // Echivalent Python: browser_open step
    // =========================================================
    private async Task<(bool Success, string Error)> OpenBrowserAsync(StepModel step, CancellationToken ct)
    {
        // Inchide browser anterior daca exista
        if (_browser != null)
            await CloseBrowserAsync();

        _playwright = await Microsoft.Playwright.Playwright.CreateAsync();

        // Parsare parametri din Description (format: "browser=chromium;headless=false;slow_mo=50")
        var p = ParseParams(step.Description ?? "");

        string browserType = p.GetValueOrDefault("browser", "chromium").ToLowerInvariant();
        bool headless      = bool.Parse(p.GetValueOrDefault("headless", "false"));
        int slowMo         = int.Parse(p.GetValueOrDefault("slow_mo", "0"));
        int width          = int.Parse(p.GetValueOrDefault("width",  "1280"));
        int height         = int.Parse(p.GetValueOrDefault("height", "720"));

        var launchOptions = new BrowserTypeLaunchOptions
        {
            Headless = headless,
            SlowMo   = slowMo
        };

        IBrowserType bt = browserType switch
        {
            "firefox" => _playwright.Firefox,
            "webkit"  => _playwright.Webkit,
            _         => _playwright.Chromium
        };

        _browser = await bt.LaunchAsync(launchOptions);
        _context = await _browser.NewContextAsync(new BrowserNewContextOptions
        {
            ViewportSize = new ViewportSize { Width = width, Height = height }
        });
        _page = await _context.NewPageAsync();

        // Handler erori pagina
        _page.PageError += (_, err) =>
            System.Diagnostics.Debug.WriteLine($"[PlaywrightEngine] Page error: {err}");

        return (true, string.Empty);
    }

    // =========================================================
    // browser_navigate � Navigare la URL
    // Params: url (required), wait_until (default: load), timeout (ms, default: 30000)
    // Echivalent Python: browser_navigate step
    // =========================================================
    private async Task<(bool Success, string Error)> NavigateAsync(
        StepModel step, CancellationToken ct)
    {
        RequireOpen();

        string url = step.TextInput ?? step.Description ?? "";
        if (string.IsNullOrWhiteSpace(url))
            return (false, "browser_navigate: URL lipsa (TextInput sau Description).");

        var p = ParseParams(step.Description ?? "");
        string waitUntil = p.GetValueOrDefault("wait_until", "load");
        int timeout      = int.Parse(p.GetValueOrDefault("timeout", "30000"));

        WaitUntilState waitState = waitUntil.ToLowerInvariant() switch
        {
            "domcontentloaded" => WaitUntilState.DOMContentLoaded,
            "networkidle"      => WaitUntilState.NetworkIdle,
            "commit"           => WaitUntilState.Commit,
            _                  => WaitUntilState.Load
        };

        // Daca URL-ul e in TextInput, foloseste-l direct
        string targetUrl = step.TextInput?.StartsWith("http") == true
            ? step.TextInput
            : url;

        await _page!.GotoAsync(targetUrl, new PageGotoOptions
        {
            WaitUntil = waitState,
            Timeout   = timeout
        });

        return (true, string.Empty);
    }

    // =========================================================
    // browser_click � Click pe selector CSS/XPath
    // Params: selector (KeyCombo), button (left/right/middle), timeout, force
    // Echivalent Python: browser_click step
    // =========================================================
    private async Task<(bool Success, string Error)> ClickAsync(
        StepModel step, CancellationToken ct)
    {
        RequireOpen();

        string selector = step.KeyCombo ?? step.Description ?? "";
        if (string.IsNullOrWhiteSpace(selector))
            return (false, "browser_click: Selector lipsa (KeyCombo).");

        var p = ParseParams(step.Description ?? "");
        int timeout   = int.Parse(p.GetValueOrDefault("timeout", "30000"));
        bool force    = bool.Parse(p.GetValueOrDefault("force", "false"));
        string button = step.Button?.ToLowerInvariant() ?? "left";

        MouseButton mouseButton = button switch
        {
            "right"  => MouseButton.Right,
            "middle" => MouseButton.Middle,
            _        => MouseButton.Left
        };

        await _page!.ClickAsync(selector, new PageClickOptions
        {
            Button  = mouseButton,
            Force   = force,
            Timeout = timeout
        });

        return (true, string.Empty);
    }

    // =========================================================
    // browser_fill � Completare camp cu text
    // Params: selector (KeyCombo), value (TextInput), clear (bool), timeout
    // Echivalent Python: browser_fill step
    // =========================================================
    private async Task<(bool Success, string Error)> FillAsync(
        StepModel step, CancellationToken ct)
    {
        RequireOpen();

        string selector = step.KeyCombo ?? "";
        string value    = step.TextInput ?? "";

        if (string.IsNullOrWhiteSpace(selector))
            return (false, "browser_fill: Selector lipsa (KeyCombo).");

        var p = ParseParams(step.Description ?? "");
        int timeout = int.Parse(p.GetValueOrDefault("timeout", "30000"));
        bool clear  = bool.Parse(p.GetValueOrDefault("clear", "true"));

        if (clear)
            await _page!.FillAsync(selector, value, new PageFillOptions { Timeout = timeout });
        else
        {
            await _page!.ClickAsync(selector, new PageClickOptions { Timeout = timeout });
            await _page!.Locator(selector).PressSequentiallyAsync(value);
        }

        return (true, string.Empty);
    }

    // =========================================================
    // browser_wait � Asteapta selector sau timeout simplu
    // Params: selector (KeyCombo, optional), state, timeout, seconds
    // Echivalent Python: browser_wait step
    // =========================================================
    private async Task<(bool Success, string Error)> WaitForAsync(
        StepModel step, CancellationToken ct)
    {
        RequireOpen();

        var p = ParseParams(step.Description ?? "");
        string selector = step.KeyCombo ?? "";
        int timeout     = int.Parse(p.GetValueOrDefault("timeout", "30000"));
        double seconds  = double.Parse(p.GetValueOrDefault("seconds", "0"),
                              System.Globalization.CultureInfo.InvariantCulture);

        if (!string.IsNullOrWhiteSpace(selector))
        {
            // Asteapta selector specific
            string state = p.GetValueOrDefault("state", "visible");
            WaitForSelectorState selectorState = state.ToLowerInvariant() switch
            {
                "hidden"   => WaitForSelectorState.Hidden,
                "attached" => WaitForSelectorState.Attached,
                "detached" => WaitForSelectorState.Detached,
                _          => WaitForSelectorState.Visible
            };

            await _page!.WaitForSelectorAsync(selector, new PageWaitForSelectorOptions
            {
                State   = selectorState,
                Timeout = timeout
            });
        }
        else if (seconds > 0)
        {
            // Asteapta N secunde (fara selector)
            await Task.Delay(TimeSpan.FromSeconds(seconds), ct);
        }
        else
        {
            // Asteapta load complet
            await _page!.WaitForLoadStateAsync(LoadState.Load,
                new PageWaitForLoadStateOptions { Timeout = timeout });
        }

        return (true, string.Empty);
    }

    // =========================================================
    // browser_screenshot � Captura pagina
    // Params: path (LocatorImage), full_page (bool)
    // Echivalent Python: browser_screenshot step
    // =========================================================
    private async Task<(bool Success, string Error)> ScreenshotAsync(
        StepModel step, CancellationToken ct)
    {
        RequireOpen();

        var p = ParseParams(step.Description ?? "");
        bool fullPage = bool.Parse(p.GetValueOrDefault("full_page", "false"));

        // Path: din LocatorImage sau auto-generat in locatori/
        string path = step.LocatorImage ?? "";
        if (string.IsNullOrWhiteSpace(path))
        {
            Directory.CreateDirectory(LocatorsDir);
            path = Path.Combine(LocatorsDir,
                $"browser_screenshot_{DateTime.Now:yyyyMMdd_HHmmss}.png");
        }

        await _page!.ScreenshotAsync(new PageScreenshotOptions
        {
            Path     = path,
            FullPage = fullPage
        });

        return (true, string.Empty);
    }

    // =========================================================
    // browser_close � Inchide browser
    // Echivalent Python: browser_close step
    // =========================================================
    private async Task<(bool Success, string Error)> CloseBrowserAsync()
    {
        try
        {
            if (_page != null && !_page.IsClosed)
                await _page.CloseAsync();
        }
        catch { /* ignora */ }

        try { if (_context != null) await _context.CloseAsync(); } catch { }
        try { if (_browser != null) await _browser.CloseAsync(); } catch { }
        try { _playwright?.Dispose(); } catch { }

        _page       = null;
        _context    = null;
        _browser    = null;
        _playwright = null;

        return (true, string.Empty);
    }

    // =========================================================
    // TakeErrorScreenshotAsync � Screenshot automat la eroare
    // Salveaza in locatori/ cu prefix "error_"
    // Echivalent Python: la eroare browser step -> screenshot
    // =========================================================
    private async Task TakeErrorScreenshotAsync(StepModel step)
    {
        try
        {
            if (_page == null || _page.IsClosed) return;
            Directory.CreateDirectory(LocatorsDir);
            string path = Path.Combine(LocatorsDir,
                $"error_{step.StepType}_{step.StepId}_{DateTime.Now:yyyyMMdd_HHmmss}.png");
            await _page.ScreenshotAsync(new PageScreenshotOptions { Path = path, FullPage = false });
        }
        catch { /* ignora erori la screenshot de eroare */ }
    }

    // =========================================================
    // RequireOpen � Guard: browserul trebuie sa fie deschis
    // =========================================================
    private void RequireOpen()
    {
        if (_page == null || _page.IsClosed)
            throw new InvalidOperationException(
                "Browser nu este deschis. Adauga un pas browser_open inainte.");
    }

    // =========================================================
    // ParseParams � Parsare parametri din Description
    // Format: "key1=val1;key2=val2" sau "url=https://..."
    // =========================================================
    private static System.Collections.Generic.Dictionary<string, string> ParseParams(string desc)
    {
        var result = new System.Collections.Generic.Dictionary<string, string>(
            StringComparer.OrdinalIgnoreCase);

        if (string.IsNullOrWhiteSpace(desc)) return result;

        foreach (var part in desc.Split(';', StringSplitOptions.RemoveEmptyEntries))
        {
            var idx = part.IndexOf('=');
            if (idx > 0)
            {
                var key = part[..idx].Trim();
                var val = part[(idx + 1)..].Trim();
                result[key] = val;
            }
        }
        return result;
    }

    // =========================================================
    // IAsyncDisposable
    // =========================================================
    public async ValueTask DisposeAsync()
    {
        await CloseBrowserAsync();
    }
}
