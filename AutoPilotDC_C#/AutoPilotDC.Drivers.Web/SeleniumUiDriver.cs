// ============================================================
// AutoPilot DC v4 — Drivers.Web
// SeleniumUiDriver.cs — Web prin Selenium WebDriver
// Aceleasi obiecte si aceiasi pasi ca Playwright; util cand
// infrastructura existenta foloseste deja WebDriver / Selenium Grid.
// Spy si Recorder functioneaza in documentul principal (nu in iframe-uri);
// la rulare iframe-urile din FramePath sunt suportate.
// ============================================================

using System.Collections;
using System.Text.Json;
using OpenQA.Selenium;
using OpenQA.Selenium.Chrome;
using OpenQA.Selenium.Chromium;
using OpenQA.Selenium.Edge;
using OpenQA.Selenium.Firefox;
using OpenQA.Selenium.Interactions;
using AutoPilotDC.Rpr.Engine;
using AutoPilotDC.Rpr.Model;

namespace AutoPilotDC.Drivers.Web;

public sealed class SeleniumUiDriver : IUiDriver, ISpyCapable, IRecordCapable
{
    private readonly WebDriverSettings _settings;
    private IWebDriver? _driver;
    private CancellationTokenSource? _recordCts;

    public UiTechnology Technology => UiTechnology.WebSelenium;
    public string DisplayName => $"Web (Selenium, {_settings.Browser})";
    public bool IsOpen => _driver != null;
    public bool IsRecording => _recordCts != null;

    public event Action<string>? Info;

    public SeleniumUiDriver(WebDriverSettings settings) => _settings = settings;

    // =========================================================
    // 1. Pornire
    // =========================================================
    public void Open(string? url)
    {
        if (_driver == null)
        {
            var profile = string.IsNullOrWhiteSpace(_settings.ProfileFolder)
                ? null
                : Path.Combine(_settings.ProfileFolder, "selenium");
            try
            {
                _driver = _settings.Browser switch
                {
                    BrowserKind.Chrome or BrowserKind.Chromium => new ChromeDriver(Chromium<ChromeOptions>(profile)),
                    BrowserKind.Firefox => new FirefoxDriver(new FirefoxOptions()),
                    _ => new EdgeDriver(Chromium<EdgeOptions>(profile)),
                };
            }
            catch (WebDriverException ex)
            {
                throw new RprStepException(
                    $"Nu pot porni {_settings.Browser} prin Selenium. Selenium Manager descarca automat driverul — " +
                    $"verifica accesul la internet sau pune msedgedriver.exe / chromedriver.exe langa aplicatie. Detalii: {ex.Message}", ex);
            }
            _driver.Manage().Timeouts().PageLoad = TimeSpan.FromMilliseconds(_settings.NavigationTimeoutMs);
        }
        if (!string.IsNullOrWhiteSpace(url))
        {
            url = url.Trim();
            if (!url.Contains("://")) url = "https://" + url;
            _driver.Navigate().GoToUrl(url);
        }
    }

    private T Chromium<T>(string? profile) where T : ChromiumOptions, new()
    {
        var o = new T();
        o.AddArgument("--start-maximized");
        if (_settings.Headless) o.AddArgument("--headless=new");
        if (profile != null)
        {
            Directory.CreateDirectory(profile);
            o.AddArgument($"--user-data-dir={profile}");
        }
        return o;
    }

    private IWebDriver Driver => _driver ?? throw new RprStepException("Browserul (Selenium) nu este deschis. Adauga pasul \"Deschide browser\".");

    private IJavaScriptExecutor Js => (IJavaScriptExecutor)Driver;

    private void EnsureScript()
    {
        var has = Js.ExecuteScript("return typeof window.__apdc !== 'undefined';");
        if (has is bool b && b) return;
        Js.ExecuteScript(SpyScript.Source);
    }

