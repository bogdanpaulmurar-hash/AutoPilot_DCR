// ============================================================
// AutoPilot DC v4 — Drivers.Web
// PlaywrightUiDriver.cs — Web prin Playwright
//
//  1. Browser cu profil persistent (login-ul SSO ramane).
//  2. Scriptul Spy injectat in fiecare pagina si iframe.
//  3. Gasire element cu fallback pe toti locatorii (self-healing):
//     primul locator care gaseste exact UN element castiga.
//  4. Spy (marcare obiect) si Recorder (actiuni -> pasi).
//  5. Tab-uri noi deschise de aplicatie devin automat pagina curenta.
// ============================================================

using System.Text.Json;
using Microsoft.Playwright;
using AutoPilotDC.Rpr.Engine;
using AutoPilotDC.Rpr.Model;
using Locator = AutoPilotDC.Rpr.Model.Locator;

namespace AutoPilotDC.Drivers.Web;

public sealed class PlaywrightUiDriver : IUiDriver, ISpyCapable, IRecordCapable
{
    private readonly WebDriverSettings _settings;
    private readonly SemaphoreSlim _startLock = new(1, 1);

    private IPlaywright? _pw;
    private IBrowser? _browser;           // doar pentru profil temporar
    private IBrowserContext? _context;
    private IPage? _page;
    private bool _bindingExposed;

    // Spy / Recorder
    private TaskCompletionSource<SpyEvent?>? _spyTcs;
    private Action<RecordedAction>? _recordCallback;

    // Popup-uri JavaScript (alert/confirm)
    private string _dialogPolicy = "accept";
    public string LastDialogMessage { get; private set; } = "";

    /// <summary>Mesaje pentru Studio (ex: "Tab nou: ...").</summary>
    public event Action<string>? Info;

    public UiTechnology Technology => UiTechnology.Web;
    public string DisplayName => $"Web (Playwright, {_settings.Browser})";
    public bool IsOpen => _page != null && !_page.IsClosed;
    public bool IsRecording => _recordCallback != null;
    public IPage? CurrentPage => _page;

    public PlaywrightUiDriver(WebDriverSettings settings)
    {
        _settings = settings;
    }

    // =========================================================
    // 1. Pornire browser
    // =========================================================
    public async Task OpenAsync(string? url, CancellationToken ct)
    {
        await _startLock.WaitAsync(ct);
        try
        {
            if (_context == null)
            {
                _pw ??= await Microsoft.Playwright.Playwright.CreateAsync();
                _context = await LaunchContextAsync();
                _context.Page += (_, p) => OnNewPage(p, fromPopup: true);
                _context.Close += (_, _) => { _context = null; _page = null; _browser = null; _bindingExposed = false; };

                await _context.AddInitScriptAsync(SpyScript.Source);
                await EnsureBindingAsync();

                foreach (var p in _context.Pages) OnNewPage(p, fromPopup: false);
                _page = _context.Pages.FirstOrDefault() ?? await _context.NewPageAsync();
                await InjectIntoAllFramesAsync(_page);
            }
            else if (_page == null || _page.IsClosed)
            {
                _page = _context.Pages.LastOrDefault(p => !p.IsClosed) ?? await _context.NewPageAsync();
            }
        }
        finally
        {
            _startLock.Release();
        }

        if (!string.IsNullOrWhiteSpace(url))
            await NavigateAsync(url, ct);
    }

