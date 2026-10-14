// ============================================================
// AutoPilot DC v4 — Drivers.Windows
// DesktopUiDriver.cs — Aplicatii desktop Windows prin UI Automation
//
//  - Spy: elementul de sub mouse e conturat; F2 = captureaza, Esc = anuleaza.
//  - Locatori: AutomationId > ControlType|Name > ControlType|ClassName > cale in arbore.
//  - Context: "proces:nume.exe" (stabil) — cautarea se face in ferestrele procesului.
//  - Mod direct: actiuni prin pattern-uri UIA (Invoke, Value, Toggle),
//    fara miscarea mouse-ului.
// ============================================================

using System.Diagnostics;
using System.Drawing;
using System.Text.RegularExpressions;
using FlaUI.Core;
using FlaUI.Core.AutomationElements;
using FlaUI.Core.Capturing;
using FlaUI.Core.Conditions;
using FlaUI.Core.Definitions;
using FlaUI.Core.Input;
using FlaUI.Core.WindowsAPI;
using FlaUI.UIA3;
using AutoPilotDC.Rpr.Engine;
using AutoPilotDC.Rpr.Model;

namespace AutoPilotDC.Drivers.Windows;

public sealed class DesktopUiDriver : IUiDriver, ISpyCapable
{
    private readonly UIA3Automation _automation = new();
    private AutomationElement? _window;   // fereastra atasata (AttachWindow / LaunchApp)
    private int _attachedPid;

    public UiTechnology Technology => UiTechnology.Desktop;
    public string DisplayName => "Desktop (UI Automation)";

    private ConditionFactory Cf => _automation.ConditionFactory;

    // =========================================================
    // 1. Ferestre / context
    // =========================================================

    /// <summary>Ferestrele in care cautam obiectul (dupa contextul lui sau fereastra atasata).</summary>
    private List<AutomationElement> CandidateWindows(UiObject? obj)
    {
        var desktop = _automation.GetDesktop();
        var context = obj?.Context ?? "";

        if (context.StartsWith("proces:", StringComparison.OrdinalIgnoreCase))
        {
            var procName = Path.GetFileNameWithoutExtension(context["proces:".Length..].Trim());
            var pids = Process.GetProcessesByName(procName).Select(p => p.Id).ToList();
            return pids.SelectMany(pid => desktop.FindAllChildren(Cf.ByProcessId(pid))).ToList();
        }

        if (!string.IsNullOrWhiteSpace(context))
        {
            var re = new Regex(context, RegexOptions.IgnoreCase);
            return desktop.FindAllChildren()
                .Where(w => re.IsMatch(w.Properties.Name.ValueOrDefault ?? ""))
                .ToList();
        }

        if (_attachedPid != 0)
            return desktop.FindAllChildren(Cf.ByProcessId(_attachedPid)).ToList();

        return _window != null ? new List<AutomationElement> { _window } : new List<AutomationElement>();
    }

    // =========================================================
    // 2. Gasire element
    // =========================================================
    private AutomationElement[] FindAll(AutomationElement root, Locator loc)
    {
        switch (loc.Kind)
        {
            case LocatorKind.AutomationId:
                return root.FindAllDescendants(Cf.ByAutomationId(loc.Value));

            case LocatorKind.UiaName:
            case LocatorKind.ClassName:
            {
                var p = loc.Value.IndexOf('|');
                var typeText = p >= 0 ? loc.Value[..p] : "";
                var text = p >= 0 ? loc.Value[(p + 1)..] : loc.Value;
                ConditionBase cond = loc.Kind == LocatorKind.UiaName ? Cf.ByName(text) : Cf.ByClassName(text);
                if (Enum.TryParse<ControlType>(typeText, true, out var ct))
                    cond = cond.And(Cf.ByControlType(ct));
                return root.FindAllDescendants(cond);
            }

            case LocatorKind.UiaPath:
            {
                var el = FollowPath(root, loc.Value);
                return el != null ? new[] { el } : Array.Empty<AutomationElement>();
            }

            default:
                return Array.Empty<AutomationElement>();
        }
    }