    // =========================================================
    // 2. Gasire element
    // =========================================================
    private void EnterFrames(UiObject obj)
    {
        Driver.SwitchTo().DefaultContent();
        foreach (var sel in obj.FramePath)
            Driver.SwitchTo().Frame(Driver.FindElement(By.CssSelector(sel)));
    }

    private IReadOnlyList<IWebElement> FindAll(Locator loc)
    {
        switch (loc.Kind)
        {
            case LocatorKind.Id:    return Driver.FindElements(By.Id(loc.Value));
            case LocatorKind.Name:  return Driver.FindElements(By.Name(loc.Value));
            case LocatorKind.XPath: return Driver.FindElements(By.XPath(loc.Value.StartsWith("xpath=") ? loc.Value[6..] : loc.Value));
            case LocatorKind.Css:
            case LocatorKind.TestId:
                return Driver.FindElements(By.CssSelector(loc.Value));
            default:
                // Rol / eticheta / text / placeholder: aceeasi logica JS ca la capturare
                EnsureScript();
                var res = Js.ExecuteScript("return window.__apdc.resolve(arguments[0], arguments[1]);", loc.Kind.ToString(), loc.Value);
                return res is IEnumerable list ? list.OfType<IWebElement>().ToList() : new List<IWebElement>();
        }
    }

    private async Task<(IWebElement? El, Locator? Used)> ResolveAsync(UiObject obj, int timeoutMs, CancellationToken ct)
    {
        var deadline = DateTime.UtcNow.AddMilliseconds(Math.Max(0, timeoutMs));
        while (true)
        {
            IWebElement? multi = null; Locator? multiUsed = null;
            try
            {
                EnterFrames(obj);
                foreach (var loc in obj.ActiveLocators)
                {
                    ct.ThrowIfCancellationRequested();
                    IReadOnlyList<IWebElement> found;
                    try { found = FindAll(loc); }
                    catch (WebDriverException) { continue; }
                    if (found.Count == 1) return (found[0], loc);
                    if (found.Count > 1 && multi == null) { multi = found[0]; multiUsed = loc; }
                }
            }
            catch (NoSuchElementException) { /* iframe-ul nu a aparut inca */ }
            catch (NoSuchFrameException) { }

            if (multi != null) return (multi, multiUsed);
            if (DateTime.UtcNow >= deadline) return (null, null);
            await Task.Delay(250, ct);
        }
    }

    private async Task<IWebElement> RequireAsync(UiObject obj, int timeoutMs, CancellationToken ct)
    {
        var (el, _) = await ResolveAsync(obj, timeoutMs, ct);
        return el ?? throw new ElementNotFoundException(obj, timeoutMs, $"pagina curenta: {Driver.Url}");
    }

    // =========================================================
    // 3. IUiDriver
    // =========================================================
    public async Task<ElementState> GetStateAsync(UiObject obj, int timeoutMs, CancellationToken ct)
    {
        if (_driver == null) return ElementState.NotFound;
        var (el, used) = await ResolveAsync(obj, timeoutMs, ct);
        if (el == null) return ElementState.NotFound;
        try
        {
            return new ElementState(true, el.Displayed, el.Enabled, el.Text.Trim(), el.GetDomProperty("value") ?? "", used);
        }
        catch (StaleElementReferenceException)
        {
            return ElementState.NotFound;
        }
    }

    public async Task HighlightAsync(UiObject obj, int durationMs, CancellationToken ct)
    {
        try
        {
            var (el, _) = await ResolveAsync(obj, Math.Min(3000, durationMs * 4), ct);
            if (el == null) return;
            EnsureScriptInCurrentFrame();
            Js.ExecuteScript("window.__apdc && window.__apdc.highlight(arguments[0], arguments[1]);", el, durationMs);
        }
        catch (WebDriverException) { }
        catch (RprStepException) { }
    }

