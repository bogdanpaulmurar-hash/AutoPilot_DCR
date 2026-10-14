// ============================================================
// AutoPilot DC v4 — RPR
// Condition.cs — Conditii configurate interactiv (dropdown-uri)
// Folosite de: Daca/Altfel, Repeta cat timp, Asteapta pana cand.
// ============================================================

namespace AutoPilotDC.Rpr.Model;

/// <summary>Ce verifica o conditie.</summary>
public enum ConditionKind
{
    // ── Despre un obiect din repository ──────────────────
    ElementExists,      // obiectul exista pe ecran
    ElementNotExists,   // obiectul NU exista (ex: popup-ul a disparut)
    ElementVisible,
    ElementEnabled,
    ElementText,        // textul obiectului <operator> valoare

    // ── Despre valori / variabile ────────────────────────
    Compare,            // {stanga} <operator> {dreapta}

    // ── Grupuri ──────────────────────────────────────────
    AllOf,              // SI  — toate conditiile copil sunt adevarate
    AnyOf,              // SAU — cel putin una e adevarata
}

/// <summary>Operatori de comparatie (afisati in dropdown).</summary>
public enum CompareOperator
{
    Equals,
    NotEquals,
    Contains,
    NotContains,
    StartsWith,
    EndsWith,
    IsEmpty,
    IsNotEmpty,
    GreaterThan,       // numeric daca ambele parti sunt numere, altfel alfabetic
    GreaterOrEqual,
    LessThan,
    LessOrEqual,
    MatchesRegex,
}

/// <summary>
/// O conditie. Toate campurile sunt simple (string/enum) ca sa poata fi
/// editate din Studio fara cod. Textele accepta variabile: {Rand.IBase}.
/// </summary>
public sealed class Condition
{
    public ConditionKind Kind { get; set; } = ConditionKind.ElementExists;

    /// <summary>Obiectul din repository (pentru Element*).</summary>
    public string Target { get; set; } = "";

    /// <summary>Partea stanga (pentru Compare). Ex: "{StatusExtras}".</summary>
    public string Left { get; set; } = "";

    public CompareOperator Operator { get; set; } = CompareOperator.Equals;

    /// <summary>Valoarea comparata. Ex: "Activ" sau "{Rand.Asteptat}".</summary>
    public string Right { get; set; } = "";

    /// <summary>Comparatie fara a tine cont de litere mari/mici.</summary>
    public bool IgnoreCase { get; set; } = true;

    /// <summary>Inverseaza rezultatul (NU).</summary>
    public bool Negate { get; set; }

    /// <summary>Cat asteptam sa apara elementul la verificare (ms). 0 = verificare instantanee.</summary>
    public int TimeoutMs { get; set; } = 0;

    /// <summary>Conditii copil pentru AllOf / AnyOf.</summary>
    public List<Condition> Children { get; set; } = new();

    /// <summary>Descriere lizibila, afisata in arborele rutinei.</summary>
    public string Describe()
    {
        string core = Kind switch
        {
            ConditionKind.ElementExists    => $"[{Target}] exista",
            ConditionKind.ElementNotExists => $"[{Target}] nu exista",
            ConditionKind.ElementVisible   => $"[{Target}] e vizibil",
            ConditionKind.ElementEnabled   => $"[{Target}] e activ",
            ConditionKind.ElementText      => $"text [{Target}] {OpText(Operator)} \"{Right}\"",
            ConditionKind.Compare          => $"{Left} {OpText(Operator)} \"{Right}\"",
            ConditionKind.AllOf            => "(" + string.Join(" SI ", Children.Select(c => c.Describe())) + ")",
            ConditionKind.AnyOf            => "(" + string.Join(" SAU ", Children.Select(c => c.Describe())) + ")",
            _ => Kind.ToString(),
        };
        return Negate ? $"NU {core}" : core;
    }

    public static string OpText(CompareOperator op) => op switch
    {
        CompareOperator.Equals         => "=",
        CompareOperator.NotEquals      => "≠",
        CompareOperator.Contains       => "contine",
        CompareOperator.NotContains    => "nu contine",
        CompareOperator.StartsWith     => "incepe cu",
        CompareOperator.EndsWith       => "se termina cu",
        CompareOperator.IsEmpty        => "e gol",
        CompareOperator.IsNotEmpty     => "nu e gol",
        CompareOperator.GreaterThan    => ">",
        CompareOperator.GreaterOrEqual => "≥",
        CompareOperator.LessThan       => "<",
        CompareOperator.LessOrEqual    => "≤",
        CompareOperator.MatchesRegex   => "potriveste regex",
        _ => op.ToString(),
    };
}