    private async Task<IBrowserContext> LaunchContextAsync()
    {
        string? channel = _settings.Browser switch
        {
            BrowserKind.Edge   => "msedge",
            BrowserKind.Chrome => "chrome",
            _                  => null,
        };
        var browserType = _settings.Browser == BrowserKind.Firefox ? _pw!.Firefox : _pw!.Chromium;
        var args = _settings.Browser == BrowserKind.Firefox ? Array.Empty<string>() : new[] { "--start-maximized" };

        try
        {
            if (!string.IsNullOrWhiteSpace(_settings.ProfileFolder))
            {
                Directory.CreateDirectory(_settings.ProfileFolder);
                return await browserType.LaunchPersistentContextAsync(_settings.ProfileFolder,
                    new BrowserTypeLaunchPersistentContextOptions
                    {
                        Channel = channel,
                        Headless = _settings.Headless,
                        Args = args,
                        ViewportSize = ViewportSize.NoViewport,
                        AcceptDownloads = true,
                    });
            }

            _browser = await browserType.LaunchAsync(new BrowserTypeLaunchOptions
            {
                Channel = channel,
                Headless = _settings.Headless,
                Args = args,
            });
            return await _browser.NewContextAsync(new BrowserNewContextOptions
            {
                ViewportSize = ViewportSize.NoViewport,
                AcceptDownloads = true,
            });
        }
        catch (PlaywrightException ex)
        {
            var hint = _settings.Browser switch
            {
                BrowserKind.Edge   => "Verifica daca Microsoft Edge e instalat. Daca profilul e folosit de alta fereastra AutoPilot, inchide-o.",
                BrowserKind.Chrome => "Verifica daca Google Chrome e instalat.",
                _ => "Ruleaza o data: pwsh bin\\Debug\\net8.0-windows\\playwright.ps1 install",
            };
            throw new RprStepException($"Nu pot porni browserul ({_settings.Browser}). {hint} Detalii: {FirstLine(ex.Message)}", ex);
        }
    }

    private void OnNewPage(IPage page, bool fromPopup)
    {
        page.Dialog += async (_, dialog) =>
        {
            LastDialogMessage = dialog.Message;
            Info?.Invoke($"Popup {dialog.Type}: {dialog.Message} → {_dialogPolicy}");
            try
            {
                if (_dialogPolicy == "dismiss") await dialog.DismissAsync();
                else await dialog.AcceptAsync();
            }
            catch { /* dialogul a fost deja inchis */ }
        };
        page.FrameNavigated += async (_, frame) =>
        {
            // daca Spy/Recorder e activ, il repornim dupa navigare
            if (_spyTcs != null || _recordCallback != null)
                await StartSpyInFrameAsync(frame, _recordCallback != null ? "record" : "spy");
        };
        page.Close += (_, _) =>
        {
            if (ReferenceEquals(_page, page))
                _page = _context?.Pages.LastOrDefault(p => !p.IsClosed);
        };

        if (fromPopup)
        {
            _page = page;
            Info?.Invoke("Tab nou deschis de aplicatie — devine pagina curenta.");
        }
    }

    private async Task EnsureBindingAsync()
    {
        if (_bindingExposed || _context == null) return;
        await _context.ExposeBindingAsync<string>("__apdcEmit", (BindingSource source, string json) => OnSpyEvent(source, json));
        _bindingExposed = true;
    }

    private static async Task InjectIntoAllFramesAsync(IPage page)
    {
        foreach (var f in page.Frames)
        {
            try { await f.EvaluateAsync(SpyScript.Source); }
            catch { /* frame inaccesibil sau in navigare */ }
        }
    }

    private async Task<IPage> RequirePageAsync(CancellationToken ct)
    {
        if (IsOpen) return _page!;
        if (_context != null)
        {
            await OpenAsync(null, ct);
            if (IsOpen) return _page!;
        }
        throw new RprStepException("Browserul nu este deschis. Adauga la inceputul rutinei pasul \"Deschide browser\".");
    }

