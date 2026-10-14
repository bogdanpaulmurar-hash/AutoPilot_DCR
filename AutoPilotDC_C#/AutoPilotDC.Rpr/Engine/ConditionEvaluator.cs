// ============================================================
// AutoPilot DC v4 — RPR
// ConditionEvaluator.cs — Evalueaza conditiile din Daca / Repeta / Asteapta
// ============================================================

using System.Globalization;
using System.Text.RegularExpressions;
using AutoPilotDC.Rpr.Model;

namespace AutoPilotDC.Rpr.Engine;

public sealed class ConditionEvaluator
{
    private readonly ObjectRepository _repo;
    private readonly IDriverProvider _drivers;
    private readonly VariableStore _vars;

    public ConditionEvaluator(ObjectRepository repo, IDriverProvider drivers, VariableStore vars)
    {
        _repo = repo;
        _drivers = drivers;
        _vars = vars;
    }

    public async Task<bool> EvaluateAsync(Condition c, CancellationToken ct)
    {
        bool result = await EvaluateCoreAsync(c, ct);
        return c.Negate ? !result : result;
    }

    private async Task<bool> EvaluateCoreAsync(Condition c, CancellationToken ct)
    {
        switch (c.Kind)
        {
            // 1. Grupuri SI / SAU (evaluare scurtcircuitata)
            case ConditionKind.AllOf:
                foreach (var ch in c.Children)
                    if (!await EvaluateAsync(ch, ct)) return false;
                return true;

            case ConditionKind.AnyOf:
                foreach (var ch in c.Children)
                    if (await EvaluateAsync(ch, ct)) return true;
                return false;

            // 2. Comparatie de valori
            case ConditionKind.Compare:
                return Compare(_vars.Resolve(c.Left), c.Operator, _vars.Resolve(c.Right), c.IgnoreCase);

            // 3. NU exista: asteptam pana dispare (pana la TimeoutMs)
            case ConditionKind.ElementNotExists:
            {
                var obj = RequireObject(c.Target);
                var driver = _drivers.Get(obj.Technology);
                var deadline = DateTime.UtcNow.AddMilliseconds(Math.Max(0, c.TimeoutMs));
                while (true)
                {
                    var st = await driver.GetStateAsync(obj, 0, ct);
                    if (!st.Exists || !st.Visible) return true;
                    if (DateTime.UtcNow >= deadline) return false;
                    await Task.Delay(250, ct);
                }
            }

            // 4. Conditii pe element
            default:
            {
                var obj = RequireObject(c.Target);
                var driver = _drivers.Get(obj.Technology);
                var st = await driver.GetStateAsync(obj, Math.Max(0, c.TimeoutMs), ct);
                return c.Kind switch
                {
                    ConditionKind.ElementExists  => st.Exists,
                    ConditionKind.ElementVisible => st.Exists && st.Visible,
                    ConditionKind.ElementEnabled => st.Exists && st.Enabled,
                    ConditionKind.ElementText    => st.Exists && Compare(
                                                        string.IsNullOrEmpty(st.Text) ? st.Value : st.Text,
                                                        c.Operator, _vars.Resolve(c.Right), c.IgnoreCase),
                    _ => false,
                };
            }
        }
    }

    private UiObject RequireObject(string name) =>
        _repo.Find(name) ?? throw new RprStepException($"Conditia foloseste obiectul [{name}], care nu exista in Object Repository.");

    // ─────────────────────────────────────────────────────────
    // Compare — folosit si de teste
    // ─────────────────────────────────────────────────────────
    public static bool Compare(string left, CompareOperator op, string right, bool ignoreCase)
    {
        left ??= ""; right ??= "";
        var cmp = ignoreCase ? StringComparison.OrdinalIgnoreCase : StringComparison.Ordinal;
        var l = left.Trim();
        var r = right.Trim();

        switch (op)
        {
            case CompareOperator.Equals:      return NumEquals(l, r) ?? string.Equals(l, r, cmp);
            case CompareOperator.NotEquals:   return !(NumEquals(l, r) ?? string.Equals(l, r, cmp));
            case CompareOperator.Contains:    return l.Contains(r, cmp);
            case CompareOperator.NotContains: return !l.Contains(r, cmp);
            case CompareOperator.StartsWith:  return l.StartsWith(r, cmp);
            case CompareOperator.EndsWith:    return l.EndsWith(r, cmp);
            case CompareOperator.IsEmpty:     return l.Length == 0;
            case CompareOperator.IsNotEmpty:  return l.Length > 0;
            case CompareOperator.MatchesRegex:
                try
                {
                    return Regex.IsMatch(l, r, ignoreCase ? RegexOptions.IgnoreCase : RegexOptions.None,
                                         TimeSpan.FromSeconds(1));
                }
                catch (ArgumentException ex)
                {
                    throw new RprStepException($"Expresie regulata invalida: \"{r}\" ({ex.Message})");
                }
        }

        // Operatori de ordine: numeric daca se poate, altfel alfabetic
        int order = TryNumber(l, out var ln) && TryNumber(r, out var rn)
            ? ln.CompareTo(rn)
            : string.Compare(l, r, cmp);

        return op switch
        {
            CompareOperator.GreaterThan    => order > 0,
            CompareOperator.GreaterOrEqual => order >= 0,
            CompareOperator.LessThan       => order < 0,
            CompareOperator.LessOrEqual    => order <= 0,
            _ => false,
        };
    }

    private static bool? NumEquals(string l, string r) =>
        TryNumber(l, out var a) && TryNumber(r, out var b) ? a == b : null;

    /// <summary>Accepta 1234.5, 1234,5, 1.234,5 si 1,234.5.</summary>
    public static bool TryNumber(string s, out decimal value)
    {
        value = 0;
        if (string.IsNullOrWhiteSpace(s)) return false;
        s = s.Trim().Replace(" ", "").Replace(" ", "");
        if (!Regex.IsMatch(s, @"^[+-]?[\d.,]+$")) return false;

        int lastDot = s.LastIndexOf('.');
        int lastComma = s.LastIndexOf(',');
        if (lastDot >= 0 && lastComma >= 0)
        {
            // separatorul zecimal e cel din dreapta
            s = lastComma > lastDot ? s.Replace(".", "").Replace(',', '.') : s.Replace(",", "");
        }
        else if (lastComma >= 0)
        {
            // doar virgula: zecimala daca e una singura si nu are exact 3 cifre dupa
            s = s.Count(ch => ch == ',') == 1 && s.Length - lastComma - 1 != 3
                ? s.Replace(',', '.')
                : s.Replace(",", "");
        }
        return decimal.TryParse(s, NumberStyles.Number, CultureInfo.InvariantCulture, out value);
    }
}
