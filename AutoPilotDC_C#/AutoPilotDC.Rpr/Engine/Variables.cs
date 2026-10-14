// ============================================================
// AutoPilot DC v4 — RPR
// Variables.cs — Variabile de rulare + inlocuirea {Variabila}
// ============================================================

using System.Globalization;
using System.Text;

namespace AutoPilotDC.Rpr.Engine;

/// <summary>
/// Variabilele unei rulari. Numele nu tin cont de litere mari/mici.
/// Variabile speciale (calculate la cerere):
///   {Azi} / {Today}      -> data curenta (dd.MM.yyyy)
///   {Acum} / {Now}       -> data si ora (dd.MM.yyyy HH:mm:ss)
///   {Acum:yyyyMMdd}      -> data/ora in formatul dat
///   {NewLine}            -> rand nou
///   {Nume:url}           -> valoarea codificata pentru adrese web (si :upper, :lower, :trim)
/// Acoladele literale se scriu dublate: {{ si }}.
/// </summary>
public sealed class VariableStore
{
    private readonly Dictionary<string, string> _values = new(StringComparer.OrdinalIgnoreCase);

    public IReadOnlyDictionary<string, string> All => _values;

    public void Set(string name, string? value)
    {
        if (string.IsNullOrWhiteSpace(name)) return;
        _values[Normalize(name)] = value ?? "";
    }

    public void Remove(string name) => _values.Remove(Normalize(name));

    /// <summary>Sterge toate variabilele cu un prefix (ex: "Rand." la schimbarea randului).</summary>
    public void RemovePrefix(string prefix)
    {
        foreach (var k in _values.Keys.Where(k => k.StartsWith(prefix, StringComparison.OrdinalIgnoreCase)).ToList())
            _values.Remove(k);
    }

    public bool TryGet(string name, out string value)
    {
        name = Normalize(name);
        if (_values.TryGetValue(name, out value!)) return true;

        // Variabile speciale
        var now = DateTime.Now;
        var colon = name.IndexOf(':');
        var baseName = colon >= 0 ? name[..colon] : name;
        var format = colon >= 0 ? name[(colon + 1)..] : null;

        // {Variabila:url} / {Variabila:upper} / {Variabila:lower} / {Variabila:trim}
        if (format != null && _values.TryGetValue(baseName.Trim(), out var raw))
        {
            switch (format.Trim().ToLowerInvariant())
            {
                case "url":   value = Uri.EscapeDataString(raw); return true;
                case "upper": value = raw.ToUpperInvariant(); return true;
                case "lower": value = raw.ToLowerInvariant(); return true;
                case "trim":  value = raw.Trim(); return true;
            }
        }

        switch (baseName.ToLowerInvariant())
        {
            case "azi":
            case "today":
                value = now.ToString(format ?? "dd.MM.yyyy", CultureInfo.InvariantCulture);
                return true;
            case "acum":
            case "now":
                value = now.ToString(format ?? "dd.MM.yyyy HH:mm:ss", CultureInfo.InvariantCulture);
                return true;
            case "newline":
                value = Environment.NewLine;
                return true;
        }
        value = "";
        return false;
    }

    public string Get(string name) => TryGet(name, out var v) ? v : "";

    private static string Normalize(string name) => name.Trim().TrimStart('{').TrimEnd('}').Trim();

    // ─────────────────────────────────────────────────────────
    // Resolve — inlocuieste {Nume} in text
    // Variabilele necunoscute raman neschimbate (si sunt raportate).
    // ─────────────────────────────────────────────────────────
    public string Resolve(string? template) => Resolve(template, out _);

    public string Resolve(string? template, out List<string> unknown)
    {
        unknown = new List<string>();
        if (string.IsNullOrEmpty(template)) return "";
        if (template.IndexOf('{') < 0 && template.IndexOf('}') < 0) return template;

        var sb = new StringBuilder(template.Length + 16);
        int i = 0;
        while (i < template.Length)
        {
            char c = template[i];

            // 1. Acolade dublate = caracter literal
            if (c == '{' && i + 1 < template.Length && template[i + 1] == '{') { sb.Append('{'); i += 2; continue; }
            if (c == '}' && i + 1 < template.Length && template[i + 1] == '}') { sb.Append('}'); i += 2; continue; }

            // 2. {Nume}
            if (c == '{')
            {
                int end = template.IndexOf('}', i + 1);
                if (end > i + 1)
                {
                    var name = template.Substring(i + 1, end - i - 1);
                    if (name.IndexOf('{') < 0 && TryGet(name, out var val))
                    {
                        sb.Append(val);
                        i = end + 1;
                        continue;
                    }
                    if (name.IndexOf('{') < 0) unknown.Add(name);
                }
            }

            sb.Append(c);
            i++;
        }
        return sb.ToString();
    }
}
