// ============================================================
// AutoPilot DC v4 — RPR
// Routine.cs — O rutina = setari + variabile + arbore de pasi
// ============================================================

namespace AutoPilotDC.Rpr.Model;

public sealed class RoutineSettings
{
    /// <summary>Ce se intampla la eroare cand pasul nu are politica proprie.</summary>
    public ErrorPolicy DefaultErrorPolicy { get; set; } = ErrorPolicy.Ask;

    /// <summary>Marcheaza elementul pe ecran inainte de fiecare actiune (ca SilkTest).</summary>
    public bool HighlightBeforeAction { get; set; } = true;

    /// <summary>Cat timp ramane marcat elementul (ms).</summary>
    public int HighlightMs { get; set; } = 350;

    /// <summary>Timeout implicit pentru gasirea elementelor (ms).</summary>
    public int DefaultTimeoutMs { get; set; } = 10000;

    /// <summary>Pauza intre pasi (ms) — util la verificare, 0 la productie.</summary>
    public int StepDelayMs { get; set; } = 0;

    /// <summary>De cate ori se reincearca automat un pas esuat inainte de politica de eroare.</summary>
    public int AutoRetries { get; set; } = 1;

    /// <summary>Captura de ecran automata la eroare.</summary>
    public bool ScreenshotOnError { get; set; } = true;

    /// <summary>v4.1: "Nu deranja" (fara notificari Windows) cat timp ruleaza rutina.</summary>
    public bool DoNotDisturb { get; set; } = true;

    /// <summary>
    /// v4.1: sistemul de preventie — pauza + intrebare la ferestre de eroare, aplicatii blocate,
    /// erori in bara de stare SAP si valori diferite de "Valoarea asteptata".
    /// </summary>
    public bool GuardEnabled { get; set; } = true;
}

public sealed class Routine
{
    /// <summary>Versiunea formatului (rutinele v3.9 sunt liste de StepModel, fara acest camp).</summary>
    public int FormatVersion { get; set; } = 2;

    public string Name { get; set; } = "Rutina noua";
    public string Description { get; set; } = "";

    /// <summary>Fisierul Object Repository folosit (gol = repository-ul implicit).</summary>
    public string RepositoryPath { get; set; } = "";

    /// <summary>Variabile cu valori initiale (editate in Studio, folosite ca {Nume}).</summary>
    public Dictionary<string, string> Variables { get; set; } = new();

    public RoutineSettings Settings { get; set; } = new();

    public List<RprNode> Steps { get; set; } = new();

    public DateTime CreatedAt { get; set; } = DateTime.Now;
    public DateTime ModifiedAt { get; set; } = DateTime.Now;

    // ── Utilitare pentru arbore ─────────────────────────────

    /// <summary>Toti pasii, recursiv (pentru validare / cautare).</summary>
    public IEnumerable<RprNode> AllNodes() => Flatten(Steps);

    public static IEnumerable<RprNode> Flatten(IEnumerable<RprNode> nodes)
    {
        foreach (var n in nodes)
        {
            yield return n;
            if (n is IContainerNode c)
                foreach (var (_, list) in c.Branches)
                    foreach (var child in Flatten(list))
                        yield return child;
        }
    }

    /// <summary>Gaseste lista care contine nodul (pentru mutare sus/jos, stergere).</summary>
    public List<RprNode>? FindParentList(RprNode node) => FindParentList(Steps, node);

    private static List<RprNode>? FindParentList(List<RprNode> list, RprNode node)
    {
        if (list.Contains(node)) return list;
        foreach (var n in list)
            if (n is IContainerNode c)
                foreach (var (_, child) in c.Branches)
                {
                    var found = FindParentList(child, node);
                    if (found != null) return found;
                }
        return null;
    }

    /// <summary>Numele obiectelor folosite de rutina (pentru validare inainte de rulare).</summary>
    public IEnumerable<string> ReferencedObjects()
    {
        foreach (var n in AllNodes())
        {
            if (n is ActionNode a && !string.IsNullOrWhiteSpace(a.Target)) yield return a.Target;
            var conds = n switch
            {
                IfNode i   => new[] { i.Condition },
                LoopNode l => new[] { l.Condition },
                WaitNode w => new[] { w.Condition },
                _          => Array.Empty<Condition>(),
            };
            foreach (var c in conds)
                foreach (var t in ConditionTargets(c))
                    yield return t;
        }
    }

    private static IEnumerable<string> ConditionTargets(Condition c)
    {
        if (!string.IsNullOrWhiteSpace(c.Target) && c.Kind is ConditionKind.ElementExists or ConditionKind.ElementNotExists
            or ConditionKind.ElementVisible or ConditionKind.ElementEnabled or ConditionKind.ElementText)
            yield return c.Target;
        foreach (var ch in c.Children)
            foreach (var t in ConditionTargets(ch))
                yield return t;
    }
}