    private Task<(AutomationElement? El, Locator? Used)> ResolveAsync(UiObject obj, int timeoutMs, CancellationToken ct) =>
        Task.Run(async () =>
        {
            var deadline = DateTime.UtcNow.AddMilliseconds(Math.Max(0, timeoutMs));
            while (true)
            {
                AutomationElement? multi = null; Locator? multiUsed = null;
                foreach (var win in CandidateWindows(obj))
                {
                    foreach (var loc in obj.ActiveLocators)
                    {
                        ct.ThrowIfCancellationRequested();
                        AutomationElement[] found;
                        try { found = FindAll(win, loc); }
                        catch (Exception) { continue; } // fereastra s-a inchis intre timp
                        if (found.Length == 1) return (found[0], loc);
                        if (found.Length > 1 && multi == null) { multi = found[0]; multiUsed = loc; }
                    }
                }
                if (multi != null) return (multi, multiUsed);
                if (DateTime.UtcNow >= deadline) return ((AutomationElement?)null, (Locator?)null);
                await Task.Delay(300, ct);
            }
        }, ct);

    private async Task<AutomationElement> RequireAsync(UiObject obj, int timeoutMs, CancellationToken ct)
    {
        var (el, _) = await ResolveAsync(obj, timeoutMs, ct);
        if (el != null) return el;
        var detail = CandidateWindows(obj).Count == 0
            ? $"nicio fereastra deschisa pentru contextul \"{obj.Context}\""
            : null;
        throw new ElementNotFoundException(obj, timeoutMs, detail);
    }

    // =========================================================
    // 3. IUiDriver
    // =========================================================
    public async Task<ElementState> GetStateAsync(UiObject obj, int timeoutMs, CancellationToken ct)
    {
        var (el, used) = await ResolveAsync(obj, timeoutMs, ct);
        if (el == null) return ElementState.NotFound;
        return await Task.Run(() =>
        {
            try
            {
                var p = el.Properties;
                return new ElementState(true, !p.IsOffscreen.ValueOrDefault, p.IsEnabled.ValueOrDefault,
                    ReadText(el), ReadValue(el), used);
            }
            catch (Exception) { return ElementState.NotFound; }
        }, ct);
    }

    public async Task HighlightAsync(UiObject obj, int durationMs, CancellationToken ct)
    {
        try
        {
            var (el, _) = await ResolveAsync(obj, Math.Min(3000, durationMs * 4), ct);
            el?.DrawHighlight(false, Color.Orange, TimeSpan.FromMilliseconds(durationMs));
        }
        catch (Exception ex) when (ex is not OperationCanceledException) { /* optional */ }
    }

    public Task<string?> CaptureErrorScreenshotAsync(string folder, string name, CancellationToken ct) =>
        Task.Run<string?>(() =>
        {
            var path = Path.Combine(folder, name + ".png");
            Capture.Screen().ToFile(path);
            return path;
        }, ct);

    public async Task<string?> ExecuteAsync(ActionRequest r, CancellationToken ct)
    {
        try
        {
            return await ExecuteCoreAsync(r, ct);
        }
        catch (Exception ex) when (ex is not RprStepException and not OperationCanceledException)
        {
            throw new RprStepException($"{ex.GetType().Name}: {ex.Message}", ex);
        }
    }