    // =========================================================
    // 2. Gasirea elementului (cu fallback pe toti locatorii)
    // =========================================================
    private ILocator Build(IPage page, UiObject obj, Locator loc)
    {
        if (obj.FramePath.Count == 0)
        {
            return loc.Kind switch
            {
                LocatorKind.Role        => RoleOf(loc.Value, out var name) is { } role
                                            ? page.GetByRole(role, new PageGetByRoleOptions { Name = name, Exact = name != null })
                                            : page.Locator(loc.Value),
                LocatorKind.Label       => page.GetByLabel(loc.Value, new PageGetByLabelOptions { Exact = true }),
                LocatorKind.Placeholder => page.GetByPlaceholder(loc.Value, new PageGetByPlaceholderOptions { Exact = true }),
                LocatorKind.Text        => page.GetByText(loc.Value, new PageGetByTextOptions { Exact = true }),
                _                       => page.Locator(CssOrXPath(loc)),
            };
        }

        IFrameLocator fl = page.FrameLocator(obj.FramePath[0]);
        for (int i = 1; i < obj.FramePath.Count; i++) fl = fl.FrameLocator(obj.FramePath[i]);

        return loc.Kind switch
        {
            LocatorKind.Role        => RoleOf(loc.Value, out var name) is { } role
                                        ? fl.GetByRole(role, new FrameLocatorGetByRoleOptions { Name = name, Exact = name != null })
                                        : fl.Locator(loc.Value),
            LocatorKind.Label       => fl.GetByLabel(loc.Value, new FrameLocatorGetByLabelOptions { Exact = true }),
            LocatorKind.Placeholder => fl.GetByPlaceholder(loc.Value, new FrameLocatorGetByPlaceholderOptions { Exact = true }),
            LocatorKind.Text        => fl.GetByText(loc.Value, new FrameLocatorGetByTextOptions { Exact = true }),
            _                       => fl.Locator(CssOrXPath(loc)),
        };
    }

    private static string CssOrXPath(Locator loc) => loc.Kind switch
    {
        LocatorKind.XPath => loc.Value.StartsWith("xpath=", StringComparison.OrdinalIgnoreCase) ? loc.Value : "xpath=" + loc.Value,
        LocatorKind.Id    => $"[id=\"{CssAttr(loc.Value)}\"]",
        LocatorKind.Name  => $"[name=\"{CssAttr(loc.Value)}\"]",
        _                 => loc.Value, // Css, TestId (selector de atribut)
    };

    private static string CssAttr(string s) => s.Replace("\\", "\\\\").Replace("\"", "\\\"");

    private static AriaRole? RoleOf(string value, out string? name)
    {
        var p = value.IndexOf('|');
        var roleText = p >= 0 ? value[..p] : value;
        name = p >= 0 ? value[(p + 1)..] : null;
        return Enum.TryParse<AriaRole>(roleText, ignoreCase: true, out var role) ? role : null;
    }

    /// <summary>Gaseste elementul; null daca nu apare in timeout.</summary>
    private async Task<(ILocator? Locator, Locator? Used)> ResolveAsync(UiObject obj, int timeoutMs, CancellationToken ct)
    {
        var page = await RequirePageAsync(ct);
        var deadline = DateTime.UtcNow.AddMilliseconds(Math.Max(0, timeoutMs));

        while (true)
        {
            ILocator? multi = null; Locator? multiUsed = null;
            foreach (var loc in obj.ActiveLocators)
            {
                ct.ThrowIfCancellationRequested();
                ILocator l;
                int count;
                try
                {
                    l = Build(page, obj, loc);
                    count = await l.CountAsync();
                }
                catch (PlaywrightException) { continue; } // locator invalid / frame in navigare

                if (count == 1) return (l, loc);
                if (count > 1 && multi == null) { multi = l.First; multiUsed = loc; }
            }

            // Niciun locator unic: acceptam primul element al primului locator care gaseste ceva
            if (multi != null) return (multi, multiUsed);
            if (DateTime.UtcNow >= deadline) return (null, null);
            await Task.Delay(250, ct);
            page = await RequirePageAsync(ct);
        }
    }

    private async Task<ILocator> RequireAsync(UiObject obj, int timeoutMs, CancellationToken ct)
    {
        var (l, _) = await ResolveAsync(obj, timeoutMs, ct);
        return l ?? throw new ElementNotFoundException(obj, timeoutMs, _page != null ? $"pagina curenta: {_page.Url}" : null);
    }

    // =========================================================
    // 3. IUiDriver
    // =========================================================
    public async Task<ElementState> GetStateAsync(UiObject obj, int timeoutMs, CancellationToken ct)
    {
        if (!IsOpen) return ElementState.NotFound;
        var (l, used) = await ResolveAsync(obj, timeoutMs, ct);
        if (l == null) return ElementState.NotFound;
        try
        {
            bool visible = await l.IsVisibleAsync();
            bool enabled = await l.IsEnabledAsync();
            string text = "";
            string value = "";
            try { text = (await l.InnerTextAsync(new LocatorInnerTextOptions { Timeout = 2000 })).Trim(); } catch (PlaywrightException) { }
            try { value = await l.InputValueAsync(new LocatorInputValueOptions { Timeout = 1000 }); } catch (PlaywrightException) { }
            return new ElementState(true, visible, enabled, text, value, used);
        }
        catch (PlaywrightException)
        {
            return ElementState.NotFound; // elementul a disparut intre timp
        }
    }