    private void EnsureScriptInCurrentFrame()
    {
        var has = Js.ExecuteScript("return typeof window.__apdc !== 'undefined';");
        if (has is not true) Js.ExecuteScript(SpyScript.Source);
    }

    public Task<string?> CaptureErrorScreenshotAsync(string folder, string name, CancellationToken ct)
    {
        if (_driver is not ITakesScreenshot shooter) return Task.FromResult<string?>(null);
        var path = Path.Combine(folder, name + ".png");
        shooter.GetScreenshot().SaveAsFile(path);
        return Task.FromResult<string?>(path);
    }

    public async Task<string?> ExecuteAsync(ActionRequest r, CancellationToken ct)
    {
        try
        {
            return await ExecuteCoreAsync(r, ct);
        }
        catch (WebDriverException ex)
        {
            throw new RprStepException(ex.Message.Split('\n')[0], ex);
        }
    }

    private async Task<string?> ExecuteCoreAsync(ActionRequest r, CancellationToken ct)
    {
        switch (r.Action)
        {
            case RprAction.OpenBrowser:  Open(r.Value); return null;
            case RprAction.Navigate:     Open(r.Value); return null;
            case RprAction.Back:         Driver.Navigate().Back(); return null;
            case RprAction.Refresh:      Driver.Navigate().Refresh(); return null;
            case RprAction.CloseBrowser: await DisposeAsync(); return null;
            case RprAction.SwitchTab:    return SwitchTab(r.Value);
            case RprAction.HandleDialog:
                try
                {
                    var alert = Driver.SwitchTo().Alert();
                    var text = alert.Text;
                    if (r.Value.Trim().StartsWith("d", StringComparison.OrdinalIgnoreCase)) alert.Dismiss(); else alert.Accept();
                    return text;
                }
                catch (NoAlertPresentException) { return ""; }
            case RprAction.ScreenshotPage:
            {
                var path = string.IsNullOrWhiteSpace(r.Value) ? Path.Combine(Ensure(r.OutputFolder), $"pagina_{DateTime.Now:yyyyMMdd_HHmmss_fff}.png") : r.Value;
                ((ITakesScreenshot)Driver).GetScreenshot().SaveAsFile(path);
                return path;
            }
            case RprAction.PressKey when r.Target == null:
                new Actions(Driver).SendKeys(ToSeleniumKeys(r.Value)).Perform();
                return null;
        }

        var obj = r.Target ?? throw new RprStepException("Actiunea are nevoie de un obiect.");
        var el = await RequireAsync(obj, r.TimeoutMs, ct);

        switch (r.Action)
        {
            case RprAction.Click:
                if (r.DirectMode) Js.ExecuteScript("arguments[0].click();", el); else el.Click();
                return null;
            case RprAction.DoubleClick: new Actions(Driver).DoubleClick(el).Perform(); return null;
            case RprAction.RightClick:  new Actions(Driver).ContextClick(el).Perform(); return null;
            case RprAction.Hover:       new Actions(Driver).MoveToElement(el).Perform(); return null;
            case RprAction.TypeText:    el.Clear(); el.SendKeys(r.Value); return null;
            case RprAction.AppendText:  el.SendKeys(r.Value); return null;
            case RprAction.Clear:       el.Clear(); return null;
            case RprAction.PressKey:    el.SendKeys(ToSeleniumKeys(r.Value)); return null;
            case RprAction.Focus:       Js.ExecuteScript("arguments[0].focus();", el); return null;
            case RprAction.Check:       if (!el.Selected) el.Click(); return null;
            case RprAction.Uncheck:     if (el.Selected) el.Click(); return null;
            case RprAction.SelectOption:
            {
                var ok = Js.ExecuteScript(
                    @"const s = arguments[0], t = arguments[1].trim();
                      if (s.tagName.toLowerCase() !== 'select') return false;
                      const i = Array.from(s.options).findIndex(o => o.text.trim() === t || o.value === t);
                      if (i < 0) return false;
                      s.selectedIndex = i;
                      s.dispatchEvent(new Event('input', { bubbles: true }));
                      s.dispatchEvent(new Event('change', { bubbles: true }));
                      return true;", el, r.Value);
                if (ok is not true)
                {
                    el.Click();
                    var opt = Driver.FindElements(By.XPath($"//*[normalize-space(.)={XPathLiteral(r.Value)}]")).LastOrDefault(e => e.Displayed)
                              ?? throw new RprStepException($"Optiunea \"{r.Value}\" nu a fost gasita.");
                    opt.Click();
                }
                return null;
            }
            case RprAction.ReadText:      return el.Text.Trim();
            case RprAction.ReadValue:     return el.GetDomProperty("value") ?? el.Text.Trim();
            case RprAction.ReadAttribute: return el.GetAttribute(r.Value) ?? "";
            case RprAction.Highlight:     await HighlightAsync(obj, 800, ct); return null;
            case RprAction.ScreenshotElement:
            {
                var path = string.IsNullOrWhiteSpace(r.Value) ? Path.Combine(Ensure(r.OutputFolder), $"{obj.Name}_{DateTime.Now:yyyyMMdd_HHmmss_fff}.png") : r.Value;
                ((ITakesScreenshot)el).GetScreenshot().SaveAsFile(path);
                return path;
            }
            default:
                throw new RprStepException($"Actiunea {r.Action} nu e disponibila pentru web (Selenium).");
        }
    }

    private string SwitchTab(string value)
    {
        var handles = Driver.WindowHandles;
        if (int.TryParse(value.Trim(), out var idx))
        {
            if (idx < 0) idx = handles.Count + idx;
            if (idx < 0 || idx >= handles.Count) throw new RprStepException($"Nu exista tab-ul {value}.");
            Driver.SwitchTo().Window(handles[idx]);
            return Driver.Title;
        }
        foreach (var h in handles)
        {
            Driver.SwitchTo().Window(h);
            if (Driver.Title.Contains(value, StringComparison.OrdinalIgnoreCase) || Driver.Url.Contains(value, StringComparison.OrdinalIgnoreCase))
                return Driver.Title;
        }
        throw new RprStepException($"Nu exista tab-ul \"{value}\".");
    }

    private static string Ensure(string dir) { Directory.CreateDirectory(dir); return dir; }

    private static string XPathLiteral(string s) =>
        !s.Contains('\'') ? $"'{s}'" : !s.Contains('"') ? $"\"{s}\"" : "concat('" + s.Replace("'", "', \"'\", '") + "')";

    /// <summary>"Ctrl+A" -> Keys.Control + "a" ; "Enter" -> Keys.Enter</summary>
    public static string ToSeleniumKeys(string combo)
    {
        var parts = combo.Split('+', StringSplitOptions.TrimEntries | StringSplitOptions.RemoveEmptyEntries);
        var sb = new System.Text.StringBuilder();
        foreach (var p in parts)
        {
            sb.Append(p.ToLowerInvariant() switch
            {
                "ctrl" or "control" => Keys.Control,
                "shift" => Keys.Shift,
                "alt" => Keys.Alt,
                "enter" or "return" => Keys.Enter,
                "tab" => Keys.Tab,
                "esc" or "escape" => Keys.Escape,
                "del" or "delete" => Keys.Delete,
                "backspace" => Keys.Backspace,
                "space" => Keys.Space,
                "home" => Keys.Home,
                "end" => Keys.End,
                "pgup" or "pageup" => Keys.PageUp,
                "pgdn" or "pagedown" => Keys.PageDown,
                "up" => Keys.ArrowUp,
                "down" => Keys.ArrowDown,
                "left" => Keys.ArrowLeft,
                "right" => Keys.ArrowRight,
                "f1" => Keys.F1, "f2" => Keys.F2, "f3" => Keys.F3, "f4" => Keys.F4,
                "f5" => Keys.F5, "f6" => Keys.F6, "f7" => Keys.F7, "f8" => Keys.F8,
                "f9" => Keys.F9, "f10" => Keys.F10, "f11" => Keys.F11, "f12" => Keys.F12,
                _ => p.Length == 1 ? p.ToLowerInvariant() : p,
            });
        }
        if (parts.Length > 1) sb.Append(Keys.Null); // elibereaza modificatorii
        return sb.ToString();
    }

    // =========================================================
    // 4. Spy + Recorder (prin coada citita periodic)
    // =========================================================
    public async Task<UiObject?> CaptureObjectAsync(SpyOptions options, CancellationToken ct)
    {
        Driver.SwitchTo().DefaultContent();
        StartSpy("spy", options.Hint);
        try
        {
            while (true)
            {
                ct.ThrowIfCancellationRequested();
                foreach (var ev in Drain("spy", options.Hint))
                {
                    if (ev.Type == "cancel") return null;
                    if (ev.Type == "captured" && ev.Element != null)
                        return ev.Element.ToUiObject(UiTechnology.WebSelenium, new List<string>());
                }
                await Task.Delay(200, ct);
            }
        }
        catch (OperationCanceledException)
        {
            return null;
        }
        finally
        {
            try { Js.ExecuteScript("window.__apdc && window.__apdc.stopSpy();"); } catch (WebDriverException) { }
        }
    }

    private void StartSpy(string mode, string hint)
    {
        EnsureScript();
        Js.ExecuteScript("window.__apdc.startSpy(arguments[0], arguments[1]);", mode, hint);
    }

    /// <summary>Citeste evenimentele din pagina; daca pagina s-a schimbat, reinjecteaza Spy.</summary>
    private List<SpyEvent> Drain(string mode, string hint)
    {
        var result = new List<SpyEvent>();
        object? raw;
        try { raw = Js.ExecuteScript("return window.__apdc ? window.__apdc.drain() : null;"); }
        catch (WebDriverException) { return result; } // navigare in curs

        if (raw == null)
        {
            try { StartSpy(mode, hint); } catch (WebDriverException) { }
            return result;
        }

        var items = JsonSerializer.Deserialize<List<string>>(raw.ToString() ?? "[]") ?? new();
        foreach (var json in items)
            if (SpyEvent.Parse(json) is { } ev) result.Add(ev);
        return result;
    }

    public Task StartRecordingAsync(Action<RecordedAction> onAction, SpyOptions options, CancellationToken ct)
    {
        Driver.SwitchTo().DefaultContent();
        StartSpy("record", options.Hint);
        _recordCts = CancellationTokenSource.CreateLinkedTokenSource(ct);
        var token = _recordCts.Token;

        _ = Task.Run(async () =>
        {
            while (!token.IsCancellationRequested)
            {
                foreach (var ev in Drain("record", options.Hint))
                {
                    if (ev.Type == "stop") { await StopRecordingAsync(); Info?.Invoke("Inregistrare oprita (Esc)."); return; }
                    if (ev.Type == "action" && ev.Element != null && ev.ToRprAction() is { } action)
                        onAction(new RecordedAction(action, ev.Element.ToUiObject(UiTechnology.WebSelenium, new List<string>()), ev.Value));
                }
                try { await Task.Delay(200, token); } catch (OperationCanceledException) { return; }
            }
        }, token);
        return Task.CompletedTask;
    }

    public Task StopRecordingAsync()
    {
        _recordCts?.Cancel();
        _recordCts = null;
        try { Js.ExecuteScript("window.__apdc && window.__apdc.stopSpy();"); } catch (Exception) { }
        return Task.CompletedTask;
    }

    public ValueTask DisposeAsync()
    {
        _recordCts?.Cancel();
        try { _driver?.Quit(); } catch (WebDriverException) { }
        _driver = null;
        return ValueTask.CompletedTask;
    }
}