    private async Task<string?> ExecuteCoreAsync(ActionRequest r, CancellationToken ct)
    {
        // ── Fara obiect ────────────────────────────────────
        switch (r.Action)
        {
            case RprAction.LaunchApp:
                return await Task.Run(() => LaunchApp(r.Value, r.TimeoutMs), ct);
            case RprAction.AttachWindow:
                return await Task.Run(() => AttachWindow(r.Value, r.TimeoutMs, ct), ct);
            case RprAction.CloseWindow:
                await Task.Run(() => { _window?.AsWindow().Close(); _window = null; _attachedPid = 0; }, ct);
                return null;
            case RprAction.PressKey when r.Target == null:
                await Task.Run(() => PressCombo(r.Value), ct);
                return null;
        }

        var obj = r.Target ?? throw new RprStepException("Actiunea are nevoie de un obiect.");
        var el = await RequireAsync(obj, r.TimeoutMs, ct);

        return await Task.Run<string?>(() =>
        {
            switch (r.Action)
            {
                case RprAction.Click:
                    if (r.DirectMode && TryDirectClick(el)) return null;
                    el.Click(moveMouse: !r.DirectMode);
                    return null;

                case RprAction.DoubleClick: el.DoubleClick(); return null;
                case RprAction.RightClick:  el.RightClick(); return null;
                case RprAction.Hover:       Mouse.MoveTo(el.GetClickablePoint()); return null;

                case RprAction.TypeText:
                    if (el.Patterns.Value.IsSupported && !el.Patterns.Value.Pattern.IsReadOnly.ValueOrDefault)
                    {
                        el.Patterns.Value.Pattern.SetValue(r.Value);
                        return null;
                    }
                    el.Focus();
                    Keyboard.TypeSimultaneously(VkCtrl, VkA);
                    Keyboard.Type(r.Value);
                    return null;

                case RprAction.AppendText:
                    el.Focus();
                    Keyboard.Type(r.Value);
                    return null;

                case RprAction.Clear:
                    if (el.Patterns.Value.IsSupported) el.Patterns.Value.Pattern.SetValue("");
                    else { el.Focus(); Keyboard.TypeSimultaneously(VkCtrl, VkA); Keyboard.Type(VkDelete); }
                    return null;

                case RprAction.PressKey:
                    el.Focus();
                    PressCombo(r.Value);
                    return null;

                case RprAction.SelectOption:
                    if (el.Properties.ControlType.ValueOrDefault == ControlType.ComboBox)
                        el.AsComboBox().Select(r.Value);
                    else
                    {
                        var item = el.FindFirstDescendant(Cf.ByName(r.Value))
                                   ?? throw new RprStepException($"Optiunea \"{r.Value}\" nu exista in lista.");
                        if (item.Patterns.SelectionItem.IsSupported) item.Patterns.SelectionItem.Pattern.Select();
                        else item.Click();
                    }
                    return null;

                case RprAction.Check:
                case RprAction.Uncheck:
                {
                    bool want = r.Action == RprAction.Check;
                    if (el.Patterns.Toggle.IsSupported)
                    {
                        var tp = el.Patterns.Toggle.Pattern;
                        for (int i = 0; i < 3 && (tp.ToggleState.ValueOrDefault == ToggleState.On) != want; i++) tp.Toggle();
                    }
                    else if (el.Patterns.SelectionItem.IsSupported && want)
                        el.Patterns.SelectionItem.Pattern.Select();
                    else
                        el.Click();
                    return null;
                }

                case RprAction.Focus:     el.Focus(); return null;
                case RprAction.ReadText:  return ReadText(el);
                case RprAction.ReadValue: return ReadValue(el);

                case RprAction.ReadAttribute:
                    return r.Value.Trim().ToLowerInvariant() switch
                    {
                        "name"         => el.Properties.Name.ValueOrDefault ?? "",
                        "automationid" => el.Properties.AutomationId.ValueOrDefault ?? "",
                        "classname"    => el.Properties.ClassName.ValueOrDefault ?? "",
                        "helptext"     => el.Properties.HelpText.ValueOrDefault ?? "",
                        "isenabled"    => el.Properties.IsEnabled.ValueOrDefault.ToString(),
                        "controltype"  => el.Properties.ControlType.ValueOrDefault.ToString(),
                        "value"        => ReadValue(el),
                        _ => throw new RprStepException("Atribute disponibile: Name, AutomationId, ClassName, HelpText, IsEnabled, ControlType, Value."),
                    };

                case RprAction.Highlight:
                    el.DrawHighlight(false, Color.Orange, TimeSpan.FromMilliseconds(800));
                    return null;

                case RprAction.ScreenshotElement:
                {
                    var path = string.IsNullOrWhiteSpace(r.Value)
                        ? Path.Combine(EnsureDir(r.OutputFolder), $"{obj.Name}_{DateTime.Now:yyyyMMdd_HHmmss_fff}.png")
                        : r.Value;
                    Capture.Element(el).ToFile(path);
                    return path;
                }

                default:
                    throw new RprStepException($"Actiunea {r.Action} nu e disponibila pentru aplicatii desktop.");
            }
        }, ct);
    }