    public async Task HighlightAsync(UiObject obj, int durationMs, CancellationToken ct)
    {
        try
        {
            var (l, _) = await ResolveAsync(obj, Math.Min(3000, durationMs * 4), ct);
            if (l == null) return;
            await l.EvaluateAsync(
                @"(e, ms) => {
                    if (window.__apdc) return window.__apdc.highlight(e, ms);
                    const o = e.style.outline; e.style.outline = '3px solid #FF9900';
                    setTimeout(() => e.style.outline = o, ms); return true;
                }", durationMs);
        }
        catch (Exception ex) when (ex is PlaywrightException or RprStepException) { /* marcarea e optionala */ }
    }

    public async Task<string?> CaptureErrorScreenshotAsync(string folder, string name, CancellationToken ct)
    {
        if (!IsOpen) return null;
        var path = Path.Combine(folder, name + ".png");
        await _page!.ScreenshotAsync(new PageScreenshotOptions { Path = path });
        return path;
    }

    public async Task<string?> ExecuteAsync(ActionRequest r, CancellationToken ct)
    {
        try
        {
            return await ExecuteCoreAsync(r, ct);
        }
        catch (PlaywrightException ex) // include si depasirile de timp (TimeoutException din Playwright)
        {
            throw new RprStepException(FirstLine(ex.Message), ex);
        }
    }

    private async Task<string?> ExecuteCoreAsync(ActionRequest r, CancellationToken ct)
    {
        int t = r.TimeoutMs;
        switch (r.Action)
        {
            // ── Browser ──────────────────────────────────────
            case RprAction.OpenBrowser:
                await OpenAsync(r.Value, ct);
                return null;

            case RprAction.Navigate:
                await RequirePageAsync(ct);
                await NavigateAsync(r.Value, ct);
                return null;

            case RprAction.Back:
                await (await RequirePageAsync(ct)).GoBackAsync(new PageGoBackOptions { Timeout = _settings.NavigationTimeoutMs });
                return null;

            case RprAction.Refresh:
                await (await RequirePageAsync(ct)).ReloadAsync(new PageReloadOptions { Timeout = _settings.NavigationTimeoutMs });
                return null;

            case RprAction.SwitchTab:
                return await SwitchTabAsync(r.Value, ct);

            case RprAction.HandleDialog:
                _dialogPolicy = r.Value.Trim().ToLowerInvariant().StartsWith("d") ? "dismiss" : "accept";
                return LastDialogMessage;

            case RprAction.ScreenshotPage:
            {
                var page = await RequirePageAsync(ct);
                var path = OutputPath(r, "pagina");
                await page.ScreenshotAsync(new PageScreenshotOptions { Path = path, FullPage = true });
                return path;
            }

            case RprAction.CloseBrowser:
                await CloseAsync();
                return null;

            case RprAction.PressKey when r.Target == null:
                await (await RequirePageAsync(ct)).Keyboard.PressAsync(KeyNames.ToPlaywright(r.Value));
                return null;
        }

        // ── Actiuni pe obiect ───────────────────────────────
        var obj = r.Target ?? throw new RprStepException("Actiunea are nevoie de un obiect.");
        var l = await RequireAsync(obj, t, ct);

        switch (r.Action)
        {
            case RprAction.Click:
                if (r.DirectMode) await l.EvaluateAsync("e => e.click()");
                else await l.ClickAsync(new LocatorClickOptions { Timeout = t });
                return null;

            case RprAction.DoubleClick:
                await l.DblClickAsync(new LocatorDblClickOptions { Timeout = t });
                return null;

            case RprAction.RightClick:
                await l.ClickAsync(new LocatorClickOptions { Timeout = t, Button = MouseButton.Right });
                return null;

            case RprAction.Hover:
                await l.HoverAsync(new LocatorHoverOptions { Timeout = t });
                return null;

            case RprAction.TypeText:
                try
                {
                    await l.FillAsync(r.Value, new LocatorFillOptions { Timeout = t });
                }
                catch (PlaywrightException)
                {
                    // elemente "custom" care nu accepta Fill: click + selectare + tastare
                    await l.ClickAsync(new LocatorClickOptions { Timeout = t });
                    await l.PressAsync("Control+A");
                    await l.PressSequentiallyAsync(r.Value, new LocatorPressSequentiallyOptions { Delay = 15 });
                }
                return null;

            case RprAction.AppendText:
                await l.PressSequentiallyAsync(r.Value, new LocatorPressSequentiallyOptions { Delay = 25, Timeout = t });
                return null;

            case RprAction.Clear:
                await l.ClearAsync(new LocatorClearOptions { Timeout = t });
                return null;

            case RprAction.PressKey:
                await l.PressAsync(KeyNames.ToPlaywright(r.Value), new LocatorPressOptions { Timeout = t });
                return null;

            case RprAction.SelectOption:
                await SelectOptionAsync(l, r.Value, t);
                return null;

            case RprAction.Check:
                await l.CheckAsync(new LocatorCheckOptions { Timeout = t });
                return null;

            case RprAction.Uncheck:
                await l.UncheckAsync(new LocatorUncheckOptions { Timeout = t });
                return null;

            case RprAction.Focus:
                await l.FocusAsync(new LocatorFocusOptions { Timeout = t });
                return null;

            case RprAction.ReadText:
                return (await l.InnerTextAsync(new LocatorInnerTextOptions { Timeout = t })).Trim();

            case RprAction.ReadValue:
                try { return await l.InputValueAsync(new LocatorInputValueOptions { Timeout = t }); }
                catch (PlaywrightException) { return ((await l.TextContentAsync(new LocatorTextContentOptions { Timeout = t })) ?? "").Trim(); }

            case RprAction.ReadAttribute:
                return await l.GetAttributeAsync(r.Value, new LocatorGetAttributeOptions { Timeout = t }) ?? "";

            case RprAction.Highlight:
                await HighlightAsync(obj, 800, ct);
                return null;

            case RprAction.ScreenshotElement:
            {
                var path = OutputPath(r, obj.Name);
                await l.ScreenshotAsync(new LocatorScreenshotOptions { Path = path, Timeout = t });
                return path;
            }

            default:
                throw new RprStepException($"Actiunea {r.Action} nu e disponibila pentru web.");
        }
    }

