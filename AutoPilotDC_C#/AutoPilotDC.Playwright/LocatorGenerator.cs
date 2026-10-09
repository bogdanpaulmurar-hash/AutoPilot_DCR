// ============================================================
// AutoPilot DC v3.9 -> C# WPF .NET 8
// LocatorGenerator.cs � Generator selectori CSS/XPath pentru browser steps
// Echivalent Python: nu exista direct, extensie noua Faza 6
// Autor: Bogdan Murar (Z003FU5C) � Siemens AG
// ============================================================

using System;
using System.Text.RegularExpressions;
using System.Threading.Tasks;
using AutoPilotDC.Models;
using Microsoft.Playwright;

namespace AutoPilotDC.Playwright;

/// <summary>
/// Generator si validator de selectori pentru browser steps.
/// Ofera metode pentru:
///   - Generare selector din element (via Playwright CDP)
///   - Validare selector existent pe pagina curenta
///   - Sugestii selector alternative (ID > Name > CSS > XPath)
///   - Conversie coordonate ecran -> selector element
/// </summary>
[System.Runtime.Versioning.SupportedOSPlatform("windows7.0")]
public sealed class LocatorGenerator
{
    private readonly PlaywrightEngine _engine;

    public LocatorGenerator(PlaywrightEngine engine)
    {
        _engine = engine ?? throw new ArgumentNullException(nameof(engine));
    }

    // =========================================================
    // ValidateSelector � Verifica daca selectorul exista pe pagina
    // Returneaza (valid, count, error)
    // =========================================================
    public async Task<(bool Valid, int Count, string Error)> ValidateSelectorAsync(
        string selector)
    {
        if (!_engine.IsOpen)
            return (false, 0, "Browser nu este deschis.");

        if (string.IsNullOrWhiteSpace(selector))
            return (false, 0, "Selector gol.");

        try
        {
            var elements = await _engine.Page!.QuerySelectorAllAsync(selector);
            int count = elements.Count;
            return (count > 0, count, count == 0 ? "Niciun element gasit." : string.Empty);
        }
        catch (Exception ex)
        {
            return (false, 0, $"Selector invalid: {ex.Message}");
        }
    }

    // =========================================================
    // SuggestSelector � Sugereaza cel mai bun selector pentru un element
    // Prioritate: #id > [name] > .class > tag[attr] > XPath
    // =========================================================
    public async Task<string> SuggestSelectorAsync(string baseSelector)
    {
        if (!_engine.IsOpen || string.IsNullOrWhiteSpace(baseSelector))
            return baseSelector;

        try
        {
            var element = await _engine.Page!.QuerySelectorAsync(baseSelector);
            if (element == null) return baseSelector;

            // Incearca ID
            var id = await element.GetAttributeAsync("id");
            if (!string.IsNullOrWhiteSpace(id))
                return $"#{EscapeCssId(id)}";

            // Incearca name
            var name = await element.GetAttributeAsync("name");
            if (!string.IsNullOrWhiteSpace(name))
                return $"[name='{name}']";

            // Incearca data-testid (bun pentru testing)
            var testId = await element.GetAttributeAsync("data-testid");
            if (!string.IsNullOrWhiteSpace(testId))
                return $"[data-testid='{testId}']";

            // Incearca aria-label
            var ariaLabel = await element.GetAttributeAsync("aria-label");
            if (!string.IsNullOrWhiteSpace(ariaLabel))
                return $"[aria-label='{ariaLabel}']";

            // Fallback: returneaza selectorul original
            return baseSelector;
        }
        catch
        {
            return baseSelector;
        }
    }

    // =========================================================
    // BuildSelectorForStep � Construieste selectorul potrivit
    // pentru un StepModel de tip browser_click / browser_fill
    // =========================================================
    public static string BuildSelectorForStep(StepModel step)
    {
        // Selector din KeyCombo (camp dedicat pentru browser steps)
        if (!string.IsNullOrWhiteSpace(step.KeyCombo))
            return step.KeyCombo;

        // Fallback: incearca sa extraga din Description
        if (!string.IsNullOrWhiteSpace(step.Description))
        {
            var match = Regex.Match(step.Description, @"selector=([^;]+)");
            if (match.Success)
                return match.Groups[1].Value.Trim();
        }

        return string.Empty;
    }

    // =========================================================
    // GetPageTitle � Titlul paginii curente
    // =========================================================
    public async Task<string> GetPageTitleAsync()
    {
        if (!_engine.IsOpen) return string.Empty;
        try { return await _engine.Page!.TitleAsync(); }
        catch { return string.Empty; }
    }

    // =========================================================
    // GetCurrentUrl � URL-ul curent
    // =========================================================
    public string GetCurrentUrl()
    {
        if (!_engine.IsOpen) return string.Empty;
        try { return _engine.Page!.Url; }
        catch { return string.Empty; }
    }

    // =========================================================
    // Helper: EscapeCssId � Escapeaza caractere speciale din ID CSS
    // =========================================================
    private static string EscapeCssId(string id)
    {
        // Escapeaza caractere speciale CSS
        return Regex.Replace(id, @"([^\w-])", @"\$1");
    }
}