    private static bool TryDirectClick(AutomationElement el)
    {
        var pt = el.Patterns;
        if (pt.Invoke.IsSupported) { pt.Invoke.Pattern.Invoke(); return true; }
        if (pt.Toggle.IsSupported) { pt.Toggle.Pattern.Toggle(); return true; }
        if (pt.SelectionItem.IsSupported) { pt.SelectionItem.Pattern.Select(); return true; }
        if (pt.ExpandCollapse.IsSupported) { pt.ExpandCollapse.Pattern.Expand(); return true; }
        return false;
    }

    private static string ReadText(AutomationElement el)
    {
        try
        {
            if (el.Patterns.Text.IsSupported)
            {
                var t = el.Patterns.Text.Pattern.DocumentRange.GetText(-1);
                if (!string.IsNullOrWhiteSpace(t)) return t.Trim();
            }
        }
        catch (Exception) { /* unele controale raporteaza Text dar nu il ofera */ }
        var v = ReadValue(el);
        return string.IsNullOrEmpty(v) ? (el.Properties.Name.ValueOrDefault ?? "") : v;
    }

    private static string ReadValue(AutomationElement el)
    {
        try
        {
            if (el.Patterns.Value.IsSupported) return el.Patterns.Value.Pattern.Value.ValueOrDefault ?? "";
            if (el.Patterns.LegacyIAccessible.IsSupported) return el.Patterns.LegacyIAccessible.Pattern.Value.ValueOrDefault ?? "";
        }
        catch (Exception) { }
        return "";
    }

    // ── Taste: "Ctrl+Shift+S", "Enter", "F5", "Alt+F4" ────────
    // Coduri virtuale Windows (VK_*) — independente de numele din enum-ul FlaUI.
    private static readonly VirtualKeyShort VkCtrl = (VirtualKeyShort)0x11;
    private static readonly VirtualKeyShort VkA = (VirtualKeyShort)0x41;
    private static readonly VirtualKeyShort VkDelete = (VirtualKeyShort)0x2E;

    private static VirtualKeyShort ToVk(string raw)
    {
        var s = raw.Trim().ToUpperInvariant();
        int code = s switch
        {
            "CTRL" or "CONTROL" => 0x11,
            "SHIFT"             => 0x10,
            "ALT"               => 0x12,
            "WIN"               => 0x5B,
            "ENTER" or "RETURN" => 0x0D,
            "TAB"               => 0x09,
            "ESC" or "ESCAPE"   => 0x1B,
            "DEL" or "DELETE"   => 0x2E,
            "INS" or "INSERT"   => 0x2D,
            "BACKSPACE"         => 0x08,
            "SPACE"             => 0x20,
            "HOME"              => 0x24,
            "END"               => 0x23,
            "PGUP" or "PAGEUP"  => 0x21,
            "PGDN" or "PAGEDOWN"=> 0x22,
            "LEFT"              => 0x25,
            "UP"                => 0x26,
            "RIGHT"             => 0x27,
            "DOWN"              => 0x28,
            _ when s.Length == 1 && (char.IsLetter(s[0]) || char.IsDigit(s[0])) => s[0],          // A-Z, 0-9
            _ when s.Length >= 2 && s[0] == 'F' && int.TryParse(s[1..], out var f) && f is >= 1 and <= 24 => 0x6F + f, // F1 = 0x70
            _ => throw new RprStepException($"Tasta necunoscuta: \"{raw}\""),
        };
        return (VirtualKeyShort)code;
    }