    private async Task NavigateAsync(string url, CancellationToken ct)
    {
        url = url.Trim();
        if (!url.Contains("://")) url = "https://" + url;
        await _page!.GotoAsync(url, new PageGotoOptions
        {
            Timeout = _settings.NavigationTimeoutMs,
            WaitUntil = WaitUntilState.DOMContentLoaded,
        });
    }

    private async Task<string> SwitchTabAsync(string value, CancellationToken ct)
    {
        await RequirePageAsync(ct);
        var pages = _context!.Pages.Where(p => !p.IsClosed).ToList();
        IPage? target = null;

        if (int.TryParse(value.Trim(), out var idx))
        {
            if (idx < 0) idx = pages.Count + idx; // -1 = ultimul tab
            if (idx >= 0 && idx < pages.Count) target = pages[idx];
        }
        else
        {
            foreach (var p in pages)
            {
                var title = await p.TitleAsync();
                if (title.Contains(value, StringComparison.OrdinalIgnoreCase) || p.Url.Contains(value, StringComparison.OrdinalIgnoreCase))
                {
                    target = p;
                    break;
                }
            }
        }

        _page = target ?? throw new RprStepException($"Nu exista tab-ul \"{value}\". Tab-uri deschise: {pages.Count}.");
        await _page.BringToFrontAsync();
        return await _page.TitleAsync();
    }

