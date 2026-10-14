// ============================================================
// AutoPilot DC v4 — Drivers.Web
// WebShared.cs — Cod comun Playwright / Selenium:
//   scriptul Spy, setari, conversia elementului capturat in UiObject,
//   normalizarea tastelor.
// ============================================================

using System.Reflection;
using System.Text.Json;
using AutoPilotDC.Rpr.Model;

namespace AutoPilotDC.Drivers.Web;

public enum BrowserKind
{
    /// <summary>Microsoft Edge instalat pe PC (recomandat in companii, nu necesita descarcari).</summary>
    Edge,
    /// <summary>Google Chrome instalat pe PC.</summary>
    Chrome,
    /// <summary>Chromium descarcat de Playwright (necesita "playwright install").</summary>
    Chromium,
    Firefox,
}

public sealed class WebDriverSettings
{
    public BrowserKind Browser { get; set; } = BrowserKind.Edge;

    public bool Headless { get; set; }

    /// <summary>
    /// Profil de browser separat si persistent: login-ul (SSO, cookies) ramane
    /// intre rulari. Gol = profil temporar.
    /// </summary>
    public string ProfileFolder { get; set; } = "";

    /// <summary>Timeout pentru incarcarea paginilor (ms).</summary>
    public int NavigationTimeoutMs { get; set; } = 60000;
}

/// <summary>Scriptul Spy (resursa incorporata).</summary>
public static class SpyScript
{
    private static string? _source;

    public static string Source
    {
        get
        {
            if (_source != null) return _source;
            var asm = Assembly.GetExecutingAssembly();
            using var stream = asm.GetManifestResourceStream("AutoPilotDC.Drivers.Web.apdc-spy.js")
                ?? throw new InvalidOperationException("Scriptul Spy lipseste din assembly (apdc-spy.js).");
            using var reader = new StreamReader(stream);
            _source = reader.ReadToEnd();
            return _source;
        }
    }
}

// ─────────────────────────────────────────────────────────────
// Elementul capturat de Spy (JSON trimis de apdc-spy.js)
// ─────────────────────────────────────────────────────────────

public sealed class CapturedLocator
{
    public string Kind { get; set; } = "";
    public string Value { get; set; } = "";
    public int Score { get; set; }
}

public sealed class CapturedElement
{
    public string Tag { get; set; } = "";
    public string Type { get; set; } = "";
    public string Role { get; set; } = "";
    public string Name { get; set; } = "";
    public string Text { get; set; } = "";
    public string Label { get; set; } = "";
    public string SuggestedName { get; set; } = "";
    public List<CapturedLocator> Locators { get; set; } = new();
    public Dictionary<string, string> Attributes { get; set; } = new();
    public string Url { get; set; } = "";

    public UiObject ToUiObject(UiTechnology technology, List<string>? framePath)
    {
        var obj = new UiObject
        {
            Name = string.IsNullOrWhiteSpace(SuggestedName) ? "Element" : SuggestedName,
            Technology = technology,
            ElementType = string.IsNullOrWhiteSpace(Role) ? Tag : $"{Tag} ({Role})",
            CapturedText = Text,
            Context = TrimUrl(Url),
            FramePath = framePath ?? new List<string>(),
            Attributes = Attributes,
            CapturedAt = DateTime.Now,
        };
        foreach (var l in Locators)
            if (Enum.TryParse<LocatorKind>(l.Kind, true, out var kind))
                obj.Locators.Add(new Locator(kind, l.Value, l.Score));
        return obj;
    }

    private static string TrimUrl(string url)
    {
        // pastram doar host + cale (fara parametri care se schimba)
        if (Uri.TryCreate(url, UriKind.Absolute, out var u)) return u.GetLeftPart(UriPartial.Path);
        return url;
    }
}

/// <summary>Eveniment trimis de script: captured / cancel / action / stop.</summary>
public sealed class SpyEvent
{
    public string Type { get; set; } = "";
    public string Action { get; set; } = "";
    public string Value { get; set; } = "";
    public CapturedElement? Element { get; set; }

    private static readonly JsonSerializerOptions Opts = new() { PropertyNameCaseInsensitive = true };

    public static SpyEvent? Parse(string json)
    {
        try { return JsonSerializer.Deserialize<SpyEvent>(json, Opts); }
        catch { return null; }
    }

    public RprAction? ToRprAction() => Action switch
    {
        "Click"        => RprAction.Click,
        "DoubleClick"  => RprAction.DoubleClick,
        "TypeText"     => RprAction.TypeText,
        "SelectOption" => RprAction.SelectOption,
        "Check"        => RprAction.Check,
        "Uncheck"      => RprAction.Uncheck,
        "PressKey"     => RprAction.PressKey,
        _              => null,
    };
}

public static class KeyNames
{
    /// <summary>"Ctrl+Shift+a" -> "Control+Shift+a" (formatul Playwright).</summary>
    public static string ToPlaywright(string key)
    {
        var parts = key.Split('+', StringSplitOptions.TrimEntries | StringSplitOptions.RemoveEmptyEntries);
        return string.Join("+", parts.Select(p => p.ToLowerInvariant() switch
        {
            "ctrl" or "control" => "Control",
            "shift"             => "Shift",
            "alt"               => "Alt",
            "win" or "meta" or "cmd" => "Meta",
            "esc" or "escape"   => "Escape",
            "del" or "delete"   => "Delete",
            "ins" or "insert"   => "Insert",
            "enter" or "return" => "Enter",
            "tab"               => "Tab",
            "space"             => "Space",
            "backspace"         => "Backspace",
            "pgup" or "pageup"  => "PageUp",
            "pgdn" or "pagedown"=> "PageDown",
            "home"              => "Home",
            "end"               => "End",
            "up"                => "ArrowUp",
            "down"              => "ArrowDown",
            "left"              => "ArrowLeft",
            "right"             => "ArrowRight",
            var f when f.Length >= 2 && f[0] == 'f' && int.TryParse(f[1..], out _) => f.ToUpperInvariant(),
            _ => p,
        }));
    }
}