    private static void PressCombo(string combo)
    {
        var keys = combo.Split('+', StringSplitOptions.TrimEntries | StringSplitOptions.RemoveEmptyEntries)
                        .Select(ToVk).ToArray();
        if (keys.Length == 0) return;
        if (keys.Length == 1) Keyboard.Type(keys[0]);
        else Keyboard.TypeSimultaneously(keys);
    }

    // ── Aplicatii / ferestre ─────────────────────────────────
    private string LaunchApp(string value, int timeoutMs)
    {
        value = value.Trim();
        string exe, args = "";
        if (value.StartsWith('"'))
        {
            int end = value.IndexOf('"', 1);
            exe = value[1..end];
            args = value[(end + 1)..].Trim();
        }
        else
        {
            int sp = value.IndexOf(".exe ", StringComparison.OrdinalIgnoreCase);
            exe = sp > 0 ? value[..(sp + 4)] : value;
            args = sp > 0 ? value[(sp + 5)..] : "";
        }

        var app = FlaUI.Core.Application.Launch(exe, args);
        _attachedPid = app.ProcessId;
        _window = app.GetMainWindow(_automation, TimeSpan.FromMilliseconds(Math.Max(5000, timeoutMs)));
        if (_window == null) throw new RprStepException($"Aplicatia {Path.GetFileName(exe)} a pornit, dar fereastra nu a aparut.");
        _window.SetForeground();
        return _window.Properties.Name.ValueOrDefault ?? "";
    }

    private string AttachWindow(string value, int timeoutMs, CancellationToken ct)
    {
        var probe = new UiObject { Context = value.Trim() };
        var deadline = DateTime.UtcNow.AddMilliseconds(Math.Max(1000, timeoutMs));
        while (true)
        {
            var win = CandidateWindows(probe).FirstOrDefault();
            if (win != null)
            {
                _window = win;
                _attachedPid = win.Properties.ProcessId.ValueOrDefault;
                win.SetForeground();
                return win.Properties.Name.ValueOrDefault ?? "";
            }
            if (DateTime.UtcNow >= deadline)
                throw new RprStepException($"Nu gasesc fereastra \"{value}\". Foloseste titlul (regex) sau proces:nume.exe.");
            ct.ThrowIfCancellationRequested();
            Thread.Sleep(300);
        }
    }

    private static string EnsureDir(string dir) { Directory.CreateDirectory(dir); return dir; }

    // =========================================================
    // 4. Spy — F2 captureaza elementul de sub mouse, Esc anuleaza
    // =========================================================
    public Task<UiObject?> CaptureObjectAsync(SpyOptions options, CancellationToken ct) =>
        Task.Run(async () =>
        {
            await Win32.WaitReleaseAsync(Win32.VK_F2, ct);
            AutomationElement? last = null;
            var lastDraw = DateTime.MinValue;

            while (true)
            {
                ct.ThrowIfCancellationRequested();

                if (Win32.IsDown(Win32.VK_ESCAPE)) return null;

                Win32.GetCursorPos(out var p);
                AutomationElement? el = null;
                try { el = _automation.FromPoint(new Point(p.X, p.Y)); } catch (Exception) { }

                if (el != null && Win32.IsDown(Win32.VK_F2))
                {
                    await Win32.WaitReleaseAsync(Win32.VK_F2, ct);
                    var obj = BuildObject(el);
                    TrySaveScreenshot(el, obj, options.ScreenshotFolder);
                    try { el.DrawHighlight(false, Color.LimeGreen, TimeSpan.FromMilliseconds(600)); } catch (Exception) { }
                    return obj;
                }

                // reconturam doar cand se schimba elementul (sau la 1 s, ca marcajul sa ramana vizibil)
                bool changed = el != null && (last == null || !SafeEquals(el, last));
                if (el != null && (changed || DateTime.UtcNow - lastDraw > TimeSpan.FromMilliseconds(900)))
                {
                    try { el.DrawHighlight(false, Color.FromArgb(0, 215, 160), TimeSpan.FromMilliseconds(1000)); } catch (Exception) { }
                    last = el;
                    lastDraw = DateTime.UtcNow;
                }
                await Task.Delay(120, ct);
            }
        }, ct);