    private static async Task SelectOptionAsync(ILocator l, string value, int timeout)
    {
        var tag = await l.EvaluateAsync<string>("e => e.tagName.toLowerCase()");
        if (tag == "select")
        {
            try
            {
                await l.SelectOptionAsync(new SelectOptionValue { Label = value }, new LocatorSelectOptionOptions { Timeout = timeout });
            }
            catch (PlaywrightException)
            {
                await l.SelectOptionAsync(new SelectOptionValue { Value = value }, new LocatorSelectOptionOptions { Timeout = timeout });
            }
            return;
        }

        // Dropdown "custom" (div-uri): deschidem lista si alegem optiunea dupa text
        await l.ClickAsync(new LocatorClickOptions { Timeout = timeout });
        var page = l.Page;
        var option = page.GetByRole(AriaRole.Option, new PageGetByRoleOptions { Name = value, Exact = true });
        if (await option.CountAsync() == 0)
            option = page.GetByText(value, new PageGetByTextOptions { Exact = true });
        await option.First.ClickAsync(new LocatorClickOptions { Timeout = timeout });
    }

    private static string OutputPath(ActionRequest r, string baseName)
    {
        if (!string.IsNullOrWhiteSpace(r.Value) && r.Action is RprAction.ScreenshotElement or RprAction.ScreenshotPage)
        {
            var dir = Path.GetDirectoryName(Path.GetFullPath(r.Value));
            if (dir != null) Directory.CreateDirectory(dir);
            return r.Value;
        }
        Directory.CreateDirectory(r.OutputFolder);
        var safe = string.Concat(baseName.Select(c => Path.GetInvalidFileNameChars().Contains(c) ? '_' : c));
        return Path.Combine(r.OutputFolder, $"{safe}_{DateTime.Now:yyyyMMdd_HHmmss_fff}.png");
    }

    // =========================================================
    // 4. Spy — marcarea interactiva a unui obiect
    // =========================================================
    public async Task<UiObject?> CaptureObjectAsync(SpyOptions options, CancellationToken ct)
    {
        var page = await RequirePageAsync(ct);
        await page.BringToFrontAsync();

        var tcs = new TaskCompletionSource<SpyEvent?>(TaskCreationOptions.RunContinuationsAsynchronously);
        _spyTcs = tcs;
        try
        {
            await StartSpyEverywhereAsync("spy", options.Hint);

            using var reg = ct.Register(() => tcs.TrySetResult(null));
            var ev = await tcs.Task;
            if (ev?.Element == null || ev.Type != "captured") return null;

            var framePath = await FramePathAsync(_lastEventFrame);
            var obj = ev.Element.ToUiObject(UiTechnology.Web, framePath);
            await VerifyAndScreenshotAsync(obj, options.ScreenshotFolder, ct);
            return obj;
        }
        finally
        {
            _spyTcs = null;
            await StopSpyEverywhereAsync();
        }
    }

    private IFrame? _lastEventFrame;

    private void OnSpyEvent(BindingSource source, string json)
    {
        var ev = SpyEvent.Parse(json);
        if (ev == null) return;
        _lastEventFrame = source.Frame;

        // Spy
        if (_spyTcs != null && ev.Type is "captured" or "cancel")
        {
            if (source.Page != null && !source.Page.IsClosed) _page = source.Page;
            _spyTcs.TrySetResult(ev);
            return;
        }

        // Recorder
        var cb = _recordCallback;
        if (cb == null) return;
        if (ev.Type == "stop") { _ = StopRecordingAsync(); Info?.Invoke("Inregistrare oprita (Esc)."); return; }
        if (ev.Type != "action" || ev.Element == null) return;

        var action = ev.ToRprAction();
        if (action == null) return;

        // calculul FramePath e asincron; il facem si apoi trimitem actiunea
        var frame = source.Frame;
        _ = Task.Run(async () =>
        {
            try
            {
                var fp = await FramePathAsync(frame);
                cb(new RecordedAction(action.Value, ev.Element.ToUiObject(UiTechnology.Web, fp), ev.Value));
            }
            catch (Exception ex) { Info?.Invoke("Eroare la inregistrare: " + ex.Message); }
        });
    }

    private async Task StartSpyEverywhereAsync(string mode, string hint)
    {
        await EnsureBindingAsync();
        foreach (var p in _context!.Pages.Where(p => !p.IsClosed))
            foreach (var f in p.Frames)
                await StartSpyInFrameAsync(f, mode, hint);
    }