    private static bool SafeEquals(AutomationElement a, AutomationElement b)
    {
        try { return a.Equals(b); } catch (Exception) { return false; }
    }

    private UiObject BuildObject(AutomationElement el)
    {
        var p = el.Properties;
        var controlType = p.ControlType.ValueOrDefault;
        var name = p.Name.ValueOrDefault ?? "";
        var autoId = p.AutomationId.ValueOrDefault ?? "";
        var cls = p.ClassName.ValueOrDefault ?? "";
        var window = TopWindow(el);
        string procName = "";
        try { procName = Process.GetProcessById(p.ProcessId.ValueOrDefault).ProcessName + ".exe"; } catch (Exception) { }

        var obj = new UiObject
        {
            Technology = UiTechnology.Desktop,
            Name = SuggestName(controlType, name, autoId),
            ElementType = controlType.ToString(),
            CapturedText = name,
            Context = string.IsNullOrEmpty(procName) ? Regex.Escape(window?.Properties.Name.ValueOrDefault ?? "") : "proces:" + procName,
            Attributes =
            {
                ["Name"] = name,
                ["AutomationId"] = autoId,
                ["ClassName"] = cls,
                ["ControlType"] = controlType.ToString(),
                ["Fereastra"] = window?.Properties.Name.ValueOrDefault ?? "",
                ["Proces"] = procName,
            },
        };

        var root = window ?? _automation.GetDesktop();
        void AddIfUnique(LocatorKind kind, string value, int score)
        {
            if (string.IsNullOrWhiteSpace(value)) return;
            try
            {
                int count = FindAll(root, new Locator(kind, value)).Length;
                if (count >= 1) obj.Locators.Add(new Locator(kind, value, count == 1 ? score : 20));
            }
            catch (Exception) { }
        }

        if (!string.IsNullOrWhiteSpace(autoId) && !Regex.IsMatch(autoId, @"^\d+$"))
            AddIfUnique(LocatorKind.AutomationId, autoId, 90);
        if (!string.IsNullOrWhiteSpace(name))
            AddIfUnique(LocatorKind.UiaName, $"{controlType}|{name}", 80);
        if (!string.IsNullOrWhiteSpace(cls))
            AddIfUnique(LocatorKind.ClassName, $"{controlType}|{cls}", 40);
        if (window != null)
        {
            var path = PathFrom(window, el);
            if (!string.IsNullOrEmpty(path)) obj.Locators.Add(new Locator(LocatorKind.UiaPath, path, 30));
        }

        obj.Locators = obj.Locators.OrderByDescending(l => l.Score).ToList();
        return obj;
    }

    private static string SuggestName(ControlType ct, string name, string autoId)
    {
        var prefix = ct switch
        {
            ControlType.Button => "Buton",
            ControlType.Edit => "Camp",
            ControlType.ComboBox => "Lista",
            ControlType.CheckBox => "Bifa",
            ControlType.RadioButton => "Optiune",
            ControlType.MenuItem => "Meniu",
            ControlType.TabItem => "Tab",
            ControlType.Hyperlink => "Link",
            ControlType.DataItem or ControlType.ListItem => "Rand",
            ControlType.Text => "Text",
            ControlType.Window => "Fereastra",
            _ => ct.ToString(),
        };
        var basis = !string.IsNullOrWhiteSpace(name) ? name : autoId;
        var clean = Regex.Replace(basis.Normalize(System.Text.NormalizationForm.FormD), @"\p{Mn}", "");
        clean = Regex.Replace(clean, @"[^A-Za-z0-9]+", "_").Trim('_');
        if (clean.Length > 30) clean = clean[..30];
        return string.IsNullOrEmpty(clean) ? prefix : $"{prefix}_{clean}";
    }