    private static async Task StartSpyInFrameAsync(IFrame frame, string mode, string hint = "")
    {
        try
        {
            await frame.EvaluateAsync(SpyScript.Source);
            await frame.EvaluateAsync("([m, h]) => window.__apdc.startSpy(m, h)", new object[] { mode, hint });
        }
        catch (PlaywrightException) { /* frame in navigare / detasat */ }
    }

    private async Task StopSpyEverywhereAsync()
    {
        if (_context == null) return;
        foreach (var p in _context.Pages.Where(p => !p.IsClosed))
            foreach (var f in p.Frames)
            {
                try { await f.EvaluateAsync("() => window.__apdc && window.__apdc.stopSpy()"); }
                catch (PlaywrightException) { }
            }
    }

    /// <summary>Lantul de selectori de iframe de la pagina principala pana la frame-ul dat.</summary>
    private static async Task<List<string>> FramePathAsync(IFrame? frame)
    {
        var path = new List<string>();
        var f = frame;
        while (f?.ParentFrame != null)
        {
            var el = await f.FrameElementAsync();
            var sel = await el.EvaluateAsync<string?>(
                "e => window.__apdc ? window.__apdc.frameSelector(e) : (e.id ? '#' + e.id : (e.name ? `iframe[name=\"${e.name}\"]` : 'iframe'))");
            path.Insert(0, string.IsNullOrWhiteSpace(sel) ? "iframe" : sel!);
            f = f.ParentFrame;
        }
        return path;
    }

    /// <summary>
    /// Verificare dupa capturare: fiecare locator e testat; cei care nu gasesc
    /// exact elementul sunt dezactivati (dar pastrati). Se salveaza si o captura.
    /// </summary>
    public async Task VerifyAndScreenshotAsync(UiObject obj, string screenshotFolder, CancellationToken ct)
    {
        var page = await RequirePageAsync(ct);
        foreach (var loc in obj.Locators)
        {
            try
            {
                int count = await Build(page, obj, loc).CountAsync();
                if (count == 0) loc.Enabled = false;               // nu gaseste nimic
                else if (count > 1) loc.Score = Math.Min(loc.Score, 20); // ambiguu: ramane doar ca rezerva
            }
            catch (PlaywrightException)
            {
                loc.Enabled = false;
            }
        }
        obj.Locators = obj.Locators.OrderByDescending(l => l.Enabled).ThenByDescending(l => l.Score).ToList();

        if (string.IsNullOrWhiteSpace(screenshotFolder)) return;
        try
        {
            var (l, _) = await ResolveAsync(obj, 1500, ct);
            if (l == null) return;
            Directory.CreateDirectory(screenshotFolder);
            var file = $"{obj.Name}_{DateTime.Now:yyyyMMdd_HHmmss}.png";
            await l.ScreenshotAsync(new LocatorScreenshotOptions { Path = Path.Combine(screenshotFolder, file), Timeout = 3000 });
            obj.Screenshot = file;
        }
        catch (PlaywrightException) { /* captura e optionala */ }
    }

    // =========================================================
    // 5. Recorder — click-uri / scriere -> pasi
    // =========================================================
    public async Task StartRecordingAsync(Action<RecordedAction> onAction, SpyOptions options, CancellationToken ct)
    {
        await RequirePageAsync(ct);
        _recordCallback = onAction;
        await StartSpyEverywhereAsync("record", options.Hint);
    }

    public async Task StopRecordingAsync()
    {
        _recordCallback = null;
        await StopSpyEverywhereAsync();
    }

    // =========================================================
    // 6. Inchidere
    // =========================================================
    public async Task CloseAsync()
    {
        try
        {
            if (_context != null) await _context.CloseAsync();
            if (_browser != null) await _browser.CloseAsync();
        }
        catch (PlaywrightException) { }
        _context = null;
        _browser = null;
        _page = null;
        _bindingExposed = false;
    }

    public async ValueTask DisposeAsync()
    {
        await CloseAsync();
        _pw?.Dispose();
        _pw = null;
    }

    private static string FirstLine(string s)
    {
        var i = s.IndexOfAny(new[] { '\r', '\n' });
        return i > 0 ? s[..i] : s;
    }
}