    private AutomationElement? TopWindow(AutomationElement el)
    {
        var walker = _automation.TreeWalkerFactory.GetControlViewWalker();
        var desktop = _automation.GetDesktop();
        AutomationElement? cur = el, parent;
        try
        {
            while ((parent = walker.GetParent(cur)) != null && !parent.Equals(desktop))
                cur = parent;
        }
        catch (Exception) { return null; }
        return cur;
    }

    // ── Cale in arbore: "Pane[1]/Button[name=OK]" ─────────────
    private string PathFrom(AutomationElement window, AutomationElement el)
    {
        var walker = _automation.TreeWalkerFactory.GetControlViewWalker();
        var segments = new List<string>();
        var cur = el;
        try
        {
            while (cur != null && !cur.Equals(window))
            {
                var parent = walker.GetParent(cur);
                if (parent == null) return "";
                var ct = cur.Properties.ControlType.ValueOrDefault;
                var name = cur.Properties.Name.ValueOrDefault ?? "";

                // index printre fratii de acelasi tip
                int index = 0, sameName = 0;
                for (var sib = walker.GetFirstChild(parent); sib != null; sib = walker.GetNextSibling(sib))
                {
                    if (sib.Equals(cur)) break;
                    if (sib.Properties.ControlType.ValueOrDefault == ct)
                    {
                        index++;
                        if ((sib.Properties.Name.ValueOrDefault ?? "") == name) sameName++;
                    }
                }
                segments.Insert(0, !string.IsNullOrEmpty(name) && sameName == 0 && !name.Contains('/') && !name.Contains(']')
                    ? $"{ct}[name={name}]"
                    : $"{ct}[{index}]");
                cur = parent;
            }
        }
        catch (Exception) { return ""; }
        return string.Join("/", segments);
    }

    private AutomationElement? FollowPath(AutomationElement root, string path)
    {
        var walker = _automation.TreeWalkerFactory.GetControlViewWalker();
        var cur = root;
        foreach (var seg in path.Split('/', StringSplitOptions.RemoveEmptyEntries))
        {
            var m = Regex.Match(seg, @"^(\w+)\[(?:name=(.*)|(\d+))\]$");
            if (!m.Success || !Enum.TryParse<ControlType>(m.Groups[1].Value, out var ct)) return null;
            var wantName = m.Groups[2].Success ? m.Groups[2].Value : null;
            int wantIndex = m.Groups[3].Success ? int.Parse(m.Groups[3].Value) : -1;

            AutomationElement? next = null;
            int i = 0;
            for (var ch = walker.GetFirstChild(cur); ch != null; ch = walker.GetNextSibling(ch))
            {
                if (ch.Properties.ControlType.ValueOrDefault != ct) continue;
                if (wantName != null ? (ch.Properties.Name.ValueOrDefault ?? "") == wantName : i == wantIndex)
                {
                    next = ch;
                    break;
                }
                i++;
            }
            if (next == null) return null;
            cur = next;
        }
        return cur;
    }

    private static void TrySaveScreenshot(AutomationElement el, UiObject obj, string folder)
    {
        if (string.IsNullOrWhiteSpace(folder)) return;
        try
        {
            Directory.CreateDirectory(folder);
            var file = $"{obj.Name}_{DateTime.Now:yyyyMMdd_HHmmss}.png";
            Capture.Element(el).ToFile(Path.Combine(folder, file));
            obj.Screenshot = file;
        }
        catch (Exception) { }
    }

    public ValueTask DisposeAsync()
    {
        _automation.Dispose();
        return ValueTask.CompletedTask;
    }
}
